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


def telegram_service(db: FakeFirestore) -> TelegramService:
    return TelegramService(db, transactional_runner=lambda function: function)


def test_generate_link_code_has_six_chars_and_ten_minute_ttl():
    db = FakeFirestore()
    service = telegram_service(db)
    before = datetime.now(timezone.utc)

    link = service.generate_link_code("user-1")
    saved = service._code_ref(link.code).get().to_dict()

    assert re.fullmatch(r"[A-Z0-9]{6}", link.code)
    assert saved["uid"] == "user-1"
    assert before + timedelta(minutes=9, seconds=59) <= saved["expiresAt"] <= before + timedelta(minutes=10, seconds=1)


def test_valid_code_links_account_and_cannot_be_reused():
    db = FakeFirestore()
    db.collection("users").document("user-1").set({"telegramUserId": None})
    service = telegram_service(db)
    code = service.generate_link_code("user-1").code

    assert service.validate_and_link(code.lower(), 123456, "alexdev") is True
    user = db.collection("users").document("user-1").get().to_dict()
    assert user["telegramUserId"] == 123456
    assert user["telegramUsername"] == "alexdev"
    assert service.validate_and_link(code, 999999) is False


@pytest.mark.parametrize("code", ["INVALID", "", "ABC123"])
def test_invalid_or_missing_code_is_rejected(code):
    assert telegram_service(FakeFirestore()).validate_and_link(code, 123456) is False


def test_expired_code_is_rejected_and_deleted():
    db = FakeFirestore()
    service = telegram_service(db)
    service._code_ref("OLD123").set(
        {"uid": "user-1", "expiresAt": datetime.now(timezone.utc) - timedelta(seconds=1)}
    )

    assert service.validate_and_link("OLD123", 123456) is False
    assert service._code_ref("OLD123").get().exists is False


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
                {"message": {"chat": {"id": 123}, "from": {"id": 123}, "text": "Hello"}},
            FakeFirestore(),
        )
    )

    assert send.await_count == 1
    assert "not linked" in send.await_args.args[1]


def test_free_text_from_linked_account_uses_unified_chat(monkeypatch):
    db = FakeFirestore()
    db.collection("users").document("user-1").set({"telegramUserId": 123})
    db.collection("telegram_identities").document("123").set({"uid": "user-1"})
    send = AsyncMock(return_value=True)
    monkeypatch.setattr(TelegramService, "send_message", send)

    calls = []

    class FakeChatService:
        def __init__(self, received_db):
            assert received_db is db

        async def process_message(self, uid, text, channel, turn_id=None):
            assert turn_id is None
            calls.append((uid, text, channel))
            return "Привет!"

    fake_module = types.ModuleType("app.services.chat_service")
    fake_module.ChatService = FakeChatService
    monkeypatch.setitem(sys.modules, "app.services.chat_service", fake_module)

    asyncio.run(
            process_telegram_update(
                {"message": {"chat": {"id": 123}, "from": {"id": 123}, "text": "Помоги с Python"}},
            db,
        )
    )

    assert calls == [("user-1", "Помоги с Python", "telegram")]
    assert send.await_args.args == (123, "Привет!")


def test_linking_persists_telegram_chat_id():
    db = FakeFirestore()
    db.collection("users").document("user-1").set({})
    service = telegram_service(db)
    code = service.generate_link_code("user-1").code
    service.validate_and_link(code, 123456, "alex")
    user = db.collection("users").document("user-1").get().to_dict()
    assert user["telegramChatId"] == 123456


def test_link_response_matches_openapi_contract():
    fields = set(LinkCodeResponse.model_fields)
    assert fields == {"linkCode", "expiresAt", "botUsername"}


def test_unlink_route_matches_openapi_contract():
    router_source = Path(__file__).parents[1].joinpath("app/api/v1/telegram.py").read_text()
    assert '@router.delete("/telegram/unlink"' in router_source


def test_identity_cannot_be_claimed_by_two_users_and_preserves_private_chat_destination():
    db = FakeFirestore()
    db.collection("users").document("user-1").set({"telegramUserId": None})
    db.collection("users").document("user-2").set({"telegramUserId": None})
    service = telegram_service(db)
    first = service.generate_link_code("user-1")
    second = service.generate_link_code("user-2")

    assert service.validate_and_link(first.code, telegram_user_id=42, telegram_chat_id=420, username="alex")
    assert not service.validate_and_link(second.code, telegram_user_id=42, telegram_chat_id=999, username="other")
    assert db.collection("telegram_identities").document("42").get().to_dict()["uid"] == "user-1"
    assert db.collection("users").document("user-1").get().to_dict()["telegramChatId"] == 420
    # A failed foreign claim does not burn a code the owner can use later.
    assert service._code_ref(second.code).get().exists


def test_group_chat_does_not_link_or_process_a_personal_account(monkeypatch):
    db = FakeFirestore()
    db.collection("users").document("user-1").set({"telegramUserId": None})
    service = telegram_service(db)
    code = service.generate_link_code("user-1").code
    send = AsyncMock(return_value=True)
    monkeypatch.setattr(TelegramService, "send_message", send)

    asyncio.run(
        process_telegram_update(
            {
                "message": {
                    "chat": {"id": -100, "type": "group"},
                    "from": {"id": 42, "username": "alex"},
                    "text": f"/link {code}",
                }
            },
            db,
        )
    )

    assert db.collection("users").document("user-1").get().to_dict()["telegramUserId"] is None
    assert not db.collection("telegram_identities").document("42").get().exists
    assert "privacy" in send.await_args.args[1].lower()


def test_update_claim_is_idempotent_and_a_failed_handler_is_released():
    now = datetime(2026, 8, 29, tzinfo=timezone.utc)
    db = FakeFirestore()
    service = TelegramService(
        db,
        transactional_runner=lambda function: function,
        clock=lambda: now,
    )

    assert service.claim_update(123) == "acquired"
    assert service.claim_update(123) == "busy"
    service.complete_update(123)
    assert service.claim_update(123) == "completed"
    assert service.claim_update(124) == "acquired"
    service.release_update(124)
    assert service.claim_update(124) == "acquired"


def test_outbound_delivery_distinguishes_retryable_and_ambiguous_failures(monkeypatch):
    db = FakeFirestore()
    service = telegram_service(db)

    class Response:
        def __init__(self, status_code: int):
            self.status_code = status_code

        def json(self):
            return {"ok": self.status_code == 200}

    class Client:
        def __init__(self, response=None, error=None):
            self.response = response
            self.error = error
            self.payload = None

        async def post(self, _url, *, json, timeout):
            self.payload = json
            assert timeout == 10.0
            if self.error:
                raise self.error
            return self.response

    import app.services.telegram_service as telegram_module

    retryable_client = Client(response=Response(429))
    monkeypatch.setattr(telegram_module, "get_http_client", lambda: retryable_client)
    result = asyncio.run(service.send_message_result(123, "<plain text>"))
    assert result.retryable and not result.ambiguous and not result.delivered
    assert "parse_mode" not in retryable_client.payload

    ambiguous_client = Client(error=telegram_module.httpx.ConnectError("timed out"))
    monkeypatch.setattr(telegram_module, "get_http_client", lambda: ambiguous_client)
    result = asyncio.run(service.send_message_result(123, "hello"))
    assert result.ambiguous and not result.retryable and not result.delivered
