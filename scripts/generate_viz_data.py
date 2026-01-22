#!/usr/bin/env python3
"""Generate visualization data from elections database."""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
import psycopg

# Output path
OUTPUT_PATH = Path(__file__).parent.parent / "viz" / "data.js"

def extract_race_type(race_title):
    """Extract race type from title (Supervisor, Council, Legislature, etc.)."""
    race_title_lower = race_title.lower()

    if "supervisor" in race_title_lower:
        return "Supervisor"
    elif "council" in race_title_lower:
        return "Council"
    elif "legislat" in race_title_lower:
        return "Legislature"
    elif "clerk" in race_title_lower:
        return "Clerk"
    elif "highway" in race_title_lower:
        return "Highway"
    elif "justice" in race_title_lower:
        return "Justice"
    elif "tax" in race_title_lower:
        return "Tax Collector"
    else:
        return "Other"

def determine_competitiveness_band(margin_pct):
    """Determine competitiveness band based on margin percentage."""
    if margin_pct < 5:
        return "Thin"
    elif margin_pct < 10:
        return "Lean"
    elif margin_pct < 20:
        return "Likely"
    else:
        return "Safe"

def normalize_party(party_str):
    """Normalize party coalition to D, R, or Other."""
    if not party_str:
        return "Other"

    party_upper = party_str.upper().strip()

    # Database already stores normalized values (D, R, Other)
    # But handle both normalized and raw formats
    if party_upper == "D" or "DEM" in party_upper or "WOR" in party_upper:
        return "D"
    elif party_upper == "R" or "REP" in party_upper or "CON" in party_upper:
        return "R"
    else:
        return "Other"

def generate_data():
    """Query database and generate JavaScript data file."""
    # Load environment from backend/.env
    project_root = Path(__file__).parent.parent
    env_path = project_root / "backend" / ".env"
    load_dotenv(env_path)

    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL not found in backend/.env")

    conn = psycopg.connect(DATABASE_URL)
    cursor = conn.cursor()

    query = """
    SELECT
        r.id,
        r.county,
        r.race_title,
        r.total_votes_cast,
        MAX(CASE WHEN c.is_winner THEN c.total_votes END) as winner_votes,
        MAX(CASE WHEN c.is_winner THEN c.name END) as winner_name,
        MAX(CASE WHEN c.is_winner THEN c.party_coalition END) as winner_party,
        MAX(CASE WHEN NOT c.is_winner THEN c.total_votes END) as runnerup_votes,
        MAX(CASE WHEN NOT c.is_winner THEN c.name END) as runnerup_name,
        MAX(CASE WHEN NOT c.is_winner THEN c.party_coalition END) as runnerup_party
    FROM races r
    JOIN candidates c ON r.id = c.race_id
    GROUP BY r.id
    HAVING winner_votes IS NOT NULL AND runnerup_votes IS NOT NULL
    """

    cursor.execute(query)
    rows = cursor.fetchall()

    races = []
    for row in rows:
        # psycopg returns tuples, not Row objects - unpack manually
        (race_id, county, race_title, total_votes_cast,
         winner_votes, winner_name, winner_party,
         runnerup_votes, runnerup_name, runnerup_party) = row

        total_votes = total_votes_cast or 0
        winner_votes = winner_votes or 0
        runnerup_votes = runnerup_votes or 0

        if total_votes == 0:
            continue

        vote_deficit = winner_votes - runnerup_votes
        margin_pct = (vote_deficit / total_votes) * 100

        race_data = {
            "id": race_id,
            "county": county,
            "race_title": race_title,
            "race_type": extract_race_type(race_title),
            "winner_name": winner_name,
            "winner_party": normalize_party(winner_party),
            "winner_votes": winner_votes,
            "runnerup_name": runnerup_name,
            "runnerup_party": normalize_party(runnerup_party),
            "runnerup_votes": runnerup_votes,
            "total_votes": total_votes,
            "margin_pct": round(margin_pct, 2),
            "vote_deficit": vote_deficit,
            "competitiveness_band": determine_competitiveness_band(margin_pct)
        }

        races.append(race_data)

    conn.close()

    # Sort by margin percentage (most competitive first)
    races.sort(key=lambda x: x["margin_pct"])

    # Extract unique values for filters
    counties = sorted(set(r["county"] for r in races))
    race_types = sorted(set(r["race_type"] for r in races))
    parties = sorted(set(r["winner_party"] for r in races))

    # Build filter options object
    filter_options = {
        "counties": counties,
        "raceTypes": race_types,
        "parties": parties
    }

    # Write JavaScript file with filter options first
    js_content = f"const FILTER_OPTIONS = {json.dumps(filter_options, indent=2)};\n\n"
    js_content += f"const racesData = {json.dumps(races, indent=2)};\n"

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        f.write(js_content)

    print(f"Generated {len(races)} races")
    print(f"Output written to: {OUTPUT_PATH}")

    # Print summary stats
    counties = set(r["county"] for r in races)
    race_types = set(r["race_type"] for r in races)
    print(f"\nCounties: {sorted(counties)}")
    print(f"Race types: {sorted(race_types)}")

    bands = {}
    for race in races:
        band = race["competitiveness_band"]
        bands[band] = bands.get(band, 0) + 1
    print(f"\nCompetitiveness distribution:")
    for band in ["Thin", "Lean", "Likely", "Safe"]:
        print(f"  {band}: {bands.get(band, 0)}")

if __name__ == "__main__":
    generate_data()
