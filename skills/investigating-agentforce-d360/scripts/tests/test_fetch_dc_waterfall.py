"""Tests for ``fetch_dc`` waterfall building blocks.

Covers the per-query helpers and the manifest writer. Doesn't drive the
full 5-wave waterfall (that's exercised live and the orchestration is
linear over the small per-query helpers tested here).

- ``_classify_session_shape`` pure
- ``_fetch``                  HTTP + storage.save side effects
- ``_fetch_empty``            no-HTTP record-only
- ``_write_manifest``         on-disk JSON shape
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
from dc import DCQueryError  # type: ignore
from .fixtures.synthetic_session import IDS  # type: ignore


# -----------------------------------------------------------------------------
# _classify_session_shape — pure
# -----------------------------------------------------------------------------


class ClassifySessionShapeTests(unittest.TestCase):

    def test_session_not_found_when_no_sessions(self):
        out = fetch_dc._classify_session_shape(
            sessions_count=0, steps_total=0,
            llm_step_count=0, gw_req_count=0,
            steps_with_generation_id=0,
        )
        self.assertEqual(out, "session_not_found")

    def test_interactions_not_materialized_yet_when_gw_present_no_steps(self):
        out = fetch_dc._classify_session_shape(
            sessions_count=1, steps_total=0,
            llm_step_count=0, gw_req_count=2,
            steps_with_generation_id=0,
        )
        self.assertEqual(out, "interactions_not_materialized_yet")

    def test_abandoned_before_llm_when_steps_present_no_llm(self):
        out = fetch_dc._classify_session_shape(
            sessions_count=1, steps_total=3,
            llm_step_count=0, gw_req_count=0,
            steps_with_generation_id=0,
        )
        self.assertEqual(out, "abandoned_before_llm")

    def test_planner_ran_no_gateway_logs(self):
        out = fetch_dc._classify_session_shape(
            sessions_count=1, steps_total=3,
            llm_step_count=2, gw_req_count=0,
            steps_with_generation_id=2,
        )
        self.assertEqual(out, "planner_ran_no_gateway_logs")

    def test_complete_for_normal_session(self):
        out = fetch_dc._classify_session_shape(
            sessions_count=1, steps_total=3,
            llm_step_count=1, gw_req_count=2,
            steps_with_generation_id=1,
        )
        self.assertEqual(out, "complete")


# -----------------------------------------------------------------------------
# _fetch — HTTP success / error paths
# -----------------------------------------------------------------------------


def _make_ctx(tmpdir: Path) -> dict:
    return {
        "session_id": IDS.SID,
        "org_alias": "my-org",
        "instance_url": "https://example.salesforce.com",
        "token": "TOKEN",
        "verbose": False,
        "queries": [],
        "started_at": datetime.now(timezone.utc),
        "org_id_15": IDS.ORG_ID_15,
        "agent_api_name": IDS.AGENT_API,
        "agent_version": IDS.AGENT_VERSION,
    }


class FetchHappyPathTests(unittest.TestCase):

    def test_fetch_records_query_in_manifest_and_saves_rows(self):
        rows = [{"ssot__Id__c": "x"}]
        with TemporaryDirectory() as t:
            with mock.patch.object(paths, "DATA_ROOT", Path(t)):
                ctx = _make_ctx(Path(t))
                with mock.patch.object(fetch_dc, "post", return_value=rows):
                    out = fetch_dc._fetch(
                        ctx, wave=1, name="sessions",
                        where="ssot__Id__c = 'x'",
                    )
        self.assertEqual(out, rows)
        self.assertEqual(len(ctx["queries"]), 1)
        entry = ctx["queries"][0]
        self.assertEqual(entry["name"], "sessions")
        self.assertEqual(entry["wave"], 1)
        self.assertEqual(entry["rows"], 1)
        self.assertEqual(entry["status"], "ok")

    def test_fetch_records_empty_status_when_zero_rows_returned(self):
        with TemporaryDirectory() as t:
            with mock.patch.object(paths, "DATA_ROOT", Path(t)):
                ctx = _make_ctx(Path(t))
                with mock.patch.object(fetch_dc, "post", return_value=[]):
                    out = fetch_dc._fetch(
                        ctx, wave=1, name="sessions",
                        where="ssot__Id__c = 'x'",
                    )
        self.assertEqual(out, [])
        self.assertEqual(ctx["queries"][0]["status"], "empty")
        self.assertIn("_unavailable_reason", ctx["queries"][0])

    def test_fetch_records_join_path_when_provided(self):
        with TemporaryDirectory() as t:
            with mock.patch.object(paths, "DATA_ROOT", Path(t)):
                ctx = _make_ctx(Path(t))
                with mock.patch.object(fetch_dc, "post", return_value=[{"x": 1}]):
                    fetch_dc._fetch(
                        ctx, wave=2, name="generations",
                        where="generationId__c = 'x'",
                        join_path="Step.GenerationId__c",
                    )
        self.assertEqual(
            ctx["queries"][0]["join_path"], "Step.GenerationId__c",
        )


class FetchErrorPathTests(unittest.TestCase):

    def test_fetch_records_error_status_when_post_raises(self):
        ctx = _make_ctx(Path("/tmp"))
        with mock.patch.object(
            fetch_dc, "post", side_effect=DCQueryError("http=500 ISE\n  body"),
        ):
            out = fetch_dc._fetch(
                ctx, wave=1, name="sessions",
                where="ssot__Id__c = 'x'",
            )
        self.assertEqual(out, [])
        entry = ctx["queries"][0]
        self.assertEqual(entry["status"], "error")
        self.assertEqual(entry["rows"], 0)
        self.assertIn("http=500 ISE", entry["_unavailable_reason"])


# -----------------------------------------------------------------------------
# _fetch_empty — record-only, no HTTP
# -----------------------------------------------------------------------------


class FetchEmptyTests(unittest.TestCase):

    def test_fetch_empty_records_skipped_status_with_reason(self):
        ctx = _make_ctx(Path("/tmp"))
        # Should not call HTTP at all.
        with mock.patch.object(fetch_dc, "post") as p:
            fetch_dc._fetch_empty(
                ctx, wave=2, name="generations",
                reason="no parent ids harvested",
            )
        p.assert_not_called()
        entry = ctx["queries"][0]
        self.assertEqual(entry["name"], "generations")
        self.assertEqual(entry["status"], "skipped")
        self.assertEqual(entry["rows"], 0)
        self.assertEqual(
            entry["_unavailable_reason"], "no parent ids harvested",
        )


# -----------------------------------------------------------------------------
# _write_manifest — JSON shape on disk
# -----------------------------------------------------------------------------


class WriteManifestTests(unittest.TestCase):

    def test_writes_manifest_at_canonical_path(self):
        with TemporaryDirectory() as t:
            with mock.patch.object(paths, "DATA_ROOT", Path(t)):
                ctx = _make_ctx(Path(t))
                ctx["queries"] = [
                    {"name": "sessions", "wave": 1, "rows": 1,
                     "elapsed_ms": 50, "status": "ok"},
                ]
                ctx["session_shape"] = "complete"
                ctx["harvested_ids"] = {"interactions": [IDS.IXN_TURN]}
                fetch_dc._write_manifest(ctx)

                manifest_path = (
                    Path(t)
                    / IDS.ORG_ID_15
                    / f"{IDS.AGENT_API}__{IDS.AGENT_VERSION}"
                    / IDS.SID
                    / "dc._session_manifest.json"
                )
                self.assertTrue(manifest_path.is_file())
                manifest = json.loads(manifest_path.read_text())
            self.assertEqual(manifest["session_id"], IDS.SID)
            self.assertEqual(manifest["org_alias"], "my-org")
            self.assertEqual(manifest["org_id_15"], IDS.ORG_ID_15)
            self.assertEqual(manifest["agent_api_name"], IDS.AGENT_API)
            self.assertEqual(manifest["agent_version"], IDS.AGENT_VERSION)
            self.assertEqual(manifest["session_shape"], "complete")
            self.assertEqual(len(manifest["queries"]), 1)
            self.assertIn("started_at_utc", manifest)
            self.assertIn("finished_at_utc", manifest)
            self.assertIn("elapsed_ms", manifest)


if __name__ == "__main__":
    unittest.main()
