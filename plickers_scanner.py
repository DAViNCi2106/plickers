"""
plickers_scanner.py
===================
Plickers Live Scanner using Tkinter GUI + OpenCV camera capture.
This ALWAYS opens a visible window on Windows, regardless of how it is launched.

Usage
-----
    python plickers_scanner.py
"""

import json
import os
import sys
import time
import threading
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import StringVar, messagebox

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

import cv2
import numpy as np
from PIL import Image, ImageTk

# resolve scanner imports
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE / "scanner"))
from detector import CardDetector

ANSWER_COLORS = {
    "A": "#4AE640",
    "B": "#F0A030",
    "C": "#3090FF",
    "D": "#E040E0",
    "?": "#888888",
}
BG        = "#14162B"
BG_PANEL  = "#1E2030"
ACCENT    = "#50E664"
FG_WHITE  = "#F0F0F0"
FG_GRAY   = "#8890AA"
BORDER    = "#32364E"


def load_student_map():
    path = _HERE / "output" / "cards.json"
    sm = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for c in data.get("cards", []):
                sm[c["card_id"]] = c.get("student_name", f"STU{c['card_id']:03d}")
            print(f"[INFO] Loaded {len(sm)} students")
        except Exception as e:
            print(f"[WARN] {e}")
    return sm


class PlickersApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Plickers Live Scanner")
        self.root.configure(bg=BG)
        self.root.resizable(True, True)

        self.student_map = load_student_map()
        self.detector    = CardDetector(student_map=self.student_map)

        self.cap            = None
        self.running        = False
        self.session        = {}
        self._lock          = threading.Lock()
        self._pending_frame = None
        self._last_results  = []
        self._fps           = 0.0

        self._build_ui()
        self._open_camera()
        self._update_loop()

    def _build_ui(self):
        self.root.columnconfigure(0, weight=3)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        cam_frame = tk.Frame(self.root, bg=BG, padx=4, pady=4)
        cam_frame.grid(row=0, column=0, sticky="nsew")
        cam_frame.rowconfigure(1, weight=1)
        cam_frame.columnconfigure(0, weight=1)

        title_bar = tk.Frame(cam_frame, bg=BG_PANEL, pady=6)
        title_bar.grid(row=0, column=0, sticky="ew")
        tk.Label(title_bar, text="PLICKERS LIVE SCANNER",
                 font=("Segoe UI", 13, "bold"), bg=BG_PANEL, fg=ACCENT
                 ).pack(side="left", padx=12)
        self.fps_label = tk.Label(title_bar, text="FPS: --",
                                  font=("Segoe UI", 9), bg=BG_PANEL, fg=FG_GRAY)
        self.fps_label.pack(side="right", padx=12)

        self.canvas = tk.Canvas(cam_frame, bg="#000000", width=800, height=520,
                                highlightthickness=0)
        self.canvas.grid(row=1, column=0, sticky="nsew", padx=4, pady=(4, 0))
        self.no_cam_id = self.canvas.create_text(
            400, 260, text="Opening camera...", fill=FG_GRAY,
            font=("Segoe UI", 16)
        )

        ctrl = tk.Frame(cam_frame, bg=BG_PANEL, pady=6)
        ctrl.grid(row=2, column=0, sticky="ew", pady=(4, 0))
        tk.Button(ctrl, text="Save Responses", command=self._save,
                  bg="#2A2D45", fg=FG_WHITE, relief="flat",
                  font=("Segoe UI", 10), padx=14, pady=4
                  ).pack(side="left", padx=8)
        tk.Button(ctrl, text="Reset Session", command=self._reset,
                  bg="#2A2D45", fg=FG_WHITE, relief="flat",
                  font=("Segoe UI", 10), padx=14, pady=4
                  ).pack(side="left", padx=4)
        self.status_lbl = tk.Label(ctrl, text="Waiting for cards...",
                                   font=("Segoe UI", 9, "italic"),
                                   bg=BG_PANEL, fg=FG_GRAY)
        self.status_lbl.pack(side="right", padx=12)

        panel = tk.Frame(self.root, bg=BG_PANEL, width=300, padx=12, pady=10)
        panel.grid(row=0, column=1, sticky="nsew", padx=(0, 4), pady=4)
        panel.columnconfigure(0, weight=1)

        tk.Label(panel, text="NOW DETECTED", font=("Segoe UI", 9, "bold"),
                 bg=BG_PANEL, fg=FG_GRAY).grid(row=0, column=0, sticky="w")

        self.name_var = StringVar(value="--")
        self.name_lbl = tk.Label(panel, textvariable=self.name_var,
                                 font=("Segoe UI", 17, "bold"),
                                 bg=BG_PANEL, fg=FG_WHITE,
                                 wraplength=260, justify="left")
        self.name_lbl.grid(row=1, column=0, sticky="w", pady=(4, 0))

        self.card_var = StringVar(value="")
        tk.Label(panel, textvariable=self.card_var,
                 font=("Segoe UI", 9), bg=BG_PANEL, fg=FG_GRAY
                 ).grid(row=2, column=0, sticky="w")

        self.badge_canvas = tk.Canvas(panel, width=120, height=120,
                                      bg=BG_PANEL, highlightthickness=0)
        self.badge_canvas.grid(row=3, column=0, pady=12)
        self._draw_badge("?")

        self.conf_var = StringVar(value="")
        tk.Label(panel, textvariable=self.conf_var,
                 font=("Segoe UI", 9), bg=BG_PANEL, fg=FG_GRAY
                 ).grid(row=4, column=0)

        tk.Frame(panel, bg=BORDER, height=1).grid(row=5, column=0,
                                                  sticky="ew", pady=10)

        tk.Label(panel, text="SESSION RESPONSES",
                 font=("Segoe UI", 9, "bold"), bg=BG_PANEL, fg=FG_GRAY
                 ).grid(row=6, column=0, sticky="w")

        log_frame = tk.Frame(panel, bg=BG_PANEL)
        log_frame.grid(row=7, column=0, sticky="nsew", pady=(4, 0))
        panel.rowconfigure(7, weight=1)

        scrollbar = tk.Scrollbar(log_frame)
        scrollbar.pack(side="right", fill="y")
        self.log_list = tk.Listbox(
            log_frame, yscrollcommand=scrollbar.set,
            bg="#181A2A", fg=FG_WHITE, selectbackground="#2A2D45",
            font=("Consolas", 9), borderwidth=0, highlightthickness=0,
            relief="flat"
        )
        self.log_list.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.log_list.yview)

    def _draw_badge(self, answer):
        self.badge_canvas.delete("all")
        color = ANSWER_COLORS.get(answer, ANSWER_COLORS["?"])
        cx, cy, r = 60, 60, 50
        self.badge_canvas.create_oval(cx-r-6, cy-r-6, cx+r+6, cy+r+6,
                                      fill="#0D0F1E", outline=color, width=3)
        self.badge_canvas.create_text(cx, cy, text=answer,
                                      font=("Segoe UI", 44, "bold"), fill=color)

    def _open_camera(self):
        t = threading.Thread(target=self._camera_thread, daemon=True)
        t.start()

    def _camera_thread(self):
        cap = None
        # Try DirectShow first (Windows - faster init)
        for idx in range(5):
            c = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
            if c.isOpened():
                cap = c
                print(f"[INFO] Camera {idx} opened (DirectShow)")
                break
            c.release()

        if cap is None:
            for idx in range(5):
                c = cv2.VideoCapture(idx)
                if c.isOpened():
                    cap = c
                    print(f"[INFO] Camera {idx} opened")
                    break
                c.release()

        if cap is None:
            self.root.after(0, lambda: self.canvas.itemconfig(
                self.no_cam_id,
                text="No camera found!\nPlug in a webcam and restart."
            ))
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT,  720)
        self.cap     = cap
        self.running = True

        prev = time.perf_counter()
        while self.running:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.02)
                continue

            annotated, results = self.detector.detect_and_annotate(frame)

            now  = time.perf_counter()
            fps  = 1.0 / max(now - prev, 1e-9)
            prev = now

            with self._lock:
                self._pending_frame = annotated
                self._last_results  = results
                self._fps           = fps

        cap.release()

    def _update_loop(self):
        try:
            self._refresh()
        except Exception as e:
            pass
        self.root.after(33, self._update_loop)

    def _refresh(self):
        with self._lock:
            frame   = self._pending_frame
            results = list(self._last_results)
            fps     = self._fps

        if frame is None:
            return

        # Convert BGR -> RGB -> PIL -> Tk
        rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        cw    = self.canvas.winfo_width()  or 800
        ch    = self.canvas.winfo_height() or 520
        fh, fw = rgb.shape[:2]
        scale = min(cw / fw, ch / fh)
        nw    = int(fw * scale)
        nh    = int(fh * scale)
        rgb   = cv2.resize(rgb, (nw, nh), interpolation=cv2.INTER_LINEAR)

        img = ImageTk.PhotoImage(Image.fromarray(rgb))
        self.canvas.delete("all")
        self.canvas.create_image(cw // 2, ch // 2, anchor="center", image=img)
        self.canvas._photo = img   # prevent GC

        self.fps_label.config(text=f"FPS: {fps:.1f}")

        if results:
            r    = results[-1]
            ans  = r["answer"]
            name = r["student_name"]
            cid  = r["card_id"]
            conf = r["confidence"]
            color = ANSWER_COLORS.get(ans, FG_WHITE)

            self.name_var.set(name)
            self.card_var.set(f"Card #{cid:03d}")
            self.conf_var.set(f"Confidence: {conf:.0f}%")
            self._draw_badge(ans)
            self.name_lbl.config(fg=color)
            self.status_lbl.config(text=f"Detected: {name}  ->  {ans}")

            self.session[cid] = r
            self._refresh_log()
        else:
            self.status_lbl.config(text="Waiting for cards...")

    def _refresh_log(self):
        self.log_list.delete(0, "end")
        for cid in sorted(self.session.keys()):
            r   = self.session[cid]
            ans = r["answer"]
            row = f"#{cid:03d}  {r['student_name'][:18]:<18}  [{ans}]"
            self.log_list.insert("end", row)

    def _save(self):
        if not self.session:
            self.status_lbl.config(text="Nothing to save yet.")
            return

        xl_path = _HERE / "50_sample_students_plickers.xlsx"
        ts      = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        saved_count = 0

        try:
            wb = openpyxl.load_workbook(xl_path)
            ws = wb.active

            # ── Ensure header columns exist ───────────────────────────────
            # Find existing headers in row 1
            headers = {cell.value: cell.column for cell in ws[1] if cell.value}

            # Add "Answer" column if missing
            if "Answer" not in headers:
                ans_col = ws.max_column + 1
                ws.cell(row=1, column=ans_col, value="Answer")
                hdr_cell = ws.cell(row=1, column=ans_col)
                hdr_cell.font      = Font(bold=True, color="FFFFFF")
                hdr_cell.fill      = PatternFill("solid", fgColor="1E2030")
                hdr_cell.alignment = Alignment(horizontal="center")
                headers["Answer"]  = ans_col

            # Add "Saved At" column if missing
            if "Saved At" not in headers:
                ts_col = ws.max_column + 1
                ws.cell(row=1, column=ts_col, value="Saved At")
                hdr_cell = ws.cell(row=1, column=ts_col)
                hdr_cell.font      = Font(bold=True, color="FFFFFF")
                hdr_cell.fill      = PatternFill("solid", fgColor="1E2030")
                hdr_cell.alignment = Alignment(horizontal="center")
                headers["Saved At"] = ts_col

            ans_col = headers["Answer"]
            ts_col  = headers["Saved At"]

            # Find the "Card ID" column index
            card_id_col = headers.get("Card ID")
            if card_id_col is None:
                raise ValueError("'Card ID' column not found in Excel sheet.")

            # Answer colour map (background fills)
            ans_fills = {
                "A": PatternFill("solid", fgColor="2D6A2D"),   # dark green
                "B": PatternFill("solid", fgColor="7A5000"),   # dark amber
                "C": PatternFill("solid", fgColor="1A3F7A"),   # dark blue
                "D": PatternFill("solid", fgColor="6A1F6A"),   # dark purple
            }
            white_font = Font(bold=True, color="FFFFFF")
            center_align = Alignment(horizontal="center")

            # ── Walk every data row and fill answer if we have it ─────────
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
                cell_card_id = row[card_id_col - 1]
                try:
                    cid = int(cell_card_id.value)
                except (TypeError, ValueError):
                    continue

                if cid in self.session:
                    ans = self.session[cid]["answer"]
                    # Write answer
                    a_cell = ws.cell(row=cell_card_id.row, column=ans_col)
                    a_cell.value     = ans
                    a_cell.font      = white_font
                    a_cell.fill      = ans_fills.get(ans, PatternFill())
                    a_cell.alignment = center_align
                    # Write timestamp
                    t_cell = ws.cell(row=cell_card_id.row, column=ts_col)
                    t_cell.value     = ts
                    t_cell.alignment = Alignment(horizontal="center")
                    saved_count += 1

            # Auto-fit answer + timestamp columns width
            ws.column_dimensions[
                openpyxl.utils.get_column_letter(ans_col)
            ].width = 10
            ws.column_dimensions[
                openpyxl.utils.get_column_letter(ts_col)
            ].width = 20

            wb.save(xl_path)
            msg = f"Saved {saved_count} responses to Excel!"
            self.status_lbl.config(text=f"✔  {msg}")
            print(f"[SAVED] {msg} -> {xl_path}")
            messagebox.showinfo("Saved!", f"{msg}\n\nFile: {xl_path.name}\nTime: {ts}")

        except PermissionError:
            err = "Excel file is open! Close it in Excel first, then save."
            self.status_lbl.config(text=f"ERROR: {err}")
            messagebox.showerror("Save Failed", err)
        except Exception as e:
            err = str(e)
            self.status_lbl.config(text=f"ERROR: {err}")
            messagebox.showerror("Save Failed", f"Could not save to Excel:\n{err}")
            print(f"[ERROR] {e}")

    def _reset(self):
        self.session.clear()
        self._refresh_log()
        self.name_var.set("--")
        self.card_var.set("")
        self.conf_var.set("")
        self._draw_badge("?")
        self.name_lbl.config(fg=FG_WHITE)
        self.status_lbl.config(text="Session reset.")

    def on_close(self):
        self.running = False
        time.sleep(0.15)
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1200x680")
    root.minsize(900, 560)

    app = PlickersApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)

    root.lift()
    root.attributes("-topmost", True)
    root.after(600, lambda: root.attributes("-topmost", False))

    root.mainloop()
