import importlib.util
import random
import sys
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "schedule_composer.py"
SPEC = importlib.util.spec_from_file_location("schedule_composer", MODULE_PATH)
composer = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = composer
SPEC.loader.exec_module(composer)


class ComposerTests(unittest.TestCase):
    def base_spec(self, requirements, fixed=None, slot_minutes=30):
        return {
            "week_start": "2026-09-28",
            "days": [
                "2026-09-28", "2026-09-29", "2026-09-30",
                "2026-10-01", "2026-10-02", "2026-10-03",
                "2026-10-04",
            ],
            "slot_minutes": slot_minutes,
            "minimum_block_minutes": 30,
            "blocks_per_day_cap": 6,
            "wake_hour": 6,
            "sleep_hour": 24,
            "fixed": fixed or [],
            "requirements": requirements,
        }

    def solve(self, spec, profile="baseline"):
        p = composer.PROFILES[profile]
        return composer.solve_once(spec, p, p["weights"], timeout_ms=5_000)

    def test_fuzz_weights_returns_integers(self):
        weights = composer.fuzz_weights({"a": 4, "b": 9}, random.Random(1))
        self.assertTrue(all(type(value) is int for value in weights.values()))

    def test_fixed_event_end_rounds_up(self):
        spec = self.base_spec([], [{
            "desc": "class", "day": "2026-09-28",
            "start": "10:00", "end": "11:15",
        }])
        self.assertEqual(set(composer.fixed_slots(spec)), {20, 21, 22})

    def test_deadline_is_hard_and_shortfall_is_soft(self):
        spec = self.base_spec([{
            "omn_id": "x:due", "title": "Due at seven", "est": 2.0,
            "due": "2026-09-28T07:00:00", "kind": "assignment",
            "topic": "course", "location": "At home",
        }])
        result = self.solve(spec)
        self.assertEqual(result["status"], "ok")
        self.assertGreater(result["objectives"]["shortfall"], 0)
        self.assertTrue(all(block["end"] <= "07:00" for block in result["blocks"]))

    def test_fixed_event_cannot_be_overlapped(self):
        spec = self.base_spec([{
            "omn_id": "x:fixed", "title": "Work", "est": 2.0,
            "due": "2026-09-28T12:00:00", "kind": "assignment",
            "topic": "course", "location": "At home",
        }], [{
            "desc": "class", "day": "2026-09-28",
            "start": "08:00", "end": "10:00",
        }])
        result = self.solve(spec)
        for block in result["blocks"]:
            self.assertTrue(block["end"] <= "08:00" or block["start"] >= "10:00")

    def test_assignment_coverage_precedes_project_coverage(self):
        fixed = []
        for day in ["2026-09-28", "2026-09-29", "2026-09-30",
                    "2026-10-01", "2026-10-02", "2026-10-03",
                    "2026-10-04"]:
            fixed.append({"desc": "blocked", "day": day,
                          "start": "07:00", "end": "23:59"})
            if day != "2026-09-28":
                fixed.append({"desc": "blocked early", "day": day,
                              "start": "06:00", "end": "07:00"})
        spec = self.base_spec([
            {"omn_id": "x:a", "title": "Assignment", "est": 1.0,
             "due": "2026-10-02", "kind": "assignment",
             "topic": "course", "location": "At home"},
            {"omn_id": "x:p", "title": "Project", "est": 1.0,
             "due": "2026-10-02", "kind": "project",
             "topic": "project", "location": "At home"},
        ], fixed)
        result = self.solve(spec)
        self.assertEqual(result["objectives"]["assignment_shortfall"], 0)
        self.assertGreater(result["objectives"]["other_shortfall"], 0)
        covered = {item["omn_id"] for block in result["blocks"]
                   for item in block["requirements"]}
        self.assertIn("x:a", covered)
        self.assertNotIn("x:p", covered)

    def test_same_topic_requirements_compose_one_block(self):
        spec = self.base_spec([
            {"omn_id": "x:1", "title": "Part one", "est": 0.5,
             "due": "2026-10-02", "kind": "assignment",
             "topic": "same-course", "location": "At home"},
            {"omn_id": "x:2", "title": "Part two", "est": 0.5,
             "due": "2026-10-02", "kind": "assignment",
             "topic": "same-course", "location": "At home"},
        ])
        result = self.solve(spec)
        self.assertEqual(result["objectives"]["blocks"], 1)
        self.assertEqual(len(result["blocks"]), 1)
        self.assertEqual(len(result["blocks"][0]["requirements"]), 2)

    def test_non_weekend_due_forbids_assignment_weekend(self):
        spec = self.base_spec([{
            "omn_id": "x:weekday", "title": "Next Monday", "est": 2.0,
            "due": "2026-10-05", "kind": "assignment",
            "topic": "course", "location": "At home",
        }])
        result = self.solve(spec)
        weekend = {"2026-10-03", "2026-10-04"}
        self.assertFalse(any(block["day"] in weekend for block in result["blocks"]))

    def test_weekend_due_uses_weekend_only_when_weekdays_cannot_fit(self):
        fixed = []
        for day in ["2026-09-28", "2026-09-29", "2026-09-30",
                    "2026-10-01", "2026-10-02"]:
            fixed.append({"desc": "full weekday", "day": day,
                          "start": "06:00", "end": "23:59"})
        spec = self.base_spec([{
            "omn_id": "x:weekend", "title": "Sunday deadline", "est": 2.0,
            "due": "2026-10-04", "kind": "assignment",
            "topic": "course", "location": "At home",
        }], fixed)
        result = self.solve(spec)
        self.assertEqual(result["objectives"]["shortfall"], 0)
        self.assertGreater(result["objectives"]["weekend_assignment"], 0)
        self.assertTrue(all(block["day"] in {"2026-10-03", "2026-10-04"}
                            for block in result["blocks"]))

    def test_fifteen_minute_model_enforces_half_hour_block(self):
        spec = self.base_spec([{
            "omn_id": "x:min", "title": "Half hour", "est": 0.5,
            "due": "2026-10-02", "kind": "assignment",
            "topic": "course", "location": "At home",
        }], slot_minutes=15)
        result = self.solve(spec)
        self.assertEqual(result["objectives"]["shortfall"], 0)
        self.assertEqual(len(result["blocks"]), 1)
        block = result["blocks"][0]
        start_h, start_m = map(int, block["start"].split(":"))
        end_h, end_m = map(int, block["end"].split(":"))
        self.assertGreaterEqual((end_h * 60 + end_m) - (start_h * 60 + start_m), 30)


if __name__ == "__main__":
    unittest.main()
