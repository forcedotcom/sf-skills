#!/usr/bin/env python3
"""Fail closed when a publishable plugin tree is unsafe or misidentified.

Source verification enforces full canonical path, byte and mode parity.
Public-tree verification permits removal of SoR sidecars and the trusted
repository sanitizer's distribution stripping, while preserving all other
content. Both modes enforce exact roster membership and release-tree safety.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
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

    expected_name = "education-cloud"
    actual_name = manifest.get("name")
    if actual_name != expected_name:
        raise ReleaseGateError(
            f"plugin.json name {actual_name!r} does not match directory {expected_name!r}"
        )

    if plugin_root.name != expected_name:
        raise ReleaseGateError("plugin root directory must be education-cloud")
    file_count = _scan(plugin_root)
    roster = json.loads((plugin_root / "scripts/skill-roster.json").read_text(encoding="utf-8"))
    if not isinstance(roster, list) or not roster or any(
            not isinstance(name, str) or not re.fullmatch(r"education-cloud-[a-z0-9]+(?:-[a-z0-9]+)*", name)
            for name in roster) or len(set(roster)) != len(roster):
        raise ReleaseGateError("expected a nonempty roster of unique Education skills")
    expected = set(roster)
    actual = {p.name for p in (plugin_root / "skills").iterdir()}
    if actual != expected or any(not (plugin_root / "skills" / name).is_dir() for name in roster):
        raise ReleaseGateError("skill roster mismatch")
    authoring_root = Path(authoring_root).resolve(strict=True)
    # The workflow also passes public-root to the source pre-copy check.
    source_plugin = authoring_root.parent / "plugins/builder/education-cloud"
    public_tree = public_root is not None and plugin_root != source_plugin
    if public_tree and plugin_root != Path(public_root).resolve().parent / "plugins/builder/education-cloud":
        raise ReleaseGateError("plugin root is outside the expected public plugin destination")
    sanitizer = authoring_root.parent / "scripts/release-ci/sanitize-public-skills.mjs"
    # Execute only the trusted authoring checkout's sanitizer, never destination code.
    program = """
        import {readFileSync} from 'node:fs';
        import {pathToFileURL} from 'node:url';
        const m = await import(pathToFileURL(process.argv[2]));
        const source = JSON.parse(readFileSync(0, 'utf8'));
        const output = {};
        for (const [name, text] of Object.entries(source)) {
            if (m.isWithheldFromPublic(text)) throw new Error(name + ': canonical skill is not public');
            const clean = m.stripInternalFrontmatterFields(text).content;
            m.assertNoInternalFields(clean);
            output[name] = clean;
        }
        process.stdout.write(JSON.stringify(output));
    """
    for name in roster:
        if not (authoring_root / name / "SKILL.md").is_file():
            raise ReleaseGateError(f"{name}: canonical skill missing")
    source_text = {name: (authoring_root / name / "SKILL.md").read_bytes().decode("utf-8")
                   for name in roster}
    try:
        result = subprocess.run(
            ["node", "--input-type=module", "-e", program, "education-public-parity", str(sanitizer)],
            input=json.dumps(source_text), text=True, encoding="utf-8",
            capture_output=True, timeout=30, check=True)
        sanitized = json.loads(result.stdout)
    except (subprocess.SubprocessError, json.JSONDecodeError) as exc:
        raise ReleaseGateError("trusted public skill sanitization failed") from exc
    for name in sorted(expected):
        source = Path(authoring_root) / name
        mirror = plugin_root / "skills" / name
        def inventory(root):
            return {str(p.relative_to(root)): p for p in root.rglob("*")}
        left, right = inventory(source), inventory(mirror)
        if public_tree:
            if any(path.name == "sor.yaml" for path in mirror.rglob("*")):
                raise ReleaseGateError(f"{name}: internal sor.yaml is not publishable")
            left = {relative: path for relative, path in left.items() if path.name != "sor.yaml"}
        if left.keys() != right.keys():
            raise ReleaseGateError(f"{name}: canonical path parity mismatch")
        for relative, original in left.items():
            copied = right[relative]
            a, b = original.lstat(), copied.lstat()
            if stat.S_IFMT(a.st_mode) != stat.S_IFMT(b.st_mode) or stat.S_IMODE(a.st_mode) != stat.S_IMODE(b.st_mode):
                raise ReleaseGateError(f"{name}/{relative}: file mode parity mismatch")
            if original.is_file():
                allowed = {original.read_bytes()}
                if public_tree and relative == "SKILL.md":
                    allowed.add(sanitized[name].encode("utf-8"))
                if copied.read_bytes() not in allowed:
                    raise ReleaseGateError(f"{name}/{relative}: content parity mismatch")
    return {"files": file_count}


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plugin-root", type=Path, required=True)
    parser.add_argument("--authoring-root", type=Path, required=True)
    parser.add_argument("--public-root", type=Path)
    options = parser.parse_args(argv)
    try:
        evidence = verify(options.plugin_root, options.authoring_root, options.public_root)
    except (OSError, ValueError, TypeError, ReleaseGateError) as exc:
        print(f"public plugin release gate failed: {exc}", file=sys.stderr)
        return 1
    print(f"public plugin release gate passed: {evidence['files']} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
