"""
app/services/card_service.py
=============================
Card management business logic:
  - create, import, assign, unassign, replace, disable
  - search by marker_id
  - student import from Excel/CSV
"""
from __future__ import annotations

import io
import logging
from datetime import datetime, timezone
from typing import List, Optional

import pandas as pd
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BadRequestError,
    CardAlreadyAssignedError,
    CardNotAssignedError,
    ConflictError,
    DuplicateError,
    NotFoundError,
    StudentAlreadyHasCardError,
)
from app.models.card import Card, StudentCard
from app.models.enums import AuditAction, CardStatus, StudentStatus
from app.models.student import Student
from app.schemas.card import CardCreate
from app.schemas.common import ImportError_, ImportSummary
from app.services.audit_service import write_audit_log

logger = logging.getLogger(__name__)

# Columns expected in the Excel/CSV import file
# Matches the existing 50_sample_students_plickers.xlsx format
REQUIRED_COLUMNS = {"Student Name", "Student ID", "Card ID"}
OPTIONAL_COLUMNS = {"S.No", "Answer", "Saved At"}


async def create_card(
    db: AsyncSession,
    school_id: int,
    data: CardCreate,
    user_id: Optional[int] = None,
) -> Card:
    # marker_id must equal card_number
    marker_id = data.card_number

    # Check uniqueness within school
    existing = await db.execute(
        select(Card).where(
            and_(Card.school_id == school_id, Card.marker_id == marker_id)
        )
    )
    if existing.scalars().first():
        raise DuplicateError("Card", f"marker_id {marker_id}")

    card = Card(school_id=school_id, card_number=data.card_number, marker_id=marker_id)
    db.add(card)
    await db.flush()

    await write_audit_log(
        db,
        action=AuditAction.CARD_CREATED,
        school_id=school_id,
        user_id=user_id,
        entity_type="Card",
        entity_id=card.id,
        metadata={"card_number": data.card_number, "marker_id": marker_id},
    )
    return card


async def assign_card(
    db: AsyncSession,
    school_id: int,
    card_id: int,
    student_id: int,
    user_id: Optional[int] = None,
) -> StudentCard:
    # Verify card belongs to this school
    card = await _get_card(db, school_id, card_id)

    if card.status == CardStatus.DISABLED:
        raise BadRequestError("Cannot assign a disabled card", "CARD_DISABLED")

    # Check card not already actively assigned
    existing_card_assign = await db.execute(
        select(StudentCard).where(
            and_(StudentCard.card_id == card_id, StudentCard.is_active == True)
        )
    )
    if existing_card_assign.scalars().first():
        raise CardAlreadyAssignedError()

    # Check student does not already have an active card
    existing_student_assign = await db.execute(
        select(StudentCard).where(
            and_(StudentCard.student_id == student_id, StudentCard.is_active == True)
        )
    )
    if existing_student_assign.scalars().first():
        raise StudentAlreadyHasCardError()

    assignment = StudentCard(student_id=student_id, card_id=card_id)
    db.add(assignment)
    card.status = CardStatus.ASSIGNED
    await db.flush()

    await write_audit_log(
        db,
        action=AuditAction.CARD_ASSIGNED,
        school_id=school_id,
        user_id=user_id,
        entity_type="StudentCard",
        entity_id=assignment.id,
        metadata={"card_id": card_id, "student_id": student_id},
    )
    return assignment


async def unassign_card(
    db: AsyncSession,
    school_id: int,
    card_id: int,
    user_id: Optional[int] = None,
    reason: Optional[str] = None,
) -> StudentCard:
    card = await _get_card(db, school_id, card_id)

    result = await db.execute(
        select(StudentCard).where(
            and_(StudentCard.card_id == card_id, StudentCard.is_active == True)
        )
    )
    assignment: Optional[StudentCard] = result.scalars().first()
    if not assignment:
        raise CardNotAssignedError()

    assignment.is_active = False
    assignment.unassigned_at = datetime.now(timezone.utc)
    card.status = CardStatus.AVAILABLE
    await db.flush()

    await write_audit_log(
        db,
        action=AuditAction.CARD_UNASSIGNED,
        school_id=school_id,
        user_id=user_id,
        entity_type="StudentCard",
        entity_id=assignment.id,
        metadata={"card_id": card_id, "reason": reason},
    )
    return assignment


async def disable_card(
    db: AsyncSession,
    school_id: int,
    card_id: int,
    user_id: Optional[int] = None,
) -> Card:
    card = await _get_card(db, school_id, card_id)
    # Unassign if active
    result = await db.execute(
        select(StudentCard).where(
            and_(StudentCard.card_id == card_id, StudentCard.is_active == True)
        )
    )
    if (assignment := result.scalars().first()):
        assignment.is_active = False
        assignment.unassigned_at = datetime.now(timezone.utc)

    card.status = CardStatus.DISABLED
    await db.flush()
    await write_audit_log(
        db, action=AuditAction.CARD_DISABLED, school_id=school_id, user_id=user_id,
        entity_type="Card", entity_id=card.id,
    )
    return card


async def replace_lost_card(
    db: AsyncSession,
    school_id: int,
    old_card_id: int,
    new_card_id: int,
    user_id: Optional[int] = None,
    reason: Optional[str] = None,
) -> StudentCard:
    """Mark old card as LOST, unassign it, assign new card to same student."""
    old_card = await _get_card(db, school_id, old_card_id)
    new_card = await _get_card(db, school_id, new_card_id)

    # Find the student from the old assignment
    result = await db.execute(
        select(StudentCard).where(
            and_(StudentCard.card_id == old_card_id, StudentCard.is_active == True)
        )
    )
    old_assign: Optional[StudentCard] = result.scalars().first()
    if not old_assign:
        raise CardNotAssignedError()

    student_id = old_assign.student_id

    # Deactivate old assignment
    old_assign.is_active = False
    old_assign.unassigned_at = datetime.now(timezone.utc)
    old_card.status = CardStatus.LOST

    # Create new assignment
    new_assign = StudentCard(student_id=student_id, card_id=new_card_id)
    db.add(new_assign)
    new_card.status = CardStatus.ASSIGNED
    await db.flush()

    await write_audit_log(
        db, action=AuditAction.CARD_REPLACED, school_id=school_id, user_id=user_id,
        entity_type="StudentCard", entity_id=new_assign.id,
        metadata={"old_card_id": old_card_id, "new_card_id": new_card_id,
                  "student_id": student_id, "reason": reason},
    )
    return new_assign


async def get_card_by_marker(
    db: AsyncSession, school_id: int, marker_id: int
) -> Card:
    result = await db.execute(
        select(Card).where(
            and_(Card.school_id == school_id, Card.marker_id == marker_id)
        )
    )
    card = result.scalars().first()
    if not card:
        raise NotFoundError("Card", f"marker_id={marker_id}")
    return card


# ── Excel / CSV bulk import ────────────────────────────────────────────────

def _find_column(columns: List[str], candidates: List[str]) -> Optional[str]:
    """Find matching column name case-insensitively and ignoring punctuation/spaces."""
    norm_map = {c.strip().lower().replace("_", " ").replace(".", ""): c for c in columns}
    for cand in candidates:
        cand_norm = cand.strip().lower().replace("_", " ").replace(".", "")
        if cand_norm in norm_map:
            return norm_map[cand_norm]
    return None


async def import_students_from_file(
    db: AsyncSession,
    school_id: int,
    class_id: Optional[int],
    section_id: Optional[int],
    file_bytes: bytes,
    filename: str,
    user_id: Optional[int] = None,
) -> ImportSummary:
    """
    Parse Excel (.xlsx/.xls) or CSV file and bulk-import students.
    Automatically allots unique Plickers cards to any students without one!

    Supported columns (case-insensitive & flexible):
      - Student Name / Name / Full Name (Required)
      - Student ID / Student Code / ID (Optional - auto-generated if missing)
      - Card ID / Card No / Card Number (Optional - auto-allotted unique card if missing)
      - Roll Number / Roll No / Roll (Optional)
      - Email (Optional)
    """
    try:
        df = _read_file(file_bytes, filename)
    except Exception as exc:
        raise BadRequestError(f"Cannot read file: {exc}", "FILE_READ_ERROR")

    if df.empty:
        raise BadRequestError("Uploaded file contains no rows.", "EMPTY_FILE")

    cols = list(df.columns)
    name_col = _find_column(cols, ["Student Name", "Name", "Full Name", "Student", "Pupil Name"])
    if not name_col:
        raise BadRequestError(
            f"Could not find Student Name column in file. Found columns: {cols}",
            "MISSING_NAME_COLUMN",
        )

    code_col = _find_column(cols, ["Student ID", "Student Code", "ID", "Code", "Admission No"])
    card_col = _find_column(cols, ["Card ID", "Card No", "Card Number", "Card", "Plicker Card", "Plickers Card"])
    roll_col = _find_column(cols, ["Roll No", "Roll Number", "Roll", "S.No", "SNo"])
    email_col = _find_column(cols, ["Email", "Email Address", "Mail"])

    errors: List[ImportError_] = []
    successful = 0

    # Pre-load existing students and cards for this school
    existing_codes_res = await db.execute(
        select(Student.student_code).where(Student.school_id == school_id)
    )
    existing_codes = set(existing_codes_res.scalars().all())

    # Find highest numeric suffix in existing STU###
    next_stu_num = 1
    for code in existing_codes:
        if code.startswith("STU") and code[3:].isdigit():
            next_stu_num = max(next_stu_num, int(code[3:]) + 1)

    # Active card assignments in this school (card_number / marker_id)
    active_cards_res = await db.execute(
        select(Card.card_number)
        .join(StudentCard, StudentCard.card_id == Card.id)
        .where(and_(Card.school_id == school_id, StudentCard.is_active == True))
    )
    assigned_card_nums = set(active_cards_res.scalars().all())

    # Pre-load all cards (card_number -> Card object)
    all_cards_res = await db.execute(
        select(Card).where(Card.school_id == school_id)
    )
    cards_by_number: dict[int, Card] = {c.card_number: c for c in all_cards_res.scalars().all()}

    # Track available card number pool (1..249)
    next_card_num = 1
    def get_next_available_card():
        nonlocal next_card_num
        while next_card_num in assigned_card_nums:
            next_card_num += 1
        card = next_card_num
        next_card_num += 1
        return card

    seen_codes: set[str] = set()
    seen_cards: set[int] = set()

    for idx, row in df.iterrows():
        row_num = int(idx) + 2  # 1-indexed, +1 for header
        try:
            name_raw = row[name_col]
            if pd.isna(name_raw) or not str(name_raw).strip():
                continue  # skip completely blank rows
            name = str(name_raw).strip()

            # Resolve student code (auto-generate if missing)
            student_id_str = ""
            if code_col and not pd.isna(row[code_col]) and str(row[code_col]).strip():
                candidate_code = str(row[code_col]).strip()
                # If numeric or simple string, format nicely
                if candidate_code.isdigit():
                    student_id_str = f"STU{int(candidate_code):03d}"
                else:
                    student_id_str = candidate_code
            
            if not student_id_str:
                while f"STU{next_stu_num:03d}" in existing_codes or f"STU{next_stu_num:03d}" in seen_codes:
                    next_stu_num += 1
                student_id_str = f"STU{next_stu_num:03d}"
                next_stu_num += 1

            if student_id_str in seen_codes:
                raise ValueError(f"Duplicate Student ID in file: {student_id_str}")
            if student_id_str in existing_codes:
                raise ValueError(f"Student ID {student_id_str} already exists in school")

            # Resolve card number (auto-allot if missing)
            target_card_num = None
            if card_col and not pd.isna(row[card_col]):
                try:
                    c_val = int(row[card_col])
                    if c_val in assigned_card_nums or c_val in seen_cards:
                        # Auto-assign next available unique card if specified card is taken
                        target_card_num = get_next_available_card()
                    else:
                        target_card_num = c_val
                except (ValueError, TypeError):
                    target_card_num = get_next_available_card()
            else:
                target_card_num = get_next_available_card()

            seen_codes.add(student_id_str)
            seen_cards.add(target_card_num)
            assigned_card_nums.add(target_card_num)

            # Split name
            parts = name.split()
            first = parts[0]
            last = " ".join(parts[1:]) if len(parts) > 1 else "."

            # Optional roll number
            roll_num = None
            if roll_col and not pd.isna(row[roll_col]):
                try:
                    roll_num = int(row[roll_col])
                except (ValueError, TypeError):
                    pass

            # Optional email
            email_val = None
            if email_col and not pd.isna(row[email_col]) and "@" in str(row[email_col]):
                email_val = str(row[email_col]).strip()

            # Create Student
            student = Student(
                school_id=school_id,
                class_id=class_id,
                section_id=section_id,
                student_code=student_id_str,
                first_name=first,
                last_name=last,
                roll_number=roll_num,
                email=email_val,
                status=StudentStatus.ACTIVE,
            )
            db.add(student)
            await db.flush()

            # Ensure Card exists
            card = cards_by_number.get(target_card_num)
            if not card:
                card = Card(
                    school_id=school_id,
                    card_number=target_card_num,
                    marker_id=target_card_num,
                    status=CardStatus.ASSIGNED,
                )
                db.add(card)
                await db.flush()
                cards_by_number[target_card_num] = card
            else:
                card.status = CardStatus.ASSIGNED

            # Create StudentCard assignment
            assignment = StudentCard(student_id=student.id, card_id=card.id, is_active=True)
            db.add(assignment)
            await db.flush()

            existing_codes.add(student_id_str)
            successful += 1

        except Exception as exc:
            errors.append(ImportError_(row=row_num, reason=str(exc)))

    total = len(df)
    summary = ImportSummary(
        total_records=total,
        successful=successful,
        failed=len(errors),
        errors=errors,
    )

    await write_audit_log(
        db, action=AuditAction.STUDENTS_IMPORTED, school_id=school_id, user_id=user_id,
        metadata={"total": total, "successful": successful, "failed": len(errors)},
    )

    return summary



# ── Helpers ────────────────────────────────────────────────────────────────

async def _get_card(db: AsyncSession, school_id: int, card_id: int) -> Card:
    result = await db.execute(
        select(Card).where(and_(Card.id == card_id, Card.school_id == school_id))
    )
    card = result.scalars().first()
    if not card:
        raise NotFoundError("Card", card_id)
    return card


def _read_file(data: bytes, filename: str) -> pd.DataFrame:
    if filename.lower().endswith(".csv"):
        return pd.read_csv(io.BytesIO(data))
    elif filename.lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(io.BytesIO(data))
    else:
        raise ValueError("Unsupported file type. Use .xlsx or .csv")


def _validate_columns(df: pd.DataFrame) -> None:
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise BadRequestError(
            f"Missing required columns: {missing}. "
            f"Expected: {REQUIRED_COLUMNS}",
            "INVALID_COLUMNS",
        )
