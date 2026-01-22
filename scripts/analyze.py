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

import sqlite3
import csv
from pathlib import Path
from typing import List, Dict, Tuple


def connect_db(db_path: str) -> sqlite3.Connection:
    """Connect to the elections database."""
    return sqlite3.connect(db_path)


def get_flip_opportunities(conn: sqlite3.Connection) -> List[Dict]:
    """
    Find R-held seats where Democrats came within 10%.
    These represent the best opportunities to flip in 2026.
    """
    query = """
    SELECT
        county,
        race_title,
        winner_name,
        winner_votes,
        runner_up_name,
        runner_up_votes,
        margin_of_victory,
        total_votes_cast
    FROM (
        SELECT
            r.county,
            r.race_title,
            r.total_votes_cast,
            w.name as winner_name,
            w.total_votes as winner_votes,
            w.party_coalition as winner_coalition,
            w.vote_share * 100 as winner_pct,
            ru.name as runner_up_name,
            ru.total_votes as runner_up_votes,
            ru.party_coalition as runner_up_coalition,
            ru.vote_share * 100 as runner_up_pct,
            (w.vote_share - COALESCE(ru.vote_share, 0)) * 100 as margin_of_victory
        FROM races r
        JOIN candidates w ON w.race_id = r.id AND w.is_winner = 1
        LEFT JOIN candidates ru ON ru.race_id = r.id AND ru.is_winner = 0
            AND ru.total_votes = (
                SELECT MAX(total_votes)
                FROM candidates
                WHERE race_id = r.id AND is_winner = 0
            )
    )
    WHERE winner_coalition = 'R'
      AND runner_up_coalition = 'D'
      AND margin_of_victory < 10
    ORDER BY margin_of_victory ASC;
    """

    cursor = conn.cursor()
    cursor.execute(query)

    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_retention_risks(conn: sqlite3.Connection) -> List[Dict]:
    """
    Find D-held seats where Republicans came within 10%.
    These represent the seats Democrats must defend in 2026.
    """
    query = """
    SELECT
        county,
        race_title,
        winner_name,
        winner_votes,
        runner_up_name,
        runner_up_votes,
        margin_of_victory,
        total_votes_cast
    FROM (
        SELECT
            r.county,
            r.race_title,
            r.total_votes_cast,
            w.name as winner_name,
            w.total_votes as winner_votes,
            w.party_coalition as winner_coalition,
            w.vote_share * 100 as winner_pct,
            ru.name as runner_up_name,
            ru.total_votes as runner_up_votes,
            ru.party_coalition as runner_up_coalition,
            ru.vote_share * 100 as runner_up_pct,
            (w.vote_share - COALESCE(ru.vote_share, 0)) * 100 as margin_of_victory
        FROM races r
        JOIN candidates w ON w.race_id = r.id AND w.is_winner = 1
        LEFT JOIN candidates ru ON ru.race_id = r.id AND ru.is_winner = 0
            AND ru.total_votes = (
                SELECT MAX(total_votes)
                FROM candidates
                WHERE race_id = r.id AND is_winner = 0
            )
    )
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
    # Paths
    db_path = "data/normalized/elections.db"
    output_dir = "data/analysis"

    # Connect to database
    conn = connect_db(db_path)

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
