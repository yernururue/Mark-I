from fastapi import APIRouter, Depends

from app.dependencies import get_current_user_id, get_telegram_service
from app.models.telegram import LinkCodeResponse, SuccessResponse
from app.services.telegram_service import TelegramService

router = APIRouter(tags=["Telegram"])

@router.post("/telegram/link", response_model=LinkCodeResponse)
async def generate_telegram_link(
    uid: str = Depends(get_current_user_id),
    telegram_service: TelegramService = Depends(get_telegram_service),
):
    """
    Generates a temporary code to link a Telegram account.
    """
    link = telegram_service.generate_link_code(uid)
    from app.config import get_settings
    return LinkCodeResponse(
        linkCode=link.code,
        expiresAt=link.expires_at,
        botUsername=get_settings().TELEGRAM_BOT_USERNAME,
    )

@router.delete("/telegram/unlink", response_model=SuccessResponse)
async def unlink_telegram(
    uid: str = Depends(get_current_user_id),
    telegram_service: TelegramService = Depends(get_telegram_service),
):
    """
    Unlinks the Telegram account from the current user.
    """
    return SuccessResponse(unlinked=telegram_service.unlink(uid))
