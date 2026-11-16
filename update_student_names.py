"""
update_student_names.py
=======================
Reads the student roster from the Excel file and injects real student
names + IDs into output/cards.json, replacing the STUxxx placeholders.

Run once:
    python update_student_names.py
"""
import json
import sys
from pathlib import Path

try:
    import openpyxl
except ImportError:
    sys.exit("[ERROR] openpyxl not installed. Run: pip install openpyxl")

_ROOT = Path(__file__).resolve().parent

EXCEL_PATH = _ROOT / "50_sample_students_plickers.xlsx"
JSON_PATH  = _ROOT / "output" / "cards.json"


def load_students() -> dict:
    """Return {card_id: {"student_id": ..., "student_name": ...}}"""
    wb = openpyxl.load_workbook(EXCEL_PATH)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    student_data = {}
    for row in rows[1:]:           # skip header row
        sno, name, sid, card_id = row
        student_data[int(card_id)] = {
            "student_id":   str(sid),
            "student_name": str(name),
        }
    return student_data


def update_json(student_data: dict) -> None:
    with open(JSON_PATH, encoding="utf-8") as fh:
        data = json.load(fh)

    updated = 0
    for card in data["cards"]:
        cid = card["card_id"]
        if cid in student_data:
            card["student_id"]   = student_data[cid]["student_id"]
            card["student_name"] = student_data[cid]["student_name"]
            updated += 1

    with open(JSON_PATH, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)

    print(f"[OK] Updated {updated}/{len(data['cards'])} cards in {JSON_PATH}")
    for card in data["cards"][:5]:
        print(f"     Card {card['card_id']:03d} -> {card['student_id']}  {card['student_name']}")
    print("     ...")


if __name__ == "__main__":
    if not EXCEL_PATH.exists():
        sys.exit(f"[ERROR] Excel file not found: {EXCEL_PATH}")
    if not JSON_PATH.exists():
        sys.exit(f"[ERROR] cards.json not found: {JSON_PATH}")

    students = load_students()
    print(f"[INFO] Loaded {len(students)} students from Excel")
    update_json(students)
    print("[DONE] cards.json updated with real student names.")
