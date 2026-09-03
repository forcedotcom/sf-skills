#!/usr/bin/env python3
"""Unit tests for sf_telemetry.py — the consent-gated, scrubbed, local-only
usage-telemetry capture (Stream A of the telemetry plan).

These are the evidence that the plan's capture scope is FULLY met with NO gaps:

  1. Plan parity   — the event catalog and per-event field allowlist exactly
                     match the plan's §2.1/§2.2 schema (a removed/renamed event
                     or field fails the build).
  2. Every event   — each of the 7 events captures a well-formed line carrying
                     the full envelope + the plan's payload fields.
  3. Scrubbing     — the "never collected" guarantee (§2.4): flag values, custom
                     binary names/args, task prompts, and non-allowlisted fields
                     are dropped before write.
  4. Command tiers — A (sf/first-party full parse), B (known tool, category only),
                     C (unknown -> "other").
  5. Consent       — default-on; true hard-off discards the buffer; env opt-out
                     and CI gates; one-time first-run notice.
  6. session_end   — duration from the per-session marker; per-session event_count
                     isolation; path-injection-safe session ids.
  7. Manifest wiring — every event has a hook in .claude-plugin/plugin.json, so
                     "captured in code" also means "fired in a real session".

Offline & hermetic: no live org, no real `sf` spawn (org resolution is mocked),
state is isolated to a per-test temp dir via chdir. Stdlib unittest only (no
pytest/PyYAML) so it runs anywhere Python 3.9+ does — same bar as the sibling
test_sf_context.py.

Run: python3 plugins/builder/salesforce-development/scripts/test/test_sf_telemetry.py
"""
from __future__ import annotations

import importlib.util
import io
import json
import multiprocessing as mp
import os
import tempfile
import time
import unittest
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
from unittest import mock

# sf_telemetry.py is the sibling of this test's parent dir: scripts/test/ -> scripts/.
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
_MODULE_PATH = _SCRIPTS_DIR / "sf_telemetry.py"
_MANIFEST_PATH = _SCRIPTS_DIR.parent / ".claude-plugin" / "plugin.json"


def _load_module():
    spec = importlib.util.spec_from_file_location("sf_telemetry_under_test", _MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


sft = _load_module()


# --- Multiprocessing workers for the _ConsentLock cross-process tests -----------
# These run in SEPARATE processes (spawn) so they exercise real OS-level mutual
# exclusion — a same-process, synchronous test cannot detect a lock that fails to
# exclude across processes. Each worker loads its OWN sf_telemetry instance from the
# module path and shares only the on-disk lock file via SF_DEV_TELEMETRY_HOME.
def _mp_load_sft(module_path, home):
    os.environ["SF_DEV_TELEMETRY_HOME"] = home
    spec = importlib.util.spec_from_file_location(f"sft_mp_{os.getpid()}", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _mp_incr_worker(module_path, home, iters, q):
    """Do `iters` lock-protected read-modify-write increments on a shared counter,
    with a sleep inside the critical section to widen the window. If the lock truly
    excludes, no updates are lost and the sum across workers is exact."""
    try:
        s = _mp_load_sft(module_path, home)
        counter = Path(home) / "counter.txt"
        for _ in range(iters):
            with s._ConsentLock(timeout=60.0) as held:
                if not held:
                    q.put(("err", "worker failed to acquire"))
                    return
                v = int(counter.read_text()) if counter.exists() else 0
                time.sleep(0.002)  # widen the RMW window to expose lost updates
                counter.write_text(str(v + 1))
        q.put(("ok", True))
    except Exception as e:  # pragma: no cover - surfaced via the queue
        q.put(("err", repr(e)))


def _mp_try_acquire_worker(module_path, home, timeout, q):
    """Attempt a single bounded acquire; report whether it was held and how long it
    waited. Used to prove timeout-while-held and success-after-release."""
    try:
        s = _mp_load_sft(module_path, home)
        t0 = time.monotonic()
        with s._ConsentLock(timeout=timeout) as held:
            elapsed = time.monotonic() - t0
            if held:
                time.sleep(0.05)  # hold briefly so the parent can observe exclusion
            q.put(("ok", bool(held), elapsed))
    except Exception as e:  # pragma: no cover
        q.put(("err", repr(e), 0.0))


def _mp_acquire_and_die_worker(module_path, home, signal_path):
    """Acquire the lock and die WITHOUT releasing it (os._exit skips __exit__). The
    kernel must release the OS lock on process death — proving cleanup does not rely
    on unsafe age-based stealing. Signals via a FILE, not an mp.Queue: os._exit skips
    the queue's background feeder flush, so a queued item could be lost."""
    try:
        s = _mp_load_sft(module_path, home)
        lock = s._ConsentLock(timeout=30.0)
        held = lock.__enter__()
        Path(signal_path).write_text("held" if held else "nolock")
    except Exception as e:  # pragma: no cover
        try:
            Path(signal_path).write_text("err:" + repr(e))
        except OSError:
            pass
    os._exit(0)  # abrupt exit — no __exit__, no explicit unlock, fd closed by kernel


# --- The plan's schema, transcribed from the Telemetry Plan §2.1 / §2.2. --------
# This is the single source of truth the code is checked against. Changing the
# code's catalog without updating the plan (or vice-versa) fails PlanParityTests.
PLAN_EVENTS = {
    "session_start": {"is_first_run"},
    "session_end": {"duration_ms", "event_count"},
    # command_invoked now fires ONLY for the plugin's own first-party bins
    # (sf-context / sf-deploy-gate) — sf/sfdx and every other binary produce no
    # event at all. So the allowlist keeps only the first-party dimensions; there
    # is no "command" path anymore (that parser was deleted with the sf/sfdx tier).
    "command_invoked": {"outcome", "binary", "category", "subcommand"},
    "skill_dispatched": {"skill", "skill_domain"},
    "agent_dispatched": {"agent_type"},
    "exception": {"error_class", "kind"},
    "mcp_tool_used": {"mcp_server", "mcp_tool", "outcome"},
    # plugin_loaded / plugin_suggestion_declined: accept/decline halves of a
    # plugin-catalog proposal (dynamic-loading-strategy-plan.md Phase 4.5).
    "plugin_loaded": {"plugin", "origin", "confidence", "surface"},
    "plugin_suggestion_declined": {"plugin", "origin", "confidence", "surface"},
    # plugin_recommended / plugin_installed: recommend-time and install-time
    # signals for a known-set plugin (W-23856691), additive to the pair above.
    "plugin_recommended": {"plugin", "origin", "confidence", "surface"},
    "plugin_installed": {"plugin", "origin", "confidence", "surface"},
}

# Every field the envelope must attach to EVERY event (§2.2 "attached to every event").
# NOTE: raw org_id is intentionally NOT enveloped on the buffered record — only the
# coarse org_bucket is. (The raw org id rides the UIP flexible format (O11y
# sf_a4dInstrumentation schema) shape ALONE, stamped at
# transmit from the live org resolve — never from this envelope, never cached.)
ENVELOPE_FIELDS = {
    "machine_id", "session_id", "os", "arch", "os_version", "locale",
    "plugin_name", "plugin_version", "suite_version", "ci", "model",
    "org_bucket",
    # harness: which agent harness ran the plugin (closed enum). Enveloped on the
    # buffered record as a carrier; emitted ONLY on the UIP shape (never PDP).
    "harness",
}

# Fields the plan promises are NEVER collected (§2.4) — used as canaries.
FORBIDDEN_SUBSTRINGS = [
    "SECRET", "token", "TOKEN", "password", "acme-prod", "projectatlas",
    "jsmith", "W-12345678", "https://", "/Users/", "customer bug",
]


class PlanParityTests(unittest.TestCase):
    """The 'no gaps' guard: code catalog == plan catalog, field-for-field."""

    def test_event_catalog_matches_plan(self):
        self.assertEqual(
            set(sft._ALLOWLIST), set(PLAN_EVENTS),
            "sf_telemetry._ALLOWLIST events differ from the plan's event set",
        )

    def test_each_event_fields_match_plan(self):
        for event, fields in PLAN_EVENTS.items():
            self.assertEqual(
                sft._ALLOWLIST[event], fields,
                f"allowlist for {event!r} differs from the plan",
            )


class TelemetryCaptureTestBase(unittest.TestCase):
    """Isolates state to a temp cwd and mocks the org CLI so capture is hermetic."""

    def setUp(self):
        self._prev_cwd = os.getcwd()
        self._tmp = tempfile.TemporaryDirectory()
        os.chdir(self._tmp.name)
        # Capture is gated on being inside a Salesforce DX project (see
        # _in_sf_project). Mark this temp cwd as one so the capture tests exercise
        # the in-project case (the norm); the out-of-project gate has its own test.
        Path("sfdx-project.json").write_text('{"packageDirectories":[{"path":"force-app"}]}')
        # Never touch a real org / real CLIID cache during tests.
        self._org = mock.patch.object(
            sft, "_resolve_org_context",
            return_value={"org_id": "00Dxx0000000001", "org_bucket": "production",
                          "username": "hermetic@example.com"},
        )
        self._org.start()
        # Point the CLI cache dir at the temp tree so _machine_id mints a fallback
        # instead of reading this machine's real CLIID.txt.
        self._cache = mock.patch.object(
            sft, "_cli_cache_dir", return_value=Path(self._tmp.name) / "no-cli-cache",
        )
        self._cache.start()
        # Clear ecosystem opt-out + CI env for a clean default-on baseline, and
        # redirect the MACHINE-WIDE telemetry home into the temp tree so consent /
        # notice / machine-id state never touches the real ~/.sf and each test is
        # isolated. (Machine-wide state is intentionally NOT cwd-relative, so the
        # chdir above no longer isolates it — this override does.)
        self._env = mock.patch.dict(os.environ, {}, clear=False)
        self._env.start()
        for var in ("SF_DISABLE_TELEMETRY", "DO_NOT_TRACK", "CI",
                    "CONTINUOUS_INTEGRATION", "BUILD_NUMBER", "GITHUB_ACTIONS"):
            os.environ.pop(var, None)
        os.environ["SF_DEV_TELEMETRY_HOME"] = str(Path(self._tmp.name) / "machine-state")
        # Disclosure-before-capture invariant: capture_event drops every non-
        # session_start event until the one-time notice has been shown (marker
        # present). In a real session session_start fires first and shows it; these
        # capture tests inject events mid-session, so establish that same post-
        # disclosure baseline here. The dedicated disclosure tests clear the marker
        # to exercise the gate itself.
        sft._mark_notified()

    def tearDown(self):
        self._env.stop()
        self._cache.stop()
        self._org.stop()
        os.chdir(self._prev_cwd)
        self._tmp.cleanup()

    # --- helpers -------------------------------------------------------------
    def capture(self, event, outcome=None, payload=None):
        """Drive one capture the way the hook does: JSON payload on stdin, the
        event (+ optional outcome/kind arg) as argv. Returns the parsed stdout."""
        argv = ["sf-context", "telemetry-capture", event]
        if outcome is not None:
            argv.append(outcome)
        stdin = io.StringIO(json.dumps(payload if payload is not None else {}))
        buf = io.StringIO()
        with mock.patch.object(sft.sys, "stdin", stdin), redirect_stdout(buf):
            rc = sft.cmd_capture(argv)
        self.assertEqual(rc, 0)
        return json.loads(buf.getvalue() or "{}")

    def consent(self, action):
        buf = io.StringIO()
        with redirect_stdout(buf):
            sft.cmd_consent(["sf-context", "telemetry", action])
        return buf.getvalue()

    def buffers(self):
        """All per-session buffer files in the current project's .sf/."""
        return sorted(Path(".sf").glob("telemetry-buffer-*.jsonl"))

    def events(self):
        """All buffered events across every per-session buffer, parsed."""
        evs = []
        for p in self.buffers():
            evs += [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
        return evs

    def last(self, event=None):
        evs = self.events()
        if event:
            evs = [e for e in evs if e["event"] == event]
        self.assertTrue(evs, f"no {event or 'any'} event was written")
        return evs[-1]

    def assertNoLeak(self, obj):
        blob = json.dumps(obj)
        for bad in FORBIDDEN_SUBSTRINGS:
            self.assertNotIn(bad, blob, f"forbidden content {bad!r} leaked into telemetry")


class EveryEventCapturedTests(TelemetryCaptureTestBase):
    """Each of the 7 plan events produces a well-formed, fully-enveloped line."""

    def test_session_start(self):
        out = self.capture("session_start",
                            payload={"session_id": "S1", "source": "startup", "model": "claude-opus-4-8"})
        self.assertTrue(out.get("continue"))
        ev = self.last("session_start")
        self.assertEqual(ev["payload"], {"is_first_run": True})
        self.assertEqual(ev["model"], "claude-opus-4-8")  # best-effort, session_start

    def test_is_first_run_is_once_per_machine_not_per_buffer(self):
        # is_first_run must be a durable machine-wide once-only signal (install /
        # activation proxy), NOT buffer existence — per-session buffers are drained on
        # every SessionEnd, so a buffer-based derivation reported first_run on almost
        # every session.
        self.capture("session_start", payload={"session_id": "S1"})
        self.assertTrue(self.last("session_start")["payload"]["is_first_run"],
                        "the first captured session on a machine is a first run")
        # Simulate a completed SessionEnd draining S1's buffer, then a later session.
        for b in self.buffers():
            b.unlink()
        self.capture("session_start", payload={"session_id": "S2"})
        s2 = [e for e in self.events() if e["event"] == "session_start"][-1]
        self.assertFalse(s2["payload"]["is_first_run"],
                         "a later session on the same machine is NOT a first run")

    def test_session_start_refire_on_compact_or_resume_is_noop(self):
        # Agent review: SessionStart matcher is "*", so Claude Code re-fires this hook
        # on resume and after compaction. A re-fire must NOT write a duplicate
        # session_start (inflating counts) NOR re-stamp start_ms (which would shrink
        # duration_ms). Only a genuine new session is recorded.
        self.capture("session_start", payload={"session_id": "S1", "source": "startup"})
        start_marker = sft._session_file("S1")
        first_stamp = json.loads(start_marker.read_text())["start_ms"]
        n_starts = len([e for e in self.events() if e["event"] == "session_start"])
        self.assertEqual(n_starts, 1)
        # Advance the clock so a re-stamp would be observable, then re-fire.
        with mock.patch.object(sft, "_now_ms", return_value=first_stamp + 5_000_000):
            for src in ("compact", "resume"):
                self.capture("session_start", payload={"session_id": "S1", "source": src})
        # No new session_start rows, and the original start_ms is untouched.
        self.assertEqual(
            len([e for e in self.events() if e["event"] == "session_start"]), 1,
            "a compact/resume re-fire must not add a session_start row")
        self.assertEqual(json.loads(start_marker.read_text())["start_ms"], first_stamp,
                         "a compact/resume re-fire must not re-stamp start_ms")

    def test_command_invoked_success(self):
        self.capture("command_invoked", "success",
                     payload={"session_id": "S1", "tool_input": {"command": "sf-context status-org"}})
        ev = self.last("command_invoked")
        self.assertEqual(ev["payload"], {"binary": "sf-context", "category": "plugin_command",
                                         "subcommand": "status-org", "outcome": "success"})

    def test_command_invoked_failure(self):
        self.capture("command_invoked", "failure",
                     payload={"session_id": "S1", "tool_input": {"command": "sf-context status-org"}})
        ev = self.last("command_invoked")
        self.assertEqual(ev["payload"], {"binary": "sf-context", "category": "plugin_command",
                                         "subcommand": "status-org", "outcome": "failure"})

    def test_skill_dispatched(self):
        # A plugin-qualified dispatch of one of OUR skills -> bare name + the
        # skill's functional domain (the leading name segment), not the plugin.
        self.capture("skill_dispatched",
                     payload={"session_id": "S1",
                              "tool_input": {"skill": "salesforce-development:platform-apex-generate"}})
        ev = self.last("skill_dispatched")
        self.assertEqual(ev["payload"]["skill"], "platform-apex-generate")
        self.assertEqual(ev["payload"]["skill_domain"], "platform")

    def test_skill_dispatched_flat_name(self):
        # The real dispatch shape in this repo is a flat, unqualified name.
        self.capture("skill_dispatched",
                     payload={"session_id": "S1", "tool_input": {"skill": "platform-apex-generate"}})
        ev = self.last("skill_dispatched")
        self.assertEqual(ev["payload"]["skill"], "platform-apex-generate")
        self.assertEqual(ev["payload"]["skill_domain"], "platform")

    def test_non_sf_skill_dispatch_is_not_recorded(self):
        # The Skill matcher fires for EVERY session skill; a third-party / user
        # skill must NOT be attributed to our product feature record.
        self.capture("skill_dispatched",
                     payload={"session_id": "S1", "tool_input": {"skill": "google-workspace:send-email"}})
        self.assertEqual([e for e in self.events() if e["event"] == "skill_dispatched"], [])

    def test_agent_dispatched(self):
        # OURS (shipped in agents/) is recorded verbatim; the free-form description
        # is never captured.
        self.capture("agent_dispatched",
                     payload={"session_id": "S1",
                              "tool_input": {"subagent_type": "architecture-review",
                                             "description": "SECRET task name"}})
        ev = self.last("agent_dispatched")
        self.assertEqual(ev["payload"], {"agent_type": "architecture-review"})
        self.assertNoLeak(ev)  # the free-form description must NOT be captured

    def test_agent_dispatched_non_plugin_emits_nothing(self):
        # The Task|Agent matcher fires for EVERY subagent — built-ins, other plugins,
        # and USER-AUTHORED custom agents with arbitrary (possibly PII) type strings.
        # This telemetry is attributed to OUR product feature, so a subagent that is
        # NOT one this plugin ships is skipped ENTIRELY — no event at all — exactly
        # like a non-Salesforce skill. (Not merely collapsed to "other".)
        for raw in ("general-purpose", "code-review", "Explore",
                    "some-teams-custom-agent", "alice@example.com-helper"):
            self.capture("agent_dispatched",
                         payload={"session_id": "S1", "tool_input": {"subagent_type": raw}})
        self.assertEqual([e for e in self.events() if e["event"] == "agent_dispatched"], [],
                         "no agent_dispatched event may be written for a non-plugin agent")

    def test_mcp_tool_used_success_and_failure(self):
        # Our OWN server (from .mcp.json) keeps its name + tool. Claude Code namespaces
        # it as mcp__plugin_<plugin>_<server>__<tool>; the classifier normalizes that
        # back to the bare server name.
        self.capture("mcp_tool_used", "success",
                     payload={"session_id": "S1",
                              "tool_name": "mcp__plugin_salesforce-development_salesforce-lsp__apex_diagnostics"})
        ev = self.last("mcp_tool_used")
        self.assertEqual(ev["payload"], {"mcp_server": "salesforce-lsp",
                                         "mcp_tool": "apex_diagnostics", "outcome": "success"})
        self.capture("mcp_tool_used", "failure",
                     payload={"session_id": "S1", "tool_name": "mcp__salesforce-api-context__query"})
        self.assertEqual(self.last("mcp_tool_used")["payload"]["outcome"], "failure")

    def test_mcp_unknown_server_emits_nothing(self):
        # A third-party / user-configured MCP server has an ARBITRARY name that can
        # carry PII (Prizm PR#1210). We record MCP tool use only for servers THIS
        # plugin ships; any other server is skipped ENTIRELY — no event at all — so
        # neither the arbitrary name NOR the fact of its use is transmitted.
        for tn in ("mcp__customer-alice@example.com__query",
                   "mcp__some-random-server__secret_tool",
                   "mcp__github__create_issue"):
            self.capture("mcp_tool_used", "success",
                         payload={"session_id": "S1", "tool_name": tn})
        self.assertEqual([e for e in self.events() if e["event"] == "mcp_tool_used"], [],
                         "no mcp_tool_used event may be written for a non-plugin MCP server")

    def test_mcp_suffix_collision_is_not_ours(self):
        # Regression (agent review #2): a THIRD-PARTY server whose name merely ENDS
        # in one of ours (e.g. `customer-alice_salesforce-lsp`) must NOT be accepted.
        # A loose `endswith("_" + known)` classified it as ours and then recorded its
        # tool name — a PII leak. Only the exact bare/namespaced forms are ours.
        server, tool = sft._classify_mcp("mcp__customer-alice_salesforce-lsp__alice@example.com")
        self.assertEqual((server, tool), ("other", "other"),
                         "a server whose name only ends in ours must collapse to other/other")
        # And it must emit NOTHING through the capture path.
        self.capture("mcp_tool_used", "success", payload={
            "session_id": "S1",
            "tool_name": "mcp__customer-alice_salesforce-lsp__alice@example.com"})
        self.assertEqual([e for e in self.events() if e["event"] == "mcp_tool_used"], [],
                         "a suffix-collision server must not produce a telemetry event")

    def test_mcp_plugin_namespaced_form_is_ours(self):
        # The reason the suffix match existed: Claude Code namespaces our own servers
        # as `plugin_salesforce-development_<server>`. That EXACT form (and the bare
        # form) must still be recognized as ours so we don't lose our own signal.
        for tn, expect_tool in (
            ("mcp__salesforce-lsp__apex_diagnostics", "apex_diagnostics"),
            ("mcp__plugin_salesforce-development_salesforce-lsp__apex_diagnostics", "apex_diagnostics"),
            ("mcp__salesforce-development_salesforce-lsp__apex_diagnostics", "apex_diagnostics"),
        ):
            server, tool = sft._classify_mcp(tn)
            self.assertEqual((server, tool), ("salesforce-lsp", expect_tool), tn)

    def test_exception_kind_parameterized(self):
        self.capture("exception", "api_error", payload={"session_id": "S1", "error_type": "rate_limit"})
        self.assertEqual(self.last("exception")["payload"], {"error_class": "rate_limit", "kind": "api_error"})
        # hook is a dormant branch: error_class is hard-clamped to "unknown" (an
        # identifier like "ValueError" could still be a secret/username), kind kept.
        self.capture("exception", "hook", payload={"session_id": "S1", "error_type": "ValueError"})
        self.assertEqual(self.last("exception")["payload"], {"error_class": "unknown", "kind": "hook"})

    def test_exception_error_class_shape_gate(self):
        # api_error: a known enum value AND any safe snake_case token survive (so a new
        # Claude error type never becomes "unknown" — no dashboard drift), while a
        # free-form message / path / uppercase / over-long value is scrubbed.
        cases = {
            "server_error": "server_error",                     # known enum
            "account_on_hold": "account_on_hold",               # known enum (added post-first-list)
            "some_future_error_type": "some_future_error_type",  # unknown but safe shape -> passes
            "/Users/me/secret.key exploded": "unknown",          # path + spaces -> scrubbed
            "RateLimit": "unknown",                              # not snake_case -> scrubbed
            "x" * 60: "unknown",                                 # over-long -> scrubbed
        }
        for raw, expected in cases.items():
            self.capture("exception", "api_error",
                         payload={"session_id": "S1", "error_type": raw})
            self.assertEqual(self.last("exception")["payload"]["error_class"], expected, raw)

    def test_all_known_error_types_survive_capture_and_egress(self):
        # Every documented StopFailure error type must survive capture AND the PDP/UIP
        # egress projection UNCHANGED — a regression guard for the exception dashboard's
        # componentId dimension (this is where a missing enum value would surface).
        for et in sorted(sft._API_ERROR_CLASSES):
            self.capture("exception", "api_error",
                         payload={"session_id": "S1", "error_type": et})
            rec = self.last("exception")
            self.assertEqual(rec["payload"]["error_class"], et, et)
            self.assertEqual(sft._to_pdp_event(rec)["componentId"], et, et)

    def test_all_events_are_capturable(self):
        """End-to-end: fire every plan event once, assert all land in the buffer."""
        self.capture("session_start", payload={"session_id": "S1", "source": "startup"})
        self.capture("command_invoked", "success", payload={"session_id": "S1", "tool_input": {"command": "sf-context status-org"}})
        self.capture("skill_dispatched", payload={"session_id": "S1", "tool_input": {"skill": "platform-apex-generate"}})
        # Use identifiers this plugin actually ships — non-plugin agents/MCP servers
        # are intentionally skipped now, so a placeholder would never land.
        self.capture("agent_dispatched", payload={"session_id": "S1", "tool_input": {"subagent_type": "salesforce-dev"}})
        self.capture("mcp_tool_used", "success", payload={"session_id": "S1", "tool_name": "mcp__salesforce-lsp__apex_diagnostics"})
        self.capture("exception", "api_error", payload={"session_id": "S1", "error_type": "e"})
        # plugin_loaded/plugin_suggestion_declined only validate against the
        # generated catalog artifact, which doesn't exist in this hermetic temp
        # cwd — stand in a fake origin map the same way the real one is shaped.
        with mock.patch.object(sft, "_plugin_catalog_origins", return_value={"agentforce-adlc": "external"}):
            self.capture("plugin_loaded", payload={"session_id": "S1", "tool_input": {
                "plugin": "agentforce-adlc", "confidence": "high", "surface": "bypass-gate"}})
            self.capture("plugin_suggestion_declined", payload={"session_id": "S1", "tool_input": {
                "plugin": "agentforce-adlc", "confidence": "medium", "surface": "discovery-command"}})
            self.capture("plugin_recommended", payload={"session_id": "S1", "tool_input": {
                "plugin": "agentforce-adlc", "confidence": "high", "surface": "session-start"}})
            self.capture("plugin_installed", payload={"session_id": "S1", "tool_input": {
                "plugin": "agentforce-adlc", "confidence": "none", "surface": "self-directed"}})
        self.capture("session_end", payload={"session_id": "S1"})
        seen = {e["event"] for e in self.events()}
        self.assertEqual(seen, set(PLAN_EVENTS), "not every plan event reached the buffer")

    def test_plugin_loaded_and_declined(self):
        with mock.patch.object(sft, "_plugin_catalog_origins", return_value={"agentforce-adlc": "external"}):
            self.capture("plugin_loaded", payload={"session_id": "S1", "tool_input": {
                "plugin": "agentforce-adlc", "confidence": "high", "surface": "bypass-gate"}})
            ev = self.last("plugin_loaded")
            self.assertEqual(ev["payload"], {"plugin": "agentforce-adlc", "origin": "external",
                                             "confidence": "high", "surface": "bypass-gate"})
            self.capture("plugin_suggestion_declined", payload={"session_id": "S1", "tool_input": {
                "plugin": "agentforce-adlc", "confidence": "medium", "surface": "discovery-command"}})
            ev = self.last("plugin_suggestion_declined")
            self.assertEqual(ev["payload"], {"plugin": "agentforce-adlc", "origin": "external",
                                             "confidence": "medium", "surface": "discovery-command"})
            self.capture("plugin_loaded", payload={"session_id": "S1", "tool_input": {
                "plugin": "agentforce-adlc", "confidence": "high", "surface": "user-prompt"}})
            ev = self.last("plugin_loaded")
            self.assertEqual(ev["payload"], {"plugin": "agentforce-adlc", "origin": "external",
                                             "confidence": "high", "surface": "user-prompt"})

    def test_plugin_loaded_rejects_unknown_plugin_or_bad_vocab(self):
        # A plugin name absent from the generated catalog (held/internal, or never
        # ours) must emit nothing — same discipline as a non-plugin MCP server/agent.
        with mock.patch.object(sft, "_plugin_catalog_origins", return_value={"agentforce-adlc": "external"}):
            self.capture("plugin_loaded", payload={"session_id": "S1", "tool_input": {
                "plugin": "some-held-internal-plugin", "confidence": "high", "surface": "bypass-gate"}})
            self.assertEqual([e for e in self.events() if e["event"] == "plugin_loaded"], [],
                             "no plugin_loaded event may be written for a plugin outside the catalog")
            # A known plugin with an out-of-vocabulary confidence/surface is also dropped.
            self.capture("plugin_loaded", payload={"session_id": "S1", "tool_input": {
                "plugin": "agentforce-adlc", "confidence": "low", "surface": "bypass-gate"}})
            self.capture("plugin_suggestion_declined", payload={"session_id": "S1", "tool_input": {
                "plugin": "agentforce-adlc", "confidence": "high", "surface": "background"}})
            self.assertEqual([e for e in self.events()
                              if e["event"] in ("plugin_loaded", "plugin_suggestion_declined")], [],
                             "an out-of-vocabulary confidence/surface must not be captured")

    def test_plugin_recommended_and_installed(self):
        with mock.patch.object(sft, "_plugin_catalog_origins", return_value={"agentforce-adlc": "external"}):
            # session-start is a persisted surface, valid for recommendation and
            # later successful-install attribution.
            self.capture("plugin_recommended", payload={"session_id": "S1", "tool_input": {
                "plugin": "agentforce-adlc", "confidence": "high", "surface": "session-start"}})
            ev = self.last("plugin_recommended")
            self.assertEqual(ev["payload"], {"plugin": "agentforce-adlc", "origin": "external",
                                             "confidence": "high", "surface": "session-start"})
            self.capture("plugin_installed", payload={"session_id": "S1", "tool_input": {
                "plugin": "agentforce-adlc", "confidence": "high", "surface": "session-start"}})
            ev = self.last("plugin_installed")
            self.assertEqual(ev["payload"], {"plugin": "agentforce-adlc", "origin": "external",
                                             "confidence": "high", "surface": "session-start"})
            # user-prompt is a persisted proposal surface, valid for both the
            # recommendation and the subsequent successful install attribution.
            self.capture("plugin_recommended", payload={"session_id": "S1", "tool_input": {
                "plugin": "agentforce-adlc", "confidence": "high", "surface": "user-prompt"}})
            ev = self.last("plugin_recommended")
            self.assertEqual(ev["payload"], {"plugin": "agentforce-adlc", "origin": "external",
                                             "confidence": "high", "surface": "user-prompt"})
            self.capture("plugin_installed", payload={"session_id": "S1", "tool_input": {
                "plugin": "agentforce-adlc", "confidence": "high", "surface": "user-prompt"}})
            ev = self.last("plugin_installed")
            self.assertEqual(ev["payload"], {"plugin": "agentforce-adlc", "origin": "external",
                                             "confidence": "high", "surface": "user-prompt"})
            # installed: self-directed (no in-session proposal) rides confidence "none".
            self.capture("plugin_installed", payload={"session_id": "S1", "tool_input": {
                "plugin": "agentforce-adlc", "confidence": "none", "surface": "self-directed"}})
            ev = self.last("plugin_installed")
            self.assertEqual(ev["payload"], {"plugin": "agentforce-adlc", "origin": "external",
                                             "confidence": "none", "surface": "self-directed"})

    def test_plugin_recommended_and_installed_reject_bad_vocab(self):
        with mock.patch.object(sft, "_plugin_catalog_origins", return_value={"agentforce-adlc": "external"}):
            # An unknown surface must not be accepted for plugin_installed.
            self.capture("plugin_installed", payload={"session_id": "S1", "tool_input": {
                "plugin": "agentforce-adlc", "confidence": "high", "surface": "background"}})
            # "self-directed"/"none" belong to plugin_installed, never plugin_recommended.
            self.capture("plugin_recommended", payload={"session_id": "S1", "tool_input": {
                "plugin": "agentforce-adlc", "confidence": "none", "surface": "self-directed"}})
            # a plugin outside the catalog is dropped on both events.
            self.capture("plugin_recommended", payload={"session_id": "S1", "tool_input": {
                "plugin": "not-ours", "confidence": "high", "surface": "session-start"}})
            self.assertEqual([e for e in self.events()
                              if e["event"] in ("plugin_recommended", "plugin_installed")], [],
                             "recommend/install events must honor their closed vocabularies")


class EnvelopeTests(TelemetryCaptureTestBase):
    def test_every_event_carries_full_envelope(self):
        self.capture("session_start", payload={"session_id": "S1", "source": "startup", "model": "m"})
        self.capture("command_invoked", "success", payload={"session_id": "S1", "tool_input": {"command": "git status"}})
        for ev in self.events():
            missing = ENVELOPE_FIELDS - set(ev)
            self.assertFalse(missing, f"{ev['event']} missing envelope fields: {missing}")
            self.assertEqual(ev["plugin_name"], "salesforce-development")
            self.assertTrue(ev["machine_id"])          # non-empty id
            # Org context is resolved at flush (session end), not at capture, so
            # SessionStart stays local-first — the envelope carries the coarse
            # org_bucket at its unresolved default until transmit stamps the
            # accurate bucket on the sent events.
            self.assertIn("org_bucket", ev)
            self.assertEqual(ev["org_bucket"], "none")
            # raw org_id must NEVER be enveloped (bucket-only privacy model)
            self.assertNotIn("org_id", ev)
            self.assertIn("timestamp", ev)
            # harness is a closed enum on every record
            self.assertIn(ev["harness"],
                          {"claude-code", "cursor", "codex", "copilot-cli",
                           "opencode", "other"})

    def test_plugin_and_suite_version_both_present_and_equal(self):
        self.capture("session_start", payload={"session_id": "S1"})
        ev = self.last("session_start")
        self.assertEqual(ev["plugin_version"], ev["suite_version"])
        self.assertTrue(ev["suite_version"])  # read from the manifest


class ScrubbingTests(TelemetryCaptureTestBase):
    def test_command_invoked_is_plugin_bin_only_no_command_key(self):
        # command.invoked now fires ONLY for the plugin's own first-party bins;
        # a captured record never carries a free-form "command" key, and sf (even
        # with flags/positionals that could carry secrets) produces NO event.
        self.capture("command_invoked", "success",
                     payload={"session_id": "S1", "tool_input": {"command": "sf-context status-org"}})
        ev = self.last("command_invoked")
        self.assertNotIn("command", ev["payload"])
        self.capture("command_invoked", "success", payload={"session_id": "S1", "tool_input": {
            "command": "sf org display secret"}})
        self.assertEqual(len([e for e in self.events() if e["event"] == "command_invoked"]), 1,
                         "sf must produce no command.invoked event")

    def test_unknown_binary_produces_no_event(self):
        # An unrecognized binary (a custom script) produces NO command.invoked event
        # at all — not a redacted "other" row — so its name, flags, and args can
        # never reach the buffer. command.invoked fires only for sf/sfdx + our bins.
        self.capture("command_invoked", "failure", payload={"session_id": "S1", "tool_input": {
            "command": "./deploy-projectatlas.sh --token SECRET123 https://acme-prod.example"}})
        self.assertEqual([e for e in self.events() if e["event"] == "command_invoked"], [],
                         "an unrecognized binary must produce no command.invoked event")

    def test_non_sf_tool_produces_no_event(self):
        # command.invoked is scoped to sf/sfdx + our own bins only — a common dev
        # tool like git is NOT allowlisted, so it produces NO event (not an "other"
        # row) and its args (here, a commit message) never reach the buffer.
        self.capture("command_invoked", "success", payload={"session_id": "S1", "tool_input": {
            "command": 'git commit -m "fix W-12345678 customer bug"'}})
        self.assertEqual([e for e in self.events() if e["event"] == "command_invoked"], [],
                         "a non-sf dev tool must produce no command.invoked event")

    def test_first_party_positional_dropped(self):
        # record-update-decision takes a free-form version string as a positional;
        # the tier model keeps subcommand + flag names but DROPS all positionals.
        self.capture("command_invoked", "success", payload={"session_id": "S1", "tool_input": {
            "command": "sf-context record-update-decision 2.3.4-SECRET --reason nag"}})
        ev = self.last("command_invoked")
        self.assertEqual(ev["payload"]["binary"], "sf-context")
        self.assertEqual(ev["payload"]["subcommand"], "record-update-decision")
        self.assertNoLeak(ev)  # the version positional must not appear

    def test_allowlist_drops_non_approved_fields(self):
        # _write_event must strip anything not on the event's allowlist, even if a
        # caller passes extra fields.
        self.capture("session_start", payload={"session_id": "S1"})  # ensure dir/consent exist
        sft._write_event("skill_dispatched",
                         {"skill": "s", "skill_domain": "d", "raw_prompt": "SECRET code here"},
                         {"session_id": "S1"})
        ev = self.last("skill_dispatched")
        self.assertEqual(set(ev["payload"]), {"skill", "skill_domain"})
        self.assertNoLeak(ev)


class CommandTierTests(TelemetryCaptureTestBase):
    def _cls(self, cmd):
        # Production classifier is _classify_command (returns the selected segment
        # plus binary/category/subcommand); these tests exercise the (binary,
        # category, subcommand) projection the removed _classify_binary wrapper used.
        return sft._classify_command(cmd)[1:]

    def test_classify_binary_tiers(self):
        # command.invoked now fires ONLY for the plugin's own first-party bins;
        # sf/sfdx and every other binary (git, npm, mystery scripts) drop to
        # "other" — there is no richer sf/sfdx tier anymore.
        self.assertEqual(self._cls("sf-context status-org"),
                         ("sf-context", "plugin_command", "status-org"))
        self.assertEqual(self._cls("sf-deploy-gate prod-check"),
                         ("sf-deploy-gate", "plugin_command", "prod-check"))
        self.assertEqual(self._cls("sf org list")[:2], ("other", "other"))
        self.assertEqual(self._cls("sfdx force:org:list")[:2], ("other", "other"))
        self.assertEqual(self._cls("git push")[:2], ("other", "other"))
        self.assertEqual(self._cls("npm ci")[:2], ("other", "other"))
        self.assertEqual(self._cls("./mystery.sh")[:2], ("other", "other"))
        # env-assignment prefix is skipped, not classified as the binary
        self.assertEqual(self._cls("FOO=bar sf-context status-org")[0], "sf-context")
        # path form reduces to basename
        self.assertEqual(self._cls("/usr/local/bin/sf-context status-org")[0], "sf-context")

    def test_classify_binary_compound_commands(self):
        # Agents routinely wrap CLI calls; the meaningful binary must be found
        # across shell operators, not lost to the leading cd/pipe head.
        self.assertEqual(self._cls("cd app && sf-context status")[:2],
                         ("sf-context", "plugin_command"))
        self.assertEqual(self._cls("sf-context status-org | jq .result")[:2],
                         ("sf-context", "plugin_command"))
        self.assertEqual(self._cls("ls -la ; sf-context status-org")[:2],
                         ("sf-context", "plugin_command"))
        # sf is no longer recognized — an all-sf/other compound stays "other"
        self.assertEqual(self._cls("echo x | sf org list")[:2], ("other", "other"))
        self.assertEqual(self._cls("cd app && git status")[:2], ("other", "other"))
        # first RECOGNIZED segment wins — sf-context is found past the leading npm segment
        self.assertEqual(self._cls("npm run build && sf-context status")[0], "sf-context")
        # first-party subcommand still resolves through a cd prefix
        self.assertEqual(self._cls("cd x && sf-context status-org"),
                         ("sf-context", "plugin_command", "status-org"))

    def test_classify_binary_compound_never_leaks(self):
        # No recognized segment => stays "other"; a secret script in a compound
        # command must NEVER surface its name/args.
        b, c, _ = self._cls("cd app && ./deploy-prod.sh --token SECRET123")
        self.assertEqual((b, c), ("other", "other"))
        # an operator INSIDE quotes is one arg, not a separator (no mis-split)
        self.assertEqual(self._cls('echo "a && b"')[:2], ("other", "other"))

    def test_command_invoked_is_plugin_bin_only(self):
        # The structural privacy guarantee that replaces the deleted sf/sfdx
        # parser: a captured command.invoked record for a first-party bin
        # contains only the allowlisted keys (no free-form "command" string),
        # and sf/sfdx produce NO event at all.
        self.capture("command_invoked", "success",
                     payload={"session_id": "S1", "tool_input": {"command": "sf-context status-org"}})
        ev = self.last("command_invoked")
        self.assertLessEqual(set(ev["payload"]), {"binary", "category", "subcommand", "outcome"})
        self.assertNotIn("command", ev["payload"])
        self.capture("command_invoked", "success",
                     payload={"session_id": "S1", "tool_input": {"command": "sf project deploy start --json"}})
        self.assertEqual(len([e for e in self.events() if e["event"] == "command_invoked"]), 1,
                         "sf must produce no additional command.invoked event")

    def test_first_party_subcommand_allowlisted(self):
        binary, cat, sub = self._cls("sf-context status-org")
        self.assertEqual((binary, cat, sub), ("sf-context", "plugin_command", "status-org"))
        binary, cat, sub = self._cls("sf-context discover overview")
        self.assertEqual((binary, cat, sub), ("sf-context", "plugin_command", "discover"))
        rec = {"event": "command_invoked", "payload": {
            "binary": binary, "category": cat, "subcommand": sub, "outcome": "success"}}
        self.assertEqual(sft._to_pdp_event(rec)["componentId"], "sf-context.discover")
        # an unknown subcommand is dropped, not stored raw
        self.assertEqual(self._cls("sf-context frobnicate-SECRET")[2], "")


class ConsentTests(TelemetryCaptureTestBase):
    def test_default_on_writes(self):
        self.assertTrue(sft._is_enabled())
        self.capture("session_start", payload={"session_id": "S1"})
        self.assertEqual(len(self.events()), 1)

    def test_hard_off_discards_buffer_and_blocks_capture(self):
        self.capture("session_start", payload={"session_id": "S1"})
        self.assertTrue(self.buffers())
        self.consent("off")
        self.assertFalse(sft._is_enabled())
        self.assertFalse(self.buffers(), "off must discard the buffer")
        out = self.capture("command_invoked", "success",
                           payload={"session_id": "S1", "tool_input": {"command": "sf org list"}})
        self.assertTrue(out.get("continue"))  # still composes with other hooks
        self.assertFalse(self.buffers(), "off must not write")

    def test_capture_racing_concurrent_optout_leaves_no_buffer(self):
        # Reviewer P1: an in-flight capture must not leave an opted-out buffer behind.
        # Simulate `telemetry off` landing DURING the write (persist the opt-out, as
        # its purge would); the post-capture compensating check sees consent now off
        # and removes the buffer this capture created.
        real_write = sft._write_event

        def write_then_off(*a, **k):
            real_write(*a, **k)
            sft._save_consent({"enabled": False})  # concurrent off lands mid-capture

        with mock.patch.object(sft, "_write_event", side_effect=write_then_off):
            self.capture("session_start", payload={"session_id": "S1"})
        self.assertFalse(self.buffers(),
                         "a capture racing a concurrent opt-out must leave no buffer")

    def test_capture_racing_optout_then_reenable_discards_event(self):
        # Reviewer P1 (harder case): an off->on toggle DURING the capture window must
        # STILL discard the in-flight, pre-opt-out event — a current-enabled check
        # alone would preserve it once consent flipped back on. The consent generation
        # captured at entry differs after the write, so the event is dropped.
        real_write = sft._write_event

        def write_then_toggle(*a, **k):
            real_write(*a, **k)
            sft._save_consent({"enabled": False})  # off (would purge in the real cmd)
            sft._save_consent({"enabled": True})   # on again, before the post-write check

        with mock.patch.object(sft, "_write_event", side_effect=write_then_toggle):
            self.capture("session_start", payload={"session_id": "S1"})
        self.assertTrue(sft._is_enabled(), "consent ends ON after the toggle")
        self.assertFalse(self.buffers(),
                         "an off->on toggle during capture must still discard the event")

    def test_stale_capture_after_real_off_on_preserves_new_event(self):
        # Reviewer P2 (faithful race): a stale capture stages its event and PAUSES;
        # then a REAL off (production persist + purge, via cmd_consent) and on land;
        # a NEW capture commits a valid, post-re-enable event; finally the stale
        # capture RESUMES and must discard ONLY its own stage — never the new event.
        # This models the production OFF purge (not a direct _save_consent) and
        # captures the surviving event AFTER the re-enable, per the review.
        real_write = sft._write_event

        def stale_write(*a, **k):
            real_write(*a, **k)  # stale capture stages its own event, then "pauses":
            with mock.patch.object(sft, "_write_event", real_write):
                self.consent("off")  # real persist + purge (clears buffers AND stages)
                self.consent("on")   # real re-enable — generation advances past gen0
                self.capture("skill_dispatched",
                             payload={"session_id": "S1",
                                      "tool_input": {"skill": "platform-apex-generate"}})

        with mock.patch.object(sft, "_write_event", side_effect=stale_write):
            self.capture("skill_dispatched",
                         payload={"session_id": "S1",
                                  "tool_input": {"skill": "platform-soql-query"}})

        self.assertTrue(sft._is_enabled(), "consent ends ON after the off->on")
        skills = [e["payload"]["skill"] for e in self.events()
                  if e["event"] == "skill_dispatched"]
        self.assertEqual(skills, ["platform-apex-generate"],
                         "the post-re-enable event survives; the stale capture "
                         "discards only its own stage")

    def test_consent_generation_is_monotonic_and_rollback_resistant(self):
        # Reviewer P1: the consent generation must never roll back. It is not a plain
        # counter (which races across processes) but max(counter+1, wall-clock ns), so
        # each transition is strictly forward — even if an on-disk value is stale/low.
        import time
        sft._save_consent({"enabled": True})
        g1 = sft._consent_generation()
        sft._save_consent({"enabled": False})
        g2 = sft._consent_generation()
        self.assertLess(g1, g2, "each transition advances the generation")
        # Simulate a racing writer having clobbered the file with a tiny counter value;
        # the next save must still jump forward to a fresh ns stamp, not roll back.
        sft._consent_file().write_text(json.dumps({"enabled": True, "gen": 1}))
        before = time.time_ns()
        sft._save_consent({"enabled": False})
        self.assertGreaterEqual(sft._consent_generation(), before,
                                "generation must not roll back to a stale counter value")

    def test_malformed_generation_does_not_break_capture(self):
        # DX Prism (fit-test-quality) r3770596133: a non-numeric persisted `gen` — a
        # hand-edited or corrupted consent file — must NOT raise out of capture_event
        # (that parse runs before the fail-silent try/finally and would break the
        # hook). It fail-safes to 0, so capture still records normally, and the
        # generation reader coerces it rather than raising.
        sft._consent_file().parent.mkdir(parents=True, exist_ok=True)
        sft._consent_file().write_text(json.dumps({"enabled": True, "gen": "not-a-number"}))
        self.assertEqual(sft._consent_generation(), 0,
                         "a malformed gen must coerce to 0, never raise")
        # capture must not raise and must still write (consent is enabled).
        self.capture("session_start", payload={"session_id": "S1"})
        self.assertEqual(len(self.events()), 1,
                         "a malformed gen must fail-safe, not break capture")

    def test_save_consent_tolerates_malformed_prior_generation(self):
        # Symmetry: a transition (on/off) over a corrupted `gen` must also not raise;
        # _save_consent coerces the prior value and still advances monotonically.
        sft._consent_file().parent.mkdir(parents=True, exist_ok=True)
        sft._consent_file().write_text(json.dumps({"enabled": True, "gen": "garbage"}))
        self.consent("off")  # must not raise
        self.assertFalse(sft._is_enabled())
        self.assertGreater(sft._consent_generation(), 0,
                           "the transition must advance the generation from a coerced 0")

    def test_off_does_not_write_or_purge_when_lock_unavailable(self):
        # Reviewer P1: an OFF that cannot acquire the consent lock must NOT write
        # consent or purge UNLOCKED — that would race another transition or a locked
        # capture. It must report STILL ON and leave state untouched. Simulate an
        # unacquirable lock by making __enter__ return False (held=False).
        self.capture("session_start", payload={"session_id": "S1"})
        self.assertTrue(self.events(), "precondition: a buffered event exists")
        self.assertTrue(sft._is_enabled(), "precondition: telemetry is ON")
        buf = io.StringIO()
        with mock.patch.object(sft._ConsentLock, "__enter__", lambda self: False), \
                redirect_stdout(buf):
            rc = sft.cmd_consent(["sf-context", "telemetry", "off"])
        self.assertEqual(rc, 1, "off must fail rather than proceed unlocked")
        self.assertIn("STILL ON", buf.getvalue())
        self.assertTrue(sft._is_enabled(),
                        "consent must remain ON — no unlocked write")
        self.assertTrue(self.events(),
                        "the buffer must NOT be purged unlocked")

    def test_on_does_not_write_when_lock_unavailable(self):
        # Reviewer P1 (mirror): an ON that cannot acquire the lock must NOT write
        # consent unlocked; it reports failure and leaves the prior state.
        self.consent("off")  # real transition (lock acquires fine, no contention)
        self.assertFalse(sft._is_enabled(), "precondition: telemetry is OFF")
        buf = io.StringIO()
        with mock.patch.object(sft._ConsentLock, "__enter__", lambda self: False), \
                redirect_stdout(buf):
            rc = sft.cmd_consent(["sf-context", "telemetry", "on"])
        self.assertEqual(rc, 1, "on must fail rather than proceed unlocked")
        self.assertFalse(sft._is_enabled(),
                         "consent must remain OFF — no unlocked write")
        self.assertNotIn("effectively on", buf.getvalue().lower(),
                         "must not claim ON when it stays OFF")

    def test_on_lock_unavailable_reports_env_optout_state(self):
        # Reviewer P2: on-failure must reflect the real state — when an env opt-out is
        # in force telemetry is OFF, so it must NOT print "effectively on".
        with mock.patch.dict(os.environ, {"SF_DISABLE_TELEMETRY": "1"}):
            self.assertFalse(sft._is_enabled())
            buf = io.StringIO()
            with mock.patch.object(sft._ConsentLock, "__enter__", lambda self: False), \
                    redirect_stdout(buf):
                rc = sft.cmd_consent(["sf-context", "telemetry", "on"])
            out = buf.getvalue()
        self.assertEqual(rc, 1)
        self.assertNotIn("effectively on", out.lower())
        self.assertIn("OFF", out)

    def test_off_lock_unavailable_when_already_off_with_buffer_reports_incomplete(self):
        # Reviewer P1 (hard-off cleanup contract): a repeated off that cannot take the
        # lock must NOT report success while a local buffer remains unpurged. The
        # message stays accurate (not "STILL ON"), but rc is nonzero and the buffer is
        # still on disk — cleanup did not complete.
        self.consent("off")
        self.assertFalse(sft._is_enabled())
        # A stranded buffer on disk (e.g. from a prior interrupted purge).
        Path(".sf").mkdir(exist_ok=True)
        stray = Path(".sf/telemetry-buffer-S1.jsonl")
        stray.write_text(json.dumps({"event": "session_start"}) + "\n")
        buf = io.StringIO()
        with mock.patch.object(sft._ConsentLock, "__enter__", lambda self: False), \
                redirect_stdout(buf):
            rc = sft.cmd_consent(["sf-context", "telemetry", "off"])
        out = buf.getvalue()
        self.assertNotEqual(rc, 0,
                            "must not report success while cleanup could not run")
        self.assertTrue(stray.exists(),
                        "buffer remains — it could not be purged without the lock")
        self.assertNotIn("STILL ON", out)  # accurate: it is not on

    def test_off_lock_unavailable_with_env_optout_reports_incomplete_persistence(self):
        # Reviewer P1: with an env opt-out, off that cannot take the lock must NOT claim
        # a durable opt-out. The persistent consent may still be default/ON and the
        # buffer unpurged, so removing the env var could reactivate telemetry and expose
        # old events — rc must be nonzero and the persistent consent must not read off.
        with mock.patch.dict(os.environ, {"DO_NOT_TRACK": "1"}):
            self.assertFalse(sft._is_enabled())
            buf = io.StringIO()
            with mock.patch.object(sft._ConsentLock, "__enter__", lambda self: False), \
                    redirect_stdout(buf):
                rc = sft.cmd_consent(["sf-context", "telemetry", "off"])
            out = buf.getvalue()
            self.assertNotEqual(rc, 0, "must not claim the durable opt-out succeeded")
            self.assertNotIn("STILL ON", out)  # accurate: env forces off right now
            self.assertTrue(sft._load_consent().get("enabled", True),
                            "persistent consent stays default/ON — opt-out not saved")

    def test_env_optout_forces_off(self):
        for var in ("SF_DISABLE_TELEMETRY", "DO_NOT_TRACK"):
            with mock.patch.dict(os.environ, {var: "1"}):
                self.assertFalse(sft._is_enabled())
                self.capture("session_start", payload={"session_id": "S1"})
                self.assertEqual(self.events(), [], f"{var} must block capture")

    def test_on_reenables(self):
        self.consent("off")
        self.consent("on")
        self.assertTrue(sft._is_enabled())
        self.capture("session_start", payload={"session_id": "S1"})
        self.assertEqual(len(self.events()), 1)

    def test_consent_is_machine_wide_across_projects(self):
        # W-23481895: opting out is sticky machine-wide, not per-repo. Turn off in
        # "project A" (this cwd), then move to a DIFFERENT project dir and confirm
        # telemetry is still off and capture still writes nothing there.
        self.consent("off")
        self.assertFalse(sft._is_enabled())
        other = Path(self._tmp.name) / "project-B"
        other.mkdir()
        prev = os.getcwd()
        os.chdir(other)
        try:
            # Same machine (SF_DEV_TELEMETRY_HOME unchanged) → still opted out.
            self.assertFalse(sft._is_enabled(), "opt-out must persist across projects")
            self.capture("session_start", payload={"session_id": "S1"})
            self.assertFalse(list((other / ".sf").glob("telemetry-buffer-*.jsonl")),
                             "a different project must honor the machine-wide opt-out")
        finally:
            os.chdir(prev)

    def test_detached_sender_rechecks_consent_and_drops_snapshot(self):
        # W-23481895 hard-off: a `telemetry off` (or env opt-out) that lands AFTER
        # the SessionEnd hook spawned the detached sender must still stop the upload.
        # cmd_send re-reads consent, drops the snapshot, and spawns no flusher.
        Path(".sf").mkdir(exist_ok=True)
        snap = Path(".sf/telemetry-snapshot-test.jsonl")
        snap.write_text(json.dumps({"event": "session_start", "session_id": "S1",
                                    "os": "darwin", "payload": {}}) + "\n")
        self.consent("off")
        # cmd_send swallows exceptions, so a raising mock would hide a regression;
        # assert on call_count of a non-raising mock instead.
        with mock.patch.object(sft, "_spawn_flusher", return_value=True) as spawn:
            rc = sft.cmd_send(["sf-context", "telemetry-send", str(snap)])
        self.assertEqual(rc, 0)
        self.assertEqual(spawn.call_count, 0, "must not spawn the uploader when opted out")
        self.assertFalse(snap.exists(), "sender must delete the snapshot when opted out")
        self.assertFalse(list(Path(".sf").glob("telemetry-pending-*.json")),
                         "sender must not stage a pending job when opted out")

    def test_off_purges_snapshots_and_pending(self):
        # `telemetry off` clears in-flight snapshot/pending files in this project,
        # not just the live buffer.
        Path(".sf").mkdir(exist_ok=True)
        Path(".sf/telemetry-buffer-S1.jsonl").write_text("{}\n")
        Path(".sf/telemetry-snapshot-1.jsonl").write_text("{}\n")
        Path(".sf/telemetry-pending-1.json").write_text("{}")
        self.consent("off")
        self.assertFalse(list(Path(".sf").glob("telemetry-buffer-*.jsonl")))
        self.assertFalse(list(Path(".sf").glob("telemetry-snapshot-*.jsonl")))
        self.assertFalse(list(Path(".sf").glob("telemetry-pending-*.json")))

    def test_off_purges_legacy_shared_buffer(self):
        # DX Prism (prizm-default) r3770452254: earlier builds used a single shared
        # buffer (telemetry-buffer.jsonl, no session suffix). The per-session glob
        # does not match it, so a hard-off must explicitly unlink the legacy file —
        # otherwise a project carried over from a pre-per-session build keeps its
        # buffered telemetry after the user is told it was discarded.
        Path(".sf").mkdir(exist_ok=True)
        legacy = Path(".sf/telemetry-buffer.jsonl")
        legacy.write_text(json.dumps({"event": "session_start"}) + "\n")
        self.consent("off")
        self.assertFalse(legacy.exists(),
                         "hard-off must discard the legacy shared buffer too")

    def test_off_reports_failure_and_returns_nonzero_when_persist_fails(self):
        # Agent review #3: telemetry defaults to ON, so a swallowed write failure on
        # `off` would tell the user it is OFF while capture keeps running — a false
        # guarantee. When _save_consent fails, `off` must report "STILL ON", steer to
        # the env opt-out, and return a non-zero exit — NOT print the success line.
        buf = io.StringIO()
        with mock.patch.object(sft, "_save_consent", return_value=False), \
                redirect_stdout(buf):
            rc = sft.cmd_consent(["x", "telemetry", "off"])
        out = buf.getvalue()
        self.assertEqual(rc, 1)
        self.assertIn("STILL ON", out)
        self.assertIn("SF_DISABLE_TELEMETRY", out)
        self.assertNotIn("now OFF", out, "must not claim success when the write failed")

    def test_off_does_not_purge_when_persist_fails(self):
        # If the opt-out did not persist, telemetry is still ON — so `off` must NOT
        # purge the live buffer (that would destroy data while leaving capture on,
        # the worst of both). Purge happens only AFTER a durable write.
        Path(".sf").mkdir(exist_ok=True)
        Path(".sf/telemetry-buffer-S1.jsonl").write_text("{}\n")
        with mock.patch.object(sft, "_save_consent", return_value=False), \
                redirect_stdout(io.StringIO()):
            sft.cmd_consent(["x", "telemetry", "off"])
        self.assertTrue(Path(".sf/telemetry-buffer-S1.jsonl").exists(),
                        "must not purge the buffer when the opt-out did not persist")

    def test_on_reports_failure_and_returns_nonzero_when_persist_fails(self):
        # Symmetry: `on` also surfaces a persist failure rather than silently claiming
        # success (the choice may not survive even though the default is ON).
        buf = io.StringIO()
        with mock.patch.object(sft, "_save_consent", return_value=False), \
                redirect_stdout(buf):
            rc = sft.cmd_consent(["x", "telemetry", "on"])
        self.assertEqual(rc, 1)
        self.assertIn("Could not persist", buf.getvalue())

    def test_off_succeeds_normally_returns_zero(self):
        # The happy path still returns 0 and prints the success line (guards against
        # the failure-path change accidentally breaking the normal case).
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = sft.cmd_consent(["x", "telemetry", "off"])
        self.assertEqual(rc, 0)
        self.assertIn("now OFF", buf.getvalue())
        self.assertFalse(sft._is_enabled())

    def test_first_run_notice_is_once_per_machine_not_per_project(self):
        # W-23481895: the notice fires exactly once per machine. Showing it in one
        # project must suppress it in every other project on the same machine.
        sft._notified_file().unlink(missing_ok=True)  # exercise the first-run path
        self.assertIsNotNone(sft.first_run_notice_lines())  # project A: shows once
        other = Path(self._tmp.name) / "project-C"
        other.mkdir()
        prev = os.getcwd()
        os.chdir(other)
        try:
            self.assertIsNone(sft.first_run_notice_lines(),
                              "notice must not re-show in a new project on the same machine")
        finally:
            os.chdir(prev)

    def test_first_run_notice_once_then_silent(self):
        # The notice is now plain content LINES (rendered as a band by cmd_detect),
        # not a pre-framed string — first_run_notice_lines() returns a list.
        sft._notified_file().unlink(missing_ok=True)  # exercise the first-run path
        first = sft.first_run_notice_lines()
        self.assertIsNotNone(first)
        self.assertIn("telemetry", "\n".join(first).lower())
        self.assertIsNone(sft.first_run_notice_lines(), "notice must fire at most once")

    def test_first_run_notice_disclosure_matches_what_is_sent(self):
        # Prizm PR#1082 r3723571269: the notice must not claim a blanket "no org
        # data" while the envelope carries an org signal. We DO send the coarse
        # org bucket (scratch/sandbox/production) AND — via the UIP shape — the raw
        # connected org id, so the notice must positively disclose BOTH, and must
        # NOT promise to exclude "org data" wholesale. What is truly excluded (org
        # name, org contents, source, paths, credentials) is still promised.
        sft._notified_file().unlink(missing_ok=True)  # exercise the first-run path
        text = "\n".join(sft.first_run_notice_lines()).lower()
        # Positively discloses the coarse org type we transmit...
        self.assertIn("scratch", text)
        self.assertIn("sandbox", text)
        self.assertIn("production", text)
        # ...and the connected org id, which the UIP shape now carries.
        self.assertIn("org id", text)      # org id IS disclosed as collected
        # ...and still promises the exclusions that hold.
        self.assertIn("org name", text)    # org name is NOT sent
        self.assertIn("source code", text)
        # Must NOT make the inaccurate blanket claim that flagged the review.
        self.assertNotIn("org data", text)
        # Tracks the doc writer's finalized wording: same voice/phrasing so the copy
        # doesn't silently drift from the approved text. If the notice is reworded,
        # this pin must be updated deliberately alongside doc-writer sign-off. The
        # notice deliberately uses NEITHER "anonymous" NOR "pseudonymous": rather than
        # editorialize with a privacy term, it positively discloses the persistent
        # identifiers it carries (a machine id and the connected org id) so there is no
        # characterization to be inaccurate about (DX Prism prizm-default r3771975212
        # flagged "anonymous" as inaccurate; the precise legal framing lives in the
        # disclosure doc, not the user-facing banner).
        self.assertIn("collects the following usage data", text)
        self.assertIn("machine id", text)   # the persistent machine identifier IS disclosed
        self.assertIn("the plugin never collects", text)
        # The notice must name EVERY captured category, not just commands/skills — the
        # allowlist also records subagent dispatch, MCP-tool use, and error events, and
        # this notice is the sole disclosure surface (agent review).
        self.assertIn("commands", text)
        self.assertIn("skills", text)
        self.assertIn("subagents", text)
        self.assertIn("mcp tools", text)
        self.assertIn("error categories", text)
        # The agent harness (which agent/editor ran the plugin) is now collected, so
        # the notice must disclose it too.
        self.assertIn("editor running the plugin", text)
        # Must characterize with NEITHER privacy term — both would invite a review
        # finding (one as inaccurate, the other as jargon); the identifier disclosures
        # above stand on their own. ("pseudonymous" does NOT contain "anonymous", so
        # both are asserted explicitly.)
        self.assertNotIn("anonymous", text)
        self.assertNotIn("pseudonymous", text)
        # The disable instructions use the REAL plugin namespace, not the stale
        # /sfdx-core:… in the draft — printing a non-existent command would misdirect.
        self.assertIn("/salesforce-development:telemetry off", text)
        self.assertNotIn("sfdx-core", text)

    def test_notice_does_not_touch_consent_file(self):
        # AC3 race-safety: the first-run notice records itself in its OWN marker
        # file and NEVER writes telemetry-config.json — so it can't clobber a
        # concurrent `telemetry on/off`. After the notice fires, consent must be
        # untouched (no file, or at least no notice-authored value).
        sft._notified_file().unlink(missing_ok=True)  # exercise the first-run path
        self.assertFalse(sft._consent_file().exists())
        self.assertIsNotNone(sft.first_run_notice_lines())
        self.assertTrue(sft._notified_file().exists(), "notice marker is its own file")
        self.assertFalse(sft._consent_file().exists(),
                         "notice must not create/modify the consent file")

    def test_notice_cannot_resurrect_a_concurrent_off(self):
        # Simulate the interleaving Codex flagged: user runs `telemetry off`, then
        # the (already-in-flight) notice fires. The notice must NOT bring telemetry
        # back on — consent stays off because the notice never writes consent.
        sft.cmd_consent(["x", "telemetry", "off"])
        self.assertFalse(sft._is_enabled())
        # A racing notice that hadn't yet marked itself: force the marker away.
        sft._notified_file().unlink(missing_ok=True)
        sft.first_run_notice_lines()  # fires, writes only its marker
        self.assertFalse(sft._is_enabled(), "notice must not resurrect an opted-out consent")

    def test_consent_file_has_no_notified_key(self):
        # The notified marker moved to its own file; consent config holds ONLY
        # enabled, so the notice and consent writers never share a file to race on.
        sft.cmd_consent(["x", "telemetry", "on"])
        cfg = json.loads(sft._consent_file().read_text())
        self.assertNotIn("notified", cfg,
                         "the notified marker must never live in the consent file")
        self.assertIn("enabled", cfg)
        # `gen` is the monotonic consent generation (transition counter); it is the
        # only other key and never a per-session/notice value.
        self.assertEqual(set(cfg.keys()), {"enabled", "gen"})

    def test_relative_telemetry_home_is_anchored_not_cwd_relative(self):
        # Fix D: a RELATIVE SF_DEV_TELEMETRY_HOME must resolve to the SAME machine-
        # wide path regardless of process CWD (else `telemetry off` in project B
        # can't reach a job queued in project A). Anchor under $HOME, not CWD.
        import tempfile
        with tempfile.TemporaryDirectory() as home, \
                mock.patch.dict(os.environ, {"SF_DEV_TELEMETRY_HOME": "rel-tele-state"}), \
                mock.patch.object(os.path, "expanduser",
                                  side_effect=lambda p: p.replace("~", home, 1)):
            here = os.getcwd()
            try:
                os.chdir(home)
                a = sft._machine_state_dir()
                sub = Path(home) / "nested"; sub.mkdir()
                os.chdir(sub)
                b = sft._machine_state_dir()
            finally:
                os.chdir(here)
            self.assertEqual(a, b, "relative override must not vary by CWD")
            self.assertEqual(a, Path(home) / "rel-tele-state")

    def test_first_run_notice_suppressed_in_ci(self):
        with mock.patch.dict(os.environ, {"CI": "1"}):
            self.assertIsNone(sft.first_run_notice_lines())

    def test_first_run_notice_suppressed_when_opted_out(self):
        with mock.patch.dict(os.environ, {"DO_NOT_TRACK": "1"}):
            self.assertIsNone(sft.first_run_notice_lines())


class ProjectScopeTests(TelemetryCaptureTestBase):
    """Capture is scoped to Salesforce DX projects: with the plugin installed and
    consent ON, a directory that is NOT a Salesforce project records NOTHING."""

    def test_no_capture_outside_sf_project(self):
        # A genuinely non-SF directory — its OWN temp tree with no sfdx-project.json
        # at the cwd or ANY ancestor (setUp's project marker is in a separate tree).
        with tempfile.TemporaryDirectory() as outside:
            prev = os.getcwd()
            os.chdir(outside)
            try:
                self.assertFalse(sft._in_sf_project())
                self.assertTrue(sft._is_enabled())  # consent ON — only the project gate stops it
                for ev, extra in (("session_start", {}),
                                  ("command_invoked", {"tool_input": {"command": "sf org list"}}),
                                  ("skill_dispatched", {"tool_input": {"skill": "platform-apex-generate"}}),
                                  ("exception", {"error_type": "rate_limit"})):
                    self.capture(ev, "success", payload={"session_id": "S1", **extra})
                self.assertEqual(self.events(), [],
                                 "no event may be captured outside a Salesforce project")
                self.assertFalse(list(Path(".sf").glob("telemetry-buffer-*.jsonl")))
            finally:
                os.chdir(prev)

    def test_capture_from_subdirectory_of_sf_project(self):
        # A hook firing in a SUBDIR of the project still counts as in-project
        # (sfdx-project.json is at an ancestor, created by setUp at the temp root).
        sub = Path(self._tmp.name) / "force-app" / "main"
        sub.mkdir(parents=True)
        prev = os.getcwd()
        os.chdir(sub)
        try:
            self.assertTrue(sft._in_sf_project())
            self.capture("session_start", payload={"session_id": "S1"})
            self.assertEqual(len(self.events()), 1, "in-project subdir must still capture")
        finally:
            os.chdir(prev)


class DisclosureGateTests(TelemetryCaptureTestBase):
    """Disclosure-before-capture (agent review #1): no event is buffered until the
    user has been shown the one-time notice. The notice must fire in EVERY ui_mode
    and from any project subdirectory, since the telemetry capture hooks (unlike the
    full-mode banner) run everywhere."""

    def test_no_capture_before_notice_shown(self):
        # Simulate a session whose FIRST telemetry activity is a non-session event
        # (e.g. compact ui_mode where the banner never rendered, or a hook order
        # where a PostToolUse fires before we recorded the notice). With no notice
        # marker, capture must record NOTHING — disclosure has not happened yet.
        sft._notified_file().unlink(missing_ok=True)
        self.assertFalse(sft._notice_shown())
        self.assertTrue(sft._is_enabled())         # consent ON
        self.assertTrue(sft._in_sf_project())       # in a project
        for ev, extra in (("command_invoked", {"tool_input": {"command": "sf org list"}}),
                          ("skill_dispatched", {"tool_input": {"skill": "platform-apex-generate"}}),
                          ("mcp_tool_used", {"tool_name": "mcp__salesforce-lsp__apex_diagnostics"}),
                          ("exception", {"error_type": "rate_limit"})):
            self.capture(ev, "success", payload={"session_id": "S1", **extra})
        self.assertEqual(self.events(), [],
                         "no event may be captured before the disclosure notice is shown")

    def test_session_start_discloses_first_then_captures(self):
        # session_start is the notice trigger. cmd_capture attempts the notice FIRST
        # (creating the marker), THEN captures — so on the first run it both surfaces
        # the notice systemMessage AND records its own event, with the marker created
        # before the buffer write (disclosure precedes capture).
        sft._notified_file().unlink(missing_ok=True)
        out = self.capture("session_start", payload={"session_id": "S1"})
        self.assertEqual(len(self.events()), 1, "session_start must capture once disclosed")
        self.assertIn("systemMessage", out, "first session_start must surface the notice")
        self.assertIn("telemetry", out["systemMessage"].lower())
        self.assertTrue(sft._notice_shown(), "session_start must create the notice marker")

    def test_session_start_not_buffered_when_disclosure_fails(self):
        # Agent review #2: if the notice marker CANNOT be created (disk error), the
        # user has not been disclosed to — so session_start must NOT be buffered, or a
        # later flush could transmit it without disclosure. Simulate the marker never
        # coming into existence and assert nothing is captured.
        sft._notified_file().unlink(missing_ok=True)
        with mock.patch.object(sft, "first_run_notice_lines", return_value=None), \
                mock.patch.object(sft, "_notice_shown", return_value=False):
            self.capture("session_start", payload={"session_id": "S1"})
        self.assertEqual(self.events(), [],
                         "session_start must not be buffered when disclosure did not happen")

    def test_flush_gated_on_disclosure(self):
        # Belt-and-braces (agent review #2): even if a buffer somehow exists (older
        # build, marker removed after capture), flush must not transmit without the
        # notice having been shown. With events buffered but the marker absent, the
        # SessionEnd flush spawns no sender.
        self.capture("session_start", payload={"session_id": "S1"})  # marker set by base setUp
        self.assertTrue(self.events())
        sft._notified_file().unlink(missing_ok=True)  # marker gone before flush
        stdin = io.StringIO(json.dumps({"session_id": "S1"}))
        buf = io.StringIO()
        sender = mock.Mock(return_value=True)
        with mock.patch.object(sft, "_spawn_sender", sender), \
                mock.patch.object(sft.sys, "stdin", stdin), redirect_stdout(buf):
            rc = sft.cmd_flush(["sf-context", "telemetry-flush"])
        self.assertEqual(rc, 0)
        self.assertEqual(sender.call_count, 0,
                         "flush must not transmit before the disclosure notice is shown")

    def test_capture_flows_once_notice_shown(self):
        # After session_start has disclosed, later events flow normally.
        sft._notified_file().unlink(missing_ok=True)
        self.capture("session_start", payload={"session_id": "S1"})
        self.capture("command_invoked", "success",
                     payload={"session_id": "S1", "tool_input": {"command": "sf-context status-org"}})
        kinds = {e["event"] for e in self.events()}
        self.assertEqual(kinds, {"session_start", "command_invoked"})

    def test_notice_fires_only_once_across_hooks(self):
        # The exclusive-create marker is a cross-process mutex: a SECOND session_start
        # (as after a resume) must NOT re-surface the notice.
        sft._notified_file().unlink(missing_ok=True)
        first = self.capture("session_start", payload={"session_id": "S1"})
        second = self.capture("session_start", payload={"session_id": "S2"})
        self.assertIn("systemMessage", first)
        self.assertNotIn("systemMessage", second, "notice must fire at most once per machine")

    def test_ci_capture_not_gated_on_disclosure(self):
        # In CI there is no human to notify; the CI path is unchanged and must not be
        # blocked by the absence of a notice marker (which is never written in CI).
        sft._notified_file().unlink(missing_ok=True)
        with mock.patch.dict(os.environ, {"CI": "true"}):
            self.assertTrue(sft._is_ci())
            self.capture("command_invoked", "success",
                         payload={"session_id": "S1", "tool_input": {"command": "sf-context status-org"}})
            self.assertEqual(len(self.events()), 1,
                             "CI capture must not be gated on the human-facing notice")


class SessionEndTests(TelemetryCaptureTestBase):
    def test_duration_and_event_count(self):
        # Control the clock so duration is deterministic.
        clock = {"t": 1_000_000}
        with mock.patch.object(sft, "_now_ms", side_effect=lambda: clock["t"]):
            self.capture("session_start", payload={"session_id": "S1"})
            self.capture("command_invoked", "success",
                         payload={"session_id": "S1", "tool_input": {"command": "sf-context status-org"}})
            clock["t"] = 1_002_500  # +2500 ms
            self.capture("session_end", payload={"session_id": "S1"})
        ev = self.last("session_end")
        self.assertEqual(ev["payload"]["duration_ms"], 2500)
        self.assertEqual(ev["payload"]["event_count"], 2)  # session_start + command_invoked

    def test_event_count_is_per_session(self):
        self.capture("session_start", payload={"session_id": "S1"})
        self.capture("command_invoked", "success",
                     payload={"session_id": "S1", "tool_input": {"command": "sf org list"}})
        self.capture("session_start", payload={"session_id": "S2"})
        self.capture("session_end", payload={"session_id": "S2"})
        s2 = [e for e in self.events() if e["event"] == "session_end" and e["session_id"] == "S2"][-1]
        self.assertEqual(s2["payload"]["event_count"], 1, "S2 count must exclude S1's events")

    def test_missing_marker_yields_zero_duration(self):
        # session_end with no prior session_start marker -> duration 0, never raises.
        self.capture("session_end", payload={"session_id": "orphan"})
        self.assertEqual(self.last("session_end")["payload"]["duration_ms"], 0)

    def test_marker_cleaned_up(self):
        self.capture("session_start", payload={"session_id": "S1"})
        self.capture("session_end", payload={"session_id": "S1"})
        self.assertEqual(list(Path(".sf").glob("telemetry-session-*.json")), [])

    def test_session_id_path_injection_is_neutralized(self):
        self.capture("session_start", payload={"session_id": "../../etc/passwd"})
        # No marker escaped .sf/, and nothing was written outside the temp cwd.
        markers = list(Path(".sf").glob("telemetry-session-*.json"))
        self.assertEqual(len(markers), 1)
        self.assertTrue(str(markers[0]).startswith(".sf/"))


class FailSilentTests(TelemetryCaptureTestBase):
    def test_garbage_stdin_still_continues(self):
        stdin = io.StringIO("this is not json {{{")
        buf = io.StringIO()
        with mock.patch.object(sft.sys, "stdin", stdin), redirect_stdout(buf):
            rc = sft.cmd_capture(["sf-context", "telemetry-capture", "session_start"])
        self.assertEqual(rc, 0)
        self.assertTrue(json.loads(buf.getvalue()).get("continue"))

    def test_unknown_event_is_noop_continue(self):
        out = self.capture("not_a_real_event", payload={"session_id": "S1"})
        self.assertTrue(out.get("continue"))
        self.assertEqual(self.events(), [])


class ManifestWiringTests(unittest.TestCase):
    """The real 'no gaps' guard at the config layer: every event that the code
    can capture is actually fired by a hook in the plugin manifest."""

    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(_MANIFEST_PATH.read_text())
        cls.hooks = cls.manifest.get("hooks", {})
        # Collect every event name a hook produces. `telemetry-capture <event>`
        # names the event directly; `telemetry-flush` is the SessionEnd writer that
        # produces session_end itself (single-writer, folded in to avoid a buffer
        # race with a parallel capture hook).
        cls.wired = {}
        for section, groups in cls.hooks.items():
            for group in groups:
                for hook in group.get("hooks", []):
                    cmd = hook.get("command", "")
                    marker = "telemetry-capture "
                    if marker in cmd:
                        event = cmd.split(marker, 1)[1].split()[0]
                        cls.wired.setdefault(event, []).append(section)
                    if "telemetry-flush" in cmd:
                        cls.wired.setdefault("session_end", []).append(section)
                    # The successful-Bash command_invoked event is captured
                    # IN-PROCESS by the post-bash dispatcher (see cmd_post_bash),
                    # not as a parallel telemetry-capture hook — develop requires
                    # the PostToolUse Bash block to be a single, race-free hook. So
                    # the post-bash hook IS the wiring for that success leg.
                    if "sf-context post-bash" in cmd:
                        cls.wired.setdefault("command_invoked", []).append(section)

    # plugin_loaded / plugin_suggestion_declined are never fired by a manifest
    # hook at all -- both are in-process capture_event(...) calls made directly
    # from sf_context.py::cmd_plugin_install as it resolves a proposal (install
    # vs. explicit decline), same "no parallel hook, single writer" discipline as
    # command_invoked's post-bash success leg, but with no distinguishable command
    # substring to detect here -- so there is nothing for this manifest scan to find.
    # plugin_recommended / plugin_installed (W-23856691) are likewise in-process
    # capture_event(...) calls -- from _plugin_catalog_match / the SessionStart banner
    # slot _session_start_plugin_slot (recommend) and cmd_plugin_install (install) --
    # never a `telemetry-capture
    # <event>` manifest hook, so this substring scan has nothing to find for them.
    _NEVER_HOOK_WIRED = {
        "plugin_loaded", "plugin_suggestion_declined",
        "plugin_recommended", "plugin_installed",
    }

    def test_every_plan_event_is_wired(self):
        for event in PLAN_EVENTS:
            if event in self._NEVER_HOOK_WIRED:
                continue
            self.assertIn(event, self.wired, f"event {event!r} has no hook in the manifest")

    def test_events_are_in_sensible_lifecycle_sections(self):
        # A light sanity check that events fire from a plausible lifecycle point.
        expected = {
            "session_start": "SessionStart",
            "session_end": "SessionEnd",   # produced by telemetry-flush
            "skill_dispatched": "PreToolUse",
            "agent_dispatched": "PreToolUse",
            "exception": "StopFailure",
        }
        for event, section in expected.items():
            self.assertIn(section, self.wired.get(event, []),
                          f"{event!r} should be wired under {section}")
        # command_invoked fires on both success and failure: success in-process via
        # the PostToolUse post-bash dispatcher, failure via a PostToolUseFailure hook.
        self.assertIn("PostToolUse", self.wired.get("command_invoked", []))
        self.assertIn("PostToolUseFailure", self.wired.get("command_invoked", []))
        # mcp_tool_used has both success and failure legs too.
        self.assertIn("PostToolUse", self.wired.get("mcp_tool_used", []))
        self.assertIn("PostToolUseFailure", self.wired.get("mcp_tool_used", []))

    def test_session_end_is_flush_not_a_parallel_capture(self):
        # session_end MUST be produced by telemetry-flush (single SessionEnd
        # writer). A parallel `telemetry-capture session_end` hook would race the
        # flush's buffer unlink — assert we did not reintroduce one.
        flush_wired = any(
            "telemetry-flush" in h.get("command", "")
            for g in self.hooks.get("SessionEnd", []) for h in g.get("hooks", [])
        )
        self.assertTrue(flush_wired, "SessionEnd must run telemetry-flush")
        capture_session_end = any(
            "telemetry-capture session_end" in h.get("command", "")
            for groups in self.hooks.values() for g in groups for h in g.get("hooks", [])
        )
        self.assertFalse(capture_session_end,
                         "session_end must not also be a parallel capture hook (buffer race)")

    def test_manifest_is_valid_json_with_hooks(self):
        self.assertIn("hooks", self.manifest)


class OrgBucketTests(unittest.TestCase):
    """Coarse org classification. The instance HOST is authoritative because
    `sf org display --json` doesn't reliably carry isScratch/isSandbox — a scratch
    org otherwise mislabels as 'production' (observed live on *.scratch...)."""

    def test_scratch_host_wins_over_missing_flags(self):
        # Real scratch org shape: has an id, NO isScratch flag — host must decide.
        self.assertEqual(sft._classify_org_bucket({
            "id": "00DDv000003yO3rMAE",
            "instanceUrl": "https://site-ruby-7718-dev-ed.scratch.my.salesforce.com",
        }), "scratch")

    def test_modern_sandbox_host(self):
        self.assertEqual(sft._classify_org_bucket({
            "id": "00D000000000001", "instanceUrl": "https://acme--dev.sandbox.my.salesforce.com",
        }), "sandbox")

    def test_legacy_sandbox_pod(self):
        self.assertEqual(sft._classify_org_bucket({
            "id": "00D000000000001", "instanceUrl": "https://cs42.salesforce.com",
        }), "sandbox")

    def test_production_host(self):
        self.assertEqual(sft._classify_org_bucket({
            "id": "00D000000000001", "instanceUrl": "https://acme.my.salesforce.com",
        }), "production")

    def test_flags_are_a_fallback_when_no_host(self):
        self.assertEqual(sft._classify_org_bucket({"id": "x", "isScratch": True}), "scratch")
        self.assertEqual(sft._classify_org_bucket({"id": "x", "isSandbox": True}), "sandbox")

    def test_no_org_is_none(self):
        self.assertEqual(sft._classify_org_bucket({}), "none")
        self.assertEqual(sft._classify_org_bucket({"instanceUrl": ""}), "none")

    def test_production_is_not_falsely_matched_by_substrings(self):
        # A vanity/my-domain host that merely contains "cs" or "sandbox" as a
        # word fragment must not be miscategorized — the patterns are anchored.
        self.assertEqual(sft._classify_org_bucket({
            "id": "x", "instanceUrl": "https://sandboxcandy.my.salesforce.com",
        }), "production")
        self.assertEqual(sft._classify_org_bucket({
            "id": "x", "instanceUrl": "https://acmecs.my.salesforce.com",
        }), "production")


class PdpMappingTests(TelemetryCaptureTestBase):
    """Stream B: every buffered event maps to a well-formed O11y PdpEvent, and
    the mapping never leaks a forbidden field into the wire shape."""

    # PdpEvent's own allowed keys (from @salesforce/telemetry types.d.ts).
    PDP_KEYS = {"eventName", "productFeatureId", "componentId", "eventVolume",
                "contextName", "contextValue"}

    def _pdp(self, record):
        ev = sft._to_pdp_event(record)
        self.assertIsNotNone(ev, f"no PdpEvent produced for {record.get('event')!r}")
        # Only PdpEvent-legal keys, always the suite's feature id, and eventName
        # follows the `<object>.<action>` convention.
        self.assertTrue(set(ev) <= self.PDP_KEYS, f"extra keys: {set(ev) - self.PDP_KEYS}")
        self.assertEqual(ev["productFeatureId"], "aJCEE000000SLW94AO")
        self.assertRegex(ev["eventName"], r"^[a-zA-Z]+\.[a-z]+$")
        self.assertNoLeak(ev)
        return ev

    def _record(self, event, payload, **envelope):
        base = {"event": event, "os": "darwin", "org_bucket": "production",
                "model": "claude-opus-4-8", "session_id": "S1", "payload": payload}
        base.update(envelope)
        return base

    def test_every_event_maps_to_pdp(self):
        cases = {
            "session_start": {"is_first_run": True},
            "session_end": {"duration_ms": 2500, "event_count": 7},
            "command_invoked": {"outcome": "success",
                                "binary": "sf-context", "category": "plugin_command",
                                "subcommand": "status-org"},
            "skill_dispatched": {"skill": "platform-apex-generate", "skill_domain": "platform"},
            "agent_dispatched": {"agent_type": "code-review"},
            "exception": {"error_class": "rate_limit", "kind": "api_error"},
            "mcp_tool_used": {"mcp_server": "api-context", "mcp_tool": "query", "outcome": "success"},
            "plugin_loaded": {"plugin": "agentforce-adlc", "origin": "external",
                              "confidence": "high", "surface": "bypass-gate"},
            "plugin_suggestion_declined": {"plugin": "agentforce-adlc", "origin": "external",
                              "confidence": "medium", "surface": "discovery-command"},
            "plugin_recommended": {"plugin": "agentforce-adlc", "origin": "external",
                              "confidence": "high", "surface": "session-start"},
            "plugin_installed": {"plugin": "agentforce-adlc", "origin": "external",
                              "confidence": "none", "surface": "self-directed"},
        }
        produced = {}
        for event, payload in cases.items():
            ev = self._pdp(self._record(event, payload))
            produced[event] = ev
        # Spot-check the load-bearing dimensions.
        self.assertEqual(produced["skill_dispatched"]["componentId"],
                         "platform-apex-generate")
        self.assertEqual(produced["skill_dispatched"]["contextValue"], "platform")
        self.assertEqual(produced["command_invoked"]["componentId"], "sf-context.status-org")
        self.assertEqual(produced["session_end"]["eventVolume"], 7)
        self.assertEqual(produced["mcp_tool_used"]["componentId"], "api-context.query")
        self.assertEqual(produced["exception"]["componentId"], "rate_limit")
        self.assertEqual(produced["plugin_loaded"]["eventName"], "plugin.loaded")
        self.assertEqual(produced["plugin_loaded"]["componentId"], "agentforce-adlc")
        self.assertEqual(produced["plugin_loaded"]["contextName"], "origin::confidence::surface")
        self.assertEqual(produced["plugin_loaded"]["contextValue"], "external::high::bypass-gate")
        self.assertEqual(produced["plugin_suggestion_declined"]["eventName"],
                         "pluginSuggestion.declined")
        self.assertEqual(produced["plugin_suggestion_declined"]["contextValue"],
                         "external::medium::discovery-command")
        self.assertEqual(produced["plugin_recommended"]["eventName"], "plugin.recommended")
        self.assertEqual(produced["plugin_recommended"]["contextValue"],
                         "external::high::session-start")
        self.assertEqual(produced["plugin_installed"]["eventName"], "plugin.installed")
        self.assertEqual(produced["plugin_installed"]["contextValue"],
                         "external::none::self-directed")
        # session.started keeps the model as componentId (original design) AND now
        # also carries it in the context tuple for a consistent model dimension.
        self.assertEqual(produced["session_start"]["componentId"], "claude-opus-4-8")
        self.assertEqual(produced["session_start"]["contextName"], "os::org_bucket::model")
        self.assertEqual(produced["session_start"]["contextValue"],
                         "darwin::production::claude-opus-4-8")

    def test_first_party_subcommand_becomes_component(self):
        ev = self._pdp(self._record("command_invoked",
                       {"binary": "sf-context", "category": "plugin_command",
                        "subcommand": "status-org", "outcome": "success"}))
        self.assertEqual(ev["componentId"], "sf-context.status-org")

    def test_other_record_maps_to_other_only(self):
        # Capture never emits an "other" command.invoked record anymore (an
        # unrecognized binary produces no event — see CommandTierTests). This is a
        # belt-and-braces check that IF such a record reached the mapper, the
        # PdpEvent would carry only "other", never a real command/args.
        ev = self._pdp(self._record("command_invoked",
                       {"binary": "other", "category": "other", "outcome": "failure"}))
        self.assertEqual(ev["componentId"], "other")

    def test_unknown_record_is_skipped(self):
        self.assertIsNone(sft._to_pdp_event({"event": "not_real", "payload": {}}))
        self.assertIsNone(sft._to_pdp_event("garbage"))

    def test_exception_error_class_reclamped_at_egress(self):
        # Defense-in-depth: a record buffered BEFORE the capture-side clamp existed
        # (or otherwise carrying an arbitrary error_class) must still be clamped when
        # projected to the wire — an unrecognized api_error value becomes "unknown"...
        leaky = self._record("exception",
                             {"error_class": "/etc/passwd leaked", "kind": "api_error"})
        self.assertEqual(self._pdp(leaky)["componentId"], "unknown")
        # ...and a dormant hook record is hard-clamped regardless of its value.
        hook = self._record("exception", {"error_class": "ValueError", "kind": "hook"})
        self.assertEqual(self._pdp(hook)["componentId"], "unknown")
        # A legitimate enum value still survives the egress clamp.
        ok = self._record("exception", {"error_class": "overloaded", "kind": "api_error"})
        self.assertEqual(self._pdp(ok)["componentId"], "overloaded")


class AgentHarnessDetectionTests(unittest.TestCase):
    """_agent_harness(): closed-enum detection of the executing harness from env
    markers, with a defined precedence and an `other` fallback. Env is cleared per
    case so detection is deterministic regardless of the harness these tests run
    under."""

    _ENUM = {"claude-code", "cursor", "codex", "copilot-cli", "opencode", "other"}

    def _harness(self, env):
        with mock.patch.dict(os.environ, env, clear=True):
            return sft._agent_harness()

    def test_claude_code_via_child_session(self):
        self.assertEqual(self._harness({"CLAUDE_CODE_CHILD_SESSION": "1"}), "claude-code")

    def test_claude_code_via_claudecode(self):
        self.assertEqual(self._harness({"CLAUDECODE": "1"}), "claude-code")

    def test_cursor(self):
        self.assertEqual(self._harness({"CURSOR_AGENT": "1"}), "cursor")

    def test_codex(self):
        self.assertEqual(self._harness({"CODEX_HOME": "/x/.codex"}), "codex")

    def test_copilot_cli_via_home(self):
        self.assertEqual(self._harness({"COPILOT_HOME": "/x/.copilot"}), "copilot-cli")

    def test_copilot_cli_via_token(self):
        self.assertEqual(self._harness({"COPILOT_GITHUB_TOKEN": "gh_x"}), "copilot-cli")

    def test_opencode_via_any_prefixed_var(self):
        self.assertEqual(self._harness({"OPENCODE_CONFIG": "/x/opencode.json"}), "opencode")

    def test_unknown_env_is_other(self):
        self.assertEqual(self._harness({}), "other")

    def test_claude_code_wins_when_multiple_markers_present(self):
        # A Claude Code hook can run inside another editor's integrated terminal, so
        # several markers appear at once; the process that spawned this script is
        # Claude Code, so it must win.
        self.assertEqual(
            self._harness({"CLAUDECODE": "1", "CURSOR_AGENT": "1", "CODEX_HOME": "/x"}),
            "claude-code")

    def test_always_returns_a_closed_enum_value(self):
        for env in ({"CLAUDECODE": "1"}, {"CURSOR_AGENT": "1"}, {"CODEX_HOME": "/x"},
                    {"COPILOT_HOME": "/x"}, {"OPENCODE_X": "1"}, {"UNRELATED": "1"}, {}):
            self.assertIn(self._harness(env), self._ENUM)


class A4dEventTests(unittest.TestCase):
    """The UIP projection (_to_a4d_event): a flat eventName + attributes map that
    the O11y reporter serializes into the UIP `message` field. It is derived from
    the PdpEvent so the shapes can't diverge on the core dims, and it carries the
    same common envelope. UIP is the SOLE event shape on the O11y transport now that
    the App Insights sink has been removed. Pure-function tests — no cwd/consent
    state.

    Privacy-neutral in this commit: the callers pass no org_id, so no org id appears
    (org_id is threaded in a follow-up commit; see the org_id test below which pins
    the projection's behavior when it IS passed)."""

    def _record(self, event, payload, **envelope):
        base = {"event": event, "os": "darwin", "org_bucket": "production",
                "plugin_version": "1.10.0", "ci": False, "model": "claude-opus-4-8",
                "machine_id": "MID", "session_id": "S1",
                "arch": "arm64", "os_version": "24.5.0", "locale": "en-US",
                "plugin_name": "salesforce-development", "payload": payload}
        base.update(envelope)
        return base

    def test_flat_shape_and_pdp_dimension_parity(self):
        rec = self._record("skill_dispatched",
                           {"skill": "platform-apex-generate", "skill_domain": "platform"})
        pdp = sft._to_pdp_event(rec)
        a4d = sft._to_a4d_event(rec)
        # Same eventName + same load-bearing dims as the PdpEvent.
        self.assertEqual(a4d["eventName"], pdp["eventName"])
        self.assertEqual(a4d["attributes"]["componentId"], pdp["componentId"])
        self.assertEqual(a4d["attributes"]["contextName"], pdp["contextName"])
        self.assertEqual(a4d["attributes"]["contextValue"], pdp["contextValue"])

    def test_full_envelope_present(self):
        rec = self._record("command_invoked",
                           {"binary": "sf-context", "category": "plugin_command",
                            "subcommand": "status-org", "outcome": "success"})
        attrs = sft._to_a4d_event(rec)["attributes"]
        self.assertLessEqual(
            {"session_Id", "os", "arch", "os_version", "locale", "plugin_name",
             "plugin_version", "org_bucket", "model", "ci", "machine_id"},
            set(attrs.keys()))
        self.assertEqual(attrs["ci"], "false")   # normalized token
        self.assertEqual(attrs["machine_id"], "MID")

    def test_event_volume_carried_as_measurement(self):
        rec = self._record("session_end", {"duration_ms": 2500, "event_count": 7})
        a4d = sft._to_a4d_event(rec)
        self.assertEqual(a4d["eventName"], "session.ended")
        self.assertEqual(a4d["attributes"]["eventVolume"], 7)

    def test_org_bucket_override_flows_through(self):
        rec = self._record("session_start", {"is_first_run": True}, org_bucket="none")
        a4d = sft._to_a4d_event(rec, org_bucket="sandbox")
        self.assertEqual(a4d["attributes"]["org_bucket"], "sandbox")

    def test_no_org_id_when_not_passed(self):
        # Privacy-neutral default: without an org_id argument, the UIP attributes
        # carry NO org id — matching the current coarse-bucket-only posture.
        rec = self._record("session_start", {"is_first_run": True})
        a4d = sft._to_a4d_event(rec)
        self.assertNotIn("org_id", a4d["attributes"])
        self.assertNotIn("org_id", json.dumps(a4d))

    def test_org_id_added_only_when_non_empty(self):
        # When an org_id IS threaded through (follow-up commit's transmit path), it
        # rides UIP as a first-class attribute; an empty org_id adds no key.
        rec = self._record("session_start", {"is_first_run": True})
        with_id = sft._to_a4d_event(rec, org_id="00Dxx0000000001")
        self.assertEqual(with_id["attributes"]["org_id"], "00Dxx0000000001")
        empty = sft._to_a4d_event(rec, org_id="")
        self.assertNotIn("org_id", empty["attributes"])

    def test_never_leaks_username_command_or_paths(self):
        rec = self._record("command_invoked",
                           {"binary": "other", "category": "other", "outcome": "success"})
        a4d = sft._to_a4d_event(rec)
        blob = json.dumps(a4d)
        for forbidden in ("username", "deploy-projectatlas", "SECRET", "/Users/", "--token"):
            self.assertNotIn(forbidden, blob)
        self.assertEqual(a4d["attributes"]["componentId"], "other")

    def test_unknown_record_is_skipped(self):
        self.assertIsNone(sft._to_a4d_event({"event": "not_real", "payload": {}}))
        self.assertIsNone(sft._to_a4d_event("garbage"))


class A4dDatasetAlignmentTests(unittest.TestCase):
    """The four UIP dataset-alignment keys (skillSource, modelId, user_Id,
    skillName) that let a team/product usage board consume our rows directly from
    the shared Skills Analytics dataset. They carry NO new/PII data — skillSource
    is a constant, modelId/user_Id alias values already sent, and skillName is
    already in the PDP componentId. They ride UIP ONLY, exactly like org_id."""

    def _record(self, event, payload, **envelope):
        base = {"event": event, "os": "darwin", "org_bucket": "production",
                "plugin_version": "1.10.0", "ci": False, "model": "claude-opus-4-8",
                "machine_id": "MID", "session_id": "S1",
                "arch": "arm64", "os_version": "24.5.0", "locale": "en-US",
                "plugin_name": "salesforce-development", "payload": payload}
        base.update(envelope)
        return base

    def test_skillsource_constant_on_every_event(self):
        for event, payload in (
            ("session_start", {"is_first_run": True}),
            ("session_end", {"duration_ms": 10, "event_count": 1}),
            ("command_invoked", {"binary": "sf-context", "category": "plugin_command",
                                 "subcommand": "status-org", "outcome": "success"}),
            ("skill_dispatched", {"skill": "platform-apex-generate", "skill_domain": "platform"}),
            ("agent_dispatched", {"agent_type": "salesforce-dev"}),
            ("mcp_tool_used", {"mcp_server": "salesforce-lsp", "mcp_tool": "apex_diagnostics",
                               "outcome": "success"}),
            ("exception", {"error_class": "DeployError", "kind": "deploy"}),
        ):
            attrs = sft._to_a4d_event(self._record(event, payload))["attributes"]
            self.assertEqual(attrs["skillSource"], "salesforce-development",
                             msg=f"skillSource missing/wrong on {event}")

    def test_modelid_aliases_model(self):
        rec = self._record("session_start", {"is_first_run": True})
        attrs = sft._to_a4d_event(rec)["attributes"]
        self.assertEqual(attrs["modelId"], "claude-opus-4-8")
        self.assertEqual(attrs["modelId"], attrs["model"])

    def test_user_id_aliases_machine_id(self):
        # AFV counts MAU/DAU via dcount(user_Id) using an anonymous machine-scoped
        # token — never PII. Our machine_id is the analog; user_Id must equal it.
        rec = self._record("command_invoked",
                           {"binary": "sf-context", "category": "plugin_command",
                            "subcommand": "status-org", "outcome": "success"})
        attrs = sft._to_a4d_event(rec)["attributes"]
        self.assertEqual(attrs["user_Id"], "MID")
        self.assertEqual(attrs["user_Id"], attrs["machine_id"])

    def test_skillname_only_on_skill_dispatched(self):
        skill = sft._to_a4d_event(
            self._record("skill_dispatched",
                         {"skill": "platform-soql-query", "skill_domain": "platform"}))
        self.assertEqual(skill["attributes"]["skillName"], "platform-soql-query")
        # Not a skill event -> no skillName key (kept semantically clean).
        for event, payload in (
            ("command_invoked", {"binary": "sf-context", "category": "plugin_command",
                                 "subcommand": "status-org", "outcome": "success"}),
            ("agent_dispatched", {"agent_type": "salesforce-dev"}),
            ("mcp_tool_used", {"mcp_server": "salesforce-lsp", "mcp_tool": "x",
                               "outcome": "success"}),
            ("session_start", {"is_first_run": True}),
        ):
            attrs = sft._to_a4d_event(self._record(event, payload))["attributes"]
            self.assertNotIn("skillName", attrs, msg=f"skillName leaked onto {event}")

    def test_alignment_keys_are_a4d_only_never_on_pdp(self):
        # Same guarantee as org_id: these four keys must never appear on the fixed
        # PDP shape — they are UIP dataset-alignment only.
        rec = self._record("skill_dispatched",
                           {"skill": "platform-apex-generate", "skill_domain": "platform"})
        pdp_blob = json.dumps(sft._to_pdp_event(rec))
        for key in ("skillSource", "modelId", "user_Id", "skillName"):
            self.assertNotIn(key, pdp_blob, msg=f"{key} leaked onto PDP")

    def test_harness_on_uip_only(self):
        # harness rides UIP as a first-class attribute ($.properties.harness) and,
        # like org_id and the alignment keys, must NEVER appear on the fixed PDP shape.
        rec = self._record("session_start", {"is_first_run": True}, harness="cursor")
        attrs = sft._to_a4d_event(rec)["attributes"]
        self.assertEqual(attrs["harness"], "cursor")
        self.assertNotIn("harness", json.dumps(sft._to_pdp_event(rec)))

    def test_harness_empty_when_record_has_none(self):
        # No harness on the record → empty string (never a raw env value / missing key
        # crash); the attribute is always present on UIP.
        rec = self._record("session_start", {"is_first_run": True})
        self.assertEqual(sft._to_a4d_event(rec)["attributes"]["harness"], "")

    def test_event_time_on_every_uip_event_only(self):
        cases = (
            ("session_start", {"is_first_run": True}),
            ("session_end", {"duration_ms": 10, "event_count": 1}),
            ("command_invoked", {"binary": "sf-context", "category": "plugin_command",
                                 "subcommand": "status-org", "outcome": "success"}),
            ("skill_dispatched", {"skill": "platform-apex-generate",
                                  "skill_domain": "platform"}),
            ("agent_dispatched", {"agent_type": "salesforce-dev"}),
            ("mcp_tool_used", {"mcp_server": "salesforce-lsp", "mcp_tool": "query",
                               "outcome": "success"}),
            ("exception", {"error_class": "rate_limit", "kind": "api_error"}),
        )
        for event, payload in cases:
            rec = self._record(event, payload, timestamp=1724170000000)
            self.assertEqual(sft._to_a4d_event(rec)["attributes"]["eventTime"],
                             "1724170000000", event)
            self.assertNotIn("eventTime", json.dumps(sft._to_pdp_event(rec)), event)

    def test_event_time_empty_when_timestamp_missing(self):
        rec = self._record("session_start", {"is_first_run": True})
        self.assertEqual(sft._to_a4d_event(rec)["attributes"]["eventTime"], "")

    def test_is_first_run_only_on_session_started(self):
        first = self._record("session_start", {"is_first_run": True})
        later = self._record("session_start", {"is_first_run": False})
        self.assertEqual(sft._to_a4d_event(first)["attributes"]["is_first_run"], "true")
        self.assertEqual(sft._to_a4d_event(later)["attributes"]["is_first_run"], "false")
        ended = self._record("session_end", {"duration_ms": 10, "event_count": 1})
        self.assertNotIn("is_first_run", sft._to_a4d_event(ended)["attributes"])
        self.assertNotIn("is_first_run", json.dumps(sft._to_pdp_event(first)))

    def test_command_surface_is_derived_on_command_invoked_only(self):
        def surface(subcommand):
            rec = self._record("command_invoked", {
                "binary": "sf-context", "category": "plugin_command",
                "subcommand": subcommand, "outcome": "success"})
            return rec, sft._to_a4d_event(rec)["attributes"]["commandSurface"]

        user, user_surface = surface("status-org")
        plugin_install, plugin_install_surface = surface("plugin-install")
        hook, hook_surface = surface("telemetry-flush")
        unknown, unknown_surface = surface("")
        self.assertEqual(user_surface, "user")
        self.assertEqual(plugin_install_surface, "user")
        self.assertEqual(hook_surface, "hook")
        self.assertEqual(unknown_surface, "unknown")
        for rec in (user, plugin_install, hook, unknown):
            self.assertNotIn("commandSurface", json.dumps(sft._to_pdp_event(rec)))
        session = self._record("session_start", {"is_first_run": True})
        self.assertNotIn("commandSurface", sft._to_a4d_event(session)["attributes"])

    def test_deploy_gate_commands_are_hook_surface(self):
        for subcommand in ("prod-check", "destructive", "auto-deploy"):
            rec = self._record("command_invoked", {
                "binary": "sf-deploy-gate", "category": "plugin_command",
                "subcommand": subcommand, "outcome": "success"})
            attrs = sft._to_a4d_event(rec)["attributes"]
            self.assertEqual(attrs["commandSurface"], "hook", subcommand)
            self.assertNotIn("commandSurface", json.dumps(sft._to_pdp_event(rec)))


class GoldenWireShapeTests(unittest.TestCase):
    """CHARACTERIZATION safety net: pin the EXACT PDP + UIP wire shapes for every
    event type. This is the guardrail for the telemetry refactor track — any change
    to a transmitted byte (a new field, a renamed key, a changed value) fails here,
    so the wire shape can never silently drift (the eval harness and the O11y
    dashboards depend on it). If you change a shape ON PURPOSE, update the goldens in
    the SAME commit and say so in the message."""

    PFID = "aJCEE000000SLW94AO"

    # A fully-populated envelope so each projected event is 100% determined.
    ENV = {
        "os": "darwin", "arch": "arm64", "os_version": "23.5.0", "locale": "en_US",
        "plugin_name": "salesforce-development", "plugin_version": "1.11.0",
        "org_bucket": "production", "model": "claude-opus-4-8", "ci": False,
        "machine_id": "MID123", "harness": "claude-code", "session_id": "S1",
    }

    PAYLOADS = {
        "session_start": {"is_first_run": True},
        "session_end": {"duration_ms": 2500, "event_count": 7},
        "command_invoked": {"binary": "sf-context", "category": "plugin_command",
                            "subcommand": "status-org", "outcome": "success"},
        "skill_dispatched": {"skill": "platform-apex-generate", "skill_domain": "platform"},
        "agent_dispatched": {"agent_type": "code-review"},
        "exception": {"error_class": "rate_limit", "kind": "api_error"},
        "mcp_tool_used": {"mcp_server": "api-context", "mcp_tool": "query", "outcome": "success"},
    }

    def _record(self, event):
        return {"event": event, **self.ENV, "payload": self.PAYLOADS[event]}

    def test_pdp_wire_shape_golden(self):
        expected = {
            "session_start": {
                "productFeatureId": self.PFID, "eventName": "session.started",
                "componentId": "claude-opus-4-8", "contextName": "os::org_bucket::model",
                "contextValue": "darwin::production::claude-opus-4-8"},
            "session_end": {
                "productFeatureId": self.PFID, "eventName": "session.ended",
                "componentId": "session", "eventVolume": 7,
                "contextName": "duration_ms", "contextValue": "2500"},
            "command_invoked": {
                "productFeatureId": self.PFID, "eventName": "command.invoked",
                "componentId": "sf-context.status-org",
                "contextName": "outcome::category", "contextValue": "success::plugin_command"},
            "skill_dispatched": {
                "productFeatureId": self.PFID, "eventName": "skill.dispatched",
                "componentId": "platform-apex-generate",
                "contextName": "skill_domain", "contextValue": "platform"},
            "agent_dispatched": {
                "productFeatureId": self.PFID, "eventName": "agent.dispatched",
                "componentId": "code-review",
                "contextName": "org_bucket", "contextValue": "production"},
            "exception": {
                "productFeatureId": self.PFID, "eventName": "exception.raised",
                "componentId": "rate_limit", "contextName": "kind", "contextValue": "api_error"},
            "mcp_tool_used": {
                "productFeatureId": self.PFID, "eventName": "mcpTool.used",
                "componentId": "api-context.query",
                "contextName": "outcome", "contextValue": "success"},
        }
        for event, want in expected.items():
            self.assertEqual(sft._to_pdp_event(self._record(event)), want, event)

    def _uip_common(self, component_id, context_name, context_value):
        return {
            "componentId": component_id, "contextName": context_name,
            "contextValue": context_value, "session_Id": "S1", "os": "darwin",
            "arch": "arm64", "os_version": "23.5.0", "locale": "en_US",
            "plugin_name": "salesforce-development", "plugin_version": "1.11.0",
            "org_bucket": "production", "model": "claude-opus-4-8", "ci": "false",
            "machine_id": "MID123", "harness": "claude-code",
            "eventTime": "",
            "skillSource": "salesforce-development", "modelId": "claude-opus-4-8",
            "user_Id": "MID123",
        }

    def test_uip_wire_shape_golden(self):
        expected = {
            "session_start": {"eventName": "session.started", "attributes": {
                **self._uip_common("claude-opus-4-8", "os::org_bucket::model",
                                   "darwin::production::claude-opus-4-8"),
                "is_first_run": "true"}},
            "session_end": {"eventName": "session.ended", "attributes": {
                **self._uip_common("session", "duration_ms", "2500"), "eventVolume": 7}},
            "command_invoked": {"eventName": "command.invoked", "attributes": {
                **self._uip_common("sf-context.status-org", "outcome::category",
                                   "success::plugin_command"),
                "commandSurface": "user"}},
            "skill_dispatched": {"eventName": "skill.dispatched", "attributes": {
                **self._uip_common("platform-apex-generate", "skill_domain", "platform"),
                "skillName": "platform-apex-generate"}},
            "agent_dispatched": {"eventName": "agent.dispatched", "attributes":
                self._uip_common("code-review", "org_bucket", "production")},
            "exception": {"eventName": "exception.raised", "attributes":
                self._uip_common("rate_limit", "kind", "api_error")},
            "mcp_tool_used": {"eventName": "mcpTool.used", "attributes":
                self._uip_common("api-context.query", "outcome", "success")},
        }
        for event, want in expected.items():
            self.assertEqual(sft._to_a4d_event(self._record(event)), want, event)

    def test_uip_org_id_added_only_when_present(self):
        rec = self._record("skill_dispatched")
        self.assertEqual(
            sft._to_a4d_event(rec, org_id="00Dxx0000000001")["attributes"]["org_id"],
            "00Dxx0000000001")
        self.assertNotIn("org_id", sft._to_a4d_event(rec)["attributes"])


@unittest.skipIf(os.name == "nt" or not hasattr(os, "chmod"),
                 "POSIX file-permission bits only")
class AtRestPermissionTests(TelemetryCaptureTestBase):
    """Review M3: telemetry-state files carry pseudonymous identifiers (machine id,
    session id, transmit-only org username, flusher output) and must be created
    0o600 — and the helper must TIGHTEN a pre-existing 0o644 file too, since O_TRUNC
    alone preserves an existing file's mode."""

    def _mode(self, path):
        return Path(path).stat().st_mode & 0o777

    def test_write_private_creates_and_tightens(self):
        p = Path(".sf") / "probe.json"
        sft._write_private(p, "{}")
        self.assertEqual(self._mode(p), 0o600)
        # A pre-existing world-readable file is tightened on the next write
        # (os.replace swaps in the private inode) — the H4 correctness point.
        os.chmod(p, 0o644)
        sft._write_private(p, '{"x": 1}')
        self.assertEqual(self._mode(p), 0o600)
        self.assertEqual(p.read_text(), '{"x": 1}')

    def test_open_private_append_tightens_existing(self):
        p = Path(".sf") / "probe.log"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("old\n")
        os.chmod(p, 0o644)
        with sft._open_private_append(p, binary=True) as fh:
            fh.write(b"new\n")
        self.assertEqual(self._mode(p), 0o600)
        self.assertEqual(p.read_text(), "old\nnew\n")

    def test_open_private_append_refuses_fifo_without_hanging(self):
        # Agent review [P2]: opening a FIFO O_WRONLY blocks until a reader appears, so a
        # pre-planted FIFO at the transmit-log path could hang the SessionEnd hook.
        # O_NONBLOCK must make the open fail fast rather than block. A SIGALRM guard
        # turns a regression (blocking open) into a failure instead of a hung test.
        import signal
        fifo = Path(".sf") / "telemetry-transmit.log"
        fifo.parent.mkdir(parents=True, exist_ok=True)
        os.mkfifo(fifo)

        def _timeout(signum, frame):
            raise AssertionError("_open_private_append blocked on a FIFO (no O_NONBLOCK)")

        old = signal.signal(signal.SIGALRM, _timeout)
        signal.alarm(3)
        try:
            with self.assertRaises(OSError):
                sft._open_private_append(fifo, binary=True)
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old)

    def test_open_private_append_refuses_symlink(self):
        # DX Prism prizm-default: a pre-planted symlink at a buffer/log path must not
        # redirect our append (or the fchmod) to an arbitrary file — O_NOFOLLOW makes
        # open() fail, so we never write through it or change the target's perms.
        outside = Path(".sf") / "outside-target.txt"
        outside.parent.mkdir(parents=True, exist_ok=True)
        outside.write_text("original")
        os.chmod(outside, 0o644)
        link = Path(".sf") / "telemetry-buffer-evil.jsonl"
        os.symlink(outside.name, link)  # relative symlink within .sf
        with self.assertRaises(OSError):
            sft._open_private_append(link)
        self.assertEqual(outside.read_text(), "original", "wrote through a symlink")
        self.assertEqual(self._mode(outside), 0o644, "chmod'd a symlink target")

    def test_tighten_existing_fixes_stale_0644(self):
        p = Path(".sf") / "probe2.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("{}")
        os.chmod(p, 0o644)
        sft._tighten_existing(p)
        self.assertEqual(self._mode(p), 0o600)

    def test_tighten_existing_refuses_symlink(self):
        # DX Prism prizm-default: the on-read chmod must not follow a symlink and flip
        # an arbitrary target to 0o600. A pre-planted symlink at a state path is left
        # untouched (its target keeps its mode).
        outside = Path(".sf") / "tighten-outside.txt"
        outside.parent.mkdir(parents=True, exist_ok=True)
        outside.write_text("x")
        os.chmod(outside, 0o644)
        link = Path(".sf") / "telemetry-org.json"
        os.symlink(outside.name, link)
        sft._tighten_existing(link)  # must be a silent no-op, not a raise
        self.assertEqual(self._mode(outside), 0o644, "chmod'd a symlink target")

    def test_captured_buffer_and_machine_id_are_private(self):
        self.capture("session_start", payload={"session_id": "S1", "source": "startup"})
        bufs = self.buffers()
        self.assertTrue(bufs, "session_start should write a buffer")
        for b in bufs:
            self.assertEqual(self._mode(b), 0o600, f"{b} is world-readable")
        mid = sft._machine_id_file()
        self.assertTrue(Path(mid).exists())
        self.assertEqual(self._mode(mid), 0o600, "machine-id file is world-readable")

    def test_session_marker_is_private(self):
        self.capture("session_start", payload={"session_id": "S1", "source": "startup"})
        marker = sft._session_file("S1")
        self.assertTrue(Path(marker).exists())
        self.assertEqual(self._mode(marker), 0o600, "session marker is world-readable")

    def test_existing_machine_id_is_tightened_on_read(self):
        # An upgrade case: a machine id minted 0o644 by an older build must be tightened
        # to 0o600 the next time it is read, not left world-readable indefinitely.
        mid_file = sft._machine_id_file()
        mid_file.parent.mkdir(parents=True, exist_ok=True)
        mid_file.write_text("deadbeef" * 4)
        os.chmod(mid_file, 0o644)
        self.assertEqual(sft._machine_id(), "deadbeef" * 4)  # reads the existing fallback
        self.assertEqual(self._mode(mid_file), 0o600, "stale 0o644 machine id not tightened")


class HardOffPurgeAuditTests(TelemetryCaptureTestBase):
    """Review L1 + M12: a hard-off must remove ALL local telemetry state — including
    the flusher transmit log and per-session markers — and merely INSPECTING status
    must never mint identifier state."""

    def test_off_purges_transmit_log_and_session_markers(self):
        self.capture("session_start", payload={"session_id": "S1", "source": "startup"})
        sft._TRANSMIT_LOG.parent.mkdir(parents=True, exist_ok=True)
        sft._TRANSMIT_LOG.write_text("flusher stderr: connected to acme@example.com\n")
        marker = sft._session_file("S1")
        self.assertTrue(marker.exists())
        self.assertTrue(sft._TRANSMIT_LOG.exists())
        self.assertTrue(self.buffers())
        self.consent("off")
        self.assertFalse(sft._TRANSMIT_LOG.exists(), "transmit log survived opt-out")
        self.assertFalse(marker.exists(), "session marker survived opt-out")
        self.assertFalse(self.buffers(), "buffers survived opt-out")

    def test_status_does_not_mint_machine_id(self):
        self.assertFalse(Path(sft._machine_id_file()).exists())
        buf = io.StringIO()
        with redirect_stdout(buf):
            sft.cmd_consent(["sf-context", "telemetry", "status"])
        self.assertIn("telemetry status", buf.getvalue().lower())
        self.assertFalse(Path(sft._machine_id_file()).exists(),
                         "inspecting status must not mint a machine id")

    def test_machine_id_peek_returns_empty_without_minting(self):
        self.assertEqual(sft._machine_id(mint=False), "")
        self.assertFalse(Path(sft._machine_id_file()).exists())


class OrgCacheTests(TelemetryCaptureTestBase):
    """Agent review #4: a raw org id must NEVER be persisted to the org cache, and
    the transmit-only username the cache DOES carry must not outlive its purpose —
    it is dropped on `telemetry off` and after a send."""

    @contextmanager
    def _mock_org_display(self, result):
        # Patch BOTH the subprocess call AND `_sf_command`: on a host without `sf` on
        # PATH (CI), `_resolve_org_context` short-circuits in `_sf_command` (via
        # shutil.which) BEFORE reaching subprocess.run, so mocking run alone is not
        # enough — the resolve would return the empty "none" envelope and never see
        # our mocked org. Force a resolvable argv so the mocked run is exercised.
        proc = mock.Mock()
        proc.stdout = json.dumps({"result": result})
        with mock.patch.object(sft, "_sf_command",
                               return_value=["sf", "org", "display", "--json"]), \
                mock.patch.object(sft.subprocess, "run", return_value=proc):
            yield

    def test_resolve_returns_org_id_but_never_caches_it(self):
        # org_id is returned live (for the transmit liveness check AND the UIP
        # shape), but the on-disk cache must hold only {org_bucket, username} —
        # never the raw org id (at-rest minimization: the cache-fallback transmit
        # path therefore emits no org id, only the live-resolved path carries it).
        self._org.stop()
        with self._mock_org_display({"id": "00Dxx0000000001",
                                     "username": "admin@acme.example",
                                     "orgId": "00Dxx0000000001"}):
            ctx = sft._resolve_org_context()
        self._org.start()
        self.assertEqual(ctx["org_id"], "00Dxx0000000001")   # returned to caller
        cached = json.loads(sft._ORG_CACHE.read_text())
        self.assertNotIn("org_id", cached, "raw org id must never be cached")
        self.assertNotIn("00Dxx0000000001", json.dumps(cached))
        self.assertEqual(set(cached.keys()), {"org_bucket", "username"})

    def test_org_context_read_reports_empty_org_id(self):
        # Even if a stale cache somehow held an org_id, the reader zeroes it — the
        # coarse bucket is the only org signal any caller may rely on.
        sft._ORG_CACHE.parent.mkdir(parents=True, exist_ok=True)
        sft._ORG_CACHE.write_text(json.dumps(
            {"org_id": "00Dstale", "org_bucket": "sandbox", "username": "u@x.example"}))
        ctx = sft._org_context()
        self.assertEqual(ctx["org_id"], "")
        self.assertEqual(ctx["org_bucket"], "sandbox")

    def test_off_purges_org_cache_with_its_username(self):
        # The cache carries the transmit-only username; `telemetry off` must delete it
        # so the username is not retained on disk after an opt-out.
        sft._ORG_CACHE.parent.mkdir(parents=True, exist_ok=True)
        sft._ORG_CACHE.write_text(json.dumps(
            {"org_bucket": "production", "username": "admin@acme.example"}))
        self.consent("off")
        self.assertFalse(sft._ORG_CACHE.exists(),
                         "off must drop the org cache (holds the transmit-only username)")

    def test_send_drops_org_cache_after_queueing(self):
        # After the detached sender queues the job, the org cache (username) is dropped
        # so it does not persist between sessions — the next session re-resolves fresh.
        Path(".sf").mkdir(exist_ok=True)
        sft._ORG_CACHE.parent.mkdir(parents=True, exist_ok=True)
        sft._ORG_CACHE.write_text(json.dumps(
            {"org_bucket": "production", "username": "admin@acme.example"}))
        snap = Path(".sf/telemetry-snapshot-oc.jsonl")
        snap.write_text(json.dumps({"event": "session_start", "session_id": "S1",
                                    "os": "darwin", "payload": {}}) + "\n")
        with mock.patch.object(sft, "_spawn_flusher", return_value=True):
            rc = sft.cmd_send(["sf-context", "telemetry-send", str(snap)])
        self.assertEqual(rc, 0)
        self.assertFalse(sft._ORG_CACHE.exists(),
                         "sender must drop the org cache after queueing the job")


class WindowsSfCommandTests(unittest.TestCase):
    """Agent review (Windows metachar): on the batch-shim (`sf.cmd`) path, cmd.exe
    RE-parses the serialized command line, so `_sf_command` must FAIL CLOSED (return
    None) when the resolved shim path or any arg carries a cmd metacharacter —
    mirroring sf_context.build_command — instead of handing `&`, `%`, `!` to cmd.exe.
    """

    def _resolve_as_windows_shim(self, resolved):
        # Simulate Windows resolving `sf` to a `.cmd` shim: os.name=="nt",
        # shutil.which -> the shim path, and a COMSPEC for the argv prefix.
        return (
            mock.patch.object(sft.os, "name", "nt"),
            mock.patch("shutil.which", return_value=resolved),
            mock.patch.dict(sft.os.environ, {"COMSPEC": r"C:\Windows\System32\cmd.exe"}),
        )

    def test_clean_shim_path_builds_comspec_argv(self):
        # Baseline: a benign shim path + benign args yields the COMSPEC /c prefix.
        p1, p2, p3 = self._resolve_as_windows_shim(r"C:\Program Files\sf\bin\sf.cmd")
        with p1, p2, p3:
            cmd = sft._sf_command(["org", "display", "--json"])
        self.assertEqual(
            cmd, [r"C:\Windows\System32\cmd.exe", "/c",
                  r"C:\Program Files\sf\bin\sf.cmd", "org", "display", "--json"])

    def test_program_files_x86_parens_in_path_are_allowed(self):
        # The system-provided shim path legitimately contains ( ) — the PATH guard
        # must NOT reject those (only the chars cmd.exe reparses even when quoted).
        shim = r"C:\Program Files (x86)\sf\bin\sf.cmd"
        p1, p2, p3 = self._resolve_as_windows_shim(shim)
        with p1, p2, p3:
            cmd = sft._sf_command(["org", "display", "--json"])
        self.assertIsNotNone(cmd)
        self.assertEqual(cmd[2], shim)

    def test_metacharacter_in_resolved_shim_path_is_refused(self):
        # A shim path carrying a reparse-dangerous char (e.g. `&`, `%`, `!`) must
        # fail closed rather than be handed to cmd.exe /c.
        for bad in (r"C:\a&b\sf.cmd", r"C:\a%PATH%\sf.cmd", r"C:\a!x!\sf.cmd",
                    r"C:\a^b\sf.cmd", 'C:\\a"b\\sf.cmd'):
            p1, p2, p3 = self._resolve_as_windows_shim(bad)
            with p1, p2, p3:
                self.assertIsNone(sft._sf_command(["org", "display", "--json"]),
                                  f"shim path {bad!r} must be refused")

    def test_metacharacter_in_arg_is_refused(self):
        # Even with a clean shim path, an arg carrying a cmd metacharacter fails closed.
        for bad_arg in ("a&b", "a|b", "a%x%", "a!x!", "a>b", "a<b", "a^b", 'a"b',
                        "a(b", "a)b", "a\nb"):
            p1, p2, p3 = self._resolve_as_windows_shim(r"C:\sf\bin\sf.cmd")
            with p1, p2, p3:
                self.assertIsNone(sft._sf_command(["org", bad_arg]),
                                  f"arg {bad_arg!r} must be refused")

    def test_posix_path_is_not_metachar_guarded(self):
        # On POSIX `sf` is a real exe (not a .cmd shim), so the cmd.exe guard does
        # not apply and the resolved argv is returned as-is.
        with mock.patch.object(sft.os, "name", "posix"), \
                mock.patch("shutil.which", return_value="/usr/local/bin/sf"):
            cmd = sft._sf_command(["org", "display", "--json"])
        self.assertEqual(cmd, ["/usr/local/bin/sf", "org", "display", "--json"])

    def test_unresolvable_sf_returns_none(self):
        # No `sf` on PATH → None, so the caller degrades to the "none" org envelope
        # instead of raising FileNotFoundError (this is exactly what broke CI when
        # tests mocked subprocess.run but not command resolution — review #1).
        with mock.patch("shutil.which", return_value=None):
            self.assertIsNone(sft._sf_command(["org", "display", "--json"]))


class ShimParityTests(unittest.TestCase):
    """Review M8: _sf_command (telemetry) and build_command (sf_context) now share
    sf_shim, so they must build BYTE-IDENTICAL argv and pin the SAME metachar refusal
    sets. This test fails if the two ever diverge again — the enforcement the old
    'MUST stay in sync' comment lacked."""

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            "sf_context_shim_parity", _SCRIPTS_DIR / "sf_context.py")
        cls.sfx = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.sfx)

    def test_metachar_sets_match_across_modules(self):
        self.assertEqual(self.sfx._CMD_ARG_METACHARACTERS,
                         sft._shim._CMD_ARG_METACHARACTERS)
        self.assertEqual(self.sfx._CMD_PATH_METACHARACTERS,
                         sft._shim._CMD_PATH_METACHARACTERS)

    def test_build_argv_parity_across_cases(self):
        cases = [
            ("/usr/local/bin/sf", ["org", "display", "--json"]),          # posix exe
            (r"C:\sf\bin\sf.cmd", ["org", "display", "--json"]),          # clean shim
            (r"C:\Program Files (x86)\sf\bin\sf.cmd", ["org", "display"]),  # parens ok
            (r"C:\a&b\sf.cmd", ["org", "display"]),                       # bad shim path
            (r"C:\sf\bin\sf.cmd", ["org", "a&b"]),                        # bad arg
            (None, ["org", "display"]),                                   # unresolved
        ]
        for resolved, args in cases:
            with mock.patch("shutil.which", return_value=resolved), \
                    mock.patch.dict(os.environ,
                                    {"COMSPEC": r"C:\Windows\System32\cmd.exe"}):
                mine = sft._sf_command(list(args))
                theirs = self.sfx.build_command("sf", list(args))
            self.assertEqual(mine, theirs,
                             f"argv divergence for resolved={resolved!r} args={args!r}")


class CliNodeModulesTests(unittest.TestCase):
    """Windows QE finding: the SF CLI's @salesforce/telemetry (the transport the
    flusher needs) must be located across BOTH install layouts. On Windows the
    installer puts the shim in `sf\\bin\\sf.cmd` but the library in a SIBLING
    `sf\\client\\node_modules` — NOT an ancestor of bin — so a plain walk-up
    resolved "" and BOTH sinks were silently skipped (no events transmitted).
    """

    @contextmanager
    def _cli_layout(self, shim_rel, lib_rel):
        # Build a fake CLI install under a temp dir: `shim_rel` is where `sf`
        # resolves, `lib_rel` is where @salesforce/telemetry lives. Patch
        # shutil.which -> the shim and os.path.realpath -> identity so the walk
        # starts at the shim's real dir.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            shim = root / shim_rel
            shim.parent.mkdir(parents=True, exist_ok=True)
            shim.write_text("")
            lib = root / lib_rel / "@salesforce" / "telemetry"
            lib.mkdir(parents=True, exist_ok=True)
            with mock.patch("shutil.which", return_value=str(shim)), \
                    mock.patch("os.path.realpath", side_effect=lambda p: p):
                yield root, lib_rel

    def test_windows_client_sibling_layout_is_found(self):
        # sf\bin\sf.cmd  +  sf\client\node_modules\@salesforce\telemetry
        with self._cli_layout("sf/bin/sf.cmd", "sf/client/node_modules") as (root, lib_rel):
            resolved = sft._cli_node_modules()
        self.assertEqual(Path(resolved), root / lib_rel,
                         "the client/ sibling node_modules must be resolved on Windows")

    def test_posix_walkup_layout_still_found(self):
        # …/lib/sf/bin/sf  +  …/lib/sf/node_modules\@salesforce\telemetry (ancestor)
        with self._cli_layout("lib/sf/bin/sf", "lib/sf/node_modules") as (root, lib_rel):
            resolved = sft._cli_node_modules()
        self.assertEqual(Path(resolved), root / lib_rel,
                         "the walk-up node_modules must still resolve on POSIX")

    def test_missing_library_resolves_empty(self):
        # `sf` resolves but no @salesforce/telemetry anywhere → "" (transmit no-ops).
        with tempfile.TemporaryDirectory() as td:
            shim = Path(td) / "sf" / "bin" / "sf.cmd"
            shim.parent.mkdir(parents=True, exist_ok=True)
            shim.write_text("")
            with mock.patch("shutil.which", return_value=str(shim)), \
                    mock.patch("os.path.realpath", side_effect=lambda p: p):
                self.assertEqual(sft._cli_node_modules(), "")

    def test_no_sf_on_path_resolves_empty(self):
        with mock.patch("shutil.which", return_value=None):
            self.assertEqual(sft._cli_node_modules(), "")


class TransmitTests(TelemetryCaptureTestBase):
    """Stream B: the flush/transmit path — job shape, consent gating, buffer
    consumption, detached spawn, and the username-is-transmit-only guarantee."""

    def _seed_session(self):
        self.capture("session_start", payload={"session_id": "S1", "model": "m"})
        self.capture("skill_dispatched", payload={"session_id": "S1", "tool_input": {"skill": "platform-soql-query"}})
        self.capture("command_invoked", "success",
                     payload={"session_id": "S1", "tool_input": {"command": "sf-context status-org"}})

    def transmit_job(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            sft.cmd_transmit(["sf-context", "telemetry-transmit"])
        return json.loads(buf.getvalue())

    def test_transmit_job_has_pdp_events_and_target(self):
        self._seed_session()
        job = self.transmit_job()
        self.assertTrue(job["enabled"])
        self.assertEqual(job["productFeatureId"], "aJCEE000000SLW94AO")
        self.assertEqual(len(job["events"]), 3)
        for ev in job["events"]:
            self.assertEqual(ev["productFeatureId"], "aJCEE000000SLW94AO")
            self.assertIn("eventName", ev)

    def test_transmit_job_has_no_hardcoded_upload_endpoint(self):
        # Upload MUST go through the connected org (endpoint derived from its
        # instanceUrl by the flusher). The job must not carry a static URL that
        # could egress telemetry to a non-org host.
        self._seed_session()
        job = self.transmit_job()
        self.assertNotIn("o11yUploadEndpoint", job)
        self.assertNotIn("salesforce.com/o11y", json.dumps(job))

    def test_transmit_disabled_is_empty(self):
        self._seed_session()
        self.consent("off")
        job = self.transmit_job()
        self.assertFalse(job["enabled"])
        self.assertEqual(job["events"], [])

    def test_transmit_job_has_a4d_events(self):
        # UIP shape rides the SAME O11y transport as PDP: the job carries one
        # a4dEvent per buffered record, alongside the PdpEvents.
        self._seed_session()
        job = self.transmit_job()
        self.assertIn("a4dEvents", job)
        self.assertEqual(len(job["a4dEvents"]), len(job["events"]))
        for ev in job["a4dEvents"]:
            self.assertIn("eventName", ev)
            self.assertIn("attributes", ev)

    def test_transmit_disabled_has_no_a4d_events(self):
        # The consent gate suppresses every shape/sink — no a4dEvents when disabled.
        self._seed_session()
        self.consent("off")
        job = self.transmit_job()
        self.assertFalse(job["enabled"])
        self.assertEqual(job.get("a4dEvents", []), [])

    def test_a4d_events_never_leak_username(self):
        # Same guarantee as PDP/AI: the connection username must NEVER appear inside
        # a UIP event. (org_id is a separate deliberate field, asserted below.)
        self._org.stop()
        with mock.patch.object(sft, "_resolve_org_context", return_value={
                "org_id": "00Dxx0000000001", "org_bucket": "production",
                "username": "admin@acme-prod.example"}):
            self._seed_session()
            job = self.transmit_job()
        self._org.start()
        for ev in job["a4dEvents"]:
            self.assertNotIn("admin@acme-prod.example", json.dumps(ev))
            self.assertNotIn("username", json.dumps(ev))

    def test_org_id_rides_a4d_only_not_pdp(self):
        # The raw org id, live-resolved at transmit, is stamped onto the UIP shape
        # ALONE. It must be present on every UIP event and ABSENT from every PDP
        # event (which stays coarse-bucket-only).
        oid = "00Dxx0000000001"
        self._org.stop()
        with mock.patch.object(sft, "_resolve_org_context", return_value={
                "org_id": oid, "org_bucket": "production",
                "username": "admin@acme-prod.example"}):
            self._seed_session()
            job = self.transmit_job()
        self._org.start()
        self.assertTrue(job["a4dEvents"])
        for ev in job["a4dEvents"]:
            self.assertEqual(ev["attributes"].get("org_id"), oid)
        for ev in job["events"]:            # PDP shape — coarse bucket only
            self.assertNotIn(oid, json.dumps(ev))

    def test_org_id_absent_from_a4d_on_cache_fallback(self):
        # When the live resolve misses and transmit falls back to the cache (which
        # never persists the org id), NO org id reaches UIP — only the live path
        # carries it. Simulate by resolving an empty org id with a cached bucket.
        self._org.stop()
        with mock.patch.object(sft, "_resolve_org_context", return_value={
                "org_id": "", "org_bucket": "sandbox", "username": "u@x.example"}):
            self._seed_session()
            job = self.transmit_job()
        self._org.start()
        for ev in job["a4dEvents"]:
            self.assertNotIn("org_id", ev["attributes"])

    def test_transmit_job_carries_consent_file(self):
        # The job hands the flusher the ABSOLUTE machine-wide consent path so it can
        # re-check opt-out at the last moment (AC3, cross-project hard-off).
        self._seed_session()
        job = self.transmit_job()
        self.assertIn("consentFile", job)
        self.assertEqual(job["consentFile"], str(sft._consent_file()))
        self.assertTrue(Path(job["consentFile"]).is_absolute())

    def test_transmit_never_leaks_username_into_events(self):
        # The org username is captured for the connection only; it must appear as
        # the transmit-job `username` but NEVER inside any event/envelope.
        self._org.stop()  # override the base mock to include a username
        with mock.patch.object(sft, "_resolve_org_context", return_value={
                "org_id": "00Dxx0000000001", "org_bucket": "production",
                "username": "admin@acme-prod.example"}):
            self.capture("session_start", payload={"session_id": "S1"})
            self.capture("command_invoked", "success",
                         payload={"session_id": "S1", "tool_input": {"command": "sf org list"}})
            job = self.transmit_job()
        self._org.start()  # restore for tearDown symmetry
        self.assertEqual(job["username"], "admin@acme-prod.example")
        for ev in job["events"]:
            self.assertNotIn("username", json.dumps(ev))
        # And the username never entered the on-disk buffer envelope either.
        for ev in self.events():
            self.assertNotIn("username", ev)
            self.assertNotIn("admin@acme-prod.example", json.dumps(ev))

    def _run_flush(self, spawn_sender):
        """Drive cmd_flush with _spawn_sender mocked. Returns the parsed stdout."""
        stdin = io.StringIO(json.dumps({"session_id": "S1"}))
        buf = io.StringIO()
        with mock.patch.object(sft, "_spawn_sender", spawn_sender), \
                mock.patch.object(sft.sys, "stdin", stdin), redirect_stdout(buf):
            rc = sft.cmd_flush(["sf-context", "telemetry-flush"])
        self.assertEqual(rc, 0)
        return json.loads(buf.getvalue())

    def test_flush_hook_snapshots_and_spawns_sender_without_org_call(self):
        # The SessionEnd hook must be non-blocking: it writes session_end, renames
        # the buffer to a private snapshot, spawns the DETACHED sender, and makes NO
        # `sf` call itself (org resolution is deferred to the sender). It must also
        # spawn NO Node flusher directly.
        self._seed_session()
        captured = {}
        sender = mock.Mock(side_effect=lambda snap: captured.update(snapshot=snap) or True)
        with mock.patch.object(sft, "_resolve_org_context",
                               side_effect=AssertionError("hook must not resolve org")), \
                mock.patch.object(sft, "_spawn_flusher",
                                  side_effect=AssertionError("hook must not spawn the Node flusher")):
            out = self._run_flush(sender)
        self.assertTrue(out.get("continue"))
        self.assertEqual(sender.call_count, 1)
        # The live buffer was renamed away; the snapshot holds all 4 events incl. end.
        self.assertFalse(list(Path(".sf").glob("telemetry-buffer-*.jsonl")),
                         "hook must rename the session's buffer to a snapshot")
        snap = Path(captured["snapshot"])
        self.assertTrue(snap.exists())
        names = [json.loads(l)["event"] for l in snap.read_text().splitlines() if l.strip()]
        self.assertIn("session_end", names)
        self.assertEqual(len(names), 4)  # start, skill, command, end

    def test_flush_isolates_concurrent_sessions(self):
        # Per-session buffers (agent/Prizm review): when S1 ends, its flush renames
        # only S1's own buffer file and transmits only S1's records. A concurrent S2
        # writes a SEPARATE file that is never observed or drained by S1's flush, so
        # S2's events are neither transmitted early nor misattributed to S1's org.
        self._seed_session()  # S1: session_start, skill, command
        self.capture("session_start", payload={"session_id": "S2", "model": "m2"})
        self.capture("skill_dispatched",
                     payload={"session_id": "S2",
                              "tool_input": {"skill": "platform-apex-generate"}})
        sender = mock.Mock(return_value=True)
        self._run_flush(sender)  # feeds {"session_id": "S1"}
        self.assertEqual(sender.call_count, 1)
        snap = Path(sender.call_args.args[0])
        snap_sessions = {json.loads(l)["session_id"]
                         for l in snap.read_text().splitlines() if l.strip()}
        self.assertEqual(snap_sessions, {"S1"},
                         "snapshot must carry only the ending session's records")
        self.assertFalse(Path(".sf/telemetry-buffer-S1.jsonl").exists(),
                         "S1's own buffer file is renamed to the snapshot")
        s2 = Path(".sf/telemetry-buffer-S2.jsonl")
        self.assertTrue(s2.exists(), "S2's separate buffer file is untouched")
        remaining = {json.loads(l)["session_id"]
                     for l in s2.read_text().splitlines() if l.strip()}
        self.assertEqual(remaining, {"S2"},
                         "a concurrent session's records remain in its own file")

    def test_each_session_flush_delivers_its_own_events_no_stranding(self):
        # The reported race: S2 ending after S1 must still transmit S2's earlier
        # events (previously S2 could snapshot only its session_end while its earlier
        # records were stranded in the shared buffer). With per-session buffers each
        # flush renames its OWN inode, so both sessions' events are delivered and no
        # buffer is left behind.
        self._seed_session()  # S1
        self.capture("session_start", payload={"session_id": "S2", "model": "m2"})
        self.capture("command_invoked", "success",
                     payload={"session_id": "S2",
                              "tool_input": {"command": "sf-context status-org"}})
        s1_sender = mock.Mock(return_value=True)
        self._run_flush(s1_sender)  # S1 ends
        s2_sender = mock.Mock(return_value=True)
        stdin = io.StringIO(json.dumps({"session_id": "S2"}))
        buf = io.StringIO()
        with mock.patch.object(sft, "_spawn_sender", s2_sender), \
                mock.patch.object(sft.sys, "stdin", stdin), redirect_stdout(buf):
            sft.cmd_flush(["sf-context", "telemetry-flush"])
        self.assertEqual(s1_sender.call_count, 1)
        self.assertEqual(s2_sender.call_count, 1,
                         "S2's own flush must transmit S2's events (not stranded)")
        s2_snap = Path(s2_sender.call_args.args[0])
        s2_sessions = {json.loads(l)["session_id"]
                       for l in s2_snap.read_text().splitlines() if l.strip()}
        self.assertEqual(s2_sessions, {"S2"})
        self.assertFalse(list(Path(".sf").glob("telemetry-buffer-*.jsonl")),
                         "both sessions' buffers are fully drained")

    def test_sender_builds_job_and_spawns_flusher_then_deletes_snapshot(self):
        # The detached sender (cmd_send) is where org resolution + upload happen.
        # It builds the transmit job from the snapshot, spawns the Node flusher on a
        # pending file holding all events, and removes the snapshot.
        self._seed_session()
        sender = mock.Mock(return_value=True)
        captured = {}
        self._run_flush(sender)                      # produces the snapshot
        snap = sender.call_args.args[0]
        with mock.patch.object(sft, "_spawn_flusher",
                               side_effect=lambda p: captured.update(pending=p) or True):
            rc = sft.cmd_send(["sf-context", "telemetry-send", str(snap)])
        self.assertEqual(rc, 0)
        pending = json.loads(Path(captured["pending"]).read_text())
        names = [e["eventName"] for e in pending["events"]]
        self.assertIn("session.ended", names)
        self.assertEqual(len(pending["events"]), 4)  # start, skill, command, end
        self.assertFalse(Path(snap).exists(), "sender must delete the snapshot when done")

    def test_flush_cleans_up_snapshot_when_sender_spawn_fails(self):
        # Agent review #3: _spawn_sender's return was ignored, so a failed launch left
        # the snapshot stranded on disk indefinitely. On spawn failure the snapshot
        # must be deleted, not orphaned.
        self._seed_session()
        captured = {}
        # A sender that "fails to launch" (returns False) and records the snapshot it
        # was handed so we can assert it was cleaned up.
        def failing_sender(snap):
            captured["snap"] = snap
            return False
        stdin = io.StringIO(json.dumps({"session_id": "S1"}))
        buf = io.StringIO()
        with mock.patch.object(sft, "_spawn_sender", failing_sender), \
                mock.patch.object(sft.sys, "stdin", stdin), redirect_stdout(buf):
            rc = sft.cmd_flush(["sf-context", "telemetry-flush"])
        self.assertEqual(rc, 0)
        self.assertFalse(Path(captured["snap"]).exists(),
                         "a failed sender spawn must not strand the snapshot on disk")
        self.assertFalse(list(Path(".sf").glob("telemetry-snapshot-*.jsonl")),
                         "no snapshot should remain after a failed spawn")

    def test_send_cleans_up_pending_when_flusher_spawn_fails(self):
        # Agent review #3: the pending job carries the transmit-only USERNAME. The
        # Node flusher normally deletes it, but a FAILED launch never runs — so on
        # spawn failure cmd_send must delete the pending file itself, or the username
        # is stranded on disk indefinitely.
        self._seed_session()
        sender = mock.Mock(return_value=True)
        self._run_flush(sender)                      # produces the snapshot
        snap = sender.call_args.args[0]
        captured = {}
        def failing_flusher(pending):
            captured["pending"] = pending
            return False
        with mock.patch.object(sft, "_spawn_flusher", failing_flusher):
            rc = sft.cmd_send(["sf-context", "telemetry-send", str(snap)])
        self.assertEqual(rc, 0)
        self.assertFalse(Path(captured["pending"]).exists(),
                         "a failed flusher spawn must not strand the pending job (holds username)")
        self.assertFalse(list(Path(".sf").glob("telemetry-pending-*.json")),
                         "no pending job should remain after a failed spawn")
        self.assertFalse(Path(snap).exists(), "snapshot still consumed on spawn failure")

    def test_flush_disabled_does_not_spawn(self):
        self._seed_session()
        self.consent("off")  # discards buffer
        # A raising sender would be swallowed by cmd_flush's guard, so assert on the
        # call count of a non-raising mock instead — a real assertion, not a no-op.
        sender = mock.Mock(return_value=True)
        out = self._run_flush(sender)
        self.assertTrue(out.get("continue"))
        self.assertEqual(sender.call_count, 0)

    def test_flush_empty_buffer_does_not_spawn_or_write_session_end(self):
        # No buffered events (fresh project) -> the hook skips wholesale: no
        # session_end written, no sender spawned. (Regression: previously cmd_flush
        # always wrote session_end and spawned even for a do-nothing session, and the
        # guarding test was a false pass because its AssertionError was swallowed.)
        sender = mock.Mock(return_value=True)
        out = self._run_flush(sender)
        self.assertTrue(out.get("continue"))
        self.assertEqual(sender.call_count, 0)
        self.assertFalse(list(Path(".sf").glob("telemetry-buffer-*.jsonl")),
                         "no buffer should be created for a do-nothing session")

    def test_dispatch_routes_flush_and_transmit(self):
        # sf_telemetry.dispatch must recognize the transmit + send subcommands.
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = sft.dispatch(["sf-context", "telemetry-transmit"])
        self.assertEqual(rc, 0)
        self.assertIn("events", json.loads(buf.getvalue()))
        # telemetry-send routes to cmd_send (no-op on a missing snapshot).
        with mock.patch.object(sft, "cmd_send", return_value=0) as send:
            self.assertEqual(sft.dispatch(["sf-context", "telemetry-send", "nope.jsonl"]), 0)
        self.assertEqual(send.call_count, 1)

    def test_session_start_does_not_resolve_org(self):
        # SessionStart is local-first / single-process: capturing session_start
        # must NOT invoke the org CLI. Org resolution is deferred to flush. If the
        # startup path ever calls _resolve_org_context again, this fails loudly.
        self._org.stop()
        with mock.patch.object(sft, "_resolve_org_context",
                               side_effect=AssertionError("session_start must not resolve org")):
            self.capture("session_start", payload={"session_id": "S1", "source": "startup"})
            self.capture("command_invoked", "success",
                         payload={"session_id": "S1", "tool_input": {"command": "sf-context status-org"}})
        self._org.start()  # restore for tearDown symmetry
        # The events still landed — capture never depends on org resolution.
        self.assertEqual({e["event"] for e in self.events()},
                         {"session_start", "command_invoked"})

    def test_flush_stamps_resolved_org_bucket_on_events(self):
        # Deferral must not cost accuracy: org is resolved ONCE at flush and the
        # bucket is stamped onto the transmitted events, even though the buffered
        # envelopes captured it as the unresolved default ("none").
        self._org.stop()
        with mock.patch.object(sft, "_resolve_org_context", return_value={
                "org_id": "00Dxx0000000001", "org_bucket": "sandbox",
                "username": "admin@acme.example"}):
            self.capture("session_start", payload={"session_id": "S1", "model": "m"})
            self.capture("agent_dispatched", payload={"session_id": "S1", "tool_input": {"subagent_type": "salesforce-dev"}})
            job = self.transmit_job()
        self._org.start()
        # The buffered envelopes carry the unresolved default...
        for ev in self.events():
            self.assertEqual(ev["org_bucket"], "none")
        # ...but the transmitted PDP events carry the flush-resolved bucket.
        started = next(e for e in job["events"] if e["eventName"] == "session.started")
        agent = next(e for e in job["events"] if e["eventName"] == "agent.dispatched")
        # session.started context is os::org_bucket::model — the resolved bucket is
        # the middle segment now that model is the trailing dim. The OS segment is
        # derived at runtime (darwin/linux/windows), so read it from the same source
        # rather than hardcoding — the test must pass on any CI platform.
        self.assertEqual(started["contextValue"], f"{sft._os_name()}::sandbox::m")
        self.assertEqual(agent["contextValue"], "sandbox")
        self.assertEqual(job["username"], "admin@acme.example")


class FlusherScriptTests(unittest.TestCase):
    """The detached Node transmitter exists and is a thin, fail-open sender."""

    def setUp(self):
        self.js = (_SCRIPTS_DIR / "telemetry-flush.js")

    def test_flusher_exists(self):
        self.assertTrue(self.js.exists(), "telemetry-flush.js must ship next to sf_telemetry.py")

    def test_flusher_exits_promptly_when_o11y_stalls(self):
        # EXECUTABLE guarantee (not just source regex): stub the CLI transport so the
        # sole O11y leg HANGS forever. The flusher must still exit 0 and delete the
        # pending file within its deadline window — proving the leg is bounded by
        # withDeadline rather than able to hang the detached process indefinitely.
        import shutil, subprocess, time, tempfile
        node = shutil.which("node")
        if not node:
            self.skipTest("node not on PATH")
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            nm = td / "node_modules" / "@salesforce"
            (nm / "telemetry").mkdir(parents=True)
            (nm / "core").mkdir(parents=True)
            # @salesforce/telemetry stub: create() returns a reporter whose O11y send
            # never resolves (hang).
            (nm / "telemetry" / "index.js").write_text(
                "class TelemetryReporter {\n"
                "  static async create(o){ return new TelemetryReporter(o); }\n"
                "  constructor(o){ this.options=o||{};\n"
                "    this.o11yReporter = { sendPdpEvent: () => new Promise(()=>{}) };\n"  # hangs
                "    this.reporter = null; }\n"
                "  sendPdpEvent(){ return new Promise(()=>{}); }\n"
                "  sendTelemetryEvent(){}\n"
                "  async flush(){}\n  async stopAsync(){ return new Promise(()=>{}); }\n"
                "  async stop(){}\n}\n"
                "module.exports = { TelemetryReporter };\n"
            )
            (nm / "telemetry" / "package.json").write_text('{"name":"@salesforce/telemetry","main":"index.js"}')
            (nm / "core" / "index.js").write_text(
                "class Org { static async create(){ return new Org(); }\n"
                "  async getConnection(){ return { instanceUrl: 'https://x.my.salesforce.com' }; } }\n"
                "module.exports = { Org };\n"
            )
            (nm / "core" / "package.json").write_text('{"name":"@salesforce/core","main":"index.js"}')
            job = {
                "cliNodeModules": str(td / "node_modules"),
                "project": "salesforce-development",
                "username": "u@example",  # enables the (now-hanging) O11y leg
                "events": [{"eventName": "session.started", "productFeatureId": "x"}],
            }
            pending = td / "pending.json"
            pending.write_text(json.dumps(job))
            # Shrink the O11y deadline (prod default 15s) to 1s via the test-only env
            # seam so this exercises the timeout path fast.
            env = dict(os.environ, SF_DEV_TELEMETRY_O11Y_DEADLINE_MS="1000")
            start = time.monotonic()
            proc = subprocess.run([node, str(self.js), str(pending)], timeout=15,
                                  capture_output=True, env=env)
            elapsed = time.monotonic() - start
            self.assertEqual(proc.returncode, 0, "flusher must exit 0 even when O11y hangs")
            # The ref'd deadline keeps the process alive until the O11y leg times out,
            # so the finally that unlinks the pending file ALWAYS runs — a pure hang
            # (no active handle) must not let node exit before cleanup.
            self.assertFalse(pending.exists(), "pending file must be consumed")
            # ~1s deadline + node startup; must be well under the 15s prod window.
            self.assertLess(elapsed, 8, f"flusher must not hang on a stalled O11y (took {elapsed:.1f}s)")

    def test_flusher_reruns_consent_check_and_skips_when_opted_out(self):
        # AC3 (hard-off): a `telemetry off` landing AFTER the job was queued — incl.
        # a job queued by ANOTHER project, whose pending file `off` can't reach —
        # must stop the upload. The flusher re-reads the machine consent right before
        # any sink runs; if it says {"enabled": false}, NO sink runs, but the pending
        # file is STILL consumed (so it doesn't wedge / re-send).
        import shutil, subprocess, tempfile
        node = shutil.which("node")
        if not node:
            self.skipTest("node not on PATH")
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            # A transport stub that writes a SENTINEL FILE the instant any sink is
            # constructed. We assert the sentinel never appears — a side effect,
            # not stderr, because an exception thrown inside the sink rejects into
            # withDeadline's swallowed promise and would never reach stderr (so a
            # stderr-only assertion could pass even if the sink actually ran).
            sentinel = td / "sink-ran.sentinel"
            nm = td / "node_modules" / "@salesforce"
            (nm / "telemetry").mkdir(parents=True)
            (nm / "core").mkdir(parents=True)
            (nm / "telemetry" / "index.js").write_text(
                "const fs=require('fs');\n"
                "class TelemetryReporter { static async create(){ "
                f"fs.writeFileSync({json.dumps(str(sentinel))}, 'ran'); "
                "return new TelemetryReporter(); }\n"
                "  sendTelemetryEvent(){} async stop(){} get o11yReporter(){ return null; } }\n"
                "module.exports = { TelemetryReporter };\n"
            )
            (nm / "telemetry" / "package.json").write_text('{"name":"@salesforce/telemetry","main":"index.js"}')
            (nm / "core" / "index.js").write_text(
                "const fs=require('fs');\n"
                "class Org { static async create(){ "
                f"fs.writeFileSync({json.dumps(str(sentinel))}, 'ran'); return new Org(); }}\n"
                "  async getConnection(){ return { instanceUrl: 'https://x.my.salesforce.com' }; } }\n"
                "module.exports = { Org };\n"
            )
            (nm / "core" / "package.json").write_text('{"name":"@salesforce/core","main":"index.js"}')
            consent = td / "telemetry-config.json"
            consent.write_text(json.dumps({"enabled": False}))  # user opted out post-queue
            job = {
                "cliNodeModules": str(td / "node_modules"),
                "consentFile": str(consent),
                "username": "u@example",
                "events": [{"eventName": "session.started", "productFeatureId": "x"}],
            }
            pending = td / "pending.json"
            pending.write_text(json.dumps(job))
            proc = subprocess.run([node, str(self.js), str(pending)], timeout=15,
                                  capture_output=True)
            self.assertEqual(proc.returncode, 0)
            # No sink was ever constructed (sentinel side-effect never fired)...
            self.assertFalse(sentinel.exists(),
                             "no sink may run once the user has opted out")
            # ...and the pending file is still consumed.
            self.assertFalse(pending.exists(), "opted-out job must still be consumed")

    def test_flusher_optout_during_async_construction_blocks_send(self):
        # Round-6 D: a `telemetry off` that lands AFTER main()'s check but DURING a
        # sink's async reporter construction must still stop the send. We simulate
        # that by having the stub reporter's create() flip the consent file to
        # {"enabled": false} — exactly the mid-construction interleaving — then
        # assert NO event was sent (the last-instant re-check before the send loop
        # catches it). A "sent" sentinel proves the send loop never ran.
        import shutil, subprocess, tempfile
        node = shutil.which("node")
        if not node:
            self.skipTest("node not on PATH")
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            sent = td / "event-sent.sentinel"
            built = td / "reporter-built.sentinel"
            consent = td / "telemetry-config.json"
            consent.write_text(json.dumps({"enabled": True}))  # ON at main()'s check
            nm = td / "node_modules" / "@salesforce"
            (nm / "telemetry").mkdir(parents=True)
            (nm / "core").mkdir(parents=True)
            # create() records that construction was REACHED (built sentinel), flips
            # consent OFF (the racing `telemetry off`), THEN returns a reporter whose
            # send writes the "sent" sentinel. Asserting built EXISTS but sent does
            # NOT proves the block happened at the pre-send re-check — not via some
            # earlier failure that would also leave `sent` absent (Codex round-7 nit).
            (nm / "telemetry" / "index.js").write_text(
                "const fs=require('fs');\n"
                "class TelemetryReporter { static async create(){ "
                f"fs.writeFileSync({json.dumps(str(built))}, '1'); "
                f"fs.writeFileSync({json.dumps(str(consent))}, JSON.stringify({{enabled:false}})); "
                "return new TelemetryReporter(); }\n"
                f"  sendTelemetryEvent(){{ fs.writeFileSync({json.dumps(str(sent))}, 'ai'); }}\n"
                "  async stop(){} async stopAsync(){} async flush(){}\n"
                f"  get o11yReporter(){{ return {{ sendPdpEvent: async () => {{ fs.writeFileSync({json.dumps(str(sent))}, 'o11y'); }} }}; }} }}\n"
                "module.exports = { TelemetryReporter };\n"
            )
            (nm / "telemetry" / "package.json").write_text('{"name":"@salesforce/telemetry","main":"index.js"}')
            (nm / "core" / "index.js").write_text(
                "class Org { static async create(){ return new Org(); }\n"
                "  async getConnection(){ return { instanceUrl: 'https://x.my.salesforce.com' }; } }\n"
                "module.exports = { Org };\n"
            )
            (nm / "core" / "package.json").write_text('{"name":"@salesforce/core","main":"index.js"}')
            job = {
                "cliNodeModules": str(td / "node_modules"),
                "consentFile": str(consent),
                "username": "u@example",
                "events": [{"eventName": "session.started", "productFeatureId": "x"}],
            }
            pending = td / "pending.json"
            pending.write_text(json.dumps(job))
            proc = subprocess.run([node, str(self.js), str(pending)], timeout=15,
                                  capture_output=True)
            self.assertEqual(proc.returncode, 0)
            # Construction was actually reached (so a "no send" result is meaningful,
            # not a masked early failure)...
            self.assertTrue(built.exists(),
                            "reporter construction must be reached for this test to be valid")
            # ...yet no event was sent because the pre-send re-check caught the flip.
            self.assertFalse(sent.exists(),
                             "an opt-out during async construction must still block the send")
            self.assertFalse(pending.exists(), "pending must be consumed")

    def test_flusher_uip_failure_still_flushes_pdp(self):
        # Agent review #2: PDP events are enqueued first, but flush()/stopAsync() sit
        # AFTER the UIP (sendTelemetryEvent) loop. A rejected UIP send must NOT abort
        # the batch: the PDP events already in the collector must still flush and the
        # reporter must be torn down. Stub o11y so sendPdpEvent records a sentinel,
        # sendTelemetryEvent REJECTS, and flush() records a sentinel — then assert both
        # the PDP send AND the flush happened despite the UIP rejection.
        import shutil, subprocess, tempfile
        node = shutil.which("node")
        if not node:
            self.skipTest("node not on PATH")
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            pdp_sent = td / "pdp-sent.sentinel"
            flushed = td / "flushed.sentinel"
            nm = td / "node_modules" / "@salesforce"
            (nm / "telemetry").mkdir(parents=True)
            (nm / "core").mkdir(parents=True)
            (nm / "telemetry" / "index.js").write_text(
                "const fs=require('fs');\n"
                "class TelemetryReporter { static async create(){ return new TelemetryReporter(); }\n"
                f"  async flush(){{ fs.writeFileSync({json.dumps(str(flushed))}, '1'); }}\n"
                "  async stopAsync(){} async stop(){}\n"
                "  get o11yReporter(){ return {\n"
                f"    sendPdpEvent: async () => {{ fs.writeFileSync({json.dumps(str(pdp_sent))}, '1'); }},\n"
                "    sendTelemetryEvent: async () => { throw new Error('UIP boom'); },\n"
                "  }; } }\n"
                "module.exports = { TelemetryReporter };\n"
            )
            (nm / "telemetry" / "package.json").write_text('{"name":"@salesforce/telemetry","main":"index.js"}')
            (nm / "core" / "index.js").write_text(
                "class Org { static async create(){ return new Org(); }\n"
                "  async getConnection(){ return { instanceUrl: 'https://x.my.salesforce.com' }; } }\n"
                "module.exports = { Org };\n"
            )
            (nm / "core" / "package.json").write_text('{"name":"@salesforce/core","main":"index.js"}')
            job = {
                "cliNodeModules": str(td / "node_modules"),
                "username": "u@example",
                "events": [{"eventName": "session.started", "productFeatureId": "x"}],
                "a4dEvents": [{"eventName": "session.started",
                               "attributes": {"skillSource": "salesforce-development"}}],
            }
            pending = td / "pending.json"
            pending.write_text(json.dumps(job))
            proc = subprocess.run([node, str(self.js), str(pending)], timeout=15,
                                  capture_output=True)
            self.assertEqual(proc.returncode, 0)
            self.assertTrue(pdp_sent.exists(), "PDP events must be enqueued")
            self.assertTrue(flushed.exists(),
                            "a UIP send failure must not prevent the PDP batch from flushing")
            self.assertFalse(pending.exists(), "pending must be consumed")

    def test_flusher_consumes_malformed_pending(self):
        # A malformed/unreadable pending file must still be unlinked — otherwise it
        # wedges the buffer and re-runs every session. (Regression: the JSON.parse
        # early-return used to sit OUTSIDE the finally.)
        import shutil, subprocess, tempfile
        node = shutil.which("node")
        if not node:
            self.skipTest("node not on PATH")
        with tempfile.TemporaryDirectory() as td:
            pending = Path(td) / "pending.json"
            pending.write_text("{ this is not json")
            proc = subprocess.run([node, str(self.js), str(pending)], timeout=15,
                                  capture_output=True)
            self.assertEqual(proc.returncode, 0)
            self.assertFalse(pending.exists(), "malformed pending must be consumed")

    def test_flusher_clamps_deadline_env(self):
        # The deadline env seams are test-only AND bounded: a bogus/huge value can't
        # keep the detached process alive for minutes. Regression guard for the
        # unbounded Number(env) seam (2147483647 => ~24.8 days).
        src = self.js.read_text()
        self.assertIn("MAX_DEADLINE_MS", src)
        self.assertRegex(src, r"Math\.min\(v, MAX_DEADLINE_MS\)")

    def test_flusher_rechecks_consent_source(self):
        src = self.js.read_text()
        # Honors the ecosystem opt-out env vars AND the machine consent file.
        self.assertIn("SF_DISABLE_TELEMETRY", src)
        self.assertIn("DO_NOT_TRACK", src)
        self.assertIn("job.consentFile", src)
        self.assertIn("enabled === false", src)

    def test_flusher_uses_pdp_and_is_failopen(self):
        src = self.js.read_text()
        # Uses the O11y PdpEvent path via the bundled CLI reporter.
        self.assertIn("sendPdpEvent", src)
        self.assertIn("@salesforce/telemetry", src)
        self.assertIn("getConnectionFn", src)         # uploads through the org
        self.assertIn("cliNodeModules", src)          # resolves the CLI's bundle
        # Endpoint is derived from the org's own instanceUrl — never a static host.
        self.assertIn("instanceUrl", src)
        self.assertIn("ui-telemetry", src)
        self.assertNotIn("telemetry.salesforce.com", src)
        # No connection => no O11y send (never egress off-org / unauthenticated).
        self.assertIn("if (!job.username) return", src)
        # Fail-open: always exits 0 and cleans up the pending file.
        self.assertIn("process.exit(0)", src)
        self.assertIn("unlinkSync", src)

    def test_flusher_single_o11y_leg(self):
        """Single-sink: the App Insights leg was removed. There is exactly ONE
        transport now — O11y — bounded by its own end-to-end deadline via
        withDeadline, and not required for exit 0 (fail-open)."""
        src = self.js.read_text()
        self.assertIn("sendO11y", src)
        self.assertIn("withDeadline", src)
        self.assertIn("O11Y_DEADLINE_MS", src)
        # The App Insights leg and its dual-sink fan-out are gone entirely.
        self.assertNotIn("sendAppInsights", src)
        self.assertNotIn("AI_DEADLINE_MS", src)
        self.assertNotIn("appInsightsKey", src)
        self.assertNotIn("Promise.allSettled", src)
        self.assertRegex(src, r"withDeadline\(\s*sendO11y\(")

    def test_flusher_awaits_delivery_before_flush(self):
        """Regression guard for the silent-drop bug: the public
        reporter.sendPdpEvent() is fire-and-forget, so calling it and then
        flushing immediately uploads NOTHING (the event's async chain hasn't
        landed it in the O11y collector yet — verified live: messagesReceived=0).
        The flusher MUST await the underlying o11yReporter.sendPdpEvent (whose
        promise resolves only once the event is in the collector), then flush."""
        src = self.js.read_text()
        # Awaits the underlying O11y reporter's send (not the fire-and-forget
        # public method) so the event is in the collector before we flush.
        self.assertIn("o11yReporter", src)
        self.assertIn("await o11y.sendPdpEvent", src)
        # Explicitly flushes the batch before stopping.
        self.assertIn("await reporter.flush()", src)
        self.assertIn("await reporter.stopAsync()", src)
        # The bug shape: a bare `reporter.sendPdpEvent(event)` in a loop with no
        # await is what silently dropped everything (the public method is gated on
        # `enableO11y && o11yReporter`, so it no-ops when O11y didn't init). The
        # send loop must NOT call the public method at all — only the awaited
        # underlying one.
        self.assertNotIn("reporter.sendPdpEvent(event)", src,
                         "the public sendPdpEvent silently drops — never use it in the loop")
        # When O11y did not initialize, the leg must SKIP honestly (fail-open),
        # not pretend to send via the no-op public method.
        self.assertRegex(src, r"if \(!o11y\) return;")

    def test_flusher_a4d_in_o11y_leg(self):
        """UIP is a second event SHAPE on the SOLE O11y transport, not a separate
        sink: it is emitted inside sendO11y (same reporter/connection/endpoint as
        PDP) via the reporter's sendTelemetryEvent over job.a4dEvents — NOT as a
        separate withDeadline leg."""
        src = self.js.read_text()
        self.assertIn("job.a4dEvents", src)
        # Emitted on the same O11y reporter as PDP.
        self.assertIn("o11y.sendTelemetryEvent", src)
        # It rides the SAME leg — there is no second withDeadline entry for UIP.
        self.assertNotRegex(src, r"withDeadline\(\s*sendA4d")
        self.assertNotIn("sendA4d", src)
        # The a4dEvents reference lives inside sendO11y: assert it appears in the
        # O11y function body (between `function sendO11y` and the next top-level
        # `async function`).
        o11y_start = src.index("async function sendO11y")
        o11y_end = src.index("async function", o11y_start + 1)
        self.assertIn("a4dEvents", src[o11y_start:o11y_end],
                      "UIP must be emitted inside the O11y leg (sendO11y)")

    def test_flusher_a4d_delivered_through_o11y_reporter(self):
        # EXECUTABLE behavior guarantee (complements the source-shape test above):
        # spawn the REAL Node flusher against a stub @salesforce/telemetry whose
        # o11yReporter records every send to a capture file. Proves the UIP events
        # actually reach the wire — same reporter/connection as PDP, via
        # o11yReporter.sendTelemetryEvent(name, attributes) — carrying their exact
        # attributes (incl. the UIP-only org_id). A string-presence test cannot show
        # this: it would pass even if the UIP loop were unreachable or sent the wrong
        # payload. Here an empty/incorrect capture fails the test.
        import shutil, subprocess, tempfile
        node = shutil.which("node")
        if not node:
            self.skipTest("node not on PATH")
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            capture = td / "o11y-sends.jsonl"
            nm = td / "node_modules" / "@salesforce"
            (nm / "telemetry").mkdir(parents=True)
            (nm / "core").mkdir(parents=True)
            # The o11yReporter records each PDP and each UIP send as a JSONL line
            # {kind, name, attributes}. sendTelemetryEvent is UIP; sendPdpEvent is PDP.
            # Both await-resolve (mirroring the real "in the collector" contract) so
            # the flusher's `await` actually gates on them. AppInsights is disabled
            # on this reporter (enableAppInsights:false), so no AI stub is needed.
            (nm / "telemetry" / "index.js").write_text(
                "const fs=require('fs');\n"
                f"const CAP={json.dumps(str(capture))};\n"
                "const rec=(o)=>fs.appendFileSync(CAP, JSON.stringify(o)+'\\n');\n"
                "class TelemetryReporter {\n"
                "  static async create(o){ return new TelemetryReporter(o); }\n"
                "  constructor(o){ this.options=o||{};\n"
                "    this.o11yReporter = {\n"
                "      sendPdpEvent: async (e) => rec({kind:'pdp', name:e.eventName}),\n"
                "      sendTelemetryEvent: async (name, attrs) => rec({kind:'a4d', name, attributes:attrs}),\n"
                "    };\n"
                "    this.reporter = null; }\n"
                "  async flush(){}\n  async stopAsync(){}\n  async stop(){}\n}\n"
                "module.exports = { TelemetryReporter };\n"
            )
            (nm / "telemetry" / "package.json").write_text('{"name":"@salesforce/telemetry","main":"index.js"}')
            (nm / "core" / "index.js").write_text(
                "class Org { static async create(){ return new Org(); }\n"
                "  async getConnection(){ return { instanceUrl: 'https://x.my.salesforce.com' }; } }\n"
                "module.exports = { Org };\n"
            )
            (nm / "core" / "package.json").write_text('{"name":"@salesforce/core","main":"index.js"}')
            a4d_attrs = {"componentId": "sf-context.status-org",
                         "contextName": "outcome::category",
                         "contextValue": "success::plugin_command",
                         "org_bucket": "scratch",
                         "org_id": "00Dxx0000000001EAA"}
            job = {
                "cliNodeModules": str(td / "node_modules"),
                "project": "salesforce-development",
                "username": "u@example",  # enables the O11y leg (UIP rides it)
                "events": [{"eventName": "session.started", "productFeatureId": "x"}],
                "a4dEvents": [{"eventName": "command.invoked", "attributes": a4d_attrs}],
                # No appInsightsKey/aiEvents: isolate the O11y leg so the capture is
                # unambiguously the UIP emission on the O11y reporter.
            }
            pending = td / "pending.json"
            pending.write_text(json.dumps(job))
            proc = subprocess.run([node, str(self.js), str(pending)], timeout=15,
                                  capture_output=True)
            self.assertEqual(proc.returncode, 0, proc.stderr.decode())
            self.assertFalse(pending.exists(), "pending file must be consumed")
            self.assertTrue(capture.exists(),
                            "the O11y reporter recorded no sends — UIP leg did not run")
            sends = [json.loads(ln) for ln in capture.read_text().splitlines() if ln.strip()]
            a4d = [s for s in sends if s["kind"] == "a4d"]
            pdp = [s for s in sends if s["kind"] == "pdp"]
            # PDP still delivered on the same reporter (UIP did not displace it)...
            self.assertEqual([s["name"] for s in pdp], ["session.started"])
            # ...and the UIP event was delivered via sendTelemetryEvent with its
            # exact name and attributes, including the UIP-only org_id.
            self.assertEqual(len(a4d), 1, "exactly one UIP event should be delivered")
            self.assertEqual(a4d[0]["name"], "command.invoked")
            self.assertEqual(a4d[0]["attributes"], a4d_attrs)
            self.assertEqual(a4d[0]["attributes"]["org_id"], "00Dxx0000000001EAA",
                             "UIP must carry the raw org_id through the O11y leg")


class ConsentLockMultiProcessTests(unittest.TestCase):
    """Reviewer follow-up: the lock must provide REAL mutual exclusion across
    processes, honor its timeout, and rely on the OS (not age-based stealing) to
    release a dead holder. These use spawned child processes so they can actually
    detect a lock that fails to exclude — a same-process synchronous test cannot.
    Skipped where no OS lock primitive (fcntl/msvcrt) is available."""

    def setUp(self):
        if not (_has_module("fcntl") or _has_module("msvcrt")):
            self.skipTest("no OS file-lock primitive (fcntl/msvcrt) available")
        self._ctx = mp.get_context("spawn")
        self._tmp = tempfile.TemporaryDirectory()
        self._home = str(Path(self._tmp.name) / "machine-state")
        os.makedirs(self._home, exist_ok=True)
        self._env = mock.patch.dict(os.environ,
                                    {"SF_DEV_TELEMETRY_HOME": self._home}, clear=False)
        self._env.start()

    def tearDown(self):
        self._env.stop()
        self._tmp.cleanup()

    def _drain(self, q, n, timeout=60):
        return [q.get(timeout=timeout) for _ in range(n)]

    def test_lock_provides_mutual_exclusion_across_processes(self):
        # N processes each do M lock-protected RMW increments on a shared counter.
        # If the lock truly excludes, the final count is exact (no lost updates); an
        # unlocked/broken lock loses updates under the widened critical section.
        n_proc, iters = 4, 25
        q = self._ctx.Queue()
        procs = [self._ctx.Process(target=_mp_incr_worker,
                                   args=(str(_MODULE_PATH), self._home, iters, q))
                 for _ in range(n_proc)]
        for p in procs:
            p.start()
        try:
            results = self._drain(q, n_proc)
        finally:
            for p in procs:
                p.join(30)
        self.assertTrue(all(tag == "ok" for tag, *_ in results),
                        f"a worker errored: {results}")
        counter = Path(self._home) / "counter.txt"
        self.assertEqual(int(counter.read_text()), n_proc * iters,
                         "the lock must serialize RMW across processes — no lost updates")

    def test_acquire_times_out_while_held_then_succeeds_after_release(self):
        # The parent HOLDS the lock; a child with a short timeout must fail to acquire
        # (returning False after ~the timeout, NOT stealing it), then succeed once the
        # parent releases. This is the fix for "acquisition failure proceeds unlocked":
        # a live holder is respected and the waiter observes a real False.
        q = self._ctx.Queue()
        holder = sft._ConsentLock(timeout=5.0)
        self.assertTrue(holder.__enter__(), "parent must acquire the lock first")
        try:
            p = self._ctx.Process(target=_mp_try_acquire_worker,
                                  args=(str(_MODULE_PATH), self._home, 0.5, q))
            p.start()
            p.join(30)
            tag, held, elapsed = q.get(timeout=10)
            self.assertEqual(tag, "ok", f"worker errored: {held}")
            self.assertFalse(held, "child must NOT acquire while the parent holds it")
            self.assertGreaterEqual(elapsed, 0.4,
                                    "child must have waited ~the full timeout, not stolen it")
        finally:
            holder.__exit__()
        # Parent released — a fresh child must now acquire.
        p2 = self._ctx.Process(target=_mp_try_acquire_worker,
                               args=(str(_MODULE_PATH), self._home, 5.0, q))
        p2.start()
        p2.join(30)
        tag, held, _elapsed = q.get(timeout=10)
        self.assertEqual(tag, "ok", f"worker errored: {held}")
        self.assertTrue(held, "child must acquire once the parent releases")

    def test_os_releases_lock_when_holder_dies_without_cleanup(self):
        # A child acquires the lock and dies via os._exit — no __exit__, no unlock. The
        # parent must then acquire promptly, proving the KERNEL released the dead
        # holder's lock. This is the safe replacement for age-based stealing (which
        # can't tell a slow-but-alive holder from a dead one).
        signal = Path(self._tmp.name) / "acquired.signal"
        child = self._ctx.Process(target=_mp_acquire_and_die_worker,
                                  args=(str(_MODULE_PATH), self._home, str(signal)))
        child.start()
        deadline = time.time() + 15
        while not signal.exists() and time.time() < deadline:
            time.sleep(0.02)
        self.assertTrue(signal.exists(), "child did not signal that it acquired the lock")
        self.assertEqual(signal.read_text(), "held",
                         "child must acquire the lock before dying")
        child.join(15)
        self.assertFalse(child.is_alive(), "child must have exited")
        got = sft._ConsentLock(timeout=5.0)
        acquired = got.__enter__()
        try:
            self.assertTrue(acquired,
                            "OS must release a dead holder's lock (no age-based stealing)")
        finally:
            got.__exit__()


def _has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


if __name__ == "__main__":
    unittest.main(verbosity=2)
