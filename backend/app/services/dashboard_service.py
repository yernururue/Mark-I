"""Firestore-backed dashboard aggregation without router-level data access."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from google.cloud.firestore_v1.client import Client as FirestoreClient
from google.cloud.firestore_v1.query import Query

from app.models.dashboard import DashboardResponse, DashboardStats
from app.models.decision import Decision
from app.models.skill import SkillSummary
from app.services.decision_migration_service import DecisionMigrationService
from app.services.observation_service import ObservationService
from app.services.skill_service import SkillService


class DashboardService:
    def __init__(self, db: FirestoreClient, *, clock: Callable[[], datetime] | None = None):
        self._db = db
        self._observations = ObservationService(db)
        self._skills = SkillService(db)
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def get_dashboard(
        self, uid: str, observation_limit: int, decision_limit: int
    ) -> DashboardResponse:
        skill_details = self._skills.get_skills(uid)
        skills = [
            SkillSummary(
                name=skill.name,
                score=skill.score,
                trend=skill.trend,
                lastUpdated=skill.lastUpdated,
            )
            for skill in skill_details
        ]
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
                streakDays=self._streak_days(all_observations, self._clock()),
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
        decisions: list[Decision] = []
        for doc in docs:
            decision = self._firestore_to_decision(doc.to_dict() or {}, document_id=doc.id)
            if decision is not None:
                decisions.append(decision)
        return decisions

    def _count_observations(self, uid: str) -> int:
        count = self._observations._get_collection(uid).count().get()
        return count[0][0].value

    @staticmethod
    def _streak_days(observations: list, now: datetime) -> int:
        dates = {observation.createdAt.astimezone(timezone.utc).date() for observation in observations}
        today = now.astimezone(timezone.utc).date()
        # A historical streak is not a current streak. Product has not approved
        # a grace day, so only a run ending today is displayed as active.
        if today not in dates:
            return 0
        current = today
        streak = 0
        while current in dates:
            streak += 1
            current = current.fromordinal(current.toordinal() - 1)
        return streak

    @staticmethod
    def _firestore_to_decision(data: dict, *, document_id: str) -> Decision | None:
        migrated = DecisionMigrationService.normalize(data, document_id=document_id)
        if migrated.document is None:
            return None
        data = migrated.document
        created_at = data.get("createdAt")
        if hasattr(created_at, "timestamp"):
            created_at = datetime.fromtimestamp(created_at.timestamp(), tz=timezone.utc)
        try:
            return Decision(
                id=data["id"],
                observationId=data["observationId"],
                action=data["action"],
                significanceScore=data["significanceScore"],
                threshold=data["threshold"],
                intensity=data["intensity"],
                escalationFlags=data.get("escalationFlags", []),
                deliveryStatus=data["deliveryStatus"],
                reason=data["reason"],
                createdAt=created_at,
            )
        except (KeyError, TypeError, ValueError):
            # A corrupt legacy row is hidden rather than crashing every user's
            # dashboard; the migration command reports it for manual repair.
            return None
