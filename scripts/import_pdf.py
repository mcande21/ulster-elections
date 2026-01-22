#!/usr/bin/env python3
"""
Auto-importing PDF extractor for election results.

Usage:
    python scripts/import_pdf.py /path/to/election_results.pdf [--full] [--county NAME]

Auto-detects county and date from PDF content, extracts races, saves JSON.
With --full flag, also reloads database and regenerates viz data.
With --county flag, override auto-detected county name (e.g., --county Greene).

Examples:
    # Auto-detect everything
    python scripts/import_pdf.py data/ulster_results.pdf

    # Override county name
    python scripts/import_pdf.py data/Official-GE25.pdf --county Greene

    # Run full pipeline
    python scripts/import_pdf.py data/results.pdf --full

    # Full pipeline with county override
    python scripts/import_pdf.py data/Official-GE25.pdf --county Greene --full
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pdfplumber

from extractors.base import parse_races
from extractors.config import STANDARD_PARTIES


def detect_county_and_date(pdf_path: Path, county_override: str = None) -> tuple[str, str]:
    """
    Auto-detect county name and election date from PDF content.

    Returns:
        (county_name, election_date) tuple
        e.g., ("Ulster", "2025-11-04")
    """
    county_name = None
    election_date = None

    with pdfplumber.open(pdf_path) as pdf:
        # Read first 3 pages for metadata
        text_sample = ""
        for page in pdf.pages[:3]:
            text_sample += page.extract_text() + "\n"

    # Use override if provided
    if county_override:
        county_name = county_override.title()
    else:
        # Detect county name
        # Strategy 1: Look for patterns like "Ulster County", "Greene County", etc.
        county_pattern = r'(\w+)\s+County'
        county_matches = re.findall(county_pattern, text_sample, re.IGNORECASE)

        if county_matches:
            # Take first match, normalize to title case
            county_name = county_matches[0].title()

        # Strategy 2: Check filename if pattern not found in content
        if not county_name:
            # Look for known county names in filename
            filename = pdf_path.name.lower()
            known_counties = ['ulster', 'greene', 'dutchess', 'columbia', 'sullivan', 'orange']
            for county in known_counties:
                if county in filename:
                    county_name = county.title()
                    break

    # Detect election date
    # Look for date patterns like "November 4, 2025" or "11/04/2025"
    date_patterns = [
        # "November 4, 2025" format
        r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s+(\d{4})',
        # "11/04/2025" or "11-04-2025" format
        r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})',
    ]

    for pattern in date_patterns:
        matches = re.findall(pattern, text_sample, re.IGNORECASE)
        if matches:
            match = matches[0]

            # Handle text month format
            if isinstance(match[0], str) and not match[0].isdigit():
                month_name, day, year = match
                try:
                    date_obj = datetime.strptime(f"{month_name} {day}, {year}", "%B %d, %Y")
                    election_date = date_obj.strftime("%Y-%m-%d")
                    break
                except ValueError:
                    continue
            # Handle numeric format
            else:
                month, day, year = match
                try:
                    date_obj = datetime(int(year), int(month), int(day))
                    election_date = date_obj.strftime("%Y-%m-%d")
                    break
                except ValueError:
                    continue

    # Validate we found both
    if not county_name:
        raise ValueError(
            "Could not detect county name from PDF. "
            "Expected pattern like 'Ulster County' in first 3 pages."
        )

    if not election_date:
        raise ValueError(
            "Could not detect election date from PDF. "
            "Expected pattern like 'November 4, 2025' in first 3 pages."
        )

    return county_name, election_date


def detect_greene_format(pdf_path: Path) -> bool:
    """
    Detect if PDF uses Greene County format.

    Greene format characteristics:
    - Has "(Vote for N)" pattern in race titles
    - Has party abbreviations like "DEM", "REP", "CON"
    - Has percentage signs in candidate lines
    """
    with pdfplumber.open(pdf_path) as pdf:
        text_sample = ""
        for page in pdf.pages[:2]:
            text_sample += page.extract_text() + "\n"

    # Check for Greene-specific patterns
    has_vote_for_parens = r'\(Vote for \d+\)' in text_sample or re.search(r'\(Vote for \d+\)', text_sample)
    has_party_abbrev = bool(re.search(r'\b(DEM|REP|CON|WFP)\b', text_sample))
    has_percentages = '%' in text_sample

    # Greene format if has vote_for pattern and party abbreviations
    return bool(has_vote_for_parens and has_party_abbrev)


def detect_local_parties(pdf_path: Path, greene_format: bool = False) -> list[str]:
    """
    Auto-detect local party lines that aren't in STANDARD_PARTIES.

    Returns:
        List of unique local party names
    """
    # Greene format doesn't use local parties in the same way
    if greene_format:
        return []

    local_parties = set()

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            lines = text.split('\n')

            for line in lines:
                # Look for lines with format "PartyName votes"
                parts = line.rsplit(maxsplit=1)
                if len(parts) == 2:
                    potential_party, votes_str = parts
                    votes_str = votes_str.replace(',', '')

                    # If it looks like a party line (text followed by number)
                    if votes_str.isdigit() and potential_party:
                        # Check if it's not a standard party
                        if (potential_party not in STANDARD_PARTIES and
                            not any(std.lower() in potential_party.lower()
                                   for std in STANDARD_PARTIES)):
                            # Filter out obvious non-party patterns
                            skip_patterns = ['Total', 'Vote', 'Write', 'Times', 'Under', 'Over', 'Double', 'General', 'Precinct']
                            # Also skip if "Total" appears anywhere (e.g., "Name Total")
                            if not any(skip in potential_party for skip in skip_patterns):
                                # Must be reasonable length and look like a party name
                                if len(potential_party.split()) <= 5 and len(potential_party) > 2:
                                    local_parties.add(potential_party)

    return sorted(local_parties)


def import_pdf(pdf_path: Path, full_pipeline: bool = False, county_override: str = None) -> None:
    """
    Import election results from PDF.

    Args:
        pdf_path: Path to PDF file
        full_pipeline: If True, also run load_db.py, analyze.py, and generate_viz_data.py
        county_override: Optional county name if auto-detection fails
    """
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    print(f"Reading PDF: {pdf_path}")

    # Detect county and date
    if county_override:
        print(f"Using county override: {county_override}")
    print("Auto-detecting county and election date...")
    county_name, election_date = detect_county_and_date(pdf_path, county_override)
    print(f"  County: {county_name}")
    print(f"  Date: {election_date}")

    # Detect format
    print("Detecting PDF format...")
    greene_format = detect_greene_format(pdf_path)
    print(f"  Format: {'Greene' if greene_format else 'Standard'}")

    # Detect local parties
    print("Auto-detecting local parties...")
    local_parties = detect_local_parties(pdf_path, greene_format)
    if local_parties:
        print(f"  Found {len(local_parties)} local parties")
        for party in local_parties[:5]:
            print(f"    - {party}")
        if len(local_parties) > 5:
            print(f"    ... and {len(local_parties) - 5} more")
    else:
        print("  No local parties detected")

    # Build config for this PDF
    config = {
        "county_name": county_name,
        "election_date": election_date,
        "local_parties": local_parties,
        "greene_format": greene_format,
    }

    # Parse races
    print(f"\nExtracting races from PDF...")
    races = parse_races(pdf_path, config)

    # Prepare output
    year = election_date.split('-')[0]
    output_filename = f"{county_name.lower()}_{year}.json"

    project_root = Path(__file__).parent.parent
    output_path = project_root / "data" / "raw" / output_filename

    output = {
        "county": county_name,
        "election_date": election_date,
        "races": races
    }

    # Save JSON
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    total_candidates = sum(len(race['candidates']) for race in races)
    print(f"\n✓ Extracted {len(races)} races with {total_candidates} candidates")
    print(f"✓ Saved to: {output_path}")

    # Run full pipeline if requested
    if full_pipeline:
        print("\n" + "="*60)
        print("Running full pipeline (--full)")
        print("="*60)

        scripts_dir = project_root / "scripts"

        # 1. Load database
        print("\n[1/3] Loading database...")
        result = subprocess.run(
            [sys.executable, str(scripts_dir / "load_db.py")],
            cwd=project_root,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"ERROR: load_db.py failed\n{result.stderr}")
            sys.exit(1)
        print(result.stdout)

        # 2. Run analysis
        print("\n[2/3] Running analysis...")
        result = subprocess.run(
            [sys.executable, str(scripts_dir / "analyze.py")],
            cwd=project_root,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"ERROR: analyze.py failed\n{result.stderr}")
            sys.exit(1)
        print(result.stdout)

        # 3. Generate viz data
        print("\n[3/3] Generating visualization data...")
        result = subprocess.run(
            [sys.executable, str(scripts_dir / "generate_viz_data.py")],
            cwd=project_root,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"ERROR: generate_viz_data.py failed\n{result.stderr}")
            sys.exit(1)
        print(result.stdout)

        print("\n" + "="*60)
        print("✓ Full pipeline complete")
        print("="*60)


def main():
    parser = argparse.ArgumentParser(
        description="Auto-import election results from PDF"
    )
    parser.add_argument(
        "pdf_path",
        type=Path,
        help="Path to PDF election results file"
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run full pipeline: extract, load DB, analyze, generate viz"
    )
    parser.add_argument(
        "--county",
        type=str,
        help="Override auto-detected county name (e.g., 'Greene')"
    )

    args = parser.parse_args()

    try:
        import_pdf(args.pdf_path, args.full, args.county)
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
