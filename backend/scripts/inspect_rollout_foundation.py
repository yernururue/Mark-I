#!/usr/bin/env python3
"""Inspect rollout resources without mutating GCP or reading secret payloads."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from dataclasses import dataclass


PROJECT_ID = "mark-i-506218"
REGION = "us-central1"
DATABASE = "mark-i"

RUNTIME_SERVICE_ACCOUNTS = (
    "mark-i-api-runtime",
    "mark-i-github-worker-runtime",
    "mark-i-opportunity-worker-runtime",
    "mark-i-pubsub-push",
    "mark-i-cloud-build",
)
SECRETS = (
    "mark-i-telegram-bot-token",
    "mark-i-telegram-webhook-secret",
    "mark-i-github-client-id",
    "mark-i-github-client-secret",
    "mark-i-github-webhook-secret",
    "mark-i-scheduler-shared-secret",
)


@dataclass(frozen=True)
class Check:
    name: str
    args: tuple[str, ...]
    foundation_required: bool = False


def _checks() -> list[Check]:
    checks = [
        Check("project", ("projects", "describe", PROJECT_ID, "--format=value(projectId)"), True),
        Check(
            "artifact-registry/mark-i-backend",
            (
                "artifacts",
                "repositories",
                "describe",
                "mark-i-backend",
                f"--location={REGION}",
                "--format=value(name)",
            ),
            True,
        ),
        Check("pubsub/topic/github-events", ("pubsub", "topics", "describe", "github-events", "--format=value(name)"), True),
        Check(
            "pubsub/topic/opportunity-collect",
            ("pubsub", "topics", "describe", "opportunity-collect", "--format=value(name)"),
            True,
        ),
        Check(
            "pubsub/subscription/github-events-sub",
            ("pubsub", "subscriptions", "describe", "github-events-sub", "--format=value(name)"),
            True,
        ),
        Check(
            "pubsub/subscription/opportunity-collect-sub",
            ("pubsub", "subscriptions", "describe", "opportunity-collect-sub", "--format=value(name)"),
            True,
        ),
    ]
    checks.extend(
        Check(
            f"service-account/{account}",
            (
                "iam",
                "service-accounts",
                "describe",
                f"{account}@{PROJECT_ID}.iam.gserviceaccount.com",
                "--format=value(email)",
            ),
            True,
        )
        for account in RUNTIME_SERVICE_ACCOUNTS
    )
    checks.extend(
        Check(
            f"secret/{secret}",
            ("secrets", "describe", secret, "--format=value(name)"),
            True,
        )
        for secret in SECRETS
    )
    checks.extend(
        Check(
            f"cloud-run/{service}",
            (
                "run",
                "services",
                "describe",
                service,
                f"--region={REGION}",
                "--format=value(status.conditions[?type=Ready].status)",
            ),
        )
        for service in ("mark-i-api", "mark-i-github-worker", "mark-i-opportunity-worker")
    )
    checks.append(
        Check(
            "scheduler/opportunity-trigger",
            (
                "scheduler",
                "jobs",
                "describe",
                "opportunity-trigger",
                f"--location={REGION}",
                "--format=value(state)",
            ),
        )
    )
    return checks


def _run(args: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ("gcloud", *args, f"--project={PROJECT_ID}", "--quiet"),
        check=False,
        capture_output=True,
        text=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict-foundation",
        action="store_true",
        help="fail if any Stage 2 foundation resource or READY Firestore index is missing",
    )
    options = parser.parse_args()

    if shutil.which("gcloud") is None:
        print("rollout-foundation: FAIL: gcloud CLI is not installed")
        return 2

    active_account = subprocess.run(
        ("gcloud", "auth", "list", "--filter=status:ACTIVE", "--format=value(account)"),
        check=False,
        capture_output=True,
        text=True,
    )
    account = active_account.stdout.strip()
    print(f"active-account: {account or 'none'}")
    print(f"scope: project={PROJECT_ID} region={REGION} database={DATABASE}")

    missing_required: list[str] = []
    for check in _checks():
        result = _run(check.args)
        value = result.stdout.strip()
        state = value if result.returncode == 0 and value else "missing"
        print(f"{check.name}: {state}")
        if check.foundation_required and state == "missing":
            missing_required.append(check.name)

    indexes = _run(
        (
            "firestore",
            "indexes",
            "composite",
            "list",
            f"--database={DATABASE}",
            "--format=value(state)",
        )
    )
    index_states = [state for state in indexes.stdout.splitlines() if state]
    ready_indexes = sum(state == "READY" for state in index_states)
    print(f"firestore/composite-indexes: ready={ready_indexes} total={len(index_states)}")
    if ready_indexes < 4:
        missing_required.append("firestore/composite-indexes")

    if options.strict_foundation and missing_required:
        print(f"rollout-foundation: FAIL: {len(missing_required)} required checks are incomplete")
        return 1

    print(f"rollout-foundation: inspected ({len(missing_required)} foundation gaps)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
