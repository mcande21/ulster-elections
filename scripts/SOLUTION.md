# PDF Text Extraction Solution

## Problem Summary

Putnam and Westchester County election PDFs had two critical text extraction issues that prevented proper data parsing:

1. **Vertical Text Extraction**: Characters appeared one per line instead of being grouped horizontally
2. **Mirrored Text**: Some candidate names and words appeared backwards (e.g., "NAMDOOG" instead of "GOODMAN")

## Root Causes

### Vertical Text Issue

**Cause**: PDFs have inconsistent character Y-positioning, with characters on the same visual line having slightly different Y coordinates (2-3 pixel spacing). pdfplumber's default extraction uses conservative grouping tolerances, treating each character as a separate line.

**Example** (Putnam Page 0 before fix):
```
P
G
N
U
o
```

**Solution**: Use adjusted extraction parameters to force more aggressive character grouping:

```python
page.extract_text(
    x_tolerance=2,
    y_tolerance=2,
    layout=False,
    x_density=7.25,
    y_density=13
)
```

The `x_density` and `y_density` parameters control how aggressively pdfplumber groups characters on the same line.

### Mirrored Text Issue

**Cause**: Some PDF pages were rendered with horizontal flip transformation, causing text to appear backwards in the source PDF itself. This is a PDF generation issue, not an extraction issue.

**Example** (Westchester Page 344):
- NAMDOOG → should be GOODMAN
- REVLUP → should be PULVER
- AHLITSAP-AVAF → should be PASTILHA-FAVA

**Solution**: Detect and reverse mirrored words using heuristics:

1. **Known patterns**: Maintain list of actual mirrored words found in PDFs
2. **Double-letter detection**: Words starting with double letters that reverse to common name endings
3. **Hyphenated names**: Handle compound names like "PASTILHA-FAVA" by processing each part

## Implementation

### Files Created

1. **`scripts/extractors/pdf_text_fixer.py`** - Main extraction utilities
   - `extract_text_with_fixes(page)` - Extract from single page with fixes
   - `extract_text_from_pdf(pdf_path, page_num)` - Extract from PDF file

2. **`scripts/test_pdf_extraction.py`** - Comprehensive test suite
   - Tests vertical text fix on Putnam pages
   - Tests mirrored text fix on Westchester pages
   - Verifies normal pages aren't broken by fixes
   - Shows before/after comparison

3. **`scripts/extractors/README.md`** - Documentation and usage guide

### Test Scripts (Development)

Development/debugging scripts (can be deleted):
- `scripts/test_vertical_extraction.py`
- `scripts/analyze_char_grouping.py`
- `scripts/find_working_solution.py`
- `scripts/optimize_extraction.py`
- `scripts/debug_mirror.py`

## Results

### Before Fixes

**Putnam Page 0**: 156 lines with individual characters
```
P
G
N
U
o
E
v
```

**Westchester Page 344**: Backward names
```
NAMDOOG
REVLUP
AHLITSAP-AVAF
```

### After Fixes

**Putnam Page 0**: 81 lines with proper grouping (48% reduction)
```
PUTNAM COUNTY ELECTORS FOR PRESIDENT / VICE PRESIDENT
GENERAL ELECTION VOTE FOR ONE
November 5, 2024
```

**Westchester Page 344**: Corrected names
```
GOODMAN
PULVER
PASTILHA-FAVA
```

### Test Results

All tests pass:
- ✓ Putnam vertical text fixed (pages 0, 30)
- ✓ Westchester mirrored text fixed (pages 344, 687)
- ✓ Normal pages unaffected (Westchester page 0)

## Usage

```python
from extractors.pdf_text_fixer import extract_text_from_pdf

# Extract single page
text = extract_text_from_pdf("data/raw/putnam_2024-11-05.pdf", page_num=0)

# Extract entire PDF
text = extract_text_from_pdf("data/raw/westchester_2024-11-05.pdf")
```

## Integration

To integrate this into existing extraction scripts:

```python
# Old code:
import pdfplumber
with pdfplumber.open(pdf_path) as pdf:
    text = pdf.pages[0].extract_text()

# New code:
from extractors.pdf_text_fixer import extract_text_with_fixes
import pdfplumber
with pdfplumber.open(pdf_path) as pdf:
    text = extract_text_with_fixes(pdf.pages[0])
```

## Known Limitations

1. **Spacing in headers**: Some column headers still have extra spacing (e.g., "D I S T R I C T" instead of "DISTRICT"). This is cosmetic and doesn't affect data parsing.

2. **Dictionary-based detection**: Currently uses hardcoded list of known mirrored words. Could be improved with dictionary lookup for automatic detection.

3. **Rotation**: Doesn't handle 90/180/270 degree page rotation (not found in tested PDFs).

## Testing Coverage

### Putnam County (61 pages)
- ✓ Page 0: Title page with vertical text
- ✓ Page 30: Data table with mixed formatting
- ✓ Page 60: Proposal page

### Westchester County (688 pages)
- ✓ Page 0: Index (clean, no issues)
- ✓ Page 344: County Court Judge with mirrored names
- ✓ Page 687: Yonkers City Court with mirrored text

## Next Steps

1. Update existing extractors (`extract_putnam.py`, `extract_westchester.py`) to use new utilities
2. Re-run extraction on all PDFs
3. Verify parsed data looks correct
4. Consider adding more mirrored word patterns as they're discovered
