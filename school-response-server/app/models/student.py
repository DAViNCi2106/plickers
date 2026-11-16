"""
app/models/student.py
=====================
Student model.
student_code format: STU001 … STU999 (matching existing cards.json convention)
"""
from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    Date,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import StudentStatus

if TYPE_CHECKING:
    from app.models.school import School, Class, Section
    from app.models.card import StudentCard
    from app.models.quiz import Response, StudentScore


class Student(Base, TimestampMixin):
    """
    A student belongs to one school, one class, and one section.
    student_code (e.g. STU017) is unique within a school and maps directly
    to the existing cards.json student_id convention.
    roll_number is a human-assigned number, unique within section.
    """
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    school_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True
    )
    class_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("classes.id", ondelete="SET NULL"), nullable=True, index=True
    )
    section_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("sections.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # Matches "STU001" … "STU999" convention in cards.json
    student_code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    roll_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(254), nullable=True)
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[StudentStatus] = mapped_column(
        SAEnum(StudentStatus, name="student_status_enum"),
        default=StudentStatus.ACTIVE,
        nullable=False,
    )

    school: Mapped["School"] = relationship(back_populates="students")
    class_: Mapped[Optional["Class"]] = relationship(back_populates="students")
    section: Mapped[Optional["Section"]] = relationship(back_populates="students")
    card_assignments: Mapped[List["StudentCard"]] = relationship(back_populates="student", cascade="all, delete-orphan")
    responses: Mapped[List["Response"]] = relationship(back_populates="student")
    scores: Mapped[List["StudentScore"]] = relationship(back_populates="student")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def active_card(self) -> Optional["StudentCard"]:
        return next((c for c in self.card_assignments if c.is_active), None)

    __table_args__ = (
        UniqueConstraint("school_id", "student_code", name="uq_student_school_code"),
        Index("ix_student_school_code", "school_id", "student_code"),
        Index("ix_student_class_section", "class_id", "section_id"),
    )
