from __future__ import annotations

import asyncio

import pytest

from ai.chat_agent import ChatToolLoopLimitError
from app.errors import ExternalServiceError
from app.models.user import CreateProfileRequest  # noqa: E402
from app.services import chat_service as chat_module  # noqa: E402
from app.services.user_service import UserService  # noqa: E402
from tests.fakes import FakeFirestore  # noqa: E402


class RecordingAgent:
    calls = []
    response = "Agent response"

    def __init__(self, db, uid, system_instruction):
        self.db = db
        self.uid = uid
        self.system_instruction = system_instruction

    async def generate_response(self, history, message):
        self.__class__.calls.append(
            {
                "uid": self.uid,
                "instruction": self.system_instruction,
                "history": history,
                "message": message,
            }
        )
        return self.__class__.response


def create_user(db, intensity="normal", goal="Learn Python"):
    UserService(db).create_profile(
        "user-1",
        "alex@example.com",
        CreateProfileRequest(
            displayName="Alex",
            goal=goal,
            intensity=intensity,
            language="en",
        ),
    )


def chat_service(db):
    return chat_module.ChatService(db, transactional_runner=lambda function: function)


@pytest.mark.parametrize(
    ("intensity", "tone_fragment"),
    [
        ("chill", "supportive, gentle"),
        ("normal", "balanced, informative"),
        ("brutal", "direct, strict"),
    ],
)
def test_chat_persona_matches_intensity(monkeypatch, intensity, tone_fragment):
    db = FakeFirestore()
    create_user(db, intensity=intensity)
    RecordingAgent.calls = []
    RecordingAgent.response = "Tailored answer"
    monkeypatch.setattr(chat_module, "ChatAgent", RecordingAgent)

    response = asyncio.run(chat_service(db).process_message("user-1", "How am I doing?", "web"))

    assert response.response == "Tailored answer"
    assert response.messageId != response.agentMessageId
    assert tone_fragment in RecordingAgent.calls[0]["instruction"]
    messages = db.collection("users").document("user-1").collection("messages").get()
    assert [message.to_dict()["role"] for message in messages] == ["user", "agent"]
    assert all(message.to_dict()["channel"] == "web" for message in messages)


def test_russian_message_and_response_keep_telegram_channel(monkeypatch):
    db = FakeFirestore()
    create_user(db)
    RecordingAgent.calls = []
    RecordingAgent.response = "Конечно, давай разберём Python."
    monkeypatch.setattr(chat_module, "ChatAgent", RecordingAgent)

    response = asyncio.run(chat_service(db).process_message("user-1", "Помоги с Python", "telegram"))

    assert response.response.startswith("Конечно")
    assert RecordingAgent.calls[0]["message"] == "Помоги с Python"
    messages = db.collection("users").document("user-1").collection("messages").get()
    assert all(message.to_dict()["channel"] == "telegram" for message in messages)


def test_sequential_messages_reuse_shared_history(monkeypatch):
    db = FakeFirestore()
    create_user(db)
    RecordingAgent.calls = []
    RecordingAgent.response = "First answer"
    monkeypatch.setattr(chat_module, "ChatAgent", RecordingAgent)
    service = chat_service(db)

    asyncio.run(service.process_message("user-1", "First question", "telegram"))
    RecordingAgent.response = "Second answer"
    asyncio.run(service.process_message("user-1", "Follow up", "web"))

    second_history = RecordingAgent.calls[1]["history"]
    assert [item["text"] for item in second_history] == ["First question", "First answer"]
    assert [item["role"] for item in second_history] == ["user", "agent"]


def test_missing_profile_raises_not_found_without_calling_agent(monkeypatch):
    db = FakeFirestore()
    RecordingAgent.calls = []
    monkeypatch.setattr(chat_module, "ChatAgent", RecordingAgent)

    from app.errors import NotFoundError
    with pytest.raises(NotFoundError):
        asyncio.run(chat_service(db).process_message("missing", "Hello", "web"))
    assert RecordingAgent.calls == []


def test_agent_failure_fallback_is_stored(monkeypatch):
    db = FakeFirestore()
    create_user(db)
    RecordingAgent.calls = []
    RecordingAgent.response = "I'm having trouble processing that right now. Please try again later."
    monkeypatch.setattr(chat_module, "ChatAgent", RecordingAgent)

    response = asyncio.run(chat_service(db).process_message("user-1", "Review my code", "web"))

    assert "trouble processing" in response.response
    saved = db.collection("users").document("user-1").collection("messages").get()
    assert saved[-1].to_dict()["text"] == response.response


def test_completed_turn_id_replays_stored_response_without_a_second_agent_call(monkeypatch):
    db = FakeFirestore()
    create_user(db)
    RecordingAgent.calls = []
    RecordingAgent.response = "Idempotent answer"
    monkeypatch.setattr(chat_module, "ChatAgent", RecordingAgent)
    service = chat_service(db)

    first = asyncio.run(service.process_message("user-1", "Question", "web", turn_id="web:turn-1"))
    second = asyncio.run(service.process_message("user-1", "Question", "web", turn_id="web:turn-1"))

    assert first == second
    assert len(RecordingAgent.calls) == 1
    assert len(db.collection("users").document("user-1").collection("messages").get()) == 2


def test_cross_channel_turns_are_serialized_before_agent_history_is_built():
    db = FakeFirestore()
    create_user(db)

    async def scenario():
        started = asyncio.Event()
        release = asyncio.Event()
        calls = []

        class BlockingAgent:
            def __init__(self, **_):
                pass

            async def generate_response(self, history, message):
                calls.append((history, message))
                started.set()
                await release.wait()
                return f"answer:{message}"

        service = chat_module.ChatService(
            db,
            agent_factory=BlockingAgent,
            transactional_runner=lambda function: function,
        )
        first = asyncio.create_task(service.process_message("user-1", "from web", "web", turn_id="web:1"))
        await started.wait()
        with pytest.raises(chat_module.ChatTurnConflictError):
            await service.process_message("user-1", "from telegram", "telegram", turn_id="telegram:2")
        release.set()
        await first
        second = await service.process_message("user-1", "from telegram", "telegram", turn_id="telegram:2")
        return calls, second

    calls, second = asyncio.run(scenario())
    assert [message for _, message in calls] == ["from web", "from telegram"]
    assert [item["text"] for item in calls[1][0]] == ["from web", "answer:from web"]
    assert second.response == "answer:from telegram"


def test_tool_loop_limit_marks_turn_terminal_without_reinvoking_the_agent():
    db = FakeFirestore()
    create_user(db)
    calls = 0

    class LoopingAgent:
        def __init__(self, **_):
            pass

        async def generate_response(self, history, message):
            nonlocal calls
            calls += 1
            raise ChatToolLoopLimitError("limit")

    service = chat_module.ChatService(
        db,
        agent_factory=LoopingAgent,
        transactional_runner=lambda function: function,
    )
    with pytest.raises(ExternalServiceError):
        asyncio.run(service.process_message("user-1", "Question", "web", turn_id="web:loop"))
    with pytest.raises(chat_module.ChatTurnFailedError):
        asyncio.run(service.process_message("user-1", "Question", "web", turn_id="web:loop"))
    turn = db.collection("users").document("user-1").collection("chat_turns").get()[0].to_dict()
    assert (calls, turn["status"], turn["terminalError"]) == (1, "failed", "tool-loop-limit")
