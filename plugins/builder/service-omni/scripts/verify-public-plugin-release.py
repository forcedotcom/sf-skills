#!/usr/bin/env python3
"""Fail closed when a publishable plugin tree is unsafe or misidentified.

Minimal counterpart to salesforce-development's verify-public-plugin-release.py:
Source checks enforce full canonical directory parity. Copied public trees have
SoR sidecars removed and may already have sanitized frontmatter, so destination
checks enforce the roster, public visibility, and absence of SoR files instead.
Both modes enforce release-tree safety invariants (no symlinks/special files, no stray transient dev directories,
bounded size) and that plugin.json identifies this exact plugin before its
tree is copied into the public marketplace repo.
"""
from __future__ import annotations

import argparse
import json
import re
import stat
import sys
from pathlib import Path
from typing import Optional

# The release workflow can bootstrap with ``cp -r`` after this process exits.
# Never create untracked bytecode that a later copy could accidentally publish.
sys.dont_write_bytecode = True

_TRANSIENT_DIRS = {"__pycache__", ".pytest_cache", ".sf"}
_MAX_ENTRIES = 4096
_MAX_DEPTH = 32
_MAX_FILE_BYTES = 16 * 1024 * 1024
_MAX_TOTAL_BYTES = 128 * 1024 * 1024


class ReleaseGateError(Exception):
    pass


def _scan(plugin_root: Path) -> int:
    """Walk the release tree, rejecting anything unsafe to publish verbatim."""
    count = 0
    total_bytes = 0

    def visit(directory: Path, relative: Path, depth: int) -> None:
        nonlocal count, total_bytes
        if depth > _MAX_DEPTH:
            raise ReleaseGateError(f"{relative}: release tree depth limit exceeded")
        for child in sorted(directory.iterdir(), key=lambda p: p.name):
            count += 1
            if count > _MAX_ENTRIES:
                raise ReleaseGateError("publishable release tree entry limit exceeded")
            child_relative = relative / child.name
            if child.name in _TRANSIENT_DIRS:
                raise ReleaseGateError(f"{child_relative}: transient directory is not publishable")
            metadata = child.lstat()
            if stat.S_ISDIR(metadata.st_mode):
                visit(child, child_relative, depth + 1)
            elif stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1:
                total_bytes += metadata.st_size
                if metadata.st_size > _MAX_FILE_BYTES:
                    raise ReleaseGateError(f"{child_relative}: release file byte limit exceeded")
                if total_bytes > _MAX_TOTAL_BYTES:
                    raise ReleaseGateError("publishable release tree total byte limit exceeded")
            else:
                raise ReleaseGateError(
                    f"{child_relative}: publishable release tree contains a link or special file"
                )

    visit(plugin_root, Path(), 0)
    return count


def verify(plugin_root: Path, authoring_root: Path, public_root: Optional[Path] = None) -> dict[str, int]:
    plugin_root = Path(plugin_root).resolve(strict=True)
    manifest_path = plugin_root / ".claude-plugin" / "plugin.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReleaseGateError(f"cannot read {manifest_path}") from exc

    expected_name = "service-omni"
    if not isinstance(manifest, dict):
        raise ReleaseGateError("plugin.json must contain an object")
    actual_name = manifest.get("name")
    if plugin_root.name != expected_name or actual_name != expected_name:
        raise ReleaseGateError(
            f"plugin.json name {actual_name!r} does not match directory {expected_name!r}"
        )

    file_count = _scan(plugin_root)
    roster_path = plugin_root / "scripts/skill-roster.json"
    try:
        roster = json.loads(roster_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReleaseGateError(f"cannot read {roster_path}") from exc
    if not isinstance(roster, list) or not roster or any(
            not isinstance(name, str) or not re.fullmatch(r"service-omni-[a-z0-9-]+", name)
            for name in roster) or len(set(roster)) != len(roster):
        raise ReleaseGateError("expected a nonempty roster of unique Omni skills")
    if sorted(p.name for p in (plugin_root / "skills").iterdir()) != sorted(roster):
        raise ReleaseGateError("skill roster mismatch")
    authoring_root = Path(authoring_root).resolve(strict=True)
    # The workflow also passes public-root to the source pre-copy check; the
    # source tree keeps its SoR sidecars and must still get full parity.
    public_tree = public_root is not None and plugin_root != authoring_root.parent / "plugins/builder/service-omni"
    for name in roster:
        canonical = authoring_root / name
        mirror = plugin_root / "skills" / name
        _scan(canonical)
        skill_path = canonical / "SKILL.md"
        try:
            skill_text = skill_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise ReleaseGateError(f"cannot read {skill_path}") from exc
        header = re.match(r"\A---[ \t]*\r?\n(.*?)^---[ \t]*\r?$",
                          skill_text, re.MULTILINE | re.DOTALL)
        if header is None:
            raise ReleaseGateError(f"{name}: missing or malformed SKILL.md frontmatter")
        frontmatter = header.group(1)
        if not re.search(r'sf-skills:[ \t]*\n[ \t]+visibility:[ \t]*(?:"public"|\'public\'|public)[ \t]*(?:#.*)?$', frontmatter, re.MULTILINE):
            raise ReleaseGateError(f"{name}: canonical sf-skills visibility is not public")
        if public_tree:
            if any(mirror.rglob("sor.yaml")):
                raise ReleaseGateError(f"{name}: internal sor.yaml is not publishable")
            if not (mirror / "SKILL.md").is_file():
                raise ReleaseGateError(f"{name}: missing SKILL.md")
            continue
        source_paths = {p.relative_to(canonical) for p in canonical.rglob("*")}
        mirror_paths = {p.relative_to(mirror) for p in mirror.rglob("*")}
        if source_paths != mirror_paths:
            raise ReleaseGateError(f"{name}: full-directory parity mismatch")
        for relative in source_paths:
            source, target = canonical / relative, mirror / relative
            if source.is_dir() != target.is_dir():
                raise ReleaseGateError(f"{name}/{relative}: type mismatch")
            if source.is_file() and (source.read_bytes() != target.read_bytes()
                    or stat.S_IMODE(source.stat().st_mode) != stat.S_IMODE(target.stat().st_mode)):
                raise ReleaseGateError(f"{name}/{relative}: byte or mode mismatch")
    return {"files": file_count}


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plugin-root", type=Path, required=True)
    parser.add_argument("--authoring-root", type=Path, required=True)
    parser.add_argument("--public-root", type=Path)
    options = parser.parse_args(argv)
    try:
        evidence = verify(options.plugin_root, options.authoring_root, options.public_root)
    except (OSError, ReleaseGateError) as exc:
        print(f"public plugin release gate failed: {exc}", file=sys.stderr)
        return 1
    print(f"public plugin release gate passed: {evidence['files']} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
