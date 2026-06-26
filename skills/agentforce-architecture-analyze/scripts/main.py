"""Phase 2 Batch 1: pipeline orchestrator for investigating-agentforce-architecture.

Composes Phase 1 primitives (config, rest_client, sf_cli, soql_loader,
probe_channels, fetch_soql, parallel_retrieve, parse_wave, finalize) into
the 13-phase flow defined in the plan.

NOT a credential holder. Credentials live in a single mutable cell
(`_creds_cell`) that both `creds_provider()` and `refresh_fn()` close over.
Every SOQL call uses `creds_provider` so `retry_on_401`'s refresh path
 can deliver fresh creds into the retry — storing the URL/token
in function args would defeat the refresh entirely.

Phase ordering:
  1  parse args                    (Bash harness does phases 1-3 today;
  2  resolve creds (sf org display)   P2 Batch 1 runs them in-process too)
  3  probe channels
  4  resolve bot + version
  5  cache check
  6  Wave A (7 parallel Tooling queries, DAG-ordered)
  7  join Wave A → _bundle_parsed.json-shaped dict
  8  Wave B (Flow + Apex bodies, parallel)
  9  parse_wave -> declared_action_tree.json
  10 render architecture.md (Batch 2 — stubbed)
  11 finalize (atomic writes + manifest)
  12 emit RESULT
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from functools import partial
from pathlib import Path
from typing import Callable, Tuple

# Phase 2 Batch 1: all cross-module wiring routes through config so a future
# relocation of DATA_ROOT / CACHE_ROOT only touches one file.
from config import (
    CACHE_TTL_DAYS,
    DATA_ROOT,
    SCHEMA_VERSION,
    build_agent_cache_dir,
    build_agent_data_dir,
)
from rest_client import RestClientError, redact_error
from sf_cli import AuthRequired, SfCliError, run_sf
from soql_loader import SoqlParamError

# Phase 2 Batch 1 imports — functional pipeline primitives.
from fetch_soql import (
    fetch_apex_bodies_by_ids,
    fetch_apex_bodies_by_names,
    fetch_bot_definition_details,
    fetch_bot_versions,
    fetch_flow_definition_by_ids,
    fetch_flow_definition_ids_by_names,
    fetch_flow_metadata,
    fetch_functions_by_plugins,
    fetch_planner_attrs,
    fetch_planner_bundle_functions,
    fetch_planner_definition,
    fetch_plugin_functions,
    fetch_plugin_instructions,
    fetch_plugins_by_planner,
)
from metadata_listing import (
    list_prompt_template_metadata,
    retrieve_prompt_templates,
)
from parallel_retrieve import fetch_bodies_parallel
from parse_bundle import classify_generation
from probe_channels import probe_channels
from resolve_invocation_target import looks_like_sf_id, resolve_or_unresolved


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="architecture")
    p.add_argument("--org-alias", required=True)
    p.add_argument("--agent", required=True, dest="agent_api_name")
    p.add_argument("--version", dest="agent_version")
    p.add_argument("--force", action="store_true", dest="force_refresh")
    # --reprobe forces a fresh channel-probe run on pipeline start.
    p.add_argument("--reprobe", action="store_true")
    p.add_argument("--parallelism", type=int, default=5)
    p.add_argument("--max-mermaid-nodes", type=int, default=80)
    p.add_argument("--work-dir", required=True)
    # Runtime-agnostic path overrides. Defaults are
    # ~/.vibe/{data,cache}/investigating-agentforce-architecture/.
    # Other runtimes (AFV OOTB, Codex, Cursor, OpenCode) pass these to land
    # artifacts under their own distribution layout.
    p.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="Override data root (default: ~/.vibe/data/investigating-agentforce-architecture).",
    )
    p.add_argument(
        "--cache-dir",
        type=Path,
        default=None,
        help="Override cache root (default: ~/.vibe/cache/investigating-agentforce-architecture).",
    )
    return p.parse_args(argv)


# ---------------------------------------------------------------------------
# Three-level rebind for --data-dir / --cache-dir overrides.
#
# Python's `from X import Y` snapshots Y into the importer's local namespace.
# Mutating X.Y later does NOT update the importer's local binding. main.py
# does `from config import DATA_ROOT, ...` at module top, so without a
# global rebind, line 2221's `str(DATA_ROOT)` would write the default path
# even when --data-dir was passed.
#
# Levels rebound:
#   1. paths.DATA_ROOT (the source of truth)
#   2. config.DATA_ROOT (the re-export)
#   3. main.DATA_ROOT (THIS module's local snapshot — via global)
#
# Plus: config.PROBE_CACHE_ROOT (derived from CACHE_ROOT at import time).
# ---------------------------------------------------------------------------


def _apply_path_overrides(args: argparse.Namespace) -> None:
    """Apply --data-dir / --cache-dir overrides across all 3 namespace levels.

    Must be called BEFORE any pipeline code reads DATA_ROOT or CACHE_ROOT.
    """
    if not (args.data_dir or args.cache_dir):
        return
    global DATA_ROOT  # rebind level 1: this module
    from _shared import runtime, paths
    import config

    skill_name = "investigating-agentforce-architecture"
    if args.data_dir:
        runtime.set_data_root_override(args.data_dir)
        new_data = runtime.resolve_data_root(skill_name)
        paths.DATA_ROOT = new_data       # level 2: paths module
        config.DATA_ROOT = new_data      # level 3: config module re-export
        DATA_ROOT = new_data              # level 1: main.py local
    if args.cache_dir:
        runtime.set_cache_root_override(args.cache_dir)
        new_cache = runtime.resolve_cache_root(skill_name)
        paths.CACHE_ROOT = new_cache
        config.CACHE_ROOT = new_cache
        config.PROBE_CACHE_ROOT = new_cache / "_channel_probe"


# ---------------------------------------------------------------------------
# Phase 2 Batch 1: credentials
# ---------------------------------------------------------------------------
# Single mutable cell read by `creds_provider`. `refresh_fn` rewrites the
# cell. `retry_on_401` in rest_client invokes refresh_fn for side effect;
# the next invocation of creds_provider picks up the new tuple. See
# rest_client 


def _build_creds_plumbing(
    initial_creds: Tuple[str, str],
    resolve_creds: Callable[[], Tuple[str, str]],
    *,
    dedupe_window_s: float = 1.0,
) -> Tuple[
    Callable[[], Tuple[str, str]],
    Callable[[], Tuple[str, str]],
    "list[Tuple[str, str]]",
]:
    """Build the (creds_provider, refresh_fn, creds_cell) triple.

     + `creds_provider` re-reads `creds_cell`
    on every call so a refresh actually lands in the NEXT SOQL attempt.
    `refresh_fn` is serialized by an internal `threading.Lock` + a
    `time.monotonic()` dedupe window — N concurrent 401s against the same
    stale token collapse to ONE `resolve_creds()` spawn per window. That
    caps real `sf org display` spawns at roughly 1/second regardless of
    pool size.

    Extracted from `main()` so the closure is testable without threading
    a whole pipeline run through argparse + mocks.

    Returns (creds_provider, refresh_fn, creds_cell). The cell is
    returned so callers/tests can inspect the current tuple directly
    (it's the single source of truth the provider reads from).
    """
    creds_cell: list[Tuple[str, str]] = [initial_creds]
    lock = threading.Lock()
    last_refresh_mono = [0.0]

    def creds_provider() -> Tuple[str, str]:
        return creds_cell[0]

    def refresh_fn() -> Tuple[str, str]:
        with lock:
            now = time.monotonic()
            if now - last_refresh_mono[0] < dedupe_window_s:
                # Another thread refreshed within the dedupe window — reuse.
                return creds_cell[0]
            creds_cell[0] = resolve_creds()
            last_refresh_mono[0] = now
            return creds_cell[0]

    return creds_provider, refresh_fn, creds_cell


_REDACTION_MARKER_FRAGMENT = "show-access-token"
"""Substring that uniquely identifies the sf CLI v2 redaction placeholder
(`"[REDACTED] Use 'sf org auth show-access-token' to view"`). We match on
this fragment rather than the full literal because the upstream wording
has shifted between sf CLI builds, but the embedded subcommand name has
been stable since cli#3560 landed."""


def _resolve_creds(org_alias: str) -> Tuple[str, str]:
    """Resolve (instance_url, access_token) for ``org_alias``.

    Two-path strategy per forcedotcom/cli#3560 (effective 2026-05-27):

      1. **Primary** — call ``sf org display`` for instanceUrl, then
         ``sf org auth show-access-token`` for the access token. This is
         the upstream long-term path; ``SF_TEMP_SHOW_SECRETS`` is
         decommissioned in summer 2026.
      2. **Fallback** — if the dedicated command isn't shipped in the
         installed sf CLI version (older releases), fall back to the
         legacy ``sf org display --verbose`` with the
         ``SF_TEMP_SHOW_SECRETS=true`` env var that ``run_sf`` injects
         unconditionally. The fallback is detected by the redaction
         placeholder appearing in the ``accessToken`` field — exact match
         on the substring ``show-access-token`` (see
         ``_REDACTION_MARKER_FRAGMENT``).

    sf_cli.run_sf already redacts stderr on failure paths. Any
    exception surfaces as `AuthRequired` / `SfCliError`; caller routes
    through `_emit_fail`.
    """
    display_data = run_sf("org_display", ORG_ALIAS=org_alias)
    display_result = display_data.get("result") or {}
    instance_url = display_result.get("instanceUrl") or ""
    if not instance_url:
        raise AuthRequired(
            "sf org display returned an incomplete payload (missing instanceUrl)"
        )

    # Primary path: dedicated command. Catches both the unknown-command
    # case (older sf CLI) and any AuthRequired surfaced from the recipe.
    try:
        token_data = run_sf("show_access_token", ORG_ALIAS=org_alias)
    except SfCliError:
        # Older sf CLI versions emit "is not a sf command" on stderr; the
        # recipe surfaces that as SfCliError. Fall back to the
        # SF_TEMP_SHOW_SECRETS path via the org_display payload we
        # already have.
        access_token = display_result.get("accessToken") or ""
    else:
        token_result = token_data.get("result") or {}
        access_token = token_result.get("accessToken") or ""

    # Defensive fallback: if the dedicated command silently returned an
    # empty token OR sf CLI redacted the org_display token to the
    # placeholder, try the org_display payload directly. SF_TEMP_SHOW_SECRETS
    # is set unconditionally by run_sf so this works as long as the env
    # var is still honoured by the installed sf CLI.
    if not access_token or _REDACTION_MARKER_FRAGMENT in access_token:
        legacy_token = display_result.get("accessToken") or ""
        if legacy_token and _REDACTION_MARKER_FRAGMENT not in legacy_token:
            access_token = legacy_token

    if not access_token or _REDACTION_MARKER_FRAGMENT in access_token:
        raise AuthRequired(
            "could not retrieve a usable access token via sf org auth "
            "show-access-token (primary) or sf org display (fallback); "
            "ensure sf CLI is logged in for this org and either the "
            "dedicated command is available or SF_TEMP_SHOW_SECRETS is "
            "still honoured."
        )

    return instance_url, access_token


def _derive_org_ids(org_alias: str) -> Tuple[str, str, str]:
    """Run `sf org display --json` once more for org_id_15 + org_id_18 +
    api_version.

    Reused call: the second `sf org display` is cheap and keeps the
    creds-resolve + org-ids functions uncoupled. When a run passes both
    through together, the overhead is two spawn()s not one — fine given
    the whole pipeline is O(seconds).

    Returns (org_id_15, org_id_18, api_version) — all strings. api_version
    matches `vNN.N` (validated by probe_channels' path builder downstream).

    Gap 3 fix (2026-05-05): returns the 18-char id as well so downstream
    emit helpers can populate the RESULT-block `ORG_ID_18` field. The
    18-char value comes straight from `sf org display`; we do NOT compute
    it from the 15-char prefix.
    """
    data = run_sf("org_display", ORG_ALIAS=org_alias)
    result = data.get("result") or {}
    org_id_18 = result.get("id") or ""
    # SF org id is 18 chars; the 15-char slice is the stable prefix used
    # everywhere in this skill. Fail fast if shorter.
    if len(org_id_18) < 15:
        raise SfCliError(f"sf org display returned malformed id (len={len(org_id_18)})")
    org_id_15 = org_id_18[:15]
    api_version_raw = str(result.get("apiVersion") or "")
    # apiVersion from sf CLI is "60.0" shape; our validator requires "v60.0".
    api_version = api_version_raw if api_version_raw.startswith("v") else f"v{api_version_raw}"
    return org_id_15, org_id_18, api_version


# ---------------------------------------------------------------------------
# Phase 4: bot resolution (in-process; Data API via fetch_soql)
# ---------------------------------------------------------------------------


def _resolve_bot(
    agent_api_name: str,
    explicit_version: str | None,
    creds_provider: Callable[[], Tuple[str, str]],
    refresh_fn: Callable[[], Tuple[str, str]],
    *,
    api_version: str,
) -> dict | None:
    """Resolve (bot_id, version, master_label, planner_name, bot_def_details).

    Returns a dict with:
        bot_id, version, master_label, version_auto_picked (bool),
        bot_definition (dict row from BotDefinition details query),
        all_versions (list of {version, status}) — retained for error ctx.

    Returns None on AGENT_NOT_FOUND. Caller distinguishes by checking the
    absence — not by catching an exception — to keep the error-emit path
    a flat if-chain.

    `api_version` is threaded in from
    `_derive_org_ids`. The Data-API helpers require it — see
    `rest_client.data_query` for why the old hardcoded `v60.0` was
    wrong (real orgs run v66 and expose fields v60 does not).
    """
    versions = fetch_bot_versions(
        agent_api_name, creds_provider,
        api_version=api_version, on_401_refresh=refresh_fn,
    )
    if not versions:
        return None

    # Natural-key sort: v10 > v9 > v2 > v1. Copy the scheme from
    # resolve_bot.py so multi-version bots rank consistently across the
    # in-process + shell-out entry points.
    def _natural_key(v: dict) -> list:
        import re
        dn = v.get("DeveloperName") or ""
        return [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", dn)]

    versions.sort(key=_natural_key, reverse=True)

    picked = None
    if explicit_version:
        for v in versions:
            if v.get("DeveloperName") == explicit_version:
                picked = v
                break
        version_auto_picked = False
    else:
        for v in versions:
            if v.get("Status") == "Active":
                picked = v
                break
        version_auto_picked = True

    if not picked:
        # Signal "version miss" distinctly from "bot miss". Caller emits
        # STATUS=AGENT_VERSION_NOT_FOUND with AVAILABLE_VERSIONS.
        return {
            "bot_id": "",
            "version": explicit_version or "",
            "master_label": "",
            "version_auto_picked": False,
            "all_versions": [
                {
                    "version": v.get("DeveloperName") or "",
                    "status": v.get("Status") or "",
                }
                for v in versions
            ],
            "_version_not_found": True,
        }

    bot_id = picked.get("BotDefinitionId") or ""
    bd_node = picked.get("BotDefinition") or {}
    master_label = bd_node.get("MasterLabel") or ""
    chosen_version = picked.get("DeveloperName") or ""

    # Phase 2 Batch 1: pull BotDefinition metadata once for the tree's
    # `agent` block. Non-fatal if the second query fails — tree falls
    # back to defaults.
    try:
        bot_def = fetch_bot_definition_details(
            agent_api_name, creds_provider,
            api_version=api_version, on_401_refresh=refresh_fn,
        )
    except (RestClientError, SoqlParamError):
        bot_def = None

    # Planner-name resolution moved to Wave A — `fetch_planner_definition`
    # now takes (agent_api_name, chosen_version) and performs a chain-LIKE
    # lookup (`<agent>%\_<vN>`). The canonical planner DeveloperName comes
    # back on the row and propagates downstream via the bundle join.
    return {
        "bot_id": bot_id,
        "version": chosen_version,
        "master_label": master_label,
        "version_auto_picked": version_auto_picked,
        "bot_definition": bot_def or {},
    }


# ---------------------------------------------------------------------------
# Phase 5: cache check
# ---------------------------------------------------------------------------


def _cache_is_fresh(cache_dir: Path) -> dict | None:
    """Return the manifest dict if the cache is hot + fresh, else None.

    Checks: manifest exists, schema_version matches, TTL not expired,
    data_path is a real file. Any failure degrades to `None` so the
    caller falls through to the pipeline-run path.

    Mirrors cache_check.py's shell-level logic; duplicated in-process so
    main.py can branch without shelling out.
    """
    import datetime as dt

    manifest_path = cache_dir / "manifest.json"
    if not manifest_path.is_file():
        return None
    try:
        manifest = json.loads(manifest_path.read_text())
    except (OSError, json.JSONDecodeError):
        return None

    if str(manifest.get("schema_version") or "0") != SCHEMA_VERSION:
        return None

    data_path_s = manifest.get("data_path") or ""
    if not data_path_s or not Path(data_path_s).is_file():
        return None

    try:
        built = dt.datetime.fromisoformat(
            (manifest.get("built_at_utc") or "").replace("Z", "+00:00")
        )
    except ValueError:
        return None

    age_days = (dt.datetime.now(dt.timezone.utc) - built).days
    ttl = int(manifest.get("ttl_days") or CACHE_TTL_DAYS)
    if age_days > ttl:
        return None

    return manifest


# ---------------------------------------------------------------------------
# Phase 6: Wave A
# ---------------------------------------------------------------------------


def _run_wave_a(
    agent_api_name: str,
    version: str | None,
    creds_provider: Callable[[], Tuple[str, str]],
    refresh_fn: Callable[[], Tuple[str, str]],
    *,
    api_version: str,
    parallelism: int = 5,
) -> dict | None:
    """Run the 7-query GenAi normalized DAG in layered parallel steps.

    A1 resolves the live `GenAiPlannerDefinition` from (agent_api_name,
    version) via a chain-LIKE lookup — Agentforce's accretive planner
    naming (v1=`<Agent>`, v2=`<Agent>_v2`, v3=`<Agent>_v2_v3`, ...) means
    (agent, version) alone is the only reliable key. The resolved row's
    `DeveloperName` is the canonical planner_name that propagates
    downstream via the bundle join in `_join_wave_a_to_bundle`.

    Returns a dict:
        {
            "planner": {...},
            "plugins": [...],                  # A2
            "bundle_functions_join": [...],    # A3
            "functions": [...],                # A4
            "instructions": [...],             # A5
            "plugin_functions_join": [...],    # A6
            "attrs": [...],                    # A7
            "unresolved": [...],               # per-channel A2..A6 failures
        }
    Returns None if A1 yields no planner row — caller emits a clean
    error instead of failing later in the join.

    Failures:
      * RestClientError / HTTPError on A1 → propagates. No graceful path
        when the planner itself is unreachable.
      * A2..A6 failures: one failure in a parallel layer doesn't abort
        the layer (fetch_bodies_parallel's contract). The failed channel
        yields an empty data list AND an entry in `unresolved` keyed by
        channel with reason `wave-a-<channel>-failed:<redacted>`. The
        caller folds these into `tree["_unresolved"]` so STATUS flips
        to PARTIAL_OK.
    """
    # A1 — scalar, no parallelism. api_version threads through
    # every fetcher; see module docstring + fetch_soql.py.
    planner = fetch_planner_definition(
        agent_api_name, version, creds_provider,
        api_version=api_version, on_401_refresh=refresh_fn,
    )
    if not planner:
        return None

    planner_id = planner.get("Id")
    if not planner_id:
        # Planner row missing Id — malformed response. Treat as miss.
        return None

    unresolved: list[dict] = []

    # Layer 2: A2 + A3 in parallel
    layer2 = fetch_bodies_parallel(
        [
            partial(
                fetch_plugins_by_planner,
                planner_id, creds_provider,
                api_version=api_version, on_401_refresh=refresh_fn,
            ),
            partial(
                fetch_planner_bundle_functions,
                planner_id, creds_provider,
                api_version=api_version, on_401_refresh=refresh_fn,
            ),
        ],
        max_workers=parallelism,
    )
    plugins = layer2[0][1] if layer2[0][0] else []
    bundle_functions_join = layer2[1][1] if layer2[1][0] else []
    for channel, (ok, r) in zip(("plugins", "bundle-functions"), layer2):
        if not ok:
            entry = {
                "kind": "WAVE_A",
                "channel": channel,
                "reason": f"wave-a-{channel}-failed:{redact_error(r)}",
            }
            preview = getattr(r, "_response_body_preview", None)
            if preview:
                entry["response_body_preview"] = preview
            unresolved.append(entry)

    plugin_ids = [p.get("Id") for p in plugins if p.get("Id")]

    # Layer 3: A4 + A5 + A6 in parallel
    layer3 = fetch_bodies_parallel(
        [
            partial(
                fetch_functions_by_plugins,
                plugin_ids, creds_provider,
                api_version=api_version, on_401_refresh=refresh_fn,
            ),
            partial(
                fetch_plugin_instructions,
                plugin_ids, creds_provider,
                api_version=api_version, on_401_refresh=refresh_fn,
            ),
            partial(
                fetch_plugin_functions,
                plugin_ids, creds_provider,
                api_version=api_version, on_401_refresh=refresh_fn,
            ),
        ],
        max_workers=parallelism,
    )
    functions = layer3[0][1] if layer3[0][0] else []
    instructions = layer3[1][1] if layer3[1][0] else []
    plugin_functions_join = layer3[2][1] if layer3[2][0] else []
    for channel, (ok, r) in zip(
        ("functions", "instructions", "plugin-functions"), layer3,
    ):
        if not ok:
            entry = {
                "kind": "WAVE_A",
                "channel": channel,
                "reason": f"wave-a-{channel}-failed:{redact_error(r)}",
            }
            preview = getattr(r, "_response_body_preview", None)
            if preview:
                entry["response_body_preview"] = preview
            unresolved.append(entry)

    # Layer 4: A7 alone, parent_ids = function_ids. Planner-level attrs
    # returned 0 rows live (a planner never carries direct attrs) so the
    # prior `function_ids ∪ {planner_id}` widened the IN-list for no
    # payoff. Keep the list minimal; dedupe defensively in case a
    # function Id repeats across bundles.
    parent_ids = list(dict.fromkeys(
        f.get("Id") for f in functions if f.get("Id")
    ))
    try:
        attrs = fetch_planner_attrs(
            parent_ids, creds_provider,
            api_version=api_version, on_401_refresh=refresh_fn,
        )
    except (RestClientError, SoqlParamError):
        attrs = []

    return {
        "planner": planner,
        "plugins": plugins,
        "bundle_functions_join": bundle_functions_join,
        "functions": functions,
        "instructions": instructions,
        "plugin_functions_join": plugin_functions_join,
        "attrs": attrs,
        "unresolved": unresolved,
    }


# ---------------------------------------------------------------------------
# Phase 7: join Wave A → _bundle_parsed.json shape
# ---------------------------------------------------------------------------


def _join_wave_a_to_bundle(
    bot_info: dict,
    wave_a: dict,
) -> dict:
    """Reshape normalized Wave-A rows into the bundle dict parse_wave expects.

    `parse_bundle.py` wrote XML-shaped bundles keyed by:
      plannerType, plannerName, generation, description, masterLabel,
      topics[{name, actions[{name, invocationTarget, invocationTargetType, ...}]}],
      plannerActions[{...}]

    We reconstruct that shape from the Tooling rows so parse_wave's
    `init_tree` + `build_root_children` accept the dict unchanged.
    """
    planner = wave_a["planner"]
    planner_type = planner.get("PlannerType") or ""
    generation = classify_generation(planner_type)

    functions_by_id = {f.get("Id"): f for f in wave_a["functions"] if f.get("Id")}
    # Plugin join: map plugin_id → ordered function_ids
    plugin_fn_map: dict[str, list[str]] = {}
    for row in wave_a["plugin_functions_join"]:
        pid = row.get("PluginId")
        fn_id = row.get("Function")
        if pid and fn_id:
            plugin_fn_map.setdefault(pid, []).append(fn_id)

    def _action_dict(fn: dict) -> dict:
        """Shape a GenAiFunctionDefinition row as a bundle-action dict."""
        return {
            "name": fn.get("DeveloperName") or fn.get("Id") or "",
            "localDeveloperName": fn.get("LocalDeveloperName"),
            "masterLabel": fn.get("MasterLabel"),
            "description": fn.get("Description"),
            "invocationTarget": fn.get("InvocationTarget"),
            "invocationTargetType": (fn.get("InvocationTargetType") or "").strip(),
            "source": fn.get("Source"),
        }

    topics = []
    for plugin in wave_a["plugins"]:
        pid = plugin.get("Id")
        fn_ids = plugin_fn_map.get(pid, [])
        actions = [
            _action_dict(functions_by_id[fid])
            for fid in fn_ids if fid in functions_by_id
        ]
        topics.append({
            "name": plugin.get("DeveloperName") or "",
            "localDeveloperName": plugin.get("LocalDeveloperName"),
            "masterLabel": plugin.get("MasterLabel"),
            "description": plugin.get("Description"),
            "canEscalate": bool(plugin.get("CanEscalate")),
            "pluginType": plugin.get("PluginType"),
            "actions": actions,
        })

    # A planner never has direct functions (user invariant, verified
    # against my-org-alias). The previous `PlannerId`-leg query leaked
    # orphan rows (e.g. `AnswerQuestionsWithKnowledge_*`) as root-level
    # children. Key retained for downstream compatibility with callers
    # that read `bundle.get("plannerActions", [])` (parse_wave, a few
    # _route / _normalize paths); always emits an empty list now.
    return {
        "plannerType": planner_type,
        "plannerName": planner.get("DeveloperName"),
        "generation": generation,
        "description": planner.get("Description"),
        "masterLabel": planner.get("MasterLabel"),
        "topics": topics,
        "plannerActions": [],
    }


# ---------------------------------------------------------------------------
# Phase 8: Wave B (Flow + Apex body fetches)
# ---------------------------------------------------------------------------


def _collect_wave_b_targets(bundle_parsed: dict) -> dict[str, list[str]]:
    """Walk topics + plannerActions. Return {kind: [invocation_target, ...]}.

    Deduplicates per-kind. Caller routes each kind through the appropriate
    fetch_soql helper.
    """
    apex_names: set[str] = set()
    apex_ids: set[str] = set()
    flow_names: set[str] = set()
    flow_ids: set[str] = set()
    # Bug 1 fix (2026-05-05): prompt-template targets can arrive as either
    # DeveloperNames (classic) OR 0hf-prefix Ids (observed in live orgs —
    # GenAiFunctionDefinition.InvocationTarget sometimes stores the Id).
    # Route to separate buckets so the Id bucket can be resolved → DevName
    # by _normalize_prompt_template_id_targets before Wave B retrieve.
    prompt_template_ids: set[str] = set()
    unresolved: list[dict] = []

    def _route(target: str, ttype: str) -> None:
        t = (ttype or "").lower()
        if not target:
            return
        # Bug 1 fix: prompt-template targets can arrive as either
        # DeveloperNames (classic) OR 0hf-prefix Ids. The Metadata API
        # retrieve expects DeveloperName; an Id sent verbatim returns
        # zero members and the target stays in _pending_fetches forever.
        # Route 0hf Ids into a separate bucket for post-lookup rewrite
        # via _normalize_prompt_template_id_targets (parallel to the
        # existing _normalize_flow_id_targets pattern).
        if t in ("prompttemplate", "generatepromptresponse") or t.startswith("prompt") or t.startswith("genai"):
            if looks_like_sf_id(target) and target[:3].lower() == "0hf":
                prompt_template_ids.add(target)
            return
        # bundle-declared kinds that never carry an Id.
        # Standard actions store their identifier (not an SF Id) directly
        # in InvocationTarget. Skip the ID router entirely — routing them
        # through resolve_or_unresolved would pollute `_unresolved` with
        # misleading "invalid-id-format" entries.
        if t == "standardinvocableaction":
            return
        # for flow/apex, only consult the ID router
        # when the target actually looks like a Salesforce Id. Classic
        # DeveloperNames (e.g. `MyFlow`, `AGNT_Foo`) don't
        # match the Id shape and used to land in _unresolved with reason
        # `invalid-id-format` — noise. Short-circuit: if it's not an Id
        # shape, skip the router and trust the invocationTargetType.
        if t in ("flow", "apex") and looks_like_sf_id(target):
            kind, _channel = resolve_or_unresolved(target, unresolved)
            if kind == "apex":
                apex_ids.add(target)
                return
            if kind in ("flow_definition", "flow_version"):
                flow_ids.add(target)
                return
            # Unknown Id prefix: resolve_or_unresolved already appended
            # to `unresolved` with reason "unknown-id-prefix:..." — fall
            # through; the target stays unrouted and surfaces there.
            return
        # Classic path: InvocationTarget is a DeveloperName.
        if t == "apex":
            apex_names.add(target)
        elif t == "flow":
            flow_names.add(target)
        # Any other unrecognized type: silently skip. parse_wave will
        # classify the node as UNKNOWN and it surfaces via _kind_counts.

    for topic in bundle_parsed.get("topics", []) or []:
        for a in topic.get("actions", []) or []:
            _route(a.get("invocationTarget") or "",
                   a.get("invocationTargetType") or "")
    for a in bundle_parsed.get("plannerActions", []) or []:
        _route(a.get("invocationTarget") or "",
               a.get("invocationTargetType") or "")

    return {
        "apex_names": sorted(apex_names),
        "apex_ids": sorted(apex_ids),
        "flow_names": sorted(flow_names),
        "flow_ids": sorted(flow_ids),
        "prompt_template_ids": sorted(prompt_template_ids),
        "_unresolved": unresolved,
    }


def _fetch_wave_b_by_names(
    *,
    apex_names: list[str],
    apex_ids: list[str],
    flow_names: list[str],
    flow_ids: list[str],
    prompt_template_ids: list[str] | None = None,
    creds_provider: Callable[[], Tuple[str, str]],
    refresh_fn: Callable[[], Tuple[str, str]],
    api_version: str,
    org_alias: str,
    parallelism: int = 5,
) -> dict:
    """Fire body fetches for an explicit set of Apex/Flow identifiers.

    Factored out of `_run_wave_b` so the iterative Wave B caller
    (`_iterate_wave_b`) can reuse the same shape on subflow rounds —
    every round's fetch concurrency + error handling semantics must
    match the initial round exactly (same parallel layer, same
    unresolved bookkeeping).

    Returns a dict with:
        apex_rows: list of ApexClass records (Name keyed)
        flow_def_rows: list of FlowDefinition records (DeveloperName keyed)
        flow_metadata: dict {version_id: Flow record}
        unresolved: list of {id, reason} from fetch failures

    Any empty input list short-circuits that branch — callers can pass
    subsets safely (e.g. subflow rounds typically pass only flow_names).
    """
    unresolved: list[dict] = []

    # First hop: resolve IDs back to names where applicable. The results
    # merge into the same rowsets the name-keyed path produces.
    # api_version threads into every fetch call.
    if apex_ids:
        try:
            apex_by_id_rows = fetch_apex_bodies_by_ids(
                apex_ids, creds_provider,
                api_version=api_version, on_401_refresh=refresh_fn,
            )
        except (RestClientError, SoqlParamError) as e:
            unresolved.append({"kind": "APEX", "reason": f"apex-by-id-failed:{redact_error(e)}"})
            apex_by_id_rows = []
    else:
        apex_by_id_rows = []

    if flow_ids:
        try:
            flow_def_by_id_rows = fetch_flow_definition_by_ids(
                flow_ids, creds_provider,
                api_version=api_version, on_401_refresh=refresh_fn,
            )
        except (RestClientError, SoqlParamError) as e:
            unresolved.append({"kind": "FLOW", "reason": f"flow-def-by-id-failed:{redact_error(e)}"})
            flow_def_by_id_rows = []
    else:
        flow_def_by_id_rows = []

    # Bug 1 fix: GenAiPromptTemplate is NOT SOQL-queryable (not on Tooling,
    # not on Data API). The only way to resolve Id → DeveloperName is
    # `sf org list metadata -m GenAiPromptTemplate`. We list every prompt
    # template in the org, build an Id → fullName map, filter to the Ids
    # we care about, and project to the same {Id, DeveloperName} shape the
    # rest of the pipeline expects.
    #
    # Failure is non-fatal — the Ids stay in the bucket and surface in
    # `_pending_fetches` rather than masking the real issue.
    if prompt_template_ids:
        try:
            rows = list_prompt_template_metadata(org_alias)
        except (SfCliError, AuthRequired) as e:
            unresolved.append({
                "kind": "PROMPT_TEMPLATE",
                "reason": f"prompt-template-listmetadata-failed:{redact_error(e)}",
            })
            rows = []
        wanted = set(prompt_template_ids)
        prompt_template_id_rows = [
            {"Id": r["id"], "DeveloperName": r["fullName"]}
            for r in rows
            if isinstance(r, dict) and r.get("id") in wanted and r.get("fullName")
        ]
    else:
        prompt_template_id_rows = []

    # Parallel layer: apex-by-name + flow-def-by-name. Empty name lists
    # still produce a task, but the downstream fetcher short-circuits on
    # empty input — the overhead is a single worker dispatch which is
    # cheaper than conditionally building the task list.
    name_layer = fetch_bodies_parallel(
        [
            partial(
                fetch_apex_bodies_by_names,
                apex_names, creds_provider,
                api_version=api_version, on_401_refresh=refresh_fn,
            ),
            partial(
                fetch_flow_definition_ids_by_names,
                flow_names, creds_provider,
                api_version=api_version, on_401_refresh=refresh_fn,
            ),
        ],
        max_workers=parallelism,
    )
    apex_name_rows = name_layer[0][1] if name_layer[0][0] else []
    flow_def_name_rows = name_layer[1][1] if name_layer[1][0] else []
    # Bug D.1 fix: include the response body preview captured by
    # rest_client._query_once when the failure was an HTTPError. Without
    # it, all wave-B 400s collapse to "HTTP Error 400: Bad Request" with
    # no signal about which name caused the malformed query. Falls back
    # to None (existing shape) for non-HTTPError failures.
    for ok, r in (name_layer[0], name_layer[1]):
        if not ok:
            entry = {"kind": "APEX_OR_FLOW", "reason": f"wave-b-batch-failed:{redact_error(r)}"}
            preview = getattr(r, "_response_body_preview", None)
            if preview:
                entry["response_body_preview"] = preview
            unresolved.append(entry)

    apex_rows = [*apex_name_rows, *apex_by_id_rows]
    flow_def_rows = [*flow_def_name_rows, *flow_def_by_id_rows]

    # Second hop: one Flow.Metadata single-row call per ActiveVersionId.
    # Parallelized via fetch_bodies_parallel.
    version_ids = [
        r.get("ActiveVersionId") for r in flow_def_rows
        if r.get("ActiveVersionId")
    ]
    metadata_tasks = [
        partial(
            fetch_flow_metadata,
            vid, creds_provider,
            api_version=api_version, on_401_refresh=refresh_fn,
        )
        for vid in version_ids
    ]
    metadata_results = fetch_bodies_parallel(
        metadata_tasks, max_workers=parallelism,
    )
    flow_metadata: dict[str, dict] = {}
    for vid, (ok, result_or_exc) in zip(version_ids, metadata_results):
        if ok and isinstance(result_or_exc, dict):
            flow_metadata[vid] = result_or_exc
        elif not ok:
            unresolved.append({
                "kind": "FLOW",
                "version_id": vid,
                "reason": f"flow-metadata-failed:{redact_error(result_or_exc)}",
            })

    return {
        "apex_rows": apex_rows,
        "flow_def_rows": flow_def_rows,
        "flow_metadata": flow_metadata,
        "prompt_template_id_rows": prompt_template_id_rows,
        "unresolved": unresolved,
    }


def _run_wave_b(
    bundle_parsed: dict,
    creds_provider: Callable[[], Tuple[str, str]],
    refresh_fn: Callable[[], Tuple[str, str]],
    *,
    api_version: str,
    org_alias: str,
    parallelism: int = 5,
) -> dict:
    """Fire body fetches for every Apex/Flow target in the bundle.

    Returns a dict with:
        apex_rows: list of ApexClass records (Name keyed)
        flow_def_rows: list of FlowDefinition records (DeveloperName keyed)
        flow_metadata: dict {version_id: Flow record}
        unresolved: list of {id, reason} from NGA ID routing

    Only covers the top-level identifiers enumerated directly in
    `bundle_parsed`. Subflows referenced inside fetched Flow.Metadata
    bodies (e.g. shared utility flows like `handleFlowFault`) are
    discovered AFTER this function returns and need a second round of
    fetching — see `_iterate_wave_b`.
    """
    targets = _collect_wave_b_targets(bundle_parsed)

    fetched = _fetch_wave_b_by_names(
        apex_names=targets["apex_names"],
        apex_ids=targets["apex_ids"],
        flow_names=targets["flow_names"],
        flow_ids=targets["flow_ids"],
        prompt_template_ids=targets.get("prompt_template_ids") or [],
        creds_provider=creds_provider,
        refresh_fn=refresh_fn,
        api_version=api_version,
        org_alias=org_alias,
        parallelism=parallelism,
    )

    # Merge the routing-layer unresolved entries (unknown-id-prefix, etc.)
    # with the fetch-layer ones. Order: routing first, fetch second — it's
    # the order they're discovered in the pipeline.
    fetched["unresolved"] = [*targets["_unresolved"], *fetched["unresolved"]]
    return fetched


# ---------------------------------------------------------------------------
# iterative Wave B for nested-subflow discovery
# ---------------------------------------------------------------------------


def _extract_refs_from_flow_metadata(
    flow_metadata: dict[str, dict],
) -> Tuple[set[str], set[str]]:
    """Scan fetched Flow.Metadata dicts for downstream subflow + apex refs.

    Returns `(subflow_names, apex_names)` — both DeveloperName sets.
    Subsets of the data that `_build_flow_children` walks, narrowed to
    just the name-extraction we need before we have enough information
    to build the full child list.

    The extractor is intentionally permissive: missing keys / non-dict
    entries / blank names all drop silently. Parsing shape mirrors the
    `Metadata.actionCalls[]` + `Metadata.subflows[]` layout documented
    in the fetch_flow_metadata docstring and exercised by the
    CLASSIC_FLOW_METADATA fixture.

    Apex discovery from actionCalls is deliberate — a subflow body CAN
    reference a new Apex class the parent tree didn't see (actionType
    == "apex" && actionName == <new class>). Missing those means the
    iterated tree has unexpanded APEX leaves even after flows resolve.
    """
    subflow_names: set[str] = set()
    apex_names: set[str] = set()
    for record in (flow_metadata or {}).values():
        if not isinstance(record, dict):
            continue
        md = record.get("Metadata")
        if not isinstance(md, dict):
            continue
        for ac in md.get("actionCalls") or []:
            if not isinstance(ac, dict):
                continue
            if (ac.get("actionType") or "") == "apex":
                nm = ac.get("actionName") or ""
                if nm:
                    apex_names.add(nm)
        for sub in md.get("subflows") or []:
            if not isinstance(sub, dict):
                continue
            nm = sub.get("flowName") or ""
            if nm:
                subflow_names.add(nm)
    return subflow_names, apex_names


def _iterate_wave_b(
    initial_wave_b: dict,
    creds_provider: Callable[[], Tuple[str, str]],
    refresh_fn: Callable[[], Tuple[str, str]],
    *,
    api_version: str,
    org_alias: str,
    parallelism: int = 5,
    max_iterations: int = 5,
) -> dict:
    """Drive Wave B to fixed-point for nested subflow / apex discovery.

    The initial `_run_wave_b` call only enumerates top-level flow refs
    from `bundle_parsed`. When those flow bodies reference subflows
    (via `Metadata.subflows[].flowName`) or new Apex classes (via
    `Metadata.actionCalls[]`), their bodies were never fetched — so
    `_build_flow_children` would shape them as leaf nodes with no
    children even though the real subtree has content.

    Per round:
      1. Extract subflow + apex refs from the current flow_metadata.
      2. Diff against already-fetched DeveloperNames.
      3. If diff empty → converged, return.
      4. Fetch the diff via `_fetch_wave_b_by_names`.
      5. Merge into the running wave_b dict.
      6. Repeat.

    Safety:
      * `max_iterations=5` — empirically 2-3 is enough on real bots
        (handleFlowFault etc.). Hit the cap → remaining unfetched names
        surface via parse_wave's `_pending_fetches.FLOW` (their names
        are never added to `visited_by_kind["FLOW"]` since they're
        absent from `flow_def_rows`) and a marker lands in `unresolved`
        for triage.
      * Fetch failures in a round are tolerated by `_fetch_wave_b_by_names`
        — the affected names simply don't make it into `flow_def_rows`
        and naturally surface as pending.

    Returns the (possibly enlarged) wave_b dict; caller mutates nothing.
    """
    if max_iterations <= 0:
        return initial_wave_b

    # Running state: copy so callers see their original dict untouched.
    merged_apex_rows = list(initial_wave_b.get("apex_rows") or [])
    merged_flow_def_rows = list(initial_wave_b.get("flow_def_rows") or [])
    merged_flow_metadata: dict[str, dict] = dict(
        initial_wave_b.get("flow_metadata") or {}
    )
    merged_unresolved = list(initial_wave_b.get("unresolved") or [])

    fetched_flow_names: set[str] = {
        r.get("DeveloperName") for r in merged_flow_def_rows
        if r.get("DeveloperName")
    }
    fetched_apex_names: set[str] = {
        r.get("Name") for r in merged_apex_rows if r.get("Name")
    }

    for _round in range(max_iterations):
        subflow_names, apex_names = _extract_refs_from_flow_metadata(
            merged_flow_metadata
        )
        new_flow_names = sorted(subflow_names - fetched_flow_names)
        new_apex_names = sorted(apex_names - fetched_apex_names)
        if not new_flow_names and not new_apex_names:
            # Fixed-point reached.
            return {
                "apex_rows": merged_apex_rows,
                "flow_def_rows": merged_flow_def_rows,
                "flow_metadata": merged_flow_metadata,
                "prompt_template_id_rows": initial_wave_b.get(
                    "prompt_template_id_rows"
                ) or [],
                "unresolved": merged_unresolved,
            }

        round_result = _fetch_wave_b_by_names(
            apex_names=new_apex_names,
            apex_ids=[],
            flow_names=new_flow_names,
            flow_ids=[],
            creds_provider=creds_provider,
            refresh_fn=refresh_fn,
            api_version=api_version,
            org_alias=org_alias,
            parallelism=parallelism,
        )
        merged_apex_rows.extend(round_result["apex_rows"])
        merged_flow_def_rows.extend(round_result["flow_def_rows"])
        merged_flow_metadata.update(round_result["flow_metadata"])
        merged_unresolved.extend(round_result["unresolved"])

        # Update fetched-name bookkeeping — we only track rows we
        # actually received (fetch failure ⇒ not fetched ⇒ will be
        # retried next round, bounded by the iteration cap).
        for r in round_result["flow_def_rows"]:
            nm = r.get("DeveloperName")
            if nm:
                fetched_flow_names.add(nm)
        for r in round_result["apex_rows"]:
            nm = r.get("Name")
            if nm:
                fetched_apex_names.add(nm)

    # Iteration cap hit. Scan one more time to see what's still pending
    # so we can surface it clearly in `unresolved`. These names will also
    # land in `_pending_fetches.FLOW` via parse_wave's visited-vs-pending
    # diff (they're absent from flow_def_rows ⇒ absent from
    # visited_by_kind["FLOW"]).
    subflow_names, apex_names = _extract_refs_from_flow_metadata(
        merged_flow_metadata
    )
    still_pending_flows = sorted(subflow_names - fetched_flow_names)
    still_pending_apex = sorted(apex_names - fetched_apex_names)
    for nm in still_pending_flows:
        merged_unresolved.append({
            "kind": "FLOW",
            "api_name": nm,
            "reason": f"wave-b-iteration-cap:{max_iterations}-rounds-exhausted",
        })
    for nm in still_pending_apex:
        merged_unresolved.append({
            "kind": "APEX",
            "api_name": nm,
            "reason": f"wave-b-iteration-cap:{max_iterations}-rounds-exhausted",
        })

    return {
        "apex_rows": merged_apex_rows,
        "flow_def_rows": merged_flow_def_rows,
        "flow_metadata": merged_flow_metadata,
        "prompt_template_id_rows": initial_wave_b.get(
            "prompt_template_id_rows"
        ) or [],
        "unresolved": merged_unresolved,
    }


# ---------------------------------------------------------------------------
# build flow_children from in-memory Wave B metadata
# ---------------------------------------------------------------------------


def _build_flow_children(
    flow_metadata: dict[str, dict],
    flow_def_rows: list[dict],
) -> dict[str, list[dict]]:
    """Produce `{flow_developer_name: [child_ref, ...]}` from Wave B data.

    Mirrors the shape `parse_wave.harvest_waves` produces from on-disk
    flow XML, but sourced from the in-memory `Flow.Metadata` JSON that
    Wave B already fetched via the Tooling REST API (the `Metadata`
    complexvalue field decodes to a plain dict — see
    `fetch_flow_metadata` + test fixture `CLASSIC_FLOW_METADATA`). The
    shape parse_wave expects per child:

        {"kind": "APEX",            "api_name": <name>, "element_name": <elem>}
        {"kind": "PROMPT_TEMPLATE", "api_name": <name>, "element_name": <elem>}
        {"kind": "STANDARD_ACTION", "api_name": <name>, "element_name": <elem>,
         "invocation_type": <actionType>}
        {"kind": "FLOW",            "api_name": <target_flow_name>,
         "element_name": <elem>}
        {"kind": "UNKNOWN",         "api_name": <name>, "element_name": <elem>,
         "invocation_type": <actionType>}

    Keying is by FlowDefinition.DeveloperName (not ActiveVersionId) —
    `walk_and_inflate` looks up by `leaf["api_name"]`, which the bundle
    populates with the Flow's DeveloperName.

    Flows whose ActiveVersionId is missing (inactive / draft-only) or
    whose fetched metadata was None are silently skipped — they never
    had a body to walk. actionCall entries missing required fields
    (`actionType`, `actionName`, or `name`) degrade to UNKNOWN via
    `classify_action_call`, which already tolerates blanks. Subflow
    entries missing `flowName` are dropped entirely (no api_name to
    descend into).
    """
    import parse_wave

    # Build ActiveVersionId → DeveloperName lookup. FlowDefinition rows with
    # no ActiveVersionId (inactive flows, or flows only materializing a
    # Latest version) skip this map — `flow_metadata` is keyed on
    # ActiveVersionId too, so they drop out symmetrically.
    version_to_name: dict[str, str] = {}
    for row in flow_def_rows or []:
        vid = row.get("ActiveVersionId")
        dev_name = row.get("DeveloperName")
        if vid and dev_name:
            version_to_name[vid] = dev_name

    flow_children: dict[str, list[dict]] = {}
    for version_id, record in (flow_metadata or {}).items():
        flow_name = version_to_name.get(version_id)
        if not flow_name:
            # No matching FlowDefinition row — can't key the children list.
            continue
        if not isinstance(record, dict):
            continue
        md = record.get("Metadata") or {}
        if not isinstance(md, dict):
            continue

        children: list[dict] = []

        # actionCalls — each entry has `name` (element id), `actionType`,
        # `actionName`. `actionType`/`actionName` may be missing on edge
        # cases (flow authored against an older API version that omits
        # the field); classify_action_call tolerates empty strings and
        # will return UNKNOWN.
        for ac in md.get("actionCalls") or []:
            if not isinstance(ac, dict):
                continue
            element_name = ac.get("name")
            action_type = ac.get("actionType") or ""
            action_name = ac.get("actionName") or ""
            if not element_name:
                # An unnamed actionCall can't be addressed in the tree
                # view; drop rather than synthesize a placeholder.
                continue
            children.append(
                parse_wave.classify_action_call(action_type, action_name, element_name)
            )

        # subflows — each has `name` (element id) + `flowName` (target).
        for sub in md.get("subflows") or []:
            if not isinstance(sub, dict):
                continue
            element_name = sub.get("name")
            target = sub.get("flowName")
            if not element_name or not target:
                continue
            children.append({
                "kind": "FLOW",
                "element_name": element_name,
                "api_name": target,
            })

        flow_children[flow_name] = children

    return flow_children


# ---------------------------------------------------------------------------
# Flow-ID → DeveloperName normalization
# ---------------------------------------------------------------------------


def _normalize_flow_id_targets(bundle_parsed: dict, flow_def_rows: list[dict]) -> None:
    """Rewrite action invocationTargets that are Flow IDs → DeveloperNames.

    Mutates `bundle_parsed` in place. No-op when no flow_def_rows match.

    Classic bots occasionally store 300Uv-prefix FlowDefinition IDs or
    301-prefix Flow version IDs in `GenAiFunctionDefinition.InvocationTarget`
    instead of DeveloperNames. Wave B's FlowDefinition fetch (by-id branch)
    already resolved those IDs; the rows carry both Id + ActiveVersionId +
    DeveloperName. We build a bi-directional map (300-id → name, 301-id →
    name via ActiveVersionId) and rewrite every action whose target is a
    known ID.

    Unmatched IDs (Flow genuinely not queryable or belongs to a managed
    package we can't see) stay as-is so the pipeline surfaces them in
    _pending_fetches rather than silently discarding.
    """
    # Build ID → DeveloperName lookup from both Id and ActiveVersionId keys.
    id_to_name: dict[str, str] = {}
    for row in flow_def_rows or []:
        dev_name = row.get("DeveloperName")
        if not dev_name:
            continue
        row_id = row.get("Id")
        if row_id:
            id_to_name[row_id] = dev_name
        active_ver = row.get("ActiveVersionId")
        if active_ver:
            id_to_name[active_ver] = dev_name

    if not id_to_name:
        return

    def _rewrite_action(action: dict) -> None:
        target = action.get("invocationTarget")
        ttype = (action.get("invocationTargetType") or "").strip().lower()
        if ttype != "flow" or not isinstance(target, str):
            return
        resolved = id_to_name.get(target)
        if resolved:
            # Preserve the original ID for traceability — consumers that
            # need it can still read `_original_invocation_target_id`.
            action["_original_invocation_target_id"] = target
            action["invocationTarget"] = resolved

    for topic in bundle_parsed.get("topics") or []:
        for action in topic.get("actions") or []:
            _rewrite_action(action)
    for action in bundle_parsed.get("plannerActions") or []:
        _rewrite_action(action)


def _normalize_prompt_template_id_targets(
    bundle_parsed: dict, prompt_template_rows: list[dict],
) -> None:
    """Rewrite action invocationTargets that are GenAiPromptTemplate Ids
    (0hf-prefix) → DeveloperNames.

    Bug 1 fix (2026-05-05): when GenAiFunctionDefinition.InvocationTarget
    stores a 0hf-prefix prompt template Id instead of a DeveloperName
    (observed in live my-org-alias org), the Metadata API retrieve
    can't match it — Wave B enqueues the Id as-is and the template
    stays in `_pending_fetches.PROMPT_TEMPLATE` forever.

    Parallel to `_normalize_flow_id_targets`: build an Id → DeveloperName
    map from `list_prompt_template_metadata` rows (projected to
    {Id, DeveloperName} shape by `_fetch_wave_b_by_names`), mutate the
    bundle in place. Unmatched Ids stay as-is (genuinely missing template,
    or the Metadata API listing failed).
    """
    id_to_name: dict[str, str] = {}
    for row in prompt_template_rows or []:
        row_id = row.get("Id")
        dev_name = row.get("DeveloperName")
        if row_id and dev_name:
            id_to_name[row_id] = dev_name

    if not id_to_name:
        return

    def _rewrite_action(action: dict) -> None:
        target = action.get("invocationTarget")
        ttype = (action.get("invocationTargetType") or "").strip().lower()
        # Match the same ttype predicate used by _route for prompt-template
        # targets — otherwise a Flow action whose target happens to collide
        # with a prompt template Id (unlikely but possible) wouldn't be
        # caught. _route's predicate is the authority on what's a prompt.
        is_prompt_ttype = (
            ttype in ("prompttemplate", "generatepromptresponse")
            or ttype.startswith("prompt")
            or ttype.startswith("genai")
        )
        if not is_prompt_ttype or not isinstance(target, str):
            return
        resolved = id_to_name.get(target)
        if resolved:
            action["_original_invocation_target_id"] = target
            action["invocationTarget"] = resolved

    for topic in bundle_parsed.get("topics") or []:
        for action in topic.get("actions") or []:
            _rewrite_action(action)
    for action in bundle_parsed.get("plannerActions") or []:
        _rewrite_action(action)


def _normalize_apex_id_targets(
    bundle_parsed: dict, apex_by_id_rows: list[dict],
) -> None:
    """Rewrite action invocationTargets that are Apex (01p-prefix Id)
    -> ApexClass Name.

    Gap B fix (2026-05-05): when GenAiFunctionDefinition.InvocationTarget
    stores a 01p-prefix ApexClass Id instead of a class Name (observed in
    live my-org-alias org, e.g. 01p000000000000AAA ->
    MyController), downstream Wave B body retrieval enqueues
    the Id as-is into `_pending_fetches.APEX` and the tree renders the raw
    Id instead of the class name.

    Parallel to `_normalize_prompt_template_id_targets`: build an Id ->
    Name map from `fetch_apex_bodies_by_ids` rows (ApexClass uses `Name`,
    not `DeveloperName`), mutate the bundle in place. Unmatched Ids stay
    as-is (genuinely missing class, or the by-Id fetch failed).
    """
    id_to_name: dict[str, str] = {}
    for row in apex_by_id_rows or []:
        row_id = row.get("Id")
        class_name = row.get("Name")
        if row_id and class_name:
            id_to_name[row_id] = class_name

    if not id_to_name:
        return

    def _rewrite_action(action: dict) -> None:
        target = action.get("invocationTarget")
        ttype = (action.get("invocationTargetType") or "").strip().lower()
        # Match the same ttype predicate used by _route for apex targets.
        # Mirrors the prompt-template normalizer's ttype gate so a Flow
        # action whose target happens to collide with an ApexClass Id
        # (unlikely but possible) isn't miscaught.
        is_apex_ttype = ttype in ("apex", "apexaction") or ttype.startswith("apex")
        if not is_apex_ttype or not isinstance(target, str):
            return
        # Prefix-gate the rewrite to the ApexClass key prefix (01p).
        # Mirrors the `target[:3].lower() == "01p"` check in _collect_wave_b_targets.
        if target[:3].lower() != "01p":
            return
        resolved = id_to_name.get(target)
        if resolved:
            action["_original_invocation_target_id"] = target
            action["invocationTarget"] = resolved

    for topic in bundle_parsed.get("topics") or []:
        for action in topic.get("actions") or []:
            _rewrite_action(action)
    for action in bundle_parsed.get("plannerActions") or []:
        _rewrite_action(action)


# ---------------------------------------------------------------------------
# Signature derivation — Apex + Flow (rendered in Section 7 of architecture.md)
# ---------------------------------------------------------------------------


def _derive_apex_signature(apex_row: dict) -> str | None:
    """Return a compact one-line signature string for an Apex class, or None.

    Sourced from `SymbolTable.methods[]` on the ApexClass Tooling row. Picks
    the "primary" method:
      1. Prefer a method annotated `@InvocableMethod` (what Flow / Agentforce
         actually invoke — typically exactly one per Agentforce-relevant
         class).
      2. Else prefer a `global` or `public static` non-constructor method.
      3. Else fall back to the first method in SymbolTable source order.

    Format: `<modifiers> <returnType> <name>(<p1_type> <p1_name>, ...)`. If
    `returnType` is absent (constructor shape) it's omitted. Parameters are
    rendered as `<type> <name>`; empty param list becomes `()`.

    Returns None when `SymbolTable` is missing/empty or contains no method
    candidates. Body parsing is intentionally NOT attempted — too brittle.
    """
    if not isinstance(apex_row, dict):
        return None
    symbol_table = apex_row.get("SymbolTable")
    if not isinstance(symbol_table, dict):
        return None
    methods = symbol_table.get("methods")
    if not isinstance(methods, list) or not methods:
        return None

    def _is_invocable(m: dict) -> bool:
        anns = m.get("annotations") or []
        for ann in anns:
            if isinstance(ann, dict):
                if (ann.get("name") or "").lower() == "invocablemethod":
                    return True
            elif isinstance(ann, str):
                if ann.lower() == "invocablemethod":
                    return True
        return False

    def _is_constructor(m: dict) -> bool:
        # SymbolTable represents constructors via `constructors[]`, but some
        # payloads fold them into `methods[]` with a null/empty returnType.
        rt = m.get("returnType")
        return not rt

    def _is_promoted(m: dict) -> bool:
        mods = [str(x).lower() for x in (m.get("modifiers") or [])]
        if _is_constructor(m):
            return False
        if "global" in mods:
            return True
        if "public" in mods and "static" in mods:
            return True
        return False

    candidates = [m for m in methods if isinstance(m, dict)]
    if not candidates:
        return None

    primary: dict | None = next((m for m in candidates if _is_invocable(m)), None)
    if primary is None:
        primary = next((m for m in candidates if _is_promoted(m)), None)
    if primary is None:
        # Last-resort: first method. Skip if it's purely a private/local helper
        # with no chance of being the public entry point — those add noise.
        primary = candidates[0]
        mods = [str(x).lower() for x in (primary.get("modifiers") or [])]
        if "private" in mods and not _is_invocable(primary):
            return None

    modifiers = [str(x) for x in (primary.get("modifiers") or [])]
    return_type = primary.get("returnType") or ""
    name = primary.get("name") or ""
    if not name:
        return None

    params_out: list[str] = []
    for p in primary.get("parameters") or []:
        if not isinstance(p, dict):
            continue
        p_type = p.get("type") or ""
        p_name = p.get("name") or ""
        if p_type and p_name:
            params_out.append(f"{p_type} {p_name}")
        elif p_type:
            params_out.append(p_type)
        elif p_name:
            params_out.append(p_name)
    params_str = ", ".join(params_out)

    parts: list[str] = []
    if modifiers:
        parts.append(" ".join(modifiers))
    if return_type:
        parts.append(return_type)
    parts.append(f"{name}({params_str})")
    return " ".join(parts)


def _derive_flow_signature(flow_metadata_record: dict) -> str | None:
    """Return a compact signature string for a Flow, or None.

    Sourced from `Metadata.variables[]` on the Tooling Flow record
    (`fetch_flow_metadata` output — the `flow_metadata_record` is the
    full Tooling row, and `.Metadata` is the decoded complexvalue dict).

    Flow variables carry boolean `isInput` / `isOutput` flags. A variable
    with `isInput: true` contributes to the `in:` side; `isOutput: true`
    contributes to the `out:` side; a variable can set both (round-trip)
    and will appear on BOTH sides. Variables with neither flag are locals
    and are skipped.

    Format: `in: <name>: <type>[, ...] | out: <name>: <type>[, ...]`.
    If only one side has entries, only that side is emitted. Returns None
    when neither side has entries.

    Collection variables render as `List<<dataType>>`. sObject variables
    use the `objectType` field (e.g. `List<Case>` rather than
    `List<SObject>`). Insertion order from `variables[]` is preserved —
    we deliberately do not sort, to keep the signature aligned with the
    flow author's declared order.
    """
    if not isinstance(flow_metadata_record, dict):
        return None
    md = flow_metadata_record.get("Metadata")
    if not isinstance(md, dict):
        # Test convenience: accept a bare Metadata dict, not just the full row.
        if "variables" in flow_metadata_record:
            md = flow_metadata_record
        else:
            return None

    variables = md.get("variables") or []
    if not isinstance(variables, list):
        return None

    def _render_type(var: dict) -> str:
        data_type = (var.get("dataType") or "").strip()
        obj_type = (var.get("objectType") or "").strip()
        apex_class = (var.get("apexClass") or "").strip()
        dt_lower = data_type.lower()
        # sObject variables carry the concrete SObject name in `objectType`
        # (e.g. `Case`). Apex-typed variables carry the concrete class name
        # in `apexClass` (e.g. `CX_OrgSelector.Org`). Without the apexClass
        # branch, collections of Apex-typed values render as the useless
        # `List<Apex>` instead of `List<CX_OrgSelector.Org>`.
        if dt_lower == "sobject" and obj_type:
            base = obj_type
        elif dt_lower == "apex" and apex_class:
            base = apex_class
        else:
            base = data_type or "Object"
        if var.get("isCollection"):
            return f"List<{base}>"
        return base

    inputs: list[str] = []
    outputs: list[str] = []
    for v in variables:
        if not isinstance(v, dict):
            continue
        name = v.get("name")
        if not name:
            continue
        rendered = f"{name}: {_render_type(v)}"
        if v.get("isInput"):
            inputs.append(rendered)
        if v.get("isOutput"):
            outputs.append(rendered)

    if not inputs and not outputs:
        return None

    parts: list[str] = []
    if inputs:
        parts.append("in: " + ", ".join(inputs))
    if outputs:
        parts.append("out: " + ", ".join(outputs))
    return " | ".join(parts)


def _stamp_signatures(
    node: dict,
    apex_sigs: dict[str, str],
    flow_sigs: dict[str, str],
    flow_reasons: dict[str, str] | None = None,
) -> None:
    """Recursively stamp `node["signature"]` on matching APEX / FLOW leaves.

    Shared utility flows / helpers that appear in multiple branches all
    receive the same stamped signature — they point at the same
    FlowDefinition / ApexClass, so the signature is the same.

    Gap 2 fix (2026-05-05): when a FLOW leaf has no signature but *does*
    have an explanation in `flow_reasons` (e.g. managed-pkg body not
    retrievable via the Data API fallback), stamp `node["_signature_reason"]`
    so the renderer can distinguish a silent hole from a known limitation.
    """
    if not isinstance(node, dict):
        return
    kind = node.get("kind")
    name = node.get("api_name")
    if kind == "APEX" and name and name in apex_sigs:
        node["signature"] = apex_sigs[name]
    elif kind == "FLOW" and name:
        if name in flow_sigs:
            node["signature"] = flow_sigs[name]
        elif flow_reasons and name in flow_reasons:
            node["_signature_reason"] = flow_reasons[name]
    for child in node.get("children") or []:
        _stamp_signatures(child, apex_sigs, flow_sigs, flow_reasons)


# ---------------------------------------------------------------------------
# Gap C (2026-05-05): prompt template body retrieve + stamp
# ---------------------------------------------------------------------------


def _is_prompt_ttype(ttype: str) -> bool:
    """Mirror the ttype predicate used by `_route` /
    `_normalize_prompt_template_id_targets` so collection + rewrite +
    retrieve all recognize the same action kind."""
    t = (ttype or "").strip().lower()
    return (
        t in ("prompttemplate", "generatepromptresponse")
        or t.startswith("prompt")
        or t.startswith("genai")
    )


def _collect_prompt_template_names(bundle_parsed: dict) -> set[str]:
    """Walk topics + plannerActions, collect prompt-template DeveloperNames.

    Called AFTER `_normalize_prompt_template_id_targets` — any 0hf-prefix
    Id that resolved via Wave B's Id-list-metadata should already be a
    DeveloperName. Defensive: drop anything that still looks Id-shaped
    (0hf prefix) so we don't send a malformed
    `GenAiPromptTemplate:0hfUv...` spec to the retrieve CLI.
    """
    names: set[str] = set()

    def _collect(action: dict) -> None:
        ttype = action.get("invocationTargetType") or ""
        if not _is_prompt_ttype(ttype):
            return
        target = action.get("invocationTarget")
        if not isinstance(target, str) or not target:
            return
        if target[:3].lower() == "0hf":
            # Id never got rewritten — the list_metadata lookup missed it
            # (managed-pkg template, permission issue). Skip; it stays in
            # _pending_fetches with the Id as the key.
            return
        names.add(target)

    for topic in bundle_parsed.get("topics") or []:
        for action in topic.get("actions") or []:
            _collect(action)
    for action in bundle_parsed.get("plannerActions") or []:
        _collect(action)
    return names


def _collect_flow_nested_prompt_template_names(
    node: dict,
    already_retrieved: dict[str, dict],
    out: set[str],
) -> None:
    """Walk the finalized tree and collect PROMPT_TEMPLATE leaves whose
    body wasn't stamped during the bundle-scoped retrieve.

    Bundle-scoped `_collect_prompt_template_names` only sees prompt
    templates declared as top-level topic/planner InvocationTargets.
    Prompt templates referenced from inside a Flow (via a
    `generatePromptResponse` actionCall) are discovered later during
    Wave B's BFS of flow XML and end up as PROMPT_TEMPLATE leaves in the
    tree — but their names never reached the first retrieve, so their
    `_body_available` stays False and content is silently lost.

    Defensive: drop 0hf-Id-shape names (managed-pkg templates whose Id
    never rewrote to a DeveloperName) — sending
    `GenAiPromptTemplate:0hfUv...` to the retrieve CLI yields a
    malformed spec; the Id stays in `_pending_fetches.PROMPT_TEMPLATE`
    as intended.
    """
    if not isinstance(node, dict):
        return
    if node.get("kind") == "PROMPT_TEMPLATE":
        name = node.get("api_name")
        if (
            isinstance(name, str)
            and name
            and name[:3].lower() != "0hf"
            and not node.get("_body_available", False)
        ):
            body = already_retrieved.get(name)
            if not (body and body.get("content")):
                out.add(name)
    for child in node.get("children") or []:
        _collect_flow_nested_prompt_template_names(child, already_retrieved, out)


def _stamp_prompt_template_bodies(
    node: dict,
    bodies: dict[str, dict],
) -> None:
    """Recursively stamp prompt-template body fields onto matching
    PROMPT_TEMPLATE leaves.

    For each leaf whose `api_name` matches a key in `bodies`, attach:
      - master_label, content, inputs, active_version_identifier
      - _body_available = True

    Leaves with no matching body get `_body_available = False` so the
    renderer can distinguish "no body retrieved" from "body successfully
    empty". Shared templates appearing in multiple branches receive the
    same stamped body (they reference the same DeveloperName).
    """
    if not isinstance(node, dict):
        return
    kind = node.get("kind")
    name = node.get("api_name")
    if kind == "PROMPT_TEMPLATE" and name:
        body = bodies.get(name)
        if body:
            node["master_label"] = body.get("masterLabel")
            node["content"] = body.get("content")
            node["inputs"] = body.get("inputs") or []
            node["active_version_identifier"] = body.get(
                "activeVersionIdentifier"
            )
            node["_body_available"] = True
        else:
            node["_body_available"] = False
    for child in node.get("children") or []:
        _stamp_prompt_template_bodies(child, bodies)


# ---------------------------------------------------------------------------
# Phase 9: build declared_action_tree.json via parse_wave primitives
# ---------------------------------------------------------------------------


def _run_parse_wave(
    bot_info: dict,
    bundle_parsed: dict,
    wave_b: dict,
    args: argparse.Namespace,
    work_dir: Path,
) -> dict:
    """Invoke parse_wave's init_tree + root-children builder in-process.

    parse_wave was written to be invoked as a subprocess with env vars
    carrying AGENT_API_NAME / AGENT_VERSION / BOT_ID / etc. For Phase 2
    Batch 1 we set those env vars transiently and call the module's
    public helpers — no subprocess overhead, same behavior.
    """
    import parse_wave

    # parse_wave reads these via os.environ.
    prior_env = {
        "AGENT_API_NAME": os.environ.get("AGENT_API_NAME"),
        "AGENT_VERSION": os.environ.get("AGENT_VERSION"),
        "BOT_ID": os.environ.get("BOT_ID"),
        "BOT_MASTER_LABEL": os.environ.get("BOT_MASTER_LABEL"),
        "VERSION_AUTO_PICKED": os.environ.get("VERSION_AUTO_PICKED"),
    }
    os.environ["AGENT_API_NAME"] = args.agent_api_name
    os.environ["AGENT_VERSION"] = bot_info["version"]
    os.environ["BOT_ID"] = bot_info["bot_id"]
    os.environ["BOT_MASTER_LABEL"] = bot_info["master_label"]
    os.environ["VERSION_AUTO_PICKED"] = "true" if bot_info["version_auto_picked"] else "false"

    try:
        # Persist the bundle for parse_wave's finalize_cap path.
        bundle_out = work_dir / "_bundle_parsed.json"
        bundle_out.write_text(json.dumps(bundle_parsed, indent=2))

        # Persist a fake _bot_definition.json so init_tree reads real
        # metadata for the agent block.
        bd_file = work_dir / "_bot_definition.json"
        bd_file.write_text(json.dumps({
            "result": {"records": [bot_info.get("bot_definition") or {}]},
        }))

        tree = parse_wave.init_tree(work_dir, bundle_parsed)

        # Build root children + track bundle-derived BFS refs.
        # call the public `empty_kind_sets` /
        # `BFS_KINDS` symbols — reaching into `parse_wave._*` reopened the
        # leading-underscore surface that closed for `redact_text`.
        visited_by_kind = parse_wave.empty_kind_sets()
        aux_visited: set[tuple[str, str]] = set()
        children, bundle_refs = parse_wave.build_root_children(
            bundle_parsed, visited_by_kind, aux_visited,
        )
        tree["root"]["children"] = children

        # Merge Flow metadata into flow_children. parse_wave wants this as
        # `{flow_name: [child_refs]}`. Build it from the in-memory
        # `Flow.Metadata` JSON Wave B already fetched — the Tooling REST
        # API decodes the `Metadata` complexvalue field into a plain dict,
        # so no XML parsing is needed (see `_build_flow_children` +
        # fixture `CLASSIC_FLOW_METADATA`). Without this, every FLOW leaf
        # in `metadata_tree.json` shipped with `children: []` and the
        # user's recursive-tree view was flat.
        flow_children = _build_flow_children(
            wave_b["flow_metadata"], wave_b["flow_def_rows"],
        )

        # BFS routing for bundle refs.
        pending_by_kind, _cycles = parse_wave.bfs_step(
            parse_wave.empty_kind_sets(), visited_by_kind, bundle_refs,
        )

        # Depth-cap accumulator threaded through inflate.
        depth_cap_pending = parse_wave.empty_kind_sets()
        parse_wave.walk_and_inflate(
            tree["root"], flow_children, pending_out=depth_cap_pending,
        )

        # Merge any Apex / Flow we actually fetched into visited — they
        # no longer count as pending.
        for row in wave_b["apex_rows"]:
            nm = row.get("Name")
            if nm:
                visited_by_kind["APEX"].add(nm)
        for row in wave_b["flow_def_rows"]:
            nm = row.get("DeveloperName")
            if nm:
                visited_by_kind["FLOW"].add(nm)
        # Gap C (2026-05-05): prompt templates whose bodies we retrieved
        # count as visited and must drop out of _pending_fetches.
        # Templates the retrieve didn't return (permission / managed-pkg /
        # retrieve failure) stay out of `visited` so they surface there,
        # mirroring the Flow-by-name "no rows = stays pending" pattern.
        prompt_template_bodies = wave_b.get("prompt_template_bodies") or {}
        for name in prompt_template_bodies:
            if name:
                visited_by_kind["PROMPT_TEMPLATE"].add(name)

        # Stamp Apex / Flow signatures onto every matching tree node so
        # render_architecture.py can populate Section 7. Wave B already
        # fetched SymbolTable (Apex) + Metadata (Flow); we just project it
        # onto `{kind, api_name}` leaves here. Shared utility flows /
        # helpers that appear in multiple positions all receive the same
        # stamped signature — that's the correct behavior (same definition).
        apex_sigs: dict[str, str] = {}
        for row in wave_b["apex_rows"]:
            nm = row.get("Name")
            if not nm:
                continue
            sig = _derive_apex_signature(row)
            if sig:
                apex_sigs[nm] = sig

        flow_sigs: dict[str, str] = {}
        # Gap 2 fix (2026-05-05): explain silent signature holes. Managed
        # flows come back from `fetch_flow_definition_ids_by_names` via the
        # FlowDefinitionView fallback with _source="FlowDefinitionView",
        # ActiveVersionId=None, _body_available=False — by design, since
        # managed-pkg flow bodies are IP-protected. Previously every such
        # row produced an unexplained "_Signature not captured._" in the
        # rendered markdown. Now we surface the structural reason.
        #
        # For the generic "no usable metadata record" case (Tooling row
        # present but flow_metadata missing — e.g. metadata fetch failed
        # or the flow has no active version at all) we also stamp a reason
        # so the renderer never silently drops the node.
        flow_reasons: dict[str, str] = {}
        flow_metadata_by_vid = wave_b.get("flow_metadata") or {}
        for row in wave_b["flow_def_rows"]:
            dev_name = row.get("DeveloperName") or row.get("_bare_developer_name")
            if not dev_name:
                continue
            source = row.get("_source") or ""
            if source == "FlowDefinitionView":
                ns = row.get("NamespacePrefix") or ""
                reason = (
                    f"managed-package (ns={ns}); body not retrievable via Tooling/Metadata API"
                    if ns
                    else "managed-package; body not retrievable via Tooling/Metadata API"
                )
                flow_reasons[dev_name] = reason
                continue
            active_ver = row.get("ActiveVersionId")
            if not active_ver:
                flow_reasons[dev_name] = "no active version"
                continue
            md_record = flow_metadata_by_vid.get(active_ver)
            if not md_record:
                flow_reasons[dev_name] = "flow metadata fetch returned no record"
                continue
            sig = _derive_flow_signature(md_record)
            if sig:
                flow_sigs[dev_name] = sig
            else:
                flow_reasons[dev_name] = "flow metadata has no in/out params"

        _stamp_signatures(tree["root"], apex_sigs, flow_sigs, flow_reasons)

        # Gap C: stamp retrieved prompt-template bodies onto the tree.
        # Leaves with a matching body gain content/master_label/inputs;
        # leaves without get `_body_available = False` so the renderer
        # can distinguish "retrieve missed" from "body truly absent".
        _stamp_prompt_template_bodies(tree["root"], prompt_template_bodies)

        for kind in parse_wave.BFS_KINDS:
            pending_by_kind[kind] |= depth_cap_pending.get(kind, set())

        depth_cap_tripped = any(depth_cap_pending[k] for k in parse_wave.BFS_KINDS)

        tree["_pending_fetches"] = {
            k: sorted(pending_by_kind.get(k, set()) - visited_by_kind.get(k, set()))
            for k in parse_wave.BFS_KINDS
        }

        any_pending = any(tree["_pending_fetches"][k] for k in parse_wave.BFS_KINDS)
        if depth_cap_tripped:
            tree["_partial"] = True
            tree["_partial_reason"] = "max-depth-cap"
        elif any_pending:
            tree["_partial"] = True
            if not tree.get("_partial_reason"):
                tree["_partial_reason"] = "pending-refs"
        else:
            tree["_partial"] = False
            tree["_partial_reason"] = None

        # Surface Wave-B-level unresolved items (e.g. unknown ID prefixes).
        for u in wave_b.get("unresolved", []) or []:
            tree.setdefault("_unresolved", []).append(u)

        node_count, depth, kind_counts = parse_wave.compute_stats(tree["root"])
        tree["node_count"] = node_count
        tree["depth"] = depth
        tree["_kind_counts"] = kind_counts

        all_visited: set[tuple[str, str]] = set(aux_visited)
        for kind, names in visited_by_kind.items():
            for n in names:
                all_visited.add((kind, n))
        tree["_visited"] = [list(v) for v in sorted(all_visited)]

        tree_path = work_dir / "declared_action_tree.json"
        tmp = tree_path.with_suffix(tree_path.suffix + ".tmp")
        tmp.write_text(json.dumps(tree, indent=2))
        os.replace(tmp, tree_path)
        return tree
    finally:
        # Restore env so test runners that reuse the process don't leak
        # state across invocations.
        for k, v in prior_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


# ---------------------------------------------------------------------------
# Phase 11: finalize
# ---------------------------------------------------------------------------


def _swap_dir_atomic(target: Path, staging: Path) -> None:
    """Per-file overwrite from `staging` into `target` — preserves any
    unrelated sibling content already present in `target`.

    P0 fix (2026-05-05): the prior implementation did
    ``os.replace(target, backup); os.replace(staging, target)`` — an
    atomic whole-directory swap that was correct in isolation but
    DESTRUCTIVE of co-tenants. The `<agent>__<ver>/` dir is co-tenanted:
    co-tenants write per-session subdirs
    (`<session_id>/`) alongside architecture's files. Swapping the whole
    directory silently wiped every cached session trace.

    New behavior: iterate `staging`'s immediate children and `os.replace`
    each one into `target`. The directory `target` itself is never
    moved or deleted, so any session subdirs under it survive.

    Trade-off: the old helper supported atomic rollback (restore from
    backup on failure). The per-file pattern cannot — a crash partway
    through the loop leaves architecture's output in a split state
    (some new files, some old). This is acceptable because:
      - per-file `os.replace` is still atomic (no empty-path window
        for any individual file, so the "concurrent reader sees
        empty dir" bug that  addressed is still closed);
      - `last_built_at.txt` is written LAST by the caller, so
        consumers can treat its presence as the success sentinel;
      - architecture is re-runnable, co-tenant session traces are not.

    Callers must still guarantee `staging` is on the same filesystem as
    `target` (helper constructs `staging` as a sibling of `target`, so
    that holds by construction).
    """
    import shutil

    if not staging.is_dir():
        raise OSError(f"staging dir missing: {staging}")

    target.mkdir(parents=True, exist_ok=True)

    for src in staging.iterdir():
        dst = target / src.name
        # Clear any existing destination so `os.replace` lands cleanly
        # when the incoming type differs (file replacing dir or vice
        # versa). For same-type overwrites `os.replace` would handle
        # files on its own, but directories require an empty target or
        # same-name existing dir — safer to unify both here.
        if dst.exists() or dst.is_symlink():
            if dst.is_dir() and not dst.is_symlink():
                shutil.rmtree(dst)
            else:
                dst.unlink()
        os.replace(src, dst)

    # Staging should be empty now; best-effort teardown.
    try:
        staging.rmdir()
    except OSError:
        shutil.rmtree(staging, ignore_errors=True)


def _run_finalize(
    data_dir: Path,
    cache_dir: Path,
    tree: dict,
    work_dir: Path,
    agent_api_name: str,
    agent_version: str,
    planner_name: str,
) -> None:
    """Atomic-write tree + summary + manifest. Keep it simple.

    For Phase 2 Batch 1 we replicate finalize.py's essential behavior
    (tree + manifest) but skip the sf_meta mirror — there's no
    sf_meta dir when main.py runs the pipeline SOQL-first. Metadata-API
    retrieves land in Batch 2/3.

    both `data_dir` and `cache_dir` are swapped
    via `_swap_dir_atomic` to close the "rmtree then rename" empty-dir
    window. A crash during the second swap restores the original from
    the staging-sibling `.<name>.backup.<pid>` rather than leaving an
    empty path.
    """
    import datetime as dt
    import shutil

    built_at = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    tree_base = f"{agent_api_name}_{agent_version}_metadata_tree"

    # Finalize's _partial computation. Mirrors finalize.py:109-117 — both
    # buckets (_pending_fetches AND _unresolved) must be empty for a
    # clean run. _unresolved captures wave-B failures (HTTP 4xx,
    # iteration-cap exhaustion, managed-flow filter misses) that have
    # already been moved out of _pending_fetches; checking only the
    # latter would silently call a partial run "converged".
    planner_ok = bool(planner_name)
    pending_total = sum(len(v) for v in (tree.get("_pending_fetches") or {}).values())
    unresolved_count = len(tree.get("_unresolved") or [])
    waves_converged = pending_total == 0 and unresolved_count == 0
    tree["_partial"] = not (planner_ok and waves_converged)
    tree.pop("_visited", None)

    # Pin deterministic child ordering as the last assembly step before
    # the authoritative write. Shared with the standalone `finalize.py`
    # subprocess so both paths produce byte-identical trees. Downstream
    # readers see one canonical order from disk; they do not re-sort.
    from finalize import sort_tree_in_place
    sort_tree_in_place(tree.get("root") or {})

    # staging names are siblings (same parent) so the
    # `os.replace` used by `_swap_dir_atomic` is a same-filesystem atomic
    # rename. `.staging.<pid>` disambiguates concurrent pipelines on the
    # same host.
    data_parent = data_dir.parent
    data_staging = data_parent / f".{data_dir.name}.staging.{os.getpid()}"
    if data_staging.exists():
        shutil.rmtree(data_staging)
    data_staging.mkdir(parents=True)
    tree_out = data_staging / f"{tree_base}.json"
    tree_out.write_text(json.dumps(tree, indent=2))

    # P2.2-1: phase 10 (architecture.md renderer). Imported lazily so a
    # renderer bug can't break the existing Batch 1 pipeline before the
    # tree JSON has been written — the tree + manifest remain the
    # authoritative outputs, architecture.md is a derived artifact.
    #
    # filename now self-identifying —
    # `{agent_api_name}_{agent_version}_architecture.md` (e.g.
    # `MyAgent_v5_architecture.md`). Same shape as the tree JSON,
    # minus the `_metadata_tree` suffix. The `.error` sidecar follows
    # the same shape.
    arch_base = f"{agent_api_name}_{agent_version}"
    arch_name = f"{arch_base}_architecture.md"
    arch_error_name = f"{arch_base}_architecture.md.error"
    try:
        from render_architecture import render as _render_architecture
        _render_architecture(tree_out, data_staging / arch_name)
    except Exception as e:
        # Best-effort: a render failure downgrades the run to "tree OK,
        # architecture skipped" rather than aborting finalize. The
        # reason string surfaces in the next-run logs for triage.
        (data_staging / arch_error_name).write_text(
            f"render_architecture failed: {type(e).__name__}: {e}\n"
        )

    # dropped `{tree_base}.summary.md` from the output contract —
    # was a redundant summary of the tree JSON; consumers should read the
    # JSON directly. See CHANGELOG for details.
    (data_staging / "last_built_at.txt").write_text(built_at + "\n")

    _swap_dir_atomic(data_dir, data_staging)

    # CACHE_DIR staging — same two-phase swap.
    cache_parent = cache_dir.parent
    cache_staging = cache_parent / f".{cache_dir.name}.staging.{os.getpid()}"
    if cache_staging.exists():
        shutil.rmtree(cache_staging)
    cache_staging.mkdir(parents=True)

    manifest = {
        "built_at_utc": built_at,
        "schema_version": tree.get("_schema_version", SCHEMA_VERSION),
        "agent": tree.get("agent", {}),
        "node_count": tree.get("node_count", 0),
        "depth": tree.get("depth", 0),
        "kind_counts": tree.get("_kind_counts", {}),
        "ttl_days": CACHE_TTL_DAYS,
        "data_path": str(data_dir / f"{tree_base}.json"),
        "partial": tree.get("_partial", False),
        "unresolved_count": len(tree.get("_unresolved", []) or []),
    }
    (cache_staging / "manifest.json").write_text(json.dumps(manifest, indent=2))
    # Copy tree + bundle sidecar for cache replay
    (cache_staging / "declared_action_tree.json").write_text(json.dumps(tree, indent=2))
    bundle_src = work_dir / "_bundle_parsed.json"
    if bundle_src.is_file():
        (cache_staging / "_bundle_parsed.json").write_text(bundle_src.read_text())

    _swap_dir_atomic(cache_dir, cache_staging)


# ---------------------------------------------------------------------------
# Emit helpers
# ---------------------------------------------------------------------------


def _read_built_at_utc(cache_dir: Path | None) -> str:
    if cache_dir is None:
        return ""
    try:
        return json.loads((cache_dir / "manifest.json").read_text()).get("built_at_utc", "") or ""
    except (OSError, ValueError):
        return ""


def _emit_fail(
    args: argparse.Namespace,
    extra_ctx: dict | None,
    status: str,
    error_detail: str = "",
    start_epoch: float | None = None,
) -> int:
    """Write an .emit_ctx.json with STATUS=<status>.

    STATUS enum (from emit_result.py):
        OK, PARTIAL_OK, INVALID_INPUT, AUTH_REQUIRED, AGENT_NOT_FOUND,
        AGENT_VERSION_NOT_FOUND, RETRIEVE_FAILED, WRITE_FAILED.

    For probe failures, the plan's description suggested SCHEMA_DRIFT
    but emit_result doesn't carry that enum value. We map probe failures
    to RETRIEVE_FAILED with an explicit error_detail — the RESULT block's
    ERROR_DETAIL carries the "schema-drift" reason. Adding a new enum
    value would require touching emit_result (out of scope P1 primitive);
    the mapping preserves emit_result's existing contract.

    Returns the exit code the caller should return.
    """
    work_dir = Path(args.work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    ctx = {
        "status": status,
        "error_detail": error_detail,
        "agent_api_name": args.agent_api_name,
        "agent_version": args.agent_version or "",
        "version_auto_picked": False,
        "agent_generation": "unknown",
        "bot_id": "",
        "org_id_15": "",
        "org_id_18": "",
        "cache_hit": False,
        "cached_at_utc": "",
        "cache_path": "",
        "output_json_path": "",
        "output_summary_path": "",
        "node_count": 0,
        "depth": 0,
        "partial": status == "PARTIAL_OK",
        "partial_reason": "",
        "pending_fetches_count": 0,
        "unresolved_count": 0,
        "available_bots": "",
        "available_versions": "",
        # Bug fix (2026-05-05): start_epoch captured once at pipeline entry
        # and threaded through every _emit_* helper. Previously each helper
        # re-captured time.time() AFTER the pipeline had already run, so
        # emit_result.py computed WALL_TIME_SECONDS against a timestamp taken
        # ~tens of seconds AFTER the real work finished and reported ~0.0s.
        "start_epoch": start_epoch if start_epoch is not None else time.time(),
        "data_dir": str(DATA_ROOT),
        "work_dir": str(work_dir),
        # failure paths never invoke the renderer.
        "architecture_path": "",
        "render_failed": False,
        "render_error_detail": "",
    }
    if extra_ctx:
        ctx.update(extra_ctx)
    (work_dir / ".emit_ctx.json").write_text(json.dumps(ctx, indent=2))
    return 1


def _emit_cache_hit(
    args: argparse.Namespace,
    data_dir: Path,
    cache_dir: Path,
    manifest: dict,
    start_epoch: float | None = None,
    *,
    org_id_15: str = "",
    org_id_18: str = "",
) -> int:
    work_dir = Path(args.work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    agent_version = manifest.get("agent", {}).get("version", "")
    tree_base = f"{args.agent_api_name}_{agent_version}_metadata_tree"

    # on a cache hit the renderer is NOT re-invoked — but the
    # architecture.md from the prior run is a legitimate output of the
    # cached data_dir. Surface it when present, skip the .error sidecar
    # since render_failed semantics only apply to THIS run's renderer.
    # filename rename to `{agent}_{ver}_architecture.md` —
    # NB `tree_base` above still carries the `_metadata_tree` suffix (it
    # names the JSON); architecture filenames drop the suffix.
    arch_base = f"{args.agent_api_name}_{agent_version}"
    arch_path = data_dir / f"{arch_base}_architecture.md"
    architecture_path = str(arch_path) if arch_path.is_file() else ""

    ctx = {
        "status": "OK",
        "error_detail": "",
        "agent_api_name": args.agent_api_name,
        "agent_version": manifest.get("agent", {}).get("version", ""),
        "version_auto_picked": manifest.get("agent", {}).get("_version_auto_picked", False),
        "agent_generation": manifest.get("agent", {}).get("generation", "unknown"),
        "bot_id": manifest.get("agent", {}).get("bot_id", ""),
        "org_id_15": org_id_15,
        "org_id_18": org_id_18,
        "cache_hit": True,
        "cached_at_utc": manifest.get("built_at_utc", ""),
        "cache_path": str(cache_dir),
        "output_json_path": str(data_dir / f"{tree_base}.json"),
        # summary.md dropped from the output contract. Field kept
        # empty for RESULT-block shape stability.
        "output_summary_path": "",
        "node_count": int(manifest.get("node_count", 0) or 0),
        "depth": int(manifest.get("depth", 0) or 0),
        "partial": bool(manifest.get("partial", False)),
        "partial_reason": "",
        "pending_fetches_count": 0,
        "unresolved_count": int(manifest.get("unresolved_count", 0) or 0),
        "available_bots": "",
        "available_versions": "",
        # Bug fix (2026-05-05): see _emit_fail note — start_epoch is captured
        # at pipeline entry and threaded through. Cache-hit paths are short-
        # running so the drift is smaller, but the field should still reflect
        # the invocation's real wall time.
        "start_epoch": start_epoch if start_epoch is not None else time.time(),
        "data_dir": str(data_dir),
        "work_dir": str(work_dir),
        # architecture-render outcome signals. render_failed
        # stays False for cache replays — that flag tracks THIS run's
        # renderer, not the cached run's; a cache hit implies no retry.
        "architecture_path": architecture_path,
        "render_failed": False,
        "render_error_detail": "",
    }
    (work_dir / ".emit_ctx.json").write_text(json.dumps(ctx, indent=2))
    return 0


def _emit_ok(
    args: argparse.Namespace,
    data_dir: Path,
    tree: dict,
    bot_info: dict,
    org_id_15: str,
    start_epoch: float | None = None,
    cache_dir: Path | None = None,
    org_id_18: str = "",
) -> int:
    work_dir = Path(args.work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    agent_version = bot_info["version"]
    tree_base = f"{args.agent_api_name}_{agent_version}_metadata_tree"
    pending_total = sum(len(v) for v in (tree.get("_pending_fetches") or {}).values())

    # surface architecture-render outcome on the success path.
    # finalize writes either `{agent}_{ver}_architecture.md` (render OK) or
    # `{agent}_{ver}_architecture.md.error` (render raised) into the
    # data_dir; we read whichever is present and plumb the fields through
    # the ctx. emit_result consumes the boolean to auto-promote
    # OK -> PARTIAL_OK when the tree landed but the diagram render failed.
    # filename rename — self-identifying shape. `tree_base` above
    # is for the JSON path (carries `_metadata_tree`); architecture uses
    # the unsuffixed agent+version base.
    arch_base = f"{args.agent_api_name}_{agent_version}"
    arch_path = data_dir / f"{arch_base}_architecture.md"
    arch_sidecar = data_dir / f"{arch_base}_architecture.md.error"
    architecture_path = str(arch_path) if arch_path.is_file() else ""
    render_failed = arch_sidecar.is_file()
    render_error_detail = ""
    if render_failed:
        try:
            raw = arch_sidecar.read_text(errors="replace").strip()
        except OSError:
            raw = ""
        if raw:
            # Single-line cap, 200-char truncation, scrubbed via the
            # rest_client redactor (same contract as write_emit_ctx).
            from rest_client import redact_text as _redact
            render_error_detail = _redact(raw.splitlines()[0])[:200]

    ctx = {
        "status": "PARTIAL_OK" if tree.get("_partial") else "OK",
        "error_detail": "",
        "agent_api_name": args.agent_api_name,
        "agent_version": bot_info["version"],
        "version_auto_picked": bot_info["version_auto_picked"],
        "agent_generation": tree.get("agent", {}).get("generation", "unknown"),
        "bot_id": bot_info["bot_id"],
        "org_id_15": org_id_15,
        # Gap 3 fix (2026-05-05): the 18-char id is available from
        # `sf org display` in _derive_org_ids but was previously dropped.
        # Now threaded from pipeline entry so the RESULT contract field is
        # actually populated on success.
        "org_id_18": org_id_18,
        "cache_hit": False,
        "cached_at_utc": _read_built_at_utc(cache_dir),
        # Gap 4 fix (2026-05-05): non-cache-hit runs write the manifest into
        # `cache_dir` (see _run_finalize) so the field should point at the
        # same path a subsequent invocation would probe. Caller passes the
        # already-computed cache_dir; we skip the leading-empty fallback
        # only when it's truly unknown (shouldn't happen on _emit_ok).
        "cache_path": str(cache_dir) if cache_dir is not None else "",
        "output_json_path": str(data_dir / f"{tree_base}.json"),
        # summary.md dropped from the output contract.
        "output_summary_path": "",
        "node_count": int(tree.get("node_count", 0) or 0),
        "depth": int(tree.get("depth", 0) or 0),
        "partial": bool(tree.get("_partial", False)),
        "partial_reason": tree.get("_partial_reason") or "",
        "pending_fetches_count": pending_total,
        "unresolved_count": len(tree.get("_unresolved", []) or []),
        "available_bots": "",
        "available_versions": "",
        # Bug fix (2026-05-05): see _emit_fail note — start_epoch threaded
        # from pipeline entry so WALL_TIME_SECONDS reflects the full run.
        "start_epoch": start_epoch if start_epoch is not None else time.time(),
        "data_dir": str(data_dir),
        "work_dir": str(work_dir),
        # architecture-render outcome signals.
        "architecture_path": architecture_path,
        "render_failed": render_failed,
        "render_error_detail": render_error_detail,
    }
    (work_dir / ".emit_ctx.json").write_text(json.dumps(ctx, indent=2))
    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def _run_pipeline(args: argparse.Namespace, start_epoch: float) -> int:  # noqa: PLR0911, PLR0915
    """Execute the 12-phase pipeline. Extracted from `main()` so the
    top-level entry point can wrap any uncaught exception in a RESULT
    block .

    Every structured failure path here already routes through
    `_emit_fail` and returns a non-zero exit code. Exceptions that
    escape this function are, by definition, bugs we hadn't thought of
    yet — `main()` catches them so the skill contract (RESULT block on
    every exit path) holds regardless.
    """
    work_dir = Path(args.work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    # Phase 2 Batch 1: single creds cell shared between provider + refresh.
    # Refresh mutates the cell; provider reads it on every attempt — this
    # is the `` refresh contract.
    #
    # Wave B fetches run N concurrent Flow.Metadata
    # calls through parallel_retrieve.fetch_bodies_parallel. `refresh_fn`
    # serializes behind a lock + 1-second monotonic dedupe window so
    # concurrent 401s don't each fork their own `sf org display`. See
    # `_build_creds_plumbing`.
    try:
        initial = _resolve_creds(args.org_alias)
    except (AuthRequired, SfCliError) as e:
        return _emit_fail(
            args, None, "AUTH_REQUIRED",
            error_detail=redact_error(e),
            start_epoch=start_epoch,
        )

    creds_provider, refresh_fn, _creds_cell = _build_creds_plumbing(
        initial,
        resolve_creds=lambda: _resolve_creds(args.org_alias),
    )

    # Phase 2.5: derive org_id_15 + org_id_18 + api_version
    try:
        org_id_15, org_id_18, api_version = _derive_org_ids(args.org_alias)
    except (AuthRequired, SfCliError) as e:
        return _emit_fail(
            args, None, "AUTH_REQUIRED",
            error_detail=redact_error(e),
            start_epoch=start_epoch,
        )

    # Phase 3: probe channels
    channels = probe_channels(
        args.org_alias, org_id_15, api_version,
        force_refresh=args.reprobe,
    )
    if channels.get("status") == "PROBE_FAILED":
        # Plan suggested STATUS=SCHEMA_DRIFT; emit_result's STATUS enum
        # doesn't include that value. Mapping to RETRIEVE_FAILED with a
        # "schema-drift" ERROR_DETAIL preserves the existing enum
        # contract while surfacing the cause. A future batch may add
        # SCHEMA_DRIFT to the enum; that change lives in emit_result.
        missing = [
            (sobj, e.get("mandatory_missing", []))
            for sobj, e in (channels.get("channels") or {}).items()
            if e.get("mandatory_missing")
        ]
        return _emit_fail(
            args, None, "RETRIEVE_FAILED",
            error_detail=f"schema-drift: mandatory fields missing: {missing[:3]}",
            start_epoch=start_epoch,
        )

    # Phase 4: resolve bot + version
    try:
        bot_info = _resolve_bot(
            args.agent_api_name, args.agent_version,
            creds_provider, refresh_fn,
            api_version=api_version,
        )
    except (RestClientError, SoqlParamError) as e:
        return _emit_fail(
            args, None, "AUTH_REQUIRED",
            error_detail=redact_error(e),
            start_epoch=start_epoch,
        )

    if bot_info is None:
        # AGENT_NOT_FOUND — emit without a list-of-available-bots context.
        # The unbounded bot-list SELECT was removed (LIMIT-less unfiltered
        # query on BotDefinition). Operators can run their own SOQL if
        # they need to enumerate available bots.
        return _emit_fail(
            args,
            {"org_id_15": org_id_15},
            "AGENT_NOT_FOUND",
            error_detail=f"BotDefinition.DeveloperName '{args.agent_api_name}' not found",
            start_epoch=start_epoch,
        )

    if bot_info.get("_version_not_found"):
        vers_csv = ",".join(
            f"{v['version']}({v['status']})" for v in bot_info.get("all_versions", [])
        )
        return _emit_fail(
            args,
            {"available_versions": vers_csv, "org_id_15": org_id_15},
            "AGENT_VERSION_NOT_FOUND",
            error_detail=f"No matching BotVersion (requested: {args.agent_version!r})",
            start_epoch=start_epoch,
        )

    # Phase 5: cache check
    data_dir = build_agent_data_dir(org_id_15, args.agent_api_name, bot_info["version"])
    cache_dir = build_agent_cache_dir(org_id_15, args.agent_api_name, bot_info["version"])
    if not args.force_refresh:
        manifest = _cache_is_fresh(cache_dir)
        if manifest is not None:
            return _emit_cache_hit(
                args, data_dir, cache_dir, manifest,
                start_epoch=start_epoch,
                org_id_15=org_id_15,
                org_id_18=org_id_18,
            )

    # Phase 6: Wave A — 7 queries, DAG-ordered parallel layers. A1 now
    # takes (agent_api_name, version) and resolves the canonical planner
    # DeveloperName from the live chain naming invariant (v1 = <Agent>,
    # vN = <Agent>...%\_vN); the row's DeveloperName becomes the
    # authoritative `planner_name` for finalize/render downstream.
    try:
        wave_a = _run_wave_a(
            args.agent_api_name, bot_info["version"],
            creds_provider, refresh_fn,
            api_version=api_version,
            parallelism=args.parallelism,
        )
    except (RestClientError, SoqlParamError) as e:
        return _emit_fail(
            args, None, "RETRIEVE_FAILED",
            error_detail=f"wave-a-failed:{redact_error(e)}",
            start_epoch=start_epoch,
        )

    if wave_a is None:
        return _emit_fail(
            args, {"org_id_15": org_id_15},
            "AGENT_NOT_FOUND",
            error_detail=(
                f"GenAiPlannerDefinition chain not found for "
                f"agent={args.agent_api_name!r} version={bot_info['version']!r}"
            ),
            start_epoch=start_epoch,
        )

    # Phase 7: join Wave A → bundle-shaped dict
    bundle_parsed = _join_wave_a_to_bundle(bot_info, wave_a)

    # Phase 8: Wave B — body fetches
    try:
        wave_b = _run_wave_b(
            bundle_parsed,
            creds_provider, refresh_fn,
            api_version=api_version,
            org_alias=args.org_alias,
            parallelism=args.parallelism,
        )
    except (RestClientError, SoqlParamError) as e:
        return _emit_fail(
            args, None, "RETRIEVE_FAILED",
            error_detail=f"wave-b-failed:{redact_error(e)}",
            start_epoch=start_epoch,
        )

    # Phase 8.5: iterative Wave B — follow subflow + apex refs from fetched
    # Flow.Metadata bodies until fixed-point. Without this pass, shared
    # utility flows (handleFlowFault) and nested subflows ship as empty
    # leaves even though their bodies are reachable via Tooling API.
    # Iteration cap safeguards against pathological flow graphs.
    try:
        wave_b = _iterate_wave_b(
            wave_b,
            creds_provider, refresh_fn,
            api_version=api_version,
            org_alias=args.org_alias,
            parallelism=args.parallelism,
            max_iterations=5,
        )
    except (RestClientError, SoqlParamError) as e:
        return _emit_fail(
            args, None, "RETRIEVE_FAILED",
            error_detail=f"wave-b-iter-failed:{redact_error(e)}",
            start_epoch=start_epoch,
        )

    # Surface Wave-A layer-2/3 task failures alongside Wave-B's so the
    # downstream `_run_parse_wave` sweep folds them into `tree["_unresolved"]`
    # and `_partial_reason` flips to PARTIAL_OK.
    wave_a_unresolved = wave_a.get("unresolved") or []
    if wave_a_unresolved:
        wave_b["unresolved"] = [*wave_a_unresolved, *(wave_b.get("unresolved") or [])]

    # normalize Flow-ID InvocationTargets → DeveloperName.
    # Classic ReAct bots occasionally store NGA-style 300Uv-prefix Flow IDs
    # in GenAiFunctionDefinition.InvocationTarget (observed in one real-org
    # benchmark run, 6 flows out of 6). Wave B's fetch_flow_definition_by_ids
    # successfully resolves them, but the resolved DeveloperName never
    # propagates back into bundle_parsed — so parse_wave sees the raw ID as
    # the flow's api_name, which never matches visited["FLOW"] (keyed on
    # DeveloperName), and every such flow ends up in _pending_fetches.
    # Result: PARTIAL_OK on what should be OK, plus unreadable Flow IDs in
    # rendered architecture.md.
    #
    # Fix: rewrite bundle_parsed's action invocationTarget in-place from
    # ID → DeveloperName using wave_b["flow_def_rows"] (both the IN-by-names
    # and the IN-by-ids branches populate it). Unresolved IDs (Flow not
    # found in the org) stay as-is and will land in _pending_fetches as
    # intended (they really are unresolved).
    _normalize_flow_id_targets(bundle_parsed, wave_b["flow_def_rows"])

    # Bug 1 fix (2026-05-05): analogous rewrite for GenAiPromptTemplate Ids.
    # Wave B's prompt-template Id fetch resolves 0hf-prefix Ids to
    # DeveloperNames; without this rewrite the bundle would enqueue the
    # raw Id into _pending_fetches.PROMPT_TEMPLATE and the downstream
    # Metadata retrieve would never match.
    _normalize_prompt_template_id_targets(
        bundle_parsed, wave_b.get("prompt_template_id_rows") or [],
    )

    # Gap B fix (2026-05-05): analogous rewrite for ApexClass Ids.
    # Wave B's fetch_apex_bodies_by_ids resolves 01p-prefix Ids to ApexClass
    # Name; without this rewrite the bundle would enqueue the raw Id into
    # _pending_fetches.APEX and the tree would render the bare Id instead
    # of the class name.
    _normalize_apex_id_targets(
        bundle_parsed, wave_b.get("apex_rows") or [],
    )

    # Gap C fix (2026-05-05): retrieve GenAiPromptTemplate bodies.
    # GenAiPromptTemplate is NOT SOQL-queryable (Tooling or Data API). The
    # only way to fetch the body is `sf project retrieve start
    # --metadata GenAiPromptTemplate:<name>,...`. After
    # _normalize_prompt_template_id_targets has rewritten 0hf-Ids to
    # DeveloperNames, collect the names and retrieve in a single sf
    # subprocess call. The resulting bodies get stashed on wave_b so
    # _run_parse_wave can stamp them onto PROMPT_TEMPLATE leaves (parallel
    # to the Apex/Flow signature stamping pattern).
    prompt_template_names = _collect_prompt_template_names(bundle_parsed)
    prompt_template_bodies: dict[str, dict] = {}
    if prompt_template_names:
        try:
            prompt_template_bodies = retrieve_prompt_templates(
                args.org_alias,
                sorted(prompt_template_names),
                work_dir,
            )
        except AuthRequired:
            raise
        except SfCliError as e:
            wave_b.setdefault("unresolved", []).append({
                "kind": "PROMPT_TEMPLATE",
                "reason": f"prompt-template-retrieve-failed:{redact_error(e)}",
            })
    wave_b["prompt_template_bodies"] = prompt_template_bodies

    # Phase 9: parse_wave -> declared_action_tree.json
    try:
        tree = _run_parse_wave(bot_info, bundle_parsed, wave_b, args, work_dir)
    except (OSError, KeyError) as e:
        return _emit_fail(
            args, None, "WRITE_FAILED",
            error_detail=f"parse-wave-failed:{redact_error(e)}",
            start_epoch=start_epoch,
        )

    # Phase 10: render architecture.md — invoked inline from _run_finalize
    # so the write lands in the same staging dir as the tree JSON and
    # participates in the atomic _swap_dir_atomic below. See P2.2-1.

    # Flow-nested prompt-template catch-up (2026-05-05). The bundle-scoped
    # retrieve at step 1 above only covers prompt templates declared as
    # top-level topic/planner InvocationTargets. Templates referenced from
    # inside a Flow (via a `generatePromptResponse` actionCall) are
    # discovered during parse_wave's BFS of flow XML — too late for the
    # first retrieve. Without this second pass their `_body_available`
    # stays False and the md renders `_Body not retrieved._` with no
    # PARTIAL flag (silent content loss). `_stamp_prompt_template_bodies`
    # is idempotent, so re-stamping already-stamped leaves is safe.
    flow_nested_names: set[str] = set()
    _collect_flow_nested_prompt_template_names(
        tree["root"], prompt_template_bodies, flow_nested_names,
    )
    if flow_nested_names:
        try:
            more_bodies = retrieve_prompt_templates(
                args.org_alias,
                sorted(flow_nested_names),
                work_dir,
            )
        except AuthRequired:
            raise
        except SfCliError as e:
            tree.setdefault("_unresolved", []).append({
                "kind": "PROMPT_TEMPLATE",
                "reason": f"prompt-template-retrieve-failed:{redact_error(e)}",
            })
        else:
            prompt_template_bodies.update(more_bodies)
            _stamp_prompt_template_bodies(tree["root"], prompt_template_bodies)
            # _kind_counts / _pending_fetches are unchanged: the leaves
            # already existed and were counted; this pass only attaches
            # body content to them. No BFS-kind reshuffling needed.

    # Phase 11: finalize. The canonical planner_name now comes from the
    # resolved planner row (Wave A), which joins into bundle_parsed as
    # `plannerName`; fall back to the agent api name if the resolver
    # returned a row without a DeveloperName (shouldn't happen on a
    # healthy planner but keeps finalize's _partial flag well-defined).
    planner_name = bundle_parsed.get("plannerName") or args.agent_api_name
    try:
        _run_finalize(
            data_dir, cache_dir, tree, work_dir,
            args.agent_api_name, bot_info["version"],
            planner_name,
        )
    except OSError as e:
        return _emit_fail(
            args, None, "WRITE_FAILED",
            error_detail=f"finalize-failed:{redact_error(e)}",
            start_epoch=start_epoch,
        )

    # Phase 12: emit RESULT
    return _emit_ok(
        args, data_dir, tree, bot_info, org_id_15,
        start_epoch=start_epoch,
        cache_dir=cache_dir,
        org_id_18=org_id_18,
    )


def main(argv: list[str] | None = None) -> int:
    """Entry point — parses args, runs pipeline, guarantees a RESULT block.

    the skill contract promises that every exit
    path emits `=== RESULT ===` with a structured STATUS. The prior
    implementation let any uncaught exception from the pipeline (e.g.
    the HTTP 405 from , or any future bug we haven't foreseen)
    propagate to the top of the process — the user saw a Python
    traceback on stderr and the wrapper skill never got its RESULT
    block. We now wrap `_run_pipeline` in a broad `except Exception` and
    funnel uncaught failures through `_emit_fail` with
    STATUS=RETRIEVE_FAILED + ERROR_DETAIL="uncaught-exception: <redacted
    message>". `redact_error` keeps tokens / full-URL querystrings out
    of the ctx file. `SystemExit` + `KeyboardInterrupt` are NOT caught —
    argparse's `--help` path + Ctrl-C must propagate normally.
    """
    args = parse_args(argv)
    # MUST happen before any pipeline phase reads DATA_ROOT / CACHE_ROOT.
    # See _apply_path_overrides docstring for the 3-level rebind contract.
    _apply_path_overrides(args)
    # Bug fix (2026-05-05): capture start_epoch ONCE at real pipeline entry
    # and thread it through every _emit_* call so WALL_TIME_SECONDS measures
    # actual pipeline duration, not ctx-write→emit_result drift.
    start_epoch = time.time()
    try:
        return _run_pipeline(args, start_epoch)
    except Exception as exc:
        # broad catch — anything that reaches here is a bug
        # but the skill contract requires a structured exit. redact_error
        # strips bearer tokens and accessToken values from the message
        # ; the exception class name leads the detail so triage
        # can still identify the shape even when the message is terse.
        redacted = redact_error(exc)
        return _emit_fail(
            args,
            None,
            "RETRIEVE_FAILED",
            error_detail=f"uncaught-exception: {redacted}",
            start_epoch=start_epoch,
        )


if __name__ == "__main__":
    sys.exit(main())
