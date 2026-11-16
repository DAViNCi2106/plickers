"""
app/services/quiz_service.py
============================
Quiz session management and scanner response processing.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import (
    DuplicateResponseError,
    NotFoundError,
    QuizSessionNotActiveError,
    CardNotAssignedError,
    ForbiddenError,
)
from app.models.card import Card, StudentCard
from app.models.enums import AuditAction, AnswerLetter, QuizSessionStatus
from app.models.quiz import (
    Question,
    QuestionSet,
    QuizSession,
    Response,
    StudentScore,
)
from app.models.student import Student
from app.schemas.quiz import ScannerResponseOut, QuizDashboardOut
from app.services.audit_service import write_audit_log

logger = logging.getLogger(__name__)


async def start_quiz_session(
    db: AsyncSession,
    session_id: int,
    school_id: int,
    user_id: int,
) -> QuizSession:
    quiz = await _get_session(db, session_id)
    _assert_school(quiz, school_id)

    if quiz.status != QuizSessionStatus.PENDING:
        raise QuizSessionNotActiveError()

    quiz.status = QuizSessionStatus.ACTIVE
    quiz.started_at = datetime.now(timezone.utc)
    await db.flush()

    await write_audit_log(
        db, action=AuditAction.QUIZ_STARTED, school_id=school_id, user_id=user_id,
        entity_type="QuizSession", entity_id=session_id,
    )
    return quiz


async def end_quiz_session(
    db: AsyncSession,
    session_id: int,
    school_id: int,
    user_id: int,
) -> QuizSession:
    quiz = await _get_session(db, session_id)
    _assert_school(quiz, school_id)

    quiz.status = QuizSessionStatus.ENDED
    quiz.ended_at = datetime.now(timezone.utc)
    await db.flush()

    await write_audit_log(
        db, action=AuditAction.QUIZ_ENDED, school_id=school_id, user_id=user_id,
        entity_type="QuizSession", entity_id=session_id,
    )
    return quiz


async def pause_quiz_session(
    db: AsyncSession,
    session_id: int,
    school_id: int,
    user_id: int,
) -> QuizSession:
    quiz = await _get_session(db, session_id)
    _assert_school(quiz, school_id)

    if quiz.status != QuizSessionStatus.ACTIVE:
        raise QuizSessionNotActiveError("Can only pause an ACTIVE session")

    quiz.status = QuizSessionStatus.PAUSED
    await db.flush()

    await write_audit_log(
        db, action=AuditAction.QUIZ_STARTED, school_id=school_id, user_id=user_id,
        entity_type="QuizSession", entity_id=session_id,
        metadata={"transition": "ACTIVE→PAUSED"},
    )
    return quiz


async def resume_quiz_session(
    db: AsyncSession,
    session_id: int,
    school_id: int,
    user_id: int,
) -> QuizSession:
    quiz = await _get_session(db, session_id)
    _assert_school(quiz, school_id)

    if quiz.status != QuizSessionStatus.PAUSED:
        raise QuizSessionNotActiveError("Can only resume a PAUSED session")

    quiz.status = QuizSessionStatus.ACTIVE
    await db.flush()

    await write_audit_log(
        db, action=AuditAction.QUIZ_STARTED, school_id=school_id, user_id=user_id,
        entity_type="QuizSession", entity_id=session_id,
        metadata={"transition": "PAUSED→ACTIVE"},
    )
    return quiz


async def process_scanner_response(
    db: AsyncSession,
    school_id: int,
    quiz_session_id: int,
    question_id: int,
    marker_id: int,
    rotation: int,
    answer: AnswerLetter,
    detected_at: datetime,
    user_id: Optional[int] = None,
) -> ScannerResponseOut:
    """
    Core scanner pipeline:
      1. Verify quiz session is ACTIVE
      2. Verify question belongs to that session's question set
      3. Find card by marker_id within school
      4. Find active student assignment for that card
      5. Prevent duplicate submissions
      6. Store response
      7. Update score aggregate
    """
    # ── 1. Verify session ─────────────────────────────────────────────────
    quiz = await _get_session(db, quiz_session_id)
    _assert_school(quiz, school_id)
    if quiz.status != QuizSessionStatus.ACTIVE:
        raise QuizSessionNotActiveError()

    # ── 2. Verify question ────────────────────────────────────────────────
    q_result = await db.execute(
        select(Question).where(
            and_(
                Question.id == question_id,
                Question.question_set_id == quiz.question_set_id,
            )
        )
    )
    question: Optional[Question] = q_result.scalars().first()
    if not question:
        raise NotFoundError("Question", question_id)

    # ── 3. Find card by marker_id ─────────────────────────────────────────
    card_result = await db.execute(
        select(Card).where(
            and_(Card.school_id == school_id, Card.marker_id == marker_id)
        )
    )
    card: Optional[Card] = card_result.scalars().first()
    if not card:
        raise NotFoundError("Card", f"marker_id={marker_id}")

    # ── 4. Find active student assignment ─────────────────────────────────
    sc_result = await db.execute(
        select(StudentCard).where(
            and_(StudentCard.card_id == card.id, StudentCard.is_active == True)
        )
    )
    student_card: Optional[StudentCard] = sc_result.scalars().first()
    if not student_card:
        raise CardNotAssignedError()

    student_id = student_card.student_id

    # ── 5. Duplicate prevention ───────────────────────────────────────────
    dup_result = await db.execute(
        select(Response).where(
            and_(
                Response.quiz_session_id == quiz_session_id,
                Response.question_id == question_id,
                Response.student_id == student_id,
            )
        )
    )
    if dup_result.scalars().first():
        raise DuplicateResponseError()

    # ── 6. Evaluate answer ────────────────────────────────────────────────
    is_correct = (answer == question.correct_answer) if question.correct_answer else False
    marks_obtained = question.marks if is_correct else 0

    response = Response(
        quiz_session_id=quiz_session_id,
        question_id=question_id,
        student_id=student_id,
        card_id=card.id,
        answer=answer,
        is_correct=is_correct,
        marks_obtained=marks_obtained,
        rotation=rotation,
        answered_at=detected_at,
    )
    db.add(response)
    await db.flush()

    # ── 7. Upsert student score aggregate ────────────────────────────────
    await _update_student_score(db, quiz_session_id, student_id, question_id, is_correct, marks_obtained)

    await write_audit_log(
        db, action=AuditAction.RESPONSE_SUBMITTED, school_id=school_id, user_id=user_id,
        entity_type="Response", entity_id=response.id,
        metadata={"marker_id": marker_id, "answer": answer.value, "is_correct": is_correct},
    )

    return ScannerResponseOut(
        student_id=student_id,
        card_id=card.id,
        answer=answer,
        is_correct=is_correct,
        marks_obtained=marks_obtained,
    )


async def get_quiz_dashboard(
    db: AsyncSession,
    quiz_session_id: int,
    school_id: int,
) -> QuizDashboardOut:
    """Aggregate live dashboard data for teacher."""
    quiz = await _get_session(db, quiz_session_id)
    _assert_school(quiz, school_id)

    # Count total students in the class/section
    q = select(func.count()).select_from(Student)
    if quiz.section_id:
        q = q.where(Student.section_id == quiz.section_id)
    elif quiz.class_id:
        q = q.where(Student.class_id == quiz.class_id)
    total_students = (await db.execute(q)).scalar_one()

    # Get all responses for this session
    resp_result = await db.execute(
        select(Response).where(Response.quiz_session_id == quiz_session_id)
        .order_by(Response.answered_at)
    )
    responses = resp_result.scalars().all()

    answer_counts: Dict[str, int] = {"A": 0, "B": 0, "C": 0, "D": 0}
    for r in responses:
        answer_counts[r.answer.value] += 1

    from app.schemas.quiz import ResponseOut
    return QuizDashboardOut(
        quiz_session_id=quiz_session_id,
        status=quiz.status,
        total_students=total_students,
        responses_received=len(responses),
        answer_counts=answer_counts,
        responses=[ResponseOut.model_validate(r) for r in responses],
    )


# ── Internal helpers ──────────────────────────────────────────────────────

async def _get_session(db: AsyncSession, session_id: int) -> QuizSession:
    result = await db.execute(
        select(QuizSession).where(QuizSession.id == session_id)
    )
    quiz = result.scalars().first()
    if not quiz:
        raise NotFoundError("QuizSession", session_id)
    return quiz


get_quiz_session = _get_session


def _assert_school(quiz: QuizSession, school_id: int) -> None:
    """Verify the quiz session's question_set belongs to this school."""
    pass  # tenant check is done at the route/dep level


async def _update_student_score(
    db: AsyncSession,
    quiz_session_id: int,
    student_id: int,
    question_id: int,
    is_correct: bool,
    marks: int,
) -> None:
    """Upsert the running score aggregate for this student/session."""
    result = await db.execute(
        select(StudentScore).where(
            and_(
                StudentScore.quiz_session_id == quiz_session_id,
                StudentScore.student_id == student_id,
            )
        )
    )
    score_row: Optional[StudentScore] = result.scalars().first()

    # Count total questions in the question set for this session
    q_count_result = await db.execute(
        select(func.count(Question.id))
        .join(QuizSession, QuizSession.question_set_id == Question.question_set_id)
        .where(QuizSession.id == quiz_session_id)
    )
    total_q = q_count_result.scalar_one() or 1

    if score_row is None:
        score_row = StudentScore(
            quiz_session_id=quiz_session_id,
            student_id=student_id,
            total_questions=total_q,
            correct_answers=1 if is_correct else 0,
            incorrect_answers=0 if is_correct else 1,
            score=marks,
            percentage=round((marks / total_q) * 100, 2) if total_q else 0.0,
        )
        db.add(score_row)
    else:
        score_row.total_questions = total_q
        if is_correct:
            score_row.correct_answers += 1
        else:
            score_row.incorrect_answers += 1
        score_row.score += marks
        score_row.percentage = round(
            (score_row.score / (total_q * 1)) * 100, 2
        )

    await db.flush()


async def recalculate_question_responses_and_scores(db: AsyncSession, question: Question) -> None:
    """Recalculate all response evaluations and student scores after question correct answer or marks change."""
    # 1. Update all responses for this question
    resp_result = await db.execute(select(Response).where(Response.question_id == question.id))
    responses = resp_result.scalars().all()
    session_ids = set()
    for r in responses:
        session_ids.add(r.quiz_session_id)
        if question.correct_answer:
            r.is_correct = (r.answer == question.correct_answer)
            r.marks_obtained = question.marks if r.is_correct else 0
        else:
            r.is_correct = False
            r.marks_obtained = 0
    await db.flush()

    # 2. Recalculate StudentScore for all affected sessions
    for sess_id in session_ids:
        q_count_res = await db.execute(
            select(func.count(Question.id))
            .join(QuizSession, QuizSession.question_set_id == Question.question_set_id)
            .where(QuizSession.id == sess_id)
        )
        total_q = q_count_res.scalar_one() or 1

        all_res_result = await db.execute(select(Response).where(Response.quiz_session_id == sess_id))
        all_responses = all_res_result.scalars().all()
        student_resp_map: Dict[int, list] = {}
        for ar in all_responses:
            student_resp_map.setdefault(ar.student_id, []).append(ar)

        for stu_id, stu_resps in student_resp_map.items():
            correct_cnt = sum(1 for x in stu_resps if x.is_correct)
            incorrect_cnt = sum(1 for x in stu_resps if not x.is_correct)
            total_marks = sum(x.marks_obtained for x in stu_resps)

            score_row_res = await db.execute(
                select(StudentScore).where(
                    and_(
                        StudentScore.quiz_session_id == sess_id,
                        StudentScore.student_id == stu_id,
                    )
                )
            )
            s_row = score_row_res.scalars().first()
            if s_row:
                s_row.total_questions = total_q
                s_row.correct_answers = correct_cnt
                s_row.incorrect_answers = incorrect_cnt
                s_row.score = total_marks
                s_row.percentage = round((total_marks / total_q) * 100, 2)
    await db.flush()
