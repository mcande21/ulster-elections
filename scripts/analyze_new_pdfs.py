#!/usr/bin/env python3
"""
Quick PDF structure analyzer for new election data files.
Samples first few pages to understand content without loading full PDFs.
"""

import pdfplumber
from pathlib import Path

def analyze_pdf(pdf_path: Path) -> dict:
    """Extract structure info from first 2 pages of PDF."""

    info = {
        'filename': pdf_path.name,
        'total_pages': 0,
        'sample_text': '',
        'county': None,
        'election_date': None,
        'races': []
    }

    try:
        with pdfplumber.open(pdf_path) as pdf:
            info['total_pages'] = len(pdf.pages)

            # Extract text from first 2 pages
            sample_pages = min(2, len(pdf.pages))
            for i in range(sample_pages):
                page_text = pdf.pages[i].extract_text()
                if page_text:
                    info['sample_text'] += f"\n--- Page {i+1} ---\n{page_text}\n"

            # Simple pattern matching for key fields
            text = info['sample_text'].lower()

            # Look for county
            if 'ulster' in text:
                info['county'] = 'Ulster County'

            # Look for date patterns
            import re
            date_pattern = r'(november|nov)\s+\d{1,2},?\s+\d{4}'
            dates = re.findall(date_pattern, text, re.IGNORECASE)
            if dates:
                info['election_date'] = dates[0]

            # Look for race indicators
            race_keywords = [
                'president', 'senator', 'representative', 'congress',
                'assembly', 'judge', 'proposition', 'district attorney'
            ]
            for keyword in race_keywords:
                if keyword in text:
                    info['races'].append(keyword)

    except Exception as e:
        info['error'] = str(e)

    return info

def main():
    data_dir = Path.home() / 'work' / 'personal' / 'code' / 'ulster-elections' / 'data'

    pdfs = [
        'Summary Results with Candidate Totals_41b03cbb-9244-4b14-b023-a0fdb76110d9.PDF',
        'Official-GE25.pdf'
    ]

    print("=" * 80)
    print("PDF STRUCTURE ANALYSIS")
    print("=" * 80)

    for pdf_name in pdfs:
        pdf_path = data_dir / pdf_name

        print(f"\n{'=' * 80}")
        print(f"FILE: {pdf_name}")
        print(f"{'=' * 80}")

        if not pdf_path.exists():
            print(f"ERROR: File not found at {pdf_path}")
            continue

        info = analyze_pdf(pdf_path)

        if 'error' in info:
            print(f"ERROR: {info['error']}")
            continue

        print(f"\nTotal Pages: {info['total_pages']}")
        print(f"County: {info['county'] or 'Not detected'}")
        print(f"Election Date: {info['election_date'] or 'Not detected'}")
        print(f"Detected Races: {', '.join(info['races']) if info['races'] else 'None detected'}")

        print(f"\n--- Sample Text (First 2 Pages) ---")
        print(info['sample_text'][:1000])  # Print first 1000 chars
        if len(info['sample_text']) > 1000:
            print(f"\n... (truncated, {len(info['sample_text'])} total chars)")

    print(f"\n{'=' * 80}")
    print("ANALYSIS COMPLETE")
    print(f"{'=' * 80}")

if __name__ == '__main__':
    main()
