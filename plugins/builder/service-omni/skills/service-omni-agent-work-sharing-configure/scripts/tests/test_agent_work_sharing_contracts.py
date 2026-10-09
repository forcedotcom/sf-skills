#!/usr/bin/env python3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _bootstrap import FakeSf, last_json  # noqa: E402


class AgentWorkSharingContractTests(unittest.TestCase):
    def test_private_model_deploys_read_and_verifies(self):
        with FakeSf() as fake:
            rc, output = fake.run(["org", "--confirm-org-wide-visibility"])
            trace = fake.read_state("trace")

        self.assertEqual(rc, 0, output)
        self.assertIn("project deploy start", trace)
        self.assertIn("CustomObject:AgentWork", trace)
        result = last_json(output)
        self.assertEqual(result["status"], "configured")
        self.assertEqual(result["previous_sharing_model"], "Private")
        self.assertEqual(result["sharing_model"], "Read")
        self.assertEqual(result["external_sharing_model"], "Private")
        self.assertTrue(result["changed"])

    def test_read_model_is_reused_without_deploy(self):
        with FakeSf() as fake:
            rc, output = fake.run(["org"], {"FAKE_CURRENT_MODEL": "Read"})
            trace = fake.read_state("trace")

        self.assertEqual(rc, 0, output)
        self.assertNotIn("project deploy start", trace)
        result = last_json(output)
        self.assertEqual(result["status"], "reused")
        self.assertFalse(result["changed"])

    def test_plan_reports_action_without_deploy(self):
        with FakeSf() as fake:
            rc, output = fake.run(["org", "--plan"])
            trace = fake.read_state("trace")

        self.assertEqual(rc, 2, output)
        self.assertNotIn("project deploy start", trace)
        result = last_json(output)
        self.assertEqual(result["status"], "action_needed")
        self.assertTrue(result["dry_run"])

    def test_production_blocks_before_deploy(self):
        with FakeSf() as fake:
            rc, output = fake.run(
                ["org", "--confirm-org-wide-visibility"],
                {"FAKE_PRODUCTION": "1"},
            )
            trace = fake.read_state("trace")

        self.assertEqual(rc, 1, output)
        self.assertNotIn("project deploy start", trace)
        self.assertIn("production", last_json(output)["blocking_issue"].lower())

    def test_developer_edition_is_safe_for_confirmed_change(self):
        with FakeSf() as fake:
            rc, output = fake.run(
                ["org", "--confirm-org-wide-visibility"],
                {"FAKE_DEVELOPER_EDITION": "1"},
            )

        self.assertEqual(rc, 0, output)
        self.assertEqual(last_json(output)["status"], "configured")

    def test_failed_readback_blocks(self):
        with FakeSf() as fake:
            rc, output = fake.run(
                ["org", "--confirm-org-wide-visibility"],
                {"FAKE_READBACK_MODEL": "Private"},
            )

        self.assertEqual(rc, 1, output)
        result = last_json(output)
        self.assertEqual(result["status"], "blocked")
        self.assertIn("read-back", result["blocking_issue"])

    def test_change_requires_explicit_org_wide_confirmation(self):
        with FakeSf() as fake:
            rc, output = fake.run(["org"])
            trace = fake.read_state("trace")

        self.assertEqual(rc, 1, output)
        self.assertNotIn("project deploy start", trace)
        self.assertIn("confirm-org-wide-visibility", last_json(output)["blocking_issue"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
