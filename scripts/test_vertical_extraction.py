#!/usr/bin/env python3
"""
Test script to diagnose and fix vertical text extraction in Putnam/Westchester PDFs.
"""

import pdfplumber
import sys
from pathlib import Path


def analyze_page_structure(pdf_path: str, page_num: int = 0):
    """Analyze PDF page structure to understand rotation/layout issues."""
    print(f"\n{'='*60}")
    print(f"Analyzing: {Path(pdf_path).name}")
    print(f"{'='*60}\n")

    with pdfplumber.open(pdf_path) as pdf:
        if page_num >= len(pdf.pages):
            print(f"Error: Page {page_num} doesn't exist (only {len(pdf.pages)} pages)")
            return

        page = pdf.pages[page_num]

        # Page properties
        print(f"Total pages: {len(pdf.pages)}")
        print(f"Analyzing page: {page_num}")
        print(f"Page rotation: {page.rotation}")
        print(f"MediaBox: {page.mediabox}")
        print(f"CropBox: {page.cropbox}")
        print(f"Page width: {page.width}")
        print(f"Page height: {page.height}")
        print()


def test_extraction_methods(pdf_path: str, page_num: int = 0):
    """Test different text extraction methods."""

    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_num]

        print(f"\n{'='*60}")
        print("METHOD 1: Default extract_text()")
        print(f"{'='*60}")
        text1 = page.extract_text()
        if text1:
            print(f"First 300 chars:")
            print(repr(text1[:300]))
            print(f"\nLine count: {len(text1.splitlines())}")
            print(f"First 5 lines:")
            for i, line in enumerate(text1.splitlines()[:5], 1):
                print(f"  {i}: {repr(line)}")
        else:
            print("No text extracted")

        print(f"\n{'='*60}")
        print("METHOD 2: extract_text(layout=True)")
        print(f"{'='*60}")
        text2 = page.extract_text(layout=True)
        if text2:
            print(f"First 300 chars:")
            print(repr(text2[:300]))
            print(f"\nLine count: {len(text2.splitlines())}")
            print(f"First 5 lines:")
            for i, line in enumerate(text2.splitlines()[:5], 1):
                print(f"  {i}: {repr(line)}")
        else:
            print("No text extracted")

        print(f"\n{'='*60}")
        print("METHOD 3: Analyze individual chars")
        print(f"{'='*60}")
        chars = page.chars
        print(f"Total chars found: {len(chars)}")
        if chars:
            print(f"\nFirst 10 characters:")
            for i, char in enumerate(chars[:10], 1):
                print(f"  {i}: '{char['text']}' at x={char['x0']:.1f}, y={char['top']:.1f}, "
                      f"size={char.get('size', 'N/A')}, rotation={char.get('rotation', 0)}")

            # Check if chars have consistent rotation
            rotations = [c.get('rotation', 0) for c in chars[:100]]
            unique_rotations = set(rotations)
            print(f"\nRotations found in first 100 chars: {unique_rotations}")

        print(f"\n{'='*60}")
        print("METHOD 4: extract_text(x_tolerance=3, y_tolerance=3)")
        print(f"{'='*60}")
        text4 = page.extract_text(x_tolerance=3, y_tolerance=3)
        if text4:
            print(f"First 300 chars:")
            print(repr(text4[:300]))
            print(f"\nLine count: {len(text4.splitlines())}")
            print(f"First 5 lines:")
            for i, line in enumerate(text4.splitlines()[:5], 1):
                print(f"  {i}: {repr(line)}")
        else:
            print("No text extracted")


def test_rotated_page(pdf_path: str, page_num: int = 0):
    """Test if manually rotating the page helps extraction."""

    print(f"\n{'='*60}")
    print("METHOD 5: Testing page rotation handling")
    print(f"{'='*60}")

    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_num]

        # If page has rotation, try to work with it
        if hasattr(page, 'rotation') and page.rotation != 0:
            print(f"Page has rotation: {page.rotation} degrees")

        # Try extracting with different settings
        text = page.extract_text(
            x_tolerance=2,
            y_tolerance=2,
            layout=False,
            x_density=7.25,
            y_density=13
        )

        if text:
            print(f"First 300 chars:")
            print(repr(text[:300]))
            print(f"\nFirst 5 lines:")
            for i, line in enumerate(text.splitlines()[:5], 1):
                print(f"  {i}: {repr(line)}")


def main():
    # Test Putnam PDF (smaller, easier to debug)
    putnam_path = "data/raw/putnam_2024-11-05.pdf"

    if not Path(putnam_path).exists():
        print(f"Error: {putnam_path} not found")
        return

    analyze_page_structure(putnam_path, page_num=0)
    test_extraction_methods(putnam_path, page_num=0)
    test_rotated_page(putnam_path, page_num=0)

    # Also check a middle page in case first page is different
    print("\n" + "="*60)
    print("Checking middle page (page 30) for comparison")
    print("="*60)
    analyze_page_structure(putnam_path, page_num=30)
    test_extraction_methods(putnam_path, page_num=30)


if __name__ == "__main__":
    main()
