from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict

class Observation(BaseModel):
    id: str
    source: str
    summary: str
    concept: str
    sentiment: str
    significanceScore: int
    metadata: Optional[Dict[str, Any]] = None
    createdAt: datetime

    model_config = ConfigDict(from_attributes=True)

class ObservationsResponse(BaseModel):
    observations: list[Observation]
    nextCursor: Optional[str] = None
    hasMore: bool
