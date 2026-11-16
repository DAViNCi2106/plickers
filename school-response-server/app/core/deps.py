"""
app/core/deps.py
================
FastAPI dependency injection: database sessions, current user, RBAC.
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import Depends, Header, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ForbiddenError, TenantViolationError, UnauthorizedError
from app.core.security import decode_token
from app.db.session import get_db
from app.models.enums import UserRole

security = HTTPBearer()


# ── Current user ─────────────────────────────────────────────────────────────

async def get_current_user_payload(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Decode JWT and return the payload dict. Raises 401 on any failure."""
    try:
        payload = decode_token(credentials.credentials)
    except JWTError:
        raise UnauthorizedError("Invalid or expired token")
    if payload.get("type") != "access":
        raise UnauthorizedError("Wrong token type")
    return payload


class CurrentUser:
    """Parsed, validated user identity from a JWT token."""

    def __init__(self, payload: dict = Depends(get_current_user_payload)):
        self.user_id: int = int(payload["sub"])
        self.school_id: Optional[int] = payload.get("school_id")
        self.role: UserRole = UserRole(payload["role"])

    # ── Role checks ──────────────────────────────────────────────────────────

    def require_role(self, *roles: UserRole) -> "CurrentUser":
        if self.role not in roles:
            raise ForbiddenError()
        return self

    def is_super_admin(self) -> bool:
        return self.role == UserRole.SUPER_ADMIN

    def is_school_admin(self) -> bool:
        return self.role in (UserRole.SUPER_ADMIN, UserRole.SCHOOL_ADMIN)

    def is_teacher_or_above(self) -> bool:
        return self.role in (UserRole.SUPER_ADMIN, UserRole.SCHOOL_ADMIN, UserRole.TEACHER)

    # ── Tenant isolation ─────────────────────────────────────────────────────

    def assert_school_access(self, school_id: int) -> None:
        """Raise 403 if user is not a super-admin and tries to access another school."""
        if self.is_super_admin():
            return
        if self.school_id != school_id:
            raise TenantViolationError()


# ── Convenient typed dependencies ────────────────────────────────────────────

def get_current_user(payload: dict = Depends(get_current_user_payload)) -> CurrentUser:
    return CurrentUser(payload)


def require_super_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    return user.require_role(UserRole.SUPER_ADMIN)


def require_school_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    return user.require_role(UserRole.SUPER_ADMIN, UserRole.SCHOOL_ADMIN)


def require_teacher(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    return user.require_role(
        UserRole.SUPER_ADMIN, UserRole.SCHOOL_ADMIN, UserRole.TEACHER
    )
