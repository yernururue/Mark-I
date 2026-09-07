#!/usr/bin/env python3
"""Render sanitized, non-mutating approval evidence for rollout gates."""

from __future__ import annotations

import argparse
import json
import re

try:
    from scripts.rollout_manifest import (
        ARTIFACT_REPOSITORY,
        IMAGE_NAME,
        PROJECT_ID,
        REGION,
        SCHEDULER_JOB,
        SECRETS,
        SERVICES,
        SUBSCRIPTIONS,
        foundation_iam_grants,
        service_account_email,
    )
except ModuleNotFoundError:
    from rollout_manifest import (
        ARTIFACT_REPOSITORY,
        IMAGE_NAME,
        PROJECT_ID,
        REGION,
        SCHEDULER_JOB,
        SECRETS,
        SERVICES,
        SUBSCRIPTIONS,
        foundation_iam_grants,
        service_account_email,
    )


def approval_document(stage: str, image_tag: str | None = None) -> dict:
    base = {"schema_version": 1, "stage": stage, "project": PROJECT_ID, "region": REGION, "mutates": False}
    if stage == "foundation":
        return {
            **base,
            "service_accounts": [service_account_email(account) for _, account, _ in SERVICES]
            + [service_account_email("mark-i-pubsub-push"), service_account_email("mark-i-cloud-build")],
            "secret_resources": list(SECRETS),
            "iam_grants": list(foundation_iam_grants()),
        }
    if stage == "bootstrap":
        if not image_tag or not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}", image_tag) or image_tag.lower() == "latest":
            raise ValueError("bootstrap approval requires an immutable image tag")
        image = f"{REGION}-docker.pkg.dev/{PROJECT_ID}/{ARTIFACT_REPOSITORY}/{IMAGE_NAME}:{image_tag}"
        return {
            **base,
            "image": image,
            "services": [service for service, _, _ in SERVICES],
            "pubsub_mode": "pull",
            "required_secret_version_inputs": ["_" + secret.removeprefix("mark-i-").replace("-", "_").upper() + "_VERSION" for secret in SECRETS],
        }
    if stage == "pubsub-push":
        return {
            **base,
            "subscriptions": list(SUBSCRIPTIONS),
            "invoker": service_account_email("mark-i-pubsub-push"),
            "workers": [service for service, _, private in SERVICES if private],
        }
    if stage == "production-promotion":
        return {
            **base,
            "scheduler": SCHEDULER_JOB,
            "schedule": "0 9 * * *",
            "timezone": "Asia/Almaty",
            "synthetic_cleanup_required": True,
        }
    raise ValueError("unknown rollout approval stage")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("foundation", "bootstrap", "pubsub-push", "production-promotion"))
    parser.add_argument("--image-tag")
    args = parser.parse_args(argv)
    try:
        document = approval_document(args.stage, args.image_tag)
    except ValueError as error:
        print(f"rollout-approval: FAIL: {error}")
        return 1
    print(json.dumps(document, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
