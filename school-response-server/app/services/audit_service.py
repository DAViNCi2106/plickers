"""
app/services/audit_service.py
=============================
Thin service for writing audit log records.
IMPORTANT: never pass password, hash, or token data into metadata.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.enums import AuditAction

logger = logging.getLogger(__name__)


async def write_audit_log(
    db: AsyncSession,
    *,
    action: AuditAction,
    school_id: Optional[int] = None,
    user_id: Optional[int] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Write an audit record. Runs in the caller's transaction so it rolls
    back if the surrounding operation fails.
    """
    # Safety: strip any accidentally-included sensitive keys
    safe_metadata = _sanitise(metadata)

    log = AuditLog(
        action=action,
        school_id=school_id,
        user_id=user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        ip_address=ip_address,
        metadata_=safe_metadata,
    )
    db.add(log)
    # Flush so the record is visible but the caller can still rollback
    await db.flush()


_FORBIDDEN = frozenset(
    {"password", "password_hash", "token", "secret", "hash", "authorization"}
)


def _sanitise(data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not data:
        return data
    return {k: "[REDACTED]" if k.lower() in _FORBIDDEN else v for k, v in data.items()}
