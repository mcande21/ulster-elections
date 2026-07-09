# Westchester County 2024-11-05 Extraction Notes

## PDF Characteristics

- **File**: `data/raw/westchester_2024-11-05.pdf` (688 pages)
- **Format**: Precinct-level tables (similar to Putnam but with differences)
- **Text mirroring**: Candidate names are reversed (SIRRAH = HARRIS)

## Mirroring Fix - ✅ WORKING

Enhanced `pdf_text_fixer.py` with:
- Known election candidate names (HARRIS, TRUMP, WALZ, VANCE, etc.)
- Unusual consonant cluster detection (PM, ZL, CN, TS, etc.)
- Double-letter start detection (LL for JILL, RR for HARRIS, etc.)

### Before/After Example (Page 110):
```
RAW:    SIRRAH, PMURT, ZLAW, ECNAV
FIXED:  HARRIS, TRUMP, WALZ, VANCE
```

## PDF Structure Differences from Putnam

| Feature | Putnam | Westchester |
|---------|--------|-------------|
| Column headers | Vertical text (candidates) | Party abbreviations (DEM, REP) |
| Row 1 | Party codes | Candidate names (with newlines) |
| TOTAL row | Single county-wide aggregate | Multiple organizational totals (Towns, Cities, Yonkers) - appear empty |
| Race title | In extracted text | Positioned outside normal text flow (requires char-level extraction) |
| Pages per race | Few (2-5) | Many (50+ for major races) |

## Parser Adaptations Made

1. **Column header detection**: Auto-detect Westchester vs Putnam format
   - If row 0 has known parties → Westchester
   - Otherwise → Putnam (vertical text)

2. **Mirrored name fixing**: Apply to Westchester candidate names
   - Split by newlines
   - Reverse mirrored words
   - Handle slashes ("/") between name parts

3. **Party aliases**: Added WOR (Working Families), W/I (Write-In)

## Extraction Challenges

1. **Race title extraction**: Titles are positioned outside standard text flow
   - Located at y=93-95 position range
   - Not captured by `extract_text()` default settings
   - Requires character-level inspection

2. **No clean TOTAL rows**: Unlike Putnam, Westchester doesn't have usable aggregated totals
   - Would require summing all precinct rows manually
   - 688 pages × multiple precincts per page = significant processing

3. **Precinct-level granularity**: Data is at precinct level, not county-wide
   - Brian's Boards needs county totals
   - Aggregation required across all precincts

## Recommended Approach

### Option 1: Manual Precinct Aggregation (Long-term)
- Extract all precinct tables
- Sum votes across all precincts per candidate
- Computationally intensive but complete

### Option 2: Use Election Board Summary (Short-term)
- Check if Westchester BOE provides a summary results page/PDF
- Often available separately from precinct-level data
- Would be much cleaner to extract

### Option 3: Alternative Data Source
- NY State Board of Elections may have aggregated data
- OpenElections project might have processed results
- AP election results APIs

## Files Modified

- `scripts/extractors/pdf_text_fixer.py` - Enhanced mirroring detection
- `scripts/extractors/parsers.py` - Westchester format support in PrecinctTableParser
- `scripts/extractors/parties.py` - Added WOR and W/I aliases

## Next Steps

1. Verify if Westchester BOE has summary results PDF
2. If not, implement full precinct aggregation (see `extract_westchester_summary.py` for framework)
3. Consider batch processing with progress persistence for 688 pages

## Test Files Created

- `scripts/check_president_page.py` - Verify mirroring fix
- `scripts/debug_mirror_detection.py` - Test heuristics
- `scripts/test_column_parsing.py` - Verify column header parsing
- `scripts/extract_westchester_summary.py` - Aggregation framework (incomplete)
