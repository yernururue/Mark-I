from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import datetime

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    channel: Literal["web", "telegram"]

class ChatResponse(BaseModel):
    response: str
    messageId: str
    agentMessageId: str

class ChatMessage(BaseModel):
    id: str
    role: str
    channel: str
    text: str
    createdAt: datetime

class MessagesResponse(BaseModel):
    messages: list[ChatMessage]
    nextCursor: Optional[str] = None
    hasMore: bool
