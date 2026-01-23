#!/usr/bin/env python3
"""Debug TOTAL row detection."""

import sys
sys.path.insert(0, 'scripts')

import pdfplumber

pdf_path = 'data/raw/westchester_2024-11-05.pdf'

print("Debugging TOTAL row detection on President page")

with pdfplumber.open(pdf_path) as pdf:
    page = pdf.pages[109]

    tables = page.extract_tables()
    table = tables[0]

    print(f"\nTable has {len(table)} rows")

    # Look for TOTAL row
    for i, row in enumerate(table):
        if row[0]:
            row_text = str(row[0]).strip().upper()
            if 'TOTAL' in row_text:
                print(f"\n✓ Found TOTAL at row {i}: {row[0]}")
                print(f"  First 10 cells: {row[:10]}")
                break
    else:
        print("\n❌ No TOTAL row found")

        # Show all rows with first cell content
        print("\nAll rows with first cell:")
        for i, row in enumerate(table):
            if row[0]:
                cell_text = str(row[0])[:60]
                print(f"  Row {i}: {cell_text}")
