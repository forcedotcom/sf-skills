#!/usr/bin/env python3
"""Classify agentforce-adlc installation state without exposing registry data.

Live skill registration is checked by the coordinator's qualified Skill-tool
dispatch. This helper is used only after that dispatch is unknown, so its
read-only registry result selects resumable install, enable, or reload guidance.
It never treats installation as proof that the owning skill is invocable.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from typing import Any


CHECKPOINT = "Help Agent — Agentforce dependency preflight"
PLUGIN_NAME = "agentforce-adlc"
SAFE_PLUGIN_ID = re.compile(r"^agentforce-adlc@[A-Za-z0-9._-]+$")

EXIT_CODES = {
    "installed_enabled": 10,
    "installed_disabled": 11,
    "missing": 12,
    "inconclusive": 13,
}


def _emit(registry_state: str, summary: str, remediation: str, plugin_id: str | None = None) -> int:
    payload = {
        "checkpoint": CHECKPOINT,
        "registryState": registry_state,
        "pluginId": plugin_id,
        "summary": summary,
        "remediation": remediation,
        "liveCapabilityVerified": False,
        "resumeCheckpoint": CHECKPOINT,
    }
    print(json.dumps(payload, separators=(",", ":")))
    return EXIT_CODES[registry_state]


def _parse_registry(raw: str) -> list[dict[str, Any]] | None:
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(parsed, list) or not all(isinstance(entry, dict) for entry in parsed):
        return None
    return parsed


def run_preflight(timeout_seconds: int) -> int:
    if shutil.which("claude") is None:
        return _emit(
            "inconclusive",
            "The Claude plugin registry command is unavailable, so agentforce-adlc installation state could not be determined.",
            "Repair the Claude Code plugin environment, or verify/install or enable agentforce-adlc explicitly, then reload plugins and resume this checkpoint.",
        )

    try:
        result = subprocess.run(
            ["claude", "plugin", "list", "--json"],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            env=os.environ.copy(),
        )
    except (OSError, subprocess.TimeoutExpired):
        return _emit(
            "inconclusive",
            "The Claude plugin registry could not be read conclusively.",
            "Repair the Claude Code plugin environment, or verify/install or enable agentforce-adlc explicitly, then reload plugins and resume this checkpoint.",
        )

    if result.returncode != 0:
        return _emit(
            "inconclusive",
            "The Claude plugin registry command failed without a trustworthy agentforce-adlc result.",
            "Repair the Claude Code plugin environment, or verify/install or enable agentforce-adlc explicitly, then reload plugins and resume this checkpoint.",
        )

    registry = _parse_registry(result.stdout)
    if registry is None:
        return _emit(
            "inconclusive",
            "The Claude plugin registry returned malformed data, so agentforce-adlc installation state could not be determined.",
            "Repair or update Claude Code, then verify/install or enable agentforce-adlc, reload plugins, and resume this checkpoint.",
        )

    matches: list[tuple[str, bool]] = []
    for entry in registry:
        plugin_id = entry.get("id")
        enabled = entry.get("enabled")
        if not isinstance(plugin_id, str) or plugin_id.partition("@")[0] != PLUGIN_NAME:
            continue
        if not SAFE_PLUGIN_ID.fullmatch(plugin_id) or not isinstance(enabled, bool):
            return _emit(
                "inconclusive",
                "The matching agentforce-adlc registry entry was not safe to classify.",
                "Inspect the plugin registry locally, reconcile the agentforce-adlc entry, reload plugins, and resume this checkpoint.",
            )
        matches.append((plugin_id, enabled))

    if not matches:
        return _emit(
            "missing",
            "No installed agentforce-adlc plugin entry was found.",
            "Install agentforce-adlc through the guarded salesforce-development plugin-install flow, reload plugins, and resume this checkpoint.",
        )

    if len(matches) != 1:
        return _emit(
            "inconclusive",
            "Multiple agentforce-adlc registry entries were found, so the owning plugin could not be selected safely.",
            "Reconcile the duplicate plugin installations, reload plugins, and resume this checkpoint.",
        )

    plugin_id, enabled = matches[0]
    if enabled:
        return _emit(
            "installed_enabled",
            "agentforce-adlc is installed and enabled, but the qualified skill is not registered in this session.",
            "Run /reload-plugins (or restart the host if reload does not expose the skill), then resume this checkpoint.",
            plugin_id,
        )

    return _emit(
        "installed_disabled",
        "agentforce-adlc is installed but disabled.",
        f"With explicit approval, enable {plugin_id}, run /reload-plugins, and resume this checkpoint.",
        plugin_id,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout-seconds", type=int, default=15, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.timeout_seconds < 1:
        parser.error("--timeout-seconds must be at least 1")
    return run_preflight(args.timeout_seconds)


if __name__ == "__main__":
    sys.exit(main())
