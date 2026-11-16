"""
app/models/enums.py
====================
All Python Enum types used across the system.
"""
from __future__ import annotations

import enum


class UserRole(str, enum.Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    SCHOOL_ADMIN = "SCHOOL_ADMIN"
    TEACHER = "TEACHER"
    STUDENT = "STUDENT"


class SchoolStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class StudentStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    TRANSFERRED = "transferred"


class CardStatus(str, enum.Enum):
    AVAILABLE = "available"
    ASSIGNED = "assigned"
    LOST = "lost"
    DISABLED = "disabled"


class QuestionSetStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class QuizSessionStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    PAUSED = "paused"
    ENDED = "ended"


class AnswerLetter(str, enum.Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class AuditAction(str, enum.Enum):
    # Auth
    USER_LOGIN = "USER_LOGIN"
    USER_LOGIN_FAILED = "USER_LOGIN_FAILED"
    USER_LOGOUT = "USER_LOGOUT"
    # Students
    STUDENT_CREATED = "STUDENT_CREATED"
    STUDENT_UPDATED = "STUDENT_UPDATED"
    STUDENT_DELETED = "STUDENT_DELETED"
    STUDENTS_IMPORTED = "STUDENTS_IMPORTED"
    # Cards
    CARD_CREATED = "CARD_CREATED"
    CARD_ASSIGNED = "CARD_ASSIGNED"
    CARD_UNASSIGNED = "CARD_UNASSIGNED"
    CARD_DISABLED = "CARD_DISABLED"
    CARD_REPLACED = "CARD_REPLACED"
    # Teachers
    TEACHER_CREATED = "TEACHER_CREATED"
    TEACHER_UPDATED = "TEACHER_UPDATED"
    # Quiz
    QUIZ_CREATED = "QUIZ_CREATED"
    QUIZ_STARTED = "QUIZ_STARTED"
    QUIZ_ENDED = "QUIZ_ENDED"
    RESPONSE_SUBMITTED = "RESPONSE_SUBMITTED"
