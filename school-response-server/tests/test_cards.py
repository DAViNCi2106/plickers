"""tests/test_cards.py — Card creation, assignment, and lookup tests."""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import get_token


async def _create_student(client, school_id, token, code="STU030", first="Test", last="Student"):
    r = await client.post(
        f"/api/v1/schools/{school_id}/students",
        json={"student_code": code, "first_name": first, "last_name": last},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text
    return r.json()["data"]["id"]


async def _create_card(client, school_id, token, card_number=30):
    r = await client.post(
        f"/api/v1/schools/{school_id}/cards",
        json={"card_number": card_number},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text
    return r.json()["data"]["id"]


@pytest.mark.asyncio
async def test_create_card(client: AsyncClient, school_a, admin_user_a):
    token = await get_token(client, "admin_a", "Password@1")
    resp = await client.post(
        f"/api/v1/schools/{school_a.id}/cards",
        json={"card_number": 42},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    # marker_id must equal card_number
    assert data["card_number"] == 42
    assert data["marker_id"] == 42
    assert data["school_id"] == school_a.id


@pytest.mark.asyncio
async def test_duplicate_card_marker_rejected(client: AsyncClient, school_a, admin_user_a):
    token = await get_token(client, "admin_a", "Password@1")
    await client.post(
        f"/api/v1/schools/{school_a.id}/cards",
        json={"card_number": 43},
        headers={"Authorization": f"Bearer {token}"},
    )
    r2 = await client.post(
        f"/api/v1/schools/{school_a.id}/cards",
        json={"card_number": 43},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_assign_card_to_student(client: AsyncClient, school_a, admin_user_a):
    token = await get_token(client, "admin_a", "Password@1")
    student_id = await _create_student(client, school_a.id, token, "STU031")
    card_id = await _create_card(client, school_a.id, token, 31)

    resp = await client.post(
        f"/api/v1/schools/{school_a.id}/cards/{card_id}/assign",
        json={"student_id": student_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["is_active"] is True


@pytest.mark.asyncio
async def test_assign_card_already_assigned(client: AsyncClient, school_a, admin_user_a):
    token = await get_token(client, "admin_a", "Password@1")
    s1 = await _create_student(client, school_a.id, token, "STU032", "Student", "One")
    s2 = await _create_student(client, school_a.id, token, "STU033", "Student", "Two")
    card_id = await _create_card(client, school_a.id, token, 32)

    await client.post(
        f"/api/v1/schools/{school_a.id}/cards/{card_id}/assign",
        json={"student_id": s1},
        headers={"Authorization": f"Bearer {token}"},
    )
    # Try assigning same card to second student
    r2 = await client.post(
        f"/api/v1/schools/{school_a.id}/cards/{card_id}/assign",
        json={"student_id": s2},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 409
    assert r2.json()["error"]["code"] == "CARD_ALREADY_ASSIGNED"


@pytest.mark.asyncio
async def test_search_card_by_marker_id(client: AsyncClient, school_a, admin_user_a):
    token = await get_token(client, "admin_a", "Password@1")
    student_id = await _create_student(client, school_a.id, token, "STU034", "Search", "Me")
    card_id = await _create_card(client, school_a.id, token, 34)
    await client.post(
        f"/api/v1/schools/{school_a.id}/cards/{card_id}/assign",
        json={"student_id": student_id},
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = await client.get(
        f"/api/v1/schools/{school_a.id}/cards/search?marker_id=34",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["card"]["marker_id"] == 34
    assert data["student_id"] == student_id
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_unassign_card(client: AsyncClient, school_a, admin_user_a):
    token = await get_token(client, "admin_a", "Password@1")
    student_id = await _create_student(client, school_a.id, token, "STU035", "Unassign", "Me")
    card_id = await _create_card(client, school_a.id, token, 35)
    await client.post(
        f"/api/v1/schools/{school_a.id}/cards/{card_id}/assign",
        json={"student_id": student_id},
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = await client.post(
        f"/api/v1/schools/{school_a.id}/cards/{card_id}/unassign",
        json={"reason": "Test unassign"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["is_active"] is False
