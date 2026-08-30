from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from firebase_admin import auth
from pydantic import ValidationError

from app.api.v1.users import create_profile, get_profile, update_profile
from app.errors import ConflictError
from app.middleware.auth import get_current_user
from app.models.user import CreateProfileRequest, UpdateProfileRequest
from app.services.user_service import UserService
from tests.fakes import FakeFirestore


@dataclass
class FakeRequest:
    headers: dict[str, str]


@pytest.mark.parametrize(
    ("headers", "token_result", "expected_uid", "expected_message"),
    [
        ({"Authorization": "Bearer valid"}, {"uid": "user-1", "email": "u@example.com"}, "user-1", None),
        ({}, None, None, "Нет заголовка авторизации"),
        ({"Authorization": "not-bearer"}, None, None, "Неправильный формат токена"),
        ({"Authorization": "Token malformed"}, None, None, "Неправильный формат токена"),
    ],
)
def test_auth_token_matrix(monkeypatch, headers, token_result, expected_uid, expected_message):
    if token_result is not None:
        monkeypatch.setattr(auth, "verify_id_token", lambda token: token_result)

    if expected_message is None:
        result = asyncio.run(get_current_user(FakeRequest(headers)))
        assert result["uid"] == expected_uid
        return

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(get_current_user(FakeRequest(headers)))
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["error"]["message"] == expected_message


def test_expired_and_invalid_tokens_return_401(monkeypatch):
    def expired(_token):
        raise auth.ExpiredIdTokenError("expired", None)

    monkeypatch.setattr(auth, "verify_id_token", expired)
    with pytest.raises(HTTPException) as expired_error:
        asyncio.run(get_current_user(FakeRequest({"Authorization": "Bearer expired"})))
    assert expired_error.value.status_code == 401
    assert expired_error.value.detail["error"]["message"] == "Токен устарел"

    monkeypatch.setattr(auth, "verify_id_token", lambda _token: (_ for _ in ()).throw(ValueError("bad token")))
    with pytest.raises(HTTPException) as invalid_error:
        asyncio.run(get_current_user(FakeRequest({"Authorization": "Bearer malformed"})))
    assert invalid_error.value.status_code == 401
    assert invalid_error.value.detail["error"]["message"] == "Недействительный токен"


@pytest.mark.parametrize(
    ("goal", "intensity", "language"),
    [
        ("Get a job at Google", "chill", "en"),
        ("Learn algorithms for LeetCode", "normal", "ru"),
        ("Master full-stack development", "brutal", "en"),
    ],
)
def test_create_and_get_profile_pict_variants(goal, intensity, language):
    db = FakeFirestore()
    service = UserService(db)
    request = CreateProfileRequest(
        displayName="Alex Dev",
        goal=goal,
        intensity=intensity,
        language=language,
    )

    created = service.create_profile("user-1", "alex@example.com", request)
    stored = db.collection("users").document("user-1").get().to_dict()

    assert created.goal == goal
    assert created.intensity == intensity
    assert created.language == language
    assert created.onboardingCompleted is True
    assert stored["skills"] == {}
    assert service.get_profile("user-1") == created


def test_get_missing_profile_returns_404():
    service = UserService(FakeFirestore())
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(get_profile(current_user={"uid": "missing"}, service=service))
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail["error"]["code"] == "NOT_FOUND"


def test_create_existing_profile_returns_409():
    db = FakeFirestore()
    service = UserService(db)
    request = CreateProfileRequest(
        displayName="Alex",
        goal="Learn algorithms",
        intensity="normal",
        language="ru",
    )
    service.create_profile("user-1", "alex@example.com", request)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            create_profile(
                request=request,
                current_user={"uid": "user-1", "email": "alex@example.com"},
                service=service,
            )
        )
    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["error"]["code"] == "CONFLICT"


def test_atomic_profile_create_does_not_overwrite_an_existing_document():
    db = FakeFirestore()
    service = UserService(db)
    original = CreateProfileRequest(displayName="Original", goal="Learn Python", intensity="normal")
    service.create_profile("user-1", "original@example.com", original)

    with pytest.raises(ConflictError):
        service.create_profile(
            "user-1",
            "attacker@example.com",
            CreateProfileRequest(displayName="Replacement", goal="Replace profile", intensity="brutal"),
        )

    stored = db.collection("users").document("user-1").get().to_dict()
    assert stored["email"] == "original@example.com"
    assert stored["displayName"] == "Original"


def test_update_missing_profile_returns_404():
    service = UserService(FakeFirestore())
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            update_profile(
                request=UpdateProfileRequest(intensity="normal"),
                current_user={"uid": "missing"},
                service=service,
            )
        )
    assert exc_info.value.status_code == 404


def test_partial_profile_update_preserves_goal_and_changes_timestamp():
    db = FakeFirestore()
    service = UserService(db)
    service.create_profile(
        "user-1",
        "alex@example.com",
        CreateProfileRequest(
            displayName="Alex",
            goal="Master full-stack",
            intensity="normal",
            language="en",
        ),
    )
    before = service.get_profile("user-1")

    updated = asyncio.run(
        update_profile(
            request=UpdateProfileRequest(intensity="chill", language="ru"),
            current_user={"uid": "user-1"},
            service=service,
        )
    )

    assert updated.goal == "Master full-stack"
    assert updated.intensity == "chill"
    assert updated.language == "ru"
    assert updated.updatedAt >= before.updatedAt


@pytest.mark.parametrize(
    "payload",
    [
        {"displayName": "", "goal": "job", "intensity": "normal"},
        {"displayName": "Alex", "goal": "job", "intensity": "extreme"},
        {"displayName": "Alex", "goal": "job", "intensity": "normal", "language": "kk"},
    ],
)
def test_profile_request_validation_rejects_invalid_values(payload):
    with pytest.raises(ValidationError):
        CreateProfileRequest.model_validate(payload)


@pytest.mark.parametrize("goal", ["", "x" * 501])
def test_profile_goal_is_free_text_but_has_mvp_length_bounds(goal):
    with pytest.raises(ValidationError):
        CreateProfileRequest(displayName="Alex", goal=goal, intensity="normal")


@pytest.mark.parametrize(
    "payload",
    [
        {"displayName": "   ", "goal": "Learn testing", "intensity": "normal"},
        {"displayName": "Alex", "goal": " \n\t ", "intensity": "normal"},
    ],
)
def test_profile_whitespace_only_text_is_rejected(payload):
    with pytest.raises(ValidationError):
        CreateProfileRequest.model_validate(payload)


def test_profile_text_is_trimmed_before_persistence():
    db = FakeFirestore()
    profile = UserService(db).create_profile(
        "user-1",
        "alex@example.com",
        CreateProfileRequest(displayName="  Alex  ", goal="  Learn Python  ", intensity="normal"),
    )
    assert (profile.displayName, profile.goal) == ("Alex", "Learn Python")


def test_profile_response_does_not_duplicate_skills_endpoint_data():
    assert "skills" not in UserService(FakeFirestore())._firestore_to_profile(
        {
            "uid": "user-1", "email": "a@example.com", "displayName": "Alex", "goal": "Learn",
            "intensity": "normal", "telegramUserId": None, "githubConnected": False,
            "createdAt": datetime.now(timezone.utc), "updatedAt": datetime.now(timezone.utc), "onboardingCompleted": True,
        }
    ).model_dump()
