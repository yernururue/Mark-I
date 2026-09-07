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
PUBSUB_TOPOLOGY = tuple(zip(TOPICS, SUBSCRIPTIONS, strict=True))
SECRETS = (
    "mark-i-telegram-bot-token",
    "mark-i-telegram-webhook-secret",
    "mark-i-github-client-id",
    "mark-i-github-client-secret",
    "mark-i-github-webhook-secret",
    "mark-i-scheduler-shared-secret",
)
SCHEDULER_JOB = "opportunity-trigger"
REQUIRED_APIS = (
    "aiplatform.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudscheduler.googleapis.com",
    "firestore.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "pubsub.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "serviceusage.googleapis.com",
)

_API_IDENTITY = f"serviceAccount:mark-i-api-runtime@{PROJECT_ID}.iam.gserviceaccount.com"
_GITHUB_IDENTITY = f"serviceAccount:mark-i-github-worker-runtime@{PROJECT_ID}.iam.gserviceaccount.com"
_OPPORTUNITY_IDENTITY = f"serviceAccount:mark-i-opportunity-worker-runtime@{PROJECT_ID}.iam.gserviceaccount.com"

SECRET_ACCESSORS = {
    "mark-i-telegram-bot-token": (_API_IDENTITY, _GITHUB_IDENTITY, _OPPORTUNITY_IDENTITY),
    "mark-i-telegram-webhook-secret": (_API_IDENTITY,),
    "mark-i-github-client-id": (_API_IDENTITY,),
    "mark-i-github-client-secret": (_API_IDENTITY,),
    "mark-i-github-webhook-secret": (_API_IDENTITY,),
    "mark-i-scheduler-shared-secret": (_API_IDENTITY,),
}


def service_account_email(account: str) -> str:
    """Return the fixed-project email for a declared service account."""
    if account not in SERVICE_ACCOUNTS:
        raise ValueError("unknown rollout service account")
    return f"{account}@{PROJECT_ID}.iam.gserviceaccount.com"


def foundation_iam_grants() -> tuple[dict[str, str], ...]:
    """Return the exact least-privilege grant set for human approval."""
    project = f"projects/{PROJECT_ID}"
    grants: list[dict[str, str]] = []
    for _, account, _ in SERVICES:
        member = f"serviceAccount:{service_account_email(account)}"
        grants.extend(
            (
                {"resource": project, "role": "roles/datastore.user", "member": member},
                {"resource": project, "role": "roles/aiplatform.user", "member": member},
            )
        )

    api_member = f"serviceAccount:{service_account_email('mark-i-api-runtime')}"
    github_member = f"serviceAccount:{service_account_email('mark-i-github-worker-runtime')}"
    build_member = f"serviceAccount:{service_account_email(CLOUD_BUILD_SERVICE_ACCOUNT)}"
    push_member = f"serviceAccount:{service_account_email(PUBSUB_PUSH_SERVICE_ACCOUNT)}"

    for topic in TOPICS:
        grants.append(
            {"resource": f"{project}/topics/{topic}", "role": "roles/pubsub.publisher", "member": api_member}
        )
    grants.extend(
        (
            {"resource": project, "role": "roles/secretmanager.admin", "member": api_member},
            {
                "resource": project,
                "role": "roles/secretmanager.secretAccessor",
                "member": github_member,
                "condition": "resource.name.startsWith('projects/691051892786/secrets/github-token-')",
            },
            {"resource": project, "role": "roles/run.admin", "member": build_member},
            {"resource": project, "role": "roles/logging.logWriter", "member": build_member},
            {
                "resource": f"{project}/locations/{REGION}/repositories/{ARTIFACT_REPOSITORY}",
                "role": "roles/artifactregistry.writer",
                "member": build_member,
            },
        )
    )
    for _, account, _ in SERVICES:
        grants.append(
            {
                "resource": f"{project}/serviceAccounts/{service_account_email(account)}",
                "role": "roles/iam.serviceAccountUser",
                "member": build_member,
            }
        )
    grants.append(
        {
            "resource": f"{project}/serviceAccounts/{service_account_email(PUBSUB_PUSH_SERVICE_ACCOUNT)}",
            "role": "roles/iam.serviceAccountUser",
            "member": build_member,
        }
    )
    for subscription in SUBSCRIPTIONS:
        grants.append(
            {
                "resource": f"{project}/subscriptions/{subscription}",
                "role": "roles/pubsub.editor",
                "member": build_member,
            }
        )
    for service, _, private in SERVICES:
        if private:
            grants.append(
                {
                    "resource": f"{project}/locations/{REGION}/services/{service}",
                    "role": "roles/run.invoker",
                    "member": push_member,
                }
            )
    for secret, members in SECRET_ACCESSORS.items():
        for member in members:
            grants.append(
                {
                    "resource": f"{project}/secrets/{secret}",
                    "role": "roles/secretmanager.secretAccessor",
                    "member": member,
                }
            )
    return tuple(grants)
