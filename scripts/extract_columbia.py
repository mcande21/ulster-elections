#!/usr/bin/env python3
"""
Extract election results from Columbia County 2025 PDF.

Handles fusion voting (multiple party lines per candidate) and various
formatting patterns across town races, county-wide races, and city races.
"""

import json
import re
from pathlib import Path
from typing import Any

import pdfplumber


def extract_vote_for(text: str) -> int | None:
    """Extract 'Vote For N' value from text."""
    match = re.search(r'Vote For (\d+)', text)
    return int(match.group(1)) if match else None


def parse_races(pdf_path: Path) -> list[dict[str, Any]]:
    """Parse all races from PDF."""
    races = []
    current_race = None
    current_candidate = None
    in_race = False

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            lines = text.split('\n')

            for i, line in enumerate(lines):
                line = line.strip()

                # Skip headers and empty lines
                if not line or 'Columbia County' in line or '2025 General Election' in line:
                    continue
                if 'Summary Results Report' in line or 'Last Updated:' in line:
                    continue
                if line.startswith('November 04, 2025'):
                    continue

                # Detect new race by "Vote For N" pattern
                vote_for = extract_vote_for(line)
                if vote_for is not None:
                    # Save previous race
                    if current_race and current_candidate:
                        current_race['candidates'].append(current_candidate)
                        current_candidate = None
                    if current_race:
                        races.append(current_race)

                    # Start new race (title is previous line)
                    race_title = lines[i - 1].strip() if i > 0 else ''
                    current_race = {
                        'race_title': race_title,
                        'vote_for': vote_for,
                        'candidates': [],
                        'write_in': 0,
                        'total_votes_cast': 0,
                        'under_votes': 0,
                        'over_votes': 0,
                    }
                    in_race = True
                    continue

                if not in_race:
                    continue

                # Skip "TOTAL" header
                if line == 'TOTAL':
                    continue

                # Parse summary statistics
                if line.startswith('Write-in'):
                    if current_candidate:
                        current_race['candidates'].append(current_candidate)
                        current_candidate = None
                    parts = line.split()
                    if len(parts) >= 2:
                        current_race['write_in'] = int(parts[-1].replace(',', ''))
                    continue

                if line.startswith('Total Votes Cast'):
                    if current_candidate:
                        current_race['candidates'].append(current_candidate)
                        current_candidate = None
                    parts = line.split()
                    if len(parts) >= 4:
                        current_race['total_votes_cast'] = int(parts[-1].replace(',', ''))
                    continue

                if line.startswith('Under Votes'):
                    parts = line.split()
                    if len(parts) >= 3:
                        current_race['under_votes'] = int(parts[-1].replace(',', ''))
                    continue

                if line.startswith('Over Votes'):
                    parts = line.split()
                    if len(parts) >= 3:
                        current_race['over_votes'] = int(parts[-1].replace(',', ''))
                    continue

                if line.startswith('Total Ballots Cast'):
                    parts = line.split()
                    if len(parts) >= 4:
                        current_race['total_ballots_cast'] = int(parts[-1].replace(',', ''))
                    in_race = False  # End of race
                    continue

                # Parse candidate lines
                # Pattern 1: "Candidate Name Total N" (end of candidate)
                if ' Total ' in line:
                    parts = line.rsplit('Total', 1)
                    if len(parts) == 2:
                        name = parts[0].strip()
                        total_str = parts[1].strip().replace(',', '')
                        try:
                            total = int(total_str)
                            if current_candidate and current_candidate['party_lines']:
                                # We have accumulated party lines, now add name and total
                                current_candidate['name'] = name
                                current_candidate['total'] = total
                                current_race['candidates'].append(current_candidate)
                                current_candidate = None
                            elif current_candidate:
                                # Current candidate has no party lines yet, just set name and total
                                current_candidate['name'] = name
                                current_candidate['total'] = total
                                current_race['candidates'].append(current_candidate)
                                current_candidate = None
                            else:
                                # No current candidate - shouldn't happen but handle it
                                current_candidate = {
                                    'name': name,
                                    'party_lines': [],
                                    'total': total
                                }
                                current_race['candidates'].append(current_candidate)
                                current_candidate = None
                        except ValueError:
                            pass
                    continue

                # Parse lines with format: "text votes"
                parts = line.rsplit(maxsplit=1)
                if len(parts) == 2:
                    prefix, votes_str = parts
                    votes_str = votes_str.replace(',', '')
                    if votes_str.isdigit():
                        votes = int(votes_str)

                        # Known party names for party line detection
                        known_parties = [
                            'Democratic', 'Republican', 'Conservative',
                            'Working Families', 'Independence', 'Liberal',
                            'Green', 'Libertarian', 'Reform', 'The Harmony Party',
                            'Future Hudson', 'Hudson United', 'Chatham For All',
                            'Chatham Neighbors Party', 'Do Something', 'Connect Ghent',
                            'Clermont Friends', 'Grounded Vision', 'Hillsdale Unity Party',
                            'Kinderhook Community Party'
                        ]

                        # Handle Yes/No for propositions
                        if prefix in ['YES', 'NO', 'Yes', 'No']:
                            current_race['candidates'].append({
                                'name': prefix,
                                'party_lines': [],
                                'total': votes
                            })
                            continue

                        # Handle write-in candidates (e.g., "Darla Dobert-Crosby (Write-In)")
                        if '(Write-In)' in prefix or '(Write-in)' in prefix:
                            name = prefix.replace('(Write-In)', '').replace('(Write-in)', '').strip()
                            current_race['candidates'].append({
                                'name': name,
                                'party_lines': [],
                                'total': votes
                            })
                            continue

                        # Pattern 2: Party line (e.g., "Democratic 1,504")
                        if prefix in known_parties:
                            if current_candidate is None:
                                current_candidate = {
                                    'name': '',
                                    'party_lines': [],
                                    'total': 0
                                }
                            current_candidate['party_lines'].append({
                                'party': prefix,
                                'votes': votes
                            })
                            continue

                        # Pattern 3: "Candidate Name Party Votes" (single line)
                        # Try two-word party first (more specific)
                        tokens = prefix.split()
                        if len(tokens) >= 3:
                            # Try last two tokens as party
                            potential_party = ' '.join(tokens[-2:])
                            if potential_party in known_parties:
                                name = ' '.join(tokens[:-2])
                                current_race['candidates'].append({
                                    'name': name,
                                    'party_lines': [{'party': potential_party, 'votes': votes}],
                                    'total': votes
                                })
                                continue

                        # Try one-word party
                        if len(tokens) >= 2:
                            potential_party = tokens[-1]
                            if potential_party in known_parties:
                                name = ' '.join(tokens[:-1])
                                current_race['candidates'].append({
                                    'name': name,
                                    'party_lines': [{'party': potential_party, 'votes': votes}],
                                    'total': votes
                                })
                                continue

                        # Last resort: if in_race and looks like name + votes (no weird chars)
                        # Only accept if tokens look like a person's name
                        if in_race and len(tokens) >= 2 and all(t[0].isupper() for t in tokens if t):
                            # Appears to be a name - treat as candidate with no party
                            current_race['candidates'].append({
                                'name': prefix,
                                'party_lines': [],
                                'total': votes
                            })
                            continue

        # Save final race
        if current_race and current_candidate:
            current_race['candidates'].append(current_candidate)
        if current_race:
            races.append(current_race)

    return races


def main():
    """Extract Columbia County election results to JSON."""
    project_root = Path(__file__).parent.parent
    pdf_path = project_root / 'data' / 'Summary Results with Candidate Totals_41b03cbb-9244-4b14-b023-a0fdb76110d9.PDF'
    output_path = project_root / 'data' / 'raw' / 'columbia_2025.json'

    if not pdf_path.exists():
        raise FileNotFoundError(f'PDF not found: {pdf_path}')

    print(f'Extracting from {pdf_path}...')
    races = parse_races(pdf_path)

    output = {
        'county': 'Columbia',
        'election_date': '2025-11-04',
        'races': races
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f'Extracted {len(races)} races to {output_path}')

    # Report on candidates
    total_candidates = sum(len(race['candidates']) for race in races)
    print(f'Total candidates: {total_candidates}')


if __name__ == '__main__':
    main()
