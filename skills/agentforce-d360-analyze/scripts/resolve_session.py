"""Resolve either an AI-agent session UUID or a Messaging session id (0Mw...)
to the canonical AI-agent session UUID that the rest of the skill uses.

## Why this exists

`ssot__AIAgentSession__dlm.ssot__RelatedMessagingSessionId__c` stores the
Service Cloud `MessagingSession.Id` (18-char Salesforce id, prefix `0Mw`).
Users often only have that messaging id on hand, not the AI-agent session
UUID (`019dface-0000-7000-8000-000000000002`). This resolver lets every
entry point in the skill accept either form — it normalises to the UUID,
and artifacts continue to land under `DATA_ROOT/<uuid>/` as before.

## Many-to-one is real

Live-verified on an internal test org: 7 distinct messaging ids map to
multiple agent sessions; one id mapped to 5 separate agent sessions.
"Most recent by start_ts" is NOT a safe default for disambiguation —
the user could legitimately want any of them. On multi-match we list
every candidate and exit non-zero; the user re-invokes with the
specific UUID.

## Two resolution modes

1. **Live** — query DC. Requires `--org`. Used by `fetch_dc.py` at the
   top of the pipeline (before any artifacts exist on disk).
2. **Disk-first** — scan `DATA_ROOT/*/dc.sessions.json` for a row whose
   `ssot__RelatedMessagingSessionId__c` matches. No DC call, no `--org`
   needed. Used by `assemble_dc.py` and `render_dc.py`. If the session
   has never been fetched, returns None and the caller errors with a
   pointer to `fetch_dc.py`.

## CLI

    python3 scripts/resolve_session.py --id <uuid|msg_id> --org <alias>

Prints the resolved UUID to stdout on single-match (or pass-through).
Non-zero exit with diagnostics on zero-match and multi-match.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).parent))

from config import DATA_ROOT
from dc import load_sql, post, resolve_org


# NOT_SET sentinel set. Matches fetch_dc.py:41; keep in sync.
_NOT_SET = {"", "NOT_SET", None}


def is_messaging_id(s: str) -> bool:
    """Shape check for a Salesforce MessagingSession id. The official key
    prefix is `0Mw`; the id is 15 or 18 chars. UUIDs are 36 chars with
    dashes, so they can't accidentally match."""
    if not s:
        return False
    return s.startswith("0Mw") and len(s) in (15, 18)


# ---- live resolution (queries Data Cloud) --------------------------------

def _live_lookup(msg_id: str, org: str) -> List[dict]:
    """Query ssot__AIAgentSession__dlm for rows where RelatedMessagingSessionId
    matches `msg_id`. Returns raw row dicts (caller decides how to handle
    N=0, N=1, N>1).

    SQL comes from `assets/dc/messaging_session.sql` — same templating
    convention as every other DMO query in this skill. The `MSG_ID`
    placeholder is interpolated as a literal string, but the caller
    guarantees (via is_messaging_id) that the value is a Salesforce
    MessagingSession id: exact 15/18 chars, `0Mw` key prefix. No quote,
    no wildcard, no semicolon can pass that shape check.
    """
    if not is_messaging_id(msg_id):
        raise ValueError(
            f"_live_lookup: msg_id {msg_id!r} failed is_messaging_id() shape check"
        )
    instance_url, token = resolve_org(org)
    sql = load_sql("messaging_session", MSG_ID=msg_id)
    return post(sql, instance_url, token, "resolve_session")


def _format_multi_match(msg_id: str, rows: List[dict]) -> str:
    """Human-readable error for the N>1 case. Lists every candidate so
    the user can pick and re-invoke."""
    lines = [
        f"resolve_session: messaging id {msg_id!r} matches {len(rows)} "
        f"ssot__AIAgentSession__dlm rows — pick one and re-invoke with its UUID:",
        "",
    ]
    for r in rows:
        uuid = r.get("ssot__Id__c")
        start = r.get("ssot__StartTimestamp__c") or "—"
        end = r.get("ssot__EndTimestamp__c") or "—"
        end_type = r.get("ssot__AiAgentSessionEndType__c") or "—"
        channel = r.get("ssot__AiAgentChannelType__c") or "—"
        lines.append(
            f"  {uuid}  start={start}  end={end}  end_type={end_type}  channel={channel}"
        )
    lines.append("")
    lines.append(
        f"Example: python3 scripts/fetch_dc.py --session {rows[0].get('ssot__Id__c')} --org <alias>"
    )
    return "\n".join(lines)


def resolve(sid_or_msg: str, *, org: str) -> str:
    """Resolve an AI-agent session UUID from either form (live DC query).
    Exits the process on zero- and multi-match with a diagnostic message.
    Pass-through for UUID input."""
    if not is_messaging_id(sid_or_msg):
        return sid_or_msg  # already a UUID (or unknown form — let caller fail)
    rows = _live_lookup(sid_or_msg, org)
    if len(rows) == 0:
        raise SystemExit(
            f"resolve_session: no ssot__AIAgentSession__dlm row with "
            f"RelatedMessagingSessionId={sid_or_msg!r} in org {org!r}"
        )
    if len(rows) > 1:
        raise SystemExit(_format_multi_match(sid_or_msg, rows))
    return rows[0]["ssot__Id__c"]


# ---- disk-first resolution (no DC call) ----------------------------------

def resolve_from_disk(sid_or_msg: str) -> Optional[str]:
    """For scripts that don't have `--org` wired up. Scans every
    ``dc.sessions.json`` under ``DATA_ROOT`` for a row whose
    ``ssot__RelatedMessagingSessionId__c`` matches ``sid_or_msg``. Returns
    the UUID (from the matching row's ``ssot__Id__c``) or None if not found.

    Layout: the nested scheme is ``DATA_ROOT/<org_id15>/<agent>__<ver>/<uuid>/
    dc.sessions.json``. Historic flat runs (``DATA_ROOT/<uuid>/...``) are
    picked up by the same ``rglob`` walk, so this resolver works across
    both layouts without caller awareness.

    Archive suffix: user-created duplicate dirs named like
    ``<uuid> - archive 1/`` carry stale copies of the same rows and would
    otherwise trigger spurious multi-match exits. They are skipped at
    scan time.

    Pass-through if input is already a UUID; returns input unchanged
    regardless of disk presence (caller validates with its own load-
    artifact check).
    """
    if not is_messaging_id(sid_or_msg):
        return sid_or_msg  # UUID — pass through (caller validates disk presence)

    matches: List[str] = []  # uuids
    if not DATA_ROOT.is_dir():
        return None
    # Nested layout is 4-deep (<org>/<agent>/<uuid>/dc.sessions.json), flat
    # is 2-deep (<uuid>/dc.sessions.json). rglob handles both without a
    # hard-coded depth.
    for sessions_p in sorted(DATA_ROOT.rglob("dc.sessions.json")):
        if not sessions_p.is_file():
            continue
        # Skip `<uuid> - archive N/` duplicate dirs — they hold stale copies
        # of the same rows and would produce spurious multi-match exits.
        if " - archive" in sessions_p.parent.name:
            continue
        try:
            data = json.loads(sessions_p.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        # `dc.sessions.json` is a list of rows (the skill saves raw DC rows).
        if not isinstance(data, list):
            continue
        for row in data:
            row_msg = (row.get("ssot__RelatedMessagingSessionId__c") or "").strip()
            if row_msg in _NOT_SET:
                continue
            if row_msg == sid_or_msg:
                uuid = row.get("ssot__Id__c")
                if uuid:
                    matches.append(uuid)
    if not matches:
        return None
    # De-duplicate across multiple dc.sessions.json files that happen to
    # contain the same row (possible if a user copies artifacts between
    # agent dirs). Distinct UUIDs remain a multi-match.
    unique = sorted(set(matches))
    if len(unique) > 1:
        raise SystemExit(
            f"resolve_session: messaging id {sid_or_msg!r} matches {len(unique)} "
            f"session directories on disk — pick a UUID and re-invoke:\n  "
            + "\n  ".join(unique)
        )
    return unique[0]


def resolve_disk_or_live(sid_or_msg: str, org: Optional[str] = None) -> str:
    """Combined path used by entry points that support both. Tries disk
    first (cheap); falls back to live DC only if `org` is supplied.
    Raises with a useful message if disk-miss and no org."""
    if not is_messaging_id(sid_or_msg):
        return sid_or_msg  # UUID — no resolution needed
    disk = resolve_from_disk(sid_or_msg)
    if disk is not None:
        return disk
    if org is None:
        raise SystemExit(
            f"resolve_session: cannot resolve messaging id {sid_or_msg!r} from "
            f"disk (no dc.sessions.json under DATA_ROOT has a matching "
            f"RelatedMessagingSessionId). Run `python3 scripts/fetch_dc.py "
            f"--session {sid_or_msg} --org <alias>` first, or re-invoke with "
            f"the AI-agent session UUID directly."
        )
    return resolve(sid_or_msg, org=org)


# ---- CLI -----------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Resolve a Salesforce messaging session id (0Mw...) to the "
                    "AI-agent session UUID the skill uses. Passes UUID input through unchanged."
    )
    ap.add_argument("--id", required=True,
                    help="Either the AI-agent session UUID or the MessagingSession id (0Mw...)")
    ap.add_argument("--org", help="sf org alias (required for live DC lookup when input is 0Mw...)")
    ap.add_argument("--disk-only", action="store_true",
                    help="Only scan DATA_ROOT/*/dc.sessions.json; no DC query")
    # Runtime-agnostic path overrides; default to ~/.vibe/...
    from _shared.cli_override import add_cli_flags, apply_overrides
    add_cli_flags(ap)
    args = ap.parse_args()
    apply_overrides(args, caller_globals=globals())

    if not is_messaging_id(args.id):
        print(args.id)
        return 0
    if args.disk_only:
        found = resolve_from_disk(args.id)
        if found is None:
            print(f"resolve_session: no local session dir matches {args.id!r}", file=sys.stderr)
            return 1
        print(found)
        return 0
    if not args.org:
        # Try disk first as a convenience; only error if that also misses.
        disk = resolve_from_disk(args.id)
        if disk is not None:
            print(disk)
            return 0
        print(
            f"resolve_session: {args.id!r} not found on disk; --org <alias> required "
            f"for a live DC lookup",
            file=sys.stderr,
        )
        return 2
    uuid = resolve(args.id, org=args.org)
    print(uuid)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
