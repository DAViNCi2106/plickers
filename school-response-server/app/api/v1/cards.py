"""app/api/v1/cards.py — Card management endpoints."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
import os
from pathlib import Path

from app.core.deps import CurrentUser, get_current_user, require_school_admin
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models.card import Card, StudentCard
from app.models.student import Student
from app.schemas.card import (
    CardAssignmentOut,
    CardAssignRequest,
    CardCreate,
    CardOut,
    CardReplaceRequest,
    CardUnassignRequest,
    StudentCardOut,
)
from app.schemas.common import APIResponse
from app.services.card_service import (
    assign_card,
    create_card,
    disable_card,
    get_card_by_marker,
    replace_lost_card,
    unassign_card,
)

router = APIRouter(prefix="/cards", tags=["Cards"])

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent

@router.get(
    "/pdf",
    summary="Download printable cards PDF",
    description="Returns the printable A4 sheet PDF of all unique Plickers cards to distribute to students.",
)
async def download_cards_pdf():
    pdf_path = _PROJECT_ROOT / "output" / "cards.pdf"
    if not pdf_path.exists():
        raise NotFoundError("Cards PDF", "cards.pdf not generated yet")
    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename="plickers_cards_sheet.pdf"
    )


@router.post(
    "",
    response_model=APIResponse[CardOut],
    status_code=201,
    summary="Create card",
    description="Register a new physical ArUco card. marker_id must equal card_number and be unique within the school.",
)
async def create_card_endpoint(
    school_id: int,
    body: CardCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_school_admin),
) -> APIResponse[CardOut]:
    user.assert_school_access(school_id)
    card = await create_card(db, school_id, body, user_id=user.user_id)
    return APIResponse(data=CardOut.model_validate(card), message="Card created")


@router.get(
    "",
    response_model=APIResponse[List[CardOut]],
    summary="List cards",
    description="List all cards for a school.",
)
async def list_cards(
    school_id: int,
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[List[CardOut]]:
    user.assert_school_access(school_id)
    q = select(Card).where(Card.school_id == school_id)
    if status:
        q = q.where(Card.status == status)
    q = q.order_by(Card.card_number)
    result = await db.execute(q)
    cards = result.scalars().all()
    return APIResponse(data=[CardOut.model_validate(c) for c in cards])


@router.get(
    "/search",
    response_model=APIResponse[CardAssignmentOut],
    summary="Search card by marker_id",
    description="Look up a card by its ArUco marker_id and return the current assignment.",
)
async def search_by_marker(
    school_id: int,
    marker_id: int = Query(..., ge=1, le=249),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[CardAssignmentOut]:
    user.assert_school_access(school_id)
    card = await get_card_by_marker(db, school_id, marker_id)

    # Get active assignment
    sc_result = await db.execute(
        select(StudentCard).where(
            and_(StudentCard.card_id == card.id, StudentCard.is_active == True)
        )
    )
    assignment = sc_result.scalars().first()

    student_id = 0
    student_code = ""
    student_name = ""
    assigned_at = card.created_at
    if assignment:
        stu_result = await db.execute(select(Student).where(Student.id == assignment.student_id))
        student = stu_result.scalars().first()
        if student:
            student_id = student.id
            student_code = student.student_code
            student_name = f"{student.first_name} {student.last_name}"
            assigned_at = assignment.assigned_at

    return APIResponse(data=CardAssignmentOut(
        card=CardOut.model_validate(card),
        student_id=student_id,
        student_code=student_code,
        student_name=student_name,
        assigned_at=assigned_at,
        is_active=assignment is not None and assignment.is_active,
    ))


@router.get(
    "/assignments",
    response_model=APIResponse[List[CardAssignmentOut]],
    summary="List card assignments",
    description="List all active card assignments for the school.",
)
async def list_card_assignments(
    school_id: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[List[CardAssignmentOut]]:
    user.assert_school_access(school_id)
    result = await db.execute(
        select(StudentCard, Card, Student)
        .join(Card, StudentCard.card_id == Card.id)
        .join(Student, StudentCard.student_id == Student.id)
        .where(and_(Card.school_id == school_id, StudentCard.is_active == True))
        .order_by(Card.card_number)
    )
    rows = result.all()
    assignments = [
        CardAssignmentOut(
            card=CardOut.model_validate(card),
            student_id=student.id,
            student_code=student.student_code,
            student_name=f"{student.first_name} {student.last_name}",
            assigned_at=sc.assigned_at,
            is_active=sc.is_active,
        )
        for sc, card, student in rows
    ]
    return APIResponse(data=assignments)


@router.get(
    "/{card_id}",
    response_model=APIResponse[CardOut],
    summary="Get card",
)
async def get_card_endpoint(
    school_id: int,
    card_id: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[CardOut]:
    user.assert_school_access(school_id)
    result = await db.execute(
        select(Card).where(and_(Card.id == card_id, Card.school_id == school_id))
    )
    card = result.scalars().first()
    if not card:
        raise NotFoundError("Card", card_id)
    return APIResponse(data=CardOut.model_validate(card))


@router.post(
    "/{card_id}/assign",
    response_model=APIResponse[StudentCardOut],
    summary="Assign card to student",
    description="Assign a physical card to a student. Fails if the card or student already has an active assignment.",
)
async def assign_card_endpoint(
    school_id: int,
    card_id: int,
    body: CardAssignRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_school_admin),
) -> APIResponse[StudentCardOut]:
    user.assert_school_access(school_id)
    assignment = await assign_card(db, school_id, card_id, body.student_id, user_id=user.user_id)
    return APIResponse(data=StudentCardOut.model_validate(assignment), message="Card assigned")


@router.post(
    "/{card_id}/unassign",
    response_model=APIResponse[StudentCardOut],
    summary="Unassign card",
    description="Remove the current student assignment from a card.",
)
async def unassign_card_endpoint(
    school_id: int,
    card_id: int,
    body: CardUnassignRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_school_admin),
) -> APIResponse[StudentCardOut]:
    user.assert_school_access(school_id)
    assignment = await unassign_card(db, school_id, card_id, user_id=user.user_id, reason=body.reason)
    return APIResponse(data=StudentCardOut.model_validate(assignment), message="Card unassigned")


@router.post(
    "/{card_id}/replace",
    response_model=APIResponse[StudentCardOut],
    summary="Replace lost card",
    description="Mark an old card as LOST and assign a new card to the same student.",
)
async def replace_card_endpoint(
    school_id: int,
    card_id: int,
    body: CardReplaceRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_school_admin),
) -> APIResponse[StudentCardOut]:
    user.assert_school_access(school_id)
    assignment = await replace_lost_card(
        db, school_id, card_id, body.new_card_id,
        user_id=user.user_id, reason=body.reason
    )
    return APIResponse(data=StudentCardOut.model_validate(assignment), message="Card replaced")


@router.post(
    "/{card_id}/disable",
    response_model=APIResponse[CardOut],
    summary="Disable card",
    description="Permanently disable a card. It cannot be assigned again.",
)
async def disable_card_endpoint(
    school_id: int,
    card_id: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_school_admin),
) -> APIResponse[CardOut]:
    user.assert_school_access(school_id)
    card = await disable_card(db, school_id, card_id, user_id=user.user_id)
    return APIResponse(data=CardOut.model_validate(card), message="Card disabled")
