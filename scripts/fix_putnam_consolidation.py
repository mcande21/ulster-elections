#!/usr/bin/env python3
"""
Consolidate duplicate candidate entries in Putnam data.

Candidates with multiple party lines appear as separate entries.
This script merges them by candidate name within each race.
"""

import json
from pathlib import Path

def consolidate_candidates(candidates):
    """Consolidate duplicate candidates by merging party_lines and summing votes."""
    consolidated = {}

    for candidate in candidates:
        name = candidate["name"]

        if name not in consolidated:
            # First occurrence - initialize
            consolidated[name] = {
                "name": name,
                "party_lines": [],
                "total": 0
            }

        # Merge party_lines
        consolidated[name]["party_lines"].extend(candidate["party_lines"])

        # Sum total votes (handle both "total" and "total_votes" keys)
        total_key = "total" if "total" in candidate else "total_votes"
        consolidated[name]["total"] += candidate.get(total_key, 0)

    return list(consolidated.values())

def fix_putnam_data(input_path, output_path):
    """Read Putnam data, consolidate candidates, write back."""
    with open(input_path, 'r') as f:
        data = json.load(f)

    # Process each race
    for race in data["races"]:
        race["candidates"] = consolidate_candidates(race["candidates"])

    # Write back
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"✓ Consolidated {input_path}")
    print(f"✓ Saved to {output_path}")

if __name__ == "__main__":
    putnam_path = Path(__file__).parent.parent / "data/raw/putnam_2024-11-05.json"
    fix_putnam_data(putnam_path, putnam_path)
