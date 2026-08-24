from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict

class Decision(BaseModel):
    id: str
    observationId: str
    significanceScore: int
    intensityThreshold: int
    escalationFlags: List[str]
    shouldNotify: bool
    reason: str
    createdAt: datetime

    model_config = ConfigDict(from_attributes=True)
