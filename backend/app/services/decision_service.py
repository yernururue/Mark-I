import uuid
from datetime import datetime, timezone, timedelta
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

class DecisionService:
    def __init__(self, db: FirestoreClient):
        self._db = db

    def _get_collection(self, uid: str):
        return self._db.collection("users").document(uid).collection("decisions")
    
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
        threshold = INTENSITY_THRESHOLDS.get(intensity, INTENSITY_THRESHOLDS["normal"])
        
        should_notify = False
        reason = ""
        
        # Escalation overrides threshold
        if any(flag in ESCALATION_RULES for flag in escalation_flags):
            should_notify = True
            reason = f"Escalation: {', '.join(escalation_flags)}"
        elif significance is not None and significance >= threshold:
            should_notify = True
            reason = f"Significance {significance} >= threshold {threshold}"
        else:
            should_notify = False
            reason = f"Significance {significance} < threshold {threshold}"
            
        # 2. Log to Firestore
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=30)
        decision_id = decision_id or f"dec-{uuid.uuid4().hex[:12]}"
        
        doc_data = {
            "id": decision_id,
            "observationId": observation_id,
            "action": "notified" if should_notify else "silent",
            "significanceScore": significance,
            "threshold": threshold,
            "intensity": intensity if intensity in INTENSITY_THRESHOLDS else "normal",
            "escalationFlags": escalation_flags,
            "deliveryStatus": "pending" if should_notify else "skipped",
            "reason": reason,
            "createdAt": now,
            "expiresAt": expires_at,
        }
        
        self._get_collection(uid).document(decision_id).set(doc_data)
        
        return should_notify, reason
