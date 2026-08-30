"""Durable per-user opportunity effects, independent of Telegram linkage."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from google.cloud import firestore
from google.cloud.firestore_v1.client import Client as FirestoreClient

from app.services.decision_service import DecisionService


@dataclass(frozen=True)
class AppliedOpportunityEffects:
    observation_id: str | None
    decision_id: str | None
    delivery_id: str | None
    should_notify: bool
    delivery_status: str
    telegram_chat_id: int | None
    reason: str | None


class OpportunityEffectService:
    """Apply one deterministic policy result for ``eventId + uid`` exactly once."""

    def __init__(
        self,
        db: FirestoreClient,
        *,
        transactional_runner: Callable = firestore.transactional,
        clock: Callable[[], datetime] | None = None,
    ):
        self._db = db
        self._transactional_runner = transactional_runner
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    @staticmethod
    def document_id(event_id: str, uid: str) -> str:
        return hashlib.sha256(f"opportunity:{event_id}:{uid}".encode("utf-8")).hexdigest()

    @staticmethod
    def _ids(event_id: str, uid: str) -> tuple[str, str, str]:
        digest = hashlib.sha256(f"opportunity:{event_id}:{uid}".encode("utf-8")).hexdigest()[:32]
        return f"opportunity-{digest}", f"opportunity-{digest}", f"opportunity-{digest}-telegram"

    @staticmethod
    def _from_record(data: dict[str, Any]) -> AppliedOpportunityEffects | None:
        effects = data.get("effects")
        if not isinstance(effects, dict) or effects.get("status") not in {"applied", "ignored"}:
            return None
        return AppliedOpportunityEffects(
            observation_id=effects.get("observationId"),
            decision_id=effects.get("decisionId"),
            delivery_id=effects.get("deliveryId"),
            should_notify=bool(effects.get("shouldNotify")),
            delivery_status=str(effects.get("deliveryStatus", "suppressed")),
            telegram_chat_id=effects.get("telegramChatId"),
            reason=effects.get("reason"),
        )

    def apply(
        self,
        *,
        uid: str,
        event_id: str,
        opportunity: dict[str, Any],
        analysis: dict[str, Any],
    ) -> AppliedOpportunityEffects:
        score = analysis.get("relevance_score")
        concept = analysis.get("concept")
        reasoning = analysis.get("reasoning")
        if not isinstance(score, int) or isinstance(score, bool) or not 0 <= score <= 10:
            raise ValueError("Opportunity relevance_score must be an integer from 0 to 10")
        if not isinstance(concept, str) or not concept.strip():
            raise ValueError("Opportunity concept must be non-blank")
        if not isinstance(reasoning, str):
            raise ValueError("Opportunity reasoning must be text")

        event_ref = self._db.collection("opportunity_effects").document(self.document_id(event_id, uid))
        user_ref = self._db.collection("users").document(uid)
        transaction = self._db.transaction()

        @self._transactional_runner
        def apply_in_transaction(transaction):
            snapshot = event_ref.get(transaction=transaction)
            existing = self._from_record(snapshot.to_dict() or {}) if snapshot.exists else None
            if existing is not None:
                return existing
            user_snapshot = user_ref.get(transaction=transaction)
            if not user_snapshot.exists:
                raise LookupError(f"Opportunity user {uid!r} does not exist")
            # The worker's stream snapshot can be stale while a Telegram link
            # or intensity update is committed. Delivery policy must use the
            # transactional user state, just like the GitHub effect path.
            current_user_data = user_snapshot.to_dict() or {}
            now = self._clock().astimezone(timezone.utc)
            if score < 7:
                effects = {
                    "status": "ignored",
                    "shouldNotify": False,
                    "deliveryStatus": "suppressed",
                    "telegramChatId": None,
                    "reason": "Opportunity relevance is below the persistence threshold",
                }
                transaction.set(event_ref, {"eventId": event_id, "uid": uid, "effects": effects, "updatedAt": now})
                return self._from_record({"effects": effects})

            observation_id, decision_id, delivery_id = self._ids(event_id, uid)
            outcome = DecisionService.evaluate_policy(
                significance=score,
                intensity=current_user_data.get("intensity", "normal"),
                escalation_flags=[],
            )
            telegram_chat_id = current_user_data.get("telegramChatId")
            if not isinstance(telegram_chat_id, int) or isinstance(telegram_chat_id, bool):
                telegram_chat_id = None
            delivery_status = "pending" if outcome.should_notify and telegram_chat_id is not None else "suppressed"
            metadata = {
                "eventId": event_id,
                "sourceUrl": opportunity.get("sourceUrl"),
                "sourceName": opportunity.get("sourceName"),
                "title": opportunity.get("title"),
            }
            transaction.set(
                user_ref.collection("observations").document(observation_id),
                {
                    "id": observation_id,
                    "source": "opportunity",
                    "summary": f"Found relevant opportunity: {opportunity.get('title', '')}. {reasoning}",
                    "concept": concept.strip(),
                    "sentiment": "positive",
                    "significanceScore": score,
                    "metadata": metadata,
                    "createdAt": now,
                },
            )
            transaction.set(
                user_ref.collection("decisions").document(decision_id),
                {
                    "schemaVersion": 2,
                    "id": decision_id,
                    "observationId": observation_id,
                    "action": "notified" if outcome.should_notify else "silent",
                    "significanceScore": score,
                    "threshold": outcome.threshold,
                    "intensity": outcome.intensity,
                    "escalationFlags": [],
                    "deliveryStatus": delivery_status,
                    "reason": outcome.reason,
                    "createdAt": now,
                    "expiresAt": now + timedelta(days=30),
                },
            )
            persisted_delivery_id = delivery_id if outcome.should_notify else None
            if persisted_delivery_id:
                transaction.set(
                    self._db.collection("delivery_effects").document(delivery_id),
                    {
                        "id": delivery_id,
                        "source": "opportunity",
                        "activityId": event_id,
                        "uid": uid,
                        "decisionId": decision_id,
                        "telegramChatId": telegram_chat_id,
                        "status": delivery_status,
                        "attempt": 0,
                        "createdAt": now,
                        "updatedAt": now,
                        "lastError": None,
                    },
                )
            effects = {
                "status": "applied",
                "observationId": observation_id,
                "decisionId": decision_id,
                "deliveryId": persisted_delivery_id,
                "shouldNotify": outcome.should_notify,
                "deliveryStatus": delivery_status,
                "telegramChatId": telegram_chat_id,
                "reason": outcome.reason,
            }
            transaction.set(
                event_ref,
                {"eventId": event_id, "uid": uid, "effects": effects, "updatedAt": now},
            )
            return self._from_record({"effects": effects})

        result = apply_in_transaction(transaction)
        if result is None:  # pragma: no cover - protects corrupt transaction adapter returns
            raise RuntimeError("Opportunity effect transaction returned no result")
        return result

    def get(self, *, uid: str, event_id: str) -> AppliedOpportunityEffects | None:
        """Return an already-decided effect before invoking AI on a redelivery."""
        snapshot = self._db.collection("opportunity_effects").document(
            self.document_id(event_id, uid)
        ).get()
        return self._from_record(snapshot.to_dict() or {}) if snapshot.exists else None
