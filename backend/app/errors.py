"""Domain errors and the documented API error envelope."""

from __future__ import annotations


class DomainError(Exception):
    status_code = 400
    code = "BAD_REQUEST"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    status_code = 404
    code = "NOT_FOUND"


class ConflictError(DomainError):
    status_code = 409
    code = "CONFLICT"


class InvalidCursorError(DomainError):
    status_code = 422
    code = "VALIDATION_ERROR"


class ExternalServiceError(DomainError):
    status_code = 502
    code = "EXTERNAL_SERVICE_ERROR"
