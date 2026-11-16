"""app/schemas/quiz.py — QuestionSet, Question, QuizSession, Response schemas."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AnswerLetter, QuestionSetStatus, QuizSessionStatus


# ── Question Set ───────────────────────────────────────────────────────────

class QuestionSetCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    subject: Optional[str] = Field(None, max_length=100)
    grade: Optional[str] = Field(None, max_length=20)


class QuestionSetUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=200)
    description: Optional[str] = None
    subject: Optional[str] = Field(None, max_length=100)
    grade: Optional[str] = Field(None, max_length=20)
    status: Optional[QuestionSetStatus] = None


class QuestionSetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    school_id: int
    teacher_id: int
    title: str
    description: Optional[str]
    subject: Optional[str]
    grade: Optional[str]
    status: QuestionSetStatus
    created_at: datetime
    updated_at: datetime
    question_count: Optional[int] = None


# ── Question ───────────────────────────────────────────────────────────────

class QuestionCreate(BaseModel):
    question_text: str = Field(..., min_length=1)
    option_a: str = Field(..., min_length=1, max_length=500)
    option_b: str = Field(..., min_length=1, max_length=500)
    option_c: str = Field(..., min_length=1, max_length=500)
    option_d: str = Field(..., min_length=1, max_length=500)
    correct_answer: Optional[AnswerLetter] = None
    marks: int = Field(default=1, ge=1, le=100)


class QuestionUpdate(BaseModel):
    question_text: Optional[str] = None
    option_a: Optional[str] = None
    option_b: Optional[str] = None
    option_c: Optional[str] = None
    option_d: Optional[str] = None
    correct_answer: Optional[AnswerLetter] = None
    marks: Optional[int] = Field(None, ge=1, le=100)


class QuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question_set_id: int
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_answer: Optional[AnswerLetter] = None
    marks: int
    created_at: datetime


class QuestionSetDetailOut(QuestionSetOut):
    questions: List[QuestionOut] = []


# ── Quiz Session ───────────────────────────────────────────────────────────

class QuizSessionCreate(BaseModel):
    question_set_id: int
    class_id: Optional[int] = None
    section_id: Optional[int] = None


class QuizSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question_set_id: int
    teacher_id: int
    class_id: Optional[int]
    section_id: Optional[int]
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    status: QuizSessionStatus
    created_at: datetime


# ── Scanner response ───────────────────────────────────────────────────────

class ScannerResponseRequest(BaseModel):
    """
    Payload sent by the computer-vision scanner after detecting a card.
    Matches the existing scanner output format:
      card_id (marker_id) → rotation → answer
    """
    quiz_session_id: int
    question_id: int
    marker_id: int = Field(..., ge=1, le=249,
                           description="ArUco marker ID detected by scanner")
    rotation: int = Field(..., description="Card rotation: 0, 90, 180, or 270")
    answer: AnswerLetter
    detected_at: datetime


class ScannerResponseOut(BaseModel):
    success: bool = True
    student_id: int
    card_id: int
    answer: AnswerLetter
    is_correct: bool
    marks_obtained: int


# ── Response ───────────────────────────────────────────────────────────────

class ResponseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    quiz_session_id: int
    question_id: int
    student_id: int
    card_id: int
    answer: AnswerLetter
    is_correct: bool
    marks_obtained: int
    rotation: Optional[int]
    answered_at: datetime


# ── Student Score ──────────────────────────────────────────────────────────

class StudentScoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    quiz_session_id: int
    student_id: int
    total_questions: int
    correct_answers: int
    incorrect_answers: int
    score: int
    percentage: float
    created_at: datetime


# ── Dashboard summary ──────────────────────────────────────────────────────

class QuizDashboardOut(BaseModel):
    """Live dashboard data for teacher."""
    quiz_session_id: int
    status: QuizSessionStatus
    total_students: int
    responses_received: int
    answer_counts: dict  # {"A": 7, "B": 18, "C": 5, "D": 2}
    responses: List[ResponseOut]
