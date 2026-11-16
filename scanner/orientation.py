"""
orientation.py
==============
Utilities for calculating physical card orientation from ArUco corner data.

Algorithm overview
------------------
ArUco always returns four corners in a fixed, canonical winding order:

    corners[0] = marker's own Top-Left  (TL)
    corners[1] = marker's own Top-Right (TR)
    corners[2] = marker's own Bot-Right (BR)
    corners[3] = marker's own Bot-Left  (BL)

This is true regardless of how the physical card is rotated — the marker's
internal asymmetric bit-pattern lets OpenCV assign TL/TR/BR/BL correctly.

We construct the marker's "canonical up" vector:

    up_vec = midpoint(TL, TR) − midpoint(BL, BR)

When the card is held normally (A at top), up_vec points toward the image
top (negative y in image coords). When rotated 90° CW (B at top), up_vec
points right (+x), etc.

    atan2(−up_vec.y, up_vec.x) gives an angle in standard math coordinates:
        ≈  90° → A (card at 0°)
        ≈   0° → B (card at 90° CW)
        ≈ −90° → C (card at 180°)
        ≈ 180° → D (card at 270° CW)

    card_rotation = (90° − angle) mod 360°, snapped to nearest 90°.
"""

from __future__ import annotations
import numpy as np
import cv2
from typing import Tuple


# ---------------------------------------------------------------------------
# Core orientation calculation
# ---------------------------------------------------------------------------

def corners_to_rotation(corners: np.ndarray, image_shape: Tuple = None) -> int:
    """
    Determine the physical card rotation from an ArUco marker's corners.

    Parameters
    ----------
    corners : np.ndarray
        Corner array as returned by cv2.aruco.detectMarkers — shape
        (1, 4, 2) or (4, 2).  Order is [TL, TR, BR, BL] in the
        marker's own canonical frame.
    image_shape : tuple, optional
        Not used in the current algorithm; kept for API compatibility.

    Returns
    -------
    int
        Card rotation in degrees: 0, 90, 180, or 270.
    """
    pts = corners.reshape(4, 2).astype(float)
    tl, tr, br, bl = pts[0], pts[1], pts[2], pts[3]

    # Midpoints of top and bottom edges of the marker (canonical frame)
    top_mid = (tl + tr) / 2.0
    bot_mid = (bl + br) / 2.0

    # "Up" direction in image space (y increases downward, so negate y)
    up_vec = top_mid - bot_mid
    angle = np.degrees(np.arctan2(-up_vec[1], up_vec[0]))

    # Convert to card rotation and snap to the nearest 90°
    raw = (90.0 - angle) % 360.0
    snapped = int(round(raw / 90.0) * 90 % 360)
    return snapped


def rotation_to_answer(rotation: int) -> str:
    """
    Map a card rotation angle to an answer letter.

    0   → A
    90  → B
    180 → C
    270 → D
    """
    mapping = {0: "A", 90: "B", 180: "C", 270: "D"}
    return mapping.get(rotation % 360, "?")


def answer_to_rotation(answer: str) -> int:
    """Map an answer letter to the expected card rotation angle."""
    mapping = {"A": 0, "B": 90, "C": 180, "D": 270}
    return mapping.get(answer.upper(), -1)


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def get_card_center(corners: np.ndarray) -> Tuple[int, int]:
    """Return the pixel centre of a detected ArUco marker."""
    pts = corners.reshape(4, 2)
    return int(np.mean(pts[:, 0])), int(np.mean(pts[:, 1]))


def compute_confidence(corners: np.ndarray) -> float:
    """
    Estimate detection confidence (0–100) from the squareness of the marker.

    A perfectly square (undistorted) marker gives ~100.
    Perspective-warped markers score lower but remain usable.
    """
    pts = corners.reshape(4, 2).astype(float)
    sides = [np.linalg.norm(pts[(i + 1) % 4] - pts[i]) for i in range(4)]
    if max(sides) == 0:
        return 0.0
    squareness = min(sides) / max(sides)

    # Also check diagonals are similar
    d1 = np.linalg.norm(pts[2] - pts[0])
    d2 = np.linalg.norm(pts[3] - pts[1])
    diag_ratio = min(d1, d2) / max(d1, d2) if max(d1, d2) > 0 else 0.0

    score = (squareness * 0.6 + diag_ratio * 0.4) * 100.0
    return round(min(score, 100.0), 1)


# ---------------------------------------------------------------------------
# Overlay drawing
# ---------------------------------------------------------------------------

_ANSWER_COLORS = {
    "A": (50,  230, 100),   # green
    "B": (50,  180, 255),   # sky-blue
    "C": (255, 120,  50),   # orange
    "D": (200,  50, 255),   # purple
}


def draw_answer_overlay(
    frame:        np.ndarray,
    corners:      np.ndarray,
    card_id:      int,
    answer:       str,
    student_name: str,
    confidence:   float = 100.0,
) -> np.ndarray:
    """
    Draw a coloured bounding polygon and info panel next to a detected card.

    Modifies *frame* in-place and also returns it for chaining.
    """
    pts = corners.reshape(4, 2).astype(int)
    cx, cy = get_card_center(corners)
    color = _ANSWER_COLORS.get(answer, (255, 255, 0))

    # --- bounding polygon --------------------------------------------------
    hull = cv2.convexHull(pts)
    cv2.polylines(frame, [hull], isClosed=True, color=color, thickness=3)

    # Corner dots with index labels (useful for debugging)
    for i, pt in enumerate(pts):
        cv2.circle(frame, tuple(pt), 6, color, -1)

    # --- text panel --------------------------------------------------------
    lines = [
        f"CARD {card_id:03d}",
        f"Student: {student_name}",
        f"Answer:  {answer}",
        f"Conf:    {confidence:.0f}%",
    ]

    font       = cv2.FONT_HERSHEY_SIMPLEX
    fscale     = 0.55
    thickness  = 2
    lh         = 22                       # line height px

    # Position panel to the right of marker centre; clamp to frame
    tx = min(cx + 30, frame.shape[1] - 210)
    ty = max(cy - (len(lines) * lh) // 2, 5)

    bx1 = max(tx - 6,  0)
    by1 = max(ty - 18, 0)
    bx2 = min(tx + 205, frame.shape[1] - 1)
    by2 = min(ty + len(lines) * lh + 6, frame.shape[0] - 1)

    # Semi-transparent dark background
    roi = frame[by1:by2, bx1:bx2]
    dark = np.zeros_like(roi)
    cv2.addWeighted(dark, 0.55, roi, 0.45, 0, roi)
    frame[by1:by2, bx1:bx2] = roi

    for i, line in enumerate(lines):
        cv2.putText(frame, line, (tx, ty + i * lh),
                    font, fscale, color, thickness, cv2.LINE_AA)

    return frame
