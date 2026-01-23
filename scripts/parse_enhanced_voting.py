#!/usr/bin/env python3
"""
Parse Enhanced Voting API data into our standard format.
"""
import json
import sys
from pathlib import Path


def parse_enhanced_voting_data(raw_data):
    """Transform Enhanced Voting API response to our format."""

    # Extract metadata
    election = raw_data['election']
    jurisdiction = raw_data['jurisdiction']

    county_name = jurisdiction['name'][0]['text'] if 'name' in jurisdiction and jurisdiction['name'] else "Unknown"
    # Extract just county name if it contains "County"
    if "County" in county_name:
        county_name = county_name.split()[0]

    election_date = election['electionDate'].split('T')[0]  # Get YYYY-MM-DD part

    # Parse ballot items (races)
    races = []
    for item in raw_data['ballotItems']:
        # Only process candidate contests
        if item['contestType'] != 'Candidate':
            continue

        race_title = item['name'][0]['text']

        # Group candidates by name (for cross-endorsement)
        candidate_map = {}

        for ballot_option in item['summaryResults']['ballotOptions']:
            candidate_name = ballot_option['name'][0]['text'] if ballot_option.get('name') and ballot_option['name'] else 'Unknown'

            # Handle party name safely
            party_name = 'Unknown'
            if ballot_option.get('party') and ballot_option['party'].get('name') and ballot_option['party']['name']:
                party_name = ballot_option['party']['name'][0]['text']

            vote_count = ballot_option['voteCount']

            if candidate_name not in candidate_map:
                candidate_map[candidate_name] = {
                    'name': candidate_name,
                    'party_lines': [],
                    'total': 0
                }

            candidate_map[candidate_name]['party_lines'].append({
                'party': party_name,
                'votes': vote_count
            })
            candidate_map[candidate_name]['total'] += vote_count

        # Convert to list and sort by total votes
        candidates = sorted(
            candidate_map.values(),
            key=lambda c: c['total'],
            reverse=True
        )

        races.append({
            'title': race_title,
            'candidates': candidates
        })

    return {
        'county': county_name,
        'election_date': election_date,
        'races': races
    }


def main():
    if len(sys.argv) < 3:
        print("Usage: parse_enhanced_voting.py <input_json> <output_json>")
        sys.exit(1)

    input_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2])

    with open(input_file) as f:
        raw_data = json.load(f)

    parsed_data = parse_enhanced_voting_data(raw_data)

    with open(output_file, 'w') as f:
        json.dump(parsed_data, f, indent=2)

    print(f"Parsed {len(parsed_data['races'])} races from {parsed_data['county']} County")
    print(f"Saved to: {output_file}")


if __name__ == '__main__':
    main()
