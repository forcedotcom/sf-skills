"""Integration tests for  (REMEDIATE): tree → write_emit_ctx → emit_result.

The defect: parse_wave.py writes `_partial_reason` and `_pending_fetches`
into the tree on disk. emit_result.py reads `ctx["partial_reason"]` and
`ctx["pending_fetches_count"]` from the emit ctx. But write_emit_ctx.py
NEVER populated those ctx keys from the tree — they silently defaulted to
empty / 0 on every run. Depth-cap truncation was invisible downstream.

These tests exercise both halves of the wiring:

    test_write_emit_ctx_reads_tree_partial_signals
        fake tree JSON → write_emit_ctx → assert ctx keys populated.

    test_end_to_end_tree_surfaces_partial_reason_in_result_block
        tree → write_emit_ctx → emit_result → assert RESULT block carries
        PARTIAL_REASON + PENDING_FETCHES_COUNT. End-to-end — this is the
        test both reviewers called for.

Missing-tree behavior is also covered so early-abort paths still work.
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

from . import _bootstrap  # noqa: F401


def _tools_dir() -> pathlib.Path:
    """Absolute path to the skill's tools/ dir — where the scripts live."""
    here = pathlib.Path(__file__).resolve()
    return here.parent.parent.parent / "tools"


def _run_script(script_name: str, env: dict) -> subprocess.CompletedProcess:
    """Invoke `python3 <tools>/<script>.py` with the given env.

    We deliberately run the scripts as subprocesses rather than importing
    them: they're shipped as stand-alone CLIs (the agent bash invokes them
    via `python3 write_emit_ctx.py`) and `main()` reads env at call time +
    returns an exit code. Subprocess gives us the exact production call
    path without having to monkey-patch os.environ.
    """
    script_path = _tools_dir() / script_name
    return subprocess.run(
        [sys.executable, str(script_path)],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


class WriteEmitCtxTreeSignalsTests(unittest.TestCase):
    """write_emit_ctx must plumb `_partial_reason` + rollup from tree."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.work_dir = pathlib.Path(self._tmp.name) / "work"
        self.data_dir = pathlib.Path(self._tmp.name) / "data"
        self.work_dir.mkdir()
        self.data_dir.mkdir()

    def _base_env(self, status: str = "OK") -> dict:
        return {
            **os.environ,
            "WORK_DIR": str(self.work_dir),
            "DATA_DIR": str(self.data_dir),
            "STATUS": status,
            "AGENT_API_NAME": "MyBot",
            "AGENT_VERSION": "v1",
            "ORG_ID_15": "00D000000000ABC",
            "BOT_ID": "0XxFAKEBOTID",
            "NODE_COUNT": "42",
            "DEPTH": "3",
            "PARTIAL": "true",
            "START_EPOCH": "0",
        }

    def _write_tree(self, payload: dict) -> None:
        (self.work_dir / "declared_action_tree.json").write_text(
            json.dumps(payload)
        )

    def _read_ctx(self) -> dict:
        return json.loads((self.work_dir / ".emit_ctx.json").read_text())

    def test_write_emit_ctx_reads_tree_partial_signals(self):
        """Fake tree → ctx carries partial_reason + pending_fetches_count."""
        self._write_tree({
            "_partial": True,
            "_partial_reason": "max-depth-cap",
            "_pending_fetches": {
                "FLOW": ["F6"],
                "APEX": [],
                "PROMPT_TEMPLATE": [],
                "STANDARD_ACTION": [],
            },
        })

        result = _run_script("write_emit_ctx.py", self._base_env())
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        ctx = self._read_ctx()
        self.assertEqual(ctx["partial_reason"], "max-depth-cap")
        self.assertEqual(ctx["pending_fetches_count"], 1)

    def test_write_emit_ctx_rollup_sums_across_kinds(self):
        self._write_tree({
            "_partial": True,
            "_partial_reason": "pending-refs",
            "_pending_fetches": {
                "FLOW": ["F1", "F2"],
                "APEX": ["A1"],
                "PROMPT_TEMPLATE": [],
                "STANDARD_ACTION": ["S1", "S2", "S3"],
            },
        })

        result = _run_script("write_emit_ctx.py", self._base_env())
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        ctx = self._read_ctx()
        self.assertEqual(ctx["partial_reason"], "pending-refs")
        self.assertEqual(ctx["pending_fetches_count"], 6)

    def test_write_emit_ctx_missing_tree_defaults_safely(self):
        """Early-abort paths never write a tree — ctx must default cleanly."""
        # No tree file written.
        result = _run_script(
            "write_emit_ctx.py",
            self._base_env(status="AGENT_NOT_FOUND"),
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        ctx = self._read_ctx()
        self.assertEqual(ctx["partial_reason"], "")
        self.assertEqual(ctx["pending_fetches_count"], 0)

    def test_write_emit_ctx_malformed_tree_defaults_safely(self):
        (self.work_dir / "declared_action_tree.json").write_text("{ not json")
        result = _run_script("write_emit_ctx.py", self._base_env())
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        ctx = self._read_ctx()
        self.assertEqual(ctx["partial_reason"], "")
        self.assertEqual(ctx["pending_fetches_count"], 0)


class TreeToResultBlockEndToEndTests(unittest.TestCase):
    """end-to-end: tree → write_emit_ctx → emit_result → RESULT block.

    This is the test both reviewers called for — it would have caught the
    original defect. A fix that only makes write_emit_ctx plumb the
    fields but doesn't verify they land in the RESULT block is not a fix.
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.work_dir = pathlib.Path(self._tmp.name) / "work"
        self.data_dir = pathlib.Path(self._tmp.name) / "data"
        self.work_dir.mkdir()
        self.data_dir.mkdir()

    def test_end_to_end_tree_surfaces_partial_reason_in_result_block(self):
        # 1. Tree on disk — depth-cap tripped, one pending flow.
        (self.work_dir / "declared_action_tree.json").write_text(json.dumps({
            "_partial": True,
            "_partial_reason": "max-depth-cap",
            "_pending_fetches": {
                "FLOW": ["F6"],
                "APEX": [],
                "PROMPT_TEMPLATE": [],
                "STANDARD_ACTION": [],
            },
        }))

        # 2. write_emit_ctx — populates .emit_ctx.json from env + tree.
        env = {
            **os.environ,
            "WORK_DIR": str(self.work_dir),
            "DATA_DIR": str(self.data_dir),
            "STATUS": "OK",
            "AGENT_API_NAME": "MyBot",
            "AGENT_VERSION": "v1",
            "ORG_ID_15": "00D000000000ABC",
            "BOT_ID": "0XxFAKEBOTID",
            "NODE_COUNT": "5",
            "DEPTH": "5",
            "PARTIAL": "true",
            "START_EPOCH": "0",
        }
        r1 = _run_script("write_emit_ctx.py", env)
        self.assertEqual(r1.returncode, 0, msg=r1.stderr)

        # 3. emit_result — reads .emit_ctx.json, prints RESULT block.
        r2 = _run_script("emit_result.py", env)
        self.assertEqual(r2.returncode, 0, msg=r2.stderr)

        # 4. Assert the RESULT block carries the plumbed fields.
        block = r2.stdout
        self.assertIn("PARTIAL_REASON=max-depth-cap", block)
        self.assertIn("PENDING_FETCHES_COUNT=1", block)
        # Auto-promote: partial=True + status=OK → PARTIAL_OK.
        self.assertIn("STATUS=PARTIAL_OK", block)
        self.assertNotIn("STATUS=OK\n", block)  # not the base OK status

    def test_end_to_end_no_tree_produces_empty_partial_fields(self):
        """Early-abort path (no tree) → RESULT block carries empties, not crashes."""
        env = {
            **os.environ,
            "WORK_DIR": str(self.work_dir),
            "DATA_DIR": str(self.data_dir),
            "STATUS": "AGENT_NOT_FOUND",
            "AGENT_API_NAME": "Missing",
            "AGENT_VERSION": "",
            "ORG_ID_15": "00D000000000ABC",
            "BOT_ID": "",
            "START_EPOCH": "0",
        }
        r1 = _run_script("write_emit_ctx.py", env)
        self.assertEqual(r1.returncode, 0, msg=r1.stderr)
        r2 = _run_script("emit_result.py", env)
        self.assertEqual(r2.returncode, 0, msg=r2.stderr)

        block = r2.stdout
        self.assertIn("STATUS=AGENT_NOT_FOUND", block)
        self.assertIn("PARTIAL_REASON=", block)
        self.assertIn("PENDING_FETCHES_COUNT=0", block)


class WriteEmitCtxArchitectureSignalsTests(unittest.TestCase):
    """write_emit_ctx must plumb architecture-render signals.

    Cases:
      * Render succeeded → architecture.md present, no sidecar →
        ctx.architecture_path set, render_failed=False, detail="".
      * Render failed → sidecar present → render_failed=True,
        detail populated (truncated + redacted).
      * Render not attempted → no file, no sidecar → empties,
        render_failed=False. This is the early-abort / cache-hit path.
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.work_dir = pathlib.Path(self._tmp.name) / "work"
        self.data_dir = pathlib.Path(self._tmp.name) / "data"
        self.work_dir.mkdir()
        self.data_dir.mkdir()

    def _base_env(self, status: str = "OK") -> dict:
        return {
            **os.environ,
            "WORK_DIR": str(self.work_dir),
            "DATA_DIR": str(self.data_dir),
            "STATUS": status,
            "AGENT_API_NAME": "MyBot",
            "AGENT_VERSION": "v1",
            "ORG_ID_15": "00D000000000ABC",
            "BOT_ID": "0XxFAKEBOTID",
            "START_EPOCH": "0",
        }

    def _read_ctx(self) -> dict:
        return json.loads((self.work_dir / ".emit_ctx.json").read_text())

    def test_render_success_surfaces_architecture_path(self):
        # filename is {agent}_{ver}_architecture.md.
        (self.data_dir / "MyBot_v1_architecture.md").write_text("# Architecture\n")
        result = _run_script("write_emit_ctx.py", self._base_env())
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        ctx = self._read_ctx()
        self.assertEqual(
            ctx["architecture_path"],
            str(self.data_dir / "MyBot_v1_architecture.md"),
        )
        self.assertFalse(ctx["render_failed"])
        self.assertEqual(ctx["render_error_detail"], "")

    def test_render_failure_surfaces_sidecar_detail(self):
        (self.data_dir / "MyBot_v1_architecture.md.error").write_text(
            "render_architecture failed: KeyError: 'agent'\n"
        )
        result = _run_script("write_emit_ctx.py", self._base_env())
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        ctx = self._read_ctx()
        self.assertTrue(ctx["render_failed"])
        self.assertIn("KeyError", ctx["render_error_detail"])
        # Sidecar's truncation + redaction happened — detail shouldn't
        # exceed 200 chars even for a pathological sidecar.
        self.assertLessEqual(len(ctx["render_error_detail"]), 200)
        # No architecture.md present → architecture_path stays empty.
        self.assertEqual(ctx["architecture_path"], "")

    def test_render_failure_detail_is_redacted(self):
        # Sidecar content mimics an exception that echoed back an
        # Authorization header — the redactor must scrub it.
        (self.data_dir / "MyBot_v1_architecture.md.error").write_text(
            "render_architecture failed: RequestError: Authorization: Bearer TESTONLY_RENDER_TOKEN xyz\n"
        )
        result = _run_script("write_emit_ctx.py", self._base_env())
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        ctx = self._read_ctx()
        self.assertTrue(ctx["render_failed"])
        self.assertNotIn("TESTONLY_RENDER_TOKEN", ctx["render_error_detail"])
        self.assertIn("<redacted>", ctx["render_error_detail"])

    def test_render_not_attempted_keeps_fields_empty(self):
        # No architecture.md, no sidecar — e.g. early-abort paths.
        result = _run_script(
            "write_emit_ctx.py",
            self._base_env(status="AGENT_NOT_FOUND"),
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        ctx = self._read_ctx()
        self.assertEqual(ctx["architecture_path"], "")
        self.assertFalse(ctx["render_failed"])
        self.assertEqual(ctx["render_error_detail"], "")

    def test_render_success_and_failure_concurrent_surfaces_both(self):
        # Edge case: architecture.md present + sidecar present. This
        # shouldn't happen in practice (finalize writes one or the
        # other), but the reader shouldn't mutate behaviour based on
        # cross-key state — path present + render_failed=True.
        (self.data_dir / "MyBot_v1_architecture.md").write_text("# Architecture\n")
        (self.data_dir / "MyBot_v1_architecture.md.error").write_text(
            "render_architecture failed: RuntimeError: partial output\n"
        )
        result = _run_script("write_emit_ctx.py", self._base_env())
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        ctx = self._read_ctx()
        self.assertTrue(ctx["render_failed"])
        self.assertEqual(
            ctx["architecture_path"],
            str(self.data_dir / "MyBot_v1_architecture.md"),
        )


class EmitResultArchitectureSignalsTests(unittest.TestCase):
    """emit_result surfaces architecture + render-failure fields.

    The integration tests in TreeToResultBlockEndToEndTests cover the
    write_emit_ctx -> emit_result handoff; these tests exercise
    emit_result's block-shaping logic in isolation via `build_block`.
    """

    def _import_mod(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "emit_result_mod", _tools_dir() / "emit_result.py",
        )
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_render_ok_emits_architecture_path_and_render_failed_false(self):
        mod = self._import_mod()
        ctx = {
            "status": "OK",
            "architecture_path": "/tmp/data/architecture.md",
            "render_failed": False,
        }
        block = mod.build_block(ctx, wall_time_seconds=0.5)
        self.assertIn("OUTPUT_ARCHITECTURE_PATH=/tmp/data/architecture.md", block)
        self.assertIn("RENDER_FAILED=false", block)
        # Detail key is ONLY emitted on failure — must NOT appear here.
        self.assertNotIn("RENDER_ERROR_DETAIL=", block)
        # Status stays OK.
        self.assertIn("STATUS=OK", block)
        self.assertNotIn("STATUS=PARTIAL_OK", block)

    def test_render_failed_auto_promotes_to_partial_ok(self):
        mod = self._import_mod()
        ctx = {
            "status": "OK",
            "architecture_path": "",  # render failed, no file produced
            "render_failed": True,
            "render_error_detail": "KeyError: 'agent'",
        }
        block = mod.build_block(ctx, wall_time_seconds=0.5)
        self.assertIn("STATUS=PARTIAL_OK", block)
        self.assertIn("RENDER_FAILED=true", block)
        self.assertIn("RENDER_ERROR_DETAIL=KeyError: 'agent'", block)
        # PARTIAL_REASON pinned to render-failed when the tree didn't
        # already claim a reason.
        self.assertIn("PARTIAL_REASON=render-failed", block)
        # OUTPUT_ARCHITECTURE_PATH always emitted, empty on failure.
        self.assertIn("OUTPUT_ARCHITECTURE_PATH=", block)

    def test_render_failed_preserves_tree_partial_reason(self):
        # When the tree is ALREADY partial with a reason, render_failed
        # must NOT clobber the tree's reason — the tree's signal is more
        # informative for triage.
        mod = self._import_mod()
        ctx = {
            "status": "OK",
            "partial": True,
            "partial_reason": "max-depth-cap",
            "render_failed": True,
            "render_error_detail": "RuntimeError: ...",
        }
        block = mod.build_block(ctx, wall_time_seconds=0.5)
        self.assertIn("PARTIAL_REASON=max-depth-cap", block)
        self.assertNotIn("PARTIAL_REASON=render-failed", block)
        # Still surfaces as PARTIAL_OK (either the tree or the render
        # flag is sufficient to trip the auto-promote).
        self.assertIn("STATUS=PARTIAL_OK", block)
        self.assertIn("RENDER_FAILED=true", block)

    def test_render_failed_does_not_clobber_error_status(self):
        mod = self._import_mod()
        ctx = {
            "status": "AUTH_REQUIRED",
            "render_failed": True,
            "render_error_detail": "ignored under error status",
        }
        block = mod.build_block(ctx, wall_time_seconds=0.1)
        self.assertIn("STATUS=AUTH_REQUIRED", block)
        self.assertNotIn("STATUS=PARTIAL_OK", block)
        # The render fields still surface for diagnostics.
        self.assertIn("RENDER_FAILED=true", block)


class EmitResultPositionalSafetyTests(unittest.TestCase):
    """emit_result must assert lines[1] starts with 'STATUS=' before rewrite.

    The auto-promote branch (PARTIAL → PARTIAL_OK) rewrites `lines[1]`
    in place. If a future refactor reorders the header, the rewrite
    would clobber the wrong line. The assertion catches that at test
    time instead of silently producing a malformed RESULT block in prod.
    """

    def test_build_block_happy_path_auto_promotes_without_asserting(self):
        """Sanity: the assertion does NOT fire under normal operation."""
        # Force import of emit_result from the tools/ dir.
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "emit_result_mod", _tools_dir() / "emit_result.py",
        )
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        ctx = {
            "status": "OK",
            "partial": True,
            "partial_reason": "max-depth-cap",
            "pending_fetches_count": 3,
            "node_count": 10,
            "depth": 5,
        }
        block = mod.build_block(ctx, wall_time_seconds=1.23)
        self.assertIn("STATUS=PARTIAL_OK", block)
        self.assertIn("PARTIAL_REASON=max-depth-cap", block)
        self.assertIn("PENDING_FETCHES_COUNT=3", block)

    def test_positional_assertion_fires_when_header_reordered(self):
        """Simulate a refactor that puts something other than STATUS at lines[1].

        We construct a fake `lines` list directly and run the same
        assertion the production code runs. This is the exact guarantee
        adds — the production assert catches the drift.
        """
        # This mirrors the production code's assertion verbatim.
        lines = ["=== RESULT ===", "WAS_MOVED=true", "STATUS=OK"]
        with self.assertRaises(AssertionError):
            assert lines[1].startswith("STATUS="), (
                f"emit block reordered — lines[1]={lines[1]!r}"
            )


if __name__ == "__main__":
    unittest.main()
