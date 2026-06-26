#!/usr/bin/env python3
"""Render the declared action tree as a box-drawing summary.md.

Called by finalize.py (cold path) and cache_check.py (hit path when the
cached summary is missing). Mirrors the old agent Phase 7 render_tree()
logic verbatim.

Usage:
    python3 summarize_tree.py <tree_json_path> <out_md_path> <built_at_utc>

Inputs:
    argv[1]   absolute path to declared_action_tree.json (or similar)
    argv[2]   output .summary.md path (overwritten atomically)
    argv[3]   ISO-8601 UTC built-at timestamp (e.g. 2026-04-25T14:00:00Z)

Outputs:
    argv[2]   rendered markdown
    exit 0    success
    exit 1    missing args, read failure, write failure
"""
import json
import os
import pathlib
import sys

KC_ORDER = [
    "BOT_DEFINITION", "TOPIC", "GEN_AI_FUNCTION",
    "FLOW", "APEX", "PROMPT_TEMPLATE",
    "STANDARD_ACTION", "UNKNOWN",
]


def render_tree(node, prefix="", is_last=True, lines=None, agent_=None):
    if lines is None:
        lines = []
    connector = "└── " if is_last else "├── "
    kind = node.get("kind", "?")
    api = node.get("api_name", "?")
    elem = node.get("element_name")
    if kind == "BOT_DEFINITION":
        v = (agent_ or {}).get("version") or ""
        label = f"[{kind}] {api}" + (f" ({v})" if v else "")
    elif kind == "GEN_AI_FUNCTION":
        unwraps = node.get("unwraps_to") or {}
        uk = unwraps.get("kind")
        un = unwraps.get("api_name")
        arrow = f" → {uk}:{un}" if uk and un else ""
        label = f"[{kind}] {api}{arrow}"
    elif kind in ("STANDARD_ACTION", "UNKNOWN"):
        # Canonical key is `invocation_type` (schema 3.1+); fall back to
        # the two legacy keys so caches built by an older parse_wave still
        # render the qualifier.
        raw = (
            node.get("invocation_type")
            or node.get("raw_invocation_type")
            or node.get("raw_action_type")
            or ""
        )
        label = f"[{kind}] {api}" + (f" ({raw})" if raw else "")
    else:
        label = f"[{kind}] {api}"
    if elem and kind != "BOT_DEFINITION":
        label += f"  — element:{elem}"
    lines.append(prefix + connector + label)
    children = node.get("children") or []
    child_prefix = prefix + ("    " if is_last else "│   ")
    for i, c in enumerate(children):
        render_tree(c, child_prefix, i == len(children) - 1, lines, agent_)
    return lines


def main() -> int:
    if len(sys.argv) != 4:
        sys.stderr.write(
            "summarize_tree.py: usage: python3 summarize_tree.py <tree_json_path> "
            "<out_md_path> <built_at_utc>\n"
        )
        return 1

    tree_path = pathlib.Path(sys.argv[1])
    out_path = pathlib.Path(sys.argv[2])
    built_at = sys.argv[3]

    try:
        tree = json.loads(tree_path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        sys.stderr.write(f"summarize_tree.py: cannot read {tree_path}: {e}\n")
        return 1

    a = tree.get("agent", {}) or {}
    kc = tree.get("_kind_counts", {}) or {}

    lines = [
        f"# {a.get('api_name', '?')} {a.get('version', '?')} — declared action tree",
        "",
        f"- **Bot ID:** `{a.get('bot_id', '?')}`",
        f"- **Master label:** {a.get('master_label', '?')}",
        f"- **Generation:** {a.get('generation', 'unknown')}",
        f"- **Planner:** `{a.get('planner_name', '?')}` ({a.get('planner_type', '?')})",
        f"- **Version auto-picked:** {a.get('_version_auto_picked', False)}",
        f"- **Built at (UTC):** {built_at}",
        f"- **Node count:** {tree.get('node_count', 0)}",
        f"- **Depth:** {tree.get('depth', 0)}",
        f"- **Partial:** {tree.get('_partial', False)}",
        "",
        "## Kind counts",
        "",
    ]
    for k in KC_ORDER:
        lines.append(f"- `{k}`: {kc.get(k, 0)}")

    lines += [
        "",
        "## Declared action tree",
        "",
        "```",
    ]
    root = tree.get("root") or {"kind": "BOT_DEFINITION", "api_name": a.get("api_name", "?"), "children": []}
    lines.extend(render_tree(root, "", True, None, a))
    lines.append("```")

    if tree.get("_unresolved"):
        lines += ["", "## Unresolved", ""]
        for u in tree["_unresolved"]:
            lines.append(
                f"- `{u.get('kind')}`/`{u.get('api_name')}` — {u.get('reason')}"
            )

    content = "\n".join(lines) + "\n"

    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = out_path.with_suffix(out_path.suffix + ".tmp")
        tmp.write_text(content)
        os.replace(tmp, out_path)
    except OSError as e:
        sys.stderr.write(f"summarize_tree.py: write failed: {e}\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
