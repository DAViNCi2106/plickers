"""tests/test_auth.py — Authentication tests."""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import get_token


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, admin_user_a, school_a):
    resp = await client.post("/api/v1/auth/login", json={
        "username": "admin_a",
        "password": "Password@1",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "access_token" in data["data"]
    assert data["data"]["role"] == "SCHOOL_ADMIN"
    assert data["data"]["school_id"] == school_a.id


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, admin_user_a):
    resp = await client.post("/api/v1/auth/login", json={
        "username": "admin_a",
        "password": "WrongPassword!",
    })
    assert resp.status_code == 401
    assert resp.json()["success"] is False
    assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_login_unknown_user(client: AsyncClient):
    resp = await client.post("/api/v1/auth/login", json={
        "username": "ghost_user",
        "password": "AnyPassword@1",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_endpoint(client: AsyncClient, admin_user_a, school_a):
    token = await get_token(client, "admin_a", "Password@1")
    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["user_id"] == admin_user_a.id
    assert resp.json()["data"]["role"] == "SCHOOL_ADMIN"


@pytest.mark.asyncio
async def test_me_without_token(client: AsyncClient):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 403  # HTTPBearer returns 403 when no header


@pytest.mark.asyncio
async def test_me_invalid_token(client: AsyncClient):
    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer this.is.not.valid"},
    )
    assert resp.status_code == 401
