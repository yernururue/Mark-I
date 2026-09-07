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
    from scripts.rollout_foundation_checks import (
        evaluate_artifact_repository,
        evaluate_cloud_run_service,
        evaluate_enabled_apis,
        evaluate_indexes,
        evaluate_project_metadata,
        evaluate_protected_file,
        evaluate_pubsub_subscription,
        evaluate_pubsub_topic,
        evaluate_role_bindings,
        evaluate_service_account,
        evaluate_secret_versions,
    )
    from scripts.rollout_manifest import (
        ARTIFACT_REPOSITORY,
        DATABASE,
        PROJECT_ID,
        PROJECT_NUMBER,
        PUBSUB_PUSH_SERVICE_ACCOUNT,
        PUBSUB_TOPOLOGY,
        REQUIRED_APIS,
        REGION,
        SCHEDULER_JOB,
        SECRET_ACCESSORS,
        SECRETS,
        SERVICE_ACCOUNTS,
        SERVICES,
        SUBSCRIPTIONS,
        TOPICS,
        service_account_email,
    )
except ModuleNotFoundError:
    from rollout_foundation_checks import (
        evaluate_artifact_repository,
        evaluate_cloud_run_service,
        evaluate_enabled_apis,
        evaluate_indexes,
        evaluate_project_metadata,
        evaluate_protected_file,
        evaluate_pubsub_subscription,
        evaluate_pubsub_topic,
        evaluate_role_bindings,
        evaluate_service_account,
        evaluate_secret_versions,
    )
    from rollout_manifest import (
        ARTIFACT_REPOSITORY,
        DATABASE,
        PROJECT_ID,
        PROJECT_NUMBER,
        PUBSUB_PUSH_SERVICE_ACCOUNT,
        PUBSUB_TOPOLOGY,
        REQUIRED_APIS,
        REGION,
        SCHEDULER_JOB,
        SECRET_ACCESSORS,
        SECRETS,
        SERVICE_ACCOUNTS,
        SERVICES,
        SUBSCRIPTIONS,
        TOPICS,
        service_account_email,
    )


BACKEND_ROOT = Path(__file__).resolve().parents[1]
COMMAND_TIMEOUT_SECONDS = 30


@dataclass(frozen=True)
class Check:
    name: str
    args: tuple[str, ...]
    foundation_required: bool = False


def _checks() -> list[Check]:
    checks = []
    checks.extend(
        Check(
            f"secret/{secret}",
            ("secrets", "describe", secret, "--format=value(name)"),
            True,
        )
        for secret in SECRETS
    )
    checks.append(
        Check(
            "scheduler/opportunity-trigger",
            (
                "scheduler",
                "jobs",
                "describe",
                SCHEDULER_JOB,
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


def _metadata_object(result: subprocess.CompletedProcess[str]) -> tuple[str, dict]:
    state = _result_state(result)
    if state != "ok":
        return state, {}
    try:
        metadata = json.loads(result.stdout)
    except (ValueError, TypeError):
        return "invalid-metadata", {}
    if not isinstance(metadata, dict):
        return "invalid-metadata", {}
    return "ok", metadata


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict-foundation",
        action="store_true",
        help="fail if any Stage 2 foundation resource or READY Firestore index is missing",
    )
    parser.add_argument(
        "--strict-bootstrap",
        action="store_true",
        help="also require all three deployed services to be on healthy latest revisions",
    )
    parser.add_argument(
        "--expect-pubsub-mode",
        choices=("pull", "push"),
        default="pull",
        help="expected subscription mode for the current rollout gate",
    )
    parser.add_argument("--json", action="store_true", help="emit one sanitized JSON evidence document")
    parser.add_argument(
        "--github-credential-file",
        type=Path,
        help="inspect metadata for the protected GitHub credential input without reading it",
    )
    options = parser.parse_args(argv)

    report = {
        "schema_version": 1,
        "scope": {"project": PROJECT_ID, "region": REGION, "database": DATABASE},
        "active_account": None,
        "checks": [],
        "foundation_gaps": [],
        "inspection_errors": [],
    }

    credential = evaluate_protected_file(options.github_credential_file)
    credential_ready = credential["state"] == "READY"

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
        strict = options.strict_foundation or options.strict_bootstrap
        code = 2 if failures else 1 if strict and gaps else 0
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
        record(
            "local/github-credential-file",
            "ok" if credential_ready else "not-ready",
            required=options.strict_foundation,
            value=credential,
        )
        record("gcloud-cli", "command-error")
        return finish()

    active_account = _run(("auth", "list", "--filter=status:ACTIVE", "--format=value(account)"))
    account = active_account.stdout.strip()
    account_state = _result_state(active_account)
    if account_state != "ok":
        record("active-account", "auth-error" if account_state == "empty" else account_state)
        return finish()
    report["active_account"] = account

    record(
        "local/github-credential-file",
        "ok" if credential_ready else "not-ready",
        required=options.strict_foundation,
        value=credential,
    )

    state, project_metadata = _metadata_object(
        _run(("projects", "describe", PROJECT_ID, "--format=json(projectId,projectNumber,lifecycleState)"))
    )
    if state != "ok":
        record("project/identity", state, required=True)
    else:
        project = evaluate_project_metadata(project_metadata, project_id=PROJECT_ID, project_number=PROJECT_NUMBER)
        record("project/identity", "ok" if project["state"] == "READY" else "not-ready", required=True, value=project)

    state, enabled_apis = _metadata_list(
        _run(("services", "list", "--enabled", "--format=json(config.name)"))
    )
    if state != "ok":
        record("project/required-apis", state, required=True)
    else:
        apis = evaluate_enabled_apis(enabled_apis, REQUIRED_APIS)
        record("project/required-apis", "ok" if apis["state"] == "READY" else "not-ready", required=True, value=apis)

    state, repository_metadata = _metadata_object(
        _run(
            (
                "artifacts",
                "repositories",
                "describe",
                ARTIFACT_REPOSITORY,
                f"--location={REGION}",
                "--format=json(name,format,mode)",
            )
        )
    )
    if state != "ok":
        record(f"artifact-registry/{ARTIFACT_REPOSITORY}", state, required=True)
    else:
        repository = evaluate_artifact_repository(
            repository_metadata,
            project_id=PROJECT_ID,
            region=REGION,
            repository=ARTIFACT_REPOSITORY,
        )
        record(
            f"artifact-registry/{ARTIFACT_REPOSITORY}",
            "ok" if repository["state"] == "READY" else "not-ready",
            required=True,
            value=repository,
        )

    for account in SERVICE_ACCOUNTS:
        email = service_account_email(account)
        state, account_metadata = _metadata_object(
            _run(("iam", "service-accounts", "describe", email, "--format=json(name,email,disabled)"))
        )
        name = f"service-account/{account}"
        if state != "ok":
            record(name, state, required=True)
            continue
        identity = evaluate_service_account(account_metadata, expected_email=email)
        record(name, "ok" if identity["state"] == "READY" else "not-ready", required=True, value=identity)

    push_email = service_account_email(PUBSUB_PUSH_SERVICE_ACCOUNT)
    for topic, subscription in PUBSUB_TOPOLOGY:
        state, topic_metadata = _metadata_object(
            _run(("pubsub", "topics", "describe", topic, "--format=json(name)"))
        )
        topic_name = f"pubsub/topic/{topic}"
        if state != "ok":
            record(topic_name, state, required=True)
        else:
            topic_result = evaluate_pubsub_topic(topic_metadata, project_id=PROJECT_ID, topic=topic)
            record(topic_name, "ok" if topic_result["state"] == "READY" else "not-ready", required=True, value=topic_result)

        state, subscription_metadata = _metadata_object(
            _run(
                (
                    "pubsub",
                    "subscriptions",
                    "describe",
                    subscription,
                    "--format=json(name,topic,ackDeadlineSeconds,pushConfig)",
                )
            )
        )
        subscription_name = f"pubsub/subscription/{subscription}"
        if state != "ok":
            record(subscription_name, state, required=True)
        else:
            subscription_result = evaluate_pubsub_subscription(
                subscription_metadata,
                project_id=PROJECT_ID,
                topic=topic,
                subscription=subscription,
                expected_mode=options.expect_pubsub_mode,
                push_service_account=push_email,
            )
            record(
                subscription_name,
                "ok" if subscription_result["state"] == "READY" else "not-ready",
                required=True,
                value=subscription_result,
            )

    image_prefix = f"{REGION}-docker.pkg.dev/{PROJECT_ID}/{ARTIFACT_REPOSITORY}/mark-i-backend:"
    for service, account, _ in SERVICES:
        state, service_metadata = _metadata_object(
            _run(
                (
                    "run",
                    "services",
                    "describe",
                    service,
                    f"--region={REGION}",
                    "--format=json(metadata.name,spec.template.spec.serviceAccountName,spec.template.spec.containers,status.conditions,status.latestCreatedRevisionName,status.latestReadyRevisionName,status.traffic)",
                )
            )
        )
        name = f"cloud-run/{service}"
        if state != "ok":
            record(name, state, required=options.strict_bootstrap)
            continue
        service_result = evaluate_cloud_run_service(
            service_metadata,
            service=service,
            service_account=service_account_email(account),
            image_prefix=image_prefix,
        )
        record(
            name,
            "ok" if service_result["state"] == "READY" else "not-ready",
            required=options.strict_bootstrap,
            value=service_result,
        )

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

        policy_state, policy = _metadata_object(
            _run(("secrets", "get-iam-policy", secret, "--format=json"))
        )
        policy_name = f"secret-iam/{secret}"
        if policy_state != "ok":
            record(policy_name, policy_state, required=True)
            continue
        access = evaluate_role_bindings(
            policy,
            role="roles/secretmanager.secretAccessor",
            required_members=SECRET_ACCESSORS[secret],
        )
        record(policy_name, "ok" if access["state"] == "READY" else "not-ready", required=True, value=access)

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
