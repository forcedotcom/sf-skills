"""Channel probe — one-shot sf sobject describe per target type, cached 7 days.

channel probe with TTL (7d), mandatory-field gate, runtime
INVALID_FIELD re-probe, and a `--reprobe` CLI flag.

Rationale: Salesforce ships quarterly releases that can rename / deprecate
Tooling sObject fields. A long-lived cache would mask a schema drift for
weeks. A 7-day TTL bounds the exposure; the `invalidate_and_reprobe` hook
is the runtime escape valve when a SOQL returns `INVALID_FIELD` mid-run.

Security:
  * Cache dir comes ONLY from `config.build_probe_cache_dir` (validated
    path; no attacker-controlled segments).
  * Cache file is written 0o600 — owner read-write only.
  * No raw sObject describe REST calls here; we go through `sf_cli.run_sf`
    which already enforces  (yaml.safe_load) +  (redacted stderr).

Mandatory vs optional fields: we ship a MANDATORY_FIELDS map of the fields
the skill's SOQL assets can't function without. A probe that sees ANY
mandatory field missing flags `status: "PROBE_FAILED"` so the caller can
surface a clean error instead of producing a subtly-wrong tree.
"""
from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Dict

# Local imports — sf_cli handles the actual describe calls + redaction.
from config import PROBE_TTL_DAYS, build_probe_cache_dir
from sf_cli import SfCliError, run_sf


# -----------------------------------------------------------------------------
# critical sObjects the skill depends on.
# -----------------------------------------------------------------------------
# `api_kind`: which describe recipe we route the call through. BotDefinition
# / BotVersion are reachable via the Data API; the GenAi* sObjects are
# Tooling-API-only. The two recipes share the same shape (sObject name in,
# queryable fields list out) so downstream handling is uniform.

_DATA_API_SOBJECTS = ("BotDefinition", "BotVersion")
_TOOLING_API_SOBJECTS = (
    "ApexClass",
    "Flow",
    "FlowDefinition",
    "GenAiPlannerDefinition",
    "GenAiPluginDefinition",
    "GenAiFunctionDefinition",
    "GenAiPlannerAttrDefinition",
)

ALL_SOBJECTS: tuple[str, ...] = _DATA_API_SOBJECTS + _TOOLING_API_SOBJECTS


# mandatory fields. These are the minimum set of fields the skill's
# SOQL assets reference by name. If a probe sees ANY of these missing, the
# probe status flips to PROBE_FAILED — we'd rather abort cleanly than
# produce a tree with silent holes from missing columns.
#
# Keep this list conservative — "mandatory" means "every code path needs
# it". Fields that only some branches use go in the queryable set without
# being gated.
MANDATORY_FIELDS: Dict[str, set[str]] = {
    "BotDefinition": {"Id", "DeveloperName"},
    "BotVersion": {"Id", "BotDefinitionId"},
    "ApexClass": {"Id", "Name"},
    "Flow": {"Id", "MasterLabel", "DefinitionId"},
    "FlowDefinition": {"Id", "DeveloperName"},
    "GenAiPlannerDefinition": {"Id", "DeveloperName", "PlannerType"},
    "GenAiPluginDefinition": {"Id", "DeveloperName"},
    "GenAiFunctionDefinition": {"Id", "DeveloperName", "InvocationTarget"},
    "GenAiPlannerAttrDefinition": {"Id"},
}


class ProbeError(RuntimeError):
    """Probe could not complete — surfaced to caller, redaction already applied."""


def _describe_sobject(org_alias: str, sobject: str, is_tooling: bool) -> dict:
    """Describe a single sObject via `sf_cli.run_sf`.

    Expected recipes (to be added alongside this module): `describe_sobject`
    for the Data API and `describe_tooling_sobject` for Tooling. Both are
    expected to return a dict of shape `{"status":0,"result":{"fields":
    [{"name":"X","queryable":true}, ...]}}`.

    We keep this helper tiny so tests can mock `run_sf` without touching
    the wire. The recipes themselves are author-controlled YAML loaded
    through `sf_cli` (yaml.safe_load).

    NOTE: the recipes don't exist on disk yet — they land in the Batch-4
    integration pass. This function is called only via `probe_channels`,
    which every test mocks. The production path stays inert until the
    recipes ship.
    """
    recipe = "describe_tooling_sobject" if is_tooling else "describe_sobject"
    try:
        data = run_sf(recipe, ORG_ALIAS=org_alias, SOBJECT=sobject)
    except SfCliError as e:
        raise ProbeError(f"describe failed for {sobject}: {e}") from None
    return data.get("result") or {}


def _extract_queryable_fields(describe_result: dict) -> list[str]:
    """Pull queryable field names from a describe result.

    Tolerant of both the shape `{"fields":[{"name":"X","queryable":true}]}`
    and the bare `{"fields":[{"name":"X"}]}` (some endpoints omit the
    queryable flag; we default to queryable=True when absent).
    """
    fields = describe_result.get("fields") or []
    out: list[str] = []
    for f in fields:
        if not isinstance(f, dict):
            continue
        name = f.get("name")
        if not isinstance(name, str) or not name:
            continue
        queryable = f.get("queryable", True)
        if queryable:
            out.append(name)
    return sorted(out)


def _is_cache_fresh(path: Path, ttl_days: int) -> bool:
    """Return True if the cached channels.json is present and not stale.

    Staleness is derived from the embedded `_built_at_utc` timestamp, NOT
    filesystem mtime — mtime can be skewed by backup / restore / rsync.

    reject future timestamps (`age_seconds < 0`) as stale. A
    `_built_at_utc` in the future means clock-skew or tampering; either
    way we can't trust the cache. The bound `0 <= age < ttl` is the
    honest freshness predicate.
    """
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return False
    built_at = data.get("_built_at_utc")
    if not isinstance(built_at, (int, float)):
        return False
    age_seconds = time.time() - float(built_at)
    # future timestamps (age < 0) are not fresh.
    return 0 <= age_seconds < (ttl_days * 86400)


def _write_cache(path: Path, payload: dict) -> None:
    """Write the probe payload atomically with 0o600 permissions.

    adjacency: the path itself is built via `build_probe_cache_dir`
    upstream, so every segment is regex-validated. Here we just enforce
    owner-only read/write and atomic rename.

    concurrent-safe tmp filename. `path.with_suffix(...+".tmp")`
    produces the same deterministic name for every concurrent caller —
    a second writer would either race on the final rename or clobber
    the first writer's in-flight bytes. `tempfile.mkstemp(dir=...)`
    returns a unique pathname per call, eliminating the collision.

    normalize parent-dir perms to 0o700 after mkdir. Even if the
    parent existed with looser permissions (umask or operator lapse),
    the probe cache directory is a per-user-per-org artifact that
    should not be world-readable.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    # normalize even if the dir pre-existed.
    try:
        os.chmod(path.parent, 0o700)
    except OSError:
        # Best-effort: on an exotic filesystem (e.g. FAT) chmod may fail.
        # Don't block the cache write on it.
        pass

    # unique tmp name per call, in the same directory as the final
    # path so `os.replace` stays atomic (same-filesystem rename).
    fd, tmp_str = tempfile.mkstemp(
        dir=str(path.parent), prefix=".channels.", suffix=".tmp",
    )
    tmp = Path(tmp_str)
    try:
        with os.fdopen(fd, "w") as f:
            f.write(json.dumps(payload, indent=2, sort_keys=True))
        os.chmod(tmp, 0o600)  # owner RW only
        os.replace(tmp, path)
    except Exception:
        # Clean up the tmp file on error — mkstemp leaves it behind.
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass
        raise


def probe_channels(
    org_alias: str,
    org_id_15: str,
    api_version: str,
    *,
    force_refresh: bool = False,
) -> dict:
    """Run (or return cached) describes for every sObject the skill touches.

    caller passes `force_refresh=True` via the `--reprobe` CLI flag
    or via `invalidate_and_reprobe` when a runtime SOQL surfaces
    `INVALID_FIELD`. Default behavior: return cached payload if present
    AND younger than `PROBE_TTL_DAYS`.

    Returns a dict of shape:
      {
        "_schema": "channels/1",
        "_built_at_utc": <epoch>,
        "status": "OK" | "PROBE_FAILED",
        "channels": {
          "BotDefinition": {
            "queryable_fields": [...],
            "mandatory_missing": [...],
            "describe_error": None | "<redacted error>"
          },
          ...
        }
      }
    """
    cache_dir = build_probe_cache_dir(org_id_15, api_version)
    cache_file = cache_dir / "channels.json"

    if not force_refresh and _is_cache_fresh(cache_file, PROBE_TTL_DAYS):
        return json.loads(cache_file.read_text())

    channels: Dict[str, dict] = {}
    any_mandatory_missing = False

    for sobject in ALL_SOBJECTS:
        is_tooling = sobject in _TOOLING_API_SOBJECTS
        entry: Dict[str, Any] = {
            "queryable_fields": [],
            "mandatory_missing": [],
            "describe_error": None,
        }
        try:
            result = _describe_sobject(org_alias, sobject, is_tooling)
        except ProbeError as e:
            # Redaction already applied by sf_cli.run_sf; we're just
            # passing the message along.
            entry["describe_error"] = str(e)
            channels[sobject] = entry
            # A describe failure is treated as "all mandatory missing"
            # for this sObject — the skill can't function against it.
            entry["mandatory_missing"] = sorted(MANDATORY_FIELDS.get(sobject, set()))
            if entry["mandatory_missing"]:
                any_mandatory_missing = True
            continue

        queryable = _extract_queryable_fields(result)
        entry["queryable_fields"] = queryable
        mandatory = MANDATORY_FIELDS.get(sobject, set())
        missing = sorted(mandatory - set(queryable))
        entry["mandatory_missing"] = missing
        if missing:
            any_mandatory_missing = True

        channels[sobject] = entry

    payload = {
        "_schema": "channels/1",
        "_built_at_utc": time.time(),
        "status": "PROBE_FAILED" if any_mandatory_missing else "OK",
        "channels": channels,
    }
    _write_cache(cache_file, payload)
    return payload


def invalidate_and_reprobe(
    org_alias: str,
    org_id_15: str,
    api_version: str,
) -> dict:
    """Delete the cached channels.json and re-run the probe.

    called when a runtime SOQL returns `INVALID_FIELD`. The cached
    schema is stale (SF release renamed / removed a field); we can't trust
    any of it, so unlink + re-probe.

    Returns the fresh payload. On a subsequent INVALID_FIELD from the
    re-probed schema, the caller should surface PROBE_FAILED rather than
    re-enter this function — one reprobe per run, not a retry loop.
    """
    cache_dir = build_probe_cache_dir(org_id_15, api_version)
    cache_file = cache_dir / "channels.json"
    try:
        cache_file.unlink()
    except FileNotFoundError:
        pass
    return probe_channels(org_alias, org_id_15, api_version, force_refresh=True)
