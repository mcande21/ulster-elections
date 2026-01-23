# Election Result Parsers

Unified parser system for extracting election results from various county formats.

## Supported Formats

### 1. Standard PDF (Columbia, Dutchess)
- Format: "Vote For N" pattern
- Candidate lines with party breakdown
- Summary stats: Write-in, Total Votes Cast, Under/Over Votes

**Parser:** `StandardPDFParser`

### 2. Contest Overview (Greene)
- Format: Race title with "(Vote for N)"
- Candidate format: "Name (PARTY1, PARTY2) votes percent%"
- Followed by party breakdown

**Parser:** `GreenePDFParser`

### 3. Canvass Narrative (Orange)
- Format: Narrative text from County Board
- Race intro: "the office of [RACE TITLE]"
- Candidate format: "Name Party received votes"
- Multi-party lines as separate entries (fusion voting)

**Parser:** `CanvassPDFParser`

### 4. Precinct Table (Putnam, Westchester)
- Format: Precinct-level tables (districts × candidates)
- Race title in page header
- Column headers with vertical text
- Party affiliations in row below headers
- TOTAL row aggregating all precincts
- Multi-page races (same race across pages)

**Parser:** `PrecinctTableParser`

**Known limitation:** Candidate names may have minor spacing issues due to vertical text extraction (e.g., "KAMALTIA MD. HARRIS" instead of "KAMALA D. HARRIS"). Vote totals are accurate.

### 5. Bootstrap HTML (Ulster)
- Format: HTML with Bootstrap styling
- Race sections with candidate boxes
- Party badges and fusion voting details

**Parser:** `HTMLParser`

## Usage

```python
from extractors.registry import get_county_config
from extractors.parsers import get_parser

# Get county configuration
county_config = get_county_config('putnam', '2024-11-05')

# Get appropriate parser
parser = get_parser(county_config)

# Parse results
results = parser.parse(source, county_config)
```

## Output Format

All parsers return a standardized structure:

```python
{
    "county": str,
    "election_date": str,
    "races": [
        {
            "race_title": str,
            "vote_for": int,
            "candidates": [
                {
                    "name": str,
                    "total_votes": int,
                    "party_lines": [
                        {"party": str, "votes": int},
                        ...
                    ]
                }
            ],
            "write_in": int,
            "total_votes_cast": int,
            "under_votes": int,
            "over_votes": int,
            "total_ballots_cast": int
        }
    ]
}
```

## Registry

County configurations are stored in `extractors/registry.py`. Each county has:
- `name`: Display name
- `format`: Parser type (standard_pdf, contest_overview, canvass, precinct_table, bootstrap_html)
- `source`: File path or URL

Add new counties by registering them in `COUNTIES` dict with appropriate format.

## Testing

Test a parser on a specific PDF:

```bash
python scripts/test_putnam_parser.py
```

This will:
1. Parse the Putnam County PDF
2. Display summary of first 3 races
3. Save full results to `data/raw/putnam_2024-11-05.json`
