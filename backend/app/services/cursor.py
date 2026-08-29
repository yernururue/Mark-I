"""Stable, opaque cursors used by Firestore-backed API pages."""

from __future__ import annotations

import base64
import json
from datetime import datetime, timezone

from app.errors import InvalidCursorError


def encode_cursor(created_at: datetime, document_id: str) -> str:
    payload = {
        "createdAt": created_at.astimezone(timezone.utc).isoformat(),
        "id": document_id,
    }
    return base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode()


def decode_cursor(cursor: str) -> tuple[datetime, str]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        payload = json.loads(raw)
        created_at = datetime.fromisoformat(payload["createdAt"].replace("Z", "+00:00"))
        document_id = payload["id"]
    except (KeyError, TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InvalidCursorError("Invalid pagination cursor") from exc
    if created_at.tzinfo is None or not isinstance(document_id, str) or not document_id:
        raise InvalidCursorError("Invalid pagination cursor")
    return created_at.astimezone(timezone.utc), document_id
