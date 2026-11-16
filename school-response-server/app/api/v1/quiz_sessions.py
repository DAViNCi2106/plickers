"""app/api/v1/quiz_sessions.py — Quiz session lifecycle endpoints."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, get_current_user, require_teacher
from app.core.exceptions import ForbiddenError, NotFoundError
from app.db.session import get_db, AsyncSessionFactory
from app.models.quiz import QuizSession, QuestionSet
from app.schemas.common import APIResponse
from app.schemas.quiz import QuizDashboardOut, QuizSessionCreate, QuizSessionOut
from app.services.quiz_service import (
    end_quiz_session,
    get_quiz_dashboard,
    get_quiz_session,
    pause_quiz_session,
    resume_quiz_session,
    start_quiz_session,
)
from app.websocket.manager import ws_manager

router = APIRouter(prefix="/quiz-sessions", tags=["Quiz Sessions"])


@router.post(
    "",
    response_model=APIResponse[QuizSessionOut],
    status_code=201,
    summary="Create quiz session",
    description="Create a new pending quiz session for a question set.",
)
async def create_quiz_session(
    school_id: int,
    body: QuizSessionCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_teacher),
) -> APIResponse[QuizSessionOut]:
    user.assert_school_access(school_id)

    # Verify question set belongs to this school
    qs_result = await db.execute(
        select(QuestionSet).where(
            and_(QuestionSet.id == body.question_set_id, QuestionSet.school_id == school_id)
        )
    )
    if not qs_result.scalars().first():
        raise NotFoundError("QuestionSet", body.question_set_id)

    session = QuizSession(
        question_set_id=body.question_set_id,
        teacher_id=user.user_id,
        class_id=body.class_id,
        section_id=body.section_id,
    )
    db.add(session)
    await db.flush()
    return APIResponse(data=QuizSessionOut.model_validate(session), message="Quiz session created")


@router.get(
    "",
    response_model=APIResponse[List[QuizSessionOut]],
    summary="List quiz sessions",
)
async def list_quiz_sessions(
    school_id: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[List[QuizSessionOut]]:
    user.assert_school_access(school_id)
    q = (
        select(QuizSession)
        .join(QuestionSet, QuizSession.question_set_id == QuestionSet.id)
        .where(QuestionSet.school_id == school_id)
    )
    if not user.is_school_admin():
        q = q.where(QuizSession.teacher_id == user.user_id)
    result = await db.execute(q.order_by(QuizSession.created_at.desc()))
    sessions = result.scalars().all()
    return APIResponse(data=[QuizSessionOut.model_validate(s) for s in sessions])


@router.get(
    "/{session_id}",
    response_model=APIResponse[QuizSessionOut],
    summary="Get quiz session details",
)
async def get_quiz_session_detail(
    school_id: int,
    session_id: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[QuizSessionOut]:
    user.assert_school_access(school_id)
    session = await get_quiz_session(db, session_id)
    return APIResponse(data=QuizSessionOut.model_validate(session))



@router.post(
    "/{session_id}/start",
    response_model=APIResponse[QuizSessionOut],
    summary="Start quiz session",
    description="Transition a PENDING session to ACTIVE. Starts accepting scanner responses.",
)
async def start_session(
    school_id: int,
    session_id: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_teacher),
) -> APIResponse[QuizSessionOut]:
    user.assert_school_access(school_id)
    quiz = await start_quiz_session(db, session_id, school_id, user.user_id)
    return APIResponse(data=QuizSessionOut.model_validate(quiz), message="Quiz started")


@router.post(
    "/{session_id}/end",
    response_model=APIResponse[QuizSessionOut],
    summary="End quiz session",
)
async def end_session(
    school_id: int,
    session_id: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_teacher),
) -> APIResponse[QuizSessionOut]:
    user.assert_school_access(school_id)
    quiz = await end_quiz_session(db, session_id, school_id, user.user_id)
    return APIResponse(data=QuizSessionOut.model_validate(quiz), message="Quiz ended")


@router.post(
    "/{session_id}/pause",
    response_model=APIResponse[QuizSessionOut],
    summary="Pause quiz session",
    description="Pause an ACTIVE session. Scanner responses will be rejected while paused.",
)
async def pause_session(
    school_id: int,
    session_id: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_teacher),
) -> APIResponse[QuizSessionOut]:
    user.assert_school_access(school_id)
    quiz = await pause_quiz_session(db, session_id, school_id, user.user_id)
    return APIResponse(data=QuizSessionOut.model_validate(quiz), message="Quiz paused")


@router.post(
    "/{session_id}/resume",
    response_model=APIResponse[QuizSessionOut],
    summary="Resume paused quiz session",
    description="Resume a PAUSED session back to ACTIVE.",
)
async def resume_session(
    school_id: int,
    session_id: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_teacher),
) -> APIResponse[QuizSessionOut]:
    user.assert_school_access(school_id)
    quiz = await resume_quiz_session(db, session_id, school_id, user.user_id)
    return APIResponse(data=QuizSessionOut.model_validate(quiz), message="Quiz resumed")


@router.get(
    "/{session_id}/dashboard",
    response_model=APIResponse[QuizDashboardOut],
    summary="Quiz live dashboard",
    description="Get aggregated live response data for the teacher dashboard.",
)
async def quiz_dashboard(
    school_id: int,
    session_id: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[QuizDashboardOut]:
    user.assert_school_access(school_id)
    dashboard = await get_quiz_dashboard(db, session_id, school_id)
    return APIResponse(data=dashboard)


# ── WebSocket ─────────────────────────────────────────────────────────────

@router.websocket("/ws/quiz/{quiz_session_id}")
async def quiz_websocket(
    websocket: WebSocket,
    quiz_session_id: int,
) -> None:
    """
    WebSocket endpoint for live quiz dashboard updates.

    Connect: ws://<host>/api/v1/quiz-sessions/ws/quiz/{quiz_session_id}

    Events pushed to the client:
      {"event": "response", "data": { ... }}
      {"event": "dashboard", "data": { ... }}
      {"event": "session_ended"}
    """
    await ws_manager.connect(websocket, quiz_session_id)
    try:
        while True:
            # Keep connection alive; all updates are server-pushed
            data = await websocket.receive_text()
            # Allow client ping/pong
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    finally:
        await ws_manager.disconnect(websocket, quiz_session_id)
