"""
County registry for Hudson Valley election data.

Centralizes configuration for all counties in the region, including
source types (HTML/PDF), URLs, local paths, and format identifiers.
"""

from typing import TypedDict, Optional, Literal


class CountyConfig(TypedDict):
    """Configuration for a single county's election data."""
    name: str
    source_type: Literal["html", "pdf"]
    results_url: Optional[str]
    local_pdf: Optional[str]
    format: str


HUDSON_VALLEY_COUNTIES: dict[str, CountyConfig] = {
    # Known counties with extractors
    "ulster": {
        "name": "Ulster",
        "source_type": "html",
        "results_url": "https://elections.ulstercountyny.gov/election-results/2025-11-05-official.html",
        "local_pdf": None,
        "format": "bootstrap_html"
    },
    "columbia": {
        "name": "Columbia",
        "source_type": "pdf",
        "results_url": None,  # Manual download
        "local_pdf": "data/Summary Results with Candidate Totals_41b03cbb-9244-4b14-b023-a0fdb76110d9.PDF",
        "format": "standard_pdf"
    },
    "dutchess": {
        "name": "Dutchess",
        "source_type": "pdf",
        "results_url": None,  # Manual download
        "local_pdf": "data/dutchess-2025-results.pdf",
        "format": "standard_pdf"
    },
    "greene": {
        "name": "Greene",
        "source_type": "pdf",
        "results_url": None,  # Manual download
        "local_pdf": "data/Official-GE25.pdf",
        "format": "contest_overview"
    },

    # Future counties (placeholders)
    "orange": {
        "name": "Orange",
        "source_type": "pdf",
        "results_url": "https://www.orangecountygov.com/DocumentCenter/View/32244",
        "local_pdf": "data/raw/orange_2024-11-05.pdf",
        "format": "canvass"
    },
    "sullivan": {
        "name": "Sullivan",
        "source_type": "pdf",
        "results_url": None,
        "local_pdf": None,
        "format": "unknown"
    },
    "putnam": {
        "name": "Putnam",
        "source_type": "pdf",
        "results_url": "http://boe.putnamcountyny.gov/wp-content/uploads/2024/12/2024-GENERAL-ELECTION-RESULTS-CERTIFIED-WEBSITE.pdf",
        "local_pdf": None,
        "format": "standard"
    },
    "rockland": {
        "name": "Rockland",
        "source_type": "pdf",
        "results_url": None,
        "local_pdf": None,
        "format": "unknown"
    },
    "westchester": {
        "name": "Westchester",
        "source_type": "pdf",
        "results_url": "https://citizenparticipation.westchestergov.com/images/stories/pdfs/2024/canvass-general-241105.pdf",
        "local_pdf": None,
        "format": "canvass"
    },
    "albany": {
        "name": "Albany",
        "source_type": "pdf",
        "results_url": None,
        "local_pdf": None,
        "format": "unknown"
    }
}


def get_county(county_id: str) -> CountyConfig:
    """
    Get county config by ID.

    Args:
        county_id: County identifier (lowercase, e.g., "ulster", "columbia")

    Returns:
        CountyConfig for the specified county

    Raises:
        KeyError: If county_id is not registered
    """
    return HUDSON_VALLEY_COUNTIES[county_id]


def list_counties() -> list[str]:
    """
    List all registered county IDs.

    Returns:
        List of county IDs in alphabetical order
    """
    return sorted(HUDSON_VALLEY_COUNTIES.keys())
