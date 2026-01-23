#!/usr/bin/env python3
"""
Test PrecinctTableParser on Putnam County PDF.
"""

import json
import sys
from pathlib import Path

# Add extractors to path
sys.path.insert(0, str(Path(__file__).parent))

from extractors.parsers import PrecinctTableParser


def test_putnam():
    """Test Putnam County PDF parsing."""
    pdf_path = Path(__file__).parent.parent / 'data' / 'raw' / 'putnam_2024-11-05.pdf'

    if not pdf_path.exists():
        print(f'PDF not found: {pdf_path}')
        return

    print(f'Testing PrecinctTableParser on {pdf_path.name}...\n')

    # Configure parser
    county_config = {
        'name': 'Putnam',
        'election_date': '2024-11-05',
        'format': 'precinct_table'
    }

    # Parse
    parser = PrecinctTableParser()
    results = parser.parse(str(pdf_path), county_config)

    # Display summary
    print(f"County: {results['county']}")
    print(f"Election Date: {results['election_date']}")
    print(f"Races found: {len(results['races'])}\n")

    # Show first 3 races
    for i, race in enumerate(results['races'][:3], 1):
        print(f"{i}. {race['race_title']}")
        print(f"   Candidates: {len(race['candidates'])}")

        # Show top 2 candidates
        for j, cand in enumerate(race['candidates'][:2], 1):
            party_str = ', '.join([f"{pl['party']} ({pl['votes']:,})" for pl in cand['party_lines']])
            print(f"   {j}. {cand['name']}: {cand['total_votes']:,} votes")
            if party_str:
                print(f"      Party lines: {party_str}")

        print(f"   Total votes cast: {race['total_votes_cast']:,}")
        print(f"   Write-in: {race['write_in']:,}")
        print(f"   Blank: {race['under_votes']:,}")
        print(f"   Void: {race['over_votes']:,}")
        print()

    # Save full results
    output_path = Path(__file__).parent.parent / 'data' / 'raw' / 'putnam_2024-11-05.json'
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"Full results saved to: {output_path}")
    print(f"Total races: {len(results['races'])}")


if __name__ == '__main__':
    test_putnam()
