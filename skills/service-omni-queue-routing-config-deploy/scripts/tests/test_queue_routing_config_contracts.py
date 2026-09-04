#!/usr/bin/env python3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _bootstrap import FakeSf, last_json, run  # noqa: E402


class InputTests(unittest.TestCase):
    def test_weight_and_percentage_are_mutually_exclusive(self):
        with FakeSf() as fake:
            rc, out = run(["org", "LeastActive", "Case_Routing_Config", "Case Routing Config", "7"],
                          path_prefix=fake, extra_env={"QRC_CAPACITY_PERCENTAGE": "100"})
        self.assertEqual(rc, 1, out)
        self.assertIn("mutually exclusive", out)

    def test_invalid_timeout_is_rejected(self):
        with FakeSf() as fake:
            rc, out = run(["org"], path_prefix=fake, extra_env={"QRC_PUSH_TIMEOUT": "99999"})
        self.assertEqual(rc, 1, out)
        self.assertIn("Invalid push-timeout", out)


class BehaviorTests(unittest.TestCase):
    def test_create_percentage_capacity_and_timeout(self):
        with FakeSf() as fake:
            rc, out = run(["org", "LeastActive"], path_prefix=fake,
                          extra_env={"QRC_CAPACITY_PERCENTAGE": "100", "QRC_PUSH_TIMEOUT": "30",
                                     "FAKE_FINAL_RM": "LeastActive", "FAKE_FINAL_CP": "100.0",
                                     "FAKE_FINAL_PT": "30", "FAKE_FINAL_CW": "null"})
        self.assertEqual(rc, 0, out)
        result = last_json(out)
        self.assertEqual(result["capacity_mode"], "percentage", out)
        self.assertEqual(result["capacity_percentage"], 100.0, out)
        self.assertEqual(result["push_timeout"], 30, out)

    def test_matching_existing_record_is_reused(self):
        with FakeSf() as fake:
            rc, out = run(["org"], path_prefix=fake, extra_env={"FAKE_EXISTING": "1"})
        self.assertEqual(rc, 0, out)
        self.assertEqual(last_json(out)["status"], "reused", out)

    def test_existing_custom_values_are_preserved_when_not_requested(self):
        custom = {
            "FAKE_EXISTING": "1",
            "FAKE_BEFORE_RM": "LeastActive",
            "FAKE_BEFORE_CW": "17",
            "FAKE_BEFORE_PT": "45",
            "FAKE_BEFORE_RP": "7",
            "FAKE_BEFORE_ML": "Existing Queue Policy",
            "FAKE_FINAL_RM": "LeastActive",
            "FAKE_FINAL_CW": "17",
            "FAKE_FINAL_PT": "45",
            "FAKE_FINAL_RP": "7",
            "FAKE_FINAL_ML": "Existing Queue Policy",
        }
        with FakeSf() as fake:
            rc, out = run(["org"], path_prefix=fake, extra_env=custom)
        self.assertEqual(rc, 0, out)
        result = last_json(out)
        self.assertEqual(result["status"], "reused", out)
        self.assertEqual(result["master_label"], "Existing Queue Policy", out)
        self.assertEqual(result["capacity_weight"], 17, out)
        self.assertEqual(result["routing_priority"], 7, out)
        self.assertEqual(result["push_timeout"], 45, out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
