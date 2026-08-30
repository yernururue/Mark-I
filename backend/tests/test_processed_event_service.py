from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import asyncio

from app.models.github import GitHubEventEnvelope
from app.services.decision_service import DecisionService
from app.services.observation_service import ObservationService
from app.services.processed_event_service import DeliveryClaimStatus, EventClaimStatus, ProcessedEventService
from app.services.github_evidence_service import GitHubEvidence
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
        "activityId": "delivery-1",
        "deliveryIds": ["delivery-1"],
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


def worker_context(db: FakeFirestore) -> SimpleNamespace:
    return SimpleNamespace(
        db=db,
        observation_service=ObservationService(db),
        skill_service=SkillService(db, transactional_runner=lambda function: function),
        decision_service=DecisionService(db),
        telegram_service=SimpleNamespace(send_message=AsyncMock()),
        processed_event_service=ProcessedEventService(db, transactional_runner=lambda function: function),
        evidence_service=SimpleNamespace(
            collect=AsyncMock(
                return_value=GitHubEvidence(
                    text="File: tests/test_retry.py\n+def test_retry(): pass",
                    supports_proficiency=True,
                    file_count=1,
                    truncated=False,
                )
            )
        ),
    )


def worker_envelope() -> GitHubEventEnvelope:
    return GitHubEventEnvelope(
        deliveryId="delivery-1",
        activityId="github:activity-1",
        eventType="push",
        uid="user-1",
        repoFullName="alex/repo",
        actorLogin="alex",
        actorId=42,
        payload={
            "repository": {"full_name": "alex/repo"},
            "before": "parent-sha",
            "after": "commit-sha",
            "commits": [],
        },
    )


def test_completed_delivery_acknowledges_duplicate_without_repeating_business_effects(monkeypatch):
    db = FakeFirestore()
    db.collection("users").document("user-1").set(
        {"skills": {}, "intensity": "normal", "telegramUserId": 123, "telegramChatId": -100}
    )
    context = worker_context(db)

    async def analyzer(**kwargs):
        return SimpleNamespace(
            summary="Good testing work",
            concept="testing",
            sentiment="positive",
            proficiencyAssessment=7.0,
            significanceScore=8,
        )

    monkeypatch.setattr("ai.analyzers.github_analyzer.analyze_github_event", analyzer)
    envelope = worker_envelope()

    first = DummyMessage(envelope.model_dump_json().encode())
    second = DummyMessage(envelope.model_dump_json().encode())
    asyncio.run(process_message_async(first, context))
    asyncio.run(process_message_async(second, context))

    assert (first.acks, first.nacks, second.acks, second.nacks) == (1, 0, 1, 0)
    assert len(db.collection("users").document("user-1").collection("observations").get()) == 1
    assert len(db.collection("users").document("user-1").collection("decisions").get()) == 1
    assert db.collection("users").document("user-1").get().to_dict()["skills"]["testing"] == 7.0
    assert context.telegram_service.send_message.await_count == 1
    assert context.telegram_service.send_message.await_args.args[0] == -100
    decision = db.collection("users").document("user-1").collection("decisions").get()[0].to_dict()
    assert decision["deliveryStatus"] == "sent"


def test_invalid_envelope_is_terminally_acknowledged_without_a_claim():
    message = DummyMessage(b'{"schemaVersion": 1}')

    asyncio.run(process_message_async(message, SimpleNamespace()))

    assert (message.acks, message.nacks) == (1, 0)


def test_retryable_analyzer_error_releases_claim_and_nacks(monkeypatch):
    db = FakeFirestore()
    db.collection("users").document("user-1").set({"skills": {}, "intensity": "normal"})
    context = worker_context(db)

    async def unavailable(**kwargs):
        raise TimeoutError("Gemini timed out")

    monkeypatch.setattr("ai.analyzers.github_analyzer.analyze_github_event", unavailable)
    message = DummyMessage(worker_envelope().model_dump_json().encode())

    asyncio.run(process_message_async(message, context))

    record = db.collection("processed_events").document("github:activity-1:user-1").get().to_dict()
    assert (message.acks, message.nacks) == (0, 1)
    assert record["status"] == "retryable"
    assert record["lastError"] == "TimeoutError"


def test_terminal_analyzer_error_completes_claim_and_acks(monkeypatch):
    from ai.analyzers.github_analyzer import GitHubAnalysisTerminalError

    db = FakeFirestore()
    db.collection("users").document("user-1").set({"skills": {}, "intensity": "normal"})
    context = worker_context(db)

    async def invalid_output(**kwargs):
        raise GitHubAnalysisTerminalError("invalid JSON")

    monkeypatch.setattr("ai.analyzers.github_analyzer.analyze_github_event", invalid_output)
    message = DummyMessage(worker_envelope().model_dump_json().encode())

    asyncio.run(process_message_async(message, context))

    record = db.collection("processed_events").document("github:activity-1:user-1").get().to_dict()
    assert (message.acks, message.nacks) == (1, 0)
    assert record["status"] == "terminal"
    assert db.collection("users").document("user-1").collection("observations").get() == []
    assert db.collection("users").document("user-1").collection("decisions").get() == []
    assert db.collection("users").document("user-1").get().to_dict()["skills"] == {}


def test_non_code_event_creates_observation_without_mutating_proficiency(monkeypatch):
    db = FakeFirestore()
    db.collection("users").document("user-1").set(
        {"skills": {"communication": 6.0}, "intensity": "normal"}
    )
    context = worker_context(db)
    context.evidence_service.collect = AsyncMock(
        return_value=GitHubEvidence(
            text="",
            supports_proficiency=False,
            file_count=0,
            truncated=False,
            omission_reason="event_has_no_code_evidence",
        )
    )

    async def analyzer(**kwargs):
        return SimpleNamespace(
            summary="A useful issue discussion",
            concept="communication",
            sentiment="positive",
            proficiencyAssessment=10.0,
            significanceScore=6,
        )

    monkeypatch.setattr("ai.analyzers.github_analyzer.analyze_github_event", analyzer)
    envelope = GitHubEventEnvelope(
        deliveryId="delivery-issue",
        activityId="github:issue-1",
        eventType="issues",
        eventAction="opened",
        uid="user-1",
        repoFullName="alex/repo",
        actorLogin="alex",
        actorId=42,
        payload={
            "action": "opened",
            "issue": {"id": 1, "title": "Race condition", "body": "Investigate ordering"},
        },
    )
    message = DummyMessage(envelope.model_dump_json().encode())

    asyncio.run(process_message_async(message, context))

    assert (message.acks, message.nacks) == (1, 0)
    assert db.collection("users").document("user-1").get().to_dict()["skills"] == {
        "communication": 6.0
    }
    observations = db.collection("users").document("user-1").collection("observations").get()
    assert len(observations) == 1
    assert observations[0].to_dict()["metadata"]["codeEvidence"]["supportsProficiency"] is False


def test_retry_after_definite_telegram_failure_reuses_immutable_analysis_and_business_effects(monkeypatch):
    db = FakeFirestore()
    db.collection("users").document("user-1").set(
        {"skills": {}, "intensity": "normal", "telegramChatId": -100}
    )
    context = worker_context(db)
    context.telegram_service.send_message = AsyncMock(side_effect=[False, True])
    calls = 0

    async def analyzer(**kwargs):
        nonlocal calls
        calls += 1
        return {
            "summary": "A new test suite",
            "concept": "testing",
            "sentiment": "positive",
            "proficiencyAssessment": 8.0,
            "significanceScore": 8,
        }

    monkeypatch.setattr("ai.analyzers.github_analyzer.analyze_github_event", analyzer)
    envelope = worker_envelope()
    first = DummyMessage(envelope.model_dump_json().encode())
    second = DummyMessage(envelope.model_dump_json().encode())

    asyncio.run(process_message_async(first, context))
    asyncio.run(process_message_async(second, context))

    assert (first.acks, first.nacks, second.acks, second.nacks) == (0, 1, 1, 0)
    assert calls == 1
    assert context.evidence_service.collect.await_count == 1
    assert len(db.collection("users").document("user-1").collection("observations").get()) == 1
    assert len(db.collection("users").document("user-1").collection("decisions").get()) == 1
    assert db.collection("users").document("user-1").get().to_dict()["skills"] == {"testing": 8.0}
    decision = db.collection("users").document("user-1").collection("decisions").get()[0].to_dict()
    assert decision["deliveryStatus"] == "sent"
    record = db.collection("processed_events").document("github:activity-1:user-1").get().to_dict()
    assert record["status"] == "completed"
    assert record["prepared"]["analysis"]["concept"] == "testing"


def test_expired_sending_lease_becomes_unknown_without_automatic_duplicate_send():
    now = datetime(2026, 8, 29, tzinfo=timezone.utc)
    db = FakeFirestore()
    db.collection("users").document("user-1").set(
        {"skills": {}, "intensity": "normal", "telegramChatId": -100}
    )
    service = ProcessedEventService(
        db,
        clock=lambda: now,
        lease=timedelta(minutes=5),
        transactional_runner=lambda function: function,
    )
    activity_id = "github:activity-lease"
    assert service.claim(activity_id, "user-1", delivery_id="delivery-1") is EventClaimStatus.ACQUIRED
    service.prepare(
        activity_id,
        "user-1",
        analysis={
            "summary": "A notable patch",
            "concept": "testing",
            "sentiment": "positive",
            "proficiencyAssessment": 8.0,
            "significanceScore": 8,
        },
        event_context={"metadata": {}},
        evidence={"supportsProficiency": True, "fileCount": 1, "truncated": False, "omissionReason": None},
    )
    effects = service.apply_business_effects(activity_id, "user-1")
    assert effects.delivery_id is not None
    assert service.claim_delivery(effects.delivery_id, "user-1", effects.decision_id) is DeliveryClaimStatus.ACQUIRED

    now += timedelta(minutes=6)

    assert service.claim_delivery(effects.delivery_id, "user-1", effects.decision_id) is DeliveryClaimStatus.UNKNOWN
    delivery = db.collection("delivery_effects").document(effects.delivery_id).get().to_dict()
    decision = db.collection("users").document("user-1").collection("decisions").document(effects.decision_id).get().to_dict()
    assert delivery["status"] == "unknown"
    assert decision["deliveryStatus"] == "unknown"


def test_different_physical_deliveries_are_recorded_against_one_logical_activity():
    db = FakeFirestore()
    service = ProcessedEventService(db, transactional_runner=lambda function: function)

    assert service.claim("github:activity-1", "user-1", delivery_id="delivery-a") is EventClaimStatus.ACQUIRED
    service.complete("github:activity-1", "user-1")
    assert service.claim("github:activity-1", "user-1", delivery_id="delivery-b") is EventClaimStatus.COMPLETED

    record = db.collection("processed_events").document("github:activity-1:user-1").get().to_dict()
    assert record["deliveryIds"] == ["delivery-a", "delivery-b"]
