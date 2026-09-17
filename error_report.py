#!/usr/bin/env python3
import argparse
from pathlib import Path
from src.error_analysis import write_error_report

parser = argparse.ArgumentParser()
parser.add_argument("results", type=Path)
parser.add_argument("--output", type=Path, default=Path(__file__).parent / "outputs/ERROR_ANALYSIS.md")
args = parser.parse_args()
counts = write_error_report(args.results, args.output)
print(f"Saved {sum(counts.values())} classified errors to {args.output}")
