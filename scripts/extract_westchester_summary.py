#!/usr/bin/env python3
"""
Extract Westchester County results - Summary approach.

Westchester PDF structure:
- 688 pages of precinct-level data
- No single aggregated TOTAL row per race
- Multiple "TOTAL OF..." rows (Towns, Cities, Yonkers) but they appear empty
- Requires summing all precinct rows to get county totals

This script extracts races and aggregates precinct data manually.
"""

import sys
import json
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent))

import pdfplumber
from extractors.pdf_text_fixer import extract_text_with_fixes, _is_word_likely_mirrored
from extractors.parties import is_known_party, normalize_party, get_display_name


def parse_westchester_table(table):
    """
    Parse a Westchester-format table.

    Returns:
        columns: List of {name, party, index} dicts
        precinct_rows: List of precinct data rows
    """
    if len(table) < 3:
        return [], []

    # Row 0: party abbreviations
    # Row 1: candidate names (mirrored, with newlines)
    header_row = table[0]
    name_row = table[1]

    columns = []
    for i, (party_cell, name_cell) in enumerate(zip(header_row, name_row)):
        party = party_cell.strip() if party_cell else ''
        name_text = name_cell.strip() if name_cell else ''

        if not party or not is_known_party(party):
            continue

        if not name_text:
            continue

        # Fix mirrored candidate names
        parts = [p.strip() for p in name_text.split('\n') if p.strip()]
        fixed_parts = []
        for part in parts:
            if part == '/':
                fixed_parts.append(part)
            else:
                words = part.split()
                fixed_words = [word[::-1] if _is_word_likely_mirrored(word) else word for word in words]
                fixed_parts.append(' '.join(fixed_words))

        candidate_name = ' '.join(fixed_parts)
        normalized = normalize_party(party)
        display_party = get_display_name(normalized)

        columns.append({
            'index': i,
            'name': candidate_name,
            'party': display_party
        })

    # Rows 2+: precinct data
    precinct_rows = []
    for row in table[2:]:
        if not row[0] or not row[0].strip():
            continue

        # Skip TOTAL rows (they're empty anyway)
        if 'TOTAL' in str(row[0]).upper():
            continue

        precinct_rows.append(row)

    return columns, precinct_rows


def extract_race_title(text):
    """Extract race title from page text."""
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    for line in lines[:15]:
        # Skip page numbers and headers
        if 'OF 688' in line or 'GENERAL' in line:
            continue

        # Look for race keywords
        if any(kw in line.upper() for kw in [
            'PRESIDENT', 'SENATOR', 'REPRESENTATIVE', 'ASSEMBLY',
            'JUSTICE', 'JUDGE', 'ATTORNEY', 'CLERK', 'PROPOSAL'
        ]):
            # Clean up the title
            title = line
            # Remove page numbers like "110-161"
            import re
            title = re.sub(r'\d+-\d+', '', title).strip()
            return title

    return None


def main():
    pdf_path = Path(__file__).parent.parent / 'data' / 'raw' / 'westchester_2024-11-05.pdf'
    output_path = Path(__file__).parent.parent / 'data' / 'raw' / 'westchester_2024-11-05.json'

    if not pdf_path.exists():
        print(f"❌ PDF not found: {pdf_path}")
        return 1

    print(f"📄 Processing: {pdf_path}")
    print(f"   Output: {output_path}")
    print("\n⚠️  Note: This PDF contains 688 pages of precinct-level data.")
    print("   Aggregating all precincts to get county-wide totals...\n")

    races = {}
    current_race_title = None
    current_race_data = None

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        print(f"🔍 Scanning {total_pages} pages...")

        for page_num, page in enumerate(pdf.pages):
            if page_num % 50 == 0:
                print(f"   Progress: {page_num}/{total_pages} pages...")

            # Extract race title
            text = extract_text_with_fixes(page)
            race_title = extract_race_title(text)

            if not race_title:
                continue

            # Check if new race
            if race_title != current_race_title:
                # Save previous race
                if current_race_data and current_race_data['candidates']:
                    races[current_race_title] = current_race_data

                # Start new race
                current_race_title = race_title
                current_race_data = {
                    'race_title': race_title,
                    'vote_for': 1,
                    'candidates': {},  # Dict keyed by candidate name
                    'write_in': 0,
                    'total_votes_cast': 0,
                    'under_votes': 0,
                    'over_votes': 0,
                    'total_ballots_cast': 0,
                }

            # Extract table
            tables = page.extract_tables()
            if not tables:
                continue

            columns, precinct_rows = parse_westchester_table(tables[0])

            if not columns or not precinct_rows:
                continue

            # Aggregate precinct data
            for row in precinct_rows:
                for col in columns:
                    col_idx = col['index']
                    if col_idx >= len(row) or not row[col_idx]:
                        continue

                    votes_str = str(row[col_idx]).replace(',', '').strip()
                    if not votes_str.isdigit():
                        continue

                    votes = int(votes_str)

                    # Get or create candidate
                    name = col['name']
                    if name not in current_race_data['candidates']:
                        current_race_data['candidates'][name] = {
                            'name': name,
                            'party_lines': [],
                            'total_votes': 0
                        }

                    # Add party line (aggregating across precincts)
                    # Find existing party line or create new
                    party_line = next(
                        (pl for pl in current_race_data['candidates'][name]['party_lines']
                         if pl['party'] == col['party']),
                        None
                    )

                    if party_line:
                        party_line['votes'] += votes
                    else:
                        current_race_data['candidates'][name]['party_lines'].append({
                            'party': col['party'],
                            'votes': votes
                        })

                    current_race_data['candidates'][name]['total_votes'] += votes

        # Save final race
        if current_race_data and current_race_data['candidates']:
            races[current_race_title] = current_race_data

    # Convert to list format
    races_list = []
    for race_title, race_data in races.items():
        race_data['candidates'] = list(race_data['candidates'].values())
        races_list.append(race_data)

    result = {
        'county': 'Westchester',
        'election_date': '2024-11-05',
        'races': races_list
    }

    print(f"\n✅ Extracted {len(races_list)} races")
    print(f"   Total candidates: {sum(len(r['candidates']) for r in races_list)}")

    # Sample output
    print("\n📊 Sample races:")
    for i, race in enumerate(races_list[:3], 1):
        print(f"\n{i}. {race['race_title']}")
        print(f"   Candidates: {len(race['candidates'])}")
        for candidate in race['candidates'][:3]:
            parties = ', '.join(pl['party'] for pl in candidate['party_lines'])
            print(f"   - {candidate['name']}: {candidate['total_votes']:,} votes ({parties})")
        if len(race['candidates']) > 3:
            print(f"   ... and {len(race['candidates']) - 3} more")

    # Save
    print(f"\n💾 Saving to: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)

    print("\n✅ Done!")
    return 0


if __name__ == '__main__':
    sys.exit(main())
