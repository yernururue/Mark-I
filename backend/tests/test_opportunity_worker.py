from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

from app.services.opportunity_effect_service import OpportunityEffectService
from app.services.processed_event_service import ProcessedEventService
from app.services.telegram_service import TelegramSendResult
from tests.fakes import FakeFirestore
from workers.opportunity_worker import process_message_async, process_opportunity_for_user


class StaticAnalyzer:
    def __init__(self, result: dict | Exception):
        self._result = result
        self.calls = 0

    def analyze_opportunity(self, opportunity, goal, skills):
        del opportunity, goal, skills
        self.calls += 1
        if isinstance(self._result, Exception):
            raise self._result
        return dict(self._result)


class RecordingTelegram:
    def __init__(self) -> None:
        self.calls: list[tuple[int, str, str | None]] = []

    async def send_message_result(self, chat_id: int, text: str, parse_mode: str | None = None):
        self.calls.append((chat_id, text, parse_mode))
        return TelegramSendResult(delivered=True)


class FakePubSubMessage:
    def __init__(self, data: dict) -> None:
        self.data = json.dumps(data).encode()
        self.acked = False
        self.nacked = False

    def ack(self) -> None:
        self.acked = True

    def nack(self) -> None:
        self.nacked = True


def make_context(db: FakeFirestore, analysis: dict | Exception):
    return SimpleNamespace(
        db=db,
        opportunity_analyzer=StaticAnalyzer(analysis),
        effect_service=OpportunityEffectService(db, transactional_runner=lambda function: function),
        delivery_service=ProcessedEventService(db, transactional_runner=lambda function: function),
        telegram_service=RecordingTelegram(),
    )


def _opportunity(event_id: str = "devto-42") -> dict:
    return {
        "eventId": event_id,
        "title": "Reliable FastAPI Background Jobs",
        "sourceName": "Dev.to",
        "sourceUrl": "https://dev.to/example",
    }


def test_linked_and_unlinked_users_get_one_business_effect_but_only_linked_user_is_notified():
    db = FakeFirestore()
    linked = {"goal": "Build reliable services", "intensity": "normal", "skills": {}, "telegramChatId": -10042}
    unlinked = {"goal": "Build reliable services", "intensity": "normal", "skills": {}}
    db.collection("users").document("linked").set(linked)
    db.collection("users").document("unlinked").set(unlinked)
    context = make_context(db, {"relevance_score": 8, "concept": "fastapi", "reasoning": "Matches the goal."})

    async def deliver_twice() -> None:
        for _ in range(2):
            await process_opportunity_for_user("linked", linked, _opportunity(), context)
            await process_opportunity_for_user("unlinked", unlinked, _opportunity(), context)

    asyncio.run(deliver_twice())

    assert context.opportunity_analyzer.calls == 2
    assert len(context.telegram_service.calls) == 1
    assert context.telegram_service.calls[0][0] == -10042
    for uid, expected_delivery in (("linked", "sent"), ("unlinked", "suppressed")):
        observations = list(db.collection("users").document(uid).collection("observations").stream())
        decisions = list(db.collection("users").document(uid).collection("decisions").stream())
        assert len(observations) == len(decisions) == 1
        assert decisions[0].to_dict()["deliveryStatus"] == expected_delivery


def test_below_threshold_is_durably_ignored_once_without_a_decision_or_notification():
    db = FakeFirestore()
    context = make_context(db, {"relevance_score": 6, "concept": "fastapi", "reasoning": "Not enough relevance."})
    user = {"goal": "Build reliable services", "intensity": "normal", "skills": {}, "telegramChatId": 99}
    db.collection("users").document("user-1").set(user)

    asyncio.run(process_opportunity_for_user("user-1", user, _opportunity(), context))
    asyncio.run(process_opportunity_for_user("user-1", user, _opportunity(), context))

    assert context.opportunity_analyzer.calls == 1
    assert context.telegram_service.calls == []
    assert list(db.collection("users").document("user-1").collection("observations").stream()) == []
    assert list(db.collection("users").document("user-1").collection("decisions").stream()) == []


def test_retryable_user_processing_failure_nacks_the_pubsub_message_without_recording_an_ignore():
    db = FakeFirestore()
    db.collection("users").document("user-1").set({"goal": "Build reliable services", "skills": {}})
    context = make_context(db, TimeoutError("provider timeout"))
    message = FakePubSubMessage(_opportunity())

    asyncio.run(process_message_async(message, context))

    assert message.nacked and not message.acked
    assert list(db.collection("opportunity_effects").stream()) == []
