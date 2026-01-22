"""
Party name normalization for NY election data.

Handles common abbreviations and variants, normalizes to canonical forms.
"""

# Map canonical party names to their known aliases
PARTY_ALIASES: dict[str, list[str]] = {
    "democratic": ["dem", "d", "democrat", "democrats"],
    "republican": ["rep", "r", "gop", "republicans"],
    "conservative": ["con", "c", "conservatives"],
    "working families": ["wfp", "wf", "working families party", "working"],
    "independence": ["ind", "i"],
    "green": ["gre", "g", "greens"],
    "libertarian": ["lib", "l", "libertarians"],
    "write-in": ["wri", "w", "write in", "writein"],
    "community 1st": ["community first", "community"],
    "larouche": [],
}

# Map canonical names to display names
CANONICAL_PARTIES: dict[str, str] = {
    "democratic": "Democratic",
    "republican": "Republican",
    "conservative": "Conservative",
    "working families": "Working Families",
    "independence": "Independence",
    "green": "Green",
    "libertarian": "Libertarian",
    "write-in": "Write-In",
    "community 1st": "Community 1st",
    "larouche": "LaRouche",
}


def normalize_party(raw: str) -> str:
    """
    Convert any party variant to canonical name.

    Args:
        raw: Raw party name from election data

    Returns:
        Lowercase canonical form, or original if unknown
    """
    normalized = raw.strip().lower()

    # Check if already canonical
    if normalized in CANONICAL_PARTIES:
        return normalized

    # Check aliases
    for canonical, aliases in PARTY_ALIASES.items():
        if normalized in aliases:
            return canonical

    # Unknown party - return normalized original
    return normalized


def get_display_name(canonical: str) -> str:
    """
    Get proper display name for a canonical party name.

    Args:
        canonical: Lowercase canonical party name

    Returns:
        Display name with proper capitalization
    """
    return CANONICAL_PARTIES.get(canonical.lower(), canonical.title())


def is_known_party(party: str) -> bool:
    """
    Check if a party name is recognized.

    Args:
        party: Party name to check

    Returns:
        True if party is in known parties or aliases
    """
    normalized = party.strip().lower()

    if normalized in CANONICAL_PARTIES:
        return True

    for aliases in PARTY_ALIASES.values():
        if normalized in aliases:
            return True

    return False
