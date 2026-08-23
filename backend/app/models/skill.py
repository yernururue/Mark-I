from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict

class SkillDetail(BaseModel):
    name: str
    score: float
    trend: str # 'up', 'down', 'stable', 'new'
    observationCount: int
    lastUpdated: datetime

    model_config = ConfigDict(from_attributes=True)

class SkillsResponse(BaseModel):
    skills: List[SkillDetail]
