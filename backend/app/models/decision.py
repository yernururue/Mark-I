from datetime import datetime
from typing import List, Literal
from pydantic import BaseModel, ConfigDict

class Decision(BaseModel):
    id: str
    observationId: str
    action: Literal["notified", "silent"]
    significanceScore: int
    threshold: int
    intensity: Literal["chill", "normal", "brutal"]
    escalationFlags: List[str]
    deliveryStatus: Literal["pending", "sent", "skipped", "failed"]
    reason: str
    createdAt: datetime

    model_config = ConfigDict(from_attributes=True)
