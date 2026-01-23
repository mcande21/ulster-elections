#!/usr/bin/env python3
"""
Comprehensive test suite for PDF extraction fixes.
"""

from pathlib import Path
from extractors.pdf_text_fixer import extract_text_from_pdf, extract_text_with_fixes
import pdfplumber


def test_putnam_vertical_fix():
    """Test that Putnam vertical text is fixed."""
    print("\n" + "="*80)
    print("TEST: Putnam Vertical Text Fix")
    print("="*80)

    pdf_path = "data/raw/putnam_2024-11-05.pdf"

    if not Path(pdf_path).exists():
        print(f"SKIP: {pdf_path} not found")
        return

    # Test page 0 (known vertical text issue)
    text = extract_text_from_pdf(pdf_path, page_num=0)
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    # Check that we get proper headers, not individual characters
    assert len(lines) < 150, f"Too many lines ({len(lines)}), text still vertical?"

    # First line should be full title
    first_line = lines[0] if lines else ""
    assert "PUTNAM" in first_line, f"Expected PUTNAM in first line, got: {first_line}"
    assert len(first_line) > 20, f"First line too short: {first_line}"

    print(f"✓ Page 0: {len(lines)} lines extracted")
    print(f"  First line: {first_line[:70]}...")

    # Test page 30
    text = extract_text_from_pdf(pdf_path, page_num=30)
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    assert len(lines) < 150, f"Page 30: Too many lines ({len(lines)})"
    print(f"✓ Page 30: {len(lines)} lines extracted")

    print("\n✓ PASS: Putnam vertical text fixed\n")


def test_westchester_mirror_fix():
    """Test that Westchester mirrored text is fixed."""
    print("\n" + "="*80)
    print("TEST: Westchester Mirrored Text Fix")
    print("="*80)

    pdf_path = "data/raw/westchester_2024-11-05.pdf"

    if not Path(pdf_path).exists():
        print(f"SKIP: {pdf_path} not found")
        return

    # Test page 344 (known mirrored names)
    text = extract_text_from_pdf(pdf_path, page_num=344)

    # Check for correctly reversed names
    assert "GOODMAN" in text, "Expected GOODMAN (reversed from NAMDOOG)"
    assert "NAMDOOG" not in text, "NAMDOOG should be reversed to GOODMAN"

    assert "PULVER" in text, "Expected PULVER (reversed from REVLUP)"
    assert "REVLUP" not in text, "REVLUP should be reversed to PULVER"

    assert "FAVA" in text, "Expected FAVA in hyphenated name"
    assert "AVAF" not in text, "AVAF should be reversed to FAVA"

    print("✓ Page 344 mirrored names fixed:")
    print("  NAMDOOG → GOODMAN")
    print("  REVLUP → PULVER")
    print("  AHLITSAP-AVAF → PASTILHA-FAVA")

    # Test page 687
    text = extract_text_from_pdf(pdf_path, page_num=687)

    assert "INLAW" in text or "EVAN" in text, "Expected correctly reversed names"
    assert "WALNI" not in text, "WALNI should be reversed"

    print("✓ Page 687 mirrored text fixed")
    print("\n✓ PASS: Westchester mirrored text fixed\n")


def test_normal_page():
    """Test that normal pages are not broken by fixes."""
    print("\n" + "="*80)
    print("TEST: Normal Pages Unchanged")
    print("="*80)

    pdf_path = "data/raw/westchester_2024-11-05.pdf"

    if not Path(pdf_path).exists():
        print(f"SKIP: {pdf_path} not found")
        return

    # Test page 0 (index page - no issues)
    text = extract_text_from_pdf(pdf_path, page_num=0)

    assert "GENERAL" in text, "Expected GENERAL in text"
    assert "INDEX" in text, "Expected INDEX in text"

    # Make sure we're not reversing normal text
    assert "LARENEG" not in text, "GENERAL incorrectly reversed!"
    assert "XEDNI" not in text, "INDEX incorrectly reversed!"

    print("✓ Page 0 (index) extracted correctly without false reversals")
    print("\n✓ PASS: Normal pages unaffected\n")


def test_comparison():
    """Compare before/after extraction results."""
    print("\n" + "="*80)
    print("COMPARISON: Before vs After Fixes")
    print("="*80)

    pdf_path = "data/raw/putnam_2024-11-05.pdf"

    if not Path(pdf_path).exists():
        print(f"SKIP: {pdf_path} not found")
        return

    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]

        # Before (default extraction)
        text_before = page.extract_text()
        lines_before = text_before.splitlines() if text_before else []

        # After (with fixes)
        text_after = extract_text_with_fixes(page)
        lines_after = text_after.splitlines()

        print(f"\nBefore: {len(lines_before)} lines")
        print("First 5 lines:")
        for i, line in enumerate(lines_before[:5], 1):
            print(f"  {i}. {repr(line)}")

        print(f"\nAfter: {len(lines_after)} lines")
        print("First 5 lines:")
        for i, line in enumerate(lines_after[:5], 1):
            print(f"  {i}. {repr(line)}")

        improvement = len(lines_before) - len(lines_after)
        print(f"\nImprovement: {improvement} fewer lines ({len(lines_after)/len(lines_before)*100:.1f}% of original)")


def run_all_tests():
    """Run all test suites."""
    print("\n" + "="*80)
    print("PDF EXTRACTION TEST SUITE")
    print("="*80)

    try:
        test_putnam_vertical_fix()
        test_westchester_mirror_fix()
        test_normal_page()
        test_comparison()

        print("\n" + "="*80)
        print("✓ ALL TESTS PASSED")
        print("="*80 + "\n")

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}\n")
        raise
    except Exception as e:
        print(f"\n✗ ERROR: {e}\n")
        raise


if __name__ == "__main__":
    run_all_tests()
