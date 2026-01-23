"""
Unified parser abstraction for election result extraction.

Consolidates logic from county-specific extractors (Ulster, Columbia, Dutchess, Greene)
into reusable parser classes with a common interface.
"""

import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import pdfplumber
import requests
from bs4 import BeautifulSoup

from .parties import get_display_name, is_known_party, normalize_party
from .pdf_text_fixer import extract_text_with_fixes


class BaseParser(ABC):
    """Base class for election result parsers."""

    @abstractmethod
    def can_parse(self, source: str, county_config: dict) -> bool:
        """
        Check if this parser can handle the given source.

        Args:
            source: File path (PDF) or URL (HTML)
            county_config: From registry

        Returns:
            True if this parser can handle the source
        """

    @abstractmethod
    def parse(self, source: str, county_config: dict) -> dict:
        """
        Parse election results.

        Args:
            source: File path (PDF) or URL (HTML)
            county_config: From registry

        Returns:
            Dict with structure: {
                "county": str,
                "election_date": str,
                "races": [
                    {
                        "race_title": str,
                        "candidates": [
                            {
                                "name": str,
                                "total_votes": int,
                                "party_lines": [{"party": str, "votes": int}, ...]
                            }
                        ]
                    }
                ]
            }
        """


class StandardPDFParser(BaseParser):
    """
    For Columbia, Dutchess style PDFs with 'Vote For N' pattern.

    Format characteristics:
    - Race title followed by "Vote For N" on next line
    - Candidate lines with party breakdown
    - Summary stats: Write-in, Total Votes Cast, Under Votes, Over Votes, Total Ballots Cast
    - Party lines appear separately or inline with candidate name
    """

    def can_parse(self, source: str, county_config: dict) -> bool:
        """Check if source is a PDF and county expects standard format."""
        return source.lower().endswith('.pdf')

    def parse(self, source: str, county_config: dict) -> dict:
        """Parse standard PDF format."""
        pdf_path = Path(source)
        if not pdf_path.exists():
            raise FileNotFoundError(f'PDF not found: {pdf_path}')

        races = self._parse_races(pdf_path)

        return {
            'county': county_config['name'],
            'election_date': county_config.get('election_date', ''),
            'races': races
        }

    def _extract_vote_for(self, text: str) -> int | None:
        """Extract 'Vote For N' value from text."""
        match = re.search(r'Vote For (\d+)', text)
        return int(match.group(1)) if match else None

    def _parse_races(self, pdf_path: Path) -> list[dict[str, Any]]:
        """Parse all races from PDF."""
        races = []
        current_race = None
        current_candidate = None
        in_race = False

        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = extract_text_with_fixes(page)
                lines = text.split('\n')

                for i, line in enumerate(lines):
                    line = line.strip()

                    # Skip headers and empty lines
                    if not line or self._is_header_line(line):
                        continue

                    # Detect new race by "Vote For N" pattern
                    vote_for = self._extract_vote_for(line)
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
                            'total_ballots_cast': 0,
                        }
                        in_race = True
                        continue

                    if not in_race:
                        continue

                    # Skip "TOTAL" header
                    if line == 'TOTAL':
                        continue

                    # Parse summary statistics
                    if self._parse_summary_line(line, current_race):
                        if current_candidate:
                            current_race['candidates'].append(current_candidate)
                            current_candidate = None
                        if line.startswith('Total Ballots Cast'):
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
                                if current_candidate:
                                    current_candidate['name'] = name
                                    current_candidate['total_votes'] = total
                                    current_race['candidates'].append(current_candidate)
                                else:
                                    current_race['candidates'].append({
                                        'name': name,
                                        'party_lines': [],
                                        'total_votes': total
                                    })
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

                            # Handle Yes/No for propositions
                            if prefix in ['YES', 'NO', 'Yes', 'No']:
                                current_race['candidates'].append({
                                    'name': prefix,
                                    'party_lines': [],
                                    'total_votes': votes
                                })
                                continue

                            # Handle write-in candidates
                            if '(Write-In)' in prefix or '(Write-in)' in prefix:
                                name = prefix.replace('(Write-In)', '').replace('(Write-in)', '').strip()
                                current_race['candidates'].append({
                                    'name': name,
                                    'party_lines': [],
                                    'total_votes': votes
                                })
                                continue

                            # Pattern 2: Party line (e.g., "Democratic 1,504")
                            if is_known_party(prefix):
                                if current_candidate is None:
                                    current_candidate = {
                                        'name': '',
                                        'party_lines': [],
                                        'total_votes': 0
                                    }
                                normalized = normalize_party(prefix)
                                display_name = get_display_name(normalized)
                                current_candidate['party_lines'].append({
                                    'party': display_name,
                                    'votes': votes
                                })
                                continue

                            # Pattern 3: "Candidate Name Party Votes" (single line)
                            # Try parsing as name + party
                            candidate_parsed = self._parse_candidate_line(prefix, votes)
                            if candidate_parsed:
                                current_race['candidates'].append(candidate_parsed)
                                continue

                            # Last resort: if in_race and looks like name + votes
                            tokens = prefix.split()
                            if in_race and len(tokens) >= 2 and all(t[0].isupper() for t in tokens if t):
                                current_race['candidates'].append({
                                    'name': prefix,
                                    'party_lines': [],
                                    'total_votes': votes
                                })
                                continue

        # Save final race
        if current_race and current_candidate:
            current_race['candidates'].append(current_candidate)
        if current_race:
            races.append(current_race)

        return races

    def _is_header_line(self, line: str) -> bool:
        """Check if line is a header to skip."""
        headers = [
            'Columbia County', 'Dutchess County Summary',
            '2025 General Election', 'Summary Results Report',
            'Last Updated:'
        ]
        return any(h in line for h in headers) or line.startswith('November 04, 2025')

    def _parse_summary_line(self, line: str, race: dict) -> bool:
        """
        Parse summary statistics line.

        Returns True if line was a summary stat, False otherwise.
        """
        if line.startswith('Write-in'):
            parts = line.split()
            if len(parts) >= 2:
                race['write_in'] = int(parts[-1].replace(',', ''))
            return True

        if line.startswith('Total Votes Cast'):
            parts = line.split()
            if len(parts) >= 4:
                race['total_votes_cast'] = int(parts[-1].replace(',', ''))
            return True

        if line.startswith('Under Votes'):
            parts = line.split()
            if len(parts) >= 3:
                race['under_votes'] = int(parts[-1].replace(',', ''))
            return True

        if line.startswith('Over Votes'):
            parts = line.split()
            if len(parts) >= 3:
                race['over_votes'] = int(parts[-1].replace(',', ''))
            return True

        if line.startswith('Total Ballots Cast'):
            parts = line.split()
            if len(parts) >= 4:
                race['total_ballots_cast'] = int(parts[-1].replace(',', ''))
            return True

        return False

    def _parse_candidate_line(self, prefix: str, votes: int) -> dict | None:
        """
        Try to parse a candidate line with inline party.

        Returns candidate dict if successful, None otherwise.
        """
        tokens = prefix.split()

        # Try two-word party first (more specific)
        if len(tokens) >= 3:
            potential_party = ' '.join(tokens[-2:])
            if is_known_party(potential_party):
                name = ' '.join(tokens[:-2])
                normalized = normalize_party(potential_party)
                display_name = get_display_name(normalized)
                return {
                    'name': name,
                    'party_lines': [{'party': display_name, 'votes': votes}],
                    'total_votes': votes
                }

        # Try one-word party
        if len(tokens) >= 2:
            potential_party = tokens[-1]
            if is_known_party(potential_party):
                name = ' '.join(tokens[:-1])
                normalized = normalize_party(potential_party)
                display_name = get_display_name(normalized)
                return {
                    'name': name,
                    'party_lines': [{'party': display_name, 'votes': votes}],
                    'total_votes': votes
                }

        return None


class GreenePDFParser(BaseParser):
    """
    For Greene-style PDFs with '(Vote for N)' in title.

    Format characteristics:
    - Race title contains "(Vote for N)" inline
    - Candidate format: "Name (PARTY1, PARTY2) votes percent%"
    - Followed by party breakdown: "PARTY votes percent%"
    - Abbreviated party codes (DEM, REP, CON, WFP, etc.)
    """

    def can_parse(self, source: str, county_config: dict) -> bool:
        """Check if source is a PDF and county expects Greene format."""
        return source.lower().endswith('.pdf')

    def parse(self, source: str, county_config: dict) -> dict:
        """Parse Greene PDF format."""
        pdf_path = Path(source)
        if not pdf_path.exists():
            raise FileNotFoundError(f'PDF not found: {pdf_path}')

        races = self._parse_races(pdf_path)

        return {
            'county': county_config['name'],
            'election_date': county_config.get('election_date', ''),
            'races': races
        }

    def _extract_vote_for(self, text: str) -> int | None:
        """Extract 'Vote for N' value from race title."""
        match = re.search(r'\(Vote for (\d+)\)', text)
        return int(match.group(1)) if match else None

    def _parse_races(self, pdf_path: Path) -> list[dict[str, Any]]:
        """Parse all races from PDF."""
        races = []
        current_race = None
        current_candidate = None

        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = extract_text_with_fixes(page)
                lines = text.split('\n')

                for line in lines:
                    line = line.strip()

                    # Skip headers and empty lines
                    if not line or self._is_header_line(line):
                        continue

                    # Detect new race by "Vote for N" pattern
                    vote_for = self._extract_vote_for(line)
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
                    if '%' in line and not line.startswith('Total'):
                        # Extract votes and percentage from end
                        parts = line.rsplit(maxsplit=2)
                        if len(parts) >= 3:
                            text_part = parts[0]
                            votes_str = parts[1].replace(',', '')

                            if votes_str.isdigit():
                                votes = int(votes_str)

                                # Check if this is a party breakdown line
                                if is_known_party(text_part):
                                    # This is a party line for current candidate
                                    if current_candidate:
                                        normalized = normalize_party(text_part)
                                        display_name = get_display_name(normalized)
                                        current_candidate['party_lines'].append({
                                            'party': display_name,
                                            'votes': votes
                                        })
                                    continue

                                # Check if this is a write-in line
                                if text_part.startswith('Write-in'):
                                    # Save previous candidate if exists
                                    if current_candidate:
                                        current_race['candidates'].append(current_candidate)
                                        current_candidate = None

                                    current_race['candidates'].append({
                                        'name': text_part,
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

    def _is_header_line(self, line: str) -> bool:
        """Check if line is a header to skip."""
        headers = [
            'Contest Overview Report',
            'General Election 2025',
            'Official Results'
        ]
        return any(h in line for h in headers) or line.startswith('file:///')


class HTMLParser(BaseParser):
    """
    For Ulster-style HTML results pages.

    Format characteristics:
    - HTML with Bootstrap formatting
    - Race sections with class 'race-*'
    - Candidate boxes with party badges
    - Fusion voting with party line details
    """

    def can_parse(self, source: str, county_config: dict) -> bool:
        """Check if source is a URL."""
        return source.startswith('http://') or source.startswith('https://')

    def parse(self, source: str, county_config: dict) -> dict:
        """Parse HTML format."""
        print(f'Fetching from {source}...')
        response = requests.get(source, timeout=30)
        response.raise_for_status()

        print('Parsing HTML...')
        races = self._parse_races(response.text)

        return {
            'county': county_config['name'],
            'election_date': county_config.get('election_date', ''),
            'races': races
        }

    def _parse_races(self, html_content: str) -> list[dict[str, Any]]:
        """Parse all races from HTML."""
        soup = BeautifulSoup(html_content, 'html.parser')
        races = []

        # Find all race sections
        sections = soup.find_all('section', class_=lambda c: c and 'race-' in c)

        for section in sections:
            race = self._parse_race(section)
            if race:
                races.append(race)

        return races

    def _parse_race(self, section) -> dict[str, Any] | None:
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
                    if party and party != 'Write-In':
                        normalized = normalize_party(party)
                        display_name = get_display_name(normalized)
                        party_lines.append({
                            'party': display_name,
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
                    normalized = normalize_party(party)
                    display_name = get_display_name(normalized)
                    party_lines.append({
                        'party': display_name,
                        'votes': party_votes
                    })
                except ValueError:
                    continue

            # Add candidate to race
            race['candidates'].append({
                'name': name,
                'party_lines': party_lines,
                'total_votes': total_votes
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
                race['write_in'] += votes
            elif name == 'Voids':
                race['over_votes'] = votes
            elif name == 'Blanks':
                race['under_votes'] = votes
            elif name == 'Total All Votes':
                race['total_ballots_cast'] = votes

        return race


class CanvassPDFParser(BaseParser):
    """
    For Orange County-style canvass narrative PDFs.

    Format characteristics:
    - Narrative text format from County Board of Canvassers
    - Race intro: "the whole number of votes given for candidates for the office of [RACE TITLE]"
    - Candidate format: "Name Party received votes"
    - Multi-party lines appear as separate entries with same candidate name
    - Summary: Blank, Void, Scattering, Total Votes, Total Ballots Cast
    """

    def can_parse(self, source: str, county_config: dict) -> bool:
        """Check if source is a PDF and county expects canvass format."""
        return source.lower().endswith('.pdf')

    def parse(self, source: str, county_config: dict) -> dict:
        """Parse canvass narrative PDF format."""
        pdf_path = Path(source)
        if not pdf_path.exists():
            raise FileNotFoundError(f'PDF not found: {pdf_path}')

        races = self._parse_races(pdf_path)

        return {
            'county': county_config['name'],
            'election_date': county_config.get('election_date', ''),
            'races': races
        }

    def _extract_race_title(self, text: str) -> str | None:
        """Extract race title from narrative intro line."""
        # Pattern: "the office of [RACE TITLE], was"
        match = re.search(r'the office of\s+(.+?),\s+was', text)
        return match.group(1).strip() if match else None

    def _parse_races(self, pdf_path: Path) -> list[dict[str, Any]]:
        """Parse all races from PDF."""
        races = []
        current_race = None
        candidate_dict = {}  # Track candidates by name for fusion voting
        pending_race_start = False  # Track when we've seen "the office of"

        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = extract_text_with_fixes(page)
                lines = text.split('\n')

                for i, line in enumerate(lines):
                    line = line.strip()

                    # Skip headers and empty lines
                    if not line or self._is_header_line(line):
                        continue

                    # Check if this line starts a race intro
                    if 'the office of' in line:
                        pending_race_start = True
                        continue

                    # If we're pending a race start, next line should have the title
                    if pending_race_start and ', was' in line:
                        # Extract race title (everything before ", was")
                        race_title = line.split(', was')[0].strip()
                        pending_race_start = False
                        # Save previous race
                        if current_race:
                            # Convert candidate dict to list
                            current_race['candidates'] = list(candidate_dict.values())
                            races.append(current_race)

                        # Start new race
                        current_race = {
                            'race_title': race_title,
                            'vote_for': 1,  # Canvass format doesn't specify
                            'candidates': [],
                            'write_in': 0,
                            'total_votes_cast': 0,
                            'under_votes': 0,
                            'over_votes': 0,
                            'total_ballots_cast': 0,
                        }
                        candidate_dict = {}
                        continue

                    if current_race is None:
                        continue

                    # Parse summary statistics (number appears BEFORE label in this format)
                    # Check previous line for number
                    if line == 'Blank' and i > 0:
                        prev_line = lines[i - 1].strip().replace(',', '')
                        if prev_line.isdigit():
                            current_race['under_votes'] = int(prev_line)
                        continue

                    if line == 'Void' and i > 0:
                        prev_line = lines[i - 1].strip().replace(',', '')
                        if prev_line.isdigit():
                            current_race['over_votes'] = int(prev_line)
                        continue

                    if line.startswith('Scattering') and i > 0:
                        prev_line = lines[i - 1].strip().replace(',', '')
                        if prev_line.isdigit():
                            current_race['write_in'] = int(prev_line)
                        continue

                    if line.startswith('Total Votes'):
                        parts = line.split()
                        if len(parts) >= 3:
                            current_race['total_votes_cast'] = int(parts[-1].replace(',', ''))
                        continue

                    if line.startswith('Total Ballots Cast'):
                        parts = line.split()
                        if len(parts) >= 4:
                            current_race['total_ballots_cast'] = int(parts[-1].replace(',', ''))
                        continue

                    # Parse candidate lines with "received" pattern
                    if ' received ' in line:
                        # Pattern: "Name Party received votes"
                        # Handle Write-in candidates: "Write-in - Name received votes"
                        parts = line.split(' received ')
                        if len(parts) == 2:
                            prefix = parts[0].strip()
                            votes_str = parts[1].strip().replace(',', '')

                            if votes_str.isdigit():
                                votes = int(votes_str)

                                # Check for write-in format
                                if prefix.startswith('Write-in -'):
                                    # Write-in candidate
                                    name = prefix.replace('Write-in -', '').strip()
                                    # Add to candidate dict with special name to avoid fusion
                                    write_in_key = f'Write-in - {name}'
                                    candidate_dict[write_in_key] = {
                                        'name': write_in_key,
                                        'party_lines': [],
                                        'total_votes': votes
                                    }
                                else:
                                    # Regular candidate: "Name Party received votes"
                                    # Extract name and party by finding last known party word
                                    tokens = prefix.split()
                                    name_parts = []
                                    party_parts = []
                                    found_party = False

                                    # Scan from end to find party
                                    for i in range(len(tokens) - 1, -1, -1):
                                        token = tokens[i]
                                        if not found_party and is_known_party(' '.join([token] + party_parts)):
                                            party_parts.insert(0, token)
                                            found_party = True
                                        elif found_party and is_known_party(' '.join([token] + party_parts)):
                                            party_parts.insert(0, token)
                                        elif found_party:
                                            name_parts.insert(0, token)
                                        else:
                                            name_parts.insert(0, token)

                                    if name_parts and party_parts:
                                        name = ' '.join(name_parts)
                                        party = ' '.join(party_parts)
                                        normalized = normalize_party(party)
                                        display_name = get_display_name(normalized)

                                        # Add or update candidate with fusion support
                                        if name not in candidate_dict:
                                            candidate_dict[name] = {
                                                'name': name,
                                                'party_lines': [],
                                                'total_votes': 0
                                            }

                                        candidate_dict[name]['party_lines'].append({
                                            'party': display_name,
                                            'votes': votes
                                        })
                                        candidate_dict[name]['total_votes'] += votes

        # Save final race
        if current_race:
            current_race['candidates'] = list(candidate_dict.values())
            races.append(current_race)

        return races

    def _is_header_line(self, line: str) -> bool:
        """Check if line is a header to skip."""
        headers = [
            'Statement of the County Board of Canvassers',
            'Orange County',
            '2024 General Election',
            'November',
            'to canvass the votes'
        ]
        return any(h in line for h in headers)


class PrecinctTableParser(BaseParser):
    """
    For Putnam/Westchester-style precinct table PDFs.

    Format characteristics:
    - Precinct-level tables with district rows × candidate/party columns
    - Race title in page header
    - Column headers with vertical text (need fixing via pdf_text_fixer)
    - Party affiliations in row below headers (DEM, REP, CON, WOR, etc.)
    - TOTAL row aggregating all precincts
    - Multi-page races (same race across multiple pages)
    """

    def can_parse(self, source: str, county_config: dict) -> bool:
        """Check if source is a PDF and county expects precinct table format."""
        return source.lower().endswith('.pdf')

    def parse(self, source: str, county_config: dict) -> dict:
        """Parse precinct table PDF format."""
        pdf_path = Path(source)
        if not pdf_path.exists():
            raise FileNotFoundError(f'PDF not found: {pdf_path}')

        races = self._parse_races(pdf_path)

        return {
            'county': county_config['name'],
            'election_date': county_config.get('election_date', ''),
            'races': races
        }

    def _extract_race_title(self, text: str) -> str | None:
        """Extract race title from page header text."""
        lines = [l.strip() for l in text.split('\n') if l.strip()]

        # Look for lines that contain race title
        # Usually in format: "COUNTY NAME RACE TITLE"
        for i, line in enumerate(lines[:10]):
            # Skip "GENERAL ELECTION" lines
            if 'GENERAL ELECTION' in line or 'November' in line or 'VOTE FOR' in line:
                continue
            # Race title usually contains keywords
            if any(keyword in line.upper() for keyword in [
                'PRESIDENT', 'SENATOR', 'GOVERNOR', 'REPRESENTATIVE',
                'ASSEMBLY', 'JUSTICE', 'JUDGE', 'DISTRICT ATTORNEY',
                'CORONER', 'CLERK', 'SUPERVISOR', 'COUNCIL'
            ]):
                # Clean up the title (remove county name prefix)
                title = line
                # Remove "PUTNAM COUNTY" or similar prefix
                for county_prefix in ['PUTNAM COUNTY', 'WESTCHESTER COUNTY']:
                    if title.startswith(county_prefix):
                        title = title[len(county_prefix):].strip()
                return title

        return None

    def _fix_vertical_text(self, text: str) -> str:
        """
        Fix vertical text in column headers.

        The PDF stores vertical text from bottom to top, with inconsistent
        character grouping. We'll do our best to reconstruct it.

        Example:
        Input: "S\nRI\nR\nA\nH\nD.\nA M\nLTI\nA\nM\nA\nK" (bottom-to-top)
        Desired: "KAMALA D. HARRIS"
        Pragmatic: "KAMALTI AM D.HARRIS" (close enough for vote totals)
        """
        # Split by newlines, filter empty, reverse
        parts = [p.strip() for p in text.split('\n') if p.strip()]
        parts = list(reversed(parts))

        # Join all parts together, treating internal spaces as part of the name
        joined = ''.join(parts)

        # Clean up common patterns
        import re
        # Add space before periods (name separators like "D.")
        joined = re.sub(r'\.', '. ', joined)
        # Add space before/after slashes
        joined = re.sub(r'/', ' / ', joined)
        # Collapse multiple spaces
        joined = re.sub(r'\s+', ' ', joined)

        return joined.strip()

    def _parse_column_headers(self, header_row: list[str], party_row: list[str]) -> list[dict]:
        """
        Parse column headers and associate with party affiliations.

        Handles two formats:
        1. Putnam: Row 0 has vertical text candidate names, Row 1 has party abbreviations
        2. Westchester: Row 0 has party abbreviations, Row 1 has candidate names (with newlines)

        Args:
            header_row: Row 0 from table
            party_row: Row 1 from table

        Returns:
            List of column info dicts with 'name' and 'party'
        """
        columns = []

        # Detect format: if header_row has known parties, it's Westchester format
        westchester_format = any(
            cell and is_known_party(cell.strip())
            for cell in header_row
            if cell
        )

        for i, (header_cell, name_cell) in enumerate(zip(header_row, party_row)):
            if westchester_format:
                # Westchester: header_row has party, party_row has candidate name
                party = header_cell.strip() if header_cell else ''
                candidate_text = name_cell.strip() if name_cell else ''
            else:
                # Putnam: header_row has candidate name (vertical), party_row has party
                party = name_cell.strip() if name_cell else ''
                candidate_text = header_cell.strip() if header_cell else ''

            # Only process columns that have a party affiliation
            if not party or not is_known_party(party):
                continue

            # This is a candidate column
            if not candidate_text:
                continue

            # Fix candidate name
            if westchester_format:
                # Westchester: names have newlines, may be mirrored
                # Split by newlines, reverse each part if mirrored, then join
                parts = [p.strip() for p in candidate_text.split('\n') if p.strip()]

                # Apply mirroring fix to each part
                from .pdf_text_fixer import _is_word_likely_mirrored
                fixed_parts = []
                for part in parts:
                    # Handle slashes (like "WALZ / HARRIS")
                    if part == '/':
                        fixed_parts.append(part)
                    else:
                        words = part.split()
                        fixed_words = []
                        for word in words:
                            if _is_word_likely_mirrored(word):
                                fixed_words.append(word[::-1])
                            else:
                                fixed_words.append(word)
                        fixed_parts.append(' '.join(fixed_words))

                candidate_name = ' '.join(fixed_parts)
            else:
                # Putnam: vertical text
                candidate_name = self._fix_vertical_text(candidate_text)

            # Normalize party
            normalized = normalize_party(party)
            display_party = get_display_name(normalized)

            columns.append({
                'index': i,
                'name': candidate_name,
                'party': display_party
            })

        return columns

    def _parse_races(self, pdf_path: Path) -> list[dict[str, Any]]:
        """Parse all races from PDF."""
        races = []
        current_race = None
        current_race_title = None
        candidate_totals = {}  # Track totals across pages for same race

        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                # Extract race title from page header
                text = extract_text_with_fixes(page)
                race_title = self._extract_race_title(text)

                if not race_title:
                    continue

                # Check if this is a new race or continuation
                if current_race_title != race_title:
                    # Save previous race if it exists
                    if current_race:
                        # Convert candidate_totals to candidates list
                        current_race['candidates'] = list(candidate_totals.values())
                        races.append(current_race)

                    # Start new race
                    current_race_title = race_title
                    current_race = {
                        'race_title': race_title,
                        'vote_for': 1,  # Precinct tables don't specify
                        'candidates': [],
                        'write_in': 0,
                        'total_votes_cast': 0,
                        'under_votes': 0,
                        'over_votes': 0,
                        'total_ballots_cast': 0,
                    }
                    candidate_totals = {}

                # Extract table data
                tables = page.extract_tables()
                if not tables:
                    continue

                table = tables[0]
                if len(table) < 3:  # Need header, party, and at least one data row
                    continue

                # Parse column headers
                header_row = table[0]
                party_row = table[1]
                columns = self._parse_column_headers(header_row, party_row)

                # Process data rows (skip header and party rows)
                for row_idx in range(2, len(table)):
                    row = table[row_idx]

                    # Check if this is the TOTAL row
                    if row[0] and 'TOTAL' in str(row[0]).upper():
                        # Use TOTAL row to get aggregate votes for each candidate
                        for col in columns:
                            col_idx = col['index']
                            if col_idx < len(row) and row[col_idx]:
                                votes_str = str(row[col_idx]).replace(',', '').strip()
                                if votes_str.isdigit():
                                    votes = int(votes_str)

                                    # Get or create candidate entry
                                    name = col['name']
                                    if name not in candidate_totals:
                                        candidate_totals[name] = {
                                            'name': name,
                                            'party_lines': [],
                                            'total_votes': 0
                                        }

                                    # Add party line
                                    if col['party']:
                                        candidate_totals[name]['party_lines'].append({
                                            'party': col['party'],
                                            'votes': votes
                                        })

                                    # Sum up total votes (only once per party line)
                                    candidate_totals[name]['total_votes'] += votes

                        # Look for BLANK, VOID, SCATTERING in subsequent rows
                        for summary_idx in range(row_idx + 1, min(row_idx + 10, len(table))):
                            summary_row = table[summary_idx]
                            if not summary_row[0]:
                                continue

                            label = str(summary_row[0]).strip().upper()

                            # Get the value (usually in second or third column)
                            value = None
                            for cell_idx in range(1, min(5, len(summary_row))):
                                cell = summary_row[cell_idx]
                                if cell:
                                    cell_str = str(cell).replace(',', '').strip()
                                    if cell_str.isdigit():
                                        value = int(cell_str)
                                        break

                            if value is not None:
                                if 'BLANK' in label:
                                    current_race['under_votes'] = value
                                elif 'VOID' in label:
                                    current_race['over_votes'] = value
                                elif 'SCATTERING' in label or 'WRITE' in label:
                                    current_race['write_in'] = value
                                elif 'TOTAL' in label and 'VOTE' in label:
                                    current_race['total_votes_cast'] = value
                                elif 'TOTAL' in label and 'BALLOT' in label:
                                    current_race['total_ballots_cast'] = value

        # Save final race
        if current_race:
            current_race['candidates'] = list(candidate_totals.values())
            races.append(current_race)

        return races


def get_parser(county_config: dict) -> BaseParser:
    """
    Factory function to get appropriate parser for a county.

    Args:
        county_config: From registry

    Returns:
        Parser instance for the county's format
    """
    # Map format to parser type
    format_type = county_config.get('format', 'standard_pdf')

    if format_type == 'contest_overview':
        return GreenePDFParser()
    elif format_type == 'bootstrap_html':
        return HTMLParser()
    elif format_type == 'canvass':
        return CanvassPDFParser()
    elif format_type == 'precinct_table':
        return PrecinctTableParser()
    else:  # standard_pdf or unknown
        return StandardPDFParser()
