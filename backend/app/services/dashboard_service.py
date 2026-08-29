"""Firestore-backed dashboard aggregation without router-level data access."""

from __future__ import annotations

from datetime import datetime, timezone

from google.cloud.firestore_v1.client import Client as FirestoreClient
from google.cloud.firestore_v1.query import Query

from app.models.dashboard import DashboardResponse, DashboardStats
from app.models.decision import Decision
from app.services.observation_service import ObservationService
from app.services.skill_service import SkillService


class DashboardService:
    def __init__(self, db: FirestoreClient):
        self._db = db
        self._observations = ObservationService(db)
        self._skills = SkillService(db)

    def get_dashboard(
        self, uid: str, observation_limit: int, decision_limit: int
    ) -> DashboardResponse:
        skills = self._skills.get_skills(uid)
        observations = self._observations.get_recent_observations(uid, limit=observation_limit)
        decisions = self.get_recent_decisions(uid, decision_limit)
        total_observations = self._count_observations(uid)
        all_observations = self._observations.get_recent_observations(uid, limit=366)
        last_activity = all_observations[0].createdAt if all_observations else None
        return DashboardResponse(
            skills=skills,
            recentObservations=observations,
            recentDecisions=decisions,
            stats=DashboardStats(
                totalObservations=total_observations,
                totalSkills=len(skills),
                streakDays=self._streak_days(all_observations),
                lastActivityAt=last_activity,
            ),
        )

    def get_recent_decisions(self, uid: str, limit: int) -> list[Decision]:
        docs = (
            self._db.collection("users")
            .document(uid)
            .collection("decisions")
            .order_by("createdAt", direction=Query.DESCENDING)
            .limit(limit)
            .stream()
        )
        return [self._firestore_to_decision(doc.to_dict()) for doc in docs]

    def _count_observations(self, uid: str) -> int:
        count = self._observations._get_collection(uid).count().get()
        return count[0][0].value

    @staticmethod
    def _streak_days(observations: list) -> int:
        dates = {observation.createdAt.astimezone(timezone.utc).date() for observation in observations}
        if not dates:
            return 0
        current = max(dates)
        streak = 0
        while current in dates:
            streak += 1
            current = current.fromordinal(current.toordinal() - 1)
        return streak

    @staticmethod
    def _firestore_to_decision(data: dict) -> Decision:
        created_at = data["createdAt"]
        if hasattr(created_at, "timestamp"):
            created_at = datetime.fromtimestamp(created_at.timestamp(), tz=timezone.utc)
        return Decision(
            id=data["id"],
            observationId=data["observationId"],
            action=data["action"],
            significanceScore=data["significanceScore"],
            threshold=data["threshold"],
            intensity=data["intensity"],
            escalationFlags=data.get("escalationFlags", []),
            deliveryStatus=data.get("deliveryStatus", "pending"),
            reason=data["reason"],
            createdAt=created_at,
        )
