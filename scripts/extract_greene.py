#!/usr/bin/env python3
"""
Extract election results from Greene County 2025 PDF.

Handles "Contest Overview Report" format with town-level races,
fusion voting (multiple party lines per candidate), and write-ins.
"""

import json
import re
from pathlib import Path
from typing import Any

import pdfplumber


def extract_vote_for(text: str) -> int | None:
    """Extract 'Vote For N' value from race title."""
    match = re.search(r'\(Vote for (\d+)\)', text)
    return int(match.group(1)) if match else None


def parse_races(pdf_path: Path) -> list[dict[str, Any]]:
    """Parse all races from PDF."""
    races = []
    current_race = None
    current_candidate = None

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            lines = text.split('\n')

            for i, line in enumerate(lines):
                line = line.strip()

                # Skip headers and empty lines
                if not line or 'Contest Overview Report' in line:
                    continue
                if 'General Election 2025' in line or 'Official Results' in line:
                    continue
                if line.startswith('file:///'):
                    continue

                # Detect new race by "Vote for N" pattern
                vote_for = extract_vote_for(line)
                if vote_for is not None:
                    # Save previous race
                    if current_race:
                        if current_candidate:
                            current_race['candidates'].append(current_candidate)
                            current_candidate = None
                        races.append(current_race)

                    # Start new race
                    current_race = {
                        'race_title': line.replace(f'(Vote for {vote_for})', '').strip(),
                        'vote_for': vote_for,
                        'candidates': [],
                        'total_votes_cast': 0,
                        'under_votes': 0,
                        'over_votes': 0,
                    }
                    continue

                if current_race is None:
                    continue

                # Parse metadata lines
                if line.startswith('Times Cast:'):
                    # Not used in output but skip
                    continue

                if line.startswith('Undervotes:'):
                    parts = line.split()
                    if len(parts) >= 2:
                        current_race['under_votes'] = int(parts[1].replace(',', ''))
                    continue

                if line.startswith('Overvotes:'):
                    parts = line.split()
                    if len(parts) >= 2:
                        current_race['over_votes'] = int(parts[1].replace(',', ''))
                    continue

                if line.startswith('Double Votes:'):
                    # Greene specific, not in our schema
                    continue

                # Skip precinct summary lines
                if 'Precincts reported:' in line:
                    continue

                # Parse "Total" line (end of race)
                if line.startswith('Total ') and '%' in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        total_str = parts[1].replace(',', '')
                        if total_str.isdigit():
                            current_race['total_votes_cast'] = int(total_str)
                    continue

                # Parse candidate lines with party breakdown
                # Pattern: "Name (PARTY1, PARTY2) votes percent%"
                # Followed by party breakdown lines: "PARTY votes percent%"

                # Check if this is a candidate line (has percentage at end)
                if '%' in line and not line.startswith('Total'):
                    # Try to parse as candidate or party line
                    # Candidate pattern: "Name (PARTIES) votes percent%"
                    # Party pattern: "PARTY votes percent%"
                    # Write-in pattern: "Write-in [name] votes percent%"

                    # Extract votes and percentage from end
                    parts = line.rsplit(maxsplit=2)
                    if len(parts) >= 3:
                        text_part = parts[0]
                        votes_str = parts[1].replace(',', '')
                        percent_str = parts[2].rstrip('%')

                        if votes_str.isdigit():
                            votes = int(votes_str)

                            # Check if this is a party breakdown line
                            known_parties = ['DEM', 'REP', 'CON', 'WFP', 'IND', 'OA', 'OT', 'HR']
                            if text_part in known_parties:
                                # This is a party line for current candidate
                                if current_candidate:
                                    party_map = {
                                        'DEM': 'Democratic',
                                        'REP': 'Republican',
                                        'CON': 'Conservative',
                                        'WFP': 'Working Families',
                                        'IND': 'Independence',
                                        'OA': 'OA',  # Unknown party/line
                                        'OT': 'OT',  # Unknown party/line
                                        'HR': 'HR'   # Unknown party/line
                                    }
                                    current_candidate['party_lines'].append({
                                        'party': party_map.get(text_part, text_part),
                                        'votes': votes
                                    })
                                continue

                            # Check if this is a write-in line
                            if text_part.startswith('Write-in'):
                                # Save previous candidate if exists
                                if current_candidate:
                                    current_race['candidates'].append(current_candidate)
                                    current_candidate = None

                                # Write-in handling
                                if text_part == 'Write-in':
                                    name = 'Write-in'
                                else:
                                    # Extract write-in name if present
                                    name = text_part

                                current_race['candidates'].append({
                                    'name': name,
                                    'total_votes': votes,
                                    'party_lines': []
                                })
                                continue

                            # This is a candidate line
                            # Save previous candidate if exists
                            if current_candidate:
                                current_race['candidates'].append(current_candidate)

                            # Extract name and parties from "Name (PARTIES)" format
                            match = re.match(r'(.+?)\s*\(([^)]+)\)', text_part)
                            if match:
                                name = match.group(1).strip()
                                parties_str = match.group(2).strip()

                                current_candidate = {
                                    'name': name,
                                    'total_votes': votes,
                                    'party_lines': []
                                }
                            else:
                                # No party info, just name
                                current_candidate = {
                                    'name': text_part,
                                    'total_votes': votes,
                                    'party_lines': []
                                }

    # Save final race
    if current_race:
        if current_candidate:
            current_race['candidates'].append(current_candidate)
        races.append(current_race)

    return races


def main():
    """Extract Greene County election results to JSON."""
    project_root = Path(__file__).parent.parent
    pdf_path = project_root / 'data' / 'Official-GE25.pdf'
    output_path = project_root / 'data' / 'raw' / 'greene_2025.json'

    if not pdf_path.exists():
        raise FileNotFoundError(f'PDF not found: {pdf_path}')

    print(f'Extracting from {pdf_path}...')
    races = parse_races(pdf_path)

    output = {
        'county': 'Greene',
        'election_date': '2025-11-04',
        'races': races
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    total_candidates = sum(len(race['candidates']) for race in races)
    print(f'Extracted {len(races)} races with {total_candidates} total candidates to {output_path}')

    # Report any extraction issues
    issues = []
    for race in races:
        if race['total_votes_cast'] == 0:
            issues.append(f"Race '{race['race_title']}' has zero total votes")
        if not race['candidates']:
            issues.append(f"Race '{race['race_title']}' has no candidates")

    if issues:
        print('\nExtraction issues:')
        for issue in issues:
            print(f'  - {issue}')
    else:
        print('No extraction issues detected.')


if __name__ == '__main__':
    main()
