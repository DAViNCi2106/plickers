"""app/schemas/user.py — User and Teacher schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import UserRole


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=150)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    role: UserRole
    school_id: Optional[int] = None


class UserOut(BaseModel):
    """Password hash is NEVER included in this schema."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    school_id: Optional[int]
    username: str
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TeacherCreate(BaseModel):
    user_id: int
    employee_id: Optional[str] = Field(None, max_length=50)
    first_name: str = Field(..., max_length=100)
    last_name: str = Field(..., max_length=100)
    phone: Optional[str] = Field(None, max_length=30)


class TeacherCreateFull(BaseModel):
    """Create user + teacher profile in one request."""
    username: str = Field(..., min_length=3, max_length=150)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    employee_id: Optional[str] = Field(None, max_length=50)
    first_name: str = Field(..., max_length=100)
    last_name: str = Field(..., max_length=100)
    phone: Optional[str] = Field(None, max_length=30)


class TeacherOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    school_id: int
    employee_id: Optional[str]
    first_name: str
    last_name: str
    phone: Optional[str]
    created_at: datetime

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class TeacherUpdate(BaseModel):
    """Partial update schema for teacher profile."""
    employee_id: Optional[str] = Field(None, max_length=50)
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=30)
