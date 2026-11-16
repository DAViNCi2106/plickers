"""app/schemas/school.py — School, AcademicYear, Class, Section schemas."""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import SchoolStatus


# ── School ─────────────────────────────────────────────────────────────────

class SchoolCreate(BaseModel):
    school_code: str = Field(..., min_length=2, max_length=32, pattern=r"^[A-Z0-9\-]+$")
    name: str = Field(..., min_length=2, max_length=200)
    address: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=30)


class SchoolUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    address: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=30)
    status: Optional[SchoolStatus] = None


class SchoolOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    school_code: str
    name: str
    address: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    status: SchoolStatus
    created_at: datetime
    updated_at: datetime


# ── Academic Year ──────────────────────────────────────────────────────────

class AcademicYearCreate(BaseModel):
    name: str = Field(..., max_length=100)
    start_date: date
    end_date: date
    is_active: bool = True


class AcademicYearOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    school_id: int
    name: str
    start_date: date
    end_date: date
    is_active: bool
    created_at: datetime


# ── Class ──────────────────────────────────────────────────────────────────

class ClassCreate(BaseModel):
    academic_year_id: int
    name: str = Field(..., max_length=100)
    grade: Optional[str] = Field(None, max_length=20)


class ClassOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    school_id: int
    academic_year_id: int
    name: str
    grade: Optional[str]
    created_at: datetime


# ── Section ────────────────────────────────────────────────────────────────

class SectionCreate(BaseModel):
    name: str = Field(..., max_length=50)


class SectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    class_id: int
    name: str
    created_at: datetime
