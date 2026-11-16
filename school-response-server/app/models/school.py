"""
app/models/school.py
=====================
School, AcademicYear, Class, Section database models.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    Boolean,
    Date,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import SchoolStatus

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.student import Student
    from app.models.card import Card
    from app.models.quiz import QuestionSet, QuizSession
    from app.models.audit import AuditLog


class School(Base, TimestampMixin):
    """
    Top-level tenant. Every piece of data belongs to exactly one school.
    school_code is a short human-readable identifier (e.g. "DEMO-HS").
    """
    __tablename__ = "schools"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    school_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(254), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    status: Mapped[SchoolStatus] = mapped_column(
        SAEnum(SchoolStatus, name="school_status_enum"), default=SchoolStatus.ACTIVE, nullable=False
    )

    # Relationships
    academic_years: Mapped[List["AcademicYear"]] = relationship(back_populates="school", cascade="all, delete-orphan")
    users: Mapped[List["User"]] = relationship(back_populates="school", cascade="all, delete-orphan")
    students: Mapped[List["Student"]] = relationship(back_populates="school", cascade="all, delete-orphan")
    cards: Mapped[List["Card"]] = relationship(back_populates="school", cascade="all, delete-orphan")
    classes: Mapped[List["Class"]] = relationship(back_populates="school", cascade="all, delete-orphan")
    question_sets: Mapped[List["QuestionSet"]] = relationship(back_populates="school", cascade="all, delete-orphan")
    audit_logs: Mapped[List["AuditLog"]] = relationship(back_populates="school", cascade="all, delete-orphan")


class AcademicYear(Base):
    __tablename__ = "academic_years"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    school_id: Mapped[int] = mapped_column(Integer, ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "2026-2027"
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    school: Mapped["School"] = relationship(back_populates="academic_years")
    classes: Mapped[List["Class"]] = relationship(back_populates="academic_year", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("school_id", "name", name="uq_academic_year_school_name"),
        Index("ix_academic_year_school_active", "school_id", "is_active"),
    )


class Class(Base):
    __tablename__ = "classes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    school_id: Mapped[int] = mapped_column(Integer, ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_year_id: Mapped[int] = mapped_column(Integer, ForeignKey("academic_years.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "Grade 10"
    grade: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # e.g. "10"
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    school: Mapped["School"] = relationship(back_populates="classes")
    academic_year: Mapped["AcademicYear"] = relationship(back_populates="classes")
    sections: Mapped[List["Section"]] = relationship(back_populates="class_", cascade="all, delete-orphan")
    students: Mapped[List["Student"]] = relationship(back_populates="class_")
    quiz_sessions: Mapped[List["QuizSession"]] = relationship(back_populates="class_")

    __table_args__ = (
        UniqueConstraint("school_id", "academic_year_id", "name", name="uq_class_school_year_name"),
    )


class Section(Base):
    __tablename__ = "sections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    class_id: Mapped[int] = mapped_column(Integer, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g. "A", "B"
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    class_: Mapped["Class"] = relationship(back_populates="sections")
    students: Mapped[List["Student"]] = relationship(back_populates="section")
    quiz_sessions: Mapped[List["QuizSession"]] = relationship(back_populates="section")

    __table_args__ = (
        UniqueConstraint("class_id", "name", name="uq_section_class_name"),
    )
