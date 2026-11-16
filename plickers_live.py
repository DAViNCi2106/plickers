"""
plickers_live.py
================
Standalone Plickers scanner — opens a camera window directly using OpenCV.
Guaranteed to work since Camera 0 is confirmed available.

Controls
--------
  Q  — quit
  S  — save responses to JSON
  R  — reset session
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

# ── resolve imports ────────────────────────────────────────────────────────
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE / "scanner"))

from detector import CardDetector

# ── colours (BGR for OpenCV) ───────────────────────────────────────────────
COLORS = {
    "A": (80,  230,  60),   # green
    "B": (245, 160,  50),   # blue
    "C": (50,  140, 255),   # orange
    "D": (245,  80, 200),   # purple
    "?": (200, 200, 200),
}

BG_DARK    = (20,  22,  35)
BG_PANEL   = (30,  32,  48)
TEXT_WHITE = (240, 240, 240)
TEXT_GRAY  = (140, 145, 170)
ACCENT     = (80,  230, 100)


# ---------------------------------------------------------------------------
# Student map loader
# ---------------------------------------------------------------------------

def load_student_map(path: str | None = None) -> dict:
    if path is None:
        path = str(_HERE / "output" / "cards.json")
    sm = {}
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            for c in data.get("cards", []):
                sm[c["card_id"]] = c.get("student_name", f"STU{c['card_id']:03d}")
            print(f"[INFO] Loaded {len(sm)} students from cards.json")
        except Exception as e:
            print(f"[WARN] {e}")
    return sm


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------

def filled_rect(img, x1, y1, x2, y2, color, alpha=0.75):
    """Draw a semi-transparent filled rectangle."""
    sub = img[y1:y2, x1:x2]
    rect = np.full_like(sub, color[::-1] if len(color) == 3 else color)
    cv2.addWeighted(rect, alpha, sub, 1 - alpha, 0, sub)
    img[y1:y2, x1:x2] = sub


def put_text(img, text, x, y, scale=0.6, color=TEXT_WHITE, thickness=1, bold=False):
    font = cv2.FONT_HERSHEY_SIMPLEX
    th = thickness + 1 if bold else thickness
    cv2.putText(img, text, (x, y), font, scale, color, th, cv2.LINE_AA)


def draw_answer_badge(img, answer, cx, cy, size=90):
    """Draw a big answer letter badge centred at (cx, cy)."""
    color = COLORS.get(answer, COLORS["?"])
    half  = size // 2
    # Dark background circle
    cv2.circle(img, (cx, cy), half + 8, (10, 12, 20), -1)
    cv2.circle(img, (cx, cy), half + 8, color, 3)
    # Letter
    font   = cv2.FONT_HERSHEY_SIMPLEX
    scale  = 3.0
    thick  = 6
    (tw, th), _ = cv2.getTextSize(answer, font, scale, thick)
    cv2.putText(img, answer, (cx - tw // 2, cy + th // 2), font, scale, color, thick, cv2.LINE_AA)


# ---------------------------------------------------------------------------
# Right-side panel
# ---------------------------------------------------------------------------

def draw_side_panel(img, results, session, fps):
    h, w = img.shape[:2]
    pw   = 340                       # panel width
    px   = w - pw                    # panel left edge

    # Panel background
    filled_rect(img, px, 0, w, h, (15, 17, 28), alpha=0.88)

    y = 30
    # ── Title ─────────────────────────────────────────────────────────────
    put_text(img, "PLICKERS SCANNER", px + 14, y, 0.65, ACCENT, 2, bold=True)
    y += 28
    put_text(img, f"FPS: {fps:4.1f}   |   Session: {len(session)} captured",
             px + 14, y, 0.42, TEXT_GRAY)
    y += 20
    cv2.line(img, (px + 10, y), (w - 10, y), (50, 55, 80), 1)
    y += 18

    if results:
        r = results[-1]   # most recently detected card
        ans   = r["answer"]
        name  = r["student_name"]
        cid   = r["card_id"]
        conf  = r["confidence"]
        color = COLORS.get(ans, COLORS["?"])

        # ── "NOW DETECTED" header ──────────────────────────────────────
        put_text(img, "NOW DETECTED", px + 14, y, 0.48, TEXT_GRAY)
        y += 22

        # ── Student name ───────────────────────────────────────────────
        # Break long names
        words = name.split()
        line1 = " ".join(words[:2])
        line2 = " ".join(words[2:]) if len(words) > 2 else ""
        put_text(img, line1, px + 14, y, 0.75, TEXT_WHITE, 2, bold=True)
        y += 28
        if line2:
            put_text(img, line2, px + 14, y, 0.75, TEXT_WHITE, 2, bold=True)
            y += 28

        put_text(img, f"Card #{cid:03d}", px + 14, y, 0.45, TEXT_GRAY)
        y += 30

        # ── Big answer badge ───────────────────────────────────────────
        badge_cx = px + pw // 2
        badge_cy = y + 70
        draw_answer_badge(img, ans, badge_cx, badge_cy, size=70)
        y += 155

        # ── Answer label ───────────────────────────────────────────────
        answer_labels = {"A": "Answer  A", "B": "Answer  B",
                         "C": "Answer  C", "D": "Answer  D"}
        label = answer_labels.get(ans, "Unknown")
        (tw2, _), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        cv2.putText(img, label, (badge_cx - tw2 // 2, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2, cv2.LINE_AA)
        y += 26

        put_text(img, f"Confidence: {conf:.0f}%", px + 14, y, 0.42, TEXT_GRAY)
        y += 30

    else:
        put_text(img, "No card detected", px + 14, y, 0.55, TEXT_GRAY)
        put_text(img, "Hold a card up", px + 14, y + 24, 0.55, TEXT_GRAY)
        put_text(img, "to the camera...", px + 14, y + 48, 0.55, TEXT_GRAY)
        y += 100

    # ── Session log ────────────────────────────────────────────────────────
    cv2.line(img, (px + 10, y), (w - 10, y), (50, 55, 80), 1)
    y += 18
    put_text(img, "SESSION RESPONSES", px + 14, y, 0.48, TEXT_GRAY)
    y += 22

    # Header
    put_text(img, f"{'Card':<5}  {'Student':<18}  Ans", px + 14, y, 0.38,
             (100, 180, 255))
    y += 18

    for cid in sorted(session.keys()):
        if y > h - 20:
            break
        r   = session[cid]
        ans = r["answer"]
        col = COLORS.get(ans, COLORS["?"])
        row_text = f"{cid:<5}  {r['student_name'][:18]:<18}"
        put_text(img, row_text, px + 14, y, 0.38, TEXT_GRAY)
        put_text(img, ans, px + 14 + 220, y, 0.42, col, 2, bold=True)
        y += 18


# ---------------------------------------------------------------------------
# Main scanner loop
# ---------------------------------------------------------------------------

def run(camera_index: int = 0, cards_json: str | None = None):
    student_map = load_student_map(cards_json)
    detector    = CardDetector(student_map=student_map)

    # Try camera indices until one opens
    cap = None
    for idx in ([camera_index] + [i for i in range(5) if i != camera_index]):
        cap = cv2.VideoCapture(idx)
        if cap.isOpened():
            print(f"[INFO] Camera opened at index {idx}")
            break
        cap.release()
    else:
        print("[ERROR] No camera found. Plug in a webcam and try again.")
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT,  720)

    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"[INFO] Resolution: {W}×{H}")
    print("[INFO] Controls: Q=Quit  S=Save  R=Reset")

    WIN = "Plickers Live Scanner  —  Q to quit"
    cv2.namedWindow(WIN, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WIN, 1240, 720)
    # Bring window to front
    cv2.setWindowProperty(WIN, cv2.WND_PROP_TOPMOST, 1)

    session   = {}
    prev_time = time.perf_counter()

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[WARN] Failed to grab frame, retrying...")
            time.sleep(0.05)
            continue

        # ── detect ────────────────────────────────────────────────────
        annotated, results = detector.detect_and_annotate(frame)

        for r in results:
            session[r["card_id"]] = r

        # ── FPS ───────────────────────────────────────────────────────
        now       = time.perf_counter()
        fps       = 1.0 / max(now - prev_time, 1e-6)
        prev_time = now

        # ── side panel ────────────────────────────────────────────────
        draw_side_panel(annotated, results, session, fps)

        # ── bottom hint bar ───────────────────────────────────────────
        bh = annotated.shape[0]
        bw = annotated.shape[1]
        filled_rect(annotated, 0, bh - 28, bw - 340, bh, (15, 17, 28), alpha=0.8)
        put_text(annotated,
                 "  [Q] Quit    [S] Save snapshot    [R] Reset session",
                 6, bh - 10, 0.42, TEXT_GRAY)

        cv2.imshow(WIN, annotated)

        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), ord("Q"), 27):    # Q or ESC
            break
        elif key in (ord("s"), ord("S")):
            _save(session)
        elif key in (ord("r"), ord("R")):
            session.clear()
            print("[INFO] Session reset.")

    cap.release()
    cv2.destroyAllWindows()

    # ── summary ───────────────────────────────────────────────────────────
    print("\n" + "═" * 50)
    print("  SESSION SUMMARY")
    print("═" * 50)
    if not session:
        print("  No cards captured.")
    else:
        print(f"  {'Card':>5}  {'Student':<24}  Answer")
        print("  " + "─" * 38)
        for cid, r in sorted(session.items()):
            print(f"  {cid:>5}  {r['student_name']:<24}  {r['answer']}")
    print("═" * 50)


def _save(session):
    if not session:
        print("[INFO] Nothing to save.")
        return
    ts    = datetime.now().strftime("%Y%m%d_%H%M%S")
    path  = _HERE / f"responses_{ts}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"timestamp": ts, "responses": list(session.values())},
                  f, indent=2, ensure_ascii=False)
    print(f"[SAVED] {path}")


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--camera",     type=int, default=0)
    ap.add_argument("--cards-json", type=str, default=None)
    args = ap.parse_args()
    run(args.camera, args.cards_json)
