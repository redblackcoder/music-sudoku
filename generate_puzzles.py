#!/usr/bin/env python3
"""
Generate Musical Sudoku PDF from KrazyDad puzzle PDFs.
Extracts number grids from source PDFs, maps digits to musical symbols
using the same mapping as the webapp (index.html), and produces a single
PDF with one puzzle per page in the webapp's print layout.
"""

import fitz  # PyMuPDF
import os
import sys

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PUZZLES_DIR = os.path.join(BASE_DIR, "puzzles")
OUTPUT_PDF = os.path.join(BASE_DIR, "musical_sudoku_puzzles.pdf")
BRAVURA_FONT = os.path.join(BASE_DIR, "Bravura.otf")

# Page size: US Letter
PAGE_W, PAGE_H = 612, 792

# Grid geometry (matches webapp print: 64px cells -> ~48pt at 72dpi)
CELL_SIZE = 48
GRID_SIZE = CELL_SIZE * 9  # 432
GRID_LEFT = (PAGE_W - GRID_SIZE) / 2
GRID_TOP = 340  # Y offset for grid start

# Symbol data matching webapp's SYMBOL_DATA
# Each entry: (unicode_char, font_size, dy_offset)
# dy offsets are for centering in cell (adapted from CSS translateY)
SYMBOL_DATA = {
    1: ("\uE1D5", 34, 8),   # noteQuarterUp
    2: ("\uE1D3", 34, 8),   # noteHalfUp
    3: ("\uE1D2", 34, 2),   # noteWhole
    4: ("\uE1D7", 34, 8),   # note8thUp
    5: ("\uE4E5", 34, 6),   # restQuarter
    # 6 = beamed eighths (drawn manually)
    7: ("\uE050", 24, 4),   # gClef
    8: ("\uE062", 26, 4),   # fClef
    9: ("\uE262", 30, 4),   # accidentalSharp
}

SYMBOL_NAMES = {
    1: "Quarter Note",
    2: "Half Note",
    3: "Whole Note",
    4: "Eighth Note",
    5: "Quarter Rest",
    6: "Beamed Eighths",
    7: "Treble Clef",
    8: "Bass Clef",
    9: "Sharp",
}

SYMBOL_DESCRIPTIONS = {
    1: "A filled note head with a stem; lasts 1 beat",
    2: "An open note head with a stem; lasts 2 beats",
    3: "An open note head without a stem; lasts 4 beats",
    4: "A filled note head with a stem and one flag; lasts 1/2 beat",
    5: "A zigzag symbol meaning silence for 1 beat",
    6: "Two eighth notes joined by a beam; each lasts 1/2 beat",
    7: "The G-clef; marks the higher-pitched staff",
    8: "The F-clef with two dots; marks the lower-pitched staff",
    9: "The sharp sign; raises a note by a half step",
}

# Difficulty folder order and display names
DIFFICULTY_ORDER = [
    ("easy", "Easy"),
    ("novice", "Novice"),
    ("intermediate", "Intermediate"),
    ("hard", "Hard"),
]

# ---------------------------------------------------------------------------
# Grid extraction from source PDFs
# ---------------------------------------------------------------------------

def extract_grids_from_pdf(pdf_path):
    """Extract 9x9 sudoku grids from the first 8 pages of a KrazyDad PDF."""
    doc = fitz.open(pdf_path)
    grids = []

    # KrazyDad PDFs use a consistent grid layout.
    # Reference positions (from verified extraction):
    REF_XS = [113.0, 156.9, 200.8, 244.7, 288.6, 332.5, 376.4, 420.3, 464.2]
    REF_YS = [123.5, 167.4, 211.3, 255.2, 299.1, 343.0, 386.9, 430.7, 474.6]
    TOLERANCE = 15

    # Each PDF has 8 puzzle pages, then hints, then answers
    num_puzzle_pages = min(8, len(doc))

    for page_idx in range(num_puzzle_pages):
        page = doc[page_idx]
        words = page.get_text("words")

        # Build the grid by matching digit positions to reference grid
        grid = [[0] * 9 for _ in range(9)]
        for w in words:
            text = w[4].strip()
            if not (text.isdigit() and len(text) == 1):
                continue
            x, y = float(w[0]), float(w[1])
            col = _closest_idx(x, REF_XS, TOLERANCE)
            row = _closest_idx(y, REF_YS, TOLERANCE)
            if 0 <= col < 9 and 0 <= row < 9:
                grid[row][col] = int(text)

        # Validate: should have some filled cells
        filled = sum(1 for r in grid for c in r if c != 0)
        if filled >= 17:
            grids.append(grid)

    doc.close()
    return grids


def _closest_idx(val, positions, tolerance=15):
    """Find the index of the closest position within tolerance."""
    for i, p in enumerate(positions):
        if abs(val - p) < tolerance:
            return i
    return -1


# ---------------------------------------------------------------------------
# PDF Generation
# ---------------------------------------------------------------------------

def draw_beamed_eighths(page, cx, cy, scale=1.0):
    """Draw beamed eighth notes (symbol 6) at center position (cx, cy).

    Matches the webapp SVG: viewBox="0 0 52 56", displayed at 38x36px.
    """
    # Scale factor: webapp displays at 38x36 from viewBox 0 0 52 56
    # For print, the cell SVG is 34x30
    sw = 34 * scale
    sh = 30 * scale
    sx = sw / 52  # x scale
    sy = sh / 56  # y scale

    # Origin: top-left of the SVG area
    ox = cx - sw / 2
    oy = cy - sh / 2

    def tx(x):
        return ox + x * sx

    def ty(y):
        return oy + y * sy

    # Draw filled ellipses (note heads) - rotated by -20 degrees
    import math

    def draw_ellipse(ecx, ecy, rx, ry, angle_deg):
        """Draw a filled rotated ellipse using a polygon approximation."""
        angle = math.radians(angle_deg)
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        points = []
        for i in range(36):
            t = 2 * math.pi * i / 36
            px = rx * math.cos(t)
            py = ry * math.sin(t)
            # Rotate
            rpx = px * cos_a - py * sin_a
            rpy = px * sin_a + py * cos_a
            points.append(fitz.Point(tx(ecx + rpx), ty(ecy + rpy)))
        shape = page.new_shape()
        shape.draw_polyline(points + [points[0]])
        shape.finish(fill=(0, 0, 0), color=(0, 0, 0))
        shape.commit()

    # Ellipse 1: cx=9, cy=44, rx=7.5, ry=5.5, rotate=-20
    draw_ellipse(9, 44, 7.5, 5.5, -20)
    # Ellipse 2: cx=37, cy=44
    draw_ellipse(37, 44, 7.5, 5.5, -20)

    # Stems
    shape = page.new_shape()
    # Stem 1: rect x=15, y=6, w=2.2, h=39
    shape.draw_rect(fitz.Rect(tx(15), ty(6), tx(17.2), ty(45)))
    shape.finish(fill=(0, 0, 0), color=(0, 0, 0))
    # Stem 2: rect x=43, y=6, w=2.2, h=39
    shape.draw_rect(fitz.Rect(tx(43), ty(6), tx(45.2), ty(45)))
    shape.finish(fill=(0, 0, 0), color=(0, 0, 0))
    # Beam: rect x=15, y=6, w=30.2, h=4.5
    shape.draw_rect(fitz.Rect(tx(15), ty(6), tx(45.2), ty(10.5)))
    shape.finish(fill=(0, 0, 0), color=(0, 0, 0))
    shape.commit()


def draw_symbol_in_cell(page, bravura_font, num, cell_x, cell_y, cell_size, fontsize_scale=1.0):
    """Draw a musical symbol centered in a cell."""
    cx = cell_x + cell_size / 2
    cy = cell_y + cell_size / 2

    if num == 6:
        draw_beamed_eighths(page, cx, cy, scale=fontsize_scale)
        return

    char, size, dy = SYMBOL_DATA[num]
    size = size * fontsize_scale

    # For fitz TextWriter, y is the baseline
    # We need to center the glyph in the cell
    # The dy from CSS translateY shifts down, so we add it
    tw = fitz.TextWriter(page.rect)
    # Get the text width for centering
    text_width = bravura_font.text_length(char, fontsize=size)
    text_x = cx - text_width / 2
    # Vertical centering: baseline roughly at center + offset
    text_y = cy + size * 0.15 + dy * fontsize_scale * 0.5
    tw.append((text_x, text_y), char, font=bravura_font, fontsize=size)
    tw.write_text(page)


def draw_small_symbol(page, bravura_font, num, cx, cy, size_factor=0.55):
    """Draw a small symbol for the reference table."""
    if num == 6:
        draw_beamed_eighths(page, cx, cy, scale=0.45)
        return

    char, size, dy = SYMBOL_DATA[num]
    size = size * size_factor
    tw = fitz.TextWriter(page.rect)
    text_width = bravura_font.text_length(char, fontsize=size)
    text_x = cx - text_width / 2
    text_y = cy + size * 0.15 + dy * size_factor * 0.4
    tw.append((text_x, text_y), char, font=bravura_font, fontsize=size)
    tw.write_text(page)


def draw_puzzle_page(doc, fonts, grid, difficulty_label):
    """Draw a single puzzle page matching the webapp's print layout."""
    bravura_font = fonts["bravura"]
    georgia_font = fonts["georgia"]
    georgia_bold = fonts["georgia_bold"]
    georgia_italic = fonts["georgia_italic"]

    page = doc.new_page(width=PAGE_W, height=PAGE_H)

    # Page margins (matching webapp: 0.45in top, 0.65in right, 0.4in bottom, 0.45in left)
    margin_left = 0.45 * 72  # 32.4
    margin_right = 0.65 * 72  # 46.8
    margin_top = 0.45 * 72  # 32.4

    y = margin_top

    # --- Header: "Musical Sudoku" ---
    tw = fitz.TextWriter(page.rect)
    header_text = "Musical Sudoku"
    header_size = 20  # ~1.6rem
    header_width = georgia_bold.text_length(header_text, fontsize=header_size)
    tw.append(((PAGE_W - header_width) / 2, y + header_size), header_text,
              font=georgia_bold, fontsize=header_size)
    tw.write_text(page)
    y += header_size + 12

    # --- Instructions ---
    inst_title_size = 10.5
    tw = fitz.TextWriter(page.rect)
    tw.append((margin_left, y + inst_title_size), "Instructions",
              font=georgia_bold, fontsize=inst_title_size)
    tw.write_text(page)
    y += inst_title_size + 4

    inst_body = (
        "Solve the Sudoku puzzle using standard Sudoku rules, however, instead of using "
        "digits 1-9, use the following musical symbols. Each symbol must appear exactly "
        "once in each row, each column, and each 3x3 square."
    )
    inst_size = 9.5
    tw = fitz.TextWriter(page.rect)
    tw.fill_textbox(
        fitz.Rect(margin_left, y, PAGE_W - margin_right, y + 50),
        inst_body, font=georgia_font, fontsize=inst_size, align=fitz.TEXT_ALIGN_LEFT
    )
    tw.write_text(page)
    y += 38

    # --- Symbol Reference Table (2 columns) ---
    y += 6
    table_top = y
    col1_x = margin_left
    col2_x = PAGE_W / 2 + 10

    left_symbols = [1, 2, 3, 4, 5]
    right_symbols = [6, 7, 8, 9]

    row_height = 22
    sym_col_width = 30
    name_col_width = 80
    desc_font_size = 8.5

    def draw_table_column(symbols, start_x, start_y):
        curr_y = start_y
        col_width = (PAGE_W / 2 - margin_left - 15) if start_x < PAGE_W / 2 else (PAGE_W - margin_right - start_x)

        for num in symbols:
            # Symbol
            sym_cx = start_x + sym_col_width / 2
            sym_cy = curr_y + row_height / 2
            draw_small_symbol(page, bravura_font, num, sym_cx, sym_cy, size_factor=0.5)

            # Name (bold)
            name_x = start_x + sym_col_width + 4
            tw_name = fitz.TextWriter(page.rect)
            tw_name.append((name_x, curr_y + row_height - 6),
                           SYMBOL_NAMES[num], font=georgia_bold, fontsize=desc_font_size)
            tw_name.write_text(page)

            # Description
            desc_x = name_x + name_col_width + 2
            tw_desc = fitz.TextWriter(page.rect)
            tw_desc.fill_textbox(
                fitz.Rect(desc_x, curr_y + 2, start_x + col_width, curr_y + row_height + 4),
                SYMBOL_DESCRIPTIONS[num], font=georgia_font, fontsize=desc_font_size - 0.5,
                align=fitz.TEXT_ALIGN_LEFT
            )
            tw_desc.write_text(page)

            # Bottom border
            shape = page.new_shape()
            shape.draw_line(fitz.Point(start_x, curr_y + row_height),
                            fitz.Point(start_x + col_width, curr_y + row_height))
            shape.finish(color=(0.85, 0.85, 0.85), width=0.5)
            shape.commit()

            curr_y += row_height
        return curr_y

    y1 = draw_table_column(left_symbols, col1_x, table_top)
    y2 = draw_table_column(right_symbols, col2_x, table_top)
    y = max(y1, y2) + 14

    # --- Sudoku Grid ---
    grid_left = (PAGE_W - GRID_SIZE) / 2
    grid_top = y

    # Draw cells and borders
    shape = page.new_shape()

    # Outer border
    shape.draw_rect(fitz.Rect(grid_left, grid_top,
                               grid_left + GRID_SIZE, grid_top + GRID_SIZE))
    shape.finish(color=(0, 0, 0), width=3)
    shape.commit()

    # Thin cell borders
    shape = page.new_shape()
    for i in range(1, 9):
        x = grid_left + i * CELL_SIZE
        y_line = grid_top
        lw = 2.5 if i % 3 == 0 else 0.5
        lc = (0, 0, 0) if i % 3 == 0 else (0.6, 0.6, 0.6)
        shape.draw_line(fitz.Point(x, grid_top), fitz.Point(x, grid_top + GRID_SIZE))
        shape.finish(color=lc, width=lw)

    for i in range(1, 9):
        y_pos = grid_top + i * CELL_SIZE
        lw = 2.5 if i % 3 == 0 else 0.5
        lc = (0, 0, 0) if i % 3 == 0 else (0.6, 0.6, 0.6)
        shape.draw_line(fitz.Point(grid_left, y_pos), fitz.Point(grid_left + GRID_SIZE, y_pos))
        shape.finish(color=lc, width=lw)

    shape.commit()

    # Draw symbols in cells
    for row in range(9):
        for col in range(9):
            val = grid[row][col]
            if val == 0:
                continue
            cell_x = grid_left + col * CELL_SIZE
            cell_y = grid_top + row * CELL_SIZE
            draw_symbol_in_cell(page, bravura_font, val, cell_x, cell_y, CELL_SIZE)

    # --- Credit footer ---
    credit_y = grid_top + GRID_SIZE + 48
    credit_text = "By Erisha | Grade 2 | Room 5"
    credit_size = 9.5
    tw = fitz.TextWriter(page.rect)
    credit_width = georgia_italic.text_length(credit_text, fontsize=credit_size)
    tw.append(((PAGE_W - credit_width) / 2, credit_y + credit_size),
              credit_text, font=georgia_italic, fontsize=credit_size)
    tw.write_text(page, color=(0.33, 0.33, 0.33))

    # --- Vertical difficulty label on left margin ---
    label_size = 10
    # Rotate text 90 degrees CCW and place on left margin
    # Use a TextWriter with morph for rotation
    tw = fitz.TextWriter(page.rect)
    label_font = georgia_font
    label_text = difficulty_label
    text_len = label_font.text_length(label_text, fontsize=label_size)

    # Position: centered vertically on the page, in the left margin
    label_x = 14
    label_cy = PAGE_H / 2

    # Write rotated text using page.insert_text with rotate parameter
    # PyMuPDF insert_text supports rotate parameter (0, 90, 180, 270)
    page.insert_text(
        fitz.Point(label_x, label_cy + text_len / 2),
        label_text,
        fontsize=label_size,
        fontname="helv",
        color=(0.4, 0.4, 0.4),
        rotate=90
    )

    return page


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def collect_all_puzzles():
    """Collect all puzzles organized by difficulty."""
    all_puzzles = []  # list of (grid, difficulty_label)

    for folder_name, display_name in DIFFICULTY_ORDER:
        folder_path = os.path.join(PUZZLES_DIR, folder_name)
        # Also check alternate spellings
        if not os.path.isdir(folder_path):
            # Try "novoice" for "novice"
            alt = folder_name
            if folder_name == "novice":
                alt = "novoice"
            folder_path = os.path.join(PUZZLES_DIR, alt)
            if not os.path.isdir(folder_path):
                print(f"  Skipping {display_name}: folder not found")
                continue

        pdf_files = sorted(
            f for f in os.listdir(folder_path) if f.lower().endswith(".pdf")
        )
        print(f"  {display_name}: {len(pdf_files)} PDF files in {os.path.basename(folder_path)}/")

        for pdf_file in pdf_files:
            pdf_path = os.path.join(folder_path, pdf_file)
            grids = extract_grids_from_pdf(pdf_path)
            print(f"    {pdf_file}: {len(grids)} puzzles extracted")
            for g in grids:
                all_puzzles.append((g, display_name))

    return all_puzzles


def main():
    print("Musical Sudoku PDF Generator")
    print("=" * 40)

    # Load fonts
    bravura_font = fitz.Font(fontfile=BRAVURA_FONT)
    georgia_font = fitz.Font(fontfile="/System/Library/Fonts/Supplemental/Georgia.ttf")
    georgia_bold = fitz.Font(fontfile="/System/Library/Fonts/Supplemental/Georgia Bold.ttf")
    georgia_italic = fitz.Font(fontfile="/System/Library/Fonts/Supplemental/Georgia Bold Italic.ttf")

    print(f"\nCollecting puzzles from {PUZZLES_DIR}...")
    all_puzzles = collect_all_puzzles()
    print(f"\nTotal puzzles: {len(all_puzzles)}")

    if not all_puzzles:
        print("No puzzles found!")
        sys.exit(1)

    # Generate output PDF
    print(f"\nGenerating {OUTPUT_PDF}...")
    doc = fitz.open()

    fonts = {
        "bravura": bravura_font,
        "georgia": georgia_font,
        "georgia_bold": georgia_bold,
        "georgia_italic": georgia_italic,
    }
    for i, (grid, difficulty) in enumerate(all_puzzles):
        draw_puzzle_page(doc, fonts, grid, difficulty)
        print(f"  Page {i + 1}: {difficulty}")

    doc.save(OUTPUT_PDF)
    doc.close()
    print(f"\nDone! Generated {len(all_puzzles)} pages -> {OUTPUT_PDF}")
    print(f"File size: {os.path.getsize(OUTPUT_PDF) / 1024:.0f} KB")


if __name__ == "__main__":
    main()
