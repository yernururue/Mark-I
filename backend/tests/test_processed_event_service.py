from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import asyncio

from app.models.github import GitHubEventEnvelope
from app.services.decision_service import DecisionService
from app.services.observation_service import ObservationService
from app.services.processed_event_service import EventClaimStatus, ProcessedEventService
from app.services.skill_service import SkillService
from tests.fakes import FakeFirestore
from workers.github_worker import process_message_async


def test_claim_creates_deterministic_processing_record_and_completes():
    now = datetime(2026, 8, 29, tzinfo=timezone.utc)
    db = FakeFirestore()
    service = ProcessedEventService(db, clock=lambda: now, transactional_runner=lambda function: function)

    assert service.claim("delivery-1", "user-1") is EventClaimStatus.ACQUIRED
    record = db.collection("processed_events").document("github:delivery-1:user-1").get().to_dict()
    assert record == {
        "source": "github",
        "deliveryId": "delivery-1",
        "userId": "user-1",
        "status": "processing",
        "attempt": 1,
        "startedAt": now,
        "updatedAt": now,
        "completedAt": None,
        "lastError": None,
    }

    service.complete("delivery-1", "user-1")

    assert service.claim("delivery-1", "user-1") is EventClaimStatus.COMPLETED


def test_live_claim_is_busy_then_expired_lease_can_be_reclaimed():
    clock_value = datetime(2026, 8, 29, tzinfo=timezone.utc)
    db = FakeFirestore()
    service = ProcessedEventService(
        db,
        clock=lambda: clock_value,
        lease=timedelta(minutes=5),
        transactional_runner=lambda function: function,
    )
    assert service.claim("delivery-1", "user-1") is EventClaimStatus.ACQUIRED
    assert service.claim("delivery-1", "user-1") is EventClaimStatus.BUSY

    clock_value += timedelta(minutes=6)

    assert service.claim("delivery-1", "user-1") is EventClaimStatus.ACQUIRED
    assert db.collection("processed_events").document("github:delivery-1:user-1").get().to_dict()["attempt"] == 2


def test_retryable_release_is_claimed_again_with_error_class_only():
    now = datetime(2026, 8, 29, tzinfo=timezone.utc)
    db = FakeFirestore()
    service = ProcessedEventService(db, clock=lambda: now, transactional_runner=lambda function: function)
    service.claim("delivery-1", "user-1")

    service.release_for_retry("delivery-1", "user-1", "TimeoutError")

    assert service.claim("delivery-1", "user-1") is EventClaimStatus.ACQUIRED
    record = db.collection("processed_events").document("github:delivery-1:user-1").get().to_dict()
    assert record["attempt"] == 2
    assert record["lastError"] is None


def test_external_effect_is_claimed_only_once():
    db = FakeFirestore()
    service = ProcessedEventService(db, transactional_runner=lambda function: function)
    service.claim("delivery-1", "user-1")

    assert service.claim_effect("delivery-1", "user-1", "telegramNotification") is True
    assert service.claim_effect("delivery-1", "user-1", "telegramNotification") is False


def test_skill_effect_is_idempotent_for_a_processed_event():
    db = FakeFirestore()
    db.collection("users").document("user-1").set({"skills": {"testing": 5.0}})
    events = ProcessedEventService(db, transactional_runner=lambda function: function)
    events.claim("delivery-1", "user-1")
    skills = SkillService(db, transactional_runner=lambda function: function)
    event_id = events.document_id("delivery-1", "user-1")

    assert skills.update_skill("user-1", "testing", 7.0, processed_event_id=event_id) == 5.6
    assert skills.update_skill("user-1", "testing", 7.0, processed_event_id=event_id) == 5.6
    assert db.collection("users").document("user-1").get().to_dict()["skills"]["testing"] == 5.6


class DummyMessage:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.acks = 0
        self.nacks = 0

    def ack(self) -> None:
        self.acks += 1

    def nack(self) -> None:
        self.nacks += 1


def test_completed_delivery_acknowledges_duplicate_without_repeating_business_effects(monkeypatch):
    db = FakeFirestore()
    db.collection("users").document("user-1").set(
        {"skills": {}, "intensity": "normal", "telegramUserId": 123}
    )
    telegram = SimpleNamespace(send_message=AsyncMock())
    context = SimpleNamespace(
        db=db,
        observation_service=ObservationService(db),
        skill_service=SkillService(db, transactional_runner=lambda function: function),
        decision_service=DecisionService(db),
        telegram_service=telegram,
        processed_event_service=ProcessedEventService(db, transactional_runner=lambda function: function),
    )

    async def analyzer(**kwargs):
        return SimpleNamespace(
            summary="Good testing work",
            concept="testing",
            sentiment="positive",
            proficiencyAssessment=7.0,
            significanceScore=8,
        )

    monkeypatch.setattr("ai.analyzers.github_analyzer.analyze_github_event", analyzer)
    envelope = GitHubEventEnvelope(
        deliveryId="delivery-1",
        eventType="push",
        uid="user-1",
        repoFullName="alex/repo",
        payload={"repository": {"full_name": "alex/repo"}, "commits": []},
    )

    first = DummyMessage(envelope.model_dump_json().encode())
    second = DummyMessage(envelope.model_dump_json().encode())
    asyncio.run(process_message_async(first, context))
    asyncio.run(process_message_async(second, context))

    assert (first.acks, first.nacks, second.acks, second.nacks) == (1, 0, 1, 0)
    assert len(db.collection("users").document("user-1").collection("observations").get()) == 1
    assert len(db.collection("users").document("user-1").collection("decisions").get()) == 1
    assert db.collection("users").document("user-1").get().to_dict()["skills"]["testing"] == 7.0
    assert telegram.send_message.await_count == 1
