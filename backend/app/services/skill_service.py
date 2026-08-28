from datetime import datetime, timezone
import math
from typing import Callable, List

from google.cloud import firestore
from google.cloud.firestore_v1.client import Client as FirestoreClient
from google.cloud.firestore_v1.transforms import DELETE_FIELD

from app.models.skill import SkillDetail
from app.services.observation_service import ObservationService


class SkillUpdateError(ValueError):
    """Invalid skill-update input that must not open a transaction."""


class UserNotFoundError(LookupError):
    """Skill updates require an existing user document."""

class SkillService:
    def __init__(self, db: FirestoreClient, transactional_runner: Callable = firestore.transactional):
        self._db = db
        self._transactional_runner = transactional_runner
        self._collection = db.collection("users")
        self._obs_service = ObservationService(db)

    def get_skills(self, uid: str) -> List[SkillDetail]:
        """
        Retrieves all skills for the user.
        """
        doc = self._collection.document(uid).get()
        if not doc.exists:
            return []
            
        data = doc.to_dict()
        skills_dict = data.get("skills", {})
        
        result = []
        for name, score in skills_dict.items():
            # Basic implementation for now - you might want to store trend and lastUpdated in DB
            # but for MVP we compute trend simply and lastUpdated to now if not stored.
            obs_count = self._obs_service.get_observation_count(uid, name)
            
            result.append(SkillDetail(
                name=name,
                score=round(score, 2),
                trend="stable",  # Needs to be derived from history in a more complex setup
                observationCount=obs_count,
                lastUpdated=datetime.now(timezone.utc)
            ))
            
        # Sort by score descending
        result.sort(key=lambda x: x.score, reverse=True)
        return result

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
                
            data = snapshot.to_dict()
            skills = data.get("skills", {})
            current_score = skills.get(concept, 0.0)
            
            if current_score == 0.0:
                new_score = float(assessment)
            else:
                new_score = round(current_score * (1 - weight) + assessment * weight, 2)
                
            # Update only the specific skill field
            # Replacing the map avoids interpreting dots in a user-provided concept
            # as Firestore nested field paths.
            transaction.update(doc_ref, {"skills": {**skills, concept: new_score}})
            if processed_ref is not None:
                transaction.set(
                    processed_ref,
                    {"effects": {**effects, "skillScore": new_score}},
                    merge=True,
                )
            
            return new_score

        return update_in_transaction(transaction, doc_ref)
