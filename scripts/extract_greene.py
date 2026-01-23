#!/usr/bin/env python3
"""
DEPRECATED: Use fetch_results.py instead.

    python scripts/fetch_results.py --county greene

This script is maintained for backwards compatibility only.
The original extraction logic has been moved to the new parser system.
"""
import subprocess
import sys


def main():
    print("=" * 60)
    print("WARNING: This script is deprecated.")
    print("Use: python scripts/fetch_results.py --county greene")
    print("=" * 60)
    print()

    subprocess.run([sys.executable, "scripts/fetch_results.py", "--county", "greene"])


if __name__ == "__main__":
    main()
