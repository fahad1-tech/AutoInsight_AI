"""
Command-line interface.

    autoinsight data.csv
    autoinsight train.csv test.csv            # same columns -> combined
    autoinsight data.csv --target Churn       # name the churn column
    autoinsight data.csv --target none        # turn churn mode off
    autoinsight data.csv -o output/my_report.html --open
    autoinsight data.csv --use-ai             # needs ANTHROPIC_API_KEY
"""

import argparse
import os
import webbrowser
from pathlib import Path

from . import __version__
from .pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="autoinsight",
        description="AutoInsight AI - automated data analysis and dashboard generator")
    parser.add_argument("csv_paths", nargs="+",
                        help="One or more CSV files (they must share the same columns if several)")
    parser.add_argument("-o", "--output", default="output/report.html",
                        help="Path of the HTML dashboard to create (default: output/report.html)")
    parser.add_argument("--target", default=None,
                        help="Churn column name. Auto-detected if omitted; 'none' disables churn mode")
    parser.add_argument("--use-ai", action="store_true",
                        help="Write the executive summary with the Claude API (needs ANTHROPIC_API_KEY)")
    parser.add_argument("--open", action="store_true",
                        help="Open the finished dashboard in your browser")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    out = run_pipeline(args.csv_paths, args.output, use_ai=args.use_ai, target=args.target)
    if args.open:
        webbrowser.open(Path(out).resolve().as_uri())
    return 0
