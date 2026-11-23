"""Behavioral checks for the conditional grounding instruction dependency."""
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "metadata_grounding_guard.py"
spec = importlib.util.spec_from_file_location("metadata_grounding_guard", SOURCE)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


class GroundingGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.skill = self.root / "SKILL.md"
        self.skill.write_text("Grounding instructions")

    def event(self, event="PreToolUse", tool="mcp__metadata-grounding__query_metadata",
              args=None, session="one", **extra):
        return {"hook_event_name": event, "tool_name": tool,
                "tool_input": args or {}, "session_id": session, **extra}

    def run_hook(self, payload):
        return guard.handle(payload, self.root / "config", self.skill)

    def allowed(self, payload=None):
        return not self.run_hook(payload or self.event())

    def load(self, session="one", response=None, skill=None):
        return self.run_hook(self.event(
            "PostToolUse", "Skill", {"skill": skill or guard.QUALIFIED_SKILL},
            session=session, tool_use_id="real-successful-load",
            tool_response=response if response is not None else
            {"success": True, "commandName": guard.QUALIFIED_SKILL}))

    def test_blocks_until_successful_native_skill_result(self):
        self.assertFalse(self.allowed())
        self.load()
        self.assertTrue(self.allowed())

    def test_attempted_skill_dispatch_does_not_grant(self):
        self.run_hook(self.event("PreToolUse", "Skill", {"skill": guard.QUALIFIED_SKILL}))
        self.assertFalse(self.allowed())

    def test_failed_and_unknown_skill_results_do_not_grant(self):
        for response in [{"success": False}, {"success": True}, {"success": True, "is_error": True},
                         {"success": True, "commandName": "unrelated"}, None, "Error loading skill"]:
            payload = self.event("PostToolUse", "Skill", {"skill": guard.QUALIFIED_SKILL},
                                 tool_response=response)
            self.run_hook(payload)
            self.assertFalse(self.allowed(), response)

    def test_failed_tool_event_does_not_grant(self):
        self.run_hook(self.event("PostToolUseFailure", "Skill", {"skill": guard.QUALIFIED_SKILL},
                                 tool_response={"success": True, "commandName": guard.QUALIFIED_SKILL}))
        self.assertFalse(self.allowed())

    def test_foreign_namespace_does_not_grant(self):
        self.load(skill="other-plugin:" + guard.SKILL)
        self.assertFalse(self.allowed())

    def test_session_isolation(self):
        self.load()
        self.assertFalse(self.allowed(self.event(session="two")))
        self.assertTrue(self.allowed())

    def test_compaction_and_resume_reset(self):
        for event in ["PostCompact", "SessionStart", "SessionEnd"]:
            self.load()
            self.run_hook(self.event(event))
            self.assertFalse(self.allowed(), event)

    def test_updated_skill_requires_another_read(self):
        self.load()
        self.skill.write_text("New grounding instructions")
        self.assertFalse(self.allowed())
        self.load()
        self.assertTrue(self.allowed())

    def test_unrelated_mcp_and_cli_operations_stay_available(self):
        for tool, args in [
            ("Bash", {"command": "sf data query --query SELECT"}),
            ("mcp__warehouse__query_metadata", {}),
            ("mcp__metadata-grounding__list_tools", {}),
            ("mcp__salesforce__dispatch", {"operationId": "runReport"}),
            ("mcp__salesforce__dispatch", {"query": "queryMetadata"}),
        ]:
            self.assertTrue(self.allowed(self.event(tool=tool, args=args)), tool)

    def test_direct_aliases_and_readonly_dispatch_are_covered(self):
        for tool, args in [
            ("mcp__metadata_grounding__search_metadata", {}),
            ("mcp__salesforce-metadata-grounding__describe_metadata", {}),
            ("mcp__salesforce-headless-360__dispatch_readonly", {"operationId": "searchMetadata"}),
            ("mcp__salesforce__dispatch", {"operationId": "queryMetadata"}),
            ("mcp__salesforce__describe", {"operation_id": "describeMetadata"}),
        ]:
            self.assertFalse(self.allowed(self.event(tool=tool, args=args)), tool)

    def test_missing_session_does_not_use_shared_state(self):
        self.load()
        self.assertFalse(self.allowed(self.event(session="")))

    def test_missing_skill_is_reported_without_installing_anything(self):
        self.load()
        self.skill.unlink()
        result = self.run_hook(self.event())
        self.assertIn("missing", result["hookSpecificOutput"]["permissionDecisionReason"])

    def test_corrupt_state_does_not_grant(self):
        path = guard.state_path("one", self.root / "config")
        path.parent.mkdir(parents=True)
        path.write_text("{corrupt")
        self.assertFalse(self.allowed())

    def test_private_state_and_untrusted_session_path(self):
        self.load(session="../../escape")
        path = guard.state_path("../../escape", self.root / "config")
        self.assertEqual(path.parent, self.root / "config/metadata-grounding-guard")
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_malformed_input_is_a_blocking_host_error(self):
        for raw in ["{", "[]"]:
            p = subprocess.run([sys.executable, str(SOURCE)], input=raw, text=True, capture_output=True)
            self.assertEqual(p.returncode, 2)
            self.assertIn("malformed", p.stderr)

    def test_existing_off_and_advisory_modes_are_respected(self):
        self.assertEqual(guard.handle(self.event(), self.root, self.skill, "off"), {})
        advisory = guard.handle(self.event(), self.root, self.skill, "advisory")
        self.assertIn("additionalContext", advisory["hookSpecificOutput"])
        self.assertNotIn("permissionDecision", advisory["hookSpecificOutput"])

    def test_mode_precedence_matches_plugin(self):
        self.assertEqual(guard.mode_from_env({}), "enforce")
        self.assertEqual(guard.mode_from_env({"CLAUDE_PLUGIN_OPTION_SKILLS_FIRST": "off"}), "off")
        self.assertEqual(guard.mode_from_env({"SF_PLUGIN_SKILLS_FIRST": "advisory",
                                             "CLAUDE_PLUGIN_OPTION_SKILLS_FIRST": "off"}), "advisory")
        self.assertEqual(guard.mode_from_env({"SF_PLUGIN_SKILLS_FIRST": "invalid",
                                             "CLAUDE_PLUGIN_OPTION_SKILLS_FIRST": "off"}), "enforce")


if __name__ == "__main__":
    unittest.main()
