#!/usr/bin/env python3
"""Find pages with TOTAL rows."""

import sys
sys.path.insert(0, 'scripts')

import pdfplumber

pdf_path = 'data/raw/westchester_2024-11-05.pdf'

print("Scanning for pages with TOTAL rows (checking every 10th page)")

with pdfplumber.open(pdf_path) as pdf:
    total_pages_found = []

    # Check pages around president race (110-161 per index)
    for page_num in range(109, min(162, len(pdf.pages))):
        page = pdf.pages[page_num]
        tables = page.extract_tables()

        if not tables:
            continue

        table = tables[0]

        for i, row in enumerate(table):
            if row and row[0] and 'TOTAL' in str(row[0]).upper():
                total_pages_found.append(page_num)
                print(f"\n✓ Page {page_num} (PDF page {page_num+1}) has TOTAL row")
                print(f"  Row {i}: {row[0]}")
                print(f"  Data: {row[:10]}")
                break

if not total_pages_found:
    print("\n❌ No TOTAL rows found in President race pages (110-161)")
else:
    print(f"\nFound TOTAL on {len(total_pages_found)} pages")
