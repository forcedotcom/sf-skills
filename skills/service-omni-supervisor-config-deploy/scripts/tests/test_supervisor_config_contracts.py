#!/usr/bin/env python3
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _bootstrap import FakeSf, last_json  # noqa: E402


class PreservationTests(unittest.TestCase):
    def test_update_preserves_existing_surface_and_visibility(self):
        actions = json.dumps(["AllAgents.ChangeQueues", "AllAgents.ChangeSkills"])
        tabs = json.dumps(["Wallboard", "Agents"])
        with FakeSf() as fake:
            rc, output = fake.run(
                ["org", "1", "CaseQueue"],
                {
                    "FAKE_EXIST_ACTIONS": actions,
                    "FAKE_EXIST_TABS": tabs,
                    "FAKE_SKILL_VISIBILITY": "AnySkill",
                },
            )
            deployed_xml = fake.read_state("deployed.xml")
            trace = fake.read_state("trace")

        self.assertEqual(rc, 0, output)
        self.assertIn("<skillVisibility>AnySkill</skillVisibility>", deployed_xml)
        self.assertIn("OmniSupervisorActionType=AllAgents.ChangeQueues", trace)
        self.assertIn("OmniSupervisorActionType=AllAgents.ChangeSkills", trace)
        self.assertIn("OmniSupervisorTabType=Wallboard", trace)
        self.assertIn("OmniSupervisorTabType=Agents", trace)
        result = last_json(output)
        self.assertEqual(result["skill_visibility"], "AnySkill", output)
        self.assertEqual(result["surface_preservation"]["actions_restored"], 2, output)
        self.assertEqual(result["surface_preservation"]["tabs_restored"], 2, output)

    def test_explicit_visibility_overrides_existing_value(self):
        with FakeSf() as fake:
            rc, output = fake.run(
                ["org", "1", "CaseQueue", "", "AllSkills"],
                {"FAKE_SKILL_VISIBILITY": "AnySkill"},
            )
            deployed_xml = fake.read_state("deployed.xml")

        self.assertEqual(rc, 0, output)
        self.assertIn("<skillVisibility>AllSkills</skillVisibility>", deployed_xml)
        self.assertEqual(last_json(output)["skill_visibility"], "AllSkills", output)

    def test_surface_rows_that_survive_deploy_are_not_inserted_again(self):
        with FakeSf() as fake:
            rc, output = fake.run(
                ["org", "1", "CaseQueue"],
                {
                    "FAKE_EXIST_ACTIONS": json.dumps(["AllAgents.ChangeQueues"]),
                    "FAKE_EXIST_TABS": json.dumps(["Wallboard"]),
                    "FAKE_DEPLOY_PRESERVES_SURFACE": "1",
                },
            )
            trace = fake.read_state("trace")

        self.assertEqual(rc, 0, output)
        self.assertNotIn("data create", trace)
        self.assertNotIn("OmniSupervisorActionType=", trace)
        self.assertNotIn("OmniSupervisorTabType=", trace)
        result = last_json(output)
        self.assertEqual(result["surface_preservation"]["actions_restored"], 0, output)
        self.assertEqual(result["surface_preservation"]["tabs_restored"], 0, output)

    def test_unsupported_existing_surface_blocks_before_deploy(self):
        with FakeSf() as fake:
            rc, output = fake.run(
                ["org", "1", "CaseQueue"],
                {"FAKE_EXIST_TABS": json.dumps(["FlexipageType"])},
            )
            deployed_xml = fake.read_state("deployed.xml")

        self.assertEqual(rc, 1, output)
        self.assertEqual(deployed_xml, "")
        self.assertIn("cannot be safely restored", last_json(output)["blocking_issue"])

    def test_custom_config_identifier_controls_query_manifest_and_deploy(self):
        custom_config = "Regional_Supervisor"
        with FakeSf() as fake:
            rc, output = fake.run(
                ["org", "1", "CaseQueue", "", "AnySkill", custom_config],
                {
                    "FAKE_CONFIG_DN": custom_config,
                    "FAKE_MASTER_LABEL": "Regional Supervisor Team",
                },
            )
            deployed_xml = fake.read_state("deployed.xml")
            package_xml = fake.read_state("package.xml")
            trace = fake.read_state("trace")

        self.assertEqual(rc, 0, output)
        self.assertEqual(last_json(output)["config_developer_name"], custom_config)
        self.assertIn("<members>Regional_Supervisor</members>", package_xml)
        self.assertIn("<masterLabel>Regional Supervisor Team</masterLabel>", deployed_xml)
        self.assertIn("DeveloperName='Regional_Supervisor'", trace)
        self.assertNotIn("DeveloperName='Omni_Supervisor'", trace)

    def test_invalid_config_identifier_is_rejected_before_org_access(self):
        with FakeSf() as fake:
            rc, output = fake.run(
                ["org", "1", "CaseQueue", "", "AnySkill", "Bad Config' OR Name != '"],
            )
            trace = fake.read_state("trace")

        self.assertEqual(rc, 1, output)
        self.assertIn("Invalid config_developer_name", output)
        self.assertEqual(trace, "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
