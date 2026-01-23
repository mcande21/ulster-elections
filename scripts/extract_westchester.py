#!/usr/bin/env python3
"""Extract Westchester County election results."""

import sys
import json
from pathlib import Path

# Add scripts dir to path
scripts_dir = Path(__file__).parent
sys.path.insert(0, str(scripts_dir))

from extractors.parsers import PrecinctTableParser

def main():
    pdf_path = Path(__file__).parent.parent / 'data' / 'raw' / 'westchester_2024-11-05.pdf'
    output_path = Path(__file__).parent.parent / 'data' / 'raw' / 'westchester_2024-11-05.json'

    if not pdf_path.exists():
        print(f"❌ PDF not found: {pdf_path}")
        return 1

    print(f"📄 Processing: {pdf_path}")
    print(f"   Output: {output_path}")

    # Configure parser
    parser = PrecinctTableParser()
    county_config = {
        'name': 'Westchester',
        'election_date': '2024-11-05',
        'format': 'precinct_table'
    }

    # Parse
    try:
        print("\n🔍 Extracting races...")
        result = parser.parse(str(pdf_path), county_config)

        print(f"\n✅ Extracted {len(result['races'])} races")
        print(f"   County: {result['county']}")
        print(f"   Election Date: {result['election_date']}")

        # Summary stats
        total_candidates = sum(len(race['candidates']) for race in result['races'])
        print(f"   Total candidates: {total_candidates}")

        # Show sample races
        print("\n📊 Sample races:")
        for i, race in enumerate(result['races'][:5], 1):
            print(f"\n{i}. {race['race_title']}")
            print(f"   Candidates: {len(race['candidates'])}")
            for candidate in race['candidates'][:3]:
                parties = ', '.join(pl['party'] for pl in candidate['party_lines'])
                print(f"   - {candidate['name']}: {candidate['total_votes']:,} votes ({parties})")
            if len(race['candidates']) > 3:
                print(f"   ... and {len(race['candidates']) - 3} more")

        if len(result['races']) > 5:
            print(f"\n... and {len(result['races']) - 5} more races")

        # Save results
        print(f"\n💾 Saving to: {output_path}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2)

        print("\n✅ Done!")
        return 0

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
