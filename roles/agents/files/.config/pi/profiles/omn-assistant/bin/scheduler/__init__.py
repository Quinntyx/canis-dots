"""Schedule composer internals.

The package is deliberately split so that source parsing and RRULE expansion
can be imported and tested without the Z3 solver installed:

- ``common``   shared vocabulary (diagnostics, requirements, fixed intervals)
- ``rrule``    RFC 5545 weekly recurrence expansion
- ``sources``  omn/Taskwarrior/spec readers
- ``model``    the Z3 block/allocation model (imports ``z3``)
- ``decode``   model -> Taskwarrior-shaped candidate records
- ``apply``    dry-run/apply against Taskwarrior + lint + gcal-sync
- ``cli``      ``plan`` / ``apply`` argument parsing
"""

__all__ = ["apply", "cli", "common", "decode", "model", "rrule", "sources"]
