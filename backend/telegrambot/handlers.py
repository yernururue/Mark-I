"""Telegram update routing with private-chat-only account interactions."""

from __future__ import annotations

from google.cloud.firestore_v1.client import Client as FirestoreClient

from app.services.telegram_service import TelegramService


def _is_private_chat(message: dict) -> bool:
    # ``type`` is mandatory in genuine Telegram updates. The default preserves
    # compatibility with minimal test fixtures while production group updates
    # are explicitly refused.
    return (message.get("chat") or {}).get("type", "private") == "private"


async def process_telegram_update(update: dict, db: FirestoreClient):
    """Route an update without making a chat id an account identity."""
    message = update.get("message") or update.get("edited_message")
    if not message:
        return
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    text = (message.get("text") or "").strip()
    if not isinstance(chat_id, int) or not text:
        return

    telegram_service = TelegramService(db)
    if not _is_private_chat(message):
        await telegram_service.send_message(
            chat_id,
            "For your privacy, please message Mark-I directly instead of using it in a group.",
        )
        return

    sender = message.get("from") or {}
    telegram_user_id = sender.get("id")
    if text.startswith("/start"):
        await _handle_start(chat_id, telegram_service)
    elif text.startswith("/link"):
        await _handle_link(chat_id, text, telegram_service, sender)
    elif not isinstance(telegram_user_id, int) or telegram_user_id <= 0:
        await telegram_service.send_message(chat_id, "I could not identify your Telegram account. Please try again.")
    else:
        from app.services.chat_service import ChatService
        from app.services.user_service import UserService

        uid = UserService(db).get_user_by_telegram_id(telegram_user_id)
        if not uid:
            await telegram_service.send_message(
                chat_id,
                "Your account is not linked. Please generate a code on the dashboard and send /link CODE.",
            )
            return
        update_id = update.get("update_id")
        turn_id = f"telegram:{update_id}" if isinstance(update_id, int) else None
        response = await ChatService(db).process_message(uid, text, channel="telegram", turn_id=turn_id)
        await telegram_service.send_message(chat_id, str(getattr(response, "response", response)))


async def _handle_start(chat_id: int, telegram_service: TelegramService):
    await telegram_service.send_message(
        chat_id,
        "Hello! I am Mark-I, your AI Developer Mentor.\n\n"
        "To link your account, generate a code in your dashboard and send me:\n/link CODE",
    )


async def _handle_link(chat_id: int, text: str, telegram_service: TelegramService, sender: dict):
    parts = text.split()
    telegram_user_id = sender.get("id")
    if len(parts) != 2 or not isinstance(telegram_user_id, int) or telegram_user_id <= 0:
        await telegram_service.send_message(chat_id, "Usage: /link CODE")
        return
    success = telegram_service.validate_and_link(
        parts[1],
        telegram_user_id,
        sender.get("username"),
        telegram_chat_id=chat_id,
    )
    if success:
        await telegram_service.send_message(
            chat_id,
            "Account successfully linked. I will now send you updates based on your intensity preference.",
        )
    else:
        await telegram_service.send_message(
            chat_id,
            "Invalid, expired, or already-used code. Please generate a new one from your dashboard.",
        )
