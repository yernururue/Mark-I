from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.services.dashboard_service import DashboardService
from app.services.decision_migration_service import DecisionMigrationService
from app.services.observation_service import ObservationService
from app.services.skill_service import SkillService
from tests.fakes import FakeFirestore


def _observation(identifier: str, concept: str, created_at: datetime) -> dict:
    return {
        "id": identifier,
        "source": "github",
        "summary": identifier,
        "concept": concept,
        "sentiment": "positive",
        "significanceScore": 7,
        "createdAt": created_at,
    }


def test_dashboard_renders_current_and_unambiguous_legacy_decisions_without_guessing_ambiguous_rows():
    db = FakeFirestore()
    now = datetime(2026, 8, 29, 12, tzinfo=timezone.utc)
    decisions = db.collection("users").document("user-1").collection("decisions")
    decisions.document("legacy-good").set(
        {
            "id": "legacy-good",
            "observationId": "obs-legacy",
            "shouldNotify": True,
            "intensityThreshold": 5,
            "significanceScore": 8,
            "createdAt": now - timedelta(seconds=1),
        }
    )
    decisions.document("current").set(
        {
            "schemaVersion": 2,
            "id": "current",
            "observationId": "obs-current",
            "action": "silent",
            "significanceScore": 2,
            "threshold": 5,
            "intensity": "normal",
            "escalationFlags": [],
            "deliveryStatus": "suppressed",
            "reason": "Below threshold",
            "createdAt": now,
        }
    )
    decisions.document("legacy-ambiguous").set(
        {
            "id": "legacy-ambiguous",
            "observationId": "obs-ambiguous",
            "intensityThreshold": 5,
            "significanceScore": 8,
            "createdAt": now + timedelta(seconds=1),
        }
    )

    result = DashboardService(db, clock=lambda: now).get_recent_decisions("user-1", 10)

    assert [decision.id for decision in result] == ["current", "legacy-good"]
    legacy = result[-1]
    assert (legacy.action, legacy.intensity, legacy.threshold, legacy.deliveryStatus) == (
        "notified",
        "normal",
        5,
        "unknown",
    )


def test_legacy_decision_migration_is_idempotent_and_reports_ambiguous_records():
    now = datetime(2026, 8, 29, tzinfo=timezone.utc)
    legacy = {
        "observationId": "obs-1",
        "shouldNotify": False,
        "intensityThreshold": 7,
        "significanceScore": 3,
        "createdAt": now,
    }
    migrated = DecisionMigrationService.migration_update(legacy, document_id="legacy", now=now)

    assert migrated.document is not None
    assert migrated.document["schemaVersion"] == 2
    assert migrated.document["action"] == "silent"
    assert migrated.document["deliveryStatus"] == "suppressed"
    assert DecisionMigrationService.migration_update(migrated.document, document_id="legacy").document == migrated.document
    ambiguous = DecisionMigrationService.migration_update(
        {**legacy, "shouldNotify": "yes"}, document_id="ambiguous", now=now
    )
    assert ambiguous.document is None
    assert "shouldNotify" in (ambiguous.reason or "")


def test_skills_and_dashboard_use_persisted_timestamps_trends_and_current_streak_only():
    db = FakeFirestore()
    now = datetime(2026, 8, 29, 12, tzinfo=timezone.utc)
    db.collection("users").document("user-1").set(
        {
            "skills": {"testing": 7.0},
            "skillSignals": {
                "testing": {"recentScores": [5.0, 6.0, 7.0], "lastUpdatedAt": now - timedelta(hours=1)}
            },
            "updatedAt": now - timedelta(hours=1),
        }
    )
    observations = db.collection("users").document("user-1").collection("observations")
    observations.document("today").set(_observation("today", "testing", now))
    observations.document("yesterday").set(_observation("yesterday", "testing", now - timedelta(days=1)))
    observations.document("old").set(_observation("old", "testing", now - timedelta(days=3)))

    skill = SkillService(db).get_skills("user-1")[0]
    dashboard = DashboardService(db, clock=lambda: now).get_dashboard("user-1", 10, 10)

    assert (skill.observationCount, skill.trend, skill.lastUpdated) == (3, "up", now - timedelta(hours=1))
    assert dashboard.stats.lastActivityAt == now
    assert dashboard.stats.streakDays == 2
    assert dashboard.skills[0].lastUpdated == now - timedelta(hours=1)

    stale_dashboard = DashboardService(db, clock=lambda: now + timedelta(days=4)).get_dashboard("user-1", 10, 10)
    assert stale_dashboard.stats.streakDays == 0


def test_cursor_boundary_excludes_newer_insertions_without_duplicates():
    db = FakeFirestore()
    service = ObservationService(db)
    now = datetime(2026, 8, 29, tzinfo=timezone.utc)
    collection = db.collection("users").document("user-1").collection("observations")
    collection.document("obs-c").set(_observation("obs-c", "testing", now))
    collection.document("obs-b").set(_observation("obs-b", "testing", now))
    collection.document("obs-a").set(_observation("obs-a", "testing", now))

    first = service.get_observations("user-1", limit=1)
    collection.document("obs-new").set(_observation("obs-new", "testing", now + timedelta(seconds=1)))
    second = service.get_observations("user-1", limit=10, cursor=first.nextCursor)

    assert [item.id for item in first.observations] == ["obs-c"]
    assert [item.id for item in second.observations] == ["obs-b", "obs-a"]
    assert {item.id for item in first.observations}.isdisjoint(item.id for item in second.observations)
