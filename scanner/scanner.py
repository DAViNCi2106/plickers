"""
scanner.py
==========
Live webcam scanner for ArUco response cards.

Controls
--------
    q  — quit
    s  — save snapshot image + JSON response log
    r  — reset session responses
    f  — toggle full-screen

Usage
-----
    python scanner.py
    python scanner.py --camera 1
    python scanner.py --cards-json ../output/cards.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

# ── resolve imports whether run from scanner/ or project root ──────────────
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
from detector import CardDetector


# ---------------------------------------------------------------------------
# Student map loader
# ---------------------------------------------------------------------------

def load_student_map(cards_json_path: str | None = None) -> dict[int, str]:
    """
    Read student names from output/cards.json.

    Falls back to STU{card_id:03d} when the file is absent or the card
    has no student_name field.
    """
    if cards_json_path is None:
        cards_json_path = str(_HERE.parent / "output" / "cards.json")

    student_map: dict[int, str] = {}
    if os.path.exists(cards_json_path):
        try:
            with open(cards_json_path, encoding="utf-8") as fh:
                data = json.load(fh)
            for card in data.get("cards", []):
                cid  = card["card_id"]
                name = card.get("student_name", f"STU{cid:03d}")
                student_map[cid] = name
            print(f"[INFO] Loaded {len(student_map)} student entries from {cards_json_path}")
        except Exception as exc:
            print(f"[WARN] Could not read cards.json: {exc}")
    else:
        print(f"[INFO] No cards.json found at {cards_json_path} — using STUxxx labels")

    return student_map


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------

def run_scanner(camera_index: int = 0, cards_json: str | None = None) -> None:
    student_map = load_student_map(cards_json)
    detector    = CardDetector(student_map=student_map)

    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print(f"[ERROR] Cannot open camera index {camera_index}")
        sys.exit(1)

    # Request HD resolution (camera may cap lower)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT,  720)

    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"[INFO] Camera {camera_index} opened at {actual_w}×{actual_h}")
    print("[INFO] Controls: [q] quit   [s] save snapshot   [r] reset session")

    session_responses: dict[int, dict] = {}   # card_id → latest result
    full_screen = False
    prev_time   = time.perf_counter()

    WIN = "ArUco Response Card Scanner — Press q to quit"
    cv2.namedWindow(WIN, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WIN, 1280, 720)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[ERROR] Failed to grab frame — exiting")
            break

        # ── detection ──────────────────────────────────────────────────────
        annotated, results = detector.detect_and_annotate(frame)

        for r in results:
            session_responses[r["card_id"]] = r

        # ── FPS counter ─────────────────────────────────────────────────────
        now      = time.perf_counter()
        fps      = 1.0 / max(now - prev_time, 1e-6)
        prev_time = now
        cv2.putText(
            annotated, f"FPS: {fps:4.1f}", (annotated.shape[1] - 120, 22),
            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (160, 160, 160), 1, cv2.LINE_AA,
        )

        # ── controls hint ───────────────────────────────────────────────────
        hint = "[q] Quit  [s] Save  [r] Reset"
        cv2.putText(
            annotated, hint, (annotated.shape[1] - len(hint) * 8, annotated.shape[0] - 10),
            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (130, 130, 130), 1, cv2.LINE_AA,
        )

        cv2.imshow(WIN, annotated)

        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break

        elif key == ord("s"):
            _save_snapshot(annotated, session_responses)

        elif key == ord("r"):
            session_responses.clear()
            print("[INFO] Session responses cleared")

        elif key == ord("f"):
            full_screen = not full_screen
            flag = cv2.WINDOW_FULLSCREEN if full_screen else cv2.WINDOW_NORMAL
            cv2.setWindowProperty(WIN, cv2.WND_PROP_FULLSCREEN, float(flag))

    cap.release()
    cv2.destroyAllWindows()

    # ── session summary ─────────────────────────────────────────────────────
    print("\n" + "═" * 52)
    print("  SESSION SUMMARY")
    print("═" * 52)
    if not session_responses:
        print("  No cards detected during this session.")
    else:
        print(f"  {'Card':>6}  {'Student':<24}  {'Answer'}")
        print("  " + "─" * 40)
        for cid, r in sorted(session_responses.items()):
            print(f"  {cid:>6}  {r['student_name']:<24}  {r['answer']}")
    print("═" * 52 + "\n")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _save_snapshot(frame: np.ndarray, responses: dict) -> None:
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    img  = f"snapshot_{ts}.png"
    jfile = f"responses_{ts}.json"

    cv2.imwrite(img, frame)
    with open(jfile, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "timestamp": ts,
                "responses": list(responses.values()),
            },
            fh,
            indent=2,
        )

    print(f"[SAVED] {img}")
    print(f"[SAVED] {jfile}")
    print(json.dumps(list(responses.values()), indent=2))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Live ArUco response-card scanner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("--camera",     type=int, default=0,    help="Camera index (default 0)")
    ap.add_argument("--cards-json", type=str, default=None, help="Path to output/cards.json")
    args = ap.parse_args()

    run_scanner(args.camera, args.cards_json)
