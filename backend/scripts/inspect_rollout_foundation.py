#!/usr/bin/env python3
"""Inspect rollout resources without mutating GCP or reading secret payloads."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

try:
    from scripts.rollout_foundation_checks import evaluate_indexes, evaluate_secret_versions
except ModuleNotFoundError:
    from rollout_foundation_checks import evaluate_indexes, evaluate_secret_versions


PROJECT_ID = "mark-i-506218"
REGION = "us-central1"
DATABASE = "mark-i"
BACKEND_ROOT = Path(__file__).resolve().parents[1]
COMMAND_TIMEOUT_SECONDS = 30

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
    command = ("gcloud", *args, f"--project={PROJECT_ID}", "--quiet")
    try:
        return subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        # Partial output and exception strings can contain credentials; discard both.
        return subprocess.CompletedProcess(command, 124, "", "timeout")
    except OSError:
        return subprocess.CompletedProcess(command, 127, "", "execution-error")


def _result_state(result: subprocess.CompletedProcess[str]) -> str:
    """Classify command failures without emitting raw CLI diagnostics."""
    if result.returncode == 0:
        return "ok" if result.stdout.strip() else "empty"
    if result.returncode == 124:
        return "timeout"
    error = result.stderr.lower()
    if any(value in error for value in ("unauthenticated", "invalid_grant", "reauth", "no active account", "do not currently have an active account", "login required")):
        return "auth-error"
    if any(value in error for value in ("permission_denied", "permission denied", "forbidden", "does not have permission", "http 403")):
        return "permission-denied"
    if any(value in error for value in ("not_found", "not found", "does not exist", "http 404")):
        return "not-found"
    if any(value in error for value in ("connection", "network", "unavailable", "timed out", "name resolution", "ssl")):
        return "network-error"
    return "command-error"


def _metadata_list(result: subprocess.CompletedProcess[str]) -> tuple[str, list[dict]]:
    state = _result_state(result)
    if state != "ok":
        return state, []
    try:
        metadata = json.loads(result.stdout)
    except (ValueError, TypeError):
        return "invalid-metadata", []
    if not isinstance(metadata, list) or not all(isinstance(item, dict) for item in metadata):
        return "invalid-metadata", []
    return "ok", metadata


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict-foundation",
        action="store_true",
        help="fail if any Stage 2 foundation resource or READY Firestore index is missing",
    )
    parser.add_argument("--json", action="store_true", help="emit one sanitized JSON evidence document")
    options = parser.parse_args(argv)

    report = {
        "schema_version": 1,
        "scope": {"project": PROJECT_ID, "region": REGION, "database": DATABASE},
        "active_account": None,
        "checks": [],
        "foundation_gaps": [],
        "inspection_errors": [],
    }

    def record(name: str, state: str, *, required: bool = False, value=None) -> None:
        entry = {"name": name, "state": state}
        if value is not None:
            entry["value"] = value
        report["checks"].append(entry)
        if required and state != "ok":
            report["foundation_gaps"].append(name)
        if state in {"permission-denied", "auth-error", "network-error", "timeout", "command-error", "empty", "invalid-metadata"}:
            report["inspection_errors"].append(name)

    def finish() -> int:
        failures = len(report["inspection_errors"])
        gaps = len(report["foundation_gaps"])
        code = 2 if failures else 1 if options.strict_foundation and gaps else 0
        report["status"] = "error" if failures else "incomplete" if gaps else "ok"
        if options.json:
            print(json.dumps(report, sort_keys=True))
        else:
            print(f"active-account: {report['active_account'] or 'none'}")
            print(f"scope: project={PROJECT_ID} region={REGION} database={DATABASE}")
            for check in report["checks"]:
                value = check.get("value")
                detail = f" ({json.dumps(value, sort_keys=True)})" if value is not None else ""
                print(f"{check['name']}: {check['state']}{detail}")
            prefix = "FAIL" if code else "inspected"
            print(f"rollout-foundation: {prefix}: {gaps} foundation gaps, {failures} inspection errors")
        return code

    if shutil.which("gcloud") is None:
        record("gcloud-cli", "command-error")
        return finish()

    active_account = _run(("auth", "list", "--filter=status:ACTIVE", "--format=value(account)"))
    account = active_account.stdout.strip()
    account_state = _result_state(active_account)
    if account_state != "ok":
        record("active-account", "auth-error" if account_state == "empty" else account_state)
        return finish()
    report["active_account"] = account

    for check in _checks():
        result = _run(check.args)
        state = _result_state(result)
        record(check.name, state, required=check.foundation_required, value=result.stdout.strip() if state == "ok" else None)

    # Inspect version metadata only; never invoke `secrets versions access`.
    source = BACKEND_ROOT.joinpath("cloudbuild.yaml").read_text(encoding="utf-8")
    for secret in SECRETS:
        substitution = "_" + secret.removeprefix("mark-i-").replace("-", "_").upper() + "_VERSION"
        match = re.search(rf"^  {re.escape(substitution)}:\s*['\"]?([1-9][0-9]*)['\"]?\s*$", source, re.MULTILINE)
        name = f"secret-version/{secret}"
        if not match:
            record(name, "invalid-metadata", required=True)
            continue
        state, versions = _metadata_list(_run(("secrets", "versions", "list", secret, "--format=json")))
        if state != "ok":
            record(name, state, required=True)
            continue
        try:
            version = evaluate_secret_versions(versions, required_version=match.group(1))
        except (ValueError, TypeError, KeyError):
            record(name, "invalid-metadata", required=True)
            continue
        record(name, "ok" if version["state"] == "ENABLED" else "not-ready", required=True, value=version)

    indexes = _run(
        (
            "firestore",
            "indexes",
            "composite",
            "list",
            f"--database={DATABASE}",
            "--format=json",
        )
    )
    state, live_indexes = _metadata_list(indexes)
    if state != "ok":
        record("firestore/composite-indexes", state, required=True)
    else:
        try:
            expected = json.loads(BACKEND_ROOT.joinpath("firestore.indexes.json").read_text(encoding="utf-8"))["indexes"]
            evaluated = evaluate_indexes(expected, live_indexes)
            ready = bool(evaluated) and all(index["state"] == "READY" for index in evaluated)
            record("firestore/composite-indexes", "ok" if ready else "not-ready", required=True, value=evaluated)
        except (ValueError, TypeError, KeyError):
            record("firestore/composite-indexes", "invalid-metadata", required=True)
    return finish()


if __name__ == "__main__":
    raise SystemExit(main())
