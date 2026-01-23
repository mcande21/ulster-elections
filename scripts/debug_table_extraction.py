#!/usr/bin/env python3
"""Debug table extraction on Westchester President page."""

import sys
sys.path.insert(0, 'scripts')

import pdfplumber
from extractors.pdf_text_fixer import extract_text_with_fixes

pdf_path = 'data/raw/westchester_2024-11-05.pdf'

print("Debugging table extraction on President page")

with pdfplumber.open(pdf_path) as pdf:
    # Page 110 in PDF = index 109
    page = pdf.pages[109]

    # Extract tables
    tables = page.extract_tables()

    print(f"\nFound {len(tables)} tables on page")

    if tables:
        table = tables[0]
        print(f"Table has {len(table)} rows")
        print(f"Table has {len(table[0]) if table else 0} columns")

        print("\n=== First 5 rows ===")
        for i, row in enumerate(table[:5]):
            print(f"\nRow {i}:")
            for j, cell in enumerate(row[:10]):  # Show first 10 columns
                cell_display = str(cell)[:50] if cell else "None"
                print(f"  Col {j}: {cell_display}")

        print("\n=== Row 0 (header) ===")
        for j, cell in enumerate(table[0]):
            print(f"Col {j}: {cell}")

        print("\n=== Row 1 (party row) ===")
        for j, cell in enumerate(table[1]):
            print(f"Col {j}: {cell}")

        # Find TOTAL row
        print("\n=== Looking for TOTAL row ===")
        for i, row in enumerate(table):
            if row[0] and 'TOTAL' in str(row[0]).upper():
                print(f"Found TOTAL at row {i}")
                print(f"TOTAL row: {row[:10]}")
                break
    else:
        print("No tables found!")

    # Try different table settings
    print("\n=== Trying with explicit table settings ===")
    table_settings = {
        "vertical_strategy": "lines",
        "horizontal_strategy": "lines",
    }

    tables2 = page.extract_tables(table_settings)
    print(f"Found {len(tables2)} tables with line-based strategy")

    if tables2:
        table2 = tables2[0]
        print(f"Table has {len(table2)} rows, {len(table2[0])} columns")
        print(f"\nFirst row: {table2[0][:5]}")
        print(f"Second row: {table2[1][:5]}")
