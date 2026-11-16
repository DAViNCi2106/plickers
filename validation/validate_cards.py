"""
validate_cards.py
=================
Validates every generated response card image.

For each card the script:

  1. Loads the PNG from cards/.
  2. Detects the ArUco marker and verifies the marker ID matches the filename.
  3. Applies four rotations that simulate holding the card with each label
     facing up (A/B/C/D), detects the marker in each, and verifies the
     answer mapping is correct.
  4. Applies a simulated perspective warp and verifies detection still works.
  5. Checks that no two cards share the same marker ID.

Physical-rotation simulation
-----------------------------
    Image rotation         Physical meaning           Expected answer
    ─────────────────────────────────────────────────────────────────
    as-is (0°)             A label facing up           A
    ROTATE_90_CW           B label facing up           B
    ROTATE_180             C label facing up           C
    ROTATE_90_CCW          D label facing up           D

Usage
-----
    python validate_cards.py
    python validate_cards.py --cards-dir ../cards
    python validate_cards.py --cards-dir ../cards --verbose
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

# ── resolve imports ──────────────────────────────────────────────────────────
_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
sys.path.insert(0, str(_ROOT / "scanner"))
from orientation import corners_to_rotation, rotation_to_answer


# ---------------------------------------------------------------------------
# ArUco detector (reuse the same parameters as scanner/detector.py)
# ---------------------------------------------------------------------------

def _make_detector() -> tuple:
    """Return (dictionary, detector_object_or_None) for the chosen dict."""
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250)
    params = cv2.aruco.DetectorParameters()
    params.adaptiveThreshWinSizeMin  = 3
    params.adaptiveThreshWinSizeMax  = 53
    params.adaptiveThreshWinSizeStep = 4
    params.minMarkerPerimeterRate    = 0.02
    params.maxMarkerPerimeterRate    = 4.0
    params.polygonalApproxAccuracyRate = 0.05
    params.errorCorrectionRate       = 0.6

    try:
        det = cv2.aruco.ArucoDetector(dictionary, params)
    except AttributeError:
        det = None   # will fall back to old API

    return dictionary, params, det


def _detect(
    img:        np.ndarray,
    dictionary: cv2.aruco.Dictionary,
    params:     cv2.aruco.DetectorParameters,
    det,
) -> tuple[list, Optional[np.ndarray]]:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    if det is not None:
        corners, ids, _ = det.detectMarkers(gray)
    else:
        corners, ids, _ = cv2.aruco.detectMarkers(gray, dictionary, parameters=params)
    return corners, ids


# ---------------------------------------------------------------------------
# Perspective warp helper
# ---------------------------------------------------------------------------

def _apply_perspective_warp(img: np.ndarray, severity: float = 0.15) -> np.ndarray:
    """
    Apply a mild trapezoidal perspective warp to *img*.

    *severity* controls the maximum shift as a fraction of the image size.
    Simulates the card being held at a slight angle to the camera.
    """
    h, w = img.shape[:2]
    dx = int(w * severity)
    dy = int(h * severity)

    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    dst = np.float32([
        [dx,  dy],
        [w - dx,   0],
        [w,        h - dy],
        [0,        h],
    ])
    M   = cv2.getPerspectiveTransform(src, dst)
    warped = cv2.warpPerspective(img, M, (w, h), borderValue=(255, 255, 255))
    return warped


# ---------------------------------------------------------------------------
# Single card validation
# ---------------------------------------------------------------------------

_ROTATIONS = [
    (None,                          "A",  "0°  (A-up)"),
    (cv2.ROTATE_90_CLOCKWISE,       "B",  "90° CW (B-up)"),
    (cv2.ROTATE_180,                "C",  "180° (C-up)"),
    (cv2.ROTATE_90_COUNTERCLOCKWISE,"D",  "270° CW (D-up)"),
]


def validate_card(
    card_path:  Path,
    dictionary: cv2.aruco.Dictionary,
    params:     cv2.aruco.DetectorParameters,
    det,
    verbose:    bool = False,
) -> dict:
    """
    Run full validation on a single card image file.

    Returns a result dict:
    {
        "card_id":   int,
        "passed":    bool,
        "id_ok":     bool,
        "rotations": [{"label": str, "expected": str, "got": str, "passed": bool}, …],
        "warp_ok":   bool,
        "errors":    [str, …],
    }
    """
    # Parse card_id from filename (card_NNN.png)
    stem = card_path.stem                # e.g. "card_017"
    try:
        expected_id = int(stem.split("_")[-1])
    except ValueError:
        return {
            "card_id": -1, "passed": False, "id_ok": False,
            "rotations": [], "warp_ok": False,
            "errors": [f"Cannot parse card ID from filename '{stem}'"],
        }

    img    = cv2.imread(str(card_path))
    errors = []

    # ── Step 1: ID check on unrotated image ─────────────────────────────────
    id_ok = False
    corners_unrot, ids_unrot = _detect(img, dictionary, params, det)
    if ids_unrot is None or len(ids_unrot) == 0:
        errors.append("Marker NOT detected in unrotated image")
    elif len(ids_unrot) > 1:
        errors.append(f"Multiple markers detected in single-card image: {ids_unrot.flatten()}")
    else:
        detected_id = int(ids_unrot.flatten()[0])
        if detected_id != expected_id:
            errors.append(f"ID mismatch: expected {expected_id}, got {detected_id}")
        else:
            id_ok = True

    # ── Step 2: Rotation tests ───────────────────────────────────────────────
    rotation_results = []
    for rot_code, expected_ans, label in _ROTATIONS:
        if rot_code is None:
            test_img = img.copy()
        else:
            test_img = cv2.rotate(img, rot_code)

        corners_r, ids_r = _detect(test_img, dictionary, params, det)
        if ids_r is None or len(ids_r) == 0:
            got_ans = "NOT_DETECTED"
            pass_ = False
            errors.append(f"Rotation {label}: marker not detected")
        else:
            corners_r_flat = corners_r[0]
            rotation_deg   = corners_to_rotation(corners_r_flat, test_img.shape)
            got_ans        = rotation_to_answer(rotation_deg)
            pass_          = (got_ans == expected_ans)
            if not pass_:
                errors.append(
                    f"Rotation {label}: expected {expected_ans}, got {got_ans} (rot={rotation_deg}°)"
                )

        rotation_results.append(
            {
                "label":    label,
                "expected": expected_ans,
                "got":      got_ans,
                "passed":   pass_,
            }
        )

    # ── Step 3: Perspective warp test ────────────────────────────────────────
    warped    = _apply_perspective_warp(img, severity=0.12)
    corners_w, ids_w = _detect(warped, dictionary, params, det)
    warp_ok   = (ids_w is not None and len(ids_w) > 0 and
                 int(ids_w.flatten()[0]) == expected_id)
    if not warp_ok:
        errors.append("Marker NOT detected after perspective warp")

    passed = id_ok and all(r["passed"] for r in rotation_results) and warp_ok

    if verbose:
        status = "PASS" if passed else "FAIL"
        print(f"  Card {expected_id:03d} [{status}]")
        for r in rotation_results:
            tick = "✓" if r["passed"] else "✗"
            print(f"    {tick} {r['label']:20s}  expected={r['expected']}  got={r['got']}")
        warp_tick = "✓" if warp_ok else "✗"
        print(f"    {warp_tick} Perspective warp test")
        if errors:
            for e in errors:
                print(f"    ⚠ {e}")

    return {
        "card_id":   expected_id,
        "passed":    passed,
        "id_ok":     id_ok,
        "rotations": rotation_results,
        "warp_ok":   warp_ok,
        "errors":    errors,
    }


# ---------------------------------------------------------------------------
# Batch validation
# ---------------------------------------------------------------------------

def validate_all(
    cards_dir: str  = "cards",
    verbose:   bool = False,
) -> bool:
    """
    Validate every card_NNN.png found in *cards_dir*.

    Returns True if all cards pass.
    """
    cards_dir_path = Path(cards_dir)
    card_files = sorted(cards_dir_path.glob("card_*.png"))

    if not card_files:
        print(f"[WARN] No card_*.png files found in '{cards_dir}'")
        return False

    print(f"\n{'='*62}")
    print(f"  VALIDATION REPORT -- {len(card_files)} cards in '{cards_dir}'")
    print(f"{'='*62}\n")

    dictionary, params, det = _make_detector()

    results  = []
    seen_ids: set[int] = set()
    dup_ids:  set[int] = set()

    for card_path in card_files:
        r = validate_card(card_path, dictionary, params, det, verbose=verbose)
        results.append(r)

        cid = r["card_id"]
        if cid in seen_ids:
            dup_ids.add(cid)
        seen_ids.add(cid)

    # ── Summary table ─────────────────────────────────────────────────────────
    print(f"\n{'-'*62}")
    print(f"  {'Card':>6}  {'ID':>4}  {'A':>4}  {'B':>4}  {'C':>4}  {'D':>4}  {'Warp':>5}  {'Overall':>8}")
    print(f"{'-'*62}")

    all_pass = True
    for r in results:
        rots = {x["expected"]: ("PASS" if x["passed"] else "FAIL") for x in r["rotations"]}
        row = (
            f"  {r['card_id']:>6}  "
            f"{'OK' if r['id_ok'] else 'FAIL':>4}  "
            f"{rots.get('A','----'):>4}  "
            f"{rots.get('B','----'):>4}  "
            f"{rots.get('C','----'):>4}  "
            f"{rots.get('D','----'):>4}  "
            f"{'OK' if r['warp_ok'] else 'FAIL':>5}  "
            f"{'[PASS]' if r['passed'] else '[FAIL]':>8}"
        )
        print(row)
        if not r["passed"]:
            all_pass = False

    print(f"{'-'*62}")

    # ── Duplicate-ID check ────────────────────────────────────────────────────
    if dup_ids:
        print(f"\n[FAIL] Duplicate marker IDs: {sorted(dup_ids)}")
        all_pass = False
    else:
        print("\n[PASS] No duplicate marker IDs.")

    # ── Final result ─────────────────────────────────────────────────────────
    passed_count = sum(1 for r in results if r["passed"])
    print(f"\n  Result: {passed_count}/{len(results)} cards passed all checks.")
    print(f"  Overall: {'ALL PASS' if all_pass else 'SOME CHECKS FAILED'}\n")
    print("=" * 62 + "\n")

    return all_pass


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Validate generated ArUco response cards.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument(
        "--cards-dir", type=str, default="cards",
        help="Directory containing card_NNN.png files (default: cards/)",
    )
    ap.add_argument(
        "--verbose", "-v", action="store_true",
        help="Print per-card per-rotation detail",
    )
    args = ap.parse_args()

    ok = validate_all(args.cards_dir, args.verbose)
    sys.exit(0 if ok else 1)
