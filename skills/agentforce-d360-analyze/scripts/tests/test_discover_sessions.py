"""Tests for ``discover_sessions`` — DC-only session picker.

Covers:
- ``parse_time_expr``     pure str → TimeRange (12 supported expressions)
- ``compose_sql``         pure args → SQL string (conditional JOINs / WHEREs)
- ``fetch_agent_names``   DC follow-up call (mocks ``post``)
- ``render_picker``       pure rows → markdown
- ``main``                argv → exit code (mocks ``resolve_org`` + ``post``)
"""
from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

from . import _bootstrap  # noqa: F401  — sys.path setup

import discover_sessions  # type: ignore
from dc import DCQueryError  # type: ignore


# -----------------------------------------------------------------------------
# parse_time_expr — pure
# -----------------------------------------------------------------------------


class ParseTimeExprTests(unittest.TestCase):

    def test_default_none_returns_last_24_hours(self):
        tr = discover_sessions.parse_time_expr(None, "UTC")
        delta = tr.end_utc - tr.start_utc
        self.assertEqual(delta, timedelta(hours=24))
        self.assertIn("default", tr.expr)

    def test_last_n_hours(self):
        tr = discover_sessions.parse_time_expr("last 2 hours", "UTC")
        self.assertEqual(tr.end_utc - tr.start_utc, timedelta(hours=2))
        self.assertEqual(tr.expr, "last 2 hours")

    def test_last_n_minutes(self):
        tr = discover_sessions.parse_time_expr("last 30 minutes", "UTC")
        self.assertEqual(tr.end_utc - tr.start_utc, timedelta(minutes=30))

    def test_last_n_days(self):
        tr = discover_sessions.parse_time_expr("last 3 days", "UTC")
        self.assertEqual(tr.end_utc - tr.start_utc, timedelta(days=3))

    def test_last_n_bare_defaults_to_hours(self):
        # Spec: "last 10" is ambiguous; the regex treats unit-less as hours.
        tr = discover_sessions.parse_time_expr("last 10", "UTC")
        self.assertEqual(tr.end_utc - tr.start_utc, timedelta(hours=10))

    def test_today_uses_local_tz_calendar_day(self):
        tr = discover_sessions.parse_time_expr("today", "UTC")
        # End - start should be exactly 24 hours.
        self.assertEqual(tr.end_utc - tr.start_utc, timedelta(days=1))

    def test_yesterday_window_precedes_today(self):
        today = discover_sessions.parse_time_expr("today", "UTC")
        yest = discover_sessions.parse_time_expr("yesterday", "UTC")
        self.assertEqual(yest.end_utc, today.start_utc)
        self.assertEqual(yest.end_utc - yest.start_utc, timedelta(days=1))

    def test_bare_iso_date(self):
        tr = discover_sessions.parse_time_expr("2026-04-22", "UTC")
        self.assertEqual(tr.end_utc - tr.start_utc, timedelta(days=1))
        self.assertEqual(tr.start_utc.year, 2026)
        self.assertEqual(tr.start_utc.month, 4)
        self.assertEqual(tr.start_utc.day, 22)

    def test_iso_date_range_inclusive(self):
        # "2026-04-22 to 2026-04-25" → 4 calendar days (22, 23, 24, 25).
        tr = discover_sessions.parse_time_expr("2026-04-22 to 2026-04-25", "UTC")
        self.assertEqual(tr.end_utc - tr.start_utc, timedelta(days=4))

    def test_explicit_iso_datetime(self):
        tr = discover_sessions.parse_time_expr(
            "2026-04-22T10:00:00Z", "UTC"
        )
        self.assertEqual(tr.start_utc.year, 2026)
        self.assertIn("since", tr.expr)

    def test_unparseable_expression_raises(self):
        with self.assertRaises(SystemExit) as ctx:
            discover_sessions.parse_time_expr("nope", "UTC")
        self.assertIn("cannot parse", str(ctx.exception))

    def test_unknown_tz_raises(self):
        with self.assertRaises(SystemExit) as ctx:
            discover_sessions.parse_time_expr("today", "Mars/Olympus")
        self.assertIn("unknown IANA timezone", str(ctx.exception))


# -----------------------------------------------------------------------------
# compose_sql — pure
# -----------------------------------------------------------------------------


def _basic_tr() -> discover_sessions.TimeRange:
    return discover_sessions.TimeRange(
        start_utc=datetime(2026, 4, 22, 0, 0, 0, tzinfo=timezone.utc),
        end_utc=datetime(2026, 4, 22, 23, 0, 0, tzinfo=timezone.utc),
        expr="test", tz_name="UTC",
    )


class ComposeSqlTests(unittest.TestCase):

    def test_no_filters_skips_joins_and_uses_no_distinct(self):
        sql = discover_sessions.compose_sql(
            tr=_basic_tr(), agent=None, channel=None,
            outcome=None, grep=None, limit=20,
        )
        # Strip SQL comments so the JOIN/DISTINCT mentions in the template
        # docblock don't fool the naive substring check.
        executable = "\n".join(
            line for line in sql.splitlines() if not line.strip().startswith("--")
        )
        self.assertNotIn("JOIN ", executable)
        self.assertNotIn("DISTINCT", executable)
        self.assertIn("ssot__StartTimestamp__c >= '2026-04-22T00:00:00.000Z'", executable)
        self.assertIn("ssot__StartTimestamp__c < '2026-04-22T23:00:00.000Z'", executable)

    def test_agent_filter_adds_participant_join(self):
        sql = discover_sessions.compose_sql(
            tr=_basic_tr(), agent="MyAgent", channel=None,
            outcome=None, grep=None, limit=20,
        )
        self.assertIn("ssot__AiAgentSessionParticipant__dlm", sql)
        self.assertIn("p.ssot__AiAgentApiName__c = 'MyAgent'", sql)
        self.assertIn("DISTINCT", sql)

    def test_messaging_channel_maps_to_scrt2_string(self):
        sql = discover_sessions.compose_sql(
            tr=_basic_tr(), agent=None, channel="Messaging",
            outcome=None, grep=None, limit=20,
        )
        self.assertIn("'SCRT2 - EmbeddedMessaging'", sql)

    def test_unknown_channel_passes_through(self):
        sql = discover_sessions.compose_sql(
            tr=_basic_tr(), agent=None, channel="Custom_Channel",
            outcome=None, grep=None, limit=20,
        )
        self.assertIn("'Custom_Channel'", sql)

    def test_outcome_filter_added(self):
        sql = discover_sessions.compose_sql(
            tr=_basic_tr(), agent=None, channel=None,
            outcome="ESCALATED", grep=None, limit=20,
        )
        self.assertIn("ssot__AiAgentSessionEndType__c = 'ESCALATED'", sql)

    def test_grep_adds_interaction_message_joins(self):
        # Default --grep is case-insensitive (§16d) — both sides are
        # wrapped in LOWER(...). The case-sensitive variant is covered
        # by test_grep_case_sensitive_opt_in below.
        sql = discover_sessions.compose_sql(
            tr=_basic_tr(), agent=None, channel=None,
            outcome=None, grep="refund", limit=20,
        )
        self.assertIn("ssot__AiAgentInteraction__dlm", sql)
        self.assertIn("ssot__AiAgentInteractionMessage__dlm", sql)
        self.assertIn("LOWER(m.ssot__ContentText__c) LIKE LOWER('%refund%')", sql)
        self.assertIn("ESCAPE '!'", sql)

    def test_grep_case_sensitive_opt_in(self):
        # --grep-case-sensitive bypasses the LOWER() wrap — restores the
        # exact-match shape for the rare user who wants it.
        sql = discover_sessions.compose_sql(
            tr=_basic_tr(), agent=None, channel=None,
            outcome=None, grep="Refund", grep_case_sensitive=True, limit=20,
        )
        self.assertIn("m.ssot__ContentText__c LIKE '%Refund%'", sql)
        self.assertNotIn("LOWER(", sql)
        self.assertIn("ESCAPE '!'", sql)

    def test_grep_escapes_like_wildcards(self):
        sql = discover_sessions.compose_sql(
            tr=_basic_tr(), agent=None, channel=None,
            outcome=None, grep="100%_off", limit=20,
        )
        # Both `%` and `_` get the `!` escape prefix
        self.assertIn("100!%!_off", sql)

    def test_grep_escapes_single_quotes(self):
        sql = discover_sessions.compose_sql(
            tr=_basic_tr(), agent=None, channel=None,
            outcome=None, grep="O'Brien", limit=20,
        )
        # Single quote doubled per SQL escaping rule
        self.assertIn("O''Brien", sql)

    def test_limit_substituted(self):
        sql = discover_sessions.compose_sql(
            tr=_basic_tr(), agent=None, channel=None,
            outcome=None, grep=None, limit=42,
        )
        self.assertIn("42", sql)


# -----------------------------------------------------------------------------
# fetch_agent_names — mocks dc.post
# -----------------------------------------------------------------------------


class FetchAgentNamesTests(unittest.TestCase):

    def test_empty_session_ids_returns_empty_dict_no_post(self):
        with mock.patch.object(discover_sessions, "post") as p:
            out = discover_sessions.fetch_agent_names(
                [], instance_url="https://x", token="t",
            )
        self.assertEqual(out, {})
        p.assert_not_called()

    def test_returns_dict_keyed_by_session_id(self):
        with mock.patch.object(discover_sessions, "post") as p:
            p.return_value = [
                {
                    "ssot__AiAgentSessionId__c": "sid1",
                    "ssot__AiAgentApiName__c": "AgentA",
                },
                {
                    "ssot__AiAgentSessionId__c": "sid2",
                    "ssot__AiAgentApiName__c": "AgentB",
                },
            ]
            out = discover_sessions.fetch_agent_names(
                ["sid1", "sid2"], instance_url="https://x", token="t",
            )
        self.assertEqual(out, {"sid1": "AgentA", "sid2": "AgentB"})

    def test_skips_rows_with_empty_agent_name(self):
        with mock.patch.object(discover_sessions, "post") as p:
            p.return_value = [
                {"ssot__AiAgentSessionId__c": "sid1", "ssot__AiAgentApiName__c": ""},
                {"ssot__AiAgentSessionId__c": "sid2", "ssot__AiAgentApiName__c": "AgentB"},
            ]
            out = discover_sessions.fetch_agent_names(
                ["sid1", "sid2"], instance_url="https://x", token="t",
            )
        self.assertEqual(out, {"sid2": "AgentB"})

    def test_dcqueryerror_returns_empty_dict_non_fatal(self):
        with mock.patch.object(discover_sessions, "post") as p:
            p.side_effect = DCQueryError("boom")
            out = discover_sessions.fetch_agent_names(
                ["sid1"], instance_url="https://x", token="t",
            )
        self.assertEqual(out, {})

    def test_uses_user_row_name_when_agent_row_is_not_set(self):
        # MyAgent-shape session: AGENT row carries 'NOT_SET',
        # USER row carries the real api_name. Old code filtered to
        # role=AGENT and would return 'NOT_SET' (or nothing). New code
        # is role-agnostic and recovers the api_name from the USER row.
        with mock.patch.object(discover_sessions, "post") as p:
            p.return_value = [
                {"ssot__AiAgentSessionId__c": "sid1", "ssot__AiAgentApiName__c": "NOT_SET"},
                {"ssot__AiAgentSessionId__c": "sid1", "ssot__AiAgentApiName__c": "MyAgent"},
            ]
            out = discover_sessions.fetch_agent_names(
                ["sid1"], instance_url="https://x", token="t",
            )
        self.assertEqual(out, {"sid1": "MyAgent"})

    def test_drops_session_when_every_row_is_not_set(self):
        # No usable api_name anywhere — picker should show '—' for the
        # session, which is more honest than displaying the literal
        # 'NOT_SET' string. Implementation contract: missing key in dict.
        with mock.patch.object(discover_sessions, "post") as p:
            p.return_value = [
                {"ssot__AiAgentSessionId__c": "sid1", "ssot__AiAgentApiName__c": "NOT_SET"},
                {"ssot__AiAgentSessionId__c": "sid1", "ssot__AiAgentApiName__c": ""},
                {"ssot__AiAgentSessionId__c": "sid1", "ssot__AiAgentApiName__c": None},
            ]
            out = discover_sessions.fetch_agent_names(
                ["sid1"], instance_url="https://x", token="t",
            )
        self.assertNotIn("sid1", out)
        self.assertEqual(out, {})

    def test_picks_lexicographic_first_on_handoff_session(self):
        # Multi-agent handoff: two distinct AGENT api_names appear on
        # different rows for the same session. Dominant-agent rule
        # (sorted(...)[0]) matches the policy used by fetch_dc — every
        # writer agrees on the session's namesake.
        with mock.patch.object(discover_sessions, "post") as p:
            p.return_value = [
                {"ssot__AiAgentSessionId__c": "sid1", "ssot__AiAgentApiName__c": "ZAgent"},
                {"ssot__AiAgentSessionId__c": "sid1", "ssot__AiAgentApiName__c": "AAgent"},
            ]
            out = discover_sessions.fetch_agent_names(
                ["sid1"], instance_url="https://x", token="t",
            )
        self.assertEqual(out, {"sid1": "AAgent"})

    def test_sql_does_not_filter_by_role(self):
        # Lock the no-role-filter contract — if a future "tighten this
        # back up" refactor re-adds the AGENT filter, MyAgent
        # sessions silently regress to '—' or 'NOT_SET' in the picker.
        captured = {}

        def fake_post(sql, *_a, **_k):
            captured["sql"] = sql
            return []

        with mock.patch.object(discover_sessions, "post", side_effect=fake_post):
            discover_sessions.fetch_agent_names(
                ["sid1"], instance_url="https://x", token="t",
            )
        self.assertNotIn("AiAgentSessionParticipantRole", captured["sql"])
        self.assertNotIn("'AGENT'", captured["sql"])


# -----------------------------------------------------------------------------
# render_picker — pure
# -----------------------------------------------------------------------------


def _picker_filters(**overrides) -> dict:
    base = {"agent": None, "channel": None, "outcome": None, "grep": None}
    base.update(overrides)
    return base


class RenderPickerTests(unittest.TestCase):

    def test_zero_rows_emits_widen_hint_with_composed_sql(self):
        out = discover_sessions.render_picker(
            rows=[], agent_by_sid={}, org="my-org",
            tr=_basic_tr(), filters=_picker_filters(),
            composed_sql="SELECT 1",
        )
        self.assertIn("No sessions matched", out)
        self.assertIn("```sql\nSELECT 1\n```", out)
        self.assertIn("Try widening", out)

    def test_renders_markdown_table_with_one_row(self):
        rows = [{
            "ssot__Id__c": "019dface-0000-7000-8000-000000000001",
            "ssot__StartTimestamp__c": "2026-04-22T10:00:00Z",
            "ssot__EndTimestamp__c": "2026-04-22T10:01:30Z",
            "ssot__AiAgentChannelType__c": "SCRT2 - EmbeddedMessaging",
            "ssot__AiAgentSessionEndType__c": "USER_ENDED",
        }]
        out = discover_sessions.render_picker(
            rows=rows, agent_by_sid={"019dface-0000-7000-8000-000000000001": "AgentA"},
            org="my-org", tr=_basic_tr(),
            filters=_picker_filters(), composed_sql="",
        )
        self.assertIn("Found **1** session", out)
        self.assertIn("`019dface-0000-7000-8000-000000000001`", out)
        self.assertIn("AgentA", out)
        # Reverse-aliased channel
        self.assertIn("Messaging", out)
        # Duration formatter
        self.assertIn("1m 30s", out)
        self.assertIn("USER_ENDED", out)

    def test_handles_session_without_known_agent_with_dash(self):
        rows = [{
            "ssot__Id__c": "sid1",
            "ssot__StartTimestamp__c": "2026-04-22T10:00:00Z",
            "ssot__EndTimestamp__c": "2026-04-22T10:00:30Z",
            "ssot__AiAgentChannelType__c": "Builder",
            "ssot__AiAgentSessionEndType__c": None,
        }]
        out = discover_sessions.render_picker(
            rows=rows, agent_by_sid={}, org="my-org",
            tr=_basic_tr(), filters=_picker_filters(), composed_sql="",
        )
        self.assertIn("| — |", out)  # agent + outcome both render as "—"
        self.assertIn("30s", out)

    def test_filter_bits_appear_in_header(self):
        rows = [{
            "ssot__Id__c": "sid1",
            "ssot__StartTimestamp__c": "2026-04-22T10:00:00Z",
            "ssot__EndTimestamp__c": "2026-04-22T10:00:30Z",
            "ssot__AiAgentChannelType__c": "Builder",
            "ssot__AiAgentSessionEndType__c": "ESCALATED",
        }]
        out = discover_sessions.render_picker(
            rows=rows, agent_by_sid={}, org="my-org", tr=_basic_tr(),
            filters=_picker_filters(agent="MyAgent", outcome="ESCALATED"),
            composed_sql="",
        )
        self.assertIn("agent=MyAgent", out)
        self.assertIn("outcome=ESCALATED", out)


# -----------------------------------------------------------------------------
# main — argv-driven exit codes
# -----------------------------------------------------------------------------


class MainTests(unittest.TestCase):

    def _argv(self, *extra: str) -> list[str]:
        # `--org` is required; everything else has a default or is optional.
        return ["discover_sessions.py", "--org", "my-org", *extra]

    def test_main_exit_zero_when_rows_returned(self):
        with mock.patch.object(discover_sessions.sys, "argv", self._argv()):
            with mock.patch.object(
                discover_sessions, "resolve_org",
                return_value=("https://example.salesforce.com", "TOKEN"),
            ):
                with mock.patch.object(
                    discover_sessions, "post",
                    return_value=[{
                        "ssot__Id__c": "sid1",
                        "ssot__StartTimestamp__c": "2026-04-22T00:00:00Z",
                        "ssot__EndTimestamp__c": "2026-04-22T00:01:00Z",
                        "ssot__AiAgentChannelType__c": "Builder",
                        "ssot__AiAgentSessionEndType__c": "USER_ENDED",
                    }],
                ):
                    rc = discover_sessions.main()
        self.assertEqual(rc, 0)

    def test_main_exit_two_when_zero_rows(self):
        with mock.patch.object(discover_sessions.sys, "argv", self._argv()):
            with mock.patch.object(
                discover_sessions, "resolve_org",
                return_value=("https://x", "T"),
            ):
                with mock.patch.object(discover_sessions, "post", return_value=[]):
                    rc = discover_sessions.main()
        self.assertEqual(rc, 2)

    def test_main_exit_one_when_dc_query_fails(self):
        with mock.patch.object(discover_sessions.sys, "argv", self._argv()):
            with mock.patch.object(
                discover_sessions, "resolve_org",
                return_value=("https://x", "T"),
            ):
                with mock.patch.object(
                    discover_sessions, "post",
                    side_effect=DCQueryError("HTTP 500"),
                ):
                    rc = discover_sessions.main()
        self.assertEqual(rc, 1)

    def test_main_rejects_zero_or_negative_limit(self):
        with mock.patch.object(
            discover_sessions.sys, "argv",
            self._argv("--limit", "0"),
        ):
            with self.assertRaises(SystemExit) as ctx:
                discover_sessions.main()
        self.assertIn("--limit must be >= 1", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
