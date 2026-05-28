"""Tests for ``fetch_dc`` helpers + DC-access-denied flow.

Complements ``test_fetch_dc_identity.py`` (which targets ``_resolve_identity``
specifically). This file lifts coverage of the other public helpers:

- ``DcAccessDenied``                   exception carrier
- ``preflight_dc_access``              401/403 classification + happy path
- ``_emit_dc_access_denied_preamble``  headless JSON shape
- ``_handle_dc_access_denied``         interactive (tty) vs headless branches
- ``_in_list``                          SQL IN-fragment helper (dedup + NOT_SET filter)
- ``_extract_trace_ids``                runtime trace-id extraction (DMO + HTML-escaped)
- ``_preflight_templates``              SQL template existence check

All subprocess + DC-access boundaries are mocked.
"""
from __future__ import annotations

import io
import json
import unittest
from unittest import mock

from . import _bootstrap  # noqa: F401  — sys.path setup

import fetch_dc  # type: ignore
from dc import DCQueryError  # type: ignore


# -----------------------------------------------------------------------------
# DcAccessDenied — small carrier
# -----------------------------------------------------------------------------


class DcAccessDeniedTests(unittest.TestCase):

    def test_str_includes_reason_and_detail(self):
        e = fetch_dc.DcAccessDenied("401", "Unauthorized")
        self.assertEqual(e.reason, "401")
        self.assertEqual(e.detail, "Unauthorized")
        self.assertIn("401: Unauthorized", str(e))


# -----------------------------------------------------------------------------
# preflight_dc_access — classify HTTP error code
# -----------------------------------------------------------------------------


class PreflightDcAccessTests(unittest.TestCase):

    def test_returns_url_and_token_on_success(self):
        with mock.patch.object(
            fetch_dc, "resolve_org",
            return_value=("https://example.salesforce.com", "TOKEN"),
        ):
            with mock.patch.object(fetch_dc, "post", return_value=[]):
                url, token = fetch_dc.preflight_dc_access("sid", "my-org")
        self.assertEqual(url, "https://example.salesforce.com")
        self.assertEqual(token, "TOKEN")

    def test_raises_dc_access_denied_on_401(self):
        with mock.patch.object(
            fetch_dc, "resolve_org",
            return_value=("https://x", "T"),
        ):
            with mock.patch.object(
                fetch_dc, "post",
                side_effect=DCQueryError("http=401 Unauthorized"),
            ):
                with self.assertRaises(fetch_dc.DcAccessDenied) as ctx:
                    fetch_dc.preflight_dc_access("sid", "my-org")
        self.assertEqual(ctx.exception.reason, "401")

    def test_raises_dc_access_denied_on_403(self):
        with mock.patch.object(
            fetch_dc, "resolve_org",
            return_value=("https://x", "T"),
        ):
            with mock.patch.object(
                fetch_dc, "post",
                side_effect=DCQueryError("http=403 Forbidden"),
            ):
                with self.assertRaises(fetch_dc.DcAccessDenied) as ctx:
                    fetch_dc.preflight_dc_access("sid", "my-org")
        self.assertEqual(ctx.exception.reason, "403")

    def test_raises_dc_access_denied_on_other_dc_error(self):
        with mock.patch.object(
            fetch_dc, "resolve_org",
            return_value=("https://x", "T"),
        ):
            with mock.patch.object(
                fetch_dc, "post",
                side_effect=DCQueryError("http=500 ISE"),
            ):
                with self.assertRaises(fetch_dc.DcAccessDenied) as ctx:
                    fetch_dc.preflight_dc_access("sid", "my-org")
        # 5xx falls into the catch-all dc_probe_failed bucket.
        self.assertEqual(ctx.exception.reason, "dc_probe_failed")


# -----------------------------------------------------------------------------
# _emit_dc_access_denied_preamble — JSON shape
# -----------------------------------------------------------------------------


class EmitPreambleTests(unittest.TestCase):

    def test_emits_single_line_json_with_two_options(self):
        buf = io.StringIO()
        with mock.patch("sys.stdout", buf):
            fetch_dc._emit_dc_access_denied_preamble("401", "Unauthorized")
        printed = buf.getvalue().strip()
        # One single-line JSON record
        self.assertEqual(printed.count("\n"), 0)
        payload = json.loads(printed)
        self.assertEqual(payload["status"], "DC_ACCESS_DENIED")
        self.assertEqual(payload["reason"], "401")
        self.assertEqual(payload["detail"], "Unauthorized")
        # Standalone d360 has retry + cancel only — no sibling-skill switch.
        self.assertEqual(len(payload["options"]), 2)
        codes = [o["code"] for o in payload["options"]]
        self.assertEqual(codes, ["1", "2"])
        actions = [o["action"] for o in payload["options"]]
        self.assertEqual(actions, ["retry", "cancel"])


# -----------------------------------------------------------------------------
# _handle_dc_access_denied — branches on tty vs not, + interactive choices
# -----------------------------------------------------------------------------


class HandleDcAccessDeniedTests(unittest.TestCase):

    def _exc(self) -> fetch_dc.DcAccessDenied:
        return fetch_dc.DcAccessDenied("401", "Unauthorized")

    def test_headless_emits_preamble_and_returns_exit_code(self):
        with mock.patch.object(
            fetch_dc, "_emit_dc_access_denied_preamble"
        ) as emit:
            rc = fetch_dc._handle_dc_access_denied(
                self._exc(), session_id="sid", is_tty=False,
            )
        emit.assert_called_once_with("401", "Unauthorized")
        self.assertEqual(rc, fetch_dc.EXIT_DC_ACCESS_DENIED)

    def test_interactive_choice_1_returns_exit_code(self):
        # User picks "1" → caller signaled to retry.
        with mock.patch.object(fetch_dc.sys, "stdin", io.StringIO("1\n")):
            with mock.patch.object(fetch_dc, "_log"):
                rc = fetch_dc._handle_dc_access_denied(
                    self._exc(), session_id="sid", is_tty=True,
                )
        self.assertEqual(rc, fetch_dc.EXIT_DC_ACCESS_DENIED)

    def test_interactive_choice_2_returns_zero_cancel(self):
        # Standalone d360: choice "2" is cancel (no sibling-skill switch).
        with mock.patch.object(fetch_dc.sys, "stdin", io.StringIO("2\n")):
            with mock.patch.object(fetch_dc, "_log"):
                rc = fetch_dc._handle_dc_access_denied(
                    self._exc(), session_id="sid", is_tty=True,
                )
        self.assertEqual(rc, 0)

    def test_interactive_unknown_choice_treated_as_cancel(self):
        # "" / "9" / random → cancel.
        with mock.patch.object(fetch_dc.sys, "stdin", io.StringIO("\n")):
            with mock.patch.object(fetch_dc, "_log"):
                rc = fetch_dc._handle_dc_access_denied(
                    self._exc(), session_id="sid", is_tty=True,
                )
        self.assertEqual(rc, 0)

    def test_interactive_keyboard_interrupt_returns_zero(self):
        # stdin.readline() raising KeyboardInterrupt → graceful 0.
        fake_stdin = mock.MagicMock()
        fake_stdin.readline.side_effect = KeyboardInterrupt
        with mock.patch.object(fetch_dc.sys, "stdin", fake_stdin):
            with mock.patch.object(fetch_dc, "_log"):
                rc = fetch_dc._handle_dc_access_denied(
                    self._exc(), session_id="sid", is_tty=True,
                )
        self.assertEqual(rc, 0)


# -----------------------------------------------------------------------------
# _in_list — SQL IN-clause fragment builder
# -----------------------------------------------------------------------------


class InListTests(unittest.TestCase):

    def test_renders_quoted_csv_inside_parens(self):
        self.assertEqual(fetch_dc._in_list(["a", "b", "c"]), "('a','b','c')")

    def test_dedups_and_preserves_first_occurrence_order(self):
        self.assertEqual(
            fetch_dc._in_list(["a", "b", "a", "c", "b"]), "('a','b','c')"
        )

    def test_drops_empty_string(self):
        self.assertEqual(fetch_dc._in_list(["a", "", "b"]), "('a','b')")

    def test_drops_NOT_SET_token(self):
        self.assertEqual(
            fetch_dc._in_list(["a", "NOT_SET", "b"]), "('a','b')"
        )

    def test_empty_input_returns_empty_parens(self):
        # All inputs filtered → "()". SQL won't accept this but that's the
        # caller's concern — the helper itself is mechanical.
        self.assertEqual(fetch_dc._in_list([]), "()")
        self.assertEqual(fetch_dc._in_list(["", "NOT_SET"]), "()")


# -----------------------------------------------------------------------------
# _extract_trace_ids — DMO field + HTML-escaped fallback
# -----------------------------------------------------------------------------


class ExtractTraceIdsTests(unittest.TestCase):

    def test_uses_telemetry_trace_id_when_populated(self):
        rows = [{"ssot__TelemetryTraceId__c": "abc123"}]
        self.assertEqual(fetch_dc._extract_trace_ids(rows), ["abc123"])

    def test_falls_back_to_attribute_text_internalTraceId(self):
        # Simulate the HTML-escaped JSON-in-a-string shape DC stores.
        rows = [{
            "ssot__TelemetryTraceId__c": "",
            "ssot__AttributeText__c": '&quot;internalTraceId&quot;:&quot;deadbeef&quot;',
        }]
        self.assertEqual(fetch_dc._extract_trace_ids(rows), ["deadbeef"])

    def test_dedupes_preserving_first_occurrence(self):
        rows = [
            {"ssot__TelemetryTraceId__c": "x"},
            {"ssot__TelemetryTraceId__c": "y"},
            {"ssot__TelemetryTraceId__c": "x"},
        ]
        self.assertEqual(fetch_dc._extract_trace_ids(rows), ["x", "y"])

    def test_drops_NOT_SET_token(self):
        rows = [{"ssot__TelemetryTraceId__c": "NOT_SET"}]
        self.assertEqual(fetch_dc._extract_trace_ids(rows), [])

    def test_returns_empty_when_no_trace_id_anywhere(self):
        rows = [{"ssot__TelemetryTraceId__c": "", "ssot__AttributeText__c": ""}]
        self.assertEqual(fetch_dc._extract_trace_ids(rows), [])


# -----------------------------------------------------------------------------
# _preflight_templates — SQL templates exist on disk
# -----------------------------------------------------------------------------


class PreflightTemplatesTests(unittest.TestCase):

    def test_succeeds_when_all_templates_present(self):
        # All the production .sql files ship in assets/dc/. This call should
        # complete cleanly under the in-tree install.
        fetch_dc._preflight_templates()  # raises if any missing


if __name__ == "__main__":
    unittest.main()
