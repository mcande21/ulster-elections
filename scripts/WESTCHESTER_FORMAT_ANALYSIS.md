# Westchester PDF Format Analysis

**PDF:** `westchester_2024-11-05.pdf` (688 pages)
**Date Analyzed:** 2026-01-22

## Executive Summary

**Format Type:** Precinct-table format (similar to Putnam)

**Complexity:** Moderate - Same structure as Putnam but with extensive text mirroring issues

**Recommended Approach:** Reuse Putnam parser with enhanced text mirroring fixes

---

## Format Structure

### Overall Organization

The Westchester PDF follows a **precinct-table format** nearly identical to Putnam County:

1. **Index pages** (pages 1-2): Table of contents with race names and page ranges
2. **Race sections**: Each race gets a page range with precinct-level data
3. **Precinct rows**: One row per precinct with vote counts across party columns
4. **Totals**: Summary row at bottom of each page/section

### Page Layout

Each race page contains:

```
[Race Title Header]                           [Page # OF 688]

[Party Line Headers]                          (e.g., DEM REP CON WOR W/I...)
[Candidate Names - MIRRORED & VERTICAL]       (one name per line, reversed)
CANVASS
TOTAL
VOID-
BLANK
BALLOT
TOTAL

[Precinct rows with vote counts]
Precinct Name | ED Code | Vote Counts... | Totals

TOTAL: [Summary counts]
```

### Example: President Race (Page 110)

```
DEM REP CON WOR W/I W/I W/I W/I W/I W/I W/I W/I W/I
DWT
ZLAW             <- "WALZ" mirrored
/ SIRRAH         <- "HARRIS" mirrored
ECNAV            <- "VANCE" mirrored
/
PMURT            <- "TRUMP" mirrored
...
CANVASS
TOTAL
VOID-
BLANK
BALLOT
TOTAL

Town of Cortlandt - 1 20001 282 363 31 10 2 0 0 0 0 0 0 0 0 688 9 697
Town of Cortlandt - 2 20002 182 233 32 11 1 0 0 0 0 0 0 0 0 459 8 467
...
```

### Example: District Attorney (Page 300)

```
DEM REP W/I W/I
DWT
ECACAC           <- "CACACE" mirrored
NASUS            <- "SUSAN" mirrored
III
ENOCRAS          <- "SARCONE" mirrored
.A
NHOJ             <- "JOHN" mirrored
FFATSGAW         <- "WAGSTAFF" mirrored
MAILLIW          <- "WILLIAM" mirrored
IRREGULAR
CANVASS
TOTAL
...

City of Mount Vernon - 1 200001 267 19 0 0 286 52 338
City of Mount Vernon - 2 200002 487 39 2 0 528 85 613
...
```

---

## Key Characteristics

### 1. Precinct Naming

**Format:** `[Municipality Type] of [Name] [Optional Subdivision] - [District] [ED Code]`

Examples:
- `City of Yonkers Ward 9 ED 1 250901`
- `City of Mount Vernon - 1 200001`
- `Town of Cortlandt - 1 20001`

### 2. Column Structure

**Party columns:** DEM, REP, CON, WOR (varies by race)
**Write-in columns:** W/I (multiple, up to 13 in President race)
**Summary columns:**
- CANVASS TOTAL (sum of all party/W-I votes)
- VOID-BLANK (invalid votes)
- BALLOT TOTAL (grand total including invalid)

### 3. ED Codes

Election District codes appear to follow these patterns:
- 6-digit codes (e.g., `250901`, `200001`)
- 5-digit codes (e.g., `20001`, `20002`)

### 4. Vote Count Format

Numbers are cleanly formatted integers separated by spaces, one per column.

---

## Text Mirroring Issue

### Problem Description

Candidate names are **horizontally mirrored (reversed)** in the extracted text.

**Root Cause:** The PDF rendering engine stores text characters in reversed order, likely due to:
- Vertical text layout being transformed to horizontal
- Right-to-left character ordering in the PDF structure
- Font rendering quirks

### Examples of Mirroring

| Mirrored (Extracted) | Correct Name |
|---------------------|--------------|
| ZLAW / SIRRAH | WALZ / HARRIS |
| ECNAV / PMURT | VANCE / TRUMP |
| NIETS LLIJ | STEIN JILL |
| TSEW LENROC | WEST CORNEL |
| ECACAC NASUS | CACACE SUSAN |
| FFATSGAW MAILLIW | WAGSTAFF WILLIAM |

### Current Fix Status

The `pdf_text_fixer.py` utility has a `_fix_mirrored_words()` function that:
- Detects words likely to be mirrored using heuristics
- Reverses them to correct the text
- Handles hyphenated names (e.g., "FAVA-PASTIHAL")

**Coverage:** Partial. Some names are fixed, but many are still reversed in the extracted text.

### Needed Improvements

1. **Expand known mirrored patterns** in `rare_starts` list
2. **Improve heuristic detection** for proper names
3. **Consider word-length thresholds** (most mirrored text is 4+ characters)
4. **Test with full candidate name database** to catch edge cases

---

## Similarity to Putnam Format

### Identical Elements

✓ Precinct-table structure
✓ Party column headers (DEM, REP, etc.)
✓ W/I columns for write-ins
✓ CANVASS TOTAL / VOID-BLANK / BALLOT TOTAL rows
✓ Total row at bottom
✓ ED codes identifying precincts
✓ One race per page range

### Differences

| Aspect | Putnam | Westchester |
|--------|--------|-------------|
| Text mirroring | None | Extensive (candidate names) |
| W/I columns | Fewer (typically 1-3) | More (up to 13 for President) |
| Precinct naming | `Town of X - District Y` | `City/Town of X Ward Y ED Z` |
| ED code format | Varies | 5-6 digit codes |
| Page count | ~200 pages | 688 pages |

---

## Parsing Complexity Assessment

### Complexity Score: **Moderate (6/10)**

**Factors:**
- **Structure:** Simple precinct-table (same as Putnam) → **Low complexity**
- **Mirroring:** Extensive text reversal requiring fix-up → **Moderate complexity**
- **Volume:** 688 pages, many races → **Moderate complexity**
- **Consistency:** Highly consistent format across races → **Low complexity**

### Reusability Score: **High (8/10)**

**Can reuse from Putnam parser:**
- Table structure detection
- Column alignment logic
- Precinct row parsing
- ED code extraction
- Vote count parsing
- Total row detection

**Needs modification:**
- Enhanced mirroring detection and correction
- Adjusted precinct name parsing (Ward/ED vs District)
- Handle more W/I columns

---

## Recommended Implementation Strategy

### Phase 1: Enhance Text Fixer

1. **Expand mirrored pattern database** in `pdf_text_fixer.py`
   - Add all known Westchester candidate names to `rare_starts`
   - Test against pages 110, 300, and other race pages

2. **Improve detection heuristics**
   - Lower threshold for proper name detection
   - Add common surname patterns (endings like -MAN, -SON, -VER)
   - Handle multi-word names separated by " / "

3. **Add validation**
   - Check if reversed word is "more English" than original
   - Use letter frequency analysis for proper names

### Phase 2: Adapt Putnam Parser

1. **Clone Putnam extractor** as base (`extract_putnam.py` → `extract_westchester.py`)

2. **Modify precinct name regex** to handle Ward/ED format:
   ```python
   # Putnam: "Town of Bedford - District 1"
   # Westchester: "City of Yonkers Ward 9 ED 1"
   ```

3. **Adjust ED code extraction** for 5-6 digit codes

4. **Handle variable W/I column count** (President has 13, others have 2-4)

5. **Test on sample pages**:
   - Page 50: NY Prop 1 (simple YES/NO)
   - Page 110-161: President (multi-candidate, many W/I)
   - Page 300-325: District Attorney (fewer columns)

### Phase 3: Full Integration

1. **Run extraction** on full 688-page PDF
2. **Validate results** against known totals
3. **Handle edge cases** (special characters, hyphenated names, etc.)
4. **Generate database import** matching Putnam schema

---

## Test Cases

### Priority Pages for Testing

| Page | Race | Reason |
|------|------|--------|
| 0 | Index | Verify page ranges |
| 50 | NY Prop 1 | Simple YES/NO format |
| 110 | President (start) | Multi-candidate, max W/I columns |
| 161 | President (end) | Verify totals |
| 300 | District Attorney | Typical multi-party race |
| 450 | Congress 16th | District-level race |

### Validation Checklist

- [ ] All candidate names correctly un-mirrored
- [ ] Party affiliations match reality
- [ ] Vote totals sum correctly (party votes → canvass → ballot)
- [ ] ED codes properly extracted
- [ ] Precinct names parsed correctly
- [ ] TOTAL rows identified and excluded from precinct data
- [ ] No duplicate precincts

---

## Conclusion

**Westchester PDF format is highly similar to Putnam** and can reuse most of the existing parser logic. The main challenge is the text mirroring issue, which requires:

1. **Enhanced text fixing** in `pdf_text_fixer.py`
2. **Minor adjustments** to precinct name parsing
3. **Testing** across multiple race types

**Estimated Effort:** 2-4 hours
- 1 hour: Enhance text mirroring fixes
- 1 hour: Adapt Putnam parser for Westchester
- 1-2 hours: Testing and validation

**Confidence:** High - The structure is well-understood and the mirroring issue has a clear solution path.
