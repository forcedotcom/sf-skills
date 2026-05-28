"""Regression guard for §16d — case-insensitive ``--grep`` default.

§16d flipped the default behaviour of ``--grep`` from case-sensitive
exact match to case-insensitive (``LOWER(...) LIKE LOWER(...)``).
Operators almost always type the quoted phrase in whatever case they
remember, not the case the agent rendered it in — the old default
silently dropped legitimate matches.

The compose_sql shape is already pinned in
``test_discover_sessions.py`` (LOWER wrap on default, bypass on opt-in,
escape semantics). What this file pins down is the
**argparse → filters dict → picker header** pipeline — the integration
seams where a refactor could:

  - flip the argparse default back to ``True`` (forgot ``default=False``)
  - drop the ``grep_case_sensitive`` key from the filters dict (header
    no longer warns the operator that the picker is in opt-in mode)
  - surface ``grep_case_sensitive`` even when ``--grep`` isn't set
    (false signal in the header for unrelated runs)
"""
from __future__ import annotations

import argparse
import unittest
from unittest import mock

from . import _bootstrap  # noqa: F401  — sys.path setup

import discover_sessions  # type: ignore


class GrepCaseSensitiveArgparseDefaultTests(unittest.TestCase):
    """The argparse flag must default to ``False`` so case-insensitive
    is the path of least resistance."""

    def _build_parser(self) -> argparse.ArgumentParser:
        # Re-export the parser the same way main() does — we don't have
        # a parser factory, so spy on the module-level ``argparse`` to
        # capture the parser before main() invokes parse_args().
        captured: dict[str, argparse.ArgumentParser] = {}
        real_parse_args = argparse.ArgumentParser.parse_args

        def capture(self, *a, **kw):  # type: ignore[no-redef]
            captured["parser"] = self
            # Stop main() before it calls anything network-y.
            raise SystemExit(0)

        with mock.patch.object(argparse.ArgumentParser, "parse_args", capture):
            with mock.patch.object(
                discover_sessions.sys, "argv",
                ["discover_sessions.py", "--org", "x"],
            ):
                with self.assertRaises(SystemExit):
                    discover_sessions.main()
        # Restore (the patch.object exit already did this, but be explicit
        # in case something held onto the bound method.)
        argparse.ArgumentParser.parse_args = real_parse_args
        return captured["parser"]

    def test_grep_case_sensitive_default_is_false(self):
        # parse_args without --grep-case-sensitive must return False.
        parser = self._build_parser()
        ns = parser.parse_args(["--org", "x"])
        self.assertFalse(ns.grep_case_sensitive,
                         "default flipped — case-insensitive was the §16d "
                         "decision; flipping default=False back to True "
                         "regresses to the pre-§16d behaviour")

    def test_grep_case_sensitive_opt_in_via_flag(self):
        # Pass the flag explicitly — must be True.
        parser = self._build_parser()
        ns = parser.parse_args(["--org", "x", "--grep-case-sensitive"])
        self.assertTrue(ns.grep_case_sensitive)


class FiltersDictSurfacesCaseSensitiveTests(unittest.TestCase):
    """The filters dict feeds render_picker's header. Without a marker,
    the operator can't tell whether their grep is in case-insensitive
    (default) or case-sensitive (opt-in) mode — a silent footgun when
    a query returns zero rows in opt-in mode by accident."""

    def _run_main_and_capture_filters(self, *extra_argv: str) -> dict:
        # Stub resolve_org + post so main() doesn't talk to DC, then
        # intercept render_picker to capture the filters dict main()
        # constructed.
        captured: dict[str, dict] = {}

        def fake_render(*, filters, **_kw):
            captured["filters"] = filters
            return "ok"

        argv = ["discover_sessions.py", "--org", "x", *extra_argv]
        with mock.patch.object(discover_sessions.sys, "argv", argv), \
             mock.patch.object(
                 discover_sessions, "resolve_org",
                 return_value=("https://x", "T"),
             ), \
             mock.patch.object(
                 discover_sessions, "post",
                 return_value=[{
                     "ssot__Id__c": "sid1",
                     "ssot__StartTimestamp__c": "2026-04-22T00:00:00Z",
                     "ssot__EndTimestamp__c": "2026-04-22T00:01:00Z",
                     "ssot__AiAgentChannelType__c": "Builder",
                     "ssot__AiAgentSessionEndType__c": "USER_ENDED",
                 }],
             ), \
             mock.patch.object(
                 discover_sessions, "render_picker",
                 side_effect=fake_render,
             ):
            discover_sessions.main()
        return captured["filters"]

    def test_filters_omit_case_sensitive_when_grep_unset(self):
        # No --grep at all: surfacing case-sensitive=yes in the header
        # would be a meaningless artifact (there's no grep to be
        # case-sensitive about). Contract: the value is None so
        # render_picker's `if v:` filter drops the bit.
        filters = self._run_main_and_capture_filters()
        self.assertIsNone(filters["grep_case_sensitive"])

    def test_filters_omit_case_sensitive_when_grep_set_but_default(self):
        # --grep set, --grep-case-sensitive NOT set: default mode is
        # case-insensitive. Don't surface the marker — the absence is
        # the default and surfacing "yes/no" on every grep would just
        # add noise to the picker header.
        filters = self._run_main_and_capture_filters("--grep", "refund")
        self.assertEqual(filters["grep"], "refund")
        self.assertIsNone(filters["grep_case_sensitive"])

    def test_filters_surface_case_sensitive_only_when_both_set(self):
        # The interesting case: operator opted in. The header MUST tell
        # them, otherwise a zero-row return looks identical to a
        # case-insensitive zero-row return.
        filters = self._run_main_and_capture_filters(
            "--grep", "Refund", "--grep-case-sensitive",
        )
        self.assertEqual(filters["grep"], "Refund")
        self.assertEqual(filters["grep_case_sensitive"], "yes")


class RenderPickerHeaderShowsCaseSensitiveTests(unittest.TestCase):
    """End-to-end: when filters dict surfaces ``grep_case_sensitive``,
    render_picker must include it in the header."""

    def _row(self) -> dict:
        return {
            "ssot__Id__c": "sid1",
            "ssot__StartTimestamp__c": "2026-04-22T10:00:00Z",
            "ssot__EndTimestamp__c": "2026-04-22T10:00:30Z",
            "ssot__AiAgentChannelType__c": "Builder",
            "ssot__AiAgentSessionEndType__c": "USER_ENDED",
        }

    def _tr(self) -> "discover_sessions.TimeRange":
        from datetime import datetime, timezone
        return discover_sessions.TimeRange(
            start_utc=datetime(2026, 4, 22, 0, 0, 0, tzinfo=timezone.utc),
            end_utc=datetime(2026, 4, 22, 23, 0, 0, tzinfo=timezone.utc),
            expr="test", tz_name="UTC",
        )

    def test_header_includes_case_sensitive_bit_when_set(self):
        out = discover_sessions.render_picker(
            rows=[self._row()], agent_by_sid={}, org="my-org",
            tr=self._tr(),
            filters={
                "agent": None, "channel": None, "outcome": None,
                "grep": "Refund", "grep_case_sensitive": "yes",
            },
            composed_sql="",
        )
        self.assertIn("grep=Refund", out)
        self.assertIn("grep_case_sensitive=yes", out)

    def test_header_omits_case_sensitive_bit_in_default_mode(self):
        # Default-mode grep (no opt-in): the bit must NOT appear.
        out = discover_sessions.render_picker(
            rows=[self._row()], agent_by_sid={}, org="my-org",
            tr=self._tr(),
            filters={
                "agent": None, "channel": None, "outcome": None,
                "grep": "refund", "grep_case_sensitive": None,
            },
            composed_sql="",
        )
        self.assertIn("grep=refund", out)
        self.assertNotIn("grep_case_sensitive", out)


if __name__ == "__main__":
    unittest.main()
