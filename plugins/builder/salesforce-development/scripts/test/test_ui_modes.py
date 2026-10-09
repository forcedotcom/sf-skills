#!/usr/bin/env python3
"""Surface-by-mode contracts for ambient Salesforce plugin UI."""
from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import ExitStack, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from _test_support import load_module, strip_ansi

SCRIPTS = Path(__file__).resolve().parent.parent
PLUGIN_ROOT = SCRIPTS.parent
SFX = load_module(SCRIPTS / "sf_context.py", "ui_modes_context")
NR = load_module(SCRIPTS / "nudge_rules.py", "ui_modes_nudge_rules")
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

# A stand-in for the SessionStart nudge seed (journey-nudges Phase 4): the exact
# selection logic isn't under test here, just that cmd_detect seeds the signature
# with whatever `_select_inline_nudge` returns. message/action (journey-nudges
# Phase 5) are needed too, since the seeded candidate now also feeds the
# model-facing "next action" text via `_nudge_next_action_text`.
SEED_CANDIDATE = SimpleNamespace(
    dedup_key="test.seed", evidence_fp="v1",
    message="Seed message.", action="sf seed action",
)


class UiModeContracts(unittest.TestCase):
    def test_manifest_declares_ui_mode_string_option_with_full_default(self):
        plugin = json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))
        config = plugin["userConfig"]
        self.assertIn("ui_mode", config)
        self.assertEqual(config["ui_mode"]["type"], "string")
        self.assertEqual(config["ui_mode"]["default"], "full")
        self.assertEqual(config["ui_mode"]["options"], ["full", "plain", "off"])
        self.assertIn("full", config["ui_mode"]["description"])
        self.assertIn("plain", config["ui_mode"]["description"])
        self.assertIn("off", config["ui_mode"]["description"])

    def test_missing_empty_and_invalid_values_fail_safe_to_full(self):
        # "compact" was retired — a stored value maps to "plain" (nearest surviving
        # reduced-chrome surface); other unknown values still fail safe to "full".
        for raw, expected in ((None, "full"), ("", "full"), ("bogus", "full"),
                              ("FULL", "full"), ("compact", "plain"),
                              ("plain", "plain"), ("off", "off")):
            env = {} if raw is None else {"CLAUDE_PLUGIN_OPTION_UI_MODE": raw}
            with self.subTest(raw=raw), mock.patch.dict(os.environ, env, clear=True):
                self.assertEqual(SFX._ui_mode(), expected)

    def test_ambient_surface_mode_matrix_and_no_color_orthogonality(self):
        full = "\x1b[32mFULL ART ●◉○\x1b[0m"
        # A real SEV_ROUTINE, non-hygiene candidate → the "Try next" band (journey-nudges
        # Phase 8), so the plain surface's band WORD is asserted non-vacuously.
        candidate = NR.Candidate(
            id="build.empty-scaffold", stage="Build", severity=NR.SEV_ROUTINE,
            confidence=NR.CONFIDENCE_A, action="sf lightning generate component",
            message="Your project has no local source yet.", dedup_key="build.empty-scaffold",
        )
        # Mode taxonomy consolidated to full / plain / off (the legacy "compact"
        # alias now resolves to "plain" in _ui_mode, so it produces the same
        # accessible semantic block — no separate one-line projection).
        cases = {}
        for mode in ("full", "compact", "plain", "off"):
            with mock.patch.dict(os.environ, {"CLAUDE_PLUGIN_OPTION_UI_MODE": mode}, clear=True):
                cases[mode] = SFX._ambient_surface(
                    full, STATE, project_name="acme", candidate=candidate)
        self.assertEqual(cases["full"], full)
        self.assertIsNone(cases["off"])
        # The legacy "compact" alias projects identically to "plain".
        self.assertEqual(cases["compact"], cases["plain"])
        self.assertNotIn("FULL ART", cases["plain"])
        self.assertNotIn("\x1b", cases["plain"])
        self.assertNotRegex(cases["plain"], r"[●◉○]")
        self.assertIn("Current stage: Project", cases["plain"])
        # Content parity with the primary surfaces: no Reached / No-evidence word-lists,
        # and the semantic-plain surface stays emoji-free — the band is announced by its
        # plain WORD instead ("Try next:"), replacing the old literal "Next:".
        self.assertNotIn("Reached:", cases["plain"])
        self.assertNotIn("No evidence:", cases["plain"])
        self.assertNotRegex(cases["plain"], r"[❌⚠🚀✨]")
        self.assertIn("Try next: Your project has no local source yet.", cases["plain"])
        # This accessibility surface is DELIBERATELY excluded from the two-line arrow
        # reformat (journey-nudges Phase 8): a literal "→" reads poorly to a screen
        # reader. The action stays inline after " — ", and no arrow leader appears.
        self.assertIn(" — ", cases["plain"])
        self.assertNotIn("→", cases["plain"])
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
                        mock.patch.object(
                            SFX, "_select_inline_nudge", return_value=SEED_CANDIDATE) as select_nudge, \
                        mock.patch.object(SFX, "_record_nudge_signature") as signature, \
                        mock.patch.object(SFX.sys, "stdin", payload), redirect_stdout(out):
                    self.assertEqual(SFX.cmd_detect(), 0)
                if source == "compact":
                    # The compact-resume reinject short-circuits before any journey/
                    # nudge state is touched at all.
                    welcomed.assert_not_called()
                    entered.assert_not_called()
                    select_nudge.assert_not_called()
                    signature.assert_not_called()
                elif mode == "off":
                    # journey-nudges Phase 5: the model-facing context (additionalContext)
                    # is emitted unconditionally, regardless of ui_mode, and now derives
                    # its "next action" text from the SAME selected candidate as every
                    # other surface — so _select_inline_nudge still runs here. Only the
                    # VISIBLE ambient surface and its welcomed/entered/signature
                    # bookkeeping are skipped, since `_ambient_surface` returns None.
                    welcomed.assert_not_called()
                    entered.assert_not_called()
                    signature.assert_not_called()
                else:
                    welcomed.assert_called_once_with("ui-mode")
                    entered.assert_called_once_with("ui-mode")
                    signature.assert_called_once_with("ui-mode", SEED_CANDIDATE)
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
        results = {mode: self.capture_detect(mode) for mode in ("full", "plain", "off")}
        contexts = {
            result["hookSpecificOutput"]["additionalContext"] for result in results.values()
        }
        self.assertEqual(len(contexts), 1)
        self.assertIn("skills first", contexts.pop().lower())
        self.assertIn(SFX.BANNER_WORDMARK, strip_ansi(results["full"]["systemMessage"]))
        self.assertNotIn(SFX.BANNER_WORDMARK, results["plain"]["systemMessage"])
        self.assertIn("Current stage: Project", results["plain"]["systemMessage"])
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
                self.assertFalse(SFX._nudge_painted_this_turn(context))
                self.assertFalse(SFX._welcomed_this_session("ui-off"))
                self.assertFalse(SFX._entered_this_session("ui-off"))
                self.assertIsNone(SFX._last_nudge_signature("ui-off"))
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
                self.assertFalse(SFX._nudge_painted_this_turn(context))
                self.assertIsNone(SFX._last_nudge_signature("wayfinder-off"))
            finally:
                SFX._PROMPT_RUNTIME_DIR = old_runtime
                SFX._WELCOME_MARKER_DIR = old_markers
                os.chdir(old_cwd)

    def test_resolution_trace_is_ambient_but_keeps_evidence_side_effects(self):
        payload = {"tool_input": {"skill": "salesforce-development:platform-apex-generate"}}
        results = {}
        for mode in ("full", "plain", "off"):
            out = io.StringIO()
            with mock.patch.dict(os.environ, {"CLAUDE_PLUGIN_OPTION_UI_MODE": mode}, clear=True), \
                    mock.patch.object(SFX, "_read_hook_payload", return_value=payload), \
                    redirect_stdout(out):
                self.assertEqual(SFX.cmd_resolution_trace(), 0)
            results[mode] = json.loads(out.getvalue())
        self.assertIn("systemMessage", results["full"])
        self.assertNotIn("\x1b", results["plain"]["systemMessage"])
        self.assertNotIn("systemMessage", results["off"])

    def test_explicit_readiness_and_safety_renderers_ignore_ui_mode(self):
        report = {"tools": [{
            "name": "Salesforce CLI", "status": "critical",
            "message": "Install the CLI before continuing.",
        }]}
        readiness = []
        for mode in ("full", "plain", "off"):
            with mock.patch.dict(os.environ, {"CLAUDE_PLUGIN_OPTION_UI_MODE": mode}, clear=True):
                readiness.append(SFX.render_readiness_text(report))
        self.assertEqual(len(set(readiness)), 1)
        self.assertIn("BLOCKED", readiness[0])
        self.assertIn("Install the CLI", readiness[0])

    def test_explicit_journey_output_is_identical_in_every_mode(self):
        """`cmd_journey`'s bare stdout is the `journey hints` list now (journey-nudges
        Phase 3), resolved via `_journey_state_with_org` + `_all_journey_hints` rather
        than the old bare `_journey_state`. Mock both so the render is deterministic
        and isolated from the real filesystem/git facts `_all_journey_hints` would
        otherwise read, then confirm the ambient UI mode never affects this
        model-reproduced surface."""
        hint = SimpleNamespace(message="Add tests for 3 changed classes.",
                                action="platform-apex-test-generate")
        outputs = []
        for mode in ("full", "plain", "off"):
            out = io.StringIO()
            with mock.patch.dict(os.environ, {"CLAUDE_PLUGIN_OPTION_UI_MODE": mode}, clear=True), \
                    mock.patch.object(SFX, "_journey_state_with_org",
                                       return_value=(STATE, Path("/tmp/ui-mode-fixture"), {"alias": "dev"})), \
                    mock.patch.object(SFX, "_all_journey_hints", return_value=[hint]), \
                    redirect_stdout(out):
                self.assertEqual(SFX.cmd_journey([]), 0)
            outputs.append(out.getvalue())
        self.assertEqual(len(set(outputs)), 1)
        # The visible surface is the journey hints list now (no state summary); assert
        # a mode-invariant hint line rather than the removed "current: Build" line.
        self.assertIn("Add tests for 3 changed classes.", outputs[0])


PROMPT_ORIENTATION = "where am I in the build and what should I do next"
PROMPT_STATUS = "what is the status of this project"
PROMPT_OVERVIEW = "what can I do here?"
PROMPT_ORDINARY = "add a description to the Industry field on Account"
PROMPT_TRIP = "I want to build an app on Salesforce"

# Sentinels for the full renders: the full-surface assertions only need to know
# WHICH surface painted, and the plain/off assertions that none of them leaked.
FULL_STATUS = "FULL-STATUS-SURFACE"
FULL_WELCOME = "FULL-WELCOME-SURFACE"
FULL_NUDGE = "FULL-NUDGE-SURFACE"
FULL_OVERVIEW = "FULL-OVERVIEW-SURFACE"
FULL_SENTINELS = (FULL_STATUS, FULL_WELCOME, FULL_NUDGE, FULL_OVERVIEW)
RUNTIME_DIRS = (
    "_WELCOME_MARKER_DIR", "_PROMPT_RUNTIME_DIR", "_PLUGIN_PROPOSAL_DIR",
    "_PLUGIN_INSTALL_PENDING_DIR", "_PLUGIN_FLOW_DIR", "_PLUGIN_LAST_OFFER_DIR",
    "_DRIVE_MARKER_DIR",
)


class NaturalLanguagePaintUiModes(unittest.TestCase):
    """W-24363502 / forcedotcom/sf-skills#340: the UserPromptSubmit status,
    orientation, and overview questions follow ui_mode. "off" is fully silent (no
    systemMessage AND no additionalContext) and records nothing; "plain" paints the
    semantic-plain projection with a note that claims only what it shows; typed slash
    commands still paint in every mode."""

    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.base = Path(self._td.name)
        self.project = self.base / "checkout"
        self.project.mkdir()
        self.project.joinpath("sfdx-project.json").write_text("{}", encoding="utf-8")
        self.outside = self.base / "elsewhere"
        self.outside.mkdir()
        self._old_cwd = Path.cwd()
        # Every runtime dir cmd_orientation_paint reads or writes. The plugin-flow
        # dirs are derived from _PROMPT_RUNTIME_DIR at import, so each is re-pointed
        # explicitly rather than left on the shared temp dir.
        runtime = self.base / "runtime"
        self._old_dirs = {name: getattr(SFX, name) for name in RUNTIME_DIRS}
        SFX._WELCOME_MARKER_DIR = self.base / "markers"
        SFX._PROMPT_RUNTIME_DIR = runtime
        for name in RUNTIME_DIRS[2:]:
            setattr(SFX, name, runtime / self._old_dirs[name].name)
        self._prompt_seq = 0

    def tearDown(self):
        for name, value in self._old_dirs.items():
            setattr(SFX, name, value)
        os.chdir(self._old_cwd)
        self._td.cleanup()

    def _env(self, mode):
        # Recommendation scoring is orthogonal to ui_mode; keep it out of the way.
        env = {"SF_PLUGIN_MATCH_SENSITIVITY": "off"}
        if mode is not None:
            env["CLAUDE_PLUGIN_OPTION_UI_MODE"] = mode
        return mock.patch.dict(os.environ, env, clear=True)

    def _render_mocks(self):
        patches = (
            mock.patch.object(SFX, "_resolve_position_and_org",
                              return_value=(STATE, {"alias": "dev"})),
            mock.patch.object(SFX, "_journey_state", return_value=STATE),
            mock.patch.object(SFX, "_select_inline_nudge", return_value=SEED_CANDIDATE),
            mock.patch.object(SFX, "project_meta", return_value={"name": "acme"}),
            mock.patch.object(SFX, "project_stats", return_value={}),
            mock.patch.object(SFX, "git_status_line", return_value=""),
            mock.patch.object(SFX, "_live_mcp_summary", return_value=""),
            mock.patch.object(SFX, "render_status_surface", return_value=FULL_STATUS),
            mock.patch.object(SFX, "_render_getting_started_welcome",
                              return_value=FULL_WELCOME),
            mock.patch.object(SFX, "_render_nudge_inline", return_value=[FULL_NUDGE]),
            mock.patch.object(SFX, "_render_overview_paint", return_value=FULL_OVERVIEW),
            mock.patch.object(SFX, "_welcome_test_drive_pointer", return_value=None),
            mock.patch.object(SFX, "_arm_overview_test_drive_proposal"),
        )
        stack = ExitStack()
        mocks = {p.attribute: stack.enter_context(p) for p in patches}
        return stack, mocks

    def paint(self, mode, prompt, *, session_id, where=None):
        """Run one UserPromptSubmit turn; return (parsed output, prompt context, mocks)."""
        os.chdir(where or self.project)
        self._prompt_seq += 1
        payload = {"prompt": prompt, "session_id": session_id,
                   "prompt_id": f"prompt-{self._prompt_seq}"}
        out = io.StringIO()
        stack, mocks = self._render_mocks()
        with stack, self._env(mode), redirect_stdout(out):
            context = SFX._prompt_context(payload, rotate_fallback=False)
            self.assertEqual(SFX.cmd_orientation_paint(
                payload=payload, prompt_context=context), 0)
        return json.loads(out.getvalue()), context, mocks

    def assert_silent(self, result, context, session_id):
        self.assertEqual(result, {"continue": True})
        self.assertFalse(SFX._nudge_painted_this_turn(context))
        self.assertFalse(SFX._welcomed_this_session(session_id))
        self.assertFalse(SFX._entered_this_session(session_id))
        self.assertIsNone(SFX._last_nudge_signature(session_id))

    def assert_plain(self, result, project="acme"):
        visible = result["systemMessage"]
        note = result["hookSpecificOutput"]["additionalContext"]
        self.assertTrue(visible.startswith("Salesforce development\n"), visible)
        self.assertIn(f"Project: {project}", visible)
        self.assertIn("Current stage: Project", visible)
        self.assertIn("Seed message.", visible)
        # The note's "current stage" is the same stage the plain line shows.
        self.assertIn("current stage: Project", note)
        self.assertNotIn("\x1b", visible)
        for sentinel in FULL_SENTINELS:
            self.assertNotIn(sentinel, visible)
        # The plain note claims only the nudge it shows — never the welcome's reply
        # shaping or the full status surface's org/project bands.
        self.assertIn("journey nudge is already visible", note)
        self.assertNotIn("one or two sentences", note)
        self.assertNotIn("Salesforce status", note)

    def test_in_project_status_and_orientation_by_mode(self):
        for prompt in (PROMPT_STATUS, PROMPT_ORIENTATION):
            results = {}
            for mode in (None, "full", "plain", "off"):
                sid = f"{prompt[:5]}-{mode}"
                with self.subTest(prompt=prompt, mode=mode):
                    result, context, mocks = self.paint(mode, prompt, session_id=sid)
                    results[mode] = result
                    pointer = mocks["_welcome_test_drive_pointer"]
                    if mode == "off":
                        self.assert_silent(result, context, sid)
                        # Off decides before any probe or render.
                        mocks["_resolve_position_and_org"].assert_not_called()
                        mocks["_journey_state"].assert_not_called()
                        pointer.assert_not_called()
                        continue
                    # The test-drive pointer is welcome chrome: only the full
                    # first-touch orientation welcome offers it.
                    if prompt == PROMPT_ORIENTATION and mode != "plain":
                        pointer.assert_called_once_with(sid)
                    else:
                        pointer.assert_not_called()
                    if mode == "plain":
                        self.assert_plain(result)
                    elif prompt == PROMPT_STATUS:
                        self.assertEqual(result["systemMessage"], FULL_STATUS)
                        self.assertIn("Salesforce status and the journey nudge",
                                      result["hookSpecificOutput"]["additionalContext"])
                    else:
                        self.assertIn(FULL_WELCOME, result["systemMessage"])
                        self.assertIn("one or two sentences",
                                      result["hookSpecificOutput"]["additionalContext"])
                    # A visible paint (full or plain) is a real first surface.
                    self.assertTrue(SFX._welcomed_this_session(sid))
                    self.assertTrue(SFX._entered_this_session(sid))
            # Unset is the full default, byte for byte.
            self.assertEqual(results[None], results["full"])

    def test_in_project_overview_is_silent_only_under_off(self):
        for mode in (None, "full", "plain", "off"):
            sid = f"overview-{mode}"
            with self.subTest(mode=mode):
                result, context, mocks = self.paint(mode, PROMPT_OVERVIEW, session_id=sid)
                arm = mocks["_arm_overview_test_drive_proposal"]
                if mode == "off":
                    self.assert_silent(result, context, sid)
                    # No test-drive proposal for a CTA that was never shown.
                    arm.assert_not_called()
                else:
                    self.assertIn(FULL_OVERVIEW, result["systemMessage"])
                    arm.assert_called_once_with(sid)

    def test_off_ordinary_then_orientation_never_paints_a_banner(self):
        sid = "off-sequence"
        first, context, mocks = self.paint("off", PROMPT_ORDINARY, session_id=sid)
        self.assert_silent(first, context, sid)
        # The hidden first-touch nudge is decided before its org probe.
        mocks["_resolve_position_and_org"].assert_not_called()
        mocks["_journey_state"].assert_not_called()
        second, context, _ = self.paint("off", PROMPT_ORIENTATION, session_id=sid)
        self.assert_silent(second, context, sid)
        # Switching to full mid-session: nothing was shown, so the first VISIBLE
        # surface is the welcome — once — and later asks get the bare nudge.
        third, _, _ = self.paint("full", PROMPT_ORIENTATION, session_id=sid)
        self.assertIn(FULL_WELCOME, third["systemMessage"])
        fourth, _, _ = self.paint("full", PROMPT_ORIENTATION, session_id=sid)
        self.assertIn(FULL_NUDGE, fourth["systemMessage"])
        self.assertNotIn(FULL_WELCOME, fourth["systemMessage"])

    def test_plain_welcome_counts_as_shown(self):
        sid = "plain-then-full"
        self.assert_plain(self.paint("plain", PROMPT_ORIENTATION, session_id=sid)[0])
        # The plain paint spends the nudge's dedupe and cap bookkeeping like any shown one.
        self.assertIsNotNone(SFX._last_nudge_signature(sid))
        self.assertIn(SEED_CANDIDATE.dedup_key, SFX._nudge_cap_keys(sid))
        later, _, _ = self.paint("full", PROMPT_ORIENTATION, session_id=sid)
        self.assertIn(FULL_NUDGE, later["systemMessage"])
        self.assertNotIn(FULL_WELCOME, later["systemMessage"])

    def test_plain_status_counts_as_shown(self):
        sid = "plain-status"
        self.assert_plain(self.paint("plain", PROMPT_STATUS, session_id=sid)[0])
        self.assertIsNotNone(SFX._last_nudge_signature(sid))
        self.assertIn(SEED_CANDIDATE.dedup_key, SFX._nudge_cap_keys(sid))

    def test_outside_project_orientation_and_overview_by_mode(self):
        for prompt in (PROMPT_ORIENTATION, PROMPT_OVERVIEW):
            for mode in (None, "full", "plain", "off"):
                sid = f"side-a-{prompt[:5]}-{mode}"
                with self.subTest(prompt=prompt, mode=mode):
                    # The session is tripped by an earlier Salesforce mention.
                    SFX._record_model_noted(sid)
                    result, context, mocks = self.paint(
                        mode, prompt, session_id=sid, where=self.outside)
                    if mode == "off":
                        self.assertEqual(result, {"continue": True})
                        self.assertFalse(SFX._nudge_painted_this_turn(context))
                        self.assertIsNone(SFX._last_nudge_signature(sid))
                        # Off decides before any state resolution or render, and arms
                        # no test-drive proposal for a CTA that was never shown.
                        mocks["_journey_state"].assert_not_called()
                        mocks["_render_overview_paint"].assert_not_called()
                        mocks["_arm_overview_test_drive_proposal"].assert_not_called()
                    elif prompt == PROMPT_OVERVIEW:
                        self.assertIn(FULL_OVERVIEW, result["systemMessage"])
                    elif mode == "plain":
                        self.assert_plain(result, project="no project")
                    else:
                        self.assertIn(FULL_NUDGE, result["systemMessage"])

    def journey_hook(self, mode, *, session_id, real_state=False):
        """Run the PostToolUse `discover journey` hook for the turn `paint` just ran.

        `real_state` leaves `_journey_state_with_org` unmocked so the project name and
        stage come from the real derivation of the current directory."""
        payload = {"tool_input": {"command": "sf-context discover journey"},
                   "session_id": session_id, "prompt_id": f"prompt-{self._prompt_seq}"}
        out = io.StringIO()
        stack, mocks = self._render_mocks()
        if not real_state:
            mocks["_journey_state_with_org"] = stack.enter_context(mock.patch.object(
                SFX, "_journey_state_with_org", return_value=(STATE, self.project, {})))
        with stack, self._env(mode), redirect_stdout(out):
            self.assertEqual(SFX.cmd_journey_paint(payload), 0)
        return json.loads(out.getvalue()), mocks

    def journey_turn_context(self, session_id):
        return SFX._prompt_context(
            {"session_id": session_id, "prompt_id": f"prompt-{self._prompt_seq}"},
            rotate_fallback=False)

    def test_off_orientation_then_model_run_journey_stays_silent(self):
        # The SessionStart directive still routes "where am I?" to `discover journey`,
        # and the off prompt paint claims no turn, so the PostToolUse paint must honor
        # the mode itself rather than rely on the dedupe.
        sid = "off-journey"
        first, context, _ = self.paint("off", PROMPT_ORIENTATION, session_id=sid)
        self.assert_silent(first, context, sid)
        result, mocks = self.journey_hook("off", session_id=sid)
        self.assertEqual(result, {"continue": True})
        # Off decides before the org-probing state resolution and nudge selection.
        mocks["_journey_state_with_org"].assert_not_called()
        mocks["_select_inline_nudge"].assert_not_called()
        mocks["_render_nudge_inline"].assert_not_called()
        self.assertFalse(SFX._nudge_painted_this_turn(context))
        self.assertIsNone(SFX._last_nudge_signature(sid))

    def test_plain_journey_paint_is_the_plain_projection(self):
        sid = "plain-journey"
        os.chdir(self.project)
        self._prompt_seq += 1  # a fresh turn the prompt hook did not paint
        result, mocks = self.journey_hook("plain", session_id=sid)
        self.assert_plain(result)
        mocks["_render_nudge_inline"].assert_not_called()
        # A plain paint claims the turn and spends the shown-once bookkeeping.
        self.assertTrue(SFX._nudge_painted_this_turn(self.journey_turn_context(sid)))
        self.assertIsNotNone(SFX._last_nudge_signature(sid))
        self.assertIn(SEED_CANDIDATE.dedup_key, SFX._nudge_cap_keys(sid))

    def test_plain_journey_paint_outside_a_project_names_no_project(self):
        # Unmocked state: the project line comes from the derived journey context,
        # not project_meta()'s "Project" placeholder.
        sid = "plain-journey-outside"
        os.chdir(self.outside)
        self._prompt_seq += 1
        result, _ = self.journey_hook("plain", session_id=sid, real_state=True)
        visible = result["systemMessage"]
        self.assertIn("Project: no project", visible)
        self.assertIn("Current stage: none yet", visible)
        self.assertNotIn("Project: Project", visible)

    def test_slash_commands_still_paint_under_off(self):
        os.chdir(self.project)
        for command, args, sentinel in (
            ("salesforce-development:status", "", FULL_STATUS),
            ("salesforce-development:discover", "overview", FULL_OVERVIEW),
        ):
            payload = {"hook_event_name": "UserPromptExpansion",
                       "expansion_type": "slash_command",
                       "command_name": command, "command_args": args}
            out = io.StringIO()
            stack, _ = self._render_mocks()
            with self.subTest(command=command), stack, self._env("off"), \
                    redirect_stdout(out):
                self.assertEqual(SFX.cmd_command_paint(payload=payload), 0)
                result = json.loads(out.getvalue())
                self.assertIn(sentinel, result["systemMessage"])
                self.assertTrue(result["hookSpecificOutput"]["additionalContext"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
