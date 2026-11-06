#!/usr/bin/env python3
"""Channel-aware Salesforce capability registry primitives.

This module hashes skill trees and provides bounded file-reading primitives.
Generic, dependency-free primitives consumed both at end-user runtime
(``plugin_catalog.py``, for the plugin-catalog gap detector) and at
release-verification time (``verify-public-plugin-release.py``). SKILL.md
frontmatter reading is release-time only and lives in
``scripts/release-ci/public-manifest.mjs``. It never serializes internal
authoring inventory.

Canonical tree hash policy (``sf-skill-tree-v1``): entries use sorted POSIX
relative paths. Directories, regular files, and symbolic links have distinct
record types. Regular-file records include a normalized executable boolean and
raw file bytes; permission bits other than any execute bit are ignored. Symlink
records include the raw link target bytes and no executable bit. Symlinks must
resolve to an existing target inside the declared safety root (the hashed tree
by default) and are not followed. Sockets, devices, FIFOs, and all other special
files are rejected.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from pathlib import Path
from typing import Optional

TREE_HASH_FORMAT = b"sf-skill-tree-v1\0"
TREE_SCAN_MAX_ENTRIES = 4096
TREE_SCAN_MAX_DEPTH = 32
TREE_SCAN_MAX_FILE_BYTES = 8 * 1024 * 1024
TREE_SCAN_MAX_TOTAL_BYTES = 64 * 1024 * 1024

# Opt-in only (default stays empty so existing skill-tree callers are
# unaffected): directory names a caller may ask to prune from the scan
# entirely — not entered, not hashed. Authored skill/plugin content never
# contains these; they are interpreter- or test-generated runtime state
# (both gitignored at the repo root) that would otherwise make a tree hash
# depend on unrelated local tool invocations (e.g. running the Python test
# suite populates ``__pycache__``, and the journey/phase-history tests write
# a relative ``.sf/`` runtime dir under the cwd the gate suites run from).
BUILD_ARTIFACT_DIR_NAMES = frozenset({"__pycache__", ".sf"})
TREE_SCAN_CHUNK_BYTES = 1024 * 1024
TREE_SCAN_DIR_FD_SUPPORTED = (
    os.name != "nt"
    and hasattr(os, "O_DIRECTORY")
    and os.open in getattr(os, "supports_dir_fd", set())
)
NAME_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


class RegistryError(ValueError):
    """A deterministic registry validation or generation error."""


def _tree_identity(
    value: os.stat_result, *, path_descriptor_boundary: bool = False
) -> tuple[int, ...]:
    identity = (
        value.st_dev, value.st_ino, value.st_mode, value.st_nlink, value.st_size,
        value.st_mtime_ns,
    )
    # CPython's native Windows path stat reports the creation time as st_ctime,
    # while fstat reports a metadata-change time. They can therefore differ for
    # the same open file. Retain ctime for path/path and descriptor/descriptor
    # race checks, but omit it when crossing between those Windows APIs.
    if os.name == "nt" and path_descriptor_boundary:
        return identity
    return identity + (value.st_ctime_ns,)


def read_regular_file_bytes(
    path: Path,
    *,
    max_bytes: int = TREE_SCAN_MAX_FILE_BYTES,
    expected: Optional[os.stat_result] = None,
    expected_parent: Optional[os.stat_result] = None,
) -> bytes:
    """Read one stable, unlinked regular file through a verified parent directory."""
    path = Path(path)
    try:
        before = path.lstat()
        parent_before = path.parent.lstat()
    except OSError as exc:
        raise RegistryError(f"{path}: cannot inspect regular file: {exc}") from exc
    if expected is not None and _tree_identity(expected) != _tree_identity(before):
        raise RegistryError(f"{path}: regular file changed before read")
    if (expected_parent is not None
            and _tree_identity(expected_parent) != _tree_identity(parent_before)):
        raise RegistryError(f"{path}: parent directory changed before read")
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
        raise RegistryError(f"{path}: expected one non-hardlinked regular file")
    flags = os.O_RDONLY
    for optional in ("O_CLOEXEC", "O_NOFOLLOW", "O_NONBLOCK", "O_BINARY"):
        flags |= getattr(os, optional, 0)
    parent_descriptor: Optional[int] = None
    descriptor: Optional[int] = None
    try:
        if TREE_SCAN_DIR_FD_SUPPORTED:
            parent_flags = os.O_RDONLY | os.O_DIRECTORY
            for optional in ("O_CLOEXEC", "O_NOFOLLOW"):
                parent_flags |= getattr(os, optional, 0)
            parent_descriptor = os.open(path.parent, parent_flags)
            opened_parent = os.fstat(parent_descriptor)
            if (_tree_identity(parent_before, path_descriptor_boundary=True)
                    != _tree_identity(opened_parent, path_descriptor_boundary=True)
                    or not stat.S_ISDIR(opened_parent.st_mode)):
                raise RegistryError(f"{path}: parent directory changed before read")
            descriptor = os.open(path.name, flags, dir_fd=parent_descriptor)
        else:
            descriptor = os.open(path, flags)
    except (OSError, RegistryError) as exc:
        if parent_descriptor is not None:
            os.close(parent_descriptor)
        if isinstance(exc, RegistryError):
            raise
        raise RegistryError(f"{path}: cannot open regular file safely: {exc}") from exc
    try:
        opened = os.fstat(descriptor)
        if (not stat.S_ISREG(opened.st_mode)
                or opened.st_nlink != 1
                or _tree_identity(before, path_descriptor_boundary=True)
                != _tree_identity(opened, path_descriptor_boundary=True)):
            raise RegistryError(f"{path}: regular file changed before read")
        if opened.st_size > max_bytes:
            raise RegistryError(f"{path}: regular file byte limit exceeded")
        chunks: list[bytes] = []
        size = 0
        while True:
            chunk = os.read(descriptor, min(TREE_SCAN_CHUNK_BYTES, max_bytes + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
            if size > max_bytes:
                raise RegistryError(f"{path}: regular file byte limit exceeded")
        finished = os.fstat(descriptor)
    except OSError as exc:
        raise RegistryError(f"{path}: cannot read regular file: {exc}") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if parent_descriptor is not None:
            os.close(parent_descriptor)
    try:
        current = path.lstat()
    except OSError as exc:
        raise RegistryError(f"{path}: regular file changed after read") from exc
    if (_tree_identity(opened) != _tree_identity(finished)
            or _tree_identity(finished, path_descriptor_boundary=True)
            != _tree_identity(current, path_descriptor_boundary=True)):
        raise RegistryError(f"{path}: regular file changed during read")
    return b"".join(chunks)


def sha256_file(path: Path) -> str:
    """Hash one bounded, stable regular file as raw bytes."""
    return hashlib.sha256(read_regular_file_bytes(path)).hexdigest()


def _hash_field(digest, value: bytes) -> None:
    digest.update(len(value).to_bytes(8, "big"))
    digest.update(value)


def inspect_skill_tree(
    root: Path, *, safety_root: Optional[Path] = None,
    budget: Optional[dict[str, int]] = None,
    executable_paths: Optional[set[str]] = None,
    exclude_dir_names: Optional[frozenset[str]] = None,
) -> dict:
    """Hash one tree and capture its SKILL.md bytes in the same bounded scan.

    Runtime callers must derive trusted prose only from ``skillMdBytes``. Regular
    files are opened no-follow/nonblocking where the host supports those flags,
    verified before reading, and consumed within explicit byte budgets. A second
    bounded inventory must match the first before captured prose is released.
    """
    root = Path(root)
    safety_root = Path(safety_root) if safety_root is not None else root
    try:
        if root.is_symlink() or not root.is_dir() or safety_root.is_symlink() or not safety_root.is_dir():
            raise RegistryError(f"{root}: tree root and safety root must be real directories")
        tree_anchor = root.resolve(strict=True)
        anchor = safety_root.resolve(strict=True)
        tree_anchor.relative_to(anchor)
        root_metadata = root.lstat()
    except (OSError, ValueError) as exc:
        raise RegistryError(f"{root}: cannot resolve tree root inside safety root: {exc}") from exc

    def inventory() -> list[tuple[str, Path, os.stat_result]]:
        entries: list[tuple[str, Path, os.stat_result]] = []

        def visit(directory: Path, depth: int) -> None:
            if depth > TREE_SCAN_MAX_DEPTH:
                raise RegistryError(f"{directory}: tree depth limit exceeded")
            try:
                children = os.scandir(directory)
            except OSError as exc:
                raise RegistryError(f"{directory}: cannot scan tree: {exc}") from exc
            try:
                for child in children:
                    if len(entries) >= TREE_SCAN_MAX_ENTRIES:
                        raise RegistryError(f"{root}: tree entry limit exceeded")
                    if budget is not None:
                        budget["entries"] = budget.get("entries", 0) + 1
                        if budget["entries"] > budget.get("maxEntries", TREE_SCAN_MAX_ENTRIES):
                            raise RegistryError(f"{root}: aggregate tree entry limit exceeded")
                    path = Path(child.path)
                    try:
                        metadata = path.lstat()
                    except OSError as exc:
                        raise RegistryError(f"{path}: cannot inspect tree entry: {exc}") from exc
                    if (exclude_dir_names and child.name in exclude_dir_names
                            and stat.S_ISDIR(metadata.st_mode)):
                        continue
                    relative = path.relative_to(root).as_posix()
                    entries.append((relative, path, metadata))
                    if stat.S_ISDIR(metadata.st_mode):
                        visit(path, depth + 1)
            finally:
                close = getattr(children, "close", None)
                if close is not None:
                    close()

        visit(root, 0)
        return entries

    entries = inventory()
    directory_metadata = {".": root_metadata}
    directory_metadata.update({
        relative: metadata
        for relative, _, metadata in entries
        if stat.S_ISDIR(metadata.st_mode)
    })
    digest = hashlib.sha256()
    digest.update(TREE_HASH_FORMAT)
    skill_md_bytes: Optional[bytes] = None
    stable = True
    total_bytes = 0
    for relative, path, metadata in sorted(entries, key=lambda item: item[0]):
        relative_bytes = relative.encode("utf-8")
        mode = metadata.st_mode
        if stat.S_ISDIR(mode):
            digest.update(b"D")
            _hash_field(digest, relative_bytes)
        elif stat.S_ISREG(mode):
            if metadata.st_nlink != 1:
                raise RegistryError(f"{path}: hardlinked tree files are not supported")
            digest.update(b"F")
            _hash_field(digest, relative_bytes)
            executable = (
                relative in executable_paths
                if executable_paths is not None
                else bool(mode & 0o111)
            )
            digest.update(b"1" if executable else b"0")
            flags = os.O_RDONLY
            for optional in ("O_CLOEXEC", "O_NOFOLLOW", "O_NONBLOCK", "O_BINARY"):
                flags |= getattr(os, optional, 0)
            parent_descriptor: Optional[int] = None
            descriptor: Optional[int] = None
            parent_relative = Path(relative).parent.as_posix()
            expected_parent = directory_metadata[parent_relative]
            use_parent_fd = TREE_SCAN_DIR_FD_SUPPORTED
            try:
                if use_parent_fd:
                    parent_flags = os.O_RDONLY | os.O_DIRECTORY
                    for optional in ("O_CLOEXEC", "O_NOFOLLOW"):
                        parent_flags |= getattr(os, optional, 0)
                    parent_descriptor = os.open(path.parent, parent_flags)
                    opened_parent = os.fstat(parent_descriptor)
                    if (_tree_identity(expected_parent, path_descriptor_boundary=True)
                            != _tree_identity(opened_parent, path_descriptor_boundary=True)
                            or not stat.S_ISDIR(opened_parent.st_mode)):
                        raise RegistryError(f"{path}: parent directory changed before read")
                    descriptor = os.open(path.name, flags, dir_fd=parent_descriptor)
                else:
                    descriptor = os.open(path, flags)
            except (OSError, RegistryError) as exc:
                if parent_descriptor is not None:
                    os.close(parent_descriptor)
                if isinstance(exc, RegistryError):
                    raise
                raise RegistryError(f"{path}: cannot open parent directory or tree file safely: {exc}") from exc
            try:
                opened = os.fstat(descriptor)
                if (not stat.S_ISREG(opened.st_mode)
                        or opened.st_nlink != 1
                        or _tree_identity(metadata, path_descriptor_boundary=True)
                        != _tree_identity(opened, path_descriptor_boundary=True)):
                    raise RegistryError(f"{path}: tree file changed before read")
                if opened.st_size > TREE_SCAN_MAX_FILE_BYTES:
                    raise RegistryError(f"{path}: tree file byte limit exceeded")
                chunks: list[bytes] = []
                file_bytes = 0
                while True:
                    chunk = os.read(descriptor, TREE_SCAN_CHUNK_BYTES)
                    if not chunk:
                        break
                    file_bytes += len(chunk)
                    total_bytes += len(chunk)
                    if budget is not None:
                        budget["bytes"] = budget.get("bytes", 0) + len(chunk)
                        if budget["bytes"] > budget.get("maxBytes", TREE_SCAN_MAX_TOTAL_BYTES):
                            raise RegistryError(f"{root}: aggregate tree byte limit exceeded")
                    if file_bytes > TREE_SCAN_MAX_FILE_BYTES:
                        raise RegistryError(f"{path}: tree file byte limit exceeded")
                    if total_bytes > TREE_SCAN_MAX_TOTAL_BYTES:
                        raise RegistryError(f"{root}: tree total byte limit exceeded")
                    chunks.append(chunk)
                content = b"".join(chunks)
                finished = os.fstat(descriptor)
            except OSError as exc:
                raise RegistryError(f"{path}: cannot read tree file: {exc}") from exc
            finally:
                if descriptor is not None:
                    os.close(descriptor)
                if parent_descriptor is not None:
                    os.close(parent_descriptor)
            try:
                current = path.lstat()
            except OSError:
                stable = False
            else:
                if (_tree_identity(opened) != _tree_identity(finished)
                        or _tree_identity(finished, path_descriptor_boundary=True)
                        != _tree_identity(current, path_descriptor_boundary=True)):
                    stable = False
            _hash_field(digest, content)
            if relative == "SKILL.md":
                skill_md_bytes = content
        elif stat.S_ISLNK(mode):
            try:
                target_text = os.readlink(path)
                resolved = path.resolve(strict=True)
                resolved.relative_to(anchor)
            except (OSError, ValueError) as exc:
                raise RegistryError(f"{path}: unsafe, dangling, or out-of-root symlink") from exc
            digest.update(b"L")
            _hash_field(digest, relative_bytes)
            _hash_field(digest, os.fsencode(target_text))
        else:
            raise RegistryError(f"{path}: special files are not supported in capability trees")

    current_root: Optional[os.stat_result] = None
    try:
        current_root = root.lstat()
        second = inventory()
    except (OSError, RegistryError):
        stable = False
        second = []
    first_fingerprint = [
        (relative, _tree_identity(metadata))
        for relative, _, metadata in sorted(entries, key=lambda item: item[0])
    ]
    second_fingerprint = [
        (relative, _tree_identity(metadata))
        for relative, _, metadata in sorted(second, key=lambda item: item[0])
    ]
    if (current_root is None
            or _tree_identity(root_metadata) != _tree_identity(current_root)
            or first_fingerprint != second_fingerprint):
        stable = False
    return {
        "treeSha256": digest.hexdigest(),
        "skillMdBytes": skill_md_bytes if stable else None,
        "stable": stable,
    }


def canonical_tree_sha256(
    root: Path, *, safety_root: Optional[Path] = None,
    executable_paths: Optional[set[str]] = None,
    exclude_dir_names: Optional[frozenset[str]] = None,
) -> str:
    """Return the canonical ``sf-skill-tree-v1`` hash for a directory tree."""
    observation = inspect_skill_tree(
        root, safety_root=safety_root, executable_paths=executable_paths,
        exclude_dir_names=exclude_dir_names,
    )
    if not observation["stable"]:
        raise RegistryError(f"{root}: tree changed during scan")
    return observation["treeSha256"]


def _valid_hash(value) -> bool:
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def main(argv: Optional[list[str]] = None) -> int:
    """CLI: batch-compute canonical hashes for one or more skill directories.

    Prints ``{"<path>": {"skillMdSha256": "...", "treeSha256": "..."}}`` as a
    single JSON object to stdout. Exists so release-verification tooling
    outside this plugin (currently a Node module) can get the canonical
    ``sf-skill-tree-v1`` hash without a second, independent implementation of
    that algorithm.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hash-skills", dest="hash_skills", nargs="+", required=True, type=Path)
    options = parser.parse_args(argv)
    try:
        result = {
            str(path): {
                "skillMdSha256": sha256_file(path / "SKILL.md"),
                "treeSha256": canonical_tree_sha256(path),
            }
            for path in options.hash_skills
        }
    except RegistryError as exc:
        print(f"capability registry error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
