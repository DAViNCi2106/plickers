"""
card_config.py
==============
Central configuration for the ArUco Response Card system.

All physical dimensions are in millimetres; pixel equivalents are
derived at the target DPI so that only one constant needs changing
to re-target a different print resolution.
"""

import cv2

# ---------------------------------------------------------------------------
# Print resolution
# ---------------------------------------------------------------------------
DPI = 300
MM_PER_INCH = 25.4
MM_TO_PX = DPI / MM_PER_INCH          # pixels per millimetre at DPI


def mm(value: float) -> int:
    """Convert millimetres to pixels at the configured DPI."""
    return int(round(value * MM_TO_PX))


# ---------------------------------------------------------------------------
# Card geometry (square so all four rotations look identical in the hand)
# ---------------------------------------------------------------------------
CARD_SIZE_MM = 85                      # card is 85 mm × 85 mm
CARD_SIZE_PX = mm(CARD_SIZE_MM)        # ≈ 1004 px at 300 DPI

# Outer border drawn inset from the card edge
BORDER_INSET_MM = 3
BORDER_INSET_PX = mm(BORDER_INSET_MM)
BORDER_WIDTH_PX = 3                    # line width in pixels

# ---------------------------------------------------------------------------
# Marker geometry
# ---------------------------------------------------------------------------
# The ArUco marker occupies 56 % of the card width; this keeps it large
# enough for reliable detection at ≥ 1 m while leaving room for labels.
MARKER_RATIO = 0.56
MARKER_SIZE_PX = int(CARD_SIZE_PX * MARKER_RATIO)   # ≈ 562 px

# Marker is centred horizontally and placed in the upper portion of the card
MARKER_X = (CARD_SIZE_PX - MARKER_SIZE_PX) // 2     # left edge of marker
MARKER_Y = mm(17)                                    # top edge of marker (17 mm down)

# ---------------------------------------------------------------------------
# ArUco dictionary
# ---------------------------------------------------------------------------
# DICT_6X6_250 provides:
#   • 6×6 binary grid  → strong Hamming distance between IDs
#   • up to 250 unique markers  → covers 100 students easily
#   • native OpenCV support  → zero extra dependencies
ARUCO_DICT_ID = cv2.aruco.DICT_6X6_250
ARUCO_DICT    = cv2.aruco.getPredefinedDictionary(ARUCO_DICT_ID)

# ---------------------------------------------------------------------------
# Label positions (pre-computed, relative to card origin)
# ---------------------------------------------------------------------------
CARD_CX = CARD_SIZE_PX // 2                           # horizontal centre
MARKER_CY = MARKER_Y + MARKER_SIZE_PX // 2            # vertical centre of marker

# A  — top-centre, above marker
LABEL_A_POS = (CARD_CX, mm(9))

# B  — right-centre, beside marker
LABEL_B_POS = (CARD_SIZE_PX - mm(9), MARKER_CY)

# C  — bottom-centre, below card-number
LABEL_C_POS = (CARD_CX, CARD_SIZE_PX - mm(9))

# D  — left-centre, beside marker
LABEL_D_POS = (mm(9), MARKER_CY)

# Card-number text centred below the marker
CARD_NUM_Y = MARKER_Y + MARKER_SIZE_PX + mm(7)

# ---------------------------------------------------------------------------
# Colours  (RGB for Pillow)
# ---------------------------------------------------------------------------
WHITE      = (255, 255, 255)
BLACK      = (0,   0,   0)
DARK_GRAY  = (40,  40,  40)
LIGHT_GRAY = (220, 220, 220)

# ---------------------------------------------------------------------------
# A4 sheet layout for PDF output
# ---------------------------------------------------------------------------
A4_W_MM = 210
A4_H_MM = 297
A4_W_PX = mm(A4_W_MM)
A4_H_PX = mm(A4_H_MM)
A4_MARGIN_MM   = 8
A4_MARGIN_PX   = mm(A4_MARGIN_MM)
A4_GAP_MM      = 4                    # gap between cards on page
A4_GAP_PX      = mm(A4_GAP_MM)
CARDS_PER_ROW  = 2
CARDS_PER_COL  = 3
CARDS_PER_PAGE = CARDS_PER_ROW * CARDS_PER_COL   # 6 per A4

# ---------------------------------------------------------------------------
# Orientation / answer mappings
# ---------------------------------------------------------------------------
# corner_index_to_rotation:
#   When the ArUco detector returns corners[i] nearest to the image
#   top-left, the card has been rotated by this many degrees clockwise.
CORNER_TO_ROTATION: dict[int, int] = {0: 0, 1: 90, 2: 180, 3: 270}

# Physical card rotation → answer letter
ROTATION_TO_ANSWER: dict[int, str] = {0: "A", 90: "B", 180: "C", 270: "D"}
ANSWER_TO_ROTATION: dict[str, int] = {v: k for k, v in ROTATION_TO_ANSWER.items()}
