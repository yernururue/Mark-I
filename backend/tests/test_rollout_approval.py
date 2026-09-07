"""Approval evidence must be exact, deterministic and secret-free."""

import json

import pytest

from scripts.render_rollout_approval import approval_document, main
from scripts.rollout_manifest import SECRETS, SERVICES, foundation_iam_grants


def test_foundation_approval_lists_exact_targets_without_payload_fields():
    document = approval_document("foundation")
    assert len(document["service_accounts"]) == 5
    assert document["secret_resources"] == list(SECRETS)
    assert document["iam_grants"] == list(foundation_iam_grants())
    serialized = json.dumps(document)
    assert "secret_value" not in serialized
    assert "payload" not in serialized
    assert document["mutates"] is False


def test_bootstrap_approval_requires_immutable_image_tag():
    with pytest.raises(ValueError, match="immutable image tag"):
        approval_document("bootstrap")
    with pytest.raises(ValueError, match="immutable image tag"):
        approval_document("bootstrap", "latest")
    document = approval_document("bootstrap", "release-20260907-deadbee")
    assert document["image"].endswith(":release-20260907-deadbee")
    assert document["services"] == [service for service, _, _ in SERVICES]
    assert document["pubsub_mode"] == "pull"


def test_later_gate_documents_keep_external_mutations_explicit():
    push = approval_document("pubsub-push")
    assert push["workers"] == ["mark-i-github-worker", "mark-i-opportunity-worker"]
    promotion = approval_document("production-promotion")
    assert promotion["schedule"] == "0 9 * * *"
    assert promotion["timezone"] == "Asia/Almaty"
    assert promotion["synthetic_cleanup_required"] is True


def test_cli_failure_never_echoes_bad_tag(capsys):
    bad_tag = "sensitive/bad-tag"
    assert main(["bootstrap", "--image-tag", bad_tag]) == 1
    assert bad_tag not in capsys.readouterr().out
