#!/usr/bin/env python3
"""
Find the exact working extraction parameters for vertical text issue.
"""

import pdfplumber
from pathlib import Path


def test_working_method(pdf_path: str, page_num: int = 0):
    """Test the method that worked in the original test."""

    print(f"\n{'='*80}")
    print(f"Testing: {Path(pdf_path).name}, Page {page_num}")
    print(f"{'='*80}\n")

    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_num]

        # This was METHOD 5 from test_vertical_extraction.py that worked
        print("Method from test_vertical_extraction.py that showed good results:")
        print("  extract_text(x_tolerance=2, y_tolerance=2, layout=False,")
        print("               x_density=7.25, y_density=13)")
        print()

        text = page.extract_text(
            x_tolerance=2,
            y_tolerance=2,
            layout=False,
            x_density=7.25,
            y_density=13
        )

        if text:
            lines = text.splitlines()
            print(f"Total lines: {len(lines)}")
            print(f"\nFirst 15 lines:")
            for i, line in enumerate(lines[:15], 1):
                print(f"  {i:2d}. {repr(line)}")
            print()

            # Check if we're getting full sentences/phrases
            full_lines = [line for line in lines if len(line.strip()) > 20]
            print(f"Lines with >20 chars: {len(full_lines)}/{len(lines)}")

            if full_lines:
                print(f"\nSample longer lines:")
                for line in full_lines[:5]:
                    print(f"  {repr(line[:80])}")
        else:
            print("No text extracted!")


def test_all_pages_sample(pdf_path: str):
    """Test a sample of pages to see if the method works consistently."""

    if not Path(pdf_path).exists():
        print(f"File not found: {pdf_path}")
        return

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        print(f"\n{'='*80}")
        print(f"Sampling pages from {Path(pdf_path).name} ({total_pages} pages)")
        print(f"{'='*80}\n")

        # Sample: first, middle, last
        sample_pages = [0, total_pages // 2, total_pages - 1]

        for page_num in sample_pages:
            test_working_method(pdf_path, page_num)


if __name__ == "__main__":
    putnam_path = "data/raw/putnam_2024-11-05.pdf"
    westchester_path = "data/raw/westchester_2024-11-05.pdf"

    if Path(putnam_path).exists():
        test_all_pages_sample(putnam_path)

    if Path(westchester_path).exists():
        test_all_pages_sample(westchester_path)
