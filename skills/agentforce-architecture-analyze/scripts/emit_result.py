#!/usr/bin/env python3
"""Final-phase RESULT emitter for investigating-agentforce-architecture.

Reads `$WORK_DIR/.emit_ctx.json` (populated by write_emit_ctx.py) and prints
the final output:

    1. One-line prose status (for humans; first signal in the log).
    2. A blank line.
    3. The `=== RESULT ===` KV block.

BEFORE writing to stdout, the complete RESULT block is teed to
`$DATA_DIR/last_result_block.txt`. Writing the tee first means a consumer
reading the file can never see a truncated block — disk write is atomic
(`tmp + os.replace`), and the stdout print is a best-effort afterthought.

The callers that abort early (AGENT_NOT_FOUND, AGENT_VERSION_NOT_FOUND,
INVALID_INPUT) emit their own RESULT blocks directly — resolve_bot.py and
fs_guard.py have the same disk-tee discipline. All other terminal paths
(OK, PARTIAL_OK, AUTH_REQUIRED, RETRIEVE_FAILED, WRITE_FAILED) flow through
this script.

Usage:
    python3 emit_result.py

Inputs:
    env $WORK_DIR     reads $WORK_DIR/.emit_ctx.json

Outputs:
    $DATA_DIR/last_result_block.txt    full RESULT block (atomic write)
    stdout                             prose line + RESULT block
    exit 0                             always (this script emits; the bash
                                       harness decides the agent's exit code)
    exit 1                             missing env, missing ctx file, bad JSON
"""
import json
import os
import pathlib
import sys
import time

STATUS_ENUM = {
    "OK",
    "PARTIAL_OK",
    "INVALID_INPUT",
    "AUTH_REQUIRED",
    "AGENT_NOT_FOUND",
    "AGENT_VERSION_NOT_FOUND",
    "RETRIEVE_FAILED",
    "WRITE_FAILED",
}

PROSE = {
    "OK": "Declared action tree discovered and cached.",
    "PARTIAL_OK": "Declared action tree partially discovered — see UNRESOLVED_COUNT.",
    "INVALID_INPUT": "Input validation failed.",
    "AUTH_REQUIRED": "sf CLI not authenticated for this org.",
    "AGENT_NOT_FOUND": "BotDefinition.DeveloperName not found in the org.",
    "AGENT_VERSION_NOT_FOUND": "No matching BotVersion under the bot.",
    "RETRIEVE_FAILED": "Metadata API retrieve failed (auth/network/permissions).",
    "WRITE_FAILED": "A filesystem write failed during finalize.",
}


def scrub(s) -> str:
    if not isinstance(s, str):
        s = "" if s is None else str(s)
    bad = set("`$\"\\\r\t\0\n")
    return "".join(c for c in s if c not in bad)


def bool_str(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    s = str(v).lower()
    return "true" if s in ("true", "1", "yes", "on") else "false"


def build_block(ctx: dict, wall_time_seconds: float) -> str:
    status = (ctx.get("status") or "").strip().upper()
    if status not in STATUS_ENUM:
        status = "WRITE_FAILED"

    lines = ["=== RESULT ===", f"STATUS={status}"]

    error_detail = scrub(ctx.get("error_detail", ""))
    if error_detail:
        lines.append(f"ERROR_DETAIL={error_detail}")

    # Always-emitted identity fields (may be empty on early-abort paths)
    lines.extend([
        f"AGENT_API_NAME={scrub(ctx.get('agent_api_name', ''))}",
        f"AGENT_VERSION={scrub(ctx.get('agent_version', ''))}",
        f"VERSION_AUTO_PICKED={bool_str(ctx.get('version_auto_picked', False))}",
        f"AGENT_GENERATION={scrub(ctx.get('agent_generation', '') or 'unknown')}",
        f"BOT_ID={scrub(ctx.get('bot_id', ''))}",
        f"ORG_ID_15={scrub(ctx.get('org_id_15', ''))}",
        f"ORG_ID_18={scrub(ctx.get('org_id_18', ''))}",
    ])

    # Output + cache paths (populated on success; may be empty on fail paths)
    # OUTPUT_ARCHITECTURE_PATH is always emitted — empty
    # string on fail paths, cache-hit paths where the renderer wasn't
    # invoked, or when render failed. Downstream consumers can distinguish
    # "no architecture produced" from "architecture produced but stale"
    # by cross-referencing RENDER_FAILED + CACHE_HIT.
    lines.extend([
        f"OUTPUT_JSON_PATH={scrub(ctx.get('output_json_path', ''))}",
        f"OUTPUT_SUMMARY_PATH={scrub(ctx.get('output_summary_path', ''))}",
        f"OUTPUT_ARCHITECTURE_PATH={scrub(ctx.get('architecture_path', '') or '')}",
        f"CACHE_PATH={scrub(ctx.get('cache_path', ''))}",
        f"CACHE_HIT={bool_str(ctx.get('cache_hit', False))}",
        f"CACHED_AT_UTC={scrub(ctx.get('cached_at_utc', ''))}",
    ])

    # Tree stats
    # emit `_partial_reason` + a rollup of `_pending_fetches` counts
    # alongside the existing PARTIAL / UNRESOLVED_COUNT fields. The write
    # path populates ctx["partial"], ctx["partial_reason"], and
    # ctx["pending_fetches_count"] from the finalized tree JSON —
    # emit_result is intentionally presentation-only and does not re-read
    # the tree itself (ctx is the single source of truth per the emit
    # contract).
    partial_flag = bool(ctx.get("partial", False))
    partial_reason = scrub(ctx.get("partial_reason", "") or "")
    pending_fetches_count = int(ctx.get("pending_fetches_count", 0) or 0)

    # If the upstream pipeline forgot to populate partial_reason but
    # flagged partial=True, emit an empty value rather than nothing —
    # downstream consumers can distinguish "no reason supplied" from
    # "key missing" this way.
    lines.extend([
        f"NODE_COUNT={int(ctx.get('node_count', 0) or 0)}",
        f"DEPTH={int(ctx.get('depth', 0) or 0)}",
        f"PARTIAL={bool_str(partial_flag)}",
        f"PARTIAL_REASON={partial_reason}",
        f"PENDING_FETCHES_COUNT={pending_fetches_count}",
        f"UNRESOLVED_COUNT={int(ctx.get('unresolved_count', 0) or 0)}",
    ])

    # when the tree is partial but status was left blank / "OK",
    # auto-promote the status to PARTIAL_OK so the RESULT block reflects
    # the tree's actual state. ERROR paths (AUTH_REQUIRED etc.) keep
    # their original status — never clobber a failure status.
    if partial_flag and status == "OK":
        # positional safety — `lines[1]` is by construction
        # "STATUS=...". If a future refactor reorders the header we want
        # a loud failure here rather than silently rewriting the wrong
        # line. Assertion cost is negligible; the payoff is catching a
        # whole class of refactor bugs at test time.
        assert lines[1].startswith("STATUS="), (
            f"emit block reordered — lines[1]={lines[1]!r}"
        )
        lines[1] = "STATUS=PARTIAL_OK"
        status = "PARTIAL_OK"

    # emit RENDER_FAILED unconditionally, and auto-promote to
    # PARTIAL_OK when the tree succeeded but the architecture.md render
    # raised. The signal surface is:
    # * RENDER_FAILED=true|false — always emitted.
    # * RENDER_ERROR_DETAIL=<...> — emitted ONLY on true, redacted
    # at write_emit_ctx-time.
    # * STATUS auto-promoted OK -> PARTIAL_OK; _partial_reason pinned
    # to "render-failed" when the tree wasn't already partial.
    # ERROR paths (AUTH_REQUIRED etc.) retain their original status:
    # render never runs in those cases, and render_failed defaults to
    # False so the auto-promote below is a no-op.
    render_failed = bool(ctx.get("render_failed", False))
    lines.append(f"RENDER_FAILED={bool_str(render_failed)}")
    if render_failed:
        detail = scrub(ctx.get("render_error_detail", "") or "")
        lines.append(f"RENDER_ERROR_DETAIL={detail}")
        if status == "OK":
            # Same positional-safety discipline as the partial auto-promote.
            assert lines[1].startswith("STATUS="), (
                f"emit block reordered — lines[1]={lines[1]!r}"
            )
            lines[1] = "STATUS=PARTIAL_OK"
            status = "PARTIAL_OK"
            # Pin a partial_reason so triagers can tell this apart from a
            # tree-level partial. We walk backwards to find the existing
            # PARTIAL_REASON line (always present — emitted above) and
            # rewrite in place. A fresh line would create two competing
            # reason values in the block.
            for idx in range(len(lines) - 1, -1, -1):
                if lines[idx].startswith("PARTIAL_REASON="):
                    # Only overwrite when the tree didn't already claim
                    # a reason — the tree's reason is more informative.
                    if lines[idx] == "PARTIAL_REASON=":
                        lines[idx] = "PARTIAL_REASON=render-failed"
                    break

    # Error-path-specific optional keys
    if status == "AGENT_NOT_FOUND":
        bots = scrub(ctx.get("available_bots", ""))
        if bots:
            lines.append(f"AVAILABLE_BOTS={bots}")
    if status == "AGENT_VERSION_NOT_FOUND":
        vers = scrub(ctx.get("available_versions", ""))
        if vers:
            lines.append(f"AVAILABLE_VERSIONS={vers}")

    lines.append(f"WALL_TIME_SECONDS={wall_time_seconds:.2f}")
    return "\n".join(lines) + "\n"


def main() -> int:
    work_dir_s = os.environ.get("WORK_DIR", "")
    if not work_dir_s:
        sys.stderr.write("emit_result.py: $WORK_DIR not set\n")
        return 1

    ctx_path = pathlib.Path(work_dir_s) / ".emit_ctx.json"
    try:
        ctx = json.loads(ctx_path.read_text())
    except FileNotFoundError:
        sys.stderr.write(f"emit_result.py: missing {ctx_path}\n")
        return 1
    except (OSError, json.JSONDecodeError) as e:
        sys.stderr.write(f"emit_result.py: cannot read {ctx_path}: {e}\n")
        return 1

    start_epoch = float(ctx.get("start_epoch") or time.time())
    wall = max(0.0, time.time() - start_epoch)

    data_dir_s = scrub(ctx.get("data_dir", ""))
    if not data_dir_s:
        # Fallback default — runtime-agnostic. Mirrors runtime.resolve_data_root()
        # in scripts/_shared/runtime.py (the pipeline's canonical helper). This
        # tool runs standalone (no sys.path to scripts/), so we duplicate the
        # default rather than import. If main.py ran with --data-dir, the
        # ctx.data_dir field already carries the override value, so this
        # branch is only reached when the pipeline aborted before writing it.
        data_dir_s = str(
            pathlib.Path.home()
            / ".vibe"
            / "data"
            / "investigating-agentforce-architecture"
            / "_agents"
        )
    data_dir = pathlib.Path(data_dir_s)
    tee_path = data_dir / "last_result_block.txt"

    body = build_block(ctx, wall)
    body += f"RESULT_BLOCK_PATH={tee_path}\n"

    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        tmp = tee_path.with_suffix(tee_path.suffix + ".tmp")
        tmp.write_text(body)
        os.replace(tmp, tee_path)
    except OSError as e:
        sys.stderr.write(f"emit_result.py: tee failed ({e}); continuing with stdout\n")

    status = (ctx.get("status") or "").strip().upper()
    prose = PROSE.get(status, f"Unknown status {status}.")
    sys.stdout.write(prose + "\n\n")
    sys.stdout.write(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
