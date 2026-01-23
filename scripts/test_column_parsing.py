#!/usr/bin/env python3
"""Test column header parsing on Westchester."""

import sys
sys.path.insert(0, 'scripts')

import pdfplumber
from extractors.parsers import PrecinctTableParser

pdf_path = 'data/raw/westchester_2024-11-05.pdf'

print("Testing column parsing on President page")

parser = PrecinctTableParser()

with pdfplumber.open(pdf_path) as pdf:
    page = pdf.pages[109]

    # Extract table
    tables = page.extract_tables()
    table = tables[0]

    print(f"\nTable has {len(table)} rows, {len(table[0])} columns")

    # Parse column headers
    header_row = table[0]
    party_row = table[1]

    print("\n=== Header row (raw) ===")
    for i, cell in enumerate(header_row[:8]):
        print(f"Col {i}: {cell}")

    print("\n=== Party/name row (raw) ===")
    for i, cell in enumerate(party_row[:8]):
        cell_display = str(cell)[:100] if cell else "None"
        print(f"Col {i}: {cell_display}")

    columns = parser._parse_column_headers(header_row, party_row)

    print(f"\n=== Parsed {len(columns)} columns ===")
    for col in columns[:8]:
        print(f"Col {col['index']}: {col['name']} ({col['party']})")
