#!/usr/bin/env python3
import sys
import pdfplumber

pdf_path = 'data/raw/westchester_2024-11-05.pdf'

print("Quick Westchester test")
print(f"Opening: {pdf_path}")

with pdfplumber.open(pdf_path) as pdf:
    print(f"Total pages: {len(pdf.pages)}")

    # Test first page
    page = pdf.pages[0]
    text = page.extract_text()

    lines = [l.strip() for l in text.split('\n') if l.strip()][:10]

    print("\nFirst 10 lines (raw):")
    for i, line in enumerate(lines, 1):
        print(f"{i}. {line}")

    # Check for mirroring
    if 'SIRRAH' in text.upper():
        print("\n⚠️  FOUND MIRRORED TEXT (SIRRAH)")
    if 'HARRIS' in text.upper():
        print("✓ Found HARRIS")
