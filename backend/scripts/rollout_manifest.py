"""Single source of truth for the fixed Mark-I rollout resource names."""

from __future__ import annotations

PROJECT_ID = "mark-i-506218"
PROJECT_NUMBER = "691051892786"
REGION = "us-central1"
DATABASE = "mark-i"
ARTIFACT_REPOSITORY = "mark-i-backend"
IMAGE_NAME = "mark-i-backend"

API_SERVICE = "mark-i-api"
GITHUB_WORKER_SERVICE = "mark-i-github-worker"
OPPORTUNITY_WORKER_SERVICE = "mark-i-opportunity-worker"

SERVICES = (
    (API_SERVICE, "mark-i-api-runtime", False),
    (GITHUB_WORKER_SERVICE, "mark-i-github-worker-runtime", True),
    (OPPORTUNITY_WORKER_SERVICE, "mark-i-opportunity-worker-runtime", True),
)

PUBSUB_PUSH_SERVICE_ACCOUNT = "mark-i-pubsub-push"
CLOUD_BUILD_SERVICE_ACCOUNT = "mark-i-cloud-build"
SERVICE_ACCOUNTS = tuple(account for _, account, _ in SERVICES) + (
    PUBSUB_PUSH_SERVICE_ACCOUNT,
    CLOUD_BUILD_SERVICE_ACCOUNT,
)

TOPICS = ("github-events", "opportunity-collect")
SUBSCRIPTIONS = ("github-events-sub", "opportunity-collect-sub")
SECRETS = (
    "mark-i-telegram-bot-token",
    "mark-i-telegram-webhook-secret",
    "mark-i-github-client-id",
    "mark-i-github-client-secret",
    "mark-i-github-webhook-secret",
    "mark-i-scheduler-shared-secret",
)
SCHEDULER_JOB = "opportunity-trigger"


def service_account_email(account: str) -> str:
    """Return the fixed-project email for a declared service account."""
    if account not in SERVICE_ACCOUNTS:
        raise ValueError("unknown rollout service account")
    return f"{account}@{PROJECT_ID}.iam.gserviceaccount.com"
