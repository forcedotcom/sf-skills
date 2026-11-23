#!/usr/bin/env python3
"""Require grounding instructions before Salesforce grounding MCP operations.

This is a workflow dependency check, not an authorization boundary. State is
per Claude session and is granted only by a successful Skill result, never by
an attempted dispatch. No org access, credentials, or model calls are used.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile

SKILL = "platform-metadata-grounding-get"
QUALIFIED_SKILL = "salesforce-development:" + SKILL
OPERATIONS = {"searchmetadata", "querymetadata", "describemetadata"}
DIRECT_SERVERS = {"metadatagrounding", "salesforcemetadatagrounding"}
DISPATCH_SERVERS = {"salesforce", "salesforceheadless360", "headless360"}


def canonical(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower()) if isinstance(value, str) else ""


def is_grounding(tool: object, args: object) -> bool:
    if not isinstance(tool, str) or not tool.startswith("mcp__"):
        return False
    parts = tool.split("__")
    if len(parts) != 3:
        return False
    server, operation = canonical(parts[1]), canonical(parts[2])
    if server in DIRECT_SERVERS:
        return operation in OPERATIONS
    if server not in DISPATCH_SERVERS or operation not in {"dispatch", "dispatchreadonly", "describe"}:
        return False
    if not isinstance(args, dict):
        return False
    return canonical(args.get("operationId", args.get("operation_id"))) in OPERATIONS


def requested_skill(payload: dict) -> str:
    args = payload.get("tool_input")
    skill = args.get("skill", "") if isinstance(args, dict) else ""
    return skill if skill in {SKILL, QUALIFIED_SKILL} else ""


def successful_skill_result(response: object) -> bool:
    if isinstance(response, dict):
        if response.get("is_error") or response.get("isError") or response.get("error"):
            return False
        return (response.get("success") is True
                and response.get("commandName") in {SKILL, QUALIFIED_SKILL})
    if isinstance(response, str):
        return response.strip() in {
            "Launching skill: " + SKILL,
            "Launching skill: " + QUALIFIED_SKILL,
        }
    return False


def state_path(session_id: str, config_dir: Path) -> Path:
    digest = hashlib.sha256(session_id.encode()).hexdigest()
    return config_dir / "metadata-grounding-guard" / (digest + ".json")


def read_state(path: Path) -> dict:
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def write_state(path: Path, value: dict) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as f:
            tmp = Path(f.name)
            json.dump(value, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)


def deny(reason: str) -> dict:
    return {"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": "[metadata-grounding-guard] " + reason,
    }}


def mode_from_env(env: dict) -> str:
    raw = env.get("SF_PLUGIN_SKILLS_FIRST", "").strip()
    if not raw:
        raw = env.get("CLAUDE_PLUGIN_OPTION_SKILLS_FIRST", "").strip()
    return raw.lower() if raw.lower() in {"enforce", "advisory", "off"} else "enforce"


def redirect(reason: str, mode: str) -> dict:
    if mode == "advisory":
        return {"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": "[metadata-grounding-guard] " + reason,
        }}
    return deny(reason)


def handle(payload: object, config_dir: Path, skill_file: Path, mode: str = "enforce") -> dict:
    if mode == "off":
        return {}
    if not isinstance(payload, dict):
        return {}
    event, tool = payload.get("hook_event_name"), payload.get("tool_name")
    args = payload.get("tool_input") or {}
    targeted = event == "PreToolUse" and is_grounding(tool, args)
    session = payload.get("session_id")
    if not isinstance(session, str) or not session:
        return redirect("Grounding instructions cannot be verified: the host supplied no session_id.", mode) if targeted else {}
    path = state_path(session, config_dir)
    if event in {"SessionStart", "PostCompact", "SessionEnd"}:
        path.unlink(missing_ok=True)
        return {}
    if event == "PostToolUse" and tool == "Skill" and requested_skill(payload):
        if successful_skill_result(payload.get("tool_response")):
            write_state(path, {"loaded": True, "skill": SKILL,
                              "source_sha256": hashlib.sha256(skill_file.read_bytes()).hexdigest(),
                              "skill_tool_use_id": payload.get("tool_use_id")})
        return {}
    if not targeted:
        return {}
    if not skill_file.is_file():
        return redirect("The grounding skill file is missing from the installed plugin. Repair the plugin before using grounding.", mode)
    state = read_state(path)
    if (state.get("loaded") is True
            and state.get("source_sha256") == hashlib.sha256(skill_file.read_bytes()).hexdigest()):
        return {}
    return redirect(
        "Load the installed " + QUALIFIED_SKILL + " skill successfully, then retry this "
        "grounding operation using its instructions. This check does not select a data route; "
        "other tools remain available.", mode
    )


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            raise ValueError("Expected a hook object")
    except (ValueError, OSError):
        print("The grounding skill check received malformed host input.", file=sys.stderr)
        return 2
    config = Path(os.environ.get("CLAUDE_CONFIG_DIR", str(Path.home() / ".claude")))
    skill_file = Path(__file__).resolve().parents[1] / "skills" / SKILL / "SKILL.md"
    mode = mode_from_env(os.environ)
    try:
        result = handle(payload, config, skill_file, mode)
    except OSError:
        if payload.get("hook_event_name") != "PreToolUse":
            print("Could not update grounding skill state.", file=sys.stderr)
            return 2
        result = redirect("The host could not read or update grounding skill state. Repair the session before retrying.", mode)
    if result:
        print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
