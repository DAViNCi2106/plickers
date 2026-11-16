"""
app/core/exceptions.py
======================
Centralised custom exception classes and HTTP error responses.
All errors use a consistent JSON envelope:

    {
      "success": false,
      "error": {
        "code": "CARD_NOT_ASSIGNED",
        "message": "The detected card is not currently assigned to a student."
      }
    }
"""
from __future__ import annotations

from fastapi import HTTPException, status


class PlickersException(HTTPException):
    """Base exception for all application-level errors."""

    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(status_code=status_code, detail={"code": code, "message": message})
        self.code = code
        self.message = message


# ── 400 Bad Request ──────────────────────────────────────────────────────────

class BadRequestError(PlickersException):
    def __init__(self, message: str, code: str = "BAD_REQUEST"):
        super().__init__(status.HTTP_400_BAD_REQUEST, code, message)


class ValidationError(PlickersException):
    def __init__(self, message: str):
        super().__init__(status.HTTP_422_UNPROCESSABLE_ENTITY, "VALIDATION_ERROR", message)


# ── 401 Unauthorized ─────────────────────────────────────────────────────────

class UnauthorizedError(PlickersException):
    def __init__(self, message: str = "Authentication required"):
        super().__init__(status.HTTP_401_UNAUTHORIZED, "UNAUTHORIZED", message)


class InvalidCredentialsError(PlickersException):
    def __init__(self):
        super().__init__(
            status.HTTP_401_UNAUTHORIZED,
            "INVALID_CREDENTIALS",
            "Invalid username or password",
        )


# ── 403 Forbidden ────────────────────────────────────────────────────────────

class ForbiddenError(PlickersException):
    def __init__(self, message: str = "You do not have permission to perform this action"):
        super().__init__(status.HTTP_403_FORBIDDEN, "FORBIDDEN", message)


class TenantViolationError(PlickersException):
    def __init__(self):
        super().__init__(
            status.HTTP_403_FORBIDDEN,
            "TENANT_VIOLATION",
            "Access to data from another school is not permitted",
        )


# ── 404 Not Found ────────────────────────────────────────────────────────────

class NotFoundError(PlickersException):
    def __init__(self, entity: str, identifier: str | int | None = None):
        msg = f"{entity} not found"
        if identifier is not None:
            msg = f"{entity} '{identifier}' not found"
        super().__init__(status.HTTP_404_NOT_FOUND, f"{entity.upper().replace(' ', '_')}_NOT_FOUND", msg)


# ── 409 Conflict ─────────────────────────────────────────────────────────────

class ConflictError(PlickersException):
    def __init__(self, message: str, code: str = "CONFLICT"):
        super().__init__(status.HTTP_409_CONFLICT, code, message)


class DuplicateError(ConflictError):
    def __init__(self, entity: str, field: str):
        super().__init__(
            f"{entity} with this {field} already exists",
            code=f"DUPLICATE_{entity.upper().replace(' ', '_')}",
        )


# ── Domain-specific errors ───────────────────────────────────────────────────

class CardNotAssignedError(PlickersException):
    def __init__(self):
        super().__init__(
            status.HTTP_404_NOT_FOUND,
            "CARD_NOT_ASSIGNED",
            "The detected card is not currently assigned to a student.",
        )


class CardAlreadyAssignedError(PlickersException):
    def __init__(self):
        super().__init__(
            status.HTTP_409_CONFLICT,
            "CARD_ALREADY_ASSIGNED",
            "This card is already actively assigned to a student.",
        )


class StudentAlreadyHasCardError(PlickersException):
    def __init__(self):
        super().__init__(
            status.HTTP_409_CONFLICT,
            "STUDENT_ALREADY_HAS_CARD",
            "This student already has an active card assignment.",
        )


class QuizSessionNotActiveError(PlickersException):
    def __init__(self):
        super().__init__(
            status.HTTP_409_CONFLICT,
            "QUIZ_SESSION_NOT_ACTIVE",
            "The quiz session is not currently active.",
        )


class DuplicateResponseError(PlickersException):
    def __init__(self):
        super().__init__(
            status.HTTP_409_CONFLICT,
            "DUPLICATE_RESPONSE",
            "A response for this student/question has already been recorded in this session.",
        )
