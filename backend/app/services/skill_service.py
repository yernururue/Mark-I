from datetime import datetime, timezone
import math
from typing import Callable, List

from google.cloud import firestore
from google.cloud.firestore_v1.client import Client as FirestoreClient

from app.models.skill import SkillDetail


class SkillUpdateError(ValueError):
    """Invalid skill-update input that must not open a transaction."""


class UserNotFoundError(LookupError):
    """Skill updates require an existing user document."""

class SkillService:
    def __init__(self, db: FirestoreClient, transactional_runner: Callable = firestore.transactional):
        self._db = db
        self._transactional_runner = transactional_runner
        self._collection = db.collection("users")
    def get_skills(self, uid: str) -> List[SkillDetail]:
        """Build all skill projections from one persisted observation read.

        The old implementation issued one aggregation query per skill and used
        ``now()`` plus a hard-coded trend. This method makes no request-time
        claims: timestamps and direction come from observations/skillSignals.
        """
        doc = self._collection.document(uid).get()
        if not doc.exists:
            return []
        data = doc.to_dict() or {}
        skills_dict = data.get("skills", {})
        if not isinstance(skills_dict, dict):
            return []
        observation_stats = self._observation_stats(uid)
        signals = data.get("skillSignals", {})
        fallback_updated_at = self._as_utc(data.get("updatedAt") or data.get("createdAt"))

        result: list[SkillDetail] = []
        for name, score in skills_dict.items():
            if not isinstance(name, str) or not isinstance(score, (int, float)) or not 0 <= score <= 10:
                continue
            count, observation_updated_at = observation_stats.get(name, (0, None))
            signal = signals.get(name) if isinstance(signals, dict) and isinstance(signals.get(name), dict) else {}
            last_updated = self._as_utc(signal.get("lastUpdatedAt")) or observation_updated_at or fallback_updated_at
            if last_updated is None:
                # An unversioned score without any persisted activity cannot
                # honestly satisfy the API's required lastUpdated contract.
                continue
            result.append(
                SkillDetail(
                    name=name,
                    score=round(float(score), 2),
                    trend=self._trend(count, signal),
                    observationCount=count,
                    lastUpdated=last_updated,
                )
            )
        result.sort(key=lambda x: x.score, reverse=True)
        return result

    def _observation_stats(self, uid: str) -> dict[str, tuple[int, datetime | None]]:
        """Return count/latest timestamp per concept with one collection read."""
        stats: dict[str, tuple[int, datetime | None]] = {}
        for snapshot in self._collection.document(uid).collection("observations").stream():
            data = snapshot.to_dict() or {}
            concept = data.get("concept")
            created_at = self._as_utc(data.get("createdAt"))
            if not isinstance(concept, str) or not concept or created_at is None:
                continue
            prior_count, prior_latest = stats.get(concept, (0, None))
            stats[concept] = (prior_count + 1, max(filter(None, (prior_latest, created_at))))
        return stats

    @staticmethod
    def _as_utc(value: object) -> datetime | None:
        if not isinstance(value, datetime):
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _trend(observation_count: int, signal: dict) -> str:
        if observation_count < 3:
            return "new"
        scores = [
            float(value)
            for value in signal.get("recentScores", [])
            if isinstance(value, (int, float))
        ]
        if len(scores) < 2:
            # There is not enough persisted score history to infer a change.
            return "stable"
        delta = scores[-1] - scores[0]
        if delta > 0.05:
            return "up"
        if delta < -0.05:
            return "down"
        return "stable"

    def update_skill(
        self,
        uid: str,
        concept: str,
        assessment: float,
        weight: float = 0.3,
        processed_event_id: str | None = None,
    ) -> float:
        """
        Updates a skill score based on a new assessment (1-10) and returns the new score.
        Formula: new = old * (1 - weight) + assessment * weight
        """
        if not concept or not concept.strip():
            raise SkillUpdateError("concept must be non-empty")
        if not math.isfinite(assessment) or not 0 <= assessment <= 10:
            raise SkillUpdateError("assessment must be a finite value from 0 to 10")
        if not math.isfinite(weight) or not 0 <= weight <= 1:
            raise SkillUpdateError("weight must be a finite value from 0 to 1")
        doc_ref = self._collection.document(uid)
        processed_ref = (
            self._db.collection("processed_events").document(processed_event_id)
            if processed_event_id
            else None
        )
        
        # We need transaction to ensure atomic read-modify-write
        transaction = self._db.transaction()
        
        @self._transactional_runner
        def update_in_transaction(transaction, doc_ref):
            if processed_ref is not None:
                processed_snapshot = processed_ref.get(transaction=transaction)
                effects = (processed_snapshot.to_dict() or {}).get("effects", {})
                prior_score = effects.get("skillScore")
                if prior_score is not None:
                    return float(prior_score)
            snapshot = doc_ref.get(transaction=transaction)
            if not snapshot.exists:
                raise UserNotFoundError(f"User {uid!r} does not exist")
                
            data = snapshot.to_dict() or {}
            skills = dict(data.get("skills", {}) or {})
            current_score = skills.get(concept, 0.0)
            
            if current_score == 0.0:
                new_score = float(assessment)
            else:
                new_score = round(current_score * (1 - weight) + assessment * weight, 2)
                
            prior_signal = (data.get("skillSignals") or {}).get(concept, {})
            prior_scores = [
                float(value)
                for value in prior_signal.get("recentScores", [])
                if isinstance(value, (int, float))
            ][-2:]
            prior_scores.append(new_score)
            signals = dict(data.get("skillSignals") or {})
            signals[concept] = {
                **(prior_signal if isinstance(prior_signal, dict) else {}),
                "recentScores": prior_scores,
                "lastUpdatedAt": datetime.now(timezone.utc),
            }
            # Replacing maps avoids interpreting a concept with dots as a
            # Firestore field path, and keeps score/signal mutations atomic.
            transaction.update(doc_ref, {"skills": {**skills, concept: new_score}, "skillSignals": signals})
            if processed_ref is not None:
                transaction.set(
                    processed_ref,
                    {"effects": {**effects, "skillScore": new_score}},
                    merge=True,
                )
            
            return new_score

        return update_in_transaction(transaction, doc_ref)
