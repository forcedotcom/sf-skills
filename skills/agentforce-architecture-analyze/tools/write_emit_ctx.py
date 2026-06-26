#!/usr/bin/env python3
"""Write the `$WORK_DIR/.emit_ctx.json` context file for `emit_result.py`.

The agent's bash pipeline has ~10 places where it needs to populate this
context file (one OK path + 6 error paths + cache-hit path). Previously this
was done with inline `python3 - <<PYCTX` heredocs; extracting it into one
script gives a stable allowlist footprint and a single source of truth for
the ctx-file shape.

This script reads every field from env vars the agent has already exported
and writes the JSON atomically. Status-specific error messages come in via
`STATUS` + `ERROR_DETAIL`; the rest of the fields are derived from the run's
already-exported state.

Usage:
    STATUS=OK ERROR_DETAIL='' CACHE_HIT=false \\
      python3 write_emit_ctx.py

Inputs (env):
    WORK_DIR             required — target dir for .emit_ctx.json
    AGENT_API_NAME       required
    AGENT_VERSION        required on success paths, may be empty on early fails
    VERSION_AUTO_PICKED  'true'/'false'; defaults to false
    AGENT_GENERATION     'classic'|'nga'|'unknown'; defaults to 'unknown'
    BOT_ID               required on success paths, may be empty on early fails
    ORG_ID_15            required on success paths, may be empty on early fails
    ORG_ID_18            required on success paths, may be empty on early fails
    CACHE_HIT            'true'/'false'; defaults to false
    CACHED_AT_UTC        ISO-8601 or empty
    NODE_COUNT           integer as string; defaults to 0
    DEPTH                integer as string; defaults to 0
    PARTIAL              'true'/'false'; defaults to false
    UNRESOLVED_COUNT     integer as string; defaults to 0
    START_EPOCH          float seconds since epoch
    DATA_DIR             required — absolute path (may be org-less sentinel dir on early fail)
    CACHE_PATH           optional — absolute path to cache dir (ends with /)
    OUTPUT_JSON_PATH     optional — computed if empty on OK path
    OUTPUT_SUMMARY_PATH  optional — computed if empty on OK path
    AVAILABLE_BOTS       optional — csv, for AGENT_NOT_FOUND
    AVAILABLE_VERSIONS   optional — csv, for AGENT_VERSION_NOT_FOUND
    STATUS               required — one of the 7 enum values
    ERROR_DETAIL         optional — human-readable error message

 (REMEDIATE) derived keys (read from tree JSON, not env):
    ctx["partial_reason"]         from tree["_partial_reason"] (default "")
    ctx["pending_fetches_count"]  sum(len(v) for v in tree["_pending_fetches"].values())
                                  (default 0)

The tree is read from `$WORK_DIR/declared_action_tree.json` — this is
where parse_wave.py writes. If the file is missing / unreadable / malformed,
both keys default to empty / 0 (pre-remediation behavior). This keeps
early-abort paths (AGENT_NOT_FOUND / AUTH_REQUIRED / etc.) working —
they never produce a tree and rightly surface `partial_reason=""` +
`pending_fetches_count=0`.

derived keys (read from data_dir, not env):
    ctx["architecture_path"]       absolute path to `architecture.md` when
                                   the renderer produced one, else "".
    ctx["render_failed"]           True iff a `architecture.md.error`
                                   sidecar exists (written by
                                   main._run_finalize on renderer exception).
    ctx["render_error_detail"]     first 200 chars of sidecar, scrubbed via
                                   rest_client.redact_text. Empty when
                                   render_failed is False. The redact pass
                                   is defensive — the sidecar shouldn't
                                   carry tokens, but exception messages
                                   can carry arbitrary org content.

The sidecar convention pairs with `architecture.md`: finalize writes the
`.error` only on exception; emit_result's RESULT-block auto-promote to
PARTIAL_OK relies on this boolean to flag "tree OK, diagram skipped".

Output:
    $WORK_DIR/.emit_ctx.json
    exit 0 on success, 1 on missing env / write failure
"""
import json
import os
import pathlib
import re
import sys


# local, dependency-free token scrub mirroring the patterns in
# `scripts/rest_client.redact_text`. Keeping the redactor inline preserves
# the tools/ <-> scripts/ decoupling (tools/ is stdlib-only by policy) and
# avoids adding a sys.path hop on every write_emit_ctx invocation. The two
# implementations must stay in sync; the shared regex shapes are:
# * Authorization: Bearer <token>
# * access(_)?Token=<value> in query strings
# * "access(_)?Token":"<value>" in JSON payloads
# If a new redaction pattern is added to rest_client.redact_text it MUST be
# mirrored here — the sidecar surface is narrow (render_architecture
# exception messages) so the risk of drift is low, but the dual-impl is a
# known trade-off for decoupling.
_TOOLS_AUTH_HEADER_RE = re.compile(
    r"(Authorization:\s*Bearer\s+)[^\s\"'<>]+",
    flags=re.IGNORECASE,
)
_TOOLS_ACCESS_TOKEN_QS_RE = re.compile(
    r"(access[_]?token=)[^&\s\"'<>]+",
    flags=re.IGNORECASE,
)
_TOOLS_ACCESS_TOKEN_JSON_RE = re.compile(
    r"(\"access[_]?token\"\s*:\s*\")[^\"]*",
    flags=re.IGNORECASE,
)


def _redact(text: str) -> str:
    if not text:
        return text
    text = _TOOLS_AUTH_HEADER_RE.sub(r"\1<redacted>", text)
    text = _TOOLS_ACCESS_TOKEN_QS_RE.sub(r"\1<redacted>", text)
    text = _TOOLS_ACCESS_TOKEN_JSON_RE.sub(r'\1<redacted>', text)
    return text


def _bool(v: str) -> bool:
    return (v or "").strip().lower() == "true"


def _int(v: str, default: int = 0) -> int:
    try:
        return int((v or "").strip() or default)
    except ValueError:
        return default


def _read_architecture_signals(
    data_dir: str,
    agent_api_name: str = "",
    agent_version: str = "",
) -> tuple[str, bool, str]:
    """surface architecture.md presence + render-failure sidecar.

    filename is now self-identifying —
    `{agent_api_name}_{agent_version}_architecture.md` (plus `.error`
    sidecar). Callers pass both identifiers through; when either is
    missing we fall back to the legacy bare `architecture.md` / `.error`
    names so early-abort paths that haven't resolved an agent yet still
    surface any stray files they produced.

    Returns `(architecture_path, render_failed, render_error_detail)`:

      * `architecture_path` — absolute str to the rendered architecture.md
        when present; `""` otherwise. Empty also covers cache-hit paths
        where a *past* run's file may exist — see the inline note.
      * `render_failed` — True iff the `.error` sidecar exists (written by
        main._run_finalize on renderer exception).
      * `render_error_detail` — first 200 chars of the sidecar, stripped +
        scrubbed via `_redact`. Empty when `render_failed` is False.

    Tolerant of: missing dir, unreadable sidecar, binary content. A failure
    to read the sidecar degrades to an empty detail string rather than
    suppressing the render_failed flag — consumers still see the outage
    signal, just without the triage text.

    Cache-hit caveat: on a cache replay, the prior run's architecture.md
    may still be present. We intentionally surface its path anyway (the
    file *is* a product of this run's data_dir). Sidecar semantics are
    different — the sidecar only lands via finalize, so a cache replay
    cannot plant a stale `.error`.
    """
    if not data_dir:
        return ("", False, "")
    dd = pathlib.Path(data_dir)
    if agent_api_name and agent_version:
        arch = dd / f"{agent_api_name}_{agent_version}_architecture.md"
        sidecar = dd / f"{agent_api_name}_{agent_version}_architecture.md.error"
    else:
        # Early-abort paths (no agent resolved) fall back to the legacy
        # bare name so any stray file still surfaces.
        arch = dd / "architecture.md"
        sidecar = dd / "architecture.md.error"

    arch_path = str(arch) if arch.is_file() else ""

    if not sidecar.is_file():
        return (arch_path, False, "")

    try:
        # read_text()'s default is utf-8 with strict errors; a sidecar
        # written by finalize is always ascii prose, but be defensive in
        # case future code changes widen the content set.
        raw = sidecar.read_text(errors="replace")
    except OSError:
        return (arch_path, True, "")

    # Truncate to a single-line-ish detail string. The sidecar format is
    # `"render_architecture failed: <ExcType>: <msg>\n"`; we strip + cap
    # at 200 chars to keep the RESULT block readable, then scrub.
    detail = raw.strip().splitlines()[0] if raw.strip() else ""
    detail = _redact(detail)[:200]
    return (arch_path, True, detail)


def _read_tree_partial_signals(work_dir: str) -> tuple[str, int]:
    """extract `_partial_reason` + pending-fetches rollup from the tree.

    Reads `$WORK_DIR/declared_action_tree.json` (parse_wave's output) and
    returns `(partial_reason, pending_fetches_count)`.

    Tolerant of: missing file, unreadable file, malformed JSON, missing
    keys, wrong-typed keys. All of those degrade to `("", 0)` — the
    pre-remediation defaults — so early-abort code paths (which never
    produce a tree) behave unchanged.

    This is intentionally defensive: write_emit_ctx runs on every exit
    path, including ones where the tree was never created. A raise here
    would turn a clean error status into a write failure.
    """
    try:
        tree_path = pathlib.Path(work_dir) / "declared_action_tree.json"
        if not tree_path.is_file():
            return ("", 0)
        tree = json.loads(tree_path.read_text())
    except (OSError, json.JSONDecodeError):
        return ("", 0)

    if not isinstance(tree, dict):
        return ("", 0)

    reason_raw = tree.get("_partial_reason")
    reason = reason_raw if isinstance(reason_raw, str) else ""

    pending = tree.get("_pending_fetches")
    count = 0
    if isinstance(pending, dict):
        for v in pending.values():
            if isinstance(v, list):
                count += len(v)

    return (reason, count)


def main() -> int:
    try:
        work_dir = os.environ["WORK_DIR"]
        data_dir = os.environ["DATA_DIR"]
        status = os.environ["STATUS"]
    except KeyError as e:
        sys.stderr.write(f"write_emit_ctx.py: missing env {e}\n")
        return 1

    agent_api_name = os.environ.get("AGENT_API_NAME", "")
    agent_version = os.environ.get("AGENT_VERSION", "")
    org_id_15 = os.environ.get("ORG_ID_15", "")

    # Default OUTPUT_*_PATH paths follow the agent-scoped naming convention.
    # Caller can override by exporting directly. If DATA_DIR already ends with
    # the per-agent suffix (because the agent bash composed it), don't re-append.
    #
    # summary.md dropped from the output contract — OUTPUT_SUMMARY_PATH
    # is kept in the RESULT block (empty string) for shape stability.
    default_json = ""
    if status in ("OK", "PARTIAL_OK") and org_id_15 and agent_api_name and agent_version:
        per_agent_suffix = f"{org_id_15}/{agent_api_name}__{agent_version}"
        dd = data_dir.rstrip("/")
        base = dd if dd.endswith(per_agent_suffix) else f"{dd}/{per_agent_suffix}"
        default_json = f"{base}/{agent_api_name}_{agent_version}_metadata_tree.json"

    output_json = os.environ.get("OUTPUT_JSON_PATH") or default_json
    output_summary = os.environ.get("OUTPUT_SUMMARY_PATH") or ""

    try:
        start_epoch = float(os.environ.get("START_EPOCH", "0") or "0")
    except ValueError:
        start_epoch = 0.0

    # derive partial_reason + pending_fetches_count from the tree
    # on disk rather than relying on the agent bash to export them. The
    # tree is the single source of truth — parse_wave wrote these fields;
    # having the bash re-export them would be a narrow, drift-prone
    # integration layer. Absent tree → default ("", 0).
    partial_reason, pending_fetches_count = _read_tree_partial_signals(work_dir)

    # derive architecture-output signals from the data_dir.
    # Parallel to the partial-signals plumbing above: data_dir is the
    # single source of truth for what finalize produced. A missing dir
    # (early-abort paths) degrades to empty fields and render_failed=False.
    architecture_path, render_failed, render_error_detail = (
        _read_architecture_signals(data_dir, agent_api_name, agent_version)
    )

    ctx = {
        "status": status,
        "error_detail": os.environ.get("ERROR_DETAIL", ""),
        "agent_api_name": agent_api_name,
        "agent_version": agent_version,
        "version_auto_picked": _bool(os.environ.get("VERSION_AUTO_PICKED", "")),
        "agent_generation": os.environ.get("AGENT_GENERATION", "") or "unknown",
        "bot_id": os.environ.get("BOT_ID", ""),
        "org_id_15": org_id_15,
        "org_id_18": os.environ.get("ORG_ID_18", ""),
        "cache_hit": _bool(os.environ.get("CACHE_HIT", "")),
        "cached_at_utc": os.environ.get("CACHED_AT_UTC", ""),
        "cache_path": os.environ.get("CACHE_PATH", ""),
        "output_json_path": output_json,
        "output_summary_path": output_summary,
        "node_count": _int(os.environ.get("NODE_COUNT", "0")),
        "depth": _int(os.environ.get("DEPTH", "0")),
        "partial": _bool(os.environ.get("PARTIAL", "")),
        # plumbed from the tree, not env.
        "partial_reason": partial_reason,
        "pending_fetches_count": pending_fetches_count,
        "unresolved_count": _int(os.environ.get("UNRESOLVED_COUNT", "0")),
        "available_bots": os.environ.get("AVAILABLE_BOTS", ""),
        "available_versions": os.environ.get("AVAILABLE_VERSIONS", ""),
        "start_epoch": start_epoch,
        "data_dir": data_dir,
        "work_dir": work_dir,
        # architecture-render outcome signals.
        "architecture_path": architecture_path,
        "render_failed": render_failed,
        "render_error_detail": render_error_detail,
    }

    out = pathlib.Path(work_dir) / ".emit_ctx.json"
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        tmp = out.with_suffix(out.suffix + ".tmp")
        tmp.write_text(json.dumps(ctx, indent=2))
        os.replace(tmp, out)
    except OSError as e:
        sys.stderr.write(f"write_emit_ctx.py: write failed: {e}\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
