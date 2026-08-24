import logging
from google.cloud.firestore_v1.client import Client as FirestoreClient

from app.services.telegram_service import TelegramService

logger = logging.getLogger(__name__)

async def process_telegram_update(update: dict, db: FirestoreClient):
    """
    Parses a Telegram update dictionary and routes commands.
    """
    if "message" not in update:
        return
        
    message = update["message"]
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "").strip()
    
    if not chat_id or not text:
        return
        
    telegram_service = TelegramService(db)
    
    if text.startswith("/start"):
        await _handle_start(chat_id, telegram_service)
    elif text.startswith("/link"):
        await _handle_link(chat_id, text, telegram_service, message)
    else:
        # In a later phase, this will route to the Chat Service
        await telegram_service.send_message(
            chat_id, 
            "I only understand `/start` and `/link CODE` for now. Chat integration is coming in Phase 6."
        )

async def _handle_start(chat_id: int, telegram_service: TelegramService):
    welcome_text = (
        "Hello! I am Mark-I, your AI Developer Mentor.\n\n"
        "To link your account, generate a code in your dashboard and send me:\n"
        "`/link CODE`"
    )
    await telegram_service.send_message(chat_id, welcome_text)

async def _handle_link(chat_id: int, text: str, telegram_service: TelegramService, message: dict):
    parts = text.split()
    if len(parts) != 2:
        await telegram_service.send_message(chat_id, "Usage: `/link 123456`")
        return
        
    code = parts[1]
    username = message.get("from", {}).get("username")
    
    success = telegram_service.validate_and_link(code, chat_id, username)
    if success:
        await telegram_service.send_message(
            chat_id, 
            "✅ Account successfully linked! I will now send you updates based on your intensity preference."
        )
    else:
        await telegram_service.send_message(
            chat_id, 
            "❌ Invalid or expired code. Please generate a new one from your dashboard."
        )
