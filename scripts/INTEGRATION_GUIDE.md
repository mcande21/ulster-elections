# Integration Guide: PDF Text Extraction Fixes

## Overview

The PDF text extraction fixes are now ready to integrate into existing extraction scripts.

## What Changed

Created new module: `scripts/extractors/pdf_text_fixer.py`

This module provides:
- `extract_text_with_fixes(page)` - Drop-in replacement for `page.extract_text()`
- Fixes vertical text extraction (Putnam, Westchester)
- Fixes mirrored text (Westchester)

## Files That Need Updates

Based on grep of `page.extract_text()` calls:

1. **`scripts/extractors/base.py`** (line 226)
2. **`scripts/extractors/parsers.py`** (lines 108, 377, 749)

## Integration Steps

### 1. Update `base.py`

**Current code** (around line 226):
```python
text = page.extract_text()
```

**Updated code**:
```python
from .pdf_text_fixer import extract_text_with_fixes

# In the function:
text = extract_text_with_fixes(page)
```

### 2. Update `parsers.py`

**Current code** (lines 108, 377, 749):
```python
text = page.extract_text()
```

**Updated code**:
```python
from .pdf_text_fixer import extract_text_with_fixes

# In each function:
text = extract_text_with_fixes(page)
```

## Testing After Integration

### 1. Run extraction tests
```bash
source backend/venv/bin/activate
python3 scripts/test_pdf_extraction.py
```

Should output:
```
✓ ALL TESTS PASSED
```

### 2. Test Putnam extraction
```bash
python3 scripts/extract_pdf.py putnam
```

Expected: Should extract text without vertical character issues

### 3. Test Westchester extraction
```bash
python3 scripts/extract_pdf.py westchester
```

Expected: Candidate names should be correct (not mirrored)

## Verification Checklist

After integrating the changes:

- [ ] All PDF extraction tests pass (`test_pdf_extraction.py`)
- [ ] Putnam PDF extracts with horizontal text (not vertical)
- [ ] Westchester PDF extracts with correct names (not mirrored)
- [ ] Existing county extractors still work (Columbia, Dutchess, Greene, Ulster)
- [ ] No regressions in normal PDFs

## Rollback Plan

If integration causes issues:

1. Revert the imports:
   ```python
   # Remove: from .pdf_text_fixer import extract_text_with_fixes
   ```

2. Revert the function calls:
   ```python
   # Change back: text = extract_text_with_fixes(page)
   # To: text = page.extract_text()
   ```

3. File an issue with specific failure details

## Known Limitations

After integration, note these limitations:

1. **Column header spacing**: Some headers still have extra spacing (e.g., "D I S T R I C T")
   - This is cosmetic and doesn't affect data parsing
   - Can be fixed with post-processing if needed

2. **New mirrored words**: If new mirrored words are found:
   - Add them to `rare_starts` list in `pdf_text_fixer.py`
   - Line 82-84 in `_is_word_likely_mirrored()`

3. **Page rotation**: Doesn't handle 90/180/270 degree rotations
   - Not found in current PDFs
   - Can be added if needed

## Support

If extraction issues occur after integration:

1. Check the test output from `test_pdf_extraction.py`
2. Review `scripts/SOLUTION.md` for technical details
3. Check `scripts/extractors/README.md` for usage examples
