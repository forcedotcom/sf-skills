"""Tests for ``render_dc`` pure-function helpers.

The renderer is large (863 stmts); covering its end-to-end markdown
output requires a complex tree fixture. These tests target the small,
pure helpers — they're cheap to test and account for ~150 stmts of the
gap.
"""
from __future__ import annotations

import unittest
from datetime import datetime, timezone

from . import _bootstrap  # noqa: F401  — sys.path setup

import render_dc  # type: ignore


# -----------------------------------------------------------------------------
# _parse_iso
# -----------------------------------------------------------------------------


class ParseIsoTests(unittest.TestCase):

    def test_returns_none_for_falsy_input(self):
        self.assertIsNone(render_dc._parse_iso(None))
        self.assertIsNone(render_dc._parse_iso(""))

    def test_parses_z_terminated(self):
        self.assertEqual(
            render_dc._parse_iso("2026-04-22T10:00:00Z"),
            datetime(2026, 4, 22, 10, 0, 0, tzinfo=timezone.utc),
        )

    def test_returns_none_for_unparseable(self):
        self.assertIsNone(render_dc._parse_iso("not-a-timestamp"))


# -----------------------------------------------------------------------------
# _fmt_offset
# -----------------------------------------------------------------------------


class FmtOffsetTests(unittest.TestCase):

    def test_returns_dash_when_timestamp_or_start_missing(self):
        anchor = datetime(2026, 4, 22, 10, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(render_dc._fmt_offset(None, anchor), "—")
        self.assertEqual(render_dc._fmt_offset("2026-04-22T10:00:00Z", None), "—")

    def test_formats_offset_with_3_decimals(self):
        anchor = datetime(2026, 4, 22, 10, 0, 0, tzinfo=timezone.utc)
        out = render_dc._fmt_offset("2026-04-22T10:00:01.234Z", anchor)
        self.assertEqual(out, "+1.234s")


# -----------------------------------------------------------------------------
# _fmt_duration_ms
# -----------------------------------------------------------------------------


class FmtDurationMsTests(unittest.TestCase):

    def test_dash_when_either_side_missing(self):
        self.assertEqual(render_dc._fmt_duration_ms(None, "2026-04-22T10:00:00Z"), "—")
        self.assertEqual(render_dc._fmt_duration_ms("2026-04-22T10:00:00Z", None), "—")

    def test_returns_int_ms_with_unit(self):
        out = render_dc._fmt_duration_ms(
            "2026-04-22T10:00:00.000Z", "2026-04-22T10:00:00.123Z",
        )
        self.assertEqual(out, "123ms")


# -----------------------------------------------------------------------------
# _decode + _truncate
# -----------------------------------------------------------------------------


class DecodeTruncateTests(unittest.TestCase):

    def test_decode_unescapes_html_and_collapses_newlines(self):
        self.assertEqual(render_dc._decode("&quot;hi&quot;\nthere"), '"hi" there')

    def test_decode_returns_empty_for_falsy(self):
        self.assertEqual(render_dc._decode(None), "")
        self.assertEqual(render_dc._decode(""), "")

    def test_truncate_pads_with_ellipsis_when_over_n(self):
        long = "a" * 100
        out = render_dc._truncate(long, n=10)
        self.assertEqual(len(out), 10)
        self.assertTrue(out.endswith("…"))

    def test_truncate_returns_input_when_under_or_equal_n(self):
        self.assertEqual(render_dc._truncate("short", n=10), "short")

    def test_truncate_returns_dash_for_falsy(self):
        self.assertEqual(render_dc._truncate(None), "—")
        self.assertEqual(render_dc._truncate(""), "—")


# -----------------------------------------------------------------------------
# _short
# -----------------------------------------------------------------------------


class ShortTests(unittest.TestCase):

    def test_returns_dash_for_falsy(self):
        self.assertEqual(render_dc._short(None), "—")
        self.assertEqual(render_dc._short(""), "—")

    def test_truncates_long_uuid_with_ellipsis(self):
        out = render_dc._short("019dface-0000-7000-8000-000000000001", keep=8)
        self.assertEqual(out, "019dface…")

    def test_returns_input_when_short(self):
        self.assertEqual(render_dc._short("abc"), "abc")


# -----------------------------------------------------------------------------
# _fmt_total_duration — h / m / s rollover
# -----------------------------------------------------------------------------


class FmtTotalDurationTests(unittest.TestCase):

    def test_returns_none_when_either_side_missing(self):
        self.assertIsNone(render_dc._fmt_total_duration(None, "2026-04-22T10:00:00Z"))

    def test_seconds_only(self):
        self.assertEqual(
            render_dc._fmt_total_duration(
                "2026-04-22T10:00:00.000Z", "2026-04-22T10:00:42.500Z",
            ),
            "42.500s",
        )

    def test_minutes_and_seconds(self):
        self.assertEqual(
            render_dc._fmt_total_duration(
                "2026-04-22T10:00:00Z", "2026-04-22T10:02:30Z",
            ),
            "2m 30.000s",
        )

    def test_hours_minutes_seconds(self):
        out = render_dc._fmt_total_duration(
            "2026-04-22T10:00:00Z", "2026-04-22T11:30:45Z",
        )
        self.assertEqual(out, "1h 30m 45.000s")


# -----------------------------------------------------------------------------
# _derive_session_end
# -----------------------------------------------------------------------------


class DeriveSessionEndTests(unittest.TestCase):

    def test_returns_session_end_ts_verbatim_when_present(self):
        end, source = render_dc._derive_session_end(
            {"end_ts": "2026-04-22T11:00:00Z", "interactions": []},
        )
        self.assertEqual(end, "2026-04-22T11:00:00Z")
        self.assertIsNone(source)

    def test_uses_session_end_interaction_start_ts(self):
        sess = {
            "end_ts": None,
            "interactions": [
                {"type": "TURN", "start_ts": "10:00", "end_ts": "10:01"},
                {"type": "SESSION_END", "start_ts": "11:00:00Z"},
            ],
        }
        end, source = render_dc._derive_session_end(sess)
        self.assertEqual(end, "11:00:00Z")
        self.assertEqual(source, "from SESSION_END interaction")

    def test_falls_back_to_last_turn_end_ts(self):
        sess = {
            "end_ts": None,
            "interactions": [
                {"type": "TURN", "start_ts": "10:00", "end_ts": "10:01"},
                {"type": "TURN", "start_ts": "10:02", "end_ts": "10:03"},
            ],
        }
        end, source = render_dc._derive_session_end(sess)
        self.assertEqual(end, "10:03")
        self.assertEqual(source, "session still open (last TURN)")

    def test_returns_none_pair_when_no_data(self):
        end, source = render_dc._derive_session_end({"interactions": []})
        self.assertIsNone(end)
        self.assertIsNone(source)


# -----------------------------------------------------------------------------
# _compose_agent_cell
# -----------------------------------------------------------------------------


class ComposeAgentCellTests(unittest.TestCase):

    def test_full_identity_concatenated(self):
        out = render_dc._compose_agent_cell({
            "agent_api_name": "MyAgent",
            "agent_version": "v3",
            "agent_label": "My Agent",
            "agent_type": "Internal",
        })
        self.assertEqual(out, "MyAgent v3 — My Agent (Internal)")

    def test_only_api_name(self):
        out = render_dc._compose_agent_cell({"agent_api_name": "MyAgent"})
        self.assertEqual(out, "MyAgent")

    def test_only_label(self):
        out = render_dc._compose_agent_cell({"agent_label": "Display Only"})
        self.assertEqual(out, "Display Only")

    def test_returns_none_for_empty_identity(self):
        self.assertIsNone(render_dc._compose_agent_cell({}))


# -----------------------------------------------------------------------------
# _section_session_bootstrap — channel-aware NOT_SET wording
# -----------------------------------------------------------------------------


class SectionSessionBootstrapNotSetWordingTests(unittest.TestCase):
    """`VariableText__c == NOT_SET` is a "no bootstrap variables" signal,
    not a messaging-channel signal. Several non-messaging shapes (E&O
    headless API, Atlas planner, generic API/integration) legitimately
    produce NOT_SET — the rendered line must not call those "production
    messaging path".
    """

    def _identity_with_no_bootstrap(self) -> dict:
        # Sentinel: bootstrap_variables key is present and explicitly None
        # (the assembler stamps None when VariableText__c is NOT_SET).
        return {"bootstrap_variables": None}

    def test_messaging_channel_keeps_messaging_path_addendum(self):
        out = "\n".join(render_dc._section_session_bootstrap(
            self._identity_with_no_bootstrap(),
            channel="SCRT2 - EmbeddedMessaging",
        ))
        self.assertIn("no bootstrap variables", out)
        self.assertIn("production messaging path", out)
        # Alias.
        out2 = "\n".join(render_dc._section_session_bootstrap(
            self._identity_with_no_bootstrap(),
            channel="Messaging",
        ))
        self.assertIn("production messaging path", out2)

    def test_non_messaging_channel_omits_messaging_path(self):
        # E&O is the wheelz that surfaced this bug — Atlas-planner
        # session on the "E & O" channel was being mislabeled
        # "production messaging path".
        out = "\n".join(render_dc._section_session_bootstrap(
            self._identity_with_no_bootstrap(),
            channel="E & O",
        ))
        self.assertIn("no bootstrap variables", out)
        self.assertNotIn("production messaging path", out)
        self.assertNotIn("messaging", out.lower())

    def test_null_channel_uses_neutral_wording(self):
        # No channel info at all — must not assume messaging.
        out = "\n".join(render_dc._section_session_bootstrap(
            self._identity_with_no_bootstrap(),
            channel=None,
        ))
        self.assertIn("no bootstrap variables", out)
        self.assertNotIn("production messaging path", out)

    def test_default_channel_kwarg_is_neutral(self):
        # Backward-compat: callers that don't pass channel get the
        # neutral wording, never the messaging-path label.
        out = "\n".join(render_dc._section_session_bootstrap(
            self._identity_with_no_bootstrap(),
        ))
        self.assertIn("no bootstrap variables", out)
        self.assertNotIn("production messaging path", out)


if __name__ == "__main__":
    unittest.main()
