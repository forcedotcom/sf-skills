#!/usr/bin/env python3
"""Verify that a copied Salesforce Development Codex package is self-contained."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


REQUIRED_FILES = frozenset({
    ".claude-plugin/plugin.json",
    ".codex-plugin/plugin.json",
    ".mcp.json",
    "scripts/codex_mcp_launcher.py",
    "scripts/codex_mcp_bootstrap.py",
    "scripts/codex_mcp_diagnostics.py",
    "scripts/codex_hooks.py",
    "scripts/codex_edit_advisory.py",
    "scripts/codex_startup.py",
    "scripts/codex_command_surface.py",
    "scripts/sf-deploy-gate",
    "scripts/sf_telemetry.py",
    "scripts/sf_shim.py",
    "scripts/telemetry-flush.js",
    "hooks/codex-hooks.json",
    "bin/lsp-precheck",
    "bin/lsp-precheck.bundled.js",
    "scripts/sf-context",
    "scripts/sf_context.py",
    "scripts/sf-mcp-proxy.bundled.js",
    "bin/sf-lsp-host.bundled.js",
    "catalog/plugins.json",
})
EXPECTED_SERVERS = frozenset({
    "salesforce-metadata-experts", "salesforce-metadata-grounding",
    "salesforce-headless-360", "salesforce-lsp",
})
EXPECTED_COMMANDS = frozenset({
    "discover", "feedback", "login", "logout", "org", "plugin-install",
    "plugin-recommendations", "project", "reset-source-tracking", "set-default",
    "setup", "status", "telemetry", "welcome",
})


def _inert_feedback(body: str) -> bool:
    return ('unsupported' in body and 'Explain this limitation and stop.' in body
            and 'Do not ask for a' in body
            and not any(token in body for token in
                        ('/commands/feedback.md', 'feedback-eligibility', 'feedback-record')))


def _load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def verify(plugin_root: Path, require_command_projection: bool = False) -> dict[str, int | str]:
    root = plugin_root.resolve(strict=True)
    failures: list[str] = []
    for relative in sorted(REQUIRED_FILES):
        if not (root / relative).is_file():
            failures.append(f"missing installed file: {relative}")

    for relative in ("scripts/sf-context", "scripts/sf-deploy-gate", "bin/lsp-precheck"):
        if (root / relative).is_file() and not os.access(root / relative, os.X_OK):
            failures.append(f"installed entrypoint is not executable: {relative}")

    codex = _load(root / ".codex-plugin/plugin.json")
    claude = _load(root / ".claude-plugin/plugin.json")
    if codex.get("version") != claude.get("version"):
        failures.append("Codex and Claude manifest versions differ")
    if codex.get("skills") != "./skills/":
        failures.append("Codex manifest does not use the installed skills tree")
    if codex.get("commands") != "./codex-commands/":
        failures.append("Codex manifest does not select its command adapters")
    command_dir = root / "codex-commands"
    if {p.stem for p in command_dir.glob('*.md')} != EXPECTED_COMMANDS:
        failures.append("Codex adapter set differs from the expected fourteen surfaces")
    projected = root / ".codex-plugin/migrated-command-skills"
    for name in sorted(EXPECTED_COMMANDS):
        adapter = command_dir / (name + '.md')
        if not (root / 'commands' / (name + '.md')).is_file():
            failures.append(f"missing shared command workflow: {name}")
        if not adapter.is_file():
            continue
        body = adapter.read_text(encoding='utf-8')
        if '$ARGUMENTS' in body:
            failures.append(f"unmigratable argument token in Codex adapter: {name}")
        if name != 'feedback' and f'/commands/{name}.md' not in body:
            failures.append(f"missing shared workflow reference: {name}")
        if name == 'feedback' and not _inert_feedback(body):
            failures.append("feedback adapter does not preserve inert collection behavior")
        skill = projected / ('source-command-' + name) / 'SKILL.md'
        if require_command_projection and not skill.is_file():
            failures.append(f"missing migrated command surface: {name}")
        if skill.is_file():
            if skill.resolve().parents[3] != root:
                failures.append(f"migrated command layout cannot resolve installed root: {name}")
            generated = skill.read_text(encoding='utf-8')
            if len(generated.encode('utf-8')) > 4000:
                failures.append(f"migrated command exceeds verified host byte limit: {name}")
            if name != 'feedback' and f'/commands/{name}.md' not in generated:
                failures.append(f"migrated command lost shared workflow reference: {name}")
            if name == 'feedback' and not _inert_feedback(generated):
                failures.append("migrated feedback surface lost its unsupported boundary")
    servers = codex.get("mcpServers")
    if not isinstance(servers, dict) or set(servers) != EXPECTED_SERVERS:
        failures.append("Codex MCP server set differs from the supported server set")
    else:
        bootstrap = root / "scripts/codex_mcp_bootstrap.py"
        if bootstrap.is_file():
            source = bootstrap.read_text(encoding="utf-8")
            for name, server in sorted(servers.items()):
                if server.get("args") != ["-I", "-c", source, name]:
                    failures.append(f"Codex MCP bootstrap differs from its source: {name}")
                if "cwd" in server:
                    failures.append(f"Codex MCP entry must not set cwd: {name}")

    file_count = 0
    for directory, directory_names, file_names in os.walk(root, followlinks=False):
        current = Path(directory)
        for name in directory_names:
            if (current / name).is_symlink():
                failures.append(f"directory symlink in artifact: {(current / name).relative_to(root)}")
        for name in file_names:
            file_count += 1
            if (current / name).is_symlink():
                failures.append(f"file symlink in artifact: {(current / name).relative_to(root)}")
    skill_count = sum(1 for path in (root / "skills").iterdir() if path.is_dir())
    if skill_count == 0:
        failures.append("installed artifact has no skills")
    if failures:
        raise ValueError("; ".join(failures))
    return {"version": str(codex["version"]), "files": file_count, "skills": skill_count,
            "command_adapters": len(EXPECTED_COMMANDS), "feedback_collection": "unsupported"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("plugin_root", type=Path)
    parser.add_argument('--require-command-projection', action='store_true')
    args = parser.parse_args()
    print(json.dumps(verify(args.plugin_root, args.require_command_projection), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
