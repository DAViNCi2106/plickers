"""app/api/v1/academic_years.py — Academic year, class, and section endpoints."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, get_current_user, require_school_admin
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models.school import AcademicYear, Class, Section
from app.schemas.common import APIResponse
from app.schemas.school import (
    AcademicYearCreate, AcademicYearOut,
    ClassCreate, ClassOut,
    SectionCreate, SectionOut,
)

router = APIRouter(tags=["Academic Structure"])


# ── Academic Years ────────────────────────────────────────────────────────

@router.post(
    "/academic-years",
    response_model=APIResponse[AcademicYearOut],
    status_code=201,
    summary="Create academic year",
)
async def create_academic_year(
    school_id: int,
    body: AcademicYearCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_school_admin),
) -> APIResponse[AcademicYearOut]:
    user.assert_school_access(school_id)
    ay = AcademicYear(school_id=school_id, **body.model_dump())
    db.add(ay)
    await db.flush()
    return APIResponse(data=AcademicYearOut.model_validate(ay), message="Academic year created")


@router.get(
    "/academic-years",
    response_model=APIResponse[List[AcademicYearOut]],
    summary="List academic years",
)
async def list_academic_years(
    school_id: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[List[AcademicYearOut]]:
    user.assert_school_access(school_id)
    result = await db.execute(
        select(AcademicYear).where(AcademicYear.school_id == school_id)
        .order_by(AcademicYear.start_date.desc())
    )
    return APIResponse(data=[AcademicYearOut.model_validate(a) for a in result.scalars().all()])


# ── Classes ───────────────────────────────────────────────────────────────

@router.post(
    "/classes",
    response_model=APIResponse[ClassOut],
    status_code=201,
    summary="Create class",
)
async def create_class(
    school_id: int,
    body: ClassCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_school_admin),
) -> APIResponse[ClassOut]:
    user.assert_school_access(school_id)
    cls = Class(school_id=school_id, **body.model_dump())
    db.add(cls)
    await db.flush()
    return APIResponse(data=ClassOut.model_validate(cls), message="Class created")


@router.get(
    "/classes",
    response_model=APIResponse[List[ClassOut]],
    summary="List classes",
)
async def list_classes(
    school_id: int,
    academic_year_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[List[ClassOut]]:
    user.assert_school_access(school_id)
    q = select(Class).where(Class.school_id == school_id)
    if academic_year_id:
        q = q.where(Class.academic_year_id == academic_year_id)
    result = await db.execute(q.order_by(Class.name))
    return APIResponse(data=[ClassOut.model_validate(c) for c in result.scalars().all()])


@router.get(
    "/classes/{class_id}",
    response_model=APIResponse[ClassOut],
    summary="Get class details",
)
async def get_class(
    school_id: int,
    class_id: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[ClassOut]:
    user.assert_school_access(school_id)
    cls_result = await db.execute(
        select(Class).where(and_(Class.id == class_id, Class.school_id == school_id))
    )
    cls = cls_result.scalars().first()
    if not cls:
        raise NotFoundError("Class", class_id)
    return APIResponse(data=ClassOut.model_validate(cls))



# ── Sections ──────────────────────────────────────────────────────────────

@router.post(
    "/classes/{class_id}/sections",
    response_model=APIResponse[SectionOut],
    status_code=201,
    summary="Create section",
)
async def create_section(
    school_id: int,
    class_id: int,
    body: SectionCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_school_admin),
) -> APIResponse[SectionOut]:
    user.assert_school_access(school_id)
    # Verify class belongs to school
    cls_result = await db.execute(
        select(Class).where(and_(Class.id == class_id, Class.school_id == school_id))
    )
    if not cls_result.scalars().first():
        raise NotFoundError("Class", class_id)

    section = Section(class_id=class_id, **body.model_dump())
    db.add(section)
    await db.flush()
    return APIResponse(data=SectionOut.model_validate(section), message="Section created")


@router.get(
    "/classes/{class_id}/sections",
    response_model=APIResponse[List[SectionOut]],
    summary="List sections",
)
async def list_sections(
    school_id: int,
    class_id: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[List[SectionOut]]:
    user.assert_school_access(school_id)
    result = await db.execute(
        select(Section)
        .join(Class, Section.class_id == Class.id)
        .where(and_(Section.class_id == class_id, Class.school_id == school_id))
        .order_by(Section.name)
    )
    return APIResponse(data=[SectionOut.model_validate(s) for s in result.scalars().all()])
