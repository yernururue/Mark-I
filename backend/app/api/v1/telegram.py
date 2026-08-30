from fastapi import APIRouter, Depends

from app.api.contracts import error_responses
from app.config import Settings, get_settings
from app.dependencies import get_current_user_id, get_telegram_service
from app.models.telegram import LinkCodeResponse, SuccessResponse
from app.services.telegram_service import TelegramService

router = APIRouter(tags=["Telegram"])

@router.post("/telegram/link", response_model=LinkCodeResponse, responses=error_responses(401, 409, 422), operation_id="generateTelegramLinkCode")
async def generate_telegram_link(
    uid: str = Depends(get_current_user_id),
    telegram_service: TelegramService = Depends(get_telegram_service),
    settings: Settings = Depends(get_settings),
):
    """
    Generates a temporary code to link a Telegram account.
    """
    link = telegram_service.generate_link_code(uid)
    return LinkCodeResponse(
        linkCode=link.code,
        expiresAt=link.expires_at,
        botUsername=settings.TELEGRAM_BOT_USERNAME,
    )

@router.delete("/telegram/unlink", response_model=SuccessResponse, responses=error_responses(401, 422), operation_id="unlinkTelegram")
async def unlink_telegram(
    uid: str = Depends(get_current_user_id),
    telegram_service: TelegramService = Depends(get_telegram_service),
):
    """
    Unlinks the Telegram account from the current user.
    """
    return SuccessResponse(unlinked=telegram_service.unlink(uid))
