#!/usr/bin/env python3
"""Debug the mirrored text detection."""

import pdfplumber
from collections import defaultdict


def debug_page_344():
    """Debug Westchester page 344 with mirrored text."""

    pdf_path = "data/raw/westchester_2024-11-05.pdf"
    page_num = 344

    print(f"Debugging page {page_num}\n")

    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_num]
        chars = page.chars

        # Check overall mirroring
        print("Overall character flow (first 100 chars):")
        decreasing = 0
        for i in range(1, min(100, len(chars))):
            if chars[i]['x0'] < chars[i-1]['x0']:
                decreasing += 1
                if decreasing <= 10:  # Show first 10 examples
                    print(f"  {i}: '{chars[i-1]['text']}' ({chars[i-1]['x0']:.1f}) -> "
                          f"'{chars[i]['text']}' ({chars[i]['x0']:.1f}) DECREASE")

        print(f"\nTotal decreasing transitions: {decreasing}/{min(100, len(chars))}")
        print(f"Percentage: {decreasing/min(100, len(chars))*100:.1f}%")

        # Look at specific lines with candidate names
        lines_by_y = defaultdict(list)
        for char in chars:
            y_pos = round(char['top'])
            lines_by_y[y_pos].append(char)

        print(f"\nLine-by-line analysis (first 15 lines):\n")
        for i, y_pos in enumerate(sorted(lines_by_y.keys())[:15], 1):
            line_chars = lines_by_y[y_pos]

            # Left-to-right
            ltr_chars = sorted(line_chars, key=lambda c: c['x0'])
            ltr_text = ''.join(c['text'] for c in ltr_chars)

            # Right-to-left
            rtl_chars = sorted(line_chars, key=lambda c: c['x0'], reverse=True)
            rtl_text = ''.join(c['text'] for c in rtl_chars)

            # Check decreasing ratio
            dec_count = 0
            for j in range(1, len(line_chars)):
                if line_chars[j]['x0'] < line_chars[j-1]['x0']:
                    dec_count += 1
            dec_ratio = dec_count / len(line_chars) if line_chars else 0

            print(f"Line {i} (Y={y_pos}, {len(line_chars)} chars, {dec_ratio*100:.0f}% decreasing):")
            print(f"  LTR: {repr(ltr_text[:50])}")
            print(f"  RTL: {repr(rtl_text[:50])}")

            # Show X positions for names
            if any(word in ltr_text.upper() for word in ['NAMDOOG', 'REVLUP', 'GOODMAN', 'PULVER']):
                print(f"  X positions: {[round(c['x0'], 1) for c in line_chars[:10]]}")
            print()


if __name__ == "__main__":
    debug_page_344()
