"""
app/models/user.py
==================
User accounts and Teacher profiles.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    Boolean,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import UserRole

if TYPE_CHECKING:
    from app.models.school import School
    from app.models.quiz import QuestionSet, QuizSession
    from app.models.audit import AuditLog


class User(Base, TimestampMixin):
    """
    Authentication record for all human users of the system.
    school_id is NULL only for SUPER_ADMIN accounts.
    Role is ALWAYS determined server-side — never trusted from the frontend.
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    school_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("schools.id", ondelete="CASCADE"), nullable=True, index=True
    )
    username: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(254), nullable=False)
    # password_hash is NEVER returned by any API endpoint
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role_enum"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    school: Mapped[Optional["School"]] = relationship(back_populates="users")
    teacher_profile: Mapped[Optional["Teacher"]] = relationship(back_populates="user", uselist=False)
    question_sets: Mapped[List["QuestionSet"]] = relationship(back_populates="teacher")
    quiz_sessions: Mapped[List["QuizSession"]] = relationship(back_populates="teacher")
    audit_logs: Mapped[List["AuditLog"]] = relationship(back_populates="user")

    __table_args__ = (
        UniqueConstraint("school_id", "username", name="uq_user_school_username"),
        UniqueConstraint("school_id", "email", name="uq_user_school_email"),
        Index("ix_user_email", "email"),
        Index("ix_user_school_role", "school_id", "role"),
    )


class Teacher(Base):
    """
    Extended profile for users with role=TEACHER or SCHOOL_ADMIN.
    employee_id is unique within a school.
    """
    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    school_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True
    )
    employee_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="teacher_profile")

    __table_args__ = (
        UniqueConstraint("school_id", "employee_id", name="uq_teacher_school_employee_id"),
        Index("ix_teacher_school", "school_id"),
    )
