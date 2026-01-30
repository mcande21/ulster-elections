#!/usr/bin/env python3
"""
Vulnerability Analysis for Ulster County 2024 Elections

Answers two strategic questions:
1. Which R-held seats are most opportunistic for Democrats to flip in 2026?
2. Which D-held seats will be hardest for Democrats to retain in 2026?

Outputs three CSV reports to data/analysis/:
- flip_opportunities.csv: R-held seats where D came within 10%
- retention_risks.csv: D-held seats where R came within 10%
- full_vulnerability_report.csv: Combined analysis
"""

import csv
import os
from pathlib import Path
from typing import List, Dict

from dotenv import load_dotenv
import psycopg


def connect_db(database_url: str) -> psycopg.Connection:
    """Connect to the elections database."""
    return psycopg.connect(database_url)


def get_flip_opportunities(conn: psycopg.Connection) -> List[Dict]:
    """
    Find R-held seats where Democrats came within 10%.
    These represent the best opportunities to flip in 2026.
    Uses ranked candidates to support multi-winner races.
    """
    query = """
    WITH ranked_candidates AS (
        SELECT
            c.*,
            r.vote_for,
            r.county,
            r.race_title,
            r.total_votes_cast,
            ROW_NUMBER() OVER (PARTITION BY c.race_id ORDER BY c.total_votes DESC) as rank
        FROM candidates c
        JOIN races r ON c.race_id = r.id
    ),
    race_analysis AS (
        SELECT
            rc_winner.county,
            rc_winner.race_title,
            rc_winner.total_votes_cast,
            rc_winner.name as winner_name,
            rc_winner.total_votes as winner_votes,
            rc_winner.party_coalition as winner_coalition,
            rc_winner.vote_share * 100 as winner_pct,
            rc_loser.name as runner_up_name,
            rc_loser.total_votes as runner_up_votes,
            rc_loser.party_coalition as runner_up_coalition,
            rc_loser.vote_share * 100 as runner_up_pct,
            (rc_winner.vote_share - COALESCE(rc_loser.vote_share, 0)) * 100 as margin_of_victory
        FROM ranked_candidates rc_winner
        LEFT JOIN ranked_candidates rc_loser
            ON rc_winner.race_id = rc_loser.race_id
            AND rc_loser.rank = rc_winner.vote_for + 1
        WHERE rc_winner.rank = rc_winner.vote_for
    )
    SELECT
        county,
        race_title,
        winner_name,
        winner_votes,
        runner_up_name,
        runner_up_votes,
        margin_of_victory,
        total_votes_cast
    FROM race_analysis
    WHERE winner_coalition = 'R'
      AND runner_up_coalition = 'D'
      AND margin_of_victory < 10
    ORDER BY margin_of_victory ASC;
    """

    cursor = conn.cursor()
    cursor.execute(query)

    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_retention_risks(conn: psycopg.Connection) -> List[Dict]:
    """
    Find D-held seats where Republicans came within 10%.
    These represent the seats Democrats must defend in 2026.
    Uses ranked candidates to support multi-winner races.
    """
    query = """
    WITH ranked_candidates AS (
        SELECT
            c.*,
            r.vote_for,
            r.county,
            r.race_title,
            r.total_votes_cast,
            ROW_NUMBER() OVER (PARTITION BY c.race_id ORDER BY c.total_votes DESC) as rank
        FROM candidates c
        JOIN races r ON c.race_id = r.id
    ),
    race_analysis AS (
        SELECT
            rc_winner.county,
            rc_winner.race_title,
            rc_winner.total_votes_cast,
            rc_winner.name as winner_name,
            rc_winner.total_votes as winner_votes,
            rc_winner.party_coalition as winner_coalition,
            rc_winner.vote_share * 100 as winner_pct,
            rc_loser.name as runner_up_name,
            rc_loser.total_votes as runner_up_votes,
            rc_loser.party_coalition as runner_up_coalition,
            rc_loser.vote_share * 100 as runner_up_pct,
            (rc_winner.vote_share - COALESCE(rc_loser.vote_share, 0)) * 100 as margin_of_victory
        FROM ranked_candidates rc_winner
        LEFT JOIN ranked_candidates rc_loser
            ON rc_winner.race_id = rc_loser.race_id
            AND rc_loser.rank = rc_winner.vote_for + 1
        WHERE rc_winner.rank = rc_winner.vote_for
    )
    SELECT
        county,
        race_title,
        winner_name,
        winner_votes,
        runner_up_name,
        runner_up_votes,
        margin_of_victory,
        total_votes_cast
    FROM race_analysis
    WHERE winner_coalition = 'D'
      AND runner_up_coalition = 'R'
      AND margin_of_victory < 10
    ORDER BY margin_of_victory ASC;
    """

    cursor = conn.cursor()
    cursor.execute(query)

    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def write_csv(data: List[Dict], output_path: str, headers: List[str]) -> None:
    """Write analysis results to CSV."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data)


def print_summary(flip_opps: List[Dict], retention_risks: List[Dict]) -> None:
    """Print executive summary to console."""
    print("=" * 80)
    print("VULNERABILITY ANALYSIS - ULSTER COUNTY 2024 ELECTIONS")
    print("=" * 80)
    print()

    print(f"FLIP OPPORTUNITIES: {len(flip_opps)} R-held seats where D came within 10%")
    print("-" * 80)
    if flip_opps:
        for i, race in enumerate(flip_opps[:5], 1):  # Top 5
            print(f"{i}. {race['race_title']} ({race['county']})")
            print(f"   Winner: {race['winner_name']} (R) - {race['winner_votes']:,} votes")
            print(f"   Runner-up: {race['runner_up_name']} (D) - {race['runner_up_votes']:,} votes")
            print(f"   Margin: {race['margin_of_victory']:.2f}%")
            print()
        if len(flip_opps) > 5:
            print(f"   ... and {len(flip_opps) - 5} more")
            print()
    else:
        print("   No R-held seats within 10%")
        print()

    print(f"RETENTION RISKS: {len(retention_risks)} D-held seats where R came within 10%")
    print("-" * 80)
    if retention_risks:
        for i, race in enumerate(retention_risks[:5], 1):  # Top 5
            print(f"{i}. {race['race_title']} ({race['county']})")
            print(f"   Winner: {race['winner_name']} (D) - {race['winner_votes']:,} votes")
            print(f"   Runner-up: {race['runner_up_name']} (R) - {race['runner_up_votes']:,} votes")
            print(f"   Margin: {race['margin_of_victory']:.2f}%")
            print()
        if len(retention_risks) > 5:
            print(f"   ... and {len(retention_risks) - 5} more")
            print()
    else:
        print("   No D-held seats within 10%")
        print()

    print("=" * 80)
    print(f"TOTAL VULNERABLE SEATS: {len(flip_opps) + len(retention_risks)}")
    print("=" * 80)


def main():
    """Run vulnerability analysis and generate reports."""
    # Load environment from backend/.env
    project_root = Path(__file__).parent.parent
    env_path = project_root / "backend" / ".env"
    load_dotenv(env_path)

    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL not found in backend/.env")

    output_dir = "data/analysis"

    # Connect to database
    conn = connect_db(DATABASE_URL)

    try:
        # Run analyses
        print("Analyzing flip opportunities (R-held seats)...")
        flip_opps = get_flip_opportunities(conn)

        print("Analyzing retention risks (D-held seats)...")
        retention_risks = get_retention_risks(conn)

        # Define CSV headers
        headers = [
            'county',
            'race_title',
            'winner_name',
            'winner_votes',
            'runner_up_name',
            'runner_up_votes',
            'margin_of_victory',
            'total_votes_cast'
        ]

        # Write reports
        print("Writing flip_opportunities.csv...")
        write_csv(flip_opps, f"{output_dir}/flip_opportunities.csv", headers)

        print("Writing retention_risks.csv...")
        write_csv(retention_risks, f"{output_dir}/retention_risks.csv", headers)

        # Combined report
        print("Writing full_vulnerability_report.csv...")
        combined = []
        for race in flip_opps:
            race['category'] = 'FLIP_OPPORTUNITY'
            combined.append(race)
        for race in retention_risks:
            race['category'] = 'RETENTION_RISK'
            combined.append(race)

        combined_headers = ['category'] + headers
        write_csv(combined, f"{output_dir}/full_vulnerability_report.csv", combined_headers)

        # Print summary
        print()
        print_summary(flip_opps, retention_risks)

        print()
        print(f"Reports written to {output_dir}/")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
