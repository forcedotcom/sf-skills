#!/usr/bin/env python3
"""Finalize: write DATA_DIR + CACHE_DIR atomically, build manifest.

Replaces old agent Phase 7. Steps:
  1. Load $WORK_DIR/declared_action_tree.json.
  2. Compute _partial = !(planner_ok && _pending_fetches empty); strip _visited.
  3. Stage DATA_DIR at $DATA_DIR.tmp: copy tree as {api}_{ver}_metadata_tree.json.
  4. rmtree final DATA_DIR; rename .tmp → DATA_DIR.
  5. Stage CACHE_DIR at $CACHE_DIR.tmp: copy metadata/<wave> dirs + sidecars.
  6. Write manifest.json.
  7. rmtree final CACHE_DIR; rename .tmp → CACHE_DIR.
  8. Seed .gitignore on data_root + cache_root parents.
  9. Write $WORK_DIR/.built_at.txt (ISO-Z UTC).

the previously-emitted `{api}_{ver}_metadata_tree.summary.md` is
dropped from the output contract — it was a redundant summary of the tree
JSON. Consumers should read the JSON directly.

Usage:
    python3 finalize.py

Inputs (env):
    WORK_DIR       required
    CACHE_DIR      required
    DATA_DIR       required
    PLANNER_NAME   optional — empty → tree marked partial
    AGENT_API_NAME, AGENT_VERSION — used for filenames

Outputs:
    $DATA_DIR/{api}_{ver}_metadata_tree.json
    $DATA_DIR/last_built_at.txt
    $CACHE_DIR/manifest.json + metadata/<wave>/... + parsed sidecars
    $WORK_DIR/.built_at.txt
    exit 0 success, 1 on any write failure → caller emits STATUS=WRITE_FAILED
"""
import datetime
import json
import os
import pathlib
import shutil
import sys


def sort_tree_in_place(root: dict) -> None:
    """Sort `root.children` and each TOPIC's children alphabetically.

    Ordering rules (2026-05-05, schema 3.1):
    - `BOT_DEFINITION.children`: TOPIC nodes first (by `api_name`
      case-insensitive), then non-topic plannerActions (by kind, then
      `api_name`). This preserves the "planner-level actions as a
      distinct trailing group" convention for readers who scan the
      rendered tree top-down.
    - Each TOPIC's children: alphabetical by `api_name`
      case-insensitive.
    - FLOW children are NOT sorted — flow-actionCall / subflow order
      is the flow author's execution sequence, not a set.
    - GEN_AI_FUNCTION / APEX / PROMPT_TEMPLATE / STANDARD_ACTION leaves
      don't have children that warrant sorting.

    Applied as a final pass after tree assembly and before the
    authoritative JSON write, so ordering is pinned at the single
    source of truth — the renderer doesn't re-sort.
    """
    if not isinstance(root, dict):
        return
    children = root.get("children") or []
    if not children:
        return

    def _root_sort_key(node: dict) -> tuple:
        kind = node.get("kind") or ""
        api = (node.get("api_name") or "").casefold()
        # TOPIC first (tier 0), everything else second (tier 1). Within
        # each tier, stable by kind + api_name case-insensitive.
        tier = 0 if kind == "TOPIC" else 1
        return (tier, kind, api)

    root["children"] = sorted(children, key=_root_sort_key)

    for child in root["children"]:
        if child.get("kind") == "TOPIC":
            child_children = child.get("children") or []
            child["children"] = sorted(
                child_children,
                key=lambda n: (n.get("api_name") or "").casefold(),
            )


def main() -> int:
    try:
        work_dir = pathlib.Path(os.environ["WORK_DIR"])
        cache_dir = pathlib.Path(os.environ["CACHE_DIR"])
        data_dir = pathlib.Path(os.environ["DATA_DIR"])
        agent_api_name = os.environ["AGENT_API_NAME"]
        agent_version = os.environ["AGENT_VERSION"]
    except KeyError as e:
        sys.stderr.write(f"finalize.py: missing env {e}\n")
        return 1

    planner_name = os.environ.get("PLANNER_NAME", "")
    tree_path = work_dir / "declared_action_tree.json"

    try:
        tree = json.loads(tree_path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        sys.stderr.write(f"finalize.py: cannot read {tree_path}: {e}\n")
        return 1

    # Compute _partial. _pending_fetches drains as wave-B BFS resolves
    # refs; failures (HTTP 4xx, iteration-cap exhaustion, managed-flow
    # filter mismatch) move OUT of _pending_fetches and into _unresolved.
    # If we only check _pending_fetches we'd silently call a run with
    # _unresolved entries "converged" — STATUS=OK with hidden failures.
    # Both buckets must be empty for a clean run.
    planner_ok = bool(planner_name)
    pending_total = sum(len(v) for v in (tree.get("_pending_fetches") or {}).values())
    unresolved_count = len(tree.get("_unresolved") or [])
    waves_converged = pending_total == 0 and unresolved_count == 0
    tree["_partial"] = not (planner_ok and waves_converged)

    # Bug F fix: parse_wave + main set _partial_reason from
    # _pending_fetches only (legacy predicate). When _pending is empty
    # but _unresolved is non-empty, those writers set reason=None. The
    # promotion above flips _partial=True from the unresolved bucket, so
    # the reason needs a matching promotion or PARTIAL_REASON= ends up
    # blank in the RESULT block.
    if tree["_partial"] and not tree.get("_partial_reason"):
        if not planner_ok:
            tree["_partial_reason"] = "no-planner"
        elif unresolved_count > 0:
            tree["_partial_reason"] = "unresolved-refs"
        else:
            tree["_partial_reason"] = "pending-refs"

    # Strip _visited (internal state — not part of the durable artifact)
    tree.pop("_visited", None)

    # Pin deterministic child ordering as the last assembly step before
    # the authoritative write — see `sort_tree_in_place` docstring for
    # the ordering rules. Downstream readers (render_architecture,
    # summarize_tree, third-party tooling) therefore see a single
    # canonical order from disk; they don't re-sort.
    sort_tree_in_place(tree.get("root") or {})

    # Rewrite the authoritative tree before copying it anywhere else
    try:
        tmp = tree_path.with_suffix(tree_path.suffix + ".tmp")
        tmp.write_text(json.dumps(tree, indent=2))
        os.replace(tmp, tree_path)
    except OSError as e:
        sys.stderr.write(f"finalize.py: cannot rewrite tree: {e}\n")
        return 1

    built_at = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    a = tree.get("agent", {}) or {}
    tree_base = f"{agent_api_name}_{agent_version}_metadata_tree"

    # --- DATA_DIR staging ---
    # summary.md dropped from the output contract; DATA_DIR now
    # holds only the tree JSON + last_built_at.txt (+ whatever the caller
    # writes alongside, e.g. architecture.md from render_architecture).
    #
    # The prior pattern was `rmtree(data_dir); data_tmp.rename(data_dir)` —
    # destructive of any co-tenant content under `<agent>__<ver>/`. We
    # now iterate staging's children and overwrite each one into data_dir
    # individually, leaving unrelated siblings intact. See
    # `main.py:_swap_dir_atomic` for the production path with the same
    # invariant.
    data_tmp = data_dir.with_suffix(".tmp")
    try:
        if data_tmp.exists():
            shutil.rmtree(data_tmp)
        data_tmp.mkdir(parents=True)
        shutil.copy(tree_path, data_tmp / f"{tree_base}.json")

        (data_tmp / "last_built_at.txt").write_text(built_at + "\n")

        data_dir.mkdir(parents=True, exist_ok=True)
        for staged in list(data_tmp.iterdir()):
            target = data_dir / staged.name
            if target.exists() or target.is_symlink():
                if target.is_dir() and not target.is_symlink():
                    shutil.rmtree(target)
                else:
                    target.unlink()
            shutil.move(str(staged), str(target))
        shutil.rmtree(data_tmp, ignore_errors=True)
    except OSError as e:
        sys.stderr.write(f"finalize.py: DATA_DIR write failed: {e}\n")
        try:
            if data_tmp.exists():
                shutil.rmtree(data_tmp)
        except OSError:
            pass
        return 1

    # --- CACHE_DIR staging ---
    cache_tmp = cache_dir.with_suffix(".tmp")
    try:
        if cache_tmp.exists():
            shutil.rmtree(cache_tmp)
        cache_tmp.mkdir(parents=True)

        # Mirror sf_meta/<wave>/ into metadata/<wave>/ verbatim so cache has:
        # retrieve.json (sf CLI output — critical for debugging silent
        # retrieves that produced zero members)
        # unpackaged/ (parsed XML tree)
        # unpackaged.zip is intentionally skipped — it's byte-for-byte the
        # same as unpackaged/ and doubles cache size on every run.
        meta_dir = cache_tmp / "metadata"
        meta_dir.mkdir()
        sf_meta = work_dir / "sf_meta"
        if sf_meta.exists():
            for wave_dir in sorted(sf_meta.iterdir()):
                if not wave_dir.is_dir():
                    continue
                dst = meta_dir / wave_dir.name
                dst.mkdir(parents=True, exist_ok=True)
                for item in wave_dir.iterdir():
                    if item.name == "unpackaged.zip":
                        continue  # redundant with unpackaged/
                    if item.is_dir():
                        shutil.copytree(item, dst / item.name, dirs_exist_ok=True)
                    else:
                        shutil.copy(item, dst / item.name)

        # Copy every WORK_DIR top-level artifact except:
        # - .emit_ctx.json (per-run shell state, irrelevant to cache)
        # - .built_at.txt (recorded in manifest.built_at_utc)
        # - sf_meta/ (handled above)
        # This catches declared_action_tree.json, _bundle_parsed.json,
        # _agent_generation.txt, _bot_definition.json, _bot_versions.json,
        # and anything future scripts write as top-level sidecars.
        SKIP_NAMES = {".emit_ctx.json", ".built_at.txt", "sf_meta"}
        for item in work_dir.iterdir():
            if item.name in SKIP_NAMES:
                continue
            if item.name.endswith(".tmp"):
                continue  # atomic-write staging from some other script
            if item.is_dir():
                shutil.copytree(item, cache_tmp / item.name, dirs_exist_ok=True)
            elif item.is_file():
                shutil.copy(item, cache_tmp / item.name)

        manifest = {
            "built_at_utc": built_at,
            "schema_version": tree.get("_schema_version", "2.4"),
            "agent": a,
            "node_count": tree.get("node_count", 0),
            "depth": tree.get("depth", 0),
            "kind_counts": tree.get("_kind_counts", {}),
            "ttl_days": 7,
            "data_path": str(data_dir / f"{tree_base}.json"),
            "partial": tree.get("_partial", False),
            "unresolved_count": len(tree.get("_unresolved", []) or []),
        }
        (cache_tmp / "manifest.json").write_text(json.dumps(manifest, indent=2))

        if cache_dir.exists():
            shutil.rmtree(cache_dir)
        cache_tmp.rename(cache_dir)
    except OSError as e:
        sys.stderr.write(f"finalize.py: CACHE_DIR write failed: {e}\n")
        try:
            if cache_tmp.exists():
                shutil.rmtree(cache_tmp)
        except OSError:
            pass
        return 1

    # --- .gitignore seeding on parent dirs (data_root + cache_root) ---
    for root in (cache_dir.parent.parent, data_dir.parent.parent):
        try:
            gi = root / ".gitignore"
            if not gi.exists():
                root.mkdir(parents=True, exist_ok=True)
                gi.write_text("*\n")
        except OSError:
            pass

    # --- .built_at.txt for emit ctx ---
    try:
        (work_dir / ".built_at.txt").write_text(built_at + "\n")
    except OSError as e:
        sys.stderr.write(f"finalize.py: .built_at.txt write failed: {e}\n")
        # Non-fatal — finalize succeeded; emit can recompute

    print(f"[finalize] built_at: {built_at}")
    print(f"[finalize] data  written: {data_dir}/{tree_base}.json")
    print(f"[finalize] cache written: {cache_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
