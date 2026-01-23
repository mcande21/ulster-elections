#!/usr/bin/env python3
"""
Main CLI entry point for fetching and processing Hudson Valley election results.

Orchestrates the full pipeline:
1. Get counties to process (registry lookup)
2. Fetch or locate source data (HTML/PDF)
3. Parse results using format-specific parsers
4. Validate extracted data
5. Save to JSON
6. Optionally load to database

Usage:
    # Fetch all Hudson Valley counties
    python scripts/fetch_results.py --all

    # Fetch specific county
    python scripts/fetch_results.py --county ulster

    # Fetch and load to database
    python scripts/fetch_results.py --all --load-db

    # Validate only (no database load)
    python scripts/fetch_results.py --all --validate-only

    # Dry run (show what would be done)
    python scripts/fetch_results.py --all --dry-run

    # Specify election date
    python scripts/fetch_results.py --county ulster --date 2025-11-04
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.extractors.registry import get_county, list_counties, CountyConfig
from scripts.extractors.parsers import get_parser
from scripts.extractors.validators import validate_extraction


def fetch_source(county_config: CountyConfig, dry_run: bool = False) -> Optional[str]:
    """
    Get source data for a county.

    For HTML: returns URL directly
    For PDF with URL: downloads and returns local path
    For PDF with local_pdf: returns local path

    Args:
        county_config: County configuration from registry
        dry_run: If True, skip actual downloads

    Returns:
        Source identifier (URL or file path), or None if unavailable
    """
    source_type = county_config["source_type"]
    results_url = county_config.get("results_url")
    local_pdf = county_config.get("local_pdf")

    if source_type == "html":
        if results_url:
            return results_url
        print(f"  ⚠️  No URL configured for HTML source")
        return None

    elif source_type == "pdf":
        # Prefer local PDF if available
        if local_pdf:
            pdf_path = Path(local_pdf)
            if pdf_path.exists():
                return str(pdf_path)
            print(f"  ⚠️  Local PDF not found: {local_pdf}")
            return None

        # Try downloading from URL
        if results_url:
            if dry_run:
                print(f"  [DRY RUN] Would download PDF from {results_url}")
                return results_url

            county_name = county_config["name"].lower()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = Path(f"data/{county_name}_{timestamp}.pdf")
            output_path.parent.mkdir(parents=True, exist_ok=True)

            print(f"  📥 Downloading PDF from {results_url}...")
            try:
                response = requests.get(results_url, timeout=30)
                response.raise_for_status()

                output_path.write_bytes(response.content)
                print(f"  ✓ Saved to {output_path}")
                return str(output_path)

            except requests.RequestException as e:
                print(f"  ✗ Download failed: {e}")
                return None

        print(f"  ⚠️  No source available (no URL or local PDF)")
        return None

    print(f"  ⚠️  Unknown source type: {source_type}")
    return None


def process_county(
    county_id: str,
    election_date: str,
    dry_run: bool = False,
    validate_only: bool = False,
    load_db: bool = False,
    force: bool = False
) -> bool:
    """
    Process a single county.

    Args:
        county_id: County identifier
        election_date: Election date (YYYY-MM-DD)
        dry_run: If True, show what would be done without executing
        validate_only: If True, validate but don't save to database
        load_db: If True, load validated data to database
        force: If True, continue despite validation errors

    Returns:
        True if processing succeeded, False otherwise
    """
    print(f"\n{'='*60}")
    print(f"Processing: {county_id}")
    print(f"{'='*60}")

    try:
        # Get county configuration
        county_config = get_county(county_id)
        county_config["election_date"] = election_date

        print(f"County: {county_config['name']}")
        print(f"Source type: {county_config['source_type']}")
        print(f"Format: {county_config['format']}")

        # Determine source
        source = fetch_source(county_config, dry_run=dry_run)
        if not source:
            print(f"✗ Failed: No source available")
            return False

        if dry_run:
            print(f"[DRY RUN] Would process source: {source}")
            return True

        print(f"Source: {source}")

        # Get appropriate parser
        parser = get_parser(county_config)
        print(f"Parser: {parser.__class__.__name__}")

        # Parse results
        print("Parsing results...")
        results = parser.parse(source, county_config)

        race_count = len(results.get("races", []))
        candidate_count = sum(
            len(race.get("candidates", []))
            for race in results.get("races", [])
        )
        print(f"✓ Extracted {race_count} races, {candidate_count} candidates")

        # Validate extraction
        print("Validating extraction...")
        issues = validate_extraction(results)

        if issues:
            print(f"\n⚠️  Found {len(issues)} validation issues:")
            for issue in issues[:10]:  # Show first 10
                print(f"  - {issue}")
            if len(issues) > 10:
                print(f"  ... and {len(issues) - 10} more")

            if not force:
                print("✗ Failed: Validation errors (use --force to override)")
                return False
            else:
                print("⚠️  Continuing with validation errors (--force)")
        else:
            print("✓ Validation passed")

        # Save to JSON
        output_path = Path(f"data/raw/{county_id}_{election_date}.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"✓ Saved to {output_path}")

        # Load to database if requested
        if load_db and not validate_only:
            print("Loading to database...")
            # TODO: Implement database loader
            # from scripts.import_pdf import load_to_database
            # load_to_database(results)
            print("⚠️  Database loader not yet implemented")

        print(f"✓ Success: {county_id}")
        return True

    except KeyError:
        print(f"✗ Failed: County '{county_id}' not found in registry")
        return False

    except FileNotFoundError as e:
        print(f"✗ Failed: {e}")
        return False

    except Exception as e:
        print(f"✗ Failed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Fetch and process Hudson Valley election results",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch all counties
  %(prog)s --all

  # Fetch specific county
  %(prog)s --county ulster

  # Fetch and load to database
  %(prog)s --all --load-db

  # Validate only
  %(prog)s --all --validate-only

  # Dry run
  %(prog)s --all --dry-run
        """
    )

    # County selection
    county_group = parser.add_mutually_exclusive_group(required=True)
    county_group.add_argument(
        "--all",
        action="store_true",
        help="Process all Hudson Valley counties"
    )
    county_group.add_argument(
        "--county",
        type=str,
        help="Process specific county (e.g., 'ulster', 'columbia')"
    )

    # Options
    parser.add_argument(
        "--date",
        type=str,
        help="Election date (YYYY-MM-DD). Default: auto-detect or 2025-11-04"
    )
    parser.add_argument(
        "--load-db",
        action="store_true",
        help="Load validated data to database"
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate extraction without loading to database"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without executing"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Continue processing despite validation errors"
    )

    args = parser.parse_args()

    # Determine election date
    election_date = args.date or "2025-11-04"

    # Get counties to process
    if args.all:
        # Filter to counties with known sources
        all_counties = list_counties()
        counties = []
        for county_id in all_counties:
            config = get_county(county_id)
            if config.get("results_url") or config.get("local_pdf"):
                counties.append(county_id)
        print(f"Processing {len(counties)} counties with available sources")
    else:
        counties = [args.county]

    # Process each county
    results = {
        "succeeded": [],
        "failed": [],
        "skipped": []
    }

    for county_id in counties:
        success = process_county(
            county_id,
            election_date=election_date,
            dry_run=args.dry_run,
            validate_only=args.validate_only,
            load_db=args.load_db,
            force=args.force
        )

        if success:
            results["succeeded"].append(county_id)
        else:
            results["failed"].append(county_id)

    # Print summary
    print(f"\n{'='*60}")
    print("Summary")
    print(f"{'='*60}")
    print(f"✓ Succeeded: {len(results['succeeded'])}")
    if results["succeeded"]:
        for county in results["succeeded"]:
            print(f"  - {county}")

    print(f"\n✗ Failed: {len(results['failed'])}")
    if results["failed"]:
        for county in results["failed"]:
            print(f"  - {county}")

    print(f"\n⊘ Skipped: {len(results['skipped'])}")
    if results["skipped"]:
        for county in results["skipped"]:
            print(f"  - {county}")

    # Exit code
    if results["failed"]:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
