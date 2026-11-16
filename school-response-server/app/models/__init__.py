"""app/models/__init__.py — Import all models so Alembic auto-discovers them."""
from app.models.school import School, AcademicYear, Class, Section
from app.models.user import User, Teacher
from app.models.student import Student
from app.models.card import Card, StudentCard
from app.models.quiz import QuestionSet, Question, QuizSession, Response, StudentScore
from app.models.audit import AuditLog
from app.models.enums import (
    UserRole,
    SchoolStatus,
    StudentStatus,
    CardStatus,
    QuestionSetStatus,
    QuizSessionStatus,
    AnswerLetter,
    AuditAction,
)

__all__ = [
    "School", "AcademicYear", "Class", "Section",
    "User", "Teacher",
    "Student",
    "Card", "StudentCard",
    "QuestionSet", "Question", "QuizSession", "Response", "StudentScore",
    "AuditLog",
    "UserRole", "SchoolStatus", "StudentStatus", "CardStatus",
    "QuestionSetStatus", "QuizSessionStatus", "AnswerLetter", "AuditAction",
]
