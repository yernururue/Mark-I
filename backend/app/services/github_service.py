"""
github_service.py — Сервис интеграции с GitHub API, Secret Manager и Pub/Sub.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import logging
import json
import uuid
import urllib.parse
import re
from typing import Any, Optional, Dict, List

from fastapi import HTTPException
from google.api_core.exceptions import NotFound, AlreadyExists
from google.cloud import pubsub_v1, secretmanager
from google.cloud.firestore_v1.client import Client as FirestoreClient
import httpx

from app.config import Settings
from app.models.github import GitHubEventEnvelope, GitHubRepo

logger = logging.getLogger(__name__)


SUPPORTED_GITHUB_EVENT_ACTIONS: dict[str, frozenset[str] | None] = {
    "push": None,
    "pull_request": frozenset({"opened", "reopened", "synchronize", "closed"}),
    "pull_request_review": frozenset({"submitted", "edited", "dismissed"}),
    "issues": frozenset({"opened", "edited", "closed", "reopened"}),
    "issue_comment": frozenset({"created", "edited"}),
    "create": None,
}


class GitHubService:
    """Сервис для интеграции с GitHub, работы с Secret Manager и Pub/Sub."""

    def __init__(
        self,
        db: FirestoreClient,
        httpx_client: httpx.AsyncClient,
        secret_client: secretmanager.SecretManagerServiceClient,
        pubsub_publisher: pubsub_v1.PublisherClient,
        settings: Settings,
    ):
        self._db = db
        self._collection = db.collection("users")
        self._httpx = httpx_client
        self._secret_client = secret_client
        self._pubsub_publisher = pubsub_publisher
        self._settings = settings

    # --- 1. OAuth Flow ---

    def generate_auth_url(self, user_uid: str) -> str:
        """Генерирует anti-CSRF state, сохраняет его в Firestore и возвращает GitHub OAuth URL."""
        state = str(uuid.uuid4())
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

        # Сохраняем state в профиль пользователя в Firestore
        self._collection.document(user_uid).update({
            "githubOAuthState": {
                "state": state,
                "expiresAt": expires_at,
            }
        })

        redirect_uri = f"{self._settings.FRONTEND_URL}/auth/github/callback"
        encoded_redirect_uri = urllib.parse.quote(redirect_uri, safe="")
        auth_url = (
            "https://github.com/login/oauth/authorize"
            f"?client_id={self._settings.GITHUB_CLIENT_ID}"
            f"&redirect_uri={encoded_redirect_uri}"
            "&scope=repo"
            f"&state={state}"
        )
        return auth_url

    async def exchange_code(self, user_uid: str, code: str, state: str) -> Dict[str, Any]:
        """Валидирует state, обменивает code на access token и сохраняет его в Secret Manager."""
        user_doc = self._collection.document(user_uid).get()
        if not user_doc.exists:
            raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Пользователь не найден"}})

        user_data = user_doc.to_dict() or {}
        saved_state_data = user_data.get("githubOAuthState")

        if not saved_state_data or saved_state_data.get("state") != state:
            raise HTTPException(status_code=400, detail={"error": {"code": "INVALID_STATE", "message": "Невалидный или отсутствующий OAuth state"}})

        # Проверка срока действия state
        expires_at = saved_state_data.get("expiresAt")
        if hasattr(expires_at, "timestamp"):
            expires_at = datetime.fromtimestamp(expires_at.timestamp(), tz=timezone.utc)
        if expires_at and expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail={"error": {"code": "EXPIRED_STATE", "message": "Срок действия OAuth state истёк"}})

        # Обнуляем state ДО обращения к API (защита от replay attack)
        self._collection.document(user_uid).update({"githubOAuthState": None})

        # Обмен кода на токен через GitHub API
        token_url = "https://github.com/login/oauth/access_token"
        headers = {"Accept": "application/json"}
        payload = {
            "client_id": self._settings.GITHUB_CLIENT_ID,
            "client_secret": self._settings.GITHUB_CLIENT_SECRET,
            "code": code,
        }

        response = await self._httpx.post(token_url, json=payload, headers=headers)
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail={"error": {"code": "GITHUB_API_ERROR", "message": "Ошибка обращения к GitHub API"}})

        data = response.json()
        access_token = data.get("access_token")
        if not access_token:
            error_desc = data.get("error_description", "Не удалось получить access token")
            raise HTTPException(status_code=400, detail={"error": {"code": "OAUTH_FAILED", "message": error_desc}})

        # Получаем данные профиля GitHub
        gh_user_response = await self._httpx.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github.v3+json"},
        )
        if gh_user_response.status_code != 200:
            raise HTTPException(status_code=502, detail={"error": {"code": "GITHUB_API_ERROR", "message": "Не удалось получить профиль GitHub"}})

        gh_user_data = gh_user_response.json()
        gh_username = gh_user_data.get("login")
        gh_user_id = gh_user_data.get("id")
        if not isinstance(gh_username, str) or not gh_username.strip():
            raise HTTPException(
                status_code=502,
                detail={"error": {"code": "GITHUB_API_ERROR", "message": "GitHub profile has no login"}},
            )

        # Сохраняем токен в Secret Manager
        secret_name = self._store_token(user_uid, access_token)

        # Обновляем Firestore
        now = datetime.now(timezone.utc)
        self._collection.document(user_uid).update({
            "githubConnected": True,
            "githubUsername": gh_username,
            "githubUserId": gh_user_id if isinstance(gh_user_id, int) else None,
            "githubTokenSecretName": secret_name,
            "updatedAt": now,
        })

        # Получаем доступные репозитории
        repos = await self.list_repos(user_uid, token=access_token)

        return {
            "githubUsername": gh_username,
            "repos": repos,
        }

    # --- 2. Secret Manager ---

    def _store_token(self, uid: str, token: str) -> str:
        """Создает или обновляет секрет github-token-{uid} в GCP Secret Manager."""
        secret_id = f"github-token-{uid}"
        parent = f"projects/{self._settings.GCP_PROJECT_ID}"
        secret_path = f"{parent}/secrets/{secret_id}"

        # Пробуем создать секрет
        try:
            self._secret_client.create_secret(
                request={
                    "parent": parent,
                    "secret_id": secret_id,
                    "secret": {"replication": {"automatic": {}}},
                }
            )
        except AlreadyExists:
            pass
        except Exception as e:
            logger.warning(f"Failed to create secret in Secret Manager (fallback to local mock if dev): {e}")

        # Добавляем версию секрета
        try:
            self._secret_client.add_secret_version(
                request={
                    "parent": secret_path,
                    "payload": {"data": token.encode("utf-8")},
                }
            )
        except Exception as e:
            logger.error(f"Error storing secret version for {secret_id}: {e}")
            raise HTTPException(status_code=503, detail="Ошибка сохранения секрета")

        return secret_id

    def _get_token(self, uid: str) -> str:
        """Читает последнюю версию секрета github-token-{uid} из Secret Manager."""
        secret_id = f"github-token-{uid}"
        name = f"projects/{self._settings.GCP_PROJECT_ID}/secrets/{secret_id}/versions/latest"
        try:
            response = self._secret_client.access_secret_version(request={"name": name})
            return response.payload.data.decode("utf-8")
        except Exception as e:
            logger.error(f"Error reading secret {secret_id}: {e}")
            raise HTTPException(
                status_code=400,
                detail={"error": {"code": "GITHUB_NOT_CONNECTED", "message": "GitHub токен не найден или устарел"}},
            )

    def _delete_token(self, uid: str) -> None:
        """Удаляет секрет github-token-{uid} из Secret Manager."""
        secret_id = f"github-token-{uid}"
        name = f"projects/{self._settings.GCP_PROJECT_ID}/secrets/{secret_id}"
        try:
            self._secret_client.delete_secret(request={"name": name})
        except NotFound:
            pass
        except Exception as e:
            logger.warning(f"Could not delete secret {secret_id}: {e}")

    # --- 3. Repos & Webhooks ---

    async def list_repos(self, user_uid: str, token: Optional[str] = None) -> List[GitHubRepo]:
        """Возвращает список репозиториев пользователя с отметкой подключённых."""
        if not token:
            token = self._get_token(user_uid)

        user_doc = self._collection.document(user_uid).get()
        connected_repos = set((user_doc.to_dict() or {}).get("connectedRepos", []))

        gh_response = await self._httpx.get(
            "https://api.github.com/user/repos?per_page=100&sort=updated",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"},
        )
        if gh_response.status_code != 200:
            raise HTTPException(status_code=502, detail={"error": {"code": "GITHUB_API_ERROR", "message": "Ошибка получения репозиториев от GitHub"}})

        raw_repos = gh_response.json()
        repos_list = []
        for r in raw_repos:
            full_name = r.get("full_name", "")
            is_private = r.get("private", False)
            repos_list.append(
                GitHubRepo(
                    fullName=full_name,
                    private=is_private,
                    connected=full_name in connected_repos,
                )
            )

        return repos_list

    async def select_repos(self, user_uid: str, repo_names: List[str]) -> Dict[str, Any]:
        """Регистрирует/удаляет вебхуки на GitHub и обновляет выбранные репозитории в Firestore."""
        repo_pattern = re.compile(r"^[\w\-\.]+/[\w\-\.]+$")
        for repo in repo_names:
            if not repo_pattern.match(repo):
                raise HTTPException(status_code=422, detail={"error": {"code": "INVALID_REPO", "message": "Некорректное имя репозитория"}})
        
        token = self._get_token(user_uid)

        user_doc = self._collection.document(user_uid).get()
        user_data = user_doc.to_dict() or {}

        current_connected = set(user_data.get("connectedRepos", []))
        webhook_ids: Dict[str, str] = dict(user_data.get("webhookIds", {}))

        target_repos = set(repo_names)

        repos_to_add = target_repos - current_connected
        repos_to_remove = current_connected - target_repos

        webhooks_registered_count = 0

        # Регистрируем вебхуки для новых репозиториев
        if self._settings.WEBHOOK_BASE_URL:
            webhook_target_url = f"{self._settings.WEBHOOK_BASE_URL.rstrip('/')}/api/v1/webhooks/github"

            for repo in sorted(repos_to_add):
                hook_id, created = await self._ensure_repository_webhook(
                    repo=repo,
                    uid=user_uid,
                    token=token,
                    target_url=webhook_target_url,
                )
                webhook_ids[repo] = hook_id
                webhooks_registered_count += int(created)

        # Удаляем вебхуки для удалённых репозиториев
        for repo in sorted(repos_to_remove):
            legacy_hook_id = webhook_ids.pop(repo, None)
            await self._release_repository_webhook(
                repo=repo,
                uid=user_uid,
                token=token,
                legacy_hook_id=legacy_hook_id,
            )

        new_connected = sorted(target_repos, key=str.casefold)
        now = datetime.now(timezone.utc)

        self._collection.document(user_uid).update({
            "connectedRepos": new_connected,
            "webhookIds": webhook_ids,
            "updatedAt": now,
        })

        return {
            "connectedRepos": new_connected,
            "webhooksRegistered": webhooks_registered_count,
        }

    async def disconnect(self, user_uid: str) -> None:
        """Отключает GitHub: удаляет вебхуки, секрет и сбрасывает данные в Firestore."""
        user_doc = self._collection.document(user_uid).get()
        if not user_doc.exists:
            return

        user_data = user_doc.to_dict() or {}
        webhook_ids: Dict[str, str] = user_data.get("webhookIds", {})

        # Пробуем прочитать токен для удаления вебхуков
        try:
            token = self._get_token(user_uid)
            connected_repos = set(user_data.get("connectedRepos", [])) | set(webhook_ids)
            for repo in sorted(connected_repos):
                await self._release_repository_webhook(
                    repo=repo,
                    uid=user_uid,
                    token=token,
                    legacy_hook_id=webhook_ids.get(repo),
                )
        except Exception:
            pass

        # Удаляем токен из Secret Manager
        self._delete_token(user_uid)

        # Сбрасываем Firestore
        now = datetime.now(timezone.utc)
        self._collection.document(user_uid).update({
            "githubConnected": False,
            "githubUsername": None,
            "githubUserId": None,
            "githubTokenSecretName": None,
            "connectedRepos": [],
            "webhookIds": {},
            "githubOAuthState": None,
            "updatedAt": now,
        })

    def _repository_hook_ref(self, repo: str):
        normalized = self._normalize_repo_full_name(repo)
        document_id = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        return self._db.collection("github_repository_hooks").document(document_id)

    def _repository_subscribers(self, repo: str, *, excluding_uid: str | None = None) -> set[str]:
        subscribers = set(self._find_repo_subscriber_ids(repo))
        if excluding_uid is not None:
            subscribers.discard(excluding_uid)
        return subscribers

    async def _discover_repository_hooks(self, repo: str, token: str, target_url: str) -> list[str]:
        """Find Mark-I hooks already pointing at this endpoint, including legacy duplicates."""
        try:
            response = await self._httpx.get(
                f"https://api.github.com/repos/{repo}/hooks?per_page=100",
                headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"},
            )
        except Exception:
            logger.warning("Could not inspect existing GitHub hooks for %s", repo)
            return []
        if response.status_code != 200 or not isinstance(response.json(), list):
            return []
        hook_ids = []
        for hook in response.json():
            config = hook.get("config") if isinstance(hook, dict) else None
            hook_id = hook.get("id") if isinstance(hook, dict) else None
            if isinstance(config, dict) and config.get("url") == target_url and hook_id is not None:
                hook_ids.append(str(hook_id))
        return sorted(set(hook_ids), key=lambda value: (not value.isdigit(), int(value) if value.isdigit() else value))

    async def _ensure_repository_webhook(
        self,
        *,
        repo: str,
        uid: str,
        token: str,
        target_url: str,
    ) -> tuple[str, bool]:
        registry_ref = self._repository_hook_ref(repo)
        registry = registry_ref.get()
        registry_data = registry.to_dict() or {}
        hook_id = registry_data.get("hookId") if registry.exists else None
        created = False

        if not hook_id or registry_data.get("targetUrl") != target_url:
            discovered = await self._discover_repository_hooks(repo, token, target_url)
            if discovered:
                hook_id = discovered[0]
                for duplicate_id in discovered[1:]:
                    try:
                        await self._httpx.delete(
                            f"https://api.github.com/repos/{repo}/hooks/{duplicate_id}",
                            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"},
                        )
                    except Exception:
                        logger.warning("Could not remove duplicate Mark-I hook %s for %s", duplicate_id, repo)
            else:
                hook_res = await self._httpx.post(
                    f"https://api.github.com/repos/{repo}/hooks",
                    headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"},
                    json={
                        "name": "web",
                        "active": True,
                        "events": sorted(SUPPORTED_GITHUB_EVENT_ACTIONS),
                        "config": {
                            "url": target_url,
                            "content_type": "json",
                            "secret": self._settings.GITHUB_WEBHOOK_SECRET,
                            "insecure_ssl": "0",
                        },
                    },
                )
                if hook_res.status_code not in (200, 201) or hook_res.json().get("id") is None:
                    raise HTTPException(
                        status_code=502,
                        detail={"error": {"code": "GITHUB_WEBHOOK_FAILED", "message": f"Could not register webhook for {repo}"}},
                    )
                hook_id = str(hook_res.json()["id"])
                created = True

        now = datetime.now(timezone.utc)
        subscribers = self._repository_subscribers(repo) | {uid}
        registry_ref.set(
            {
                "repoFullName": repo,
                "repoNormalized": self._normalize_repo_full_name(repo),
                "hookId": str(hook_id),
                "targetUrl": target_url,
                "subscriberUids": sorted(subscribers),
                "updatedAt": now,
                "createdAt": registry_data.get("createdAt", now),
            }
        )
        return str(hook_id), created

    async def _release_repository_webhook(
        self,
        *,
        repo: str,
        uid: str,
        token: str,
        legacy_hook_id: str | None,
    ) -> None:
        registry_ref = self._repository_hook_ref(repo)
        registry = registry_ref.get()
        registry_data = registry.to_dict() or {}
        shared_hook_id = str(registry_data.get("hookId")) if registry.exists and registry_data.get("hookId") else None
        remaining = self._repository_subscribers(repo, excluding_uid=uid)
        if remaining and shared_hook_id:
            registry_ref.update({"subscriberUids": sorted(remaining), "updatedAt": datetime.now(timezone.utc)})
            return

        hook_ids = {value for value in (shared_hook_id, legacy_hook_id) if value}
        for hook_id in hook_ids:
            try:
                await self._httpx.delete(
                    f"https://api.github.com/repos/{repo}/hooks/{hook_id}",
                    headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"},
                )
            except Exception:
                logger.warning("Could not delete Mark-I webhook %s for %s", hook_id, repo)
        if registry.exists:
            registry_ref.delete()

    # --- 4. Webhook HMAC Verification ---

    def verify_webhook_signature(self, payload_bytes: bytes, signature_header: str) -> bool:
        """Проверяет HMAC-SHA256 подпись вебхука от GitHub."""
        if not signature_header or not signature_header.startswith("sha256="):
            return False

        expected_sig = signature_header.split("=", 1)[1]
        secret_bytes = self._settings.GITHUB_WEBHOOK_SECRET.encode("utf-8")

        computed_hmac = hmac.new(secret_bytes, payload_bytes, hashlib.sha256).hexdigest()
        return hmac.compare_digest(computed_hmac, expected_sig)

    # --- 5. Pub/Sub Publishing ---

    @staticmethod
    def _normalize_repo_full_name(repo_full_name: str) -> str:
        return repo_full_name.strip().casefold()

    def _find_repo_subscriber_ids(self, repo_full_name: str) -> list[str]:
        """Return all users monitoring a repository, before actor attribution.

        Existing data may have repository names with differing case.  Scanning the
        user collection is deliberate for the current small MVP and gives exact,
        case-insensitive semantics until a normalized Firestore index is introduced.
        """
        normalized_repo = self._normalize_repo_full_name(repo_full_name)
        if not normalized_repo:
            return []

        uids = []
        for snapshot in self._collection.stream():
            data = snapshot.to_dict() or {}
            repos = data.get("connectedRepos") or []
            if any(
                isinstance(repo, str)
                and self._normalize_repo_full_name(repo) == normalized_repo
                for repo in repos
            ):
                uids.append(snapshot.id)
        return sorted(set(uids))

    @staticmethod
    def _event_actor(payload: Dict[str, Any]) -> tuple[str, int | None] | None:
        sender = payload.get("sender")
        if not isinstance(sender, dict):
            return None
        login = sender.get("login")
        actor_id = sender.get("id")
        if not isinstance(login, str) or not login.strip():
            return None
        return login.strip(), actor_id if isinstance(actor_id, int) and actor_id > 0 else None

    @staticmethod
    def _event_action(event_type: str, payload: Dict[str, Any]) -> str | None:
        if event_type in {"push", "create"}:
            return None
        action = payload.get("action")
        return action.strip() if isinstance(action, str) and action.strip() else None

    @classmethod
    def _is_supported_event(cls, event_type: str, payload: Dict[str, Any]) -> bool:
        supported_actions = SUPPORTED_GITHUB_EVENT_ACTIONS.get(event_type)
        if event_type not in SUPPORTED_GITHUB_EVENT_ACTIONS:
            return False
        if supported_actions is None:
            return True
        return cls._event_action(event_type, payload) in supported_actions

    def _find_connected_actor_user_ids(
        self,
        repo_full_name: str,
        *,
        actor_login: str,
        actor_id: int | None,
    ) -> list[str]:
        normalized_login = actor_login.casefold()
        matches: list[str] = []
        for uid in self._find_repo_subscriber_ids(repo_full_name):
            snapshot = self._collection.document(uid).get()
            data = snapshot.to_dict() or {}
            stored_id = data.get("githubUserId")
            stored_login = data.get("githubUsername")
            if actor_id is not None and isinstance(stored_id, int):
                matched = actor_id == stored_id
            else:
                matched = isinstance(stored_login, str) and stored_login.strip().casefold() == normalized_login
            if matched:
                matches.append(uid)
        return sorted(set(matches))

    @classmethod
    def _activity_id(
        cls,
        event_type: str,
        repo_full_name: str,
        payload: Dict[str, Any],
        actor_login: str,
        actor_id: int | None,
    ) -> str:
        action = cls._event_action(event_type, payload)
        if event_type == "push":
            identity = [payload.get("after"), payload.get("before"), payload.get("ref")]
        elif event_type == "pull_request":
            item = payload.get("pull_request") or {}
            identity = [item.get("id") or item.get("number"), item.get("updated_at"), (item.get("head") or {}).get("sha")]
        elif event_type == "pull_request_review":
            item = payload.get("review") or {}
            identity = [item.get("id"), item.get("submitted_at") or item.get("updated_at")]
        elif event_type == "issues":
            item = payload.get("issue") or {}
            identity = [item.get("id") or item.get("number"), item.get("updated_at")]
        elif event_type == "issue_comment":
            item = payload.get("comment") or {}
            identity = [item.get("id"), item.get("updated_at") or item.get("created_at")]
        else:
            identity = [payload.get("ref_type"), payload.get("ref")]
        fingerprint = {
            "eventType": event_type,
            "eventAction": action,
            "repo": cls._normalize_repo_full_name(repo_full_name),
            "actor": actor_id or actor_login.casefold(),
            "identity": identity,
        }
        digest = hashlib.sha256(
            json.dumps(fingerprint, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        ).hexdigest()
        return f"github:{digest}"

    def publish_event(self, event_type: str, delivery_id: str, payload: Dict[str, Any]) -> list[str]:
        """Publish only to the connected Mark-I account matching the event actor."""
        topic_path = self._pubsub_publisher.topic_path(
            self._settings.GCP_PROJECT_ID,
            self._settings.PUBSUB_GITHUB_TOPIC,
        )

        repo_full_name = payload.get("repository", {}).get("full_name", "")
        if not isinstance(repo_full_name, str) or not repo_full_name.strip():
            raise HTTPException(
                status_code=400,
                detail={"error": {"code": "BAD_REQUEST", "message": "Missing repository full name"}},
            )

        if not self._is_supported_event(event_type, payload):
            logger.info("Ignoring unsupported GitHub event/action %s/%s", event_type, payload.get("action"))
            return []

        actor = self._event_actor(payload)
        if actor is None:
            logger.warning("Ignoring GitHub delivery without a canonical sender", extra={"delivery_id": delivery_id})
            return []
        actor_login, actor_id = actor
        uids = self._find_connected_actor_user_ids(
            repo_full_name,
            actor_login=actor_login,
            actor_id=actor_id,
        )
        if not uids:
            logger.warning(
                "Ignoring GitHub delivery for an unconnected repository",
                extra={"delivery_id": delivery_id, "repo_full_name": repo_full_name},
            )
            return []

        for uid in uids:
            envelope = GitHubEventEnvelope(
                deliveryId=delivery_id,
                activityId=self._activity_id(event_type, repo_full_name, payload, actor_login, actor_id),
                eventType=event_type,
                eventAction=self._event_action(event_type, payload),
                uid=uid,
                repoFullName=repo_full_name,
                actorLogin=actor_login,
                actorId=actor_id,
                payload=payload,
            )
            try:
                future = self._pubsub_publisher.publish(
                    topic_path,
                    data=envelope.model_dump_json().encode("utf-8"),
                    schemaVersion=str(envelope.schemaVersion),
                    eventType=envelope.eventType,
                    repoFullName=envelope.repoFullName,
                    uid=envelope.uid,
                    deliveryId=envelope.deliveryId,
                )
                future.result(timeout=5)
            except Exception as exc:
                logger.error("Failed to publish GitHub delivery %s for uid %s", delivery_id, uid)
                raise HTTPException(status_code=500, detail="Ошибка публикации события") from exc
        return uids
