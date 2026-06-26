"""Tests for ``assemble_dc`` pure helpers — independent of disk fixtures.

Complements ``test_assemble_dc_gateway_direct.py`` (binding chain) by
hitting the small, mechanical helpers that bridge raw DC rows and the
assembled tree:

- ``_clean``           NOT_SET sentinel collapse
- ``_harvest_str``     unescape + quote-strip + UNSET_VALUE
- ``_ts``              ISO-8601 → datetime; NOT_SET / non-string → None
- ``_index_unique``    PK dedup with first-write-wins + collision record
- ``_groupby``         group rows by FK, dropping NOT_SET keys
- ``_extract_trace_id`` primary col with HTML-escaped fallback
- ``_tier``            ACTION < TOPIC < GUARDRAIL < other
- ``_window_contains`` half-open / closed timestamp interval semantics
- ``_load``            disk read with malformed-json tolerance
"""
from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from . import _bootstrap  # noqa: F401  — sys.path setup

import assemble_dc  # type: ignore


# -----------------------------------------------------------------------------
# _clean — NOT_SET → None
# -----------------------------------------------------------------------------


class CleanTests(unittest.TestCase):

    def test_not_set_token_returns_none(self):
        self.assertIsNone(assemble_dc._clean("NOT_SET"))

    def test_empty_string_returns_none(self):
        self.assertIsNone(assemble_dc._clean(""))

    def test_actual_value_passes_through(self):
        self.assertEqual(assemble_dc._clean("real value"), "real value")
        self.assertEqual(assemble_dc._clean(42), 42)


# -----------------------------------------------------------------------------
# _harvest_str — unescape + quote-strip + UNSET_VALUE collapse
# -----------------------------------------------------------------------------


class HarvestStrTests(unittest.TestCase):

    def test_none_returns_none(self):
        self.assertIsNone(assemble_dc._harvest_str(None))

    def test_unescapes_html_entities(self):
        self.assertEqual(
            assemble_dc._harvest_str("&quot;0Xx000&quot;"),
            "0Xx000",
        )

    def test_strips_outer_double_quotes(self):
        self.assertEqual(assemble_dc._harvest_str('"value"'), "value")

    def test_unset_value_collapses_to_none(self):
        self.assertIsNone(assemble_dc._harvest_str("UNSET_VALUE"))

    def test_not_set_collapses_to_none(self):
        self.assertIsNone(assemble_dc._harvest_str("NOT_SET"))

    def test_empty_string_collapses_to_none(self):
        self.assertIsNone(assemble_dc._harvest_str(""))


# -----------------------------------------------------------------------------
# _ts — ISO-8601 timestamp parsing
# -----------------------------------------------------------------------------


class TsTests(unittest.TestCase):

    def test_parses_iso_z_timestamp(self):
        out = assemble_dc._ts("2026-04-22T10:00:00Z")
        self.assertEqual(out, datetime(2026, 4, 22, 10, 0, 0, tzinfo=timezone.utc))

    def test_parses_iso_offset_timestamp(self):
        out = assemble_dc._ts("2026-04-22T10:00:00+00:00")
        self.assertEqual(out, datetime(2026, 4, 22, 10, 0, 0, tzinfo=timezone.utc))

    def test_returns_none_for_non_string(self):
        self.assertIsNone(assemble_dc._ts(None))
        self.assertIsNone(assemble_dc._ts(12345))

    def test_returns_none_for_not_set(self):
        self.assertIsNone(assemble_dc._ts("NOT_SET"))
        self.assertIsNone(assemble_dc._ts(""))

    def test_returns_none_for_unparseable(self):
        self.assertIsNone(assemble_dc._ts("not-a-timestamp"))


# -----------------------------------------------------------------------------
# _index_unique
# -----------------------------------------------------------------------------


class IndexUniqueTests(unittest.TestCase):

    def test_builds_dict_keyed_by_field(self):
        rows = [{"id": "a", "v": 1}, {"id": "b", "v": 2}]
        out = assemble_dc._index_unique(rows, "id", [], dmo_label="t")
        self.assertEqual(set(out.keys()), {"a", "b"})

    def test_first_write_wins_on_collision(self):
        rows = [{"id": "a", "v": 1}, {"id": "a", "v": 2}]
        collisions: list[dict] = []
        out = assemble_dc._index_unique(rows, "id", collisions, dmo_label="dmo1")
        self.assertEqual(out["a"]["v"], 1)
        self.assertEqual(len(collisions), 1)
        self.assertEqual(collisions[0]["dmo"], "dmo1")
        self.assertEqual(collisions[0]["key"], "a")

    def test_skips_NOT_SET_keys(self):
        rows = [{"id": "NOT_SET", "v": 1}, {"id": "", "v": 2}, {"id": "a", "v": 3}]
        out = assemble_dc._index_unique(rows, "id", [], dmo_label="t")
        self.assertEqual(set(out.keys()), {"a"})


# -----------------------------------------------------------------------------
# _groupby
# -----------------------------------------------------------------------------


class GroupbyTests(unittest.TestCase):

    def test_groups_rows_by_key(self):
        rows = [{"k": "a", "v": 1}, {"k": "b", "v": 2}, {"k": "a", "v": 3}]
        out = assemble_dc._groupby(rows, "k")
        self.assertEqual([r["v"] for r in out["a"]], [1, 3])
        self.assertEqual([r["v"] for r in out["b"]], [2])

    def test_skips_NOT_SET_keys(self):
        rows = [{"k": "a", "v": 1}, {"k": "NOT_SET", "v": 2}]
        out = assemble_dc._groupby(rows, "k")
        self.assertNotIn("NOT_SET", out)
        self.assertIn("a", out)


# -----------------------------------------------------------------------------
# _extract_trace_id
# -----------------------------------------------------------------------------


class ExtractTraceIdTests(unittest.TestCase):

    def test_uses_primary_column_when_populated(self):
        out = assemble_dc._extract_trace_id({"ssot__TelemetryTraceId__c": "abc"})
        self.assertEqual(out, "abc")

    def test_falls_back_to_html_escaped_attribute_text(self):
        out = assemble_dc._extract_trace_id({
            "ssot__TelemetryTraceId__c": "",
            "ssot__AttributeText__c": '&quot;internalTraceId&quot;:&quot;deadbeef&quot;',
        })
        self.assertEqual(out, "deadbeef")

    def test_returns_none_when_no_trace_id_anywhere(self):
        out = assemble_dc._extract_trace_id({
            "ssot__TelemetryTraceId__c": "",
            "ssot__AttributeText__c": "no trace here",
        })
        self.assertIsNone(out)

    def test_returns_none_for_NOT_SET(self):
        out = assemble_dc._extract_trace_id({
            "ssot__TelemetryTraceId__c": "NOT_SET",
            "ssot__AttributeText__c": "",
        })
        self.assertIsNone(out)


# -----------------------------------------------------------------------------
# _tier — ACTION < TOPIC < GUARDRAIL < other
# -----------------------------------------------------------------------------


class TierTests(unittest.TestCase):

    def test_action_step_is_lowest_tier(self):
        self.assertLess(
            assemble_dc._tier("ACTION_STEP"),
            assemble_dc._tier("TOPIC_STEP"),
        )

    def test_topic_step_outranks_guardrails(self):
        self.assertLess(
            assemble_dc._tier("TOPIC_STEP"),
            assemble_dc._tier("TRUST_GUARDRAILS_STEP"),
        )

    def test_unknown_step_type_falls_to_end(self):
        self.assertEqual(
            assemble_dc._tier("MYSTERY"),
            len(assemble_dc._TIER_ORDER),
        )


# -----------------------------------------------------------------------------
# _window_contains
# -----------------------------------------------------------------------------


class WindowContainsTests(unittest.TestCase):

    def _ts(self, h, m, s):
        return datetime(2026, 4, 22, h, m, s, tzinfo=timezone.utc)

    def test_in_range_inclusive_of_start_and_end(self):
        gw = self._ts(10, 0, 5)
        self.assertTrue(
            assemble_dc._window_contains(gw, self._ts(10, 0, 0), self._ts(10, 0, 10))
        )

    def test_open_ended_when_end_is_none(self):
        gw = self._ts(11, 0, 0)
        self.assertTrue(
            assemble_dc._window_contains(gw, self._ts(10, 0, 0), None)
        )

    def test_returns_false_when_start_is_none(self):
        gw = self._ts(10, 0, 0)
        self.assertFalse(
            assemble_dc._window_contains(gw, None, self._ts(11, 0, 0))
        )

    def test_returns_false_when_before_start(self):
        gw = self._ts(9, 0, 0)
        self.assertFalse(
            assemble_dc._window_contains(gw, self._ts(10, 0, 0), self._ts(11, 0, 0))
        )

    def test_returns_false_when_after_end(self):
        gw = self._ts(12, 0, 0)
        self.assertFalse(
            assemble_dc._window_contains(gw, self._ts(10, 0, 0), self._ts(11, 0, 0))
        )


# -----------------------------------------------------------------------------
# _load — disk read with tolerance
# -----------------------------------------------------------------------------


class LoadTests(unittest.TestCase):

    def test_returns_empty_list_when_file_missing(self):
        with TemporaryDirectory() as t:
            warnings: list[str] = []
            self.assertEqual(
                assemble_dc._load(Path(t), "missing", warnings), []
            )
            # Missing file is normal — no warning recorded.
            self.assertEqual(warnings, [])

    def test_returns_loaded_rows_when_file_valid(self):
        with TemporaryDirectory() as t:
            tmp = Path(t)
            (tmp / "dc.sessions.json").write_text(json.dumps([{"a": 1}, {"a": 2}]))
            warnings: list[str] = []
            out = assemble_dc._load(tmp, "sessions", warnings)
            self.assertEqual(out, [{"a": 1}, {"a": 2}])
            self.assertEqual(warnings, [])

    def test_returns_empty_list_and_records_warning_on_malformed_json(self):
        with TemporaryDirectory() as t:
            tmp = Path(t)
            (tmp / "dc.broken.json").write_text("<<<not json>>>")
            warnings: list[str] = []
            out = assemble_dc._load(tmp, "broken", warnings)
            self.assertEqual(out, [])
            self.assertEqual(warnings, ["broken"])


if __name__ == "__main__":
    unittest.main()
