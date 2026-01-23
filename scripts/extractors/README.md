# PDF Text Extraction Utilities

## Problem

Putnam and Westchester County election PDFs have two text extraction issues:

1. **Vertical Text**: Characters appear one per line instead of horizontally grouped
2. **Mirrored Text**: Some text is rendered backwards (e.g., "NAMDOOG" instead of "GOODMAN")

## Solution

Use `pdf_text_fixer.py` which provides:

### `extract_text_with_fixes(page)`

Extracts text from a pdfplumber page with automatic fixes:
- Uses optimized extraction parameters to group characters horizontally
- Detects and reverses mirrored words

### `extract_text_from_pdf(pdf_path, page_num=None)`

Extract text from entire PDF or specific page with fixes applied.

## Usage

```python
from extractors.pdf_text_fixer import extract_text_from_pdf

# Extract single page
text = extract_text_from_pdf("data/raw/putnam_2024-11-05.pdf", page_num=0)

# Extract entire PDF
text = extract_text_from_pdf("data/raw/westchester_2024-11-05.pdf")
```

## Technical Details

### Vertical Text Fix

**Problem**: Default pdfplumber extraction treats each character as a separate line due to inconsistent Y-positioning in the PDF.

**Solution**: Use adjusted density parameters:
```python
page.extract_text(
    x_tolerance=2,
    y_tolerance=2,
    layout=False,
    x_density=7.25,
    y_density=13
)
```

These parameters tell pdfplumber to be more aggressive about grouping characters on the same line.

### Mirrored Text Fix

**Problem**: Some PDFs have text rendered with horizontal flip transformation, causing words to appear backwards.

**Solution**: Detect and reverse mirrored words using heuristics:

1. **Known mirrored patterns**: Maintain list of actual mirrored words found in PDFs
2. **Double-letter detection**: Words starting with double letters (e.g., "NN", "SS") that reverse to common name endings
3. **Hyphenated names**: Handle compound names like "PASTILHA-FAVA"

## Tested Pages

### Putnam County (61 pages)
- ✓ Page 0: Title page with spacing issues
- ✓ Page 30: Data table with mixed formatting
- ✓ Page 60: Proposal page

### Westchester County (688 pages)
- ✓ Page 0: Index (clean extraction)
- ✓ Page 344: County Court Judge with mirrored names
- ✓ Page 687: Yonkers City Court with mirrored text

## Examples

**Before** (Putnam Page 0):
```
P
G
N
U
o
E
v
```

**After**:
```
PUTNAM COUNTY ELECTORS FOR PRESIDENT / VICE PRESIDENT
GENERAL ELECTION VOTE FOR ONE
November 5, 2024
```

**Before** (Westchester Page 344):
```
NAMDOOG
REVLUP
AHLITSAP-AVAF
```

**After**:
```
GOODMAN
PULVER
PASTILHA-FAVA
```

## Future Improvements

- Auto-detect mirrored words using dictionary lookup instead of hardcoded patterns
- Handle rotated pages (90/180/270 degree rotation)
- Improve spacing in column headers (e.g., "D I" → "DISTRICT")
