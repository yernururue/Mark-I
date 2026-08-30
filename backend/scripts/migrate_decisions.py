"""Idempotently migrate unambiguous legacy Firestore decision documents.

Run with ``python scripts/migrate_decisions.py --dry-run`` first. The command
does not create missing policy fields: ambiguous records are reported and left
untouched for manual review.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Any

from google.cloud import firestore

from app.services.decision_migration_service import (
    CURRENT_DECISION_SCHEMA_VERSION,
    DecisionMigrationService,
)


@dataclass
class MigrationReport:
    scanned: int = 0
    migrated: int = 0
    already_current: int = 0
    ambiguous: int = 0
    errors: int = 0


def migrate_decisions(db: Any, *, dry_run: bool) -> MigrationReport:
    report = MigrationReport()
    for snapshot in db.collection_group("decisions").stream():
        report.scanned += 1
        data = snapshot.to_dict() or {}
        if data.get("schemaVersion") == CURRENT_DECISION_SCHEMA_VERSION:
            report.already_current += 1
            continue
        result = DecisionMigrationService.migration_update(data, document_id=snapshot.id)
        if result.document is None:
            report.ambiguous += 1
            print(f"SKIP {snapshot.reference.path}: {result.reason}")
            continue
        if dry_run:
            report.migrated += 1
            print(f"WOULD MIGRATE {snapshot.reference.path}")
            continue
        try:
            snapshot.reference.update(result.document)
            report.migrated += 1
            print(f"MIGRATED {snapshot.reference.path}")
        except Exception as exc:  # Preserve progress and report every failed document.
            report.errors += 1
            print(f"ERROR {snapshot.reference.path}: {type(exc).__name__}")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Report migration candidates without writing")
    args = parser.parse_args()
    report = migrate_decisions(firestore.Client(), dry_run=args.dry_run)
    print(
        "scanned={scanned} migrated={migrated} current={already_current} ambiguous={ambiguous} errors={errors}".format(
            **report.__dict__
        )
    )
    return 1 if report.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
