"""Fetch all 24 Data Cloud artifacts for one Agentforce session.

Given a session UUID and an `sf` org alias, this CLI drives the waterfall
of DC queries defined in `assets/dc/*.sql`, lands each result under the
nested layout:

    DATA_ROOT/<org_id_15>/<agent_api_name>__<agent_version>/<sid>/dc.<name>.json

…via `storage.save`, and emits a `dc._session_manifest.json` summarizing
counts, timings, and empty-by-design reasons.

Design contract:
  - SQL loaded via `dc.load_sql(name, **params)` only — no inline concat.
  - Responses parsed via `dc.parse(response)` — no inline dict digging.
  - Persistence via `storage.save(data, org, agent, ver, sid, "dc", name)`
    — no direct writes. Every on-disk path is validated by
    ``paths.session_dir`` before it's touched.
  - Identity is resolved BEFORE the first write. The sessions + participants
    queries run first so (org_id_15, agent_api_name, agent_version) can be
    derived; those three segments name the session dir.
  - Every output file is written exactly once; empty artifacts go through
    `_fetch_empty(name, reason)` so the manifest records why.
  - Rerunning the same session overwrites prior artifacts.

Invocation:
    python3 scripts/fetch_dc.py --session <uuid> --org <alias> [--verbose]

After the waterfall finishes, the fetcher chains two downstream steps:
  1. assemble_dc.main_for_session → dc._session_tree.json
     (skip with --no-assemble).
  2. render_dc.main_for_session → dc._session_summary.md
     (skip with --no-render). Runs against the on-disk tree from step 1
     or a prior run.

## DC-access preflight

Before the waterfall starts, we run a single cheap probe:

    SELECT Id FROM ssot__AIAgentSession__dlm WHERE ssot__Id__c = '<esc_sid>' LIMIT 1

If the probe fails (401/403, no org alias, resolve_org failure), we raise
``DcAccessDenied`` and the top-level ``main()`` branches on
``sys.stdin.isatty()``:

  - Interactive (tty): print a 2-option menu, read one line from stdin.
    (1) retry with a different --org  (2) cancel.
  - Headless (no tty): emit a single-line JSON preamble to stdout and
    ``exit(10)`` immediately. Orchestrators (subagents, CI, ``claude -p``)
    see ``exit(10)`` as the stable contract for "DC access denied".

``exit(10)`` is the stable contract between this skill and any orchestrator
wrapper — a non-zero exit code that is distinct from generic errors.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import DATA_ROOT, paths, sql as _sql_mod
from dc import SQL_DIR, DCQueryError, load_sql, post, resolve_org
from storage import save


# ---- preflight / exit contracts -------------------------------------------

# Exit code reserved for "DC access denied".
# Orchestrators grep for this specifically. See module docstring for the full
# contract; do not reuse for other failure modes.
EXIT_DC_ACCESS_DENIED = 10


class DcAccessDenied(RuntimeError):
    """DC probe failed in a way that tells us DC is unusable for this session.

    Carries both a short machine-readable ``reason`` (for the JSON preamble
    payload — e.g. ``"401"``, ``"no_org"``, ``"resolve_org_failed"``) and a
    longer human-readable ``detail`` (surfaced in the interactive prompt).
    """

    def __init__(self, reason: str, detail: str) -> None:
        self.reason = reason
        self.detail = detail
        super().__init__(f"{reason}: {detail}")


def preflight_dc_access(
    session_id: str,
    org_alias: str,
) -> tuple[str, str]:
    """Probe DC for this session. Returns (instance_url, token) on success.

    Runs the cheapest possible DC query — a single ``LIMIT 1`` against
    ``ssot__AIAgentSession__dlm`` — to establish that:
      - ``sf`` CLI can resolve the org alias to an instance URL + token.
      - DC accepts the token (no 401/403).
      - The session id is well-formed SOQL (no literal injection).

    Raises ``DcAccessDenied`` on failure. The ``session_id`` is escaped
    via ``sql._escape_sql_literal`` before being interpolated, matching
    the Batch-C defense for ``_session_row_live``. The probe does NOT
    require the session to exist — a zero-row response is success
    (proves DC is reachable and auth'd).
    """
    # Stage 1: resolve org alias → instance_url + token. Any failure here
    # is classified as "no_org" / "resolve_org_failed" — we never got far
    # enough to hit DC.
    try:
        instance_url, token = resolve_org(org_alias)
    except SystemExit as e:
        raise DcAccessDenied("no_org", str(e)) from e

    # Stage 2: issue the probe. Reuse ``sessions`` template with a narrow
    # WHERE clause + LIMIT 1. The escape hardens against injection at the
    # literal interpolation point.
    esc_sid = _sql_mod._escape_sql_literal(session_id)
    probe_sql = (
        f"SELECT ssot__Id__c FROM ssot__AIAgentSession__dlm "
        f"WHERE ssot__Id__c = '{esc_sid}' LIMIT 1"
    )
    try:
        post(probe_sql, instance_url, token, "preflight")
    except DCQueryError as e:
        msg = str(e)
        # Classify based on the HTTP code in the error message. The error
        # body carries ``http=<code>`` right at the start per dc.post().
        if "http=401" in msg:
            raise DcAccessDenied("401", msg) from e
        if "http=403" in msg:
            raise DcAccessDenied("403", msg) from e
        raise DcAccessDenied("dc_probe_failed", msg) from e
    return instance_url, token


def _emit_dc_access_denied_preamble(
    reason: str,
    detail: str,
) -> None:
    """Headless fallback: emit the machine-readable preamble to stdout.

    Single-line JSON per the Batch-D plan. Followed by ``exit(EXIT_DC_ACCESS_DENIED)``
    by the caller. Kept separate so tests can drive it without spawning a
    subprocess.
    """
    payload = {
        "status":  "DC_ACCESS_DENIED",
        "reason":  reason,
        "detail":  detail,
        "options": [
            {"code": "1", "action": "retry", "arg": "--org <alias>"},
            {"code": "2", "action": "cancel"},
        ],
    }
    print(json.dumps(payload))


def _handle_dc_access_denied(
    exc: DcAccessDenied,
    *,
    session_id: str,
    is_tty: bool,
) -> int:
    """Branch on tty presence and return an exit code.

    Interactive: print the 2-option menu; read one line from stdin.
      - ``1`` → signal caller to retry (returns ``EXIT_DC_ACCESS_DENIED``;
        outer ``main()`` may re-prompt for alias in a bounded loop — for
        now we surface the exit code and let the user re-invoke).
      - ``2`` → return 0 (user cancelled; graceful exit).

    Headless: emit JSON preamble + ``EXIT_DC_ACCESS_DENIED`` immediately.
    """
    if not is_tty:
        _emit_dc_access_denied_preamble(exc.reason, exc.detail)
        return EXIT_DC_ACCESS_DENIED

    _log(
        f"\nThis skill requires Data Cloud access, which failed: "
        f"{exc.detail}\nYour options:\n"
        f"  (1) Retry with a different org alias (pass --org <alias>)\n"
        f"  (2) Cancel\nPick one: "
    )
    try:
        choice = sys.stdin.readline().strip()
    except (KeyboardInterrupt, EOFError):
        return 0
    if choice == "1":
        _log("Re-invoke with: python3 fetch_dc.py --session "
             f"{session_id} --org <new-alias>")
        return EXIT_DC_ACCESS_DENIED
    # Any other response is treated as cancel.
    return 0


# ---- constants -------------------------------------------------------------

_INTERNAL_TRACE_RE = re.compile(r'"internalTraceId":"([a-f0-9]+)"')  # @rule-suppress starter-sec-002 — re.compile, not exec/eval
_NOT_SET = {"", "NOT_SET", None}
# Mirrors _shared/fs_guard.API_NAME_RE. Duplicated locally as a pre-flight
# gate so the cross-role fallback's adopted api_name string satisfies the
# path-builder's regex before we hand it to paths.session_dir(). Without
# this, paths.session_dir would reject the path with an opaque
# ValidationError after the fallback claimed success — operator confusion.
# Anchored \A...\Z + `.fullmatch()` (not ^...$ + .match) so trailing
# newlines don't slip through; matches the security pattern in fs_guard.
_API_NAME_RE = re.compile(r"\A[A-Za-z0-9_]+\Z")  # @rule-suppress starter-sec-002 — re.compile, not exec/eval
# Mirrors _shared/fs_guard.AGENT_VERSION_RE. Used by the cross-role
# fallback so we never adopt a malformed version string into a session-dir
# path.
_VERSION_RE = re.compile(r"\Av[0-9]+\Z")  # @rule-suppress starter-sec-002 — re.compile, not exec/eval

# All 24 .sql templates — checked for existence at startup.
_TEMPLATES = (
    "sessions", "interactions", "messages", "moments", "participants",
    "tag_associations", "gateway_requests",
    "steps", "moment_interactions",
    "telemetry_spans", "generations", "app_generation",
    "gateway_request_tags", "gateway_responses", "gateway_records",
    "gateway_request_metadata", "gateway_request_llm",
    "feedback",
    "content_quality", "content_category", "feedback_details",
    "tag_definitions", "tag_definition_associations", "tags",
)


# ---- small helpers ---------------------------------------------------------

def _in_list(ids: list[str]) -> str:
    """SQL `IN (…)` fragment. Dedupes, drops NOT_SET/empty, preserves order."""
    seen: dict[str, None] = {}
    for i in ids:
        if i and i not in _NOT_SET and i not in seen:
            seen[i] = None
    return "(" + ",".join(f"'{i}'" for i in seen) + ")"


def _extract_trace_ids(interactions: list[dict]) -> list[str]:
    """Pull runtime trace_ids from interaction rows.

    `ssot__TelemetryTraceId__c` is often empty — the real trace_id lives
    HTML-escaped inside `ssot__AttributeText__c` as `"internalTraceId":"…"`.
    See references/dc_dmo_fields.md for the full gotcha.
    """
    out: list[str] = []
    for r in interactions:
        tid = r.get("ssot__TelemetryTraceId__c") or ""
        if tid and tid not in _NOT_SET:
            out.append(tid)
            continue
        attr = html.unescape(r.get("ssot__AttributeText__c") or "")
        m = _INTERNAL_TRACE_RE.search(attr)
        if m:
            out.append(m.group(1))
    # dedupe, preserve order
    return list(dict.fromkeys(out))


def _preflight_templates() -> None:
    """Refuse to start if any .sql template is missing."""
    missing = [n for n in _TEMPLATES if not (SQL_DIR / f"{n}.sql").is_file()]
    if missing:
        raise SystemExit(
            f"missing SQL templates in {SQL_DIR}: {', '.join(missing)}"
        )


# ---- fetch helpers (single entry point for disk writes + manifest) --------

def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def _fetch(
    ctx: dict,
    wave: int,
    name: str,
    where: str,
    order_by: str = "",
    *,
    join_path: str | None = None,
) -> list[dict]:
    """Run a live query, save result, append manifest entry, return rows."""
    sql = load_sql(name, WHERE_CLAUSE=where, ORDER_BY=order_by)
    if ctx["verbose"]:
        _log(f"    SQL[{name}]:\n{sql}\n")
    t0 = time.monotonic()
    try:
        rows = post(sql, ctx["instance_url"], ctx["token"], name)
    except DCQueryError as e:
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        _log(f"  dc.{name:<30} ERROR ({elapsed_ms}ms)")
        entry = {
            "name": name, "wave": wave, "rows": 0,
            "elapsed_ms": elapsed_ms, "status": "error",
            "_unavailable_reason": str(e).splitlines()[0],
        }
        ctx["queries"].append(entry)
        return []
    elapsed_ms = int((time.monotonic() - t0) * 1000)
    # Only persist when there's data. Zero-row / error / skipped outcomes
    # are recorded in the manifest (status + _unavailable_reason); a
    # matching dc.<name>.json would be an empty `[]` file adding noise to
    # the per-session directory. assemble_dc._load tolerates missing
    # files by returning [].
    if rows:
        save(
            rows,
            ctx["org_id_15"],
            ctx["agent_api_name"],
            ctx["agent_version"],
            ctx["session_id"],
            "dc",
            name,
        )
    entry = {
        "name": name, "wave": wave, "rows": len(rows),
        "elapsed_ms": elapsed_ms,
        "status": "ok" if rows else "empty",
    }
    if join_path:
        entry["join_path"] = join_path
    if not rows:
        entry["_unavailable_reason"] = (
            f"query returned zero rows for where={where[:120]}"
        )
    ctx["queries"].append(entry)
    _log(f"  dc.{name:<30} rows={len(rows):<5} ({elapsed_ms}ms)")
    return rows


def _fetch_empty(ctx: dict, wave: int, name: str, reason: str) -> None:
    """Record a skipped query in the manifest — no HTTP call, no artifact file."""
    ctx["queries"].append({
        "name": name, "wave": wave, "rows": 0,
        "elapsed_ms": 0, "status": "skipped",
        "_unavailable_reason": reason,
    })
    _log(f"  dc.{name:<30} SKIPPED ({reason})")


# ---- main entry point -----------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(
        prog="fetch_dc.py",
        description="Fetch all 24 DC artifacts for one Agentforce session.",
    )
    ap.add_argument("--session", required=True,
                    help="AI-agent session UUID, OR a Salesforce MessagingSession id "
                         "(0Mw... prefix). Messaging ids are resolved to the UUID "
                         "via a one-row DC lookup before the waterfall starts.")
    ap.add_argument("--org", required=True, help="sf org alias")
    ap.add_argument("--verbose", action="store_true", help="dump each SQL before POST")
    ap.add_argument("--no-assemble", action="store_true",
                    help="skip tree assembly after fetch")
    ap.add_argument("--no-render", action="store_true",
                    help="skip summary markdown rendering")
    # Runtime-agnostic path overrides; default to ~/.vibe/...
    from _shared.cli_override import add_cli_flags, apply_overrides
    add_cli_flags(ap)
    args = ap.parse_args()
    apply_overrides(args, caller_globals=globals())

    _preflight_templates()

    # Accept either a UUID or a MessagingSession id (0Mw...). The resolver
    # passes UUIDs through unchanged; on messaging ids it tries disk first
    # (any prior fetch left dc.sessions.json behind under DATA_ROOT), and
    # falls back to a live one-row DC lookup only if disk misses. This keeps
    # fetch_dc consistent with every other entry point and avoids a
    # round-trip when re-invoking against an already-fetched session.
    # On multi-match or zero-match the resolver exits with a diagnostic.
    from resolve_session import is_messaging_id, resolve_disk_or_live
    input_id = args.session
    session_id = resolve_disk_or_live(input_id, org=args.org)
    if is_messaging_id(input_id):
        _log(f"resolved messaging id {input_id} → AiAgentSession {session_id}")

    # Preflight — one cheap probe before the waterfall starts.
    # Fails fast with DcAccessDenied on 401/403/no-org. The outer try
    # block routes the exception through _handle_dc_access_denied, which
    # emits either an interactive prompt or a JSON preamble depending on
    # tty presence, then exits with EXIT_DC_ACCESS_DENIED (10).
    try:
        instance_url, token = preflight_dc_access(session_id, args.org)
    except DcAccessDenied as exc:
        return _handle_dc_access_denied(
            exc,
            session_id=session_id,
            is_tty=sys.stdin.isatty(),
        )
    _log(f"org:     {instance_url}")
    _log(f"session: {session_id}\n")

    ctx = {
        "session_id": session_id,
        "org_alias": args.org,
        "instance_url": instance_url,
        "token": token,
        "verbose": args.verbose,
        "queries": [],
        "started_at": datetime.now(timezone.utc),
        # Populated by _resolve_identity() before the first storage.save call.
        "org_id_15": None,
        "agent_api_name": None,
        "agent_version": None,
    }

    _run_waterfall(ctx)

    _write_manifest(ctx)

    if not args.no_assemble:
        from assemble_dc import main_for_session as _assemble
        _assemble(args.session)

    if not args.no_render:
        from render_dc import main_for_session as _render
        _render(args.session)  # SystemExits if tree is missing

    return 0


def _fetch_no_save(
    ctx: dict, wave: int, name: str, where: str, order_by: str = "",
) -> list[dict]:
    """Variant of ``_fetch`` that skips the on-disk write.

    Used for the identity-resolution phase: ``sessions`` and ``participants``
    run before we know ``(org_id_15, agent_api_name, agent_version)``, which
    are required to build the target session dir. We stash the rows and
    write them via ``storage.save`` once identity is resolved.

    Manifest entry is still appended so the final ``dc._session_manifest.json``
    mirrors every query run.
    """
    sql = load_sql(name, WHERE_CLAUSE=where, ORDER_BY=order_by)
    if ctx["verbose"]:
        _log(f"    SQL[{name}]:\n{sql}\n")
    t0 = time.monotonic()
    try:
        rows = post(sql, ctx["instance_url"], ctx["token"], name)
    except DCQueryError as e:
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        _log(f"  dc.{name:<30} ERROR ({elapsed_ms}ms)")
        ctx["queries"].append({
            "name": name, "wave": wave, "rows": 0,
            "elapsed_ms": elapsed_ms, "status": "error",
            "_unavailable_reason": str(e).splitlines()[0],
        })
        return []
    elapsed_ms = int((time.monotonic() - t0) * 1000)
    entry = {
        "name": name, "wave": wave, "rows": len(rows),
        "elapsed_ms": elapsed_ms,
        "status": "ok" if rows else "empty",
    }
    if not rows:
        entry["_unavailable_reason"] = (
            f"query returned zero rows for where={where[:120]}"
        )
    ctx["queries"].append(entry)
    _log(f"  dc.{name:<30} rows={len(rows):<5} ({elapsed_ms}ms)  [deferred save]")
    return rows


def _lookup_org_id_via_sf_cli(org_alias: str) -> str:
    """Return the 15-char org id from ``sf org display --target-org <alias>``.

    Fallback path for ``_resolve_identity``: the DMO field
    ``ssot__InternalOrganizationId__c`` is occasionally null on
    otherwise-well-formed sessions (materialization gap in the SSOT
    pipeline). Since the authenticated ``sf`` alias already knows the
    org id, we ask the CLI directly rather than failing the whole run.

    Matches the shell pattern used by ``dc.resolve_org`` — same argv, same
    JSON shape (``.result.id``). Any non-zero exit, missing binary, or
    malformed payload propagates to the caller as an exception so the
    outer ``_resolve_identity`` can raise a unified "both sources failed"
    diagnostic.
    """
    proc = subprocess.run(
        ["sf", "org", "display", "--target-org", org_alias, "--json"],
        capture_output=True, text=True, check=True,
    )
    payload = json.loads(proc.stdout)
    org_id = (payload.get("result") or {}).get("id") or ""
    if len(org_id) < 15:
        raise ValueError(
            f"sf org display returned result.id={org_id!r} (len<15)"
        )
    return org_id[:15]


def _resolve_identity(
    sessions: list[dict],
    participants: list[dict],
    org_alias: str,
) -> tuple[str, str, str]:
    """Derive (org_id_15, agent_api_name, agent_version) from wave-1 rows.

    - ``org_id_15`` — ``sessions[0].ssot__InternalOrganizationId__c[:15]``,
      falling back to ``sf org display --target-org <org_alias>`` when the
      DMO field is null/empty/shorter-than-15 (a known SSOT materialization
      gap; the authenticated CLI alias knows the org id regardless).
    - ``agent_api_name`` / ``agent_version`` — first AGENT participant row
      (sorted by participant id for determinism) with both fields populated.

    **Dominant-agent policy:** if multiple AGENT participants are present
    (handoff sessions), the one with the lexicographically first
    ``agent_api_name`` wins. Matches the ``sorted(agents_observed)[0]``
    rule used by ``_session_row_live`` so every writer agrees on the
    session's home dir.

    Raises ``SystemExit`` with a clear diagnostic when any segment cannot
    be derived. We deliberately do NOT fall back to a catch-all "unknown"
    agent dir — writing under a synthetic identity would let every
    ambiguous session pile into the same folder and corrupt the layout
    invariant downstream readers depend on.
    """
    if not sessions:
        raise SystemExit(
            "fetch_dc: sessions query returned 0 rows; "
            "cannot resolve org identity — is the session id correct?"
        )
    org_id_18 = sessions[0].get("ssot__InternalOrganizationId__c") or ""
    if org_id_18 and len(org_id_18) >= 15:
        org_id_15 = org_id_18[:15]
    else:
        # DMO field is null/empty/short. The session is otherwise well-formed
        # — fall back to the authenticated sf alias for the org id.
        try:
            org_id_15 = _lookup_org_id_via_sf_cli(org_alias)
        except (subprocess.CalledProcessError, FileNotFoundError,
                json.JSONDecodeError, ValueError) as e:
            raise SystemExit(
                f"fetch_dc: both DMO field and sf org display failed — "
                f"sessions[0].ssot__InternalOrganizationId__c={org_id_18!r}, "
                f"sf org display --target-org {org_alias!r} error: "
                f"{type(e).__name__}: {e}"
            )
        _log(
            f"  org_id_15 fallback to sf org display: {org_id_15} "
            f"(DMO field was null)"
        )

    # Collect every AGENT participant with a non-empty agent_api_name +
    # agent_version. Sort by (api_name, version) for a stable dominant-
    # agent pick on handoffs.
    candidates = sorted(
        {
            (
                p.get("ssot__AiAgentApiName__c") or "",
                p.get("ssot__AiAgentVersionApiName__c") or "",
            )
            for p in participants
            if p.get("ssot__AiAgentSessionParticipantRole__c") == "AGENT"
        }
    )
    # Drop entries missing either field.
    candidates = [(n, v) for n, v in candidates if n and v and n not in _NOT_SET and v not in _NOT_SET]
    if not candidates:
        # Fallback: some agent shapes (e.g. MyAgent on Messaging)
        # leave AGENT rows with api_name/version=NOT_SET while USER (or
        # other-role) participant rows carry both fields. Harvest from
        # ANY role first so we land on the real (api_name, version) pair
        # — that's what assemble_dc later reconciles into the tree, so
        # the dir name and tree.identity will agree out of the gate
        # rather than dir=__v0/ + tree=__v24/.
        cross_role = sorted({
            (
                p.get("ssot__AiAgentApiName__c") or "",
                p.get("ssot__AiAgentVersionApiName__c") or "",
            )
            for p in participants
        })
        cross_role = [
            (n, v) for n, v in cross_role
            if n and n not in _NOT_SET
            and v and v not in _NOT_SET
            and _API_NAME_RE.fullmatch(n)
            and _VERSION_RE.fullmatch(v)
        ]
        if cross_role:
            api_name, version = cross_role[0]
            _log(
                f"  identity fallback: strict AGENT-row resolution failed; "
                f"using api_name={api_name!r} version={version!r} from a "
                f"non-AGENT participant row"
            )
            return org_id_15, api_name, version
        # Last-ditch fallback: api_name from any role, but no version
        # available anywhere. Stamp version='v0' (placeholder satisfying
        # ^v[0-9]+$). Without this, the entire DC pipeline is unrunnable
        # for those sessions even though all the downstream rows exist.
        # The Builder Previewer shape legitimately lands here — every
        # version_api_name in DC for that session truly is empty/v0.
        any_names = sorted({
            (p.get("ssot__AiAgentApiName__c") or "")
            for p in participants
        })
        any_names = [n for n in any_names if n and n not in _NOT_SET]
        # Only promote names that satisfy fs_guard's API_NAME_RE — otherwise
        # paths.session_dir would reject the dir later with an opaque
        # ValidationError. Cleaner UX is to fall through to the original
        # SystemExit, which carries actionable diagnostic text.
        any_names = [n for n in any_names if _API_NAME_RE.fullmatch(n)]
        if any_names:
            _log(
                f"  identity fallback: strict AGENT-row resolution failed; "
                f"no participant row carries (api_name, version) together; "
                f"using api_name={any_names[0]!r} from any participant row, "
                f"version='v0' (placeholder)"
            )
            return org_id_15, any_names[0], "v0"
        raise SystemExit(
            "fetch_dc: no AGENT participants with agent_api_name + "
            "agent_version on this session; cannot resolve identity. "
            "If the session was created recently, STDM materialization "
            "may not have completed yet — retry in a few minutes. "
            "Otherwise the session may be malformed."
        )
    agent_api_name, agent_version = candidates[0]
    return org_id_15, agent_api_name, agent_version


def _run_waterfall(ctx: dict) -> None:
    """5-wave forward-only orchestration.

    Wave 1 fetches session-scoped rows directly keyed on the session id.
    Wave 2 fetches interaction-scoped rows (Steps, MomentInteractions).
    Wave 3 fans out to Generation (via Step.GenerationId) and to the full
    Gateway audit chain (via GatewayRequest.sessionId__c harvested in
    wave 1 — GatewayResponse, Tags, ObjRecord, Metadata, LLM).
    Wave 4 fetches Generation-scoped child rows (Quality, Category,
    Feedback children).
    Wave 5 fetches the agent/tag catalog (not session-keyed).

    Every edge is forward from Session. See `references/dc_dmo_fields.md`
    for the full join map.

    Wave-1 ordering: ``sessions`` + ``participants`` run first with
    deferred saves so ``_resolve_identity`` can compute the session's
    target dir BEFORE any on-disk write. Without this ordering, the
    first ``storage.save`` call would fail validation (``paths.session_dir``
    requires the 3 identity segments). Once identity is stamped on
    ``ctx``, remaining wave-1 queries save through the normal ``_fetch``
    path.
    """
    sid = ctx["session_id"]
    sid_q = f"'{sid}'"

    # ---- wave 1a: identity resolution (deferred save) --------------------
    _log("== wave 1a: identity resolution ==")
    sessions = _fetch_no_save(ctx, 1, "sessions",
                              f"ssot__Id__c = {sid_q}")
    participants = _fetch_no_save(ctx, 1, "participants",
                                  f"ssot__AiAgentSessionId__c = {sid_q}")
    (
        ctx["org_id_15"],
        ctx["agent_api_name"],
        ctx["agent_version"],
    ) = _resolve_identity(sessions, participants, ctx["org_alias"])
    _log(
        f"  identity: org={ctx['org_id_15']}  "
        f"agent={ctx['agent_api_name']}  version={ctx['agent_version']}"
    )

    # Flush deferred writes now that identity is known. Empty results
    # stay unwritten (same contract as ``_fetch``).
    if sessions:
        save(
            sessions, ctx["org_id_15"], ctx["agent_api_name"],
            ctx["agent_version"], sid, "dc", "sessions",
        )
    if participants:
        save(
            participants, ctx["org_id_15"], ctx["agent_api_name"],
            ctx["agent_version"], sid, "dc", "participants",
        )

    # ---- wave 1b: remaining session-scoped (5 queries) -------------------
    _log("\n== wave 1b: session-scoped ==")
    interactions = _fetch(ctx, 1, "interactions",
                          f"ssot__AiAgentSessionId__c = {sid_q}",
                          "ORDER BY ssot__StartTimestamp__c")
    messages = _fetch(ctx, 1, "messages",
                      f"ssot__AiAgentSessionId__c = {sid_q}",
                      "ORDER BY ssot__MessageSentTimestamp__c")
    moments = _fetch(ctx, 1, "moments",
                     f"ssot__AiAgentSessionId__c = {sid_q}",
                     "ORDER BY ssot__StartTimestamp__c")
    _fetch(ctx, 1, "tag_associations",
           f"ssot__AiAgentSessionId__c = {sid_q}")
    # sessionId__c is stored as a literal quoted string ('"<uuid>"'); raw-UUID
    # exact match returns 0 rows. LIKE handles both '"<uuid>"' and any future
    # variant cleanly. See references/dc_dmo_fields.md.
    gw_requests = _fetch(ctx, 1, "gateway_requests",
                         f"sessionId__c LIKE '%{sid}%'",
                         "ORDER BY timestamp__c")

    # Harvest IDs from wave 1 for downstream waves
    interaction_ids = [r.get("ssot__Id__c") for r in interactions]
    # Agent name harvest: moments DMO is sparse — many short or
    # abandoned-before-tagging sessions never write a moment row, leaving
    # agent_api_names empty even though the agent identity was already
    # resolved upstream. Fall through to participants (always populated
    # for any session with ≥1 turn) and finally to ctx.agent_api_name
    # (resolved during identity wave 1a from BotDefinition).
    _harvested = {
        r["ssot__AiAgentApiName__c"]
        for r in moments
        if r.get("ssot__AiAgentApiName__c") and r["ssot__AiAgentApiName__c"] not in _NOT_SET
    }
    _harvested |= {
        r["ssot__AiAgentApiName__c"]
        for r in participants
        if r.get("ssot__AiAgentApiName__c") and r["ssot__AiAgentApiName__c"] not in _NOT_SET
    }
    if not _harvested and ctx.get("agent_api_name"):
        _harvested = {ctx["agent_api_name"]}
    agent_api_names = sorted(_harvested)
    gw_req_ids = [r.get("gatewayRequestId__c") for r in gw_requests]
    trace_ids = _extract_trace_ids(interactions)
    _log(f"  harvested: {len(interaction_ids)} interactions, "
         f"{len(moments)} moments, trace_ids={len(trace_ids)}, "
         f"gw_req_ids={len(gw_req_ids)}, agents={agent_api_names}")

    # ---- wave 2: interaction/moment-scoped (2 queries) --------------------
    _log("\n== wave 2: interaction/moment-scoped ==")
    interaction_in = _in_list(interaction_ids)
    if interaction_in != "()":
        steps = _fetch(ctx, 2, "steps",
                       f"ssot__AiAgentInteractionId__c IN {interaction_in}",
                       "ORDER BY ssot__StartTimestamp__c")
        _fetch(ctx, 2, "moment_interactions",
               f"ssot__AiAgentInteractionId__c IN {interaction_in}")
    else:
        steps = []
        _fetch_empty(ctx, 2, "steps",
                     "no interactions for session")
        _fetch_empty(ctx, 2, "moment_interactions",
                     "no interactions for session")

    # Harvest generation IDs from steps for forward fetch of GenAIGeneration.
    # (Step.ssot__GenAiGatewayResponseId__c / ssot__GenAiGatewayRequestId__c are
    # NOT harvested — those would be backward chains. Gateway audit rows are
    # fetched forward from the session via GatewayRequest.sessionId__c in wave 1.)
    step_gen_ids = [s.get("ssot__GenerationId__c") for s in steps]
    _log(f"  harvested: generation_ids={len([x for x in step_gen_ids if x and x not in _NOT_SET])}")

    # ---- wave 3: trace/generation/gateway fanout (6 queries) --------------
    _log("\n== wave 3: trace/generation/gateway fanout ==")

    # telemetry_spans — on trace_ids from interactions
    trace_in = _in_list(trace_ids)
    if trace_in != "()":
        _fetch(ctx, 3, "telemetry_spans",
               f"ssot__TelemetryTrace__c IN {trace_in}",
               "ORDER BY ssot__StartDateTime__c")
    else:
        _fetch_empty(ctx, 3, "telemetry_spans",
                     "no trace_ids extractable from interactions "
                     "(TelemetryTraceId__c empty and no internalTraceId in AttributeText__c)")

    # generations — canonical path: steps.ssot__GenerationId__c
    gen_in = _in_list(step_gen_ids)
    if gen_in != "()":
        generations = _fetch(ctx, 3, "generations",
                             f"generationId__c IN {gen_in}",
                             "ORDER BY timestamp__c",
                             join_path="steps.ssot__GenerationId__c")
        # app_generation — same join key as generations (sibling DMO)
        _fetch(ctx, 3, "app_generation",
               f"generationId__c IN {gen_in}",
               "ORDER BY timestamp__c",
               join_path="steps.ssot__GenerationId__c")
    else:
        generations = []
        _fetch_empty(ctx, 3, "generations",
                     "no step.ssot__GenerationId__c values on this session "
                     "(all steps had NOT_SET or steps table was empty)")
        _fetch_empty(ctx, 3, "app_generation",
                     "no step.ssot__GenerationId__c values on this session "
                     "(all steps had NOT_SET or steps table was empty)")

    # --- Gateway audit chain (forward-only from session) ------------------
    # All audit rows flow forward from Session via GatewayRequest.sessionId__c
    # (harvested in wave 1). Every child table is keyed on the authoritative
    # gw_req_ids from that wave-1 fetch:
    #
    #   GenAIGatewayResponse       generationRequestId__c IN {gw_req_ids}
    #   GenAIGatewayRequestTag     parent__c              IN {gw_req_ids}
    #   GenAIGtwyObjRecord         parent__c              IN {gw_req_ids}
    #   GenAIGtwyRequestMetadata   parent__c              IN {gw_req_ids}
    #   GenAIGtwyRequestLLM        parent__c              IN {gw_req_ids}
    #
    # No Step->Response->Request chain. Step's GenAiGatewayRequestId__c and
    # GenAiGatewayResponseId__c FKs exist but we don't harvest them: they
    # only cover LLM_STEP-owned calls and miss nested features like
    # PromptTemplateGenerationsInvocable. The session-direct fetch in wave 1
    # is the authoritative set.
    gw_req_in = _in_list(gw_req_ids)
    if gw_req_in != "()":
        _fetch(ctx, 3, "gateway_responses",
               f"generationRequestId__c IN {gw_req_in}",
               "ORDER BY timestamp__c",
               join_path="gateway_requests.gatewayRequestId__c")
        _fetch(ctx, 3, "gateway_request_tags",
               f"parent__c IN {gw_req_in}")
        _fetch(ctx, 3, "gateway_records",
               f"parent__c IN {gw_req_in}")
        _fetch(ctx, 3, "gateway_request_metadata",
               f"parent__c IN {gw_req_in}")
        _fetch(ctx, 3, "gateway_request_llm",
               f"parent__c IN {gw_req_in}")
    else:
        gw_empty_reason = (
            "no gateway_requests matched GatewayRequest.sessionId__c LIKE "
            "'%<sid>%' in wave 1 — Trust Layer gateway logging may be "
            "disabled for this org, or the session produced no LLM calls"
        )
        for n in ("gateway_responses", "gateway_request_tags", "gateway_records",
                  "gateway_request_metadata", "gateway_request_llm"):
            _fetch_empty(ctx, 3, n, gw_empty_reason)

    # feedback — keyed by generationId (no session col on GenAIFeedback)
    gen_ids_for_feedback = [r.get("generationId__c") for r in generations]
    feedback_in = _in_list(gen_ids_for_feedback)
    if feedback_in != "()":
        feedback = _fetch(ctx, 3, "feedback",
                          f"generationId__c IN {feedback_in}")
    else:
        feedback = []
        _fetch_empty(ctx, 3, "feedback",
                     "no generation_ids available (generations wave was empty)")

    # ---- wave 4: generation/feedback-dependent (3 queries) ----------------
    _log("\n== wave 4: generation/feedback-dependent ==")
    gen_only_in = _in_list(gen_ids_for_feedback)
    if gen_only_in != "()":
        quality = _fetch(ctx, 4, "content_quality",
                         f"parent__c IN {gen_only_in}")
    else:
        quality = []
        _fetch_empty(ctx, 4, "content_quality",
                     "no generation_ids (parent__c IN cannot be empty)")

    # content_category — parent is (generation_ids ∪ quality.id__c)
    quality_ids = [r.get("id__c") or r.get("ssot__Id__c") for r in quality]
    category_parent_ids = gen_ids_for_feedback + quality_ids
    category_in = _in_list(category_parent_ids)
    if category_in != "()":
        _fetch(ctx, 4, "content_category",
               f"parent__c IN {category_in}")
    else:
        _fetch_empty(ctx, 4, "content_category",
                     "no generation_ids or quality_ids to parent to")

    # feedback_details — parent is feedback row id.
    # GenAIFeedback__dlm PK is `feedbackId__c` (no ssot__ prefix, verified via describe);
    # the old harvest used ssot__Id__c which doesn't exist on this DMO.
    feedback_ids = [r.get("feedbackId__c") for r in feedback]
    feedback_ids_in = _in_list(feedback_ids)
    if feedback_ids_in != "()":
        _fetch(ctx, 4, "feedback_details",
               f"parent__c IN {feedback_ids_in}")
    else:
        _fetch_empty(ctx, 4, "feedback_details",
                     "no feedback rows for this session "
                     "(no user thumbs-up/down on any generation)")

    # ---- wave 5: tag catalog (agent-scoped) -------------------------------
    _log("\n== wave 5: tag catalog ==")
    # Live orgs use 'Available' (not Help-doc's 'Active'). If that returns
    # zero rows, retry unfiltered — some orgs have a different enum value or
    # the definitions predate the Status field. See references/dc_dmo_fields.md.
    tag_defs = _fetch(ctx, 5, "tag_definitions",
                      "ssot__Status__c = 'Available'")
    if not tag_defs:
        _log("  (tag_definitions Status='Available' empty — retrying unfiltered)")
        # Pop the empty entry so _fetch can append a fresh one for the retry.
        # The retry overwrites the same on-disk artifact (last run wins).
        ctx["queries"].pop()
        tag_defs = _fetch(ctx, 5, "tag_definitions",
                          "ssot__Id__c IS NOT NULL")
        # Tag the retry in the manifest for traceability.
        ctx["queries"][-1]["notes"] = (
            "retried unfiltered after Status='Available' returned 0 rows"
        )
        if not tag_defs:
            ctx["queries"][-1]["_unavailable_reason"] = (
                "tag_definitions truly empty on this org"
            )

    agent_in = _in_list(agent_api_names)
    if agent_in != "()":
        _fetch(ctx, 5, "tag_definition_associations",
               f"ssot__AiAgentApiName__c IN {agent_in}")
    else:
        _fetch_empty(ctx, 5, "tag_definition_associations",
                     "no agent api names observed in moments")

    def_ids = [r.get("ssot__Id__c") for r in tag_defs]
    def_in = _in_list(def_ids)
    if def_in != "()":
        _fetch(ctx, 5, "tags",
               f"ssot__AiAgentTagDefinitionId__c IN {def_in}")
    else:
        _fetch_empty(ctx, 5, "tags",
                     "no tag_definition ids (tag_definitions was empty)")

    # Tally steps by type for the session_shape classifier.
    steps_by_type = {
        "LLM_STEP": 0, "ACTION_STEP": 0, "TOPIC_STEP": 0,
        "TRUST_GUARDRAILS_STEP": 0, "SESSION_END": 0,
    }
    for s in steps:
        t = s.get("ssot__AiAgentInteractionStepType__c")
        if t in steps_by_type:
            steps_by_type[t] += 1

    # Stash harvested-id counts for the manifest
    steps_with_gen = sum(1 for g in step_gen_ids if g and g not in _NOT_SET)
    ctx["harvested_ids"] = {
        "sessions": len(sessions),
        "messages": len(messages),
        "interactions": len(interaction_ids),
        "moments": len(moments),
        "steps_total": len(steps),
        "steps_by_type": steps_by_type,
        "steps_with_generation_id": steps_with_gen,
        "trace_ids_from_interactions": len(trace_ids),
        "gateway_request_ids": len(gw_req_ids),
        "generation_ids": sum(
            1 for g in gen_ids_for_feedback if g and g not in _NOT_SET
        ),
        "agents_observed": agent_api_names,
    }

    # Classify session shape. 5-value enum; rules evaluated top-to-bottom, first-match-wins.
    # See references/dc_dmo_fields.md for rationale.
    ctx["session_shape"] = _classify_session_shape(
        sessions_count=len(sessions),
        steps_total=len(steps),
        llm_step_count=steps_by_type["LLM_STEP"],
        steps_with_generation_id=steps_with_gen,
        gw_req_count=len(gw_req_ids),
    )


def _classify_session_shape(*, sessions_count, steps_total, llm_step_count,
                            steps_with_generation_id, gw_req_count):
    """6-value session-shape diagnostic. First match wins.

    Rules (top-to-bottom):
    - session_not_found                       — sessions.json returned 0 rows
    - interactions_not_materialized_yet       — gw_reqs > 0 AND steps == 0. Gateway DMOs
                                                materialize within minutes; STDM Interaction
                                                / Step / Message DMOs can take hours to days.
                                                Detected BEFORE abandoned_before_llm because
                                                gw_req_count > 0 is a stronger positive signal
                                                than steps_total > 0 (and the two rules'
                                                inputs are disjoint on this path — steps == 0
                                                here, gw_reqs == 0 for abandoned).
    - abandoned_before_llm                    — steps > 0, LLM_STEP == 0, gw_reqs == 0
    - gateway_requests_dropped_by_stdm        — LLM_STEP > 0
                                                AND gw_reqs == 0 AND steps_with_generation_id == 0.
                                                STDM dropped not just gateway_requests but also
                                                generations (the join chain Step→Generation
                                                is broken). Frequently observed on Atlas-routed
                                                sessions; visible in Splunk LLMGatewayUsageEventWriter
                                                even when DC has zero rows.
    - planner_ran_no_gateway_logs             — LLM_STEP > 0 AND steps_with_generation_id > 0
                                                AND gw_reqs == 0 (the extra guard prevents a
                                                broken generations-IN-clause from being
                                                misclassified here). Generations wrote to DC,
                                                gateway_requests did not — narrower defect than
                                                gateway_requests_dropped_by_stdm.
    - complete                                — everything else (the "normal" bucket,
                                                including partial chain-orphan sessions)

    See references/dc_dmo_fields.md for rationale.
    """
    if sessions_count == 0:
        return "session_not_found"
    if gw_req_count > 0 and steps_total == 0:
        return "interactions_not_materialized_yet"
    if steps_total > 0 and llm_step_count == 0 and gw_req_count == 0:
        return "abandoned_before_llm"
    # When LLM_STEPs ran but neither gateway_requests nor generations
    # wrote, the STDM exporter dropped both. Distinct from
    # planner_ran_no_gateway_logs (which still has generation rows).
    if (llm_step_count > 0 and steps_with_generation_id == 0
            and gw_req_count == 0):
        return "gateway_requests_dropped_by_stdm"
    if (llm_step_count > 0 and steps_with_generation_id > 0
            and gw_req_count == 0):
        return "planner_ran_no_gateway_logs"
    return "complete"


def _write_manifest(ctx: dict) -> None:
    """Emit dc._session_manifest.json next to the 24 artifacts."""
    finished = datetime.now(timezone.utc)
    elapsed_ms = int((finished - ctx["started_at"]).total_seconds() * 1000)
    manifest = {
        "_doc": "Per-query summary of this DC fetch run.",
        "session_id": ctx["session_id"],
        "org_alias": ctx["org_alias"],
        "instance_url": ctx["instance_url"],
        # Identity resolved in wave 1a, before any on-disk write. Stamped
        # here so downstream readers can recover (org, agent, version)
        # without re-parsing the tree.
        "org_id_15": ctx.get("org_id_15"),
        "agent_api_name": ctx.get("agent_api_name"),
        "agent_version": ctx.get("agent_version"),
        "session_shape": ctx.get("session_shape", "unknown"),
        "started_at_utc": ctx["started_at"].isoformat().replace("+00:00", "Z"),
        "finished_at_utc": finished.isoformat().replace("+00:00", "Z"),
        "elapsed_ms": elapsed_ms,
        "queries": ctx["queries"],
        "harvested_ids": ctx.get("harvested_ids", {}),
    }
    target = paths.session_dir(
        ctx["org_id_15"],
        ctx["agent_api_name"],
        ctx["agent_version"],
        ctx["session_id"],
    ) / "dc._session_manifest.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(manifest, indent=2, default=str) + "\n")
    _log(f"\nmanifest: {target}  ({elapsed_ms}ms total)")


if __name__ == "__main__":
    sys.exit(main())
