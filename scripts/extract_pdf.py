#!/usr/bin/env python3
"""
Entry point for PDF election results extraction.

Usage:
    python scripts/extract_pdf.py columbia
    python scripts/extract_pdf.py dutchess
    python scripts/extract_pdf.py greene
"""

import sys

from extractors.base import extract_races_from_pdf
from extractors.config import COUNTY_CONFIGS


def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/extract_pdf.py <county>")
        print(f"Available counties: {', '.join(COUNTY_CONFIGS.keys())}")
        sys.exit(1)

    county = sys.argv[1].lower()

    try:
        extract_races_from_pdf(county)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
