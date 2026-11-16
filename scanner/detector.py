"""
detector.py
===========
Core ArUco card detection engine.

Wraps cv2.aruco.ArucoDetector (OpenCV ≥ 4.8) with a fallback to the
older cv2.aruco.detectMarkers API for OpenCV 4.x builds.

Usage
-----
    from detector import CardDetector

    detector = CardDetector(student_map={1: "Alice", 2: "Bob"})
    results  = detector.detect(frame)          # list[dict]
    annotated, results = detector.detect_and_annotate(frame)
"""

from __future__ import annotations

import sys
import os
import cv2
import numpy as np
from typing import Dict, List, Optional, Tuple

# Allow running from project root or from scanner/ directory
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from orientation import (
    corners_to_rotation,
    rotation_to_answer,
    compute_confidence,
    draw_answer_overlay,
    get_card_center,
)


# ---------------------------------------------------------------------------
# Detector parameters (tuned for classroom use)
# ---------------------------------------------------------------------------

def _make_parameters() -> cv2.aruco.DetectorParameters:
    p = cv2.aruco.DetectorParameters()

    # Adaptive thresholding
    p.adaptiveThreshWinSizeMin  = 3
    p.adaptiveThreshWinSizeMax  = 53
    p.adaptiveThreshWinSizeStep = 4
    p.adaptiveThreshConstant    = 7

    # Contour filtering
    p.minMarkerPerimeterRate  = 0.02   # detect smaller markers at distance
    p.maxMarkerPerimeterRate  = 4.0
    p.polygonalApproxAccuracyRate = 0.05
    p.minCornerDistanceRate   = 0.05
    p.minDistanceToBorder     = 3

    # Bit-extraction
    if hasattr(p, "perspectiveCorrectedCount"):
        p.perspectiveCorrectedCount = 1  # allows mild perspective distortion
    p.errorCorrectionRate       = 0.6  # allow up to 60 % of correctable errors

    # Subpixel corner refinement for distant or angled cards in the room
    if hasattr(cv2.aruco, "CORNER_REFINE_SUBPIX"):
        p.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
    elif hasattr(cv2.aruco, "CORNER_REFINE_CONTOUR"):
        p.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_CONTOUR

    return p


def _detect_markers(
    gray:       np.ndarray,
    dictionary: cv2.aruco.Dictionary,
    parameters: cv2.aruco.DetectorParameters,
) -> Tuple[list, Optional[np.ndarray], list]:
    """Unified detection call supporting both old and new OpenCV APIs."""
    try:
        # OpenCV ≥ 4.8 new API
        det = cv2.aruco.ArucoDetector(dictionary, parameters)
        corners, ids, rejected = det.detectMarkers(gray)
    except AttributeError:
        # OpenCV 4.x legacy API
        corners, ids, rejected = cv2.aruco.detectMarkers(
            gray, dictionary, parameters=parameters
        )
    return corners, ids, rejected


# ---------------------------------------------------------------------------
# CardDetector class
# ---------------------------------------------------------------------------

class CardDetector:
    """
    Detects ArUco response cards in a video frame and resolves
    marker ID → student name and corner geometry → answer letter.
    """

    def __init__(self, student_map: Optional[Dict[int, str]] = None):
        """
        Parameters
        ----------
        student_map : dict, optional
            Mapping  {card_id: student_name}.
            Falls back to "STU{card_id:03d}" when card is not in the map.
        """
        self.dictionary = cv2.aruco.getPredefinedDictionary(
            cv2.aruco.DICT_6X6_250
        )
        self.parameters  = _make_parameters()
        self.student_map = student_map or {}

    # ------------------------------------------------------------------
    def detect(self, frame: np.ndarray) -> List[Dict]:
        """
        Detect all response cards in *frame*.

        Returns
        -------
        list[dict]
            Each element:
            {
                "card_id":      int,
                "student_id":   str,          # "STU001"
                "student_name": str,
                "rotation":     int,          # 0 / 90 / 180 / 270
                "answer":       str,          # "A" / "B" / "C" / "D"
                "corners":      list,         # [[x,y], ...]  shape 4×2
                "confidence":   float,        # 0–100
            }
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners_list, ids, _ = _detect_markers(
            gray, self.dictionary, self.parameters
        )

        detected_dict = {}
        if ids is not None:
            for i, marker_id in enumerate(ids.flatten()):
                mid = int(marker_id)
                detected_dict[mid] = corners_list[i]

        # Multi-pass with CLAHE to catch cards in shadows or back of the classroom
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray_clahe = clahe.apply(gray)
        corners_clahe, ids_clahe, _ = _detect_markers(
            gray_clahe, self.dictionary, self.parameters
        )
        if ids_clahe is not None:
            for i, marker_id in enumerate(ids_clahe.flatten()):
                mid = int(marker_id)
                if mid not in detected_dict:
                    detected_dict[mid] = corners_clahe[i]

        results: List[Dict] = []
        if not detected_dict:
            return results

        for card_id, corners in detected_dict.items():

            rotation = corners_to_rotation(corners, frame.shape)
            answer   = rotation_to_answer(rotation)
            conf     = compute_confidence(corners)
            name     = self.student_map.get(card_id, f"STU{card_id:03d}")

            results.append(
                {
                    "card_id":      card_id,
                    "student_id":   f"STU{card_id:03d}",
                    "student_name": name,
                    "rotation":     rotation,
                    "answer":       answer,
                    "corners":      corners.reshape(4, 2).tolist(),
                    "confidence":   conf,
                }
            )

        # Sort by card_id for consistent ordering
        results.sort(key=lambda r: r["card_id"])
        return results

    # ------------------------------------------------------------------
    def detect_and_annotate(
        self, frame: np.ndarray
    ) -> Tuple[np.ndarray, List[Dict]]:
        """
        Detect cards and draw coloured overlays directly onto *frame*.

        Returns
        -------
        (annotated_frame, results)
        """
        results  = self.detect(frame)
        annotated = frame.copy()

        for r in results:
            corners = np.array(r["corners"], dtype=np.float32)
            annotated = draw_answer_overlay(
                annotated,
                corners,
                r["card_id"],
                r["answer"],
                r["student_name"],
                r["confidence"],
            )

        annotated = self._draw_hud(annotated, results)
        return annotated, results

    # ------------------------------------------------------------------
    def _draw_hud(
        self, frame: np.ndarray, results: List[Dict]
    ) -> np.ndarray:
        """Draw a heads-up summary panel in the top-left corner."""
        font  = cv2.FONT_HERSHEY_SIMPLEX
        lh    = 22
        lines = [f"  Cards detected: {len(results)}"]
        for r in results:
            lines.append(
                f"  [{r['card_id']:03d}] {r['student_name'][:16]:<16}  {r['answer']}"
            )

        panel_w = 330
        panel_h = len(lines) * lh + 14

        roi  = frame[0:panel_h, 0:panel_w]
        dark = np.zeros_like(roi)
        cv2.addWeighted(dark, 0.65, roi, 0.35, 0, roi)
        frame[0:panel_h, 0:panel_w] = roi

        for i, line in enumerate(lines):
            color = (0, 255, 180) if i == 0 else (210, 210, 210)
            cv2.putText(
                frame, line, (4, 14 + i * lh),
                font, 0.50, color, 1, cv2.LINE_AA,
            )

        return frame
