from typing import Literal
from fastapi import APIRouter, Depends, Query

from app.api.contracts import error_responses
from app.dependencies import get_chat_service, get_current_user_id
from app.models.chat import ChatRequest, ChatResponse, MessagesResponse
from app.services.chat_service import ChatService

router = APIRouter(tags=["Chat"])

@router.post("/chat", response_model=ChatResponse, responses=error_responses(401, 422), operation_id="sendChatMessage")
async def process_chat_message(
    request: ChatRequest,
    uid: str = Depends(get_current_user_id),
    chat_service: ChatService = Depends(get_chat_service),
):
    """
    Отправка сообщения в чат (Web).
    """
    return await chat_service.process_message(uid, request.message, channel=request.channel, turn_id=request.turnId)

@router.get("/messages", response_model=MessagesResponse, responses=error_responses(401, 422), operation_id="getMessages")
async def get_chat_messages(
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = None,
    channel: Literal["web", "telegram"] | None = None,
    uid: str = Depends(get_current_user_id),
    chat_service: ChatService = Depends(get_chat_service),
):
    """
    Получение истории сообщений пользователя.
    """
    return chat_service.get_messages(uid, limit=limit, cursor=cursor, channel=channel)
