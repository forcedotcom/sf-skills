#!/usr/bin/env python3
"""First-run setup: grant allowlist rules + seed runtime dir + touch sentinel.

Idempotent. Called by the skill's Phase 0 on first invocation (sentinel
absent). On every subsequent run the skill skips calling this script
entirely because the sentinel file already exists.

Three actions:
 1. Merge the canonical rules into ~/.claude/settings.json permissions.allow.
    Only adds missing entries; preserves any rules already present.
    Atomic write: staged tmp file in the same directory + os.replace().
    On corrupt JSON, the original is copied aside to .corrupt.backup and
    the script exits 2 without modifying anything — Claude Code refusing
    to start on a blanked permission list is worse than refusing to grant.
 2. mkdir -p ~/.claude/data/investigating-agentforce-d360/ + write .gitignore
    (`*`) iff the current content is not already exactly `*`. STDM artifacts
    carry org-specific ids and user content; preventing accidental git
    commits is load-bearing.
 3. Touch the versioned sentinel at
    ~/.claude/.investigating-agentforce-d360.allowlist-done.v1
    (suffix tracks the rule-set version — bump on rule changes so existing
    installs re-run grant to pick up new rules).

Usage:
    python3 ~/.claude/skills/investigating-agentforce-d360/tools/grant_allowlist.py

Inputs:
    none (all paths hardcoded under $HOME/.claude/)

Outputs:
    side effects: settings.json rewritten, data/.gitignore seeded,
                  sentinel touched
    stdout: one progress line per action
    exit 0: full success (including "nothing to do" when all rules present)
    exit 1: write failure (disk full, permission denied)
    exit 2: settings.json unparseable (refuses to wipe)
"""
from __future__ import annotations

import json
import os
import pathlib
import shutil
import sys
import tempfile

HOME = pathlib.Path.home()
SETTINGS = HOME / ".claude" / "settings.json"
DATA = HOME / ".claude" / "data" / "investigating-agentforce-d360"
SKILL = HOME / ".claude" / "skills" / "investigating-agentforce-d360"

# Bump sentinel suffix when NEEDED changes so existing installs re-run
# grant to pick up new rules.
SENTINEL = HOME / ".claude" / ".investigating-agentforce-d360.allowlist-done.v1"
LEGACY_SENTINELS: list[pathlib.Path] = []

# Canonical allowlist rules. Every skill path is scoped — no blanket
# python3:*. The shell-introspection block (ls/grep/head/tail/wc/stat)
# scopes to the skill + data dirs to avoid leaking access elsewhere.
# `~` isn't expanded by the permission matcher — literal absolute paths.
NEEDED: list[str] = [
    # skill source + data: full RW on dir itself AND descendants
    f"Read({SKILL})",
    f"Read({SKILL}/**)",
    f"Edit({SKILL}/**)",
    f"Write({SKILL}/**)",
    f"Read({DATA})",
    f"Read({DATA}/**)",
    f"Write({DATA}/**)",

    # first-time bootstrap: mkdir the roots themselves and any descendants
    f"Bash(mkdir -p {SKILL})",
    f"Bash(mkdir -p {SKILL}/**)",
    f"Bash(mkdir -p {DATA})",
    f"Bash(mkdir -p {DATA}/**)",

    # /tmp — scratch for ad-hoc work
    "Read(/tmp/**)",
    "Write(/tmp/**)",
    "Bash(ls /tmp/**)",
    "Bash(ls -lh /tmp/**)",
    "Bash(cat /tmp/**)",
    "Bash(head * /tmp/**)",
    "Bash(head -c * /tmp/**)",
    "Bash(tail * /tmp/**)",
    "Bash(rm -f /tmp/**)",
    "Bash(rm -rf /tmp/sf-*)",
    "Bash(cat > /tmp/* <<*)",

    # python entrypoints (any args)
    f"Bash(python3 {SKILL}/scripts/*.py:*)",

    # sf CLI — single shape used by scripts/dc.py
    "Bash(sf org display --target-org * --json)",

    # read-only shell introspection within the two dirs
    f"Bash(ls {DATA})",
    f"Bash(ls {DATA}/**)",
    f"Bash(ls {SKILL})",
    f"Bash(ls {SKILL}/**)",
    f"Bash(grep * {DATA}/**)",
    f"Bash(grep * {SKILL}/**)",
    f"Bash(head * {DATA}/**)",
    f"Bash(head * {SKILL}/**)",
    f"Bash(tail * {DATA}/**)",
    f"Bash(tail * {SKILL}/**)",
    f"Bash(wc -l {DATA}/**)",
    f"Bash(wc -l {SKILL}/**)",
    f"Bash(stat * {DATA}/**)",
    f"Bash(stat * {SKILL}/**)",
]

# Rules to drop on each grant pass. Empty in v1; populated on rule-set changes.
LEGACY_RULES_TO_REMOVE: list[str] = []


def _load_settings() -> dict:
    """Load ~/.claude/settings.json. Corrupt JSON → exit 2, don't overwrite."""
    if not SETTINGS.is_file():
        print(f"grant_allowlist: creating {SETTINGS}")
        return {}
    try:
        return json.loads(SETTINGS.read_text())
    except json.JSONDecodeError as e:
        backup = SETTINGS.with_suffix(".json.corrupt.backup")
        shutil.copy2(SETTINGS, backup)
        print(
            f"grant_allowlist: settings.json unparseable ({e}); backed up to "
            f"{backup}; refusing to write.",
            file=sys.stderr,
        )
        sys.exit(2)


def _atomic_write(path: pathlib.Path, content: str) -> None:
    """Write content to path atomically (tmp in same dir + os.replace)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "w") as f:
            f.write(content)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def merge_allowlist() -> int:
    settings = _load_settings()
    perms = settings.setdefault("permissions", {})
    allow = perms.setdefault("allow", [])
    if not isinstance(allow, list):
        print(
            "grant_allowlist: permissions.allow is not a list; refusing to overwrite.",
            file=sys.stderr,
        )
        sys.exit(2)

    # Drop legacy rules. Idempotent — second run finds nothing to remove.
    removed: list[str] = []
    for legacy in LEGACY_RULES_TO_REMOVE:
        while legacy in allow:
            allow.remove(legacy)
            removed.append(legacy)

    existing = set(allow)
    added = [r for r in NEEDED if r not in existing]

    if not added and not removed:
        print(f"grant_allowlist: all {len(NEEDED)} rules already present")
        return 0

    allow.extend(added)
    _atomic_write(SETTINGS, json.dumps(settings, indent=2) + "\n")
    if added:
        print(f"grant_allowlist: merged {len(added)} new rule(s) into {SETTINGS}")
        for r in added:
            print(f"  + {r}")
    if removed:
        print(f"grant_allowlist: removed {len(removed)} legacy rule(s) from {SETTINGS}")
        for r in removed:
            print(f"  - {r}")
    return len(added) + len(removed)


def seed_data_gitignore() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    gi = DATA / ".gitignore"
    if gi.is_file() and gi.read_text().strip() == "*":
        print(f"grant_allowlist: {gi} already correct")
        return
    gi.write_text("*\n")
    print(f"grant_allowlist: seeded {gi}")


def touch_sentinel() -> None:
    SENTINEL.parent.mkdir(parents=True, exist_ok=True)
    SENTINEL.touch()
    print(f"grant_allowlist: touched sentinel {SENTINEL}")
    # Clean up legacy sentinel paths so subsequent runs trigger re-grant
    # on the next version bump without leaving stale files around.
    for legacy in LEGACY_SENTINELS:
        if legacy.is_file():
            try:
                legacy.unlink()
                print(f"grant_allowlist: removed legacy sentinel {legacy}")
            except OSError:
                pass


def main() -> int:
    try:
        merge_allowlist()
        seed_data_gitignore()
        touch_sentinel()
    except OSError as e:
        print(f"grant_allowlist: I/O error: {e}", file=sys.stderr)
        return 1
    print("grant_allowlist: done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
