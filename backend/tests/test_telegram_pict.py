from __future__ import annotations

import asyncio
import re
import sys
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from app.models.telegram import LinkCodeResponse
from app.services.telegram_service import TelegramService
from telegrambot.handlers import process_telegram_update
from tests.fakes import FakeFirestore


def test_generate_link_code_has_six_chars_and_ten_minute_ttl():
    db = FakeFirestore()
    service = TelegramService(db)
    before = datetime.now(timezone.utc)

    code = service.generate_link_code("user-1")
    saved = db.collection("telegram_link_codes").document(code).get().to_dict()

    assert re.fullmatch(r"[A-Z0-9]{6}", code)
    assert saved["uid"] == "user-1"
    assert before + timedelta(minutes=9, seconds=59) <= saved["expiresAt"] <= before + timedelta(minutes=10, seconds=1)


def test_valid_code_links_account_and_cannot_be_reused():
    db = FakeFirestore()
    db.collection("users").document("user-1").set({"telegramUserId": None})
    service = TelegramService(db)
    code = service.generate_link_code("user-1")

    assert service.validate_and_link(code.lower(), 123456, "alexdev") is True
    user = db.collection("users").document("user-1").get().to_dict()
    assert user["telegramUserId"] == 123456
    assert user["telegramUsername"] == "alexdev"
    assert service.validate_and_link(code, 999999) is False


@pytest.mark.parametrize("code", ["INVALID", "", "ABC123"])
def test_invalid_or_missing_code_is_rejected(code):
    assert TelegramService(FakeFirestore()).validate_and_link(code, 123456) is False


def test_expired_code_is_rejected_and_deleted():
    db = FakeFirestore()
    db.collection("telegram_link_codes").document("OLD123").set(
        {"uid": "user-1", "expiresAt": datetime.now(timezone.utc) - timedelta(seconds=1)}
    )
    service = TelegramService(db)

    assert service.validate_and_link("OLD123", 123456) is False
    assert db.collection("telegram_link_codes").document("OLD123").get().exists is False


def test_start_command_sends_link_instructions(monkeypatch):
    send = AsyncMock(return_value=True)
    monkeypatch.setattr(TelegramService, "send_message", send)

    asyncio.run(
        process_telegram_update(
            {"message": {"chat": {"id": 123}, "from": {"username": "alex"}, "text": "/start"}},
            FakeFirestore(),
        )
    )

    assert send.await_count == 1
    assert "/link CODE" in send.await_args.args[1]


def test_link_without_code_returns_usage(monkeypatch):
    send = AsyncMock(return_value=True)
    monkeypatch.setattr(TelegramService, "send_message", send)

    asyncio.run(
        process_telegram_update(
            {"message": {"chat": {"id": 123}, "from": {"username": "alex"}, "text": "/link"}},
            FakeFirestore(),
        )
    )

    assert send.await_count == 1
    assert "Usage" in send.await_args.args[1]


def test_free_text_from_unlinked_account_returns_link_prompt(monkeypatch):
    send = AsyncMock(return_value=True)
    monkeypatch.setattr(TelegramService, "send_message", send)

    asyncio.run(
        process_telegram_update(
            {"message": {"chat": {"id": 123}, "text": "Hello"}},
            FakeFirestore(),
        )
    )

    assert send.await_count == 1
    assert "not linked" in send.await_args.args[1]


def test_free_text_from_linked_account_uses_unified_chat(monkeypatch):
    db = FakeFirestore()
    db.collection("users").document("user-1").set({"telegramUserId": 123})
    send = AsyncMock(return_value=True)
    monkeypatch.setattr(TelegramService, "send_message", send)

    calls = []

    class FakeChatService:
        def __init__(self, received_db):
            assert received_db is db

        async def process_message(self, uid, text, channel):
            calls.append((uid, text, channel))
            return "Привет!"

    fake_module = types.ModuleType("app.services.chat_service")
    fake_module.ChatService = FakeChatService
    monkeypatch.setitem(sys.modules, "app.services.chat_service", fake_module)

    asyncio.run(
        process_telegram_update(
            {"message": {"chat": {"id": 123}, "text": "Помоги с Python"}},
            db,
        )
    )

    assert calls == [("user-1", "Помоги с Python", "telegram")]
    assert send.await_args.args == (123, "Привет!")


@pytest.mark.xfail(strict=True, reason="Firestore schema requires telegramChatId, but validate_and_link never writes it.")
def test_linking_persists_telegram_chat_id():
    db = FakeFirestore()
    db.collection("users").document("user-1").set({})
    service = TelegramService(db)
    code = service.generate_link_code("user-1")
    service.validate_and_link(code, 123456, "alex")
    user = db.collection("users").document("user-1").get().to_dict()
    assert user["telegramChatId"] == 123456


@pytest.mark.xfail(strict=True, reason="OpenAPI requires linkCode/expiresAt/botUsername; the model exposes only code.")
def test_link_response_matches_openapi_contract():
    fields = set(LinkCodeResponse.model_fields)
    assert fields == {"linkCode", "expiresAt", "botUsername"}


@pytest.mark.xfail(strict=True, reason="The implementation uses DELETE /telegram/link; OpenAPI specifies /telegram/unlink.")
def test_unlink_route_matches_openapi_contract():
    router_source = Path(__file__).parents[1].joinpath("app/api/v1/telegram.py").read_text()
    assert '@router.delete("/telegram/unlink"' in router_source

