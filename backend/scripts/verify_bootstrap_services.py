#!/usr/bin/env python3
"""Read-only, fail-closed health and access gate for the three rollout services."""

from __future__ import annotations

import json
import subprocess
import urllib.error
import urllib.parse
import urllib.request

PROJECT_ID = "mark-i-506218"
REGION = "us-central1"
SERVICES = (("mark-i-api", False), ("mark-i-github-worker", True), ("mark-i-opportunity-worker", True))
COMMAND_TIMEOUT_SECONDS = 30
HTTP_TIMEOUT_SECONDS = 15
MAX_HEALTH_BYTES = 16_384
STATUS_FORMAT = "json(status.url,status.conditions,status.latestCreatedRevisionName,status.latestReadyRevisionName,status.traffic)"


class GateFailure(Exception):
    """Carries only a fixed, sanitized diagnostic suitable for build logs."""


def run_gcloud(*args: str) -> str:
    try:
        result = subprocess.run(
            ("gcloud", *args, f"--project={PROJECT_ID}", "--quiet"),
            check=False,
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError, UnicodeError):
        raise GateFailure("gcloud command could not complete") from None
    if result.returncode:
        raise GateFailure("gcloud command failed")
    return result.stdout


def service_url(service: str) -> str:
    raw = run_gcloud("run", "services", "describe", service, f"--region={REGION}", f"--format={STATUS_FORMAT}")
    try:
        document = json.loads(raw)
    except (ValueError, TypeError):
        raise GateFailure("service metadata is invalid JSON") from None
    status = document.get("status") if isinstance(document, dict) else None
    if not isinstance(status, dict):
        raise GateFailure("service status is missing")
    conditions = status.get("conditions")
    if not isinstance(conditions, list):
        raise GateFailure("service readiness is missing")
    ready = [item for item in conditions if isinstance(item, dict) and item.get("type") == "Ready"]
    if len(ready) != 1 or ready[0].get("status") != "True":
        raise GateFailure("service is not Ready")
    revision = status.get("latestReadyRevisionName")
    if not isinstance(revision, str) or not revision or status.get("latestCreatedRevisionName") != revision:
        raise GateFailure("latest created revision is not ready")
    traffic = status.get("traffic")
    if not isinstance(traffic, list) or not traffic:
        raise GateFailure("revision traffic is missing")
    total = 0
    for target in traffic:
        if not isinstance(target, dict):
            raise GateFailure("revision traffic is malformed")
        percent = target.get("percent", 0)
        if type(percent) is not int or not 0 <= percent <= 100:
            raise GateFailure("revision traffic is malformed")
        if percent and target.get("revisionName") != revision:
            raise GateFailure("traffic targets an older revision")
        total += percent
    if total != 100:
        raise GateFailure("latest ready revision does not receive all traffic")
    url = status.get("url")
    if not isinstance(url, str):
        raise GateFailure("service URL is missing")
    try:
        parsed = urllib.parse.urlsplit(url)
        valid = (
            parsed.scheme == "https"
            and parsed.hostname is not None
            and parsed.hostname.startswith(f"{service}-")
            and parsed.hostname.endswith(".run.app")
            and parsed.netloc == parsed.hostname
            and parsed.path in ("", "/")
            and not parsed.query
            and not parsed.fragment
        )
    except ValueError:
        valid = False
    if not valid:
        raise GateFailure("service URL is not a canonical HTTPS Cloud Run URL")
    return url.rstrip("/")


class NoRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # A redirect must never forward the worker's bearer token to another host.
        return None


def request_health(url: str, token: str | None = None) -> tuple[int, bytes]:
    headers = {"Accept": "application/json"}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(f"{url}/health", headers=headers)
    try:
        with urllib.request.build_opener(NoRedirects()).open(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
            body = response.read(MAX_HEALTH_BYTES + 1)
            if len(body) > MAX_HEALTH_BYTES:
                raise GateFailure("health response exceeds size limit")
            return response.status, body
    except urllib.error.HTTPError as error:
        status = error.code
        error.close()
        return status, b""
    except (OSError, ValueError, urllib.error.URLError):
        raise GateFailure("health request could not complete") from None


def require_healthy(url: str, token: str | None = None) -> None:
    status, body = request_health(url, token)
    if status != 200:
        raise GateFailure("health endpoint did not return HTTP 200")
    try:
        health = json.loads(body)
    except (ValueError, UnicodeError):
        raise GateFailure("health endpoint returned invalid JSON") from None
    if not isinstance(health, dict) or health.get("status") != "ok":
        raise GateFailure("health endpoint did not report status ok")


def verify_service(service: str, private: bool) -> None:
    url = service_url(service)
    if private:
        status, _ = request_health(url)
        if status not in (401, 403):
            raise GateFailure("worker did not reject anonymous access")
        token = run_gcloud("auth", "print-identity-token", f"--audiences={url}").strip()
        if not token or any(character.isspace() or ord(character) < 32 for character in token):
            raise GateFailure("identity token is missing or malformed")
        require_healthy(url, token)
    else:
        require_healthy(url)


def main() -> int:
    for service, private in SERVICES:
        try:
            verify_service(service, private)
        except GateFailure as error:
            print(f"bootstrap-services: FAIL: {service}: {error}")
            return 1
        print(f"bootstrap-services: PASS: {service} ({'private' if private else 'public'})")
    print("bootstrap-services: PASS: all latest revisions are healthy and receive 100% traffic")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
