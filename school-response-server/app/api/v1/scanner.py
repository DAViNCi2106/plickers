"""
app/api/v1/scanner.py
=====================
Two endpoints:
  POST /api/v1/scanner/responses      — submit a scanned response (already stored)
  POST /api/v1/scanner/detect-frame   — detect ArUco cards in a browser camera frame
"""
from __future__ import annotations

import base64
import logging
import os
import sys
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, require_teacher
from app.db.session import get_db
from app.schemas.quiz import ScannerResponseOut, ScannerResponseRequest
from app.services.quiz_service import get_quiz_dashboard, process_scanner_response
from app.websocket.manager import ws_manager

router = APIRouter(prefix="/scanner", tags=["Scanner"])
logger = logging.getLogger(__name__)

# Resolve the scanner/ directory once at module load
_HERE = os.path.dirname(os.path.abspath(__file__))              # app/api/v1
_SCANNER_DIR = os.path.normpath(os.path.join(_HERE, "..", "..", "..", "..", "scanner"))


def _ensure_scanner_on_path() -> None:
    if os.path.isdir(_SCANNER_DIR) and _SCANNER_DIR not in sys.path:
        sys.path.insert(0, _SCANNER_DIR)


# ── Submit scanner response ───────────────────────────────────────────────────

@router.post(
    "/responses",
    response_model=ScannerResponseOut,
    summary="Submit scanner response",
)
async def submit_response(
    body: ScannerResponseRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_teacher),
) -> ScannerResponseOut:
    school_id = user.school_id
    if school_id is None:
        from app.core.exceptions import ForbiddenError
        raise ForbiddenError("Scanner must be authenticated as a school user")

    result = await process_scanner_response(
        db,
        school_id=school_id,
        quiz_session_id=body.quiz_session_id,
        question_id=body.question_id,
        marker_id=body.marker_id,
        rotation=body.rotation,
        answer=body.answer,
        detected_at=body.detected_at,
        user_id=user.user_id,
    )

    try:
        dashboard = await get_quiz_dashboard(db, body.quiz_session_id, school_id)
        await ws_manager.broadcast(
            body.quiz_session_id,
            {
                "event": "response",
                "data": {
                    "student_id": result.student_id,
                    "card_id": result.card_id,
                    "answer": result.answer.value,
                    "is_correct": result.is_correct,
                    "marks_obtained": result.marks_obtained,
                    "responses_received": dashboard.responses_received,
                    "total_students": dashboard.total_students,
                    "answer_counts": dashboard.answer_counts,
                },
            },
        )
    except Exception:
        pass

    return result


# ── Frame detection: browser camera → ArUco → student list ───────────────────

class FrameDetectRequest(BaseModel):
    """Base64-encoded JPEG/PNG frame from the browser webcam."""
    frame_b64: str  # may include data:image/jpeg;base64, prefix


class DetectedCard(BaseModel):
    card_id: int
    marker_id: int
    student_id: Optional[int] = None   # DB id if found
    student_code: Optional[str] = None
    student_name: str                  # "First Last" or "STU###"
    answer: str                        # A / B / C / D
    rotation: int
    confidence: float


class FrameDetectResponse(BaseModel):
    detections: List[DetectedCard]
    frame_count: int


@router.post(
    "/detect-frame",
    response_model=FrameDetectResponse,
    summary="Detect ArUco response cards in one camera frame",
    description=(
        "Called by the Teacher UI browser. Accepts a base64-encoded JPEG frame, "
        "runs ArUco card detection, and returns each detected card with the matching "
        "student name and answer letter. Student names are resolved from the school DB. "
        "Does NOT persist responses — call POST /responses for that."
    ),
)
async def detect_frame(
    body: FrameDetectRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_teacher),
) -> FrameDetectResponse:
    import numpy as np
    import cv2

    # ── 1. Decode base64 JPEG ────────────────────────────────────────────
    b64 = body.frame_b64
    if "," in b64:
        b64 = b64.split(",", 1)[1]

    try:
        image_bytes = base64.b64decode(b64)
        nparr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None:
            return FrameDetectResponse(detections=[], frame_count=0)
    except Exception as exc:
        logger.warning(f"Frame decode failed: {exc}")
        return FrameDetectResponse(detections=[], frame_count=0)

    # ── 2. Build student_map {marker_id → (student_id, student_code, full_name)} from DB ──
    from app.models.card import Card, StudentCard
    from app.models.student import Student

    student_map: Dict[int, Dict[str, Any]] = {}
    if user.school_id:
        rows = await db.execute(
            select(Card.marker_id, Student.id, Student.student_code,
                   Student.first_name, Student.last_name)
            .join(StudentCard, StudentCard.card_id == Card.id)
            .join(Student, Student.id == StudentCard.student_id)
            .where(
                and_(
                    Card.school_id == user.school_id,
                    StudentCard.is_active == True,
                )
            )
        )
        for row in rows.all():
            marker_id, stu_id, stu_code, first, last = row
            student_map[int(marker_id)] = {
                "student_id": stu_id,
                "student_code": stu_code,
                "full_name": f"{first} {last}".strip(),
            }

    # ── 3. Run ArUco detector ─────────────────────────────────────────────
    _ensure_scanner_on_path()
    raw_results: List[Dict] = []
    try:
        from detector import CardDetector  # type: ignore
        name_only_map = {mid: info["full_name"] for mid, info in student_map.items()}
        detector = CardDetector(student_map=name_only_map)
        raw_results = detector.detect(frame)
    except ImportError:
        logger.warning("CardDetector not available server-side (OpenCV/scanner missing)")
    except Exception as exc:
        logger.error(f"ArUco detection error: {exc}")

    # ── 4. Enrich with DB student info ───────────────────────────────────
    detections: List[DetectedCard] = []
    for r in raw_results:
        mid = int(r["card_id"])
        db_info = student_map.get(mid, {})
        detections.append(
            DetectedCard(
                card_id=mid,
                marker_id=mid,
                student_id=db_info.get("student_id"),
                student_code=db_info.get("student_code"),
                student_name=db_info.get("full_name") or r.get("student_name", f"STU{mid:03d}"),
                answer=r["answer"],
                rotation=r["rotation"],
                confidence=r["confidence"],
            )
        )

    return FrameDetectResponse(detections=detections, frame_count=1)
