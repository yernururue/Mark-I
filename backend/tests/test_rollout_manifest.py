"""Keep every rollout utility aligned to one fixed resource manifest."""

import pytest

from scripts import inspect_rollout_foundation, validate_rollout_config, verify_bootstrap_services
from scripts.rollout_manifest import (
    PROJECT_ID,
    SECRETS,
    SERVICE_ACCOUNTS,
    SERVICES,
    service_account_email,
)


def test_service_accounts_are_unique_and_fixed_to_rollout_project():
    assert len(SERVICE_ACCOUNTS) == len(set(SERVICE_ACCOUNTS)) == 5
    assert all(service_account_email(account).endswith(f"@{PROJECT_ID}.iam.gserviceaccount.com") for account in SERVICE_ACCOUNTS)


def test_rollout_utilities_share_service_and_secret_manifests():
    assert inspect_rollout_foundation.SERVICES == SERVICES
    assert inspect_rollout_foundation.SECRETS == SECRETS
    assert verify_bootstrap_services.SERVICES == tuple((service, private) for service, _, private in SERVICES)
    assert validate_rollout_config.REQUIRED_SECRETS == set(SECRETS)


def test_unknown_service_account_is_rejected():
    with pytest.raises(ValueError, match="unknown rollout service account"):
        service_account_email("unrelated")
