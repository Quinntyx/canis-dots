import importlib.util
import sys
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "taskwarrior_lint.py"
SPEC = importlib.util.spec_from_file_location("taskwarrior_lint", MODULE_PATH)
linter = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = linter
SPEC.loader.exec_module(linter)


class TodoAttributionTests(unittest.TestCase):
    def test_small_pins_leave_remainder_for_large_requirement(self):
        refs = [f"small{i}" for i in range(5)] + ["assignment"]
        pinned = {f"small{i}": 10 / 60 for i in range(5)}
        estimates = {**pinned, "assignment": 12.0}
        credit = linter.attribute_block(3.0, refs, pinned, estimates)
        self.assertAlmostEqual(sum(credit[f"small{i}"] for i in range(5)), 50 / 60)
        self.assertAlmostEqual(credit["assignment"], 2 + 10 / 60)
        self.assertAlmostEqual(sum(credit.values()), 3.0)

    def test_overcommitted_pins_never_create_time(self):
        credit = linter.attribute_block(
            1.0, ["first", "second", "open"],
            {"first": 0.75, "second": 0.75},
            {"first": 1.0, "second": 1.0, "open": 4.0},
        )
        self.assertAlmostEqual(credit["first"], 0.75)
        self.assertAlmostEqual(credit["second"], 0.25)
        self.assertEqual(credit["open"], 0)
        self.assertLessEqual(sum(credit.values()), 1.0)

    def test_open_items_use_remaining_not_original_estimate(self):
        credit = linter.attribute_block(
            2.0, ["nearly-done", "large"], {},
            {"nearly-done": 4.0, "large": 4.0},
            {"nearly-done": 3.5, "large": 0.0},
        )
        self.assertAlmostEqual(credit["nearly-done"], 2.0 * 0.5 / 4.5)
        self.assertAlmostEqual(credit["large"], 2.0 * 4.0 / 4.5)

    def test_after_due_block_does_not_satisfy_requirement(self):
        record = {"id": "x:late", "title": "Late work", "meta": {"est": "2h"}}

        class FakeContext:
            def __init__(self):
                self.tasks = [{
                    "todo": "- finish [omn:x:late]",
                    "scheduled": "20261005T050000Z",
                    "est": "2h",
                }]
                self.omn = [record]
                self.week_sunday = date(2026, 10, 4)
                self.now = datetime(2026, 9, 29, tzinfo=linter.TZ)

            @staticmethod
            def duration(task):
                return None

            @staticmethod
            def est_of(task):
                return timedelta(hours=2)

            @staticmethod
            def omn_assignments():
                return [(record, date(2026, 10, 4))]

        warnings = linter.TodoCoverage().check(FakeContext())
        warning = next(item for item in warnings if item.refs == ["x:late"])
        self.assertIn("0.00h of 2.0h", warning.message)
        self.assertEqual(warning.severity, "ERROR")


if __name__ == "__main__":
    unittest.main()
