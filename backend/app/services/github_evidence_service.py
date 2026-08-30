"""Bounded, redacted GitHub code evidence for proficiency assessment."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import re
from typing import Any, Literal

import httpx
from google.api_core.exceptions import NotFound as GoogleNotFound

from app.models.github import GitHubEventEnvelope


MAX_EVIDENCE_FILES = 50
MAX_EVIDENCE_BYTES = 60_000
MAX_PATCH_BYTES_PER_FILE = 12_000


class GitHubEvidenceRetryableError(RuntimeError):
    """A transient GitHub API failure should retry the Pub/Sub delivery."""


@dataclass(frozen=True)
class GitHubEvidence:
    text: str
    supports_proficiency: bool
    file_count: int
    truncated: bool
    omission_reason: str | None = None


_EXCLUDED_PATH_PARTS = frozenset(
    {
        "node_modules",
        "vendor",
        "vendors",
        "dist",
        "build",
        ".next",
        "coverage",
    }
)
_EXCLUDED_FILENAMES = frozenset(
    {
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "poetry.lock",
        "cargo.lock",
    }
)
_EXCLUDED_SUFFIXES = (
    ".min.js",
    ".min.css",
    ".map",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".pdf",
    ".zip",
    ".gz",
    ".woff",
    ".woff2",
)
_SENSITIVE_LINE = re.compile(
    r"(?i)(password|passwd|secret|api[_-]?key|access[_-]?token|private[_-]?key)\s*[:=]"
)
_TOKEN_VALUE = re.compile(
    r"(?i)(gh[pousr]_[a-z0-9]{20,}|github_pat_[a-z0-9_]{20,}|bearer\s+[a-z0-9._~+/-]{16,})"
)
_PRIVATE_KEY = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")


def _is_excluded_file(filename: str) -> bool:
    normalized = filename.replace("\\", "/").casefold()
    parts = set(normalized.split("/"))
    return (
        bool(parts & _EXCLUDED_PATH_PARTS)
        or normalized.rsplit("/", 1)[-1] in _EXCLUDED_FILENAMES
        or normalized.endswith(_EXCLUDED_SUFFIXES)
    )


def _redact_patch(patch: str) -> str:
    redacted: list[str] = []
    private_key = False
    for line in patch.splitlines():
        if _PRIVATE_KEY.search(line):
            private_key = True
            redacted.append("[REDACTED PRIVATE KEY]")
            continue
        if private_key:
            if "-----END " in line and "PRIVATE KEY-----" in line:
                private_key = False
            continue
        if _SENSITIVE_LINE.search(line):
            prefix = line[:1] if line[:1] in {"+", "-", " "} else ""
            redacted.append(f"{prefix}[REDACTED SENSITIVE LINE]")
            continue
        redacted.append(_TOKEN_VALUE.sub("[REDACTED TOKEN]", line))
    return "\n".join(redacted)


class GitHubEvidenceService:
    """Fetch code-bearing patches without placing OAuth tokens in event payloads."""

    def __init__(
        self,
        httpx_client: httpx.AsyncClient,
        token_provider: Callable[[str], str],
        *,
        max_files: int = MAX_EVIDENCE_FILES,
        max_bytes: int = MAX_EVIDENCE_BYTES,
        max_patch_bytes: int = MAX_PATCH_BYTES_PER_FILE,
    ) -> None:
        self._httpx = httpx_client
        self._token_provider = token_provider
        self._max_files = max_files
        self._max_bytes = max_bytes
        self._max_patch_bytes = max_patch_bytes

    async def collect(self, envelope: GitHubEventEnvelope) -> GitHubEvidence:
        endpoint_kind = self._endpoint(envelope)
        if endpoint_kind is None:
            return GitHubEvidence("", False, 0, False, "event_has_no_code_evidence")
        endpoint, response_shape = endpoint_kind
        try:
            token = self._token_provider(envelope.uid)
        except GoogleNotFound:
            return GitHubEvidence("", False, 0, False, "github_token_not_found")
        except Exception as exc:
            raise GitHubEvidenceRetryableError("GitHub token provider is unavailable") from exc
        if not isinstance(token, str) or not token:
            return GitHubEvidence("", False, 0, False, "github_token_not_found")
        try:
            response = await self._httpx.get(
                endpoint,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise GitHubEvidenceRetryableError("GitHub evidence request failed") from exc
        if response.status_code == 429 or response.status_code >= 500:
            raise GitHubEvidenceRetryableError(f"GitHub evidence returned {response.status_code}")
        if response.status_code == 403 and response.headers.get("X-RateLimit-Remaining") == "0":
            raise GitHubEvidenceRetryableError("GitHub evidence rate limit exhausted")
        if response.status_code != 200:
            return GitHubEvidence("", False, 0, False, f"github_http_{response.status_code}")

        try:
            payload = response.json()
        except (TypeError, ValueError):
            return GitHubEvidence("", False, 0, False, "invalid_github_response")
        files = payload.get("files") if response_shape == "object" and isinstance(payload, dict) else payload
        if not isinstance(files, list):
            return GitHubEvidence("", False, 0, False, "invalid_github_response")
        return self._render_files(files)

    @staticmethod
    def _endpoint(envelope: GitHubEventEnvelope) -> tuple[str, Literal["object", "list"]] | None:
        repo = envelope.repoFullName
        payload = envelope.payload
        if envelope.eventType == "push":
            before, after = payload.get("before"), payload.get("after")
            if isinstance(before, str) and before and isinstance(after, str) and after:
                return f"https://api.github.com/repos/{repo}/compare/{before}...{after}", "object"
            return None
        if envelope.eventType in {"pull_request", "pull_request_review"}:
            pr = payload.get("pull_request") or {}
            number = payload.get("number") or pr.get("number")
            if isinstance(number, int) and number > 0:
                return f"https://api.github.com/repos/{repo}/pulls/{number}/files?per_page=100", "list"
        return None

    def _render_files(self, files: list[Any]) -> GitHubEvidence:
        sections: list[str] = []
        total_bytes = 0
        considered = 0
        truncated = len(files) > self._max_files
        for item in files[: self._max_files]:
            if not isinstance(item, dict):
                continue
            filename = item.get("filename")
            patch = item.get("patch")
            if not isinstance(filename, str) or not isinstance(patch, str) or not patch.strip():
                continue
            if _is_excluded_file(filename):
                continue
            considered += 1
            raw_patch = patch.encode("utf-8")
            if len(raw_patch) > self._max_patch_bytes:
                suffix = b"\n[PATCH TRUNCATED]"
                allowed = max(0, self._max_patch_bytes - len(suffix))
                patch = raw_patch[:allowed].decode("utf-8", errors="ignore") + suffix.decode()
                truncated = True
            section = f"File: {filename}\n{_redact_patch(patch)}"
            section_bytes = section.encode("utf-8")
            remaining = self._max_bytes - total_bytes
            if remaining <= 0:
                truncated = True
                break
            if len(section_bytes) > remaining:
                suffix = b"\n[EVIDENCE TRUNCATED]"
                allowed = max(0, remaining - len(suffix))
                section = section_bytes[:allowed].decode("utf-8", errors="ignore") + suffix[:remaining].decode(
                    "utf-8", errors="ignore"
                )
                truncated = True
            sections.append(section)
            total_bytes += len(section.encode("utf-8"))
            if total_bytes >= self._max_bytes:
                break
        if not sections:
            return GitHubEvidence("", False, considered, truncated, "no_usable_patch")
        return GitHubEvidence("\n\n".join(sections), True, considered, truncated)
