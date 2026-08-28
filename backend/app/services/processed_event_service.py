"""Transactional ownership records for at-least-once event delivery."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Callable

from google.cloud import firestore
from google.cloud.firestore_v1.client import Client as FirestoreClient


class EventClaimStatus(StrEnum):
    ACQUIRED = "acquired"
    COMPLETED = "completed"
    BUSY = "busy"


class ProcessedEventService:
    """Own one source delivery per user before executing business side effects."""

    def __init__(
        self,
        db: FirestoreClient,
        *,
        clock: Callable[[], datetime] | None = None,
        lease: timedelta = timedelta(minutes=10),
        transactional_runner: Callable = firestore.transactional,
    ) -> None:
        self._db = db
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._lease = lease
        self._transactional_runner = transactional_runner

    @staticmethod
    def document_id(delivery_id: str, uid: str) -> str:
        return f"github:{delivery_id}:{uid}"

    def _document(self, delivery_id: str, uid: str):
        return self._db.collection("processed_events").document(self.document_id(delivery_id, uid))

    @staticmethod
    def _as_utc(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def claim(self, delivery_id: str, uid: str) -> EventClaimStatus:
        """Atomically acquire, recognize completion, or defer a live lease."""
        doc_ref = self._document(delivery_id, uid)
        transaction = self._db.transaction()

        @self._transactional_runner
        def claim_in_transaction(transaction, doc_ref):
            now = self._as_utc(self._clock())
            snapshot = doc_ref.get(transaction=transaction)
            if snapshot.exists:
                data = snapshot.to_dict() or {}
                if data.get("status") == "completed":
                    return EventClaimStatus.COMPLETED
                started_at = self._as_utc(data.get("startedAt"))
                if data.get("status") == "processing" and started_at and now - started_at < self._lease:
                    return EventClaimStatus.BUSY
                attempt = int(data.get("attempt", 0)) + 1
            else:
                attempt = 1

            transaction.set(
                doc_ref,
                {
                    "source": "github",
                    "deliveryId": delivery_id,
                    "userId": uid,
                    "status": "processing",
                    "attempt": attempt,
                    "startedAt": now,
                    "updatedAt": now,
                    "completedAt": None,
                    "lastError": None,
                },
                merge=True,
            )
            return EventClaimStatus.ACQUIRED

        return claim_in_transaction(transaction, doc_ref)

    def complete(self, delivery_id: str, uid: str) -> None:
        now = self._as_utc(self._clock())
        self._document(delivery_id, uid).update(
            {"status": "completed", "completedAt": now, "updatedAt": now, "lastError": None}
        )

    def release_for_retry(self, delivery_id: str, uid: str, error_class: str) -> None:
        now = self._as_utc(self._clock())
        self._document(delivery_id, uid).update(
            {"status": "retryable", "updatedAt": now, "lastError": error_class}
        )

    def claim_effect(self, delivery_id: str, uid: str, effect: str) -> bool:
        """Claim an external effect before it is issued, providing at-most-once send."""
        doc_ref = self._document(delivery_id, uid)
        transaction = self._db.transaction()

        @self._transactional_runner
        def claim_effect_in_transaction(transaction, doc_ref):
            snapshot = doc_ref.get(transaction=transaction)
            data = snapshot.to_dict() or {}
            effects = data.get("effects", {})
            if effects.get(effect):
                return False
            transaction.set(
                doc_ref,
                {"effects": {**effects, effect: "claimed"}, "updatedAt": self._as_utc(self._clock())},
                merge=True,
            )
            return True

        return claim_effect_in_transaction(transaction, doc_ref)
