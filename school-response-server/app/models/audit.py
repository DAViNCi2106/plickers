"""
app/models/audit.py
====================
Audit log table — records all sensitive and important operations.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import AuditAction

if TYPE_CHECKING:
    from app.models.school import School
    from app.models.user import User


class AuditLog(Base):
    """
    Immutable audit trail — records are never deleted.
    Sensitive fields (passwords, tokens) must NEVER appear in metadata.
    """
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    school_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("schools.id", ondelete="SET NULL"), nullable=True, index=True
    )
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[AuditAction] = mapped_column(
        SAEnum(AuditAction, name="audit_action_enum"), nullable=False, index=True
    )
    entity_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    entity_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)  # IPv4 or IPv6
    timestamp: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False, index=True)
    # Extra contextual data — NEVER include passwords/tokens/hashes
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)

    school: Mapped[Optional["School"]] = relationship(back_populates="audit_logs")
    user: Mapped[Optional["User"]] = relationship(back_populates="audit_logs")

    __table_args__ = (
        Index("ix_audit_school_timestamp", "school_id", "timestamp"),
        Index("ix_audit_user_action", "user_id", "action"),
    )
