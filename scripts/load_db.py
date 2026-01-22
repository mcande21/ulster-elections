#!/usr/bin/env python3
"""
Load election data from JSON files into PostgreSQL database with vulnerability scoring.
"""

import json
import os
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv
import psycopg


def create_schema(conn: psycopg.Connection) -> None:
    """Create database schema."""
    cursor = conn.cursor()

    # Drop existing views and tables
    cursor.execute("DROP VIEW IF EXISTS turnout_analysis CASCADE")
    cursor.execute("DROP VIEW IF EXISTS party_performance CASCADE")
    cursor.execute("DROP VIEW IF EXISTS competitive_races CASCADE")
    cursor.execute("DROP TABLE IF EXISTS party_lines CASCADE")
    cursor.execute("DROP TABLE IF EXISTS candidates CASCADE")
    cursor.execute("DROP TABLE IF EXISTS races CASCADE")

    cursor.execute("""
        CREATE TABLE races (
            id SERIAL PRIMARY KEY,
            county TEXT NOT NULL,
            election_date DATE,
            race_title TEXT NOT NULL,
            vote_for INTEGER DEFAULT 1,
            total_votes_cast INTEGER,
            under_votes INTEGER,
            over_votes INTEGER,
            total_ballots_cast INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE candidates (
            id SERIAL PRIMARY KEY,
            race_id INTEGER REFERENCES races(id),
            name TEXT NOT NULL,
            total_votes INTEGER,
            is_winner BOOLEAN DEFAULT FALSE,
            vote_share REAL,
            party_coalition TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE party_lines (
            id SERIAL PRIMARY KEY,
            candidate_id INTEGER REFERENCES candidates(id),
            party TEXT NOT NULL,
            votes INTEGER
        )
    """)

    # Create indexes for faster queries
    cursor.execute("CREATE INDEX idx_candidates_race ON candidates(race_id)")
    cursor.execute("CREATE INDEX idx_party_lines_candidate ON party_lines(candidate_id)")
    cursor.execute("CREATE INDEX idx_races_county ON races(county)")
    cursor.execute("CREATE INDEX idx_candidates_race_winner ON candidates(race_id, is_winner)")

    conn.commit()


def determine_coalition(party_lines: List[Dict]) -> str:
    """Determine party coalition based on party lines."""
    parties = {pl['party'].lower() for pl in party_lines}

    if 'democratic' in parties or 'working families' in parties:
        return 'D'
    elif 'republican' in parties or 'conservative' in parties:
        return 'R'
    else:
        return 'Other'


def load_race(conn: psycopg.Connection, county: str, election_date: str, race_data: Dict) -> None:
    """Load a single race and its candidates into the database."""
    cursor = conn.cursor()

    # Insert race
    cursor.execute("""
        INSERT INTO races (county, election_date, race_title, vote_for, total_votes_cast,
                          under_votes, over_votes, total_ballots_cast)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (
        county,
        election_date,
        race_data['race_title'],
        race_data.get('vote_for', 1),
        race_data.get('total_votes_cast'),
        race_data.get('under_votes'),
        race_data.get('over_votes'),
        race_data.get('total_ballots_cast')
    ))

    race_id = cursor.fetchone()[0]
    total_votes = race_data.get('total_votes_cast', 0)

    # Find winner (highest vote total)
    candidates = race_data.get('candidates', [])
    if candidates:
        # Prefer 'total_votes', fallback to 'total' for backward compatibility
        max_votes = max(c.get('total_votes') or c.get('total', 0) for c in candidates)

        # Load candidates
        for candidate in candidates:
            # Prefer 'total_votes', fallback to 'total' for backward compatibility
            candidate_total = candidate.get('total_votes') or candidate.get('total', 0)
            is_winner = candidate_total == max_votes
            vote_share = candidate_total / total_votes if total_votes > 0 else 0
            party_coalition = determine_coalition(candidate.get('party_lines', []))

            cursor.execute("""
                INSERT INTO candidates (race_id, name, total_votes, is_winner,
                                      vote_share, party_coalition)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                race_id,
                candidate['name'],
                candidate_total,
                is_winner,
                vote_share,
                party_coalition
            ))

            candidate_id = cursor.fetchone()[0]

            # Load party lines
            for party_line in candidate.get('party_lines', []):
                cursor.execute("""
                    INSERT INTO party_lines (candidate_id, party, votes)
                    VALUES (%s, %s, %s)
                """, (
                    candidate_id,
                    party_line['party'],
                    party_line['votes']
                ))

    conn.commit()


def load_json_file(conn: psycopg.Connection, json_path: Path) -> int:
    """Load all races from a JSON file."""
    with open(json_path) as f:
        data = json.load(f)

    county = data['county']
    election_date = data.get('election_date', '2025-11-04')  # Default to 2025 general
    races = data.get('races', [])

    for race in races:
        load_race(conn, county, election_date, race)

    return len(races)


def create_analysis_views(conn: psycopg.Connection) -> None:
    """Create views for vulnerability analysis."""
    cursor = conn.cursor()

    # Competitive races view (margin < 10%)
    cursor.execute("""
        CREATE VIEW competitive_races AS
        WITH race_margins AS (
            SELECT
                r.id,
                r.county,
                r.race_title,
                r.total_votes_cast,
                MAX(CASE WHEN c.is_winner THEN c.total_votes END) as winner_votes,
                MAX(CASE WHEN c.is_winner THEN c.party_coalition END) as winner_party,
                MAX(CASE WHEN NOT c.is_winner THEN c.total_votes END) as runnerup_votes,
                MAX(CASE WHEN NOT c.is_winner THEN c.party_coalition END) as runnerup_party
            FROM races r
            JOIN candidates c ON r.id = c.race_id
            GROUP BY r.id
        )
        SELECT
            id,
            county,
            race_title,
            winner_party,
            runnerup_party,
            winner_votes,
            runnerup_votes,
            ROUND((winner_votes - runnerup_votes) * 100.0 / total_votes_cast, 2) as margin_pct,
            (winner_votes - runnerup_votes) as vote_margin
        FROM race_margins
        WHERE (winner_votes - runnerup_votes) * 100.0 / total_votes_cast < 10
        ORDER BY margin_pct
    """)

    # Party performance summary
    cursor.execute("""
        CREATE VIEW party_performance AS
        SELECT
            r.county,
            c.party_coalition,
            COUNT(*) as races_entered,
            SUM(CASE WHEN c.is_winner THEN 1 ELSE 0 END) as races_won,
            ROUND(SUM(CASE WHEN c.is_winner THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as win_rate,
            SUM(c.total_votes) as total_votes
        FROM candidates c
        JOIN races r ON c.race_id = r.id
        GROUP BY r.county, c.party_coalition
        ORDER BY r.county, races_won DESC
    """)

    # Turnout analysis
    cursor.execute("""
        CREATE VIEW turnout_analysis AS
        SELECT
            county,
            race_title,
            total_ballots_cast,
            total_votes_cast,
            under_votes,
            over_votes,
            ROUND(under_votes * 100.0 / total_ballots_cast, 2) as under_vote_pct,
            ROUND(total_votes_cast * 100.0 / total_ballots_cast, 2) as turnout_pct
        FROM races
        WHERE total_ballots_cast > 0
        ORDER BY under_vote_pct DESC
    """)

    conn.commit()


def print_summary(conn: psycopg.Connection) -> None:
    """Print summary statistics."""
    cursor = conn.cursor()

    print("\n=== Database Summary ===\n")

    # Total counts
    cursor.execute("SELECT COUNT(*) FROM races")
    race_count = cursor.fetchone()[0]
    print(f"Total races: {race_count}")

    cursor.execute("SELECT COUNT(*) FROM candidates")
    candidate_count = cursor.fetchone()[0]
    print(f"Total candidates: {candidate_count}")

    # By county
    print("\n=== Races by County ===")
    cursor.execute("""
        SELECT county, election_date, COUNT(*) as race_count
        FROM races
        GROUP BY county, election_date
        ORDER BY county, election_date
    """)
    for row in cursor.fetchall():
        print(f"{row[0]} ({row[1]}): {row[2]} races")

    # Party performance
    print("\n=== Party Performance ===")
    cursor.execute("""
        SELECT county, party_coalition, races_won, win_rate
        FROM party_performance
        ORDER BY county, races_won DESC
    """)
    for row in cursor.fetchall():
        print(f"{row[0]} - {row[1]}: {row[2]} wins ({row[3]}%)")

    # Competitive races
    print("\n=== Most Competitive Races (< 5% margin) ===")
    cursor.execute("""
        SELECT county, race_title, winner_party, margin_pct, vote_margin
        FROM competitive_races
        WHERE margin_pct < 5
        ORDER BY margin_pct
        LIMIT 10
    """)
    for row in cursor.fetchall():
        print(f"{row[0]} - {row[1]}: {row[2]} won by {row[3]}% ({row[4]} votes)")

    # High undervote races
    print("\n=== High Undervote Races (> 5%) ===")
    cursor.execute("""
        SELECT county, race_title, under_vote_pct
        FROM turnout_analysis
        WHERE under_vote_pct > 5
        ORDER BY under_vote_pct DESC
        LIMIT 10
    """)
    for row in cursor.fetchall():
        print(f"{row[0]} - {row[1]}: {row[2]}% undervote")


def main():
    """Main execution."""
    # Load environment from backend/.env
    project_root = Path(__file__).parent.parent
    env_path = project_root / "backend" / ".env"
    load_dotenv(env_path)

    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL not found in backend/.env")

    # Setup paths
    raw_dir = project_root / "data" / "raw"

    # Connect and create schema
    print(f"Connecting to PostgreSQL...")
    with psycopg.connect(DATABASE_URL) as conn:
        print("Creating database schema...")
        create_schema(conn)

        # Load data files (glob-load all JSON files)
        print("\nLoading data files...")

        for json_file in sorted(raw_dir.glob("*.json")):
            count = load_json_file(conn, json_file)
            print(f"Loaded {count} races from {json_file.name}")

        # Create analysis views
        print("\nCreating analysis views...")
        create_analysis_views(conn)

        # Print summary
        print_summary(conn)

        conn.commit()

    print(f"\n✓ Database loaded successfully")


if __name__ == "__main__":
    main()
