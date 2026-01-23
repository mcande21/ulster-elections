#!/usr/bin/env python3
import sys
sys.path.insert(0, 'scripts')

from extractors.pdf_text_fixer import _is_word_likely_mirrored

# Test the mirrored words we found
test_words = ['SIRRAH', 'PMURT', 'ZLAW', 'ECNAV', 'NIETS', 'LLIJ', 'TSEW', 'LENROC', 'REVILO']

print("Testing mirror detection heuristic:\n")

for word in test_words:
    is_mirrored = _is_word_likely_mirrored(word)
    reversed_word = word[::-1]
    print(f"{word:15} -> {reversed_word:15}  Detected: {'✓' if is_mirrored else '✗'}")
