"""
app/schemas/common.py
=====================
Shared response envelopes and base schemas.
"""
from __future__ import annotations

from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Standard success envelope."""
    success: bool = True
    data: Optional[T] = None
    message: Optional[str] = None


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated list response."""
    success: bool = True
    data: List[T]
    total: int
    page: int
    per_page: int
    pages: int


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail


class ImportError_(BaseModel):
    row: int
    reason: str


class ImportSummary(BaseModel):
    total_records: int
    successful: int
    failed: int
    errors: List[ImportError_]
