"""Reusable OpenAPI response declarations for the canonical JSON error envelope."""

from __future__ import annotations

from app.models.common import ErrorResponse


def error_responses(*status_codes: int) -> dict[int, dict[str, object]]:
    """Declare documented error statuses without changing runtime behaviour."""
    descriptions = {
        400: "Invalid request",
        401: "Missing or invalid Firebase token",
        404: "Resource not found",
        409: "Resource already exists",
        422: "Invalid request body",
        503: "Service temporarily unavailable",
    }
    return {
        status_code: {
            "model": ErrorResponse,
            "description": descriptions.get(status_code, "Request failed"),
        }
        for status_code in status_codes
    }
