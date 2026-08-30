from datetime import datetime
from typing import List
from pydantic import BaseModel

from app.models.skill import SkillSummary
from app.models.observation import Observation
from app.models.decision import Decision

class DashboardStats(BaseModel):
    totalObservations: int
    totalSkills: int
    streakDays: int
    lastActivityAt: datetime | None

class DashboardResponse(BaseModel):
    skills: List[SkillSummary]
    recentObservations: List[Observation]
    recentDecisions: List[Decision]
    stats: DashboardStats
