"""app/api/v1/auth.py — Authentication endpoints."""
from fastapi import APIRouter, Body, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, CurrentUser
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
)
from app.schemas.common import APIResponse
from app.services.auth_service import authenticate_user, change_password, refresh_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=APIResponse[TokenResponse],
    summary="Login",
    description=(
        "Authenticate with username + password. Returns a JWT access token and a refresh token. "
        "Rate-limited to 10 requests/minute per IP."
    ),
    responses={
        200: {"description": "Login successful"},
        401: {"description": "Invalid credentials"},
        429: {"description": "Too many login attempts"},
    },
)
@limiter.limit("10/minute")
async def login(
    request: Request,
    body: LoginRequest = Body(...),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[TokenResponse]:
    ip = request.client.host if request.client else None
    token_data = await authenticate_user(db, body.username, body.password, ip_address=ip)
    return APIResponse(data=token_data, message="Login successful")


@router.post(
    "/refresh",
    response_model=APIResponse[TokenResponse],
    summary="Refresh access token",
    description=(
        "Exchange a valid refresh token for a new access token + refresh token pair. "
        "Refresh tokens expire after the configured REFRESH_TOKEN_EXPIRE_DAYS."
    ),
    responses={
        200: {"description": "Token refreshed"},
        401: {"description": "Invalid or expired refresh token"},
    },
)
async def refresh(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[TokenResponse]:
    token_data = await refresh_access_token(db, body.refresh_token)
    return APIResponse(data=token_data, message="Token refreshed")


@router.get(
    "/me",
    response_model=APIResponse[dict],
    summary="Current user info",
    description="Return the identity of the currently authenticated user.",
)
async def me(current_user: CurrentUser = Depends(get_current_user)) -> APIResponse[dict]:
    return APIResponse(data={
        "user_id": current_user.user_id,
        "school_id": current_user.school_id,
        "role": current_user.role.value,
    })


@router.post(
    "/change-password",
    response_model=APIResponse[None],
    summary="Change password",
    description=(
        "Change the authenticated user's password. "
        "Requires the current password for verification. "
        "Passwords are stored as Argon2id hashes — plain text is never persisted."
    ),
    responses={
        200: {"description": "Password changed successfully"},
        400: {"description": "Current password is incorrect"},
        401: {"description": "Authentication required"},
    },
)
async def change_password_endpoint(
    body: ChangePasswordRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[None]:
    await change_password(
        db,
        user_id=current_user.user_id,
        current_password=body.current_password,
        new_password=body.new_password,
    )
    return APIResponse(message="Password changed successfully")
