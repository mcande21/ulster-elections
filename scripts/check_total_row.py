#!/usr/bin/env python3
"""Check TOTAL row data on page 160."""

import sys
sys.path.insert(0, 'scripts')

import pdfplumber

pdf_path = 'data/raw/westchester_2024-11-05.pdf'

print("Checking TOTAL row on page 160")

with pdfplumber.open(pdf_path) as pdf:
    page = pdf.pages[160]

    tables = page.extract_tables()
    table = tables[0]

    print(f"\nTable has {len(table)} rows, {len(table[0])} columns")

    # Show all rows
    for i, row in enumerate(table):
        if row[0]:
            print(f"\nRow {i}: {row[0]}")
            # Show vote data
            print(f"  Columns: {row[:15]}")
