"""app/schemas/student.py — Student schemas."""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import StudentStatus


class StudentCreate(BaseModel):
    class_id: Optional[int] = None
    section_id: Optional[int] = None
    student_code: str = Field(..., max_length=20, pattern=r"^STU\d{3,6}$",
                              description="Matches existing format: STU001 … STU999")
    roll_number: Optional[int] = Field(None, ge=1)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    date_of_birth: Optional[date] = None


class StudentUpdate(BaseModel):
    class_id: Optional[int] = None
    section_id: Optional[int] = None
    roll_number: Optional[int] = Field(None, ge=1)
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    date_of_birth: Optional[date] = None
    status: Optional[StudentStatus] = None


class StudentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    school_id: int
    class_id: Optional[int]
    section_id: Optional[int]
    student_code: str
    roll_number: Optional[int]
    first_name: str
    last_name: str
    email: Optional[str]
    date_of_birth: Optional[date]
    status: StudentStatus
    created_at: datetime
    updated_at: datetime

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
