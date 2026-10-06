#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["z3-solver>=4.12"]
# ///
"""Propose and apply Taskwarrior-shaped week schedules from omn requirements.

This is the entry point. The implementation lives in the sibling ``scheduler``
package:

- ``scheduler.sources`` reads ``omn export`` and ``task export`` (or a JSON
  spec via ``--spec`` for deterministic tests) and builds the week's
  requirements + fixed intervals + diagnostics;
- ``scheduler.model`` solves the first-class block/allocation Z3 model with
  tracked hard constraints and small soft-bucket ladders;
- ``scheduler.decode`` turns a model into Taskwarrior-shaped candidate records
  with exact ``@10m [omn:<id>]`` todo pins;
- ``scheduler.apply`` performs the dry-run-default, UUID-safe apply against
  Taskwarrior, then lints and syncs the calendar.

Normal use::

    schedule_composer.py plan --week 2026-09-28 --candidates 3 --out plan.json
    schedule_composer.py apply --plan plan.json --candidate 0 --yes

JSON spec input (``plan --spec FILE``) is a testing/debugging seam, not the
normal planning interface. The historic positional-spec invocation is still
accepted for compatibility.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scheduler.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
