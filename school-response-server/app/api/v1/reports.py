"""app/api/v1/reports.py — Reports and analytics endpoints."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, get_current_user, require_teacher
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models.quiz import QuizSession, QuestionSet, Response, StudentScore
from app.models.student import Student
from app.schemas.common import APIResponse
from app.schemas.quiz import StudentScoreOut

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get(
    "/quiz-sessions/{session_id}/scores",
    response_model=APIResponse[List[StudentScoreOut]],
    summary="Quiz session scores",
    description="Get per-student scores for a completed quiz session.",
)
async def session_scores(
    school_id: int,
    session_id: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[List[StudentScoreOut]]:
    user.assert_school_access(school_id)
    _assert_session_in_school(await _get_session(db, session_id, school_id))

    result = await db.execute(
        select(StudentScore)
        .where(StudentScore.quiz_session_id == session_id)
        .order_by(StudentScore.score.desc())
    )
    scores = result.scalars().all()
    return APIResponse(data=[StudentScoreOut.model_validate(s) for s in scores])


@router.get(
    "/students/{student_id}/performance",
    response_model=APIResponse[dict],
    summary="Student performance history",
    description="Aggregate performance data for a single student across all quiz sessions.",
)
async def student_performance(
    school_id: int,
    student_id: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[dict]:
    user.assert_school_access(school_id)

    # Verify student belongs to this school
    stu_result = await db.execute(
        select(Student).where(and_(Student.id == student_id, Student.school_id == school_id))
    )
    student = stu_result.scalars().first()
    if not student:
        raise NotFoundError("Student", student_id)

    # Aggregate across all sessions
    scores_result = await db.execute(
        select(StudentScore).where(StudentScore.student_id == student_id)
    )
    scores = scores_result.scalars().all()

    sessions_count = len(scores)
    avg_pct = round(sum(s.percentage for s in scores) / sessions_count, 2) if sessions_count else 0.0
    total_correct = sum(s.correct_answers for s in scores)
    total_answered = sum(s.total_questions for s in scores)

    return APIResponse(data={
        "student_id": student_id,
        "student_code": student.student_code,
        "full_name": f"{student.first_name} {student.last_name}",
        "sessions_participated": sessions_count,
        "total_questions_answered": total_answered,
        "total_correct": total_correct,
        "average_percentage": avg_pct,
        "scores": [StudentScoreOut.model_validate(s) for s in scores],
    })


@router.get(
    "/quiz-sessions/{session_id}/summary",
    response_model=APIResponse[dict],
    summary="Quiz session summary",
    description="High-level summary: answer distribution, participation rate, top scorers.",
)
async def session_summary(
    school_id: int,
    session_id: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[dict]:
    user.assert_school_access(school_id)
    quiz = await _get_session(db, session_id, school_id)

    # Responses
    resp_result = await db.execute(
        select(Response).where(Response.quiz_session_id == session_id)
    )
    responses = resp_result.scalars().all()

    answer_counts = {"A": 0, "B": 0, "C": 0, "D": 0}
    correct_count = 0
    for r in responses:
        answer_counts[r.answer.value] += 1
        if r.is_correct:
            correct_count += 1

    # Scores
    scores_result = await db.execute(
        select(StudentScore)
        .where(StudentScore.quiz_session_id == session_id)
        .order_by(StudentScore.score.desc())
    )
    scores = scores_result.scalars().all()
    avg_pct = round(sum(s.percentage for s in scores) / len(scores), 2) if scores else 0.0

    return APIResponse(data={
        "quiz_session_id": session_id,
        "status": quiz.status.value,
        "started_at": quiz.started_at,
        "ended_at": quiz.ended_at,
        "total_responses": len(responses),
        "correct_responses": correct_count,
        "accuracy_rate": round(correct_count / len(responses) * 100, 1) if responses else 0.0,
        "answer_distribution": answer_counts,
        "students_participated": len(scores),
        "average_score_percentage": avg_pct,
        "top_scorers": [StudentScoreOut.model_validate(s) for s in scores[:5]],
    })


# ── Helpers ────────────────────────────────────────────────────────────────

async def _get_session(db: AsyncSession, session_id: int, school_id: int) -> QuizSession:
    result = await db.execute(
        select(QuizSession)
        .join(QuestionSet, QuizSession.question_set_id == QuestionSet.id)
        .where(and_(QuizSession.id == session_id, QuestionSet.school_id == school_id))
    )
    session = result.scalars().first()
    if not session:
        raise NotFoundError("QuizSession", session_id)
    return session


def _assert_session_in_school(session: QuizSession) -> None:
    pass  # enforced by join in _get_session
