"""
app/models/quiz.py
==================
QuestionSet, Question, QuizSession, Response, StudentScore models.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import AnswerLetter, QuestionSetStatus, QuizSessionStatus

if TYPE_CHECKING:
    from app.models.school import School, Class, Section
    from app.models.user import User
    from app.models.student import Student
    from app.models.card import Card


class QuestionSet(Base, TimestampMixin):
    __tablename__ = "question_sets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    school_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True
    )
    teacher_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    subject: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    grade: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    status: Mapped[QuestionSetStatus] = mapped_column(
        SAEnum(QuestionSetStatus, name="question_set_status_enum"),
        default=QuestionSetStatus.DRAFT,
        nullable=False,
    )

    school: Mapped["School"] = relationship(back_populates="question_sets")
    teacher: Mapped["User"] = relationship(back_populates="question_sets")
    questions: Mapped[List["Question"]] = relationship(
        back_populates="question_set", cascade="all, delete-orphan", order_by="Question.id"
    )
    quiz_sessions: Mapped[List["QuizSession"]] = relationship(back_populates="question_set")


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    question_set_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("question_sets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    option_a: Mapped[str] = mapped_column(String(500), nullable=False)
    option_b: Mapped[str] = mapped_column(String(500), nullable=False)
    option_c: Mapped[str] = mapped_column(String(500), nullable=False)
    option_d: Mapped[str] = mapped_column(String(500), nullable=False)
    correct_answer: Mapped[Optional[AnswerLetter]] = mapped_column(
        SAEnum(AnswerLetter, name="answer_letter_enum"), nullable=True
    )
    marks: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    question_set: Mapped["QuestionSet"] = relationship(back_populates="questions")
    responses: Mapped[List["Response"]] = relationship(back_populates="question")


class QuizSession(Base):
    """
    A live quiz event: a teacher runs a question set for a class/section.
    """
    __tablename__ = "quiz_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    question_set_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("question_sets.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    teacher_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    class_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("classes.id", ondelete="SET NULL"), nullable=True, index=True
    )
    section_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("sections.id", ondelete="SET NULL"), nullable=True, index=True
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[QuizSessionStatus] = mapped_column(
        SAEnum(QuizSessionStatus, name="quiz_session_status_enum"),
        default=QuizSessionStatus.PENDING,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    question_set: Mapped["QuestionSet"] = relationship(back_populates="quiz_sessions")
    teacher: Mapped["User"] = relationship(back_populates="quiz_sessions")
    class_: Mapped[Optional["Class"]] = relationship(back_populates="quiz_sessions")
    section: Mapped[Optional["Section"]] = relationship(back_populates="quiz_sessions")
    responses: Mapped[List["Response"]] = relationship(
        back_populates="quiz_session", cascade="all, delete-orphan"
    )
    student_scores: Mapped[List["StudentScore"]] = relationship(
        back_populates="quiz_session", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_quiz_session_status", "status"),)


class Response(Base):
    """
    A single student's answer for a single question in a session.
    Duplicate prevention: (quiz_session_id, question_id, student_id) UNIQUE.
    """
    __tablename__ = "responses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    quiz_session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("quiz_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    student_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    card_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("cards.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    answer: Mapped[AnswerLetter] = mapped_column(
        SAEnum(AnswerLetter, name="answer_letter_enum"), nullable=False
    )
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    marks_obtained: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # rotation received from the scanner (0/90/180/270)
    rotation: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    answered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    quiz_session: Mapped["QuizSession"] = relationship(back_populates="responses")
    question: Mapped["Question"] = relationship(back_populates="responses")
    student: Mapped["Student"] = relationship(back_populates="responses")
    card: Mapped["Card"] = relationship(back_populates="responses")

    __table_args__ = (
        # Prevent duplicate submissions per student per question per session
        UniqueConstraint(
            "quiz_session_id", "question_id", "student_id",
            name="uq_response_session_question_student",
        ),
        Index("ix_response_session_student", "quiz_session_id", "student_id"),
    )


class StudentScore(Base):
    """Aggregated per-student score for a completed quiz session."""

    __tablename__ = "student_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    quiz_session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("quiz_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    student_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    total_questions: Mapped[int] = mapped_column(Integer, nullable=False)
    correct_answers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    incorrect_answers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # sum of marks_obtained
    percentage: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    quiz_session: Mapped["QuizSession"] = relationship(back_populates="student_scores")
    student: Mapped["Student"] = relationship(back_populates="scores")

    __table_args__ = (
        UniqueConstraint("quiz_session_id", "student_id", name="uq_score_session_student"),
    )
