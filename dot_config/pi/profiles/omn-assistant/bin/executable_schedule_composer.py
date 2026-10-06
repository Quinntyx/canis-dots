#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["z3-solver>=4.12"]
# ///
"""Semantic-color 96x7 grid scheduler. See grid_scheduler/README.md.

The frozen previous engine is available explicitly as
schedule_composer_legacy.py. Legacy specs/plans are not silently converted.
Planning is read-only; apply is dry-run unless --yes is supplied.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from grid_scheduler.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
