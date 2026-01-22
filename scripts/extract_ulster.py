#!/usr/bin/env python3
"""
Extract election results from Ulster County 2025 HTML.

Handles fusion voting (multiple party lines per candidate) and parses
HTML structure with Bootstrap formatting.
"""

import json
import re
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup


def parse_races(html_content: str) -> list[dict[str, Any]]:
    """Parse all races from HTML."""
    soup = BeautifulSoup(html_content, 'html.parser')
    races = []

    # Find all race sections
    sections = soup.find_all('section', class_=lambda c: c and 'race-' in c)

    for section in sections:
        race = parse_race(section)
        if race:
            races.append(race)

    return races


def parse_race(section) -> dict[str, Any] | None:
    """Parse a single race section."""
    # Extract race title
    title_tag = section.find('h5', class_='race-title')
    if not title_tag:
        return None
    race_title = title_tag.get_text(strip=True)

    # Initialize race structure
    race = {
        'race_title': race_title,
        'vote_for': 1,  # Ulster doesn't specify, default to 1
        'candidates': [],
        'write_in': 0,
        'total_votes_cast': 0,
        'under_votes': 0,
        'over_votes': 0,
        'total_ballots_cast': 0,
    }

    # Parse candidates
    candidate_boxes = section.find_all('div', class_='candidate-box')

    for box in candidate_boxes:
        # Main candidate row
        main_row = box.find('div', class_='candidate-row')
        if not main_row:
            continue

        # Get candidate name
        name_div = main_row.find('div', class_='candidate-name')
        if not name_div:
            continue
        name = name_div.get_text(strip=True)

        # Skip summary rows
        if name in ['Candidate Votes']:
            # This is the summary section
            votes_text = main_row.find_all('div')[2].get_text(strip=True)
            race['total_votes_cast'] = int(votes_text.replace(',', ''))
            continue

        # Get candidate total votes
        vote_divs = main_row.find_all('div', recursive=False)
        if len(vote_divs) < 3:
            continue

        total_text = vote_divs[2].get_text(strip=True)
        try:
            total_votes = int(total_text.replace(',', ''))
        except ValueError:
            continue

        # Check if this is Write-In
        if name == 'Write-In':
            race['write_in'] = total_votes
            continue

        # Parse party lines (fusion voting)
        party_lines = []

        # Check for single party in main row (non-fusion candidates)
        party_div = main_row.find('div', class_='candidate-party')
        if party_div:
            badge = party_div.find('span', class_='badge')
            if badge:
                party = badge.get_text(strip=True)
                # Only add if it's not "Write-In" badge
                if party and party != 'Write-In':
                    party_lines.append({
                        'party': party,
                        'votes': total_votes
                    })

        # Check for multiple party lines (fusion voting)
        detail_rows = box.find_all('div', class_='candidate-details')

        for detail_row in detail_rows:
            # Get party name from badge
            badge = detail_row.find('span', class_='badge')
            if not badge:
                continue
            party = badge.get_text(strip=True)

            # Get party line votes
            detail_divs = detail_row.find_all('div', recursive=False)
            if len(detail_divs) < 2:
                continue

            party_votes_text = detail_divs[1].get_text(strip=True)
            try:
                party_votes = int(party_votes_text.replace(',', ''))
                party_lines.append({
                    'party': party,
                    'votes': party_votes
                })
            except ValueError:
                continue

        # Add candidate to race
        race['candidates'].append({
            'name': name,
            'party_lines': party_lines,
            'total': total_votes
        })

    # Parse summary statistics
    summary_rows = section.find_all('div', class_='candidate-row')
    for row in summary_rows:
        name_div = row.find('div', class_='candidate-name')
        if not name_div:
            continue

        name = name_div.get_text(strip=True)
        vote_divs = row.find_all('div', recursive=False)

        if len(vote_divs) < 2:
            continue

        votes_text = vote_divs[1].get_text(strip=True)
        try:
            votes = int(votes_text.replace(',', ''))
        except ValueError:
            continue

        if name == 'Unqualified Write-In':
            # Count as write-in
            race['write_in'] += votes
        elif name == 'Voids':
            race['over_votes'] = votes
        elif name == 'Blanks':
            race['under_votes'] = votes
        elif name == 'Total All Votes':
            race['total_ballots_cast'] = votes

    return race


def main():
    """Extract Ulster County election results to JSON."""
    project_root = Path(__file__).parent.parent
    output_path = project_root / 'data' / 'raw' / 'ulster_2025.json'

    url = 'https://elections.ulstercountyny.gov/election-results/2025-11-05-official.html'

    print(f'Fetching from {url}...')
    response = requests.get(url)
    response.raise_for_status()

    print('Parsing HTML...')
    races = parse_races(response.text)

    output = {
        'county': 'Ulster',
        'election_date': '2025-11-05',
        'races': races
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f'Extracted {len(races)} races to {output_path}')


if __name__ == '__main__':
    main()
