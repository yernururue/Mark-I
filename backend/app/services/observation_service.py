import uuid
from datetime import datetime, timezone
from typing import List, Optional

from google.cloud.firestore_v1.client import Client as FirestoreClient
from google.cloud.firestore_v1.query import Query
from google.cloud.firestore_v1.base_query import FieldFilter

from app.models.observation import Observation, ObservationsResponse
from app.services.cursor import decode_cursor, encode_cursor

class ObservationService:
    def __init__(self, db: FirestoreClient):
        self._db = db

    def _get_collection(self, uid: str):
        return self._db.collection("users").document(uid).collection("observations")

    def create_observation(
        self,
        uid: str,
        source: str,
        summary: str,
        concept: str,
        sentiment: str,
        significance_score: int,
        metadata: Optional[dict] = None,
        observation_id: Optional[str] = None,
    ) -> Observation:
        """
        Creates a new observation in Firestore.
        """
        now = datetime.now(timezone.utc)
        obs_id = observation_id or f"obs-{uuid.uuid4().hex[:12]}"
        
        doc_data = {
            "id": obs_id,
            "source": source,
            "summary": summary,
            "concept": concept,
            "sentiment": sentiment,
            "significanceScore": significance_score,
            "metadata": metadata or {},
            "createdAt": now,
        }

        self._get_collection(uid).document(obs_id).set(doc_data)

        # Parse back to Pydantic model for consistency
        return self._firestore_to_observation(doc_data)

    def get_recent_observations(
        self, 
        uid: str, 
        limit: int = 10,
        concept: Optional[str] = None,
        source: Optional[str] = None,
    ) -> List[Observation]:
        """
        Reads recent observations, optionally filtered by concept.
        """
        query = self._get_collection(uid)
        
        if concept:
            query = query.where(filter=FieldFilter("concept", "==", concept))
        if source:
            query = query.where(filter=FieldFilter("source", "==", source))
            
        query = query.order_by("createdAt", direction=Query.DESCENDING).limit(limit)
        
        docs = query.stream()
        return [self._firestore_to_observation(doc.to_dict()) for doc in docs]

    def get_observations(
        self,
        uid: str,
        limit: int,
        cursor: str | None = None,
        source: str | None = None,
        concept: str | None = None,
    ) -> ObservationsResponse:
        """Return a stable newest-first page with no duplicate boundary item."""
        query = self._get_collection(uid)
        if source:
            query = query.where(filter=FieldFilter("source", "==", source))
        if concept:
            query = query.where(filter=FieldFilter("concept", "==", concept))
        query = query.order_by("createdAt", direction=Query.DESCENDING).order_by("__name__", direction=Query.DESCENDING)
        if cursor:
            created_at, document_id = decode_cursor(cursor)
            query = query.start_after({"createdAt": created_at, "__name__": document_id})
        docs = list(query.limit(limit + 1).stream())
        has_more = len(docs) > limit
        page_docs = docs[:limit]
        observations = [self._firestore_to_observation(doc.to_dict()) for doc in page_docs]
        next_cursor = None
        if has_more and observations:
            next_cursor = encode_cursor(observations[-1].createdAt, observations[-1].id)
        return ObservationsResponse(
            observations=observations,
            nextCursor=next_cursor,
            hasMore=has_more,
        )

    def get_observation_count(self, uid: str, concept: str) -> int:
        """
        Gets the total count of observations for a specific concept.
        In a real prod app with massive scale, you'd use Firestore Count() aggregation.
        For MVP, counting stream is fine or keeping a counter in the skill doc.
        We'll use standard count() aggregation.
        """
        query = self._get_collection(uid).where(filter=FieldFilter("concept", "==", concept))
        count_query = query.count()
        results = count_query.get()
        return results[0][0].value

    def _firestore_to_observation(self, data: dict) -> Observation:
        created_at = data.get("createdAt")
        if hasattr(created_at, "timestamp"):
            created_at = datetime.fromtimestamp(created_at.timestamp(), tz=timezone.utc)
            
        return Observation(
            id=data["id"],
            source=data["source"],
            summary=data["summary"],
            concept=data["concept"],
            sentiment=data["sentiment"],
            significanceScore=data.get("significanceScore", 0),
            metadata=data.get("metadata", {}),
            createdAt=created_at,
        )
