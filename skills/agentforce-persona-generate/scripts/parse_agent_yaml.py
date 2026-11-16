#!/usr/bin/env python3
"""Parse an Agent Script .agent file and return a normalized dict.

READ-ONLY. This script never writes back to the source file. It opens the
file, walks the structure, and returns a normalized Python dict that the
SKILL.md flow can iterate over without caring about the file's exact YAML
nesting.

Usage:
    python3 parse_agent_yaml.py <path-to-.agent-file>

Output (stdout): JSON-formatted normalized structure.

Normalized shape:
    {
        "system": {
            "instructions": str,
            "welcome": str,
            "error": str,
        },
        "config": {
            "developer_name": str,
            "agent_label": str,
            "agent_type": str,
            ...
        },
        "subagents": [
            {
                "name": str,
                "description": str,
                "instructions": str | None,
                "reasoning_instructions": str | None,
                "system_override": str | None,
                "actions": [{"name": str, "progress_indicator_message": str | None}, ...]
            },
            ...
        ],
        "actions_global": [{"name": str, "progress_indicator_message": str | None}, ...],
    }

The skill uses this structure to:
- SCORE: traverse subagents and actions, score per layer
- ENCODE (brownfield): produce a proposed-new-file with only persona-bearing
  fields modified, preserving everything else exactly as the source had it.

Note on Agent Script syntax: .agent files are YAML-LIKE but use directive
syntax (`->`, `|`, `system:`, `subagent name:`) that isn't strict YAML. This
parser does best-effort regex-based extraction targeted at the persona-bearing
fields the skill needs. For full Agent Script parsing, refer to the
developing-agentforce skill in forcedotcom/sf-skills.
"""

import json
import re
import sys
from pathlib import Path

# An indented body: indented lines, plus blank lines that sit between them.
_BODY = r"(?:[ \t]+\S.*\n?|[ \t]*\n(?=[ \t]+\S))*"


def parse_agent_file(path: Path) -> dict:
    """Parse an .agent file and return normalized structure. Read-only."""
    text = path.read_text(encoding="utf-8")

    return {
        "system": _extract_system(text),
        "config": _extract_config(text),
        "subagents": _extract_subagents(text),
        "actions_global": [],  # Global actions are rare; usually nested under subagents.
    }


def _extract_block(text: str, header: str) -> str | None:
    """Extract a top-level block (system, config, etc.) by indent boundary.

    Returns the block content (lines after the header, dedented) or None if
    the header isn't present.
    """
    lines = text.splitlines()
    in_block = False
    block_indent: int | None = None
    block_lines: list[str] = []

    for line in lines:
        if not in_block:
            stripped = line.strip()
            if stripped == header or stripped == f"{header}:":
                in_block = True
                continue
        else:
            if not line.strip():
                block_lines.append(line)
                continue
            indent = len(line) - len(line.lstrip())
            if block_indent is None:
                block_indent = indent
            if indent < block_indent and line.strip():
                # Dedent below the block — we're out.
                break
            block_lines.append(line[block_indent:] if len(line) >= block_indent else line)

    return "\n".join(block_lines).rstrip() if block_lines else None


def _extract_field(block: str | None, key: str) -> str | None:
    """Extract a `key: value` or `key: |` literal-block field from a block."""
    if not block:
        return None

    # Try literal block scalar first: key: |\n    text...
    # or a procedural block, as in Agent Script reasoning: key: ->\n    | text
    pattern_literal = rf"^{re.escape(key)}:\s*(?:\||->)\s*\n({_BODY})"
    m = re.search(pattern_literal, block, flags=re.MULTILINE)
    if m:
        return _dedent(m.group(1)).rstrip()

    # Try inline string: key: "value" or key: value
    pattern_inline = rf'^{re.escape(key)}:\s*"?([^"\n]*?)"?\s*$'
    m = re.search(pattern_inline, block, flags=re.MULTILINE)
    if m:
        val = m.group(1).strip()
        return val if val else None

    return None


def _dedent(text: str) -> str:
    """Strip the common leading whitespace from every line."""
    lines = text.splitlines()
    indents = [len(l) - len(l.lstrip()) for l in lines if l.strip()]
    if not indents:
        return text
    common = min(indents)
    return "\n".join(l[common:] if len(l) >= common else l for l in lines)


def _extract_system(text: str) -> dict:
    block = _extract_block(text, "system")
    if not block:
        return {"instructions": None, "welcome": None, "error": None}

    # messages is a sub-block
    messages_block = _extract_block(block, "messages")

    return {
        "instructions": _extract_field(block, "instructions"),
        "welcome": _extract_field(messages_block, "welcome"),
        "error": _extract_field(messages_block, "error"),
    }


def _extract_config(text: str) -> dict:
    block = _extract_block(text, "config")
    if not block:
        return {}

    return {
        "developer_name": _extract_field(block, "developer_name"),
        "agent_label": _extract_field(block, "agent_label"),
        "description": _extract_field(block, "description"),
        "agent_type": _extract_field(block, "agent_type"),
        # default_agent_user belongs under `access:`; older files had it under `config:`.
        "default_agent_user": _extract_field(_extract_block(text, "access"), "default_agent_user")
        or _extract_field(block, "default_agent_user"),
    }


def _extract_subagents(text: str) -> list[dict]:
    """Find each `start_agent NAME:` and `subagent NAME:` block and extract its
    persona-bearing fields. A focused agent has only a `start_agent` block."""
    # Match block declarations and capture name + body (blank lines inside stay in it)
    pattern = rf"^(?:start_agent|subagent)\s+(\w+):\s*\n({_BODY})"
    subagents: list[dict] = []

    for match in re.finditer(pattern, text, flags=re.MULTILINE):
        name = match.group(1)
        body = _dedent(match.group(2))

        system_override_block = _extract_block(body, "system")
        reasoning_block = _extract_block(body, "reasoning")

        subagents.append({
            "name": name,
            "description": _extract_field(body, "description"),
            "system_override": _extract_field(system_override_block, "instructions"),
            "reasoning_instructions": _extract_field(reasoning_block, "instructions"),
            "actions": _extract_subagent_actions(body),
        })

    return subagents


def _extract_subagent_actions(subagent_body: str) -> list[dict]:
    """Extract per-action progress_indicator_message from a subagent's actions: block."""
    actions_block = _extract_block(subagent_body, "actions")
    if not actions_block:
        return []

    actions: list[dict] = []
    # Action declarations are like: `action_name:` followed by indented properties
    pattern = rf"^(\w+):\s*\n({_BODY})"
    for match in re.finditer(pattern, actions_block, flags=re.MULTILINE):
        name = match.group(1)
        body = _dedent(match.group(2))
        actions.append({
            "name": name,
            "progress_indicator_message": _extract_field(body, "progress_indicator_message"),
        })

    return actions


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: parse_agent_yaml.py <path-to-.agent-file>", file=sys.stderr)
        return 1

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        return 1

    parsed = parse_agent_file(path)
    print(json.dumps(parsed, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
