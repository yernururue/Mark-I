import uuid
import random
import string
import httpx
from datetime import datetime, timezone, timedelta
import logging
from dataclasses import dataclass
from typing import Callable

from google.cloud import firestore
from google.cloud.firestore_v1.client import Client as FirestoreClient
from app.config import Settings, get_settings
from app.errors import ConflictError

logger = logging.getLogger(__name__)

# Reusable module-level client
_http_client = None


@dataclass(frozen=True)
class TelegramLinkCode:
    code: str
    expires_at: datetime

def get_http_client() -> httpx.AsyncClient:
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
    ):
        self._db = db
        self._transactional_runner = transactional_runner
        settings = settings or get_settings()
        self._bot_token = settings.TELEGRAM_BOT_TOKEN or ""

    def _get_codes_collection(self):
        return self._db.collection("telegram_link_codes")
        
    def _get_users_collection(self):
        return self._db.collection("users")

    async def send_message(self, chat_id: int, text: str, parse_mode: str = "HTML") -> bool:
        """
        Sends a message to a Telegram chat using httpx.
        """
        if not self._bot_token:
            logger.error("TELEGRAM_BOT_TOKEN is not set.")
            return False
            
        url = f"https://api.telegram.org/bot{self._bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        }
        
        client = get_http_client()
        try:
            response = await client.post(url, json=payload, timeout=10.0)
            if response.status_code == 200:
                return True
            else:
                logger.error(f"Failed to send Telegram message: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Exception sending Telegram message: {e}")
            return False

    def generate_link_code(self, uid: str) -> TelegramLinkCode:
        """
        Generates a 6-character code and stores it with a 10-minute TTL.
        """
        user = self._get_users_collection().document(uid).get()
        if user.exists and (user.to_dict() or {}).get("telegramUserId") is not None:
            raise ConflictError("Telegram account is already linked")
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
        
        self._get_codes_collection().document(code).set({
            "uid": uid,
            "expiresAt": expires_at
        })
        
        return TelegramLinkCode(code=code, expires_at=expires_at)

    def validate_and_link(
        self,
        code: str,
        telegram_user_id: int,
        username: str | None = None,
        telegram_chat_id: int | None = None,
    ) -> bool:
        """
        Validates the code and links the telegram_user_id to the Firebase user.
        Returns True if successful, False otherwise.
        """
        code = code.strip().upper()
        if not code:
            return False
        doc_ref = self._get_codes_collection().document(code)
        transaction = self._db.transaction()
        chat_id = telegram_chat_id if telegram_chat_id is not None else telegram_user_id

        @self._transactional_runner
        def consume_link_code(transaction):
            doc = doc_ref.get(transaction=transaction)
            if not doc.exists:
                return False
            data = doc.to_dict() or {}
            expires_at = data.get("expiresAt")
            if expires_at and expires_at < datetime.now(timezone.utc):
                transaction.delete(doc_ref)
                return False
            uid = data.get("uid")
            if not isinstance(uid, str) or not uid:
                transaction.delete(doc_ref)
                return False
            user_ref = self._get_users_collection().document(uid)
            update_data = {
                "telegramUserId": telegram_user_id,
                "telegramChatId": chat_id,
                "updatedAt": datetime.now(timezone.utc),
            }
            if username:
                update_data["telegramUsername"] = username
            transaction.update(user_ref, update_data)
            transaction.delete(doc_ref)
            return True

        return consume_link_code(transaction)

    def unlink(self, uid: str) -> bool:
        """Idempotently clear Telegram identity and outstanding link codes."""
        user_ref = self._get_users_collection().document(uid)
        user = user_ref.get()
        if user.exists:
            user_ref.update(
                {
                    "telegramUserId": None,
                    "telegramChatId": None,
                    "telegramUsername": None,
                    "updatedAt": datetime.now(timezone.utc),
                }
            )
        for code_doc in self._get_codes_collection().where(
            filter=firestore.FieldFilter("uid", "==", uid)
        ).stream():
            self._get_codes_collection().document(code_doc.id).delete()
        return True
