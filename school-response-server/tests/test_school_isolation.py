"""
tests/test_school_isolation.py
===============================
CRITICAL: Verifies that School A's users cannot access School B's data.
This is the primary tenant-isolation security test.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import UserRole
from app.models.user import User
from app.core.security import hash_password
from tests.conftest import get_token


@pytest.mark.asyncio
async def test_school_a_admin_cannot_list_school_b_students(
    client: AsyncClient, db: AsyncSession, school_a, school_b, admin_user_a
):
    """School A admin must get 403 when requesting School B students."""
    # Create an admin for school B
    user_b = User(
        school_id=school_b.id,
        username="admin_b",
        email="admin@schoolb.test",
        password_hash=hash_password("Password@1"),
        role=UserRole.SCHOOL_ADMIN,
    )
    db.add(user_b)
    await db.flush()

    token_a = await get_token(client, "admin_a", "Password@1")

    # School A admin tries to access School B's student list
    resp = await client.get(
        f"/api/v1/schools/{school_b.id}/students",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "TENANT_VIOLATION"


@pytest.mark.asyncio
async def test_school_a_admin_cannot_create_student_in_school_b(
    client: AsyncClient, db: AsyncSession, school_a, school_b, admin_user_a
):
    """School A admin must get 403 when creating a student in School B."""
    token_a = await get_token(client, "admin_a", "Password@1")

    resp = await client.post(
        f"/api/v1/schools/{school_b.id}/students",
        json={"student_code": "STU001", "first_name": "Hacker", "last_name": "Attempt"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_school_a_admin_cannot_create_card_in_school_b(
    client: AsyncClient, school_a, school_b, admin_user_a
):
    """School A admin must get 403 when creating a card in School B."""
    token_a = await get_token(client, "admin_a", "Password@1")

    resp = await client.post(
        f"/api/v1/schools/{school_b.id}/cards",
        json={"card_number": 1},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_same_marker_id_allowed_in_different_schools(
    client: AsyncClient, db: AsyncSession, school_a, school_b, admin_user_a
):
    """Two different schools may have cards with the same marker_id."""
    # Create admin for School B
    user_b = User(
        school_id=school_b.id,
        username="admin_b2",
        email="admin2@schoolb.test",
        password_hash=hash_password("Password@1"),
        role=UserRole.SCHOOL_ADMIN,
    )
    db.add(user_b)
    await db.flush()

    token_a = await get_token(client, "admin_a", "Password@1")
    token_b = await get_token(client, "admin_b2", "Password@1")

    # School A creates card with marker_id=99
    r_a = await client.post(
        f"/api/v1/schools/{school_a.id}/cards",
        json={"card_number": 99},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert r_a.status_code == 201

    # School B can also create a card with marker_id=99 — different tenant
    r_b = await client.post(
        f"/api/v1/schools/{school_b.id}/cards",
        json={"card_number": 99},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert r_b.status_code == 201


@pytest.mark.asyncio
async def test_super_admin_can_access_any_school(
    client: AsyncClient, school_a, school_b, super_admin
):
    """SUPER_ADMIN must be able to access data in any school."""
    token = await get_token(client, "superadmin", "SuperPass@1")

    for school in [school_a, school_b]:
        resp = await client.get(
            f"/api/v1/schools/{school.id}/students",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, f"Super admin blocked from school {school.id}"
