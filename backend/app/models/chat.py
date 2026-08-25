from pydantic import BaseModel
from typing import List
from datetime import datetime

class ChatRequest(BaseModel):
    text: str

class ChatResponse(BaseModel):
    text: str

class ChatMessage(BaseModel):
    id: str
    role: str
    channel: str
    text: str
    createdAt: datetime
