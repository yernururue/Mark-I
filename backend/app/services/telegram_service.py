"""Telegram identity, outbound delivery, and webhook-update state.

Telegram's ``from.id`` identifies a person while ``chat.id`` identifies the
conversation where the bot can send a message. Treating them as the same
value breaks group chats and lets a shared chat become an account identity.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
import string
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Literal

import httpx
from google.cloud import firestore
from google.cloud.firestore_v1.client import Client as FirestoreClient
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_random_exponential

from app.config import Settings, get_settings
from app.errors import ConflictError

logger = logging.getLogger(__name__)

_http_client: httpx.AsyncClient | None = None
_LINK_CODE_ALPHABET = string.ascii_uppercase + string.digits


@dataclass(frozen=True)
class TelegramLinkCode:
    code: str
    expires_at: datetime


@dataclass(frozen=True)
class TelegramSendResult:
    """The distinction prevents retrying a request with an unknown outcome."""

    delivered: bool
    retryable: bool = False
    ambiguous: bool = False
    error: str | None = None


TelegramUpdateClaim = Literal["acquired", "completed", "busy"]


def get_http_client() -> httpx.AsyncClient:
    """Lazily create the process-owned HTTP client only when Telegram is used."""
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient()
    return _http_client


class TelegramService:
    def __init__(
        self,
        db: FirestoreClient,
        settings: Settings | None = None,
        transactional_runner: Callable = firestore.transactional,
        code_factory: Callable[[], str] | None = None,
        clock: Callable[[], datetime] | None = None,
    ):
        self._db = db
        self._transactional_runner = transactional_runner
        settings = settings or get_settings()
        self._bot_token = settings.TELEGRAM_BOT_TOKEN or ""
        self._code_factory = code_factory or self._new_link_code
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def _get_codes_collection(self):
        return self._db.collection("telegram_link_codes")

    def _get_identities_collection(self):
        return self._db.collection("telegram_identities")

    def _get_updates_collection(self):
        return self._db.collection("telegram_updates")

    def _get_users_collection(self):
        return self._db.collection("users")

    @staticmethod
    def _new_link_code() -> str:
        return "".join(secrets.choice(_LINK_CODE_ALPHABET) for _ in range(6))

    @staticmethod
    def _code_document_id(code: str) -> str:
        """Do not store a reusable dashboard secret as a Firestore document id."""
        return hashlib.sha256(code.encode("utf-8")).hexdigest()

    def _code_ref(self, code: str):
        return self._get_codes_collection().document(self._code_document_id(code))

    async def send_message_result(
        self,
        chat_id: int,
        text: str,
        parse_mode: str | None = None,
    ) -> TelegramSendResult:
        """Send an outbound message without collapsing definite and unknown failure.

        A transport failure can happen after Telegram accepted a request. Callers
        record it as unknown instead of resending the same business effect. A
        429/5xx response can safely be retried.
        """
        if not self._bot_token:
            logger.error("TELEGRAM_BOT_TOKEN is not set")
            return TelegramSendResult(delivered=False, error="bot token is not configured")

        url = f"https://api.telegram.org/bot{self._bot_token}/sendMessage"
        payload: dict[str, object] = {"chat_id": chat_id, "text": text}
        if parse_mode is not None:
            payload["parse_mode"] = parse_mode
        try:
            response = await get_http_client().post(url, json=payload, timeout=10.0)
        except httpx.RequestError as exc:
            # RequestError text can include the token-bearing Telegram URL.
            logger.warning("Telegram delivery outcome is unknown: %s", type(exc).__name__)
            return TelegramSendResult(delivered=False, ambiguous=True, error="transport failure")
        except Exception:  # Defensive seam for an injected/non-httpx client.
            logger.exception("Telegram delivery outcome is unknown")
            return TelegramSendResult(delivered=False, ambiguous=True, error="transport failure")

        if response.status_code == 200:
            try:
                if response.json().get("ok", True):
                    return TelegramSendResult(delivered=True)
            except (ValueError, AttributeError):
                return TelegramSendResult(delivered=True)
            return TelegramSendResult(delivered=False, error="telegram rejected request")
        if response.status_code == 429 or response.status_code >= 500:
            logger.warning("Telegram delivery retryable status: %s", response.status_code)
            return TelegramSendResult(delivered=False, retryable=True, error=f"HTTP {response.status_code}")
        logger.warning("Telegram delivery rejected: %s", response.status_code)
        return TelegramSendResult(delivered=False, error=f"HTTP {response.status_code}")

    async def send_message(self, chat_id: int, text: str, parse_mode: str | None = None) -> bool:
        """Compatibility wrapper for conversational replies, which are plain text."""
        return (await self.send_message_result(chat_id, text, parse_mode)).delivered

    def generate_link_code(self, uid: str) -> TelegramLinkCode:
        """Create one cryptographically-random, collision-safe ten-minute code."""
        user = self._get_users_collection().document(uid).get()
        if user.exists and (user.to_dict() or {}).get("telegramUserId") is not None:
            raise ConflictError("Telegram account is already linked")
        expires_at = self._clock() + timedelta(minutes=10)

        for _ in range(8):
            code = self._code_factory().strip().upper()
            if len(code) != 6 or any(character not in _LINK_CODE_ALPHABET for character in code):
                raise ValueError("link-code factory returned an invalid code")
            code_ref = self._code_ref(code)
            transaction = self._db.transaction()

            @self._transactional_runner
            def reserve_code(transaction):
                if code_ref.get(transaction=transaction).exists:
                    return False
                transaction.set(code_ref, {"uid": uid, "expiresAt": expires_at})
                return True

            if reserve_code(transaction):
                return TelegramLinkCode(code=code, expires_at=expires_at)
        raise RuntimeError("could not allocate a unique Telegram link code")

    def validate_and_link(
        self,
        code: str,
        telegram_user_id: int,
        username: str | None = None,
        telegram_chat_id: int | None = None,
    ) -> bool:
        """Atomically consume a code and claim the immutable Telegram identity."""
        code = code.strip().upper()
        if not code or not isinstance(telegram_user_id, int) or telegram_user_id <= 0:
            return False
        if telegram_chat_id is None or not isinstance(telegram_chat_id, int):
            telegram_chat_id = telegram_user_id

        code_ref = self._code_ref(code)
        identity_ref = self._get_identities_collection().document(str(telegram_user_id))

        @self._transactional_runner
        def consume_link_code(transaction):
            code_snapshot = code_ref.get(transaction=transaction)
            if not code_snapshot.exists:
                return False
            data = code_snapshot.to_dict() or {}
            expires_at = data.get("expiresAt")
            if expires_at and expires_at < self._clock():
                transaction.delete(code_ref)
                return False
            uid = data.get("uid")
            if not isinstance(uid, str) or not uid:
                transaction.delete(code_ref)
                return False

            user_ref = self._get_users_collection().document(uid)
            user_snapshot = user_ref.get(transaction=transaction)
            if not user_snapshot.exists:
                transaction.delete(code_ref)
                return False
            identity_snapshot = identity_ref.get(transaction=transaction)
            identity = identity_snapshot.to_dict() or {}
            if identity_snapshot.exists and identity.get("uid") != uid:
                # Do not burn an owner's valid code because a different person
                # attempted to claim an existing Telegram person identity.
                return False

            old_telegram_user_id = (user_snapshot.to_dict() or {}).get("telegramUserId")
            if isinstance(old_telegram_user_id, int) and old_telegram_user_id != telegram_user_id:
                old_identity_ref = self._get_identities_collection().document(str(old_telegram_user_id))
                old_identity = old_identity_ref.get(transaction=transaction)
                if old_identity.exists and (old_identity.to_dict() or {}).get("uid") == uid:
                    transaction.delete(old_identity_ref)

            now = self._clock()
            update_data = {
                "telegramUserId": telegram_user_id,
                "telegramChatId": telegram_chat_id,
                "updatedAt": now,
            }
            if username:
                update_data["telegramUsername"] = username
            transaction.update(user_ref, update_data)
            transaction.set(
                identity_ref,
                {
                    "uid": uid,
                    "telegramUserId": telegram_user_id,
                    "telegramChatId": telegram_chat_id,
                    "telegramUsername": username or None,
                    "updatedAt": now,
                },
            )
            transaction.delete(code_ref)
            return True

        # The SDK retries an aborted transaction with its original transaction
        # token. Under an actual concurrent code consume the emulator (and
        # Firestore pessimistic locking) can exhaust that token's lock wait.
        # Retry the complete, idempotent callback with a fresh transaction; by
        # then the winner has deleted the code and this call safely returns
        # ``False`` rather than surfacing a transient 500 to the bot user.
        @retry(
            retry=retry_if_exception_type(ValueError),
            wait=wait_random_exponential(multiplier=0.02, max=0.2),
            stop=stop_after_attempt(4),
            reraise=True,
        )
        def consume_with_fresh_transaction() -> bool:
            return consume_link_code(self._db.transaction())

        return consume_with_fresh_transaction()

    def unlink(self, uid: str) -> bool:
        """Idempotently detach the user and only their owned identity record."""
        user_ref = self._get_users_collection().document(uid)
        transaction = self._db.transaction()

        @self._transactional_runner
        def unlink_identity(transaction):
            user_snapshot = user_ref.get(transaction=transaction)
            if not user_snapshot.exists:
                return
            old_telegram_user_id = (user_snapshot.to_dict() or {}).get("telegramUserId")
            if isinstance(old_telegram_user_id, int):
                identity_ref = self._get_identities_collection().document(str(old_telegram_user_id))
                identity_snapshot = identity_ref.get(transaction=transaction)
                if identity_snapshot.exists and (identity_snapshot.to_dict() or {}).get("uid") == uid:
                    transaction.delete(identity_ref)
            transaction.update(
                user_ref,
                {
                    "telegramUserId": None,
                    "telegramChatId": None,
                    "telegramUsername": None,
                    "updatedAt": self._clock(),
                },
            )

        unlink_identity(transaction)
        for code_doc in self._get_codes_collection().where(
            filter=firestore.FieldFilter("uid", "==", uid)
        ).stream():
            self._get_codes_collection().document(code_doc.id).delete()
        return True

    def claim_update(self, update_id: int, *, lease_seconds: int = 120) -> TelegramUpdateClaim:
        """Claim one Telegram delivery before any user-visible side effect."""
        update_ref = self._get_updates_collection().document(str(update_id))
        transaction = self._db.transaction()

        @self._transactional_runner
        def claim(transaction):
            now = self._clock()
            snapshot = update_ref.get(transaction=transaction)
            data = snapshot.to_dict() or {}
            state = data.get("state")
            lease_until = data.get("leaseUntil")
            if state == "completed":
                return "completed"
            if state == "processing" and lease_until and lease_until > now:
                return "busy"
            transaction.set(
                update_ref,
                {
                    "state": "processing",
                    "leaseUntil": now + timedelta(seconds=lease_seconds),
                    "updatedAt": now,
                    "attempt": int(data.get("attempt", 0)) + 1,
                },
            )
            return "acquired"

        return claim(transaction)

    def complete_update(self, update_id: int) -> None:
        self._get_updates_collection().document(str(update_id)).update(
            {"state": "completed", "leaseUntil": None, "updatedAt": self._clock()}
        )

    def release_update(self, update_id: int) -> None:
        """Make a failed handler delivery immediately eligible for Telegram retry."""
        self._get_updates_collection().document(str(update_id)).update(
            {"state": "retryable", "leaseUntil": None, "updatedAt": self._clock()}
        )
