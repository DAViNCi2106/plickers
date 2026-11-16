"""
app/models/card.py
==================
Physical ArUco response card models.

Key design:
  card_number == marker_id  (e.g. card 17 uses ArUco marker ID 17)
  Both are UNIQUE within a school.
  StudentCard enforces only one active assignment per student AND per card.
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
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import CardStatus

if TYPE_CHECKING:
    from app.models.school import School
    from app.models.student import Student
    from app.models.quiz import Response


class Card(Base):
    """
    Represents one physical printed ArUco card.

    card_number  → human-readable number on the card (e.g. 17)
    marker_id    → ArUco marker ID baked into the card (equals card_number)
    Both are unique within a school — no two active cards share a marker_id.
    """
    __tablename__ = "cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    school_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Card number printed on the physical card — e.g. 17
    card_number: Mapped[int] = mapped_column(Integer, nullable=False)
    # ArUco marker ID — equals card_number in this system
    marker_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    status: Mapped[CardStatus] = mapped_column(
        SAEnum(CardStatus, name="card_status_enum"),
        default=CardStatus.AVAILABLE,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    school: Mapped["School"] = relationship(back_populates="cards")
    student_assignments: Mapped[List["StudentCard"]] = relationship(
        back_populates="card", cascade="all, delete-orphan"
    )
    responses: Mapped[List["Response"]] = relationship(back_populates="card")

    __table_args__ = (
        # card_number unique per school
        UniqueConstraint("school_id", "card_number", name="uq_card_school_number"),
        # marker_id unique per school (CRITICAL — prevents two cards being detected as the same)
        UniqueConstraint("school_id", "marker_id", name="uq_card_school_marker"),
        Index("ix_card_school_marker", "school_id", "marker_id"),
        Index("ix_card_school_number", "school_id", "card_number"),
    )


class StudentCard(Base):
    """
    Assignment junction: which student holds which physical card.

    Business rules (enforced by DB + service layer):
      1. One active card per student at a time.
      2. One active student per card at a time.
      3. When a card is replaced, the old assignment gets unassigned_at set,
         is_active = False, and the card status = LOST / DISABLED.
    """
    __tablename__ = "student_cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    card_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("cards.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assigned_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    unassigned_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    student: Mapped["Student"] = relationship(back_populates="card_assignments")
    card: Mapped["Card"] = relationship(back_populates="student_assignments")

    __table_args__ = (
        # Only one active assignment per student
        Index(
            "uix_student_active_card",
            "student_id",
            unique=True,
            postgresql_where="is_active = true",
        ),
        # Only one active assignment per card
        Index(
            "uix_card_active_student",
            "card_id",
            unique=True,
            postgresql_where="is_active = true",
        ),
    )
