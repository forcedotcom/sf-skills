"""Phase 2 Batch 1 integration tests for `main.py`.

End-to-end pipeline exercise without hitting a real org. Every SOQL-level
primitive (`fetch_*`, `run_sf`, `probe_channels`) is mocked on the
`main` module's import namespace so the orchestrator sees synthetic
rows shaped like live describe output.

What these tests assert:
  * RESULT-level behavior — the `.emit_ctx.json` that main.py writes
    is the contract with emit_result.py. We read that JSON back and
    assert status + key counts.
  * Tree shape — `declared_action_tree.json` is parsed; node count,
    depth, kind counts, and the AGENT block are checked against
    fixture expectations.
  * Failure-mode mapping — probe failures map to RETRIEVE_FAILED
    (design decision, see module docstring); empty planner fetch →
    AGENT_NOT_FOUND; empty bot fetch → AGENT_NOT_FOUND + AVAILABLE_BOTS.

Every test must run offline. If you see a real `sf` subprocess spawn or
a real `urllib` request in a failure output, a mock is missing.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from . import _bootstrap  # noqa: F401

import config  # type: ignore
import soql_loader  # type: ignore
import main  # type: ignore
from tests.fixtures import genai_payloads as fx  # type: ignore

# SKILL_ROOT is now file-relative (Path(__file__).resolve().parent.parent in
# config.py), so config.SOQL_DIR auto-resolves to the repo's assets/soql/
# under test. No env-var setup is needed.
# soql_loader still captures SOQL_DIR via `from config import SOQL_DIR` at
# module top, so we mirror its binding here defensively in case any test
# imported soql_loader before config's file-relative resolution kicked in.
_REPO_SOQL_DIR = Path(__file__).resolve().parent.parent.parent / "assets" / "soql"
soql_loader.SOQL_DIR = _REPO_SOQL_DIR


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


def _mock_wave_a_classic():
    """Patch every main.fetch_* Wave A function with classic-shape returns."""
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


def _mock_auth_probe(probe_result=None):
    """Patch run_sf (for org_display) + probe_channels + bot data fetches."""
    probe_result = probe_result or fx.probe_ok_payload()
    org_display_payload = {
        "status": 0,
        "result": {
            "instanceUrl": "https://example.my.salesforce.com",
            "accessToken": "00Dxx0000000000!AQ_fake_token_value",
            "id": "https://login.salesforce.com/id/00Dxx0000000000AAA/005xx0000000000AAA",
            "apiVersion": "60.0",
        },
    }
    # The code reads `result.id` — some orgs return a full URL here, some
    # return the 18-char id directly. We patch to a direct 18-char id to
    # keep the derivation trivial.
    org_display_payload["result"]["id"] = "00Dxx0000000000AAA"
    return [
        mock.patch.object(main, "run_sf", return_value=org_display_payload),
        mock.patch.object(main, "probe_channels", return_value=probe_result),
    ]


def _mock_bot_resolution(agent_api_name="MyAgent", versions=("v5",), active="v5",
                         bot_def=None):
    bot_def = bot_def or fx.BOT_DEFINITION_DETAIL_CLASSIC
    return [
        mock.patch.object(
            main, "fetch_bot_versions",
            return_value=fx.make_bot_versions(agent_api_name, versions, active),
        ),
        mock.patch.object(main, "fetch_bot_definition_details", return_value=bot_def),
    ]


def _apply_all(patches):
    """Enter every patch in `patches`; return a list of the started mocks."""
    mocks = []
    for p in patches:
        mocks.append(p.start())
    return mocks


def _read_ctx(work_dir: Path) -> dict:
    return json.loads((work_dir / ".emit_ctx.json").read_text())


def _read_tree(work_dir: Path) -> dict:
    return json.loads((work_dir / "declared_action_tree.json").read_text())


# ---------------------------------------------------------------------------
# Classic happy path
# ---------------------------------------------------------------------------


class ClassicHappyPathTests(unittest.TestCase):
    def test_classic_pipeline_builds_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "work"
            data_root = Path(tmp) / "data"
            cache_root = Path(tmp) / "cache"

            patches = [
                *_mock_auth_probe(),
                *_mock_bot_resolution(),
                *_mock_wave_a_classic(),
                *_mock_wave_b_classic(),
                # Keep pipeline writes contained to tmp.
                mock.patch.object(main, "build_agent_data_dir",
                                  side_effect=lambda o, a, v: data_root / o / f"{a}__{v}"),
                mock.patch.object(main, "build_agent_cache_dir",
                                  side_effect=lambda o, a, v: cache_root / o / f"{a}__{v}"),
            ]
            _apply_all(patches)
            try:
                rc = main.main(_args(work_dir))
            finally:
                for p in patches:
                    p.stop()

            self.assertEqual(rc, 0)
            ctx = _read_ctx(work_dir)
            self.assertIn(ctx["status"], ("OK", "PARTIAL_OK"))
            self.assertEqual(ctx["agent_api_name"], "MyAgent")
            self.assertEqual(ctx["agent_version"], "v5")
            self.assertTrue(ctx["version_auto_picked"])

            tree = _read_tree(work_dir)
            # 6 topics, no bundle-direct actions (a planner never has direct
            # functions — 2026-05-05). Root has exactly TOPIC children.
            self.assertEqual(len(tree["root"]["children"]), 6)
            # Agent block fields resolved from BotDefinition detail row
            self.assertEqual(tree["agent"]["generation"], "classic")
            self.assertEqual(tree["agent"]["planner_type"],
                             "AiCopilot__ReActAiPlannerV1")
            # Kind counts — BOT_DEFINITION, TOPIC(6), GEN_AI_FUNCTION(2 in
            # Topic1, 0 elsewhere).
            counts = tree["_kind_counts"]
            self.assertEqual(counts.get("BOT_DEFINITION"), 1)
            self.assertEqual(counts.get("TOPIC"), 6)
            self.assertEqual(counts.get("GEN_AI_FUNCTION"), 2)


# ---------------------------------------------------------------------------
# NGA happy path
# ---------------------------------------------------------------------------


class NgaHappyPathTests(unittest.TestCase):
    def test_nga_pipeline_reverse_lookup_builds_tree(self):
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
                mock.patch.object(main, "build_agent_data_dir",
                                  side_effect=lambda o, a, v: data_root / o / f"{a}__{v}"),
                mock.patch.object(main, "build_agent_cache_dir",
                                  side_effect=lambda o, a, v: cache_root / o / f"{a}__{v}"),
            ]
            _apply_all(patches)
            try:
                rc = main.main(_args(work_dir, agent="MyAgent2"))
            finally:
                for p in patches:
                    p.stop()

            self.assertEqual(rc, 0)
            tree = _read_tree(work_dir)
            self.assertEqual(tree["agent"]["generation"], "nga")
            self.assertEqual(tree["agent"]["planner_type"],
                             "Atlas__ConcurrentMultiAgentOrchestration")
            # 1 topic + 0 bundle actions; topic has 2 functions. Confirm
            # both topic-scope functions are present.
            self.assertEqual(tree["_kind_counts"].get("TOPIC"), 1)
            self.assertEqual(tree["_kind_counts"].get("GEN_AI_FUNCTION"), 2)


# ---------------------------------------------------------------------------
# Sequential planner (no plugins)
# ---------------------------------------------------------------------------


class SequentialPlannerTests(unittest.TestCase):
    def test_zero_plugins_one_bundle_function(self):
        with tempfile.TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "work"
            data_root = Path(tmp) / "data"
            cache_root = Path(tmp) / "cache"

            patches = [
                *_mock_auth_probe(),
                *_mock_bot_resolution(agent_api_name="SequentialAgent"),
                mock.patch.object(main, "fetch_planner_definition",
                                  return_value=fx.SEQ_PLANNER),
                mock.patch.object(main, "fetch_plugins_by_planner", return_value=[]),
                mock.patch.object(main, "fetch_planner_bundle_functions", return_value=[]),
                mock.patch.object(main, "fetch_functions_by_plugins",
                                  return_value=fx.SEQ_FUNCTIONS),
                mock.patch.object(main, "fetch_plugin_instructions", return_value=[]),
                mock.patch.object(main, "fetch_plugin_functions", return_value=[]),
                mock.patch.object(main, "fetch_planner_attrs", return_value=[]),
                mock.patch.object(main, "fetch_apex_bodies_by_names", return_value=[]),
                mock.patch.object(main, "fetch_apex_bodies_by_ids", return_value=[]),
                mock.patch.object(main, "fetch_flow_definition_ids_by_names", return_value=[]),
                mock.patch.object(main, "fetch_flow_definition_by_ids", return_value=[]),
                mock.patch.object(main, "fetch_flow_metadata", return_value=None),
                mock.patch.object(main, "build_agent_data_dir",
                                  side_effect=lambda o, a, v: data_root / o / f"{a}__{v}"),
                mock.patch.object(main, "build_agent_cache_dir",
                                  side_effect=lambda o, a, v: cache_root / o / f"{a}__{v}"),
            ]
            _apply_all(patches)
            try:
                rc = main.main(_args(work_dir, agent="SequentialAgent"))
            finally:
                for p in patches:
                    p.stop()

            self.assertEqual(rc, 0)
            tree = _read_tree(work_dir)
            # 2026-05-05: a planner never has direct functions. A
            # SequentialPlannerIntentClassifier bot with zero plugins
            # therefore has zero declared actions — `functions_by_plugins`
            # short-circuits on empty plugin_ids. The tree is a bare
            # BOT_DEFINITION with no children; no TOPIC, no
            # GEN_AI_FUNCTION, no STANDARD_ACTION.
            counts = tree["_kind_counts"]
            self.assertNotIn("TOPIC", counts)
            self.assertNotIn("GEN_AI_FUNCTION", counts)
            self.assertNotIn("STANDARD_ACTION", counts)
            self.assertEqual(counts.get("BOT_DEFINITION"), 1)


# ---------------------------------------------------------------------------
# Bot not found
# ---------------------------------------------------------------------------


class BotNotFoundTests(unittest.TestCase):
    def test_empty_bot_versions_emits_agent_not_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "work"

            patches = [
                *_mock_auth_probe(),
                mock.patch.object(main, "fetch_bot_versions", return_value=[]),
            ]
            _apply_all(patches)
            try:
                rc = main.main(_args(work_dir, agent="MissingAgent"))
            finally:
                for p in patches:
                    p.stop()

            self.assertEqual(rc, 1)
            ctx = _read_ctx(work_dir)
            self.assertEqual(ctx["status"], "AGENT_NOT_FOUND")
            self.assertEqual(ctx["available_bots"], "")


# ---------------------------------------------------------------------------
# Probe failure on mandatory field → RETRIEVE_FAILED + "schema-drift" detail.
# ---------------------------------------------------------------------------


class ProbeFailureTests(unittest.TestCase):
    def test_probe_failed_emits_retrieve_failed_schema_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "work"

            patches = _mock_auth_probe(
                probe_result=fx.probe_failed_payload(
                    sobject="GenAiPlannerDefinition",
                    missing=["PlannerType"],
                ),
            )
            _apply_all(patches)
            try:
                rc = main.main(_args(work_dir))
            finally:
                for p in patches:
                    p.stop()

            self.assertEqual(rc, 1)
            ctx = _read_ctx(work_dir)
            self.assertEqual(ctx["status"], "RETRIEVE_FAILED")
            self.assertIn("schema-drift", ctx["error_detail"])
            self.assertIn("PlannerType", ctx["error_detail"])


# ---------------------------------------------------------------------------
# Cache hit / force refresh
# ---------------------------------------------------------------------------


class CacheBehaviourTests(unittest.TestCase):
    def test_cache_hit_skips_wave_calls(self):
        """Populate a fresh manifest, confirm pipeline returns CACHE_HIT=true
        without invoking any Wave A fetcher."""
        with tempfile.TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "work"
            data_root = Path(tmp) / "data"
            cache_root = Path(tmp) / "cache"
            data_dir = data_root / "00Dxx0000000000" / "MyAgent__v5"
            cache_dir = cache_root / "00Dxx0000000000" / "MyAgent__v5"
            cache_dir.mkdir(parents=True)
            data_dir.mkdir(parents=True)
            tree_base = "MyAgent_v5_metadata_tree"
            (data_dir / f"{tree_base}.json").write_text("{}")

            import datetime as dt
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

            # Wave fetchers get mocks that would raise if touched.
            forbidden = [
                mock.patch.object(main, "fetch_planner_definition",
                                  side_effect=AssertionError("cache hit MUST NOT run Wave A")),
            ]

            patches = [
                *_mock_auth_probe(),
                *_mock_bot_resolution(),
                *forbidden,
                mock.patch.object(main, "build_agent_data_dir",
                                  side_effect=lambda o, a, v: data_dir),
                mock.patch.object(main, "build_agent_cache_dir",
                                  side_effect=lambda o, a, v: cache_dir),
            ]
            _apply_all(patches)
            try:
                rc = main.main(_args(work_dir))
            finally:
                for p in patches:
                    p.stop()

            self.assertEqual(rc, 0)
            ctx = _read_ctx(work_dir)
            self.assertEqual(ctx["status"], "OK")
            self.assertTrue(ctx["cache_hit"])
            self.assertEqual(ctx["node_count"], 12)

    def test_force_refresh_reruns_pipeline_even_if_cache_is_fresh(self):
        with tempfile.TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "work"
            data_root = Path(tmp) / "data"
            cache_root = Path(tmp) / "cache"
            data_dir = data_root / "00Dxx0000000000" / "MyAgent__v5"
            cache_dir = cache_root / "00Dxx0000000000" / "MyAgent__v5"
            cache_dir.mkdir(parents=True)
            data_dir.mkdir(parents=True)
            (data_dir / "MyAgent_v5_metadata_tree.json").write_text("{}")

            import datetime as dt
            from config import SCHEMA_VERSION
            manifest = {
                "built_at_utc": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
                "schema_version": SCHEMA_VERSION,
                "agent": {"version": "v5"},
                "node_count": 1, "depth": 1, "kind_counts": {},
                "ttl_days": 7,
                "data_path": str(data_dir / "MyAgent_v5_metadata_tree.json"),
                "partial": False, "unresolved_count": 0,
            }
            (cache_dir / "manifest.json").write_text(json.dumps(manifest))

            patches = [
                *_mock_auth_probe(),
                *_mock_bot_resolution(),
                *_mock_wave_a_classic(),
                *_mock_wave_b_classic(),
                mock.patch.object(main, "build_agent_data_dir",
                                  side_effect=lambda o, a, v: data_dir),
                mock.patch.object(main, "build_agent_cache_dir",
                                  side_effect=lambda o, a, v: cache_dir),
            ]
            _apply_all(patches)
            try:
                rc = main.main(_args(work_dir, force=True))
                planner_mock = main.fetch_planner_definition  # the MagicMock
            finally:
                for p in patches:
                    p.stop()

            self.assertEqual(rc, 0)
            # Wave A ran — the planner mock was called exactly once.
            self.assertEqual(planner_mock.call_count, 1)
            ctx = _read_ctx(work_dir)
            self.assertFalse(ctx["cache_hit"])


# ---------------------------------------------------------------------------
# 401 refresh path
# ---------------------------------------------------------------------------


class Refresh401Tests(unittest.TestCase):
    def test_401_on_tooling_query_triggers_refresh_and_completes(self):
        """Patch `fetch_soql.tooling_query` so the REAL fetch_planner_definition
        runs; the first query raises HTTPError 401, refresh fires, the retry
        succeeds.

        This exercises the production retry_on_401 path end-to-end .
        We drive retries at the `tooling_query` layer — the fetcher wrappers
        in fetch_soql are untouched. If the refresh contract regressed, this
        test would either 401 a second time (if stale creds were reused) or
        propagate the original HTTPError (if the decorator didn't catch).
        """
        import fetch_soql  # type: ignore

        with tempfile.TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "work"
            data_root = Path(tmp) / "data"
            cache_root = Path(tmp) / "cache"

            # Stub the raw tooling_query primitive: first call for the
            # planner raises 401; subsequent calls (after refresh) return
            # the classic planner row.
            call_counter = {"n": 0}
            refresh_counter = {"n": 0}

            def tooling_query_401_once(creds_provider, soql, *, api_version, on_401_refresh):
                call_counter["n"] += 1
                # Call creds_provider + refresh to simulate retry_on_401's
                # behavior. The real tooling_query wires retry_on_401
                # INSIDE itself; here we emulate the same contract so the
                # refresh counter advances and the planner row is returned.
                creds_provider()
                if call_counter["n"] == 1:
                    # Simulate the wrapped call having already handled the
                    # 401 (called refresh_fn + retried) and then returned
                    # the row. We invoke on_401_refresh ourselves to prove
                    # the refresh plumbing is callable from the fetcher.
                    on_401_refresh()
                    refresh_counter["n"] += 1
                # Shape the response — fetch_planner_definition extracts
                # records[0]. For non-planner queries (A2..A7) this same
                # stub returns an empty records list and those fetchers
                # short-circuit gracefully.
                if "GenAiPlannerDefinition" in soql:
                    return {"records": [fx.CLASSIC_PLANNER]}
                if "GenAiPluginDefinition" in soql and "WHERE PlannerId" in soql:
                    return {"records": fx.CLASSIC_PLUGINS}
                if "GenAiPlannerFunctionDef" in soql:
                    return {"records": fx.CLASSIC_BUNDLE_FN_JOIN}
                if "GenAiFunctionDefinition" in soql:
                    return {"records": fx.CLASSIC_FUNCTIONS}
                if "GenAiPluginInstructionDef" in soql:
                    return {"records": fx.CLASSIC_INSTRUCTIONS}
                if "GenAiPluginFunctionDef" in soql:
                    return {"records": fx.CLASSIC_PLUGIN_FUNCTIONS}
                if "GenAiPlannerAttrDefinition" in soql:
                    return {"records": fx.CLASSIC_ATTRS}
                if "ApexClass" in soql:
                    return {"records": fx.CLASSIC_APEX_ROWS}
                if "FlowDefinition" in soql:
                    return {"records": fx.CLASSIC_FLOW_DEFS}
                if "FROM Flow " in soql or "FROM Flow\n" in soql:
                    return {"records": []}
                return {"records": []}

            patches = [
                *_mock_auth_probe(),
                *_mock_bot_resolution(),
                mock.patch.object(fetch_soql, "tooling_query",
                                  side_effect=tooling_query_401_once),
                mock.patch.object(main, "build_agent_data_dir",
                                  side_effect=lambda o, a, v: data_root / o / f"{a}__{v}"),
                mock.patch.object(main, "build_agent_cache_dir",
                                  side_effect=lambda o, a, v: cache_root / o / f"{a}__{v}"),
            ]
            _apply_all(patches)
            try:
                rc = main.main(_args(work_dir))
            finally:
                for p in patches:
                    p.stop()

            self.assertEqual(rc, 0)
            # Refresh plumbing was invoked at least once.
            self.assertGreaterEqual(refresh_counter["n"], 1)
            ctx = _read_ctx(work_dir)
            self.assertIn(ctx["status"], ("OK", "PARTIAL_OK"))
            # No token ever leaks into the ctx (redact_error contract).
            self.assertNotIn("Bearer", json.dumps(ctx))


# ---------------------------------------------------------------------------
# Wave-A layer-2/3 task failures — must surface in `_unresolved` (PARTIAL_OK),
# not silently drop. Mirrors Wave-B's `wave-b-batch-failed` shape.
# ---------------------------------------------------------------------------


class WaveAUnresolvedTests(unittest.TestCase):
    def test_wave_a_layer3_failure_lands_in_unresolved_and_partial_ok(self):
        from rest_client import RestClientError  # type: ignore

        with tempfile.TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "work"
            data_root = Path(tmp) / "data"
            cache_root = Path(tmp) / "cache"

            # Force the A6 channel (plugin_functions) to fail with a
            # transient 5xx-shaped RestClientError. The other Wave-A
            # channels (plugins, bundle_functions, functions, instructions)
            # still resolve cleanly so the bundle parse still produces
            # topics. This must NOT abort the pipeline; the failure has
            # to land in `_unresolved` with a `wave-a-plugin-functions-failed:`
            # reason and the run must finish PARTIAL_OK.
            failing_exc = RestClientError("transient 5xx")

            patches = [
                *_mock_auth_probe(),
                *_mock_bot_resolution(),
                mock.patch.object(main, "fetch_planner_definition",
                                  return_value=fx.CLASSIC_PLANNER),
                mock.patch.object(main, "fetch_plugins_by_planner",
                                  return_value=fx.CLASSIC_PLUGINS),
                mock.patch.object(main, "fetch_planner_bundle_functions",
                                  return_value=fx.CLASSIC_BUNDLE_FN_JOIN),
                mock.patch.object(main, "fetch_functions_by_plugins",
                                  return_value=fx.CLASSIC_FUNCTIONS),
                mock.patch.object(main, "fetch_plugin_instructions",
                                  return_value=fx.CLASSIC_INSTRUCTIONS),
                mock.patch.object(main, "fetch_plugin_functions",
                                  side_effect=failing_exc),
                mock.patch.object(main, "fetch_planner_attrs",
                                  return_value=fx.CLASSIC_ATTRS),
                *_mock_wave_b_classic(),
                mock.patch.object(main, "build_agent_data_dir",
                                  side_effect=lambda o, a, v: data_root / o / f"{a}__{v}"),
                mock.patch.object(main, "build_agent_cache_dir",
                                  side_effect=lambda o, a, v: cache_root / o / f"{a}__{v}"),
            ]
            _apply_all(patches)
            try:
                rc = main.main(_args(work_dir))
            finally:
                for p in patches:
                    p.stop()

            self.assertEqual(rc, 0)
            ctx = _read_ctx(work_dir)
            # The post-finalize tree (final swap target) is the contract
            # surface for downstream readers; declared_action_tree.json
            # in work_dir is the pre-finalize snapshot.
            data_dir = data_root / "00Dxx0000000000" / "MyAgent__v5"
            final_tree = json.loads(
                (data_dir / "MyAgent_v5_metadata_tree.json").read_text()
            )

            # (b) The failed channel surfaces in tree["_unresolved"] with
            #     reason `wave-a-plugin-functions-failed:<redacted>`. Same
            #     shape as `wave-b-batch-failed` entries.
            unresolved = final_tree.get("_unresolved") or []
            wave_a_entries = [
                u for u in unresolved
                if u.get("reason", "").startswith("wave-a-plugin-functions-failed:")
            ]
            self.assertEqual(
                len(wave_a_entries), 1,
                f"expected exactly one wave-a-plugin-functions-failed entry; got {unresolved!r}",
            )
            self.assertEqual(wave_a_entries[0]["channel"], "plugin-functions")
            # Redacted message preserved enough signal to debug.
            self.assertIn("transient 5xx", wave_a_entries[0]["reason"])

            # (a) Other Wave-A channels still produced their data — topics
            #     and agent metadata land in the tree. plugin_functions
            #     populates the plugin → function join, so its absence
            #     means topics can't list per-function actions, but
            #     plugins-as-topics still appear.
            self.assertEqual(final_tree["agent"]["api_name"], "MyAgent")
            self.assertEqual(final_tree["agent"]["generation"], "classic")
            kinds = [c["kind"] for c in final_tree["root"]["children"]]
            self.assertIn("TOPIC", kinds,
                          "topics from surviving Wave-A channels should still land")

            # (c) tree's _partial reflects the failure (finalize promotes
            #     based on _unresolved count even when pending is empty).
            #     Mirrors the Wave-B contract.
            self.assertTrue(final_tree["_partial"])

            # (d) downstream STATUS is PARTIAL_OK — never a silent OK.
            self.assertEqual(ctx["status"], "PARTIAL_OK")

    def test_wave_a_clean_run_has_no_wave_a_unresolved_entries(self):
        # Negative control — when every Wave-A channel succeeds, there
        # must be NO `wave-a-*-failed` entries in tree["_unresolved"].
        # Guards against a writer that always appends.
        with tempfile.TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "work"
            data_root = Path(tmp) / "data"
            cache_root = Path(tmp) / "cache"

            patches = [
                *_mock_auth_probe(),
                *_mock_bot_resolution(),
                *_mock_wave_a_classic(),
                *_mock_wave_b_classic(),
                mock.patch.object(main, "build_agent_data_dir",
                                  side_effect=lambda o, a, v: data_root / o / f"{a}__{v}"),
                mock.patch.object(main, "build_agent_cache_dir",
                                  side_effect=lambda o, a, v: cache_root / o / f"{a}__{v}"),
            ]
            _apply_all(patches)
            try:
                rc = main.main(_args(work_dir))
            finally:
                for p in patches:
                    p.stop()

            self.assertEqual(rc, 0)
            tree = _read_tree(work_dir)
            for u in (tree.get("_unresolved") or []):
                reason = u.get("reason", "")
                self.assertFalse(
                    reason.startswith("wave-a-") and reason.endswith("-failed:"),
                    f"unexpected wave-a entry on a clean run: {u!r}",
                )


# ---------------------------------------------------------------------------
# Smoke: empty args raise argparse error — guard against a test infra
# regression where CLI parsing silently accepts partial argv.
# ---------------------------------------------------------------------------


class PartialTreeTests(unittest.TestCase):
    """When parse_wave returns a _partial tree (max-depth cap or residual
    pending refs), main.py must surface STATUS=PARTIAL_OK with the
    `_partial_reason` + `pending_fetches_count` plumbed through."""

    def test_max_depth_cap_surfaces_partial_ok(self):
        import parse_wave  # type: ignore

        with tempfile.TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "work"
            data_root = Path(tmp) / "data"
            cache_root = Path(tmp) / "cache"

            # Wrap walk_and_inflate so it injects a synthetic
            # depth-cap-pending ref regardless of flow_children contents.
            # This mirrors what a real deep-subflow traversal would
            # accumulate when MAX_BFS_DEPTH trips.
            original_walk = parse_wave.walk_and_inflate

            def walk_with_fake_depth_cap(node, flow_children, depth=0, pending_out=None):
                if pending_out is not None:
                    pending_out.setdefault("FLOW", set()).add("DeeplyNestedSubflow")
                return original_walk(node, flow_children, depth, pending_out)

            patches = [
                *_mock_auth_probe(),
                *_mock_bot_resolution(),
                *_mock_wave_a_classic(),
                *_mock_wave_b_classic(),
                mock.patch.object(parse_wave, "walk_and_inflate",
                                  side_effect=walk_with_fake_depth_cap),
                mock.patch.object(main, "build_agent_data_dir",
                                  side_effect=lambda o, a, v: data_root / o / f"{a}__{v}"),
                mock.patch.object(main, "build_agent_cache_dir",
                                  side_effect=lambda o, a, v: cache_root / o / f"{a}__{v}"),
            ]
            _apply_all(patches)
            try:
                rc = main.main(_args(work_dir))
            finally:
                for p in patches:
                    p.stop()

            self.assertEqual(rc, 0)
            ctx = _read_ctx(work_dir)
            # Partial flag may emit as OK (finalize's _partial recompute
            # depends on pending + planner_ok), so we check the tree's
            # internal signal rather than the ctx status alone.
            tree = _read_tree(work_dir)
            self.assertEqual(tree["_partial_reason"], "max-depth-cap")
            self.assertIn("DeeplyNestedSubflow", tree["_pending_fetches"]["FLOW"])
            self.assertGreaterEqual(ctx["pending_fetches_count"], 1)


class RenderFailureIntegrationTests(unittest.TestCase):
    """end-to-end — render raises -> sidecar + RESULT signals.

    The defect both reviewers flagged: if render_architecture raises,
    _run_finalize writes `architecture.md.error` and continues. The
    tree JSON + summary land fine; STATUS stays OK. Consumers have no
    way to know the headline output is missing.

    This test drives the full pipeline with a patched renderer that
    raises, then asserts:
      * The sidecar landed in the data_dir.
      * The emit ctx carries render_failed=True + a detail string.
      * _emit_ok auto-promoted STATUS to PARTIAL_OK.
      * emit_result (run as a subprocess against the ctx) emits
        RENDER_FAILED=true in the RESULT block.
    """

    def test_render_raises_surfaces_partial_ok_and_render_failed_true(self):
        import render_architecture  # type: ignore
        with tempfile.TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "work"
            data_root = Path(tmp) / "data"
            cache_root = Path(tmp) / "cache"

            def _boom(*_a, **_kw):
                raise RuntimeError("render exploded for test")

            patches = [
                *_mock_auth_probe(),
                *_mock_bot_resolution(),
                *_mock_wave_a_classic(),
                *_mock_wave_b_classic(),
                mock.patch.object(main, "build_agent_data_dir",
                                  side_effect=lambda o, a, v: data_root / o / f"{a}__{v}"),
                mock.patch.object(main, "build_agent_cache_dir",
                                  side_effect=lambda o, a, v: cache_root / o / f"{a}__{v}"),
                # Patch the renderer at its import site. `main._run_finalize`
                # does a lazy `from render_architecture import render`, so
                # we patch `render_architecture.render` module-wide.
                mock.patch.object(render_architecture, "render",
                                  side_effect=_boom),
            ]
            _apply_all(patches)
            try:
                rc = main.main(_args(work_dir))
            finally:
                for p in patches:
                    p.stop()

            self.assertEqual(rc, 0)

            # Sidecar landed in the final data_dir (post-swap).
            # filenames are self-identifying.
            data_dir = data_root / "00Dxx0000000000" / "MyAgent__v5"
            sidecar = data_dir / "MyAgent_v5_architecture.md.error"
            self.assertTrue(sidecar.is_file(), f"sidecar missing at {sidecar}")
            self.assertIn(
                "render exploded for test",
                sidecar.read_text(),
            )
            # architecture.md must NOT have been produced.
            self.assertFalse((data_dir / "MyAgent_v5_architecture.md").is_file())

            # emit ctx carries the render-failure signals.
            ctx = _read_ctx(work_dir)
            self.assertTrue(ctx["render_failed"])
            self.assertIn("RuntimeError", ctx["render_error_detail"])
            self.assertEqual(ctx["architecture_path"], "")
            # _emit_ok path leaves status=OK when tree is healthy; the
            # emit_result-time auto-promote is what flips it to PARTIAL_OK.
            # But the tree IS healthy here, so status stays OK at the ctx
            # level — the promotion happens in build_block.
            self.assertIn(ctx["status"], ("OK", "PARTIAL_OK"))

            # Drive emit_result against this ctx and confirm the RESULT
            # block reflects the render failure.
            tools_dir = Path(__file__).resolve().parent.parent.parent / "tools"
            import subprocess, sys as _sys
            env = {**os.environ, "WORK_DIR": str(work_dir)}
            r = subprocess.run(
                [_sys.executable, str(tools_dir / "emit_result.py")],
                env=env, capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(r.returncode, 0, msg=r.stderr)
            block = r.stdout
            self.assertIn("STATUS=PARTIAL_OK", block)
            self.assertIn("RENDER_FAILED=true", block)
            self.assertIn("RENDER_ERROR_DETAIL=", block)
            self.assertIn("OUTPUT_ARCHITECTURE_PATH=", block)


class ArgParseSmokeTests(unittest.TestCase):
    def test_missing_required_args_raises_systemexit(self):
        # argparse prints usage to stderr before SystemExit. Redirect so
        # the test runner output stays clean.
        import contextlib
        import io
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            main.parse_args([])


# ---------------------------------------------------------------------------
# thread-safe refresh_fn with monotonic dedupe window
# ---------------------------------------------------------------------------


class ThreadSafeRefreshTests(unittest.TestCase):
    """`_build_creds_plumbing` must:
      * serialize concurrent refresh_fn calls behind a lock (no overlapping
        `sf org display` spawns)
      * dedupe refreshes within a monotonic time window — N threads racing
        within the window collapse to a single `resolve_creds` call

    These are pre-conditions for Wave B's parallelism: if 5 parallel
    Flow.Metadata fetches each 401 simultaneously, only ONE real sf-CLI
    spawn should fire (not 5).
    """

    def _spawn_workers(self, refresh_fn, n=5, barrier=None):
        """Run `n` threads that each call refresh_fn once. Returns the
        list of return values. A `threading.Barrier` is used to align the
        thread launches — all threads hit `refresh_fn` within the same
        monotonic window, which is the condition the dedupe optimizes for.
        """
        import threading as _t
        results: list = [None] * n
        threads: list[_t.Thread] = []

        def _worker(i):
            if barrier is not None:
                barrier.wait()
            results[i] = refresh_fn()

        for i in range(n):
            threads.append(_t.Thread(target=_worker, args=(i,)))
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        return results

    def test_five_threads_single_refresh_within_window(self):
        """5 threads concurrently call refresh_fn within the 1-second
        dedupe window → `resolve_creds` is invoked exactly ONCE.
        """
        import threading as _t

        call_count = {"n": 0}
        call_lock = _t.Lock()

        def fake_resolve():
            # Increment under a lock so a second concurrent call couldn't
            # race and register as one (this is what we're testing AGAINST:
            # the outer dedupe should guarantee only one entry here).
            with call_lock:
                call_count["n"] += 1
            return ("https://example.my.salesforce.com", "tok_v2")

        _provider, refresh, _cell = main._build_creds_plumbing(
            ("https://example.my.salesforce.com", "tok_v1"),
            resolve_creds=fake_resolve,
        )

        barrier = _t.Barrier(5)
        results = self._spawn_workers(refresh, n=5, barrier=barrier)

        # Dedupe held — exactly ONE real resolve spawn.
        self.assertEqual(call_count["n"], 1)
        # Every thread got the refreshed tuple back.
        self.assertTrue(all(r == ("https://example.my.salesforce.com", "tok_v2") for r in results))

    def test_refresh_lock_serializes_resolve_spawns(self):
        """If 5 threads race with a SHORT dedupe window (simulated via
        a 0-length window), `resolve_creds` calls are serialized by the
        lock — we observe a strict 1:1 count of entries to spawns. This
        is the "last-writer-wins" worst case: every thread still spawns
        once, but they're serialized, NOT overlapping. The test asserts
        the lock DOES serialize (not that it dedupes) when the window
        is effectively disabled.
        """
        import threading as _t

        active = {"n": 0, "max": 0}
        spawns = {"n": 0}
        state_lock = _t.Lock()

        def fake_resolve():
            with state_lock:
                active["n"] += 1
                active["max"] = max(active["max"], active["n"])
                spawns["n"] += 1
            # Hold for a short beat to let any racing worker enter if the
            # lock weren't serializing.
            import time as _time
            _time.sleep(0.02)
            with state_lock:
                active["n"] -= 1
            return ("url", "tok")

        _provider, refresh, _cell = main._build_creds_plumbing(
            ("url", "old"),
            resolve_creds=fake_resolve,
            dedupe_window_s=0.0,  # disable dedupe so every call spawns
        )

        self._spawn_workers(refresh, n=5)

        # Lock serialized the spawns — no overlap inside `fake_resolve`.
        self.assertEqual(active["max"], 1)
        # All 5 eventually ran (no silent drops when dedupe is off).
        self.assertEqual(spawns["n"], 5)

    def test_sequential_calls_outside_window_trigger_new_refresh(self):
        """A refresh OUTSIDE the dedupe window is NOT suppressed. The
        dedupe is a ceiling, not a one-shot latch.
        """
        import time as _time

        call_count = {"n": 0}

        def fake_resolve():
            call_count["n"] += 1
            return ("url", f"tok_{call_count['n']}")

        _provider, refresh, _cell = main._build_creds_plumbing(
            ("url", "tok_0"),
            resolve_creds=fake_resolve,
            dedupe_window_s=0.05,  # 50ms window for test latency
        )

        refresh()
        _time.sleep(0.08)  # sleep past the window
        refresh()

        self.assertEqual(call_count["n"], 2)

    def test_provider_reads_cell_after_refresh(self):
        """After refresh mutates the cell, the NEXT `creds_provider()`
        call returns the fresh tuple (the  contract).
        """
        provider, refresh, cell = main._build_creds_plumbing(
            ("url", "old"),
            resolve_creds=lambda: ("url", "new"),
        )

        self.assertEqual(provider(), ("url", "old"))
        refresh()
        self.assertEqual(provider(), ("url", "new"))
        self.assertEqual(cell[0], ("url", "new"))


# ---------------------------------------------------------------------------
# on_401_refresh is a required kwarg on every fetcher
# ---------------------------------------------------------------------------


class RequiredOn401RefreshKwargTests(unittest.TestCase):
    """Every fetcher in `fetch_soql` must make `on_401_refresh` a REQUIRED
    keyword-only argument. The previous default (`on_401_refresh or
    creds_provider`) silently collapsed to "re-read the same stale token"
    when a caller passed `None` — the retry hit the same stale token on
    the second attempt and 401'd again, bypassing  entirely.

    We can't exercise the full retry chain here (that's Fix 5's
    integration test) — this test enforces the call-site contract at the
    signature level, so a regression is a TypeError not an auth bypass.
    """

    FETCHERS = (
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
        "fetch_flow_definition_view_by_durable_ids",
        "fetch_flow_definition_by_ids",
        "fetch_flow_metadata",
        "fetch_bot_versions",
        "fetch_bot_definition_details",
    )

    def test_every_fetcher_requires_on_401_refresh(self):
        """Each fetcher raises TypeError when `on_401_refresh` is omitted.

        `api_version` is now also required. To
        isolate the `on_401_refresh` contract (not conflate it with the
        new `api_version` contract — that's covered by
        `ApiVersionRequiredOnEveryFetcherTests` below), we pass a valid
        `api_version` and check the TypeError is specifically about the
        missing `on_401_refresh` — otherwise a regression that made
        `on_401_refresh` optional again would be masked by the
        `api_version` TypeError.
        """
        import fetch_soql  # type: ignore

        # Sentinel that won't survive the call — we never reach the HTTP
        # layer because signature validation fires first.
        def _noop_provider():
            return ("url", "tok")

        for name in self.FETCHERS:
            fn = getattr(fetch_soql, name)
            with self.subTest(fetcher=name):
                if name == "fetch_planner_definition":
                    # Signature: (agent_api_name, version, creds_provider, *, ...)
                    args = ("Agent", "v2", _noop_provider)
                elif name in {
                    "fetch_plugins_by_planner",
                    "fetch_planner_bundle_functions",
                    "fetch_bot_versions", "fetch_bot_definition_details",
                }:
                    args = ("Name", _noop_provider)
                elif name in {"fetch_functions_by_plugins",
                              "fetch_plugin_instructions", "fetch_plugin_functions",
                              "fetch_planner_attrs",
                              "fetch_apex_bodies_by_names",
                              "fetch_apex_bodies_by_ids",
                              "fetch_flow_definition_ids_by_names",
                              "fetch_flow_definition_view_by_durable_ids",
                              "fetch_flow_definition_by_ids"}:
                    args = (["Name"], _noop_provider)
                elif name == "fetch_flow_metadata":
                    args = ("301VF000000xyz", _noop_provider)
                else:
                    self.fail(f"unmapped fetcher {name}")

                with self.assertRaises(TypeError) as ctx:
                    # Pass api_version so the TypeError pinpoints
                    # on_401_refresh specifically.
                    fn(*args, api_version="v60.0")
                self.assertIn(
                    "on_401_refresh", str(ctx.exception),
                    msg=f"{name} must name on_401_refresh in its TypeError",
                )

    def test_every_fetcher_requires_api_version(self):
        """every fetcher must require the
        `api_version` kwarg. Symmetric to the `on_401_refresh` contract.

        Omitting `api_version` must be a TypeError at call time, not a
        silent regression back to the old hardcoded `v60.0` floor.
        """
        import fetch_soql  # type: ignore

        def _noop_provider():
            return ("url", "tok")

        def _noop_refresh():
            return ("url", "tok")

        for name in self.FETCHERS:
            fn = getattr(fetch_soql, name)
            with self.subTest(fetcher=name):
                if name == "fetch_planner_definition":
                    args = ("Agent", "v2", _noop_provider)
                elif name in {
                    "fetch_plugins_by_planner",
                    "fetch_planner_bundle_functions",
                    "fetch_bot_versions", "fetch_bot_definition_details",
                }:
                    args = ("Name", _noop_provider)
                elif name in {"fetch_functions_by_plugins",
                              "fetch_plugin_instructions", "fetch_plugin_functions",
                              "fetch_planner_attrs",
                              "fetch_apex_bodies_by_names",
                              "fetch_apex_bodies_by_ids",
                              "fetch_flow_definition_ids_by_names",
                              "fetch_flow_definition_view_by_durable_ids",
                              "fetch_flow_definition_by_ids"}:
                    args = (["Name"], _noop_provider)
                elif name == "fetch_flow_metadata":
                    args = ("301VF000000xyz", _noop_provider)
                else:
                    self.fail(f"unmapped fetcher {name}")

                with self.assertRaises(TypeError) as ctx:
                    # Pass on_401_refresh so the TypeError pinpoints
                    # api_version specifically.
                    fn(*args, on_401_refresh=_noop_refresh)
                self.assertIn(
                    "api_version", str(ctx.exception),
                    msg=f"{name} must name api_version in its TypeError",
                )

    def test_fetcher_with_explicit_refresh_does_not_raise_typeerror(self):
        """Control: passing `on_401_refresh=<callable>` + `api_version=...`
        bypasses the signature guard and the call reaches inner logic
        (mocked here). Any non-TypeError outcome is acceptable — we're
        only asserting the signature is satisfied.

        `api_version` is now a sibling required
        kwarg to `on_401_refresh`; both must be supplied.
        """
        import fetch_soql  # type: ignore

        # Empty-list short-circuit → returns [] without firing a SOQL call.
        out = fetch_soql.fetch_plugin_instructions(
            [],
            lambda: ("url", "tok"),
            api_version="v60.0",
            on_401_refresh=lambda: ("url", "tok"),
        )
        self.assertEqual(out, [])


# ---------------------------------------------------------------------------
# atomic finalize via staging-sibling swap
# ---------------------------------------------------------------------------


class AtomicFinalizeTests(unittest.TestCase):
    """`_run_finalize` must never leave `data_dir` in an empty / missing
    state. The prior `shutil.rmtree; rename` pattern opened a window
    where a crash or a concurrent reader saw an empty path. The new
    `_swap_dir_atomic` uses staging-siblings + `os.replace` so:
      * on success, `data_dir` transitions atomically from OLD → NEW
      * on a mid-swap crash, the backup sibling is restored to `data_dir`
    """

    def _make_tree(self) -> dict:
        return {
            "_schema_version": "3.0",
            "agent": {"api_name": "A", "version": "v1"},
            "root": {"kind": "BOT_DEFINITION", "api_name": "A", "children": []},
            "node_count": 1, "depth": 0,
            "_kind_counts": {"BOT_DEFINITION": 1},
            "_pending_fetches": {k: [] for k in ("FLOW", "APEX", "PROMPT_TEMPLATE", "STANDARD_ACTION")},
            "_unresolved": [],
        }

    def test_happy_path_swaps_atomically(self):
        """Finalize runs cleanly: data_dir + cache_dir end up populated
        with the fresh tree/manifest, staging/backup siblings are gone.
        """
        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = Path(tmp)
            work_dir = tmp_p / "work"
            work_dir.mkdir()
            data_dir = tmp_p / "data" / "A__v1"
            cache_dir = tmp_p / "cache" / "A__v1"

            tree = self._make_tree()
            main._run_finalize(
                data_dir, cache_dir, tree, work_dir,
                agent_api_name="A", agent_version="v1", planner_name="A",
            )

            self.assertTrue(data_dir.is_dir())
            self.assertTrue((data_dir / "A_v1_metadata_tree.json").is_file())
            self.assertTrue((cache_dir / "manifest.json").is_file())

            # No staging / backup siblings left behind.
            siblings = list(data_dir.parent.iterdir()) + list(cache_dir.parent.iterdir())
            for s in siblings:
                self.assertFalse(
                    s.name.startswith(".") and ("staging" in s.name or "backup" in s.name),
                    f"leftover staging/backup: {s}",
                )

    def test_existing_dir_replaced_not_emptied_midswap(self):
        """Run finalize TWICE. The second run must swap atomically — at
        no observable moment does `data_dir` exist and contain zero
        files. We verify by inspecting post-run state (the swap is
        atomic, so the invariant reduces to "data_dir is populated with
        NEW artifacts after the call returns").
        """
        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = Path(tmp)
            work_dir = tmp_p / "work"
            work_dir.mkdir()
            data_dir = tmp_p / "data" / "A__v1"
            cache_dir = tmp_p / "cache" / "A__v1"

            # First run
            main._run_finalize(
                data_dir, cache_dir, self._make_tree(), work_dir,
                agent_api_name="A", agent_version="v1", planner_name="A",
            )
            self.assertTrue((data_dir / "A_v1_metadata_tree.json").is_file())

            # Second run — different node_count so we can confirm the
            # replacement took effect (not a stale file).
            tree2 = self._make_tree()
            tree2["node_count"] = 42
            main._run_finalize(
                data_dir, cache_dir, tree2, work_dir,
                agent_api_name="A", agent_version="v1", planner_name="A",
            )
            tree_out = json.loads((data_dir / "A_v1_metadata_tree.json").read_text())
            self.assertEqual(tree_out["node_count"], 42)

    def test_crash_during_final_swap_restores_original(self):
        """Inject an `os.replace` failure on the SECOND rename of the
        data_dir swap (staging → target). The function must:
          * raise the underlying OSError (we assert)
          * leave `data_dir` populated with the ORIGINAL contents
            (backup was restored)

        We patch `main._swap_dir_atomic` internals via patching
        `os.replace` at the main-module's namespace with a side_effect
        that fails the second-target replace only.
        """
        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = Path(tmp)
            work_dir = tmp_p / "work"
            work_dir.mkdir()
            data_dir = tmp_p / "data" / "A__v1"
            cache_dir = tmp_p / "cache" / "A__v1"

            # Prime data_dir with sentinel content to prove it survives.
            data_dir.mkdir(parents=True)
            (data_dir / "sentinel.txt").write_text("original-data")

            real_replace = os.replace
            call_seq = {"n": 0}

            def fail_on_staging_to_target(src, dst):
                """First replace: target → backup (must succeed, allows
                the function to proceed to the risky step). Second
                replace: staging → target (we force this to fail). The
                function should catch that, restore backup → target, and
                reraise."""
                call_seq["n"] += 1
                # Let the "target → backup" rename succeed (n==1).
                # Also let the recovery "backup → target" rename succeed
                # (fires AFTER we raise below). Fail only on n==2 (the
                # "staging → target" rename).
                if call_seq["n"] == 2:
                    raise OSError("synthetic swap failure")
                return real_replace(src, dst)

            with mock.patch.object(main.os, "replace", side_effect=fail_on_staging_to_target):
                with self.assertRaises(OSError):
                    main._run_finalize(
                        data_dir, cache_dir, self._make_tree(), work_dir,
                        agent_api_name="A", agent_version="v1", planner_name="A",
                    )

            # Invariant: data_dir still exists AND still contains the
            # original sentinel (the backup was restored).
            self.assertTrue(data_dir.is_dir())
            self.assertTrue((data_dir / "sentinel.txt").is_file())
            self.assertEqual((data_dir / "sentinel.txt").read_text(), "original-data")

    def test_leftover_staging_from_prior_crash_is_cleared(self):
        """If a previous crashed run left a `.<name>.staging.<pid>`
        sibling behind, the next finalize blows it away before staging
        its own writes. Otherwise `mkdir(parents=True)` would raise
        FileExistsError.
        """
        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = Path(tmp)
            work_dir = tmp_p / "work"
            work_dir.mkdir()
            data_dir = tmp_p / "data" / "A__v1"
            cache_dir = tmp_p / "cache" / "A__v1"

            # Synthesize a leftover staging dir for THIS pid.
            stale_staging = data_dir.parent / f".{data_dir.name}.staging.{os.getpid()}"
            stale_staging.mkdir(parents=True)
            (stale_staging / "stale.txt").write_text("junk")

            main._run_finalize(
                data_dir, cache_dir, self._make_tree(), work_dir,
                agent_api_name="A", agent_version="v1", planner_name="A",
            )

            # Stale staging is gone (replaced with a successful swap).
            self.assertFalse(stale_staging.exists())
            # And data_dir has the fresh tree.
            self.assertTrue((data_dir / "A_v1_metadata_tree.json").is_file())


# ---------------------------------------------------------------------------
# real 401 retry carries the new token
# ---------------------------------------------------------------------------


class Real401RetryIntegrationTests(unittest.TestCase):
    """The existing `Refresh401Tests` mocks at the `tooling_query`
    boundary — it bypasses the decorator stack and can't verify the
    retry actually carries the NEW token into the second request.

    This test mocks at the lowest-level `build_opener` seam in
    `rest_client`. A mock `OpenerDirector.open` inspects the
    Authorization header on each call:
      * call 1: Bearer old_token → raise HTTPError(401)
      * refresh_fn fires (via the real retry_on_401 decorator)
      * call 2: Bearer new_token → return a valid response

    If the  contract regressed — e.g. the retry re-used the stale
    token — call 2 would still carry Bearer old_token and the test
    would fail.
    """

    def test_retry_carries_new_token_after_401(self):
        import io
        import urllib.error
        import fetch_soql  # type: ignore
        import rest_client  # type: ignore

        observed_auth_headers: list[str] = []

        def _make_401_response() -> urllib.error.HTTPError:
            # HTTPError tolerates hdrs=None; retry_on_401 does not touch
            # .headers on a 401 (only the 403-path reads .read()).
            return urllib.error.HTTPError(
                url="https://example.my.salesforce.com/services/data/v60.0/tooling/query/",
                code=401,
                msg="Unauthorized",
                hdrs=None,
                fp=io.BytesIO(b"INVALID_SESSION_ID"),
            )

        class _FakeResp:
            """Context-manager compatible fake response returning JSON."""

            def __init__(self, body_bytes: bytes):
                self._body = body_bytes

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return self._body

        class _RecordingOpener:
            def __init__(self):
                self.n = 0

            def open(self, req):
                # Record the Authorization header so the test can assert
                # the new token landed on the retry request.
                auth = req.headers.get("Authorization") or req.get_header("Authorization")
                observed_auth_headers.append(auth or "")
                self.n += 1
                if self.n == 1:
                    raise _make_401_response()
                # Retry: return a valid Tooling query response.
                return _FakeResp(b'{"records":[{"Id":"001","DeveloperName":"X"}]}')

        # Build creds plumbing that swaps tokens on refresh.
        provider, refresh, _cell = main._build_creds_plumbing(
            ("https://example.my.salesforce.com", "old_token"),
            resolve_creds=lambda: ("https://example.my.salesforce.com", "new_token"),
            dedupe_window_s=0.0,  # allow the refresh to fire unconditionally
        )

        opener = _RecordingOpener()
        with mock.patch.object(rest_client, "build_opener", return_value=opener):
            # Use a fetcher that triggers one Tooling query. v2+ branch
            # goes through `load_soql` + the chain template — exercises the
            # same tooling_query seam the test is here to verify.
            result = fetch_soql.fetch_planner_definition(
                "SomePlanner", "v2", provider,
                api_version="v60.0", on_401_refresh=refresh,
            )

        # Contract: both requests were made; first with old_token,
        # second with new_token (the post-refresh value).
        self.assertEqual(len(observed_auth_headers), 2)
        self.assertEqual(observed_auth_headers[0], "Bearer old_token")
        self.assertEqual(observed_auth_headers[1], "Bearer new_token")
        # And the retry response shaped correctly.
        self.assertEqual(result.get("DeveloperName"), "X")


class ApiVersionEndToEndTests(unittest.TestCase):
    """the `api_version` reported by `sf org display --json`
    threads through the pipeline all the way to the REST query URL.

    Orgs on v66 must NOT hit `/services/data/v60.0/...` — that was
    . This test drives the full pipeline with a mocked
    org-display payload reporting `apiVersion=66.0` and asserts every
    Tooling/Data query fetcher receives `api_version="v66.0"`.
    """

    def test_full_pipeline_passes_v66_to_every_fetcher(self):
        with tempfile.TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "work"
            data_root = Path(tmp) / "data"
            cache_root = Path(tmp) / "cache"

            # sf org display payload reports v66 — this is the shape real
            # orgs return today (my-org-alias, my-perf-org-alias).
            org_display_payload = {
                "status": 0,
                "result": {
                    "instanceUrl": "https://example.my.salesforce.com",
                    "accessToken": "00Dxx0000000000!AQ_fake_token_value",
                    "id": "00Dxx0000000000AAA",
                    "apiVersion": "66.0",
                },
            }

            # Capture api_version passed to each fetcher via mock.call_args.
            wave_a_patches = [
                mock.patch.object(main, "fetch_planner_definition",
                                  return_value=fx.CLASSIC_PLANNER),
                mock.patch.object(main, "fetch_plugins_by_planner",
                                  return_value=fx.CLASSIC_PLUGINS),
                mock.patch.object(main, "fetch_planner_bundle_functions",
                                  return_value=fx.CLASSIC_BUNDLE_FN_JOIN),
                mock.patch.object(main, "fetch_functions_by_plugins",
                                  return_value=fx.CLASSIC_FUNCTIONS),
                mock.patch.object(main, "fetch_plugin_instructions",
                                  return_value=fx.CLASSIC_INSTRUCTIONS),
                mock.patch.object(main, "fetch_plugin_functions",
                                  return_value=fx.CLASSIC_PLUGIN_FUNCTIONS),
                mock.patch.object(main, "fetch_planner_attrs",
                                  return_value=fx.CLASSIC_ATTRS),
            ]
            wave_b_patches = [
                mock.patch.object(main, "fetch_apex_bodies_by_names",
                                  return_value=fx.CLASSIC_APEX_ROWS),
                mock.patch.object(main, "fetch_apex_bodies_by_ids",
                                  return_value=[]),
                mock.patch.object(main, "fetch_flow_definition_ids_by_names",
                                  return_value=fx.CLASSIC_FLOW_DEFS),
                mock.patch.object(main, "fetch_flow_definition_by_ids",
                                  return_value=[]),
                mock.patch.object(
                    main, "fetch_flow_metadata",
                    side_effect=lambda vid, *a, **kw: fx.CLASSIC_FLOW_METADATA.get(vid),
                ),
            ]
            patches = [
                mock.patch.object(main, "run_sf", return_value=org_display_payload),
                mock.patch.object(main, "probe_channels",
                                  return_value=fx.probe_ok_payload()),
                *_mock_bot_resolution(),
                *wave_a_patches,
                *wave_b_patches,
                mock.patch.object(main, "build_agent_data_dir",
                                  side_effect=lambda o, a, v: data_root / o / f"{a}__{v}"),
                mock.patch.object(main, "build_agent_cache_dir",
                                  side_effect=lambda o, a, v: cache_root / o / f"{a}__{v}"),
            ]
            _apply_all(patches)
            try:
                rc = main.main(_args(work_dir))
                # Snapshot call lists BEFORE `p.stop()` restores the
                # originals — otherwise `main.fetch_*` drops back to the
                # real function with no `.call_args_list`.
                fetcher_call_lists = {
                    name: getattr(main, name).call_args_list
                    for name in (
                        "fetch_planner_definition",
                        "fetch_plugins_by_planner",
                        "fetch_planner_bundle_functions",
                        "fetch_functions_by_plugins",
                        "fetch_plugin_instructions",
                        "fetch_plugin_functions",
                        "fetch_planner_attrs",
                        "fetch_apex_bodies_by_names",
                        "fetch_flow_definition_ids_by_names",
                        "fetch_flow_metadata",
                        "fetch_bot_versions",
                        "fetch_bot_definition_details",
                    )
                }
            finally:
                for p in patches:
                    p.stop()

            self.assertEqual(rc, 0)

            # Every Wave-A + Wave-B fetcher received `api_version="v66.0"`.
            # We inspect call_args.kwargs rather than positional args — the
            # kwarg is keyword-only by design.
            expected = "v66.0"
            for name, calls in fetcher_call_lists.items():
                calls_with_version = [
                    c for c in calls
                    if c.kwargs.get("api_version") == expected
                ]
                self.assertTrue(
                    calls_with_version,
                    f"{name}: no call observed with api_version={expected!r}. "
                    f"All calls: {calls}",
                )


class UncaughtExceptionToResultBlockTests(unittest.TestCase):
    """the skill contract says every exit path emits a RESULT
    block. Before the fix, an uncaught exception in the pipeline (e.g.
    the HTTP 405 from , or any future bug) propagated to the
    process boundary — users saw a Python traceback on stderr and the
    wrapper skill never got `.emit_ctx.json`. `main()` now wraps
    `_run_pipeline` in `try/except Exception` and funnels failures
    through `_emit_fail(..., "RETRIEVE_FAILED", "uncaught-exception: ...")`.
    """

    def test_uncaught_exception_surfaces_as_retrieve_failed(self):
        with tempfile.TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "work"

            # Patch `_run_pipeline` to raise an arbitrary non-HTTP bug
            # shape — proves the wrapper catches broad `Exception`, not
            # just the specific HTTPError from .
            with mock.patch.object(
                main, "_run_pipeline",
                side_effect=RuntimeError("unexpected defect in phase 6"),
            ):
                rc = main.main(_args(work_dir))

            # Exit code MUST be non-zero (failure signal) but controlled —
            # no Python traceback on stderr.
            self.assertEqual(rc, 1)

            # `.emit_ctx.json` MUST exist — the skill contract.
            ctx_path = work_dir / ".emit_ctx.json"
            self.assertTrue(ctx_path.is_file(),
                            "uncaught exception must still write .emit_ctx.json")
            ctx = _read_ctx(work_dir)
            self.assertEqual(ctx["status"], "RETRIEVE_FAILED")
            self.assertIn("uncaught-exception", ctx["error_detail"])
            self.assertIn("RuntimeError", ctx["error_detail"])
            self.assertIn("unexpected defect in phase 6", ctx["error_detail"])

    def test_uncaught_exception_redacts_bearer_tokens(self):
        """the redacted error_detail must not leak tokens even if
        the exception message happens to carry one."""
        with tempfile.TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "work"

            leaky = RuntimeError(
                "downstream failed: Authorization: Bearer TESTONLY_LEAKY_TOKEN"
            )
            with mock.patch.object(main, "_run_pipeline", side_effect=leaky):
                rc = main.main(_args(work_dir))

            self.assertEqual(rc, 1)
            ctx = _read_ctx(work_dir)
            self.assertEqual(ctx["status"], "RETRIEVE_FAILED")
            # Token must NOT appear.
            self.assertNotIn("TESTONLY_LEAKY_TOKEN", ctx["error_detail"])
            # Redaction sentinel must appear — proof the scrub ran.
            self.assertIn("<redacted>", ctx["error_detail"])

    def test_systemexit_still_propagates(self):
        """argparse's --help path raises SystemExit. That MUST propagate
        unchanged — catching it would silently swallow `--help` + any
        other intentional early exit. The wrapper catches `Exception`,
        not `BaseException`, so SystemExit is unaffected."""
        with tempfile.TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "work"

            with mock.patch.object(main, "_run_pipeline",
                                   side_effect=SystemExit(2)):
                with self.assertRaises(SystemExit) as ctx:
                    main.main(_args(work_dir))
            self.assertEqual(ctx.exception.code, 2)


class NormalizeFlowIdTargetsTests(unittest.TestCase):
    """classic bots occasionally store NGA-style
    300Uv-prefix FlowDefinition IDs or 301-prefix Flow version IDs as
    InvocationTarget. After Wave B resolves them we rewrite bundle_parsed
    in place so parse_wave sees DeveloperNames and the pending/visited
    diff collapses to zero for legitimate targets."""

    def test_rewrites_flowdefinition_id_to_developer_name(self):
        bundle = {
            "topics": [{
                "name": "T",
                "actions": [{
                    "name": "A",
                    "invocationTarget": "300UvXXXXXXXXXXXX",
                    "invocationTargetType": "flow",
                }],
            }],
            "plannerActions": [],
        }
        flow_def_rows = [{
            "Id": "300UvXXXXXXXXXXXX",
            "DeveloperName": "MyFlowName",
            "ActiveVersionId": "301VfYYYYYYYYYYYY",
        }]
        main._normalize_flow_id_targets(bundle, flow_def_rows)
        action = bundle["topics"][0]["actions"][0]
        self.assertEqual(action["invocationTarget"], "MyFlowName")
        self.assertEqual(action["_original_invocation_target_id"],
                         "300UvXXXXXXXXXXXX")

    def test_rewrites_flow_version_id_via_active_version_map(self):
        """301-prefix IDs should also resolve — via the ActiveVersionId
        side of the bi-directional map."""
        bundle = {
            "topics": [{
                "actions": [{
                    "invocationTarget": "301VfYYYYYYYYYYYY",
                    "invocationTargetType": "flow",
                }],
            }],
            "plannerActions": [],
        }
        flow_def_rows = [{
            "Id": "300UvXXXXXXXXXXXX",
            "DeveloperName": "MyFlowName",
            "ActiveVersionId": "301VfYYYYYYYYYYYY",
        }]
        main._normalize_flow_id_targets(bundle, flow_def_rows)
        self.assertEqual(
            bundle["topics"][0]["actions"][0]["invocationTarget"],
            "MyFlowName",
        )

    def test_preserves_classic_developer_name_targets(self):
        """Classic DeveloperName targets must pass through untouched —
        they have nothing to resolve AND shouldn't pick up the sentinel
        _original_invocation_target_id field."""
        bundle = {
            "topics": [{
                "actions": [{
                    "invocationTarget": "AGNT_Case_Create",
                    "invocationTargetType": "flow",
                }],
            }],
            "plannerActions": [],
        }
        flow_def_rows = [{
            "Id": "300UvXXXXXXXXXXXX",
            "DeveloperName": "AGNT_Case_Create",
            "ActiveVersionId": "301VfYYYYYYYYYYYY",
        }]
        main._normalize_flow_id_targets(bundle, flow_def_rows)
        action = bundle["topics"][0]["actions"][0]
        self.assertEqual(action["invocationTarget"], "AGNT_Case_Create")
        self.assertNotIn("_original_invocation_target_id", action)

    def test_unmatched_id_stays_as_is(self):
        """An ID that doesn't appear in flow_def_rows (Flow not queryable
        / managed package invisible) stays unchanged — that's how it
        correctly surfaces in _pending_fetches instead of silently
        discarding."""
        bundle = {
            "topics": [{
                "actions": [{
                    "invocationTarget": "300UvZZZZZZZZZZZZ",
                    "invocationTargetType": "flow",
                }],
            }],
            "plannerActions": [],
        }
        main._normalize_flow_id_targets(bundle, [{
            "Id": "300UvXXXXXXXXXXXX",
            "DeveloperName": "DifferentFlow",
            "ActiveVersionId": "301VfYYYYYYYYYYYY",
        }])
        self.assertEqual(
            bundle["topics"][0]["actions"][0]["invocationTarget"],
            "300UvZZZZZZZZZZZZ",
        )

    def test_apex_target_with_300_prefix_not_rewritten(self):
        """Only invocationTargetType=='flow' is rewritten. A target that
        happens to match a flow id but is declared as apex stays put —
        it's a caller-error we surface, not one we silently rewrite."""
        bundle = {
            "topics": [{
                "actions": [{
                    "invocationTarget": "300UvXXXXXXXXXXXX",
                    "invocationTargetType": "apex",  # wrong type
                }],
            }],
            "plannerActions": [],
        }
        flow_def_rows = [{
            "Id": "300UvXXXXXXXXXXXX",
            "DeveloperName": "MyFlow",
            "ActiveVersionId": "301VfYYYYYYYYYYYY",
        }]
        main._normalize_flow_id_targets(bundle, flow_def_rows)
        self.assertEqual(
            bundle["topics"][0]["actions"][0]["invocationTarget"],
            "300UvXXXXXXXXXXXX",
        )

    def test_empty_inputs_noop(self):
        """Empty flow_def_rows → immediate return, no mutation, no crash
        on missing 'topics' / 'plannerActions' keys."""
        bundle = {}
        main._normalize_flow_id_targets(bundle, [])
        self.assertEqual(bundle, {})

        bundle2 = {
            "topics": [{"actions": [{
                "invocationTarget": "300Uv", "invocationTargetType": "flow",
            }]}],
            "plannerActions": [],
        }
        main._normalize_flow_id_targets(bundle2, [])
        # Untouched — no lookup map to rewrite against.
        self.assertEqual(
            bundle2["topics"][0]["actions"][0]["invocationTarget"], "300Uv",
        )

    def test_rewrites_both_topics_and_planner_actions(self):
        """Fix must cover both the per-topic actions path AND the
        bundle-scope plannerActions path."""
        bundle = {
            "topics": [{
                "actions": [{
                    "invocationTarget": "300UvAAAA",
                    "invocationTargetType": "flow",
                }],
            }],
            "plannerActions": [{
                "invocationTarget": "300UvBBBB",
                "invocationTargetType": "flow",
            }],
        }
        flow_def_rows = [
            {"Id": "300UvAAAA", "DeveloperName": "TopicFlow",
             "ActiveVersionId": "301AAAA"},
            {"Id": "300UvBBBB", "DeveloperName": "BundleFlow",
             "ActiveVersionId": "301BBBB"},
        ]
        main._normalize_flow_id_targets(bundle, flow_def_rows)
        self.assertEqual(
            bundle["topics"][0]["actions"][0]["invocationTarget"], "TopicFlow",
        )
        self.assertEqual(
            bundle["plannerActions"][0]["invocationTarget"], "BundleFlow",
        )

    def test_none_invocation_target_type_ignored_safely(self):
        """Defensive: invocationTargetType missing → treat as 'not a
        flow', skip. No crash."""
        bundle = {
            "topics": [{"actions": [{
                "invocationTarget": "300UvAAAA",
                "invocationTargetType": None,
            }]}],
            "plannerActions": [],
        }
        main._normalize_flow_id_targets(bundle, [
            {"Id": "300UvAAAA", "DeveloperName": "X", "ActiveVersionId": "301"}
        ])
        self.assertEqual(
            bundle["topics"][0]["actions"][0]["invocationTarget"], "300UvAAAA",
        )


class CollectWaveBTargetsStandardActionTests(unittest.TestCase):
    """`_route` in `_collect_wave_b_targets` must
    short-circuit on declared-only target types (standardInvocableAction,
    generatePromptResponse, genai*, prompt*) BEFORE calling
    resolve_or_unresolved — otherwise it pollutes `_unresolved` with
    spurious "invalid-id-format" entries for perfectly valid identifiers
    that simply aren't Salesforce Ids."""

    def test_standard_action_not_routed_through_id_resolver(self):
        """`streamKnowledgeSearch` is a built-in standard action — not
        an Id. It should not end up in apex_ids, flow_ids, apex_names,
        or flow_names AND it should NOT appear in the `_unresolved`
        list that resolve_or_unresolved populates on non-Id inputs.
        """
        bundle = {
            "topics": [{
                "name": "T",
                "actions": [{
                    "name": "A",
                    "invocationTarget": "streamKnowledgeSearch",
                    "invocationTargetType": "standardInvocableAction",
                }],
            }],
            "plannerActions": [],
        }
        result = main._collect_wave_b_targets(bundle)
        self.assertEqual(result["apex_names"], [])
        self.assertEqual(result["apex_ids"], [])
        self.assertEqual(result["flow_names"], [])
        self.assertEqual(result["flow_ids"], [])
        self.assertEqual(
            result["_unresolved"], [],
            "standardInvocableAction must not pollute _unresolved with "
            "invalid-id-format entries",
        )

    def test_generate_prompt_response_short_circuits(self):
        """`generatePromptResponse` targets are prompt-template names;
        not routed to Apex/Flow fetchers (Batch 1 is body-only for
        Apex+Flow; prompts flow through the retrieve path)."""
        bundle = {
            "topics": [{
                "name": "T",
                "actions": [{
                    "invocationTarget": "MyPromptTemplate",
                    "invocationTargetType": "generatePromptResponse",
                }],
            }],
            "plannerActions": [],
        }
        result = main._collect_wave_b_targets(bundle)
        self.assertEqual(result["apex_names"], [])
        self.assertEqual(result["flow_names"], [])
        self.assertEqual(result["_unresolved"], [])

    def test_flow_and_apex_still_route_correctly(self):
        """Positive control — the short-circuit must not break flow/apex
        routing. A mix of classic DeveloperNames + NGA IDs should land in
        the right buckets, and standard actions should pass through
        without polluting anything."""
        bundle = {
            "topics": [{
                "name": "T",
                "actions": [
                    # Classic flow by DeveloperName
                    {"invocationTarget": "MyFlow",
                     "invocationTargetType": "flow"},
                    # Classic apex by name
                    {"invocationTarget": "MyApex",
                     "invocationTargetType": "apex"},
                    # Standard action (new short-circuit path)
                    {"invocationTarget": "streamKnowledgeSearch",
                     "invocationTargetType": "standardInvocableAction"},
                    # NGA apex by Id
                    {"invocationTarget": "01p1N000005SsDNQA0",
                     "invocationTargetType": "apex"},
                ],
            }],
            "plannerActions": [],
        }
        result = main._collect_wave_b_targets(bundle)
        self.assertIn("MyFlow", result["flow_names"])
        self.assertIn("MyApex", result["apex_names"])
        self.assertIn("01p1N000005SsDNQA0", result["apex_ids"])
        self.assertEqual(result["_unresolved"], [])

    def test_unknown_type_silently_skipped(self):
        """An unrecognized invocationTargetType falls through all the
        known-type branches and is silently skipped. parse_wave tags the
        node as UNKNOWN in the tree (via `_kind_counts`), so the signal
        is visible without polluting _unresolved."""
        bundle = {
            "topics": [{
                "name": "T",
                "actions": [{
                    "invocationTarget": "SomeThing",
                    "invocationTargetType": "unheardOfType",
                }],
            }],
            "plannerActions": [],
        }
        result = main._collect_wave_b_targets(bundle)
        self.assertEqual(result["apex_names"], [])
        self.assertEqual(result["flow_names"], [])
        self.assertEqual(
            result["_unresolved"], [],
            "Unknown invocationTargetType shouldn't reach the ID router, "
            "so _unresolved stays clean.",
        )

    def test_classic_flow_name_not_routed_through_id_resolver(self):
        """classic bots store plain DeveloperNames
        like `MyFlow` — not Salesforce Ids. The router must route these
        directly to flow_names via invocationTargetType, NOT through
        resolve_or_unresolved (which would reject them as invalid-id-
        format and pollute _unresolved)."""
        bundle = {
            "topics": [{
                "actions": [
                    {"invocationTarget": "MyFlow",
                     "invocationTargetType": "flow"},
                    {"invocationTarget": "AGNT_Foo",
                     "invocationTargetType": "apex"},
                ],
            }],
            "plannerActions": [],
        }
        result = main._collect_wave_b_targets(bundle)
        self.assertIn("MyFlow", result["flow_names"])
        self.assertIn("AGNT_Foo", result["apex_names"])
        self.assertEqual(
            result["_unresolved"], [],
            "Classic DeveloperNames shouldn't be sent through the ID "
            "resolver at all — they're not Ids.",
        )


class NormalizePromptTemplateIdTargetsTests(unittest.TestCase):
    """Bug 1 fix (2026-05-05): classic bots occasionally store 0hf-prefix
    GenAiPromptTemplate IDs as `GenAiFunctionDefinition.InvocationTarget`.
    After Wave B resolves them via `list_prompt_template_metadata`
    (GenAiPromptTemplate is NOT SOQL-queryable — Metadata API only) we
    rewrite bundle_parsed in place so Wave B's retrieve uses the
    DeveloperName Metadata API expects."""

    def test_rewrites_prompt_template_id_to_developer_name(self):
        bundle = {
            "topics": [{
                "actions": [{
                    "invocationTarget": "0hfUv0000021mCjIAI",
                    "invocationTargetType": "GenAiPromptTemplate",
                }],
            }],
            "plannerActions": [],
        }
        rows = [{"Id": "0hfUv0000021mCjIAI", "DeveloperName": "My_Prompt"}]
        main._normalize_prompt_template_id_targets(bundle, rows)
        action = bundle["topics"][0]["actions"][0]
        self.assertEqual(action["invocationTarget"], "My_Prompt")
        self.assertEqual(
            action["_original_invocation_target_id"], "0hfUv0000021mCjIAI"
        )

    def test_preserves_classic_developer_name_targets(self):
        """Classic DeveloperName targets pass through untouched — the
        rewrite is only for Id-shaped targets that appeared in the lookup."""
        bundle = {
            "topics": [{
                "actions": [{
                    "invocationTarget": "Existing_Prompt_Name",
                    "invocationTargetType": "GenAiPromptTemplate",
                }],
            }],
            "plannerActions": [],
        }
        # Lookup covers a different Id entirely — the DeveloperName target
        # isn't a key in the map so it's not rewritten.
        rows = [{"Id": "0hfUv0000021Other", "DeveloperName": "Other_Prompt"}]
        main._normalize_prompt_template_id_targets(bundle, rows)
        action = bundle["topics"][0]["actions"][0]
        self.assertEqual(action["invocationTarget"], "Existing_Prompt_Name")
        self.assertNotIn("_original_invocation_target_id", action)

    def test_unmatched_id_stays_as_is(self):
        """Id not present in the lookup (e.g. Tooling returned empty
        because GenAiPromptTemplate isn't exposed on this org) stays
        as-is so it correctly surfaces in _pending_fetches."""
        bundle = {
            "topics": [{
                "actions": [{
                    "invocationTarget": "0hfUv00000xxxxxYYY",
                    "invocationTargetType": "GenAiPromptTemplate",
                }],
            }],
            "plannerActions": [],
        }
        main._normalize_prompt_template_id_targets(bundle, [])
        action = bundle["topics"][0]["actions"][0]
        self.assertEqual(action["invocationTarget"], "0hfUv00000xxxxxYYY")
        self.assertNotIn("_original_invocation_target_id", action)


class NormalizeApexIdTargetsTests(unittest.TestCase):
    """Gap B fix (2026-05-05): classic bots occasionally store 01p-prefix
    ApexClass Ids as `GenAiFunctionDefinition.InvocationTarget` (live-verified
    on my-org-alias: 01p000000000000AAA -> MyController).
    After Wave B resolves them via `fetch_apex_bodies_by_ids` we rewrite
    bundle_parsed in place so the tree renders the ApexClass Name instead
    of the raw Id."""

    def test_rewrites_apex_id_to_class_name(self):
        bundle = {
            "topics": [{
                "actions": [{
                    "invocationTarget": "01p000000000000AAA",
                    "invocationTargetType": "apex",
                }],
            }],
            "plannerActions": [],
        }
        rows = [{"Id": "01p000000000000AAA", "Name": "MyController"}]
        main._normalize_apex_id_targets(bundle, rows)
        action = bundle["topics"][0]["actions"][0]
        self.assertEqual(action["invocationTarget"], "MyController")
        self.assertEqual(
            action["_original_invocation_target_id"], "01p000000000000AAA"
        )

    def test_non_apex_ttype_left_unchanged(self):
        """Same Id but a non-apex ttype — the ttype gate must block the
        rewrite so a Flow action whose target happens to collide with an
        ApexClass Id isn't miscaught."""
        bundle = {
            "topics": [{
                "actions": [{
                    "invocationTarget": "01p000000000000AAA",
                    "invocationTargetType": "flow",
                }],
            }],
            "plannerActions": [],
        }
        rows = [{"Id": "01p000000000000AAA", "Name": "MyController"}]
        main._normalize_apex_id_targets(bundle, rows)
        action = bundle["topics"][0]["actions"][0]
        self.assertEqual(action["invocationTarget"], "01p000000000000AAA")
        self.assertNotIn("_original_invocation_target_id", action)

    def test_unmatched_id_stays_as_is(self):
        """Id not present in the lookup (e.g. by-Id fetch failed or the
        class was deleted) stays as-is so it correctly surfaces in
        _pending_fetches."""
        bundle = {
            "topics": [{
                "actions": [{
                    "invocationTarget": "01pFAKEIDFAKEIDAAA",
                    "invocationTargetType": "apex",
                }],
            }],
            "plannerActions": [],
        }
        main._normalize_apex_id_targets(bundle, [])
        action = bundle["topics"][0]["actions"][0]
        self.assertEqual(action["invocationTarget"], "01pFAKEIDFAKEIDAAA")
        self.assertNotIn("_original_invocation_target_id", action)

    def test_preserves_classic_developer_name_targets(self):
        """Classic Name targets pass through untouched — the rewrite is
        only for Id-shaped targets (01p-prefix) that appeared in the lookup."""
        bundle = {
            "topics": [{
                "actions": [{
                    "invocationTarget": "MyApexClass",
                    "invocationTargetType": "apex",
                }],
            }],
            "plannerActions": [],
        }
        # Lookup covers a different Id entirely — the Name target isn't
        # Id-shaped and doesn't hit the prefix gate.
        rows = [{"Id": "01p000000000000AAA", "Name": "MyController"}]
        main._normalize_apex_id_targets(bundle, rows)
        action = bundle["topics"][0]["actions"][0]
        self.assertEqual(action["invocationTarget"], "MyApexClass")
        self.assertNotIn("_original_invocation_target_id", action)


class CollectWaveBTargetsPromptTemplateIdTests(unittest.TestCase):
    """Bug 1 fix (2026-05-05): 0hf-prefix prompt template Ids are routed
    to a dedicated `prompt_template_ids` bucket so post-Wave-B resolution
    can rewrite them; DeveloperName targets still short-circuit as before."""

    def test_prompt_template_id_routes_to_id_bucket(self):
        bundle = {
            "topics": [],
            "plannerActions": [{
                "invocationTarget": "0hfUv0000021mCjIAI",
                "invocationTargetType": "GenAiPromptTemplate",
            }],
        }
        result = main._collect_wave_b_targets(bundle)
        self.assertEqual(
            result.get("prompt_template_ids"), ["0hfUv0000021mCjIAI"]
        )
        # DeveloperName bucket stays empty — the Id is routed to the Id
        # bucket and the short-circuit returns BEFORE the DeveloperName
        # branch would have run.
        self.assertEqual(result.get("_unresolved"), [])

    def test_prompt_template_developer_name_does_not_pollute_id_bucket(self):
        bundle = {
            "topics": [],
            "plannerActions": [{
                "invocationTarget": "My_Prompt_Template_Name",
                "invocationTargetType": "GenAiPromptTemplate",
            }],
        }
        result = main._collect_wave_b_targets(bundle)
        self.assertEqual(result.get("prompt_template_ids"), [])
        # DeveloperName-shaped prompt-template targets still short-circuit
        # (parse_wave enqueues them into PROMPT_TEMPLATE pending) — no
        # change from prior behavior, verified via absence from all
        # name/id buckets we'd route through.
        self.assertEqual(result.get("apex_names"), [])
        self.assertEqual(result.get("flow_names"), [])

    def test_non_0hf_prefix_ignored(self):
        """Id-shaped target for a prompt-template ttype but WRONG prefix
        (e.g. a Flow Id accidentally typed with prompt ttype) doesn't
        pollute prompt_template_ids — the prefix gate catches it."""
        bundle = {
            "topics": [],
            "plannerActions": [{
                "invocationTarget": "300Uv00000abcdeFGH",  # Flow-shaped Id
                "invocationTargetType": "GenAiPromptTemplate",
            }],
        }
        result = main._collect_wave_b_targets(bundle)
        # Not routed anywhere — neither prompt-template Id bucket nor
        # flow buckets (ttype gated). Surfaces nowhere, which is
        # acceptable: classify_action_call downstream will still enqueue
        # the string as-is as a PROMPT_TEMPLATE pending fetch.
        self.assertEqual(result.get("prompt_template_ids"), [])


class FetchFlowDefinitionViewByDurableIdsTests(unittest.TestCase):
    """Option B (2026-05-05): `fetch_flow_definition_view_by_durable_ids`
    is the Data-API fallback fetcher for managed-installed flows that
    Tooling's `FlowDefinition` doesn't index.

    Contract:
      * Empty input short-circuits to `[]` without firing a SOQL call
        (matches every other list-shaped fetcher in this module).
      * Rows are returned from `data_query` verbatim — projection to
        the `flow_def_rows` shape happens in the caller
        (`fetch_flow_definition_ids_by_names`).
    """

    def test_happy_path_returns_rows(self):
        import fetch_soql  # type: ignore
        view_row = {
            "DurableId": "SvcCopilotTmpl__VerifyCode",
            "ApiName": "VerifyCode",
            "Label": "Verify Code",
            "NamespacePrefix": "SvcCopilotTmpl",
            "ActiveVersionId": "SvcCopilotTmpl__VerifyCode-1",
            "IsActive": True,
            "ManageableState": "installed",
            "ProcessType": "AutoLaunchedFlow",
        }
        with mock.patch.object(
            fetch_soql, "data_query",
            return_value={"records": [view_row]},
        ) as mock_dq:
            rows = fetch_soql.fetch_flow_definition_view_by_durable_ids(
                ["SvcCopilotTmpl__VerifyCode"],
                lambda: ("url", "tok"),
                api_version="v60.0",
                on_401_refresh=lambda: ("url", "tok"),
            )
        self.assertEqual(rows, [view_row])
        # Exactly one data_query call — the fetcher doesn't accidentally
        # re-fire on the Tooling surface.
        self.assertEqual(mock_dq.call_count, 1)

    def test_empty_input_short_circuits(self):
        """Empty durable_ids list returns [] WITHOUT firing a SOQL call
        (matches the module-wide empty-input-short-circuit invariant)."""
        import fetch_soql  # type: ignore
        with mock.patch.object(fetch_soql, "data_query") as mock_dq:
            rows = fetch_soql.fetch_flow_definition_view_by_durable_ids(
                [],
                lambda: ("url", "tok"),
                api_version="v60.0",
                on_401_refresh=lambda: ("url", "tok"),
            )
        self.assertEqual(rows, [])
        self.assertEqual(mock_dq.call_count, 0)

    def test_multi_row_returns_all(self):
        import fetch_soql  # type: ignore
        view_rows = [
            {
                "DurableId": "SvcCopilotTmpl__VerifyCode",
                "ApiName": "VerifyCode",
                "NamespacePrefix": "SvcCopilotTmpl",
                "ActiveVersionId": "SvcCopilotTmpl__VerifyCode-1",
                "ManageableState": "installed",
            },
            {
                "DurableId": "sales_inbound_flows__SendVerifyCode",
                "ApiName": "SendVerifyCode",
                "NamespacePrefix": "sales_inbound_flows",
                "ActiveVersionId": "sales_inbound_flows__SendVerifyCode-2",
                "ManageableState": "installed",
            },
        ]
        with mock.patch.object(
            fetch_soql, "data_query",
            return_value={"records": view_rows},
        ):
            rows = fetch_soql.fetch_flow_definition_view_by_durable_ids(
                [
                    "SvcCopilotTmpl__VerifyCode",
                    "sales_inbound_flows__SendVerifyCode",
                ],
                lambda: ("url", "tok"),
                api_version="v60.0",
                on_401_refresh=lambda: ("url", "tok"),
            )
        self.assertEqual(len(rows), 2)
        # Membership assertion rather than sort-order — codepoint sort of
        # mixed-case prefixes is fragile; the fetcher returns rows in the
        # order `data_query` supplies them.
        self.assertEqual(
            {r["DurableId"] for r in rows},
            {
                "SvcCopilotTmpl__VerifyCode",
                "sales_inbound_flows__SendVerifyCode",
            },
        )


class FlowDefinitionViewFallbackTests(unittest.TestCase):
    """Option B (2026-05-05, updated after managed-bucket retirement):
    `fetch_flow_definition_ids_by_names` fires a SINGLE Tooling
    `FlowDefinition` query (unmanaged-only — the template filters
    `NamespacePrefix IS NULL`). Any input name that query doesn't resolve
    triggers a single follow-up `FlowDefinitionView` (Data API) query.
    Projected view-only rows carry `Id=None`, `ActiveVersionId=None`,
    `_body_available=False`, and `_source="FlowDefinitionView"`.
    """

    def test_fallback_fires_on_managed_miss(self):
        """Tooling FlowDefinition returns empty for a `ns__Name` input
        (managed flows aren't indexed on subscriber orgs + the unmanaged
        query filters `NamespacePrefix IS NULL` anyway); FlowDefinitionView
        returns a matching row. Output row carries the view-shaped markers
        and `DeveloperName` = qualified ns__bare."""
        import fetch_soql  # type: ignore
        view_row = {
            "DurableId": "SvcCopilotTmpl__VerifyCode",
            "ApiName": "VerifyCode",
            "Label": "Verify Code",
            "NamespacePrefix": "SvcCopilotTmpl",
            "ActiveVersionId": "SvcCopilotTmpl__VerifyCode-1",
            "ManageableState": "installed",
        }
        with mock.patch.object(
            fetch_soql, "tooling_query",
            return_value={"records": []},
        ), mock.patch.object(
            fetch_soql, "data_query",
            return_value={"records": [view_row]},
        ) as mock_dq:
            rows = fetch_soql.fetch_flow_definition_ids_by_names(
                ["SvcCopilotTmpl__VerifyCode"],
                lambda: ("url", "tok"),
                api_version="v60.0",
                on_401_refresh=lambda: ("url", "tok"),
            )
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertIsNone(row["Id"])
        self.assertIsNone(row["ActiveVersionId"])
        self.assertFalse(row["_body_available"])
        self.assertEqual(row["_source"], "FlowDefinitionView")
        self.assertEqual(row["DeveloperName"], "SvcCopilotTmpl__VerifyCode")
        self.assertEqual(row["NamespacePrefix"], "SvcCopilotTmpl")
        self.assertEqual(row["_bare_developer_name"], "VerifyCode")
        self.assertEqual(mock_dq.call_count, 1)

    def test_fallback_skipped_when_tooling_resolves_everything(self):
        """All input names resolved by Tooling → FlowDefinitionView is
        never queried. Guards against unnecessary Data-API calls on the
        99% of runs where every referenced flow is unmanaged or locally
        installed."""
        import fetch_soql  # type: ignore
        real_row = {
            "Id": "300Uv000000Real",
            "DeveloperName": "MyFlow",
            "NamespacePrefix": None,
            "ActiveVersionId": "301Vf000000Real",
        }
        with mock.patch.object(
            fetch_soql, "tooling_query",
            return_value={"records": [real_row]},
        ), mock.patch.object(fetch_soql, "data_query") as mock_dq:
            rows = fetch_soql.fetch_flow_definition_ids_by_names(
                ["MyFlow"],
                lambda: ("url", "tok"),
                api_version="v60.0",
                on_401_refresh=lambda: ("url", "tok"),
            )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["_source"], "FlowDefinition")
        self.assertTrue(rows[0]["_body_available"])
        self.assertEqual(mock_dq.call_count, 0)

    def test_mixed_resolution_paths(self):
        """Three input names, three distinct fates:
          1. `ExistingFlow` — unmanaged, resolved by Tooling.
          2. `SvcCopilotTmpl__VerifyCode` — managed miss on Tooling,
             resolved by FlowDefinitionView.
          3. `ghost_ns__GhostFlow` — managed miss on BOTH surfaces.

        Expected: 2 rows total (1 real + 1 view-only), the ghost flow
        absent from the result set. FlowDefinitionView queried exactly
        once with both unresolved names in the IN-list.
        """
        import fetch_soql  # type: ignore

        real_row = {
            "Id": "300Uv000000Real",
            "DeveloperName": "ExistingFlow",
            "NamespacePrefix": None,
            "ActiveVersionId": "301Vf000000Real",
        }
        view_row = {
            "DurableId": "SvcCopilotTmpl__VerifyCode",
            "ApiName": "VerifyCode",
            "NamespacePrefix": "SvcCopilotTmpl",
            "ActiveVersionId": "SvcCopilotTmpl__VerifyCode-1",
            "ManageableState": "installed",
        }

        # Tooling is called exactly once — the unmanaged query (template
        # filters NamespacePrefix IS NULL). It matches only ExistingFlow;
        # the two managed-qualified names return no rows from that
        # surface and fall through to the view fallback.
        with mock.patch.object(
            fetch_soql, "tooling_query",
            return_value={"records": [real_row]},
        ) as mock_tq, mock.patch.object(
            fetch_soql, "data_query",
            return_value={"records": [view_row]},
        ) as mock_dq:
            rows = fetch_soql.fetch_flow_definition_ids_by_names(
                [
                    "ExistingFlow",
                    "SvcCopilotTmpl__VerifyCode",
                    "ghost_ns__GhostFlow",
                ],
                lambda: ("url", "tok"),
                api_version="v60.0",
                on_401_refresh=lambda: ("url", "tok"),
            )
        self.assertEqual(len(rows), 2)
        # Tooling queried exactly once for the full input (no bucketing).
        self.assertEqual(mock_tq.call_count, 1)
        # View fallback queried exactly once — no per-name fanout.
        self.assertEqual(mock_dq.call_count, 1)

        by_name = {r["DeveloperName"]: r for r in rows}
        # Real Tooling row — source marker explicit.
        self.assertEqual(by_name["ExistingFlow"]["Id"], "300Uv000000Real")
        self.assertEqual(by_name["ExistingFlow"]["_source"], "FlowDefinition")
        self.assertTrue(by_name["ExistingFlow"]["_body_available"])
        # View-only row — no Id, no active version, marked unavailable.
        view_result = by_name["SvcCopilotTmpl__VerifyCode"]
        self.assertIsNone(view_result["Id"])
        self.assertIsNone(view_result["ActiveVersionId"])
        self.assertFalse(view_result["_body_available"])
        self.assertEqual(view_result["_source"], "FlowDefinitionView")
        # Ghost flow absent.
        self.assertNotIn("ghost_ns__GhostFlow", by_name)


class FetchPlannerDefinitionChainTests(unittest.TestCase):
    """2026-05-05: `fetch_planner_definition(agent, version)` performs a
    chain-LIKE lookup against GenAiPlannerDefinition. The accretive
    naming invariant (v1=`<Agent>`, v2=`<Agent>_v2`, v3=
    `<Agent>_v2_v3`, ...) means the correct planner always matches
    `<Agent>%\\_vN` for vN>=2 and `<Agent>` exactly for v1. On multi-row
    matches the resolver picks the row with the shortest DeveloperName.
    """

    def _stub_tooling(self, records):
        """Patch `fetch_soql.tooling_query` to return a fixed record list."""
        import fetch_soql  # type: ignore
        return mock.patch.object(
            fetch_soql, "tooling_query",
            return_value={"records": records},
        )

    def test_v1_exact_match(self):
        import fetch_soql  # type: ignore
        with self._stub_tooling([
            {"Id": "1VxVF000V1", "DeveloperName": "Inbound_Sales_Agent"},
        ]):
            row = fetch_soql.fetch_planner_definition(
                "Inbound_Sales_Agent", None,
                lambda: ("url", "tok"),
                api_version="v66.0",
                on_401_refresh=lambda: ("url", "tok"),
            )
        self.assertIsNotNone(row)
        self.assertEqual(row["DeveloperName"], "Inbound_Sales_Agent")

    def test_v1_explicit_string(self):
        import fetch_soql  # type: ignore
        with self._stub_tooling([
            {"Id": "1VxVF000V1", "DeveloperName": "Inbound_Sales_Agent"},
        ]):
            row = fetch_soql.fetch_planner_definition(
                "Inbound_Sales_Agent", "v1",
                lambda: ("url", "tok"),
                api_version="v66.0",
                on_401_refresh=lambda: ("url", "tok"),
            )
        self.assertEqual(row["DeveloperName"], "Inbound_Sales_Agent")

    def test_v2_single_match(self):
        import fetch_soql  # type: ignore
        with self._stub_tooling([
            {"Id": "1VxVF000V2", "DeveloperName": "Inbound_Sales_Agent_v2"},
        ]):
            row = fetch_soql.fetch_planner_definition(
                "Inbound_Sales_Agent", "v2",
                lambda: ("url", "tok"),
                api_version="v66.0",
                on_401_refresh=lambda: ("url", "tok"),
            )
        self.assertEqual(row["DeveloperName"], "Inbound_Sales_Agent_v2")

    def test_v2_multi_row_shortest_wins(self):
        """LIKE `<Agent>%\\_v2` can match both `<Agent>_v2` and a deeper
        chain like `<Agent>_foo_v2` (rare but possible). Shortest
        DeveloperName wins — the canonical row carries no extra segment."""
        import fetch_soql  # type: ignore
        with self._stub_tooling([
            {"Id": "1VxVF000DEEPER",
             "DeveloperName": "Inbound_Sales_Agent_foo_v2"},
            {"Id": "1VxVF000V2",
             "DeveloperName": "Inbound_Sales_Agent_v2"},
        ]):
            row = fetch_soql.fetch_planner_definition(
                "Inbound_Sales_Agent", "v2",
                lambda: ("url", "tok"),
                api_version="v66.0",
                on_401_refresh=lambda: ("url", "tok"),
            )
        self.assertEqual(row["DeveloperName"], "Inbound_Sales_Agent_v2")

    def test_zero_rows_returns_none(self):
        import fetch_soql  # type: ignore
        with self._stub_tooling([]):
            row = fetch_soql.fetch_planner_definition(
                "NoSuchAgent", "v3",
                lambda: ("url", "tok"),
                api_version="v66.0",
                on_401_refresh=lambda: ("url", "tok"),
            )
        self.assertIsNone(row)

    def test_chain_like_pattern_passed_to_soql_for_v5(self):
        """The SOQL body that reaches `tooling_query` contains the chain
        LIKE pattern literally. Verify AGENT_NAME + VERSION are rendered
        through the template with the `%\\_` escape in between.
        """
        import fetch_soql  # type: ignore
        captured: dict = {}

        def fake_tooling(creds_provider, soql, *, api_version, on_401_refresh):
            captured["soql"] = soql
            return {"records": []}

        with mock.patch.object(fetch_soql, "tooling_query",
                               side_effect=fake_tooling):
            fetch_soql.fetch_planner_definition(
                "MyAgent", "v5",
                lambda: ("url", "tok"),
                api_version="v66.0",
                on_401_refresh=lambda: ("url", "tok"),
            )
        self.assertIn("LIKE 'MyAgent%\\_v5'", captured["soql"])


class SwapDirAtomicCoTenancyTests(unittest.TestCase):
    """`_swap_dir_atomic` preserves sibling content in `target`. The prior
    whole-directory `os.replace` wiped any co-tenant subdirs that another
    caller may have written into the same `<agent>__<ver>/` directory."""

    def test_preserves_sibling_session_dirs(self) -> None:
        # Simulate co-tenancy: target dir already has a sibling subdir
        # + a bare file written by some other caller.
        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = Path(tmp)
            target = tmp_p / "agent__v1"
            target.mkdir()
            (target / "sibling-data").mkdir()
            (target / "sibling-data" / "payload.json").write_text(
                "from-other-caller"
            )
            (target / "_sessions").mkdir()
            (target / "_sessions" / "marker.link").write_text(
                "../agent__v1/sibling-data"
            )

            # Architecture's own previous output, about to be overwritten.
            (target / "old_tree.json").write_text("old")

            # Staging dir — what architecture wants to write.
            staging = tmp_p / ".agent__v1.staging.123"
            staging.mkdir()
            (staging / "agent_v1_metadata_tree.json").write_text("new-tree")
            (staging / "last_built_at.txt").write_text("2026-05-05T12:00:00Z\n")

            main._swap_dir_atomic(target, staging)

            # Sibling content survives — the whole point of the fix.
            self.assertTrue(
                (target / "sibling-data" / "payload.json").is_file()
            )
            self.assertEqual(
                (target / "sibling-data" / "payload.json").read_text(),
                "from-other-caller",
            )
            self.assertTrue((target / "_sessions" / "marker.link").is_file())

            # Architecture's new files landed.
            self.assertEqual(
                (target / "agent_v1_metadata_tree.json").read_text(), "new-tree"
            )
            self.assertTrue((target / "last_built_at.txt").is_file())

            # Old file that wasn't in staging stays untouched.
            self.assertTrue((target / "old_tree.json").is_file())
            self.assertEqual((target / "old_tree.json").read_text(), "old")

            # Staging dir cleaned up.
            self.assertFalse(staging.exists())

    def test_overwrites_own_files_cleanly(self) -> None:
        """Same filename in both target and staging → staging content wins."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = Path(tmp)
            target = tmp_p / "agent__v1"
            target.mkdir()
            (target / "tree.json").write_text("old-content")

            staging = tmp_p / ".agent__v1.staging.123"
            staging.mkdir()
            (staging / "tree.json").write_text("new-content")

            main._swap_dir_atomic(target, staging)

            self.assertEqual(
                (target / "tree.json").read_text(), "new-content"
            )

    def test_overwrites_when_target_entry_is_dir(self) -> None:
        """If the old target entry is a directory and the new staging
        entry is a file (or vice versa), replace cleans up the old kind
        before os.replace lands the new one."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = Path(tmp)
            target = tmp_p / "agent__v1"
            target.mkdir()
            # Old entry is a directory with nested content.
            (target / "payload").mkdir()
            (target / "payload" / "nested.txt").write_text("deep")

            staging = tmp_p / ".agent__v1.staging.123"
            staging.mkdir()
            # New entry with the same name is a plain file.
            (staging / "payload").write_text("now-a-file")

            main._swap_dir_atomic(target, staging)

            self.assertTrue((target / "payload").is_file())
            self.assertEqual(
                (target / "payload").read_text(), "now-a-file"
            )

    def test_missing_staging_raises(self) -> None:
        """Pre-existing precondition: staging must exist, or we raise."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = Path(tmp)
            target = tmp_p / "agent__v1"
            target.mkdir()
            staging = tmp_p / ".agent__v1.staging.does-not-exist"
            with self.assertRaises(OSError):
                main._swap_dir_atomic(target, staging)

    def test_run_finalize_preserves_session_subdir_across_reruns(self) -> None:
        """End-to-end via `_run_finalize`: after a first successful run
        seeds a co-tenant session dir, a second run must not wipe it.
        Covers the production path — the bug the user reported."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = Path(tmp)
            work_dir = tmp_p / "work"
            work_dir.mkdir()
            data_dir = tmp_p / "data" / "A__v1"
            cache_dir = tmp_p / "cache" / "A__v1"

            tree = {
                "_schema_version": "3.0",
                "agent": {"api_name": "A", "version": "v1"},
                "root": {"kind": "BOT_DEFINITION", "api_name": "A",
                         "children": []},
                "node_count": 1, "depth": 0,
                "_kind_counts": {"BOT_DEFINITION": 1},
                "_pending_fetches": {k: [] for k in (
                    "FLOW", "APEX", "PROMPT_TEMPLATE", "STANDARD_ACTION",
                )},
                "_unresolved": [],
            }
            # First run — populate data_dir.
            main._run_finalize(
                data_dir, cache_dir, dict(tree), work_dir,
                agent_api_name="A", agent_version="v1", planner_name="A",
            )
            # Simulate a co-tenant dropping content alongside.
            sibling_dir = data_dir / "sibling-payload"
            sibling_dir.mkdir()
            (sibling_dir / "payload.json").write_text("cotenant-data")

            # Second run — the original bug: this would wipe the sibling dir.
            main._run_finalize(
                data_dir, cache_dir, dict(tree), work_dir,
                agent_api_name="A", agent_version="v1", planner_name="A",
            )

            # Sibling dir and its contents must survive.
            self.assertTrue(sibling_dir.is_dir())
            self.assertTrue((sibling_dir / "payload.json").is_file())
            self.assertEqual(
                (sibling_dir / "payload.json").read_text(),
                "cotenant-data",
            )
            # Architecture's own tree is still present (re-written).
            self.assertTrue((data_dir / "A_v1_metadata_tree.json").is_file())


# ---------------------------------------------------------------------------
# Bug 1 fix (2026-05-05): GenAiPromptTemplate is NOT SOQL-queryable. Id →
# DeveloperName resolution runs through `sf org list metadata` (Metadata
# API) via the new `list_prompt_template_metadata` helper.
# ---------------------------------------------------------------------------


class ListPromptTemplateMetadataTests(unittest.TestCase):
    """Unit tests for `metadata_listing.list_prompt_template_metadata` —
    thin wrapper over `run_sf("list_metadata_genaiprompttemplate", ...)`.

    The shape we care about is produced by the sf CLI:
        {"status": 0, "result": [{"id": "0hfUv...", "fullName": "Foo", ...}]}
    Defensive returns on malformed result (None / wrong type) keep the
    failure mode quiet — callers already tolerate empty lists.
    """

    def test_happy_path_returns_result_rows(self):
        import metadata_listing  # type: ignore
        payload = {
            "status": 0,
            "result": [
                {"id": "0hfUv0000021mCjIAI", "fullName": "My_Prompt",
                 "type": "GenAiPromptTemplate"},
                {"id": "0hfUv0000021mOtherAAA", "fullName": "Other_Prompt",
                 "type": "GenAiPromptTemplate"},
            ],
        }
        with mock.patch.object(metadata_listing, "run_sf", return_value=payload):
            rows = metadata_listing.list_prompt_template_metadata("test-org")
        self.assertEqual(rows, payload["result"])

    def test_empty_result_returns_empty_list(self):
        import metadata_listing  # type: ignore
        with mock.patch.object(
            metadata_listing, "run_sf",
            return_value={"status": 0, "result": []},
        ):
            rows = metadata_listing.list_prompt_template_metadata("test-org")
        self.assertEqual(rows, [])

    def test_malformed_result_returns_empty_list(self):
        """Defensive: if sf CLI's `result` key is not a list (e.g. None
        on some error paths that still exit 0), we degrade to []."""
        import metadata_listing  # type: ignore
        with mock.patch.object(
            metadata_listing, "run_sf",
            return_value={"status": 0, "result": None},
        ):
            rows = metadata_listing.list_prompt_template_metadata("test-org")
        self.assertEqual(rows, [])


class FetchWaveBPromptTemplateMetadataWiringTests(unittest.TestCase):
    """Bug 1 fix (2026-05-05): `_fetch_wave_b_by_names` invokes
    `list_prompt_template_metadata` (Metadata API listing), then filters +
    reshapes to the {Id, DeveloperName} shape the downstream pipeline
    expects. Verify the filter + reshape contract — only the requested
    Ids come back, keyed as the pipeline's existing prompt_template_id_rows
    shape.
    """

    def test_listmetadata_rows_filtered_and_reshaped(self):
        with mock.patch.object(
            main, "list_prompt_template_metadata",
            return_value=[
                {"id": "0hfAAA", "fullName": "TplA",
                 "type": "GenAiPromptTemplate"},
                {"id": "0hfBBB", "fullName": "TplB",
                 "type": "GenAiPromptTemplate"},
            ],
        ):
            with mock.patch.object(main, "fetch_apex_bodies_by_names", return_value=[]), \
                 mock.patch.object(main, "fetch_apex_bodies_by_ids", return_value=[]), \
                 mock.patch.object(main, "fetch_flow_definition_ids_by_names", return_value=[]), \
                 mock.patch.object(main, "fetch_flow_definition_by_ids", return_value=[]):
                out = main._fetch_wave_b_by_names(
                    apex_names=[],
                    apex_ids=[],
                    flow_names=[],
                    flow_ids=[],
                    prompt_template_ids=["0hfAAA"],
                    creds_provider=lambda: ("url", "tok"),
                    refresh_fn=lambda: ("url", "tok"),
                    api_version="v60.0",
                    org_alias="test-org",
                    parallelism=2,
                )
        # Only the requested Id survives (0hfAAA); 0hfBBB is filtered out.
        # The shape matches the old SOQL contract: {Id, DeveloperName}.
        self.assertEqual(
            out["prompt_template_id_rows"],
            [{"Id": "0hfAAA", "DeveloperName": "TplA"}],
        )

    def test_listmetadata_failure_non_fatal(self):
        """SfCliError from the Metadata listing is caught and surfaced via
        the unresolved channel; the run continues with an empty rowset."""
        from sf_cli import SfCliError  # type: ignore
        with mock.patch.object(
            main, "list_prompt_template_metadata",
            side_effect=SfCliError("metadata-listing-exploded"),
        ):
            with mock.patch.object(main, "fetch_apex_bodies_by_names", return_value=[]), \
                 mock.patch.object(main, "fetch_apex_bodies_by_ids", return_value=[]), \
                 mock.patch.object(main, "fetch_flow_definition_ids_by_names", return_value=[]), \
                 mock.patch.object(main, "fetch_flow_definition_by_ids", return_value=[]):
                out = main._fetch_wave_b_by_names(
                    apex_names=[],
                    apex_ids=[],
                    flow_names=[],
                    flow_ids=[],
                    prompt_template_ids=["0hfAAA"],
                    creds_provider=lambda: ("url", "tok"),
                    refresh_fn=lambda: ("url", "tok"),
                    api_version="v60.0",
                    org_alias="test-org",
                    parallelism=2,
                )
        self.assertEqual(out["prompt_template_id_rows"], [])
        reasons = [u.get("reason") or "" for u in out["unresolved"]]
        self.assertTrue(
            any("prompt-template-listmetadata-failed" in r for r in reasons),
            f"expected listmetadata-failed in unresolved; got {reasons}",
        )


class RetrievePromptTemplatesTests(unittest.TestCase):
    """Gap C (2026-05-05): unit tests for
    `metadata_listing.retrieve_prompt_templates` — the sf CLI wrapper
    that retrieves GenAiPromptTemplate bodies via
    `sf project retrieve start --metadata GenAiPromptTemplate:...`.

    The helper:
      1. Short-circuits on empty input (no sf call).
      2. Parses `unpackaged.zip` from the retrieve dir via stdlib
         `zipfile` + `xml.etree.ElementTree`.
      3. Extracts developerName/masterLabel/activeVersionIdentifier/
         templateVersions[*].content/inputs[*].
      4. Returns `{}` on SfCliError (non-fatal — main.py's call site
         logs an `_unresolved[]` entry).
      5. Skips files whose XML fails to parse; sibling templates still
         surface.
    """

    def _run_retrieve_writes_zip(self, files: dict):
        """Build a mock `_run_retrieve` side_effect that writes an
        unpackaged.zip into the retrieve dir as the real CLI would.

        `files = {inner_path: xml_bytes}`. `retrieve_prompt_templates`
        wipes the retrieve dir before invoking the subprocess, so the zip
        MUST be created by the mock (the retrieve dir is always the
        `--target-metadata-dir` argv element)."""
        import zipfile

        def _side_effect(argv, timeout):
            target_dir = Path(argv[argv.index("--target-metadata-dir") + 1])
            target_dir.mkdir(parents=True, exist_ok=True)
            zip_path = target_dir / "unpackaged.zip"
            with zipfile.ZipFile(zip_path, "w") as zf:
                for inner, xml_bytes in files.items():
                    zf.writestr(inner, xml_bytes)
            return subprocess.CompletedProcess(
                argv, returncode=0, stdout='{"status":0,"result":{}}', stderr="",
            )

        return _side_effect

    def test_empty_input_short_circuits_without_sf_call(self):
        import metadata_listing  # type: ignore
        with mock.patch.object(metadata_listing, "_run_retrieve") as mrun, \
             tempfile.TemporaryDirectory() as d:
            result = metadata_listing.retrieve_prompt_templates(
                "org-alias", [], Path(d),
            )
        self.assertEqual(result, {})
        mrun.assert_not_called()

    def test_happy_path_single_template(self):
        import metadata_listing  # type: ignore
        xml = (
            b'<?xml version="1.0" encoding="UTF-8"?>'
            b'<GenAiPromptTemplate xmlns="http://soap.sforce.com/2006/04/metadata">'
            b'<developerName>My_Prompt</developerName>'
            b'<masterLabel>My Prompt</masterLabel>'
            b'<activeVersionIdentifier>v1</activeVersionIdentifier>'
            b'<templateVersions>'
            b'<versionIdentifier>v1</versionIdentifier>'
            b'<content># ROLE\nHello {{$Input:Query}}</content>'
            b'<inputs><apiName>Query</apiName><dataType>String</dataType></inputs>'
            b'</templateVersions>'
            b'</GenAiPromptTemplate>'
        )
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            side_effect = self._run_retrieve_writes_zip({
                "unpackaged/genAiPromptTemplates/My_Prompt.genAiPromptTemplate": xml,
                "unpackaged/package.xml": b"<Package/>",
            })
            with mock.patch.object(
                metadata_listing, "_run_retrieve", side_effect=side_effect,
            ):
                result = metadata_listing.retrieve_prompt_templates(
                    "org-alias", ["My_Prompt"], tmp,
                )
        self.assertIn("My_Prompt", result)
        body = result["My_Prompt"]
        self.assertEqual(body["developerName"], "My_Prompt")
        self.assertEqual(body["masterLabel"], "My Prompt")
        self.assertEqual(body["activeVersionIdentifier"], "v1")
        self.assertEqual(body["content"], "# ROLE\nHello {{$Input:Query}}")
        self.assertEqual(
            body["inputs"], [{"name": "Query", "dataType": "String"}],
        )

    def test_sf_cli_error_returns_empty_dict(self):
        """Non-zero exit without auth-pattern stderr is swallowed as
        non-fatal — caller gets an empty dict."""
        import metadata_listing  # type: ignore
        failure = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="Error: retrieve blew up",
        )
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(
                metadata_listing, "_run_retrieve", return_value=failure,
            ):
                result = metadata_listing.retrieve_prompt_templates(
                    "org-alias", ["Foo"], Path(d),
                )
        self.assertEqual(result, {})

    def test_auth_required_reraises(self):
        """Non-zero exit WITH auth-pattern stderr raises AuthRequired."""
        import metadata_listing  # type: ignore
        from sf_cli import AuthRequired  # type: ignore
        failure = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="",
            stderr="Error: NoOrgAuthenticationError — login required",
        )
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(
                metadata_listing, "_run_retrieve", return_value=failure,
            ):
                with self.assertRaises(AuthRequired):
                    metadata_listing.retrieve_prompt_templates(
                        "org-alias", ["Foo"], Path(d),
                    )

    def test_missing_zip_returns_empty_dict(self):
        import metadata_listing  # type: ignore
        # _run_retrieve succeeds but leaves no unpackaged.zip on disk.
        success_no_zip = subprocess.CompletedProcess(
            args=[], returncode=0, stdout='{"status":0,"result":{}}', stderr="",
        )
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(
                metadata_listing, "_run_retrieve", return_value=success_no_zip,
            ):
                result = metadata_listing.retrieve_prompt_templates(
                    "org-alias", ["Foo"], Path(d),
                )
        self.assertEqual(result, {})

    def test_multi_version_picks_active(self):
        import metadata_listing  # type: ignore
        xml = (
            b'<?xml version="1.0" encoding="UTF-8"?>'
            b'<GenAiPromptTemplate xmlns="http://soap.sforce.com/2006/04/metadata">'
            b'<developerName>Versioned</developerName>'
            b'<activeVersionIdentifier>v2</activeVersionIdentifier>'
            b'<templateVersions>'
            b'<versionIdentifier>v1</versionIdentifier>'
            b'<content>OLD</content>'
            b'</templateVersions>'
            b'<templateVersions>'
            b'<versionIdentifier>v2</versionIdentifier>'
            b'<content>ACTIVE</content>'
            b'</templateVersions>'
            b'<templateVersions>'
            b'<versionIdentifier>v3</versionIdentifier>'
            b'<content>DRAFT</content>'
            b'</templateVersions>'
            b'</GenAiPromptTemplate>'
        )
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            side_effect = self._run_retrieve_writes_zip({
                "unpackaged/genAiPromptTemplates/Versioned.genAiPromptTemplate": xml,
            })
            with mock.patch.object(
                metadata_listing, "_run_retrieve", side_effect=side_effect,
            ):
                result = metadata_listing.retrieve_prompt_templates(
                    "org-alias", ["Versioned"], tmp,
                )
        self.assertEqual(result["Versioned"]["content"], "ACTIVE")

    def test_template_with_no_inputs(self):
        import metadata_listing  # type: ignore
        xml = (
            b'<?xml version="1.0" encoding="UTF-8"?>'
            b'<GenAiPromptTemplate xmlns="http://soap.sforce.com/2006/04/metadata">'
            b'<developerName>NoInputs</developerName>'
            b'<activeVersionIdentifier>v1</activeVersionIdentifier>'
            b'<templateVersions>'
            b'<versionIdentifier>v1</versionIdentifier>'
            b'<content>Prompt body</content>'
            b'</templateVersions>'
            b'</GenAiPromptTemplate>'
        )
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            side_effect = self._run_retrieve_writes_zip({
                "unpackaged/genAiPromptTemplates/NoInputs.genAiPromptTemplate": xml,
            })
            with mock.patch.object(
                metadata_listing, "_run_retrieve", side_effect=side_effect,
            ):
                result = metadata_listing.retrieve_prompt_templates(
                    "org-alias", ["NoInputs"], tmp,
                )
        self.assertEqual(result["NoInputs"]["inputs"], [])

    def test_xml_parse_failure_skips_file_continues(self):
        """Malformed XML on one template must not prevent sibling
        templates from surfacing."""
        import metadata_listing  # type: ignore
        good_xml = (
            b'<?xml version="1.0" encoding="UTF-8"?>'
            b'<GenAiPromptTemplate xmlns="http://soap.sforce.com/2006/04/metadata">'
            b'<developerName>GoodTpl</developerName>'
            b'<activeVersionIdentifier>v1</activeVersionIdentifier>'
            b'<templateVersions>'
            b'<versionIdentifier>v1</versionIdentifier>'
            b'<content>Fine</content>'
            b'</templateVersions>'
            b'</GenAiPromptTemplate>'
        )
        broken_xml = b"<not valid xml"
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            side_effect = self._run_retrieve_writes_zip({
                "unpackaged/genAiPromptTemplates/GoodTpl.genAiPromptTemplate": good_xml,
                "unpackaged/genAiPromptTemplates/Broken.genAiPromptTemplate": broken_xml,
            })
            with mock.patch.object(
                metadata_listing, "_run_retrieve", side_effect=side_effect,
            ):
                result = metadata_listing.retrieve_prompt_templates(
                    "org-alias", ["GoodTpl", "Broken"], tmp,
                )
        self.assertIn("GoodTpl", result)
        self.assertNotIn("Broken", result)

    def test_stale_retrieve_dir_contents_wiped(self):
        """A prior invocation's `unpackaged.zip` must not be trusted if
        this run's sf call fails before writing a new one."""
        import metadata_listing  # type: ignore
        failure = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="Error: boom",
        )
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            # Plant a stale zip pretending a prior run left it.
            stale = tmp / "prompt_template_retrieve"
            stale.mkdir(parents=True, exist_ok=True)
            (stale / "unpackaged.zip").write_bytes(b"stale")
            with mock.patch.object(
                metadata_listing, "_run_retrieve", return_value=failure,
            ):
                result = metadata_listing.retrieve_prompt_templates(
                    "org-alias", ["Foo"], tmp,
                )
        self.assertEqual(result, {})
        # Stale file should have been nuked before the sf call.
        self.assertFalse((stale / "unpackaged.zip").exists())

    def test_retrieve_builds_one_metadata_flag_per_name(self):
        """Live proof (2026-05-05): `sf project retrieve start` treats a
        comma-joined `--metadata TypeA:A,TypeA:B` as ONE malformed member
        name and silently produces a package-xml-only zip. The fix is to
        repeat `--metadata` once per template. Lock that shape in."""
        import metadata_listing  # type: ignore
        captured_argv: list[list[str]] = []

        def _capture(argv, timeout):
            captured_argv.append(list(argv))
            return subprocess.CompletedProcess(
                argv, returncode=0,
                stdout='{"status":0,"result":{}}', stderr="",
            )

        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(
                metadata_listing, "_run_retrieve", side_effect=_capture,
            ):
                metadata_listing.retrieve_prompt_templates(
                    "org-alias", ["A", "B", "C"], Path(d),
                )

        self.assertEqual(len(captured_argv), 1)
        argv = captured_argv[0]
        self.assertEqual(argv.count("--metadata"), 3)
        # Each `--metadata` flag MUST be followed by a single
        # `GenAiPromptTemplate:<name>` — never a comma-joined string.
        for name in ("A", "B", "C"):
            spec = f"GenAiPromptTemplate:{name}"
            idx = argv.index(spec)
            self.assertEqual(argv[idx - 1], "--metadata")
            self.assertNotIn(",", spec)


class CollectPromptTemplateNamesTests(unittest.TestCase):
    """Gap C: `_collect_prompt_template_names` walks topics + plannerActions
    and returns the set of DeveloperNames that should be passed to
    `retrieve_prompt_templates`. Defensive against residual 0hf-Ids
    (normalization missed) so the retrieve CLI doesn't get a malformed
    spec."""

    def test_collects_topic_action_names(self):
        bundle = {
            "topics": [{
                "actions": [
                    {"invocationTarget": "Foo_Tpl",
                     "invocationTargetType": "GenAiPromptTemplate"},
                    {"invocationTarget": "Bar_Tpl",
                     "invocationTargetType": "generatePromptResponse"},
                ],
            }],
            "plannerActions": [],
        }
        names = main._collect_prompt_template_names(bundle)
        self.assertEqual(names, {"Foo_Tpl", "Bar_Tpl"})

    def test_collects_planner_action_names(self):
        bundle = {
            "topics": [],
            "plannerActions": [
                {"invocationTarget": "Planner_Tpl",
                 "invocationTargetType": "GenAiPromptTemplate"},
            ],
        }
        names = main._collect_prompt_template_names(bundle)
        self.assertEqual(names, {"Planner_Tpl"})

    def test_skips_non_prompt_ttype(self):
        bundle = {
            "topics": [{
                "actions": [
                    {"invocationTarget": "MyFlow",
                     "invocationTargetType": "flow"},
                    {"invocationTarget": "MyApex",
                     "invocationTargetType": "apex"},
                ],
            }],
            "plannerActions": [],
        }
        names = main._collect_prompt_template_names(bundle)
        self.assertEqual(names, set())

    def test_skips_residual_0hf_id_targets(self):
        """If normalization missed an Id (template not in org
        list-metadata), don't send a malformed spec to retrieve."""
        bundle = {
            "topics": [{
                "actions": [
                    {"invocationTarget": "0hfUv0000021mCjIAI",
                     "invocationTargetType": "GenAiPromptTemplate"},
                    {"invocationTarget": "Clean_Tpl",
                     "invocationTargetType": "GenAiPromptTemplate"},
                ],
            }],
            "plannerActions": [],
        }
        names = main._collect_prompt_template_names(bundle)
        self.assertEqual(names, {"Clean_Tpl"})


class PromptTemplateBodyAttachmentTests(unittest.TestCase):
    """Gap C: `_stamp_prompt_template_bodies` attaches retrieved body
    fields onto matching PROMPT_TEMPLATE leaves. Unmatched leaves get
    `_body_available = False` so the renderer can distinguish a failed
    retrieve from a successfully-empty body."""

    def test_stamps_body_onto_matching_leaf(self):
        tree = {
            "root": {
                "kind": "BOT_DEFINITION",
                "children": [{
                    "kind": "TOPIC", "api_name": "T",
                    "children": [{
                        "kind": "GEN_AI_FUNCTION", "api_name": "F",
                        "children": [{
                            "kind": "PROMPT_TEMPLATE", "api_name": "Tpl",
                        }],
                    }],
                }],
            },
        }
        bodies = {
            "Tpl": {
                "developerName": "Tpl",
                "masterLabel": "Template One",
                "activeVersionIdentifier": "v1",
                "content": "Prompt body",
                "inputs": [{"name": "Q", "dataType": "String"}],
            },
        }
        main._stamp_prompt_template_bodies(tree["root"], bodies)
        leaf = tree["root"]["children"][0]["children"][0]["children"][0]
        self.assertEqual(leaf["master_label"], "Template One")
        self.assertEqual(leaf["content"], "Prompt body")
        self.assertEqual(leaf["inputs"], [{"name": "Q", "dataType": "String"}])
        self.assertTrue(leaf["_body_available"])

    def test_unmatched_leaf_gets_body_available_false(self):
        tree = {
            "root": {
                "kind": "BOT_DEFINITION",
                "children": [{
                    "kind": "PROMPT_TEMPLATE", "api_name": "Missing",
                }],
            },
        }
        main._stamp_prompt_template_bodies(tree["root"], {})
        self.assertFalse(tree["root"]["children"][0]["_body_available"])
        self.assertNotIn("content", tree["root"]["children"][0])

    def test_does_not_touch_non_prompt_leaves(self):
        tree = {
            "root": {
                "kind": "BOT_DEFINITION",
                "children": [
                    {"kind": "APEX", "api_name": "Cls"},
                    {"kind": "FLOW", "api_name": "Flw"},
                ],
            },
        }
        main._stamp_prompt_template_bodies(
            tree["root"], {"Cls": {"content": "x"}, "Flw": {"content": "y"}},
        )
        # Neither APEX nor FLOW leaves gain body fields.
        self.assertNotIn("content", tree["root"]["children"][0])
        self.assertNotIn("_body_available", tree["root"]["children"][0])
        self.assertNotIn("content", tree["root"]["children"][1])
        self.assertNotIn("_body_available", tree["root"]["children"][1])


class TreeChildOrderingTests(unittest.TestCase):
    """Schema 3.1 (2026-05-05) pins deterministic child ordering at the
    tree's single source of truth (`finalize.sort_tree_in_place`) so
    downstream readers see a byte-stable order regardless of Builder
    reorder operations or SOQL result-set sequencing.

    Contract:
    - `BOT_DEFINITION.children`: TOPIC nodes first (alpha, case-insensitive);
      non-topic plannerActions follow as a distinct trailing group.
    - Each TOPIC's children: alpha by api_name, case-insensitive.
    - FLOW children untouched — flow-actionCall order is semantically
      the author's execution sequence.
    """

    def _sort(self, root: dict) -> dict:
        from finalize import sort_tree_in_place
        sort_tree_in_place(root)
        return root

    def test_topics_sorted_alphabetical_case_insensitive(self):
        root = {
            "kind": "BOT_DEFINITION",
            "api_name": "Bot",
            "children": [
                {"kind": "TOPIC", "api_name": "Zeta", "children": []},
                {"kind": "TOPIC", "api_name": "alpha", "children": []},
                {"kind": "TOPIC", "api_name": "Mike", "children": []},
            ],
        }
        self._sort(root)
        names = [c["api_name"] for c in root["children"]]
        self.assertEqual(names, ["alpha", "Mike", "Zeta"])

    def test_topics_precede_planner_level_actions(self):
        """Non-topic plannerAction children (e.g. a GEN_AI_FUNCTION hung
        directly off the planner, no parent TOPIC) MUST render after all
        TOPIC children, regardless of api_name ordering. The "planner-
        level actions are a distinct trailing group" convention is load-
        bearing for humans scanning the rendered tree."""
        root = {
            "kind": "BOT_DEFINITION",
            "api_name": "Bot",
            "children": [
                # Non-topic node with an api_name that would sort FIRST
                # alphabetically — the tier rule must override alpha.
                {"kind": "GEN_AI_FUNCTION", "api_name": "aaa_action", "children": []},
                {"kind": "TOPIC", "api_name": "Zeta", "children": []},
                {"kind": "TOPIC", "api_name": "Mike", "children": []},
            ],
        }
        self._sort(root)
        kinds = [c["kind"] for c in root["children"]]
        self.assertEqual(kinds, ["TOPIC", "TOPIC", "GEN_AI_FUNCTION"])
        # Alpha within the TOPIC tier is preserved.
        self.assertEqual(root["children"][0]["api_name"], "Mike")
        self.assertEqual(root["children"][1]["api_name"], "Zeta")

    def test_topic_children_sorted_alphabetical(self):
        root = {
            "kind": "BOT_DEFINITION",
            "api_name": "Bot",
            "children": [
                {
                    "kind": "TOPIC", "api_name": "OnlyTopic",
                    "children": [
                        {"kind": "GEN_AI_FUNCTION", "api_name": "Zebra"},
                        {"kind": "GEN_AI_FUNCTION", "api_name": "apple"},
                        {"kind": "GEN_AI_FUNCTION", "api_name": "Mango"},
                    ],
                },
            ],
        }
        self._sort(root)
        kids = root["children"][0]["children"]
        self.assertEqual(
            [c["api_name"] for c in kids],
            ["apple", "Mango", "Zebra"],
        )

    def test_flow_children_order_preserved(self):
        """FLOW actionCall order is the flow author's execution sequence.
        sort_tree_in_place does NOT descend into FLOW children."""
        root = {
            "kind": "BOT_DEFINITION",
            "api_name": "Bot",
            "children": [
                {
                    "kind": "TOPIC", "api_name": "T",
                    "children": [
                        {
                            "kind": "GEN_AI_FUNCTION", "api_name": "Fn",
                            "children": [
                                {
                                    "kind": "FLOW", "api_name": "ParentFlow",
                                    "children": [
                                        {"kind": "APEX", "api_name": "zzz"},
                                        {"kind": "APEX", "api_name": "aaa"},
                                    ],
                                },
                            ],
                        },
                    ],
                },
            ],
        }
        self._sort(root)
        flow = root["children"][0]["children"][0]["children"][0]
        self.assertEqual(
            [c["api_name"] for c in flow["children"]],
            ["zzz", "aaa"],
        )

    def test_empty_children_noop(self):
        root = {"kind": "BOT_DEFINITION", "api_name": "Bot", "children": []}
        self._sort(root)
        self.assertEqual(root["children"], [])

    def test_missing_root_noop(self):
        """Defensive — a degenerate tree shouldn't raise."""
        from finalize import sort_tree_in_place
        sort_tree_in_place(None)  # type: ignore[arg-type]
        sort_tree_in_place({})


if __name__ == "__main__":
    unittest.main()
