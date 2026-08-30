from datetime import datetime
from typing import List, Literal
from pydantic import BaseModel, ConfigDict, Field

class Decision(BaseModel):
    id: str
    observationId: str
    action: Literal["notified", "silent"]
    significanceScore: int = Field(ge=1, le=10)
    threshold: int = Field(ge=1, le=10)
    intensity: Literal["chill", "normal", "brutal"]
    escalationFlags: List[str]
    deliveryStatus: Literal["pending", "sending", "sent", "suppressed", "failed", "unknown"]
    reason: str
    createdAt: datetime

    model_config = ConfigDict(from_attributes=True)
