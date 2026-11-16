"""
plickers_gui.py
===============
Standalone Plickers-style scanner with a proper Tkinter GUI window.

Layout
------
  ┌─────────────────────────────────────────────────────────────┐
  │  🎥 LIVE CAMERA FEED (left, big)  │  📋 RESULTS PANEL (right) │
  │                                    │                           │
  │   ArUco overlays drawn on feed     │  ● Student Name           │
  │                                    │  ● Answer  A / B / C / D  │
  │                                    │  ● Confidence %           │
  │                                    │  ─────────────────        │
  │                                    │  Session log              │
  └─────────────────────────────────────────────────────────────┘

Usage
-----
    python plickers_gui.py
    python plickers_gui.py --camera 1
    python plickers_gui.py --cards-json output/cards.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import font as tkfont
from typing import Dict, List

import cv2
import numpy as np
from PIL import Image, ImageTk

# ── resolve scanner imports ────────────────────────────────────────────────
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE / "scanner"))

from detector import CardDetector

# ── colour palette ─────────────────────────────────────────────────────────
BG_DARK      = "#0f1117"
BG_PANEL     = "#1a1d27"
BG_CARD      = "#22263a"
ACCENT_BLUE  = "#4e9ef5"
ACCENT_GREEN = "#3de680"
TEXT_WHITE   = "#f0f0f0"
TEXT_GRAY    = "#8a8fa8"
TEXT_DIM     = "#555978"

ANSWER_COLORS = {
    "A": "#3de680",   # green
    "B": "#4e9ef5",   # blue
    "C": "#ff8c42",   # orange
    "D": "#c97bf5",   # purple
    "?": "#ffffff",
}

ANSWER_BG = {
    "A": "#0d3320",
    "B": "#0d2040",
    "C": "#3d2010",
    "D": "#2a1040",
    "?": "#222222",
}


# ---------------------------------------------------------------------------
# Student map loader
# ---------------------------------------------------------------------------

def load_student_map(cards_json_path: str | None = None) -> Dict[int, str]:
    if cards_json_path is None:
        cards_json_path = str(_HERE / "output" / "cards.json")

    student_map: Dict[int, str] = {}
    if os.path.exists(cards_json_path):
        try:
            with open(cards_json_path, encoding="utf-8") as fh:
                data = json.load(fh)
            for card in data.get("cards", []):
                cid  = card["card_id"]
                name = card.get("student_name", f"STU{cid:03d}")
                student_map[cid] = name
        except Exception as exc:
            print(f"[WARN] Could not read cards.json: {exc}")
    return student_map


# ---------------------------------------------------------------------------
# Main GUI Application
# ---------------------------------------------------------------------------

class PlickersApp:
    FEED_W = 820
    FEED_H = 560
    PANEL_W = 360

    def __init__(self, root: tk.Tk, camera_index: int = 0, cards_json: str | None = None):
        self.root = root
        self.root.title("📷 Plickers Live Scanner")
        self.root.configure(bg=BG_DARK)
        self.root.resizable(True, True)

        self.student_map = load_student_map(cards_json)
        self.detector    = CardDetector(student_map=self.student_map)

        self.cap = cv2.VideoCapture(camera_index)
        if not self.cap.isOpened():
            # Try next camera index automatically
            for idx in range(5):
                self.cap = cv2.VideoCapture(idx)
                if self.cap.isOpened():
                    print(f"[INFO] Opened camera at index {idx}")
                    break
            else:
                tk.messagebox.showerror(
                    "Camera Error",
                    f"Cannot open any camera.\nTry running with --camera 1"
                )
                root.destroy()
                return

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT,  720)

        self.session: Dict[int, dict] = {}  # card_id → last result
        self.running = True
        self._photo  = None  # keep reference to avoid GC

        self._build_ui()
        self._start_loop()

    # ──────────────────────────────────────────────────────────────────────
    # UI construction
    # ──────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── top title bar ──────────────────────────────────────────────────
        title_bar = tk.Frame(self.root, bg=BG_PANEL, height=54)
        title_bar.pack(fill="x", side="top")
        title_bar.pack_propagate(False)

        tk.Label(
            title_bar,
            text="🎓  Plickers Live Scanner",
            bg=BG_PANEL, fg=TEXT_WHITE,
            font=("Segoe UI", 16, "bold"),
            padx=18,
        ).pack(side="left", pady=10)

        # Camera status indicator
        self.cam_status = tk.Label(
            title_bar,
            text="● LIVE",
            bg=BG_PANEL, fg=ACCENT_GREEN,
            font=("Segoe UI", 11, "bold"),
            padx=12,
        )
        self.cam_status.pack(side="right", pady=10)

        # FPS label
        self.fps_label = tk.Label(
            title_bar,
            text="FPS: --",
            bg=BG_PANEL, fg=TEXT_GRAY,
            font=("Segoe UI", 10),
            padx=12,
        )
        self.fps_label.pack(side="right", pady=10)

        # ── main body ──────────────────────────────────────────────────────
        body = tk.Frame(self.root, bg=BG_DARK)
        body.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Left: camera feed
        cam_frame = tk.Frame(body, bg=BG_DARK)
        cam_frame.pack(side="left", fill="both", expand=True)

        cam_label_text = tk.Label(
            cam_frame, text="📹  Camera Feed",
            bg=BG_DARK, fg=TEXT_GRAY,
            font=("Segoe UI", 9),
        )
        cam_label_text.pack(anchor="w", pady=(4, 2))

        self.feed_canvas = tk.Label(
            cam_frame,
            bg="#000000",
            relief="flat",
            cursor="crosshair",
        )
        self.feed_canvas.pack(fill="both", expand=True)

        # Right: results panel
        panel_outer = tk.Frame(body, bg=BG_DARK, width=self.PANEL_W)
        panel_outer.pack(side="right", fill="y", padx=(10, 0))
        panel_outer.pack_propagate(False)

        self._build_results_panel(panel_outer)

        # ── bottom status bar ──────────────────────────────────────────────
        status_bar = tk.Frame(self.root, bg=BG_PANEL, height=32)
        status_bar.pack(fill="x", side="bottom")
        status_bar.pack_propagate(False)

        self.status_label = tk.Label(
            status_bar,
            text="  Hold a student's card up to the camera...",
            bg=BG_PANEL, fg=TEXT_GRAY,
            font=("Segoe UI", 9),
            anchor="w",
        )
        self.status_label.pack(side="left", fill="x", expand=True, pady=5, padx=6)

        btn_reset = tk.Button(
            status_bar,
            text="↺  Reset Session",
            bg="#2a2d3e", fg=TEXT_GRAY,
            font=("Segoe UI", 9),
            relief="flat",
            cursor="hand2",
            padx=10,
            command=self._reset_session,
        )
        btn_reset.pack(side="right", pady=4, padx=6)

        btn_save = tk.Button(
            status_bar,
            text="💾  Save Responses",
            bg="#1e4a8c", fg=TEXT_WHITE,
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            cursor="hand2",
            padx=10,
            command=self._save_responses,
        )
        btn_save.pack(side="right", pady=4, padx=4)

    def _build_results_panel(self, parent):
        tk.Label(
            parent, text="📋  Detected Results",
            bg=BG_DARK, fg=TEXT_GRAY,
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(4, 2))

        # ── big "now showing" card ─────────────────────────────────────────
        now_frame = tk.Frame(parent, bg=BG_CARD, bd=0, relief="flat")
        now_frame.pack(fill="x", pady=(0, 8))

        tk.Label(
            now_frame, text="NOW DETECTED",
            bg=BG_CARD, fg=TEXT_DIM,
            font=("Segoe UI", 8, "bold"),
            pady=8, padx=12,
        ).pack(anchor="w")

        # Student name
        self.lbl_name = tk.Label(
            now_frame,
            text="—",
            bg=BG_CARD, fg=TEXT_WHITE,
            font=("Segoe UI", 18, "bold"),
            wraplength=320,
            justify="left",
            padx=12, pady=2,
        )
        self.lbl_name.pack(anchor="w")

        self.lbl_student_id = tk.Label(
            now_frame,
            text="",
            bg=BG_CARD, fg=TEXT_GRAY,
            font=("Segoe UI", 9),
            padx=12,
        )
        self.lbl_student_id.pack(anchor="w")

        # Big answer badge
        self.lbl_answer = tk.Label(
            now_frame,
            text="?",
            bg=ANSWER_BG["?"], fg=ANSWER_COLORS["?"],
            font=("Segoe UI", 72, "bold"),
            width=2,
            pady=10,
        )
        self.lbl_answer.pack(fill="x", padx=12, pady=10)

        # Answer text label
        self.lbl_answer_text = tk.Label(
            now_frame,
            text="Waiting for card...",
            bg=BG_CARD, fg=TEXT_GRAY,
            font=("Segoe UI", 11),
            padx=12, pady=4,
        )
        self.lbl_answer_text.pack(anchor="w")

        # Confidence
        self.lbl_conf = tk.Label(
            now_frame,
            text="",
            bg=BG_CARD, fg=TEXT_DIM,
            font=("Segoe UI", 9),
            padx=12, pady=6,
        )
        self.lbl_conf.pack(anchor="w")

        # ── session log ────────────────────────────────────────────────────
        tk.Label(
            parent, text="📊  Session Responses",
            bg=BG_DARK, fg=TEXT_GRAY,
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(6, 2))

        log_frame = tk.Frame(parent, bg=BG_PANEL, bd=0)
        log_frame.pack(fill="both", expand=True)

        scrollbar = tk.Scrollbar(log_frame, bg=BG_PANEL, troughcolor=BG_DARK)
        scrollbar.pack(side="right", fill="y")

        self.log_box = tk.Text(
            log_frame,
            bg=BG_PANEL, fg=TEXT_WHITE,
            font=("Consolas", 10),
            relief="flat",
            state="disabled",
            yscrollcommand=scrollbar.set,
            padx=8, pady=6,
            cursor="arrow",
            wrap="none",
        )
        self.log_box.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.log_box.yview)

        # Tag colours for each answer
        for ans, col in ANSWER_COLORS.items():
            self.log_box.tag_config(f"ans_{ans}", foreground=col, font=("Consolas", 10, "bold"))
        self.log_box.tag_config("dim", foreground=TEXT_DIM)
        self.log_box.tag_config("header", foreground=ACCENT_BLUE, font=("Consolas", 9, "bold"))

        self._log_header()

    # ──────────────────────────────────────────────────────────────────────
    # Video loop
    # ──────────────────────────────────────────────────────────────────────

    def _start_loop(self):
        self._prev_time = time.perf_counter()
        self._update()

    def _update(self):
        if not self.running:
            return

        ret, frame = self.cap.read()
        if not ret:
            self.root.after(50, self._update)
            return

        # ── detect ──────────────────────────────────────────────────────
        annotated, results = self.detector.detect_and_annotate(frame)

        for r in results:
            self.session[r["card_id"]] = r

        # ── FPS ─────────────────────────────────────────────────────────
        now = time.perf_counter()
        fps = 1.0 / max(now - self._prev_time, 1e-6)
        self._prev_time = now
        self.fps_label.config(text=f"FPS: {fps:4.1f}")

        # ── push frame to canvas ────────────────────────────────────────
        canvas_w = self.feed_canvas.winfo_width()  or self.FEED_W
        canvas_h = self.feed_canvas.winfo_height() or self.FEED_H

        rgb    = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
        pil    = Image.fromarray(rgb)
        pil    = pil.resize((canvas_w, canvas_h), Image.BILINEAR)
        photo  = ImageTk.PhotoImage(pil)
        self._photo = photo  # prevent GC
        self.feed_canvas.config(image=photo)

        # ── update results panel ────────────────────────────────────────
        if results:
            # Show the most recently detected card (last in list)
            latest = results[-1]
            self._update_now_panel(latest)
            self._update_log(latest)
            self.status_label.config(
                text=f"  ✓ {len(results)} card(s) in view  |  "
                     f"Session total: {len(self.session)} students"
            )
        else:
            self._clear_now_panel()
            self.status_label.config(
                text=f"  Hold a student's card up to the camera...  "
                     f"|  Session: {len(self.session)} captured"
            )

        self.root.after(16, self._update)   # ~60 fps target

    # ──────────────────────────────────────────────────────────────────────
    # Panel updates
    # ──────────────────────────────────────────────────────────────────────

    def _update_now_panel(self, r: dict):
        ans   = r["answer"]
        name  = r["student_name"]
        cid   = r["card_id"]
        conf  = r["confidence"]
        color = ANSWER_COLORS.get(ans, "#ffffff")
        bg    = ANSWER_BG.get(ans, "#222222")

        self.lbl_name.config(text=name)
        self.lbl_student_id.config(text=f"Card #{cid:03d}  ·  STU{cid:03d}")
        self.lbl_answer.config(text=ans, fg=color, bg=bg)

        answer_labels = {"A": "Answer A", "B": "Answer B", "C": "Answer C", "D": "Answer D"}
        self.lbl_answer_text.config(
            text=answer_labels.get(ans, "Unknown"),
            fg=color,
        )
        self.lbl_conf.config(text=f"Confidence: {conf:.0f}%")

    def _clear_now_panel(self):
        self.lbl_name.config(text="—")
        self.lbl_student_id.config(text="")
        self.lbl_answer.config(text="?", fg=ANSWER_COLORS["?"], bg=ANSWER_BG["?"])
        self.lbl_answer_text.config(text="Waiting for card...", fg=TEXT_GRAY)
        self.lbl_conf.config(text="")

    def _log_header(self):
        self.log_box.config(state="normal")
        self.log_box.insert("end", f"{'Card':<5}  {'Student':<22}  {'Ans'}\n", "header")
        self.log_box.insert("end", "─" * 34 + "\n", "dim")
        self.log_box.config(state="disabled")

    _logged_cards: set = set()

    def _update_log(self, r: dict):
        cid = r["card_id"]
        # Only log each card once per session (update if answer changed)
        key = (cid, r["answer"])
        if key in self._logged_cards:
            return
        self._logged_cards.add(key)

        ans  = r["answer"]
        line = f"{cid:<5}  {r['student_name'][:22]:<22}  "

        self.log_box.config(state="normal")
        self.log_box.insert("end", line, "dim")
        self.log_box.insert("end", ans + "\n", f"ans_{ans}")
        self.log_box.see("end")
        self.log_box.config(state="disabled")

    # ──────────────────────────────────────────────────────────────────────
    # Buttons
    # ──────────────────────────────────────────────────────────────────────

    def _reset_session(self):
        self.session.clear()
        self._logged_cards = set()
        self.log_box.config(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.config(state="disabled")
        self._log_header()
        self._clear_now_panel()
        self.status_label.config(text="  Session reset. Hold a card up to the camera...")

    def _save_responses(self):
        if not self.session:
            self.status_label.config(text="  Nothing to save yet.")
            return
        ts    = datetime.now().strftime("%Y%m%d_%H%M%S")
        jfile = _HERE / f"responses_{ts}.json"
        with open(jfile, "w", encoding="utf-8") as fh:
            json.dump(
                {"timestamp": ts, "responses": list(self.session.values())},
                fh, indent=2, ensure_ascii=False,
            )
        self.status_label.config(text=f"  ✅ Saved → {jfile.name}")
        print(f"[SAVED] {jfile}")

    # ──────────────────────────────────────────────────────────────────────
    # Cleanup
    # ──────────────────────────────────────────────────────────────────────

    def on_close(self):
        self.running = False
        if self.cap.isOpened():
            self.cap.release()
        self.root.destroy()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Plickers GUI Scanner")
    ap.add_argument("--camera",     type=int, default=0,    help="Camera index (default 0)")
    ap.add_argument("--cards-json", type=str, default=None, help="Path to output/cards.json")
    args = ap.parse_args()

    root = tk.Tk()
    root.geometry("1200x680")
    root.minsize(900, 580)

    app = PlickersApp(root, camera_index=args.camera, cards_json=args.cards_json)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
