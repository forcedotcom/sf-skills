"""End-to-end waterfall tests for ``fetch_dc._run_waterfall``.

Mocks ``dc.post`` at the network boundary; dispatches per-query fixture
rows so the 5-wave orchestration runs to completion. Asserts on:

- per-query manifest entries (rows, status, wave)
- harvested_ids tracking across waves
- session_shape classification
- on-disk dc.<name>.json artifacts written by ``storage.save``
"""
from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from . import _bootstrap  # noqa: F401  — sys.path setup

import fetch_dc  # type: ignore
from config import paths  # type: ignore
from .fixtures.synthetic_session import IDS, make_rows  # type: ignore


def _build_fixture_dispatch() -> dict[str, list[dict]]:
    """Return rows keyed by DMO name for the synthetic session fixture."""
    return make_rows()


def _make_post_dispatcher(rows_by_name: dict[str, list[dict]]):
    """Return a fake ``dc.post`` that dispatches to the right fixture
    rows by inspecting the query_name argument."""
    def fake_post(sql: str, instance_url: str, token: str, query_name: str = ""):
        # `_fetch` passes the template name as query_name; that's exactly
        # what we keyed on in the fixture.
        return list(rows_by_name.get(query_name, []))
    return fake_post


def _make_ctx(tmpdir: Path) -> dict:
    """Build the same ctx shape that fetch_dc.main() builds."""
    return {
        "session_id": IDS.SID,
        "org_alias": "my-org",
        "instance_url": "https://example.salesforce.com",
        "token": "TOKEN",
        "verbose": False,
        "queries": [],
        "started_at": datetime.now(timezone.utc),
        "org_id_15": None,
        "agent_api_name": None,
        "agent_version": None,
    }


class _WaterfallHarness:
    """Patch DATA_ROOT + dc.post; build ctx; run the waterfall."""

    def __init__(self, *, rows_overrides: dict[str, list[dict]] | None = None):
        self.rows_overrides = rows_overrides or {}

    def __enter__(self):
        self._tmp = TemporaryDirectory()
        self._tmpdir = Path(self._tmp.name)
        self.ctx = _make_ctx(self._tmpdir)
        rows = _build_fixture_dispatch()
        rows.update(self.rows_overrides)
        self._post = _make_post_dispatcher(rows)
        self._patches = [
            mock.patch.object(paths, "DATA_ROOT", self._tmpdir),
            mock.patch.object(fetch_dc, "post", side_effect=self._post),
            # Keep _log quiet during tests
            mock.patch.object(fetch_dc, "_log"),
        ]
        for p in self._patches:
            p.start()
        return self

    def __exit__(self, *exc):
        for p in self._patches:
            p.stop()
        self._tmp.cleanup()

    def session_dir(self) -> Path:
        # macOS resolves /var → /private/var; resolve once so `is_file`
        # checks work after storage.save's path composition.
        return (
            self._tmpdir.resolve()
            / IDS.ORG_ID_15
            / f"{IDS.AGENT_API}__{IDS.AGENT_VERSION}"
            / IDS.SID
        )


# -----------------------------------------------------------------------------
# Identity stamping (wave 1a)
# -----------------------------------------------------------------------------


class WaterfallIdentityTests(unittest.TestCase):

    def test_identity_resolved_into_ctx_after_wave_1a(self):
        with _WaterfallHarness() as h:
            fetch_dc._run_waterfall(h.ctx)
        self.assertEqual(h.ctx["org_id_15"], IDS.ORG_ID_15)
        self.assertEqual(h.ctx["agent_api_name"], IDS.AGENT_API)
        self.assertEqual(h.ctx["agent_version"], IDS.AGENT_VERSION)

    def test_sessions_and_participants_persisted_after_identity_resolved(self):
        # The deferred-save flush in wave 1a should write both files.
        with _WaterfallHarness() as h:
            fetch_dc._run_waterfall(h.ctx)
            # Search the entire tmp tree — avoids macOS /private/var ↔ /var
            # resolution discrepancies between paths.session_dir() and our
            # locally-built path.
            written = {p.name for p in h._tmpdir.rglob("dc.*.json")}
        self.assertIn("dc.sessions.json", written)
        self.assertIn("dc.participants.json", written)


# -----------------------------------------------------------------------------
# Wave-by-wave artifact persistence
# -----------------------------------------------------------------------------


class WaterfallWritesArtifactsTests(unittest.TestCase):

    def test_populated_dmos_emit_dc_json_artifacts(self):
        with _WaterfallHarness() as h:
            fetch_dc._run_waterfall(h.ctx)
            files = {p.name for p in h._tmpdir.rglob("dc.*.json")}
        # 11 DMOs are populated in the synthetic fixture; each lands as a file.
        for name in (
            "dc.sessions.json", "dc.interactions.json", "dc.steps.json",
            "dc.messages.json", "dc.participants.json",
            "dc.gateway_requests.json", "dc.gateway_responses.json",
            "dc.generations.json", "dc.content_quality.json",
            "dc.gateway_records.json", "dc.gateway_request_tags.json",
        ):
            self.assertIn(name, files, f"{name} should be on disk")

    def test_zero_row_dmos_skipped_no_artifact(self):
        with _WaterfallHarness() as h:
            fetch_dc._run_waterfall(h.ctx)
            files = {p.name for p in h._tmpdir.rglob("dc.*.json")}
        # `tags` and friends have empty rows → no on-disk artifact.
        self.assertNotIn("dc.tags.json", files)
        self.assertNotIn("dc.tag_definitions.json", files)


# -----------------------------------------------------------------------------
# Manifest entries (one per query)
# -----------------------------------------------------------------------------


class WaterfallManifestTests(unittest.TestCase):

    def test_24_query_entries_appended(self):
        with _WaterfallHarness() as h:
            fetch_dc._run_waterfall(h.ctx)
        names = [q["name"] for q in h.ctx["queries"]]
        # Exactly the 24 templates fetch_dc declares (no duplicates from
        # tag_definitions retry: synthetic fixture's tag_definitions is
        # empty, so retry runs once and overwrites the prior empty entry).
        self.assertGreaterEqual(len(names), 24)
        # Critical names appear at least once
        for required in ("sessions", "interactions", "steps", "participants",
                         "gateway_requests", "generations", "messages"):
            self.assertIn(required, names)

    def test_each_query_has_wave_status_rows_elapsed_ms(self):
        with _WaterfallHarness() as h:
            fetch_dc._run_waterfall(h.ctx)
        for q in h.ctx["queries"]:
            self.assertIn("name", q)
            self.assertIn("wave", q)
            self.assertIn("rows", q)
            self.assertIn("status", q)
            self.assertIn("elapsed_ms", q)
            self.assertIn(q["status"], ("ok", "empty", "skipped", "error"))


# -----------------------------------------------------------------------------
# harvested_ids
# -----------------------------------------------------------------------------


class WaterfallHarvestedIdsTests(unittest.TestCase):

    def test_harvested_ids_match_fixture_counts(self):
        with _WaterfallHarness() as h:
            fetch_dc._run_waterfall(h.ctx)
            harvested = h.ctx["harvested_ids"]
        self.assertEqual(harvested["sessions"], 1)
        self.assertEqual(harvested["interactions"], 3)
        self.assertEqual(harvested["steps_total"], 3)
        self.assertEqual(harvested["gateway_request_ids"], 2)
        # moments DMO is empty; fetch_dc falls through to the participants
        # harvest (AGENT participant row carries IDS.AGENT_API = "DemoAgent").
        from .fixtures.synthetic_session import IDS  # type: ignore
        self.assertEqual(harvested["agents_observed"], [IDS.AGENT_API])

    def test_steps_by_type_categorizes_correctly(self):
        with _WaterfallHarness() as h:
            fetch_dc._run_waterfall(h.ctx)
            sbt = h.ctx["harvested_ids"]["steps_by_type"]
        # Synthetic fixture has 1 each of TOPIC_STEP, ACTION_STEP, TRUST_GUARDRAILS_STEP
        self.assertEqual(sbt["ACTION_STEP"], 1)
        self.assertEqual(sbt["TOPIC_STEP"], 1)
        self.assertEqual(sbt["TRUST_GUARDRAILS_STEP"], 1)
        self.assertEqual(sbt["LLM_STEP"], 0)


# -----------------------------------------------------------------------------
# Session-shape classification
# -----------------------------------------------------------------------------


class WaterfallSessionShapeTests(unittest.TestCase):

    def test_normal_session_classified_as_complete(self):
        with _WaterfallHarness() as h:
            fetch_dc._run_waterfall(h.ctx)
        self.assertEqual(h.ctx["session_shape"], "complete")

    def test_no_steps_with_gateway_requests_classified_as_lag(self):
        # Override: empty interactions/steps/messages but keep gateway_requests.
        rows = make_rows()
        rows["interactions"] = []
        rows["steps"] = []
        rows["messages"] = []
        with _WaterfallHarness(rows_overrides=rows) as h:
            fetch_dc._run_waterfall(h.ctx)
        self.assertEqual(h.ctx["session_shape"], "interactions_not_materialized_yet")

    def test_steps_no_llm_no_gateway_classified_as_abandoned(self):
        # ACTION_STEP + TOPIC_STEP exist but no LLM_STEP and no gateway_requests.
        rows = make_rows()
        rows["gateway_requests"] = []
        rows["gateway_responses"] = []
        rows["gateway_records"] = []
        rows["gateway_request_tags"] = []
        with _WaterfallHarness(rows_overrides=rows) as h:
            fetch_dc._run_waterfall(h.ctx)
        self.assertEqual(h.ctx["session_shape"], "abandoned_before_llm")


# -----------------------------------------------------------------------------
# Empty harvest branches (zero IDs → _fetch_empty path)
# -----------------------------------------------------------------------------


class WaterfallEmptyHarvestTests(unittest.TestCase):

    def test_no_interactions_skips_steps_via_fetch_empty(self):
        rows = make_rows()
        rows["interactions"] = []
        with _WaterfallHarness(rows_overrides=rows) as h:
            fetch_dc._run_waterfall(h.ctx)
        # The steps query should be in the manifest as 'skipped'.
        steps_entries = [q for q in h.ctx["queries"] if q["name"] == "steps"]
        self.assertEqual(len(steps_entries), 1)
        self.assertEqual(steps_entries[0]["status"], "skipped")
        self.assertIn("no interactions", steps_entries[0]["_unavailable_reason"])

    def test_no_gateway_requests_skips_audit_chain(self):
        rows = make_rows()
        rows["gateway_requests"] = []
        with _WaterfallHarness(rows_overrides=rows) as h:
            fetch_dc._run_waterfall(h.ctx)
        # gateway_responses + tags + records + metadata + llm all skipped
        for name in ("gateway_responses", "gateway_request_tags",
                     "gateway_records", "gateway_request_metadata",
                     "gateway_request_llm"):
            entries = [q for q in h.ctx["queries"] if q["name"] == name]
            self.assertEqual(entries[0]["status"], "skipped",
                             f"{name} should be skipped")


if __name__ == "__main__":
    unittest.main()
