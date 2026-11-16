"""
app/services/auth_service.py
============================
Authentication business logic: login, token creation, password change.
"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import InvalidCredentialsError, UnauthorizedError, BadRequestError
from app.core.security import create_access_token, create_refresh_token, decode_token, hash_password, verify_password
from app.models.audit import AuditLog
from app.models.enums import AuditAction
from app.models.user import User
from app.schemas.auth import TokenResponse
from app.services.audit_service import write_audit_log

logger = logging.getLogger(__name__)


async def authenticate_user(
    db: AsyncSession,
    username: str,
    password: str,
    ip_address: Optional[str] = None,
) -> TokenResponse:
    """
    Verify credentials and return a JWT access token.
    Logs both successful and failed login attempts.
    """
    # Look up user — search by username or email
    from sqlalchemy import or_
    result = await db.execute(
        select(User).where(
            or_(User.username == username, User.email == username),
            User.is_active == True,
        )
    )
    user: Optional[User] = result.scalars().first()

    if not user or not verify_password(password, user.password_hash):
        # Log failed attempt — no sensitive data in metadata
        await write_audit_log(
            db,
            action=AuditAction.USER_LOGIN_FAILED,
            ip_address=ip_address,
            metadata={"attempted_username": username[:50]},
        )
        raise InvalidCredentialsError()

    # Build token claims — role determined from DB, never from request
    token = create_access_token(
        subject=user.id,
        extra_claims={
            "role": user.role.value,
            "school_id": user.school_id,
        },
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    await write_audit_log(
        db,
        action=AuditAction.USER_LOGIN,
        school_id=user.school_id,
        user_id=user.id,
        entity_type="User",
        entity_id=user.id,
        ip_address=ip_address,
    )

    return TokenResponse(
        access_token=token,
        refresh_token=create_refresh_token(
            subject=user.id,
            extra_claims={"role": user.role.value, "school_id": user.school_id},
        ),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=user.id,
        role=user.role.value,
        school_id=user.school_id,
    )


async def refresh_access_token(
    db: AsyncSession,
    refresh_token: str,
) -> TokenResponse:
    """
    Exchange a valid refresh token for a new access + refresh token pair.
    The refresh token must have type='refresh' and be signed by us.
    """
    from jose import JWTError

    try:
        payload = decode_token(refresh_token)
    except JWTError:
        raise UnauthorizedError("Invalid or expired refresh token")

    if payload.get("type") != "refresh":
        raise UnauthorizedError("Not a refresh token")

    user_id = int(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))
    user: Optional[User] = result.scalars().first()
    if not user:
        raise UnauthorizedError("User not found or inactive")

    new_access = create_access_token(
        subject=user.id,
        extra_claims={"role": user.role.value, "school_id": user.school_id},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    new_refresh = create_refresh_token(
        subject=user.id,
        extra_claims={"role": user.role.value, "school_id": user.school_id},
    )

    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=user.id,
        role=user.role.value,
        school_id=user.school_id,
    )


async def change_password(
    db: AsyncSession,
    user_id: int,
    current_password: str,
    new_password: str,
) -> None:
    """
    Change a user's password after verifying the current one.
    The new hash replaces the old; no plain text is ever logged.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user: Optional[User] = result.scalars().first()
    if not user:
        raise UnauthorizedError("User not found")

    if not verify_password(current_password, user.password_hash):
        raise BadRequestError("Current password is incorrect", "INCORRECT_PASSWORD")

    user.password_hash = hash_password(new_password)
    await db.flush()
