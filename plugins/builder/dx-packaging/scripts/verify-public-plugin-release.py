#!/usr/bin/env python3
"""Fail closed when a packaging plugin tree is unsafe to publish.

In addition to release-tree safety and plugin identity, every bundled skill
must explicitly declare ``metadata.distribution.sf-skills.visibility: public``.
The plugin currently groups public and pre-release packaging skills internally;
this guard prevents a future marketplace opt-in from publishing the entire tree
before every bundled skill is ready.
"""
from __future__ import annotations

import argparse
import json
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


def _sf_skills_visibility(skill_md: Path) -> Optional[str]:
    """Read the narrowly scoped visibility value from YAML frontmatter."""
    try:
        lines = skill_md.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise ReleaseGateError(f"cannot read {skill_md}") from exc
    if not lines or lines[0].strip() != "---":
        return None
    try:
        end = next(index for index, line in enumerate(lines[1:], 1) if line.strip() == "---")
    except StopIteration:
        return None

    frontmatter = lines[1:end]
    for index, line in enumerate(frontmatter):
        if line != "  distribution:":
            continue
        for channel_index in range(index + 1, len(frontmatter)):
            channel_line = frontmatter[channel_index]
            if channel_line and not channel_line.startswith("    "):
                break
            if channel_line != "    sf-skills:":
                continue
            for value_line in frontmatter[channel_index + 1:]:
                if value_line and not value_line.startswith("      "):
                    break
                prefix = "      visibility:"
                if value_line.startswith(prefix):
                    return value_line[len(prefix):].strip().strip("\"'") or None
            return None
        return None
    return None


def _verify_public_skills(plugin_root: Path) -> int:
    skills_root = plugin_root / "skills"
    if not skills_root.is_dir():
        raise ReleaseGateError("publishable plugin has no skills directory")
    count = 0
    for skill_dir in sorted(skills_root.iterdir(), key=lambda path: path.name):
        if not skill_dir.is_dir():
            raise ReleaseGateError(f"skills/{skill_dir.name}: expected a skill directory")
        skill_md = skill_dir / "SKILL.md"
        visibility = _sf_skills_visibility(skill_md)
        if visibility != "public":
            shown = repr(visibility) if visibility is not None else "missing"
            raise ReleaseGateError(
                f"skills/{skill_dir.name}: sf-skills visibility is {shown}, expected 'public'"
            )
        count += 1
    if count == 0:
        raise ReleaseGateError("publishable plugin has no bundled skills")
    return count


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


def verify(plugin_root: Path) -> dict[str, int]:
    plugin_root = Path(plugin_root).resolve(strict=True)
    manifest_path = plugin_root / ".claude-plugin" / "plugin.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReleaseGateError(f"cannot read {manifest_path}") from exc

    expected_name = plugin_root.name
    actual_name = manifest.get("name")
    if actual_name != expected_name:
        raise ReleaseGateError(
            f"plugin.json name {actual_name!r} does not match directory {expected_name!r}"
        )

    file_count = _scan(plugin_root)
    skill_count = _verify_public_skills(plugin_root)
    return {"files": file_count, "skills": skill_count}


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plugin-root", type=Path, required=True)
    parser.add_argument("--authoring-root", type=Path, required=True)
    parser.add_argument("--public-root", type=Path)
    options = parser.parse_args(argv)
    try:
        evidence = verify(options.plugin_root)
    except (OSError, ReleaseGateError) as exc:
        print(f"public plugin release gate failed: {exc}", file=sys.stderr)
        return 1
    print(f"public plugin release gate passed: {evidence['files']} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
