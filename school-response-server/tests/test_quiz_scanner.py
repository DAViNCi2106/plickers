"""
tests/test_quiz_scanner.py
==========================
Tests for quiz session lifecycle and scanner response submission.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.card import Card, StudentCard
from app.models.enums import (
    AnswerLetter, CardStatus, QuestionSetStatus,
    QuizSessionStatus, StudentStatus, UserRole,
)
from app.models.quiz import Question, QuestionSet, QuizSession
from app.models.school import AcademicYear, Class, School, Section
from app.models.student import Student
from app.models.user import User
from tests.conftest import get_token


async def _seed_quiz_env(db: AsyncSession, school):
    """Seed a minimal quiz environment and return all IDs."""
    ay = AcademicYear(school_id=school.id, name="2026-2027",
                      start_date=date(2026, 6, 1), end_date=date(2027, 3, 31))
    db.add(ay)
    await db.flush()

    cls = Class(school_id=school.id, academic_year_id=ay.id, name="Grade 10", grade="10")
    db.add(cls)
    await db.flush()

    section = Section(class_id=cls.id, name="A")
    db.add(section)
    await db.flush()

    teacher_user = User(
        school_id=school.id, username="quiz_teacher",
        email="qt@school.test", password_hash=hash_password("Password@1"),
        role=UserRole.TEACHER,
    )
    db.add(teacher_user)
    await db.flush()

    qs = QuestionSet(
        school_id=school.id, teacher_id=teacher_user.id,
        title="Test Quiz", status=QuestionSetStatus.PUBLISHED,
    )
    db.add(qs)
    await db.flush()

    q = Question(
        question_set_id=qs.id,
        question_text="What is 2+2?",
        option_a="3", option_b="4", option_c="5", option_d="6",
        correct_answer=AnswerLetter.B,
        marks=2,
    )
    db.add(q)
    await db.flush()

    student = Student(
        school_id=school.id, class_id=cls.id, section_id=section.id,
        student_code="STU099", first_name="Quiz", last_name="Student",
        status=StudentStatus.ACTIVE,
    )
    db.add(student)
    await db.flush()

    card = Card(school_id=school.id, card_number=99, marker_id=99, status=CardStatus.ASSIGNED)
    db.add(card)
    await db.flush()

    assignment = StudentCard(student_id=student.id, card_id=card.id)
    db.add(assignment)

    quiz = QuizSession(
        question_set_id=qs.id, teacher_id=teacher_user.id,
        class_id=cls.id, section_id=section.id,
        status=QuizSessionStatus.PENDING,
    )
    db.add(quiz)
    await db.flush()

    return {
        "teacher_username": "quiz_teacher",
        "question_id": q.id,
        "quiz_session_id": quiz.id,
        "student_id": student.id,
        "card_id": card.id,
    }


@pytest.mark.asyncio
async def test_quiz_session_lifecycle(client: AsyncClient, db: AsyncSession, school_a):
    env = await _seed_quiz_env(db, school_a)
    token = await get_token(client, env["teacher_username"], "Password@1")

    # Start session
    r = await client.post(
        f"/api/v1/schools/{school_a.id}/quiz-sessions/{env['quiz_session_id']}/start",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "active"

    # End session
    r = await client.post(
        f"/api/v1/schools/{school_a.id}/quiz-sessions/{env['quiz_session_id']}/end",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "ended"


@pytest.mark.asyncio
async def test_scanner_response_correct_answer(
    client: AsyncClient, db: AsyncSession, school_a
):
    env = await _seed_quiz_env(db, school_a)
    token = await get_token(client, env["teacher_username"], "Password@1")

    # Start the session first
    await client.post(
        f"/api/v1/schools/{school_a.id}/quiz-sessions/{env['quiz_session_id']}/start",
        headers={"Authorization": f"Bearer {token}"},
    )

    # Submit correct answer (B = marker rotation 90°)
    resp = await client.post(
        "/api/v1/scanner/responses",
        json={
            "quiz_session_id": env["quiz_session_id"],
            "question_id": env["question_id"],
            "marker_id": 99,
            "rotation": 90,
            "answer": "B",
            "detected_at": datetime.now(timezone.utc).isoformat(),
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["is_correct"] is True
    assert data["marks_obtained"] == 2
    assert data["student_id"] == env["student_id"]


@pytest.mark.asyncio
async def test_scanner_response_wrong_answer(
    client: AsyncClient, db: AsyncSession, school_a
):
    env = await _seed_quiz_env(db, school_a)
    token = await get_token(client, env["teacher_username"], "Password@1")

    await client.post(
        f"/api/v1/schools/{school_a.id}/quiz-sessions/{env['quiz_session_id']}/start",
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = await client.post(
        "/api/v1/scanner/responses",
        json={
            "quiz_session_id": env["quiz_session_id"],
            "question_id": env["question_id"],
            "marker_id": 99,
            "rotation": 0,
            "answer": "A",  # wrong (correct is B)
            "detected_at": datetime.now(timezone.utc).isoformat(),
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["is_correct"] is False
    assert resp.json()["marks_obtained"] == 0


@pytest.mark.asyncio
async def test_duplicate_response_rejected(
    client: AsyncClient, db: AsyncSession, school_a
):
    """Second submission for the same student/question/session must be rejected."""
    env = await _seed_quiz_env(db, school_a)
    token = await get_token(client, env["teacher_username"], "Password@1")

    await client.post(
        f"/api/v1/schools/{school_a.id}/quiz-sessions/{env['quiz_session_id']}/start",
        headers={"Authorization": f"Bearer {token}"},
    )

    payload = {
        "quiz_session_id": env["quiz_session_id"],
        "question_id": env["question_id"],
        "marker_id": 99,
        "rotation": 90,
        "answer": "B",
        "detected_at": datetime.now(timezone.utc).isoformat(),
    }

    r1 = await client.post(
        "/api/v1/scanner/responses", json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r1.status_code == 200

    # Second submission — must be rejected
    r2 = await client.post(
        "/api/v1/scanner/responses", json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 409
    assert r2.json()["error"]["code"] == "DUPLICATE_RESPONSE"


@pytest.mark.asyncio
async def test_scanner_response_inactive_session_rejected(
    client: AsyncClient, db: AsyncSession, school_a
):
    """Scanner must not accept responses for a PENDING or ENDED session."""
    env = await _seed_quiz_env(db, school_a)
    token = await get_token(client, env["teacher_username"], "Password@1")
    # Session is still PENDING — not started

    resp = await client.post(
        "/api/v1/scanner/responses",
        json={
            "quiz_session_id": env["quiz_session_id"],
            "question_id": env["question_id"],
            "marker_id": 99,
            "rotation": 90,
            "answer": "B",
            "detected_at": datetime.now(timezone.utc).isoformat(),
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "QUIZ_SESSION_NOT_ACTIVE"
