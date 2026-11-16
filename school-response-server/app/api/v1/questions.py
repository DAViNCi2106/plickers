"""app/api/v1/questions.py — QuestionSet and Question endpoints."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, get_current_user, require_teacher
from app.core.exceptions import ForbiddenError, NotFoundError
from app.db.session import get_db
from app.models.enums import AuditAction
from app.models.quiz import Question, QuestionSet
from app.schemas.common import APIResponse
from app.schemas.quiz import (
    QuestionCreate,
    QuestionOut,
    QuestionUpdate,
    QuestionSetCreate,
    QuestionSetOut,
    QuestionSetDetailOut,
    QuestionSetUpdate,
)
from app.services.audit_service import write_audit_log

router = APIRouter(prefix="/question-sets", tags=["Question Sets"])


# ── Question Sets ─────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=APIResponse[QuestionSetOut],
    status_code=201,
    summary="Create question set",
    description="Create a new question set. TEACHER or above.",
)
async def create_question_set(
    school_id: int,
    body: QuestionSetCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_teacher),
) -> APIResponse[QuestionSetOut]:
    user.assert_school_access(school_id)
    qs = QuestionSet(school_id=school_id, teacher_id=user.user_id, **body.model_dump())
    db.add(qs)
    await db.flush()
    await write_audit_log(
        db, action=AuditAction.QUIZ_CREATED, school_id=school_id, user_id=user.user_id,
        entity_type="QuestionSet", entity_id=qs.id,
    )
    out = QuestionSetOut.model_validate(qs)
    out.question_count = 0
    return APIResponse(data=out, message="Question set created")


@router.get(
    "",
    response_model=APIResponse[List[QuestionSetOut]],
    summary="List question sets",
)
async def list_question_sets(
    school_id: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[List[QuestionSetOut]]:
    user.assert_school_access(school_id)
    q = select(QuestionSet).where(QuestionSet.school_id == school_id)
    # Teachers see only their own
    if not user.is_school_admin():
        q = q.where(QuestionSet.teacher_id == user.user_id)
    result = await db.execute(q.order_by(QuestionSet.created_at.desc()))
    items = result.scalars().all()
    return APIResponse(data=[QuestionSetOut.model_validate(i) for i in items])


@router.get(
    "/{qs_id}",
    response_model=APIResponse[QuestionSetDetailOut],
    summary="Get question set",
)
async def get_question_set(
    school_id: int,
    qs_id: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[QuestionSetDetailOut]:
    user.assert_school_access(school_id)
    qs = await _get_qs(db, school_id, qs_id)
    _assert_qs_access(user, qs)
    out = QuestionSetDetailOut.model_validate(qs)
    out.questions = [QuestionOut.model_validate(q) for q in qs.questions]
    out.question_count = len(qs.questions)
    return APIResponse(data=out)


@router.patch(
    "/{qs_id}",
    response_model=APIResponse[QuestionSetOut],
    summary="Update question set",
)
async def update_question_set(
    school_id: int,
    qs_id: int,
    body: QuestionSetUpdate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_teacher),
) -> APIResponse[QuestionSetOut]:
    user.assert_school_access(school_id)
    qs = await _get_qs(db, school_id, qs_id)
    _assert_qs_access(user, qs)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(qs, field, value)
    await db.flush()
    return APIResponse(data=QuestionSetOut.model_validate(qs))


# ── Questions ─────────────────────────────────────────────────────────────

@router.post(
    "/{qs_id}/questions",
    response_model=APIResponse[QuestionOut],
    status_code=201,
    summary="Add question",
    description="Add a multiple-choice question to a question set.",
)
async def add_question(
    school_id: int,
    qs_id: int,
    body: QuestionCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_teacher),
) -> APIResponse[QuestionOut]:
    user.assert_school_access(school_id)
    qs = await _get_qs(db, school_id, qs_id)
    _assert_qs_access(user, qs)
    question = Question(question_set_id=qs_id, **body.model_dump())
    db.add(question)
    await db.flush()
    return APIResponse(data=QuestionOut.model_validate(question), message="Question added")


@router.get(
    "/{qs_id}/questions",
    response_model=APIResponse[List[QuestionOut]],
    summary="List questions",
)
async def list_questions(
    school_id: int,
    qs_id: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[List[QuestionOut]]:
    user.assert_school_access(school_id)
    qs = await _get_qs(db, school_id, qs_id)
    _assert_qs_access(user, qs)
    return APIResponse(data=[QuestionOut.model_validate(q) for q in qs.questions])


@router.patch(
    "/{qs_id}/questions/{q_id}",
    response_model=APIResponse[QuestionOut],
    summary="Update question or correct answer",
    description="Update question details, options, or correct answer. Recalculates live responses if answer changed.",
)
async def update_question(
    school_id: int,
    qs_id: int,
    q_id: int,
    body: QuestionUpdate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_teacher),
) -> APIResponse[QuestionOut]:
    user.assert_school_access(school_id)
    qs = await _get_qs(db, school_id, qs_id)
    _assert_qs_access(user, qs)

    res = await db.execute(
        select(Question).where(and_(Question.id == q_id, Question.question_set_id == qs_id))
    )
    q = res.scalars().first()
    if not q:
        raise NotFoundError("Question", q_id)

    old_correct = q.correct_answer
    old_marks = q.marks
    update_data = body.model_dump(exclude_unset=True)

    for field, val in update_data.items():
        setattr(q, field, val)

    await db.flush()

    if ("correct_answer" in update_data and q.correct_answer != old_correct) or ("marks" in update_data and q.marks != old_marks):
        from app.services.quiz_service import recalculate_question_responses_and_scores
        await recalculate_question_responses_and_scores(db, q)

    await db.commit()
    await db.refresh(q)
    return APIResponse(data=QuestionOut.model_validate(q), message="Question updated successfully")


# ── Helpers ────────────────────────────────────────────────────────────────

async def _get_qs(db: AsyncSession, school_id: int, qs_id: int) -> QuestionSet:
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(QuestionSet)
        .where(and_(QuestionSet.id == qs_id, QuestionSet.school_id == school_id))
        .options(selectinload(QuestionSet.questions))
    )
    qs = result.scalars().first()
    if not qs:
        raise NotFoundError("QuestionSet", qs_id)
    return qs


def _assert_qs_access(user: CurrentUser, qs: QuestionSet) -> None:
    if not user.is_school_admin() and qs.teacher_id != user.user_id:
        raise ForbiddenError("You can only access your own question sets")


# ── Quick Quiz: create by number of questions + correct answers only ─────────

from typing import Optional as Opt
from pydantic import BaseModel as BM, Field as F


class QuickQuizQuestionIn(BM):
    """One question entry for the quick-quiz builder."""
    correct_answer: Opt[str] = F(None, pattern="^[ABCD]$")
    label: Opt[str] = None          # optional short topic label / question title
    question_text: Opt[str] = None
    marks: int = F(1, ge=1, le=10)
    option_a: Opt[str] = None
    option_b: Opt[str] = None
    option_c: Opt[str] = None
    option_d: Opt[str] = None


class QuickQuizCreate(BM):
    title: str = F(..., min_length=2, max_length=200)
    subject: Opt[str] = None
    grade: Opt[str] = None
    questions: List[QuickQuizQuestionIn]  # length == num_questions


class QuickQuizOut(BM):
    question_set_id: int
    title: str
    num_questions: int
    question_ids: List[int]


@router.post(
    "/quick-create",
    response_model=APIResponse[QuickQuizOut],
    status_code=201,
    summary="Quick Quiz: create by number + correct answers only",
    description=(
        "Creates a QuestionSet with N questions in one request. "
        "Supports custom question text and options A–D, defaulting to 'Option A-D' if empty. "
        "Designed for rapid card-scanning quizzes."
    ),
)
async def quick_create_quiz(
    school_id: int,
    body: QuickQuizCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_teacher),
) -> APIResponse[QuickQuizOut]:
    from app.models.enums import AnswerLetter, QuestionSetStatus

    user.assert_school_access(school_id)

    # 1. Create question set
    qs = QuestionSet(
        school_id=school_id,
        teacher_id=user.user_id,
        title=body.title,
        subject=body.subject,
        grade=body.grade,
        description=f"Quick quiz with {len(body.questions)} questions",
        status=QuestionSetStatus.PUBLISHED,
    )
    db.add(qs)
    await db.flush()  # get qs.id

    # 2. Create questions
    question_ids: List[int] = []
    for i, qin in enumerate(body.questions, start=1):
        q_text = qin.question_text or qin.label or f"Question {i}"
        correct = AnswerLetter(qin.correct_answer) if qin.correct_answer else None
        q = Question(
            question_set_id=qs.id,
            question_text=q_text,
            option_a=qin.option_a or "Option A",
            option_b=qin.option_b or "Option B",
            option_c=qin.option_c or "Option C",
            option_d=qin.option_d or "Option D",
            correct_answer=correct,
            marks=qin.marks,
        )
        db.add(q)
        await db.flush()
        question_ids.append(q.id)

    await write_audit_log(
        db, action=AuditAction.QUIZ_CREATED, school_id=school_id, user_id=user.user_id,
        entity_type="QuestionSet", entity_id=qs.id,
        metadata={"quick_quiz": True, "num_questions": len(body.questions)},
    )

    return APIResponse(
        data=QuickQuizOut(
            question_set_id=qs.id,
            title=qs.title,
            num_questions=len(question_ids),
            question_ids=question_ids,
        ),
        message=f"Quick quiz created with {len(question_ids)} questions",
    )
