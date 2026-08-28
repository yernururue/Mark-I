"""
github_service.py — Сервис интеграции с GitHub API, Secret Manager и Pub/Sub.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import logging
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

        gh_username = gh_user_response.json().get("login")

        # Сохраняем токен в Secret Manager
        secret_name = self._store_token(user_uid, access_token)

        # Обновляем Firestore
        now = datetime.now(timezone.utc)
        self._collection.document(user_uid).update({
            "githubConnected": True,
            "githubUsername": gh_username,
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
        webhook_ids: Dict[str, str] = user_data.get("webhookIds", {})

        target_repos = set(repo_names)

        repos_to_add = target_repos - current_connected
        repos_to_remove = current_connected - target_repos

        webhooks_registered_count = 0

        # Регистрируем вебхуки для новых репозиториев
        if self._settings.WEBHOOK_BASE_URL:
            webhook_target_url = f"{self._settings.WEBHOOK_BASE_URL.rstrip('/')}/api/v1/webhooks/github"

            for repo in repos_to_add:
                try:
                    hook_res = await self._httpx.post(
                        f"https://api.github.com/repos/{repo}/hooks",
                        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"},
                        json={
                            "name": "web",
                            "active": True,
                            "events": ["push", "pull_request", "pull_request_review", "issues", "issue_comment", "create"],
                            "config": {
                                "url": webhook_target_url,
                                "content_type": "json",
                                "secret": self._settings.GITHUB_WEBHOOK_SECRET,
                                "insecure_ssl": "0",
                            },
                        },
                    )
                    if hook_res.status_code in (200, 201):
                        hook_data = hook_res.json()
                        webhook_ids[repo] = str(hook_data.get("id"))
                        webhooks_registered_count += 1
                    else:
                        logger.warning(f"Could not register webhook for {repo}: status {hook_res.status_code}")
                except Exception as e:
                    logger.error(f"Error registering webhook for {repo}: {e}")

        # Удаляем вебхуки для удалённых репозиториев
        for repo in repos_to_remove:
            hook_id = webhook_ids.pop(repo, None)
            if hook_id and token:
                try:
                    await self._httpx.delete(
                        f"https://api.github.com/repos/{repo}/hooks/{hook_id}",
                        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"},
                    )
                except Exception as e:
                    logger.warning(f"Could not delete webhook {hook_id} for {repo}: {e}")

        new_connected = list(target_repos)
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
            for repo, hook_id in webhook_ids.items():
                try:
                    await self._httpx.delete(
                        f"https://api.github.com/repos/{repo}/hooks/{hook_id}",
                        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"},
                    )
                except Exception as e:
                    logger.warning(f"Disconnect: failed to delete webhook {hook_id} for {repo}: {e}")
        except Exception:
            pass

        # Удаляем токен из Secret Manager
        self._delete_token(user_uid)

        # Сбрасываем Firestore
        now = datetime.now(timezone.utc)
        self._collection.document(user_uid).update({
            "githubConnected": False,
            "githubUsername": None,
            "githubTokenSecretName": None,
            "connectedRepos": [],
            "webhookIds": {},
            "githubOAuthState": None,
            "updatedAt": now,
        })

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

    def _find_connected_user_ids(self, repo_full_name: str) -> list[str]:
        """Return all users monitoring a repository, in deterministic uid order.

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

    def publish_event(self, event_type: str, delivery_id: str, payload: Dict[str, Any]) -> list[str]:
        """Publish one canonical envelope for every user monitoring the repository."""
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

        uids = self._find_connected_user_ids(repo_full_name)
        if not uids:
            logger.warning(
                "Ignoring GitHub delivery for an unconnected repository",
                extra={"delivery_id": delivery_id, "repo_full_name": repo_full_name},
            )
            return []

        for uid in uids:
            envelope = GitHubEventEnvelope(
                deliveryId=delivery_id,
                eventType=event_type,
                uid=uid,
                repoFullName=repo_full_name,
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
