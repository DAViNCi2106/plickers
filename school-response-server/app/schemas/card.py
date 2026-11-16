"""app/schemas/card.py — Card and StudentCard schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import CardStatus


class CardCreate(BaseModel):
    card_number: int = Field(..., ge=1, le=249,
                             description="ArUco DICT_6X6_250 supports IDs 0-249")
    # marker_id equals card_number in this system
    marker_id: Optional[int] = Field(None, ge=1, le=249)

    def model_post_init(self, __context):
        # Enforce: marker_id always equals card_number
        if self.marker_id is None:
            object.__setattr__(self, "marker_id", self.card_number)


class CardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    school_id: int
    card_number: int
    marker_id: int
    status: CardStatus
    created_at: datetime


class CardAssignRequest(BaseModel):
    student_id: int


class CardUnassignRequest(BaseModel):
    reason: Optional[str] = Field(None, max_length=200)


class CardReplaceRequest(BaseModel):
    new_card_id: int
    reason: Optional[str] = Field(None, max_length=200)


class StudentCardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    card_id: int
    assigned_at: datetime
    unassigned_at: Optional[datetime]
    is_active: bool


class CardAssignmentOut(BaseModel):
    """Full view: card + student details."""
    card: CardOut
    student_id: int
    student_code: str
    student_name: str
    assigned_at: datetime
    is_active: bool
