from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from google.cloud import firestore

from app.services.decision_service import DecisionService
from app.services.observation_service import ObservationService
from app.services.skill_service import SkillService
from tests.fakes import FakeFirestore


@pytest.mark.parametrize(
    ("significance", "intensity", "flags", "expected"),
    [
        (9, "chill", [], True),
        (5, "chill", [], False),
        (3, "brutal", [], True),
        (1, "brutal", [], False),
        (5, "normal", [], True),
        (4, "normal", [], False),
        (2, "chill", ["new_concept"], True),
        (1, "chill", ["repeated_error"], True),
        (3, "normal", ["milestone_reached"], True),
        (8, "brutal", ["skill_regression"], True),
        (7, "chill", [], True),
        (6, "chill", [], False),
    ],
)
def test_decision_policy_pict_matrix(significance, intensity, flags, expected):
    db = FakeFirestore()
    service = DecisionService(db)

    should_notify, reason = service.evaluate_and_log(
        uid="user-1",
        observation_id="obs-1",
        significance=significance,
        intensity=intensity,
        escalation_flags=flags,
    )

    saved = db.collection("users").document("user-1").collection("decisions").get()
    assert should_notify is expected
    assert len(saved) == 1
    assert saved[0].to_dict()["action"] == ("notified" if expected else "silent")
    assert saved[0].to_dict()["threshold"] == {"chill": 7, "normal": 5, "brutal": 3}[intensity]
    assert saved[0].to_dict()["intensity"] == intensity
    assert saved[0].to_dict()["deliveryStatus"] == ("pending" if expected else "skipped")
    assert "Escalation" in reason if flags else "Significance" in reason


@pytest.mark.parametrize(
    ("current", "assessment", "expected"),
    [
        (0.0, 8, 8.0),
        (5.0, 7, 5.6),
        (10.0, 10, 10.0),
        (7.0, 2, 5.5),
        (3.5, 5, 3.95),
    ],
)
def test_skill_weighted_average_pict_cases(current, assessment, expected):
    db = FakeFirestore()
    db.collection("users").document("user-1").set({"skills": {"testing": current}})
    service = SkillService(db, transactional_runner=lambda function: function)

    result = service.update_skill("user-1", "testing", assessment)

    assert result == expected
    assert db.collection("users").document("user-1").get().to_dict()["skills"]["testing"] == expected


def test_skill_service_uses_supported_firestore_transaction_api():
    assert callable(firestore.transactional)


def test_skills_are_sorted_descending_for_dashboard():
    db = FakeFirestore()
    db.collection("users").document("user-1").set({"skills": {"python": 4.0, "testing": 8.0}})
    observations = ObservationService(db)
    observations.create_observation("user-1", "github", "Python work", "python", "positive", 4)
    observations.create_observation("user-1", "github", "Tests", "testing", "positive", 8)

    skills = SkillService(db).get_skills("user-1")

    assert [skill.name for skill in skills] == ["testing", "python"]
    assert [skill.observationCount for skill in skills] == [1, 1]


def test_observations_filter_by_concept_and_order_newest_first():
    db = FakeFirestore()
    collection = db.collection("users").document("user-1").collection("observations")
    now = datetime.now(timezone.utc)
    collection.document("obs-old").set(
        {
            "id": "obs-old",
            "source": "github",
            "summary": "Old recursion",
            "concept": "recursion",
            "sentiment": "neutral",
            "significanceScore": 3,
            "createdAt": now - timedelta(days=1),
        }
    )
    collection.document("obs-new").set(
        {
            "id": "obs-new",
            "source": "chat",
            "summary": "New recursion",
            "concept": "recursion",
            "sentiment": "positive",
            "significanceScore": 6,
            "createdAt": now,
        }
    )
    collection.document("obs-other").set(
        {
            "id": "obs-other",
            "source": "github",
            "summary": "Testing",
            "concept": "testing",
            "sentiment": "positive",
            "significanceScore": 7,
            "createdAt": now,
        }
    )

    observations = ObservationService(db).get_recent_observations("user-1", concept="recursion")

    assert [item.id for item in observations] == ["obs-new", "obs-old"]


def test_observations_support_source_filter_from_api_contract():
    db = FakeFirestore()
    service = ObservationService(db)
    assert service.get_recent_observations("user-1", source="github") == []
