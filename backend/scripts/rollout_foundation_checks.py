"""Pure, payload-free checks of Firestore and Secret Manager metadata."""

from __future__ import annotations

import json
import re
import stat
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


def evaluate_project_metadata(metadata: Any, *, project_id: str, project_number: str) -> dict[str, Any]:
    """Verify that gcloud resolved the immutable rollout project."""
    if not isinstance(metadata, dict):
        return {"state": "INVALID"}
    actual_id = metadata.get("projectId")
    actual_number = str(metadata.get("projectNumber", ""))
    lifecycle = metadata.get("lifecycleState")
    if actual_id != project_id or actual_number != project_number:
        return {"state": "MISMATCH"}
    if lifecycle != "ACTIVE":
        return {"state": "INACTIVE", "lifecycle": lifecycle if isinstance(lifecycle, str) else "UNKNOWN"}
    return {"state": "READY", "project_id": actual_id, "project_number": actual_number}


def evaluate_enabled_apis(metadata: Any, required: tuple[str, ...]) -> dict[str, Any]:
    """Compare enabled API names with the fixed rollout requirement set."""
    if not isinstance(metadata, list) or not all(isinstance(item, dict) for item in metadata):
        return {"state": "INVALID", "missing": list(required)}
    enabled = {
        item.get("config", {}).get("name")
        for item in metadata
        if isinstance(item.get("config"), dict)
    }
    missing = sorted(set(required) - enabled)
    return {"state": "READY" if not missing else "MISSING", "missing": missing}


def evaluate_role_bindings(
    policy: Any,
    *,
    role: str,
    required_members: tuple[str, ...],
    allowed_members: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Fail closed on missing or unexpected unconditional IAM members."""
    allowed = set(required_members if allowed_members is None else allowed_members)
    required = set(required_members)
    if not isinstance(policy, dict) or not isinstance(policy.get("bindings", []), list):
        return {"state": "INVALID", "missing": sorted(required), "unexpected": []}
    members: set[str] = set()
    conditional = False
    for binding in policy.get("bindings", []):
        if not isinstance(binding, dict) or binding.get("role") != role:
            continue
        values = binding.get("members")
        if not isinstance(values, list) or not all(isinstance(member, str) for member in values):
            return {"state": "INVALID", "missing": sorted(required), "unexpected": []}
        if binding.get("condition") is not None:
            conditional = True
            continue
        members.update(values)
    missing = sorted(required - members)
    unexpected = sorted(members - allowed)
    state = "READY" if not missing and not unexpected and not conditional else "MISMATCH"
    return {"state": state, "missing": missing, "unexpected": unexpected, "conditional": conditional}


def evaluate_service_account(metadata: Any, *, expected_email: str) -> dict[str, Any]:
    """Require the exact enabled service-account identity."""
    if not isinstance(metadata, dict):
        return {"state": "INVALID"}
    email = metadata.get("email")
    name = metadata.get("name")
    expected_name = f"projects/-/serviceAccounts/{expected_email}"
    if email != expected_email or name != expected_name:
        return {"state": "MISMATCH"}
    if metadata.get("disabled") is True:
        return {"state": "DISABLED", "email": email}
    if metadata.get("disabled") not in (False, None):
        return {"state": "INVALID"}
    return {"state": "READY", "email": email}


def evaluate_artifact_repository(
    metadata: Any,
    *,
    project_id: str,
    region: str,
    repository: str,
) -> dict[str, Any]:
    """Require the fixed regional standard Docker repository."""
    if not isinstance(metadata, dict):
        return {"state": "INVALID"}
    expected_name = f"projects/{project_id}/locations/{region}/repositories/{repository}"
    fields = {
        "name": metadata.get("name"),
        "format": metadata.get("format"),
        "mode": metadata.get("mode", "STANDARD_REPOSITORY"),
    }
    if fields != {"name": expected_name, "format": "DOCKER", "mode": "STANDARD_REPOSITORY"}:
        return {"state": "MISMATCH"}
    return {"state": "READY", **fields}


def evaluate_pubsub_topic(metadata: Any, *, project_id: str, topic: str) -> dict[str, Any]:
    """Require a topic in the fixed rollout project."""
    if not isinstance(metadata, dict):
        return {"state": "INVALID"}
    if metadata.get("name") != f"projects/{project_id}/topics/{topic}":
        return {"state": "MISMATCH"}
    return {"state": "READY", "topic": topic}


def evaluate_pubsub_subscription(
    metadata: Any,
    *,
    project_id: str,
    topic: str,
    subscription: str,
    expected_mode: str,
    push_service_account: str,
) -> dict[str, Any]:
    """Verify topic attribution and pull/authenticated-push rollout mode."""
    if expected_mode not in {"pull", "push"} or not isinstance(metadata, dict):
        return {"state": "INVALID"}
    expected_name = f"projects/{project_id}/subscriptions/{subscription}"
    expected_topic = f"projects/{project_id}/topics/{topic}"
    deadline = metadata.get("ackDeadlineSeconds")
    if metadata.get("name") != expected_name or metadata.get("topic") != expected_topic:
        return {"state": "MISMATCH"}
    if type(deadline) is not int or not 10 <= deadline <= 600:
        return {"state": "MISMATCH"}
    push = metadata.get("pushConfig")
    if expected_mode == "pull":
        if push not in (None, {}):
            return {"state": "MISMATCH"}
    else:
        if not isinstance(push, dict):
            return {"state": "MISMATCH"}
        endpoint = push.get("pushEndpoint")
        token = push.get("oidcToken")
        try:
            parsed = urlsplit(endpoint)
            canonical_endpoint = (
                parsed.scheme == "https"
                and parsed.hostname is not None
                and parsed.hostname.endswith(".run.app")
                and parsed.path in ("", "/")
                and not parsed.query
                and not parsed.fragment
            )
        except (TypeError, ValueError):
            canonical_endpoint = False
        if (
            not canonical_endpoint
            or not isinstance(token, dict)
            or token.get("serviceAccountEmail") != push_service_account
            or token.get("audience") != endpoint
        ):
            return {"state": "MISMATCH"}
    return {"state": "READY", "mode": expected_mode, "ack_deadline_seconds": deadline}


def evaluate_protected_file(path: str | Path | None) -> dict[str, Any]:
    """Check credential-file metadata without opening or naming the file."""
    if path is None or not str(path):
        return {"state": "UNSET"}
    candidate = Path(path)
    try:
        metadata = candidate.lstat()
    except (OSError, ValueError, TypeError):
        return {"state": "MISSING"}
    if stat.S_ISLNK(metadata.st_mode):
        return {"state": "SYMLINK"}
    if not stat.S_ISREG(metadata.st_mode):
        return {"state": "NOT_REGULAR"}
    mode = stat.S_IMODE(metadata.st_mode)
    return {
        "state": "READY" if mode == 0o600 else "INSECURE_MODE",
        "mode": f"{mode:04o}",
    }


def _index_signature(index: dict[str, Any], *, ignore_name: bool) -> tuple:
    collection = index.get("collectionGroup")
    resource_name = index.get("name", "")
    if resource_name:
        match = re.fullmatch(r"projects/[^/]+/databases/[^/]+/collectionGroups/([^/]+)/indexes/[^/]+", resource_name)
        if not match or (collection and collection != match[1]):
            raise ValueError("invalid index resource name")
        collection = match[1]
    scope = index.get("queryScope")
    if not isinstance(collection, str) or not collection or scope not in ("COLLECTION", "COLLECTION_GROUP"):
        raise ValueError("index must declare a collection group and query scope")
    fields = index.get("fields")
    if not isinstance(fields, list) or not fields:
        raise ValueError("index must declare ordered fields")
    signature = []
    for field in fields:
        if not isinstance(field, dict) or not isinstance(field.get("fieldPath"), str) or not field["fieldPath"]:
            raise ValueError("invalid index field")
        modes = [mode for mode in ("order", "arrayConfig", "vectorConfig") if mode in field]
        if len(modes) != 1:
            raise ValueError("index field must have exactly one indexing mode")
        mode = modes[0]
        value = field[mode]
        if mode == "order" and value not in ("ASCENDING", "DESCENDING"):
            raise ValueError("invalid field order")
        if mode == "arrayConfig" and value != "CONTAINS":
            raise ValueError("invalid array indexing mode")
        if mode == "vectorConfig" and not isinstance(value, dict):
            raise ValueError("invalid vector indexing mode")
        if ignore_name and field["fieldPath"] == "__name__":
            continue
        signature.append((field["fieldPath"], mode, json.dumps(value, sort_keys=True)))
    if not signature:
        raise ValueError("index has no declared fields")
    return collection, scope, tuple(signature)


def evaluate_indexes(expected: list[dict], live: list[dict]) -> list[dict]:
    """Report each declared index, matching scope and ordered field semantics.

    Firestore adds an implicit document-name field to live metadata. Ignore it
    only when the declaration does not explicitly set its order. Unrelated
    READY indexes never satisfy a declaration, and malformed live records do
    not count as matches.
    """
    if not isinstance(expected, list) or not expected:
        raise ValueError("expected indexes must be a nonempty list")
    if not isinstance(live, list):
        raise ValueError("live indexes must be a list")
    results = []
    for declaration in expected:
        if not isinstance(declaration, dict):
            raise ValueError("invalid index declaration")
        signature = _index_signature(declaration, ignore_name=False)
        ignore_name = not any(field[0] == "__name__" for field in signature[2])
        states = set()
        for index in live:
            if not isinstance(index, dict):
                continue
            try:
                matches = _index_signature(index, ignore_name=ignore_name) == signature
            except (ValueError, TypeError):
                continue
            if matches:
                state = index.get("state")
                states.add(state if state in ("READY", "CREATING", "NEEDS_REPAIR", "ERROR") else "UNKNOWN")
        state = next((state for state in ("READY", "NEEDS_REPAIR", "ERROR", "CREATING", "UNKNOWN") if state in states), "MISSING")
        results.append({
            "collectionGroup": signature[0],
            "queryScope": signature[1],
            "fields": declaration["fields"],
            "state": state,
        })
    return results


def _version_id(name: Any) -> str | None:
    if not isinstance(name, str):
        return None
    match = re.fullmatch(r"(?:projects/[^/]+/secrets/[^/]+/versions/)?([1-9][0-9]*|latest)", name)
    return match[1] if match else None


def evaluate_secret_versions(versions: list[dict], required_version: str | None = None) -> dict:
    """Check enabled metadata without accessing secret payloads.

    With no pin, any enabled version is sufficient for foundation readiness.
    A numeric pin must itself be enabled. ``latest`` resolves to the largest
    version number, even if that version is disabled or destroyed.
    """
    if not isinstance(versions, list):
        raise ValueError("secret versions must be a list")
    required = _version_id(required_version) if required_version is not None else None
    if required_version is not None and required is None:
        raise ValueError("required secret version must be numeric or latest")
    states: dict[str, str] = {}
    for version in versions:
        if not isinstance(version, dict):
            continue
        number = _version_id(version.get("name"))
        if number is None or number == "latest":
            continue
        state = version.get("state")
        state = state if state in ("ENABLED", "DISABLED", "DESTROYED") else "UNKNOWN"
        if number in states and states[number] != state:
            state = "UNKNOWN"
        states[number] = state
    enabled = sorted((number for number, state in states.items() if state == "ENABLED"), key=int)
    if required == "latest":
        selected = max(states, key=int) if states else None
    elif required is not None:
        selected = required
    else:
        selected = enabled[-1] if enabled else (max(states, key=int) if states else None)
    return {
        "state": states.get(selected, "MISSING"),
        "version": selected,
        "enabled_versions": enabled,
    }
