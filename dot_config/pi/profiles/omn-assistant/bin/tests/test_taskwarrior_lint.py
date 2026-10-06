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


class NativePublicationLintTests(unittest.TestCase):
    @staticmethod
    def context():
        ctx = object.__new__(linter.Context)
        ctx.week_monday = date(2026, 9, 28)
        ctx.week_sunday = date(2026, 10, 4)
        ctx.now = datetime(2026, 10, 2, 13, tzinfo=linter.TZ)
        ctx.tasks = []
        ctx.omn = []
        return ctx

    def test_exclusive_24_hour_end_is_next_midnight(self):
        ctx = self.context()
        task = {"scheduled": "20261002T050000Z", "starttime": "20:00", "endtime": "24:00"}
        begin, end = ctx.datetimes(task)
        self.assertEqual(end.date(), date(2026, 10, 3))
        self.assertEqual(end - begin, timedelta(hours=4))

    def test_recurrence_carried_date_comparison(self):
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            artifact = Path(folder) / "recurrence.txt"
            artifact.write_text("At least 1 session per calendar week")
            ctx = self.context()
            ctx.omn = [{"id": "practice", "title": "Practice piano", "meta": {},
                        "artifacts": {"rrule": artifact.as_uri()}}]
            ctx.tasks = [{"status": "pending", "scheduled": "20261007T050000Z",
                          "description": "Practice piano"}]
            self.assertEqual(linter.RecurrenceArtifactsCovered().check(ctx), [])

    def assessment_context(self):
        ctx = self.context()
        ctx.omn = [
            {"id": "assessment", "type": "task", "title": "Common Exam",
             "meta": {"due": "2026-10-02T23:00:00Z", "in_class_assessment_for": "exam"}},
            {"id": "exam", "type": "event", "title": "Exam",
             "meta": {"start": "2026-10-02T16:00:00-05:00", "end": "2026-10-02T18:00:00-05:00"}},
        ]
        ctx.tasks = [{"status": "pending", "tags": ["fixed"], "description": "Attend Exam",
                      "scheduled": "20261002T050000Z", "starttime": "16:00", "endtime": "18:00",
                      "todo": "- Attend Exam [omn:exam]", "est": "2h"}]
        return ctx

    def test_assessment_covered_by_actual_exact_fixed_exam(self):
        self.assertEqual(linter.TodoCoverage().check(self.assessment_context()), [])

    def test_link_never_hides_unfixed_or_wrong_time_exam(self):
        for change in ({"tags": []}, {"endtime": "17:45"}):
            with self.subTest(change=change):
                ctx = self.assessment_context()
                ctx.tasks[0].update(change)
                warnings = linter.TodoCoverage().check(ctx)
                self.assertTrue(any(w.severity == "ERROR" and w.refs == ["assessment"] for w in warnings))

    def test_travel_references_never_satisfy_homework(self):
        ctx = self.context()
        ctx.omn = [{"id": "hw", "type": "task", "title": "Homework", "meta": {"due": "2026-10-04", "est": "6h"}}]
        ctx.tasks = [{"status": "pending", "tags": ["managed", "travel"], "description": "Drive home",
                      "scheduled": "20261004T050000Z", "starttime": "17:00", "endtime": "22:00",
                      "todo": "- Homework @300m [omn:hw]", "est": "5h"}]
        warnings = linter.TodoCoverage().check(ctx)
        self.assertTrue(any(w.severity == "ERROR" and w.refs == ["hw"] for w in warnings))

    def test_legacy_registration_needs_exact_title_location_and_interval(self):
        ctx = self.assessment_context()
        ctx.omn[1]["meta"]["location"] = "ECSW 1.315"
        ctx.tasks[0]["location"] = "ECSW 1.315"
        ctx.tasks[0].pop("todo")
        ctx.tasks.append({"status": "pending", "description": "Other work",
                          "scheduled": "20261002T050000Z", "starttime": "09:00", "endtime": "10:00",
                          "todo": "- Other work [omn:other]"})
        self.assertEqual(linter.TodoCoverage().check(ctx), [])
        for changes in ({"location": "Wrong room"}, {"description": "Attend another exam"}):
            with self.subTest(changes=changes):
                original = dict(ctx.tasks[0])
                ctx.tasks[0].update(changes)
                warnings = linter.TodoCoverage().check(ctx)
                self.assertTrue(any(w.severity == "ERROR" and w.refs == ["assessment"] for w in warnings))
                ctx.tasks[0] = original


if __name__ == "__main__":
    unittest.main()
