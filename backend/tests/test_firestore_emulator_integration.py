"""Acceptance coverage for Firestore semantics unavailable in the in-memory fake."""

from __future__ import annotations

import os
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from google.cloud import firestore

from app.config import Settings
from app.errors import ConflictError
from app.models.user import CreateProfileRequest
from app.services.telegram_service import TelegramService
from app.services.user_service import UserService


pytestmark = pytest.mark.emulator


def _db():
    if not os.getenv("FIRESTORE_EMULATOR_HOST"):
        pytest.skip("Firestore Emulator is required; run through firebase emulators:exec")
    return firestore.Client(
        project=os.getenv("FIRESTORE_EMULATOR_PROJECT", "demo-mark-i"),
        database=os.getenv("FIRESTORE_DATABASE", "(default)"),
    )


def test_emulator_transactionally_consumes_one_link_code_under_concurrency_and_rolls_back_callback():
    db = _db()
    collection = db.collection(f"acceptance_{uuid.uuid4().hex}")
    user_ref = db.collection("users").document(f"acceptance-{uuid.uuid4().hex}")
    user_ref.set({"telegramUserId": None, "telegramChatId": None})
    service = TelegramService(
        db,
        Settings(_env_file=None, TELEGRAM_BOT_TOKEN="test"),
        code_factory=lambda: "ABC123",
    )
    # The service itself uses a Firestore transaction. Two distinct Telegram
    # identities race for one code; only one can consume it and commit.
    code_ref = db.collection("telegram_link_codes").document(service._code_document_id("ABC123"))
    code_ref.set({"uid": user_ref.id, "expiresAt": None})
    rollback_ref = collection.document("rollback")

    def consume(telegram_user_id: int) -> bool:
        return service.validate_and_link("ABC123", telegram_user_id, telegram_chat_id=telegram_user_id)

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(consume, (101, 202)))

        assert sorted(results) == [False, True]
        assert not code_ref.get().exists
        assert user_ref.get().to_dict()["telegramUserId"] in {101, 202}

        @firestore.transactional
        def write_then_fail(transaction):
            transaction.set(rollback_ref, {"mustNotPersist": True})
            raise RuntimeError("intentional rollback")

        with pytest.raises(RuntimeError, match="intentional rollback"):
            write_then_fail(db.transaction())
        assert not rollback_ref.get().exists
    finally:
        user_ref.delete()
        code_ref.delete()
        rollback_ref.delete()


def test_emulator_profile_create_uses_firestore_create_precondition_under_concurrency():
    db = _db()
    uid = f"acceptance-{uuid.uuid4().hex}"
    service = UserService(db)
    request = CreateProfileRequest(displayName="Acceptance", goal="Verify Firestore", intensity="normal")

    def create_once():
        try:
            service.create_profile(uid, "acceptance@example.test", request)
            return "created"
        except ConflictError:
            return "exists"

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(lambda _: create_once(), range(2)))
        assert sorted(outcomes) == ["created", "exists"]
        assert db.collection("users").document(uid).get().exists
    finally:
        db.collection("users").document(uid).delete()
