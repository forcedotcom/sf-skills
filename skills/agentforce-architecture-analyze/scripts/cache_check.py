#!/usr/bin/env python3
"""Cache hit/miss check for investigating-agentforce-architecture.

Replaces old agent Phase 0.5 (manifest read, schema-version check, TTL age
check, path-existence check, env export on hit, RESULT-block assembly).

Flow:
  1. If FORCE_REFRESH=true → emit CACHE_HIT=false, exit 0.
  2. Read $CACHE_DIR/manifest.json. Any I/O or parse failure → miss.
  3. if schema_version != config.SCHEMA_VERSION → miss,
     emit CACHE_INVALIDATED_REASON=schema-version-mismatch, and
     `shutil.rmtree` the cache dir (gated to paths under CACHE_ROOT).
  4. If data_path file missing → miss (atomic rename failed mid-write).
  5. If age > ttl_days (default 7) → miss (no rmtree — just stale).
  6. Hit path:
     - Copy {agent}_{ver}_metadata_tree.json from cache into DATA_DIR +
       WORK_DIR.
     - Copy `declared_action_tree.json` sidecar into WORK_DIR so emit ctx
       + downstream greps work.
     - Stdout: eval-able lines (CACHE_HIT=true, CACHED_AT_UTC, NODE_COUNT,
       DEPTH, AGENT_GENERATION, BOT_ID, VERSION_AUTO_PICKED, PARTIAL,
       UNRESOLVED_COUNT, OUTPUT_JSON_PATH, OUTPUT_SUMMARY_PATH).

`{tree_base}.summary.md` was dropped from the output contract.
Cache-hit no longer copies or regenerates a summary file; OUTPUT_SUMMARY_PATH
is emitted empty for RESULT-block shape stability.

Usage:
    eval "$(python3 cache_check.py)"

Inputs (env):
    CACHE_DIR        required — $CACHE_ROOT/$ORG_ID_15/$AGENT__$VER
    DATA_DIR         required — $DATA_ROOT/$ORG_ID_15/$AGENT__$VER
    WORK_DIR         required
    AGENT_API_NAME   required
    AGENT_VERSION    required
    FORCE_REFRESH    'true'|'false' (default false)

Outputs:
    stdout: eval-able K=V lines
    files (hit only): DATA_DIR/{tree_base}.json and matching copy in WORK_DIR
    exit 0 always (miss is not an error)
"""
import json
import os
import pathlib
import shlex
import shutil
import sys
import datetime as dt

import config  # for SCHEMA_VERSION + CACHE_ROOT path-guard 


# refuse to operate if CACHE_ROOT itself is a symlink.
# _safe_rmtree_under_cache_root calls resolve() on both target and root; a
# symlinked CACHE_ROOT collapses the is_relative_to check because both sides
# land on the symlink target, so rmtree would happily delete whatever lives
# there — outside the sanctioned cache subtree. The guard was designed to
# prevent rmtree escaping the cache; if the root itself can escape, the
# guard is moot. Fail fast at import time so the failure surfaces at the
# correct layer (configuration, not deletion).
#
# Path.is_symlink() returns False for non-existent paths, which is the
# correct behaviour for pristine installs (CACHE_ROOT hasn't been created
# yet; the script will mkdir it on first write and subsequent imports will
# validate the real directory).
if config.CACHE_ROOT.is_symlink():
    raise RuntimeError(
        f"CACHE_ROOT is a symlink ({config.CACHE_ROOT} -> "
        f"{config.CACHE_ROOT.resolve()}). This is rejected for safety; the "
        "_safe_rmtree_under_cache_root guard cannot protect against a "
        "symlinked-root escape. Resolve the symlink or update "
        "config.CACHE_ROOT to a real directory."
    )


def miss(reason: str | None = None):
    """Emit CACHE_HIT=false and exit 0.

    if `reason` is provided, emit a second K=V line
    `CACHE_INVALIDATED_REASON=<reason>` so downstream emit_result can
    surface the invalidation cause in the RESULT block.
    """
    sys.stdout.write("CACHE_HIT=false\n")
    if reason:
        sys.stdout.write(f"CACHE_INVALIDATED_REASON={shlex.quote(reason)}\n")
    sys.exit(0)


def _safe_rmtree_under_cache_root(target: pathlib.Path) -> bool:
    """`shutil.rmtree(target)` ONLY if `target` resolves under CACHE_ROOT.

    Defence against a miscomputed cache_dir that could point outside the
    sanctioned cache root (symlink shenanigans, env-var tampering, or a
    future refactor that forgets to run through `build_agent_cache_dir`).
    We resolve both sides to absolute paths and confirm CACHE_ROOT is a
    prefix before handing to rmtree.

    Returns True on successful deletion, False if the path was refused or
    the rmtree itself failed. Never raises — callers on the miss() path
    can't act on a failure anyway.
    """
    try:
        target_abs = target.resolve(strict=False)
        root_abs = config.CACHE_ROOT.resolve(strict=False)
    except (OSError, RuntimeError):
        return False
    # Path.is_relative_to exists on 3.9+. Explicit check is clearer than
    # a try/except on relative_to().
    try:
        if not target_abs.is_relative_to(root_abs):
            return False
    except AttributeError:  # pragma: no cover — safety for <3.9
        try:
            target_abs.relative_to(root_abs)
        except ValueError:
            return False
    if not target_abs.exists():
        return True  # nothing to do, treat as successful no-op
    try:
        shutil.rmtree(target_abs)
    except OSError:
        return False
    return True


def main() -> int:
    try:
        cache_dir = pathlib.Path(os.environ["CACHE_DIR"])
        data_dir = pathlib.Path(os.environ["DATA_DIR"])
        work_dir = pathlib.Path(os.environ["WORK_DIR"])
        agent_api_name = os.environ["AGENT_API_NAME"]
        agent_version = os.environ["AGENT_VERSION"]
    except KeyError as e:
        sys.stderr.write(f"cache_check.py: missing env {e}\n")
        miss()

    if (os.environ.get("FORCE_REFRESH", "").strip().lower() == "true"):
        miss()

    manifest_path = cache_dir / "manifest.json"
    if not manifest_path.is_file():
        miss()

    try:
        manifest = json.loads(manifest_path.read_text())
    except (OSError, json.JSONDecodeError):
        miss()

    # Schema version gate.
    # strict match against config.SCHEMA_VERSION. Any mismatch (too
    # old OR unexpected future/unknown value) invalidates the cache, and
    # we delete the cache directory so the next run starts clean — a
    # stale tree under a legacy schema is worse than no cache, because
    # downstream code may parse shapes it no longer understands. The
    # legacy `< 2.4` check is subsumed (anything that doesn't equal the
    # current SCHEMA_VERSION triggers this branch).
    schema = str(manifest.get("schema_version") or "0")
    if schema != config.SCHEMA_VERSION:
        _safe_rmtree_under_cache_root(cache_dir)
        miss("schema-version-mismatch")

    # data_path existence
    data_path_s = manifest.get("data_path") or ""
    data_path = pathlib.Path(data_path_s) if data_path_s else None
    if not data_path or not data_path.is_file():
        miss()

    # TTL age check
    try:
        built = dt.datetime.fromisoformat(
            (manifest.get("built_at_utc") or "").replace("Z", "+00:00")
        )
    except ValueError:
        miss()
    age_days = (dt.datetime.now(dt.timezone.utc) - built).days
    ttl = int(manifest.get("ttl_days") or 7)
    if age_days > ttl:
        miss()

    # --- Hit path ---
    tree_base = f"{agent_api_name}_{agent_version}_metadata_tree"
    data_dir.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)

    dst_json = data_dir / f"{tree_base}.json"

    # The manifest's data_path points at the authoritative tree copy. Re-copy
    # to DATA_DIR + WORK_DIR so the filesystem layout is stable for callers.
    try:
        shutil.copy(data_path, dst_json)
    except OSError:
        miss()

    # Stage a declared_action_tree.json sidecar in WORK_DIR for any downstream
    # script that expects the generic name.
    try:
        shutil.copy(dst_json, work_dir / "declared_action_tree.json")
    except OSError:
        pass

    # no summary.md handling — dropped from the output contract.
    agent_meta = manifest.get("agent") or {}
    kind_counts = manifest.get("kind_counts") or {}

    exports = [
        ("CACHE_HIT", "true"),
        ("CACHED_AT_UTC", manifest.get("built_at_utc", "")),
        ("NODE_COUNT", str(manifest.get("node_count", 0))),
        ("DEPTH", str(manifest.get("depth", 0))),
        ("AGENT_GENERATION", agent_meta.get("generation") or "unknown"),
        ("BOT_ID", agent_meta.get("bot_id") or ""),
        ("BOT_MASTER_LABEL", agent_meta.get("master_label") or ""),
        ("VERSION_AUTO_PICKED", "true" if agent_meta.get("_version_auto_picked") else "false"),
        ("PARTIAL", "true" if manifest.get("partial") else "false"),
        ("UNRESOLVED_COUNT", str(manifest.get("unresolved_count", 0))),
        ("OUTPUT_JSON_PATH", str(dst_json)),
        # summary.md dropped from the output contract; field kept
        # empty for RESULT-block shape stability.
        ("OUTPUT_SUMMARY_PATH", ""),
        ("PLANNER_NAME", agent_meta.get("planner_name") or ""),
    ]
    # Pass kind counts too, in case finalize.py runs later without re-parsing
    # (it won't on cache hit, but the values keep the RESULT block complete).
    for k, v in kind_counts.items():
        exports.append((f"KC_{k}", str(v)))

    sys.stdout.write("\n".join(f"{k}={shlex.quote(v)}" for k, v in exports) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
