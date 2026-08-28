from __future__ import annotations

import asyncio

import pytest

import app.config as config_module

# Temporary test seam: the missing production accessor has its own strict xfail regression.
config_module.get_settings = lambda: config_module.settings

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

    response = asyncio.run(chat_module.ChatService(db).process_message("user-1", "How am I doing?", "web"))

    assert response == "Tailored answer"
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

    response = asyncio.run(chat_module.ChatService(db).process_message("user-1", "Помоги с Python", "telegram"))

    assert response.startswith("Конечно")
    assert RecordingAgent.calls[0]["message"] == "Помоги с Python"
    messages = db.collection("users").document("user-1").collection("messages").get()
    assert all(message.to_dict()["channel"] == "telegram" for message in messages)


def test_sequential_messages_reuse_shared_history(monkeypatch):
    db = FakeFirestore()
    create_user(db)
    RecordingAgent.calls = []
    RecordingAgent.response = "First answer"
    monkeypatch.setattr(chat_module, "ChatAgent", RecordingAgent)
    service = chat_module.ChatService(db)

    asyncio.run(service.process_message("user-1", "First question", "telegram"))
    RecordingAgent.response = "Second answer"
    asyncio.run(service.process_message("user-1", "Follow up", "web"))

    second_history = RecordingAgent.calls[1]["history"]
    assert [item["text"] for item in second_history] == ["First question", "First answer"]
    assert [item["role"] for item in second_history] == ["user", "agent"]


def test_missing_profile_returns_safe_error_without_calling_agent(monkeypatch):
    db = FakeFirestore()
    RecordingAgent.calls = []
    monkeypatch.setattr(chat_module, "ChatAgent", RecordingAgent)

    response = asyncio.run(chat_module.ChatService(db).process_message("missing", "Hello", "web"))

    assert response == "Error: User profile not found."
    assert RecordingAgent.calls == []


def test_agent_failure_fallback_is_stored(monkeypatch):
    db = FakeFirestore()
    create_user(db)
    RecordingAgent.calls = []
    RecordingAgent.response = "I'm having trouble processing that right now. Please try again later."
    monkeypatch.setattr(chat_module, "ChatAgent", RecordingAgent)

    response = asyncio.run(chat_module.ChatService(db).process_message("user-1", "Review my code", "web"))

    assert "trouble processing" in response
    saved = db.collection("users").document("user-1").collection("messages").get()
    assert saved[-1].to_dict()["text"] == response

