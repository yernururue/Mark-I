from typing import List
from fastapi import APIRouter, Depends
from google.cloud.firestore_v1.client import Client as FirestoreClient

from app.dependencies import get_db, get_current_user_id
from app.models.chat import ChatRequest, ChatResponse, ChatMessage
from app.services.chat_service import ChatService

router = APIRouter(tags=["Chat"])

@router.post("/chat", response_model=ChatResponse)
async def process_chat_message(
    request: ChatRequest,
    uid: str = Depends(get_current_user_id),
    db: FirestoreClient = Depends(get_db)
):
    """
    Отправка сообщения в чат (Web).
    """
    chat_service = ChatService(db)
    response_text = await chat_service.process_message(uid, request.text, channel="web")
    return ChatResponse(text=response_text)

@router.get("/messages", response_model=List[ChatMessage])
async def get_chat_messages(
    uid: str = Depends(get_current_user_id),
    db: FirestoreClient = Depends(get_db)
):
    """
    Получение истории сообщений пользователя.
    """
    messages_ref = db.collection("users").document(uid).collection("messages")
    docs = messages_ref.order_by("createdAt", direction="ASCENDING").limit_to_last(50).get()
    
    messages = []
    for doc in docs:
        data = doc.to_dict()
        messages.append(ChatMessage(
            id=data.get("id"),
            role=data.get("role"),
            channel=data.get("channel"),
            text=data.get("text"),
            createdAt=data.get("createdAt")
        ))
    return messages
