"""
PDF text extraction utilities for handling vertical and mirrored text issues.

These utilities fix problems found in Putnam and Westchester election PDFs:
1. Vertical text extraction (characters appearing one per line)
2. Mirrored/reversed text (right-to-left character ordering)
"""

import pdfplumber
from typing import List, Dict, Any
from collections import defaultdict


def extract_text_with_fixes(page) -> str:
    """
    Extract text from a PDF page with fixes for vertical and mirrored text.

    Args:
        page: pdfplumber page object

    Returns:
        Extracted text as string
    """
    # Try optimized extraction parameters first
    text = page.extract_text(
        x_tolerance=2,
        y_tolerance=2,
        layout=False,
        x_density=7.25,
        y_density=13
    )

    if not text:
        return ""

    # Fix mirrored words (words that are reversed/flipped)
    text = _fix_mirrored_words(text)

    return text


def _fix_mirrored_words(text: str) -> str:
    """
    Fix words that appear reversed/mirrored in the text.

    This handles cases where PDFs render text with horizontal flip,
    causing words to appear backwards (e.g., "NAMDOOG" -> "GOODMAN").

    Args:
        text: Extracted text that may contain mirrored words

    Returns:
        Text with mirrored words reversed
    """
    lines = text.splitlines()
    fixed_lines = []

    for line in lines:
        # Process each word
        words = line.split()
        fixed_words = []

        for word in words:
            # Handle hyphenated words (common in names like "FAVA-PASTIHAL")
            if '-' in word:
                parts = word.split('-')
                fixed_parts = []
                for part in parts:
                    if len(part) > 3 and part.isalpha() and _is_word_likely_mirrored(part):
                        fixed_parts.append(part[::-1])
                    else:
                        fixed_parts.append(part)
                fixed_words.append('-'.join(fixed_parts))
            # Check if word looks mirrored (heuristic: mostly letters, len > 3)
            elif len(word) > 3 and word.isalpha() and _is_word_likely_mirrored(word):
                # Reverse it
                fixed_words.append(word[::-1])
            else:
                fixed_words.append(word)

        fixed_lines.append(' '.join(fixed_words))

    return '\n'.join(fixed_lines)


def _is_word_likely_mirrored(word: str) -> bool:
    """
    Heuristic to detect if a word is likely mirrored.

    Checks for common patterns in mirrored names/words:
    - Double letters at start (mirrored from end: "NAMDOOG" has "OO" -> "NN")
    - Unusual consonant clusters
    - Known mirrored patterns

    Args:
        word: Word to check

    Returns:
        True if word appears to be mirrored
    """
    # Skip short words and words with numbers/special chars
    if len(word) < 4 or not word.isalpha():
        return False

    word_upper = word.upper()

    # Common mirrored indicators (these patterns are rare at word start in English)
    # These are actual mirrored words found in Westchester PDFs
    rare_starts = ['NYLAREHS', 'NAMDOOG', 'REVLUP', 'AHLITSAP', 'DRAHCIR',
                   'WALNI', 'NAVE', 'RALUGERRI', 'SSAVNAC', 'LATOT', 'DIOV',
                   'KNALB', 'TOLLAB', 'DWT', 'AVAF']

    # Check if word matches known mirrored patterns
    if any(word_upper.startswith(pattern) for pattern in rare_starts):
        return True

    # Heuristic: Words with double letters at start (common in mirrored text)
    # Lower threshold to 4+ chars for short names
    if len(word) >= 4:
        # Double letter at start is suspicious for proper names
        if word_upper[0] == word_upper[1] and word_upper[0] in 'NMLRSTABCDEFGHIJKLPQUVWXYZ':
            # Check if reversing would give common ending
            reversed_word = word_upper[::-1]
            if reversed_word.endswith(('MAN', 'SON', 'VER', 'TON', 'LER', 'HAM', 'ANN', 'VAN')):
                return True

    return False


def extract_text_from_pdf(pdf_path: str, page_num: int = None) -> str:
    """
    Extract text from PDF file with automatic fixes.

    Args:
        pdf_path: Path to PDF file
        page_num: Specific page number to extract (0-indexed), or None for all pages

    Returns:
        Extracted text
    """
    with pdfplumber.open(pdf_path) as pdf:
        if page_num is not None:
            if page_num >= len(pdf.pages):
                raise ValueError(f"Page {page_num} doesn't exist (only {len(pdf.pages)} pages)")
            return extract_text_with_fixes(pdf.pages[page_num])
        else:
            # Extract all pages
            texts = []
            for page in pdf.pages:
                text = extract_text_with_fixes(page)
                if text:
                    texts.append(text)
            return '\n\n'.join(texts)


# Testing utilities
def test_extraction(pdf_path: str, page_nums: List[int] = None):
    """
    Test text extraction on specific pages.

    Args:
        pdf_path: Path to PDF file
        page_nums: List of page numbers to test
    """
    from pathlib import Path

    if page_nums is None:
        page_nums = [0]

    print(f"\n{'='*80}")
    print(f"Testing extraction: {Path(pdf_path).name}")
    print(f"{'='*80}\n")

    with pdfplumber.open(pdf_path) as pdf:
        for page_num in page_nums:
            if page_num >= len(pdf.pages):
                print(f"Page {page_num} doesn't exist")
                continue

            print(f"\nPage {page_num}:")
            print("-" * 80)

            page = pdf.pages[page_num]
            text = extract_text_with_fixes(page)

            if text:
                lines = [l for l in text.splitlines() if l.strip()]
                print(f"Total lines: {len(lines)}")
                print(f"\nFirst 10 lines:")
                for i, line in enumerate(lines[:10], 1):
                    display = line[:70] + ('...' if len(line) > 70 else '')
                    print(f"  {i:2d}. {display}")
            else:
                print("No text extracted")


if __name__ == "__main__":
    # Test on problematic pages
    test_extraction("data/raw/putnam_2024-11-05.pdf", [0, 30])
    test_extraction("data/raw/westchester_2024-11-05.pdf", [0, 344, 687])
