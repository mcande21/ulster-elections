#!/usr/bin/env python3
"""
Analyze how characters are grouped on lines to find optimal extraction parameters.
"""

import pdfplumber
from pathlib import Path
from collections import defaultdict


def analyze_char_positions(pdf_path: str, page_num: int = 0):
    """Analyze character positions to understand grouping."""

    print(f"\n{'='*80}")
    print(f"Character Position Analysis: {Path(pdf_path).name}, Page {page_num}")
    print(f"{'='*80}\n")

    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_num]
        chars = page.chars

        # Group characters by Y position (same line)
        lines_by_y = defaultdict(list)
        for char in chars:
            y_pos = round(char['top'], 1)  # Round to nearest 0.1
            lines_by_y[y_pos].append(char)

        # Sort by Y position (top to bottom)
        sorted_y_positions = sorted(lines_by_y.keys())

        print(f"Total unique Y positions (lines): {len(sorted_y_positions)}")
        print(f"Total characters: {len(chars)}")
        print()

        # Show first few lines
        print("First 10 lines by Y position:")
        for i, y_pos in enumerate(sorted_y_positions[:10], 1):
            line_chars = sorted(lines_by_y[y_pos], key=lambda c: c['x0'])
            text = ''.join(c['text'] for c in line_chars)
            char_count = len(line_chars)
            print(f"  {i}. Y={y_pos:6.1f} ({char_count:3d} chars): {text[:80]}")

        # Analyze Y-spacing between lines
        print("\nY-spacing between consecutive lines (first 20):")
        for i in range(min(20, len(sorted_y_positions) - 1)):
            y1 = sorted_y_positions[i]
            y2 = sorted_y_positions[i + 1]
            spacing = y2 - y1
            chars1 = sorted(lines_by_y[y1], key=lambda c: c['x0'])
            chars2 = sorted(lines_by_y[y2], key=lambda c: c['x0'])
            text1 = ''.join(c['text'] for c in chars1)[:40]
            text2 = ''.join(c['text'] for c in chars2)[:40]
            print(f"  {i+1}. Spacing: {spacing:5.1f} | {text1} -> {text2}")

        # Check if default extraction is grouping chars on the same Y
        print("\n" + "="*80)
        print("Testing different extraction parameters:")
        print("="*80 + "\n")

        # Default
        print("1. Default extract_text():")
        text = page.extract_text()
        print(f"   Lines: {len(text.splitlines())}, First line: {repr(text.splitlines()[0] if text else '')}")

        # Adjusted x/y density
        print("\n2. extract_text(x_density=7.25, y_density=13):")
        text = page.extract_text(x_density=7.25, y_density=13)
        print(f"   Lines: {len(text.splitlines())}, First line: {repr(text.splitlines()[0] if text else '')}")

        # More aggressive
        print("\n3. extract_text(x_density=10, y_density=15):")
        text = page.extract_text(x_density=10, y_density=15)
        lines = text.splitlines() if text else []
        print(f"   Lines: {len(lines)}")
        for i, line in enumerate(lines[:5], 1):
            print(f"   Line {i}: {repr(line)}")

        # Even more aggressive
        print("\n4. extract_text(x_density=15, y_density=20):")
        text = page.extract_text(x_density=15, y_density=20)
        lines = text.splitlines() if text else []
        print(f"   Lines: {len(lines)}")
        for i, line in enumerate(lines[:5], 1):
            print(f"   Line {i}: {repr(line)}")

        # Try y_tolerance instead
        print("\n5. extract_text(y_tolerance=5):")
        text = page.extract_text(y_tolerance=5)
        lines = text.splitlines() if text else []
        print(f"   Lines: {len(lines)}")
        for i, line in enumerate(lines[:5], 1):
            print(f"   Line {i}: {repr(line)}")


def test_both_pdfs():
    """Test both Putnam and Westchester PDFs."""

    putnam_path = "data/raw/putnam_2024-11-05.pdf"
    westchester_path = "data/raw/westchester_2024-11-05.pdf"

    if Path(putnam_path).exists():
        analyze_char_positions(putnam_path, page_num=0)

        # Also check page 30
        print("\n" + "="*80)
        analyze_char_positions(putnam_path, page_num=30)

    if Path(westchester_path).exists():
        print("\n" + "="*80)
        print("WESTCHESTER PDF ANALYSIS")
        print("="*80)
        analyze_char_positions(westchester_path, page_num=0)


if __name__ == "__main__":
    test_both_pdfs()
