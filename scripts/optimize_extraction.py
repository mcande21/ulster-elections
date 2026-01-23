#!/usr/bin/env python3
"""
Optimize extraction parameters to fix spacing and text direction issues.
"""

import pdfplumber
from pathlib import Path


def test_parameter_combinations(pdf_path: str, page_num: int):
    """Test various combinations of extraction parameters."""

    print(f"\n{'='*80}")
    print(f"Optimizing: {Path(pdf_path).name}, Page {page_num}")
    print(f"{'='*80}\n")

    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_num]

        # Analyze characters to check text direction
        chars = page.chars[:50]
        print("Sample characters (first 50):")
        print(f"  Text: {''.join(c['text'] for c in chars)}")
        print(f"  X positions: {[round(c['x0'], 1) for c in chars[:10]]}")
        print(f"  Are X positions increasing (left-to-right)? {chars[1]['x0'] > chars[0]['x0'] if len(chars) > 1 else 'N/A'}")
        print()

        test_configs = [
            {
                "name": "Current (working but spaced)",
                "params": {"x_tolerance": 2, "y_tolerance": 2, "x_density": 7.25, "y_density": 13}
            },
            {
                "name": "Higher x_tolerance (group chars closer)",
                "params": {"x_tolerance": 5, "y_tolerance": 2, "x_density": 7.25, "y_density": 13}
            },
            {
                "name": "Even higher x_tolerance",
                "params": {"x_tolerance": 8, "y_tolerance": 2, "x_density": 7.25, "y_density": 13}
            },
            {
                "name": "Higher y_tolerance too",
                "params": {"x_tolerance": 5, "y_tolerance": 5, "x_density": 7.25, "y_density": 13}
            },
            {
                "name": "Moderate both tolerances",
                "params": {"x_tolerance": 3, "y_tolerance": 3, "layout": False}
            },
            {
                "name": "Higher both tolerances",
                "params": {"x_tolerance": 5, "y_tolerance": 5, "layout": False}
            },
            {
                "name": "Just use layout mode",
                "params": {"layout": True}
            },
        ]

        for config in test_configs:
            print(f"{config['name']}:")
            print(f"  Params: {config['params']}")

            try:
                text = page.extract_text(**config['params'])
                if text:
                    lines = [l for l in text.splitlines() if l.strip()]
                    print(f"  Lines: {len(lines)}")
                    print(f"  First 5 non-empty lines:")
                    for i, line in enumerate(lines[:5], 1):
                        display = line[:70] + ('...' if len(line) > 70 else '')
                        print(f"    {i}. {repr(display)}")
                else:
                    print("  No text extracted")
            except Exception as e:
                print(f"  Error: {e}")
            print()


def check_text_direction(pdf_path: str, page_num: int):
    """Check if text is reversed/mirrored."""

    print(f"\n{'='*80}")
    print(f"Text Direction Check: {Path(pdf_path).name}, Page {page_num}")
    print(f"{'='*80}\n")

    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_num]
        chars = page.chars

        if not chars:
            print("No characters found")
            return

        # Group chars by Y position
        from collections import defaultdict
        lines_by_y = defaultdict(list)
        for char in chars:
            y_pos = round(char['top'])
            lines_by_y[y_pos].append(char)

        # Check a few lines for direction
        print("Checking first 3 lines for text direction:\n")
        for i, y_pos in enumerate(sorted(lines_by_y.keys())[:3], 1):
            line_chars = lines_by_y[y_pos]

            # Sort by X position
            sorted_chars = sorted(line_chars, key=lambda c: c['x0'])
            text_ltr = ''.join(c['text'] for c in sorted_chars)

            # Reverse order
            sorted_chars_reversed = sorted(line_chars, key=lambda c: c['x0'], reverse=True)
            text_rtl = ''.join(c['text'] for c in sorted_chars_reversed)

            print(f"Line {i} (Y={y_pos}):")
            print(f"  Left-to-right: {repr(text_ltr[:60])}")
            print(f"  Right-to-left: {repr(text_rtl[:60])}")

            # Check if RTL makes more sense (has more dictionary words)
            if len(text_ltr) > 10 and len(text_rtl) > 10:
                # Simple heuristic: check if reversed has less repeated chars
                if text_rtl.upper() != text_rtl[::-1].upper():
                    print(f"  -> Text appears to be mirrored/reversed")
            print()


def find_optimal_params():
    """Find optimal extraction parameters for both PDFs."""

    putnam_path = "data/raw/putnam_2024-11-05.pdf"
    westchester_path = "data/raw/westchester_2024-11-05.pdf"

    # Test Putnam page with spacing issues
    if Path(putnam_path).exists():
        print("="*80)
        print("PUTNAM PDF - Page with spacing issues")
        print("="*80)
        test_parameter_combinations(putnam_path, page_num=0)

    # Test Westchester page with reversed text
    if Path(westchester_path).exists():
        print("\n" + "="*80)
        print("WESTCHESTER PDF - Page with reversed text")
        print("="*80)
        check_text_direction(westchester_path, page_num=344)
        test_parameter_combinations(westchester_path, page_num=344)


if __name__ == "__main__":
    find_optimal_params()
