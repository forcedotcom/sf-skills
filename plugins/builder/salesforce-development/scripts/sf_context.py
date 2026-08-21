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
    record-update-decision  Write legacy per-version SF CLI update state (compatibility command)
    wayfinder    Re-orient after an org-connect (PostToolUse hook on sf org login / config set target-org).
    prompt-dispatch  Establish prompt state and route UserPromptSubmit in-process.
    status, status-org, status-project  On-demand project/org state (/salesforce-development:status etc.).
    (Also internal advisory/state hooks: skills-first-advisory, record-skill-dispatch,
     feedback-nudge, record-feedback-decision — see main() for the full dispatch table.)

All commands emit a single JSON object on stdout matching Claude Code's hook output spec.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unicodedata
import urllib.error
import urllib.request
from collections import namedtuple
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
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
# The cross-platform command-building primitives (executable resolution, the
# Windows batch-shim invocation, and the cmd.exe metacharacter refusal sets) now
# live in the shared sf_shim module, imported by BOTH sf_context and sf_telemetry so
# there is ONE definition that cannot drift. Loaded robustly: a bare import works in
# production (scripts/ is sys.path[0] when the wrapper runs), and the by-path
# fallback covers importlib-based unit tests (which load this file by path without
# scripts/ on sys.path) and post-chdir use.
def _load_sf_shim():
    try:
        import sf_shim as _m  # fast path (scripts/ importable)
        return _m
    except Exception:
        import importlib.util as _ilu
        _p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sf_shim.py")
        _spec = _ilu.spec_from_file_location("sf_shim", _p)
        _m = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_m)
        return _m


_shim = _load_sf_shim()

# The shim-wrapping logic + metachar refusal sets are single-sourced in sf_shim;
# resolution (NAME -> path) stays LOCAL so this module's resolve_executable mock in
# the test suite keeps working. Re-export the shared data/predicates under the
# existing names for in-module callers.
_WINDOWS_SHIM_SUFFIXES = _shim._WINDOWS_SHIM_SUFFIXES
_CMD_ARG_METACHARACTERS = _shim._CMD_ARG_METACHARACTERS
_CMD_PATH_METACHARACTERS = _shim._CMD_PATH_METACHARACTERS


def _contains_any(value: str, chars) -> bool:
    return _shim._contains_any(value, chars)


def _is_windows_shim(path: str) -> bool:
    """True when a resolved path is a Windows batch shim needing a cmd wrapper."""
    return _shim.is_windows_shim(path)


def _has_cmd_metacharacters(value: str) -> bool:
    """Back-compat helper (arg set). Prefer _contains_any with an explicit set."""
    return _shim._contains_any(value, _CMD_ARG_METACHARACTERS)


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


def build_command(name: str, args: Optional[list] = None) -> Optional[list]:
    """Build the argv to spawn `name` + `args` cross-platform, or None if `name`
    cannot be resolved on PATH (or, on the shim path, an arg is unsafe). Resolves
    `name` locally (PATHEXT-aware), then delegates the shim-wrapping + metacharacter
    refusal to the shared sf_shim.build_argv."""
    resolved = resolve_executable(name)
    if resolved is None:
        return None
    return _shim.build_argv(resolved, args)


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
    lines = ["Diagnostic:"]

    def append_value(prefix: str, value: object) -> None:
        safe = _sanitize_dynamic_text(value)
        width = max(1, 80 - _terminal_cell_width(prefix))
        chunks = _wrap_cells(safe, width) or [""]
        lines.append(prefix + chunks[0])
        lines.extend(" " * _terminal_cell_width(prefix) + chunk for chunk in chunks[1:])

    append_value("  platform: ", ctx.get("platform", ""))
    append_value("  shell:    ", ctx.get("shell", "") or "(unset)")
    append_value("  cwd:      ", ctx.get("cwd", ""))
    append_value("  plugin:   ", ctx.get("pluginRoot", ""))
    lines.append("  resolved executables:")
    for name, path in (ctx.get("resolvedExecutables") or {}).items():
        append_value(f"    {_sanitize_dynamic_text(name)}: ", path)
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
    session_title: Optional[str] = None,
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
        if session_title:
            output["sessionTitle"] = session_title
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


# The SessionStart inventory is deliberately a single bounded walk. These roots are
# dependency/cache/VCS trees, not project metadata inventory; prune them before
# descent so even a very large vendored tree costs one directory entry, not one stat
# per file. The dot-directories are the same exclusions used by the journey artifact
# walks, with vendor added for repositories that check in third-party source.
_PROJECT_STATS_EXCLUDED_DIRS = {
    ".claude", ".git", ".sf", ".sfdx", "node_modules", "vendor",
}
_PROJECT_STATS_FILE_CAP = 10_000
_PROJECT_STATS_ENTRY_CAP = 12_000
_PROJECT_STATS_DEPTH_CAP = 32
_PROJECT_DESCRIPTOR_MAX_BYTES = 64 * 1024


def _declared_package_paths(descriptor: dict) -> list:
    """Return structurally valid package-directory path strings."""
    entries = descriptor.get("packageDirectories")
    if not isinstance(entries, list):
        return []
    paths = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        path = entry.get("path")
        if isinstance(path, str) and path.strip():
            paths.append(path)
    return paths


def _validated_package_roots(project_root: Path, descriptor: dict) -> list:
    """Resolve contained relative package roots and remove exact duplicates."""
    candidates = set()
    for relative in _declared_package_paths(descriptor):
        path = Path(relative)
        if path.is_absolute():
            continue
        try:
            resolved = (project_root / path).resolve()
            resolved.relative_to(project_root)
            if not resolved.is_dir():
                continue
        except (OSError, RuntimeError, ValueError):
            continue
        candidates.add(resolved)

    return sorted(candidates, key=lambda path: (len(path.parts), str(path)))


def project_stats() -> dict:
    """Count the existing project inventory in one pruned, file-capped local walk.

    A cap or filesystem error returns the counts accumulated so far. SessionStart is
    informational: bounded partial facts are preferable to blocking startup, and the
    unchanged result shape keeps every renderer fail-soft.
    """
    counts = {
        "apex_src": 0,
        "apex_test": 0,
        "triggers": 0,
        "lwc": 0,
        "aura": 0,
        "objects": 0,
        "permsets": 0,
        "flows": 0,
    }
    examined = 0
    entries_seen = 0
    try:
        project_root = Path.cwd().resolve()
        descriptor = _read_project_descriptor(project_root)
        package_roots = _validated_package_roots(project_root, descriptor)
        if not package_roots:
            return counts
        accepted_roots = frozenset(package_roots)
        required_package_paths = set()
        for root in package_roots:
            required_cursor = root
            while True:
                required_package_paths.add(required_cursor)
                if required_cursor == project_root:
                    break
                required_cursor = required_cursor.parent

        for current, dirs, files in os.walk(
            ".", topdown=True, onerror=lambda _error: None, followlinks=False
        ):
            current_path = Path(current)
            try:
                resolved_current = current_path.resolve()
                depth = len(resolved_current.relative_to(project_root).parts)
            except (OSError, RuntimeError, ValueError):
                return counts
            if depth > _PROJECT_STATS_DEPTH_CAP:
                dirs[:] = []
                continue

            in_package = False
            package_cursor = resolved_current
            excluded_ancestor = False
            while True:
                if package_cursor in accepted_roots and not excluded_ancestor:
                    in_package = True
                    break
                if package_cursor == project_root:
                    break
                if package_cursor.name in _PROJECT_STATS_EXCLUDED_DIRS:
                    excluded_ancestor = True
                package_cursor = package_cursor.parent

            kept_dirs = []
            for name in dirs:
                child = resolved_current / name
                required_for_package = child in required_package_paths
                if required_for_package or (
                    in_package and name not in _PROJECT_STATS_EXCLUDED_DIRS
                ):
                    kept_dirs.append(name)
            dirs[:] = sorted(kept_dirs)
            files = sorted(files) if in_package else []
            entries_seen += len(dirs) + len(files)
            if entries_seen > _PROJECT_STATS_ENTRY_CAP:
                return counts
            in_lwc = "lwc" in current_path.parts
            for filename in files:
                examined += 1
                if examined > _PROJECT_STATS_FILE_CAP:
                    return counts
                if filename.endswith(".cls"):
                    if filename.endswith("Test.cls") or filename.endswith("_Test.cls"):
                        counts["apex_test"] += 1
                    else:
                        counts["apex_src"] += 1
                elif filename.endswith(".trigger"):
                    counts["triggers"] += 1
                elif in_lwc and filename.endswith(".js-meta.xml"):
                    counts["lwc"] += 1
                elif filename.endswith((".cmp-meta.xml", ".app-meta.xml", ".evt-meta.xml")):
                    counts["aura"] += 1
                elif filename.endswith(".object-meta.xml"):
                    counts["objects"] += 1
                elif filename.endswith(".permissionset-meta.xml"):
                    counts["permsets"] += 1
                elif filename.endswith(".flow-meta.xml"):
                    counts["flows"] += 1
    except OSError:
        pass
    return counts


def git_status_line() -> str:
    """Return a one-line git summary, or empty string if not a git repo."""
    inside = run(["git", "rev-parse", "--is-inside-work-tree"], timeout=2).strip()
    if inside != "true":
        return ""
    porcelain = run(["git", "status", "--porcelain"], timeout=2)
    changed = sum(1 for line in porcelain.splitlines() if line.strip())
    return f"{changed} file(s) changed" if changed > 0 else "working tree clean"


def _read_project_descriptor(project_root: Optional[Path] = None) -> dict:
    """Read one bounded real project descriptor, failing soft to an empty object."""
    path = (project_root or Path.cwd()) / "sfdx-project.json"
    try:
        metadata = path.lstat()
        if (not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1
                or metadata.st_size > _PROJECT_DESCRIPTOR_MAX_BYTES):
            return {}
        with path.open("rb") as stream:
            raw = stream.read(_PROJECT_DESCRIPTOR_MAX_BYTES + 1)
        if len(raw) > _PROJECT_DESCRIPTOR_MAX_BYTES:
            return {}
        data = json.loads(raw.decode("utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        return {}


def project_meta() -> dict:
    """Read sfdx-project.json fields needed for the project box."""
    data = _read_project_descriptor()
    if not data:
        return {"name": "Project", "source_api": "unknown", "package_dirs": "force-app"}
    name = data.get("name") or "Project"
    source_api = data.get("sourceApiVersion") or "unknown"
    package_dirs = ", ".join(_declared_package_paths(data)) or "force-app"
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
ORIENTATION_DIRECTIVE = """Orientation routing (narrow):
For the user's workflow position/progress — “where am I?”, “what stage am I at?”,
“what should I do next?”, “catch me up”, “how far along am I?”, or “where did I
leave off?” — dispatch salesforce-development:discovery with `where` (`journey`).
Answer in two parts: 1. if the rail was not already displayed, reproduce it
unmodified in your reply; 2. add a short relevance read, next step, and unknowns.
If context says it already displayed the rail, skip this step: never restate,
reproduce, redraw, or re-run it. “Where is the Account class?” and other
code/metadata locators are ordinary tasks; never answer those with the journey rail.
"""


SKILLS_FIRST_COMPACT = """Skills first (required): match Salesforce work to an installed owning skill and
dispatch it before writing code, metadata, or raw commands. Resolution hierarchy:
1. installed Skill; 2. SF CLI with `--json` only when no skill covers it;
3. direct API only when neither skill nor CLI fits.
"""


def _session_model_context(
    *, project: Optional[dict], state: dict, configured_org: str = "",
    displayed_org: Optional[str] = None, project_present: bool,
) -> str:
    """Return compact, sanitized semantic SessionStart facts, never visible chrome."""
    identity = _banner_provenance()
    capability = identity.get("capabilities")
    addable = identity.get("addable")
    release = identity.get("releaseRef") or "unknown"
    catalog = f"capabilities={capability if capability is not None else 'unknown'}"
    catalog += f"; addable={addable if addable is not None else 'unknown'}"
    catalog += f"; release={_clip(str(release), 24)}"

    stages = state.get("stages") or []
    current = _clip(str(state.get("currentStage") or "unknown"), 32)
    current_is_reached = bool(stages) and all(s.get("status") != "future" for s in stages)
    reached = [str(s.get("name") or "") for s in stages
               if s.get("status") == "complete"
               or (s.get("status") == "current" and current_is_reached)]
    no_evidence = [str(s.get("name") or "") for s in stages
                   if s.get("status") == "future"
                   or (s.get("status") == "current" and not current_is_reached)]
    state_context = state.get("context") or {}
    org_state = _clip(str(state_context.get("orgStatus") or "unknown"), 24)
    shown_value = displayed_org if displayed_org is not None else state_context.get("orgAlias")
    shown = shown_value or "none"
    configured = configured_org or (
        shown if org_state in ("reachable", "configured", "configured-unprobed") else "none"
    )

    lines = [
        f"plugin: salesforce-development v{_clip(str(identity.get('version') or '?'), 24)}",
        f"catalog: {catalog}",
    ]
    if project_present:
        meta = project or {}
        lines.append(
            "project: present; "
            f"name={_clip(str(meta.get('name') or state_context.get('project') or 'Project'), 24)}; "
            f"sourceApi={_clip(str(meta.get('source_api') or 'unknown'), 16)}; "
            f"packages={_clip(str(meta.get('package_dirs') or 'force-app'), 24)}"
        )
    else:
        lines.append("project: absent (no sfdx-project.json)")
    lines += [
        f"org: configured={_clip(str(configured), 24)}; displayed={_clip(str(shown), 24)}; state={org_state}",
        f"current stage: {current}",
        "reached: " + (", ".join(_clip(name, 24) for name in reached) or "none"),
        "no evidence: " + (", ".join(_clip(name, 24) for name in no_evidence) or "none"),
        f"next action: {_clip(str(NEXT_ACTION.get(state.get('currentStage'), '')), 88)}",
        f"discovery: {DISCOVERY_POINTER}",
        SKILLS_FIRST_COMPACT.strip(),
        ORIENTATION_DIRECTIVE.strip(),
    ]
    return "\n".join(lines)


# A LEAN re-injection of the skills-first principle, used after context
# compaction (#406). SKILLS_FIRST_DIRECTIVE is injected once at startup; this
# re-states only the durable behavioral rule (skills → CLI → API) after a
# compaction reclaims context, keeping skills-first DURABLE across the long,
# complex sessions where skills matter most rather than evaporating the moment
# context is summarized.
SKILLS_FIRST_REINJECT = """salesforce-development durable context after compaction:
The installed Salesforce skill catalog remains active.

Skills first (required): match Salesforce work to an installed owning skill and
explicitly dispatch it before writing code, metadata, or raw commands.
Resolution hierarchy: 1. installed Skill; 2. SF CLI with `--json` only when no
skill covers the operation; 3. direct API only when neither skill nor CLI fits.

Ask “what can I do here?” or run /salesforce-development:discovery.

""" + ORIENTATION_DIRECTIVE


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

# Lockup + band color, fully theme-adaptive (owner direction 2026-08-04). Every hue is
# a 16-color ANSI palette index or an attribute, NOT truecolor: Claude Code maps palette
# SGR through its OWN active theme, so these track the host UI and re-tune light↔dark,
# where a fixed RGB would look identical on every theme and could wash out on a light
# background. The lockup art and wordmark flatten to one bright-blue; ok/warn/link take
# palette hues; the muted/secondary tone carries NO SGR at all — it rides Claude Code's
# systemMessage dimming and renders as the theme's own dimmed foreground (see
# _paint_muted and the "muted" band style). Same vocabulary the discovery overview uses
# (discovery_catalog._SGR_* / _muted), so every Tier-1 painted surface shares one theme.
#
# Two rules make this read correctly in Claude Code specifically:
#   1. Every colored (non-muted) run is prefixed with SGR 22 (normal intensity). Claude
#      Code renders a hook's systemMessage DIMMED by default, so the undim makes accents
#      read ABOVE the muted baseline; muted runs omit it, staying dimmed.
#   2. Color is emitted unless NO_COLOR is set, and is NEVER gated on isatty: the banner
#      is printed into a hook's JSON systemMessage, so stdout is always a pipe and Claude
#      Code does the terminal rendering. An isatty check would suppress color in exactly
#      the case we want it. Model-reproduced stdout paths (/status, /welcome, /discovery
#      journey) and the readiness banner pass color=False, so no ANSI reaches that pipe.
_SGR_RESET = "\x1b[0m"
_SGR_UNDIM = "\x1b[22m"
_SGR_BOLD = "\x1b[1m"
_SGR_GREEN = "\x1b[32m"
_SGR_YELLOW = "\x1b[33m"          # "amber"
_SGR_CYAN = "\x1b[36m"            # link tint
_SGR_BRIGHT_BLUE = "\x1b[94m"     # the flattened brand lockup + wordmark hue

# Segment style name -> the SGR sequence applied to the run (_paint_line resets after).
# "muted" maps to "" — emitted plain, so CC's systemMessage dimming renders it as the
# theme's dimmed foreground (the shared secondary gray). "body" is undimmed default fg
# (normal), "head" is bold, and ok/warn/link take palette hues. No truecolor anywhere,
# so the ANSI-strip regex still yields a plain form byte-identical to the colored one.
_BAND_STYLES = {
    "body": _SGR_UNDIM,
    "muted": "",
    "ok": _SGR_UNDIM + _SGR_GREEN,
    "warn": _SGR_UNDIM + _SGR_YELLOW,
    "head": _SGR_UNDIM + _SGR_BOLD,
    "link": _SGR_UNDIM + _SGR_CYAN,
}
# The rules align to the 64-column ANSI-Shadow lockup edge, giving the bands a
# clean seam to the art above them.
_BAND_WIDTH = 64


def _banner_color_enabled() -> bool:
    """Whether to paint the Tier-1 systemMessage surfaces (banner, bands, journey rail,
    welcome, wayfinder). ON by default now (owner direction 2026-08-04); honors
    NO_COLOR. The palette is fully theme-adaptive — 16-color + attributes, no truecolor
    — so these surfaces re-tune with Claude Code's active theme (see _BAND_STYLES).

    Model-reproduced stdout paths (/status, /welcome, /discovery journey) and the
    readiness banner pass color=False explicitly, so no ANSI reaches a pipe the model
    re-emits — this gate governs only the visible systemMessage paths.
    """
    return not os.environ.get("NO_COLOR")


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


def _paint_lockup(art: str) -> str:
    """Paint the lockup art one themeable hue — bright-blue, dim-cancelled per line.

    Flattened from the old per-column truecolor gradient (owner direction 2026-08-04):
    the hue is a 16-color palette index Claude Code maps through the active theme, so it
    re-tunes with light/dark instead of imposing one fixed RGB. Stripping ANSI returns
    the original art byte-for-byte, which is what the geometry goldens assert against.
    """
    return "\n".join(
        f"{_SGR_UNDIM}{_SGR_BRIGHT_BLUE}{line}{_SGR_RESET}" for line in art.splitlines()
    )


def _paint_wordmark(version: str) -> str:
    """Tint the wordmark: the lettered name bright-blue (matching the lockup), the
    separators and version muted (plain, so Claude Code's dimming renders them as the
    theme's dimmed foreground). The visible text is identical to the plain
    `{BANNER_WORDMARK}   ·   v{version}` form, so a screen reader and the
    ANSI-stripping goldens see the same string."""
    return (
        f"{_SGR_UNDIM}{_SGR_BRIGHT_BLUE}{_WORDMARK_SALESFORCE}{_SGR_RESET}"
        f"   ·   "
        f"{_SGR_UNDIM}{_SGR_BRIGHT_BLUE}{_WORDMARK_360}{_SGR_RESET}"
        f"   ·   v{version}"
    )


def _paint_muted(text: str) -> str:
    """A muted/secondary line: emitted plain, so Claude Code's systemMessage dimming
    renders it as the theme's own dimmed foreground (the shared secondary gray). Pure
    pass-through — the dimming is CC's, pulled from the active theme, nothing hard-coded.
    Mirrors discovery_catalog._muted so the banner and overview share one gray."""
    return text

_ARTIFACT_READ_ERRORS = (OSError, ValueError, TypeError, KeyError, IndexError)
# The lockup is contractually ≤80 columns, so the artifact strings and counts it
# interpolates are bounded here. A catalog with 100k capabilities is not a real
# artifact; treating one as unreadable is safer than wrapping the pinned visual.
_IDENTITY_LIMIT = 24
_COUNT_CEILING = 100000


_BIDI_CONTROLS = frozenset(
    {"\u061c", "\u200e", "\u200f", *map(chr, range(0x202A, 0x202F)),
     *map(chr, range(0x2066, 0x2070))}
)


def _ansi_sequence_end(value: str, start: int) -> int:
    """Return the end of an ANSI/ECMA-48 sequence beginning at ``start``.

    Unterminated control strings consume the remainder. Dynamic terminal text is
    never allowed to expose an OSC/DCS payload merely because its terminator was
    truncated.
    """
    size = len(value)
    introducer = value[start]
    pos = start + 1
    kind = value[pos] if introducer == "\x1b" and pos < size else introducer
    if introducer == "\x1b" and pos < size:
        pos += 1
    if kind in ("[", "\x9b"):  # CSI: parameters/intermediates, then final byte
        while pos < size:
            if "@" <= value[pos] <= "~":
                return pos + 1
            pos += 1
        return size
    if kind in ("]", "P", "X", "^", "_", "\x90", "\x98", "\x9d", "\x9e", "\x9f"):
        while pos < size:
            if value[pos] in ("\x07", "\x9c"):
                return pos + 1
            if value[pos] == "\x1b" and pos + 1 < size and value[pos + 1] == "\\":
                return pos + 2
            pos += 1
        return size
    # A two-byte ESC sequence, optionally with intermediate bytes. Restart at
    # the byte after ESC: `kind` itself is the final byte for ESC 7 / ESC c.
    pos = start + 1
    while pos < size and " " <= value[pos] <= "/":
        pos += 1
    return min(size, pos + 1)


def _sanitize_dynamic_text(value: object) -> str:
    """Return untrusted dynamic text safe for one terminal line.

    Removes complete or truncated ANSI ESC/CSI/OSC/control-string sequences and
    their payloads, all C0/C1 controls (including CR/LF/TAB), bidi controls and
    isolates, and Unicode line/paragraph separators. Safe Unicode is retained.
    Authored multiline copy is not routed through this boundary helper.
    """
    if not isinstance(value, str):
        value = str(value) if value is not None else ""
    out: list[str] = []
    pos = 0
    while pos < len(value):
        ch = value[pos]
        if ch == "\x1b" or ch in ("\x90", "\x98", "\x9b", "\x9d", "\x9e", "\x9f"):
            pos = _ansi_sequence_end(value, pos)
            continue
        codepoint = ord(ch)
        if ch in ("\t", "\n", "\r", "\u2028", "\u2029"):
            if out and out[-1] != " ":
                out.append(" ")
            pos += 1
            continue
        if (codepoint < 0x20 or 0x7F <= codepoint <= 0x9F
                or ch in _BIDI_CONTROLS):
            pos += 1
            continue
        out.append(ch)
        pos += 1
    return "".join(out)


def _is_cluster_extender(ch: str) -> bool:
    codepoint = ord(ch)
    return (
        unicodedata.combining(ch) != 0
        or unicodedata.category(ch) in ("Mn", "Me")
        or ch == "\u200d"
        or 0xFE00 <= codepoint <= 0xFE0F
        or 0xE0100 <= codepoint <= 0xE01EF
        or 0x1F3FB <= codepoint <= 0x1F3FF
    )


def _is_emoji_like(ch: str) -> bool:
    codepoint = ord(ch)
    return 0x1F000 <= codepoint <= 0x1FAFF


def _codepoint_cells(ch: str) -> int:
    if ch == "\u200d" or _is_cluster_extender(ch):
        return 0
    if unicodedata.east_asian_width(ch) in ("W", "F") or _is_emoji_like(ch):
        return 2
    return 1


def _grapheme_clusters(value: str):
    """Yield conservative display clusters using only :mod:`unicodedata`.

    This supported approximation keeps combining/variation/modifier tails, emoji
    ZWJ sequences, and regional-indicator pairs together. It intentionally makes
    no claim of perfect parity with every terminal's grapheme implementation.
    ANSI sequences are yielded atomically and have zero cells. Orphan extenders
    are dropped so clipping cannot create a dangling mark or joiner.
    """
    pos = 0
    while pos < len(value):
        ch = value[pos]
        if ch == "\x1b" or ch in ("\x90", "\x98", "\x9b", "\x9d", "\x9e", "\x9f"):
            end = _ansi_sequence_end(value, pos)
            yield value[pos:end], 0
            pos = end
            continue
        if _is_cluster_extender(ch):
            pos += 1
            continue
        cluster = ch
        width = _codepoint_cells(ch)
        pos += 1
        # A flag is one cluster/two cells, not two independent wide symbols.
        if 0x1F1E6 <= ord(ch) <= 0x1F1FF and pos < len(value) and 0x1F1E6 <= ord(value[pos]) <= 0x1F1FF:
            cluster += value[pos]
            pos += 1
        while pos < len(value):
            nxt = value[pos]
            if nxt == "\u200d":
                if pos + 1 >= len(value) or _is_cluster_extender(value[pos + 1]):
                    pos += 1
                    break
                cluster += nxt + value[pos + 1]
                width = max(width, _codepoint_cells(value[pos + 1]))
                pos += 2
                continue
            if _is_cluster_extender(nxt):
                cluster += nxt
                if nxt == "\ufe0f":  # explicit emoji presentation
                    width = max(width, 2)
                pos += 1
                continue
            break
        yield cluster, width


def _terminal_cell_width(value: str) -> int:
    """Visible terminal cells for the documented conservative approximation."""
    return sum(width for _, width in _grapheme_clusters(value))


_UI_MODES = frozenset({"full", "compact", "plain", "off"})


def _ui_mode() -> str:
    """Return the validated plugin UI option; malformed input is never silence."""
    raw = os.environ.get("CLAUDE_PLUGIN_OPTION_UI_MODE", "")
    return raw if raw in _UI_MODES else "full"


def _session_title(payload: dict, project: dict) -> Optional[str]:
    """Return a stable, privacy-minimal title without overwriting user intent."""
    source = payload.get("source") or payload.get("matcher") or ""
    existing = payload.get("session_title") or payload.get("sessionTitle") or ""
    if source not in {"startup", "resume", "fork"} or str(existing).strip():
        return None
    if _ui_mode() == "off":
        return None
    name = _sanitize_dynamic_text(project.get("name") or project.get("path") or "project")
    return _clip_cells(f"SF · {name}", 60)


def _ambient_surface(
    full_surface: str, state: dict, *, project_name: object = ""
) -> Optional[str]:
    """Project ambient chrome into full, compact, semantic-plain, or hidden form.

    Explicit command output and safety/advisory paths do not call this helper.
    ``NO_COLOR`` remains renderer-level and does not select a UI mode.
    """
    mode = _ui_mode()
    if mode == "full":
        return full_surface
    if mode == "off":
        return None
    stages = state.get("stages") or []
    current = _sanitize_dynamic_text(state.get("currentStage") or "unknown")
    current_is_reached = bool(stages) and all(
        item.get("status") != "future" for item in stages if isinstance(item, dict)
    )
    reached = [
        _sanitize_dynamic_text(item.get("name") or "") for item in stages
        if isinstance(item, dict) and (
            item.get("status") == "complete"
            or (item.get("status") == "current" and current_is_reached)
        )
    ]
    no_evidence = [
        _sanitize_dynamic_text(item.get("name") or "") for item in stages
        if isinstance(item, dict) and (
            item.get("status") == "future"
            or (item.get("status") == "current" and not current_is_reached)
        )
    ]
    project = _sanitize_dynamic_text(project_name) or "no project"
    next_action = _sanitize_dynamic_text(NEXT_ACTION.get(state.get("currentStage"), ""))
    if mode == "compact":
        return _clip_cells(
            f"◆ salesforce-development · {project} · current {current} · next {next_action}",
            80,
        )
    return "\n".join((
        "Salesforce development",
        _clip_cells(f"Project: {project}", 80),
        _clip_cells(f"Current stage: {current}", 80),
        _clip_cells("Reached: " + (", ".join(reached) or "none"), 80),
        _clip_cells("No evidence: " + (", ".join(no_evidence) or "none"), 80),
        _clip_cells(f"Next: {next_action}", 80),
    ))


def _clip_cells(value: object, limit: int) -> str:
    """Sanitize and clip dynamic text to ``limit`` terminal cells with an ellipsis."""
    safe = _sanitize_dynamic_text(value)
    if limit <= 0:
        return ""
    if _terminal_cell_width(safe) <= limit:
        return safe
    budget = max(0, limit - 1)
    out: list[str] = []
    used = 0
    for cluster, width in _grapheme_clusters(safe):
        if used + width > budget:
            break
        out.append(cluster)
        used += width
    return "".join(out) + "…"


def _pad_cells(value: object, width: int) -> str:
    """Sanitize, cell-clip, then right-pad a dynamic field to ``width`` cells."""
    clipped = _clip_cells(value, width)
    return clipped + " " * max(0, width - _terminal_cell_width(clipped))


def _clip(value: str, limit: int) -> str:
    """Backward-compatible cell-aware clipping for dynamic display fields."""
    return _clip_cells(value, limit)


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
    version = _clip_cells(facts.get("version", "?"), _IDENTITY_LIMIT)
    provenance = None
    if facts.get("capabilities") is not None:
        capabilities = _sanitize_dynamic_text(facts.get("capabilities"))
        addable = _sanitize_dynamic_text(facts.get("addable"))
        release = _clip_cells(facts.get("releaseRef"), _IDENTITY_LIMIT)
        provenance = _clip_cells(
            f"{capabilities} capabilities · {addable} addable · release {release}",
            _BAND_WIDTH,
        )
    if use_color:
        try:
            lines = [_paint_lockup(BANNER), _paint_wordmark(version), _paint_muted(BANNER_TAGLINE)]
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
    """Render a labeled box with cell-aware, single-line dynamic fields."""
    inner = width
    safe_title = _clip_cells(title, max(1, inner - 4))
    top = "╭─ " + safe_title + " " + "─" * max(0, inner - _terminal_cell_width(safe_title) - 3) + "╮"
    bot = "╰" + "─" * inner + "╯"
    lines = [top]
    for label, value in rows:
        text = "  " + (_pad_cells(label, 14) + _sanitize_dynamic_text(value) if label else "")
        text = _clip_cells(text, inner)
        lines.append("│" + _pad_cells(text, inner) + "│")
    lines.append(bot)
    return "\n".join(lines)


def _paint_line(segments: list[tuple[str, str]], *, color: bool) -> str:
    """Render `[(text, style), ...]` to one line.

    When color is on, each segment takes its style's palette SGR (theme-adaptive); the
    "muted" style emits plain, so CC's systemMessage dimming renders it as the theme's
    dimmed foreground. When off (NO_COLOR / model-reproduced stdout), the segments are
    concatenated plain. Either way `strip_ansi(painted) == "".join(text for text, _ in
    segments)`, so the goldens track visible text and the model-facing context stays clean.
    """
    if not color:
        return "".join(text for text, _ in segments)
    out = []
    for text, style in segments:
        sgr = _BAND_STYLES[style]
        out.append(f"{sgr}{text}{_SGR_RESET}" if sgr else text)
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


def _notice_band_content(lines: list) -> list:
    """Format plain notice lines (e.g. the telemetry first-run notice, from
    sf_telemetry) into one band group: the first line is the heading, the rest
    body, and blank strings stay as spacer rows. Clipped to the band's text width
    so the ≤80 contract holds. Used to weave the notice in as the FIRST band —
    below the logo lockup, above the org guidance/environment."""
    content: list = []
    for i, line in enumerate(lines):
        if not line:
            content.append("")   # blank spacer, rendered verbatim by render_bands
        else:
            content.append([(_clip(line, 78), "head" if i == 0 else "muted")])
    return content


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
    mcp_status = _sanitize_dynamic_text(mcp_status)
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
    skills = (_sanitize_dynamic_text(facts.get("foundation"))
              if facts.get("foundation") is not None else None)
    library = (_sanitize_dynamic_text(facts.get("library"))
               if facts.get("library") is not None else None)
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
    edition_full = _sanitize_dynamic_text(org.get("edition") or "unknown")
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
    detail = " · ".join(
        _sanitize_dynamic_text(p)
        for p in (org.get("username") or "", org.get("instanceUrl") or "") if p
    )
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
    values = {key: _sanitize_dynamic_text(stats[key]) for key in
              ("apex_src", "apex_test", "triggers", "lwc", "aura", "objects", "permsets", "flows")}
    row1 = (f"Apex {values['apex_src']} src / {values['apex_test']} test · Triggers {values['triggers']} · "
            f"LWC {values['lwc']} · Aura {values['aura']} · Objects {values['objects']}")
    row2 = f"Perm sets {values['permsets']} · Flows {values['flows']}"
    if git_line:
        row2 += f" · {_sanitize_dynamic_text(git_line)}"
    return [header, [(_clip(row1, 78), "muted")], [(_clip(row2, 78), "muted")]]


def render_project_band(project: dict, stats: dict, git_line: str, color: bool) -> list[str]:
    """The project inventory as a standalone rule-framed band."""
    return render_band(_project_content(project, stats, git_line), color=color)


_WAYFINDING_LINES = (
    ("You don't memorize commands here.", "head"),
    ('✳ New here? run /salesforce-development:discovery — or ask "what can I do here?"', "link"),
)


def _wayfinding_footer(next_line: Optional[str] = None, *, color: bool = False) -> list[str]:
    """The reusable wayfinding footer — one definition, pulled in by any surface.

    Two fixed lines: the "you don't memorize commands here" mindset line and the ✳
    discovery pointer (the same two affordances as DISCOVERY_POINTER — run the discovery
    command, or just ask — in the banner's voice). Optionally closed by a caller-supplied
    `next_line`, so the tail is DYNAMIC per surface: pass None where a next step is already
    shown (the SessionStart banner, whose journey rail prints `likely next` directly
    above — restating it would double the guidance), or pass the computed step where there
    is no rail (the readiness banner's "Next: …"). Returns paint lines; when color is off
    each line is its plain text, and `strip_ansi(line)` equals the plain text when on."""
    lines = [_paint_line([segment], color=color) for segment in _WAYFINDING_LINES]
    if next_line:
        lines.append(_paint_line([(next_line, "body")], color=color))
    return lines


def render_invitation(color: bool) -> list[str]:
    """The SessionStart banner's closing invitation: the shared wayfinding footer with
    NO "Next:" line — the journey rail rendered directly above already prints the `likely
    next` step (the readiness banner has no rail, so ITS footer carries the third line —
    the one intended difference). Counts are deliberately NOT restated here — the installed
    count rides in the install summary and the library/addable totals in the provenance
    line, so repeating them would be a third printing of the same facts."""
    return _wayfinding_footer(color=color)


def render_banner_message(org: dict, project: dict, stats: dict, git_line: str, mcp_status: str,
                          *, color: Optional[bool] = None, state: Optional[dict] = None,
                          notice_lines: Optional[list] = None) -> str:
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
    that same data — no extra `sf` calls.

    `notice_lines` (optional) is the one-time telemetry notice's plain text; when
    given it renders as the FIRST band — below the logo/install lockup, above the
    environment band — sharing the region's dividers. Passed on the visible channel
    only (never in the model-facing context), so the notice stays user-only."""
    resolved = _banner_color_enabled() if color is None else color
    facts = _banner_provenance()
    # Leading blank line separates the banner from Claude Code's
    # `SessionStart:startup says:` wrapper that prefixes the systemMessage.
    parts = ["", render_banner_block(color=resolved, facts=facts), ""]
    parts += render_install_summary(resolved, facts=facts)
    parts.append("")
    # The telemetry notice (when due) leads the band region, then environment and
    # project — all one rule-region sharing single dividers, no doubled rules.
    groups = [
        _environment_content(org, mcp_status),
        _project_content(project, stats, git_line),
    ]
    if notice_lines:
        groups.insert(0, _notice_band_content(notice_lines))
    parts += render_bands(groups, color=resolved)
    # The rail rides below the bands. include_context=False: the bands right above
    # already state the project and org, so the rail's context row would repeat them.
    if state is not None:
        parts += ["", _render_journey_rail(state, color=resolved, include_context=False)]
    parts.append("")
    parts += render_invitation(resolved)
    return "\n".join(parts)


def render_degraded_banner(title: str, body_lines: list[str], project: Optional[dict] = None,
                           stats: Optional[dict] = None, git_line: str = "",
                           state: Optional[dict] = None, notice_lines: Optional[list] = None) -> str:
    """A compact banner for non-success states (no org / unreachable). Leaner than
    the connected path — no install summary; the provenance line already signals
    the plugin is live and its inventory counts are not actionable when the problem
    is the org. Renders the lockup, then a rule-region: the guidance (bold title +
    the caller's lines verbatim) and, when a project is detected, the project band
    sharing the divider so a no-org/unreachable session still shows where you are.
    Then the pointer.

    `notice_lines` (optional) is the one-time telemetry notice's plain text; when
    given it leads the rule-region — below the logo lockup, above the guidance —
    sharing the region's dividers. Passed on the visible channel only."""
    color = _banner_color_enabled()
    guidance: list = [[(_clip(title, 78), "head")]]
    for line in body_lines:
        guidance.append(_clip(line, 78) if not line else [(_clip(line, 78), "muted")])
    groups = [guidance]
    if project is not None and stats is not None:
        groups.append(_project_content(project, stats, git_line))
    if notice_lines:
        groups.insert(0, _notice_band_content(notice_lines))
    parts = ["", render_banner_block(color=color), ""]
    parts += render_bands(groups, color=color)
    # Even with no reachable org, SessionStart shows the rail — its `likely next`
    # is exactly the action these states need (authenticate / set a target org).
    if state is not None:
        parts += ["", _render_journey_rail(state, color=color, include_context=False)]
    # Close with the shared wayfinding footer — unified with the connected banner's
    # invitation. No Next line: the rail above already prints `likely next` (the
    # authenticate / set-target / fix action), so passing one would double it.
    parts += [""] + _wayfinding_footer(color=color)
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
                             mcp_status: str, color: bool, state: Optional[dict] = None,
                             include_rail: bool = True) -> str:
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
              _sanitize_dynamic_text(org.get("edition") or "unknown")]
    if org.get("apiVersion"):
        facets.append(f"API v{_sanitize_dynamic_text(org['apiVersion'])}")
    # Clip the whole header to the rail width — edition/API come from the org and
    # are normally short, but the ≤80 contract must hold even for hostile values.
    header = _clip("◆ connected — " + " · ".join(facets), _RAIL_WIDTH)
    parts = ["", _paint_line([(header, "head")], color=color)]
    # The six-stage rail rides along ONLY when it actually moved since the user last
    # saw it (the caller gates on the step-signature). A routine re-set of the same
    # target leaves every step in place, so repainting would just echo the orientation
    # paint or SessionStart banner; the connected-org header above is the real news and
    # always shows. A genuine first connect (Connect ○→●) moves a step, so it paints.
    if include_rail:
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
# Readiness checks inspect the cached "update available from X to Y" warning
# that `sf` writes to STDERR. SessionStart does not run this check. The legacy
# record-update-decision command remains available as a compatibility seam, but
# no active advisory reads its state.

# Set SFDX_SKIP_CLI_UPDATE_CHECK=1 to disable the readiness check (mirrors SFDX_LSP).
_UPDATE_CHECK_ENV = "SFDX_SKIP_CLI_UPDATE_CHECK"
# Legacy per-project decision state, written only for command compatibility.
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
        "current": _sanitize_dynamic_text(_normalize_version(m.group(1))),
        "latest": _sanitize_dynamic_text(_normalize_version(m.group(2))),
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


def _record_update_decision(version: str, reason: str) -> bool:
    """Persist legacy per-version decision state for command compatibility.
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


# --- Environment-readiness verdict (front-of-journey gate) --------------------
#
# A single cached verdict written by the check-tools chokepoint. Both entry
# points to a scan — the /salesforce-development:setup command and the
# platform-environment-validate skill — funnel through cmd_check_tools, so
# writing it there populates the same state no matter how the scan was
# triggered. The getting-started welcome reads it CHEAPLY (no subprocess) so it
# doesn't nudge a newcomer toward "create a project" before the toolchain is
# verified. Like the legacy _UPDATE_STATE writer: one JSON object, cwd-relative
# .sf/, fail-open read / fail-silent write.
#
# Honesty invariant (non-negotiable): an absent or corrupt verdict reads as {} —
# "unchecked", never a pass. Only a real, signature-matched all-green scan yields
# a "ready" that suppresses the nudge.
_READINESS_STATE = Path(".sf") / "environment-readiness.json"
_READINESS_JSON_MAX_BYTES = 64 * 1024

# Prefix on the readiness backstop's deny reason so the block is unambiguously
# attributable to this gate (mirrors sf-deploy-gate's tagged reasons).
_READINESS_GATE_TAG = "[salesforce-development · environment-readiness]"


def _load_bounded_small_json(path: Path) -> dict:
    """Read one bounded regular-file JSON object, failing open otherwise.

    Readiness files use the same pinned project ``.sf`` directory boundary as
    phase history. The direct-path branch remains only for this private helper's
    non-readiness unit seam and still refuses final-component links.
    """
    flags = os.O_RDONLY
    for name in ("O_NOFOLLOW", "O_NONBLOCK", "O_CLOEXEC", "O_BINARY"):
        flags |= getattr(os, name, 0)

    fd = None
    directory = None
    try:
        if path.parent == Path(".sf"):
            directory = _open_phase_directory(False)
            if directory is None:
                return {}
            fd = _open_phase_child(directory, path.name, flags)
        else:
            fd = os.open(path, flags)
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                or info.st_size > _READINESS_JSON_MAX_BYTES):
            return {}
        chunks = []
        remaining = _READINESS_JSON_MAX_BYTES + 1
        while remaining:
            chunk = os.read(fd, remaining)
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        encoded = b"".join(chunks)
        if len(encoded) > _READINESS_JSON_MAX_BYTES:
            return {}
        value = json.loads(encoded)
        return value if isinstance(value, dict) else {}
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, RecursionError):
        return {}
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
        if directory is not None:
            _close_phase_directory(directory)


def _atomic_write_small_json(path: Path, value: object) -> bool:
    """Atomically publish one bounded owner-private JSON file in pinned ``.sf``."""
    try:
        encoded = json.dumps(value, indent=2).encode("utf-8")
    except (RecursionError, TypeError, ValueError, UnicodeEncodeError):
        return False
    if len(encoded) > _READINESS_JSON_MAX_BYTES:
        return False
    if (not isinstance(path, Path) or path.is_absolute()
            or path.parent != Path(".sf") or path.name in ("", ".", "..")):
        return False

    temporary_name = f".{path.name}.{secrets.token_hex(8)}.tmp"
    temporary_owned = False
    directory = _open_phase_directory(True)
    if directory is None:
        return False
    fd = None
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
        fd = _open_phase_child(directory, temporary_name, flags, 0o600)
        temporary_owned = True
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise OSError("unsafe readiness JSON temporary")
        view = memoryview(encoded)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise OSError("short readiness JSON write")
            view = view[written:]
        os.fsync(fd)
        os.close(fd)
        fd = None
        if not _replace_phase_entry(directory, temporary_name, path.name):
            return False
        temporary_owned = False
        # A visible rename is not a durable publication until the containing
        # directory entry is synced. Do not report success when that cannot be proven.
        return _sync_phase_directory(directory)
    except OSError:
        return False
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
        if temporary_owned:
            _unlink_phase_entry(directory, temporary_name)
        _close_phase_directory(directory)


def _toolchain_signature() -> str:
    """A cheap fingerprint of the resolved dev-tool executables — PATH lookups
    only, NO subprocess. Used to decide whether a cached "ready" verdict still
    applies: if any of these resolve differently than when the scan ran (e.g. the
    user just installed Node, or `sf` moved), the cached pass is stale and we
    re-nudge rather than trust a green that no longer describes this machine.

    Each resolved path is canonicalized with realpath so the signature is STABLE
    across shells: version managers (fnm, nvm, pyenv) hand out a per-shell shim path
    that varies invocation-to-invocation but resolves to the same real binary.
    Without canonicalization that shim churn would spuriously invalidate a fresh
    pass between the scan and a later welcome; with it, the signature keys on the
    real executable — and still changes when the underlying version does, since a
    new version is a new realpath target."""
    import os

    def _canonical(path: str) -> str:
        if not path:
            return ""
        try:
            return os.path.realpath(path)
        except OSError:
            return path

    return "|".join(_canonical(resolve_executable(t) or "") for t in ("sf", "node", "npm", "git"))


def _load_readiness_state() -> dict:
    return _load_bounded_small_json(_READINESS_STATE)


def _record_readiness_verdict(ready: bool, needs_attention: list, signature: str,
                              blockers: list = None) -> bool:
    """Persist the coarse readiness verdict.

    Two lists, because "safe to scaffold" is not "all green":
      - `needs_attention` — names of the critical OR warn rows: the honest "not
        green" list the banner speaks to (advisory + blocking together).
      - `blockers` — names of the CRITICAL rows only: the subset that would
        actually make scaffolding (and the build/deploy it leads to) fail. This is
        what the scaffold gate blocks on and names in its deny reason.
    `ready` should be "no blockers", NOT "all green" — a 🟡 warn is advisory and
    must never gate. `blockers` defaults to `needs_attention` when omitted so an
    older caller that doesn't distinguish severities keeps its prior behaviour.
    Returns True on success and False when the bounded atomic write cannot complete."""
    if blockers is None:
        blockers = needs_attention
    return _atomic_write_small_json(
        _READINESS_STATE,
        {
            "ready": ready,
            "needsAttention": needs_attention,
            "blockers": blockers,
            "signature": signature,
            "checkedAt": datetime.now(timezone.utc).isoformat(),
        },
    )


def _readiness_is_fresh(signature: str) -> bool:
    """A cached verdict counts as fresh only when it was a PASS *and* the current
    toolchain signature matches the one recorded at scan time. A not-ready verdict
    is never fresh, and any change on PATH invalidates a stale green."""
    state = _load_readiness_state()
    return bool(state.get("ready")) and state.get("signature") == signature


# The FULL check-tools report, persisted alongside the coarse verdict. The
# PostToolUse readiness-paint hook renders the deterministic banner from this —
# a PostToolUse payload carries only the executed command, never the tool's
# stdout, so the report cannot be read back from the hook event itself. Same
# cwd-relative .sf/, fail-silent write / fail-open read as _READINESS_STATE.
_READINESS_REPORT = Path(".sf") / "environment-readiness-report.json"


def _record_readiness_report(report: dict) -> bool:
    """Persist the full check-tools report. Returns True on success, False when
    the best-effort bounded atomic write cannot be completed."""
    return _atomic_write_small_json(_READINESS_REPORT, report)


def _load_readiness_report() -> dict:
    """Read the persisted report, or {} when absent/corrupt/oversized."""
    return _load_bounded_small_json(_READINESS_REPORT)


def cmd_record_update_decision() -> int:
    """Legacy compatibility command for persisting per-version CLI update state.
    Usage: sf-context record-update-decision <version> <reason>."""
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

# --- Prompt-scoped hook coordination -----------------------------------------
# Hook processes cannot coordinate through cwd: sessions may share a project and a
# session may `/cd` while one prompt is still active. Prompt facts therefore live in
# a private OS-runtime namespace keyed by validated session + native prompt_id. On
# hosts predating prompt_id, the single UserPromptSubmit dispatcher rotates a random
# fallback token and later hooks resolve it. That fallback cannot distinguish a truly
# delayed prior-turn event; native prompt_id can.
#
# Facts are independent marker files. In particular, the rail marker is created with
# O_CREAT|O_EXCL immediately before visible emission. This gives an at-most-once
# posture across hook processes: a crash after claiming but before emit can lose a
# rail, but concurrent eligible painters cannot duplicate it. Missing/corrupt state
# never becomes evidence for suppression.
_PROMPT_RUNTIME_DIR = Path(tempfile.gettempdir()) / "sf-hl360-runtime-v1"
_PROMPT_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_PROMPT_MAX_SESSIONS = 128
_PROMPT_MAX_TURNS_PER_SESSION = 128
_PROMPT_MAX_SKILLS = 64
_PROMPT_MAX_AGE_SECONDS = 2 * 24 * 60 * 60
# Hard ceilings for best-effort cleanup. Hostile temp trees must not make a hook
# enumerate, sort, or recursively traverse attacker-controlled entry counts.
_PROMPT_CLEANUP_SESSION_SCAN_CAP = 256
_PROMPT_CLEANUP_TURN_SCAN_CAP = 256
_PROMPT_CLEANUP_CHILD_SCAN_CAP = _PROMPT_MAX_SKILLS + 4
PromptContext = namedtuple("PromptContext", ("session_key", "prompt_key", "path"))

# --- Durable phase tracker (journey-rail reachability engine) ----------------
# An append-only JSONL history of the build-lifecycle phases this project has
# genuinely reached — one line per witnessed milestone. It is the store the
# journey rail's reachability rests on: a stage's status is DERIVED from this
# recorded history (a recorded reach => `●`, the working cursor => `◉`, nothing
# recorded => `○`), never re-guessed live. That is what lets Deploy/Observe earn
# `●` honestly instead of being hardcoded `unknown`: completion is a historical
# fact on disk, and a historical fact does not decay.
#
# Append-only (unlike the independent prompt marker files); the several hook
# processes serialize appends with a contained advisory-locked fd, and one bad line can
# be rejected without losing the rest. Same `.sf/` scratch convention and
# fail-silent hot-path discipline as the state files above: a write must never
# raise or touch stdout (which carries the hook's JSON contract); missing/unsafe
# history fails OPEN to no evidence.
#
# Per-line schema (new writes are versioned; valid unversioned legacy rows remain readable):
#   { "schemaVersion": 1,
#     "type":   "phase-reached",     # deploy | test-run | observe | observe-skill | …
#     "stage":  "Deploy",            # one of JOURNEY_STAGES
#     "outcome":"passed",            # passed | failed | present  (failed => micro "attempted", not ●)
#     "orgHash":"…",                 # org-match ANNOTATION only — never gates the ● (optional)
#     "source": "cmd_post_deploy",   # which writer recorded it
#     "ts":     "2026-08-02T…" }     # ISO-8601 UTC
_PHASE_HISTORY = Path(".sf") / "phase-history.jsonl"
_PHASE_HISTORY_LOCK = Path(".sf") / "phase-history.lock"
_PHASE_ORG_KEY = Path(".sf") / "phase-org.key"
_PHASE_HISTORY_SCHEMA_VERSION = 1
_PHASE_HISTORY_MAX_FILE_BYTES = 1024 * 1024
_PHASE_HISTORY_MAX_LINE_BYTES = 16 * 1024
_PHASE_HISTORY_MAX_RECORDS = 4096
_PHASE_HISTORY_TOKEN_MAX = 64
_PHASE_HISTORY_TIMESTAMP_MAX = 40
_PHASE_HISTORY_LOCK_WAIT_SECONDS = 1.0
_PHASE_HISTORY_OUTCOMES = frozenset({"passed", "failed", "present"})
_PHASE_HISTORY_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")
_PHASE_HISTORY_ORG_DIGEST = re.compile(r"^[a-f0-9]{64}$")
_JOURNEY_RESET_NONCE = re.compile(r"^[a-f0-9]{64}$")
_JOURNEY_RESET_SCOPES = frozenset({"all", "current-org", "other-org", "unattributed"})
_PHASE_HISTORY_KEYS = frozenset(
    {"schemaVersion", "type", "stage", "outcome", "source", "ts", "orgHash"}
)
_PHASE_EVENT_MATRIX = {
    "deploy": frozenset({("Deploy", "passed"), ("Deploy", "failed")}),
    "test-run": frozenset({("Test", "passed")}),
    "observe": frozenset({("Observe", "passed")}),
    "observe-skill": frozenset({("Observe", "present")}),
}
PhaseHistoryResult = namedtuple(
    "PhaseHistoryResult", ("accepted", "rejected", "truncated", "records")
)
PhaseDirectory = namedtuple(
    "PhaseDirectory",
    ("fd", "path", "relative", "root_path", "root_identity", "parent_identity"),
)
PhaseReplaceOutcome = namedtuple("PhaseReplaceOutcome", ("status",))
PhaseTempWriteOutcome = namedtuple("PhaseTempWriteOutcome", ("success", "owned"))
_PHASE_REPLACE_SUCCESS = "success"
_PHASE_REPLACE_ROLLED_BACK = "failed-with-confirmed-rollback"
_PHASE_REPLACE_UNCERTAIN = "uncertain-rollback-failed"
_PHASE_DIR_FD_SUPPORTED = os.open in getattr(os, "supports_dir_fd", set())


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


# --- Prompt-scoped skills and rail state -------------------------------------

def _runtime_id(value: object) -> Optional[str]:
    return value if isinstance(value, str) and _PROMPT_ID_PATTERN.fullmatch(value) else None


def _runtime_key(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _ensure_private_runtime_dir(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        info = path.lstat()
        if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode):
            return False
        if hasattr(os, "getuid") and info.st_uid != os.getuid():
            return False
        try:
            path.chmod(0o700)
        except OSError:
            pass
        return True
    except OSError:
        return False


def _atomic_private_text(path: Path, value: str) -> bool:
    """Atomically replace one private marker without following a destination symlink."""
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(8)}")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(temporary, flags, 0o600)
        try:
            os.write(fd, value.encode("ascii"))
            os.fsync(fd)
        finally:
            os.close(fd)
        # replace(2) replaces the directory entry itself; it does not follow a
        # symlink already occupying the destination name.
        os.replace(temporary, path)
        return True
    except OSError:
        try:
            temporary.unlink()
        except OSError:
            pass
        return False


def _private_text(path: Path, max_bytes: int = 4096) -> Optional[str]:
    """Read one owned regular marker without following links or accepting hardlinks."""
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
        try:
            info = os.fstat(fd)
            if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                    or (hasattr(os, "getuid") and info.st_uid != os.getuid())):
                return None
            data = os.read(fd, max_bytes + 1)
            if len(data) > max_bytes:
                return None
            return data.decode("ascii")
        finally:
            os.close(fd)
    except (OSError, UnicodeDecodeError):
        return None


def _private_marker_exists(path: Path) -> bool:
    try:
        info = path.lstat()
        return (stat.S_ISREG(info.st_mode) and info.st_nlink == 1
                and (not hasattr(os, "getuid") or info.st_uid == os.getuid()))
    except OSError:
        return False


def _prompt_context(payload: dict, *, rotate_fallback: bool = False) -> Optional[PromptContext]:
    """Resolve one native/fallback prompt namespace, or None on invalid state.

    Only UserPromptSubmit passes rotate_fallback=True. Later hooks without native
    prompt_id read that session's current token; a missing/corrupt token therefore
    fails open instead of suppressing current guidance.
    """
    if not isinstance(payload, dict):
        return None
    session_id = _runtime_id(payload.get("session_id") or payload.get("sessionId"))
    if session_id is None or not _ensure_private_runtime_dir(_PROMPT_RUNTIME_DIR):
        return None
    session_path = _PROMPT_RUNTIME_DIR / _runtime_key(session_id)
    if not _ensure_private_runtime_dir(session_path):
        return None

    native = payload.get("prompt_id") or payload.get("promptId")
    prompt_id = _runtime_id(native) if native is not None else None
    if native is not None and prompt_id is None:
        return None
    if prompt_id is None:
        current = session_path / "current-fallback"
        if rotate_fallback:
            prompt_id = "fallback-" + secrets.token_hex(24)
            if not _atomic_private_text(current, prompt_id):
                return None
        else:
            text = _private_text(current)
            if text is None:
                return None
            prompt_id = _runtime_id(text.strip())
            if prompt_id is None or not prompt_id.startswith("fallback-"):
                return None

    prompt_path = session_path / _runtime_key(prompt_id)
    if not _ensure_private_runtime_dir(prompt_path):
        return None
    try:
        os.utime(session_path, None)
        os.utime(prompt_path, None)
    except OSError:
        pass
    return PromptContext(_runtime_key(session_id), _runtime_key(prompt_id), prompt_path)


def _remove_prompt_dir(path: Path) -> bool:
    """Remove only the fixed, shallow shape written by this plugin."""
    try:
        scanned = 0
        with os.scandir(path) as entries:
            for entry in entries:
                scanned += 1
                if scanned > _PROMPT_CLEANUP_CHILD_SCAN_CAP:
                    return False
                child = path / entry.name
                if entry.name == "rail.claim" and entry.is_file(follow_symlinks=False):
                    child.unlink()
                elif entry.name == "skills" and entry.is_dir(follow_symlinks=False):
                    skill_count = 0
                    with os.scandir(child) as skills:
                        for skill in skills:
                            skill_count += 1
                            if skill_count > _PROMPT_MAX_SKILLS:
                                return False
                            if (not _SKILL_NAME_PATTERN.fullmatch(skill.name)
                                    or not skill.is_file(follow_symlinks=False)):
                                return False
                            (child / skill.name).unlink()
                    child.rmdir()
                else:
                    return False
        path.rmdir()
        return True
    except OSError:
        return False


def _remove_session_dir(path: Path, current: Optional[PromptContext]) -> bool:
    try:
        scanned = 0
        with os.scandir(path) as entries:
            for entry in entries:
                scanned += 1
                if scanned > _PROMPT_CLEANUP_TURN_SCAN_CAP:
                    return False
                child = path / entry.name
                if entry.name == "current-fallback" and entry.is_file(follow_symlinks=False):
                    child.unlink()
                elif (re.fullmatch(r"[a-f0-9]{64}", entry.name)
                      and entry.is_dir(follow_symlinks=False)
                      and (current is None or child != current.path)):
                    if not _remove_prompt_dir(child):
                        return False
                else:
                    return False
        path.rmdir()
        return True
    except OSError:
        return False


def _prune_prompt_runtime(current: Optional[PromptContext]) -> None:
    """Bounded best-effort pruning; correctness never depends on cleanup."""
    try:
        now = time.time()
        scanned_sessions = 0
        managed_sessions = 0
        with os.scandir(_PROMPT_RUNTIME_DIR) as sessions:
            for session in sessions:
                scanned_sessions += 1
                if scanned_sessions > _PROMPT_CLEANUP_SESSION_SCAN_CAP:
                    break
                if (not re.fullmatch(r"[a-f0-9]{64}", session.name)
                        or not session.is_dir(follow_symlinks=False)):
                    continue
                managed_sessions += 1
                session_path = _PROMPT_RUNTIME_DIR / session.name
                info = session.stat(follow_symlinks=False)
                stale_session = now - info.st_mtime > _PROMPT_MAX_AGE_SECONDS
                excess_session = managed_sessions > _PROMPT_MAX_SESSIONS
                if ((stale_session or excess_session)
                        and (current is None or session.name != current.session_key)):
                    _remove_session_dir(session_path, current)
                    continue
                scanned_turns = 0
                managed_turns = 0
                with os.scandir(session_path) as turns:
                    for turn in turns:
                        scanned_turns += 1
                        if scanned_turns > _PROMPT_CLEANUP_TURN_SCAN_CAP:
                            break
                        if (not re.fullmatch(r"[a-f0-9]{64}", turn.name)
                                or not turn.is_dir(follow_symlinks=False)):
                            continue
                        managed_turns += 1
                        turn_path = session_path / turn.name
                        stale = now - turn.stat(follow_symlinks=False).st_mtime > _PROMPT_MAX_AGE_SECONDS
                        excess = managed_turns > _PROMPT_MAX_TURNS_PER_SESSION
                        if ((stale or excess)
                                and (current is None or turn_path != current.path)):
                            _remove_prompt_dir(turn_path)
    except OSError:
        pass


def _record_dispatched_skill(context: Optional[PromptContext], skill: str) -> None:
    if context is None or not isinstance(skill, str) or not _SKILL_NAME_PATTERN.fullmatch(skill):
        return
    skills = context.path / "skills"
    if not _ensure_private_runtime_dir(skills):
        return
    try:
        count = 0
        with os.scandir(skills) as markers:
            for _ in markers:
                count += 1
                if count >= _PROMPT_MAX_SKILLS:
                    break
        if count >= _PROMPT_MAX_SKILLS and not _private_marker_exists(skills / skill):
            return
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(skills / skill, flags, 0o600)
        os.close(fd)
    except FileExistsError:
        pass
    except OSError:
        pass


def _dispatched_skills(context: Optional[PromptContext]) -> set[str]:
    if context is None:
        return set()
    try:
        skills = context.path / "skills"
        found = set()
        with os.scandir(skills) as markers:
            for index, marker in enumerate(markers):
                if index >= _PROMPT_MAX_SKILLS:
                    break
                if (marker.is_file(follow_symlinks=False)
                        and _SKILL_NAME_PATTERN.fullmatch(marker.name)):
                    found.add(marker.name)
        return found
    except OSError:
        return set()


def _claim_prompt_rail(context: Optional[PromptContext]) -> bool:
    """Atomically claim this prompt's visible rail immediately before emission.

    False means another process already won. An I/O failure returns True (without a
    durable claim), deliberately failing toward duplicate guidance rather than
    suppressing current output.
    """
    if context is None:
        return False
    try:
        fd = os.open(context.path / "rail.claim", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.close(fd)
        return True
    except FileExistsError:
        return False
    except OSError:
        return True


def _rail_painted_this_turn(context_or_session) -> bool:
    context = context_or_session
    if isinstance(context_or_session, str):
        context = _prompt_context({"session_id": context_or_session}, rotate_fallback=False)
    return bool(context and _private_marker_exists(context.path / "rail.claim"))


def _record_rail_painted(context_or_session) -> None:
    """Compatibility wrapper; production painters claim before emitting."""
    context = context_or_session
    if isinstance(context_or_session, str):
        context = _prompt_context({"session_id": context_or_session}, rotate_fallback=False)
    _claim_prompt_rail(context)


def cmd_record_skill_dispatch() -> int:
    """Record a Skill dispatch as an independent marker in this prompt namespace."""
    payload = _read_hook_payload()
    tool_input = payload.get("tool_input", {}) or payload.get("toolInput", {}) or {}
    skill = (tool_input.get("skill") or tool_input.get("skill_name")
             or tool_input.get("name") or "") if isinstance(tool_input, dict) else ""
    bare = skill.split(":")[-1] if isinstance(skill, str) else ""
    _record_dispatched_skill(_prompt_context(payload, rotate_fallback=False), bare)
    print(json.dumps({"continue": True}))
    return 0


def cmd_reset_dispatch_turn() -> int:
    """Legacy command compatibility; no manifest hook uses it.

    On old hosts this rotates the same cryptographically random fallback token now
    owned by prompt-dispatch. Native prompt_id needs no reset because it is the key.
    """
    payload = _read_hook_payload()
    context = _prompt_context(payload, rotate_fallback=not bool(
        payload.get("prompt_id") or payload.get("promptId")))
    _prune_prompt_runtime(context)
    print(json.dumps({"continue": True}))
    return 0


# --- Project-scoped rail STEP-SIGNATURE (the reprint-on-change gate) ----------
# Distinct from the atomic prompt claim above: the claim de-dupes concurrent visible
# rails for one prompt, while this signature governs whether an unsolicited connect
# wayfinder should carry a rail at all. It survives prompts but is namespaced by both
# session and stable project root, so equal stages in a newly entered project still
# paint once. Missing/unreadable state means "nothing shown" and never suppresses.
def _rail_signature(state: dict) -> str:
    """A fingerprint of the SIX rail STEPS — the ordered (stage, status) pairs, and
    nothing else. The org header, edition/API, and source-tracking note are
    deliberately excluded: "a journey rail step changed" is about the steps, so a
    connect that re-resolves the same org yields an IDENTICAL signature and the
    unsolicited rail de-dupes. `likely next` is a pure function of the cursor, so
    the step tuple already captures it."""
    return "|".join(
        f"{s.get('name')}:{s.get('status')}" for s in (state.get("stages") or [])
    )


def _last_rail_signature(session_id: str) -> Optional[str]:
    """The last steps shown in this session *and stable project root*.

    Equal stages in project B must not be mistaken for a rail already shown in
    project A. Missing state remains fail-open to painting.
    """
    if not session_id:
        return None
    marker = _session_marker(session_id, "railsig")
    if not _ensure_private_runtime_dir(marker.parent):
        return None
    sig = _private_text(marker)
    return sig.strip() or None if sig is not None else None


def _record_rail_signature(session_id: str, state: dict) -> None:
    """Persist a steps-only signature under the current stable project namespace."""
    if not session_id:
        return
    marker = _session_marker(session_id, "railsig")
    if _ensure_private_runtime_dir(marker.parent):
        _atomic_private_text(marker, _rail_signature(state))


def _phase_file_names() -> Optional[tuple[str, str, str]]:
    """Return fixed child names only when all configured paths are safe `.sf` paths."""
    paths = (_PHASE_HISTORY, _PHASE_HISTORY_LOCK, _PHASE_ORG_KEY)
    if any(
        not isinstance(path, Path)
        or path.is_absolute()
        or path.parent != Path(".sf")
        or path.name in ("", ".", "..")
        for path in paths
    ):
        return None
    return paths[0].name, paths[1].name, paths[2].name


def _phase_identity(info: os.stat_result) -> tuple[int, int]:
    return info.st_dev, info.st_ino


def _phase_is_link_or_reparse(info: os.stat_result) -> bool:
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return stat.S_ISLNK(info.st_mode) or bool(
        reparse and getattr(info, "st_file_attributes", 0) & reparse
    )


def _phase_safe_directory_info(info: os.stat_result) -> bool:
    return stat.S_ISDIR(info.st_mode) and not _phase_is_link_or_reparse(info)


def _phase_fallback_unchanged(directory: PhaseDirectory) -> bool:
    try:
        root_info = directory.root_path.lstat()
        parent_info = directory.path.lstat()
        return (
            _phase_safe_directory_info(root_info)
            and _phase_safe_directory_info(parent_info)
            and _phase_identity(root_info) == directory.root_identity
            and _phase_identity(parent_info) == directory.parent_identity
            and directory.path.parent == directory.root_path
        )
    except (AttributeError, OSError):
        return False


def _open_phase_directory(create: bool) -> Optional[PhaseDirectory]:
    """Open and pin the real project `.sf` directory before child operations.

    On platforms supporting `dir_fd`, both creation and the no-follow directory
    open are relative to a pinned cwd descriptor, eliminating pathname parent
    swaps. The fallback pins and identity-checks the directory for platforms whose
    Python runtime lacks openat-style APIs.
    """
    if _phase_file_names() is None:
        return None
    parent = Path(".sf")
    relative = _PHASE_DIR_FD_SUPPORTED
    root_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    directory_flags = root_flags | getattr(os, "O_BINARY", 0)
    directory_flags |= getattr(os, "O_NOFOLLOW", 0)
    if relative:
        root_fd = None
        try:
            # Pin the process's actual cwd inode directly. Never resolve getcwd() and
            # reopen that pathname: an attacker can replace it between those calls.
            root_fd = os.open(".", root_flags)
            if create:
                try:
                    os.mkdir(".sf", 0o700, dir_fd=root_fd)
                except FileExistsError:
                    pass
            fd = os.open(".sf", directory_flags, dir_fd=root_fd)
            info = os.fstat(fd)
            if not stat.S_ISDIR(info.st_mode):
                os.close(fd)
                return None
            return PhaseDirectory(
                fd=fd, path=parent, relative=True, root_path=None,
                root_identity=None, parent_identity=None,
            )
        except OSError:
            return None
        finally:
            if root_fd is not None:
                os.close(root_fd)

    try:
        # Windows Python does not expose openat/dir_fd for os.open. Capture one
        # canonical root pathname, reject reparse/symlink directories, and retain
        # root + parent identities for checks immediately before and after every
        # child open. Stable normal paths work; any observed race fails closed.
        reported_root = Path(os.getcwd())
        reported_info = reported_root.lstat()
        root = Path(os.path.realpath(reported_root))
        parent = root / ".sf"
        root_info = root.lstat()
        if (
            not _phase_safe_directory_info(reported_info)
            or not _phase_safe_directory_info(root_info)
            or _phase_identity(reported_info) != _phase_identity(root_info)
        ):
            return None
        if create:
            try:
                os.mkdir(parent, 0o700)
            except FileExistsError:
                pass
        parent_info = parent.lstat()
        if not _phase_safe_directory_info(parent_info):
            return None
        directory = PhaseDirectory(
            fd=None,
            path=parent,
            relative=False,
            root_path=root,
            root_identity=_phase_identity(root_info),
            parent_identity=_phase_identity(parent_info),
        )
        return directory if _phase_fallback_unchanged(directory) else None
    except OSError:
        return None


def _close_phase_directory(directory: Optional[PhaseDirectory]) -> None:
    if directory is not None and directory.fd is not None:
        try:
            os.close(directory.fd)
        except OSError:
            pass


def _open_phase_child(
    directory: PhaseDirectory, name: str, flags: int, mode: int = 0o600
) -> int:
    """Open a child of the pinned `.sf` directory without following its final link."""
    flags |= getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    if directory.relative:
        return os.open(name, flags, mode, dir_fd=directory.fd)
    # Windows fallback: no directory fds. Check the canonical root and `.sf`
    # identities both before and after opening the full child pathname.
    if not _phase_fallback_unchanged(directory):
        raise OSError("phase root or directory changed")
    child = directory.path / name
    before = None
    try:
        before = child.lstat()
        if _phase_is_link_or_reparse(before) or not stat.S_ISREG(before.st_mode):
            raise OSError("unsafe phase child")
        if before.st_nlink != 1:
            raise OSError("hard-linked phase child")
    except FileNotFoundError:
        if not flags & os.O_CREAT:
            raise
    fd = os.open(child, flags, mode)
    try:
        opened = os.fstat(fd)
        after = child.lstat()
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_nlink != 1
            or _phase_is_link_or_reparse(after)
            or not stat.S_ISREG(after.st_mode)
            or after.st_nlink != 1
            or _phase_identity(after) != _phase_identity(opened)
            or (before is not None and _phase_identity(before) != _phase_identity(opened))
            or not _phase_fallback_unchanged(directory)
        ):
            raise OSError("phase child or parent changed")
        return fd
    except Exception:
        os.close(fd)
        raise


def _phase_regular_fd(fd: int) -> bool:
    info = os.fstat(fd)
    return stat.S_ISREG(info.st_mode) and info.st_nlink == 1


def _phase_private_fd(fd: int) -> bool:
    """Accept only an owned, singly-linked regular file for private attribution data."""
    info = os.fstat(fd)
    return (
        stat.S_ISREG(info.st_mode)
        and info.st_nlink == 1
        and (not hasattr(os, "getuid") or info.st_uid == os.getuid())
        and (os.name == "nt" or stat.S_IMODE(info.st_mode) & 0o077 == 0)
    )


def _phase_restrict_fd(fd: int) -> None:
    """Apply owner-only mode where the platform supports descriptor chmod."""
    if hasattr(os, "fchmod"):
        try:
            os.fchmod(fd, 0o600)
        except OSError:
            pass


def _phase_timestamp_valid(value: object) -> bool:
    if not isinstance(value, str) or not (1 <= len(value) <= _PHASE_HISTORY_TIMESTAMP_MAX):
        return False
    if not value.isascii() or any(ord(char) < 0x20 or ord(char) == 0x7f for char in value):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _phase_token_valid(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) <= _PHASE_HISTORY_TOKEN_MAX
        and _PHASE_HISTORY_TOKEN.fullmatch(value) is not None
    )


def _validate_phase_record(value: object) -> Optional[dict]:
    """Validate and normalize one legacy or versioned phase-history record.

    Only allowlisted fields cross the boundary, so ignored JSON properties cannot
    later become model context by accident. Valid unversioned legacy rows remain
    readable; versioned rows require the full writer schema.
    """
    if not isinstance(value, dict) or not set(value).issubset(_PHASE_HISTORY_KEYS):
        return None
    versioned = "schemaVersion" in value
    version = value.get("schemaVersion")
    if versioned and (isinstance(version, bool) or version != _PHASE_HISTORY_SCHEMA_VERSION):
        return None
    stage, outcome, event_type = value.get("stage"), value.get("outcome"), value.get("type")
    if stage not in JOURNEY_STAGES or outcome not in _PHASE_HISTORY_OUTCOMES:
        return None
    if not _phase_token_valid(event_type) or event_type not in _PHASE_EVENT_MATRIX:
        return None
    if (stage, outcome) not in _PHASE_EVENT_MATRIX[event_type]:
        return None
    source = value.get("source")
    timestamp = value.get("ts")
    # The oldest unversioned rows carried only type/stage/outcome. When annotations
    # are present they are validated just as strictly as the current schema.
    if versioned and (source is None or timestamp is None):
        return None
    if "source" in value and not _phase_token_valid(source):
        return None
    if "ts" in value and not _phase_timestamp_valid(timestamp):
        return None
    org_hash = value.get("orgHash")
    if "orgHash" in value and (
        not isinstance(org_hash, str) or _PHASE_HISTORY_ORG_DIGEST.fullmatch(org_hash) is None
    ):
        return None

    normalized = {}
    if versioned:
        normalized["schemaVersion"] = version
    for key in ("type", "stage", "outcome", "source", "ts", "orgHash"):
        if key in value:
            normalized[key] = value[key]
    return normalized


def _empty_phase_history() -> PhaseHistoryResult:
    return PhaseHistoryResult(accepted=0, rejected=0, truncated=False, records=[])


def _parse_phase_history_bytes(preimage: bytes) -> PhaseHistoryResult:
    """Apply the canonical bounded parser to an already pinned byte preimage."""
    raw = preimage[:_PHASE_HISTORY_MAX_FILE_BYTES + 1]
    file_truncated = len(raw) > _PHASE_HISTORY_MAX_FILE_BYTES
    raw = raw[:_PHASE_HISTORY_MAX_FILE_BYTES]
    # Never parse the cap-cut tail as a record. A writer always terminates a record
    # with newline, so a nonterminated tail is incomplete when the file was capped.
    if file_truncated and raw and not raw.endswith(b"\n"):
        raw = raw.rpartition(b"\n")[0]
        if raw:
            raw += b"\n"

    records: list[dict] = []
    rejected = 0
    truncated = file_truncated
    for encoded in raw.splitlines():
        if not encoded.strip():
            continue
        if len(encoded) > _PHASE_HISTORY_MAX_LINE_BYTES:
            rejected += 1
            continue
        try:
            value = json.loads(encoded.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
            rejected += 1
            continue
        record = _validate_phase_record(value)
        if record is None:
            rejected += 1
            continue
        if len(records) >= _PHASE_HISTORY_MAX_RECORDS:
            truncated = True
            break
        records.append(record)
    return PhaseHistoryResult(
        accepted=len(records), rejected=rejected, truncated=truncated, records=records
    )


def _load_phase_history_result() -> PhaseHistoryResult:
    """Return the one canonical bounded parse result for durable journey evidence.

    Missing or unsafe history remains fail-open to no evidence. Invalid lines are
    counted without exposing their bytes; file and record caps set `truncated`.
    """
    names = _phase_file_names()
    directory = _open_phase_directory(False)
    if names is None or directory is None:
        return _empty_phase_history()
    fd = None
    try:
        fd = _open_phase_child(
            directory, names[0], os.O_RDONLY | getattr(os, "O_NONBLOCK", 0)
        )
        if not _phase_regular_fd(fd):
            return _empty_phase_history()
        with os.fdopen(fd, "rb", closefd=False) as stream:
            raw = stream.read(_PHASE_HISTORY_MAX_FILE_BYTES + 1)
        return _parse_phase_history_bytes(raw)
    except OSError:
        return _empty_phase_history()
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
        _close_phase_directory(directory)


def _load_phase_history() -> list[dict]:
    """Compatibility list wrapper over the canonical bounded parser."""
    return _load_phase_history_result().records


def _public_phase_evidence(record: dict, current_org_hash: Optional[str] = None) -> dict:
    """Project one accepted record into the bounded, non-sensitive public shape."""
    event_hash = record.get("orgHash")
    scope = "unattributed"
    if current_org_hash and event_hash:
        scope = "current-org" if hmac.compare_digest(current_org_hash, event_hash) else "other-org"
    return {
        "stage": record.get("stage"),
        "type": record.get("type"),
        "outcome": record.get("outcome"),
        "source": record.get("source"),
        "ts": record.get("ts"),
        "scope": scope,
    }


def _phase_history_present() -> bool:
    """Check only the pinned history entry; never return or render its path."""
    names = _phase_file_names()
    directory = _open_phase_directory(False)
    if names is None or directory is None:
        return False
    fd = None
    try:
        fd = _open_phase_child(directory, names[0], os.O_RDONLY)
        return _phase_regular_fd(fd)
    except OSError:
        return False
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
        _close_phase_directory(directory)


def _accepted_phase_records(values: object) -> list[dict]:
    """Normalize injected/in-memory history through the canonical record validator."""
    if not isinstance(values, list):
        return []
    accepted = []
    for value in values[:_PHASE_HISTORY_MAX_RECORDS]:
        record = _validate_phase_record(value)
        if record is not None:
            accepted.append(record)
    return accepted


def _try_phase_advisory_lock(fd: int) -> bool:
    try:
        if os.name == "nt":
            import msvcrt
            if os.fstat(fd).st_size == 0:
                os.write(fd, b"\0")
                os.fsync(fd)
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except (OSError, ImportError):
        return False


def _acquire_phase_history_lock(directory: PhaseDirectory) -> Optional[int]:
    """Lock the pinned persistent lock-file fd with a bounded advisory wait."""
    names = _phase_file_names()
    if names is None:
        return None
    try:
        fd = _open_phase_child(directory, names[1], os.O_RDWR | os.O_CREAT, 0o600)
        if not _phase_regular_fd(fd):
            os.close(fd)
            return None
        _phase_restrict_fd(fd)
    except OSError:
        return None
    deadline = time.monotonic() + _PHASE_HISTORY_LOCK_WAIT_SECONDS
    while not _try_phase_advisory_lock(fd):
        if time.monotonic() >= deadline:
            os.close(fd)
            return None
        time.sleep(0.01)
    return fd


def _release_phase_history_lock(lock: Optional[int]) -> None:
    if lock is None:
        return
    try:
        if os.name == "nt":
            import msvcrt
            os.lseek(lock, 0, os.SEEK_SET)
            msvcrt.locking(lock, msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock, fcntl.LOCK_UN)
    except (OSError, ImportError):
        pass
    try:
        os.close(lock)
    except OSError:
        pass


def _phase_key_bytes(directory: PhaseDirectory, *, create: bool) -> Optional[bytes]:
    """Read or create the project-local HMAC key through the pinned `.sf` fd.

    The caller holds the phase-history lock. Links, non-owned files, hardlinks,
    wrong-sized values, and all I/O failures are rejected without replacement.
    """
    names = _phase_file_names()
    if names is None:
        return None
    fd = None
    try:
        try:
            fd = _open_phase_child(
                directory, names[2], os.O_RDONLY | getattr(os, "O_NONBLOCK", 0)
            )
        except FileNotFoundError:
            if not create:
                return None
            fd = _open_phase_child(
                directory, names[2], os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o600
            )
            _phase_restrict_fd(fd)
            if not _phase_private_fd(fd):
                return None
            key = secrets.token_bytes(32)
            view = memoryview(key)
            while view:
                written = os.write(fd, view)
                if written <= 0:
                    return None
                view = view[written:]
            os.fsync(fd)
            return key
        _phase_restrict_fd(fd)
        if not _phase_private_fd(fd):
            return None
        data = os.read(fd, 33)
        return data if len(data) == 32 else None
    except OSError:
        return None
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass


def _phase_org_digest(org_id: object, *, create: bool = False) -> Optional[str]:
    """HMAC one canonical org ID without exposing either input or digest."""
    normalized = _normalize_salesforce_org_id(org_id)
    if normalized is None:
        return None
    directory = _open_phase_directory(create)
    if directory is None:
        return None
    lock = _acquire_phase_history_lock(directory)
    if lock is None:
        _close_phase_directory(directory)
        return None
    try:
        key = _phase_key_bytes(directory, create=create)
        if key is None:
            return None
        return hmac.new(key, normalized.encode("ascii"), hashlib.sha256).hexdigest()
    finally:
        _release_phase_history_lock(lock)
        _close_phase_directory(directory)


def _encode_phase_record(record: dict) -> bytes:
    return (json.dumps(record, separators=(",", ":")) + "\n").encode("utf-8")


def _retained_phase_history(records: list[dict], mandatory: dict) -> Optional[bytes]:
    """Select priority evidence with bounded append headroom, in original order.

    Mandatory evidence and the newest passed Test/Deploy/Observe anchors may use
    the hard caps when necessary. Ordinary noise fills only soft caps, reserving a
    bounded slice for later appends so crossing a cap does not turn every subsequent
    event into a full replace/fsync cycle.
    """
    combined = [*records, mandatory]
    mandatory_index = len(combined) - 1
    encoded = [_encode_phase_record(record) for record in combined]
    mandatory_bytes = len(encoded[mandatory_index])
    if _PHASE_HISTORY_MAX_RECORDS < 1 or mandatory_bytes > _PHASE_HISTORY_MAX_FILE_BYTES:
        return None

    record_headroom = (
        min(64, max(1, _PHASE_HISTORY_MAX_RECORDS // 16))
        if _PHASE_HISTORY_MAX_RECORDS > 1 else 0
    )
    soft_record_cap = max(1, _PHASE_HISTORY_MAX_RECORDS - record_headroom)
    byte_headroom = (
        max(mandatory_bytes, min(64 * 1024, max(1, _PHASE_HISTORY_MAX_FILE_BYTES // 16)))
        if _PHASE_HISTORY_MAX_FILE_BYTES > mandatory_bytes else 0
    )
    soft_byte_cap = max(
        mandatory_bytes, _PHASE_HISTORY_MAX_FILE_BYTES - byte_headroom
    )

    selected = {mandatory_index}
    selected_bytes = mandatory_bytes

    anchors = []
    for stage in ("Test", "Deploy", "Observe"):
        for index in range(mandatory_index, -1, -1):
            record = combined[index]
            if record.get("stage") == stage and record.get("outcome") == "passed":
                anchors.append(index)
                break

    def retain(index: int, *, priority: bool = False) -> None:
        nonlocal selected_bytes
        record_cap = _PHASE_HISTORY_MAX_RECORDS if priority else soft_record_cap
        byte_cap = _PHASE_HISTORY_MAX_FILE_BYTES if priority else soft_byte_cap
        if index in selected or len(selected) >= record_cap:
            return
        size = len(encoded[index])
        if selected_bytes + size <= byte_cap:
            selected.add(index)
            selected_bytes += size

    # Anchors outrank headroom, since losing the newest passed stage proof would
    # regress the journey. Remaining records are newest-first and stop at soft caps.
    for index in sorted(anchors, reverse=True):
        retain(index, priority=True)
    for index in range(mandatory_index - 1, -1, -1):
        retain(index)

    return b"".join(encoded[index] for index in sorted(selected))


def _record_phase_event(
    stage: str,
    outcome: str,
    *,
    source: str,
    org_id: str = "",
    event_type: str = "phase-reached",
) -> bool:
    """Validate and durably retain one versioned milestone under the phase lock.

    The hot-path contract remains fail-silent: unsafe paths, invalid fields, lock
    timeout, and I/O errors return False without touching stdout.
    """
    record = {
        "schemaVersion": _PHASE_HISTORY_SCHEMA_VERSION,
        "type": event_type,
        "stage": stage,
        "outcome": outcome,
        "source": source,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    record = _validate_phase_record(record)
    if record is None:
        return False
    encoded = _encode_phase_record(record)
    if len(encoded.rstrip(b"\n")) > _PHASE_HISTORY_MAX_LINE_BYTES:
        return False

    names = _phase_file_names()
    directory = _open_phase_directory(True)
    if names is None or directory is None:
        return False
    lock = _acquire_phase_history_lock(directory)
    if lock is None:
        _close_phase_directory(directory)
        return False
    fd = None
    try:
        # Derive inside the same lock as the write so concurrent first writers
        # cannot mint different project keys. The canonical ID never enters `record`.
        if org_id:
            normalized = _normalize_salesforce_org_id(org_id)
            key = _phase_key_bytes(directory, create=True) if normalized else None
            if key is not None:
                record["orgHash"] = hmac.new(
                    key, normalized.encode("ascii"), hashlib.sha256
                ).hexdigest()
                record = _validate_phase_record(record)
                if record is None:
                    return False
                encoded = _encode_phase_record(record)
        if (len(encoded.rstrip(b"\n")) > _PHASE_HISTORY_MAX_LINE_BYTES
                or len(encoded) > _PHASE_HISTORY_MAX_FILE_BYTES
                or _PHASE_HISTORY_MAX_RECORDS < 1):
            return False

        try:
            fd = _open_phase_child(
                directory, names[0], os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_EXCL, 0o600
            )
        except FileExistsError:
            observed = _read_phase_preimage(directory)
            if observed is None:
                return False
            preimage, identity = observed
            result = _parse_phase_history_bytes(preimage)
            if (result.rejected or result.truncated
                    or (preimage and not preimage.endswith(b"\n"))):
                return False

            if (result.accepted + 1 <= _PHASE_HISTORY_MAX_RECORDS
                    and len(preimage) + len(encoded) <= _PHASE_HISTORY_MAX_FILE_BYTES):
                fd = _open_phase_child(directory, names[0], os.O_WRONLY | os.O_APPEND)
                if not _phase_regular_fd(fd) or _phase_identity(os.fstat(fd)) != identity:
                    return False
            else:
                retained = _retained_phase_history(result.records, record)
                if retained is None:
                    return False
                outcome = _replace_phase_history(directory, preimage, identity, retained)
                return outcome.status == _PHASE_REPLACE_SUCCESS

        if not _phase_regular_fd(fd):
            return False
        _phase_restrict_fd(fd)
        _write_all(fd, encoded)
        os.fsync(fd)
        return True
    except OSError:
        return False
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
        _release_phase_history_lock(lock)
        _close_phase_directory(directory)


def _record_attributed_phase_event(
    stage: str, outcome: str, *, source: str, event_type: str, org_id: Optional[str]
) -> bool:
    """Keep the legacy unattributed writer call shape when identity is unresolved."""
    kwargs = {"org_id": org_id} if org_id else {}
    return _record_phase_event(
        stage, outcome, source=source, event_type=event_type, **kwargs
    )


# The session id of the hook event currently being handled. Each hook invocation
# is its OWN short-lived process handling exactly one event for one session (the
# shim `exec`s python3 per call), so a module global set when the payload is parsed
# is unambiguous for that process's lifetime. It lets `_welcome_readiness` (the
# D9 connect cheap-check, and the readiness-paint banner) consult the per-session
# env-check marker without threading a session id through every signature. Empty on
# the non-hook Bash subcommand path (no payload), where readiness then reads
# conservatively as unverified.
_CURRENT_SESSION_ID = ""


def _read_hook_payload() -> dict:
    """Read and parse the hook's JSON stdin payload once, TTY/empty-guarded.

    Claude Code passes e.g. `{"source": "startup", "session_id": "…"}`. Returns
    `{}` when stdin is a TTY (a manual `sf-context detect` run) or empty/unparseable
    (the `--plugin-dir` test harness), so callers default to the full startup path.
    Stdin reads once, so callers that need both `source` and `session_id` go through
    this rather than re-reading. Side effect: stashes the payload's `session_id` in
    `_CURRENT_SESSION_ID` so the session-scoped readiness gate can read it without
    every intermediate caller having to thread it through.
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
    payload = payload if isinstance(payload, dict) else {}
    sid = payload.get("session_id") or payload.get("sessionId")
    if isinstance(sid, str) and sid:
        global _CURRENT_SESSION_ID
        _CURRENT_SESSION_ID = sid
    return payload


def _load_sf_telemetry():
    """Import the sibling sf_telemetry module, with the by-path fallback the rest
    of this file uses for its siblings. Returns the module, or None if it can't be
    loaded (telemetry is always optional — no caller fails because it's absent).

    The scripts dir is not on sys.path under importlib-based unit tests (and after
    a chdir into a project dir), so a bare `import` can miss; fall back to loading
    it by absolute path, the same shim cmd_features/cmd_discovery use."""
    try:
        import sf_telemetry
        return sf_telemetry
    except Exception:
        # Broad on purpose: telemetry is always optional, so ANY load failure — not
        # just ImportError, but a module-level SyntaxError/RuntimeError etc. — must
        # fall through to the by-path fallback (and ultimately None) rather than
        # propagate a traceback into a hook or the consent command.
        try:
            import importlib.util
            module_path = Path(__file__).resolve().parent / "sf_telemetry.py"
            spec = importlib.util.spec_from_file_location("sf_telemetry", module_path)
            if spec is None or spec.loader is None:
                return None
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
        except Exception:
            return None


def _telemetry_notice_lines() -> list:
    """The one-time telemetry notice as plain content lines (no rules), owned by
    detect so it renders as a band woven INTO the banner — below the logo lockup,
    above the org guidance. The telemetry SessionStart hook is record-only. Returns
    [] when not the first run, when opted out, in CI, or if the telemetry module is
    absent — detect never fails because of telemetry.

    NOTE: calling this marks the notice shown (fire-once gate lives in telemetry),
    so it must be called exactly once per detect, on the visible path only."""
    try:
        sf_telemetry = _load_sf_telemetry()
        if sf_telemetry is None:
            return []
        return sf_telemetry.first_run_notice_lines() or []
    except Exception:
        return []


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
        emit("SessionStart", SKILLS_FIRST_REINJECT)
        return 0

    if not Path("sfdx-project.json").exists():
        # Stay silent in non-Salesforce directories — the plugins are global, but
        # surfacing a banner everywhere would be noisy. The orientation rule is
        # agent-facing only, so it adds no visible noise here; the journey rail still
        # answers "where am I?" from durable global signals — a verified environment
        # and any connected org light the front stages even before a project exists.
        root = Path.cwd().resolve()
        state = _derive_journey_state(
            root, has_project=False, target="", target_error=None, org_display=None
        )
        emit(
            "SessionStart",
            _session_model_context(
                project=None, state=state,
                configured_org=(state.get("context") or {}).get("orgAlias") or "",
                displayed_org=(state.get("context") or {}).get("orgAlias") or "",
                project_present=False,
            ),
        )
        return 0

    # In a project → gather the banner and journey state before committing any
    # per-session suppression fact. A session that enters a project WITHOUT a
    # visible SessionStart here (for example `/cd` mid-session or ui_mode=off)
    # records neither, so its first visible ambient rail remains available.
    root = Path.cwd().resolve()
    # Project metadata and inventory are local facts. Git status is intentionally
    # left unprobed here because even a local `git` invocation is an external
    # subprocess; explicit project/status surfaces may still resolve it on demand.
    project = project_meta()
    ui_mode = _ui_mode()
    stats = project_stats() if ui_mode == "full" else None
    git_line = "git status unprobed"

    # SessionStart is local-first: read only project/user config. A configured
    # target earns Connect, but passive startup never claims live reachability,
    # edition, or API version. `/status` and the post-login wayfinder own those
    # live facts.
    target = _configured_target_alias(root) or ""

    # The one-time telemetry notice as plain lines ([] when not due / opted out /
    # in CI). Computed ONCE here — calling it marks it shown, so it must fire at
    # most once per detect — then woven as the FIRST band (below the logo lockup,
    # above the org guidance) into the visible banner below. It rides the visible
    # systemMessage only; the model-facing `context` is a separate structured
    # object (`_session_model_context`) and never carries the notice. Gated on the
    # full-banner path (stats is not None): compact/plain/off surfaces don't render
    # the banner, so the notice must not burn its fire-once flag there — it will
    # show on the next full-banner session instead.
    notice_lines = _telemetry_notice_lines() if stats is not None else []

    if not target:
        state = _derive_journey_state(root, has_project=True, target="",
                                      target_error=None, org_display=None)
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
        ], project=project, stats=stats, git_line=git_line, state=state,
           notice_lines=notice_lines) if stats is not None else ""
        context = _session_model_context(
            project=project, state=state, configured_org="", displayed_org="",
            project_present=True,
        )
    else:
        state = _derive_journey_state(
            root, has_project=True, target=target,
            target_error="unprobed", org_display=None,
        )
        msg = render_degraded_banner("Target Org Configured (Unprobed)", [
            f"Configured target: '{_sanitize_dynamic_text(target)}'.",
            "Reachability, edition, and API version are not probed at startup.",
            "Run /salesforce-development:status for live org status.",
            "",
            "Skills are available for local code generation.",
        ], project=project, stats=stats, git_line=git_line, state=state,
           notice_lines=notice_lines) if stats is not None else ""
        context = _session_model_context(
            project=project, state=state, configured_org=target,
            displayed_org=target, project_present=True,
        )

    visible = _ambient_surface(
        msg, state, project_name=project.get("name") or project.get("path") or "project"
    )
    emit(
        "SessionStart",
        context,
        system_message=visible,
        session_title=_session_title(payload, project),
    )
    if visible is not None:
        # Commit shown-state only after the output write returns. This suppresses
        # the next logo/ambient rail only when SessionStart actually displayed it.
        _record_welcomed(session_id)
        _record_entered(session_id)
        # Seed the step-signature so a routine post-login wayfinder can de-duplicate
        # an unchanged rail while still repainting after a genuine stage move.
        _record_rail_signature(session_id, state)
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
        print(f"Salesforce project detected, but org '{_sanitize_dynamic_text(target)}' is unreachable. Run 'sf org login web' to re-authenticate.")
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
        print(f"Org '{_sanitize_dynamic_text(target)}' is unreachable. Run: sf org login web")
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
# The scaffold chokepoint — creating a DX project. The front-of-journey readiness
# gate's PreToolUse backstop fires here (see cmd_scaffold_gate): if the visible
# welcome's steer-to-setup was bypassed, this is the last cheap place to catch a
# definitively-broken toolchain before a project is generated onto it.
_SCAFFOLD_COMMAND = re.compile(r"(?i)\bsf\s+project\s+generate\b")

# --- Observe / Test signal matchers (journey-rail reachability engine) -------
# Executed-command matchers for the phase-tracker writers (cmd_post_observe,
# cmd_post_test_run). Same self-gating rationale and `\s+`-tolerant style as the
# deploy matchers above — the writers gate on these so they stay silent if a
# Claude Code build ignores the plugin.json `if:` matcher and fires every hook.
# `sf apex run test` is asynchronous by default, so successful PostToolUse only
# proves submission. A synchronous pass is trusted only for a standalone simple
# command: shell composition can mask the `sf` exit code or merely mention the
# command as text. `--wait` alone is also inconclusive because it can return a run
# ID after timing out without the tests having completed.
_PHASE_EVIDENCE_SHELL_SYNTAX = frozenset(";&|<>\n\r\x00`()#$*?[]{}\\!~%^")
# Skills whose dispatch is a Tier-C activity signal for Observe — enough to move
# the cursor (◉) there, never to light the ● (only a fact/event does that). Real
# skill names, verified against skills/.
_OBSERVE_DISPATCH_SKILLS = frozenset({"platform-apex-logs-debug", "agentforce-observe"})


def _hook_command(payload: dict) -> str:
    """The executed Bash command from a PreToolUse/PostToolUse hook payload, or ""."""
    tool_input = payload.get("tool_input") or payload.get("toolInput") or {}
    return (tool_input.get("command") or "") if isinstance(tool_input, dict) else ""


def _hook_reports_failure(payload: object) -> bool:
    """Whether a PostToolUse payload AFFIRMATIVELY reports the tool failed.

    The supported host routes a failed tool call to the distinct PostToolUseFailure
    event, so a success payload normally carries no failure marker — but some builds
    fire every PostToolUse Bash hook regardless of exit status (the same misbehavior
    the deploy-family self-gates already defend against). A journey `passed` milestone
    must never be minted from a run that actually failed, so the success writers
    consult this before recording.

    Deliberately conservative: it returns True ONLY on an explicit failure signal in
    `tool_response` (non-zero exit, interrupted, or an error flag). An absent, opaque,
    or unrecognized response shape returns False so a genuine success — or an older
    host that omits the field — is never suppressed (journey evidence must not fail
    closed). The zero-exit case is likewise never flagged."""
    if not isinstance(payload, dict):
        return False
    response = payload.get("tool_response")
    if response is None:
        response = payload.get("toolResponse")
    if not isinstance(response, dict):
        return False
    if (response.get("interrupted") is True or response.get("is_error") is True
            or response.get("isError") is True):
        return True
    for key in ("exitCode", "exit_code", "returncode"):
        value = response.get(key)
        if isinstance(value, bool):
            continue  # a JSON bool is not an exit status
        if isinstance(value, int) and value != 0:
            return True
        if isinstance(value, str) and value.strip().lstrip("-").isdigit() and int(value) != 0:
            return True
    return False


def _standalone_argv(command: object) -> Optional[list[str]]:
    """Parse one simple literal command, rejecting shell composition/expansion."""
    if not isinstance(command, str) or not command.strip():
        return None
    if any(char in command for char in _PHASE_EVIDENCE_SHELL_SYNTAX):
        return None
    try:
        return shlex.split(command, comments=False, posix=True) or None
    except ValueError:
        return None


def _standalone_sf_argv(command: object) -> Optional[list[str]]:
    """Parse one simple literal `sf` command, rejecting every shell expansion seam."""
    argv = _standalone_argv(command)
    return argv if argv and argv[0] == "sf" else None


def _is_connect_command(command: object) -> bool:
    argv = _standalone_sf_argv(command)
    if argv is None:
        return False
    return (
        len(argv) >= 3 and argv[:3] == ["sf", "org", "login"]
    ) or (
        len(argv) >= 4 and argv[:3] == ["sf", "config", "set"]
        and (argv[3] == "target-org" or argv[3].startswith("target-org="))
    )


def _is_sf_context_command(command: object, *args: str) -> bool:
    if isinstance(command, str):
        for prefix in (
            '"${CLAUDE_PLUGIN_ROOT}"/scripts/sf-context',
            "${CLAUDE_PLUGIN_ROOT}/scripts/sf-context",
        ):
            if command.startswith(prefix):
                command = "sf-context" + command[len(prefix):]
                break
    argv = _standalone_argv(command)
    if argv is None or len(argv) != len(args) + 1:
        return False
    executable = Path(argv[0]).name.lower()
    if executable not in {"sf-context", "sf-context.py", "sf-context.cmd", "sf-context.exe"}:
        return False
    return argv[1:] == list(args)


# A dry-run / check-only deploy VALIDATES metadata without mutating the org, so it
# is not Deploy evidence. The existing carve-out drops `validate`/`preview`/`report`/
# `cancel` by SUB-COMMAND; these are the same intent expressed as a FLAG on `start`
# (`--dry-run` is the current form; `--checkonly`/`--check-only` are the legacy
# aliases). Match only the unambiguous long forms — never a short flag that a real
# deploy might reuse for another meaning.
_DEPLOY_DRY_RUN_FLAGS = {"--dry-run", "--checkonly", "--check-only"}


def _standalone_deploy_argv(command: object) -> Optional[list[str]]:
    argv = _standalone_sf_argv(command)
    if argv is None or len(argv) < 4:
        return None
    if argv[:3] != ["sf", "project", "deploy"] or argv[3] not in {"start", "quick", "resume"}:
        return None
    # Reject a validate-only run at this single choke point so neither the success
    # writer (cmd_post_deploy) nor the failure writer (cmd_post_deploy_failure) records
    # a Deploy milestone for it, and the post-bash dispatcher doesn't route it. The
    # deploy-failure ADVISORY still fires: it self-gates on the whole `sf project
    # deploy` family, not on this accepted argv.
    if any(arg in _DEPLOY_DRY_RUN_FLAGS for arg in argv[4:]):
        return None
    return argv


def _salesforce_id_suffix(value15: str) -> str:
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ012345"
    suffix = []
    for offset in range(0, 15, 5):
        bits = 0
        for bit, char in enumerate(value15[offset:offset + 5]):
            if char.isupper():
                bits |= 1 << bit
        suffix.append(alphabet[bits])
    return "".join(suffix)


def _normalize_salesforce_org_id(value: object) -> Optional[str]:
    """Return one canonical 18-character org ID, or None when it is not proven."""
    if not isinstance(value, str) or len(value) not in (15, 18):
        return None
    if not value.startswith("00D") or not value.isascii() or not value.isalnum():
        return None
    canonical = value[:15] + _salesforce_id_suffix(value[:15])
    if len(value) == 18 and value != canonical:
        return None
    return canonical


def _phase_target_value(value: object) -> Optional[str]:
    if not isinstance(value, str):
        return None
    value = value.strip()
    if (not value or value.startswith("-") or len(value) > 1024
            or any(ord(char) < 0x20 or ord(char) == 0x7f for char in value)):
        return None
    return value


def _effective_phase_target(argv: list[str]) -> Optional[str]:
    """Conservatively reproduce Oclif target selection for accepted standalone argv.

    The last supported explicit occurrence wins. Any malformed target occurrence is
    ambiguous and prevents fallback to the configured default.
    """
    explicit = False
    malformed = False
    selected = None
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg in ("--target-org", "-o"):
            explicit = True
            if index + 1 >= len(argv):
                malformed = True
            else:
                selected = _phase_target_value(argv[index + 1])
                malformed = malformed or selected is None
                index += 1
        elif arg.startswith("--target-org="):
            explicit = True
            selected = _phase_target_value(arg.split("=", 1)[1])
            malformed = malformed or selected is None
        elif arg.startswith("-o=") or (arg.startswith("-o") and arg != "-o"):
            explicit = True
            malformed = True
        index += 1
    if explicit:
        return None if malformed else selected
    return _phase_target_value(_configured_target_alias(Path.cwd().resolve()))


def _resolve_phase_org_id(argv: list[str]) -> Optional[str]:
    """Resolve a command's effective target to a stable ID with one bounded call."""
    target = _effective_phase_target(argv)
    if target is None:
        return None
    try:
        display = get_org_display(target)
    except Exception:
        return None
    if not isinstance(display, dict):
        return None
    return _normalize_salesforce_org_id(display.get("id") or display.get("orgId"))


def _standalone_observe_kind(command: object) -> Optional[str]:
    argv = _standalone_sf_argv(command)
    if argv is None:
        return None
    if len(argv) >= 4 and argv[:3] == ["sf", "apex", "tail"] and argv[3] == "log":
        return "strong"
    if len(argv) >= 4 and argv[:3] == ["sf", "apex", "get"] and argv[3] == "log":
        return "strong"
    if len(argv) >= 4 and argv[:3] == ["sf", "apex", "list"] and argv[3] == "log":
        return "strong"
    if len(argv) >= 3 and argv[:3] in (["sf", "org", "open"], ["sf", "data", "query"]):
        return "soft"
    return None


def _is_final_synchronous_apex_test(command: object) -> bool:
    """Whether PostToolUse success belongs to one standalone synchronous test run."""
    argv = _standalone_sf_argv(command)
    if argv is None or argv[:4] != ["sf", "apex", "run", "test"]:
        return False
    args = argv[4:]
    return "--synchronous" in args or "-y" in args


def _deploy_test_level(argv: list[str]) -> Optional[str]:
    """Return Oclif's effective value: the last occurrence wins."""
    level = None
    for index, arg in enumerate(argv[4:], start=4):
        if arg == "--test-level":
            level = argv[index + 1] if index + 1 < len(argv) else None
        elif arg.startswith("--test-level="):
            level = arg.split("=", 1)[1]
    return level


def cmd_wayfinder(payload: Optional[dict] = None) -> int:
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
        if payload is None:
            payload = _read_hook_payload()
        if not _is_connect_command(_hook_command(payload)):
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
        )
        session_id = payload.get("session_id") or payload.get("sessionId") or ""
        prompt_context = _prompt_context(payload, rotate_fallback=False)
        # Reprint only when this project's step signature moved. A concurrent painter
        # may still own this prompt's one rail; the connected-org header always emits.
        rail_moved = _rail_signature(state) != _last_rail_signature(session_id)
        msg = render_wayfinder_message(org, project, stats, git_line, mcp_status, color,
                                       state=state, include_rail=rail_moved)
        ambient = _ambient_surface(
            msg, state, project_name=project.get("name") or root.name
        )
        without_rail = None
        if rail_moved:
            without_rail = _ambient_surface(
                render_wayfinder_message(
                    org, project, stats, git_line, mcp_status, color,
                    state=state, include_rail=False,
                ),
                state,
                project_name=project.get("name") or root.name,
            )
        model_note = (
            f"Target org is now '{_sanitize_dynamic_text(org.get('alias') or target)}' "
            f"({_sanitize_dynamic_text(org.get('edition') or 'unknown')}, "
            f"API v{_sanitize_dynamic_text(org.get('apiVersion') or '?')}). "
            "Update the working assumption accordingly."
        )
        if ambient is None:
            # ui_mode=off hides this ambient surface. Preserve the semantic org
            # update, but do not claim or record a rail that was never displayed.
            emit("PostToolUse", model_note)
            return 0
        # Claim after every render and immediately before emit. Missing state fails
        # open to a duplicate rail; an existing claim uses the pre-rendered header.
        if rail_moved and prompt_context is not None and not _claim_prompt_rail(prompt_context):
            rail_moved = False
            ambient = without_rail
        emit("PostToolUse", model_note, system_message=ambient)
        if rail_moved:
            _record_rail_signature(session_id, state)
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
    # CLI is installed but out of date — a 🟡 warning, not 🟢. Uses the
    # no-network _detect_update_notice helper, which reads the cached warning from
    # `sf version` stderr. Honors the hard update-check opt-out
    # (SFDX_SKIP_CLI_UPDATE_CHECK=1) so a user who disabled update checks never
    # sees this warn. Legacy record-update-decision state is not consulted — an
    # explicit readiness scan reports the factual state each time.
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

    # Cache a coarse readiness verdict for the front-of-journey gate. This is the
    # chokepoint both entry points hit (/salesforce-development:setup and the
    # platform-environment-validate skill), so the verdict is written no matter
    # how the scan was triggered.
    #
    # "Safe to scaffold" is deliberately NOT "all green". Two lists:
    #   - `blockers` — CRITICAL rows only: a genuinely broken/missing prerequisite
    #     that would make `sf project generate` (or the build/deploy it leads to)
    #     actually fail. This is the readiness FLOOR the scaffold gate enforces.
    #   - `needs_attention` — critical + warn: the honest "not green" list the
    #     banner speaks to. A 🟡 warn (a non-LTS Node, an org-scoped source-tracking
    #     note, an outdated-but-working CLI) is ADVISORY — worth surfacing, but it
    #     builds and deploys fine, so it must NEVER block scaffolding.
    # `ready` is "no blockers", so warnings are shown but never gate (informational
    # rows — e.g. the MCP process row — count as neither). This matches the gate's
    # own rule: block only when we can prove the environment broken, never merely
    # imperfect. Fail-silent: a write failure never disrupts the report.
    blockers = [r.get("name") for r in results if r.get("status") == "critical"]
    needs_attention = [r.get("name") for r in results if r.get("status") in ("critical", "warn")]
    _record_readiness_verdict(
        ready=not blockers,
        needs_attention=needs_attention,
        blockers=blockers,
        signature=_toolchain_signature(),
    )
    # Persist the full report too — the readiness-paint PostToolUse hook renders the
    # deterministic Tier-1 banner from it (it cannot see this stdout). Fail-silent.
    _record_readiness_report(output)

    print(json.dumps(output))
    return 0


# --- Readiness banner: the deterministic Tier-1 render -----------------------
# The framed "Ready to build on Salesforce?" banner is a pinned signature visual,
# like the SessionStart logo and the journey rail — so the plugin paints it
# deterministically rather than asking the model to hand-render it from the
# check-tools JSON (the old Tier-2 path, where the model did fragile width/count
# arithmetic every run). "Principles, not pixels": the per-tool status and the
# footer counts are the hard facts and come straight from the report. Status dots
# remain useful visual signals, while explicit READY/WARN/BLOCKED/INFO words make
# the same state available without color or glyph knowledge. The TABLE needs no ANSI
# color plumbing and survives NO_COLOR / strip_ansi; only the wayfinding footer opts
# into color on the visible paint path (the ✳ New here? cyan link, matching the
# welcome), and NO_COLOR forces even that plain.
_READINESS_WIDTH = 80
_READINESS_RULE = "─" * _READINESS_WIDTH
_READINESS_HEADER = " Ready to build on Salesforce?   checking your toolchain…"
_READINESS_SKILL_TAG = "(skill: platform-environment-validate)"
_READINESS_DOTS = {"ok": "🟢", "warn": "🟡", "critical": "🔴", "info": "ℹ️"}
_READINESS_WORDS = {"ok": "READY", "warn": "WARN", "critical": "BLOCKED", "info": "INFO"}
# Left-pad names to the longest ("Salesforce MCP (endpoint)" = 25) plus a 2-space
# gap so the value column lines up.
_READINESS_NAME_WIDTH = 27
# Rows that go 🟡/🔴 only because no org is connected yet — they are not a tool to
# install, so they steer the wayfinding Next line to "connect an org", not "fix all".
_READINESS_ORG_ROWS = {"Salesforce MCP (endpoint)", "Source Tracking"}


def _readiness_row_value(row: dict) -> str:
    """Return the sanitized value without rephrasing remediation text.

    A green row with a version keeps the compact version display. All versionless
    rows and every attention/info row retain their full message for cell wrapping.
    """
    status = _sanitize_dynamic_text(row.get("status") or "")
    version = _sanitize_dynamic_text(row.get("version") or "").strip()
    message = _sanitize_dynamic_text(row.get("message") or "").strip()
    if status == "ok" and version:
        if version.lower().startswith("git version "):
            version = version[len("git version "):].strip()
        return version
    return message or version


def _wrap_cells(value: object, width: int) -> list[str]:
    """Wrap sanitized text at spaces/cell boundaries without splitting clusters."""
    text = _sanitize_dynamic_text(value).strip()
    if not text:
        return [""]
    lines: list[str] = []
    while _terminal_cell_width(text) > width:
        clusters = list(_grapheme_clusters(text))
        used = 0
        cut = 0
        space_cut = 0
        for index, (cluster, cells) in enumerate(clusters):
            if used + cells > width:
                break
            used += cells
            cut = index + 1
            if cluster.isspace():
                space_cut = cut
        if cut == 0:  # Defensive only: width is positive on all callers.
            cut = 1
        split = space_cut or cut
        lines.append("".join(cluster for cluster, _ in clusters[:split]).rstrip())
        text = "".join(cluster for cluster, _ in clusters[split:]).lstrip()
    lines.append(text)
    return lines


def _readiness_row_lines(row: dict) -> list[str]:
    """One line per tool — dot + explicit status word + name + the detail value at its
    natural width, NEVER wrapped (owner direction 2026-08-05).

    Wrapping a long detail to fit the 80-col frame turned one tool into 2–3 physical
    lines, which pushed each following status dot down and left vertical GAPS between
    the dots. Keeping every tool on a single line holds the dots evenly spaced; a detail
    longer than the terminal simply soft-wraps at the edge (the pre-hardening behavior,
    which read better in a normal wide terminal). Status stays legible without color via
    the READY/WARN/BLOCKED/INFO word, so this detail column is the one place intentionally
    exempt from the ≤80 frame. Still returns a list (one element) for its callers —
    `render_readiness_text` extends with it and `_readiness_row_line` takes [0]."""
    status = _sanitize_dynamic_text(row.get("status") or "info")
    if status not in _READINESS_WORDS:
        status = "info"
    dot = _READINESS_DOTS[status]
    word = _READINESS_WORDS[status]
    name = _sanitize_dynamic_text(row.get("name") or "")
    if name.endswith(" plugin"):  # "Code Analyzer plugin" → "Code Analyzer"
        name = name[: -len(" plugin")]
    marker = _pad_cells(f"{dot} {word}", 11)
    prefix = f" {marker}{_pad_cells(name, _READINESS_NAME_WIDTH)}"
    return [(prefix + _readiness_row_value(row)).rstrip()]


def _readiness_row_line(row: dict) -> str:
    """Compatibility seam returning the single rendered row line."""
    return _readiness_row_lines(row)[0]


def _readiness_footer_line(rows: list) -> str:
    """The closing verdict line. All green (no 🔴/🟡) → " ✓ toolchain ready";
    otherwise " ⚠ <N> need attention · <M> ready", plus " · <K> note" when any ℹ️
    rows exist. The owning-skill tag is right-aligned to the frame width."""
    need = sum(1 for r in rows if r.get("status") in ("critical", "warn"))
    ready = sum(1 for r in rows if r.get("status") == "ok")
    notes = sum(1 for r in rows if r.get("status") == "info")
    if need == 0:
        verdict = " ✓ toolchain ready"
    else:
        verdict = f" ⚠ {need} need attention · {ready} ready"
        if notes:
            verdict += f" · {notes} note"
    pad = _READINESS_WIDTH - _terminal_cell_width(verdict) - _terminal_cell_width(_READINESS_SKILL_TAG)
    return verdict + (" " * pad if pad >= 2 else "  ") + _READINESS_SKILL_TAG


def _readiness_next_line(rows: list) -> str:
    """The readiness banner's dynamic "Next:" step, chosen from the scan: a tool needing
    install/update wins ("fix all"); else only the org-dependent rows need attention
    ("connect an org"); else all green ("start building")."""
    attention = [r for r in rows if r.get("status") in ("critical", "warn")]
    tool_attention = [r for r in attention if r.get("name") not in _READINESS_ORG_ROWS]
    if not attention:
        return 'Next: start building → "create a Salesforce project"'
    if tool_attention:
        return 'Next: get build-ready → say "fix all"'
    return 'Next: connect an org → "connect an org"'


def _readiness_wayfinding_footer(rows: list, *, color: bool = False) -> str:
    """The three-line footer that closes the readiness output: the shared wayfinding
    footer (`_wayfinding_footer`) with the readiness-specific "Next:" step passed in as
    its dynamic tail.

    `color` defaults False so the goldens and any plain caller are unchanged, but the
    visible paint path opts in (color=_banner_color_enabled()): the ✳ New here? pointer
    then renders as the same cyan link as the SessionStart/welcome invitation (owner
    direction 2026-08-05), instead of reading as a lesser, all-gray footer. The banner's
    TABLE still carries status in content codepoints (🟢🟡🔴 / ℹ️ + READY/WARN words),
    never ANSI — only this footer takes color — and NO_COLOR forces the whole thing plain."""
    return "\n".join(_wayfinding_footer(_readiness_next_line(rows), color=color))


def render_readiness_text(report: dict, *, color: bool = False) -> str:
    """The framed toolchain-readiness banner as a string — the deterministic Tier-1
    sibling of what the platform-environment-validate skill used to hand-render.

    Input is the check-tools report ({"tools": [...], "diagnostic": {...}?}). Rows
    render in the report's fixed order (Salesforce CLI, Code Analyzer, Node.js, NPM,
    Git, the three Salesforce MCP rows, Source Tracking); a row is omitted only if
    the report omits it. Never raises on a well-formed report — and the paint hook
    wraps it fail-open regardless. The diagnostic block is intentionally NOT drawn
    here: it stays model-facing (the model surfaces it in prose), keeping the paint
    to the pinned signature visual.

    `color` defaults False — the table carries status in emoji dots + READY/WARN words
    (no ANSI), so every golden reads the plain string with no strip_ansi. Only the
    visible paint path passes color=_banner_color_enabled(), which colors ONLY the
    wayfinding footer (the ✳ New here? pointer as a cyan link), matching the
    welcome/SessionStart invitation; NO_COLOR still forces it fully plain."""
    rows = [r for r in (report.get("tools") or []) if isinstance(r, dict)]
    lines = [_READINESS_RULE, _READINESS_HEADER, _READINESS_RULE]
    for row in rows:
        lines.extend(_readiness_row_lines(row))
    lines += [_READINESS_RULE, _readiness_footer_line(rows), "",
              _readiness_wayfinding_footer(rows, color=color)]
    return "\n".join(lines)


def cmd_readiness_banner() -> int:
    """Print the deterministic readiness banner to stdout — the fallback the
    platform-environment-validate skill invokes when the PostToolUse paint hook did
    NOT fire (an older Claude Code build, or a paint fallback), so the skill never
    hand-renders the banner from the check-tools JSON. Row order, status words, the
    footer verdict, and the wayfinding Next step are all decided once, here, by the
    same render_readiness_text the paint hook uses — reading the same persisted report
    check-tools just wrote in this cwd (never re-running the scan).

    Prints plain (color=False), matching the model-reproducible stdout discipline of
    the other command surfaces. Fail-open like the paint hook: on any error, or when
    no report has been recorded yet, it prints a one-line pointer to stderr and returns
    2 — the check-tools JSON stays the authoritative, machine-readable result."""
    try:
        report = _load_readiness_report()
        tools = report.get("tools")
        if not isinstance(tools, list) or not tools:
            raise ValueError("no persisted readiness report")
        print(render_readiness_text(report, color=False))
        return 0
    except Exception:
        print("Readiness banner unavailable — run `sf-context check-tools` first.", file=sys.stderr)
        return 2


# Self-gate: fire the paint only when the executed Bash command was the check-tools
# scan. The plugin.json PostToolUse Bash hook carries no `if:` (some Claude Code
# builds ignore it and fire every Bash hook on every command), so — like wayfinder
# — the gate lives here, or the banner would repaint after an unrelated `cd`/grep.
_READINESS_SCAN_COMMAND = re.compile(r"sf-context\S*\s+check-tools\b")


def _readiness_paint_note() -> str:
    """Model-facing note when the readiness banner paints on the visible channel.

    Like the overview and the SessionStart banner, this is a Tier-1 surface the
    plugin displays directly — so the model must NOT reproduce it. It adds only its
    read and then proceeds to Phase 2 (install/update) from the JSON it already has."""
    return (
        "The Salesforce toolchain readiness banner (the framed \"Ready to build on Salesforce?\" "
        "block — one status row per tool, the footer verdict, and the wayfinding footer) has just "
        "been displayed to the user on the visible channel. It is already shown — do NOT reproduce, "
        "redraw, or re-render it from the check-tools JSON. Add only your own short read, then "
        "continue with Phase 2 (install/update) using the JSON report; if it carries a `diagnostic` "
        "block, surface it. Never re-run a failed check a different way and present a 🔴/🟡 tool as "
        "🟢 — a failed check stays failed until that same check-tools check passes."
    )


def _render_readiness_paint() -> Optional[str]:
    """Render the readiness banner for the paint hook from the persisted report, or
    None on any failure (no report yet, corrupt file, empty tools, or a render
    error). None makes the hook stay silent, so the model falls back to hand-
    rendering the banner from the check-tools JSON per the skill — today's behavior."""
    try:
        report = _load_readiness_report()
        tools = report.get("tools")
        if not isinstance(tools, list) or not tools:
            return None
        # Visible systemMessage paint: color the ✳ New here? footer (cyan link) to
        # match the welcome/SessionStart invitation. Honors NO_COLOR via the gate.
        return render_readiness_text(report, color=_banner_color_enabled())
    except Exception:
        return None


def cmd_readiness_paint(payload: Optional[dict] = None) -> int:
    """PostToolUse Bash hook: after a `check-tools` scan, paint the deterministic
    readiness banner on the visible systemMessage channel and hand the model a
    plain "already shown — add only your read" note.

    Self-gates on the command (see _READINESS_SCAN_COMMAND). Fail-open: any error,
    or a report that can't be rendered, degrades to a silent {"continue": true} —
    the model then hand-renders the banner from the JSON, so no failure is ever
    surfaced on the user's turn and the scan's own output is untouched."""
    try:
        if payload is None:
            payload = _read_hook_payload()
        if not _is_sf_context_command(_hook_command(payload), "check-tools"):
            print(json.dumps({"continue": True}))
            return 0
        # A passing scan THIS session lights Setup: record the session-scoped marker
        # so the front-of-journey readiness gate treats the toolchain as verified for
        # the rest of this session (and re-verifies next session — readiness is a
        # current property). Read back the coarse verdict check-tools just wrote in
        # this same cwd; a not-ready scan records nothing, so the cursor honestly
        # stays at Setup. Fail-silent — never disrupts the paint.
        if _load_readiness_state().get("ready"):
            _record_env_verified(payload.get("session_id") or payload.get("sessionId") or "")
        block = _render_readiness_paint()
        if block is not None:
            emit("PostToolUse", _readiness_paint_note(), system_message="\n" + block)
        else:
            print(json.dumps({"continue": True}))
        return 0
    except Exception:
        print(json.dumps({"continue": True}))
        return 0


# The journey-rail paint after the MODEL runs `sf-context discovery journey` (Lever
# C). The on-demand rail otherwise reaches the user only by the model reproducing the
# command's stdout — which is plain (cmd_journey strips ANSI), so color never
# survives. This PostToolUse Bash hook paints the SAME rail in color on the visible
# systemMessage channel (like the UserPromptSubmit orientation paint and the
# wayfinder), so a FUZZY orientation question the UserPromptSubmit regex missed — but
# the model recognized (per ORIENTATION_DIRECTIVE) and answered by running the
# command — still gets the colored rail, not a colorless reproduction. Excludes the
# `--json` form (a machine read for the model's own reasoning, not a request to show
# the user a rail). Self-gates on the command like readiness-paint/wayfinder, because
# not every Claude Code build honors the plugin.json `if:` matcher.
_JOURNEY_PAINT_COMMAND = re.compile(r"sf-context\S*\s+discovery\s+journey\b(?!\s+--json)")


def cmd_journey_paint(payload: Optional[dict] = None) -> int:
    """PostToolUse Bash hook: after the model runs `sf-context discovery journey`,
    paint the colored six-stage rail on the visible systemMessage channel and hand the
    model the same "already shown — add only your read" note the UserPromptSubmit
    orientation paint uses.

    De-dupes against the SAME turn's UserPromptSubmit paint via the turn-scoped ledger
    — if a rail already painted this turn (the regex-hit fast path, Lever A), this
    stays silent, so at most one rail paints per turn. Requires a session id: a paint
    we cannot de-dupe (no id) stays silent rather than risk a double, so the model
    falls back to reproducing the plain rail (today's behavior). Fail-open: any error
    degrades to a silent {"continue": true}, so a crash never disrupts the turn."""
    try:
        if payload is None:
            payload = _read_hook_payload()
        if not _is_sf_context_command(_hook_command(payload), "discovery", "journey"):
            print(json.dumps({"continue": True}))
            return 0
        session_id = payload.get("session_id") or payload.get("sessionId") or ""
        prompt_context = _prompt_context(payload, rotate_fallback=False)
        if prompt_context is None:
            # No trustworthy turn key: leave the command's plain output for the model
            # rather than claiming the visible rail was shown or suppressing its reply.
            print(json.dumps({"continue": True}))
            return 0
        if _rail_painted_this_turn(prompt_context):
            print(json.dumps({"continue": True}))
            return 0
        state = _journey_state()
        surface = "\n" + _render_journey_rail(state, color=_banner_color_enabled())
        if not _claim_prompt_rail(prompt_context):
            print(json.dumps({"continue": True}))
            return 0
        emit("PostToolUse", _orientation_paint_note(state), system_message=surface)
        _record_rail_signature(session_id, state)
        return 0
    except Exception:
        print(json.dumps({"continue": True}))
        return 0


def cmd_post_deploy(payload: Optional[dict] = None) -> int:
    # Self-gate on the command: advise only after a deploy actually MUTATED the org
    # (start/quick/resume). Two failure modes this guards: some Claude Code builds
    # ignore the plugin.json `if:` matcher and fire every PostToolUse Bash hook on
    # every command (so `cd`/grep must stay silent); and even a real
    # `sf project deploy validate`/`preview`/`report`/`cancel` deploys NOTHING, so
    # "Deployment complete" there is a false signal the model might act on — e.g.
    # concluding metadata is live and skipping the real deploy after a validate.
    if payload is None:
        payload = _read_hook_payload()
    cmd = _hook_command(payload)
    deploy_argv = _standalone_deploy_argv(cmd)
    if deploy_argv is None or _hook_reports_failure(payload):
        # Non-mutating/validate-only (rejected by _standalone_deploy_argv) or a deploy
        # the host affirmatively reported as failed: not a Deploy milestone, and
        # "Deployment complete." would be a false signal — stay silent.
        print(json.dumps({"continue": True}))
        return 0
    # Resolve exactly the target this accepted argv used. Resolution failure never
    # loses the project-global milestone; it only leaves this event unattributed.
    org_id = _resolve_phase_org_id(deploy_argv)
    _record_attributed_phase_event(
        "Deploy", "passed", source="cmd_post_deploy", org_id=org_id,
        event_type="deploy")
    # A successful deploy carrying a real --test-level (anything but NoTestRun) ran
    # the org's Apex tests and they passed — the deploy would have failed otherwise —
    # so it's also a Tier-B Test signal, free to capture since the hook already has
    # the command string.
    level = _deploy_test_level(deploy_argv)
    if level and level.lower() != "notestrun":
        _record_attributed_phase_event(
            "Test", "passed", source="cmd_post_deploy", org_id=org_id,
            event_type="test-run")
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

    # Persist a mutating-deploy FAILURE to the durable tracker, using the SAME
    # command scope as cmd_post_deploy's success path (start/quick/resume) so the
    # two writers agree on what a "deploy" is. outcome "failed" keeps Deploy's `●`
    # dark (a failed deploy did not reach the org) while letting the micro tier read
    # the attempt. The advisory below still fires on the whole deploy family.
    # Fail-silent, append-only.
    deploy_argv = _standalone_deploy_argv(cmd)
    if deploy_argv is not None:
        org_id = _resolve_phase_org_id(deploy_argv)
        _record_attributed_phase_event(
            "Deploy", "failed", source="cmd_post_deploy_failure", org_id=org_id,
            event_type="deploy")

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


# --- Observe / Test signal writers (journey-rail reachability engine) --------
# New PostToolUse Bash hooks that persist Observe and Test milestones to the
# durable phase tracker. They only RECORD — no user-visible or model-facing emit —
# so the rail surfaces the signal on the next paint. Advisory-only, fail-open.

def _has_prior_deploy_success(org_hash: Optional[str] = None) -> bool:
    """Whether a proven successful Deploy exists for this exact org digest."""
    if not org_hash:
        return False
    return any(
        rec.get("stage") == "Deploy"
        and rec.get("outcome") == "passed"
        and isinstance(rec.get("orgHash"), str)
        and hmac.compare_digest(rec["orgHash"], org_hash)
        for rec in _load_phase_history_result().records
    )


def cmd_post_observe(payload: Optional[dict] = None) -> int:
    """PostToolUse Bash hook after an observability command: record an Observe
    milestone. Two signal strengths:
      - `sf apex tail|get|list log` — reading the org's debug logs IS observing,
        the strongest single Observe signal; records Observe/passed outright.
      - `sf org open` / `sf data query` — softer; recorded ONLY when a prior
        successful deploy is already on record (the ordering guard above), else
        skipped as a high-false-positive "poke around the org".

    Self-gates on the command; fail-open; never blocks and never emits."""
    if payload is None:
        payload = _read_hook_payload()
    cmd = _hook_command(payload)
    # A command the host reported as failed did not observe the org — drop it so
    # neither the strong nor the soft branch records an Observe milestone.
    observe_kind = None if _hook_reports_failure(payload) else _standalone_observe_kind(cmd)
    argv = _standalone_sf_argv(cmd) if observe_kind else None
    org_id = _resolve_phase_org_id(argv) if argv is not None else None
    if observe_kind == "strong":
        _record_attributed_phase_event(
            "Observe", "passed", source="cmd_post_observe", org_id=org_id,
            event_type="observe")
    elif observe_kind == "soft":
        org_hash = _phase_org_digest(org_id, create=False) if org_id else None
        if org_hash and _has_prior_deploy_success(org_hash):
            _record_attributed_phase_event(
                "Observe", "passed", source="cmd_post_observe", org_id=org_id,
                event_type="observe")
    print(json.dumps({"continue": True}))
    return 0


def cmd_post_test_run(payload: Optional[dict] = None) -> int:
    """PostToolUse Bash hook after a final synchronous `sf apex run test` result:
    record Test/passed (Tier-B, the strongest Test signal). Default and `--wait`
    runs can return successfully with only an asynchronous run ID, so they do not
    earn journey evidence. Self-gates on the command; fail-open; never emits."""
    if payload is None:
        payload = _read_hook_payload()
    command = _hook_command(payload)
    if _is_final_synchronous_apex_test(command) and not _hook_reports_failure(payload):
        argv = _standalone_sf_argv(command)
        org_id = _resolve_phase_org_id(argv) if argv is not None else None
        _record_attributed_phase_event(
            "Test", "passed", source="cmd_post_test_run", org_id=org_id,
            event_type="test-run")
    print(json.dumps({"continue": True}))
    return 0


def cmd_post_bash() -> int:
    """Dispatch one successful Bash payload to at most one existing handler.

    The dispatcher owns stdin so the selected handler receives the already-parsed
    payload. Precedence keeps the visible paint routes ahead of standalone journey
    evidence writers; an unknown or malformed payload is a silent allow.
    """
    payload = _read_hook_payload()
    command = _hook_command(payload)
    # Usage telemetry for a successful Bash runs in-process here, not as a second
    # PostToolUse Bash hook: this block is a single dispatcher precisely so the
    # coordinated paints can't race for stdin/stdout by hook order, and telemetry
    # must ride that same guarantee. capture_event is print-free and fail-silent —
    # it writes the local buffer only and never touches stdout — so it composes
    # with whichever visible handler the dispatch below selects (or the silent
    # allow). Consent-gating and scrubbing live inside capture_event.
    try:
        sf_telemetry = _load_sf_telemetry()
        if sf_telemetry is not None:
            # Mirror the sibling success-writers (cmd_post_deploy/observe/apex-test):
            # some builds fire PostToolUse:Bash regardless of exit status, so consult
            # _hook_reports_failure rather than assuming success — a failed first-party
            # plugin command must be recorded as "failure", not logged as a success.
            outcome = "failure" if _hook_reports_failure(payload) else "success"
            sf_telemetry.capture_event("command_invoked", outcome, payload)
    except Exception:
        pass  # telemetry must never break the post-bash dispatch
    if _is_sf_context_command(command, "check-tools"):
        return cmd_readiness_paint(payload=payload)
    if _is_connect_command(command):
        return cmd_wayfinder(payload=payload)
    if _is_sf_context_command(command, "discovery", "journey"):
        return cmd_journey_paint(payload=payload)
    if _standalone_deploy_argv(command) is not None:
        return cmd_post_deploy(payload=payload)
    if _is_final_synchronous_apex_test(command):
        return cmd_post_test_run(payload=payload)
    if _standalone_observe_kind(command) is not None:
        return cmd_post_observe(payload=payload)
    print(json.dumps({"continue": True}))
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


# Enforcement allow-list: only these skills are BLOCKED (deny + redirect). Each
# owns a 1:1 bypass-prone `sf` op, so a deny is always satisfiable by dispatching
# it. Everything else `_skills_first_match` returns stays warn-only, so a hard
# deny can never name a nonexistent skill or block a step with no single owner.
_ENFORCEABLE_SKILLS = frozenset({
    "platform-soql-query",
    "platform-metadata-retrieve",
    "platform-apex-test-run",
    "platform-manifest-generate",
})

# Map an enforced skill to sibling skills whose in-turn dispatch ALSO satisfies
# its deny (the owning skill itself always does; these are added). platform-soql-query
# delegates query EXECUTION to platform-data-manage, so a turn where the delegate
# dispatched is just as validated — its `sf data query` must flow through, not re-deny.
_DISPATCH_DELEGATES = {
    "platform-soql-query": frozenset({"platform-data-manage"}),
}


def _skills_first_match(tool_name: str, tool_input: dict) -> Optional[tuple[str, str]]:
    """Return (skill_hint, advice) for a bypass-prone op, or None to stay silent."""
    if tool_name in ("Edit", "Write", "MultiEdit"):
        # Normalize Windows `\` to `/` so basename/segment checks are OS-independent.
        path = (
            tool_input.get("file_path") or tool_input.get("filePath") or ""
        ).replace("\\", "/").lower()
        if not path:
            return None
        # Hand-authoring a deploy manifest is the non-CLI bypass of
        # platform-manifest-generate. Scope to Write/MultiEdit (a small in-place
        # Edit isn't authoring), and detect either by name or by content, so a
        # non-standard filename (`pkg.xml`, a heredoc target) can't slip past.
        if tool_name in ("Write", "MultiEdit"):
            name = path.rsplit("/", 1)[-1]
            is_manifest_name = name == "package.xml" or (
                name.startswith("destructivechanges")
                and name.endswith(".xml")
                # match only the real files, not prose like `destructivechanges-notes.xml`
                and name in (
                    "destructivechanges.xml",
                    "destructivechangespre.xml",
                    "destructivechangespost.xml",
                )
            )
            # MultiEdit carries its text in `edits: [{old_string, new_string}]`,
            # not a top-level `content`/`new_string`, so pull the edit bodies too —
            # otherwise content detection never fires for MultiEdit and a
            # non-standard manifest filename slips through (F4 gap).
            edits = tool_input.get("edits")
            edit_bodies = (
                " ".join(
                    e.get("new_string") or e.get("new_str") or ""
                    for e in edits
                    if isinstance(e, dict)
                )
                if isinstance(edits, list)
                else ""
            )
            body = (
                tool_input.get("content")
                or tool_input.get("new_string")
                or tool_input.get("new_str")
                or edit_bodies
                or ""
            )
            is_manifest_body = (
                path.endswith(".xml")
                and "<package" in body.lower()
                and "soap.sforce.com/2006/04/metadata" in body.lower()
            )
            if is_manifest_name or is_manifest_body:
                return ("platform-manifest-generate", "authoring a deploy manifest directly")
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
        raw = tool_input.get("command", "") or ""
        # Normalize surface variants onto the modern space-separated `sf` form the
        # rules below expect: collapse whitespace runs, and fold the legacy `sfdx`
        # binary and colon-style topics (`sfdx force:data:soql:query`, `sf data:query`).
        norm = re.sub(r"\s+", " ", raw.lower())
        norm = re.sub(r"\bsfdx\b", "sf", norm)
        norm = norm.replace("force:", "").replace(":", " ")
        # Fold old topic verbs onto modern nouns (`sf data soql query` → `sf data query`).
        norm = norm.replace("sf data soql query", "sf data query")
        norm = norm.replace("sf apex test run", "sf apex run test")
        # Order matters: most specific sub-commands first.
        rules = [
            ("sf apex run test", "platform-apex-test-run", "running Apex tests via raw CLI"),
            ("sf apex run", "platform-apex-anonymous-run", "running anonymous Apex via raw CLI"),
            ("sf project retrieve", "platform-metadata-retrieve", "retrieving org metadata via raw CLI"),
            ("sf project generate manifest", "platform-manifest-generate",
             "generating a package.xml manifest via raw CLI"),
            ("sf data query", "platform-soql-query", "querying org data via raw CLI"),
        ]
        for needle, skill, why in rules:
            if needle in norm:
                return (skill, why)
        return None

    return None


def cmd_skills_first_advisory() -> int:
    """PreToolUse skills-first check: route bypass-prone ops to the owning skill.

    Reads the tool payload from stdin (Claude Code passes `{tool_name,
    tool_input}` JSON), the same channel sf-deploy-gate uses.

    A bypass-prone op whose owning skill is on the `_ENFORCEABLE_SKILLS`
    allow-list is BLOCKED with a `deny` + redirect to that skill. Every other
    match — the generic metadata fallback and Apex/declarative authoring nudges —
    is WARN-ONLY (emits `continue: true`), so a deny can never point at a skill
    that does not exist or block a step with no single owning skill.
    """
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except (json.JSONDecodeError, ValueError):
        payload = {}
    # Well-formed non-object JSON (`[]`, `"x"`, `42`) has no `.get`; since this is a
    # BLOCKING hook, an AttributeError would crash the tool call. Treat it as empty.
    if not isinstance(payload, dict):
        payload = {}
    tool_name = payload.get("tool_name", "") or payload.get("toolName", "")
    tool_input = payload.get("tool_input", {}) or payload.get("toolInput", {}) or {}
    if not isinstance(tool_input, dict):
        tool_input = {}
    prompt_context = _prompt_context(payload, rotate_fallback=False)

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
    dispatched = _dispatched_skills(prompt_context)
    # The deny is satisfied by the owning skill OR any delegate it hands the call
    # to (platform-soql-query → platform-data-manage), so the delegate's own call
    # flows through instead of re-denying.
    satisfying = {skill} | _DISPATCH_DELEGATES.get(skill, frozenset())
    if dispatched & satisfying:
        print(json.dumps({"continue": True}))
        return 0

    # Enforcement: promote the nudge to a blocking deny so the model dispatches the
    # owning skill instead of a raw CLI/manifest write. Only `_ENFORCEABLE_SKILLS`
    # denies. The turn-aware suppression above already cleared any op whose owning
    # skill dispatched this turn, so the deny cannot deadlock the workflow.
    if skill in _ENFORCEABLE_SKILLS:
        reason = (
            f"Skills-first enforcement: this looks like {why}. Dispatch the "
            f"`{skill}` skill instead — it owns this operation and encodes the "
            f"validated workflow, governor-limit/FLS guardrails, and error "
            f"recovery a raw call skips. Once that skill runs, its own underlying "
            f"calls are allowed through."
        )
        emit("PreToolUse", "", decision="deny", reason=reason)
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


def cmd_scaffold_gate() -> int:
    """PreToolUse Bash gate on `sf project generate` — the scaffold chokepoint of
    the front-of-journey readiness floor.

    Enforces the readiness floor WITHOUT ever running the scan: a PATH lookup plus
    one small verdict read only (the on-demand-only-scan invariant holds — no ~9s
    spike in a hook). Policy, graded by how cheaply we can prove the environment
    broken:

    - `sf` absent → `sf project generate` will fail outright → DENY with remediation.
    - a scan that RAN and FAILED for THIS toolchain (signature match, ready False) →
      known-broken → DENY, naming what needs attention.
    - a fresh signature-matched pass → allow silently.
    - otherwise (no verdict, or a stale one from a since-changed toolchain) → ALLOW,
      but nudge the model to verify first. We do NOT block on merely-unchecked: we
      can't cheaply prove it's broken, and blocking a fine environment to force a
      ~9s scan is user-hostile.

    Self-gates on the command (some Claude Code builds fire every Bash PreToolUse
    hook regardless of the plugin.json `if:`), and fails OPEN on any error — a
    readiness gate must never wedge scaffolding shut on its own bug."""
    try:
        payload = _read_hook_payload()
        if not _SCAFFOLD_COMMAND.search(_hook_command(payload)):
            print(json.dumps({"continue": True}))
            return 0
        if resolve_executable("sf") is None:
            emit("PreToolUse", "", decision="deny", reason=(
                _READINESS_GATE_TAG + " The Salesforce CLI (`sf`) isn't on your PATH, so "
                "`sf project generate` will fail. Run the platform-environment-validate skill "
                "(or /salesforce-development:setup) to get the SF CLI, Node, and git ready, then "
                "scaffold."))
            return 0
        state = _load_readiness_state()
        signature_matches = state.get("signature") == _toolchain_signature()
        if signature_matches and bool(state.get("ready")):
            print(json.dumps({"continue": True}))          # fresh pass — allow silently
            return 0
        if signature_matches and state.get("ready") is False:
            # Name only the true BLOCKERS (critical rows). Advisory 🟡 warnings live
            # in needsAttention but must never read as "fix before you can scaffold" —
            # ready is False here precisely because a critical prerequisite is broken.
            # Fall back to needsAttention for verdicts written before blockers existed,
            # then to a generic phrase.
            blocking = state.get("blockers")
            if blocking is None:
                blocking = state.get("needsAttention")
            missing = ", ".join(
                _sanitize_dynamic_text(n) for n in (blocking or []) if n
            ) or "a required prerequisite"
            emit("PreToolUse", "", decision="deny", reason=(
                _READINESS_GATE_TAG + f" Your last environment check found a broken prerequisite "
                f"({missing}) that would stop the project you create from building or deploying. Fix "
                "that and re-run the platform-environment-validate skill (or "
                "/salesforce-development:setup) before scaffolding. Advisory warnings on their own "
                "(e.g. a non-LTS Node, an org-scoped source-tracking note) never block — only a "
                "genuinely broken prerequisite does."))
            return 0
        # Unverified (no verdict) or stale (toolchain changed since the scan): we
        # can't prove it broken → allow, but nudge the model to verify first.
        emit("PreToolUse", (
            "Environment-readiness: the local toolchain hasn't been verified this session, so "
            "`sf project generate` is proceeding unchecked. Consider running the "
            "platform-environment-validate skill (or /salesforce-development:setup) first to "
            "confirm the SF CLI, Node, and git are ready — a missing prerequisite would surface "
            "later at build or deploy time, not now."))
        return 0
    except Exception:
        print(json.dumps({"continue": True}))
        return 0


# Six stages (front-of-journey redesign, plan §5 / D5·D7·D11). The two FRONT stages
# are discrete EARNED facts, each lit by its own cheap, network-free signal:
# `Connect` is an org CURRENTLY set as the target, `Project` is a DX project present
# here. Environment readiness is deliberately NOT a stage — it is a PRECONDITION
# surfaced by the readiness banner + the Connect/Project triggers, never an earned
# journey position (that is why "Setup" left the rail). `Build` is source in the
# project; the back stages ride file facts and durable passed events.
JOURNEY_STAGES = ("Connect", "Project", "Build", "Test", "Deploy", "Observe")

# One bounded, deterministic next action per stage. Deliberately generic: the
# rail knows the stage, never the user's intent, so nothing here may promise an
# outcome or name a command the session has not verified is available.
NEXT_ACTION: dict[str, str] = {
    "Connect": "Authenticate an org, then explicitly set it as the target.",
    "Project": "Create a DX project to anchor your source and direction.",
    "Build": "Add source to a package directory in the project.",
    "Test": "Add or run the owning Apex/Jest tests for your source.",
    "Deploy": "Validate against a declared target before deploying.",
    "Observe": "Use the owning architecture and observability skills.",
}

# Rail geometry: one glyph plus ten connectors is an 11-column cell, so stage
# labels land under their own glyph. The cell is deliberately wider than the
# longest label ("welcome"/"observe", 7) so adjacent labels keep clear air between
# them. len(connector)+1 must equal the cell width, or the glyph row and label row
# drift out of alignment.
#
# Three statuses, three glyphs — no `unknown`. A stage is `complete` (●) once its
# own evidence exists and stays lit (completion does not decay); `current` (◉) is
# the cursor, the first stage still lacking evidence, which may sit BEHIND a lit
# later stage on a cyclical rail; `future` (○) is everything not yet reached.
_JOURNEY_GLYPHS = {"complete": "●", "current": "◉", "future": "○"}
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


# Cap on files examined by the on-disk artifact walks (_has_local_source_artifacts
# for Build, _has_test_artifacts for Test) so a pathological tree — e.g. a huge
# non-source vendor/static-resource subtree under a package dir with no early-exit
# hit — can't stall the ≤5s SessionStart / paint path. Past the cap both walks fail
# closed to "no Tier-A signal on disk"; a durable phase-tracker event can still light
# the stage. Mirrors the transcript scanner's line cap.
_ARTIFACT_SCAN_FILE_CAP = 4000
_ARTIFACT_SCAN_ENTRY_CAP = 5000
_ARTIFACT_SCAN_DEPTH_CAP = 32


def _bounded_artifact_walk_step(
    candidate: Path, current: object, dirs: list[str], files: list[str],
    excluded_dirs: set[str], entries_seen: int,
) -> tuple[bool, int, list[str]]:
    current_path = Path(current)
    try:
        depth = len(current_path.relative_to(candidate).parts)
    except ValueError:
        dirs[:] = []
        return False, entries_seen, []
    if depth > _ARTIFACT_SCAN_DEPTH_CAP:
        dirs[:] = []
        return False, entries_seen, []
    dirs[:] = sorted(
        name for name in dirs
        if name not in excluded_dirs and not name.startswith(".")
    )
    ordered_files = sorted(files)
    entries_seen += len(dirs) + len(ordered_files)
    if entries_seen > _ARTIFACT_SCAN_ENTRY_CAP:
        dirs[:] = []
        return False, entries_seen, []
    return True, entries_seen, ordered_files


def _has_local_source_artifacts(project_root: Path) -> bool:
    """Return whether a declared local package directory contains a source file.

    This is deliberately a local, read-only check. It follows packageDirectories
    from sfdx-project.json, does not inspect org state, and does not treat the
    project descriptor or top-level housekeeping files as source artifacts.
    """
    descriptor = _read_project_descriptor(project_root)
    entries = descriptor.get("packageDirectories") if isinstance(descriptor, dict) else None
    paths = [entry.get("path") for entry in entries or [] if isinstance(entry, dict) and entry.get("path")]
    if not paths:
        paths = ["force-app"]

    root = project_root.resolve()
    excluded_dirs = {"node_modules", ".git", ".sf", ".sfdx", ".claude"}
    scanned = 0
    entries_seen = 0
    for configured in paths:
        candidate = (root / str(configured)).resolve()
        if candidate != root and root not in candidate.parents:
            continue
        if not candidate.is_dir():
            continue
        for current, dirs, files in os.walk(candidate):
            accepted, entries_seen, files = _bounded_artifact_walk_step(
                candidate, current, dirs, files, excluded_dirs, entries_seen
            )
            if not accepted:
                if entries_seen > _ARTIFACT_SCAN_ENTRY_CAP:
                    return False
                continue
            current_path = Path(current)
            for filename in files:
                # Bound the walk so a huge non-source subtree with no early-exit hit
                # can't run away on the paint path (the sibling test walk does the same).
                scanned += 1
                if scanned > _ARTIFACT_SCAN_FILE_CAP:
                    return False
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


# Content markers that make an Apex class a test to the compiler — the PRIMARY,
# highest-fidelity Test signal. A `*Test.cls` NAME alone can lie (a helper misnamed
# `AccountTest.cls` isn't a test); the `@isTest` annotation / `testMethod` keyword
# cannot. Matched case-insensitively.
_APEX_TEST_MARKERS = ("@istest", "testmethod")
# Read only the head of each .cls: the annotation sits at the class/method decl up
# top, so a bounded read keeps the walk cheap on the ≤5s hook budget.
_APEX_TEST_SCAN_BYTES = 4096


def _has_test_artifacts(project_root: Path) -> bool:
    """Return whether the project carries on-disk TEST artifacts — the Tier-A Test
    signal. A filesystem fact, network-free, re-derived live at paint exactly as
    _has_local_source_artifacts is for Build. True on the FIRST of:
      - an Apex class whose head contains `@isTest` / `testMethod` (primary);
      - an LWC Jest spec (a `.test.js` inside a `__tests__/` directory);
      - an ApexTestSuite (`*.testSuite-meta.xml`).
    One os.walk over the declared package dirs, early-exit on first hit, byte- and
    file-capped, following the same packageDirectories / excluded-dir / path-escape
    discipline as _has_local_source_artifacts. Fail-closed to False on any I/O
    error: an unreadable tree simply doesn't light Test from Tier A."""
    descriptor = _read_project_descriptor(project_root)
    entries = descriptor.get("packageDirectories") if isinstance(descriptor, dict) else None
    paths = [entry.get("path") for entry in entries or [] if isinstance(entry, dict) and entry.get("path")]
    if not paths:
        paths = ["force-app"]

    root = project_root.resolve()
    excluded_dirs = {"node_modules", ".git", ".sf", ".sfdx", ".claude"}
    scanned = 0
    entries_seen = 0
    for configured in paths:
        candidate = (root / str(configured)).resolve()
        if candidate != root and root not in candidate.parents:
            continue
        if not candidate.is_dir():
            continue
        for current, dirs, files in os.walk(candidate):
            # Keep .git/node_modules out, but DO descend into __tests__ (dotless,
            # so it survives the startswith('.') filter) — that's where Jest lives.
            accepted, entries_seen, files = _bounded_artifact_walk_step(
                candidate, current, dirs, files, excluded_dirs, entries_seen
            )
            if not accepted:
                if entries_seen > _ARTIFACT_SCAN_ENTRY_CAP:
                    return False
                continue
            current_path = Path(current)
            in_tests_dir = "__tests__" in current_path.parts
            for filename in files:
                scanned += 1
                if scanned > _ARTIFACT_SCAN_FILE_CAP:
                    return False
                lower = filename.casefold()
                if lower.endswith(".testsuite-meta.xml"):
                    return True
                if in_tests_dir and lower.endswith(".test.js"):
                    return True
                if lower.endswith(".cls"):
                    try:
                        with open(current_path / filename, "r", encoding="utf-8", errors="ignore") as fh:
                            head = fh.read(_APEX_TEST_SCAN_BYTES).casefold()
                    except OSError:
                        continue
                    if any(marker in head for marker in _APEX_TEST_MARKERS):
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
    printable = _sanitize_dynamic_text(value).strip()
    return _clip_cells(printable, _DISPLAY_NAME_LIMIT)


def _project_display_name(project_root: Path) -> Optional[str]:
    """Name the project from its descriptor, falling back to the directory name.

    Root-bound on purpose: project_meta() reads the current directory and
    substitutes a "Project" placeholder, and neither is honest on this path.
    None means there is no project here at all.
    """
    descriptor = project_root.joinpath("sfdx-project.json")
    if not descriptor.is_file():
        return None
    data = _read_project_descriptor(project_root)
    declared = _bounded_display_name(data.get("name") if isinstance(data, dict) else None)
    # Directory names are untrusted too — macOS permits newlines in them.
    return declared or _bounded_display_name(project_root.name) or "(unnamed)"


# Well-known filenames under ~/.sfdx that are NOT authentications: the CLI's own
# bookkeeping. Skipped fast so they are never even read. This is a first pass, NOT
# the gate — the org-id-keyed *.sandbox.json sandbox-PROCESS cache is also tokenless
# and can't be enumerated by name, so an authentication is confirmed by CONTENT below.
_NON_AUTH_SFDX_FILES = {"alias.json", "sfdx-config.json", "key.json", "sf-tokens.json", "stash.json"}
# A persisted authentication carries at least one stored credential. @salesforce/core
# writes one of these into every auth file (accessToken/refreshToken for OAuth, the
# private key for JWT, password for username-password / scratch orgs); a tokenless
# cache the CLI co-locates in ~/.sfdx carries none. This is the discriminator a
# filename check can't make — it is what tells a real login apart from bookkeeping.
_AUTH_CREDENTIAL_KEYS = ("accessToken", "refreshToken", "privateKey", "privateKeyFile", "password")
# Bound the store scan on the hot path: a handful of small (~1-2 KB) JSON files is
# normal; past the cap, or on a file too large to be an auth entry, fail closed.
_SFDX_AUTH_SCAN_FILE_CAP = 512
_SFDX_AUTH_READ_BYTES = 65536


def _has_authed_org() -> bool:
    """Cheap, subprocess-free "has the user ever authenticated an org" signal — a
    single listing of the global auth store, NO `sf` round-trip, so it is safe on
    the SessionStart / paint path (the on-demand-only org-probe invariant holds).

    Auth is a per-USER, global fact: `sf` writes one `<key>.json` auth file per org
    under ~/.sfdx, independent of the current project or directory. So this stays
    true for a developer who authed an org earlier and then starts a fresh project
    elsewhere — the connection does not decay with cwd, which is exactly why it
    lights the durable `Connect` stage rather than a per-context target-org probe.

    A `<key>.json` counts only when it actually carries a stored credential
    (`_AUTH_CREDENTIAL_KEYS`): the CLI co-locates tokenless caches in the same
    directory — notably the org-id-keyed `*.sandbox.json` sandbox-process record,
    which persists after `sf org logout --all` removes every real auth file — and a
    name-only check would false-light `Connect` from one, faking a connection that
    was never made. Reading each candidate's head (bounded, in-process, never
    surfaced) is the honest test of "is this a real authentication."

    Honesty: presence means "reached Connect (ever authed an org)" — a historical
    fact; it does NOT assert any token is still live. Reachability-now is a freshness
    annotation resolved elsewhere, never a reason to un-light `Connect`. Fails soft:
    a missing store, or an unreadable / corrupt / oversized file, yields False (per
    file and overall), never raising on the hook path."""
    try:
        entries = list((Path.home() / ".sfdx").iterdir())
    except OSError:
        return False
    scanned = 0
    for entry in entries:
        if entry.suffix != ".json" or entry.name in _NON_AUTH_SFDX_FILES:
            continue
        scanned += 1
        if scanned > _SFDX_AUTH_SCAN_FILE_CAP:
            return False
        try:
            if not entry.is_file():
                continue
            with open(entry, "r", encoding="utf-8", errors="ignore") as fh:
                data = json.loads(fh.read(_SFDX_AUTH_READ_BYTES))
        except (OSError, json.JSONDecodeError, ValueError):
            continue
        if isinstance(data, dict) and any(data.get(key) for key in _AUTH_CREDENTIAL_KEYS):
            return True
    return False


# The config keys that name a default/target org, newest form first: modern `sf`
# writes `target-org` into `.sf/config.json`; legacy `sfdx` wrote `defaultusername`
# into `.sfdx/sfdx-config.json`. A project configured by either tool still counts.
_TARGET_ORG_CONFIG_KEYS = ("target-org", "defaultusername")


def _configured_target_alias(root: Path) -> Optional[str]:
    """The org name CURRENTLY set as the default/target — read subprocess-free from the
    local project config first, then the global user config — or None if none is set.
    This is the value `_has_target_org` booleanizes; returning the NAME lets the org
    band show *which* org is targeted (reachability unprobed) instead of a bare
    "unknown" that would contradict the lit Connect dot for a returning developer.

    Safe on the SessionStart / paint path (the on-demand-only org-probe invariant
    holds; no `sf` round-trip). Honors the modern `sf` `target-org` key and the legacy
    sfdx `defaultusername`; a present-but-empty (or whitespace-only) value is not a
    target. Fails soft: a missing / unreadable / corrupt config is skipped per file,
    never raising; None overall when nothing is configured anywhere."""
    candidates = (
        root / ".sf" / "config.json",
        root / ".sfdx" / "sfdx-config.json",
        Path.home() / ".sf" / "config.json",
        Path.home() / ".sfdx" / "sfdx-config.json",
    )
    for cfg in candidates:
        try:
            data = json.loads(cfg.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, ValueError):
            continue
        if isinstance(data, dict):
            for key in _TARGET_ORG_CONFIG_KEYS:
                value = data.get(key)
                if isinstance(value, str) and value.strip():
                    return value
    return None


def _has_target_org(root: Path) -> bool:
    """Is an org CURRENTLY set as the default/target — the signal the `Connect` stage
    lights from. Deliberately DISTINCT from `_has_authed_org`: that answers "has the
    user ever authenticated an org" (auth history, per-user, cwd-independent); this
    answers "is one configured as the target right now" — the org the next `sf`
    command would actually act on. A developer can have many orgs authed yet none
    targeted here, so the rail tracks the target, not the history. A configured-but-
    offline target still counts as "set" — reachability is a band annotation resolved
    elsewhere, never a reason to un-light Connect (the non-decay rule). Thin boolean
    over `_configured_target_alias` so the "is one set" and "which one" reads never
    drift."""
    return _configured_target_alias(root) is not None


def _derive_journey_state(
    root: Path,
    *,
    has_project: bool,
    target: str,
    target_error: Optional[str],
    org_display: Optional[dict],
) -> dict:
    """Infer the journey rail from the already-resolved org plus cheap local reads.

    No CLI or org round-trip happens here — the caller resolves the org and passes
    it in, so the org is never queried twice for one surface — but this DOES perform
    the bounded, network-free local reads the rail derives from: on-disk source and
    test artifacts (Tier-A), and the durable phase tracker (Tier-B). Split out of
    `_journey_state` so a caller that has ALREADY resolved the org (SessionStart's
    banner, the on-demand status paint) shares the identical derivation.

    The rail is CYCLICAL, not a linear progress bar. A stage lights ● from its OWN
    evidence, decided independently of its neighbours: a cheap, network-free FRONT
    signal (an org currently set as the target lights Connect; a DX project present
    here lights Project), a live Tier-A file fact (source / tests on disk light Build
    / Test) OR a durable Tier-B event on the tracker (a *passed* deploy, test-run, or
    observe). So Deploy can be ● while Test is ○ (deployed with no tests on record),
    and the ◉ cursor — the first stage still lacking evidence — can sit BEHIND a lit
    later stage. Completion is a historical fact and does not decay; there is no
    `unknown` glyph and no position-implies-status assumption. Environment readiness
    is NOT a rail stage — it is a precondition surfaced elsewhere (plan §5 / D5)."""
    # --- Org band: honest 4-state org status + alias/reason (unchanged shape). ---
    reason = "No sfdx-project.json is present in the current directory."
    # Four honest states, never a fake boolean — unknown / not-configured /
    # unreachable / reachable. "unknown" is the answer before a project exists,
    # because this path never probes an org without one; the Connect stage still
    # lights from the configured target (_has_target_org / a resolved target), not
    # from this reachability probe.
    org_status, org_alias = "unknown", None
    if has_project:
        reason = "A Salesforce DX project is present, but no configured and reachable target org was verified."
        if target:
            org_alias = _bounded_display_name(target) or "(unnamed)"
            # Passive startup passes this sentinel after reading local config. It
            # must not turn "not probed" into a reachability claim; explicit status
            # paths omit the sentinel and retain their live reachable/unreachable
            # resolution.
            org_status = "configured-unprobed" if target_error == "unprobed" else "unreachable"
            if org_display:
                # `sf org display` output is untrusted in shape as well as content:
                # get_org_display() can hand back a `result` array or a non-string
                # alias, so degrade to the configured target instead of raising.
                declared = org_display.get("alias") if isinstance(org_display, dict) else None
                org_status = "reachable"
                org_alias = _bounded_display_name(declared) or _bounded_display_name(target) or "(unnamed)"
        elif not target_error:
            # Only the clean ("", "") leg means "no default org is set". A failed
            # query stays "unknown" — never a fabricated "no org" (W-23466800 /
            # WIN-027), matching every other get_target_org_detailed() caller.
            org_status = "not-configured"

    # A configured target org is a real, EARNED Connect even without a project or a
    # live probe — a returning developer who has run `sf org login --set-default` is
    # not a newcomer. Outside a project the org is never probed (org_status stays
    # "unknown"), so reflect WHICH org is targeted — read subprocess-free from config —
    # rather than a bare "unknown" that would contradict the lit Connect dot. This is
    # the "treat the global default as legitimate, and SHOW it" call (plan §5 / D6).
    # Reachability stays unprobed here; the "configured" band carries no ✓.
    configured_alias = _configured_target_alias(root)
    if not has_project and org_status == "unknown" and configured_alias:
        org_status = "configured"
        org_alias = _bounded_display_name(configured_alias) or "(unnamed)"

    # Load the canonical history once. Public evidence projections below are
    # allowlisted and never carry orgHash or rejected input bytes. Scope uses only
    # an identity the caller already resolved; it never adds a passive CLI call.
    history = _load_phase_history_result().records if has_project else []
    current_org_hash = None
    if isinstance(org_display, dict):
        current_org_id = _normalize_salesforce_org_id(
            org_display.get("id") or org_display.get("orgId")
        )
        if current_org_id:
            current_org_hash = _phase_org_digest(current_org_id, create=False)

    # --- Reached set: per-stage evidence, order-independent (the cyclical core). --
    # The two FRONT stages are discrete EARNED facts, each lit by its OWN current
    # signal — both cheap, network-free reads (no `sf` subprocess):
    #   Connect — an org is CURRENTLY set as the target (a resolved target, or one read
    #             from .sf/config.json via _has_target_org), NOT a history of ever
    #             having authenticated one. "Have I authed orgs" and "is one my target
    #             now" are different questions (auth history vs current target); the
    #             rail tracks the org the next command would act on. Reachability-now
    #             is deliberately NOT a lighting basis — a target set but offline is
    #             still set — so `●` never flips ●→○ when an org blips (non-decay); the
    #             band annotates reachability separately.
    #   Project — a DX project exists here (sfdx-project.json / has_project). The
    #             project is the container everything downstream hangs off, and its
    #             existence is a discrete earned fact, so it is its own dot. Environment
    #             READINESS is deliberately NOT a rail stage — it is a precondition
    #             surfaced by the readiness banner + the Connect/Project triggers, never
    #             an earned journey position (front-of-journey redesign, plan §5 / D5).
    reached: set[str] = set()
    if bool(target) or configured_alias:
        reached.add("Connect")
    # The Project dot AND the back stages are project-gated: their evidence is a
    # descriptor / source / tests / history read relative to a project root, so without
    # a project there is nothing honest to read and walking an arbitrary cwd would be
    # both wrong and unbounded. Build lights on SOURCE, not a bare scaffold — a
    # scaffolded-but-empty project lights Project ● and leaves the cursor at Build.
    if has_project:
        # A DX project exists here — Project is earned the moment its descriptor does.
        reached.add("Project")
        # Tier-A source/test facts are about files on disk — independent of the org,
        # so they light Build/Test even when the target is unreachable. Bounded,
        # early-exit, network-free walks (see the helpers); safe on the paint path.
        if _has_local_source_artifacts(root):
            reached.add("Build")
        if _has_test_artifacts(root):
            reached.add("Test")
        # Tier-B durable history: a stage a hooked outcome has PROVEN, non-decaying.
        # Only `passed` lights ● — a failed deploy is a micro-tier "attempted" and a
        # Tier-C skill dispatch is activity, neither of which is proof (signal ladder).
        passed = {rec.get("stage") for rec in history if rec.get("outcome") == "passed"}
        for stage in ("Test", "Deploy", "Observe"):
            if stage in passed:
                reached.add(stage)

    # --- Cursor: the first stage still lacking its own evidence. On a fully-lit
    # rail it rests on the terminal Observe — you are in the observe/iterate loop.
    cursor = next((name for name in JOURNEY_STAGES if name not in reached), JOURNEY_STAGES[-1])
    if has_project and org_status == "reachable":
        reason = f"Project and reachable org are available; the journey cursor rests at {cursor}."

    stages = []
    for name in JOURNEY_STAGES:
        if name == cursor:
            status = "current"
        elif name in reached:
            status = "complete"
        else:
            status = "future"
        evidence = [_public_phase_evidence(record, current_org_hash) for record in history
                    if record.get("stage") == name][-_JOURNEY_EVIDENCE_CAP:]
        stages.append({"name": name, "status": status, "evidence": evidence})
    ordered_reached = [name for name in JOURNEY_STAGES if name in reached]
    return {
        "mode": "journey",
        "currentStage": cursor,
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
            "Each stage lights from its own evidence — a cheap front signal (an org currently "
            "set as the target lights Connect; a DX project present here lights Project), a live "
            "source / test file fact (Build / Test), or a durable passed deploy / test-run / "
            "observe event on the phase tracker. The cursor marks the first stage still lacking "
            "evidence and may sit behind a lit later stage; nothing is assumed from position alone."
        ),
        "schemaVersion": 2,
        "cursor": cursor,
        "reached": ordered_reached,
        "allReached": len(ordered_reached) == len(JOURNEY_STAGES),
    }


def _journey_state(project_root: Optional[Path] = None) -> dict:
    """Gather the journey facts from the CLI + filesystem, then derive the stage.

    The self-contained path: probe target-org and org display, then hand off to
    `_derive_journey_state` (which does the local source/test/tracker reads itself).
    Callers that have ALREADY resolved the org (SessionStart, the status paint) skip
    this and call `_derive_journey_state` directly, so the org is never queried twice
    for one surface."""
    root = (project_root or Path.cwd()).resolve()
    has_project = root.joinpath("sfdx-project.json").is_file()
    target, target_error = "", None
    org_display: Optional[dict] = None
    if has_project:
        target, target_error = get_target_org_detailed()
        if target:
            org_display = get_org_display(target)
    return _derive_journey_state(
        root,
        has_project=has_project,
        target=target,
        target_error=target_error,
        org_display=org_display,
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
                                      target_error="cli-unresolved", org_display=None)
        return state, None
    target, target_error = get_target_org_detailed()
    org: Optional[dict] = None
    org_display: Optional[dict] = None
    if target and not target_error:
        with ThreadPoolExecutor(max_workers=2) as pool:
            list_fut = pool.submit(get_org_list)
            display_fut = pool.submit(get_org_display, target)
            org_list_data = list_fut.result()
            org_display = display_fut.result()
        if org_display:
            org = resolve_org_info(target, org_list=org_list_data, org_display=org_display)
    state = _derive_journey_state(root, has_project=True, target=target,
                                  target_error=target_error, org_display=org_display)
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
    if status == "configured":
        # Set as the default target, but reachability was not probed on this path —
        # so it shows the org (a returning dev IS connected) without a ✓ it can't earn.
        return f"org: {alias}"
    if status == "configured-unprobed":
        return f"org: {alias} (unprobed)"
    return "org: unknown"


def _journey_context_line(context: dict) -> str:
    """Compose the context row, clamped so the pinned rail always fits 80 columns.

    Source tracking is a PROJECT concept — it only becomes meaningful once you are
    building in a project — so the source-tracking cell is shown ONLY in a project;
    outside one the row is just the project + org cells (which also frees the width for
    the full org alias instead of clipping it). When shown, the source-tracking state is
    a fact about what was NOT checked, so it is never the thing dropped to make room; only
    the two untrusted names give ground, and the rail keeps its geometry instead of
    soft-wrapping at the terminal edge.
    """
    project = context.get("project")
    line = ""
    for limit in range(_DISPLAY_NAME_LIMIT, 3, -1):
        segments = [
            f"sfdx project: {_clip(project, limit)}" if project else "sfdx project: (none detected)",
            _journey_org_cell(context, limit),
        ]
        if project:
            segments.append("source-tracking … (not probed)")
        line = "   ".join(segments)
        if _terminal_cell_width(line) <= _RAIL_WIDTH:
            break
    return line


_JOURNEY_GLYPH_STYLES = {"complete": "ok", "current": "link", "future": "muted"}


def _render_signpost(state: dict, *, color: bool = False, include_context: bool = True) -> list[str]:
    """The visual signpost lines: (optionally) the context row, the glyph bar, and
    the stage labels. Shared by the journey rail, the getting-started welcome, and
    the wayfinder (which omits the context row — its header already states the org).

    Every glyph is derived from that stage's status, so a not-yet stage can never
    render as reached. No positioned "you are here" marker on the rail itself — the
    current stage reads from its greened ◉ glyph and the `likely next` line; the
    inline marker jumbled the layout. No glyph legend either: the three distinct
    shapes (● reached · ◉ here now · ○ not yet) carry state on their own and survive
    NO_COLOR, including the cyclical case where the ◉ cursor sits behind a lit ●."""
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
    label_parts: list[str] = []
    for stage in stages:
        label = _clip_cells(stage.get("name") or "?", _JOURNEY_CELL_WIDTH).lower()
        padding = " " * max(0, _JOURNEY_CELL_WIDTH - _terminal_cell_width(label))
        label_parts.append((_green(label) if stage.get("status") == "current" else label) + padding)
    labels = "".join(label_parts).rstrip()
    lines: list = []
    if include_context:
        lines += [_paint_line([(_journey_context_line(context), "muted")], color=color), ""]
    lines += [_paint_line(glyphs, color=color), _paint_line([(labels, "body")], color=color)]
    return lines


def _render_journey_rail(state: dict, *, color: bool = False, include_context: bool = True) -> str:
    """Render the six-stage signpost rail from an inferred journey state: the
    signpost and the one `likely next` step. Flush-left by design.

    No glyph legend: the three distinct shapes (● reached · ◉ here now · ○ not yet)
    carry state on their own and survive NO_COLOR — including the cyclical case
    where the ◉ cursor sits behind a lit ● (the shapes differ, so the cursor is
    unambiguous wherever it sits). The stale "Inference is bounded" footnote stays
    retired. `include_context=False` also drops the context row (the wayfinder's
    header already states the org).
    """
    stages = state.get("stages") or []
    current = _clip_cells(state.get("currentStage") or "?", 64)
    # On a fully evidenced rail the cursor deliberately rests on Observe even
    # though Observe is reached. That is the ONLY case where `current` also belongs
    # in the reached summary; otherwise current is the first stage lacking evidence.
    # Read the derivation's own `allReached` — a no-`future` rail is NOT proof the
    # cursor is reached (the honest cyclical case, e.g. cursor Test with Deploy/Observe
    # lit, has no `future` stage yet the cursor is unreached).
    current_is_reached = bool(state.get("allReached"))
    reached = [
        _clip_cells(s.get("name") or "?", 64) for s in stages
        if s.get("status") == "complete" or (s.get("status") == "current" and current_is_reached)
    ]
    no_evidence = [
        _clip_cells(s.get("name") or "?", 64) for s in stages
        if s.get("status") == "future" or (s.get("status") == "current" and not current_is_reached)
    ]
    summary = [
        _clip_cells(f"current: {current}", _RAIL_WIDTH),
        _clip_cells("reached: " + (", ".join(reached) if reached else "none"), _RAIL_WIDTH),
        _clip_cells("no evidence: " + (", ".join(no_evidence) if no_evidence else "none"), _RAIL_WIDTH),
    ]
    next_action = _sanitize_dynamic_text(NEXT_ACTION.get(state.get("currentStage"), ""))
    return "\n".join([
        *_render_signpost(state, color=color, include_context=include_context),
        *summary,
        "",
        _paint_line([(_pad_cells("likely next", _JOURNEY_LABEL_WIDTH) + next_action, "body")], color=color),
    ])


def _journey_reset_history_status(result: PhaseHistoryResult) -> str:
    if result.rejected and not result.accepted:
        return "corrupt"
    if result.rejected:
        return "partially-valid"
    return "available"


def _journey_reset_args(args: list[str]) -> Optional[dict]:
    """Parse the small fixed reset grammar without accepting positional text."""
    parsed = {"stage": None, "scope": "all", "confirm": None, "json": False}
    seen: set[str] = set()
    index = 0
    while index < len(args):
        flag = args[index]
        if flag == "--json":
            if flag in seen:
                return None
            parsed["json"] = True
            seen.add(flag)
            index += 1
            continue
        if flag not in ("--stage", "--scope", "--confirm") or flag in seen:
            return None
        if index + 1 >= len(args):
            return None
        parsed[flag[2:]] = args[index + 1]
        seen.add(flag)
        index += 2
    if parsed["stage"] is not None and parsed["stage"] not in JOURNEY_STAGES:
        return None
    if parsed["scope"] not in _JOURNEY_RESET_SCOPES:
        return None
    if parsed["confirm"] is not None and not _JOURNEY_RESET_NONCE.fullmatch(parsed["confirm"]):
        return None
    return parsed


def _journey_reset_project() -> Optional[tuple[str, tuple[int, int]]]:
    """Return a public project label and private canonical-root identity."""
    try:
        root_info = os.stat(".", follow_symlinks=False)
    except OSError:
        return None
    if not stat.S_ISDIR(root_info.st_mode) or not Path("sfdx-project.json").is_file():
        return None
    label = _project_display_name(Path(".")) or "(unnamed)"
    # A project name is a label, never a path. Remove both platform separators
    # even when one is not native on this host, then apply the existing boundary.
    label = _bounded_display_name(label.replace("/", " ").replace("\\", " ")) or "(unnamed)"
    return label, _phase_identity(root_info)


def _phase_key_bytes_readonly(directory: PhaseDirectory) -> Optional[bytes]:
    """Read an already-private attribution key without chmod or other mutation."""
    names = _phase_file_names()
    if names is None:
        return None
    fd = None
    try:
        fd = _open_phase_child(
            directory, names[2], os.O_RDONLY | getattr(os, "O_NONBLOCK", 0)
        )
        if not _phase_private_fd(fd):
            return None
        data = os.read(fd, 33)
        return data if len(data) == 32 else None
    except OSError:
        return None
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass


def _current_phase_org_hash(directory: Optional[PhaseDirectory] = None) -> Optional[str]:
    """Resolve current identity and read the existing private key without mutation.

    Reset owns synchronization: dry-run deliberately performs no persistent lock
    operation, while confirm calls this under the already-held phase lock.
    """
    target, error = get_target_org_detailed()
    if not target or error:
        return None
    display = get_org_display(target)
    if not isinstance(display, dict):
        return None
    org_id = _normalize_salesforce_org_id(display.get("id") or display.get("orgId"))
    if org_id is None:
        return None
    owned = directory is None
    directory = directory or _open_phase_directory(False)
    if directory is None:
        return None
    try:
        key = _phase_key_bytes_readonly(directory)
        return (hmac.new(key, org_id.encode("ascii"), hashlib.sha256).hexdigest()
                if key is not None else None)
    finally:
        if owned:
            _close_phase_directory(directory)


def _journey_reset_nonce(
    root_identity: tuple[int, int], stage: Optional[str], scope: str, preimage: bytes,
    current_hash: Optional[str] = None,
) -> str:
    """Bind authorization to root inode, resolved filters, and every history byte."""
    binding = json.dumps(
        {"root": [root_identity[0], root_identity[1]], "stage": stage, "scope": scope,
         # Private resolved identity is part of a current/other scope filter. It is
         # digested into the nonce and never returned, so retargeting between dry
         # run and confirmation cannot silently select a different record set.
         "scopeIdentity": current_hash if scope in ("current-org", "other-org") else None},
        sort_keys=True, separators=(",", ":"),
    ).encode("ascii")
    preimage_digest = hashlib.sha256(preimage).digest()
    return hashlib.sha256(b"journey-reset-v1\0" + binding + b"\0" + preimage_digest).hexdigest()


def _read_phase_preimage(directory: PhaseDirectory) -> Optional[tuple[bytes, tuple[int, int]]]:
    names = _phase_file_names()
    if names is None:
        return None
    fd = None
    try:
        fd = _open_phase_child(
            directory, names[0], os.O_RDONLY | getattr(os, "O_NONBLOCK", 0)
        )
        if not _phase_regular_fd(fd):
            return None
        identity = _phase_identity(os.fstat(fd))
        chunks = []
        remaining = _PHASE_HISTORY_MAX_FILE_BYTES + 1
        while remaining > 0:
            chunk = os.read(fd, min(64 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks), identity
    except OSError:
        return None
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass


def _write_all(fd: int, value: bytes) -> None:
    view = memoryview(value)
    while view:
        written = os.write(fd, view)
        if written <= 0:
            raise OSError("short phase write")
        view = view[written:]


def _unlink_phase_entry(directory: PhaseDirectory, name: str) -> None:
    try:
        if directory.relative:
            os.unlink(name, dir_fd=directory.fd)
        elif _phase_fallback_unchanged(directory):
            (directory.path / name).unlink()
    except OSError:
        pass


def _phase_windows() -> bool:
    return os.name == "nt"


def _windows_kernel32():
    """Load kernel32 through ctypes only on the Windows durability path."""
    import ctypes
    return ctypes.WinDLL("kernel32", use_last_error=True)


def _windows_flush_phase_directory(directory: PhaseDirectory) -> bool:
    """Open and flush the pinned `.sf` directory using native Windows APIs."""
    if directory.relative or not _phase_fallback_unchanged(directory):
        return False
    handle = None
    api = None
    try:
        import ctypes
        from ctypes import wintypes
        api = _windows_kernel32()
        api.CreateFileW.argtypes = (
            wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
            wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
        )
        api.CreateFileW.restype = wintypes.HANDLE
        api.FlushFileBuffers.argtypes = (wintypes.HANDLE,)
        api.FlushFileBuffers.restype = wintypes.BOOL
        api.CloseHandle.argtypes = (wintypes.HANDLE,)
        api.CloseHandle.restype = wintypes.BOOL
        # Read access plus sharing for readers, writers, and renames/deletes keeps
        # this durability handle from blocking cooperating phase-history writers.
        handle = api.CreateFileW(
            str(directory.path), 0x80000000, 0x1 | 0x2 | 0x4, None, 3,
            0x02000000, None,
        )
        invalid = ctypes.c_void_p(-1).value
        if handle in (None, 0, invalid):
            return False
        flushed = bool(api.FlushFileBuffers(handle))
        closed = bool(api.CloseHandle(handle))
        handle = None
        return flushed and closed and _phase_fallback_unchanged(directory)
    except Exception:
        return False
    finally:
        if handle not in (None, 0) and api is not None:
            try:
                api.CloseHandle(handle)
            except Exception:
                pass


def _sync_phase_directory(directory: PhaseDirectory) -> bool:
    """Durably sync directory entries on Windows and POSIX."""
    if _phase_windows():
        return _windows_flush_phase_directory(directory)
    fd = None
    try:
        if directory.relative:
            os.fsync(directory.fd)
        else:
            if not _phase_fallback_unchanged(directory):
                return False
            fd = os.open(directory.path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            os.fsync(fd)
            if not _phase_fallback_unchanged(directory):
                return False
        return True
    except OSError:
        return False
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass


def _sync_phase_file(directory: PhaseDirectory, name: str) -> bool:
    fd = None
    try:
        fd = _open_phase_child(directory, name, os.O_RDWR)
        if not _phase_regular_fd(fd):
            return False
        os.fsync(fd)
        return True
    except OSError:
        return False
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass


def _replace_phase_entry(directory: PhaseDirectory, source: str, destination: str) -> bool:
    try:
        if directory.relative:
            os.replace(source, destination, src_dir_fd=directory.fd, dst_dir_fd=directory.fd)
        else:
            if not _phase_fallback_unchanged(directory):
                return False
            os.replace(directory.path / source, directory.path / destination)
            if not _phase_fallback_unchanged(directory):
                return False
        return True
    except OSError:
        return False


def _create_phase_backup(directory: PhaseDirectory, preimage: bytes) -> bool:
    """Create and durably publish one contained byte-exact backup.

    A file-write failure removes its incomplete entry. A directory-sync failure
    deliberately leaves the fully written backup in place for diagnosis/recovery,
    but returns failure so active history cannot be replaced.
    """
    for _ in range(8):
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        name = f"phase-history.backup-{stamp}-{secrets.token_hex(8)}.jsonl"
        fd = None
        created = False
        written = False
        try:
            fd = _open_phase_child(directory, name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            created = True
            if not _phase_regular_fd(fd):
                raise OSError("unsafe backup")
            _phase_restrict_fd(fd)
            _write_all(fd, preimage)
            os.fsync(fd)
            os.close(fd)
            fd = None
            written = True
            return _sync_phase_directory(directory)
        except FileExistsError:
            if fd is not None:
                os.close(fd)
            continue
        except OSError:
            return False
        finally:
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
            if created and not written:
                _unlink_phase_entry(directory, name)
    return False


def _write_phase_temp(
    directory: PhaseDirectory, name: str, value: bytes
) -> PhaseTempWriteOutcome:
    """Exclusively create one temp and report success separately from ownership."""
    fd = None
    owned = False
    try:
        fd = _open_phase_child(directory, name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        # Only a successful exclusive open establishes that this invocation owns
        # the directory entry. A collision never grants cleanup authority.
        owned = True
        if not _phase_regular_fd(fd):
            return PhaseTempWriteOutcome(False, owned)
        _phase_restrict_fd(fd)
        _write_all(fd, value)
        os.fsync(fd)
        return PhaseTempWriteOutcome(True, owned)
    except OSError:
        return PhaseTempWriteOutcome(False, owned)
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass


def _replace_phase_history(
    directory: PhaseDirectory, expected: bytes, expected_identity: tuple[int, int], retained: bytes
) -> PhaseReplaceOutcome:
    """Atomically replace an unchanged preimage and retain uncertain recovery.

    Before active replacement, an owner-only byte-exact recovery artifact and a
    separate rollback temp are fsynced and durably published. Success or confirmed
    rollback removes the recovery artifact; uncertain outcomes retain it.
    """
    names = _phase_file_names()
    if names is None:
        return PhaseReplaceOutcome(_PHASE_REPLACE_ROLLED_BACK)
    token = secrets.token_hex(16)
    temp_name = f".phase-history.reset-{token}.tmp"
    rollback_name = f".phase-history.rollback-{token}.tmp"
    recovery_name = f".phase-history.recovery-{token}.jsonl"
    terminal = _PHASE_REPLACE_ROLLED_BACK
    temp_owned = False
    recovery_owned = False
    rollback_owned = False
    try:
        written = _write_phase_temp(directory, temp_name, retained)
        temp_owned = written.owned
        if not written.success:
            return PhaseReplaceOutcome(terminal)
        written = _write_phase_temp(directory, recovery_name, expected)
        recovery_owned = written.owned
        if not written.success:
            return PhaseReplaceOutcome(terminal)
        written = _write_phase_temp(directory, rollback_name, expected)
        rollback_owned = written.owned
        if not written.success:
            return PhaseReplaceOutcome(terminal)
        if not _sync_phase_directory(directory):
            return PhaseReplaceOutcome(terminal)
        observed = _read_phase_preimage(directory)
        if observed is None:
            return PhaseReplaceOutcome(terminal)
        current, current_identity = observed
        if current_identity != expected_identity or len(current) != len(expected) or not hmac.compare_digest(
            hashlib.sha256(current).digest(), hashlib.sha256(expected).digest()
        ):
            return PhaseReplaceOutcome(terminal)
        # The fallback helper can report failure after os.replace consumed the
        # source. Relinquish source-name cleanup authority before the attempt: from
        # this point onward, anything appearing at temp_name may be a new collision.
        temp_owned = False
        if not _replace_phase_entry(directory, temp_name, names[0]):
            # A post-replace parent-identity failure cannot prove which active bytes
            # are durable, so preserve the existing uncertain-outcome classification.
            terminal = _PHASE_REPLACE_UNCERTAIN
            return PhaseReplaceOutcome(terminal)
        if _sync_phase_file(directory, names[0]) and _sync_phase_directory(directory):
            terminal = _PHASE_REPLACE_SUCCESS
            return PhaseReplaceOutcome(terminal)
        # Post-replace durability failure is not success. Restore the original
        # preimage atomically from the separate already-fsynced rollback file,
        # leaving the durable recovery artifact independent until the outcome is known.
        # As with the main temp, a false fallback result may follow source
        # consumption. Never clean rollback_name after replacement was attempted.
        rollback_owned = False
        if not _replace_phase_entry(directory, rollback_name, names[0]):
            terminal = _PHASE_REPLACE_UNCERTAIN
            return PhaseReplaceOutcome(terminal)
        if not _sync_phase_file(directory, names[0]):
            terminal = _PHASE_REPLACE_UNCERTAIN
            return PhaseReplaceOutcome(terminal)
        if not _sync_phase_directory(directory):
            terminal = _PHASE_REPLACE_UNCERTAIN
            return PhaseReplaceOutcome(terminal)
        return PhaseReplaceOutcome(terminal)
    finally:
        if temp_owned:
            _unlink_phase_entry(directory, temp_name)
        if rollback_owned:
            _unlink_phase_entry(directory, rollback_name)
        if recovery_owned and terminal != _PHASE_REPLACE_UNCERTAIN:
            _unlink_phase_entry(directory, recovery_name)


def _journey_reset_selected(record: dict, stage: Optional[str], scope: str,
                            current_hash: Optional[str]) -> bool:
    if stage is not None and record.get("stage") != stage:
        return False
    event_hash = record.get("orgHash")
    if scope == "all":
        return True
    if scope == "unattributed":
        return event_hash is None
    if not event_hash or not current_hash:
        return False
    matches = hmac.compare_digest(event_hash, current_hash)
    return matches if scope == "current-org" else not matches


def _journey_reset_payload(
    *, project: str, stage: Optional[str], scope: str, result: PhaseHistoryResult,
    selected: int, nonce: Optional[str], dry_run: bool, reset: bool,
    rejected_removed: int = 0, no_history: bool = False,
    blocked_reason: Optional[str] = None,
) -> dict:
    stage_note = (
        "Connect, Project, and Build have no durable records; their live facts re-derive."
        if stage in ("Connect", "Project", "Build") else
        "Only validated durable Test, Deploy, and Observe records are reset."
    )
    return {
        "schemaVersion": 1,
        "mode": "journey-reset",
        "project": project,
        "filters": {"stage": stage or "all", "scope": scope},
        "selectedAcceptedRecords": selected,
        "history": {
            "status": "missing" if no_history else _journey_reset_history_status(result),
            "accepted": result.accepted, "rejected": result.rejected,
            "truncated": result.truncated,
        },
        "dryRun": dry_run,
        "reset": reset,
        "noHistory": no_history,
        "nonce": nonce,
        "backupCreated": reset,
        "rejectedRecordsRemoved": rejected_removed,
        "stageNote": stage_note,
        "liveFactsNote": (
            "Live target, project, source, and test facts relight when they re-derive; "
            "reset changes durable accepted records only."
        ),
        "confirmationRequired": bool(nonce and dry_run),
        "blocked": blocked_reason is not None,
        "blockedReason": blocked_reason,
    }


def _render_journey_reset(payload: dict) -> str:
    filters = payload["filters"]
    lines = [
        "Journey reset " + ("dry run" if payload["dryRun"] else "complete"),
        _clip_cells(f"project: {payload['project']}", _RAIL_WIDTH),
        _clip_cells(f"filters: stage={filters['stage']} scope={filters['scope']}", _RAIL_WIDTH),
        f"selected accepted records: {payload['selectedAcceptedRecords']}",
        _clip_cells(
            "history: {status} accepted={accepted} rejected={rejected} truncated={truncated}".format(
                **payload["history"]), _RAIL_WIDTH),
        _clip_cells(payload["stageNote"], _RAIL_WIDTH),
        _clip_cells(payload["liveFactsNote"], _RAIL_WIDTH),
    ]
    if payload["noHistory"]:
        lines.append("No history exists; nothing changed.")
    elif payload["blocked"]:
        lines.append(_clip_cells(f"blocked: {payload['blockedReason']}", _RAIL_WIDTH))
    elif payload["dryRun"]:
        lines += ["Explicit confirmation is required. Do not infer it.",
                  f"nonce: {payload['nonce']}"]
    else:
        lines.append(
            f"backup created; rejected records removed: {payload['rejectedRecordsRemoved']}"
        )
    return "\n".join(lines)


def cmd_journey_reset(args: list[str]) -> int:
    parsed = _journey_reset_args(args)
    if parsed is None:
        print("Usage: sf-context discovery journey reset [--stage <Connect|Project|Build|Test|Deploy|Observe>] [--scope all|current-org|other-org|unattributed] [--confirm <nonce>] [--json]", file=sys.stderr)
        return 2
    project = _journey_reset_project()
    if project is None:
        print("Journey reset requires a Salesforce DX project.", file=sys.stderr)
        return 2
    project_label, root_identity = project
    names = _phase_file_names()
    directory = _open_phase_directory(False)
    if names is None:
        print("Journey reset refused an unsafe history configuration.", file=sys.stderr)
        return 2
    if directory is None:
        try:
            Path(".sf").lstat()
        except FileNotFoundError:
            payload = _journey_reset_payload(
                project=project_label, stage=parsed["stage"], scope=parsed["scope"],
                result=_empty_phase_history(), selected=0, nonce=None, dry_run=True,
                reset=False, no_history=True)
            print(json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
                  if parsed["json"] else _render_journey_reset(payload))
            return 0
        except OSError:
            pass
        print("Journey reset refused an unsafe history path.", file=sys.stderr)
        return 2

    def missing_or_unsafe() -> tuple[bool, int]:
        try:
            if directory.relative:
                os.stat(names[0], dir_fd=directory.fd, follow_symlinks=False)
            else:
                (directory.path / names[0]).lstat()
        except FileNotFoundError:
            payload = _journey_reset_payload(
                project=project_label, stage=parsed["stage"], scope=parsed["scope"],
                result=_empty_phase_history(), selected=0, nonce=None, dry_run=True,
                reset=False, no_history=True)
            print(json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
                  if parsed["json"] else _render_journey_reset(payload))
            return True, 0
        except OSError:
            pass
        print("Journey reset refused an unsafe history entry.", file=sys.stderr)
        return True, 2

    # A dry run is a strict tree read: no persistent lock file is opened or
    # created. Confirm's nonce/preimage check closes the intervening-change gap.
    lock = None
    if parsed["confirm"] is not None:
        preliminary = _read_phase_preimage(directory)
        if preliminary is None:
            handled, code = missing_or_unsafe()
            _close_phase_directory(directory)
            return code
        lock = _acquire_phase_history_lock(directory)
        if lock is None:
            _close_phase_directory(directory)
            print("Journey reset could not acquire the phase lock.", file=sys.stderr)
            return 3
    try:
        current_hash = None
        if parsed["scope"] in ("current-org", "other-org"):
            current_hash = _current_phase_org_hash(directory)
            if current_hash is None:
                print("Journey reset scope requires a resolvable current org identity.",
                      file=sys.stderr)
                return 2
        observed = _read_phase_preimage(directory)
        if observed is None:
            _, code = missing_or_unsafe()
            return code
        preimage, identity = observed
        result = _parse_phase_history_bytes(preimage)
        if result.rejected or result.truncated:
            reasons = []
            if result.rejected:
                reasons.append(f"rejected records={result.rejected}")
            if result.truncated:
                reasons.append("history is truncated")
            blocked_reason = (
                "Reset is blocked because canonical parsing is incomplete: "
                + "; ".join(reasons) + "."
            )
            if parsed["confirm"] is not None:
                print("Journey reset blocked by rejected or truncated history; history is unchanged.",
                      file=sys.stderr)
                return 3
            payload = _journey_reset_payload(
                project=project_label, stage=parsed["stage"], scope=parsed["scope"],
                result=result, selected=0, nonce=None, dry_run=True, reset=False,
                blocked_reason=blocked_reason)
            print(json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
                  if parsed["json"] else _render_journey_reset(payload))
            return 0

        selected = sum(
            1 for record in result.records if _journey_reset_selected(
                record, parsed["stage"], parsed["scope"], current_hash)
        )
        nonce = _journey_reset_nonce(
            root_identity, parsed["stage"], parsed["scope"], preimage, current_hash
        )
        if parsed["confirm"] is None:
            payload = _journey_reset_payload(
                project=project_label, stage=parsed["stage"], scope=parsed["scope"],
                result=result, selected=selected, nonce=nonce, dry_run=True, reset=False)
            print(json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
                  if parsed["json"] else _render_journey_reset(payload))
            return 0
        if not hmac.compare_digest(parsed["confirm"], nonce):
            print("Journey reset confirmation failed because the history preimage changed.",
                  file=sys.stderr)
            return 3
        retained_records = [
            record for record in result.records
            if not _journey_reset_selected(record, parsed["stage"], parsed["scope"], current_hash)
        ]
        retained = b"".join(
            (json.dumps(record, separators=(",", ":")) + "\n").encode("utf-8")
            for record in retained_records
        )
        if not _create_phase_backup(directory, preimage):
            print("Journey reset could not durably create its required backup; history is unchanged.",
                  file=sys.stderr)
            return 3
        replace_outcome = _replace_phase_history(directory, preimage, identity, retained)
        if replace_outcome.status == _PHASE_REPLACE_UNCERTAIN:
            print(
                "Journey reset failed closed: active history state is uncertain; a durable "
                "backup exists and manual inspect/recovery is required.",
                file=sys.stderr,
            )
            return 3
        if replace_outcome.status != _PHASE_REPLACE_SUCCESS:
            print("Journey reset conflicted or failed with confirmed rollback; history is unchanged.",
                  file=sys.stderr)
            return 3
        payload = _journey_reset_payload(
            project=project_label, stage=parsed["stage"], scope=parsed["scope"],
            result=result, selected=selected, nonce=None, dry_run=False, reset=True)
        print(json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
              if parsed["json"] else _render_journey_reset(payload))
        return 0
    finally:
        _release_phase_history_lock(lock)
        _close_phase_directory(directory)


def _journey_inspection() -> dict:
    """Return a bounded, sanitized view of the durable history only."""
    present = _phase_history_present()
    result = _load_phase_history_result()
    if not present:
        status = "missing"
    elif result.rejected and not result.accepted:
        status = "corrupt"
    elif result.rejected:
        status = "partially-valid"
    else:
        status = "available"
    current_org_hash = (
        _current_phase_org_hash()
        if any(record.get("orgHash") for record in result.records)
        else None
    )
    grouped = []
    for stage in JOURNEY_STAGES:
        evidence = [_public_phase_evidence(record, current_org_hash) for record in result.records
                    if record.get("stage") == stage][-_JOURNEY_EVIDENCE_CAP:]
        grouped.append({"stage": stage, "evidence": evidence})
    return {
        "schemaVersion": 1,
        "historySchema": "phase-history/v1",
        "status": status,
        "counts": {
            "accepted": result.accepted,
            "rejected": result.rejected,
            "truncated": result.truncated,
        },
        "stages": grouped,
        "evidencePerStageLimit": _JOURNEY_EVIDENCE_CAP,
        "derivationNote": (
            "Live target, project, source, and test facts are derived separately "
            "and are not durable history records."
        ),
    }


def _render_journey_inspection(inspection: dict) -> str:
    counts = inspection["counts"]
    lines = [
        "Journey history inspection (read-only)",
        f"schema: {inspection['historySchema']}   status: {inspection['status']}",
        (f"accepted: {counts['accepted']}   rejected: {counts['rejected']}   "
         f"truncated: {str(counts['truncated']).lower()}"),
    ]
    for group in inspection["stages"]:
        evidence = group["evidence"]
        lines.append(f"{group['stage']}: {len(evidence)} shown")
        for event in evidence:
            detail = (f"  {event['type'] or '-'} {event['outcome'] or '-'} "
                      f"{event['source'] or '-'} {event['ts'] or '-'} "
                      f"scope={event['scope']}")
            lines.append(_clip_cells(detail, _RAIL_WIDTH))
    lines.append(_clip_cells(inspection["derivationNote"], _RAIL_WIDTH))
    return "\n".join(lines)


def cmd_journey(args: list[str]) -> int:
    """Print the journey signpost, inspect history, or run guarded reset."""
    if args[:1] == ["reset"]:
        return cmd_journey_reset(args[1:])
    if args in (["inspect"], ["inspect", "--json"]):
        inspection = _journey_inspection()
        if args[-1:] == ["--json"]:
            print(json.dumps(inspection, ensure_ascii=False, separators=(",", ":")))
        else:
            print(_render_journey_inspection(inspection))
        return 0
    if args not in ([], ["--json"]):
        print("Usage: sf-context discovery journey [--json] | "
              "sf-context discovery journey inspect [--json] | "
              "sf-context discovery journey reset [options]", file=sys.stderr)
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
    # "what can I do here?" is deliberately NOT here — it is a capability-catalog
    # question answered by discovery overview, not a where-am-I/rail question. See
    # _is_discovery_overview_intent.
    # "what next" / "whats next" / "what's next" / "what is next" / "what should i do next"
    r"what(?:'?s|\s+is|\s+should\s+i\s+do)?\s+next|"
    # Fuzzy-tail orientation phrasings (Lever A): still FIRST-PERSON-anchored — the honest
    # signal is the user asking about THEIR OWN position/progress, never a bare topic noun.
    # Each risky alt carries a trailing-preposition negative-lookahead so a task-scoped recap
    # ("catch me up ON the reviewer comments", "how far along am I IN the migration") stays
    # ordinary work and does not paint. A miss still falls back to the model routing + plain rail.
    r"remind\s+me\s+(?:where\s+i\s+(?:left\s+off|was)|what\s+i\s+was\s+doing)(?!\s+(?:on|with|about|in|to)\b)|"
    r"catch\s+me\s+up(?!\s+(?:on|with|about)\b)|"
    r"how\s+far\s+along\s+am\s+i(?!\s+(?:in|on|with|to)\b)|"
    r"am\s+i\s+making\s+(?:any\s+)?progress(?!\s+(?:on|with|toward|towards|in)\b)|"
    r"what\s+have\s+(?:i|we)\s+(?:done|got(?:ten)?\s+done|accomplished|completed|finished)\s+so\s+far(?!\s+(?:on|with|in|to|for|by|about)\b)|"
    r"what\s+have\s+(?:i|we)\s+accomplished(?!\s+(?:with|on|in|by|using|so)\b)|"
    r"what\s+should\s+i\s+(?:be\s+)?work(?:ing)?\s+on\b(?!\s+(?:on|with|for|in|to)\b)|"
    r"how(?:'?s|\s+is)\s+(?:my|the|our)\s+project\s+(?:going|coming(?:\s+along)?|progressing)(?!\s+to\b)|"
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
    r"\bwhere\s+(?:do\s+)?(?:things|we|i)\s+stand\b(?!\s+(?:on|with|about|against)\b)"
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


# --- Micro tier (Decision A: HYBRID) -----------------------------------------
# The macro rail is hook-rendered on the visible systemMessage channel (a pinned,
# goldened signature visual). The MICRO tier — the inner work of the CURRENT stage
# — is rendered by the MODEL, but only from a deterministic fact block the hook
# emits on the model-only additionalContext channel, never free-form. This is the
# dual-channel seam the redesign lands on (docs/design/journey-rail-two-tier-
# redesign.md): hook owns hard facts + honesty-by-construction; model owns the
# presentation (which vehicle, how to phrase). The block below carries ONLY fields
# that a writer actually persists to .sf/phase-history.jsonl — never the spike
# fixture's invented error text/counts — so the north star holds: the model cannot
# surface a fact the tracker does not have.
_MICRO_EVENT_CAP = 6   # bound the current-stage event list the block hands the model
_JOURNEY_EVIDENCE_CAP = 8  # per stage; bounds both journey JSON and inspect output


def _current_stage_substate(events: list[dict]) -> str:
    """Sub-state vocab for the CURRENT (cursor) stage, from its recorded events:
    `iterating` | `attempted` | `working` | `entered`.

    `iterating` — the terminal Observe cursor has passed evidence and remains the
    iteration cursor on a fully reached rail. `attempted` — an outcome-shaped event fired and did NOT succeed (a recorded
    `failed`): an attempt was made and did not land. `working` — some activity is
    on record for the stage but no failure (e.g. a `present` observe-skill dispatch).
    `entered` — nothing recorded yet; the cursor simply rests here. Usually the
    cursor is the first stage still lacking its `●`; the fully reached exception
    keeps Observe current so iteration can continue."""
    if any(isinstance(e, dict) and e.get("outcome") == "passed" for e in events):
        # A fully reached rail deliberately keeps Observe as the iteration cursor.
        # Do not describe its durable passed evidence as merely "working".
        return "iterating"
    if any(isinstance(e, dict) and e.get("outcome") == "failed" for e in events):
        return "attempted"
    if events:
        return "working"
    return "entered"


def _journey_micro_facts(state: dict, history: Optional[list[dict]] = None) -> dict:
    """The deterministic micro-tier fact block for the current stage.

    Drawn from the reducer `state` (for the cursor) plus the durable phase tracker
    (for the cursor stage's inner-work events). Every event field is one a writer
    genuinely persists — `type` / `outcome` / `source` — so nothing here is invented;
    error text and counts live only in the model's own turn context, never in the
    tracker, and are deliberately absent. `history` is injectable for tests; it
    defaults to the same fail-open read the reducer uses."""
    cursor = _sanitize_dynamic_text(state.get("currentStage") or JOURNEY_STAGES[0])
    hist = (_accepted_phase_records(history) if history is not None
            else _load_phase_history_result().records)
    events = [r for r in hist if r.get("stage") == cursor]
    trimmed = [
        {"type": e.get("type"), "outcome": e.get("outcome"), "source": e.get("source")}
        for e in events[-_MICRO_EVENT_CAP:]
    ]
    return {
        "schema": "journey-context/v1",
        "cursor": cursor,
        "substate": _current_stage_substate(events),
        "reached": any(e.get("outcome") == "passed" for e in events),
        "events": trimmed,
        "likely_next": _sanitize_dynamic_text(NEXT_ACTION.get(cursor, "")).strip(),
    }


def _render_journey_context_block(facts: dict) -> str:
    """Render the fact block as compact, values-only plain text for additionalContext.

    No narration and no glyph rail — the hook states facts; the model renders the
    tier. Deterministic and ANSI-free, so it is byte-reproducible and safe to golden."""
    lines = [
        "journey-context (deterministic facts from .sf/phase-history.jsonl — the "
        "plugin does not render the micro tier, you do):",
        f"  current stage: {_sanitize_dynamic_text(facts['cursor'])}",
        f"  substate: {_sanitize_dynamic_text(facts['substate'])}",
        f"  reached: {str(bool(facts.get('reached'))).lower()}",
    ]
    events = facts.get("events") or []
    if events:
        lines.append("  events on record for this stage (oldest first):")
        for ev in events:
            lines.append(
                f"    - type={_sanitize_dynamic_text(ev.get('type'))} "
                f"outcome={_sanitize_dynamic_text(ev.get('outcome'))} "
                f"source={_sanitize_dynamic_text(ev.get('source'))}"
            )
    else:
        lines.append("  events on record for this stage: none")
    lines.append(f"  likely next: {_sanitize_dynamic_text(facts['likely_next'])}")
    return "\n".join(lines)


def _journey_paint_facts(state: dict) -> str:
    """Compact bounded facts shared by orientation and status model notes."""
    stages = state.get("stages") or []
    stage = _clip(str(state.get("currentStage") or "unknown"), 32)
    # `allReached` (not a no-`future` proxy) is the only honest signal that the cursor
    # itself is reached — otherwise the cursor is the first stage still lacking evidence
    # and belongs in `no evidence`, even in the cyclical case that has no `future` stage.
    current_is_reached = bool(state.get("allReached"))
    reached = [_clip(str(s.get("name") or ""), 24) for s in stages
               if s.get("status") == "complete"
               or (s.get("status") == "current" and current_is_reached)]
    no_evidence = [_clip(str(s.get("name") or ""), 24) for s in stages
                   if s.get("status") == "future"
                   or (s.get("status") == "current" and not current_is_reached)]
    facts = _journey_micro_facts(state)
    lines = [
        f"current stage: {stage}",
        "reached: " + (", ".join(reached) or "none"),
        "no evidence: " + (", ".join(no_evidence) or "none"),
        f"substate: {_clip(str(facts.get('substate') or 'entered'), 24)}",
        "recent events: none",
    ]
    events = facts.get("events") or []
    if events:
        lines[-1] = "recent events (oldest first):"
        for event in events:
            lines.append(
                "- "
                f"type={_clip(str(event.get('type') or ''), 28)}; "
                f"outcome={_clip(str(event.get('outcome') or ''), 20)}; "
                f"source={_clip(str(event.get('source') or ''), 40)}"
            )
    lines.append(f"next action: {_clip(str(facts.get('likely_next') or ''), 88)}")
    return "\n".join(lines)


def _micro_tier_note(state: dict) -> str:
    """Backward-compatible name for the compact journey fact note."""
    return _journey_paint_facts(state)


def _orientation_paint_note(state: dict) -> str:
    """Compact facts after the visible rail paint; never repeat rendering chrome."""
    return (
        "The salesforce-development position rail is already visible.\n"
        "Do not reproduce, redraw, or restate it; do not run the journey command.\n"
        "Add only your short project-relevant interpretation when useful.\n"
        + _journey_paint_facts(state)
    )


def _status_paint_note(state: dict) -> str:
    """Compact facts after the visible status paint; never repeat rendering chrome."""
    return (
        "Salesforce status and the position rail are already visible.\n"
        "Do not reproduce, redraw, restate, or re-run status or journey.\n"
        "Add only a short project-relevant interpretation when useful.\n"
        + _journey_paint_facts(state)
    )


# The MCP status the welcome's org band reports. The banner's MCP line is a
# tri-state indicator plus the real server names from .mcp.json; a "connecting"
# status renders the honest pending "⟳ connecting" (the sf-mcp-proxy mints its JWT
# lazily on the first message, so at greeting time connectivity is pending, not
# confirmed) — the same posture the SessionStart banner takes.
_WELCOME_MCP_STATUS = "connecting via sf-mcp-proxy"


def _resolve_welcome_org(root: Path) -> Optional[dict]:
    """Probe the configured target org for the getting-started welcome's org band, or
    None when none is configured or the probe fails.

    The out-of-project welcome fires at most ONCE per session (gated on
    `_welcomed_this_session`), so — unlike an ordinary hot-path prompt — it can afford
    the one-time parallel probe (`sf org list` + `sf org display`, the same pair
    `_resolve_position_and_org` runs in a project) that turns the cheap `org: <alias>`
    config read into the FULL org band (edition · API · username · instance · MCP), so
    the welcome reads as the SAME surface as the SessionStart banner (owner direction
    2026-08-05, presentation parity). This deliberately relaxes the "no org probe
    outside a project" hot-path invariant (plan I2/I4) for this one gated, once-per-
    session surface; it is bounded and fail-soft at every step — no `sf` on PATH, no
    configured target, or any failed / empty query yields None, and the caller degrades
    to the subprocess-free `org: <alias>` line. A true newcomer with no configured
    target never probes, so the zero-org greeting stays instant."""
    if resolve_executable("sf") is None:
        return None
    alias = _configured_target_alias(root)
    if not alias:
        return None
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            list_fut = pool.submit(get_org_list)
            display_fut = pool.submit(get_org_display, alias)
            org_list_data = list_fut.result()
            org_display = display_fut.result()
    except Exception:
        # Any probe failure (timeout, CLI error, thread failure) degrades to the
        # cheap alias line — the welcome must never raise on the paint path.
        return None
    if not org_display:
        return None
    return resolve_org_info(alias, org_list=org_list_data, org_display=org_display) or None


def _welcome_org_band_content(state: dict, org: Optional[dict]) -> list:
    """The welcome's org-band content, mirroring the SessionStart banner's environment
    band so the welcome reads as the same surface (owner direction 2026-08-05). The
    DATA differs by what is known: the FULL environment block when the org was probed,
    the subprocess-free `org: <alias>` line when a target is configured but the probe
    was skipped or failed, and an explicit "none connected" line when no org is set —
    the empty org section a newcomer still sees laid out."""
    if org:
        return _environment_content(org, _WELCOME_MCP_STATUS)
    ctx = state.get("context") or {}
    alias = ctx.get("orgAlias")
    if alias and ctx.get("orgStatus") in ("configured", "configured-unprobed", "reachable"):
        # A target is set (Connect ● for a returning dev) but the full probe was
        # skipped or failed — show WHICH org honestly, with no ✓ it can't earn.
        return [[("org: ", "body"), (_clip(str(alias), _DISPLAY_NAME_LIMIT), "body")]]
    return [[("org: ", "body"), ("none connected", "muted")]]


def _welcome_project_band_content(state: dict) -> list:
    """The welcome's project-band content. Inside a project it is the banner's full
    inventory; outside one it is a single honest line — the "one piece of information"
    that there is no project here (owner direction 2026-08-05)."""
    if (state.get("context") or {}).get("project"):
        return _project_content(project_meta(), project_stats(), git_status_line())
    return [[("sfdx project: ", "body"), ("(none detected)", "muted")]]


def _render_getting_started_welcome(
    state: dict, *, org: Optional[dict] = None, color: bool = False
) -> str:
    """The once-per-scenario welcome: the HEADLESS 360 identity, the org and project
    bands, the position rail, what to say next, and the shared wayfinding footer.

    Presentation parity (owner direction 2026-08-05): out of a project the SessionStart
    banner stays silent, so THIS is the first-touch surface — and it must not look like
    a lesser thing than the in-project banner. It now paints the SAME chrome as
    `render_banner_message`: the COLORED HEADLESS lockup, the install summary
    (✓ Installed · N skills installed · library …), the rule-delimited org + project
    bands, the signpost rail, and the "you don't memorize commands · ✳ New here?"
    invitation. Only the DATA inside differs by context — the org band is the full
    probed block, a cheap `org: <alias>` line, or "none connected"; the project band is
    the real inventory or a single "(none detected)" line — and the guidance is the
    welcome's own peer CTAs rather than the banner's bare `likely next`.

    Front-of-journey redesign (D6): the welcome is a SURFACE, not a rail stage, and its
    CTAs are readiness-AGNOSTIC — they run NO environment check and never gate on
    readiness (the readiness tax is deferred to the moment the user actually connects an
    org (D9) or creates a project (D11)). Inside a project it shows the concrete `likely
    next` action. Outside a project it adapts to the EARNED Connect state (a cheap config
    read; the full org block, when shown, comes from `_resolve_welcome_org`, threaded in
    by the caller):
      - No target org (a true newcomer) → orient and offer Connect and Project as EQUAL
        next steps (neither is a prerequisite; you can scaffold and build locally with
        no org), plus one awareness heads-up naming the environment tax. Rail all-○.
      - A target org already configured (a returning developer — Connect ● / cursor at
        Project) → do NOT offer to connect or name the env tax; reflect that they are
        connected and pivot to setting up a project + "what can I do here", or
        describing what they want to build."""
    facts = _banner_provenance()
    parts: list[str] = [render_banner_block(color=color, facts=facts), ""]
    parts += render_install_summary(color, facts=facts)
    parts.append("")
    # The org + project bands share the banner's rule-region idiom; the rail rides
    # below with NO context row (include_context=False) — the bands already state the
    # org and project, so the context row would only repeat them (matching the banner).
    parts += render_bands([
        _welcome_org_band_content(state, org),
        _welcome_project_band_content(state),
    ], color=color)
    parts += ["", *_render_signpost(state, color=color, include_context=False)]
    stage = state.get("currentStage")
    in_project = bool((state.get("context") or {}).get("project"))
    if not in_project:
        create_cta = '  •  "create a Salesforce project"'
        if (state.get("context") or {}).get("orgAlias"):
            # Returning developer: an org is ALREADY set as the target (Connect ● — the
            # cursor sits at Project), so this is not a newcomer. Don't offer to connect
            # and don't name the environment tax (they have the CLI — that is how an org
            # got targeted). Pivot to picking a direction and scaffolding a project. Bullet
            # labels use the fixed width so descriptions align and lines stay ≤80 columns.
            overview_cta = '  •  "what can I do here?"'
            parts += [
                "",
                "You already have a target org set. Next, set up a project to build in:",
                f"{create_cta:<38}scaffold a new DX project",
                f"{overview_cta:<38}see what you can build here",
                "",
                "Or just describe what you want to build and we'll shape it from there.",
            ]
        else:
            # True newcomer (no target org): orient with THREE peer next steps, led by
            # DISCOVERY — "what can I do here?" is the lowest-commitment, most on-brand
            # first move (the whole POV is capability discovery) — then Connect and Project.
            # No readiness gating, no check — plus a single awareness heads-up (D6/Q1=b)
            # naming the environment tax without running any check. Fixed-width bullet
            # labels keep descriptions aligned and every line ≤80 columns.
            overview_cta = '  •  "what can I do here?"'
            connect_cta = '  •  "connect an org"'
            parts += [
                "",
                "Get started — explore, describe what you want to build, or jump in:",
                f"{overview_cta:<38}see what you can build here",
                f"{connect_cta:<38}authenticate and target an org",
                f"{create_cta:<38}scaffold a new DX project",
                "",
                "When you're ready to connect an org or start a project, you'll want your",
                "environment set up (SF CLI, Node, git) — I can check it anytime.",
            ]
    else:
        nxt = NEXT_ACTION.get(stage, "").strip()
        parts += ["", f"{'likely next':<{_JOURNEY_LABEL_WIDTH}}{nxt}"]
    # The shared invitation closes the surface (the "you don't memorize commands · ✳
    # New here?" footer), unifying it with the SessionStart banner (owner direction).
    parts += [""] + render_invitation(color)
    return "\n".join(parts)


# The HEADLESS logo shows ONCE per session, total. The marker is keyed on the
# session id and lives in the plugin's private OS runtime dir — deliberately NOT cwd-relative, so it
# survives the `/cd` from the folder where you started into a project you just
# scaffolded (those are different directories; a cwd-relative flag would forget
# and re-show the logo). Whichever surface paints the logo first — SessionStart,
# the outside-a-project welcome, or the first in-project orientation — records it,
# and the rest show just the rail. A new session (new id) greets once again.
_WELCOME_MARKER_DIR = _PROMPT_RUNTIME_DIR / "session-markers"
_CREATE_FLOW_LOCK_WAIT_SECONDS = 1.0


def _stable_project_root(root: Optional[Path] = None) -> Path:
    """Canonical project root for session markers; stable when cwd moves below it."""
    current = (root or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if candidate.joinpath("sfdx-project.json").is_file():
            return candidate
    return current


def _session_marker(session_id: str, kind: str) -> Path:
    session_key = _runtime_key(session_id)
    if kind in {"entered", "railsig"}:
        project_key = _runtime_key(os.fspath(_stable_project_root()))
        return _WELCOME_MARKER_DIR / project_key / f"{kind}-{session_key}"
    return _WELCOME_MARKER_DIR / f"{kind}-{session_key}"


def _session_marker_present(session_id: str, kind: str) -> bool:
    if not session_id:
        return False
    marker = _session_marker(session_id, kind)
    return _ensure_private_runtime_dir(marker.parent) and _private_marker_exists(marker)


def _record_session_marker(session_id: str, kind: str) -> None:
    if not session_id:
        return
    marker = _session_marker(session_id, kind)
    if _ensure_private_runtime_dir(marker.parent):
        _atomic_private_text(marker, "1")


def _welcomed_this_session(session_id: str) -> bool:
    return _session_marker_present(session_id, "welcome")


def _record_welcomed(session_id: str) -> None:
    _record_session_marker(session_id, "welcome")


# A separate per-session marker for "has the first-in-project orientation already
# fired" — so entering a project surfaces the position rail exactly once, on the
# first message that isn't itself an orientation question or an org-connect (which
# the wayfinder owns).
def _entered_this_session(session_id: str) -> bool:
    return _session_marker_present(session_id, "entered")


def _record_entered(session_id: str) -> None:
    _record_session_marker(session_id, "entered")


# A per-session marker for "the toolchain has passed a check-tools scan this
# session" — the session-scoped truth `_welcome_readiness` lights Setup from. It is
# cwd-INDEPENDENT (lives in the OS temp dir, keyed on the session id) so the verdict
# survives a `/cd` from where the scan ran into a scaffolded project, and it resets
# every new session, so readiness is honestly re-verified per session rather than
# trusted from a durable cross-session cache. The readiness-paint hook records it
# after a passing scan.
def _env_verified_this_session(session_id: str) -> bool:
    return _session_marker_present(session_id, "envready")


def _record_env_verified(session_id: str) -> None:
    _record_session_marker(session_id, "envready")


# A per-session marker for "the create-flow note has already fired this session" — so
# the project-creation moment (D11/Q4=c) hands the model its create-flow guidance (and
# its one light catalog nudge) exactly ONCE, and never re-nudges on later create-intent
# prompts (the noise the once-only rule exists to avoid). Cwd-independent like the
# other session markers, reset per session.
def _create_flow_shown_this_session(session_id: str) -> bool:
    return _session_marker_present(session_id, "createflow")


def _record_create_flow_shown(session_id: str) -> None:
    _record_session_marker(session_id, "createflow")


def _acquire_create_flow_lock(session_id: str) -> Optional[int]:
    """Bound the cross-process create-flow check→emit→record transaction.

    This session-scoped advisory lock is independent of ``rail.claim``: waiting for
    create guidance never consumes the prompt's visible-rail budget. Unsafe lock
    entries and timeout fail closed to a silent turn; a later prompt may retry.
    """
    if not isinstance(session_id, str) or not session_id:
        return None
    path = _session_marker(session_id, "createflow-lock")
    if not _ensure_private_runtime_dir(path.parent):
        return None
    flags = os.O_RDWR | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags, 0o600)
        _phase_restrict_fd(fd)
        if not _phase_private_fd(fd):
            os.close(fd)
            return None
    except OSError:
        return None

    deadline = time.monotonic() + _CREATE_FLOW_LOCK_WAIT_SECONDS
    while not _try_phase_advisory_lock(fd):
        if time.monotonic() >= deadline:
            try:
                os.close(fd)
            except OSError:
                pass
            return None
        time.sleep(0.01)
    return fd


def _release_create_flow_lock(lock: Optional[int]) -> None:
    """Release the shared advisory primitive and close its session lock fd."""
    _release_phase_history_lock(lock)


_CONNECT_INTENT = re.compile(
    r"(?ix)\b(?:connect|log\s?in|sign\s?in|authenticate|auth\b|"
    r"set\s+(?:the\s+)?(?:default\s+)?(?:target[-\s]?)?org|set\s+default|"
    r"(?:choose|pick|select|use)\s+(?:an?\s+|my\s+|the\s+)?org)\b"
)


def _is_connect_intent(prompt: str) -> bool:
    """A prompt about connecting/choosing an org — the D9/D10 connect moment. The
    plugin NEVER runs `sf org login` itself, so on this intent it does a cheap
    `sf`-on-PATH check plus local target/auth reads and hands the model a
    re-orientation note (see _connect_flow_note). The post-login wayfinder still owns
    re-orientation AFTER a real login runs, so the two never double up."""
    return isinstance(prompt, str) and bool(_CONNECT_INTENT.search(prompt))


_CREATE_PROJECT_INTENT = re.compile(
    r"(?ix)"
    # A creation verb sitting within a short window of the word "project". "set up" /
    # "setup" / "setting up" are included because "set up a project" is the most common
    # way people phrase scaffolding one — but, like every verb here, "project" must sit
    # within ~24 chars, so "set up my environment" (no nearby "project") never trips.
    r"\b(?:creat(?:e|ing)|scaffold(?:ing)?|generat(?:e|ing)|start(?:ing)?|"
    r"set(?:ting)?\s*up|spin(?:ning)?\s+up|bootstrap(?:ping)?|initializ(?:e|ing))"
    r"\b[^.\n]{0,24}?\bproject\b"
    r"|\bnew\s+(?:salesforce\s+|dx\s+)?project\b"
    r"|\bsf(?:dx)?\s+project\s+(?:generate|create)\b"
)


def _is_create_project_intent(prompt: str) -> bool:
    """A prompt about creating/scaffolding a NEW DX project — the D11 project-creation
    moment that proactively surfaces the discovery overview (once) so the user can
    pick a direction. Precision-biased: a creation verb must sit right next to the
    word "project" (so "create a custom object" / "add a field" — Build-stage work
    inside an existing project — never match), or the explicit `sf project generate`
    form."""
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 2000:
        return False
    return bool(_CREATE_PROJECT_INTENT.search(prompt))


_ENVIRONMENT_INTENT = re.compile(
    r"(?ix)"
    # A readiness verb within a short window of an environment / toolchain word …
    r"\b(?:set(?:ting)?\s*up|check(?:ing)?|verif(?:y|ying)|validat(?:e|ing)|"
    r"configur(?:e|ing)|prepar(?:e|ing)|get(?:ting)?|install(?:ing)?|fix(?:ing)?)\b"
    r"[^.\n]{0,20}?\b(?:environment|toolchain|tooling|sf\s+cli|dev(?:elopment)?\s+env)\b"
    # … or an environment/toolchain word paired with a readiness noun …
    r"|\b(?:environment|toolchain|tooling)\s+(?:check|setup|set\s*up|readiness|validation)\b"
    # … or the direct "am I set up / ready to build" and "is my env/tools ready" asks.
    r"|\bam\s+i\s+(?:set\s*up|ready\s+to\s+build)\b"
    r"|\b(?:is|are)\s+(?:my|the)\s+(?:environment|tools?|toolchain)\s+(?:ready|set\s*up|installed)\b"
)


def _is_environment_intent(prompt: str) -> bool:
    """An explicit environment-readiness ask ("set up / check / verify my environment",
    "am I set up?", "is my toolchain ready?"). The environment check is a STAGE-INDEPENDENT
    capability (it left the rail in D5) — the ~9s check-tools scan surfaced by the readiness
    banner — so it earns its own direct trigger, independent of Connect and Project (which
    merely CALL it when applicable: Connect when `sf` is absent (D9), Project at create time
    (D11)). Precision-biased: a readiness verb must sit next to an environment/toolchain word,
    so "set up a project" (no env word) routes to create-intent, not here, and "connect an
    org" is untouched. The ~9s scan never runs in the hook (I4); this only steers the model
    to the on-demand check."""
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 2000:
        return False
    return bool(_ENVIRONMENT_INTENT.search(prompt))


_OVERVIEW_INTENT = re.compile(
    r"(?ix)what\s+can\s+i\s+do\s+here|"
    r"what\s+can\s+(?:this|it|the\s+plugin)\s+do|"
    r"what\s+are\s+my\s+options"
)


def _is_discovery_overview_intent(prompt: str) -> bool:
    """A capability-catalog question ("what can I do here?"), not a position
    question. The discovery skill/command owns the overview render, so the paint
    hook steps aside here — it never substitutes the journey rail for this ask."""
    return isinstance(prompt, str) and bool(_OVERVIEW_INTENT.search(prompt))


def _is_getting_started_intent(prompt: str) -> bool:
    """Side A (outside a project): the conservative trigger. The plugin is global,
    so in an arbitrary directory we surface the welcome only when the prompt names
    Salesforce — an explicit signal of intent — and never on a locator question."""
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 2000:
        return False
    if _LOCATOR_EXCLUSION.search(prompt):
        return False
    return "salesforce" in prompt.lower()


def _welcome_readiness() -> str:
    """Coarse, near-free environment-readiness signal — a PATH lookup plus a
    session-marker stat, NO subprocess (the on-demand-only scan invariant holds).
    After the front-of-journey redesign this no longer lights a rail stage or gates
    the welcome; its live consumer is the D9 connect cheap-check (_connect_flow_note),
    which routes to environment setup when `sf` is "absent" rather than letting an
    interactive `sf org login` crash into `command not found`. Three states:

    - "absent"      — the SF CLI isn't on PATH, so the environment is definitively
                      not ready; connecting an org can't proceed until setup runs.
    - "ready"       — the toolchain passed a `check-tools` scan THIS session (the
                      readiness-paint hook records a session-scoped marker on the
                      pass), so we don't re-nag for the rest of the session.
    - "unverified"  — `sf` is present but no pass has been recorded this session;
                      nudge the model to run the environment check before scaffolding.

    Environment readiness is a CURRENT property, not a historical one: a toolchain
    can drift between sessions (Node upgraded, the CLI moved) and a project can be
    old while its environment is no longer where it needs to be. So "ready" is scoped
    to THIS session (via `_CURRENT_SESSION_ID` + the per-session marker) and re-earned
    each session — never trusted from a durable cross-session cache. Honesty
    invariant: only a real pass THIS session yields "ready"; an absent marker (new
    session, or no pass yet) is unverified, never a pass."""
    if resolve_executable("sf") is None:
        return "absent"
    if _env_verified_this_session(_CURRENT_SESSION_ID):
        return "ready"
    return "unverified"


# The zero-org newcomer (D10c) can't get a first org from the CLI — that is a web
# signup. Minimal honest pointer only; the full hand-off is the (still-proposed)
# first-org onboarding flow (docs/design/first-org-onboarding-proposal.md).
_FIRST_ORG_SIGNUP_URL = "https://developer.salesforce.com/signup"


def _connect_flow_note(root: Path) -> str:
    """Model-facing guidance for a connect-org intent (D9/D10).

    Rides additionalContext ONLY — never a painted Tier-1 surface (painting stays the
    SessionStart banner and the post-login wayfinder). Cheap and subprocess-free: a
    PATH lookup for `sf` (via _welcome_readiness) plus the local target-org / auth-
    history reads, and it NEVER runs `sf org login` — an interactive browser auth flow
    is neither cheap nor silent, and letting a missing `sf` crash into `command not
    found` is the ugliest failure to "let happen". The cheap check catches the exact
    failure we care about — `sf` absent — BEFORE any login is attempted.

    Four honest outcomes:
      - `sf` absent          → route to environment setup (no login attempt).
      - target already set   → nothing to connect; confirm and proceed.
      - no target, has auth  → the D10 (a)/(b) ternary (existing org / scratch org).
      - no target, no auth   → D10 (c): the zero-org newcomer — a minimal pointer to a
                               free Developer Edition web signup, then return.
    """
    if _welcome_readiness() == "absent":
        return (
            "The user wants to connect an org, but the Salesforce CLI (`sf`) is NOT on their PATH — an "
            "`sf org login` would fail with `command not found`. Do NOT attempt a login. First get the "
            "environment ready: run the platform-environment-validate skill (or the "
            "/salesforce-development:setup command) to install and verify the SF CLI, Node, and git, "
            "then connect once `sf` resolves."
        )
    if _has_target_org(root):
        return (
            "The user mentioned connecting an org, but one is ALREADY set as the target here (a local "
            "or global default). There is nothing to connect — confirm the current target and continue "
            "with their actual request; only run a login if they explicitly ask to switch to a "
            "different org (the post-connect wayfinder re-orients if they do)."
        )
    if _has_authed_org():
        return (
            "The user wants to connect an org and `sf` is installed, but none is set as the target "
            "here. Guide them — do NOT run `sf org login` yourself: (a) authenticate or reuse an "
            "existing org and set it as the target (the /salesforce-development:login command wraps "
            "`sf org login web --set-default`); or (b) create a scratch org via the dx-org-manage "
            "skill, which REQUIRES an authenticated Dev Hub (it surfaces NoDefaultEnvFound without "
            "one). They have authenticated an org before, so (a) is the likely fit. The post-login "
            "wayfinder re-orients automatically once a login runs."
        )
    return (
        "The user wants to connect an org, `sf` is installed, but they have no target org set and no "
        "authenticated org on record — most likely a newcomer with no Salesforce org yet. The suite "
        "CANNOT create a first org (that is a web signup, not a CLI step), so do NOT fabricate an "
        "in-suite provisioning step and do NOT attempt a login. Point them, briefly and honestly, to "
        "sign up for a free Developer Edition org at " + _FIRST_ORG_SIGNUP_URL + " , then come back "
        "and connect it (the /salesforce-development:login command, or `sf org login web`) — the "
        "wayfinder re-orients on their return."
    )


def _welcome_note(state: dict) -> str:
    """Model-facing note when the getting-started welcome paints on the visible
    channel — orients the model and keeps its reply tight, without reprinting the
    welcome or racing ahead of the flow.

    Front-of-journey redesign (D6): readiness-AGNOSTIC. Outside a project the model
    offers connecting an org and creating a project as EQUAL next steps and must NOT
    run an environment/tooling check now — the readiness tax is deferred to the
    moment the user actually connects (D9) or creates a project (D11)."""
    base = (
        "The salesforce-development getting-started welcome has just been displayed to the user on "
        "the visible channel (the HEADLESS 360 identity, their position on the journey, and what to "
        "say next). Do NOT reproduce or redraw the welcome — it is already shown. Keep your reply to "
        "one or two sentences. Do NOT enumerate a list of things they could build, and do NOT launch a "
        "multiple-choice menu — the welcome already shows the next actions; let them answer in their "
        "own words."
    )
    in_project = bool((state.get("context") or {}).get("project"))
    if not in_project:
        if (state.get("context") or {}).get("orgAlias"):
            # Returning developer: a target org is already configured, so Connect is
            # earned and the cursor rests at Project. They are NOT a newcomer — do not
            # re-offer connecting or run a check; pivot to setting up a project (D6
            # refinement: treat the configured global default as legitimate).
            return base + (
                " They ALREADY have a target org set, so they are not a newcomer and Connect is "
                "done — do NOT offer to connect an org, do NOT run `sf org login`, and do NOT run an "
                "environment or tooling check. Steer them toward setting up a PROJECT to build in: "
                "help them describe what they want to build, surface what they can do here (the "
                "capability overview), and move toward scaffolding a DX project. Touch org "
                "connection only if they explicitly ask to switch to a different org."
            )
        return base + (
            " They have not connected an org or created a project yet. Offer THREE peer next steps: "
            "exploring what they can build here (the capability overview — \"what can I do here?\"), "
            "connecting an org, and creating a project — none is a prerequisite of the others — or "
            "simply help them describe what they want to build. Leading with discovery is fine (it is "
            "the lowest-commitment first step). Do NOT run an environment or tooling check now, and do "
            "NOT push project creation as a prerequisite: environment readiness is confirmed only when "
            "the user actually moves to connect an org or create a project, not at this greeting."
        )
    stage = _sanitize_dynamic_text(state.get("currentStage", "?"))
    nxt = _sanitize_dynamic_text(NEXT_ACTION.get(stage, "")).strip()
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


def _overview_paint_note() -> str:
    """Model-facing note when the capability overview paints on the visible channel.

    The overview is a Tier-1 surface — the plugin displays it directly to the user,
    like the SessionStart banner — so, unlike the rail's reproduce-then-read
    contract, the model must NOT reproduce it. It adds only its own read."""
    return (
        "The salesforce-development capability overview (\"what you can do here\": the release/counts "
        "line and the two capability groups — installed, and available to add) has just been displayed "
        "to the user on the visible channel. It is already shown — do NOT reproduce, redraw, or re-run "
        "the discovery overview command. Add only your own short read: what these capabilities mean for "
        "the work in front of the user right now, the single most useful next step, and — when no org is "
        "connected — the concrete value of connecting. Never invent or recompute a count or label, and "
        "never present this generic catalog as if it were already tailored to the user's org."
    )


def _create_flow_note() -> str:
    """Model-facing note for the project-creation moment (D11/Q4=c). The user asked to
    CREATE a project, so the OUTCOME they want is a scaffolded project — the hook does
    NOT paint the capability catalog here (dumping the full overview read as a
    non-sequitur to a directive "set me up a new project"). Instead the model drives the
    scaffold and drops ONE light, optional nudge that the catalog is browsable. The
    deferred readiness tax still lands here: creating a project needs a working
    toolchain, so the model verifies the environment first — a MODEL-turn scan (the ~9s
    check never runs in a hook, I4; cmd_scaffold_gate is the cheap PreToolUse backstop
    on the actual `sf project generate`)."""
    return (
        "The user asked to create / set up a new Salesforce project — the OUTCOME they want is a "
        "scaffolded DX project, so drive toward that; do NOT stop at describing options or dump the "
        "capability catalog. Two steps: (1) creating a project needs a working toolchain — first verify "
        "the environment by running the platform-environment-validate skill (or the "
        "/salesforce-development:setup command) to confirm the SF CLI, Node, and git and install "
        "anything missing BEFORE scaffolding, so a missing prerequisite surfaces here with a reason "
        "rather than as a raw failure at generate time; (2) help them pick a DIRECTION for what they're "
        "building, map it to a project template, and scaffold it. As you begin, add ONE light, optional "
        "nudge — a single sentence — that they can explore the full capability catalog by saying \"what "
        "can I do here?\" as they think about what to build; keep it a brief aside, not the main thread, "
        "and do NOT reproduce or recompute the catalog."
    )


def _environment_check_note() -> str:
    """Model-facing note for an explicit environment-readiness intent ("set up / check my
    environment", "am I set up?"). The environment check is STAGE-INDEPENDENT — the ~9s
    check-tools scan surfaced by the readiness banner — so it has its own direct trigger,
    not owned by any rail stage. Connect (when `sf` is absent) and Project (at create time)
    route here too, but the user can also ask for it outright. Steer the model to the single
    chokepoint; the scan runs on demand via the skill/command, never in this hook (I4)."""
    return (
        "The user wants to set up or check their development environment. Run the "
        "platform-environment-validate skill (or the /salesforce-development:setup command) — the single "
        "~9s readiness check that verifies the SF CLI, Node, npm, git, the Salesforce MCP servers, and "
        "source tracking, then paints the readiness banner listing anything that needs attention. Do NOT "
        "hand-roll the individual tool checks yourself (that command is the one chokepoint), and do NOT "
        "gate their other work on it unless they asked — environment readiness is a precondition, not a "
        "journey stage."
    )


def _render_overview_paint(root: Path) -> Optional[str]:
    """Render the discovery overview block for the paint hook, or None on any
    failure (the caller then stays silent and the model falls back to routing to
    the overview command and reproducing its plain stdout — today's behavior).

    The overview is org-neutral and performs no target-org or CLI reads. The catalog
    renderer is imported lazily and only here, so an ordinary turn never pays for it.

    color=True: this is the visible-systemMessage paint path, so it carries the
    overview's 16-color palette (theme-adaptive, defined in discovery_catalog).
    The palette self-strips under NO_COLOR and is deliberately independent of the
    banner's truecolor gate (_banner_color_enabled); the command path stays plain
    because _print_overview renders with color off."""
    try:
        try:
            from discovery_catalog import render_overview_text
        except ImportError:
            import importlib.util
            module_path = Path(__file__).resolve().parent / "discovery_catalog.py"
            spec = importlib.util.spec_from_file_location("sf_discovery_catalog", module_path)
            if spec is None or spec.loader is None:
                return None
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            render_overview_text = module.render_overview_text
        plugin_root = Path(__file__).resolve().parent.parent
        return render_overview_text(plugin_root, cwd=root, org_presence=None, color=True)
    except Exception:
        return None


def _prompt_rail_allowed(context: Optional[PromptContext]) -> bool:
    """Claim valid state; unavailable state fails open toward duplicate guidance."""
    return context is None or _claim_prompt_rail(context)


def cmd_prompt_dispatch() -> int:
    """The sole UserPromptSubmit handler: read once, establish turn, route in-process."""
    payload = _read_hook_payload()
    has_native_prompt = bool(payload.get("prompt_id") or payload.get("promptId"))
    context = _prompt_context(payload, rotate_fallback=not has_native_prompt)
    _prune_prompt_runtime(context)
    return cmd_orientation_paint(payload=payload, prompt_context=context)


def cmd_orientation_paint(payload: Optional[dict] = None,
                          prompt_context: Optional[PromptContext] = None) -> int:
    """UserPromptSubmit routing and paint, invoked in-process by prompt-dispatch.

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
        if payload is None:
            payload = _read_hook_payload()
            has_native_prompt = bool(payload.get("prompt_id") or payload.get("promptId"))
            prompt_context = _prompt_context(
                payload, rotate_fallback=not has_native_prompt)
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
                state, org = _resolve_position_and_org(root)
                # Live MCP health here too, so a re-asked "where am I?" reflects
                # real reachability rather than a stale sidecar (matches /status).
                mcp_active_org = (org.get("alias"), org.get("username")) if org else None
                surface = render_status_surface(
                    state, org, project_meta(), project_stats(), git_status_line(),
                    _live_mcp_summary(active_org=mcp_active_org),
                    color=color, logo=show_logo,
                )
                if not _prompt_rail_allowed(prompt_context):
                    print(json.dumps({"continue": True}))
                    return 0
                emit("UserPromptSubmit", _status_paint_note(state), system_message=surface)
                _record_entered(session_id)
                if show_logo:
                    _record_welcomed(session_id)
                _record_rail_signature(session_id, state)
                return 0

            # A positional orientation question paints just the rail — the logo on
            # the first surface of the session, the rail thereafter.
            if _is_orientation_question(prompt):
                if show_logo:
                    # The welcome now paints the full banner chrome (org + project
                    # bands), so resolve the org once here — _resolve_position_and_org
                    # returns both the state and the org dict, so the band is not a
                    # second probe. The bare-rail else-branch never needs the org dict.
                    state, org = _resolve_position_and_org(root)
                    message = _welcome_note(state)
                    surface = "\n" + _render_getting_started_welcome(state, org=org, color=color)
                else:
                    state = _journey_state()
                    message = _orientation_paint_note(state)
                    surface = "\n" + _render_journey_rail(state, color=color)
                if not _prompt_rail_allowed(prompt_context):
                    print(json.dumps({"continue": True}))
                    return 0
                emit("UserPromptSubmit", message, system_message=surface)
                _record_entered(session_id)
                if show_logo:
                    _record_welcomed(session_id)
                _record_rail_signature(session_id, state)
                return 0

            # An explicit environment-readiness intent ("set up / check my environment").
            # The environment check is stage-independent (it left the rail in D5); route the
            # model to the on-demand check (the ~9s scan never runs in this hook — I4).
            # Checked before connect so "set up my environment" is not mistaken for anything
            # else. Model-facing only; mark entered so the ambient rail doesn't also fire.
            if _is_environment_intent(prompt):
                note = _environment_check_note()
                emit("UserPromptSubmit", note)
                _record_entered(session_id)
                return 0

            # An org-connect intent (D9/D10). The plugin NEVER runs `sf org login`
            # itself, so instead of staying silent we do the cheap `sf`-on-PATH check
            # + local target/auth reads and hand the model the re-orientation note
            # (model-facing only — painting stays the SessionStart banner and the
            # post-login wayfinder). Mark entered so the ambient rail doesn't also fire.
            if _is_connect_intent(prompt):
                note = _connect_flow_note(root)
                emit("UserPromptSubmit", note)
                _record_entered(session_id)
                return 0

            # A capability-catalog question ("what can I do here?"): paint the
            # overview block itself on the visible channel — the Tier-1 surface, like
            # the SessionStart banner. The plugin displays it directly and the model
            # adds only its read (see _overview_paint_note); it never reproduces it.
            # Colored per the owner mocks: _render_overview_paint renders with the
            # 16-color palette (theme-adaptive, self-stripping under NO_COLOR), which
            # rides this always-on visible channel independent of the banner's
            # truecolor gate (_banner_color_enabled). Mark entered so the ambient rail
            # never intercepts an overview ask. On any render failure
            # _render_overview_paint returns None and we stay silent, so the model
            # falls back to routing to the overview command and reproducing its
            # plain stdout — today's behavior.
            if _is_discovery_overview_intent(prompt):
                block = _render_overview_paint(root)
                if block is not None:
                    note = _overview_paint_note()
                    emit("UserPromptSubmit", note, system_message="\n" + block)
                    _record_entered(session_id)
                else:
                    print(json.dumps({"continue": True}))
                return 0

            # First non-orientation, non-connect message after entering the project:
            # surface the rail once as ambient orientation. Needs a session id to
            # dedupe — without one, stay silent (never nudge every turn).
            if not session_id or _entered_this_session(session_id):
                print(json.dumps({"continue": True}))
                return 0
            if show_logo:
                # First-surface welcome in-project: resolve the org once (state + org
                # dict together) so the welcome's org band is the full probed block,
                # matching the SessionStart banner.
                state, org = _resolve_position_and_org(root)
                surface = "\n" + _render_getting_started_welcome(state, org=org, color=color)
            else:
                state = _journey_state()
                surface = "\n" + _render_journey_rail(state, color=color)
            ambient = _ambient_surface(
                surface, state, project_name=project_meta().get("name") or root.name
            )
            if ambient is None:
                print(json.dumps({"continue": True}))
                return 0
            if not _prompt_rail_allowed(prompt_context):
                print(json.dumps({"continue": True}))
                return 0
            emit("UserPromptSubmit", _entered_note(state), system_message=ambient)
            _record_entered(session_id)
            if show_logo:
                _record_welcomed(session_id)
            _record_rail_signature(session_id, state)
            return 0

        # Side A — outside a project. A capability question ("what can I do here?")
        # is a solicited answer, not an unsolicited banner, so it MAY paint here — but
        # only once the plugin has already been tripped this session (the HEADLESS
        # welcome/logo has shown, i.e. _welcomed). Same discipline as the logo: no
        # trip, no paint. Colored via the same palette as the in-project paint.
        #
        # Untripped, we deliberately do NOT return here — fall through to the
        # getting-started check below. An overview ask can ALSO name Salesforce
        # ("what can I do here with Salesforce?"), which matches _is_getting_started
        # too; that naming IS the trip, so it must reach the welcome rather than be
        # swallowed silently. A render failure likewise falls through — and there
        # _welcomed is already True, so the check below is silent (no re-welcome).
        if _is_discovery_overview_intent(prompt) and _welcomed_this_session(session_id):
            block = _render_overview_paint(Path.cwd().resolve())
            if block is not None:
                emit("UserPromptSubmit", _overview_paint_note(),
                     system_message="\n" + block)
                return 0

        # Side A — outside a project: an orientation question ("where am I") paints
        # just the position rail, but — like the overview above — only once the
        # plugin has been tripped this session (welcomed). Untripped, orientation
        # phrasing alone is not a Salesforce cue (the plugin is global), so it stays
        # silent. When it fires, the rail rides the visible systemMessage channel
        # (its greened cursor survives — the accent is embedded via _green, not the
        # gated palette) and the model note stops it re-running the journey command
        # or reprinting the rail. Tier-1, the same contract as in-project: without
        # this branch the model serviced "where am I" itself (ran the command, then
        # reproduced its stripped-plain stdout), which double-printed a colorless rail.
        if _is_orientation_question(prompt) and _welcomed_this_session(session_id):
            state = _journey_state()
            surface = "\n" + _render_journey_rail(state, color=_banner_color_enabled())
            if not _prompt_rail_allowed(prompt_context):
                print(json.dumps({"continue": True}))
                return 0
            emit("UserPromptSubmit", _orientation_paint_note(state), system_message=surface)
            _record_rail_signature(session_id, state)
            return 0

        # Side A — outside a project: an explicit environment-readiness intent ("set up /
        # check my environment"), gated on welcomed like the asks above — untripped, a bare
        # "set up my environment" in a random dir is not a Salesforce cue, so it stays
        # silent. Routes the model to the stage-independent on-demand check (I4: the ~9s
        # scan never runs here). Checked before connect so the phrasing is never conflated.
        if _is_environment_intent(prompt) and _welcomed_this_session(session_id):
            emit("UserPromptSubmit", _environment_check_note())
            return 0

        # Side A — outside a project: a connect-org intent (D9/D10), but — like the
        # overview and orientation asks above — only once the plugin has been tripped
        # this session (welcomed). This is the core newcomer path: they said "build on
        # Salesforce" (the welcome trips the session), then "connect an org". We hand
        # the model the same cheap-check + ternary re-orientation note (model-facing
        # only, no paint); untripped, a bare "connect" in a random dir is not a
        # Salesforce cue, so it stays silent. The plugin still never runs the login.
        if _is_connect_intent(prompt) and _welcomed_this_session(session_id):
            emit("UserPromptSubmit", _connect_flow_note(Path.cwd().resolve()))
            return 0

        # Side A — outside a project: a create-a-project intent (D11/Q4=c). The user asked
        # to CREATE a project, so the OUTCOME is a scaffolded project — the hook does NOT
        # paint the capability catalog here (dumping the full overview read as a non-sequitur
        # to a directive "set me up a new project"). It hands the model the create-flow note,
        # which drives env-verify → pick a direction → scaffold and adds ONE light, optional
        # nudge that the catalog is browsable ("what can I do here?"). Model-facing only, no
        # paint — so there is nothing to render and no fail-open block. Gated on welcomed
        # (tripped) and fired at most once per session, so a follow-up create-intent doesn't
        # re-nudge; "what can I do here?" still paints the full overview on demand via the
        # overview branch above.
        if (_is_create_project_intent(prompt) and _welcomed_this_session(session_id)):
            # The marker is the overwhelmingly common post-first-use path. Avoid a
            # filesystem lock on every later create-like prompt, while retaining the
            # under-lock recheck that makes concurrent first contenders emit once.
            if _create_flow_shown_this_session(session_id):
                print(json.dumps({"continue": True}))
                return 0
            create_flow_lock = _acquire_create_flow_lock(session_id)
            if create_flow_lock is None:
                print(json.dumps({"continue": True}))
                return 0
            try:
                # Another hook process may have emitted while this contender waited.
                if _create_flow_shown_this_session(session_id):
                    print(json.dumps({"continue": True}))
                    return 0
                note = _create_flow_note()
                emit("UserPromptSubmit", note)
                _record_create_flow_shown(session_id)
                return 0
            finally:
                _release_create_flow_lock(create_flow_lock)

        # Side A — outside a project: only a Salesforce mention surfaces the
        # welcome, and only once per scenario (then ordinary turns are untouched).
        if not _is_getting_started_intent(prompt) or _welcomed_this_session(session_id):
            print(json.dumps({"continue": True}))
            return 0
        state = _journey_state()
        # Presentation parity (owner direction 2026-08-05): the welcome now paints the
        # full banner chrome (colored lockup, install summary, org + project bands, the
        # wayfinding footer). When a target org is configured, resolve it ONCE here so
        # the org band is the full probed block; a true newcomer with no target never
        # probes and pays nothing (_resolve_welcome_org fails soft to the cheap alias
        # line). Front-of-journey redesign (D6): the welcome's CTAs stay readiness-
        # AGNOSTIC — they offer connect/create as peers with a single awareness heads-up
        # and run NO environment check (that tax is deferred to D9 connect / D11 create).
        org = _resolve_welcome_org(Path.cwd().resolve())
        surface = "\n" + _render_getting_started_welcome(
            state, org=org, color=_banner_color_enabled()
        )
        ambient = _ambient_surface(surface, state, project_name="no project")
        if ambient is None:
            print(json.dumps({"continue": True}))
            return 0
        if not _prompt_rail_allowed(prompt_context):
            print(json.dumps({"continue": True}))
            return 0
        emit("UserPromptSubmit", _welcome_note(state), system_message=ambient)
        _record_welcomed(session_id)
        _record_rail_signature(session_id, state)
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
    # Tier-C signal: an observe skill ran this turn. Persist it durably (append-only,
    # fail-silent) so it can surface in the micro-tier "activity" fact line. It does
    # NOT move the ◉ cursor and NEVER lights Observe's `●`: the reducer reads only
    # `outcome == "passed"` events (a Tier-A/B fact) and ignores this `present`
    # dispatch entirely — a skill dispatch is intent, not proof (signal ladder).
    if bare in _OBSERVE_DISPATCH_SKILLS:
        _record_phase_event("Observe", "present", source="cmd_resolution_trace", event_type="observe-skill")
    mode = _ui_mode()
    if mode == "off":
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
        color=_banner_color_enabled() and mode != "plain",
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
    # Every catalog mode is offline and org-neutral. Passing None preserves the JSON
    # compatibility field as the stable value "unknown" without fabricating state.
    return run_discovery(
        args, plugin_root=Path(__file__).resolve().parent.parent, org_presence=None
    )


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
    if cmd == "readiness-paint":
        return cmd_readiness_paint()
    if cmd == "readiness-banner":
        return cmd_readiness_banner()
    if cmd == "discovery":
        return cmd_discovery(sys.argv[2:])
    if cmd == "post-deploy":
        return cmd_post_deploy()
    if cmd == "post-bash":
        return cmd_post_bash()
    if cmd == "post-deploy-failure":
        return cmd_post_deploy_failure()
    if cmd == "post-observe":
        return cmd_post_observe()
    if cmd == "post-test-run":
        return cmd_post_test_run()
    if cmd == "skills-first-advisory":
        return cmd_skills_first_advisory()
    if cmd == "scaffold-gate":
        return cmd_scaffold_gate()
    if cmd == "resolution-trace":
        return cmd_resolution_trace()
    if cmd == "record-skill-dispatch":
        return cmd_record_skill_dispatch()
    if cmd == "prompt-dispatch":
        return cmd_prompt_dispatch()
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
    if cmd == "journey-paint":
        return cmd_journey_paint()
    if cmd in ("telemetry", "telemetry-capture", "telemetry-flush", "telemetry-transmit"):
        # Stream A (capture): consent-gated, scrubbed, local-only usage-telemetry.
        # Stream B (flush/transmit): detached O11y-PDP upload through the org.
        # All telemetry logic lives in the sibling module to keep this file focused.
        # Route through _load_sf_telemetry() (bare import + by-path fallback) so the
        # dispatch resolves the sibling even under importlib-based tests / after a
        # chdir, exactly like the other telemetry entry points in this file.
        # Defense-in-depth: _load_sf_telemetry() is written to never raise, but wrap
        # the call too so a future regression can't turn a hook or `telemetry off` into
        # a traceback — treat any failure as "module unavailable".
        try:
            sf_telemetry = _load_sf_telemetry()
        except Exception:
            sf_telemetry = None
        if sf_telemetry is None:
            # The hook subcommands are optional — silently no-op so a missing telemetry
            # module never breaks a hook. But the USER-FACING consent command must fail
            # CLOSED and loud: reporting success for `telemetry off` without actually
            # opting out would be a broken hard-off promise.
            if cmd == "telemetry":
                print("Telemetry controls are unavailable: the telemetry module could not "
                      "be loaded. No change was made.", file=sys.stderr)
                return 1
            return 0  # capture/flush/transmit hooks: optional, never fail the hook
        return sf_telemetry.dispatch(sys.argv)
    print(f"Unknown command: {cmd}", file=sys.stderr)
    print("Usage: sf-context [detect|discovery|verify-org|check-tools|readiness-paint|readiness-banner|post-bash|post-deploy|post-deploy-failure|skills-first-advisory|scaffold-gate|resolution-trace|record-skill-dispatch|prompt-dispatch|feedback-nudge|record-feedback-decision|record-update-decision|status|status-org|status-project|wayfinder|orientation-rail|journey-paint|telemetry|telemetry-capture|telemetry-flush|telemetry-transmit]", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
