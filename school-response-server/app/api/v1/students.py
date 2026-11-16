"""app/api/v1/students.py — Student CRUD + Excel/CSV bulk import."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import CurrentUser, get_current_user, require_school_admin
from app.core.exceptions import BadRequestError, DuplicateError, NotFoundError
from app.db.session import get_db
from app.models.enums import AuditAction
from app.models.student import Student
from app.schemas.common import APIResponse, ImportSummary
from app.schemas.student import StudentCreate, StudentOut, StudentUpdate
from app.services.audit_service import write_audit_log
from app.services.card_service import import_students_from_file

router = APIRouter(prefix="/students", tags=["Students"])


@router.post(
    "",
    response_model=APIResponse[StudentOut],
    status_code=201,
    summary="Create student",
    description="Create a single student. SCHOOL_ADMIN or above required.",
)
async def create_student(
    school_id: int,
    body: StudentCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_school_admin),
) -> APIResponse[StudentOut]:
    user.assert_school_access(school_id)

    existing = (await db.execute(
        select(Student).where(
            and_(Student.school_id == school_id, Student.student_code == body.student_code)
        )
    )).scalars().first()
    if existing:
        raise DuplicateError("Student", "student_code")

    student = Student(school_id=school_id, **body.model_dump())
    db.add(student)
    await db.flush()

    await write_audit_log(
        db, action=AuditAction.STUDENT_CREATED, school_id=school_id, user_id=user.user_id,
        entity_type="Student", entity_id=student.id,
        metadata={"student_code": student.student_code},
    )
    return APIResponse(data=StudentOut.model_validate(student), message="Student created")


@router.get(
    "",
    response_model=APIResponse[List[StudentOut]],
    summary="List students",
    description="List students for a school. Supports filtering by class/section.",
)
async def list_students(
    school_id: int,
    class_id: Optional[int] = Query(None),
    section_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[List[StudentOut]]:
    user.assert_school_access(school_id)

    q = select(Student).where(Student.school_id == school_id)
    if class_id:
        q = q.where(Student.class_id == class_id)
    if section_id:
        q = q.where(Student.section_id == section_id)
    q = q.order_by(Student.student_code)

    result = await db.execute(q)
    students = result.scalars().all()
    return APIResponse(data=[StudentOut.model_validate(s) for s in students])


@router.get(
    "/{student_id}",
    response_model=APIResponse[StudentOut],
    summary="Get student",
)
async def get_student(
    school_id: int,
    student_id: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[StudentOut]:
    user.assert_school_access(school_id)
    student = await _get_student(db, school_id, student_id)
    return APIResponse(data=StudentOut.model_validate(student))


@router.patch(
    "/{student_id}",
    response_model=APIResponse[StudentOut],
    summary="Update student",
)
async def update_student(
    school_id: int,
    student_id: int,
    body: StudentUpdate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_school_admin),
) -> APIResponse[StudentOut]:
    user.assert_school_access(school_id)
    student = await _get_student(db, school_id, student_id)

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(student, field, value)
    await db.flush()

    await write_audit_log(
        db, action=AuditAction.STUDENT_UPDATED, school_id=school_id, user_id=user.user_id,
        entity_type="Student", entity_id=student.id,
    )
    return APIResponse(data=StudentOut.model_validate(student))


@router.delete(
    "/{student_id}",
    response_model=APIResponse[None],
    summary="Delete student",
)
async def delete_student(
    school_id: int,
    student_id: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_school_admin),
) -> APIResponse[None]:
    user.assert_school_access(school_id)
    student = await _get_student(db, school_id, student_id)
    await db.delete(student)
    await db.flush()
    await write_audit_log(
        db, action=AuditAction.STUDENT_DELETED, school_id=school_id, user_id=user.user_id,
        entity_type="Student", entity_id=student_id,
    )
    return APIResponse(message="Student deleted")


@router.post(
    "/import",
    response_model=APIResponse[ImportSummary],
    summary="Bulk import students from Excel/CSV",
    description=(
        "Upload an Excel (.xlsx) or CSV file to bulk-import students and "
        "auto-assign cards. Expected columns: S.No, Student Name, Student ID, Card ID. "
        "Matches the existing 50_sample_students_plickers.xlsx format. "
        "Uses a transaction — partial failures do not corrupt the database."
    ),
    status_code=200,
)
async def import_students(
    school_id: int,
    file: UploadFile = File(..., description="Excel (.xlsx) or CSV file"),
    class_id: Optional[int] = Form(None),
    section_id: Optional[int] = Form(None),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_school_admin),
) -> APIResponse[ImportSummary]:
    user.assert_school_access(school_id)

    if file.size and file.size > settings.max_upload_size_bytes:
        raise BadRequestError(
            f"File too large. Maximum {settings.MAX_UPLOAD_SIZE_MB} MB.",
            "FILE_TOO_LARGE",
        )

    allowed = {".xlsx", ".xls", ".csv"}
    suffix = "." + (file.filename or "").rsplit(".", 1)[-1].lower()
    if suffix not in allowed:
        raise BadRequestError("Only .xlsx, .xls, or .csv files accepted.", "INVALID_FILE_TYPE")

    file_bytes = await file.read()
    summary = await import_students_from_file(
        db,
        school_id=school_id,
        class_id=class_id,
        section_id=section_id,
        file_bytes=file_bytes,
        filename=file.filename or "upload",
        user_id=user.user_id,
    )
    return APIResponse(data=summary, message=f"Import complete: {summary.successful} succeeded, {summary.failed} failed")


# ── Internal helper ────────────────────────────────────────────────────────

async def _get_student(db: AsyncSession, school_id: int, student_id: int) -> Student:
    result = await db.execute(
        select(Student).where(and_(Student.id == student_id, Student.school_id == school_id))
    )
    student = result.scalars().first()
    if not student:
        raise NotFoundError("Student", student_id)
    return student
