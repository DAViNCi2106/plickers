"""app/api/v1/teachers.py — Teacher management."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, get_current_user, require_school_admin
from app.core.exceptions import DuplicateError, NotFoundError
from app.core.security import hash_password
from app.db.session import get_db
from app.models.enums import AuditAction, UserRole
from app.models.user import Teacher, User
from app.schemas.common import APIResponse
from app.schemas.user import TeacherCreateFull, TeacherOut, UserOut, TeacherUpdate
from app.services.audit_service import write_audit_log

router = APIRouter(prefix="/teachers", tags=["Teachers"])


@router.post(
    "",
    response_model=APIResponse[TeacherOut],
    status_code=201,
    summary="Create teacher",
    description="Create a user account + teacher profile. SCHOOL_ADMIN only.",
)
async def create_teacher(
    school_id: int,
    body: TeacherCreateFull,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_school_admin),
) -> APIResponse[TeacherOut]:
    user.assert_school_access(school_id)

    # Check username uniqueness within school
    existing = (await db.execute(
        select(User).where(and_(User.school_id == school_id, User.username == body.username))
    )).scalars().first()
    if existing:
        raise DuplicateError("User", "username")

    # Check employee_id uniqueness
    if body.employee_id:
        dup_emp = (await db.execute(
            select(Teacher).where(
                and_(Teacher.school_id == school_id, Teacher.employee_id == body.employee_id)
            )
        )).scalars().first()
        if dup_emp:
            raise DuplicateError("Teacher", "employee_id")

    # Create user account — password is hashed before storage
    new_user = User(
        school_id=school_id,
        username=body.username,
        email=body.email,
        password_hash=hash_password(body.password),  # hash ONLY — never store plain
        role=UserRole.TEACHER,
    )
    db.add(new_user)
    await db.flush()

    teacher = Teacher(
        user_id=new_user.id,
        school_id=school_id,
        employee_id=body.employee_id,
        first_name=body.first_name,
        last_name=body.last_name,
        phone=body.phone,
    )
    db.add(teacher)
    await db.flush()

    await write_audit_log(
        db, action=AuditAction.TEACHER_CREATED, school_id=school_id, user_id=user.user_id,
        entity_type="Teacher", entity_id=teacher.id,
        metadata={"employee_id": body.employee_id},
    )
    return APIResponse(data=TeacherOut.model_validate(teacher), message="Teacher created")


@router.get(
    "",
    response_model=APIResponse[List[TeacherOut]],
    summary="List teachers",
)
async def list_teachers(
    school_id: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[List[TeacherOut]]:
    user.assert_school_access(school_id)
    result = await db.execute(
        select(Teacher).where(Teacher.school_id == school_id).order_by(Teacher.last_name)
    )
    teachers = result.scalars().all()
    return APIResponse(data=[TeacherOut.model_validate(t) for t in teachers])


@router.get(
    "/{teacher_id}",
    response_model=APIResponse[TeacherOut],
    summary="Get teacher",
)
async def get_teacher(
    school_id: int,
    teacher_id: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[TeacherOut]:
    user.assert_school_access(school_id)
    result = await db.execute(
        select(Teacher).where(and_(Teacher.id == teacher_id, Teacher.school_id == school_id))
    )
    teacher = result.scalars().first()
    if not teacher:
        raise NotFoundError("Teacher", teacher_id)
    return APIResponse(data=TeacherOut.model_validate(teacher))


@router.patch(
    "/{teacher_id}",
    response_model=APIResponse[TeacherOut],
    summary="Update teacher",
    description="Update teacher profile fields. SCHOOL_ADMIN or above required.",
)
async def update_teacher(
    school_id: int,
    teacher_id: int,
    body: TeacherUpdate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_school_admin),
) -> APIResponse[TeacherOut]:
    user.assert_school_access(school_id)
    result = await db.execute(
        select(Teacher).where(and_(Teacher.id == teacher_id, Teacher.school_id == school_id))
    )
    teacher = result.scalars().first()
    if not teacher:
        raise NotFoundError("Teacher", teacher_id)

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(teacher, field, value)
    await db.flush()

    await write_audit_log(
        db, action=AuditAction.TEACHER_UPDATED, school_id=school_id, user_id=user.user_id,
        entity_type="Teacher", entity_id=teacher.id,
    )
    return APIResponse(data=TeacherOut.model_validate(teacher))


@router.delete(
    "/{teacher_id}",
    response_model=APIResponse[None],
    summary="Deactivate teacher",
    description=(
        "Deactivate a teacher's account (soft delete). "
        "Sets the underlying User.is_active = False; does not remove data. "
        "SCHOOL_ADMIN or above required."
    ),
)
async def delete_teacher(
    school_id: int,
    teacher_id: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_school_admin),
) -> APIResponse[None]:
    user.assert_school_access(school_id)
    result = await db.execute(
        select(Teacher).where(and_(Teacher.id == teacher_id, Teacher.school_id == school_id))
    )
    teacher = result.scalars().first()
    if not teacher:
        raise NotFoundError("Teacher", teacher_id)

    # Soft-delete: deactivate the underlying user account
    user_result = await db.execute(select(User).where(User.id == teacher.user_id))
    teacher_user = user_result.scalars().first()
    if teacher_user:
        teacher_user.is_active = False
    await db.flush()

    await write_audit_log(
        db, action=AuditAction.TEACHER_UPDATED, school_id=school_id, user_id=user.user_id,
        entity_type="Teacher", entity_id=teacher_id,
        metadata={"action": "deactivated"},
    )
    return APIResponse(message="Teacher deactivated")
