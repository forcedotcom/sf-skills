#!/usr/bin/env python3
"""Surface-by-mode contracts for ambient Salesforce plugin UI."""
from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from _test_support import load_module, strip_ansi

SCRIPTS = Path(__file__).resolve().parent.parent
PLUGIN_ROOT = SCRIPTS.parent
SFX = load_module(SCRIPTS / "sf_context.py", "ui_modes_context")
PLUGIN_JSON = PLUGIN_ROOT / ".claude-plugin/plugin.json"

STATE = {
    "currentStage": "Build",
    "reason": "Create source metadata.",
    "stages": [
        {"name": "Connect", "status": "complete"},
        {"name": "Project", "status": "complete"},
        {"name": "Build", "status": "current"},
        {"name": "Test", "status": "future"},
        {"name": "Deploy", "status": "future"},
        {"name": "Observe", "status": "future"},
    ],
    "context": {"project": "acme", "orgAlias": "dev", "orgStatus": "unprobed"},
}


class UiModeContracts(unittest.TestCase):
    def test_manifest_declares_one_string_option_with_full_default(self):
        plugin = json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))
        config = plugin["userConfig"]
        self.assertEqual(set(config), {"ui_mode"})
        self.assertEqual(config["ui_mode"]["type"], "string")
        self.assertEqual(config["ui_mode"]["default"], "full")
        self.assertIn("full", config["ui_mode"]["description"])
        self.assertIn("compact", config["ui_mode"]["description"])
        self.assertIn("plain", config["ui_mode"]["description"])
        self.assertIn("off", config["ui_mode"]["description"])

    def test_missing_empty_and_invalid_values_fail_safe_to_full(self):
        for raw, expected in ((None, "full"), ("", "full"), ("bogus", "full"),
                              ("FULL", "full"), ("compact", "compact"),
                              ("plain", "plain"), ("off", "off")):
            env = {} if raw is None else {"CLAUDE_PLUGIN_OPTION_UI_MODE": raw}
            with self.subTest(raw=raw), mock.patch.dict(os.environ, env, clear=True):
                self.assertEqual(SFX._ui_mode(), expected)

    def test_ambient_surface_mode_matrix_and_no_color_orthogonality(self):
        full = "\x1b[32mFULL ART ●◉○\x1b[0m"
        cases = {}
        for mode in ("full", "compact", "plain", "off"):
            with mock.patch.dict(os.environ, {"CLAUDE_PLUGIN_OPTION_UI_MODE": mode}, clear=True):
                cases[mode] = SFX._ambient_surface(full, STATE, project_name="acme")
        self.assertEqual(cases["full"], full)
        self.assertIsNone(cases["off"])
        self.assertNotIn("FULL ART", cases["compact"])
        self.assertIn("salesforce-development", cases["compact"])
        self.assertIn("Build", cases["compact"])
        self.assertLessEqual(max(map(SFX._terminal_cell_width, cases["compact"].splitlines())), 80)
        self.assertNotIn("\x1b", cases["plain"])
        self.assertNotRegex(cases["plain"], r"[●◉○]")
        self.assertIn("Current stage: Build", cases["plain"])
        self.assertIn("Reached: Connect, Project", cases["plain"])
        self.assertIn("No evidence: Build, Test, Deploy, Observe", cases["plain"])
        with mock.patch.dict(os.environ, {
            "CLAUDE_PLUGIN_OPTION_UI_MODE": "full", "NO_COLOR": "1"
        }, clear=True):
            # NO_COLOR affects renderers, not mode selection or ambient policy.
            self.assertEqual(SFX._ui_mode(), "full")
            self.assertIsNotNone(SFX._ambient_surface(strip_ansi(full), STATE, project_name="acme"))

    def capture_detect(self, mode: str, *, source: str = "startup", session_title: str = "") -> dict:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "sfdx-project.json").write_text(
                '{"packageDirectories":[{"path":"force-app","default":true}]}',
                encoding="utf-8",
            )
            old = Path.cwd()
            os.chdir(root)
            try:
                payload = io.StringIO(json.dumps({
                    "source": source, "session_id": "ui-mode", "session_title": session_title,
                }))
                out = io.StringIO()
                with mock.patch.dict(os.environ, {"CLAUDE_PLUGIN_OPTION_UI_MODE": mode}, clear=True), \
                        mock.patch.object(SFX, "_derive_journey_state", return_value=STATE), \
                        mock.patch.object(SFX, "project_meta", return_value={"name": "acme"}), \
                        mock.patch.object(SFX, "project_stats", return_value={
                            key: 0 for key in (
                                "apex_src", "apex_test", "triggers", "lwc",
                                "aura", "objects", "permsets", "flows",
                            )
                        }), \
                        mock.patch.object(SFX, "_configured_target_alias", return_value="dev"), \
                        mock.patch.object(SFX, "_record_welcomed") as welcomed, \
                        mock.patch.object(SFX, "_record_entered") as entered, \
                        mock.patch.object(SFX, "_record_rail_signature") as signature, \
                        mock.patch.object(SFX.sys, "stdin", payload), redirect_stdout(out):
                    self.assertEqual(SFX.cmd_detect(), 0)
                if source == "compact" or mode == "off":
                    welcomed.assert_not_called()
                    entered.assert_not_called()
                    signature.assert_not_called()
                else:
                    welcomed.assert_called_once_with("ui-mode")
                    entered.assert_called_once_with("ui-mode")
                    signature.assert_called_once_with("ui-mode", STATE)
                return json.loads(out.getvalue())
            finally:
                os.chdir(old)

    def test_session_start_title_is_bounded_project_only_and_respects_user_title(self):
        startup = self.capture_detect("full")
        self.assertEqual(startup["sessionTitle"], "SF · acme")
        self.assertLessEqual(SFX._terminal_cell_width(startup["sessionTitle"]), 60)
        self.assertNotIn("dev", startup["sessionTitle"])
        self.assertNotIn("sessionTitle", self.capture_detect(
            "full", source="resume", session_title="My hand-named session"
        ))
        self.assertNotIn("sessionTitle", self.capture_detect("full", source="clear"))
        self.assertNotIn("sessionTitle", self.capture_detect("off"))

    def test_only_session_start_handler_has_a_status_message(self):
        plugin = json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))
        handlers = []
        for event, blocks in plugin["hooks"].items():
            for block in blocks:
                for handler in block.get("hooks", []):
                    if "statusMessage" in handler:
                        handlers.append((event, handler["statusMessage"]))
        self.assertEqual(handlers, [(
            "SessionStart", "Loading local Salesforce project context…"
        )])

    def test_session_start_context_is_invariant_and_off_only_hides_visible_ambient_ui(self):
        results = {mode: self.capture_detect(mode) for mode in ("full", "compact", "plain", "off")}
        contexts = {
            result["hookSpecificOutput"]["additionalContext"] for result in results.values()
        }
        self.assertEqual(len(contexts), 1)
        self.assertIn("skills first", contexts.pop().lower())
        self.assertIn(SFX.BANNER_WORDMARK, strip_ansi(results["full"]["systemMessage"]))
        self.assertNotIn(SFX.BANNER_WORDMARK, results["compact"]["systemMessage"])
        self.assertIn("Current stage: Build", results["plain"]["systemMessage"])
        self.assertNotIn("systemMessage", results["off"])

    def test_off_does_not_claim_or_mark_a_hidden_ambient_prompt_surface(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            root.joinpath("sfdx-project.json").write_text("{}", encoding="utf-8")
            old_cwd = Path.cwd()
            old_markers = SFX._WELCOME_MARKER_DIR
            old_runtime = SFX._PROMPT_RUNTIME_DIR
            os.chdir(root)
            SFX._WELCOME_MARKER_DIR = root / "markers"
            SFX._PROMPT_RUNTIME_DIR = root / "runtime"
            try:
                payload = {
                    "prompt": "add a field to Account",
                    "session_id": "ui-off",
                    "prompt_id": "prompt-1",
                }
                context = SFX._prompt_context(payload, rotate_fallback=False)
                out = io.StringIO()
                with mock.patch.dict(
                        os.environ, {"CLAUDE_PLUGIN_OPTION_UI_MODE": "off"}, clear=True), \
                        mock.patch.object(
                            SFX, "_resolve_position_and_org", return_value=(STATE, {"alias": "dev"})), \
                        mock.patch.object(SFX, "project_meta", return_value={"name": "acme"}), \
                        redirect_stdout(out):
                    self.assertEqual(SFX.cmd_orientation_paint(
                        payload=payload, prompt_context=context
                    ), 0)
                self.assertEqual(json.loads(out.getvalue()), {"continue": True})
                self.assertFalse(SFX._rail_painted_this_turn(context))
                self.assertFalse(SFX._welcomed_this_session("ui-off"))
                self.assertFalse(SFX._entered_this_session("ui-off"))
                self.assertIsNone(SFX._last_rail_signature("ui-off"))
            finally:
                SFX._PROMPT_RUNTIME_DIR = old_runtime
                SFX._WELCOME_MARKER_DIR = old_markers
                os.chdir(old_cwd)

    def test_off_wayfinder_keeps_model_note_without_claim_or_signature(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            root.joinpath("sfdx-project.json").write_text("{}", encoding="utf-8")
            old_cwd = Path.cwd()
            old_markers = SFX._WELCOME_MARKER_DIR
            old_runtime = SFX._PROMPT_RUNTIME_DIR
            os.chdir(root)
            SFX._WELCOME_MARKER_DIR = root / "markers"
            SFX._PROMPT_RUNTIME_DIR = root / "runtime"
            try:
                payload = {
                    "tool_input": {"command": "sf config set target-org dev"},
                    "session_id": "wayfinder-off",
                    "prompt_id": "prompt-1",
                }
                org = {
                    "alias": "dev", "edition": "Developer", "apiVersion": "65.0",
                    "username": "dev@example.com", "instanceUrl": "https://example.com",
                }
                out = io.StringIO()
                with mock.patch.dict(
                        os.environ, {"CLAUDE_PLUGIN_OPTION_UI_MODE": "off"}, clear=True), \
                        mock.patch.object(SFX, "get_target_org_detailed", return_value=("dev", "")), \
                        mock.patch.object(SFX, "resolve_org_info", return_value=org), \
                        mock.patch.object(SFX, "project_meta", return_value={"name": "acme"}), \
                        mock.patch.object(SFX, "project_stats", return_value={}), \
                        mock.patch.object(SFX, "git_status_line", return_value=""), \
                        mock.patch.object(SFX, "_derive_journey_state", return_value=STATE), \
                        redirect_stdout(out):
                    self.assertEqual(SFX.cmd_wayfinder(payload=payload), 0)
                result = json.loads(out.getvalue())
                self.assertIn("Target org is now 'dev'", result[
                    "hookSpecificOutput"]["additionalContext"])
                self.assertNotIn("systemMessage", result)
                context = SFX._prompt_context(payload, rotate_fallback=False)
                self.assertFalse(SFX._rail_painted_this_turn(context))
                self.assertIsNone(SFX._last_rail_signature("wayfinder-off"))
            finally:
                SFX._PROMPT_RUNTIME_DIR = old_runtime
                SFX._WELCOME_MARKER_DIR = old_markers
                os.chdir(old_cwd)

    def test_resolution_trace_is_ambient_but_keeps_evidence_side_effects(self):
        payload = {"tool_input": {"skill": "salesforce-development:platform-apex-generate"}}
        results = {}
        for mode in ("full", "compact", "plain", "off"):
            out = io.StringIO()
            with mock.patch.dict(os.environ, {"CLAUDE_PLUGIN_OPTION_UI_MODE": mode}, clear=True), \
                    mock.patch.object(SFX, "_read_hook_payload", return_value=payload), \
                    redirect_stdout(out):
                self.assertEqual(SFX.cmd_resolution_trace(), 0)
            results[mode] = json.loads(out.getvalue())
        self.assertIn("systemMessage", results["full"])
        self.assertIn("systemMessage", results["compact"])
        self.assertNotIn("\x1b", results["plain"]["systemMessage"])
        self.assertNotIn("systemMessage", results["off"])

    def test_explicit_readiness_and_safety_renderers_ignore_ui_mode(self):
        report = {"tools": [{
            "name": "Salesforce CLI", "status": "critical",
            "message": "Install the CLI before continuing.",
        }]}
        readiness = []
        for mode in ("full", "compact", "plain", "off"):
            with mock.patch.dict(os.environ, {"CLAUDE_PLUGIN_OPTION_UI_MODE": mode}, clear=True):
                readiness.append(SFX.render_readiness_text(report))
        self.assertEqual(len(set(readiness)), 1)
        self.assertIn("BLOCKED", readiness[0])
        self.assertIn("Install the CLI", readiness[0])

    def test_explicit_journey_output_is_identical_in_every_mode(self):
        outputs = []
        for mode in ("full", "compact", "plain", "off"):
            out = io.StringIO()
            with mock.patch.dict(os.environ, {"CLAUDE_PLUGIN_OPTION_UI_MODE": mode}, clear=True), \
                    mock.patch.object(SFX, "_journey_state", return_value=STATE), redirect_stdout(out):
                self.assertEqual(SFX.cmd_journey([]), 0)
            outputs.append(out.getvalue())
        self.assertEqual(len(set(outputs)), 1)
        self.assertIn("current: Build", outputs[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
