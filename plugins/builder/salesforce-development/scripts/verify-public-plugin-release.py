#!/usr/bin/env python3
"""Fail closed when the publishable Salesforce plugin tree is stale or leaks prose."""
from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from pathlib import Path
from typing import Iterator, Optional

# The release workflow can bootstrap with ``cp -r`` after this process exits.
# Never create untracked bytecode that a later copy could accidentally publish.
sys.dont_write_bytecode = True

import capability_registry as registry
import discovery_catalog as catalog

_TRANSIENT_DIRS = {"__pycache__", ".pytest_cache", ".sf"}
_RELEASE_MAX_ENTRIES = 4096
_RELEASE_MAX_DEPTH = 32
_RELEASE_MAX_FILE_BYTES = 16 * 1024 * 1024
_RELEASE_MAX_TOTAL_BYTES = 128 * 1024 * 1024
# Bound the leak scan's own recursion so a pathologically nested publishable JSON
# fails closed with a clear error instead of an uncaught RecursionError.
_JSON_MAX_DEPTH = 64


def _release_files(plugin_root: Path) -> Iterator[tuple[Path, bytes]]:
    """Yield bounded release-file bytes while pinning every ancestor directory."""
    count = 0
    total_bytes = 0
    dir_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    file_flags = os.O_RDONLY
    for optional in ("O_CLOEXEC", "O_NOFOLLOW"):
        dir_flags |= getattr(os, optional, 0)
    for optional in ("O_CLOEXEC", "O_NOFOLLOW", "O_NONBLOCK", "O_BINARY"):
        file_flags |= getattr(os, optional, 0)

    def account(relative: Path, content: bytes) -> tuple[Path, bytes]:
        nonlocal total_bytes
        total_bytes += len(content)
        if total_bytes > _RELEASE_MAX_TOTAL_BYTES:
            raise registry.RegistryError("publishable release tree total byte limit exceeded")
        return relative, content

    def read_fd(parent_fd: int, name: str, metadata: os.stat_result, relative: Path) -> bytes:
        try:
            descriptor = os.open(name, file_flags, dir_fd=parent_fd)
        except OSError as exc:
            raise registry.RegistryError(f"{relative}: cannot open release file safely") from exc
        try:
            opened = os.fstat(descriptor)
            if (not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1
                    or registry._tree_identity(metadata) != registry._tree_identity(opened)):
                raise registry.RegistryError(f"{relative}: release file changed before read")
            if opened.st_size > _RELEASE_MAX_FILE_BYTES:
                raise registry.RegistryError(f"{relative}: release file byte limit exceeded")
            chunks: list[bytes] = []
            size = 0
            while True:
                chunk = os.read(
                    descriptor,
                    min(registry.TREE_SCAN_CHUNK_BYTES, _RELEASE_MAX_FILE_BYTES + 1 - size),
                )
                if not chunk:
                    break
                chunks.append(chunk)
                size += len(chunk)
                if size > _RELEASE_MAX_FILE_BYTES:
                    raise registry.RegistryError(f"{relative}: release file byte limit exceeded")
            finished = os.fstat(descriptor)
            current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            if (registry._tree_identity(opened) != registry._tree_identity(finished)
                    or registry._tree_identity(finished) != registry._tree_identity(current)):
                raise registry.RegistryError(f"{relative}: release file changed during read")
            return b"".join(chunks)
        finally:
            os.close(descriptor)

    def visit_fd(directory_fd: int, relative_dir: Path, depth: int) -> Iterator[tuple[Path, bytes]]:
        nonlocal count
        if depth > _RELEASE_MAX_DEPTH:
            raise registry.RegistryError(f"{relative_dir}: release tree depth limit exceeded")
        try:
            children = os.scandir(directory_fd)
        except OSError as exc:
            raise registry.RegistryError(f"{relative_dir}: cannot scan release tree") from exc
        try:
            for child in children:
                count += 1
                if count > _RELEASE_MAX_ENTRIES:
                    raise registry.RegistryError("publishable release tree entry limit exceeded")
                relative = relative_dir / child.name
                if child.name in _TRANSIENT_DIRS:
                    raise registry.RegistryError(f"{relative}: transient directory is not publishable")
                metadata = os.stat(child.name, dir_fd=directory_fd, follow_symlinks=False)
                if stat.S_ISDIR(metadata.st_mode):
                    try:
                        child_fd = os.open(child.name, dir_flags, dir_fd=directory_fd)
                    except OSError as exc:
                        raise registry.RegistryError(f"{relative}: cannot open release directory safely") from exc
                    try:
                        opened = os.fstat(child_fd)
                        if registry._tree_identity(metadata) != registry._tree_identity(opened):
                            raise registry.RegistryError(f"{relative}: release directory changed")
                        yield from visit_fd(child_fd, relative, depth + 1)
                    finally:
                        os.close(child_fd)
                elif stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1:
                    yield account(relative, read_fd(directory_fd, child.name, metadata, relative))
                else:
                    raise registry.RegistryError(
                        f"{relative}: publishable release tree contains a link or special file"
                    )
        finally:
            children.close()

    if registry.TREE_SCAN_DIR_FD_SUPPORTED and os.scandir in getattr(os, "supports_fd", set()):
        root_metadata = plugin_root.lstat()
        try:
            root_fd = os.open(plugin_root, dir_flags)
        except OSError as exc:
            raise registry.RegistryError("cannot open publishable plugin root safely") from exc
        try:
            if registry._tree_identity(root_metadata) != registry._tree_identity(os.fstat(root_fd)):
                raise registry.RegistryError("publishable plugin root changed")
            yield from visit_fd(root_fd, Path(), 0)
        finally:
            os.close(root_fd)
        return

    # Cross-platform fallback: bounded explicit recursion with pre/post identity
    # checks. The public release workflow runs on POSIX and uses the pinned path.
    def visit_path(
        directory: Path, relative_dir: Path, depth: int, expected_dir: os.stat_result
    ) -> Iterator[tuple[Path, bytes]]:
        nonlocal count
        if depth > _RELEASE_MAX_DEPTH:
            raise registry.RegistryError(f"{relative_dir}: release tree depth limit exceeded")
        current_dir = directory.lstat()
        if registry._tree_identity(current_dir) != registry._tree_identity(expected_dir):
            raise registry.RegistryError(f"{relative_dir}: release directory changed")
        children = os.scandir(directory)
        try:
            for child in children:
                count += 1
                if count > _RELEASE_MAX_ENTRIES:
                    raise registry.RegistryError("publishable release tree entry limit exceeded")
                path = Path(child.path)
                relative = relative_dir / child.name
                if child.name in _TRANSIENT_DIRS:
                    raise registry.RegistryError(f"{relative}: transient directory is not publishable")
                metadata = path.lstat()
                if stat.S_ISDIR(metadata.st_mode):
                    yield from visit_path(path, relative, depth + 1, metadata)
                elif stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1:
                    content = registry.read_regular_file_bytes(
                        path,
                        max_bytes=_RELEASE_MAX_FILE_BYTES,
                        expected=metadata,
                        expected_parent=current_dir,
                    )
                    yield account(relative, content)
                else:
                    raise registry.RegistryError(
                        f"{relative}: publishable release tree contains a link or special file"
                    )
        finally:
            children.close()

    yield from visit_path(plugin_root, Path(), 0, plugin_root.lstat())


def _json_strings(value, depth: int = 0) -> Iterator[str]:
    if depth > _JSON_MAX_DEPTH:
        raise registry.RegistryError("publishable release JSON nesting limit exceeded")
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _json_strings(item, depth + 1)
    elif isinstance(value, dict):
        for key, item in value.items():
            if isinstance(key, str):
                yield key
            yield from _json_strings(item, depth + 1)


def verify(
    plugin_root: Path, authoring_root: Path, public_root: Optional[Path] = None
) -> dict[str, int]:
    plugin_root = Path(plugin_root).resolve(strict=True)
    authoring_root = Path(authoring_root).resolve(strict=True)
    public_root = Path(public_root).resolve(strict=True) if public_root is not None else None
    manifest = registry.load_public_manifest(plugin_root / registry.PUBLIC_MANIFEST_RELATIVE)
    catalog.check(authoring_root.parent, plugin_root)

    public = {row["name"] for row in manifest["skills"]}
    foundation = set(registry.skill_directories(plugin_root / "skills"))
    authoring = set(registry.skill_directories(authoring_root))
    protected_names = sorted((public - foundation) | (authoring - public - foundation))
    protected: list[tuple[str, str, bytes]] = []
    seen_descriptions: set[tuple[str, str]] = set()
    roots = [authoring_root]
    if public_root is not None:
        roots.append(public_root)
    for source_root in roots:
        source_inventory = registry.skill_directories(source_root)
        for name in protected_names:
            source_dir = source_inventory.get(name)
            if source_dir is None:
                continue
            description = registry.read_skill(source_dir / "SKILL.md")["description"]
            identity = (name, description)
            if identity in seen_descriptions:
                continue
            seen_descriptions.add(identity)
            protected.append((name, description, description.encode("utf-8")))

    file_count = 0
    leaks: list[str] = []
    for relative, content in _release_files(plugin_root):
        file_count += 1
        json_values: tuple[str, ...] = ()
        if relative.suffix.lower() == ".json":
            try:
                parsed = json.loads(content.decode("utf-8"))
            except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
                # A publishable .json that won't decode/parse can't be scanned for a
                # JSON-*escaped* description leak. Fail closed rather than fall back to
                # the raw-bytes check alone, which would miss an escaped form.
                raise registry.RegistryError(
                    f"{relative}: unparseable JSON in publishable release tree"
                ) from exc
            json_values = tuple(_json_strings(parsed))
        for name, description, raw in protected:
            if raw in content or any(description in value for value in json_values):
                leaks.append(f"{name}: {relative}")
    if leaks:
        detail = "; ".join(leaks[:10])
        raise registry.RegistryError(f"public-only/internal description leak: {detail}")
    return {"files": file_count, "descriptions": len(protected)}


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plugin-root", type=Path, required=True)
    parser.add_argument("--authoring-root", type=Path, required=True)
    parser.add_argument("--public-root", type=Path)
    options = parser.parse_args(argv)
    try:
        evidence = verify(options.plugin_root, options.authoring_root, options.public_root)
    except (OSError, registry.RegistryError) as exc:
        print(f"public plugin release gate failed: {exc}", file=sys.stderr)
        return 1
    print(
        "public plugin release gate passed: "
        f"{evidence['files']} files, {evidence['descriptions']} protected descriptions"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
