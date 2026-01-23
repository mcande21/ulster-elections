"""
Data quality validation for extracted election results.

Validates extraction output before database load to catch common data quality issues.
"""

from typing import List, Dict, Any


def validate_extraction(data: Dict[str, Any]) -> List[str]:
    """
    Validate extracted election data.

    Args:
        data: Dict with "races" list, each race has "race_title", "candidates" list
              Each candidate has "name", "total_votes", optional "party_lines" list

    Returns:
        List of validation issues (empty if valid)
    """
    issues = []

    if not isinstance(data, dict):
        issues.append("Data must be a dictionary")
        return issues

    if "races" not in data:
        issues.append("Missing 'races' key in data")
        return issues

    races = data["races"]
    if not isinstance(races, list):
        issues.append("'races' must be a list")
        return issues

    if not races:
        issues.append("No races found in data")
        return issues

    # Track race titles to detect duplicates
    race_titles = set()

    for i, race in enumerate(races):
        race_issues = validate_race(race)
        for issue in race_issues:
            issues.append(f"Race {i}: {issue}")

        # Check for duplicate race titles
        race_title = race.get("race_title", "")
        if race_title in race_titles:
            issues.append(f"Race {i}: Duplicate race title '{race_title}'")
        race_titles.add(race_title)

    return issues


def validate_race(race: Dict[str, Any]) -> List[str]:
    """Validate a single race entry."""
    issues = []

    if not isinstance(race, dict):
        issues.append("Race must be a dictionary")
        return issues

    # Check required fields
    if "race_title" not in race or not race["race_title"]:
        issues.append("Missing or empty 'race_title'")

    if "candidates" not in race:
        issues.append("Missing 'candidates' list")
        return issues

    candidates = race["candidates"]
    if not isinstance(candidates, list):
        issues.append("'candidates' must be a list")
        return issues

    if not candidates:
        issues.append(f"No candidates in race '{race.get('race_title', 'unknown')}'")
        return issues

    # Track candidate names to detect duplicates
    candidate_names = set()
    race_title = race.get("race_title", "unknown")

    for candidate in candidates:
        candidate_issues = validate_candidate(candidate, race_title)
        issues.extend(candidate_issues)

        # Check for duplicate candidates
        candidate_name = candidate.get("name", "")
        if candidate_name in candidate_names:
            issues.append(f"Duplicate candidate '{candidate_name}'")
        candidate_names.add(candidate_name)

    return issues


def validate_candidate(candidate: Dict[str, Any], race_title: str) -> List[str]:
    """Validate a single candidate entry."""
    issues = []

    if not isinstance(candidate, dict):
        issues.append(f"Candidate in race '{race_title}' must be a dictionary")
        return issues

    # Check required fields
    if "name" not in candidate or not candidate["name"]:
        issues.append(f"Candidate in race '{race_title}' missing or empty 'name'")

    candidate_name = candidate.get("name", "unknown")

    if "total_votes" not in candidate:
        issues.append(f"Candidate '{candidate_name}' missing 'total_votes'")
        return issues

    total_votes = candidate["total_votes"]

    # Validate vote counts
    if not isinstance(total_votes, (int, float)):
        issues.append(f"Candidate '{candidate_name}' total_votes must be numeric")
        return issues

    if total_votes < 0:
        issues.append(f"Candidate '{candidate_name}' has negative votes: {total_votes}")

    # Validate party lines if present
    if "party_lines" in candidate:
        party_lines = candidate["party_lines"]
        if not isinstance(party_lines, list):
            issues.append(f"Candidate '{candidate_name}' party_lines must be a list")
        else:
            party_line_total = 0
            party_names = set()

            for party_line in party_lines:
                if not isinstance(party_line, dict):
                    issues.append(f"Candidate '{candidate_name}' party line must be a dictionary")
                    continue

                if "party" not in party_line or not party_line["party"]:
                    issues.append(f"Candidate '{candidate_name}' party line missing 'party'")

                if "votes" not in party_line:
                    issues.append(f"Candidate '{candidate_name}' party line missing 'votes'")
                    continue

                party_name = party_line.get("party", "unknown")
                votes = party_line["votes"]

                # Check for duplicate party lines
                if party_name in party_names:
                    issues.append(
                        f"Candidate '{candidate_name}' has duplicate party line '{party_name}'"
                    )
                party_names.add(party_name)

                if not isinstance(votes, (int, float)):
                    issues.append(
                        f"Candidate '{candidate_name}' party line '{party_name}' votes must be numeric"
                    )
                    continue

                if votes < 0:
                    issues.append(
                        f"Candidate '{candidate_name}' party line '{party_name}' has negative votes: {votes}"
                    )

                party_line_total += votes

            # Party line votes should not exceed candidate total
            if party_line_total > total_votes:
                issues.append(
                    f"Candidate '{candidate_name}' party line total ({party_line_total}) "
                    f"exceeds candidate total ({total_votes})"
                )

    return issues
