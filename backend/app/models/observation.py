from datetime import datetime
from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, ConfigDict, Field

class Observation(BaseModel):
    id: str
    source: Literal["github", "opportunity", "chat"]
    summary: str
    concept: str
    sentiment: Literal["positive", "negative", "neutral"]
    significanceScore: int = Field(ge=1, le=10)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    createdAt: datetime

    model_config = ConfigDict(from_attributes=True)

class ObservationsResponse(BaseModel):
    observations: list[Observation]
    nextCursor: Optional[str] = None
    hasMore: bool
