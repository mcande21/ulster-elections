#!/usr/bin/env python3
import sys
sys.path.insert(0, 'scripts')

import pdfplumber
from extractors.pdf_text_fixer import extract_text_with_fixes

pdf_path = 'data/raw/westchester_2024-11-05.pdf'

print("Checking President page (page 109 - 0-indexed)")

with pdfplumber.open(pdf_path) as pdf:
    # Page 110 in PDF = index 109
    page = pdf.pages[109]

    # Raw extraction
    raw_text = page.extract_text()

    # With fixes
    fixed_text = extract_text_with_fixes(page)

    print("\n=== RAW TEXT (first 20 lines) ===")
    raw_lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
    for i, line in enumerate(raw_lines[:20], 1):
        print(f"{i:2d}. {line}")

    print("\n=== FIXED TEXT (first 20 lines) ===")
    fixed_lines = [l.strip() for l in fixed_text.split('\n') if l.strip()]
    for i, line in enumerate(fixed_lines[:20], 1):
        print(f"{i:2d}. {line}")

    # Check for mirroring indicators
    print("\n=== MIRRORING CHECK ===")
    mirrored_words = ['SIRRAH', 'PMURT', 'ZLAW', 'ECNAV']
    correct_words = ['HARRIS', 'TRUMP', 'WALZ', 'VANCE']

    print("\nIn RAW text:")
    for word in mirrored_words:
        if word in raw_text.upper():
            print(f"  ⚠️  Found: {word}")
    for word in correct_words:
        if word in raw_text.upper():
            print(f"  ✓ Found: {word}")

    print("\nIn FIXED text:")
    for word in mirrored_words:
        if word in fixed_text.upper():
            print(f"  ⚠️  Found: {word}")
    for word in correct_words:
        if word in fixed_text.upper():
            print(f"  ✓ Found: {word}")
