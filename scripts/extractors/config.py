"""County-specific configuration for PDF extractors."""

from pathlib import Path
from typing import Any

COUNTY_CONFIGS: dict[str, dict[str, Any]] = {
    "columbia": {
        "county_name": "Columbia",
        "election_date": "2025-11-04",
        "input_pdf": "data/Summary Results with Candidate Totals_41b03cbb-9244-4b14-b023-a0fdb76110d9.PDF",
        "output_json": "data/raw/columbia_2025.json",
        "local_parties": [
            "The Harmony Party",
            "Future Hudson",
            "Hudson United",
            "Chatham For All",
            "Chatham Neighbors Party",
            "Do Something",
            "Connect Ghent",
            "Clermont Friends",
            "Grounded Vision",
            "Hillsdale Unity Party",
            "Kinderhook Community Party",
        ],
        # Greene format uses different patterns
        "greene_format": False,
    },
    "dutchess": {
        "county_name": "Dutchess",
        "election_date": "2025-11-04",
        "input_pdf": "data/dutchess-2025-results.pdf",
        "output_json": "data/raw/dutchess_2025.json",
        "local_parties": [
            "Non- Partisan",
            "Nonpartisan",
            "Petition",
            "Pawling Values",
            "PK's Choice",
        ],
        "greene_format": False,
    },
    "greene": {
        "county_name": "Greene",
        "election_date": "2025-11-04",
        "input_pdf": "data/Official-GE25.pdf",
        "output_json": "data/raw/greene_2025.json",
        "local_parties": [],
        # Greene uses different format with party abbreviations
        "greene_format": True,
    },
}

# Standard parties common to all counties
STANDARD_PARTIES = [
    "Democratic",
    "Republican",
    "Conservative",
    "Working Families",
    "Independence",
    "Liberal",
    "Green",
    "Libertarian",
    "Reform",
]

# Greene-specific party abbreviations
GREENE_PARTY_MAP = {
    "DEM": "Democratic",
    "REP": "Republican",
    "CON": "Conservative",
    "WFP": "Working Families",
    "IND": "Independence",
    "OA": "OA",
    "OT": "OT",
    "HR": "HR",
}
