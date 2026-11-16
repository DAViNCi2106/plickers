# Plickers-Style ArUco Response Card System

A classroom response system built with **OpenCV ArUco markers** + **Python**.
Each student gets a unique printed card. When they hold it up to the camera,
the system instantly identifies **who** they are and **what answer** (A/B/C/D)
they are choosing based on the card's orientation.

---

## How It Works

```
ArUco Marker ID  →  Card Number  →  Student Name
Card Orientation →  A / B / C / D  →  Answer
```

| Label held facing UP | Answer detected |
|---|---|
| A (top)    | A |
| B (right)  | B |
| C (bottom) | C |
| D (left)   | D |

---

## Project Structure

```
plickers/
│
├── START_SCANNER.bat           ← Double-click to launch scanner (Windows)
├── plickers_live.py            ← Main live scanner (OpenCV window)
├── plickers_gui.py             ← Alternative GUI scanner (Tkinter)
├── update_student_names.py     ← Inject Excel names into cards.json
├── 50_sample_students_plickers.xlsx  ← Student roster (50 students)
│
├── generator/
│   ├── card_config.py          ← Dimensions & ArUco settings
│   └── generate_cards.py       ← CLI card generator (prints student names)
│
├── scanner/
│   ├── orientation.py          ← Corner → rotation → answer logic
│   ├── detector.py             ← CardDetector class
│   └── scanner.py              ← Basic webcam scanner
│
├── validation/
│   └── validate_cards.py       ← Automated validation suite
│
├── cards/                      ← 50 PNG card images (with student names)
├── output/
│   ├── cards.json              ← Student ↔ card mapping (all 50 names)
│   └── cards.pdf               ← Printable PDF (6 cards per A4 page)
└── requirements.txt
```

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

> ⚠️ Use `opencv-contrib-python` (NOT `opencv-python`) — it includes ArUco.

### 2. Launch the scanner

**Option A — Double-click (easiest):**
```
Double-click  START_SCANNER.bat
```

**Option B — From terminal:**
```bash
python plickers_live.py

# If camera index 0 doesn't work:
python plickers_live.py --camera 1
```

The camera window opens automatically and starts detecting cards.

### 3. Print the cards

Open `output/cards.pdf` and print at **100% scale** (no "fit to page").
Six 85 mm × 85 mm cards are arranged per A4 page.
Each card now has the **student's name printed on it** for easy distribution.

### 4. Use in class

1. Distribute each numbered card to the matching student
2. Ask a multiple-choice question
3. Students hold their card with their chosen answer facing UP:
   - **A up** → Answer A
   - **B up** (right edge up) → Answer B
   - **C up** (bottom up) → Answer C
   - **D up** (left edge up) → Answer D
4. The scanner shows the student name + answer in real time

---

## Scanner Controls

| Key | Action |
|---|---|
| `Q` | Quit |
| `S` | Save all responses to JSON file |
| `R` | Reset session (clear captured answers) |

---

## Student Roster (50 Students)

| Card | Student | Card | Student |
|---|---|---|---|
| 001 | Arun Kumar       | 026 | Lakshmi Priya  |
| 002 | Priya Sharma     | 027 | Aravind S      |
| 003 | Rahul Verma      | 028 | Shreya Kapoor  |
| 004 | Sneha Iyer       | 029 | Pranav N       |
| 005 | Karthik Raj      | 030 | Deepika V      |
| 006 | Ananya Rao       | 031 | Ajay Krishnan  |
| 007 | Vikram Singh     | 032 | Bhavana R      |
| 008 | Divya Nair       | 033 | Surya Prakash  |
| 009 | Aditya Menon     | 034 | Neha Agarwal   |
| 010 | Meera Krishnan   | 035 | Ramesh K       |
| 011 | Rohit Patel      | 036 | Sanjana Devi   |
| 012 | Kavya S          | 037 | Abhishek T     |
| 013 | Sanjay Prakash   | 038 | Gayathri M     |
| 014 | Nisha Reddy      | 039 | Varun Raj      |
| 015 | Akash Gupta      | 040 | Rithika S      |
| 016 | Pooja Das        | 041 | Yash Shah      |
| 017 | Harish Babu      | 042 | Pavithra N     |
| 018 | Aishwarya M      | 043 | Manoj Kumar    |
| 019 | Naveen Kumar     | 044 | Ishita Mehta   |
| 020 | Keerthana R      | 045 | Dinesh R       |
| 021 | Siddharth Jain   | 046 | Harini B       |
| 022 | Swathi Narayanan | 047 | Sathish Kumar  |
| 023 | Vishal Anand     | 048 | Tanya Bose     |
| 024 | Janani S         | 049 | Gokul Nath     |
| 025 | Mohammed Irfan   | 050 | Anjali Menon   |

---

## Regenerate Cards (if roster changes)

```bash
# Regenerate all cards with names from the Excel file
python generator/generate_cards.py --start 1 --end 50 \
    --output cards --out-dir output \
    --excel 50_sample_students_plickers.xlsx

# Then update cards.json
python update_student_names.py
```

## Validate Cards

```bash
python validation/validate_cards.py --cards-dir cards
# Expected: 50/50 ALL PASS
```

---

## Known Limitations

| Issue | Detail |
|---|---|
| Extreme tilt | Detection degrades beyond ~55° off-axis |
| Glare | Use matte lamination — glossy reflects light |
| Distance | Minimum ~40×40 px of marker in frame |
| Lighting | Avoid harsh shadows directly over marker area |

---

## License

Original work — no Plickers assets used. MIT License.
