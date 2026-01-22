#!/usr/bin/env python3
"""
Unified PDF election results extractor.

Handles fusion voting (multiple party lines per candidate) across
Columbia, Dutchess, and Greene counties' PDF formats.
"""

import json
import re
from pathlib import Path
from typing import Any

import pdfplumber

from .config import COUNTY_CONFIGS, GREENE_PARTY_MAP, STANDARD_PARTIES


def extract_vote_for(text: str, greene_format: bool = False) -> int | None:
    """Extract 'Vote For N' value from text."""
    if greene_format:
        # Greene format: "(Vote for N)"
        match = re.search(r'\(Vote for (\d+)\)', text)
    else:
        # Columbia/Dutchess format: "Vote For N"
        match = re.search(r'Vote For (\d+)', text)
    return int(match.group(1)) if match else None


def parse_candidate_line(
    line: str,
    known_parties: list[str],
    current_candidate: dict[str, Any] | None,
    current_race: dict[str, Any],
    greene_format: bool = False,
) -> tuple[dict[str, Any] | None, bool]:
    """
    Parse a candidate line and return (updated_candidate, line_was_handled).

    Returns:
        (current_candidate, True) if line was processed
        (None, False) if line should be skipped
    """
    # Parse lines with format: "text votes"
    parts = line.rsplit(maxsplit=1)
    if len(parts) != 2:
        return (current_candidate, False)

    prefix, votes_str = parts
    votes_str = votes_str.replace(',', '')
    if not votes_str.isdigit():
        return (current_candidate, False)

    votes = int(votes_str)

    # Handle Yes/No for propositions
    if prefix in ['YES', 'NO', 'Yes', 'No']:
        current_race['candidates'].append({
            'name': prefix,
            'party_lines': [],
            'total_votes': votes
        })
        return (None, True)

    # Handle write-in candidates
    if '(Write-In)' in prefix or '(Write-in)' in prefix or prefix.startswith('Write-in'):
        name = prefix.replace('(Write-In)', '').replace('(Write-in)', '').strip()
        if name == 'Write-in':
            name = 'Write-in'
        current_race['candidates'].append({
            'name': name,
            'party_lines': [],
            'total_votes': votes
        })
        return (None, True)

    # Pattern: Party line (e.g., "Democratic 1,504")
    if prefix in known_parties:
        if current_candidate is None:
            current_candidate = {
                'name': '',
                'party_lines': [],
                'total_votes': 0
            }
        current_candidate['party_lines'].append({
            'party': prefix,
            'votes': votes
        })
        return (current_candidate, True)

    # Pattern: "Candidate Name Party Votes" (single line)
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
                'total_votes': votes
            })
            return (None, True)

    # Try one-word party
    if len(tokens) >= 2:
        potential_party = tokens[-1]
        if potential_party in known_parties:
            name = ' '.join(tokens[:-1])
            current_race['candidates'].append({
                'name': name,
                'party_lines': [{'party': potential_party, 'votes': votes}],
                'total_votes': votes
            })
            return (None, True)

    # Last resort: if looks like name + votes (no weird chars)
    # Only accept if tokens look like a person's name
    if len(tokens) >= 2 and all(t[0].isupper() for t in tokens if t):
        # Appears to be a name - treat as candidate with no party
        current_race['candidates'].append({
            'name': prefix,
            'party_lines': [],
            'total_votes': votes
        })
        return (None, True)

    return (current_candidate, False)


def parse_greene_candidate_line(
    line: str,
    current_candidate: dict[str, Any] | None,
    current_race: dict[str, Any],
) -> dict[str, Any] | None:
    """Parse Greene-specific candidate line format."""
    # Skip lines that aren't candidate/party lines
    if not '%' in line:
        return current_candidate
    if line.startswith('Total'):
        return current_candidate
    if 'Precincts reported:' in line:
        return current_candidate

    # Extract votes and percentage from end
    parts = line.rsplit(maxsplit=2)
    if len(parts) < 3:
        return current_candidate

    text_part = parts[0]
    votes_str = parts[1].replace(',', '')
    percent_str = parts[2].rstrip('%')

    if not votes_str.isdigit():
        return current_candidate

    votes = int(votes_str)

    # Check if this is a party breakdown line
    known_parties = list(GREENE_PARTY_MAP.keys())
    if text_part in known_parties:
        # This is a party line for current candidate
        if current_candidate:
            current_candidate['party_lines'].append({
                'party': GREENE_PARTY_MAP.get(text_part, text_part),
                'votes': votes
            })
        return current_candidate

    # Check if this is a write-in line
    if text_part.startswith('Write-in'):
        # Save previous candidate if exists
        if current_candidate:
            current_race['candidates'].append(current_candidate)
            current_candidate = None

        name = text_part if text_part != 'Write-in' else 'Write-in'
        current_race['candidates'].append({
            'name': name,
            'total_votes': votes,
            'party_lines': []
        })
        return None

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

    return current_candidate


def parse_races(pdf_path: Path, config: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse all races from PDF using county-specific configuration."""
    races = []
    current_race = None
    current_candidate = None
    in_race = False
    greene_format = config.get('greene_format', False)

    # Build known parties list
    known_parties = STANDARD_PARTIES + config.get('local_parties', [])

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            lines = text.split('\n')

            for i, line in enumerate(lines):
                line = line.strip()

                # Skip headers and empty lines (county-specific patterns)
                if not line:
                    continue

                # Common skip patterns
                if 'Summary' in line and 'County' in line:
                    continue
                if '2025 General Election' in line or 'General Election 2025' in line:
                    continue
                if 'Last Updated:' in line or line.startswith('November 04, 2025'):
                    continue
                if line.startswith('file:///'):
                    continue
                if 'Official Results' in line or 'Contest Overview Report' in line:
                    continue

                # Detect new race by "Vote For N" pattern
                vote_for = extract_vote_for(line, greene_format)
                if vote_for is not None:
                    # Save previous race
                    if current_race and current_candidate:
                        current_race['candidates'].append(current_candidate)
                        current_candidate = None
                    if current_race:
                        races.append(current_race)

                    # Start new race
                    if greene_format:
                        # Greene: title includes vote_for pattern
                        race_title = line.replace(f'(Vote for {vote_for})', '').strip()
                    else:
                        # Columbia/Dutchess: title is previous line
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

                    # Add total_ballots_cast for non-Greene formats
                    if not greene_format:
                        current_race['total_ballots_cast'] = 0

                    in_race = True
                    continue

                # Skip lines when not actively parsing a race
                if not in_race:
                    continue

                # Skip "TOTAL" header
                if line == 'TOTAL':
                    continue

                # Parse summary statistics
                # Greene format: write-ins are candidates, not summary stats
                if line.startswith('Write-in') and not greene_format:
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

                if line.startswith('Under Votes') or line.startswith('Undervotes:'):
                    parts = line.split()
                    if len(parts) >= 2:
                        current_race['under_votes'] = int(parts[-1].replace(',', ''))
                    continue

                if line.startswith('Over Votes') or line.startswith('Overvotes:'):
                    parts = line.split()
                    if len(parts) >= 2:
                        current_race['over_votes'] = int(parts[-1].replace(',', ''))
                    continue

                if line.startswith('Total Ballots Cast'):
                    parts = line.split()
                    if len(parts) >= 4:
                        current_race['total_ballots_cast'] = int(parts[-1].replace(',', ''))
                    in_race = False  # End of race
                    continue

                # Greene-specific metadata
                if line.startswith('Times Cast:') or line.startswith('Double Votes:'):
                    continue
                if 'Precincts reported:' in line:
                    continue

                # Parse "Total" line for Greene format
                if greene_format and line.startswith('Total ') and '%' in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        total_str = parts[1].replace(',', '')
                        if total_str.isdigit():
                            current_race['total_votes_cast'] = int(total_str)
                    continue

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
                                current_candidate['total_votes'] = total
                                current_race['candidates'].append(current_candidate)
                                current_candidate = None
                            elif current_candidate:
                                # Current candidate has no party lines yet, just set name and total
                                current_candidate['name'] = name
                                current_candidate['total_votes'] = total
                                current_race['candidates'].append(current_candidate)
                                current_candidate = None
                            else:
                                # No current candidate - shouldn't happen but handle it
                                current_candidate = {
                                    'name': name,
                                    'party_lines': [],
                                    'total_votes': total
                                }
                                current_race['candidates'].append(current_candidate)
                                current_candidate = None
                        except ValueError:
                            pass
                    continue

                # Parse candidate lines based on format
                if greene_format:
                    current_candidate = parse_greene_candidate_line(
                        line, current_candidate, current_race
                    )
                else:
                    current_candidate, handled = parse_candidate_line(
                        line, known_parties, current_candidate, current_race, greene_format
                    )
                    # Continue to next line if handled
                    if handled:
                        continue

    # Save final race
    if current_race and current_candidate:
        current_race['candidates'].append(current_candidate)
    if current_race:
        races.append(current_race)

    return races


def extract_races_from_pdf(county: str) -> None:
    """Extract races from PDF for specified county."""
    config = COUNTY_CONFIGS.get(county.lower())
    if not config:
        raise ValueError(f'Unknown county: {county}. Available: {list(COUNTY_CONFIGS.keys())}')

    # Resolve paths relative to project root (2 levels up from this file)
    project_root = Path(__file__).parent.parent.parent
    pdf_path = project_root / config['input_pdf']
    output_path = project_root / config['output_json']

    if not pdf_path.exists():
        raise FileNotFoundError(f'PDF not found: {pdf_path}')

    print(f"Extracting from {pdf_path}...")
    races = parse_races(pdf_path, config)

    output = {
        'county': config['county_name'],
        'election_date': config['election_date'],
        'races': races
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    total_candidates = sum(len(race['candidates']) for race in races)
    print(f"Extracted {len(races)} races with {total_candidates} total candidates to {output_path}")

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
