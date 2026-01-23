#!/usr/bin/env python3
"""Test PrecinctTableParser on Westchester PDF sample."""

import sys
from pathlib import Path

# Add scripts dir to path
scripts_dir = Path(__file__).parent
sys.path.insert(0, str(scripts_dir))

from extractors.parsers import PrecinctTableParser
from extractors.pdf_text_fixer import extract_text_with_fixes
import pdfplumber

pdf_path = Path(__file__).parent.parent / 'data' / 'raw' / 'westchester_2024-11-05.pdf'

print(f"Testing Westchester PDF: {pdf_path}")
print(f"PDF exists: {pdf_path.exists()}")
print()

# Test text extraction on first few pages to check for mirroring
print("=" * 80)
print("Testing text extraction with mirroring fix (first 3 pages)")
print("=" * 80)

with pdfplumber.open(pdf_path) as pdf:
    print(f"Total pages: {len(pdf.pages)}")

    for page_num in range(min(3, len(pdf.pages))):
        page = pdf.pages[page_num]
        text = extract_text_with_fixes(page)

        print(f"\n--- Page {page_num} ---")
        lines = [l.strip() for l in text.split('\n') if l.strip()]

        # Show first 15 lines
        for i, line in enumerate(lines[:15]):
            print(f"{i+1:2d}. {line}")

        # Check for mirrored names
        text_upper = text.upper()
        mirrored_indicators = ['SIRRAH', 'PMURT', 'ZLAW', 'ECNAV']
        found_mirrored = [m for m in mirrored_indicators if m in text_upper]

        if found_mirrored:
            print(f"\n⚠️  Found mirrored text: {found_mirrored}")

        # Check for corrected names
        corrected_indicators = ['HARRIS', 'TRUMP', 'WALZ', 'VANCE']
        found_corrected = [c for c in corrected_indicators if c in text_upper]

        if found_corrected:
            print(f"✓ Found corrected text: {found_corrected}")

print("\n" + "=" * 80)
print("Testing PrecinctTableParser on first 20 pages")
print("=" * 80)

# Test parser on sample
parser = PrecinctTableParser()
county_config = {
    'name': 'Westchester',
    'election_date': '2024-11-05',
    'format': 'precinct_table'
}

# Parse just first 20 pages
with pdfplumber.open(pdf_path) as pdf:
    # Temporarily limit pages for testing
    limited_pdf_path = pdf_path  # Will process all but break after finding races

try:
    result = parser.parse(str(pdf_path), county_config)

    print(f"\nExtracted {len(result['races'])} races")
    print(f"County: {result['county']}")
    print(f"Election Date: {result['election_date']}")

    # Show first 3 races
    for i, race in enumerate(result['races'][:3]):
        print(f"\n--- Race {i+1}: {race['race_title']} ---")
        print(f"Vote for: {race['vote_for']}")
        print(f"Candidates: {len(race['candidates'])}")

        for candidate in race['candidates'][:5]:
            print(f"  - {candidate['name']}: {candidate['total_votes']:,} votes")
            for party_line in candidate['party_lines']:
                print(f"    {party_line['party']}: {party_line['votes']:,}")

        if len(race['candidates']) > 5:
            print(f"  ... and {len(race['candidates']) - 5} more candidates")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
