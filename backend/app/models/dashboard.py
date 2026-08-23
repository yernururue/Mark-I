from typing import List
from pydantic import BaseModel

from app.models.skill import SkillDetail
from app.models.observation import Observation

class DashboardStats(BaseModel):
    totalObservations: int
    totalDecisions: int
    activeSkills: int
    overallTrend: str

class DashboardResponse(BaseModel):
    skills: List[SkillDetail]
    recentObservations: List[Observation]
    recentDecisions: List[dict] # Will type this properly in later phases
    stats: DashboardStats
