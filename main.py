#!/usr/bin/env python3
"""Convenience launcher: `python main.py data.csv` (same as `python -m autoinsight data.csv`)."""
from autoinsight.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
