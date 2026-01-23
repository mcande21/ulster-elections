#!/usr/bin/env python3
"""Quick database loader with better error handling."""
import json
import os
from pathlib import Path
from dotenv import load_dotenv
import psycopg
import sys

# Load environment
load_dotenv(Path(__file__).parent.parent / "backend" / ".env")
DATABASE_URL = os.getenv("DATABASE_URL")

# Import from load_db
sys.path.insert(0, str(Path(__file__).parent))
from load_db import create_schema, load_json_file, create_analysis_views, print_summary

def main():
    raw_dir = Path(__file__).parent.parent / "data" / "raw"

    print("Connecting...")
    with psycopg.connect(DATABASE_URL, connect_timeout=10) as conn:
        print("Creating schema...")
        create_schema(conn)

        files = sorted(raw_dir.glob("*.json"))
        print(f"\nFound {len(files)} files to load")

        for i, json_file in enumerate(files, 1):
            print(f"\n[{i}/{len(files)}] Loading {json_file.name}...", end=" ", flush=True)
            try:
                count = load_json_file(conn, json_file)
                print(f"✓ {count} races")
                conn.commit()  # Commit after each file
            except Exception as e:
                print(f"✗ Error: {e}")
                raise

        print("\nCreating views...", end=" ", flush=True)
        create_analysis_views(conn)
        print("✓")

        print("\nSummary:")
        print_summary(conn)

        conn.commit()

    print(f"\n✓ Complete")

if __name__ == "__main__":
    main()
