"""Safe compatibility and migration rules for pre-v2 decision records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.services.decision_service import INTENSITY_THRESHOLDS


CURRENT_DECISION_SCHEMA_VERSION = 2


@dataclass(frozen=True)
class DecisionMigration:
    document: dict[str, Any] | None
    reason: str | None = None


class DecisionMigrationService:
    """Map only unambiguous legacy fields; never guess a policy decision."""

    @staticmethod
    def normalize(data: dict[str, Any], *, document_id: str) -> DecisionMigration:
        if data.get("schemaVersion") == CURRENT_DECISION_SCHEMA_VERSION:
            return DecisionMigration(document=dict(data))

        should_notify = data.get("shouldNotify")
        threshold = data.get("intensityThreshold")
        significance = data.get("significanceScore")
        observation_id = data.get("observationId")
        created_at = data.get("createdAt")
        if not isinstance(should_notify, bool):
            return DecisionMigration(None, "legacy decision has no boolean shouldNotify")
        if not isinstance(threshold, int) or threshold not in INTENSITY_THRESHOLDS.values():
            return DecisionMigration(None, "legacy decision has an ambiguous intensityThreshold")
        if not isinstance(significance, int) or not 1 <= significance <= 10:
            return DecisionMigration(None, "legacy decision has an invalid significanceScore")
        if not isinstance(observation_id, str) or not observation_id:
            return DecisionMigration(None, "legacy decision has no observationId")
        if not isinstance(created_at, datetime):
            return DecisionMigration(None, "legacy decision has no createdAt timestamp")

        intensity = next(name for name, value in INTENSITY_THRESHOLDS.items() if value == threshold)
        action = "notified" if should_notify else "silent"
        return DecisionMigration(
            {
                "schemaVersion": CURRENT_DECISION_SCHEMA_VERSION,
                "id": data.get("id") if isinstance(data.get("id"), str) else document_id,
                "observationId": observation_id,
                "action": action,
                "significanceScore": significance,
                "threshold": threshold,
                "intensity": intensity,
                "escalationFlags": [
                    flag for flag in data.get("escalationFlags", []) if isinstance(flag, str)
                ],
                # Legacy records did not establish whether an external request
                # succeeded. "unknown" is truthful and prevents a false claim
                # that a notification was delivered.
                "deliveryStatus": "unknown" if should_notify else "suppressed",
                "reason": data.get("reason")
                if isinstance(data.get("reason"), str) and data["reason"].strip()
                else "Migrated legacy decision; original delivery outcome is unavailable.",
                "createdAt": created_at,
                "legacySchemaVersion": data.get("schemaVersion", 1),
            }
        )

    @staticmethod
    def migration_update(data: dict[str, Any], *, document_id: str, now: datetime | None = None) -> DecisionMigration:
        result = DecisionMigrationService.normalize(data, document_id=document_id)
        if result.document is None or data.get("schemaVersion") == CURRENT_DECISION_SCHEMA_VERSION:
            return result
        migrated = dict(result.document)
        migrated["migratedAt"] = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        return DecisionMigration(migrated)
