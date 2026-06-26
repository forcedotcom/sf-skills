"""Session discovery for investigating-agentforce-d360 — Data Cloud only.

Lets the user find candidate sessions when they don't have a session id.
Output is a numbered picker table to stdout; the skill agent asks the user
to pick one, then falls through to the existing fetch_dc.py pipeline with
the chosen UUID. Writes no artifacts.

DC-only by design (no OTel path).

## CLI

    python3 scripts/discover_sessions.py --org <alias> [options]

Options (all optional except --org):
  --since <expr>    "last 2 hours" | "last 10" | "today" | "yesterday"
                    | "YYYY-MM-DD" | "YYYY-MM-DD to YYYY-MM-DD"
                    | explicit UTC/TZ datetime (RFC 3339). Default: last 24 hours.
  --agent <name>    Agent API name (e.g. MyAgent). Adds participant JOIN.
  --channel <type>  Builder | Messaging | Voice. "Messaging" maps to
                    "SCRT2 - EmbeddedMessaging" in SQL.
  --outcome <type>  USER_ENDED | ESCALATED | TRANSFERRED | TIMEOUT | NOT_SET
  --grep <pattern>  Substring in conversation text (user input + agent output).
                    Adds interaction + message JOINs. Case-insensitive by
                    default (LOWER on both sides); pass --grep-case-sensitive
                    for exact match. `%` and `_` are escaped so they match
                    the literal char.
  --grep-case-sensitive
                    Opt-in: make --grep case-sensitive (rare; default is
                    case-insensitive because users almost always type the
                    quote in whatever case they remember it).
  --tz <IANA>       Override auto-detected local tz (e.g. America/Los_Angeles).
                    Only affects calendar-day resolution (today/yesterday/
                    bare-date/date-range); `last N` windows are anchored to
                    UTC regardless. The chosen tz is echoed in zero-row
                    output so the user can sanity-check boundaries.
  --limit <N>       Max sessions. Default 20.

Exit codes:
  0 — ≥1 session found
  2 — zero sessions (picker prints composed SQL so user can widen)
  other — DC query or arg-parse error
"""
from __future__ import annotations

import argparse
import html
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

sys.path.insert(0, str(Path(__file__).parent))

from dc import DCQueryError, load_sql, post, resolve_org
from _shared.sql import _escape_sql_literal


# ---- channel alias ---------------------------------------------------------

# Source-skill convention: users type "Messaging" but DC stores the full
# SCRT2 string. Other channels pass through as-is (Builder, Voice).
_CHANNEL_ALIAS = {
    "Messaging": "SCRT2 - EmbeddedMessaging",
}


# ---- escaping --------------------------------------------------------------
#
# `_escape_sql_literal` is imported from `_shared.sql` (single source of
# truth per its module docstring). Do NOT re-declare locally — divergence
# would break the documented contract that every DC-SQL caller shares one
# escape strategy.

_LIKE_ESCAPE = "!"  # ASCII, doesn't collide with SQL syntax, no quoting ambiguity

def _escape_like_pattern(s: str) -> str:
    """Escape SQL LIKE wildcards (`%`, `_`) and the escape char itself
    (`!`) so `--grep "100%_off"` matches the literal text, not "100
    anything-underscore-off". Quote-doubling still happens on top of this
    via _escape_sql_literal. Used with the `ESCAPE '!'` clause in the
    composed SQL.

    Backslash was avoided because `ESCAPE '\\'` in source reduces to a
    bare backslash on the wire, which some SQL parsers read as an
    unterminated string literal (\\' → escaped quote).
    """
    return (
        s.replace(_LIKE_ESCAPE, _LIKE_ESCAPE * 2)
        .replace("%", f"{_LIKE_ESCAPE}%")
        .replace("_", f"{_LIKE_ESCAPE}_")
    )


# ---- time parsing ----------------------------------------------------------

@dataclass(frozen=True)
class TimeRange:
    """Half-open UTC range [start, end). `expr` is the original user input
    so the picker header can echo back what was searched."""
    start_utc: datetime
    end_utc: datetime
    expr: str
    tz_name: str  # IANA or "UTC"

    def iso(self, dt: datetime) -> str:
        return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _autodetect_tz() -> str:
    """IANA tz from /etc/localtime symlink (macOS / most Linux). Falls
    back to the TZ env var, then UTC."""
    link = Path("/etc/localtime")
    try:
        if link.is_symlink():
            target = os.readlink(link)
            # Typically .../zoneinfo/America/Los_Angeles
            if "zoneinfo/" in target:
                return target.split("zoneinfo/", 1)[1]
    except OSError:
        pass
    return os.environ.get("TZ") or "UTC"


_RX_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")  # @rule-suppress starter-sec-002 — re.compile, not eval/exec
_RX_DATE_RANGE = re.compile(r"^(\d{4}-\d{2}-\d{2})\s+to\s+(\d{4}-\d{2}-\d{2})$")  # @rule-suppress starter-sec-002 — re.compile, not eval/exec
_RX_LAST_N = re.compile(  # @rule-suppress starter-sec-002 — re.compile, not eval/exec
    r"^last\s+(\d+)(?:\s+(hour|hours|day|days|minute|minutes))?$",
    re.IGNORECASE,
)


def parse_time_expr(expr: Optional[str], tz_name: str) -> TimeRange:
    """Parse one of the supported time expressions into a UTC half-open
    range. Default (None) is "last 24 hours" so every query has a sane
    time predicate — DC scans over the whole DMO without one are slow."""
    tz_name = tz_name or _autodetect_tz()
    try:
        local_tz = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        raise SystemExit(f"discover_sessions: unknown IANA timezone {tz_name!r}")

    now_utc = datetime.now(timezone.utc)

    if expr is None:
        return TimeRange(
            start_utc=now_utc - timedelta(hours=24),
            end_utc=now_utc,
            expr="last 24 hours (default)",
            tz_name=tz_name,
        )

    s = expr.strip()
    sl = s.lower()

    # "last N" / "last N hours" / "last N days" / "last N minutes"
    m = _RX_LAST_N.match(sl)
    if m:
        n = int(m.group(1))
        unit = (m.group(2) or "hours").lower()
        if unit in ("hour", "hours"):
            delta = timedelta(hours=n)
        elif unit in ("day", "days"):
            delta = timedelta(days=n)
        elif unit in ("minute", "minutes"):
            delta = timedelta(minutes=n)
        else:
            raise SystemExit(f"discover_sessions: unsupported time unit {unit!r}")
        return TimeRange(
            start_utc=now_utc - delta,
            end_utc=now_utc,
            expr=s,
            tz_name=tz_name,
        )

    # "today" / "yesterday" — calendar day in local tz
    if sl in ("today", "yesterday"):
        local_now = datetime.now(local_tz)
        offset_days = 0 if sl == "today" else 1
        start_local = local_now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=offset_days)
        end_local = start_local + timedelta(days=1)
        return TimeRange(
            start_utc=start_local.astimezone(timezone.utc),
            end_utc=end_local.astimezone(timezone.utc),
            expr=s,
            tz_name=tz_name,
        )

    # "YYYY-MM-DD to YYYY-MM-DD" — inclusive range in local tz
    m = _RX_DATE_RANGE.match(s)
    if m:
        start_d, end_d = m.group(1), m.group(2)
        start_local = datetime.strptime(start_d, "%Y-%m-%d").replace(tzinfo=local_tz)
        end_local = datetime.strptime(end_d, "%Y-%m-%d").replace(tzinfo=local_tz) + timedelta(days=1)
        return TimeRange(
            start_utc=start_local.astimezone(timezone.utc),
            end_utc=end_local.astimezone(timezone.utc),
            expr=s,
            tz_name=tz_name,
        )

    # Bare "YYYY-MM-DD"
    if _RX_DATE.match(s):
        start_local = datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=local_tz)
        end_local = start_local + timedelta(days=1)
        return TimeRange(
            start_utc=start_local.astimezone(timezone.utc),
            end_utc=end_local.astimezone(timezone.utc),
            expr=s,
            tz_name=tz_name,
        )

    # Try RFC 3339 single datetime — caller probably meant "since this time"
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=local_tz)
        return TimeRange(
            start_utc=dt.astimezone(timezone.utc),
            end_utc=now_utc,
            expr=f"since {s}",
            tz_name=tz_name,
        )
    except ValueError:
        pass

    raise SystemExit(
        f"discover_sessions: cannot parse --since {s!r}. "
        f"Try: `last 2 hours`, `today`, `yesterday`, `2026-04-22`, "
        f"`2026-04-22 to 2026-04-25`, or an ISO datetime."
    )


# ---- SQL composition -------------------------------------------------------

def compose_sql(
    *,
    tr: TimeRange,
    agent: Optional[str],
    channel: Optional[str],
    outcome: Optional[str],
    grep: Optional[str],
    grep_case_sensitive: bool = False,
    limit: int,
) -> str:
    """Build the discovery SQL. Conditional JOINs + WHERE ANDs are
    composed from `tr` + flag args; the SQL skeleton lives at
    `assets/dc/discover_sessions.sql`."""
    joins: list[str] = []
    wheres: list[str] = [
        f"s.ssot__StartTimestamp__c >= '{tr.iso(tr.start_utc)}'",
        f"s.ssot__StartTimestamp__c < '{tr.iso(tr.end_utc)}'",
    ]

    if agent:
        joins.append(
            "JOIN ssot__AiAgentSessionParticipant__dlm p "
            "ON s.ssot__Id__c = p.ssot__AiAgentSessionId__c"
        )
        wheres.append(f"p.ssot__AiAgentApiName__c = '{_escape_sql_literal(agent)}'")

    if grep:
        joins.append(
            "JOIN ssot__AiAgentInteraction__dlm i "
            "ON s.ssot__Id__c = i.ssot__AiAgentSessionId__c"
        )
        joins.append(
            "JOIN ssot__AiAgentInteractionMessage__dlm m "
            "ON i.ssot__Id__c = m.ssot__AiAgentInteractionId__c"
        )
        # LIKE wildcards (%, _) and the escape char (!) are neutralized so
        # `--grep "100%_off"` matches the literal substring. Quote-doubling
        # is layered on top via _escape_sql_literal. The `ESCAPE '!'` clause
        # tells SQL the escape char is `!`.
        pat = _escape_sql_literal(_escape_like_pattern(grep))
        if grep_case_sensitive:
            wheres.append(
                f"m.ssot__ContentText__c LIKE '%{pat}%' ESCAPE '{_LIKE_ESCAPE}'"
            )
        else:
            # Lowercase both sides so the predicate is case-insensitive.
            # Default behaviour — users almost always type the quoted
            # phrase in whatever case they remember, not the case the
            # agent rendered it in.
            wheres.append(
                f"LOWER(m.ssot__ContentText__c) LIKE LOWER('%{pat}%') "
                f"ESCAPE '{_LIKE_ESCAPE}'"
            )

    if channel:
        ch = _CHANNEL_ALIAS.get(channel, channel)
        wheres.append(f"s.ssot__AiAgentChannelType__c = '{_escape_sql_literal(ch)}'")

    if outcome:
        wheres.append(f"s.ssot__AiAgentSessionEndType__c = '{_escape_sql_literal(outcome)}'")

    # DISTINCT when JOINs are present — a session can JOIN multiple
    # participants / messages and explode rows.
    columns = (
        "s.ssot__Id__c, s.ssot__StartTimestamp__c, s.ssot__EndTimestamp__c, "
        "s.ssot__AiAgentChannelType__c, s.ssot__AiAgentSessionEndType__c"
    )
    select_list = f"DISTINCT {columns}" if joins else columns

    return load_sql(
        "discover_sessions",
        SELECT_LIST=select_list,
        JOINS="\n".join(joins),
        WHERE_CLAUSE=" AND ".join(wheres),
        LIMIT=str(limit),
    )


# ---- agent-name enrichment -------------------------------------------------

_NAME_NOT_SET = {"", "NOT_SET", None}


def fetch_agent_names(
    session_ids: list[str], *, instance_url: str, token: str
) -> dict[str, str]:
    """One follow-up query to grab agent names for discovered sessions.
    The discovery query itself drops agent name from the projection
    because adding it to SELECT forces a participant JOIN on every query
    (including the no-filter case) and DC penalizes that.

    Returns {session_uuid: agent_api_name}. Missing sessions → not in dict.

    No role filter on the SQL. Some agent shapes (e.g. MyAgent) leave
    AGENT-role rows with ``ssot__AiAgentApiName__c = 'NOT_SET'`` while USER-
    role rows correctly carry the agent's api_name. Filtering to ``role =
    'AGENT'`` would either return no row (picker shows '—' for a session
    that clearly has an agent) or return the literal ``'NOT_SET'`` (picker
    misleads the operator). Dropping the role filter and de-duplicating in
    Python with the dominant-agent rule (``sorted(...)[0]``) recovers both
    cases. Mirrors the fallback in ``fetch_dc._resolve_identity``.
    """
    if not session_ids:
        return {}
    quoted = ", ".join(f"'{_escape_sql_literal(sid)}'" for sid in session_ids)
    sql = (
        "SELECT ssot__AiAgentSessionId__c, ssot__AiAgentApiName__c "
        "FROM ssot__AiAgentSessionParticipant__dlm "
        f"WHERE ssot__AiAgentSessionId__c IN ({quoted})"
    )
    try:
        rows = post(sql, instance_url, token, "discover_sessions_agent_names")
    except DCQueryError:
        return {}  # non-fatal — picker shows "—" for agent
    # Group all api_names per session, drop NOT_SET sentinels, dominant-agent
    # pick (lexicographic first) to match the rule used in fetch_dc.
    # Sessions where every participant row is NOT_SET fall out of the result
    # entirely — the picker will show '—', which is more honest than
    # displaying the literal 'NOT_SET'.
    by_sid: dict[str, set[str]] = {}
    for row in rows:
        sid = row.get("ssot__AiAgentSessionId__c")
        name = row.get("ssot__AiAgentApiName__c")
        if not sid or name in _NAME_NOT_SET:
            continue
        by_sid.setdefault(sid, set()).add(name)
    return {sid: sorted(names)[0] for sid, names in by_sid.items() if names}


# ---- rendering -------------------------------------------------------------

def _fmt_duration(start_iso: Optional[str], end_iso: Optional[str]) -> str:
    """Human-readable duration (e.g. "1m 12s", "28s") from two ISO timestamps.
    Returns "—" if start_iso is missing or unparseable. When end_iso is
    None but start_iso parses, computes elapsed-from-now and appends "+"
    to signal the session is still open (or end timestamp hasn't
    materialized in DC yet)."""
    if not start_iso:
        return "—"
    try:
        start = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
    except ValueError:
        return "—"
    ongoing = False
    if not end_iso:
        end = datetime.now(timezone.utc)
        ongoing = True
    else:
        try:
            end = datetime.fromisoformat(end_iso.replace("Z", "+00:00"))
        except ValueError:
            return "—"
    seconds = int((end - start).total_seconds())
    if seconds < 0:
        return "—"
    suffix = "+" if ongoing else ""
    if seconds < 60:
        return f"{seconds}s{suffix}"
    m, s = divmod(seconds, 60)
    if m < 60:
        return (f"{m}m {s}s" if s else f"{m}m") + suffix
    h, m = divmod(m, 60)
    return f"{h}h {m}m{suffix}"


def _fmt_channel(raw: Optional[str]) -> str:
    """Compact channel label for the picker."""
    if not raw:
        return "—"
    # Reverse the Messaging alias for readability.
    if raw == "SCRT2 - EmbeddedMessaging":
        return "Messaging"
    # Custom channel labels arrive HTML-encoded from DC (e.g. "E &amp; O").
    return html.unescape(raw)


def _fmt_start(iso: Optional[str]) -> str:
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return iso
    return dt.strftime("%Y-%m-%d %H:%M:%SZ")


def render_picker(
    *,
    rows: list[dict],
    agent_by_sid: dict[str, str],
    org: str,
    tr: TimeRange,
    filters: dict[str, Optional[str]],
    composed_sql: str,
) -> str:
    """Markdown picker. Returned as a string so the caller prints once
    (single subprocess write on stdout)."""
    filter_bits = [f"{tr.expr}"]
    for k, v in filters.items():
        if v:
            filter_bits.append(f"{k}={v}")
    header_filters = " · ".join(filter_bits)

    if not rows:
        # Echo the composed SQL so the user can widen the query.
        return (
            f"No sessions matched in **{org}** ({header_filters}).\n\n"
            f"Range searched (UTC): `{tr.iso(tr.start_utc)}` → `{tr.iso(tr.end_utc)}`\n"
            f"Local tz: `{tr.tz_name}`\n\n"
            f"Composed SQL:\n```sql\n{composed_sql}\n```\n"
            f"Try widening: larger `--since`, drop `--channel`/`--outcome`, or broaden `--grep`."
        )

    lines = [
        f"Found **{len(rows)}** session{'s' if len(rows) != 1 else ''} in "
        f"**{org}** ({header_filters}):",
        "",
        "| # | UUID | Start (UTC) | Agent | Channel | Duration | Outcome |",
        "|---|------|-------------|-------|---------|----------|---------|",
    ]
    for i, row in enumerate(rows, start=1):
        uuid = row.get("ssot__Id__c") or "—"
        agent = agent_by_sid.get(uuid, "—")
        lines.append(
            f"| {i} | `{uuid}` | {_fmt_start(row.get('ssot__StartTimestamp__c'))} "
            f"| {agent} | {_fmt_channel(row.get('ssot__AiAgentChannelType__c'))} "
            f"| {_fmt_duration(row.get('ssot__StartTimestamp__c'), row.get('ssot__EndTimestamp__c'))} "
            f"| {row.get('ssot__AiAgentSessionEndType__c') or '—'} |"
        )
    lines.append("")
    lines.append(f"Pick a number (1–{len(rows)}) to trace, or paste a UUID.")
    return "\n".join(lines)


# ---- CLI -------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Find candidate Agentforce sessions via Data Cloud. "
                    "Prints a numbered picker; no artifacts written.",
    )
    ap.add_argument("--org", required=True, help="sf CLI org alias (the one you configured via `sf org login`)")
    ap.add_argument("--since", help='time range: "last 2 hours" | "today" | "yesterday" | '
                                    '"YYYY-MM-DD" | "YYYY-MM-DD to YYYY-MM-DD" | ISO datetime. '
                                    'Default: last 24 hours.')
    ap.add_argument("--agent", help="Agent API name (exact match)")
    ap.add_argument("--channel", help="Builder | Messaging | Voice (or full STDM string)")
    ap.add_argument("--outcome", help="USER_ENDED | ESCALATED | TRANSFERRED | TIMEOUT | NOT_SET")
    ap.add_argument(
        "--grep",
        help="substring in conversation text (user + agent); "
             "case-insensitive by default — pass --grep-case-sensitive for exact match",
    )
    ap.add_argument(
        "--grep-case-sensitive",
        action="store_true",
        default=False,
        help="opt-in: make --grep case-sensitive (rare; default is case-insensitive)",
    )
    ap.add_argument("--tz", help="IANA timezone override for calendar-day resolution")
    ap.add_argument("--limit", type=int, default=20, help="max sessions (default 20)")
    # Runtime-agnostic path overrides; default to ~/.vibe/...
    # discover_sessions doesn't read DATA_ROOT directly, but accepts the flags
    # for contract consistency with the other 4 d360 entry scripts.
    from _shared.cli_override import add_cli_flags, apply_overrides
    add_cli_flags(ap)
    args = ap.parse_args()
    apply_overrides(args, caller_globals=globals())

    if args.limit < 1:
        raise SystemExit("discover_sessions: --limit must be >= 1")

    tr = parse_time_expr(args.since, args.tz or "")
    sql = compose_sql(
        tr=tr,
        agent=args.agent,
        channel=args.channel,
        outcome=args.outcome,
        grep=args.grep,
        grep_case_sensitive=args.grep_case_sensitive,
        limit=args.limit,
    )

    instance_url, token = resolve_org(args.org)
    try:
        rows = post(sql, instance_url, token, "discover_sessions")
    except DCQueryError as e:
        print(f"discover_sessions: DC query failed.\n{e}", file=sys.stderr)
        return 1

    agent_by_sid: dict[str, str] = {}
    if rows:
        sids = [r["ssot__Id__c"] for r in rows if r.get("ssot__Id__c")]
        agent_by_sid = fetch_agent_names(sids, instance_url=instance_url, token=token)

    filters = {
        "agent": args.agent,
        "channel": args.channel,
        "outcome": args.outcome,
        "grep": args.grep,
        # Only surface the case-sensitive note when --grep is in play AND
        # the user opted into exact match — the default (insensitive) is
        # the boring path and shouldn't clutter the picker header.
        "grep_case_sensitive": "yes" if (args.grep and args.grep_case_sensitive) else None,
    }
    print(render_picker(
        rows=rows,
        agent_by_sid=agent_by_sid,
        org=args.org,
        tr=tr,
        filters=filters,
        composed_sql=sql,
    ))
    return 0 if rows else 2


if __name__ == "__main__":
    raise SystemExit(main())
