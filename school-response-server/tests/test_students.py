"""tests/test_students.py — Student CRUD and import tests."""
from __future__ import annotations

import io
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import get_token


@pytest.mark.asyncio
async def test_create_student(client: AsyncClient, school_a, admin_user_a):
    token = await get_token(client, "admin_a", "Password@1")
    resp = await client.post(
        f"/api/v1/schools/{school_a.id}/students",
        json={
            "student_code": "STU001",
            "first_name": "Arun",
            "last_name": "Kumar",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["student_code"] == "STU001"
    assert data["first_name"] == "Arun"
    assert data["school_id"] == school_a.id


@pytest.mark.asyncio
async def test_create_duplicate_student(client: AsyncClient, school_a, admin_user_a):
    token = await get_token(client, "admin_a", "Password@1")
    payload = {"student_code": "STU002", "first_name": "Priya", "last_name": "Sharma"}
    # First creation
    r1 = await client.post(
        f"/api/v1/schools/{school_a.id}/students",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r1.status_code == 201

    # Duplicate
    r2 = await client.post(
        f"/api/v1/schools/{school_a.id}/students",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_list_students(client: AsyncClient, school_a, admin_user_a):
    token = await get_token(client, "admin_a", "Password@1")
    for i in range(3, 6):
        await client.post(
            f"/api/v1/schools/{school_a.id}/students",
            json={"student_code": f"STU{i:03d}", "first_name": f"Test{i}", "last_name": "Student"},
            headers={"Authorization": f"Bearer {token}"},
        )
    resp = await client.get(
        f"/api/v1/schools/{school_a.id}/students",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert len(resp.json()["data"]) >= 3


@pytest.mark.asyncio
async def test_student_invalid_code_format(client: AsyncClient, school_a, admin_user_a):
    token = await get_token(client, "admin_a", "Password@1")
    resp = await client.post(
        f"/api/v1/schools/{school_a.id}/students",
        json={"student_code": "BADFORMAT", "first_name": "Bad", "last_name": "Code"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422  # Pydantic regex validation failure


@pytest.mark.asyncio
async def test_import_students_csv(client: AsyncClient, school_a, admin_user_a):
    """Import students via CSV matching the existing Excel format."""
    token = await get_token(client, "admin_a", "Password@1")

    csv_content = (
        "S.No,Student Name,Student ID,Card ID\n"
        "1,Arun Kumar,STU010,10\n"
        "2,Priya Sharma,STU011,11\n"
        "3,Rahul Verma,STU012,12\n"
    )
    resp = await client.post(
        f"/api/v1/schools/{school_a.id}/students/import",
        files={"file": ("students.csv", csv_content.encode(), "text/csv")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    summary = resp.json()["data"]
    assert summary["total_records"] == 3
    assert summary["successful"] == 3
    assert summary["failed"] == 0


@pytest.mark.asyncio
async def test_import_duplicate_card_id(client: AsyncClient, school_a, admin_user_a):
    """CSV with duplicate Card IDs should report failures, not corrupt DB."""
    token = await get_token(client, "admin_a", "Password@1")

    csv_content = (
        "S.No,Student Name,Student ID,Card ID\n"
        "1,Valid Student,STU020,20\n"
        "2,Also Valid,STU021,20\n"  # duplicate Card ID
    )
    resp = await client.post(
        f"/api/v1/schools/{school_a.id}/students/import",
        files={"file": ("dup.csv", csv_content.encode(), "text/csv")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    summary = resp.json()["data"]
    assert summary["successful"] == 1
    assert summary["failed"] == 1
    assert any("Duplicate" in e["reason"] for e in summary["errors"])
