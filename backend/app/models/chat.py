from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Literal, Optional
from datetime import datetime

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    channel: Literal["web", "telegram"]
    turnId: str | None = Field(default=None, min_length=1, max_length=256)

    model_config = ConfigDict(extra="forbid")

    @field_validator("message", mode="before")
    @classmethod
    def strip_message(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("turnId", mode="before")
    @classmethod
    def strip_turn_id(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

class ChatResponse(BaseModel):
    response: str
    messageId: str
    agentMessageId: str

class Message(BaseModel):
    id: str
    role: Literal["user", "agent"]
    channel: Literal["web", "telegram"]
    text: str
    createdAt: datetime

class MessagesResponse(BaseModel):
    messages: list[Message]
    nextCursor: Optional[str] = None
    hasMore: bool


# Backward-compatible Python import; the public OpenAPI component is ``Message``.
ChatMessage = Message
