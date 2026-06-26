#!/usr/bin/env python3
"""Bot + version resolution via two sf data query calls.

Replaces the old agent's Phase 0b–0e (bot/version SOQL, natural-key sort,
error-block assembly) + Phase 1's parallel BotDefinition SOQL. One process,
one RESULT-block emission point.

Flow:
  1. `sf data query` for BotVersion WHERE BotDefinition.DeveloperName=$AGENT_API_NAME.
  2. If 0 rows → follow-up query for AVAILABLE_BOTS, emit STATUS=AGENT_NOT_FOUND.
  3. Natural-key sort versions (v10 > v9 > v2 > v1); pick explicit match or
     Active highest-numbered auto-pick.
  4. If no match → emit STATUS=AGENT_VERSION_NOT_FOUND with AVAILABLE_VERSIONS
     in `v5(Active),v4(Inactive),...` form.
  5. Run a second `sf data query` for BotDefinition (MasterLabel, Description,
     AgentType, Type, AgentTemplate, BotSource) and write `_bot_definition.json`
     for parse_wave.py.

On success, prints eval-friendly KV lines to stdout:
    BOT_FOUND=true
    BOT_ID=<18-char>
    BOT_MASTER_LABEL=<shlex-quoted>
    AGENT_VERSION=<resolved version>
    VERSION_AUTO_PICKED=true|false

Also writes `$WORK_DIR/_bot_versions.json` + `$WORK_DIR/_bot_definition.json`
as raw sidecars (archived into the cache by finalize.py).

Usage:
    eval "$(python3 resolve_bot.py)"

Inputs (env):
    ORG_ALIAS         required — sf CLI target org alias
    AGENT_API_NAME    required — BotDefinition.DeveloperName
    AGENT_VERSION     optional — explicit BotVersion.DeveloperName (if empty, auto-pick)
    WORK_DIR          required — sidecar JSON landing area
    ORG_ID_15         optional — used for error-block context
    ORG_ID_18         optional — used for error-block context
    ERROR_TEE         optional — tee path for error RESULT blocks

Outputs:
    stdout on success: eval-able KV lines (above)
    stdout on error:   full STATUS=AGENT_NOT_FOUND|AGENT_VERSION_NOT_FOUND block
    files: $WORK_DIR/_bot_versions.json, _bot_definition.json, _all_bots.json (on miss)
    exit 0 on success, 1 on any failure branch
"""
import json
import os
import pathlib
import re
import shlex
import subprocess
import sys


def scrub(s) -> str:
    if not isinstance(s, str):
        s = "" if s is None else str(s)
    bad = set("`$\"\\\r\t\0\n")
    return "".join(c for c in s if c not in bad)


def emit_error_block(status: str, error_detail: str, extras: dict) -> None:
    """Write a terminal RESULT block to stdout + $ERROR_TEE, then exit 1."""
    lines = [
        "=== RESULT ===",
        f"STATUS={status}",
        f"ERROR_DETAIL={scrub(error_detail)}",
        f"AGENT_API_NAME={scrub(os.environ.get('AGENT_API_NAME', ''))}",
        f"ORG_ID_15={scrub(os.environ.get('ORG_ID_15', ''))}",
        f"ORG_ID_18={scrub(os.environ.get('ORG_ID_18', ''))}",
    ]
    for k, v in extras.items():
        lines.append(f"{k}={scrub(v)}")
    block = "\n".join(lines) + "\n"

    tee_path = os.environ.get("ERROR_TEE")
    if tee_path:
        try:
            p = pathlib.Path(tee_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            tmp = p.with_suffix(p.suffix + ".tmp")
            tmp.write_text(block)
            os.replace(tmp, p)
        except OSError:
            pass

    sys.stdout.write(block)
    sys.exit(1)


def run_sf_query(query: str, out_path: pathlib.Path, org_alias: str) -> dict:
    """Run `sf data query --json` and return parsed JSON (or {} on failure)."""
    try:
        result = subprocess.run(
            ["sf", "data", "query",
             "--target-org", org_alias,
             "--json",
             "--query", query],
            capture_output=True, text=True, timeout=60,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        emit_error_block(
            "AUTH_REQUIRED",
            f"sf data query failed ({type(e).__name__}: {e}) — check sf CLI install + auth",
            {},
        )
        return {}  # unreachable
    if result.returncode != 0:
        # Print stderr to help user debug, then bail as AUTH_REQUIRED (most
        # common cause is the target-org alias not being logged in)
        emit_error_block(
            "AUTH_REQUIRED",
            f"sf data query returned rc={result.returncode}: {result.stderr[:200]}",
            {},
        )
    try:
        out_path.write_text(result.stdout)
        return json.loads(result.stdout)
    except (OSError, json.JSONDecodeError) as e:
        emit_error_block(
            "AUTH_REQUIRED",
            f"sf data query JSON parse error: {e}",
            {},
        )
        return {}  # unreachable


def natural_key(v: str):
    return [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", v or "")]


def main() -> int:
    try:
        org_alias = os.environ["ORG_ALIAS"]
        agent_api_name = os.environ["AGENT_API_NAME"]
        work_dir = pathlib.Path(os.environ["WORK_DIR"])
    except KeyError as e:
        sys.stderr.write(f"resolve_bot.py: missing env {e}\n")
        return 1

    # Defense-in-depth: bash harness pre-validates AGENT_API_NAME via
    # fs_guard, but importers that call resolve_bot.main() directly bypass
    # that gate — and the SOQL below is built with f-strings. Re-validate
    # here so the regex check is local to the SOQL construction. Mirrors
    # fetch_soql.py's belt-and-braces validation.
    from config import fs_guard  # re-exported from _shared/
    try:
        fs_guard.validate_api_name(agent_api_name, label="AGENT_API_NAME")
    except fs_guard.ValidationError as e:
        emit_error_block("INVALID_INPUT", str(e), {})
        return 1  # unreachable

    explicit_version = os.environ.get("AGENT_VERSION", "").strip()
    work_dir.mkdir(parents=True, exist_ok=True)

    # --- Step 1: BotVersion query (with BotDefinition join) ---
    q_versions = (
        "SELECT Id, DeveloperName, Status, BotDefinitionId, "
        "BotDefinition.DeveloperName, BotDefinition.MasterLabel "
        f"FROM BotVersion WHERE BotDefinition.DeveloperName='{agent_api_name}'"
    )
    versions_json = run_sf_query(q_versions, work_dir / "_bot_versions.json", org_alias)
    records = (versions_json.get("result") or {}).get("records") or []

    # --- Step 2: AGENT_NOT_FOUND branch ---
    if not records:
        q_all = "SELECT DeveloperName FROM BotDefinition ORDER BY DeveloperName"
        all_bots = run_sf_query(q_all, work_dir / "_all_bots.json", org_alias)
        bots_csv = ",".join(
            r.get("DeveloperName", "")
            for r in ((all_bots.get("result") or {}).get("records") or [])
            if r.get("DeveloperName")
        )
        emit_error_block(
            "AGENT_NOT_FOUND",
            f"BotDefinition.DeveloperName '{agent_api_name}' not found in org {org_alias}",
            {"AVAILABLE_BOTS": bots_csv},
        )
        return 1  # unreachable

    # --- Step 3: sort (natural-key, DESC) + pick ---
    records.sort(key=lambda r: natural_key(r.get("DeveloperName") or ""), reverse=True)
    picked = None
    if explicit_version:
        for v in records:
            if v.get("DeveloperName") == explicit_version:
                picked = v
                break
        version_auto_picked = False
    else:
        for v in records:
            if v.get("Status") == "Active":
                picked = v
                break
        version_auto_picked = True

    # --- Step 4: AGENT_VERSION_NOT_FOUND branch ---
    if not picked:
        vers_csv = ",".join(
            f"{v.get('DeveloperName', '?')}({v.get('Status', '?')})"
            for v in records
        )
        requested = explicit_version or "<auto-pick>"
        emit_error_block(
            "AGENT_VERSION_NOT_FOUND",
            f"No matching BotVersion under BotDefinition {agent_api_name} (requested: '{requested}')",
            {
                "AVAILABLE_VERSIONS": vers_csv,
                "BOT_ID": picked.get("BotDefinitionId") if picked else (records[0].get("BotDefinitionId") or ""),
            },
        )
        return 1  # unreachable

    bot_id = picked.get("BotDefinitionId") or ""
    bd_node = picked.get("BotDefinition") or {}
    bot_master_label = bd_node.get("MasterLabel") or ""
    chosen_version = picked.get("DeveloperName") or ""

    # --- Step 5: BotDefinition metadata (for parse_wave.py enrichment) ---
    q_def = (
        "SELECT DeveloperName, MasterLabel, Description, AgentType, Type, "
        "AgentTemplate, BotSource FROM BotDefinition "
        f"WHERE DeveloperName='{agent_api_name}' LIMIT 1"
    )
    try:
        result = subprocess.run(
            ["sf", "data", "query",
             "--target-org", org_alias,
             "--json",
             "--query", q_def],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            (work_dir / "_bot_definition.json").write_text(result.stdout)
        else:
            # Non-fatal; parse_wave.py tolerates an empty bot_definition.json
            (work_dir / "_bot_definition.json").write_text('{"result":{"records":[]}}')
    except (subprocess.TimeoutExpired, FileNotFoundError):
        (work_dir / "_bot_definition.json").write_text('{"result":{"records":[]}}')

    # --- Success: emit eval-friendly lines ---
    out_lines = [
        "BOT_FOUND=true",
        f"BOT_ID={shlex.quote(bot_id)}",
        f"BOT_MASTER_LABEL={shlex.quote(bot_master_label)}",
        f"AGENT_VERSION={shlex.quote(chosen_version)}",
        f"VERSION_AUTO_PICKED={'true' if version_auto_picked else 'false'}",
    ]
    sys.stdout.write("\n".join(out_lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
