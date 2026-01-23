# Enhanced Voting Data Extraction

This document explains how to extract election data from the Enhanced Voting portal.

## Overview

Enhanced Voting provides a public API for election results at URLs like:
- `https://app.enhancedvoting.com/results/public/{county-slug}/{election-code}`

## API Endpoints

The data API follows this pattern:
```
https://app.enhancedvoting.com/results/public/api/elections/{county-slug}/{election-code}/data
```

### County Slugs (Hudson Valley)
- `orange-county-ny`
- `putnam-county-ny`
- `rockland-county-ny`
- `sullivan-county-ny`
- `dutchess-county-ny`
- `ulster-county-ny`

### Election Codes
- `GE25` - General Election 2025
- `GE24` - General Election 2024
- `PE25` - Primary Election 2025

## Extraction Process

### 1. Download Raw Data

```bash
curl -s 'https://app.enhancedvoting.com/results/public/api/elections/putnam-county-ny/GE25/data' \
  > data/raw/putnam_2025_raw_enhanced.json
```

### 2. Parse to Standard Format

```bash
python3 scripts/parse_enhanced_voting.py \
  data/raw/putnam_2025_raw_enhanced.json \
  data/raw/putnam_2025.json
```

### 3. Load into Database

```bash
python3 scripts/load_db.py data/raw/putnam_2025.json
```

## Data Structure

### Enhanced Voting API Response

```json
{
  "jurisdiction": {...},
  "election": {
    "electionDate": "2025-11-04T00:00:00",
    ...
  },
  "ballotItems": [
    {
      "name": [{"languageId": "en", "text": "Race Title"}],
      "contestType": "Candidate",
      "summaryResults": {
        "ballotOptions": [
          {
            "name": [{"languageId": "en", "text": "Candidate Name"}],
            "voteCount": 12345,
            "party": {
              "name": [{"languageId": "en", "text": "Democratic"}],
              "abbreviation": "DEM"
            }
          }
        ]
      }
    }
  ]
}
```

### Our Standard Format

```json
{
  "county": "Putnam",
  "election_date": "2025-11-04",
  "races": [
    {
      "title": "Race Title",
      "candidates": [
        {
          "name": "Candidate Name",
          "party_lines": [
            {"party": "Democratic", "votes": 12345}
          ],
          "total": 12345
        }
      ]
    }
  ]
}
```

## 2025 Data Extracted

| County | Races | Election Date | Source |
|--------|-------|---------------|--------|
| Orange | 149 | 2025-11-04 | Enhanced Voting API |
| Putnam | 30 | 2025-11-04 | Enhanced Voting API |
| Rockland | 42 | 2025-11-04 | Enhanced Voting API |
| Sullivan | 79 | 2025-11-04 | Enhanced Voting API |

## Notes

- The API returns cross-endorsed candidates with separate entries per party line
- The parser automatically groups these by candidate name and sums totals
- Write-in candidates appear with party "Unknown"
- Only processes `contestType: "Candidate"` items (skips referendums/propositions)
