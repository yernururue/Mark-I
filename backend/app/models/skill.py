from datetime import datetime
from typing import List, Literal
from pydantic import BaseModel, ConfigDict, Field

class SkillDetail(BaseModel):
    name: str
    score: float = Field(ge=0, le=10)
    trend: Literal["up", "down", "stable", "new"]
    observationCount: int = Field(ge=0)
    lastUpdated: datetime

    model_config = ConfigDict(from_attributes=True)

class SkillsResponse(BaseModel):
    skills: List[SkillDetail]


class SkillSummary(BaseModel):
    """Dashboard projection; detailed counts belong to GET /skills only."""

    name: str
    score: float = Field(ge=0, le=10)
    trend: Literal["up", "down", "stable", "new"]
    lastUpdated: datetime

    model_config = ConfigDict(from_attributes=True)
