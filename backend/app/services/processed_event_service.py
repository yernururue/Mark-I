"""Durable state machines for logical GitHub activities and external delivery."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum
import hashlib
from typing import Any, Callable

from google.cloud import firestore
from google.cloud.firestore_v1.client import Client as FirestoreClient

from app.services.decision_service import DecisionService, calculate_escalation_flags


class EventClaimStatus(StrEnum):
    ACQUIRED = "acquired"
    COMPLETED = "completed"
    BUSY = "busy"


class DeliveryClaimStatus(StrEnum):
    ACQUIRED = "acquired"
    SENT = "sent"
    SUPPRESSED = "suppressed"
    UNKNOWN = "unknown"
    BUSY = "busy"


class ProcessedEventConflictError(ValueError):
    """The same logical activity key was reused for conflicting immutable data."""


@dataclass(frozen=True)
class AppliedGitHubEffects:
    observation_id: str
    decision_id: str
    delivery_id: str | None
    should_notify: bool
    delivery_status: str
    telegram_chat_id: int | None
    reason: str
    escalation_flags: tuple[str, ...]
    skill_score: float | None


class ProcessedEventService:
    """Own and resume one logical GitHub activity per Mark-I user."""

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
    def document_id(activity_id: str, uid: str) -> str:
        logical_id = activity_id if activity_id.startswith("github:") else f"github:{activity_id}"
        return f"{logical_id}:{uid}"

    def _document(self, activity_id: str, uid: str):
        return self._db.collection("processed_events").document(self.document_id(activity_id, uid))

    @staticmethod
    def _as_utc(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _append_unique(values: Any, value: str) -> list[str]:
        existing = [item for item in (values or []) if isinstance(item, str)]
        return existing if value in existing else [*existing, value]

    def claim(self, activity_id: str, uid: str, *, delivery_id: str | None = None) -> EventClaimStatus:
        """Acquire a logical activity while retaining physical delivery IDs for audit."""
        doc_ref = self._document(activity_id, uid)
        transaction = self._db.transaction()
        physical_delivery_id = delivery_id or activity_id

        @self._transactional_runner
        def claim_in_transaction(transaction, doc_ref):
            now = self._as_utc(self._clock())
            snapshot = doc_ref.get(transaction=transaction)
            if snapshot.exists:
                data = snapshot.to_dict() or {}
                delivery_ids = self._append_unique(data.get("deliveryIds"), physical_delivery_id)
                if data.get("status") in {"completed", "terminal"}:
                    transaction.set(doc_ref, {"deliveryIds": delivery_ids, "updatedAt": now}, merge=True)
                    return EventClaimStatus.COMPLETED
                started_at = self._as_utc(data.get("startedAt"))
                if data.get("status") in {"processing", "delivering"} and started_at and now - started_at < self._lease:
                    transaction.set(doc_ref, {"deliveryIds": delivery_ids, "updatedAt": now}, merge=True)
                    return EventClaimStatus.BUSY
                attempt = int(data.get("attempt", 0)) + 1
            else:
                delivery_ids = [physical_delivery_id]
                attempt = 1

            transaction.set(
                doc_ref,
                {
                    "source": "github",
                    "activityId": activity_id,
                    "deliveryIds": delivery_ids,
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

    def get_prepared(self, activity_id: str, uid: str) -> dict[str, Any] | None:
        snapshot = self._document(activity_id, uid).get()
        if not snapshot.exists:
            return None
        prepared = (snapshot.to_dict() or {}).get("prepared")
        return dict(prepared) if isinstance(prepared, dict) else None

    def prepare(
        self,
        activity_id: str,
        uid: str,
        *,
        analysis: dict[str, Any],
        event_context: dict[str, Any],
        evidence: dict[str, Any],
    ) -> dict[str, Any]:
        """Persist validated AI output before any observation/skill/decision effect."""
        doc_ref = self._document(activity_id, uid)
        transaction = self._db.transaction()

        @self._transactional_runner
        def prepare_in_transaction(transaction, doc_ref):
            snapshot = doc_ref.get(transaction=transaction)
            if not snapshot.exists:
                raise ProcessedEventConflictError("Logical GitHub event was not claimed")
            data = snapshot.to_dict() or {}
            existing = data.get("prepared")
            if isinstance(existing, dict):
                return dict(existing)
            prepared = {
                "analysis": dict(analysis),
                "eventContext": dict(event_context),
                "evidence": dict(evidence),
                "preparedAt": self._as_utc(self._clock()),
            }
            transaction.set(doc_ref, {"prepared": prepared, "updatedAt": self._as_utc(self._clock())}, merge=True)
            return prepared

        return prepare_in_transaction(transaction, doc_ref)

    @staticmethod
    def _effect_ids(activity_id: str, uid: str) -> tuple[str, str, str]:
        digest = hashlib.sha256(f"{activity_id}:{uid}".encode("utf-8")).hexdigest()[:32]
        return f"github-{digest}", f"github-{digest}", f"github-{digest}-telegram"

    @staticmethod
    def _weighted_score(current_score: float | None, assessment: float, weight: float = 0.3) -> float:
        current = float(current_score or 0.0)
        return float(assessment) if current == 0.0 else round(current * (1 - weight) + assessment * weight, 2)

    @staticmethod
    def _effects_from_record(data: dict[str, Any]) -> AppliedGitHubEffects | None:
        business = (data.get("effects") or {}).get("business")
        if not isinstance(business, dict) or business.get("status") != "applied":
            return None
        return AppliedGitHubEffects(
            observation_id=business["observationId"],
            decision_id=business["decisionId"],
            delivery_id=business.get("deliveryId"),
            should_notify=bool(business["shouldNotify"]),
            delivery_status=business["deliveryStatus"],
            telegram_chat_id=business.get("telegramChatId"),
            reason=business["reason"],
            escalation_flags=tuple(business.get("escalationFlags", [])),
            skill_score=business.get("skillScore"),
        )

    def apply_business_effects(self, activity_id: str, uid: str) -> AppliedGitHubEffects:
        """Atomically create the observation, skill mutation, decision and outbox."""
        event_ref = self._document(activity_id, uid)
        user_ref = self._db.collection("users").document(uid)
        transaction = self._db.transaction()

        @self._transactional_runner
        def apply_in_transaction(transaction, event_ref, user_ref):
            now = self._as_utc(self._clock())
            event_snapshot = event_ref.get(transaction=transaction)
            event_data = event_snapshot.to_dict() or {}
            existing = self._effects_from_record(event_data)
            if existing is not None:
                return existing
            prepared = event_data.get("prepared")
            if not isinstance(prepared, dict):
                raise ProcessedEventConflictError("Logical GitHub event has no prepared analysis")
            analysis = prepared.get("analysis") or {}
            event_context = prepared.get("eventContext") or {}
            evidence = prepared.get("evidence") or {}
            concept = analysis.get("concept")
            if not isinstance(concept, str) or not concept:
                raise ProcessedEventConflictError("Prepared analysis has no concept")

            user_snapshot = user_ref.get(transaction=transaction)
            if not user_snapshot.exists:
                raise LookupError(f"GitHub event user {uid!r} does not exist")
            user_data = user_snapshot.to_dict() or {}
            skills = dict(user_data.get("skills") or {})
            previous_score = skills.get(concept)
            supports_proficiency = bool(evidence.get("supportsProficiency"))
            updated_score: float | None = float(previous_score) if previous_score is not None else None
            skill_signals = dict(user_data.get("skillSignals") or {})
            flags: list[str] = []
            if supports_proficiency:
                updated_score = self._weighted_score(previous_score, float(analysis["proficiencyAssessment"]))
                prior_signal = skill_signals.get(concept) if isinstance(skill_signals.get(concept), dict) else {}
                sentiments = [
                    value
                    for value in prior_signal.get("recentSentiments", [])
                    if value in {"positive", "negative", "neutral"}
                ][-2:]
                sentiments.append(analysis["sentiment"])
                scores = [
                    float(value)
                    for value in prior_signal.get("recentScores", [])
                    if isinstance(value, (int, float))
                ][-2:]
                scores.append(updated_score)
                flags = calculate_escalation_flags(
                    concept_existed=concept in skills,
                    previous_score=float(previous_score) if previous_score is not None else None,
                    updated_score=updated_score,
                    sentiment=analysis["sentiment"],
                    recent_sentiments=sentiments,
                )
                skills[concept] = updated_score
                skill_signals[concept] = {
                    "recentSentiments": sentiments,
                    "recentScores": scores,
                    "lastUpdatedAt": now,
                    "lastActivityId": activity_id,
                }

            outcome = DecisionService.evaluate_policy(
                significance=int(analysis["significanceScore"]),
                intensity=user_data.get("intensity", "normal"),
                escalation_flags=flags,
            )
            observation_id, decision_id, outbox_id = self._effect_ids(activity_id, uid)
            telegram_chat_id = user_data.get("telegramChatId")
            if not isinstance(telegram_chat_id, int) or isinstance(telegram_chat_id, bool):
                telegram_chat_id = None
            delivery_status = "pending" if outcome.should_notify and telegram_chat_id is not None else "suppressed"

            metadata = dict(event_context.get("metadata") or {})
            metadata.update(
                {
                    "activityId": activity_id,
                    "deliveryIds": list(event_data.get("deliveryIds") or []),
                    "codeEvidence": evidence,
                }
            )
            observation_ref = user_ref.collection("observations").document(observation_id)
            decision_ref = user_ref.collection("decisions").document(decision_id)
            transaction.set(
                observation_ref,
                {
                    "id": observation_id,
                    "source": "github",
                    "summary": analysis["summary"],
                    "concept": concept,
                    "sentiment": analysis["sentiment"],
                    "significanceScore": int(analysis["significanceScore"]),
                    "metadata": metadata,
                    "createdAt": now,
                },
            )
            if supports_proficiency:
                transaction.update(user_ref, {"skills": skills, "skillSignals": skill_signals, "updatedAt": now})
            transaction.set(
                decision_ref,
                {
                    "schemaVersion": 2,
                    "id": decision_id,
                    "observationId": observation_id,
                    "action": "notified" if outcome.should_notify else "silent",
                    "significanceScore": int(analysis["significanceScore"]),
                    "threshold": outcome.threshold,
                    "intensity": outcome.intensity,
                    "escalationFlags": flags,
                    "deliveryStatus": delivery_status,
                    "reason": outcome.reason,
                    "createdAt": now,
                    "expiresAt": now + timedelta(days=30),
                },
            )
            delivery_id: str | None = None
            if outcome.should_notify:
                delivery_id = outbox_id
                transaction.set(
                    self._db.collection("delivery_effects").document(delivery_id),
                    {
                        "id": delivery_id,
                        "source": "github",
                        "activityId": activity_id,
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
            business = {
                "status": "applied",
                "observationId": observation_id,
                "decisionId": decision_id,
                "deliveryId": delivery_id,
                "shouldNotify": outcome.should_notify,
                "deliveryStatus": delivery_status,
                "telegramChatId": telegram_chat_id,
                "reason": outcome.reason,
                "escalationFlags": flags,
                "skillScore": updated_score,
                "appliedAt": now,
            }
            transaction.set(
                event_ref,
                {"effects": {**(event_data.get("effects") or {}), "business": business}, "updatedAt": now},
                merge=True,
            )
            return self._effects_from_record({"effects": {"business": business}})

        result = apply_in_transaction(transaction, event_ref, user_ref)
        if result is None:  # pragma: no cover - defensive guard for corrupt transaction results
            raise ProcessedEventConflictError("Business effect transaction returned no result")
        return result

    def claim_delivery(self, delivery_id: str, uid: str, decision_id: str) -> DeliveryClaimStatus:
        delivery_ref = self._db.collection("delivery_effects").document(delivery_id)
        decision_ref = self._db.collection("users").document(uid).collection("decisions").document(decision_id)
        transaction = self._db.transaction()

        @self._transactional_runner
        def claim_in_transaction(transaction, delivery_ref, decision_ref):
            now = self._as_utc(self._clock())
            snapshot = delivery_ref.get(transaction=transaction)
            data = snapshot.to_dict() or {}
            status = data.get("status")
            if status == "sent":
                return DeliveryClaimStatus.SENT
            if status == "suppressed":
                return DeliveryClaimStatus.SUPPRESSED
            if status == "unknown":
                return DeliveryClaimStatus.UNKNOWN
            started_at = self._as_utc(data.get("startedAt"))
            if status == "sending" and started_at and now - started_at < self._lease:
                return DeliveryClaimStatus.BUSY
            if status == "sending":
                transaction.update(delivery_ref, {"status": "unknown", "updatedAt": now, "lastError": "expired-sending-lease"})
                transaction.update(decision_ref, {"deliveryStatus": "unknown"})
                return DeliveryClaimStatus.UNKNOWN
            if status not in {"pending", "failed"}:
                return DeliveryClaimStatus.SUPPRESSED
            transaction.update(
                delivery_ref,
                {
                    "status": "sending",
                    "attempt": int(data.get("attempt", 0)) + 1,
                    "startedAt": now,
                    "updatedAt": now,
                    "lastError": None,
                },
            )
            transaction.update(decision_ref, {"deliveryStatus": "sending"})
            return DeliveryClaimStatus.ACQUIRED

        return claim_in_transaction(transaction, delivery_ref, decision_ref)

    def mark_delivery(self, delivery_id: str, uid: str, decision_id: str, status: str, error: str | None = None) -> None:
        if status not in {"sent", "failed", "unknown"}:
            raise ValueError(f"Unsupported delivery status {status!r}")
        delivery_ref = self._db.collection("delivery_effects").document(delivery_id)
        decision_ref = self._db.collection("users").document(uid).collection("decisions").document(decision_id)
        transaction = self._db.transaction()

        @self._transactional_runner
        def mark_in_transaction(transaction, delivery_ref, decision_ref):
            now = self._as_utc(self._clock())
            transaction.update(
                delivery_ref,
                {"status": status, "updatedAt": now, "completedAt": now, "lastError": error},
            )
            transaction.update(decision_ref, {"deliveryStatus": status})

        mark_in_transaction(transaction, delivery_ref, decision_ref)

    def complete(self, activity_id: str, uid: str) -> None:
        now = self._as_utc(self._clock())
        self._document(activity_id, uid).update(
            {"status": "completed", "completedAt": now, "updatedAt": now, "lastError": None}
        )

    def mark_terminal(self, activity_id: str, uid: str, error_class: str) -> None:
        now = self._as_utc(self._clock())
        self._document(activity_id, uid).update(
            {"status": "terminal", "completedAt": now, "updatedAt": now, "lastError": error_class}
        )

    def release_for_retry(self, activity_id: str, uid: str, error_class: str) -> None:
        now = self._as_utc(self._clock())
        self._document(activity_id, uid).update(
            {"status": "retryable", "updatedAt": now, "lastError": error_class}
        )

    def claim_effect(self, activity_id: str, uid: str, effect: str) -> bool:
        """Compatibility helper for non-delivery callers; durable sends use claim_delivery."""
        doc_ref = self._document(activity_id, uid)
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
