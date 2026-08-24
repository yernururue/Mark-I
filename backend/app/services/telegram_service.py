import os
import uuid
import random
import string
import httpx
from datetime import datetime, timezone, timedelta
import logging

from google.cloud.firestore_v1.client import Client as FirestoreClient

logger = logging.getLogger(__name__)

class TelegramService:
    def __init__(self, db: FirestoreClient):
        self._db = db
        # Usually from config, but let's read from env directly or pass via config
        self._bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")

    def _get_codes_collection(self):
        return self._db.collection("telegram_link_codes")
        
    def _get_users_collection(self):
        return self._db.collection("users")

    async def send_message(self, chat_id: int, text: str, parse_mode: str = "Markdown") -> bool:
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
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=10.0)
                if response.status_code == 200:
                    return True
                else:
                    logger.error(f"Failed to send Telegram message: {response.text}")
                    return False
        except Exception as e:
            logger.error(f"Exception sending Telegram message: {e}")
            return False

    def generate_link_code(self, uid: str) -> str:
        """
        Generates a 6-character code and stores it with a 10-minute TTL.
        """
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
        
        self._get_codes_collection().document(code).set({
            "uid": uid,
            "expiresAt": expires_at
        })
        
        return code

    def validate_and_link(self, code: str, telegram_user_id: int, username: str = None) -> bool:
        """
        Validates the code and links the telegram_user_id to the Firebase user.
        Returns True if successful, False otherwise.
        """
        code = code.strip().upper()
        doc_ref = self._get_codes_collection().document(code)
        doc = doc_ref.get()
        
        if not doc.exists:
            return False
            
        data = doc.to_dict()
        expires_at = data.get("expiresAt")
        
        if expires_at and expires_at < datetime.now(timezone.utc):
            doc_ref.delete()
            return False
            
        uid = data.get("uid")
        
        # Link the user
        user_ref = self._get_users_collection().document(uid)
        update_data = {
            "telegramLinked": True,
            "telegramUserId": telegram_user_id
        }
        if username:
            update_data["telegramUsername"] = username
            
        user_ref.update(update_data)
        
        # Delete code so it can't be reused
        doc_ref.delete()
        
        return True
