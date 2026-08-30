import uuid
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from collections.abc import Sequence
from typing import List

from google.cloud.firestore_v1.client import Client as FirestoreClient

from app.models.decision import Decision

INTENSITY_THRESHOLDS = {
    "chill": 7,    # Only notify for highly significant events
    "normal": 5,   # Balanced notifications  
    "brutal": 3,   # Notify for almost everything
}

ESCALATION_RULES = [
    "repeated_error",      # Same concept, negative sentiment, 3+ times
    "skill_regression",    # Skill score decreased by >= 1 point
    "new_concept",         # First time a concept appears
    "milestone_reached",   # Skill score crosses 5 or 8
]


@dataclass(frozen=True)
class DecisionOutcome:
    should_notify: bool
    threshold: int
    intensity: str
    reason: str


def calculate_escalation_flags(
    *,
    concept_existed: bool,
    previous_score: float | None,
    updated_score: float,
    sentiment: str,
    recent_sentiments: Sequence[str],
) -> list[str]:
    """Return only supported deterministic flags in stable policy order."""
    flags: list[str] = []
    prior = previous_score if previous_score is not None else 0.0
    if not concept_existed:
        flags.append("new_concept")
    if concept_existed and updated_score <= prior - 1.0:
        flags.append("skill_regression")
    if any(prior < milestone <= updated_score for milestone in (5.0, 8.0)):
        flags.append("milestone_reached")
    if sentiment == "negative" and len(recent_sentiments) == 3 and all(
        item == "negative" for item in recent_sentiments
    ):
        flags.append("repeated_error")
    return [flag for flag in flags if flag in ESCALATION_RULES]

class DecisionService:
    def __init__(self, db: FirestoreClient):
        self._db = db

    def _get_collection(self, uid: str):
        return self._db.collection("users").document(uid).collection("decisions")

    @staticmethod
    def evaluate_policy(significance: int, intensity: str, escalation_flags: List[str]) -> DecisionOutcome:
        normalized_intensity = intensity if intensity in INTENSITY_THRESHOLDS else "normal"
        threshold = INTENSITY_THRESHOLDS[normalized_intensity]
        supported_flags = [flag for flag in escalation_flags if flag in ESCALATION_RULES]
        if supported_flags:
            return DecisionOutcome(True, threshold, normalized_intensity, f"Escalation: {', '.join(supported_flags)}")
        if significance >= threshold:
            return DecisionOutcome(
                True,
                threshold,
                normalized_intensity,
                f"Significance {significance} >= threshold {threshold}",
            )
        return DecisionOutcome(
            False,
            threshold,
            normalized_intensity,
            f"Significance {significance} < threshold {threshold}",
        )
    
    def evaluate_and_log(
        self,
        uid: str,
        observation_id: str,
        significance: int,
        intensity: str,
        escalation_flags: List[str],
        decision_id: str | None = None,
    ) -> tuple[bool, str]:
        """
        Evaluates whether a notification should be sent based on intensity and significance,
        logs the decision to Firestore, and returns (should_notify, reason).
        """
        # 1. Evaluate
        outcome = self.evaluate_policy(significance, intensity, escalation_flags)
            
        # 2. Log to Firestore
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=30)
        decision_id = decision_id or f"dec-{uuid.uuid4().hex[:12]}"
        
        doc_data = {
            "id": decision_id,
            "observationId": observation_id,
            "schemaVersion": 2,
            "action": "notified" if outcome.should_notify else "silent",
            "significanceScore": significance,
            "threshold": outcome.threshold,
            "intensity": outcome.intensity,
            "escalationFlags": escalation_flags,
            "deliveryStatus": "pending" if outcome.should_notify else "suppressed",
            "reason": outcome.reason,
            "createdAt": now,
            "expiresAt": expires_at,
        }
        
        self._get_collection(uid).document(decision_id).set(doc_data)
        
        return outcome.should_notify, outcome.reason
