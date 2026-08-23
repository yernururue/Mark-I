from datetime import datetime, timezone
from typing import List

from google.cloud.firestore_v1.client import Client as FirestoreClient
from google.cloud.firestore_v1.transforms import DELETE_FIELD

from app.models.skill import SkillDetail
from app.services.observation_service import ObservationService

class SkillService:
    def __init__(self, db: FirestoreClient):
        self._db = db
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

    def update_skill(self, uid: str, concept: str, assessment: int, weight: float = 0.3) -> float:
        """
        Updates a skill score based on a new assessment (1-10) and returns the new score.
        Formula: new = old * (1 - weight) + assessment * weight
        """
        doc_ref = self._collection.document(uid)
        
        # We need transaction to ensure atomic read-modify-write
        transaction = self._db.transaction()
        
        @self._db.transactional
        def update_in_transaction(transaction, doc_ref):
            snapshot = doc_ref.get(transaction=transaction)
            if not snapshot.exists:
                return 0.0
                
            data = snapshot.to_dict()
            skills = data.get("skills", {})
            current_score = skills.get(concept, 0.0)
            
            if current_score == 0.0:
                new_score = float(assessment)
            else:
                new_score = round(current_score * (1 - weight) + assessment * weight, 2)
                
            # Update only the specific skill field
            transaction.update(doc_ref, {
                f"skills.{concept}": new_score
            })
            
            return new_score

        return update_in_transaction(transaction, doc_ref)
