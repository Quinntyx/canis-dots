#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["z3-solver>=4.12"]
# ///
"""Explicit entrypoint for the frozen interval-v1 scheduler. Not the default."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "legacy", "interval-v1"))
from scheduler.cli import main

if __name__ == "__main__":
    print("Legacy interval-v1 scheduler: use schedule_composer.py for grid-week/v1.", file=sys.stderr)
    raise SystemExit(main())
