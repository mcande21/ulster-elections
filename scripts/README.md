# Election Data Scripts

## fetch_results.py

Main CLI for fetching and processing Hudson Valley election results.

### Prerequisites

```bash
# Activate backend virtual environment
source backend/venv/bin/activate

# Install dependencies (if not already installed)
pip install requests beautifulsoup4
```

### Usage

```bash
# Fetch all Hudson Valley counties with available sources
python scripts/fetch_results.py --all

# Fetch specific county
python scripts/fetch_results.py --county columbia

# Dry run (show what would be done)
python scripts/fetch_results.py --all --dry-run

# Validate only (skip database load)
python scripts/fetch_results.py --all --validate-only

# Force processing despite validation errors
python scripts/fetch_results.py --county columbia --force

# Specify election date
python scripts/fetch_results.py --county columbia --date 2025-11-04
```

### Available Counties

Counties with configured sources:

- **columbia**: PDF (local) - Standard PDF format
- **dutchess**: PDF (local) - Standard PDF format
- **greene**: PDF (local) - Contest Overview format
- **ulster**: HTML (URL) - Bootstrap HTML format

### Output

Extracted data is saved to `data/raw/{county}_{date}.json`

### Validation

The validator checks for:

- Required fields (race_title, candidate name, total_votes)
- Numeric vote counts
- Non-negative votes
- Duplicate races/candidates
- Party line totals not exceeding candidate totals

Use `--force` to save data despite validation errors.

### Database Loading

The `--load-db` flag is not yet implemented. For now, use the existing `scripts/import_pdf.py` flow.
