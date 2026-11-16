"""
generate_cards.py
=================
Generates printable ArUco response cards as individual PNG images,
an A4 PDF sheet, and a JSON manifest.

Card layout (square, 85 mm × 85 mm at 300 DPI)
------------------------------------------------

    ┌─────────────────────────────────────────────┐
    │                    ▲ A                       │
    │                                             │
    │   D ◀  ┌───────────────────────┐  ▶ B       │
    │        │                       │            │
    │        │    ArUco Marker       │            │
    │        │    (6×6, DICT_250)    │            │
    │        │                       │            │
    │        └───────────────────────┘            │
    │                                             │
    │              ▼ C                            │
    │          CARD  017                          │
    └─────────────────────────────────────────────┘

Orientation contract
--------------------
    When the card is HELD so that label X faces up:
        A → answer A   (card at 0°   from canonical)
        B → answer B   (card at 90°  CW from canonical)
        C → answer C   (card at 180° from canonical)
        D → answer D   (card at 270° CW from canonical)

Usage
-----
    python generate_cards.py --start 1 --end 50
    python generate_cards.py --start 1 --end 100 --output ../cards
    python generate_cards.py --help
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

try:
    import openpyxl
    _HAS_OPENPYXL = True
except ImportError:
    _HAS_OPENPYXL = False

# ── resolve card_config whether run from generator/ or project root ────────
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
from card_config import (
    CARD_SIZE_PX, MARKER_SIZE_PX, MARKER_X, MARKER_Y,
    LABEL_A_POS, LABEL_B_POS, LABEL_C_POS, LABEL_D_POS,
    CARD_NUM_Y, CARD_CX, MARKER_CY,
    WHITE, BLACK, DARK_GRAY, LIGHT_GRAY,
    BORDER_INSET_PX, BORDER_WIDTH_PX,
    ARUCO_DICT, DPI,
    A4_W_PX, A4_H_PX, A4_MARGIN_PX, A4_GAP_PX,
    CARDS_PER_ROW, CARDS_PER_COL, CARDS_PER_PAGE,
)


# ---------------------------------------------------------------------------
# Font loading (graceful fallback)
# ---------------------------------------------------------------------------

_FONT_CANDIDATES = [
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/calibrib.ttf",
    "C:/Windows/Fonts/verdanab.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in _FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    # Last resort: PIL built-in bitmap font (no size param)
    return ImageFont.load_default()


# Pre-load font sizes used across the card
_FONT_ANSWER = _load_font(80)   # A / B / C / D labels
_FONT_ARROW  = _load_font(36)   # ▲ ▶ ▼ ◀ directional arrows
_FONT_NUM    = _load_font(44)   # card number line
_FONT_SMALL  = _load_font(26)   # "CARD" prefix in number line


# ---------------------------------------------------------------------------
# Marker generation (OpenCV ArUco)
# ---------------------------------------------------------------------------

def _generate_marker_image(marker_id: int, size_px: int) -> Image.Image:
    """
    Generate a single ArUco marker as a Pillow Image (grayscale L mode).

    The marker includes the mandatory black border that ArUco needs for
    detection.  We add an extra white quiet-zone via card margins.
    """
    marker_np = np.zeros((size_px, size_px), dtype=np.uint8)
    cv2.aruco.generateImageMarker(ARUCO_DICT, marker_id, size_px, marker_np, 1)
    return Image.fromarray(marker_np, mode="L").convert("RGB")


# ---------------------------------------------------------------------------
# Single card drawing
# ---------------------------------------------------------------------------

def _draw_text_centred(
    draw:   ImageDraw.Draw,
    text:   str,
    cx:     int,
    cy:     int,
    font:   ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill:   tuple = BLACK,
) -> None:
    """Draw *text* centred on (cx, cy)."""
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    draw.text((cx - w // 2, cy - h // 2), text, font=font, fill=fill)


def generate_card_image(card_id: int, student_name: str = "") -> Image.Image:
    """
    Render a single response card for *card_id* and return a PIL Image.

    The ArUco marker ID equals card_id  (marker 1 → Card 001, etc.).
    """
    # ── canvas ──────────────────────────────────────────────────────────────
    img  = Image.new("RGB", (CARD_SIZE_PX, CARD_SIZE_PX), color=WHITE)
    draw = ImageDraw.Draw(img)

    # ── outer border ────────────────────────────────────────────────────────
    inset = BORDER_INSET_PX
    draw.rectangle(
        [inset, inset, CARD_SIZE_PX - inset, CARD_SIZE_PX - inset],
        outline=BLACK,
        width=BORDER_WIDTH_PX,
    )

    # ── ArUco marker ────────────────────────────────────────────────────────
    marker_img = _generate_marker_image(card_id, MARKER_SIZE_PX)
    img.paste(marker_img, (MARKER_X, MARKER_Y))

    # Thin border around marker for visual clarity
    draw.rectangle(
        [
            MARKER_X - 2,
            MARKER_Y - 2,
            MARKER_X + MARKER_SIZE_PX + 1,
            MARKER_Y + MARKER_SIZE_PX + 1,
        ],
        outline=DARK_GRAY,
        width=1,
    )

    # ── Answer labels ────────────────────────────────────────────────────────
    # Each label is drawn at the corresponding edge centre.
    # The arrow symbol visually reinforces which edge is "up".

    ax, ay = LABEL_A_POS
    _draw_text_centred(draw, "A", ax, ay - 10, _FONT_ANSWER)
    _draw_text_centred(draw, "▲", ax, ay + 46, _FONT_ARROW, fill=DARK_GRAY)

    bx, by = LABEL_B_POS
    _draw_text_centred(draw, "B", bx, by - 10, _FONT_ANSWER)
    _draw_text_centred(draw, "▶", bx, by + 46, _FONT_ARROW, fill=DARK_GRAY)

    cx_c, cy_c = LABEL_C_POS
    _draw_text_centred(draw, "C", cx_c, cy_c - 56, _FONT_ANSWER)
    _draw_text_centred(draw, "▼", cx_c, cy_c,      _FONT_ARROW, fill=DARK_GRAY)

    dx, dy = LABEL_D_POS
    _draw_text_centred(draw, "D", dx, dy - 10, _FONT_ANSWER)
    _draw_text_centred(draw, "◀", dx, dy + 46, _FONT_ARROW, fill=DARK_GRAY)

    # ── Card number ──────────────────────────────────────────────────────────
    num_text = f"CARD  {card_id:03d}"
    _draw_text_centred(draw, num_text, CARD_CX, CARD_NUM_Y, _FONT_NUM)

    # ── Student name (printed below card number) ──────────────────────────────
    if student_name:
        name_y = CARD_NUM_Y + 36
        _draw_text_centred(draw, student_name, CARD_CX, name_y, _FONT_SMALL, fill=DARK_GRAY)

    # ── Corner registration marks (subtle, help with perspective calibration)
    mark_r = 6
    mark_inset = BORDER_INSET_PX + 10
    for mx, my in [
        (mark_inset,                mark_inset),
        (CARD_SIZE_PX - mark_inset, mark_inset),
        (mark_inset,                CARD_SIZE_PX - mark_inset),
        (CARD_SIZE_PX - mark_inset, CARD_SIZE_PX - mark_inset),
    ]:
        draw.ellipse(
            [mx - mark_r, my - mark_r, mx + mark_r, my + mark_r],
            fill=DARK_GRAY,
        )

    return img


# ---------------------------------------------------------------------------
# Batch generation
# ---------------------------------------------------------------------------

def _load_student_names_from_excel(excel_path: Path) -> dict[int, dict]:
    """
    Load student names from the Excel roster.
    Returns {card_id: {"student_id": ..., "student_name": ...}}
    """
    if not _HAS_OPENPYXL:
        print("[WARN] openpyxl not installed — cards will use STUxxx labels")
        return {}
    wb = openpyxl.load_workbook(excel_path)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    data = {}
    for row in rows[1:]:   # skip header
        sno, name, sid, card_id = row
        data[int(card_id)] = {"student_id": str(sid), "student_name": str(name)}
    print(f"[GEN] Loaded {len(data)} student names from {excel_path.name}")
    return data


def generate_cards(
    start:  int,
    end:    int,
    output_dir: str  = "cards",
    out_dir: str     = "output",
    excel_path: Optional[str] = None,
) -> list[dict]:
    """
    Generate cards from *start* to *end* (inclusive).

    Saves each card as cards/card_NNN.png, produces output/cards.pdf
    and output/cards.json.

    Returns the manifest list for further use.
    """
    output_dir = Path(output_dir)
    out_dir    = Path(out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest: list[dict] = []
    card_images: list[Image.Image] = []

    total = end - start + 1
    print(f"[GEN] Generating {total} cards (IDs {start} to {end}) ...")

    # Load student names from Excel if provided, else fall back to STUxxx
    student_data: dict[int, dict] = {}
    if excel_path:
        ep = Path(excel_path)
        if ep.exists():
            student_data = _load_student_names_from_excel(ep)
        else:
            print(f"[WARN] Excel file not found: {excel_path}")

    for card_id in range(start, end + 1):
        info = student_data.get(card_id, {})
        sid  = info.get("student_id",   f"STU{card_id:03d}")
        name = info.get("student_name", f"STU{card_id:03d}")

        img      = generate_card_image(card_id, student_name=name)
        filename = output_dir / f"card_{card_id:03d}.png"
        img.save(str(filename), dpi=(DPI, DPI))
        card_images.append(img)

        manifest.append(
            {
                "card_id":  card_id,
                "marker_id": card_id,
                "student_id": sid,
                "student_name": name,
                "filename": str(filename),
                "orientation_mapping": {
                    "0":   "A",
                    "90":  "B",
                    "180": "C",
                    "270": "D",
                },
            }
        )

        if card_id % 10 == 0 or card_id == end:
            print(f"  ... {card_id - start + 1}/{total} done  ->  {filename.name}  [{name}]")

    # ── JSON manifest ────────────────────────────────────────────────────────
    json_path = out_dir / "cards.json"
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump({"cards": manifest}, fh, indent=2)
    print(f"[GEN] Manifest saved  ->  {json_path}")

    # ── PDF ──────────────────────────────────────────────────────────────────
    pdf_path = _build_pdf(card_images, manifest, out_dir)
    print(f"[GEN] PDF saved       ->  {pdf_path}")

    print(f"[GEN] Done. {total} cards generated.\n")
    return manifest


# ---------------------------------------------------------------------------
# PDF builder
# ---------------------------------------------------------------------------

def _build_pdf(
    card_images: list[Image.Image],
    manifest:    list[dict],
    out_dir:     Path,
) -> Path:
    """
    Arrange cards on A4 pages (CARDS_PER_PAGE per page) and save as PDF.
    """
    pages: list[Image.Image] = []

    for page_start in range(0, len(card_images), CARDS_PER_PAGE):
        batch = card_images[page_start: page_start + CARDS_PER_PAGE]
        page  = Image.new("RGB", (A4_W_PX, A4_H_PX), color=WHITE)

        for slot, card_img in enumerate(batch):
            row = slot // CARDS_PER_ROW
            col = slot %  CARDS_PER_ROW

            # Scale card to fit within grid cell while keeping 300 DPI quality
            cell_w = (A4_W_PX - 2 * A4_MARGIN_PX - (CARDS_PER_ROW - 1) * A4_GAP_PX) // CARDS_PER_ROW
            cell_h = (A4_H_PX - 2 * A4_MARGIN_PX - (CARDS_PER_COL - 1) * A4_GAP_PX) // CARDS_PER_COL
            cell_size = min(cell_w, cell_h)

            scaled = card_img.resize((cell_size, cell_size), Image.LANCZOS)

            x = A4_MARGIN_PX + col * (cell_size + A4_GAP_PX)
            y = A4_MARGIN_PX + row * (cell_size + A4_GAP_PX)
            page.paste(scaled, (x, y))

        pages.append(page)

    pdf_path = out_dir / "cards.pdf"
    if pages:
        pages[0].save(
            str(pdf_path),
            save_all    = True,
            append_images = pages[1:],
            resolution  = DPI,
        )

    return pdf_path


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Generate ArUco response cards (PNG + PDF + JSON).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument(
        "--start",  type=int, default=1,
        help="First card ID to generate (default: 1)",
    )
    ap.add_argument(
        "--end",    type=int, default=50,
        help="Last card ID to generate (default: 50)",
    )
    ap.add_argument(
        "--output", type=str, default="cards",
        help="Output directory for PNG files (default: cards/)",
    )
    ap.add_argument(
        "--out-dir", type=str, default="output",
        help="Directory for cards.pdf and cards.json (default: output/)",
    )
    ap.add_argument(
        "--preview", action="store_true",
        help="Open a window showing a preview of card 1 before generating",
    )
    ap.add_argument(
        "--excel", type=str, default=None,
        help="Path to Excel roster (.xlsx) to print student names on cards",
    )
    return ap.parse_args()


if __name__ == "__main__":
    args = _parse_args()

    if args.start < 1:
        sys.exit("[ERROR] --start must be ≥ 1")
    if args.end > 250:
        sys.exit("[ERROR] --end must be ≤ 250 (DICT_6X6_250 limit)")
    if args.start > args.end:
        sys.exit("[ERROR] --start must be ≤ --end")

    if args.preview:
        preview = generate_card_image(args.start)
        preview_np = cv2.cvtColor(np.array(preview), cv2.COLOR_RGB2BGR)
        # Show at screen-friendly size
        h, w = preview_np.shape[:2]
        preview_small = cv2.resize(preview_np, (w // 3, h // 3))
        cv2.imshow(f"Preview — Card {args.start:03d}  (any key to continue)", preview_small)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    generate_cards(
        start      = args.start,
        end        = args.end,
        output_dir = args.output,
        out_dir    = args.out_dir,
        excel_path = args.excel,
    )
