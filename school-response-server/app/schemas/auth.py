"""app/schemas/auth.py — Authentication request/response schemas."""
from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class LoginRequest(BaseModel):
    username: str | None = Field(None, max_length=150)
    email: str | None = Field(None, max_length=150)
    password: str = Field(..., min_length=6, max_length=128)

    @model_validator(mode="after")
    def validate_identifier(self) -> LoginRequest:
        if not self.username and not self.email:
            raise ValueError("Either username or email must be provided")
        if not self.username:
            self.username = self.email
        return self


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user_id: int
    role: str
    school_id: int | None = None


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=6, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)
