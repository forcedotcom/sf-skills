#!/usr/bin/env python3
"""sf-context — Salesforce org detection and context utility for the salesforce-development plugin.

Commands:
    detect       Detect SF project, resolve org, fetch platform JWT, populate env (SessionStart hook).
                 On a post-compaction re-fire (source="compact") it skips the CLI/banner and
                 re-injects only the lean skills-first reminder so the directive stays durable (#406).
    verify-org   Verify org is connected and reachable (PreToolUse hook on deploy/delete)
    post-deploy  Suggest post-deployment actions (PostToolUse hook on a successful deploy)
    post-deploy-failure  Route a FAILED deploy to the owning skill (PostToolUseFailure hook on deploy) (#405)
    check-tools  Scan all required dev tools and print a JSON status report (/salesforce-development:status)
    discovery    Browse the public-channel catalog, show the journey signpost, run on-demand feature detection, or explicitly gated internal preview.
    resolution-trace  Render a bounded Skill resolution trace from the current hook payload.
    record-update-decision  Persist a per-version no-nag gate for the SF CLI update notice (agent-invoked)
    wayfinder    Re-orient after an org-connect (PostToolUse hook on sf org login / config set target-org).
    orientation-rail  Paint the journey rail / status surface on orientation questions (UserPromptSubmit hook).
    status, status-org, status-project  On-demand project/org state (/salesforce-development:status etc.).
    (Also internal advisory/state hooks: skills-first-advisory, record-skill-dispatch, reset-dispatch-turn,
     feedback-nudge, record-feedback-decision — see main() for the full dispatch table.)

All commands emit a single JSON object on stdout matching Claude Code's hook output spec.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from collections import namedtuple
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional


# --- Cross-platform executable resolution (W-23466799 / WIN-026) --------------------------
# On Windows, `sf` and `npm` are batch shims (`sf.cmd`, `npm.cmd`) while `node`
# and `git` are native `.exe` programs. Python's subprocess (CreateProcess) will
# NOT run a `.cmd`/`.bat` without a shell, so `subprocess.run(["sf", ...])` throws
# FileNotFoundError, gets swallowed into empty output, and produces false
# "Not found" / "No default org" results (see docs/windows-compatibility.md,
# "Setup subprocess resolution on Windows"). This resolver is the single place
# that turns a tool NAME into a spawnable argv, cross-platform.
#
# Design constraints:
#   - Use shutil.which(): it honors PATHEXT on Windows, so `sf` finds `sf.cmd`.
#   - A `.cmd`/`.bat` shim is invoked via [COMSPEC, "/c", resolved, *args] so the
#     batch shim actually runs. We pass an ARGV ARRAY (never a shell string), but
#     that alone is NOT injection-proof for a batch shim: CreateProcess still
#     serializes the argv, and cmd.exe re-parses that command line, so shell
#     metacharacters (& | < > ^ % " ! ( )) in an argument would execute. Rather
#     than attempt an error-prone cmd.exe quoter, we REFUSE any argument (and any
#     reparse-dangerous char in the resolved shim path) on the shim path (fail
#     closed — see _CMD_ARG_METACHARACTERS / _CMD_PATH_METACHARACTERS).
#   - Everything else spawns the resolved absolute path directly with shell=False.
#   - Kept as one small, well-tested function so the future Node port
#     (WIN-005/006/007) can mirror it exactly.
_WINDOWS_SHIM_SUFFIXES = (".cmd", ".bat")


def resolve_executable(name: str) -> Optional[str]:
    """Resolve a tool NAME (e.g. "sf") to an absolute path, cross-platform.

    Delegates to shutil.which, which honors PATHEXT on Windows so a `.cmd`/`.bat`
    shim (sf.cmd, npm.cmd) resolves just like a native `.exe`. When `name` already
    looks like a path (contains a separator), it is returned as-is if it exists,
    else looked up on PATH. Returns None when the tool cannot be found — callers
    treat that as a hard, reportable failure (W-23466800 / WIN-027), never a silent success.
    """
    if not name:
        return None
    has_sep = (os.sep in name) or bool(os.altsep and os.altsep in name)
    if has_sep:
        return name if os.path.exists(name) else shutil.which(name)
    return shutil.which(name)


def _is_windows_shim(path: str) -> bool:
    """True when a resolved path is a Windows batch shim needing a cmd wrapper."""
    return path.lower().endswith(_WINDOWS_SHIM_SUFFIXES)


# cmd.exe re-parses the command line it is handed, so these characters keep shell
# meaning inside a batch-shim invocation even though we pass an argv array
# (list2cmdline quotes spaces/quotes, not these). We refuse them on the shim path
# instead of trying to quote them — a fully-correct cmd.exe quoter is notoriously
# hard, and every legitimate caller here passes fixed subcommands/flags plus an
# org alias, none of which contain these. The bash deploy gate keeps the SAME arg
# set so the two guards don't diverge; the future Node port must too.
#
# Two sets: args are fully controlled (subcommands/flags/aliases) so we reject the
# widest set, including `(` `)` (grouping) and `!` (delayed expansion). The
# resolved shim PATH is system-provided and legitimately contains `(`/`)` (e.g.
# "C:\Program Files (x86)\..."), so its guard omits those — but still rejects the
# chars cmd.exe reparses even inside quotes (`%` env-expansion, `!`) or that break
# quoting (`"`), plus the redirection/chaining set for the unquoted (no-space)
# path case.
_CMD_ARG_METACHARACTERS = ("&", "|", "<", ">", "^", "%", '"', "!", "(", ")", "\n", "\r")
_CMD_PATH_METACHARACTERS = ("&", "|", "<", ">", "^", "%", '"', "!", "\n", "\r")


def _contains_any(value: str, chars) -> bool:
    return any(ch in value for ch in chars)


def _has_cmd_metacharacters(value: str) -> bool:
    """Back-compat helper (arg set). Prefer _contains_any with an explicit set."""
    return _contains_any(value, _CMD_ARG_METACHARACTERS)


def build_command(name: str, args: Optional[list] = None) -> Optional[list]:
    """Build the argv to spawn `name` + `args` cross-platform, or None if `name`
    cannot be resolved on PATH (or, on the shim path, an arg is unsafe).

    - Resolves `name` via resolve_executable (PATHEXT-aware).
    - If the resolved path is a `.cmd`/`.bat` shim, returns
      [COMSPEC, "/c", resolved, *args] (COMSPEC from env, fallback "cmd.exe") so
      the batch shim runs. Passing an argv array preserves argv boundaries, but it
      is NOT sufficient for injection safety on a batch shim, because cmd.exe
      re-parses the serialized command line. So on this path we REFUSE (return
      None, fail closed) if any ARG contains a cmd metacharacter, OR the resolved
      shim PATH contains a reparse-dangerous char — rather than attempt cmd.exe
      quoting. See _CMD_ARG_METACHARACTERS / _CMD_PATH_METACHARACTERS.
    - Otherwise returns [resolved, *args] for a direct shell=False spawn (POSIX
      and native Windows `.exe`), which is not subject to the cmd.exe reparse.
    """
    args = list(args) if args else []
    resolved = resolve_executable(name)
    if resolved is None:
        return None
    if _is_windows_shim(resolved):
        if _contains_any(resolved, _CMD_PATH_METACHARACTERS) or any(
            _contains_any(a, _CMD_ARG_METACHARACTERS) for a in args
        ):
            return None
        comspec = os.environ.get("COMSPEC", "cmd.exe")
        return [comspec, "/c", resolved, *args]
    return [resolved, *args]


def _is_windows() -> bool:
    return sys.platform.startswith("win")


def _cli_timeout() -> int:
    """Per-call timeout for CLI-backed calls.

    `sf`/oclif startup is slow on Windows (~5s cold) and each `.cmd` now runs
    through an extra `cmd.exe` layer, so concurrent CLI checks on a cold cache can
    exceed a short timeout and produce false negatives that self-correct on a
    re-run — a W-23466800 (WIN-027) determinism wrinkle observed on the native VM. Give CLI
    calls more headroom on Windows. A genuinely-missing tool still fails instantly
    (resolve_executable returns None without spawning), so this only affects
    present-but-slow tools, never the missing-tool path."""
    return 30 if _is_windows() else 10


def _check_tools_workers() -> int:
    """check-tools concurrency. Fewer workers on Windows to cut the cold-start
    contention between parallel slow `sf.cmd` spawns that caused first-run false
    negatives on the org-dependent checks."""
    return 3 if _is_windows() else 7


# Structured outcome of a CLI call so callers can distinguish "the tool ran and
# returned no value" from "the tool could not be run" (unresolved / timeout /
# nonzero exit / launch error). `run()` keeps the simple "stdout-or-empty"
# contract; `run_result()` preserves the failure reason for the org/status paths
# (W-23466800 / WIN-027: a broken CLI must not masquerade as "no org configured").
#   reason: "" (ok) | "empty" | "unresolved" | "timeout" | "nonzero" | "error"
RunResult = namedtuple("RunResult", ["ok", "stdout", "returncode", "reason"])


def run_result(cmd: list, timeout: Optional[int] = None) -> RunResult:
    """Run a command and return a structured RunResult.

    The first element of `cmd` is a tool NAME (e.g. "sf"); it is resolved
    cross-platform via build_command so a Windows `.cmd`/`.bat` shim launches
    correctly. Always spawns an argv array with shell=False. `timeout` defaults to
    the platform-aware `_cli_timeout()` (longer on Windows) when not specified."""
    if not cmd:
        return RunResult(False, "", None, "empty")
    if timeout is None:
        timeout = _cli_timeout()
    argv = build_command(cmd[0], cmd[1:])
    if argv is None:
        # Missing on PATH, or refused (cmd metacharacters on a shim path).
        return RunResult(False, "", None, "unresolved")
    try:
        result = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
        )
    except subprocess.TimeoutExpired:
        return RunResult(False, "", None, "timeout")
    except (FileNotFoundError, OSError):
        return RunResult(False, "", None, "error")
    if result.returncode == 0:
        return RunResult(True, result.stdout, 0, "")
    return RunResult(False, result.stdout, result.returncode, "nonzero")


def run(cmd: list, timeout: Optional[int] = None) -> str:
    """Run a command, capturing stdout. Returns empty string on failure.

    Thin wrapper over run_result() preserving the "empty string on failure"
    contract most callers depend on; a genuinely unresolvable tool returns ""
    too (and is surfaced as a hard failure by the check-tools / org paths, per
    W-23466800 / WIN-027)."""
    res = run_result(cmd, timeout)
    return res.stdout if res.ok else ""


# --- Deterministic failure diagnostics (W-23466800 / WIN-027) -----------------------------
# When an automated check fails, print an actionable, SECRET-FREE diagnostic so a
# real failure is understandable instead of silently empty — and so it is not
# quietly "fixed" by a model-run PowerShell/shell fallback that flips the reported
# result to green. Deliberately contains only environment shape (platform, shell,
# cwd, plugin root) and the RESOLVED executable paths; it NEVER reads or emits
# tokens, JWTs, access tokens, or any auth material.
_DIAGNOSTIC_TOOLS = ("sf", "npm", "node", "git")


def _active_shell() -> str:
    """Best-effort active shell: COMSPEC on Windows, SHELL on POSIX. Neither is a
    secret. Empty string when unset."""
    if sys.platform.startswith("win"):
        return os.environ.get("COMSPEC", "cmd.exe")
    return os.environ.get("SHELL", "")


def _plugin_root() -> str:
    """Absolute path to the plugin root (parent of scripts/)."""
    return str(Path(__file__).resolve().parent.parent)


def diagnostic_context(tools: Optional[list] = None) -> dict:
    """A secret-free diagnostic for a failed automated check (W-23466800 / WIN-027).

    Reports platform (sys.platform), the active shell, working directory, plugin
    root, and the cross-platform-RESOLVED path for each tool (or "not found on
    PATH"). Never includes tokens/secrets — it only locates executables."""
    names = list(tools) if tools else list(_DIAGNOSTIC_TOOLS)
    resolved = {name: (resolve_executable(name) or "not found on PATH") for name in names}
    return {
        "platform": sys.platform,
        "shell": _active_shell(),
        "cwd": os.getcwd(),
        "pluginRoot": _plugin_root(),
        "resolvedExecutables": resolved,
    }


def render_diagnostic_lines(ctx: dict) -> str:
    """Human-readable rendering of diagnostic_context() for text (non-JSON)
    command output such as status-org."""
    lines = [
        "Diagnostic:",
        f"  platform: {ctx.get('platform', '')}",
        f"  shell:    {ctx.get('shell', '') or '(unset)'}",
        f"  cwd:      {ctx.get('cwd', '')}",
        f"  plugin:   {ctx.get('pluginRoot', '')}",
        "  resolved executables:",
    ]
    for name, path in (ctx.get("resolvedExecutables") or {}).items():
        lines.append(f"    {name}: {path}")
    return "\n".join(lines)


def parse_json(s: str) -> dict:
    """Parse JSON, return empty dict on any failure."""
    try:
        return json.loads(s) if s else {}
    except json.JSONDecodeError:
        return {}


def emit(
    event: str,
    message: str,
    *,
    decision: Optional[str] = None,
    reason: Optional[str] = None,
    system_message: Optional[str] = None,
) -> None:
    """Print a hook output JSON object."""
    output: dict = {"hookSpecificOutput": {"hookEventName": event}}
    if decision:
        output["hookSpecificOutput"]["permissionDecision"] = decision
        output["hookSpecificOutput"]["permissionDecisionReason"] = reason or ""
    else:
        output["continue"] = True
        if message:
            output["hookSpecificOutput"]["additionalContext"] = message
        # systemMessage renders visibly to the user at session start (top-level field per hook spec).
        if system_message:
            output["systemMessage"] = system_message
    print(json.dumps(output))


def get_target_org_detailed() -> tuple:
    """Resolve the default org, distinguishing "no org set" from "the CLI query
    failed" (W-23466800 / WIN-027).

    Returns (org_alias, error_reason):
      - ("<alias>", "") — the CLI ran and an org is configured.
      - ("", "")        — the CLI ran fine but no default org is set.
      - ("", "<reason>")— the CLI could not be queried (unresolved / timeout /
                          nonzero / error), OR it exited 0 but returned output we
                          can't trust ("invalid-output": malformed JSON, a
                          non-object root, or a missing/!list `result`). Callers
                          report a CLI failure with a diagnostic, NOT a false
                          "no org".

    Environment precedence: honor SF_TARGET_ORG / SFDX_TARGET_ORG before the CLI
    config, matching how `sf` itself (and the proxy's resolveTargetOrg) resolves
    the target org. Without this, a session that overrides the org via env would
    read a different (or empty) config value here — so `/status` would report
    "no org", and the MCP-health filter would reject sidecars the proxy stamped
    with the env org. Env-first keeps the consumer aligned with the producer.
    """
    env_org = os.environ.get("SF_TARGET_ORG") or os.environ.get("SFDX_TARGET_ORG")
    if env_org:
        return env_org, ""
    res = run_result(["sf", "config", "get", "target-org", "--json"])
    if not res.ok:
        return "", (res.reason or "failed")
    # Exit 0 is necessary but not sufficient: validate the expected shape before
    # concluding "no org", so malformed/unexpected output isn't misread as an
    # empty config (and never raises on a non-dict root or non-dict entries).
    data = parse_json(res.stdout)
    if not isinstance(data, dict):
        return "", "invalid-output"
    result = data.get("result")
    if not isinstance(result, list):
        return "", "invalid-output"
    for r in result:
        if isinstance(r, dict) and r.get("name") == "target-org":
            return (r.get("value", "") or ""), ""
    # Well-formed response with no target-org entry → genuinely no default org.
    return "", ""


def get_target_org() -> str:
    """Back-compat string accessor: the alias, or "" for both no-org and
    CLI-failure. Paths that must tell those apart use get_target_org_detailed()."""
    return get_target_org_detailed()[0]


# Path to the bundled Node helper that uses @salesforce/core directly.
# Set to None when not available — the script falls back to sequential sf CLI calls.
def _bundled_helper_path() -> Optional[Path]:
    here = Path(__file__).resolve().parent
    candidate = here / "sf-org-info.bundled.js"
    return candidate if candidate.exists() else None


def fetch_org_info_via_node() -> Optional[dict]:
    """Run the bundled @salesforce/core helper. Returns:
        {targetOrg, orgInfo, jwt, error} on success
        None if the bundle isn't present or fails completely.
    """
    helper = _bundled_helper_path()
    if helper is None:
        return None
    out = run(["node", str(helper)], timeout=15)
    if not out:
        return None
    data = parse_json(out)
    return data if isinstance(data, dict) else None


def get_org_list() -> dict:
    return parse_json(run(["sf", "org", "list", "--json"])).get("result", {}) or {}


def get_org_display(target: str) -> dict:
    return parse_json(run(["sf", "org", "display", "--target-org", target, "--json"])).get("result", {}) or {}


def resolve_org_info(target: str, *, org_list: Optional[dict] = None, org_display: Optional[dict] = None) -> dict:
    """Combine `sf org list` (rich metadata) and `sf org display` (canonical alias) to build a unified view.

    Pass pre-fetched results via the keyword args to avoid duplicate CLI calls when the caller
    has already kicked off these queries in parallel.
    """
    if org_list is None:
        org_list = get_org_list()
    if org_display is None:
        org_display = get_org_display(target)

    pool = (org_list.get("nonScratchOrgs") or []) + (org_list.get("scratchOrgs") or [])
    canonical_alias = org_display.get("alias")
    canonical_username = org_display.get("username")

    match = next(
        (
            o
            for o in pool
            if o.get("alias") == target
            or o.get("username") == target
            or (canonical_alias and o.get("alias") == canonical_alias)
            or (canonical_username and o.get("username") == canonical_username)
        ),
        None,
    )

    if match:
        edition = match.get("orgEdition") or "unknown"
        if match.get("isSandbox"):
            suffix = "(Sandbox)"
        elif match.get("isScratch"):
            suffix = "(Scratch)"
        elif match.get("isDevHub"):
            suffix = "(DevHub)"
        else:
            suffix = "(Production)"
        return {
            "alias": match.get("alias") or target,
            "edition": f"{edition} {suffix}",
            "apiVersion": match.get("instanceApiVersion") or org_display.get("apiVersion") or "unknown",
            "instanceUrl": match.get("instanceUrl") or org_display.get("instanceUrl") or "",
            "username": match.get("username") or org_display.get("username") or "",
            "isSandbox": match.get("isSandbox", False),
            "isScratch": match.get("isScratch", False),
            "isDevHub": match.get("isDevHub", False),
        }
    if org_display:
        return {
            "alias": org_display.get("alias") or target,
            "edition": "stale auth (re-login may be needed)",
            "apiVersion": org_display.get("apiVersion") or "unknown",
            "instanceUrl": org_display.get("instanceUrl") or "",
            "username": org_display.get("username") or "",
            "isSandbox": False,
            "isScratch": False,
            "isDevHub": False,
        }
    return {}


def is_production(org_info: dict) -> bool:
    """A best-effort heuristic for production vs. non-production orgs."""
    if org_info.get("isSandbox") or org_info.get("isScratch") or org_info.get("isDevHub"):
        return False
    instance = (org_info.get("instanceUrl") or "").lower()
    if "test.salesforce.com" in instance or "--" in instance:
        return False
    return True


def count_files(patterns: list[str], path_filter: Optional[str] = None) -> int:
    """Recursively count files matching any pattern. Excludes node_modules, .git, .sfdx."""
    excluded_parts = {"node_modules", ".git", ".sfdx"}
    total = 0
    for pat in patterns:
        for p in Path(".").rglob(pat):
            if any(part in excluded_parts for part in p.parts):
                continue
            if path_filter and path_filter not in str(p):
                continue
            if p.is_file():
                total += 1
    return total


def project_stats() -> dict:
    apex_total = count_files(["*.cls"])
    apex_test = count_files(["*Test.cls", "*_Test.cls"])
    return {
        "apex_src": max(apex_total - apex_test, 0),
        "apex_test": apex_test,
        "triggers": count_files(["*.trigger"]),
        "lwc": count_files(["*.js-meta.xml"], path_filter="/lwc/"),
        "aura": count_files(["*.cmp-meta.xml", "*.app-meta.xml", "*.evt-meta.xml"]),
        "objects": count_files(["*.object-meta.xml"]),
        "permsets": count_files(["*.permissionset-meta.xml"]),
        "flows": count_files(["*.flow-meta.xml"]),
    }


def git_status_line() -> str:
    """Return a one-line git summary, or empty string if not a git repo."""
    inside = run(["git", "rev-parse", "--is-inside-work-tree"], timeout=2).strip()
    if inside != "true":
        return ""
    porcelain = run(["git", "status", "--porcelain"], timeout=2)
    changed = sum(1 for line in porcelain.splitlines() if line.strip())
    return f"{changed} file(s) changed" if changed > 0 else "working tree clean"


def project_meta() -> dict:
    """Read sfdx-project.json fields needed for the project box."""
    try:
        data = json.loads(Path("sfdx-project.json").read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {"name": "Project", "source_api": "unknown", "package_dirs": "force-app"}
    name = data.get("name") or "Project"
    source_api = data.get("sourceApiVersion") or "unknown"
    dirs = [p.get("path", "") for p in data.get("packageDirectories", [])]
    package_dirs = ", ".join(d for d in dirs if d) or "force-app"
    return {"name": name, "source_api": source_api, "package_dirs": package_dirs}


SKILLS_FIRST_DIRECTIVE = """
# Salesforce Project Conventions (auto-injected by salesforce-development)

You are working in a Salesforce DX project with the `salesforce-development` plugin installed.

## Skills-first principle (REQUIRED)

For ANY request involving Salesforce platform development, you MUST check for an applicable installed skill BEFORE writing code, generating metadata, or running CLI commands from defaults. Skills encode validated workflows, platform best practices, and project conventions that default knowledge does not capture.

This session has a catalog of Salesforce skills installed (Apex, metadata, deployment,
LWC/UI, SOQL/data, Agentforce, org/auth, and more). Their names and trigger phrases are
already loaded — match your request against them by intent and ALWAYS prefer the owning
skill over default behavior. When a skill applies, dispatch it explicitly rather than
authoring `.cls`/`.trigger`/`-meta.xml` files or running `sf` from defaults.

## Capability Resolution Hierarchy (MANDATORY)

1. **Skills first** — match the request against an installed skill and activate it explicitly.
2. **SF CLI second** — when no skill covers the operation, use `sf` commands with `--json`.
3. **Direct API last** — only when neither a skill nor a CLI command satisfies the need.

If you start to handle a request without checking skills, STOP and re-evaluate. Default behavior loses platform best practices, governor-limit awareness, security patterns, and validated test patterns that the skills enforce.

## Slash commands available

`/salesforce-development:status`, `/salesforce-development:org`, `/salesforce-development:project` — project/org state
`/salesforce-development:login`, `/salesforce-development:logout`, `/salesforce-development:set-default` — auth management
"""


# The single user-facing pointer to the discovery surface. Reused verbatim as the
# banner/wayfinder CTA (so exactly one pointer shows) and as the closing line of
# SKILLS_FIRST_REINJECT below.
DISCOVERY_POINTER = 'Ask “what can I do here?” or run /salesforce-development:discovery.'


# The pointer above is addressed to the USER; this rule is addressed to the model,
# so it rides `additionalContext` only and never clutters the visible banner.
#
# Why it exists: the banner states the project and org facts, which is a good enough
# answer that the model stops there. Measured on this branch — "where am I?" routed
# to discovery 0 times in 4 runs (every environment, zero tool calls), with one reply
# saying outright "the plugin banner detected sfdx-project.json". The banner ends up
# suppressing the surface built to answer the question, so the rail's six-stage
# position, likely-next action, and honest unknowns never reach the user. The narrow
# carve-out keeps "where is the Account class?" a normal task.
ORIENTATION_DIRECTIVE = """
# Orientation questions (salesforce-development)

When the user asks where they are in the workflow — “where am I?”, “what stage am I at?”,
“what should I do next?”, “am I set up?” — do NOT answer from this banner's facts or from your
own inspection of the directory. Dispatch the `salesforce-development:discovery` capability with
`where` (equivalently `journey`). The banner reports only project and org state; the rail alone
reports the six-stage position, the bounded next action, and which stages are genuinely unknown.

Answer in two parts, in this order:

1. Reproduce the rail in your reply, first, inside a fenced block, unmodified — its glyphs, stage
   labels and marker exactly as the command emitted them. Do NOT assume the command's own output
   is visible to the user; a tool result may be collapsed or absent from what they read, so the
   rail has to be in your message. EXCEPTION: if this turn's context says the plugin already
   displayed the rail to the user, skip this step — do not reproduce or re-run it — and give only
   part 2. It is deterministic, so they see the same grounding picture and can compare sessions.
2. Then add your own short read of it: what this stage means for what THEY are working on, the
   concrete next step in this project, and what stays unknown. That is the relevance the rail
   cannot carry. Never restate the rail line by line, never replace it with a summary of
   itself, and never redraw or re-glyph it.

This covers the USER's position, never where a thing lives: “where is the Account class?” and any
request to find code or metadata are ordinary tasks — never answer those with the journey rail.
"""


def _agent_context(body: str) -> str:
    """Attach the model-facing orientation rule to an agent-facing SessionStart body.

    The banner is painted with ANSI color for the user-visible `systemMessage`,
    but this body feeds `additionalContext`, which the model reads as text and
    never renders. Strip the color here: escape bytes in the agent context are
    pure token cost on the SessionStart hot path and only obscure the very facts
    (counts, provenance, org state) the context exists to convey. Color stays on
    the user-visible surface only.
    """
    return _ANSI_RE.sub("", body) + "\n" + ORIENTATION_DIRECTIVE


# A LEAN re-injection of the skills-first principle, used after context
# compaction (#406). SKILLS_FIRST_DIRECTIVE is injected once at startup; this
# re-states only the durable behavioral rule (skills → CLI → API) after a
# compaction reclaims context, keeping skills-first DURABLE across the long,
# complex sessions where skills matter most rather than evaporating the moment
# context is summarized.
SKILLS_FIRST_REINJECT = """
# Salesforce skills-first reminder (re-injected by salesforce-development after compaction)

This is a Salesforce DX project with the `salesforce-development` plugin installed.
The installed skill catalog is still in effect after this compaction. The
capability-resolution rule still holds:

1. **Skills first** — for ANY Salesforce platform work (Apex, metadata, deploy,
   LWC, SOQL, Agentforce, org/auth), match the request to an installed skill and
   dispatch it BEFORE writing code, generating metadata, or running `sf` from
   defaults. Skills encode validated workflows, governor-limit/FLS guardrails,
   and project conventions that default knowledge does not.
2. **SF CLI second** — when no skill covers the operation, use `sf … --json`.
3. **Direct API last** — only when neither a skill nor a CLI command fits.

If you find yourself about to author a `.cls`/`.trigger`/`-meta.xml` file or run
a raw `sf apex run` / `sf project retrieve` / `sf data query`, STOP and check for
the owning skill first.

Ask “what can I do here?” or run /salesforce-development:discovery.
"""


# The HEADLESS lockup as designed: FIGlet ANSI Shadow, 64 columns, with the
# wordmark carried by the letter-spaced line below rather than crammed into the
# art. Block and box-drawing glyphs are safe here for the same reason the org and
# project boxes are — `_force_utf8_stdio()` runs before anything prints.
#
# Deliberately uncolored. The design comp paints the letters with a blue→purple
# gradient, but that is CSS on an HTML mock; this string lands in a hook's
# `systemMessage`, not on a stream whose color tier we can detect or control. So
# the mark is monochrome by construction and reads the same under NO_COLOR, a
# dumb TERM, or a pipe.
BANNER = """██╗  ██╗███████╗ █████╗ ██████╗ ██╗     ███████╗███████╗███████╗
██║  ██║██╔════╝██╔══██╗██╔══██╗██║     ██╔════╝██╔════╝██╔════╝
███████║█████╗  ███████║██║  ██║██║     █████╗  ███████╗███████╗
██╔══██║██╔══╝  ██╔══██║██║  ██║██║     ██╔══╝  ╚════██║╚════██║
██║  ██║███████╗██║  ██║██████╔╝███████╗███████╗███████║███████║
╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═════╝ ╚══════╝╚══════╝╚══════╝╚══════╝"""

# Letter-spaced to sit under the art at the comp's proportions. Split into its
# two tinted pieces (see _paint_wordmark) so the plain and colored forms share
# one source. The version is left unspaced so it stays greppable and readable
# when spoken.
_WORDMARK_SALESFORCE = "s a l e s f o r c e"
_WORDMARK_360 = "3 6 0"
BANNER_WORDMARK = f"{_WORDMARK_SALESFORCE}   ·   {_WORDMARK_360}"

BANNER_TAGLINE = "headless Salesforce development, from inside the agent"

# Brand color, matching the design comp. The block art carries the comp's CSS
# linear-gradient(100deg, #00A1E0 0%, #39b3ff 45%, #7c5cff 100%); a terminal
# can't do a true gradient, so we approximate it per display column in 24-bit
# truecolor. The wordmark reuses the comp's spot colors (salesforce lavender,
# a bright-blue "360"), and the muted slate is the comp's dim tone for
# separators, version, tagline, and provenance.
#
# Two rules make this read correctly in Claude Code specifically:
#   1. Every colored line is prefixed with SGR 22 (normal intensity). Claude
#      Code renders a hook's systemMessage DIMMED by default, so without the
#      dim-cancel the whole lockup reads muted grey — which is exactly the
#      "why is it grey" the design review flagged.
#   2. Color is emitted unless NO_COLOR is set, and is NEVER gated on isatty:
#      the banner is printed into a hook's JSON systemMessage, so stdout is
#      always a pipe and Claude Code does the terminal rendering. An isatty
#      check would suppress color in precisely the case we want it.
_GRADIENT_STOPS = ((0.0, (0x00, 0xA1, 0xE0)), (0.45, (0x39, 0xB3, 0xFF)), (1.0, (0x7C, 0x5C, 0xFF)))
_WORDMARK_SALESFORCE_RGB = (0xB7, 0x9C, 0xFF)
_WORDMARK_360_RGB = (0x39, 0xB3, 0xFF)
_MUTED_RGB = (0x6F, 0x83, 0xA6)
_SGR_RESET = "\x1b[0m"
_SGR_UNDIM = "\x1b[22m"
# The current-stage accent uses the 16-color PALETTE green (SGR 32), not a truecolor
# RGB. These surfaces are rendered by Claude Code (a systemMessage), which maps SGR
# through its OWN theme — so the palette green matches the host UI and re-tunes with
# Claude Code's light/dark theme, instead of imposing one fixed mint on every session
# (which a truecolor RGB would, and which could wash out on a light theme). See _green.
_SGR_GREEN = "\x1b[32m"

# Palette for the status bands below the lockup. Same comp language as the
# wordmark: bright body text, muted slate for rules/secondary facts, a green
# check for positive state and amber for a warning. Every value is a truecolor
# triple painted via the dim-cancelled _paint_line, so the plain (NO_COLOR /
# ANSI-stripped) form is byte-identical to the colored one — the golden
# convention the lockup already relies on.
_OK_RGB = (0x5F, 0xD0, 0x8A)
_WARN_RGB = (0xF2, 0xC5, 0x6B)
_HEAD_RGB = (0xE7, 0xED, 0xF7)
_BODY_RGB = (0xC6, 0xD6, 0xEE)
_LINK_RGB = (0xBF, 0xE0, 0xFF)
# Segment style name -> (rgb, bold). Bold uses SGR 1, which the ANSI-strip regex
# (\x1b\[[0-9;]*m) still removes — so no colon-form SGR ever leaks into the
# model-facing additionalContext.
_BAND_STYLES = {
    "body": (_BODY_RGB, False),
    "muted": (_MUTED_RGB, False),
    "ok": (_OK_RGB, False),
    "warn": (_WARN_RGB, False),
    "head": (_HEAD_RGB, True),
    "link": (_LINK_RGB, False),
}
# The rules align to the 64-column ANSI-Shadow lockup edge, giving the bands a
# clean seam to the art above them.
_BAND_WIDTH = 64


def _banner_color_enabled() -> bool:
    """Whether the plugin's full truecolor palette is enabled. Off by design.

    Banner, band, trace, status, and welcome palette styling therefore renders as
    plain text in production. The journey rail's current-stage marker is separate:
    `_green()` retains one host-themed 16-color accent unless `NO_COLOR` is set.
    The `color=` plumbing remains so the broader palette can be re-enabled here.
    """
    return False


def _gradient_rgb(t: float) -> tuple[int, int, int]:
    """Interpolate the brand gradient at position t in [0, 1] (linear RGB)."""
    t = 0.0 if t < 0 else 1.0 if t > 1 else t
    for (p0, c0), (p1, c1) in zip(_GRADIENT_STOPS, _GRADIENT_STOPS[1:]):
        if t <= p1:
            f = 0.0 if p1 == p0 else (t - p0) / (p1 - p0)
            return tuple(round(a + (b - a) * f) for a, b in zip(c0, c1))
    return _GRADIENT_STOPS[-1][1]


def _fg(rgb: tuple[int, int, int]) -> str:
    """24-bit truecolor foreground SGR for an (r, g, b) triple."""
    return f"\x1b[38;2;{rgb[0]};{rgb[1]};{rgb[2]}m"


def _green(text: str) -> str:
    """Wrap text in the palette (16-color) green — the single accent kept on the
    otherwise-plain surfaces, marking the current journey stage (its dot and label).

    Uses the ANSI palette index (SGR 32), NOT a truecolor RGB, on purpose: these
    surfaces are rendered by Claude Code (a systemMessage), which maps SGR through
    its OWN theme (verified empirically — retinting the terminal theme did not move
    these colors). So the palette green matches the surrounding Claude Code UI and
    re-tunes with its light/dark theme, whereas a fixed mint would look identical on
    every session and could wash out on a light theme.

    Honors NO_COLOR, and `strip_ansi()` returns the text unchanged, so the plain/
    golden forms and every ≤80 measurement are untouched. It rides the systemMessage
    channel (orientation rail, wayfinder, welcome); the `/discovery journey` stdout
    path strips it, since that output is model-reproduced."""
    if os.environ.get("NO_COLOR"):
        return text
    return f"{_SGR_UNDIM}{_SGR_GREEN}{text}{_SGR_RESET}"


def _paint_gradient(art: str) -> str:
    """Paint block art with the per-column brand gradient, dim-cancelled per line.

    The visible glyphs are untouched; only SGR codes are interleaved. Stripping
    ANSI returns the original art byte-for-byte, which is what the geometry
    goldens assert against.
    """
    lines = art.splitlines()
    span = max(max((len(line) for line in lines), default=1) - 1, 1)
    painted = []
    for line in lines:
        buf, prev = _SGR_UNDIM, None
        for col, ch in enumerate(line):
            code = _fg(_gradient_rgb(col / span))
            if code != prev:
                buf += code
                prev = code
            buf += ch
        painted.append(buf + _SGR_RESET)
    return "\n".join(painted)


def _paint_wordmark(version: str) -> str:
    """Tint the wordmark to the comp: salesforce lavender, 360 bright blue,
    separators and version muted. The visible text is identical to the plain
    `{BANNER_WORDMARK}   ·   v{version}` form, so a screen reader and the
    ANSI-stripping goldens see the same string."""
    sf, three, muted = _fg(_WORDMARK_SALESFORCE_RGB), _fg(_WORDMARK_360_RGB), _fg(_MUTED_RGB)
    return (
        f"{_SGR_UNDIM}{sf}{_WORDMARK_SALESFORCE}{_SGR_RESET}"
        f"{_SGR_UNDIM}{muted}   ·   {_SGR_RESET}"
        f"{_SGR_UNDIM}{three}{_WORDMARK_360}{_SGR_RESET}"
        f"{_SGR_UNDIM}{muted}   ·   v{version}{_SGR_RESET}"
    )


def _paint_muted(text: str) -> str:
    """Wrap a plain line in the comp's muted slate (dim-cancelled)."""
    return f"{_SGR_UNDIM}{_fg(_MUTED_RGB)}{text}{_SGR_RESET}"

_ARTIFACT_READ_ERRORS = (OSError, ValueError, TypeError, KeyError, IndexError)
# The lockup is contractually ≤80 columns, so the artifact strings and counts it
# interpolates are bounded here. A catalog with 100k capabilities is not a real
# artifact; treating one as unreadable is safer than wrapping the pinned visual.
_IDENTITY_LIMIT = 24
_COUNT_CEILING = 100000


def _clip(value: str, limit: int) -> str:
    """Clip a display string to `limit` columns, marking the cut."""
    return value if len(value) <= limit else value[: limit - 1] + "…"


def _banner_provenance(plugin_root: Optional[Path] = None) -> dict:
    """Read the banner's identity facts straight from the checked artifacts.

    Deliberately a plain `json.load` of the plugin manifest and the generated
    discovery catalog rather than `discovery_catalog.load_catalog`: this runs on
    the SessionStart hot path, and that loader adds a module import plus full
    schema validation to every session start. Fail-open by design — an
    unreadable or malformed artifact degrades the banner (`v?`, no provenance
    line) instead of raising, because a crashing SessionStart hook degrades the
    whole session. No count or version is ever hardcoded here.
    """
    root = plugin_root or Path(__file__).resolve().parent.parent
    facts: dict = {
        "version": "?",
        "capabilities": None,
        "foundation": None,
        "library": None,
        "addable": None,
        "releaseRef": None,
    }
    try:
        version = json.loads((root / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))["version"]
        if type(version) is str and version:
            facts["version"] = _clip(version, _IDENTITY_LIMIT)
    except _ARTIFACT_READ_ERRORS:
        pass
    try:
        catalog = json.loads((root / "catalog/discovery.json").read_text(encoding="utf-8"))
        counts = catalog["counts"]
        release_data = catalog["publicRelease"]
        if type(counts) is not dict or type(release_data) is not dict:
            raise TypeError("invalid catalog facts")
        visible = counts.get("visibleUnion")
        foundation = counts.get("foundation")
        addable = counts.get("publicStandaloneAddable")
        release = release_data.get("releaseRef")
        if type(visible) is int and 0 <= visible < _COUNT_CEILING:
            facts["library"] = visible
        if type(foundation) is int and 0 <= foundation < _COUNT_CEILING:
            facts["foundation"] = foundation
        if (
            facts["library"] is not None
            and type(addable) is int
            and 0 <= addable < _COUNT_CEILING
            and type(release) is str
            and release
        ):
            facts.update(
                capabilities=visible,
                addable=addable,
                releaseRef=_clip(release, _IDENTITY_LIMIT),
            )
    except _ARTIFACT_READ_ERRORS:
        pass
    return facts


def render_banner_block(
    plugin_root: Optional[Path] = None,
    *,
    color: Optional[bool] = None,
    facts: Optional[dict] = None,
) -> str:
    """Compose the pinned lockup: block art plus artifact-derived identity lines.

    Block art is invisible to a screen reader and to anything that strips it, so
    the running version and catalog provenance are also stated in text. The
    wordmark line is letter-spaced for the comp, which means a screen reader
    spells it out; the tagline underneath is what states the product in plain
    prose. The version is the plugin that is actually running; the release ref on
    the provenance line is the catalog snapshot those counts came from.

    `color` defaults to the NO_COLOR-honoring `_banner_color_enabled()` so the
    SessionStart systemMessage stays colored; callers that print to the
    model-reproduced slash-command stdout pipe (where ANSI can't survive) pass
    `color=False` to force the plain lockup.
    """
    use_color = _banner_color_enabled() if color is None else color
    facts = facts or _banner_provenance(plugin_root)
    version = facts["version"]
    provenance = None
    if facts["capabilities"] is not None:
        provenance = (
            f"{facts['capabilities']} capabilities · {facts['addable']} addable "
            f"· release {facts['releaseRef']}"
        )
    if use_color:
        try:
            lines = [_paint_gradient(BANNER), _paint_wordmark(version), _paint_muted(BANNER_TAGLINE)]
            if provenance is not None:
                lines.append(_paint_muted(provenance))
            return "\n".join(lines)
        except Exception:
            # Colorization must never raise on the SessionStart hot path; a
            # crashing hook degrades the whole session. Fall through to plain.
            pass
    lines = [BANNER, f"{BANNER_WORDMARK}   ·   v{version}", BANNER_TAGLINE]
    if provenance is not None:
        lines.append(provenance)
    return "\n".join(lines)


def render_box(title: str, rows: list[tuple[str, str]], width: int = 60) -> str:
    """Render a labeled box with a title row."""
    inner = width
    top = "╭─ " + title + " " + "─" * (inner - len(title) - 3) + "╮"
    bot = "╰" + "─" * inner + "╯"
    lines = [top]
    for label, value in rows:
        text = f"  {label:<14}{value}" if label else "  "
        if len(text) > inner - 1:
            text = text[: inner - 2] + "…"
        lines.append("│" + text.ljust(inner) + "│")
    lines.append(bot)
    return "\n".join(lines)


def _paint_line(segments: list[tuple[str, str]], *, color: bool) -> str:
    """Render `[(text, style), ...]` to one line.

    When color is on, each segment is wrapped in its style's dim-cancelled
    truecolor SGR; when off (NO_COLOR), the segments are concatenated plain.
    Either way `strip_ansi(painted) == "".join(text for text, _ in segments)`,
    so the goldens track visible text and the model-facing context stays clean.
    """
    if not color:
        return "".join(text for text, _ in segments)
    out = []
    for text, style in segments:
        rgb, bold = _BAND_STYLES[style]
        bold_sgr = "\x1b[1m" if bold else ""
        out.append(f"{_SGR_UNDIM}{bold_sgr}{_fg(rgb)}{text}{_SGR_RESET}")
    return "".join(out)


def render_bands(groups: list, *, color: bool) -> list[str]:
    """One or more content groups sharing single rule dividers (the comp's idiom):
    rule, group, rule, group, …, rule. Adjacent groups share the divider instead
    of each drawing its own, so two bands never render a doubled rule. Each content
    line is either a pre-rendered string (e.g. a blank spacer) or a
    `[(text, style), ...]` segment list."""
    rule = _paint_line([("─" * _BAND_WIDTH, "muted")], color=color)
    out = [rule]
    for i, group in enumerate(groups):
        if i:
            out.append(rule)
        out.extend(item if isinstance(item, str) else _paint_line(item, color=color) for item in group)
    out.append(rule)
    return out


def render_band(content_lines: list, *, color: bool) -> list[str]:
    """A single rule-delimited status band — `render_bands` with one group."""
    return render_bands([content_lines], color=color)


def _mcp_indicator(mcp_status: str) -> tuple[str, str]:
    """Tri-state MCP indicator, because at SessionStart we usually CANNOT confirm
    connectivity: the sf-mcp-proxy mints its JWT lazily on the first message, so
    a "connecting"/"bridged" status is pending — not a failure. Only ✗ when we
    have positive evidence MCP is unusable.

    Recognizes two vocabularies: the legacy SessionStart strings
    ("connected"/"connecting"/"bridged") AND the WIN-033/040 health summary
    ("... active" when every observed server is ok; "partial —" when some are ok
    and some down; "not yet observed" while pending; "NOT activated"/"degraded" on
    trouble). Note "active" is NOT a substring of "not activated", so the healthy
    check does not misfire on the inactive summary.

    PRECEDENCE MATTERS: the partial summary contains the word "active" (as in
    "others active"), so "partial" MUST be tested before the healthy check or a
    half-outage would paint a false ✓."""
    low = mcp_status.lower()
    # Partial = some tracked servers healthy, at least one down. Its own glyph so a
    # half-working feature reads differently from both healthy and a full outage.
    if "partial" in low:
        return "⚠ partial", "warn"
    if "connected" in low or "active" in low:
        return "✓ connected", "ok"
    if "connecting" in low or "bridged" in low or "not yet observed" in low:
        return "⟳ connecting", "muted"
    return "✗ unavailable", "warn"


def _artifact_root(plugin_root: Optional[Path]) -> Path:
    return plugin_root or Path(__file__).resolve().parent.parent


def _installed_skill_count(plugin_root: Optional[Path] = None) -> Optional[int]:
    """The bundled (foundation) skill count, straight from the catalog. None when
    the catalog is unreadable — the count is dropped, never fabricated."""
    try:
        counts = json.loads((_artifact_root(plugin_root) / "catalog/discovery.json").read_text(encoding="utf-8"))["counts"]
        n = counts["foundation"]
        if type(n) is int and 0 <= n < _COUNT_CEILING:
            return n
    except _ARTIFACT_READ_ERRORS:
        pass
    return None


def _install_facets(
    plugin_root: Optional[Path] = None, *, skills: Optional[int] = None
) -> list[tuple[int, str]]:
    """Artifact-derived (count, label) facets for the install summary line.

    Fail-open per facet: an unreadable or empty artifact drops that facet rather
    than guessing a zero. Same discipline as `_banner_provenance` — nothing here
    is hardcoded; every number is counted from the checked-in plugin tree.
    """
    root = _artifact_root(plugin_root)
    facets: list[tuple[int, str]] = []
    if skills is None:
        skills = _installed_skill_count(plugin_root)
    if skills is not None:
        facets.append((skills, "skills"))
    for subdir, label in (("commands", "commands"), ("agents", "agents")):
        try:
            n = sum(1 for p in (root / subdir).glob("*.md") if p.is_file())
            if 0 < n < _COUNT_CEILING:
                facets.append((n, label))
        except _ARTIFACT_READ_ERRORS:
            pass
    try:
        servers = json.loads((root / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]
        if 0 < len(servers) < _COUNT_CEILING:
            facets.append((len(servers), "MCP servers"))
    except _ARTIFACT_READ_ERRORS:
        pass
    return facets


def _mcp_server_names(plugin_root: Optional[Path] = None) -> list[str]:
    """The configured MCP server ids from .mcp.json that the health glyph ACTUALLY
    covers, with the `salesforce-` prefix stripped for display
    (`salesforce-api-context` -> `api-context`). [] on any read error — the names
    line is then omitted rather than invented.

    Scoped to the platform-MCP servers in `_MCP_SERVER_SLUGS`: those are the
    org-gated remote servers this feature probes. `salesforce-lsp` is a LOCAL
    stdio process (not org-gated, not remotely reachable), so it is deliberately
    excluded — otherwise it would sit next to a single ✓/✗ glyph that never
    reflects it, which is exactly the mismatch a viewer misreads."""
    try:
        servers = json.loads((_artifact_root(plugin_root) / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]
    except _ARTIFACT_READ_ERRORS:
        return []
    names = []
    for key in servers:
        name = str(key)
        if name not in _MCP_SERVER_SLUGS:
            continue  # only servers the health glyph covers (excludes local lsp)
        names.append(name[len("salesforce-"):] if name.startswith("salesforce-") else name)
    return [n for n in names if n]


def _plugin_display_name(plugin_root: Optional[Path] = None) -> str:
    """This plugin's own name from its manifest; a pinned brand constant is the
    fail-open fallback (the plugin identity, like the wordmark, is allowed to be
    a constant — it does not vary per org)."""
    try:
        name = json.loads((_artifact_root(plugin_root) / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))["name"]
        if type(name) is str and name:
            return _clip(name, _IDENTITY_LIMIT)
    except _ARTIFACT_READ_ERRORS:
        pass
    return "salesforce-development"


def render_install_summary(
    color: bool, plugin_root: Optional[Path] = None, *, facts: Optional[dict] = None
) -> list[str]:
    """The install lockup, mirroring the comp's welcome block with real counts.

    "Installed" is a present-state label — the plugin IS installed, true on every
    session — so the green "✓ Installed <plugin>" lead reads honestly. (The dropped
    "reloaded"/"marketplace" fictions stay dropped: they claimed events the payload
    can't witness.) The skills story leads the facet line, mirroring the comp: the
    installed count in green against the artifact-derived library total, then the
    remaining facets (commands, agents, MCP servers). Every count is artifact-
    derived and drops out when unavailable — nothing here is hardcoded.
    """
    lines = [_paint_line(
        [("✓ Installed ", "ok"), (_plugin_display_name(plugin_root), "body")], color=color)]
    facts = facts or _banner_provenance(plugin_root)
    skills = facts.get("foundation")
    library = facts.get("library")
    others = [
        (n, label)
        for n, label in _install_facets(plugin_root, skills=skills)
        if label != "skills"
    ]
    segments: list[tuple[str, str]] = []
    if skills is not None:
        segments.append((f"{skills} skills installed", "ok"))
        if library is not None:
            segments.append((f" · {library} in library", "muted"))
    if others:
        joined = " · ".join(f"{n} {label}" for n, label in others)
        segments.append((f" · {joined}" if segments else joined, "muted"))
    if segments:
        lines.append(_paint_line(segments, color=color))
    return lines


def _org_summary_segments(org: dict) -> list[tuple[str, str]]:
    """The one-line org identity: `org <alias> <glyph> · <edition> · API <n>`.

    The reachability glyph is honest: ✓ only when list metadata resolved, ⚠ for
    the stale-auth branch of `resolve_org_info` (never a green check on stale
    auth). Both glyphs are one display column — the "stale auth" wording rides in
    the edition cell (which `resolve_org_info` sets to it) rather than a wider
    inline glyph, so the fixed budget is constant and the line holds ≤80 columns
    even on absurd values (17 fixed + 24 + 28 + 8 = 77).
    """
    edition_full = str(org.get("edition") or "unknown")
    glyph, gstyle = ("⚠", "warn") if "stale auth" in edition_full.lower() else ("✓", "ok")
    return [
        ("org: ", "body"),
        (_clip(str(org.get("alias") or "?"), _DISPLAY_NAME_LIMIT - 8), "body"),
        (" ", "body"),
        (glyph, gstyle),
        (" · ", "muted"),
        (_clip(edition_full, 28), "body"),
        (" · API ", "muted"),
        (_clip(str(org.get("apiVersion") or "unknown"), 8), "body"),
    ]


def _environment_content(org: dict, mcp_status: str, plugin_root: Optional[Path] = None) -> list:
    """The environment band's content (unframed): org summary, an optional dim
    detail line (username · instance), and the MCP line (real server names + a
    single tri-state indicator — never a fabricated per-server ✓)."""
    content: list = [_org_summary_segments(org)]
    detail = " · ".join(p for p in (org.get("username") or "", org.get("instanceUrl") or "") if p)
    if detail:
        content.append([(_clip(detail, 78), "muted")])
    mcp_short, mcp_style = _mcp_indicator(mcp_status)
    names = _mcp_server_names(plugin_root)
    if names:
        content.append([("MCP: ", "muted"), (_clip(" · ".join(names), 55), "muted"),
                        (" — ", "muted"), (mcp_short, mcp_style)])
    else:
        content.append([("MCP: ", "muted"), (mcp_short, mcp_style)])
    return content


def render_environment_band(org: dict, mcp_status: str, color: bool, plugin_root: Optional[Path] = None) -> list[str]:
    """The connected-org environment band as a standalone rule-framed band."""
    return render_band(_environment_content(org, mcp_status, plugin_root), color=color)


def _project_content(project: dict, stats: dict, git_line: str) -> list:
    """The project inventory band's content (unframed) — every fact the old
    project box carried, kept (C preserves facts the mock omits). The two stat
    rows are a single muted color, clipped as plain text to hold ≤80 columns."""
    header = [
        ("sfdx project: ", "body"),
        (_clip(str(project.get("name") or "Project"), _DISPLAY_NAME_LIMIT - 11), "head"),
        (" · Source API ", "muted"),
        (_clip(str(project.get("source_api") or "unknown"), 8), "body"),
        (" · ", "muted"),
        (_clip(str(project.get("package_dirs") or "force-app"), 20), "body"),
    ]
    row1 = (f"Apex {stats['apex_src']} src / {stats['apex_test']} test · Triggers {stats['triggers']} · "
            f"LWC {stats['lwc']} · Aura {stats['aura']} · Objects {stats['objects']}")
    row2 = f"Perm sets {stats['permsets']} · Flows {stats['flows']}"
    if git_line:
        row2 += f" · {git_line}"
    return [header, [(_clip(row1, 78), "muted")], [(_clip(row2, 78), "muted")]]


def render_project_band(project: dict, stats: dict, git_line: str, color: bool) -> list[str]:
    """The project inventory as a standalone rule-framed band."""
    return render_band(_project_content(project, stats, git_line), color=color)


def render_invitation(color: bool) -> list[str]:
    """The closing invitation: the "just say what you want" mindset line and the
    single DISCOVERY_POINTER (reused verbatim as the CTA so the visible message
    carries exactly one pointer). Counts are deliberately NOT restated here — the
    installed count rides in the install summary and the library/addable totals in
    the banner's provenance line, so repeating them would be a third printing of
    the same facts."""
    return [
        _paint_line([("You don't memorize commands here.", "head"),
                     (" Just say what you want to build.", "body")], color=color),
        _paint_line([(DISCOVERY_POINTER, "link")], color=color),
    ]


def render_banner_message(org: dict, project: dict, stats: dict, git_line: str, mcp_status: str,
                          *, color: Optional[bool] = None, state: Optional[dict] = None) -> str:
    """Compose the full SessionStart message: the pinned lockup, then the comp's
    rule-delimited bands — install summary, environment, project inventory — the
    position rail (when `state` is supplied), and the closing invitation.

    `color` defaults to the NO_COLOR-honoring `_banner_color_enabled()`, which is
    correct for the SessionStart systemMessage (the color-safe channel, stripped
    for the model by `_agent_context`). `/status` and `/welcome` print this to the
    model-reproduced stdout pipe — where ANSI turns to escape-junk — so they pass
    `color=False` to force the fully plain lockup (mirroring `cmd_journey`).

    `state` is the inferred journey state; pass it so the banner shows "where you
    are" (the rail) alongside "what's here" (the bands). Callers already resolved
    the org for the bands, so they build `state` via `_derive_journey_state` from
    that same data — no extra `sf` calls."""
    resolved = _banner_color_enabled() if color is None else color
    facts = _banner_provenance()
    # Leading blank line separates the banner from Claude Code's
    # `SessionStart:startup says:` wrapper that prefixes the systemMessage.
    parts = ["", render_banner_block(color=resolved, facts=facts), ""]
    parts += render_install_summary(resolved, facts=facts)
    parts.append("")
    # Environment and project render as one rule-region sharing a single middle
    # divider — no doubled rule between adjacent bands.
    parts += render_bands([
        _environment_content(org, mcp_status),
        _project_content(project, stats, git_line),
    ], color=resolved)
    # The rail rides below the bands. include_context=False: the bands right above
    # already state the project and org, so the rail's context row would repeat them.
    if state is not None:
        parts += ["", _render_journey_rail(state, color=resolved, include_context=False)]
    parts.append("")
    parts += render_invitation(resolved)
    return "\n".join(parts)


def render_degraded_banner(title: str, body_lines: list[str], project: Optional[dict] = None,
                           stats: Optional[dict] = None, git_line: str = "",
                           state: Optional[dict] = None) -> str:
    """A compact banner for non-success states (no org / unreachable). Leaner than
    the connected path — no install summary; the provenance line already signals
    the plugin is live and its inventory counts are not actionable when the problem
    is the org. Renders the lockup, then a rule-region: the guidance (bold title +
    the caller's lines verbatim) and, when a project is detected, the project band
    sharing the divider so a no-org/unreachable session still shows where you are.
    Then the pointer."""
    color = _banner_color_enabled()
    guidance: list = [[(_clip(title, 78), "head")]]
    for line in body_lines:
        guidance.append(_clip(line, 78) if not line else [(_clip(line, 78), "muted")])
    groups = [guidance]
    if project is not None and stats is not None:
        groups.append(_project_content(project, stats, git_line))
    parts = ["", render_banner_block(color=color), ""]
    parts += render_bands(groups, color=color)
    # Even with no reachable org, SessionStart shows the rail — its `likely next`
    # is exactly the action these states need (authenticate / set a target org).
    if state is not None:
        parts += ["", _render_journey_rail(state, color=color, include_context=False)]
    parts += ["", _paint_line([(DISCOVERY_POINTER, "link")], color=color)]
    return "\n".join(parts)


def render_status_surface(state: dict, org: Optional[dict], project: dict, stats: dict,
                          git_line: str, mcp_status: str, *, color: bool, logo: bool = False) -> str:
    """The on-demand status view painted when the user asks for status by name: the
    connected-org and project bands PLUS the position rail — the full "where I am"
    picture. Distinct from a positional question ("what's next"), which paints only
    the rail.

    Rides the color-carrying systemMessage channel. `logo` prepends the lockup on
    the rare turn the identity has not yet shown this session. The rail drops its
    context row (include_context=False) — the bands right above already state the
    project and org, so the row would only repeat them. With no reachable org the
    org band degrades to one honest line; the rail's `likely next` carries the fix."""
    parts: list[str] = [""]
    if logo:
        parts += [render_banner_block(color=color), ""]
    if org:
        env = _environment_content(org, mcp_status)
    else:
        ctx = state.get("context") or {}
        status = ctx.get("orgStatus")
        if status == "unreachable":
            line = f"org: {_clip(str(ctx.get('orgAlias') or 'target'), 32)} ✗ unreachable — sf org login web"
        elif status == "not-configured":
            line = "org: no default set — sf org login web, then sf config set target-org <alias>"
        else:  # unknown — the CLI could not be resolved or the org query failed
            line = "org: status unknown — check the Salesforce CLI (sf) is installed and on PATH"
        env = [[(_clip(line, 78), "muted")]]
    parts += render_bands([env, _project_content(project, stats, git_line)], color=color)
    parts += ["", _render_journey_rail(state, color=color, include_context=False)]
    return "\n".join(parts)


# The post-connect wayfinder: a LEAN re-orientation the plugin emits after the
# user connects an org mid-session (PostToolUse on `sf org login` / `sf config
# set target-org`). The big session-start lockup shows once; this is the reprise
# — a plugin-voice header, the colored journey rail, and the pointer — so the user
# lands back on "here's where you are now." The detailed environment/project bands
# are deliberately omitted (see render_wayfinder_message). It rides the
# systemMessage channel, the only pipe where the banner palette survives.
WAYFINDER_HEADER_NUDGE = "◆ salesforce-development"


def render_wayfinder_message(org: dict, project: dict, stats: dict, git_line: str,
                             mcp_status: str, color: bool, state: Optional[dict] = None) -> str:
    """Lean post-connect re-orientation: which org connected, the position rail, the
    one next step, and the pointer. Crucial-only — the detailed environment/project
    bands (username, instance URL, MCP-pending, the all-zero fresh-project inventory)
    are omitted: this fires on a routine target-org change, and the overture already
    played at session start. `project`/`stats`/`git_line`/`mcp_status` are accepted
    for signature stability but no longer rendered here.

    `state` is the inferred journey state; the caller has already resolved `org`, so
    it builds `state` via `_derive_journey_state` and passes it here — no second `sf`
    round-trip, and the rail can't disagree with the header (both read one org fetch)."""
    facets = [_clip(str(org.get("alias") or "org"), _DISPLAY_NAME_LIMIT),
              str(org.get("edition") or "unknown")]
    if org.get("apiVersion"):
        facets.append(f"API v{org['apiVersion']}")
    # Clip the whole header to the rail width — edition/API come from the org and
    # are normally short, but the ≤80 contract must hold even for hostile values.
    header = _clip("◆ connected — " + " · ".join(facets), _RAIL_WIDTH)
    parts = ["", _paint_line([(header, "head")], color=color)]
    # The rail without its context row — the header above already states the org.
    parts += ["", _render_journey_rail(state if state is not None else _journey_state(),
                                       color=color, include_context=False)]
    parts += ["", _paint_line([(DISCOVERY_POINTER, "link")], color=color)]
    return "\n".join(parts)


def render_wayfinder_nudge(color: bool, target: Optional[str] = None) -> str:
    """A lean nudge for the in-between state: the connect command ran but no
    reachable default org resolved yet (a login without --set-default, or a
    target that isn't reachable). Point at the one remaining step rather than
    re-orient against an org we don't actually have."""
    if target:
        body = [
            f"Target '{_clip(target, 32)}' is set but not reachable yet.",
            "Re-authenticate:  sf org login web --set-default",
        ]
    else:
        body = [
            "Logged in — set a default org to finish orienting:",
            "  sf config set target-org <alias>",
        ]
    lines = [_paint_line([(WAYFINDER_HEADER_NUDGE, "head")], color=color)]
    lines += [_paint_line([(_clip(line, 78), "muted")], color=color) for line in body]
    return "\n".join([""] + lines)


# --- SF CLI update notice (#244) --------------------------------------------
#
# Every `sf` invocation prints an "update available from X to Y" warning to
# STDERR. That leaks into agentic flows that read combined output, and the CLI
# silently drifts out of date. At SessionStart we surface it ONCE and let the
# agent offer the update, with a per-version no-nag gate so a decline (or a
# failed update) doesn't keep nagging for the SAME version — but a newer version
# prompts again.

# Set SFDX_SKIP_CLI_UPDATE_CHECK=1 to disable the whole check (mirrors SFDX_LSP).
_UPDATE_CHECK_ENV = "SFDX_SKIP_CLI_UPDATE_CHECK"
# Per-project suppression state, kept in the project's .sf directory.
_UPDATE_STATE = Path(".sf") / "sf-cli-update-state.json"
_ANSI_RE = __import__("re").compile(r"\x1b\[[0-9;]*m")


def _normalize_version(v: str) -> str:
    """Trim trailing punctuation/whitespace from a captured version token
    (the warning ends the version with a period: '… to 2.139.6.')."""
    return v.strip().rstrip(".")


def _detect_update_notice() -> Optional[dict]:
    """Read the cached oclif update warning from `sf version` stderr (no network
    call — oclif caches the check). Returns {current, latest} when an update is
    available, else None."""
    # We need stderr here (the oclif warning lands there), so we can't use run()
    # which only returns stdout — but we still resolve `sf` cross-platform via
    # build_command so a Windows `sf.cmd` shim is launched correctly (W-23466799 / WIN-026).
    argv = build_command("sf", ["version"])
    if argv is None:
        return None
    try:
        result = subprocess.run(
            argv, capture_output=True, text=True, timeout=_cli_timeout(), shell=False
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None
    stderr = _ANSI_RE.sub("", result.stderr or "")
    m = __import__("re").search(
        r"update available from (\S+) to (\S+)", stderr
    )
    if not m:
        return None
    return {
        "current": _normalize_version(m.group(1)),
        "latest": _normalize_version(m.group(2)),
    }


def _resolve_update_command() -> str:
    """The correct update command depends on how `sf` was installed:
    standalone installer → `sf update`; npm-global → reinstall via npm
    (`sf update` is a no-op there)."""
    sf_path = resolve_executable("sf")
    real = os.path.realpath(sf_path) if sf_path else ""
    if "node_modules" in real or "/npm/" in real:
        return "npm install --global @salesforce/cli@latest"
    return "sf update"


def _load_update_state() -> dict:
    try:
        return json.loads(_UPDATE_STATE.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def _is_update_suppressed(latest: str) -> bool:
    """Per-version gate: suppressed only when the declined/failed version equals
    the currently-available one. A newer `latest` is never suppressed."""
    return _load_update_state().get("declined_version") == latest


def _record_update_decision(version: str, reason: str) -> bool:
    """Persist a per-version suppression so we stop nagging for `version`.
    `reason` is 'user_declined' or 'update_failed'. Returns True on success."""
    try:
        _UPDATE_STATE.parent.mkdir(parents=True, exist_ok=True)
        _UPDATE_STATE.write_text(
            json.dumps(
                {"declined_version": version, "reason": reason},
                indent=2,
            )
        )
        return True
    except OSError:
        return False


def _update_advisory() -> Optional[str]:
    """Context block instructing the agent to offer the CLI update — or None
    when disabled, no update available, or the version is suppressed."""
    import os

    if os.environ.get(_UPDATE_CHECK_ENV) == "1":
        return None
    notice = _detect_update_notice()
    if not notice:
        return None
    if _is_update_suppressed(notice["latest"]):
        return None
    cmd = _resolve_update_command()
    return (
        "\n## Salesforce CLI update available\n\n"
        f"The SF CLI is **{notice['current']}**; **{notice['latest']}** is available. "
        "The CLI prints this notice to stderr on every invocation, which can pollute "
        "agentic output parsing — and the CLI is drifting out of date.\n\n"
        "**Before continuing with substantial work, offer to update it:**\n"
        f"- Ask the user if they want to update now. If yes, run: `{cmd}`\n"
        "- After a SUCCESSFUL update, confirm the new version and continue.\n"
        "- If the user declines, OR the update fails, record it so we stop "
        "nagging for this version (the gate is per-version — a newer release "
        "will prompt again):\n"
        f"  - declined: `sf-context record-update-decision {notice['latest']} user_declined`\n"
        f"  - failed:   `sf-context record-update-decision {notice['latest']} update_failed`\n"
        "- Do not re-prompt for this same version afterwards.\n"
    )


def cmd_record_update_decision() -> int:
    """Agent-invoked: persist a per-version no-nag suppression for the CLI
    update notice. Usage: sf-context record-update-decision <version> <reason>."""
    version = sys.argv[2] if len(sys.argv) > 2 else ""
    reason = sys.argv[3] if len(sys.argv) > 3 else "user_declined"
    if not version:
        print(
            json.dumps(
                {"ok": False, "error": "missing <version> argument"}
            )
        )
        return 1
    if reason not in ("user_declined", "update_failed"):
        reason = "user_declined"
    ok = _record_update_decision(_normalize_version(version), reason)
    print(json.dumps({"ok": ok, "declined_version": _normalize_version(version),
                      "reason": reason}))
    return 0 if ok else 1


# --- Plugin-effectiveness feedback loop (issue #277) -------------------------
# Supplies the three things a self-review lacks on its own: a trigger, an opt-in
# gate, and a moment to act. This module owns the trigger + gate only — it NEVER
# runs any grading (a non-interactive ≤5s hook can't; that needs the live model +
# session history). It only *offers* a stopping point to reflect on how the
# plugin's skills performed.
#
# Privacy posture (this is the FIRST step toward an off-machine path):
#   - DEFAULT OFF. Enabled per-project only via SFDX_FEEDBACK=1 (mirrors the
#     SFDX_AUTO_DEPLOY / SFDX_LSP env-var gates).
#   - The nudge surfaces ONCE per session and only after substantive work, so it
#     stays out of the way (Stop fires on every turn — see _feedback_already_nudged).
#   - It keeps a human in the loop before anything leaves the machine.
_FEEDBACK_ENV = "SFDX_FEEDBACK"
_FEEDBACK_STATE = Path(".sf") / "feedback-config.json"
# `sf` sub-commands that mark a session as having done substantive, gradeable work.
_FEEDBACK_SUBSTANTIVE = ("project deploy", "apex run test", "project retrieve")

# --- Turn-aware skills-first advisory (#415) ---------------------------------
# A turn-scoped ledger of which skills have dispatched in the CURRENT user turn,
# so the skills-first advisory (#286) stops re-nudging on every subsequent
# Edit/Write/raw-`sf` once the owning skill has already entered. The advisory
# hook is stateless per-call, so the state lives in a small JSON file:
#   { "session": "<session_id>", "skills": ["generating-apex", ...] }
# A `Skill`-matcher PreToolUse hook appends to `skills` (record-skill-dispatch),
# a UserPromptSubmit hook clears it at the top of each turn (reset-dispatch-turn,
# the turn delimiter — Claude Code passes no native turn id), and
# cmd_skills_first_advisory() reads it to suppress a nudge whose owning skill is
# already present. Keyed on session_id so a stale ledger from another session is
# ignored rather than wrongly suppressing. Same `.sf/` scratch convention and
# fail-silent discipline as the feedback state above.
_DISPATCH_STATE = Path(".sf") / "skill-dispatch-state.json"


def _feedback_enabled() -> bool:
    import os
    return os.environ.get(_FEEDBACK_ENV) == "1"


def _load_feedback_state() -> dict:
    try:
        return json.loads(_FEEDBACK_STATE.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def _feedback_already_nudged(session_id: str) -> bool:
    """One nudge per session: Stop fires at the end of every assistant turn, so
    without this guard the offer would repeat all session long."""
    if not session_id:
        return False
    return _load_feedback_state().get("nudged_session") == session_id


def _record_feedback_nudge(session_id: str) -> bool:
    try:
        _FEEDBACK_STATE.parent.mkdir(parents=True, exist_ok=True)
        state = _load_feedback_state()
        state["nudged_session"] = session_id
        _FEEDBACK_STATE.write_text(json.dumps(state, indent=2))
        return True
    except OSError:
        return False


def _transcript_has_substantive_work(transcript_path: str) -> bool:
    """Scan the session transcript (JSONL) for a substantive `sf` invocation —
    a deploy, a test run, or a retrieve. Best-effort and cheap: a plain substring
    scan of each line, no full JSON parse, capped so a huge transcript can't stall
    the ≤5s hook budget. Returns False (stay silent) on any read problem."""
    if not transcript_path:
        return False
    try:
        with open(transcript_path, "r", encoding="utf-8", errors="ignore") as fh:
            for i, line in enumerate(fh):
                if i > 20000:  # safety cap — well past any real session
                    break
                if "sf " in line and any(s in line for s in _FEEDBACK_SUBSTANTIVE):
                    return True
    except OSError:
        return False
    return False


def cmd_feedback_nudge() -> int:
    """Stop hook: when SFDX_FEEDBACK=1, offer a once-per-session prompt to reflect
    on how the plugin's skills performed after substantive work. WARN-ONLY — always
    `continue: true`; never blocks. Reads {session_id, transcript_path} from stdin.
    Stays silent (and cheap) when the gate is off, which is the default."""
    if not _feedback_enabled():
        print(json.dumps({"continue": True}))
        return 0
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except (json.JSONDecodeError, ValueError):
        payload = {}
    session_id = payload.get("session_id", "") or payload.get("sessionId", "")
    transcript = payload.get("transcript_path", "") or payload.get("transcriptPath", "")

    if _feedback_already_nudged(session_id):
        print(json.dumps({"continue": True}))
        return 0
    if not _transcript_has_substantive_work(transcript):
        print(json.dumps({"continue": True}))
        return 0

    _record_feedback_nudge(session_id)
    emit(
        "Stop",
        "💡 Plugin-effectiveness feedback (SFDX_FEEDBACK=1): this session ran "
        "substantive Salesforce work. If it's a good stopping point, consider "
        "reflecting on how the **plugin's skills** performed — whether the right "
        "skill dispatched, whether the capability hierarchy was followed, and "
        "whether MCP context was leveraged. Skip if mid-task. "
        "(Offered once per session; disable by unsetting SFDX_FEEDBACK.)",
    )
    return 0


def cmd_record_feedback_decision() -> int:
    """Agent-invoked: persist the per-project feedback opt-in choice in
    `.sf/feedback-config.json`. Usage:
        sf-context record-feedback-decision <on|off>
    Mirrors record-update-decision. The env var SFDX_FEEDBACK is the live gate;
    this records intent so the agent can remember the user's choice."""
    choice = (sys.argv[2] if len(sys.argv) > 2 else "").lower()
    if choice not in ("on", "off"):
        print(json.dumps({"ok": False, "error": "usage: record-feedback-decision <on|off>"}))
        return 1
    try:
        _FEEDBACK_STATE.parent.mkdir(parents=True, exist_ok=True)
        state = _load_feedback_state()
        state["opt_in"] = (choice == "on")
        _FEEDBACK_STATE.write_text(json.dumps(state, indent=2))
        ok = True
    except OSError:
        ok = False
    print(json.dumps({"ok": ok, "opt_in": choice == "on"}))
    return 0 if ok else 1


# --- Turn-aware skills-first advisory state (#415) ---------------------------

def _load_dispatch_state() -> dict:
    """Read the turn-scoped dispatch ledger; {} on any read/parse failure."""
    try:
        data = json.loads(_DISPATCH_STATE.read_text())
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _dispatched_skills(session_id: str) -> set[str]:
    """Skills already dispatched in the CURRENT turn for this session.

    Suppression requires a real session match: returns an empty set when
    `session_id` is missing (malformed payload — production always sends one) or
    when the ledger belongs to a different session (stale from a prior session
    that never got a UserPromptSubmit reset). This way we never wrongly suppress
    a nudge based on another session's — or an unkeyed — ledger."""
    if not session_id:
        return set()
    state = _load_dispatch_state()
    if state.get("session") != session_id:
        return set()
    skills = state.get("skills")
    return set(skills) if isinstance(skills, list) else set()


def cmd_record_skill_dispatch() -> int:
    """PreToolUse hook on the `Skill` tool: append the dispatched skill to the
    turn-scoped ledger so the skills-first advisory can stay quiet for that
    skill's owned ops for the rest of the turn (#415).

    WARN-ONLY by charter — always emits `continue: true`, NEVER denies (unlike
    the e2e harness's `log-dispatch` twin, which denies to intercept). Reads
    `{session_id, tool_input}` from stdin; the skill name is the Skill tool's
    `skill`/`name` input. Fail-silent on any I/O error."""
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except (json.JSONDecodeError, ValueError):
        payload = {}
    session_id = payload.get("session_id", "") or payload.get("sessionId", "")
    tool_input = payload.get("tool_input", {}) or payload.get("toolInput", {}) or {}
    skill = (
        tool_input.get("skill")
        or tool_input.get("skill_name")
        or tool_input.get("name")
        or ""
    )
    # The Skill tool may carry a plugin-qualified name (`salesforce-development:platform-apex-generate`);
    # the advisory matches on the bare skill name, so store the bare tail too.
    bare = skill.split(":")[-1] if skill else ""
    if bare:
        try:
            state = _load_dispatch_state()
            if state.get("session") != session_id:
                state = {"session": session_id, "skills": []}
            skills = state.get("skills")
            if not isinstance(skills, list):
                skills = []
            if bare not in skills:
                skills.append(bare)
            state["skills"] = skills
            _DISPATCH_STATE.parent.mkdir(parents=True, exist_ok=True)
            _DISPATCH_STATE.write_text(json.dumps(state, indent=2))
        except OSError:
            pass  # best-effort; never fail the hook on a log-write error
    print(json.dumps({"continue": True}))
    return 0


def cmd_reset_dispatch_turn() -> int:
    """UserPromptSubmit hook: reset the turn-scoped dispatch ledger at the top of
    each user turn (#415). This is the turn delimiter — Claude Code passes no
    native per-turn id, and `session_id` is stable across a session, so a new
    user prompt is the signal that a fresh turn (and a fresh skills-first budget)
    has begun. Re-seeds the ledger to the current session with no skills.

    WARN-ONLY — always `continue: true`; fail-silent on I/O error."""
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except (json.JSONDecodeError, ValueError):
        payload = {}
    session_id = payload.get("session_id", "") or payload.get("sessionId", "")
    try:
        _DISPATCH_STATE.parent.mkdir(parents=True, exist_ok=True)
        _DISPATCH_STATE.write_text(
            json.dumps({"session": session_id, "skills": []}, indent=2)
        )
    except OSError:
        pass
    print(json.dumps({"continue": True}))
    return 0


def _read_hook_payload() -> dict:
    """Read and parse the hook's JSON stdin payload once, TTY/empty-guarded.

    Claude Code passes e.g. `{"source": "startup", "session_id": "…"}`. Returns
    `{}` when stdin is a TTY (a manual `sf-context detect` run) or empty/unparseable
    (the `--plugin-dir` test harness), so callers default to the full startup path.
    Stdin reads once, so callers that need both `source` and `session_id` go through
    this rather than re-reading.
    """
    try:
        if sys.stdin.isatty():
            return {}
        data = sys.stdin.read()
    except Exception:
        return {}
    if not data.strip():
        return {}
    payload = parse_json(data)
    return payload if isinstance(payload, dict) else {}


def cmd_detect() -> int:
    payload = _read_hook_payload()
    source = payload.get("source") or payload.get("matcher") or ""
    session_id = payload.get("session_id") or payload.get("sessionId") or ""

    # After a context compaction the SessionStart hook re-fires with
    # source="compact" (PreCompact cannot inject context — it's block-only — so
    # SessionStart(compact)+additionalContext is the supported re-injection
    # point). Re-running the full detect here would re-mint the banner, re-hit
    # the org CLI, and re-inject the entire skill catalog — wasteful on exactly
    # the boundary compaction exists to economize. Instead re-inject ONLY the
    # lean skills-first reminder, with no CLI calls and no visible banner, so the
    # directive stays durable across long sessions (#406).
    if source == "compact":
        if not Path("sfdx-project.json").exists():
            print(json.dumps({"continue": True}))
            return 0
        emit("SessionStart", _agent_context(SKILLS_FIRST_REINJECT))
        return 0

    if not Path("sfdx-project.json").exists():
        # Stay silent in non-Salesforce directories — the plugins are global, but
        # surfacing a banner everywhere would be noisy. The orientation rule is
        # agent-facing only, so it adds no visible noise here; Welcome is a real
        # journey stage and "where am I?" is a fair question to ask from it.
        emit(
            "SessionStart",
            _agent_context(
                "No sfdx-project.json found. This does not appear to be a Salesforce project. "
                "Skills are still available if needed. " + DISCOVERY_POINTER
            ),
        )
        return 0

    # In a project → a banner carrying the HEADLESS logo AND the journey rail is
    # about to paint (every in-project branch below emits the rail via `state` —
    # connected or degraded). Record BOTH per-session markers now: `welcomed`, so
    # the first in-project orientation question does not re-show the logo, and
    # `entered`, so the first ordinary prompt does not repaint the rail this banner
    # already showed — a duplicate that would also cost a second org fetch,
    # defeating the no-double-fetch design (see cmd_orientation_paint's ambient
    # branch). A session that enters a project WITHOUT a SessionStart here (e.g.
    # `/cd` mid-session) records neither, so its first-message ambient rail still fires.
    _record_welcomed(session_id)
    _record_entered(session_id)

    root = Path.cwd().resolve()
    # Project context (name, source API, code inventory, git) is derivable the
    # moment sfdx-project.json is confirmed above — it needs no org. Compute it
    # once here so every path shares it: the connected banner AND the degraded
    # (no-org / unreachable) banners, which still show where you are even when
    # the org can't be reached.
    project = project_meta()
    stats = project_stats()
    git_line = git_status_line()

    # JWT minting + env-host resolution moved to the sf-mcp-proxy stdio bridge
    # (see the sf-mcp-proxy.bundled.js sibling) —
    # Claude Code's .mcp.json env-var
    # expansion happens at plugin load, before SessionStart hooks fire, so this
    # script can no longer be the place that produces those values. Here we
    # only resolve org metadata for the banner.
    bundled = fetch_org_info_via_node()

    if bundled and bundled.get("orgInfo"):
        org = bundled["orgInfo"]
    else:
        target = (bundled.get("targetOrg") if bundled else None) or get_target_org()
        if not target:
            state = _derive_journey_state(root, has_project=True, target="",
                                          target_error=None, org_display=None, has_source=False)
            msg = render_degraded_banner("No Default Org", [
                "Salesforce project detected, but no target-org is set.",
                "",
                "Quick start:",
                "  /salesforce-development:login --alias <name> --set-default",
                "",
                "Or directly:",
                "  sf org login web",
                "  sf config set target-org <alias>",
                "",
                "Skills are available for local code generation.",
            ], project=project, stats=stats, git_line=git_line, state=state)
            # The degraded paths carry no skills-first directive, so the orientation
            # rule is attached here explicitly — and these are precisely the states
            # ("no org", "unreachable") where the user asks where they are.
            emit("SessionStart", _agent_context(msg), system_message=msg)
            return 0

        with ThreadPoolExecutor(max_workers=2) as pool:
            list_fut = pool.submit(get_org_list)
            display_fut = pool.submit(get_org_display, target)
            org_list_data = list_fut.result()
            org_display_data = display_fut.result()

        org = resolve_org_info(target, org_list=org_list_data, org_display=org_display_data)
        if not org:
            state = _derive_journey_state(root, has_project=True, target=target,
                                          target_error=None, org_display=None, has_source=False)
            msg = render_degraded_banner("Org Unreachable", [
                f"Configured org '{target}' is unreachable.",
                "Auth may have expired or the org was deleted.",
                "",
                "Quick fix — re-authenticate:",
                "  sf org login web --alias <name> --set-default",
                "",
                "Or switch to a different org:",
                "  /salesforce-development:set-default <alias>",
                "",
                "Skills are available for local code generation.",
            ], project=project, stats=stats, git_line=git_line, state=state)
            # The degraded paths carry no skills-first directive, so the orientation
            # rule is attached here explicitly — and these are precisely the states
            # ("no org", "unreachable") where the user asks where they are.
            emit("SessionStart", _agent_context(msg), system_message=msg)
            return 0

    # MCP server health: actively probe both platform-MCP servers so the launch
    # banner reflects REAL current reachability, not a possibly-stale sidecar or a
    # blind "connecting" (the proxy mints its JWT lazily on first message, so
    # without a probe we would have no confirmed status at session start). Each
    # probe is ~1-2s and they run in parallel; a probe that can't run falls back
    # to the last-known sidecar (see _live_mcp_summary).
    mcp_status = _live_mcp_summary(active_org=(org.get("alias"), org.get("username")))

    # The reachable org is already resolved above, so build the rail from it — no
    # second `sf` round-trip. Only the local source check runs, a bounded
    # early-exit filesystem walk, to place the stage at Scaffold vs. Build.
    state = _derive_journey_state(
        root, has_project=True,
        target=org.get("alias") or org.get("username") or "org",
        target_error=None, org_display=org,
        has_source=_has_local_source_artifacts(root),
    )
    banner = render_banner_message(org, project, stats, git_line, mcp_status, state=state)
    # `systemMessage` is what the user sees (visible banner only).
    # `additionalContext` carries the banner PLUS the skills-first directive that
    # shapes Claude's behavior for the rest of the session — this is the lever
    # that keeps Claude from bypassing the installed skills with default knowledge.
    context = _agent_context(banner + "\n" + SKILLS_FIRST_DIRECTIVE)
    system_message = banner
    # Surface an available SF CLI update once per session (agent-facing guidance
    # only; the user-visible banner stays uncluttered). Per-version no-nag gate
    # lives in _update_advisory. See #244.
    advisory = _update_advisory()
    if advisory:
        context = context + "\n" + advisory
    emit("SessionStart", context, system_message=system_message)
    return 0


def cmd_verify_org() -> int:
    # Self-gate on the command: this gate fails CLOSED (denies) before a deploy or
    # delete, so it must run ONLY on those commands. Some Claude Code builds ignore
    # the plugin.json `if:` matcher and fire every PreToolUse Bash hook on every
    # command — without this gate, an unrelated `cd`/`ls`/`grep` would be DENIED
    # whenever no org is set, blocking ordinary shell use. Anything that is not a
    # deploy/delete is always allowed, before any CLI work.
    payload = _read_hook_payload()
    if not _DEPLOY_OR_DELETE_COMMAND.search(_hook_command(payload)):
        print(json.dumps({"continue": True}))
        return 0

    # W-23466800 (WIN-027): distinguish "the CLI itself can't be resolved" from "no org set".
    # An unresolvable `sf` is an environment failure, not a config choice;
    # conflating them (the Windows sf.cmd bug) produced a false "no org" and let a
    # shell fallback mask the real problem. Report it explicitly, with a
    # secret-free diagnostic, and still deny (fail closed on the deploy gate).
    # All deny reasons carry this source tag so a denial is never misattributed to
    # Claude Code's auto-mode classifier (the two gates have overlapping symptoms —
    # see the guard-rail note in README.md). This gate fires only on
    # `sf project deploy|delete`; it never gates read-only commands.
    tag = "[salesforce-development · deploy-gate] "
    if resolve_executable("sf") is None:
        emit(
            "PreToolUse",
            "",
            decision="deny",
            reason=(
                tag
                + "Salesforce CLI (sf) could not be resolved on PATH, so org state "
                "cannot be verified before deploying. Install/repair the CLI and "
                "ensure it is on PATH.\n"
                + render_diagnostic_lines(diagnostic_context(["sf"]))
            ),
        )
        return 0

    target, err = get_target_org_detailed()
    if err:
        # CLI present but the query failed — fail closed, but say WHY (not a false
        # "no org"), with a secret-free diagnostic (W-23466800 / WIN-027).
        emit(
            "PreToolUse",
            "",
            decision="deny",
            reason=(
                tag
                + f"Salesforce CLI (sf) is present but the org query failed ({err}), "
                "so org state cannot be verified before deploying.\n"
                + render_diagnostic_lines(diagnostic_context(["sf"]))
            ),
        )
        return 0
    if not target:
        emit(
            "PreToolUse",
            "",
            decision="deny",
            reason=tag + "No target org is configured. Run 'sf config set target-org <alias>' before deploying.",
        )
        return 0

    if not get_org_display(target):
        emit(
            "PreToolUse",
            "",
            decision="deny",
            reason=tag + "Cannot reach the target org. Your session may have expired. Run 'sf org login web' to re-authenticate.",
        )
        return 0

    print(json.dumps({"continue": True}))
    return 0


def cmd_status() -> int:
    """Print the same banner/org/project view as `detect`, but without writing env vars or fetching the JWT.
    Suitable for on-demand /salesforce-development:status invocations."""
    if not Path("sfdx-project.json").exists():
        print("No sfdx-project.json found in the current directory.")
        return 0

    # W-23466800 (WIN-027): an unresolvable CLI is distinct from "no org set" — say so.
    if resolve_executable("sf") is None:
        print("Salesforce CLI (sf) could not be resolved on PATH — cannot read org state.")
        print(render_diagnostic_lines(diagnostic_context(["sf"])))
        return 0

    target, err = get_target_org_detailed()
    if err:
        print(f"Salesforce CLI (sf) is present but the org query failed ({err}) — cannot read org state.")
        print(render_diagnostic_lines(diagnostic_context(["sf"])))
        return 0
    if not target:
        print("Salesforce project detected, but no default org is set.\n"
              "  1. sf org login web\n"
              "  2. sf config set target-org <alias>")
        return 0

    # Resolve the org BEFORE probing MCP health. An earlier version overlapped the
    # probe with this CLI fetch to shave ~1.4s, but the probe runs on an executor
    # thread that cannot be cancelled: on the unreachable-org early return below,
    # `concurrent.futures` still joins the live worker thread at interpreter exit,
    # so `/status` would hang until the probe subprocesses hit their timeout despite
    # having already printed the unreachable message. Probing an unreachable org is
    # wasted work anyway, so resolve first and skip the probe entirely when it fails.
    org = resolve_org_info(target)
    if not org:
        print(f"Salesforce project detected, but org '{target}' is unreachable. Run 'sf org login web' to re-authenticate.")
        return 0

    # WIN-040: actively probe MCP health so the banner reflects REAL current
    # reachability, not a possibly-stale sidecar (the demo gap: a server activated
    # with no intervening MCP traffic would otherwise still read inactive). Falls
    # back to the last-known sidecar for any server whose probe cannot run.
    mcp_status = _live_mcp_summary((target, org.get("alias"), org.get("username")))
    project = project_meta()
    stats = project_stats()
    git_line = git_status_line()

    # `/status` and `/welcome` are the status command — they show the rail too, so
    # this view matches SessionStart and the on-demand status paint. The org is
    # already resolved above; only the local source check is added.
    root = Path.cwd().resolve()
    state = _derive_journey_state(
        root, has_project=True,
        target=target, target_error=None, org_display=org,
        has_source=_has_local_source_artifacts(root),
    )

    # `/status` and `/welcome` capture this stdout and have the model reproduce
    # it verbatim — the model-reproduced pipe, where ANSI can't survive as color.
    # Force plain (like cmd_journey), then strip the rail's current-stage green
    # accent, which `_green` applies unconditionally: it belongs on the
    # systemMessage surfaces, never on this reproduced pipe (mirrors cmd_journey).
    banner = render_banner_message(org, project, stats, git_line, mcp_status, color=False, state=state)
    print(_ANSI_RE.sub("", banner))
    return 0


def cmd_status_org() -> int:
    """Print just the connected-org box (no banner, no project stats)."""
    # W-23466800 (WIN-027): if the CLI can't be resolved, say so explicitly (with a secret-free
    # diagnostic) rather than misreporting "no default org" — that false negative
    # was the Windows sf.cmd symptom that made /salesforce-development:org wrong.
    if resolve_executable("sf") is None:
        print("Salesforce CLI (sf) could not be resolved on PATH — cannot read org state.")
        print(render_diagnostic_lines(diagnostic_context(["sf"])))
        return 0

    target, err = get_target_org_detailed()
    if err:
        # The CLI is present but the query itself failed (timeout/nonzero/launch)
        # — distinct from "no org set", so don't misreport (W-23466800 / WIN-027).
        print(f"Salesforce CLI (sf) is present but the org query failed ({err}) — cannot read org state.")
        print(render_diagnostic_lines(diagnostic_context(["sf"])))
        return 0
    if not target:
        print("No default org configured. Run: sf config set target-org <alias>")
        return 0
    org = resolve_org_info(target)
    if not org:
        print(f"Org '{target}' is unreachable. Run: sf org login web")
        return 0

    def short(s: str, n: int) -> str:
        return s if len(s) <= n else s[: n - 1] + "…"

    print(render_box(
        "Connected Org",
        [
            ("Alias", org.get("alias", "?")),
            ("Edition", org.get("edition", "unknown")),
            ("API", f"v{org.get('apiVersion', '?')}"),
            ("Instance", short(org.get("instanceUrl") or "?", 60 - 18)),
            ("Username", short(org.get("username") or "?", 60 - 18)),
        ],
    ))
    return 0


def cmd_status_project() -> int:
    """Print just the project box (no banner, no org info)."""
    if not Path("sfdx-project.json").exists():
        print("No sfdx-project.json in the current directory.")
        return 0
    project = project_meta()
    stats = project_stats()
    git_line = git_status_line()
    proj_rows = [
        ("Source API", f"v{project.get('source_api', '?')}"),
        ("Package", project.get("package_dirs", "")),
        ("", ""),
        ("Apex", f"{stats['apex_src']} source / {stats['apex_test']} test"),
        ("Triggers", str(stats["triggers"])),
        ("LWC", str(stats["lwc"])),
        ("Aura", str(stats["aura"])),
        ("Objects", str(stats["objects"])),
        ("Perm sets", str(stats["permsets"])),
        ("Flows", str(stats["flows"])),
    ]
    if git_line:
        proj_rows.append(("", ""))
        proj_rows.append(("Git", git_line))
    print(render_box(project.get("name", "Project"), proj_rows))
    return 0


# Executed-Bash-command matchers. The deploy-time hooks (verify-org, post-deploy,
# the sf-deploy-gate prod-check/destructive gates, lsp-precheck) and the wayfinder
# all SELF-GATE on the command with these, instead of trusting the plugin.json
# `if:` matcher — some Claude Code builds ignore `if:` and fire every Bash hook on
# every command. Self-gating is what keeps verify-org from denying an unrelated
# `cd`/`ls` when no org is set, keeps the wayfinder rail from painting after a
# `cd`, and keeps post-deploy from advising "Deployment complete" after a grep (or
# after a check-only `deploy validate`). These match the executed command string,
# distinct from `_CONNECT_INTENT`, which matches a natural-language user prompt.
#
# `\s+` (not a literal space) is deliberate: `sf` tolerates arbitrary whitespace
# (`sf  project   deploy`), so a single-space match would let an unusual-but-valid
# command slip a gate. The bash gates (scripts/sf-deploy-gate, bin/lsp-precheck)
# mirror these patterns so the two guards can't diverge on whitespace.
_CONNECT_COMMAND = re.compile(r"(?i)\bsf\s+org\s+login\b|\bsf\s+config\s+set\s+target-org\b")
# Only the prod-MUTATING deploy forms (start/quick/resume) — the ones after which
# metadata actually changed the org. Excludes check-only `deploy validate` and
# `preview`/`report`/`cancel`, so post-deploy's "Deployment complete" advice never
# fires on an operation that deployed nothing (which could make the model skip the
# real deploy after a validate).
_DEPLOY_MUTATING_COMMAND = re.compile(r"(?i)\bsf\s+project\s+deploy\s+(?:start|quick|resume)\b")
# Deploy OR delete, any sub-command — the reachability gate (verify-org) fires on
# the whole family, since even a `validate` needs a resolvable, reachable org.
_DEPLOY_OR_DELETE_COMMAND = re.compile(r"(?i)\bsf\s+project\s+(?:deploy|delete)\b")


def _hook_command(payload: dict) -> str:
    """The executed Bash command from a PreToolUse/PostToolUse hook payload, or ""."""
    tool_input = payload.get("tool_input") or payload.get("toolInput") or {}
    return (tool_input.get("command") or "") if isinstance(tool_input, dict) else ""


def cmd_wayfinder() -> int:
    """PostToolUse hook after an org-connect command (`sf org login` / `sf config
    set target-org`): a LEAN, colored re-orientation on the systemMessage channel
    — connected org + project state + journey position — without re-minting the
    session-start lockup.

    Self-gates on the command: this fires only when the executed Bash command is an
    org-connect. The plugin.json `if:` matcher scopes it too, but not every Claude
    Code build honors `if:` — some fire every Bash hook on every command — so the
    gate lives here as well, or the rail would paint after an unrelated `cd`/grep.
    (The single registration in plugin.json is what keeps one connect = one paint.)

    Fail open: a crashing PostToolUse hook must never disrupt the session, so any
    error degrades to a silent {"continue": true}. Emits color only on the
    user-visible systemMessage; the model-facing additionalContext is a short
    plain (ANSI-free) note that the target org just changed, so the model updates
    the working assumption SessionStart may have set (e.g. "no default org")."""
    try:
        payload = _read_hook_payload()
        if not _CONNECT_COMMAND.search(_hook_command(payload)):
            print(json.dumps({"continue": True}))
            return 0
        if not Path("sfdx-project.json").exists():
            print(json.dumps({"continue": True}))
            return 0
        color = _banner_color_enabled()
        root = Path.cwd().resolve()
        target, err = get_target_org_detailed()
        if err or not target:
            # The connect command ran, but no default org resolves yet.
            emit("PostToolUse", "", system_message=render_wayfinder_nudge(color))
            return 0
        org = resolve_org_info(target)
        if not org:
            emit("PostToolUse", "",
                 system_message=render_wayfinder_nudge(color, target=target))
            return 0
        project = project_meta()
        stats = project_stats()
        git_line = git_status_line()
        mcp_status = "bridged via sf-mcp-proxy (run /doctor to confirm)"
        # Build the rail from the org just resolved — no second `sf` round-trip, and
        # the rail can't disagree with the header above (both from one org fetch).
        state = _derive_journey_state(
            root, has_project=True,
            target=org.get("alias") or org.get("username") or target,
            target_error=None, org_display=org,
            has_source=_has_local_source_artifacts(root),
        )
        msg = render_wayfinder_message(org, project, stats, git_line, mcp_status, color, state=state)
        # Plain, ANSI-free model note — the color rides systemMessage only.
        model_note = (
            f"Target org is now '{org.get('alias') or target}' "
            f"({org.get('edition') or 'unknown'}, API v{org.get('apiVersion') or '?'}). "
            "Update the working assumption accordingly."
        )
        emit("PostToolUse", model_note, system_message=msg)
        return 0
    except Exception:
        print(json.dumps({"continue": True}))
        return 0


_NODE_MIN = (18, 0)
_NPM_MIN = (3, 10)


def _parse_semver(version_str: str) -> tuple[int, ...]:
    """Extract leading numeric components from a version string like 'v18.3.0' or '2.138.6'."""
    import re
    nums = re.findall(r"\d+", version_str)
    return tuple(int(n) for n in nums[:3]) if nums else (0,)


def _check_sf_cli() -> dict:
    raw = run(["sf", "--version"])
    if not raw:
        return {"name": "Salesforce CLI", "status": "critical", "version": None,
                "message": "Not found — install with: npm install --global @salesforce/cli"}
    version_match = __import__("re").search(r"@salesforce/cli/(\S+)", raw)
    version = version_match.group(1) if version_match else raw.strip().splitlines()[0]

    # Readiness = latest. When the cached oclif check reports a newer release, the
    # CLI is installed but out of date — a 🟡 warning, not 🟢. Reuses the same
    # no-network notice the session banner uses (_detect_update_notice reads the
    # cached warning from `sf version` stderr). Honors the hard update-check
    # opt-out (SFDX_SKIP_CLI_UPDATE_CHECK=1) so a user who disabled update checks
    # never sees this warn; the per-version no-nag suppression does NOT apply here
    # — an explicit readiness scan reports the factual state each time.
    if os.environ.get(_UPDATE_CHECK_ENV) != "1":
        notice = _detect_update_notice()
        if notice and notice.get("latest") and notice["latest"] != version:
            return {"name": "Salesforce CLI", "status": "warn", "version": version,
                    "message": f"Version {version} is outdated — {notice['latest']} is available. "
                               f"Update with: {_resolve_update_command()}"}

    return {"name": "Salesforce CLI", "status": "ok", "version": version, "message": "Installed"}


_CODE_ANALYZER_PLUGIN = "@salesforce/plugin-code-analyzer"


def _jit_registered_plugins() -> dict:
    """Return the CLI's `oclif.jitPlugins` map (plugin name → pinned version), or {}.

    A JIT ("just-in-time") plugin is declared by the Salesforce CLI but only
    physically installed the first time one of its commands runs. `sf plugins
    inspect` FAILS for a JIT plugin that hasn't been auto-installed yet, so a
    plugin can be fully available to the user and still look "not installed" to
    inspect. The root CLI entry in `sf plugins --json` carries the CLI's own
    package.json under `pjson`, whose `oclif.jitPlugins` map is the authoritative
    registry of these deferred plugins."""
    data = parse_json(run(["sf", "plugins", "--json"]))
    if not isinstance(data, list):
        return {}
    for entry in data:
        if not isinstance(entry, dict):
            continue
        is_root = entry.get("isRoot") or (entry.get("options") or {}).get("isRoot")
        if not is_root:
            continue
        oclif = (entry.get("pjson") or {}).get("oclif") or {}
        jit = oclif.get("jitPlugins")
        return jit if isinstance(jit, dict) else {}
    return {}


def _check_code_analyzer() -> dict:
    # Fast path: physically installed → `sf plugins inspect` returns its version.
    data = parse_json(run(["sf", "plugins", "inspect", _CODE_ANALYZER_PLUGIN, "--json"]))
    # inspect returns a list; take the first entry. A not-installed JIT plugin can
    # yield {"error": {}} (or nothing), so require a real version before calling it
    # installed — otherwise fall through to the JIT check below.
    entry = (data[0] if isinstance(data, list) and data else data) or {}
    version = entry.get("version") if isinstance(entry, dict) else None
    if version:
        return {"name": "Code Analyzer plugin", "status": "ok", "version": version, "message": "Installed"}

    # Not physically installed — but if the CLI registers it as a JIT plugin, it
    # will auto-install on first `sf code-analyzer` run. That's available, not
    # missing, so do NOT report it critical.
    jit = _jit_registered_plugins()
    if _CODE_ANALYZER_PLUGIN in jit:
        return {"name": "Code Analyzer plugin", "status": "ok",
                "version": jit.get(_CODE_ANALYZER_PLUGIN) or "unknown",
                "message": "Registered as a JIT plugin — installs automatically on first `sf code-analyzer` run"}

    return {"name": "Code Analyzer plugin", "status": "critical", "version": None,
            "message": "Not installed — run: sf plugins install @salesforce/plugin-code-analyzer"}


def _check_node() -> dict:
    raw = run(["node", "--version"])
    if not raw:
        return {"name": "Node.js", "status": "critical", "version": None,
                "message": "Not found — install Node.js >= 18 from https://nodejs.org"}
    version = raw.strip()
    parsed = _parse_semver(version)
    if parsed < _NODE_MIN:
        return {"name": "Node.js", "status": "critical", "version": version,
                "message": f"Version {version} is below the required minimum (18). Upgrade from https://nodejs.org"}
    major = parsed[0]
    # Warn on odd (non-LTS) major versions
    if major % 2 != 0:
        return {"name": "Node.js", "status": "warn", "version": version,
                "message": f"Version {version} is a non-LTS release. Consider switching to the latest even-numbered LTS."}
    return {"name": "Node.js", "status": "ok", "version": version, "message": "Installed"}


def _check_npm() -> dict:
    raw = run(["npm", "--version"])
    if not raw:
        return {"name": "NPM", "status": "critical", "version": None,
                "message": "Not found — NPM is usually bundled with Node.js"}
    version = raw.strip()
    parsed = _parse_semver(version)
    if parsed < _NPM_MIN:
        return {"name": "NPM", "status": "warn", "version": version,
                "message": f"Version {version} is below the recommended minimum (3.10). Run: npm install --global npm@latest"}
    return {"name": "NPM", "status": "ok", "version": version, "message": "Installed"}


def _check_git() -> dict:
    raw = run(["git", "--version"])
    if not raw:
        return {"name": "Git", "status": "critical", "version": None,
                "message": "Not found — install Git from https://git-scm.com"}
    version = raw.strip()
    return {"name": "Git", "status": "ok", "version": version, "message": "Installed"}


def _check_source_tracking() -> dict:
    target = get_target_org()
    if not target:
        return {"name": "Source Tracking", "status": "warn", "version": None,
                "message": "No default org configured — connect an org first, then re-run setup"}
    raw = run(["sf", "project", "deploy", "preview", "--json", "--target-org", target])
    if not raw:
        return {"name": "Source Tracking", "status": "warn", "version": None,
                "message": f"Could not determine status for org '{target}'. Run: sf org enable tracking"}
    data = parse_json(raw)
    if data.get("status") == 1:
        msg = str(data.get("message", "")).lower()
        if "source tracking" in msg or "not supported" in msg or "not enabled" in msg:
            return {"name": "Source Tracking", "status": "warn", "version": None,
                    "message": f"Not enabled for org '{target}'. Run: sf org enable tracking"}
        return {"name": "Source Tracking", "status": "warn", "version": None,
                "message": f"Could not verify for org '{target}': {data.get('message', 'unknown error')}"}
    return {"name": "Source Tracking", "status": "ok", "version": None,
            "message": f"Enabled for org '{target}'"}


# --- Per-server platform-MCP health (WIN-033 passive + WIN-040 active) --------------------
# Shared contract with the Node producer (proxy.js) — see CONTRACT-mcp-health.md at the repo
# root. The consumer owns this server-key -> slug-arg mapping; the sidecar filename AND the
# `--probe` CLI arg both use the SLUG ARG (e.g. "metadata-experts"), never the `.mcp.json`
# server key ("salesforce-metadata-experts").
_MCP_SERVER_SLUGS = {
    "salesforce-api-context": "salesforce-api-context",
    "salesforce-metadata-experts": "metadata-experts",
}

# state -> (row status, message). "inactive" is the headline case both WIN-033/WIN-040
# exist for: the server is not activated/provisioned for this tenant.
_MCP_STATE_TABLE = {
    "ok": ("ok", "Server active and reachable"),
    "inactive": ("critical",
                 "Server not activated in this org — enable it in Setup -> Integrations -> "
                 "API Catalog -> MCP Servers -> Salesforce Servers, set this server to Active, "
                 "then re-run /status"),
    "auth": ("warn", "Auth/JWT problem reaching the server — re-run sf org login web"),
    "env-not-ready": ("warn",
                       "No org/project context — connect an org in a Salesforce project, "
                       "then re-run /status"),
    "unreachable": ("warn", "Server endpoint unreachable — check network or VPN"),
}

# Directory the producer writes sidecars into: <cwd>/.sf/mcp-health/<slug>.json.
_MCP_HEALTH_DIR = Path(".sf") / "mcp-health"


def _mcp_row_name(slug: str) -> str:
    return f"Salesforce MCP ({slug})"


def _read_health_sidecar(slug: str) -> Optional[dict]:
    """WIN-033 (passive): read `.sf/mcp-health/<slug>.json` if present.

    Returns the parsed dict on success, or None when the sidecar is absent,
    unreadable, or not valid JSON — callers must treat None as "no observation
    yet", never invent a state. Never raises."""
    path = _MCP_HEALTH_DIR / f"{slug}.json"
    try:
        if not path.exists():
            return None
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _render_mcp_state_row(slug: str, state: Optional[str], detail: str = "") -> dict:
    """Render a check-tools row for `slug` from a health `state` string, per the
    state -> row-status/message table in CONTRACT-mcp-health.md. An unknown/missing
    state renders as a neutral warn row rather than crashing or guessing "ok"."""
    mapping = _MCP_STATE_TABLE.get(state or "")
    if mapping is None:
        return {"name": _mcp_row_name(slug), "status": "warn", "version": None,
                "message": f"Unrecognized health state '{state}' reported for this server"}
    status, message = mapping
    if detail and state == "inactive":
        message = f"{message} ({detail})"
    return {"name": _mcp_row_name(slug), "status": status, "version": None, "message": message}


def _passive_mcp_row(slug: str) -> dict:
    """WIN-033: render a row from the sidecar if one exists, else a neutral
    "not yet observed" row (never invent a state when the sidecar is absent)."""
    sidecar = _read_health_sidecar(slug)
    if sidecar is None:
        return {"name": _mcp_row_name(slug), "status": "info", "version": None,
                "message": "Not yet observed — run a task, or /salesforce-development:check-tools to probe"}
    return _render_mcp_state_row(slug, sidecar.get("state"), str(sidecar.get("detail") or ""))


def _summarize_mcp_states(observed: dict) -> str:
    """Render the compact one-line MCP-health summary from a {slug: state} map of
    observations. Shared by the passive (sidecar-read) and live (active-probe)
    summaries so both speak the exact same vocabulary the banner icon
    (`_mcp_indicator`) recognizes. Reports the least-healthy observed state so an
    inactive server is never hidden behind a healthy one; a partial observation —
    some servers `ok`, others not yet observed, none bad — reads as PENDING, not
    an outage."""
    # Order = severity (worst first) so the summary surfaces the worst state.
    severity = ["inactive", "unreachable", "auth", "env-not-ready", "ok"]
    total = len(_MCP_SERVER_SLUGS)
    if not observed:
        return "sf-mcp-proxy: not yet observed — run check-tools to probe (api-context, metadata-experts)"
    worst = next((s for s in severity if s in observed.values()), None)
    if worst == "ok" and len(observed) == total:
        return "sf-mcp-proxy: api-context, metadata-experts active"
    # PARTIAL: at least one tracked server is healthy AND at least one is in a bad
    # state (inactive/unreachable/auth). A half-working feature is neither a full
    # outage nor healthy, so it gets its own "partial" summary → ⚠ glyph. The word
    # "partial" is what `_mcp_indicator` keys on, and it is checked there BEFORE
    # the "active" test so the "(others active)" wording does not read as healthy.
    healthy = [s for s, st in observed.items() if st == "ok"]
    bad_states = ("inactive", "unreachable", "auth")
    has_bad = any(st in bad_states for st in observed.values())
    partial = bool(healthy) and has_bad
    if worst == "inactive":
        bad = ", ".join(s for s, st in observed.items() if st == "inactive")
        if partial:
            return (f"sf-mcp-proxy: partial — {bad} NOT activated in this org "
                    f"(others active) — enable in Setup (check-tools for detail)")
        return f"sf-mcp-proxy: {bad} NOT activated in this org — enable in Setup (check-tools for detail)"
    if worst == "ok":
        # Every observed server is ok, but at least one has not reported yet.
        # This is pending, not degraded — the summary must read as connecting
        # (contains "not yet observed", never "active"), so the banner shows ⟳.
        pending = ", ".join(s for s in _MCP_SERVER_SLUGS.values() if s not in observed)
        return f"sf-mcp-proxy: {pending} not yet observed — run check-tools to probe"
    # Any real bad/mixed state (auth / unreachable / env-not-ready).
    if partial:
        return "sf-mcp-proxy: partial — some servers degraded (others active) — run check-tools for per-server detail"
    return "sf-mcp-proxy: degraded — run check-tools for per-server detail"


def _org_identity_candidates(active_org) -> set:
    """Normalize the caller's notion of "the active org" to a set of acceptable
    identifier strings. `active_org` may be a single string (alias OR username)
    or an iterable of them — the producer stamps whichever `resolveTargetOrg`
    returned (often the configured username), while the consumer usually knows
    the resolved alias for the SAME org, so a sidecar is valid when its `org`
    matches ANY known identifier. Empty/None entries are dropped."""
    if active_org is None:
        return set()
    values = [active_org] if isinstance(active_org, str) else list(active_org)
    return {str(v) for v in values if v}


def _sidecar_state_for_org(slug: str, active_org):
    """Last-known state for `slug` from its sidecar, org-filtered. Returns the
    state string, or None when there is no usable observation. A sidecar written
    against a DIFFERENT org is rejected (a stale/foreign `ok` must not read as
    healthy for the org the user is on now) — but only when we both know the
    active org AND the sidecar recorded one, so a valid reading is never
    over-filtered.

    `active_org` may be a single identifier (alias or username) or a collection
    of them; the sidecar is accepted when its `org` matches ANY of them, so an
    alias-vs-username mismatch for the same org does not reject a valid reading
    (review P2 #2)."""
    sidecar = _read_health_sidecar(slug)
    if sidecar is None:
        return None
    accepted = _org_identity_candidates(active_org)
    sidecar_org = sidecar.get("org")
    if accepted and sidecar_org and sidecar_org not in accepted:
        return None
    return sidecar.get("state")


def _passive_mcp_summary(active_org=None) -> str:
    """WIN-033: a compact one-line MCP-health summary built from the passively
    observed health sidecars (no network, no JWT mint). `active_org` (a single
    alias/username or a collection of them) filters observations to the current
    org (see `_sidecar_state_for_org`). Used where a fast, network-free read is
    preferred over live accuracy."""
    observed = {}
    for slug in _MCP_SERVER_SLUGS.values():
        state = _sidecar_state_for_org(slug, active_org)
        if state is not None:
            observed[slug] = state
    return _summarize_mcp_states(observed)


def _live_mcp_summary(active_org=None) -> str:
    """WIN-040: like `_passive_mcp_summary` but ACTIVELY probes each server first,
    so the banner reflects real current reachability rather than a possibly-stale
    sidecar. This is what keeps the UI honest after a server is activated/
    deactivated with no intervening MCP traffic (the demo gap): the probe mints a
    JWT and does one `initialize` round-trip per server (~1-2s each, run in
    parallel), and — as a side effect — rewrites the sidecar, so a later passive
    read stays consistent.

    A live probe result is authoritative for THIS session's org, so it is used
    directly (no org filter needed). For any server whose probe could not run at
    all (missing bundle / timeout / offline), we fall back to that server's
    last-known org-filtered sidecar, so a transient failure degrades to the
    cached reading instead of erasing it."""
    slugs = list(_MCP_SERVER_SLUGS.values())
    results: dict = {}
    if slugs:
        with ThreadPoolExecutor(max_workers=len(slugs)) as pool:
            futs = {slug: pool.submit(_probe_server_raw, slug) for slug in slugs}
            results = {slug: f.result() for slug, f in futs.items()}
    observed = {}
    for slug in slugs:
        data = results.get(slug)
        if isinstance(data, dict) and data.get("state"):
            observed[slug] = data.get("state")  # live probe: authoritative
            continue
        state = _sidecar_state_for_org(slug, active_org)  # fall back to last-known
        if state is not None:
            observed[slug] = state
    return _summarize_mcp_states(observed)


def _probe_server_raw(slug: str, timeout: Optional[int] = None) -> Optional[dict]:
    """WIN-040: actively probe one MCP server via
    `node <sf-mcp-proxy.bundled.js> --probe <slug>`, through the same WIN-026
    resolver used by the rest of this module (build_command/run_result — the
    same resolution `get_target_org`/`get_org_display` rely on for `sf`).

    Returns the parsed `{slug,state,detail,httpStatus,org}` JSON line from
    stdout, or None when the probe could not be run at all (missing proxy
    bundle, non-zero exit, timeout, or unparseable stdout) — the caller
    decides how to degrade (e.g. fall back to the passive sidecar). Never
    raises."""
    proxy = Path(__file__).resolve().parent / "sf-mcp-proxy.bundled.js"
    if not proxy.exists():
        return None
    res = run_result(["node", str(proxy), "--probe", slug], timeout=timeout)
    if not res.ok:
        return None
    stdout = (res.stdout or "").strip()
    if not stdout:
        return None
    # Contract: "--probe" prints exactly one JSON line to stdout. Take the last
    # non-empty line defensively in case anything else leaked onto stdout.
    line = stdout.splitlines()[-1]
    data = parse_json(line)
    return data if isinstance(data, dict) and data else None


def _probe_server(slug: str, timeout: Optional[int] = None) -> dict:
    """WIN-040: render a check-tools row from a live `--probe` run of `slug`.
    Thin rendering wrapper over `_probe_server_raw` — never raises; a probe
    that could not be run at all renders a `warn` row explaining that, rather
    than crashing the whole check-tools report."""
    data = _probe_server_raw(slug, timeout=timeout)
    if data is None:
        return {"name": _mcp_row_name(slug), "status": "warn", "version": None,
                "message": "Could not probe this server — see /doctor or re-run /status"}
    return _render_mcp_state_row(slug, data.get("state"), str(data.get("detail") or ""))


def _check_mcp() -> list:
    """MCP readiness, split into THREE deterministic, independently-reported
    concerns (W-23466800 / WIN-027): (a) config-file presence, (b) platform endpoint
    reachability, and (c) actual MCP process health. Each is its own row and none
    is inferred from another — in particular, a present `.mcp.json` is NOT
    reported as a healthy MCP process, and a green config/endpoint never flips the
    process row green."""
    here = Path(__file__).resolve().parent.parent
    rows = []

    # (a) Config-file presence — deterministic, offline (file + proxy binary).
    mcp_file = here / ".mcp.json"
    servers = []
    if not mcp_file.exists():
        rows.append({"name": "Salesforce MCP (config)", "status": "critical", "version": None,
                     "message": f".mcp.json not found at {mcp_file}. Try /reload-plugins."})
    else:
        parsed = True
        try:
            data = json.loads(mcp_file.read_text())
            servers = list(data.get("mcpServers", {}).keys())
        except (json.JSONDecodeError, OSError):
            parsed = False
        if not parsed:
            rows.append({"name": "Salesforce MCP (config)", "status": "warn", "version": None,
                         "message": ".mcp.json found but could not be parsed"})
        elif not servers:
            rows.append({"name": "Salesforce MCP (config)", "status": "warn", "version": None,
                         "message": ".mcp.json has no mcpServers configured"})
        else:
            # PR #5 (W-23466798 / WIN-010) replaced the extensionless `sf-mcp-proxy` Bash
            # wrapper with an exec-form Node launch of the bundled JS, so the
            # presence check targets the bundle. The file check itself is a plain
            # Path.exists (no external tool), but everything in this module that
            # DOES shell out (get_target_org/get_org_display below) now runs
            # through the W-23466799 (WIN-026) resolver.
            # NOTE (sf-skills-internal port): the bundle is vendored alongside this
            # module under scripts/, not under a bin/ subdir, so resolve it as a
            # sibling of __file__ (mirrors _bundled_helper_path for sf-org-info).
            proxy = Path(__file__).resolve().parent / "sf-mcp-proxy.bundled.js"
            if not proxy.exists():
                rows.append({"name": "Salesforce MCP (config)", "status": "critical", "version": None,
                             "message": f"MCP proxy bundle missing at {proxy}. Try /reload-plugins."})
            else:
                rows.append({"name": "Salesforce MCP (config)", "status": "ok", "version": None,
                             "message": f"Configured ({', '.join(servers)})"})

    # (b) Per-server platform-MCP health (WIN-033 + WIN-040 — see
    # CONTRACT-mcp-health.md). Replaces the old single "endpoint reachability"
    # row (an org-instance-URL HEAD probe, `_probe_url`, which only proved
    # network connectivity, never the platform-MCP host itself). check-tools is
    # an on-demand invocation, so the row SHOWN here is the live `--probe`
    # result (WIN-040) for each of the 2 servers; the proxy's own sidecar write
    # keeps a later passive read (`_passive_mcp_row`, WIN-033) consistent. The
    # two probes are independent subprocess calls, so run them concurrently
    # (same nested-pool pattern as the org-list/org-display fetch above) rather
    # than paying their timeouts back-to-back.
    with ThreadPoolExecutor(max_workers=2) as pool:
        probe_futs = [pool.submit(_probe_server, slug) for slug in _MCP_SERVER_SLUGS.values()]
        rows.extend(f.result() for f in probe_futs)

    # (c) Actual MCP process health — NOT knowable from this script (Claude Code
    # owns the MCP subprocess lifecycle). Report it as INFORMATIONAL (not a
    # warning) so a healthy setup can read fully green, while still refusing to
    # infer "healthy" from (a)/(b) — the W-23466800 (WIN-027) anti-pattern (config presence
    # must not become an inaccurate green).
    rows.append({"name": "Salesforce MCP (process)", "status": "info", "version": None,
                 "message": "Process health not verified here — confirm with /mcp or /doctor. "
                            "A green config/endpoint does NOT prove the MCP process launched."})
    return rows


def cmd_check_tools() -> int:
    """Run all prerequisite checks and print a JSON report.

    `_check_mcp` returns a LIST (its three distinct concerns), so results are
    flattened. On ANY hard failure a secret-free `diagnostic` block is attached
    (W-23466800 / WIN-027) so the failure is understandable — and so it is not quietly flipped
    green by a model-run shell fallback that finds the tool a different way."""
    with ThreadPoolExecutor(max_workers=_check_tools_workers()) as pool:
        futures = [
            pool.submit(_check_sf_cli),
            pool.submit(_check_code_analyzer),
            pool.submit(_check_node),
            pool.submit(_check_npm),
            pool.submit(_check_git),
            pool.submit(_check_mcp),
            pool.submit(_check_source_tracking),
        ]
        raw_results = [f.result() for f in futures]

    results = []
    for r in raw_results:
        if isinstance(r, list):
            results.extend(r)
        else:
            results.append(r)

    output = {"tools": results}
    if any(r.get("status") == "critical" for r in results):
        output["diagnostic"] = diagnostic_context()
    print(json.dumps(output))
    return 0


def cmd_post_deploy() -> int:
    # Self-gate on the command: advise only after a deploy actually MUTATED the org
    # (start/quick/resume). Two failure modes this guards: some Claude Code builds
    # ignore the plugin.json `if:` matcher and fire every PostToolUse Bash hook on
    # every command (so `cd`/grep must stay silent); and even a real
    # `sf project deploy validate`/`preview`/`report`/`cancel` deploys NOTHING, so
    # "Deployment complete" there is a false signal the model might act on — e.g.
    # concluding metadata is live and skipping the real deploy after a validate.
    payload = _read_hook_payload()
    if not _DEPLOY_MUTATING_COMMAND.search(_hook_command(payload)):
        print(json.dumps({"continue": True}))
        return 0
    emit(
        "PostToolUse",
        "Deployment complete. Consider:\n"
        "- Assign permission sets: sf org assign permset --name <PermSetName>\n"
        "- Run tests: sf apex run test --synchronous\n"
        "- Verify in org: sf org open",
    )
    return 0


# --- Deploy-failure advisory (issue #405) ------------------------------------
# `cmd_post_deploy` only fires on a SUCCESSFUL deploy — Claude Code routes a
# failed tool call to the distinct `PostToolUseFailure` event (verified on the
# installed version, not assumed). A failed deploy is the richest teaching
# moment in the SF loop, so we route it to the owning skill.
#
# Key constraint discovered empirically: the `PostToolUseFailure` payload does
# NOT carry the tool's stdout/stderr (no `tool_response`) — only the original
# `tool_input.command` and a terse `error: "Exit code N"`. So we CANNOT parse
# the deploy's `--json` error here. We don't need to: the model already has the
# error text in its own context. The hook's job is to route ATTENTION to the
# owning skill at the failure moment and hand the model a decision tree to match
# against the error it can already see. Advisory-only, fail-open.
def cmd_post_deploy_failure() -> int:
    """PostToolUseFailure advisory: route a failed deploy to the owning skill.

    Fail-open — any missing/garbled payload or a non-deploy command yields a
    silent allow. Never blocks.
    """
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except (json.JSONDecodeError, ValueError):
        payload = {}
    tool_input = payload.get("tool_input") or payload.get("toolInput") or {}
    cmd = (tool_input.get("command") or "") if isinstance(tool_input, dict) else ""

    # The hook is matcher-scoped to `Bash(sf project deploy*)`, but defend against
    # a mis-wired matcher: only advise on an actual deploy command.
    if "sf project deploy" not in cmd:
        print(json.dumps({"continue": True}))
        return 0

    # Branch on the deploy sub-command. `validate` and `quick` are prod-path
    # operations with their own owning skills; bare `deploy start` is the general
    # case. (`sf project deploy start` is the common form; the others are rarer.)
    if "deploy validate" in cmd:
        owner = ("platform-deploy-validate",
                 "A pre-deploy VALIDATION failed — it caught the problem before it reached the org.")
    elif "deploy quick" in cmd:
        owner = ("platform-quick-deploy",
                 "A quick-deploy (validated job → prod) failed.")
    else:
        owner = ("platform-metadata-deploy", "A deploy failed.")

    skill, lead = owner
    advice = (
        f"⚠️ Deploy-failure check: {lead} Before retrying, dispatch the owning "
        f"skill rather than hand-editing and re-running raw `sf`:\n"
        f"- Route to `{skill}` for the deploy workflow + error-recovery steps.\n"
        f"- If the error names a FIELD shape (Roll-up Summary, Master-Detail, "
        f"formula return type, FLS on a required field), the fix belongs in "
        f"`platform-custom-field-generate`.\n"
        f"- If it names an OBJECT shape (sharing model, name field, "
        f"deployment-status), use `platform-custom-object-generate`.\n"
        f"- For a permission-set / FLS error, use `platform-permission-set-generate`.\n"
        f"- For an Apex compile/test failure, use `platform-apex-generate` / "
        f"`platform-apex-test-generate`.\n"
        f"Match the error you just saw to the skill above and dispatch it. "
        f"(Advisory only — proceeding is allowed; see #405.)"
    )
    emit("PostToolUseFailure", advice)
    return 0


# --- Skills-first advisory (issue #286) --------------------------------------
# The SKILLS_FIRST_DIRECTIVE is injected once at SessionStart, but two project
# effectiveness reviews (complex-object-superbadge, apex-callouts-superbadge)
# showed a fluent agent routes straight to raw `sf`/metadata edits and the
# directive has ~0 behavioral effect. This PreToolUse advisory re-surfaces the
# owning skill at the point of bypass. It is WARN-ONLY by design — it NEVER
# blocks (hooks observe-and-advise, per CLAUDE.md); it emits `additionalContext`
# nudging a skills-first check, then lets the tool run.

# Ordered (pattern, skill, why) rules. First match wins: Edit/Write file paths are
# matched against the metadata-XML patterns, Bash commands against the `sf`
# sub-command needles. Kept deliberately small and high-precision — only the
# operations the reviews caught bypassing.
# Metadata-XML suffixes with NO owning skill in the corpus. Editing these must
# NOT trigger the generic "use the matching platform metadata skill" nudge,
# because that skill does not exist — an advisory pointing at a phantom skill is
# pure noise (#445 item 3). This is a precise allowlist of common owner-less
# types, matched on the filename tail; anything not listed keeps the generic
# nudge (the conservative default, since a real owning skill usually exists).
_OWNERLESS_META_SUFFIXES = (
    "reportfolder-meta.xml",       # report folders (the report itself → platform-report-generate)
    "dashboard-meta.xml",
    "dashboardfolder-meta.xml",
    "labels-meta.xml",             # custom labels
    "settings-meta.xml",           # org/feature settings
    "layout-meta.xml",             # page layouts (classic)
    "profile-meta.xml",            # profiles
    "custommetadata-meta.xml",     # custom metadata type records
    "staticresource-meta.xml",
    "remotesite-meta.xml",
    "namedcredential-meta.xml",
    "email-meta.xml",              # email templates
)


def _has_no_owning_skill(path: str) -> bool:
    """True if `path` is a metadata type with no owning skill (stay silent)."""
    return any(path.endswith(suffix) for suffix in _OWNERLESS_META_SUFFIXES)


def _skills_first_match(tool_name: str, tool_input: dict) -> Optional[tuple[str, str]]:
    """Return (skill_hint, advice) for a bypass-prone op, or None to stay silent."""
    if tool_name in ("Edit", "Write", "MultiEdit"):
        path = (tool_input.get("file_path") or tool_input.get("filePath") or "").lower()
        if not path:
            return None
        # Apex source edits — the implementation-phase bypass from #413's review,
        # where every `.cls`/`.trigger` was authored via raw Edit and
        # `platform-apex-generate` never fired (triggers matched; invocation didn't).
        # Match the source files, not the `.cls-meta.xml` sidecar (low value).
        if path.endswith(".cls") or path.endswith(".trigger"):
            if path.endswith("test.cls"):
                return ("platform-apex-test-generate", "authoring an Apex test class directly")
            return ("platform-apex-generate", "authoring Apex directly")
        # Code sidecars (`.cls-meta.xml` / `.trigger-meta.xml`) are apiVersion/status
        # stubs, not metadata authoring — stay quiet rather than emit the generic
        # "editing metadata XML" nudge below.
        if path.endswith(".cls-meta.xml") or path.endswith(".trigger-meta.xml"):
            return None
        # Metadata XML edits — the declarative-bypass class from #286's source review.
        if path.endswith("-meta.xml") or "/objects/" in path or "/fields/" in path:
            if "field-meta.xml" in path or "/fields/" in path:
                return ("platform-custom-field-generate",
                        "editing custom-field metadata directly")
            if "object-meta.xml" in path or "/objects/" in path:
                return ("platform-custom-object-generate",
                        "editing custom-object metadata directly")
            if "flexipage-meta.xml" in path:
                return ("platform-flexipage-generate", "editing a FlexiPage directly")
            if "permissionset-meta.xml" in path:
                return ("platform-permission-set-generate", "editing a permission set directly")
            if "flow-meta.xml" in path:
                return ("automation-flow-generate", "editing a Flow directly")
            if "validationrule-meta.xml" in path:
                return ("platform-validation-rule-generate",
                        "editing a validation rule directly")
            if "listview-meta.xml" in path:
                return ("platform-list-view-generate", "editing a list view directly")
            if "tab-meta.xml" in path:
                return ("platform-custom-tab-generate", "editing a custom tab directly")
            if "report-meta.xml" in path:
                return ("platform-report-generate", "editing a report directly")
            # NOTE: *.app-meta.xml is intentionally NOT mapped — it's ambiguous
            # between CustomApplication (platform-custom-application-generate) and an
            # Aura app bundle (platform-lightning-app-coordinate); a wrong name is
            # worse than the generic nudge below.
            #
            # The generic fallback only fires for metadata types that HAVE an
            # owning skill somewhere in the corpus. Types with no owning skill
            # (e.g. *.reportFolder-meta.xml, *.labels-meta.xml, *.settings-meta.xml)
            # must NOT nudge — a "use the matching skill" advisory that points at
            # a skill that doesn't exist is pure noise (#445 item 3). Keep an
            # allowlist of owner-less suffixes that stay silent.
            if _has_no_owning_skill(path):
                return None
            return ("the matching platform metadata skill", "editing metadata XML directly")
        return None

    if tool_name == "Bash":
        cmd = tool_input.get("command", "") or ""
        # Order matters: most specific sub-commands first.
        rules = [
            ("sf apex run test", "platform-apex-test-run", "running Apex tests via raw CLI"),
            ("sf apex run", "platform-apex-anonymous-run", "running anonymous Apex via raw CLI"),
            ("sf project retrieve", "platform-metadata-retrieve", "retrieving org metadata via raw CLI"),
            ("sf data query", "platform-soql-query", "querying org data via raw CLI"),
        ]
        for needle, skill, why in rules:
            if needle in cmd:
                return (skill, why)
        return None

    return None


def cmd_skills_first_advisory() -> int:
    """PreToolUse advisory: nudge toward the owning skill on bypass-prone ops.

    WARN-ONLY — always emits `continue: true`; never denies. Reads the tool
    payload from stdin (Claude Code passes `{tool_name, tool_input}` JSON), the
    same channel sf-deploy-gate uses.
    """
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except (json.JSONDecodeError, ValueError):
        payload = {}
    tool_name = payload.get("tool_name", "") or payload.get("toolName", "")
    tool_input = payload.get("tool_input", {}) or payload.get("toolInput", {}) or {}
    session_id = payload.get("session_id", "") or payload.get("sessionId", "")

    match = _skills_first_match(tool_name, tool_input)
    if not match:
        # Nothing to advise — stay quiet so the hook adds no noise to normal ops.
        print(json.dumps({"continue": True}))
        return 0

    skill, why = match
    # Turn-aware suppression (#415): if the owning skill has already dispatched in
    # this turn, the developer/model is already in the validated workflow — don't
    # re-nudge on every subsequent owned Edit/Write/raw-`sf`. Per-skill scope: a
    # `platform-apex-generate` dispatch silences `.cls`/`.trigger` nudges but NOT a
    # later `platform-permission-set-generate` op. The generic fallbacks ("the
    # matching platform metadata skill") are not real skill names, so they never
    # match the ledger and keep nudging — the conservative choice.
    if skill in _dispatched_skills(session_id):
        print(json.dumps({"continue": True}))
        return 0

    advice = (
        f"⚠️ Skills-first check: this looks like {why}. "
        f"The `{skill}` skill likely owns this operation — it encodes the "
        f"validated workflow, governor-limit/FLS guardrails, and error recovery "
        f"that a raw call skips. Prefer dispatching it before continuing. "
        f"(Advisory only — proceeding is allowed; see #286.)"
    )
    emit("PreToolUse", advice)
    return 0


JOURNEY_STAGES = ("Welcome", "Setup", "Scaffold", "Build", "Deploy", "Observe")

# One bounded, deterministic next action per stage. Deliberately generic: the
# rail knows the stage, never the user's intent, so nothing here may promise an
# outcome or name a command the session has not verified is available.
NEXT_ACTION: dict[str, str] = {
    "Welcome": "Create or open a Salesforce DX project.",
    "Setup": "Authenticate an org, then explicitly set it as the target.",
    "Scaffold": "Create source in a declared package directory.",
    "Build": "Run the owning tests, then validate before deploying.",
    "Deploy": "Validate against a declared target before deploying.",
    "Observe": "Use the owning architecture and observability skills.",
}

# Rail geometry: one glyph plus ten connectors is an 11-column cell, so stage
# labels land under their own glyph. The cell is deliberately wider than the
# longest label ("scaffold", 8) so adjacent labels keep clear air between them —
# at 9 columns "scaffold build" read as one word. len(connector)+1 must equal the
# cell width, or the glyph row and label row drift out of alignment.
_JOURNEY_GLYPHS = {"complete": "●", "current": "◉", "future": "○", "unknown": "○"}
_JOURNEY_CONNECTOR = "─" * 10
_JOURNEY_CELL_WIDTH = 11
_JOURNEY_LABEL_WIDTH = 14
_DISPLAY_NAME_LIMIT = 32
# The rail is pinned like the banner: every line stays inside 80 columns so the
# glyph/label/marker alignment survives a standard terminal.
_RAIL_WIDTH = 80

_SALESFORCE_SOURCE_SUFFIXES = {
    ".cls", ".trigger", ".page", ".component", ".resource", ".email",
}
_BUNDLE_SOURCE_SUFFIXES = {
    ".js", ".ts", ".html", ".css", ".svg", ".cmp", ".app", ".evt",
    ".intf", ".design", ".auradoc", ".tokens",
}


def _is_salesforce_source_artifact(path: Path, package_root: Path) -> bool:
    """Recognize bounded Metadata API source and Lightning bundle files."""
    try:
        relative = path.relative_to(package_root)
    except ValueError:
        return False
    name = path.name.casefold()
    if name.endswith("-meta.xml") and len(name) > len("-meta.xml"):
        return True
    if path.suffix.casefold() in _SALESFORCE_SOURCE_SUFFIXES:
        return True
    parts = tuple(part.casefold() for part in relative.parts[:-1])
    for bundle_type in ("lwc", "aura"):
        if bundle_type in parts:
            index = parts.index(bundle_type)
            if len(parts) >= index + 2 and path.suffix.casefold() in _BUNDLE_SOURCE_SUFFIXES:
                return True
    return False


def _has_local_source_artifacts(project_root: Path) -> bool:
    """Return whether a declared local package directory contains a source file.

    This is deliberately a local, read-only check. It follows packageDirectories
    from sfdx-project.json, does not inspect org state, and does not treat the
    project descriptor or top-level housekeeping files as source artifacts.
    """
    try:
        descriptor = json.loads(project_root.joinpath("sfdx-project.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        descriptor = {}
    entries = descriptor.get("packageDirectories") if isinstance(descriptor, dict) else None
    paths = [entry.get("path") for entry in entries or [] if isinstance(entry, dict) and entry.get("path")]
    if not paths:
        paths = ["force-app"]

    root = project_root.resolve()
    excluded_dirs = {"node_modules", ".git", ".sf", ".sfdx", ".claude"}
    for configured in paths:
        candidate = (root / str(configured)).resolve()
        if candidate != root and root not in candidate.parents:
            continue
        if not candidate.is_dir():
            continue
        for current, dirs, files in os.walk(candidate):
            dirs[:] = [name for name in dirs if name not in excluded_dirs and not name.startswith(".")]
            current_path = Path(current)
            for filename in files:
                path = current_path / filename
                try:
                    relative_to_root = path.relative_to(root)
                    relative_to_package = path.relative_to(candidate)
                except ValueError:
                    continue
                if relative_to_root == Path("sfdx-project.json"):
                    continue
                # When the package path is '.', root-level repository/config files
                # are not evidence of Salesforce source.
                if candidate == root and len(relative_to_package.parts) == 1:
                    continue
                if path.is_file() and _is_salesforce_source_artifact(path, candidate):
                    return True
    return False


def _bounded_display_name(value: object) -> str:
    """Clamp untrusted text to a single printable, bounded rail cell.

    Descriptor names and org aliases are attacker-controlled in a cloned repo (and
    the alias is org-supplied), while the rail is a fixed-shape surface the model is
    told to present. An embedded newline or a 300-char run there would forge
    plugin-authored copy and break the pinned line count, so strip anything
    non-printable (newlines, tabs, ANSI) and truncate the way render_box does.
    Untrusted JSON carries untrusted *types* too, so a non-string is "" rather
    than a TypeError on a hook path.
    """
    if not isinstance(value, str):
        return ""
    printable = "".join(ch for ch in value if ch.isprintable()).strip()
    if len(printable) > _DISPLAY_NAME_LIMIT:
        return printable[: _DISPLAY_NAME_LIMIT - 1] + "…"
    return printable


def _project_display_name(project_root: Path) -> Optional[str]:
    """Name the project from its descriptor, falling back to the directory name.

    Root-bound on purpose: project_meta() reads the current directory and
    substitutes a "Project" placeholder, and neither is honest on this path.
    None means there is no project here at all.
    """
    descriptor = project_root.joinpath("sfdx-project.json")
    if not descriptor.is_file():
        return None
    try:
        data = json.loads(descriptor.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        data = {}
    declared = _bounded_display_name(data.get("name") if isinstance(data, dict) else None)
    # Directory names are untrusted too — macOS permits newlines in them.
    return declared or _bounded_display_name(project_root.name) or "(unnamed)"


def _derive_journey_state(
    root: Path,
    *,
    has_project: bool,
    target: str,
    target_error: Optional[str],
    org_display: Optional[dict],
    has_source: bool,
) -> dict:
    """Infer the journey stage from already-gathered facts — pure, no CLI or
    filesystem I/O. Split out of `_journey_state` so a caller that has ALREADY
    resolved the org (SessionStart's banner, the on-demand status paint) can build
    the identical rail without a second `sf` round-trip. `_journey_state` is the
    fetching wrapper; this is the derivation both share."""
    current = "Welcome"
    reason = "No sfdx-project.json is present in the current directory."
    # Four honest states, never a fake boolean — unknown / not-configured /
    # unreachable / reachable. "unknown" is the answer before a project exists,
    # because this path never probes an org at the Welcome stage.
    org_status, org_alias = "unknown", None

    if has_project:
        current = "Setup"
        reason = "A Salesforce DX project is present, but no configured and reachable target org was verified."
        if target:
            org_status, org_alias = "unreachable", target
            if org_display:
                current = "Scaffold"
                reason = "The project and target org are available, but no local source artifacts were found."
                # `sf org display` output is untrusted in shape as well as content:
                # get_org_display() can hand back a `result` array or a non-string
                # alias, so degrade to the configured target instead of raising.
                declared = org_display.get("alias") if isinstance(org_display, dict) else None
                org_status = "reachable"
                org_alias = _bounded_display_name(declared) or target
                if has_source:
                    current = "Build"
                    reason = "The project, reachable target org, and local source artifacts are available."
        elif not target_error:
            # Only the clean ("", "") leg means "no default org is set". A failed
            # query stays "unknown" — never a fabricated "no org" (W-23466800 /
            # WIN-027), matching every other get_target_org_detailed() caller.
            org_status = "not-configured"

    current_index = JOURNEY_STAGES.index(current)
    stages = []
    for index, name in enumerate(JOURNEY_STAGES):
        if name in ("Deploy", "Observe"):
            status = "unknown"
        elif index < current_index:
            status = "complete"
        elif index == current_index:
            status = "current"
        else:
            status = "future"
        stages.append({"name": name, "status": status})
    return {
        "mode": "journey",
        "currentStage": current,
        "reason": reason,
        "stages": stages,
        "context": {
            "project": _project_display_name(root),
            "orgAlias": _bounded_display_name(org_alias) if org_alias else None,
            "orgStatus": org_status,
            # Pending in iteration-1: the only available check issues an extra
            # `sf project deploy preview`, which must never run on this path.
            "sourceTracking": "unknown",
        },
        "inferenceBounded": True,
        "boundary": (
            "Inference uses only the current project descriptor, a configured/reachable target, "
            "and local source artifacts. Deploy and Observe require durable verified history."
        ),
    }


def _journey_state(project_root: Optional[Path] = None) -> dict:
    """Gather the journey facts from the CLI + filesystem, then derive the stage.

    The self-contained path: probe target-org, org display, and local source, then
    hand off to `_derive_journey_state`. Callers that have ALREADY resolved the org
    (SessionStart, the status paint) skip this and call `_derive_journey_state`
    directly, so the org is never queried twice for one surface."""
    root = (project_root or Path.cwd()).resolve()
    has_project = root.joinpath("sfdx-project.json").is_file()
    target, target_error = "", None
    org_display: Optional[dict] = None
    has_source = False
    if has_project:
        target, target_error = get_target_org_detailed()
        if target:
            org_display = get_org_display(target)
            if org_display:
                has_source = _has_local_source_artifacts(root)
    return _derive_journey_state(
        root,
        has_project=has_project,
        target=target,
        target_error=target_error,
        org_display=org_display,
        has_source=has_source,
    )


def _resolve_position_and_org(root: Path) -> tuple[dict, Optional[dict]]:
    """Resolve the org ONCE and return (journey_state, org_or_None) for the status
    surface, which shows both the org band and the rail. Fetching here — rather than
    letting `_journey_state` re-probe — keeps the org to a single round-trip:
    `org list` and `org display` run in parallel (matching `cmd_detect`), and the
    derived state is built from the same data the band uses. Fails soft: an
    unresolvable CLI or a failed query yields a Setup/unknown state and no org band,
    never a fabricated 'no org' (W-23466800 / WIN-027)."""
    if resolve_executable("sf") is None:
        state = _derive_journey_state(root, has_project=True, target="",
                                      target_error="cli-unresolved", org_display=None, has_source=False)
        return state, None
    target, target_error = get_target_org_detailed()
    org: Optional[dict] = None
    org_display: Optional[dict] = None
    has_source = False
    if target and not target_error:
        with ThreadPoolExecutor(max_workers=2) as pool:
            list_fut = pool.submit(get_org_list)
            display_fut = pool.submit(get_org_display, target)
            org_list_data = list_fut.result()
            org_display = display_fut.result()
        if org_display:
            org = resolve_org_info(target, org_list=org_list_data, org_display=org_display)
            has_source = _has_local_source_artifacts(root)
    state = _derive_journey_state(root, has_project=True, target=target,
                                  target_error=target_error, org_display=org_display, has_source=has_source)
    return state, org


def _journey_org_cell(context: dict, limit: int = _DISPLAY_NAME_LIMIT) -> str:
    """State the org honestly, including when it was never configured or probed."""
    status = context.get("orgStatus")
    # Already bounded in _journey_state; "(unnamed)" covers an alias with nothing
    # printable in it, so the cell never renders as a bare "org  ✓".
    alias = _clip(context.get("orgAlias") or "(unnamed)", limit)
    if status == "reachable":
        return f"org: {alias} ✓"
    if status == "unreachable":
        return f"org: {alias} ✗ unreachable"
    if status == "not-configured":
        return "org: not configured"
    return "org: unknown"


def _journey_context_line(context: dict) -> str:
    """Compose the context row, clamped so the pinned rail always fits 80 columns.

    Only the two untrusted names give ground. The source-tracking state is a fact
    about what was NOT checked, so it is never the thing dropped to make room, and
    the rail keeps its geometry instead of soft-wrapping at the terminal edge.
    """
    project = context.get("project")
    line = ""
    for limit in range(_DISPLAY_NAME_LIMIT, 3, -1):
        line = "   ".join([
            f"sfdx project: {_clip(project, limit)}" if project else "sfdx project: (none detected)",
            _journey_org_cell(context, limit),
            "source-tracking … (not probed)",
        ])
        if len(line) <= _RAIL_WIDTH:
            break
    return line


_JOURNEY_GLYPH_STYLES = {"complete": "ok", "current": "link", "future": "muted", "unknown": "muted"}


def _render_signpost(state: dict, *, color: bool = False, include_context: bool = True) -> list[str]:
    """The visual signpost lines: (optionally) the context row, the glyph bar, and
    the stage labels. Shared by the journey rail, the getting-started welcome, and
    the wayfinder (which omits the context row — its header already states the org).

    Every glyph is derived from that stage's status, so an unknown stage can never
    render as complete. No "you are here" marker — the current stage reads from its
    ◉ glyph and the `likely next` line; the positioned marker jumbled the layout.
    """
    stages = state["stages"]
    context = state.get("context") or {}
    glyphs: list[tuple[str, str]] = []
    for index, stage in enumerate(stages):
        if index:
            glyphs.append((_JOURNEY_CONNECTOR, "muted"))
        g = _JOURNEY_GLYPHS.get(stage["status"], "○")
        # The current stage's dot is greened — the single accent marking "you are
        # here" on the otherwise-plain rail (honors NO_COLOR; strips to plain).
        glyphs.append((_green(g) if stage["status"] == "current" else g,
                       _JOURNEY_GLYPH_STYLES.get(stage["status"], "muted")))
    labels = "".join(
        (_green(s["name"].lower()) if s["status"] == "current" else s["name"].lower())
        + " " * max(0, _JOURNEY_CELL_WIDTH - len(s["name"]))
        for s in stages
    ).rstrip()
    lines: list = []
    if include_context:
        lines += [_paint_line([(_journey_context_line(context), "muted")], color=color), ""]
    lines += [_paint_line(glyphs, color=color), _paint_line([(labels, "body")], color=color)]
    return lines


def _render_journey_rail(state: dict, *, color: bool = False, include_context: bool = True) -> str:
    """Render the six-stage signpost rail from an inferred journey state: the
    signpost plus the one `likely next` step. Flush-left by design.

    Trimmed to signpost + next step — the legend and the "Deploy and Observe stay
    unknown" / "Inference is bounded" footnotes were removed as noise; the ◉ glyph
    and the next action carry the meaning. `include_context=False` also drops the
    context row (the wayfinder's header already states the org).
    """
    return "\n".join([
        *_render_signpost(state, color=color, include_context=include_context),
        "",
        _paint_line([(f"{'likely next':<{_JOURNEY_LABEL_WIDTH}}{NEXT_ACTION.get(state['currentStage'], '')}", "body")], color=color),
    ])


def cmd_journey(args: list[str]) -> int:
    """Print the deterministic six-stage journey signpost in human or JSON mode."""
    if args not in ([], ["--json"]):
        print("Usage: sf-context discovery journey [--json]", file=sys.stderr)
        return 2
    state = _journey_state()
    if args == ["--json"]:
        print(json.dumps(state, ensure_ascii=False, separators=(",", ":")))
        return 0
    # This stdout is model-reproduced, so it must be plain — strip the current-stage
    # green accent (it rides the systemMessage surfaces, not here).
    print(_ANSI_RE.sub("", _render_journey_rail(state)))
    return 0


# Orientation-question detection for the paint hook. The on-demand journey rail
# reaches the user by the MODEL reproducing it as text — a pipe that cannot carry
# terminal color (a markdown-fenced reply strips/garbles ANSI). So when the user
# asks an orientation question, a UserPromptSubmit hook paints the SAME rail on
# the systemMessage channel, the one pipe Claude Code renders directly (in color,
# like the banner and wayfinder), and tells the model the rail is already shown so
# it adds only its read. Precision-biased on purpose: a miss just falls back to
# the model routing to the journey command and reproducing the plain rail (today's
# behavior), and an over-fire paints an unasked-for rail. Locator questions
# ("where is the X") are ordinary tasks and are explicitly excluded.
# First-person-anchored: the honest orientation signal is the user asking about
# THEIR OWN position ("where am I", "what stage am I at"), not a bare domain noun.
# "journey" (Marketing Cloud Journey Builder) and "stage" (Opportunity Stage) are
# first-class Salesforce terms, so the bare words must NOT paint the rail — only
# the explicit `discovery journey`/`where` command form and the first-person
# questions do. A missed phrasing just falls back to the model routing + plain rail.
_ORIENTATION_TRIGGER = re.compile(
    r"(?ix)(?:"
    r"where\s+am\s+i|where\s+are\s+we\b|"
    r"wh(?:at|ich)\s+stage\s+am\s+i|what\s+phase\s+am\s+i|"
    r"am\s+i\s+(?:set\s*up|ready|good\s+to\s+go)|"
    r"where\s+(?:do|should|to)\s+i?\s*(?:start|begin)|"
    r"how\s+do\s+i\s+get\s+(?:started|going)|"
    r"what\s+can\s+i\s+do\s+here|"
    # "what next" / "whats next" / "what's next" / "what is next" / "what should i do next"
    r"what(?:'?s|\s+is|\s+should\s+i\s+do)?\s+next|"
    r"(?:^|[\s/])(?:salesforce-development:)?discovery\s+(?:journey|where)\b"
    r")"
)
_LOCATOR_EXCLUSION = re.compile(
    r"(?ix)where(?:'s|\s+(?:is|are))\s+the\b|"
    r"\bwhich\s+(?:file|dir|directory|folder|class|method|function|line)\b"
)


def _is_orientation_question(prompt: str) -> bool:
    """True when the prompt is a where-am-I / what-stage question the rail answers.

    Locator questions are matched first and always lose — "where is the Account
    class?" is a Grep task, never the journey rail."""
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 2000:
        return False
    if _LOCATOR_EXCLUSION.search(prompt):
        return False
    return bool(_ORIENTATION_TRIGGER.search(prompt))


# A prompt asking for the project/org/environment STATUS by name — the richest ask,
# painting the org + project bands AND the rail (positional questions paint only the
# rail). Precision-biased like the orientation trigger: a miss just means the model
# answers in prose. Task-scoped status ("git status", "deploy status") is excluded —
# that is ordinary work, not the plugin's position view.
_STATUS_EXCLUSION = re.compile(
    r"(?ix)\b(?:git|deploy(?:ment)?|build|job|test|ci|pipeline|pr|pull\s+request|run|commit)\s+status\b|"
    r"\bstatus\s+of\s+(?:the\s+|my\s+|this\s+)?(?:deploy(?:ment)?|build|job|test|run|pr|pull\s+request|pipeline|commit)\b"
)
_STATUS_TRIGGER = re.compile(
    r"(?ix)(?:"
    r"^\s*status\b[\s?!.]*$|"                                        # bare "status"
    r"\bstatus\s+(?:check|report)\b|"
    r"\b(?:project|org|environment|env|setup|session)\s+status\b|"
    r"\bstatus\s+of\s+(?:my|the|this|our)\s+(?:project|org|environment|setup|session|work)\b|"
    r"\bwhat(?:'?s|\s+is)\s+(?:the|my|our)\s+(?:current\s+)?status\b(?!\s+of\b)|"
    r"\b(?:show|display|give)\s+(?:me\s+)?(?:the\s+|my\s+)?(?:current\s+)?status\b|"
    r"\bwhere\s+do\s+(?:things|we|i)\s+stand\b"
    r")"
)


def _is_status_question(prompt: str) -> bool:
    """True when the prompt asks for the project/org status by name — paints the
    bands + rail. Locator and task-scoped ("git/deploy status") prompts lose first."""
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 2000:
        return False
    if _LOCATOR_EXCLUSION.search(prompt) or _STATUS_EXCLUSION.search(prompt):
        return False
    return bool(_STATUS_TRIGGER.search(prompt))


def _orientation_paint_note(state: dict) -> str:
    """The model-facing note that rides `additionalContext` when the hook paints
    the rail: enough facts for the model's read, plus the do-not-reproduce rule.

    Deliberately does NOT hand the model the rail ASCII to parrot — just the stage,
    position and next action as prose — so the visible rail comes only from the
    colored systemMessage."""
    stages = state.get("stages") or []
    stage = state.get("currentStage", "?")
    index = next((i for i, s in enumerate(stages) if s.get("status") == "current"), 0)
    nxt = NEXT_ACTION.get(stage, "").strip()
    return (
        "The salesforce-development position rail has just been displayed to the user, in color, "
        f"on the visible channel. Current stage: {stage} ({index + 1} of {len(stages) or 6}). "
        f"Likely next: {nxt} Deploy and Observe stay unknown without durable verified history.\n"
        "Do NOT reproduce, redraw, or restate the rail, and do not run the journey command — it is "
        "already shown. Add only your own short read: what this stage means for what the user is "
        "working on in THIS project, the concrete next step, and what stays unknown."
    )


def _status_paint_note(state: dict) -> str:
    """Model-facing note when the on-demand status surface paints: the connected-org
    band, the project band, and the rail are already on the visible channel, so the
    model adds only a short read and never reprints them or re-runs status/journey."""
    stages = state.get("stages") or []
    stage = state.get("currentStage", "?")
    index = next((i for i, s in enumerate(stages) if s.get("status") == "current"), 0)
    nxt = NEXT_ACTION.get(stage, "").strip()
    return (
        "The salesforce-development status has just been displayed to the user, in color, on the "
        "visible channel — the connected-org band, the project inventory band, and the position rail. "
        f"Current stage: {stage} ({index + 1} of {len(stages) or 6}). Likely next: {nxt} "
        "Do NOT reproduce, redraw, or restate any of it, and do not run the status or journey commands "
        "— it is already shown. Add only your own short read: what this state means for what the user "
        "is working on, and the concrete next step."
    )


def _render_getting_started_welcome(state: dict, *, color: bool = False) -> str:
    """The once-per-scenario welcome: the HEADLESS 360 identity, the current
    signpost, and the next step. Unstyled by default — small enough for the
    UserPromptSubmit output cap, and it degrades by construction with no color
    to mangle.

    State-adaptive tail: with no project it offers the onboarding CTAs (create a
    project / connect an org); inside a project it shows the concrete `likely next`
    action, so it never tells someone already in a project to "create a project"."""
    facts = _banner_provenance()
    lines = [BANNER, f"{BANNER_WORDMARK}   ·   v{facts['version']}", BANNER_TAGLINE]
    if facts["capabilities"] is not None:
        summary = f"{facts['capabilities']} capabilities · {facts['addable']} addable"
        installed = _installed_skill_count()
        if installed is not None:
            summary += f" · {installed} installed"
        lines.append(f"{summary} · release {facts['releaseRef']}")
    lines += [""] + _render_signpost(state, color=color)
    if state.get("currentStage") == "Welcome":
        lines += [
            "",
            "Get started — just say what you want:",
            '  •  "create a Salesforce project"    scaffold a new DX project',
            '  •  "connect an org"                 I\'ll list your authed orgs to pick from',
        ]
    else:
        nxt = NEXT_ACTION.get(state.get("currentStage"), "").strip()
        lines += ["", f"{'likely next':<{_JOURNEY_LABEL_WIDTH}}{nxt}"]
    return "\n".join(lines)


# The HEADLESS logo shows ONCE per session, total. The marker is keyed on the
# session id and lives in the OS temp dir — deliberately NOT cwd-relative, so it
# survives the `/cd` from the folder where you started into a project you just
# scaffolded (those are different directories; a cwd-relative flag would forget
# and re-show the logo). Whichever surface paints the logo first — SessionStart,
# the outside-a-project welcome, or the first in-project orientation — records it,
# and the rest show just the rail. A new session (new id) greets once again.
_WELCOME_MARKER_DIR = Path(tempfile.gettempdir())


def _session_marker(session_id: str, kind: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_-]", "", session_id)[:80]
    return _WELCOME_MARKER_DIR / f"sf-hl360-{kind}-{safe}"


def _welcomed_this_session(session_id: str) -> bool:
    return bool(session_id) and _session_marker(session_id, "welcome").exists()


def _record_welcomed(session_id: str) -> None:
    if not session_id:
        return
    try:
        _session_marker(session_id, "welcome").touch()
    except OSError:
        pass


# A separate per-session marker for "has the first-in-project orientation already
# fired" — so entering a project surfaces the position rail exactly once, on the
# first message that isn't itself an orientation question or an org-connect (which
# the wayfinder owns).
def _entered_this_session(session_id: str) -> bool:
    return bool(session_id) and _session_marker(session_id, "entered").exists()


def _record_entered(session_id: str) -> None:
    if not session_id:
        return
    try:
        _session_marker(session_id, "entered").touch()
    except OSError:
        pass


_CONNECT_INTENT = re.compile(
    r"(?ix)\b(?:connect|log\s?in|sign\s?in|authenticate|auth\b|"
    r"set\s+(?:the\s+)?(?:default\s+)?(?:target[-\s]?)?org|set\s+default|"
    r"(?:choose|pick|select|use)\s+(?:an?\s+|my\s+|the\s+)?org)\b"
)


def _is_connect_intent(prompt: str) -> bool:
    """A prompt about connecting/choosing an org — the wayfinder owns that moment,
    so the first-in-project rail steps aside to avoid a double paint."""
    return isinstance(prompt, str) and bool(_CONNECT_INTENT.search(prompt))


def _is_getting_started_intent(prompt: str) -> bool:
    """Side A (outside a project): the conservative trigger. The plugin is global,
    so in an arbitrary directory we surface the welcome only when the prompt names
    Salesforce — an explicit signal of intent — and never on a locator question."""
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 2000:
        return False
    if _LOCATOR_EXCLUSION.search(prompt):
        return False
    return "salesforce" in prompt.lower()


def _welcome_note(state: dict) -> str:
    """Model-facing note when the getting-started welcome paints on the visible
    channel — orients the model and keeps its reply tight, without reprinting the
    welcome or racing ahead of the flow."""
    stage = state.get("currentStage", "?")
    nxt = NEXT_ACTION.get(stage, "").strip()
    base = (
        "The salesforce-development getting-started welcome has just been displayed to the user on "
        "the visible channel (the HEADLESS 360 identity, their position, and what to say next). Do "
        "NOT reproduce or redraw the welcome — it is already shown. Keep your reply to one or two "
        "sentences. Do NOT enumerate a list of things they could build, and do NOT launch a "
        "multiple-choice menu — the welcome already shows the next actions; let them answer in their "
        "own words."
    )
    if stage == "Welcome":
        return base + (
            " There is no Salesforce project here yet, so the single next step is to create one: "
            'invite them to say "create a Salesforce project" (connecting an org comes after). Do '
            "NOT ask what they want to build yet — scoping happens once a project exists."
        )
    return base + f" Current stage: {stage}. Likely next: {nxt} Point them to that one next step."


def _entered_note(state: dict) -> str:
    """Model-facing note when the position rail paints as *ambient* orientation on
    the user's first in-project message — the user asked for something, so the model
    should act on it, not orient. The rail is already on screen."""
    return (
        "The salesforce-development position rail has been shown to the user as ambient orientation "
        "(they have just moved into this project). It is already displayed — do NOT reproduce, "
        "redraw, or comment on it. Proceed with the user's actual request."
    )


def cmd_orientation_paint() -> int:
    """UserPromptSubmit hook, two-sided.

    OUTSIDE a Salesforce project (Side A) the plugin can't presume — it's global —
    so only a prompt that names Salesforce surfaces the getting-started welcome.
    INSIDE a project (Side B) the context already proves intent, so any orientation
    question paints. The welcome greets once per session (Side A or B); after that,
    orientation questions paint just the position rail.

    All painting rides the user-visible systemMessage channel; the model gets a
    plain note so it adds only its read and never reprints the surface.

    Fail open: any error → silent {"continue": true}. Silent on every prompt that
    is neither an in-project orientation question nor an out-of-project Salesforce
    mention, so ordinary turns are untouched."""
    try:
        payload = _read_hook_payload()
        prompt = payload.get("prompt", "")
        session_id = payload.get("session_id") or payload.get("sessionId") or ""

        # Leading blank separates the surface from Claude Code's hook-message wrapper.
        if Path("sfdx-project.json").exists():
            # The HEADLESS logo shows once per session — only when we can dedupe (a
            # session id is present) and it hasn't been shown yet. This flag and the
            # intent regexes below are all cheap; the org/filesystem work is deferred
            # into the branches that actually paint, so an ordinary turn (the common
            # case, which falls through to silent) pays nothing. Previously
            # `_journey_state` ran here on EVERY prompt and was then often discarded.
            show_logo = bool(session_id) and not _welcomed_this_session(session_id)
            color = _banner_color_enabled()
            root = Path.cwd().resolve()

            # A status question by name is the richest ask: it paints the connected-
            # org and project bands AND the rail. The org is resolved once, shared
            # by the band and the rail (no double query).
            if _is_status_question(prompt):
                _record_entered(session_id)
                if show_logo:
                    _record_welcomed(session_id)
                state, org = _resolve_position_and_org(root)
                # Live MCP health here too, so a re-asked "where am I?" reflects
                # real reachability rather than a stale sidecar (matches /status).
                mcp_active_org = (org.get("alias"), org.get("username")) if org else None
                surface = render_status_surface(
                    state, org, project_meta(), project_stats(), git_status_line(),
                    _live_mcp_summary(active_org=mcp_active_org),
                    color=color, logo=show_logo,
                )
                emit("UserPromptSubmit", _status_paint_note(state), system_message=surface)
                return 0

            # A positional orientation question paints just the rail — the logo on
            # the first surface of the session, the rail thereafter.
            if _is_orientation_question(prompt):
                _record_entered(session_id)
                state = _journey_state()
                if show_logo:
                    _record_welcomed(session_id)
                    emit("UserPromptSubmit", _welcome_note(state),
                         system_message="\n" + _render_getting_started_welcome(state))
                else:
                    emit("UserPromptSubmit", _orientation_paint_note(state),
                         system_message="\n" + _render_journey_rail(state, color=color))
                return 0

            # An org-connect: the wayfinder owns that moment. Mark entered so we
            # don't also nudge afterward, and stay silent here.
            if _is_connect_intent(prompt):
                _record_entered(session_id)
                print(json.dumps({"continue": True}))
                return 0

            # First non-orientation, non-connect message after entering the project:
            # surface the rail once as ambient orientation. Needs a session id to
            # dedupe — without one, stay silent (never nudge every turn).
            if not session_id or _entered_this_session(session_id):
                print(json.dumps({"continue": True}))
                return 0
            _record_entered(session_id)
            state = _journey_state()
            if show_logo:
                _record_welcomed(session_id)
                emit("UserPromptSubmit", _entered_note(state),
                     system_message="\n" + _render_getting_started_welcome(state))
            else:
                emit("UserPromptSubmit", _entered_note(state),
                     system_message="\n" + _render_journey_rail(state, color=color))
            return 0

        # Side A — outside a project: only a Salesforce mention surfaces the
        # welcome, and only once per scenario (then ordinary turns are untouched).
        if not _is_getting_started_intent(prompt) or _welcomed_this_session(session_id):
            print(json.dumps({"continue": True}))
            return 0
        state = _journey_state()
        _record_welcomed(session_id)
        emit("UserPromptSubmit", _welcome_note(state),
             system_message="\n" + _render_getting_started_welcome(state))
        return 0
    except Exception:
        print(json.dumps({"continue": True}))
        return 0


_SKILL_NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def cmd_resolution_trace() -> int:
    """PostToolUse Skill hook: render one safe line from this invocation only."""
    payload = _read_hook_payload()
    tool_input = payload.get("tool_input") or payload.get("toolInput") or {}
    if not isinstance(tool_input, dict):
        print(json.dumps({"continue": True}))
        return 0
    skill = tool_input.get("skill") or tool_input.get("skill_name") or tool_input.get("name") or ""
    if not isinstance(skill, str):
        skill = ""
    bare = skill.rsplit(":", 1)[-1]
    if len(bare) > 64 or not _SKILL_NAME_PATTERN.fullmatch(bare):
        print(json.dumps({"continue": True}))
        return 0
    # The ⚙ glyph and "resolution:" framing are the plugin talking, so they
    # ride the brand-blue link voice; the resolution ladder is secondary (muted).
    # This is the color-safe systemMessage channel (Claude Code renders it
    # directly); message="" means no additionalContext, so no ANSI reaches the
    # model. strip_ansi(line) equals the plain form, and NO_COLOR forces plain.
    #
    # Clip the skill name so the line holds ≤80 columns: the fixed framing
    # ("⚙ " + " · resolution: " + "Skill → CLI → API [Skill]") is 42 columns, and
    # `bare` is only validated to ≤64 chars, so a real 54-char skill would
    # otherwise render at 96. 42 + 38 = 80.
    line = _paint_line(
        [(f"⚙ {_clip(bare, 38)} · resolution: ", "link"),
         ("Skill → CLI → API [Skill]", "muted")],
        color=_banner_color_enabled(),
    )
    emit("PostToolUse", "", system_message=line)
    return 0


def cmd_features(args: list[str]) -> int:
    """Load and run org-feature detection only for the explicit on-demand mode."""
    try:
        from feature_detection import run_features
    except ImportError:
        # Supports importlib-based unit tests where the scripts directory is not
        # automatically placed on sys.path.
        import importlib.util
        module_path = Path(__file__).resolve().parent / "feature_detection.py"
        spec = importlib.util.spec_from_file_location("sf_feature_detection", module_path)
        if spec is None or spec.loader is None:
            print("Feature detection error: runtime is unavailable", file=sys.stderr)
            return 2
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        run_features = module.run_features
    return run_features(
        args,
        plugin_root=Path(__file__).resolve().parent.parent,
        runner=run_result,
    )


def cmd_discovery(args: list[str]) -> int:
    """Dispatch public offline catalog/journey, on-demand features, or gated internal preview."""
    if args and args[0] == "features":
        return cmd_features(args[1:])
    if args and args[0] in ("journey", "where"):
        return cmd_journey(args[1:])
    try:
        from discovery_catalog import run_discovery
    except ImportError:
        # Supports importlib-based unit tests where the scripts directory is not
        # automatically placed on sys.path.
        import importlib.util
        module_path = Path(__file__).resolve().parent / "discovery_catalog.py"
        spec = importlib.util.spec_from_file_location("sf_discovery_catalog", module_path)
        if spec is None or spec.loader is None:
            print("Discovery error: catalog runtime is unavailable", file=sys.stderr)
            return 2
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        run_discovery = module.run_discovery
    return run_discovery(args, plugin_root=Path(__file__).resolve().parent.parent)


def _force_utf8_stdio() -> None:
    """Force UTF-8 on stdout/stderr.

    Windows consoles default to a legacy code page (e.g. cp1252) that cannot
    encode the box-drawing / status glyphs the status commands print, so a plain
    `print()` of the org/project box raises UnicodeEncodeError on native Windows
    (observed during Windows QE of /salesforce-development:org). Reconfiguring the streams to
    UTF-8 at startup fixes the human-readable output without a per-invocation
    `PYTHONIOENCODING=utf-8` workaround. It is a no-op on macOS/Linux (already
    UTF-8) and on any stream without `reconfigure()` (e.g. a StringIO under test).
    Hook JSON is unaffected — `json.dumps` is ASCII-escaped by default."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8")
            except (ValueError, OSError):
                pass


def main() -> int:
    _force_utf8_stdio()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "detect"
    if cmd == "detect":
        return cmd_detect()
    if cmd == "verify-org":
        return cmd_verify_org()
    if cmd == "check-tools":
        return cmd_check_tools()
    if cmd == "discovery":
        return cmd_discovery(sys.argv[2:])
    if cmd == "post-deploy":
        return cmd_post_deploy()
    if cmd == "post-deploy-failure":
        return cmd_post_deploy_failure()
    if cmd == "skills-first-advisory":
        return cmd_skills_first_advisory()
    if cmd == "resolution-trace":
        return cmd_resolution_trace()
    if cmd == "record-skill-dispatch":
        return cmd_record_skill_dispatch()
    if cmd == "reset-dispatch-turn":
        return cmd_reset_dispatch_turn()
    if cmd == "feedback-nudge":
        return cmd_feedback_nudge()
    if cmd == "record-feedback-decision":
        return cmd_record_feedback_decision()
    if cmd == "record-update-decision":
        return cmd_record_update_decision()
    if cmd == "status":
        return cmd_status()
    if cmd == "status-org":
        return cmd_status_org()
    if cmd == "status-project":
        return cmd_status_project()
    if cmd == "wayfinder":
        return cmd_wayfinder()
    if cmd == "orientation-rail":
        return cmd_orientation_paint()
    print(f"Unknown command: {cmd}", file=sys.stderr)
    print("Usage: sf-context [detect|discovery|verify-org|check-tools|post-deploy|post-deploy-failure|skills-first-advisory|resolution-trace|record-skill-dispatch|reset-dispatch-turn|feedback-nudge|record-feedback-decision|record-update-decision|status|status-org|status-project|wayfinder|orientation-rail]", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
