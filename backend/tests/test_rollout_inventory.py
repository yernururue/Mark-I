"""Offline checks for inventory failure handling and sanitized evidence."""

import json
import subprocess

import pytest

from scripts import inspect_rollout_foundation as inventory


@pytest.mark.parametrize(
    ("diagnostic", "expected"),
    [
        ("NOT_FOUND: secret does not exist", "not-found"),
        ("PERMISSION_DENIED: resource not found or access denied", "permission-denied"),
        ("UNAUTHENTICATED: refresh required", "auth-error"),
        ("You do not currently have an active account selected", "auth-error"),
        ("ConnectionError: endpoint unavailable", "network-error"),
        ("unexpected failure", "command-error"),
    ],
)
def test_classifies_command_failures(diagnostic, expected):
    assert inventory._result_state(subprocess.CompletedProcess([], 1, "", diagnostic)) == expected


def test_timeout_discards_partial_output(monkeypatch):
    def timeout(command, **kwargs):
        assert kwargs["timeout"] == inventory.COMMAND_TIMEOUT_SECONDS
        raise subprocess.TimeoutExpired(command, kwargs["timeout"], output="secret-output", stderr="secret-error")

    monkeypatch.setattr(inventory.subprocess, "run", timeout)
    result = inventory._run(("projects", "describe", inventory.PROJECT_ID))
    assert inventory._result_state(result) == "timeout"
    assert "secret" not in result.stdout + result.stderr


def test_execution_failure_becomes_sanitized_result(monkeypatch):
    def denied(*args, **kwargs):
        raise OSError("secret-location")

    monkeypatch.setattr(inventory.subprocess, "run", denied)
    result = inventory._run(("auth", "list"))
    assert inventory._result_state(result) == "command-error"
    assert "secret" not in result.stderr


@pytest.mark.parametrize("metadata", ["not-json", "{}", '["unexpected"]'])
def test_rejects_invalid_metadata(metadata):
    assert inventory._metadata_list(subprocess.CompletedProcess([], 0, metadata, "")) == ("invalid-metadata", [])


@pytest.fixture
def simulated_inventory(monkeypatch):
    monkeypatch.setattr(inventory.shutil, "which", lambda command: "/fake/gcloud")
    monkeypatch.setattr(
        inventory,
        "_checks",
        lambda: [inventory.Check("foundation-resource", ("pubsub", "topics", "describe"), True)],
    )
    monkeypatch.setattr(inventory, "SECRETS", ())
    monkeypatch.setattr(inventory, "SECRET_ACCESSORS", {})
    monkeypatch.setattr(inventory, "evaluate_indexes", lambda expected, live: [{"state": "READY"}])
    monkeypatch.setattr(inventory, "evaluate_project_metadata", lambda metadata, **kwargs: {"state": "READY"})
    monkeypatch.setattr(inventory, "evaluate_enabled_apis", lambda metadata, required: {"state": "READY", "missing": []})
    monkeypatch.setattr(inventory, "SERVICE_ACCOUNTS", ())
    monkeypatch.setattr(inventory, "evaluate_artifact_repository", lambda metadata, **kwargs: {"state": "READY"})

    def configure(*, resource_code=0, resource_error="", account="builder@example.com", index_code=0):
        def run(args):
            if args[0] == "auth":
                return subprocess.CompletedProcess(args, 0, account, "")
            if args[0] == "projects":
                return subprocess.CompletedProcess(args, 0, "{}", "")
            if args[0] == "services":
                return subprocess.CompletedProcess(args, 0, "[]", "")
            if args[0] == "artifacts":
                return subprocess.CompletedProcess(args, 0, "{}", "")
            if args[0] == "firestore":
                return subprocess.CompletedProcess(args, index_code, "[]", "PERMISSION_DENIED secret-diagnostic")
            return subprocess.CompletedProcess(
                args,
                resource_code,
                inventory.PROJECT_ID if not resource_code else "",
                resource_error,
            )

        monkeypatch.setattr(inventory, "_run", run)

    return configure


def test_inventory_reports_permission_error_and_never_prints_diagnostic(simulated_inventory, capsys):
    simulated_inventory(resource_code=1, resource_error="PERMISSION_DENIED secret-diagnostic")
    assert inventory.main(["--json"]) == 2
    output = capsys.readouterr().out
    assert "secret-diagnostic" not in output
    report = json.loads(output)
    assert report["status"] == "error"
    assert report["inspection_errors"] == ["foundation-resource"]
    assert report["foundation_gaps"] == ["foundation-resource"]


@pytest.mark.parametrize(("strict", "expected_code"), [(False, 0), (True, 1)])
def test_missing_resource_remains_distinct_from_inspection_failure(simulated_inventory, capsys, strict, expected_code):
    simulated_inventory(resource_code=1, resource_error="NOT_FOUND: missing")
    assert inventory.main(["--json", *(["--strict-foundation"] if strict else [])]) == expected_code
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "incomplete"
    assert report["inspection_errors"] == []


def test_failed_index_command_cannot_pass_from_stdout(simulated_inventory, capsys):
    simulated_inventory(index_code=1)
    assert inventory.main(["--json"]) == 2
    report = json.loads(capsys.readouterr().out)
    assert report["inspection_errors"] == ["firestore/composite-indexes"]


def test_no_active_account_stops_inventory(simulated_inventory, capsys):
    simulated_inventory(account="")
    assert inventory.main(["--json"]) == 2
    report = json.loads(capsys.readouterr().out)
    assert report["checks"] == [{"name": "active-account", "state": "auth-error"}]


def test_json_output_is_one_complete_document(simulated_inventory, capsys):
    simulated_inventory()
    assert inventory.main(["--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "ok"
    assert report["scope"]["project"] == inventory.PROJECT_ID
    assert report["schema_version"] == 1


def test_strict_inventory_requires_protected_github_credential_file(simulated_inventory, capsys):
    simulated_inventory()
    assert inventory.main(["--strict-foundation", "--json"]) == 1
    report = json.loads(capsys.readouterr().out)
    assert "local/github-credential-file" in report["foundation_gaps"]
    assert report["checks"][0]["value"] == {"state": "UNSET"}


def test_inventory_reports_only_credential_metadata(simulated_inventory, capsys, tmp_path):
    credential = tmp_path / "sensitive-name"
    credential.write_text("super-secret-value", encoding="utf-8")
    credential.chmod(0o600)
    simulated_inventory()
    assert inventory.main(["--strict-foundation", "--json", "--github-credential-file", str(credential)]) == 0
    output = capsys.readouterr().out
    assert str(credential) not in output
    assert "super-secret-value" not in output
    report = json.loads(output)
    assert report["checks"][0] == {
        "name": "local/github-credential-file",
        "state": "ok",
        "value": {"mode": "0600", "state": "READY"},
    }
