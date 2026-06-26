"""P2.3-3: end-to-end fixture integration tests.

Drives `main.main(argv)` against synthetic fixtures — no real org, no
sf CLI spawn, no HTTP. Every REST/sf boundary is mocked at the
`main.fetch_*` / `main.run_sf` / `main.probe_channels` surface; all
layers below (join, parse, render, finalize) run as production code.

Tests (one per pipeline path):
  1. classic_react_end_to_end       — STATUS=OK, tree + summary + architecture.md
  2. nga_orchestration_end_to_end   — NGA reverse-lookup + `par/and` state diagram
  3. cache_hit_end_to_end           — poisoned Wave A — must never be called
  4. probe_failed_end_to_end        — STATUS=RETRIEVE_FAILED + schema-drift detail
  5. force_refresh_end_to_end       — pre-populated fresh cache ignored
  6. render_failure_end_to_end      — STATUS=PARTIAL_OK + RENDER_FAILED=true

Each test carves its own tempdir for work/cache/data so no cross-test
state leaks. Assertions focus on the observable surface (RESULT block
+ on-disk artifacts) rather than on implementation details of
intermediate steps — the same tests survive a refactor of main.py's
internal phase ordering.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from . import _bootstrap  # noqa: F401

import config  # type: ignore
import soql_loader  # type: ignore
import main  # type: ignore
from tests.fixtures import genai_payloads as fx  # type: ignore

# SKILL_ROOT is now file-relative in config.py, so config.SOQL_DIR auto-
# resolves to the repo's assets/soql/ under test. soql_loader still
# captures SOQL_DIR via `from config import SOQL_DIR` at module top, so
# we mirror its binding here defensively.
_REPO_SOQL_DIR = Path(__file__).resolve().parent.parent.parent / "assets" / "soql"
soql_loader.SOQL_DIR = _REPO_SOQL_DIR

# emit_result.py lives under tools/; tests invoke it via subprocess so the
# tool's RESULT-formatting logic is exercised under the same contract the
# SKILL.md Bash wrapper uses.
_TOOLS_DIR = Path(__file__).resolve().parent.parent.parent / "tools"


# ---------------------------------------------------------------------------
# Shared helpers (mirrored from test_main_pipeline — intentionally copied
# rather than imported, so a refactor of that file doesn't silently change
# the end-to-end test behavior.)
# ---------------------------------------------------------------------------


def _args(work_dir: Path, **overrides) -> list[str]:
    base = [
        "--org-alias", "test-org",
        "--agent", overrides.pop("agent", "MyAgent"),
        "--work-dir", str(work_dir),
        "--parallelism", "2",
    ]
    for k, v in overrides.items():
        flag = "--" + k.replace("_", "-")
        if isinstance(v, bool):
            if v:
                base.append(flag)
        else:
            base.extend([flag, str(v)])
    return base


def _mock_auth_probe(probe_result=None):
    probe_result = probe_result or fx.probe_ok_payload()
    org_display_payload = {
        "status": 0,
        "result": {
            "instanceUrl": "https://example.my.salesforce.com",
            "accessToken": "00Dxx0000000000!AQ_fake_token_value",
            "id": "00Dxx0000000000AAA",
            "apiVersion": "60.0",
        },
    }
    return [
        mock.patch.object(main, "run_sf", return_value=org_display_payload),
        mock.patch.object(main, "probe_channels", return_value=probe_result),
    ]


def _mock_bot_resolution(agent_api_name="MyAgent", bot_def=None,
                         versions=("v5",), active="v5"):
    bot_def = bot_def or fx.BOT_DEFINITION_DETAIL_CLASSIC
    return [
        mock.patch.object(
            main, "fetch_bot_versions",
            return_value=fx.make_bot_versions(agent_api_name, versions, active),
        ),
        mock.patch.object(main, "fetch_bot_definition_details", return_value=bot_def),
    ]


def _mock_wave_a_classic():
    return [
        mock.patch.object(main, "fetch_planner_definition", return_value=fx.CLASSIC_PLANNER),
        mock.patch.object(main, "fetch_plugins_by_planner", return_value=fx.CLASSIC_PLUGINS),
        mock.patch.object(main, "fetch_planner_bundle_functions", return_value=fx.CLASSIC_BUNDLE_FN_JOIN),
        mock.patch.object(main, "fetch_functions_by_plugins", return_value=fx.CLASSIC_FUNCTIONS),
        mock.patch.object(main, "fetch_plugin_instructions", return_value=fx.CLASSIC_INSTRUCTIONS),
        mock.patch.object(main, "fetch_plugin_functions", return_value=fx.CLASSIC_PLUGIN_FUNCTIONS),
        mock.patch.object(main, "fetch_planner_attrs", return_value=fx.CLASSIC_ATTRS),
    ]


def _mock_wave_b_classic():
    return [
        mock.patch.object(main, "fetch_apex_bodies_by_names", return_value=fx.CLASSIC_APEX_ROWS),
        mock.patch.object(main, "fetch_apex_bodies_by_ids", return_value=[]),
        mock.patch.object(main, "fetch_flow_definition_ids_by_names", return_value=fx.CLASSIC_FLOW_DEFS),
        mock.patch.object(main, "fetch_flow_definition_by_ids", return_value=[]),
        mock.patch.object(
            main, "fetch_flow_metadata",
            side_effect=lambda vid, *a, **kw: fx.CLASSIC_FLOW_METADATA.get(vid),
        ),
    ]


def _mock_wave_a_nga():
    return [
        mock.patch.object(main, "fetch_planner_definition", return_value=fx.NGA_PLANNER),
        mock.patch.object(main, "fetch_plugins_by_planner", return_value=fx.NGA_PLUGINS),
        mock.patch.object(main, "fetch_planner_bundle_functions", return_value=[]),
        mock.patch.object(main, "fetch_functions_by_plugins", return_value=fx.NGA_FUNCTIONS),
        mock.patch.object(main, "fetch_plugin_instructions", return_value=[]),
        mock.patch.object(main, "fetch_plugin_functions", return_value=fx.NGA_PLUGIN_FUNCTIONS),
        mock.patch.object(main, "fetch_planner_attrs", return_value=[]),
    ]


def _mock_wave_b_nga():
    return [
        mock.patch.object(main, "fetch_apex_bodies_by_names", return_value=[]),
        mock.patch.object(main, "fetch_apex_bodies_by_ids", return_value=fx.NGA_APEX_BY_ID),
        mock.patch.object(main, "fetch_flow_definition_ids_by_names", return_value=[]),
        mock.patch.object(main, "fetch_flow_definition_by_ids", return_value=fx.NGA_FLOW_DEF_BY_ID),
        mock.patch.object(main, "fetch_flow_metadata", return_value={
            "Id": "301VF999NGAVER", "FullName": "NGAResolvedFlow-1", "Metadata": {},
        }),
    ]


def _apply(patches):
    for p in patches:
        p.start()


def _stop(patches):
    for p in patches:
        p.stop()


def _run_emit_result(work_dir: Path) -> subprocess.CompletedProcess:
    """Drive emit_result.py against the ctx main.py wrote.

    Exercises the same SKILL.md Bash-wrapper contract: main.py writes
    .emit_ctx.json, emit_result.py reads + renders. Subprocess call so
    the tool runs under a clean env (no leaked test-process state).
    """
    env = {**os.environ, "WORK_DIR": str(work_dir)}
    return subprocess.run(
        [sys.executable, str(_TOOLS_DIR / "emit_result.py")],
        env=env, capture_output=True, text=True, timeout=30,
    )


def _parse_result_block(stdout: str) -> dict:
    """Pull KV pairs out of the `=== RESULT ===` block."""
    lines = stdout.splitlines()
    out: dict[str, str] = {}
    in_block = False
    for line in lines:
        if line.strip() == "=== RESULT ===":
            in_block = True
            continue
        if in_block and "=" in line:
            k, _, v = line.partition("=")
            out[k] = v
    return out


# ---------------------------------------------------------------------------
# Test 1 — classic ReAct end-to-end
# ---------------------------------------------------------------------------


class ClassicReactEndToEndTests(unittest.TestCase):
    """P2.3-3: classic ReAct pipeline on MyAgent-v5-shaped fixtures.

    Asserts observable surface only: on-disk artifacts + RESULT block
    KV pairs. Internal phase ordering can change without breaking this
    test.
    """

    def test_classic_react_end_to_end_produces_full_artifact_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "work"
            data_root = Path(tmp) / "data"
            cache_root = Path(tmp) / "cache"

            patches = [
                *_mock_auth_probe(),
                *_mock_bot_resolution(),
                *_mock_wave_a_classic(),
                *_mock_wave_b_classic(),
                mock.patch.object(
                    main, "build_agent_data_dir",
                    side_effect=lambda o, a, v: data_root / o / f"{a}__{v}",
                ),
                mock.patch.object(
                    main, "build_agent_cache_dir",
                    side_effect=lambda o, a, v: cache_root / o / f"{a}__{v}",
                ),
            ]
            _apply(patches)
            try:
                rc = main.main(_args(work_dir))
            finally:
                _stop(patches)

            self.assertEqual(rc, 0)

            # --- on-disk artifacts ---
            data_dir = data_root / "00Dxx0000000000" / "MyAgent__v5"
            tree_file = data_dir / "MyAgent_v5_metadata_tree.json"
            arch_file = data_dir / "MyAgent_v5_architecture.md"

            self.assertTrue(tree_file.is_file(), "metadata_tree.json missing")
            self.assertTrue(arch_file.is_file(), "architecture.md missing")
            # summary.md dropped from the output contract —
            # confirm it is NOT written.
            self.assertFalse(
                (data_dir / "MyAgent_v5_metadata_tree.summary.md").exists(),
                "summary.md should have been dropped from the output contract",
            )
            # rendered architecture filename embeds the agent
            # api name (new convention — proves the rename is wired).
            self.assertTrue(
                arch_file.name.startswith("MyAgent"),
                f"architecture filename should start with agent api name, got {arch_file.name}",
            )

            tree = json.loads(tree_file.read_text())
            self.assertGreater(tree.get("node_count", 0), 0)
            self.assertEqual(tree["agent"]["generation"], "classic")

            # --- emit_result RESULT block ---
            r = _run_emit_result(work_dir)
            self.assertEqual(r.returncode, 0, msg=r.stderr)
            block = _parse_result_block(r.stdout)
            self.assertIn(block["STATUS"], ("OK", "PARTIAL_OK"))
            self.assertEqual(block["OUTPUT_ARCHITECTURE_PATH"], str(arch_file))
            self.assertEqual(block["RENDER_FAILED"], "false")
            self.assertGreater(int(block["NODE_COUNT"]), 0)


# ---------------------------------------------------------------------------
# Test 2 — NGA end-to-end
# ---------------------------------------------------------------------------


class NgaEndToEndTests(unittest.TestCase):
    """P2.3-3: NGA ConcurrentMultiAgentOrchestration end-to-end.

    Exercises the NGA reverse-lookup path (InvocationTarget is a 15/18-
    char Id, not a DeveloperName) and verifies the architecture.md
    carries NGA-specific state-diagram content (`par/and dispatch`).
    """

    def test_nga_end_to_end_produces_par_state_diagram(self):
        with tempfile.TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "work"
            data_root = Path(tmp) / "data"
            cache_root = Path(tmp) / "cache"

            patches = [
                *_mock_auth_probe(),
                *_mock_bot_resolution(
                    agent_api_name="MyAgent2",
                    bot_def=fx.BOT_DEFINITION_DETAIL_NGA,
                ),
                *_mock_wave_a_nga(),
                *_mock_wave_b_nga(),
                mock.patch.object(
                    main, "build_agent_data_dir",
                    side_effect=lambda o, a, v: data_root / o / f"{a}__{v}",
                ),
                mock.patch.object(
                    main, "build_agent_cache_dir",
                    side_effect=lambda o, a, v: cache_root / o / f"{a}__{v}",
                ),
            ]
            _apply(patches)
            try:
                rc = main.main(_args(work_dir, agent="MyAgent2"))
            finally:
                _stop(patches)

            self.assertEqual(rc, 0)

            data_dir = data_root / "00Dxx0000000000" / "MyAgent2__v5"
            tree_file = data_dir / "MyAgent2_v5_metadata_tree.json"
            arch_file = data_dir / "MyAgent2_v5_architecture.md"

            self.assertTrue(tree_file.is_file())
            self.assertTrue(arch_file.is_file())

            tree = json.loads(tree_file.read_text())
            self.assertEqual(tree["agent"]["generation"], "nga")
            # NGA reverse-lookup worked — the tree built a TOPIC node for
            # NGATopic1 with 2 GEN_AI_FUNCTION children (Flow + Apex).
            counts = tree["_kind_counts"]
            self.assertEqual(counts.get("TOPIC"), 1)
            self.assertEqual(counts.get("GEN_AI_FUNCTION"), 2)

            # Architecture.md renders — surface the NGA tell via the
            # Data flow / Topic anatomy sections. The Planner state
            # machine section (which previously carried `par/and
            # dispatch`) was retired from the default pipeline in
            # 2026-05; the NGA-specific state-diagram output is now
            # exercised directly in RenderNgaTests.
            arch_text = arch_file.read_text()
            self.assertIn("NGATopic1", arch_text)
            self.assertIn("NGAFlowAction", arch_text)
            self.assertIn("NGAApexAction", arch_text)
            # Retired section must not appear.
            self.assertNotIn("Planner state machine", arch_text)

            r = _run_emit_result(work_dir)
            block = _parse_result_block(r.stdout)
            self.assertIn(block["STATUS"], ("OK", "PARTIAL_OK"))
            self.assertEqual(block["AGENT_GENERATION"], "nga")


# ---------------------------------------------------------------------------
# Test 3 — cache hit end-to-end
# ---------------------------------------------------------------------------


class CacheHitEndToEndTests(unittest.TestCase):
    """P2.3-3: pre-populated fresh cache short-circuits the pipeline.

    Wave A + Wave B fetchers are poisoned with AssertionError — the
    test fails loudly if main.py attempts any fetch on a cache hit.
    """

    def test_cache_hit_end_to_end_skips_all_wave_calls(self):
        import datetime as dt

        with tempfile.TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "work"
            data_root = Path(tmp) / "data"
            cache_root = Path(tmp) / "cache"
            data_dir = data_root / "00Dxx0000000000" / "MyAgent__v5"
            cache_dir = cache_root / "00Dxx0000000000" / "MyAgent__v5"
            data_dir.mkdir(parents=True)
            cache_dir.mkdir(parents=True)

            tree_base = "MyAgent_v5_metadata_tree"
            # Minimal tree + architecture.md so the cache-hit emit ctx
            # surfaces an OUTPUT_ARCHITECTURE_PATH.
            # architecture filename is self-identifying.
            (data_dir / f"{tree_base}.json").write_text(json.dumps({
                "_schema_version": "3.0",
                "agent": {"generation": "classic"},
                "root": {"children": []},
                "node_count": 12, "depth": 3,
                "_kind_counts": {}, "_unresolved": [],
            }))
            (data_dir / "MyAgent_v5_architecture.md").write_text("# cached arch\n")

            from config import SCHEMA_VERSION
            manifest = {
                "built_at_utc": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
                "schema_version": SCHEMA_VERSION,
                "agent": {
                    "version": "v5", "bot_id": "0Xa000000000ABC",
                    "generation": "classic", "_version_auto_picked": True,
                },
                "node_count": 12, "depth": 3, "kind_counts": {},
                "ttl_days": 7,
                "data_path": str(data_dir / f"{tree_base}.json"),
                "partial": False, "unresolved_count": 0,
            }
            (cache_dir / "manifest.json").write_text(json.dumps(manifest))

            def _poison(*_a, **_kw):
                raise AssertionError("cache hit MUST NOT invoke any Wave fetcher")

            poisoned_fetchers = [
                mock.patch.object(main, name, side_effect=_poison)
                for name in (
                    "fetch_planner_definition",
                    "fetch_plugins_by_planner",
                    "fetch_planner_bundle_functions",
                    "fetch_functions_by_plugins",
                    "fetch_plugin_instructions",
                    "fetch_plugin_functions",
                    "fetch_planner_attrs",
                    "fetch_apex_bodies_by_names",
                    "fetch_apex_bodies_by_ids",
                    "fetch_flow_definition_ids_by_names",
                    "fetch_flow_definition_by_ids",
                    "fetch_flow_metadata",
                )
            ]

            patches = [
                *_mock_auth_probe(),
                *_mock_bot_resolution(),
                *poisoned_fetchers,
                mock.patch.object(
                    main, "build_agent_data_dir",
                    side_effect=lambda o, a, v: data_dir,
                ),
                mock.patch.object(
                    main, "build_agent_cache_dir",
                    side_effect=lambda o, a, v: cache_dir,
                ),
            ]
            _apply(patches)
            try:
                rc = main.main(_args(work_dir))
            finally:
                _stop(patches)

            self.assertEqual(rc, 0)

            r = _run_emit_result(work_dir)
            block = _parse_result_block(r.stdout)
            self.assertEqual(block["STATUS"], "OK")
            self.assertEqual(block["CACHE_HIT"], "true")
            self.assertEqual(int(block["NODE_COUNT"]), 12)
            # Cached architecture.md surfaces as the OUTPUT path.
            # filename embeds agent api name + version.
            self.assertTrue(block["OUTPUT_ARCHITECTURE_PATH"].endswith("MyAgent_v5_architecture.md"))
            self.assertEqual(block["RENDER_FAILED"], "false")


# ---------------------------------------------------------------------------
# Test 4 — probe-failed end-to-end
# ---------------------------------------------------------------------------


class ProbeFailedEndToEndTests(unittest.TestCase):
    """P2.3-3: channel probe returns PROBE_FAILED -> RETRIEVE_FAILED.

    Verifies Batch 2.1 remediation: schema-drift manifests as
    STATUS=RETRIEVE_FAILED with ERROR_DETAIL containing `schema-drift`
    rather than a fabricated SCHEMA_DRIFT enum value. The emit_result
    STATUS enum doesn't include SCHEMA_DRIFT, so mapping to
    RETRIEVE_FAILED preserves the existing contract while surfacing
    the cause in ERROR_DETAIL.
    """

    def test_probe_failed_end_to_end_emits_retrieve_failed(self):
        with tempfile.TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "work"

            patches = _mock_auth_probe(
                probe_result=fx.probe_failed_payload(
                    sobject="GenAiPlannerDefinition",
                    missing=["PlannerType", "DeveloperName"],
                ),
            )
            _apply(patches)
            try:
                rc = main.main(_args(work_dir))
            finally:
                _stop(patches)

            # Pipeline returns nonzero on terminal failure — matches the
            # SKILL.md Bash wrapper's set +e / capture _rc / exit _rc
            # contract.
            self.assertEqual(rc, 1)

            r = _run_emit_result(work_dir)
            self.assertEqual(r.returncode, 0, msg=r.stderr)
            block = _parse_result_block(r.stdout)
            self.assertEqual(block["STATUS"], "RETRIEVE_FAILED")
            self.assertIn("schema-drift", block["ERROR_DETAIL"])
            # The specific missing fields surface in the detail string
            # (first 3 only per main.py's truncation).
            self.assertIn("PlannerType", block["ERROR_DETAIL"])


# ---------------------------------------------------------------------------
# Test 5 — --force end-to-end
# ---------------------------------------------------------------------------


class ForceRefreshEndToEndTests(unittest.TestCase):
    """P2.3-3: fresh cache + --force -> full pipeline runs, cache supersedes.

    Asserts:
      * Wave A fetcher was invoked exactly once (cache was NOT used).
      * CACHE_HIT=false in the RESULT block.
      * Post-run manifest differs from pre-run manifest (node_count
        reflects the live-fetched tree, not the 999-node placeholder).
    """

    def test_force_refresh_bypasses_fresh_cache(self):
        import datetime as dt

        with tempfile.TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "work"
            data_root = Path(tmp) / "data"
            cache_root = Path(tmp) / "cache"
            data_dir = data_root / "00Dxx0000000000" / "MyAgent__v5"
            cache_dir = cache_root / "00Dxx0000000000" / "MyAgent__v5"
            data_dir.mkdir(parents=True)
            cache_dir.mkdir(parents=True)
            (data_dir / "MyAgent_v5_metadata_tree.json").write_text("{}")

            from config import SCHEMA_VERSION
            stale_manifest = {
                "built_at_utc": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
                "schema_version": SCHEMA_VERSION,
                "agent": {"version": "v5"},
                # Bogus node count to detect whether the cache path or
                # the live-fetched tree won.
                "node_count": 999, "depth": 99, "kind_counts": {},
                "ttl_days": 7,
                "data_path": str(data_dir / "MyAgent_v5_metadata_tree.json"),
                "partial": False, "unresolved_count": 0,
            }
            (cache_dir / "manifest.json").write_text(json.dumps(stale_manifest))

            patches = [
                *_mock_auth_probe(),
                *_mock_bot_resolution(),
                *_mock_wave_a_classic(),
                *_mock_wave_b_classic(),
                mock.patch.object(
                    main, "build_agent_data_dir",
                    side_effect=lambda o, a, v: data_dir,
                ),
                mock.patch.object(
                    main, "build_agent_cache_dir",
                    side_effect=lambda o, a, v: cache_dir,
                ),
            ]
            _apply(patches)
            try:
                rc = main.main(_args(work_dir, force=True))
                planner_calls = main.fetch_planner_definition.call_count
            finally:
                _stop(patches)

            self.assertEqual(rc, 0)
            # Wave A actually fired — cache was NOT consulted.
            self.assertEqual(planner_calls, 1)

            # Manifest on disk post-run reflects the live fetch, not the
            # 999-node placeholder.
            post_manifest = json.loads((cache_dir / "manifest.json").read_text())
            self.assertNotEqual(post_manifest.get("node_count"), 999)
            self.assertGreater(post_manifest.get("node_count", 0), 0)

            r = _run_emit_result(work_dir)
            block = _parse_result_block(r.stdout)
            self.assertIn(block["STATUS"], ("OK", "PARTIAL_OK"))
            self.assertEqual(block["CACHE_HIT"], "false")


# ---------------------------------------------------------------------------
# Test 6 — render failure end-to-end
# ---------------------------------------------------------------------------


class RenderFailureEndToEndTests(unittest.TestCase):
    """P2.3-3: renderer raises -> tree OK, architecture.md.error sidecar,
    STATUS=PARTIAL_OK, RENDER_FAILED=true in RESULT block.

    contract. The pipeline does NOT abort on render failure —
    the tree JSON is the authoritative output; architecture.md is
    derived. This test asserts the signalling: downstream consumers can
    distinguish "headline diagram missing" from "pipeline succeeded
    cleanly" via RENDER_FAILED + the sidecar.
    """

    def test_render_failure_end_to_end_surfaces_partial_ok(self):
        import render_architecture  # type: ignore

        with tempfile.TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "work"
            data_root = Path(tmp) / "data"
            cache_root = Path(tmp) / "cache"

            def _boom(*_a, **_kw):
                raise RuntimeError("render exploded for end-to-end test")

            patches = [
                *_mock_auth_probe(),
                *_mock_bot_resolution(),
                *_mock_wave_a_classic(),
                *_mock_wave_b_classic(),
                mock.patch.object(
                    main, "build_agent_data_dir",
                    side_effect=lambda o, a, v: data_root / o / f"{a}__{v}",
                ),
                mock.patch.object(
                    main, "build_agent_cache_dir",
                    side_effect=lambda o, a, v: cache_root / o / f"{a}__{v}",
                ),
                mock.patch.object(render_architecture, "render", side_effect=_boom),
            ]
            _apply(patches)
            try:
                rc = main.main(_args(work_dir))
            finally:
                _stop(patches)

            self.assertEqual(rc, 0)

            data_dir = data_root / "00Dxx0000000000" / "MyAgent__v5"
            # Sidecar landed, architecture.md did NOT.
            # filenames are self-identifying.
            self.assertTrue((data_dir / "MyAgent_v5_architecture.md.error").is_file())
            self.assertFalse((data_dir / "MyAgent_v5_architecture.md").is_file())
            # Tree JSON DID land — the render failure is isolated to the
            # derived artifact.
            self.assertTrue(
                (data_dir / "MyAgent_v5_metadata_tree.json").is_file()
            )

            r = _run_emit_result(work_dir)
            block = _parse_result_block(r.stdout)
            # emit_result auto-promotes OK -> PARTIAL_OK on render failure
            # (see build_block .2-R1).
            self.assertEqual(block["STATUS"], "PARTIAL_OK")
            self.assertEqual(block["RENDER_FAILED"], "true")
            self.assertEqual(block["OUTPUT_ARCHITECTURE_PATH"], "")
            self.assertIn("RENDER_ERROR_DETAIL", block)
            self.assertTrue(block["RENDER_ERROR_DETAIL"])  # non-empty


if __name__ == "__main__":
    unittest.main()
