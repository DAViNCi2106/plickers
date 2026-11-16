"""app/api/v1/schools.py — School management endpoints."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, get_current_user, require_super_admin
from app.db.session import get_db
from app.models.school import School
from app.schemas.common import APIResponse
from app.schemas.school import SchoolCreate, SchoolOut, SchoolUpdate
from app.core.exceptions import DuplicateError, NotFoundError

router = APIRouter(prefix="/schools", tags=["Schools"])


@router.post(
    "",
    response_model=APIResponse[SchoolOut],
    summary="Create school",
    description="Create a new school tenant. SUPER_ADMIN only.",
    status_code=201,
)
async def create_school(
    body: SchoolCreate,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_super_admin),
) -> APIResponse[SchoolOut]:
    existing = (await db.execute(
        select(School).where(School.school_code == body.school_code)
    )).scalars().first()
    if existing:
        raise DuplicateError("School", "school_code")

    school = School(**body.model_dump())
    db.add(school)
    await db.flush()
    return APIResponse(data=SchoolOut.model_validate(school), message="School created")


@router.get(
    "",
    response_model=APIResponse[List[SchoolOut]],
    summary="List schools",
    description="List all schools. SUPER_ADMIN only.",
)
async def list_schools(
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_super_admin),
) -> APIResponse[List[SchoolOut]]:
    result = await db.execute(select(School).order_by(School.name))
    schools = result.scalars().all()
    return APIResponse(data=[SchoolOut.model_validate(s) for s in schools])


@router.get(
    "/{school_id}",
    response_model=APIResponse[SchoolOut],
    summary="Get school",
)
async def get_school(
    school_id: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[SchoolOut]:
    user.assert_school_access(school_id)
    result = await db.execute(select(School).where(School.id == school_id))
    school = result.scalars().first()
    if not school:
        raise NotFoundError("School", school_id)
    return APIResponse(data=SchoolOut.model_validate(school))


@router.patch(
    "/{school_id}",
    response_model=APIResponse[SchoolOut],
    summary="Update school",
)
async def update_school(
    school_id: int,
    body: SchoolUpdate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[SchoolOut]:
    user.assert_school_access(school_id)
    result = await db.execute(select(School).where(School.id == school_id))
    school = result.scalars().first()
    if not school:
        raise NotFoundError("School", school_id)

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(school, field, value)
    await db.flush()
    return APIResponse(data=SchoolOut.model_validate(school))
