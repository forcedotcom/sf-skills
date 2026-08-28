#!/usr/bin/env python3
"""Channel-aware Salesforce capability registry primitives.

The public release manifest is the only release-channel input to the checked
catalog. This module hashes skill trees and builds, snapshots, and verifies
that manifest; it never serializes internal authoring inventory.

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
import subprocess
import sys
import unicodedata
from pathlib import Path
from typing import Optional
from urllib.parse import unquote, urlsplit

PUBLIC_MANIFEST_SCHEMA = "2.0"
PUBLIC_REPOSITORY = "https://github.com/forcedotcom/sf-skills.git"
RELEASE_REF_PATTERN = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+")
PUBLIC_MANIFEST_RELATIVE = Path("catalog/public-release-manifest.json")
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
# a relative ``.sf/`` runtime dir under ``scripts/test/``).
BUILD_ARTIFACT_DIR_NAMES = frozenset({"__pycache__", ".sf"})
TREE_SCAN_CHUNK_BYTES = 1024 * 1024
TREE_SCAN_DIR_FD_SUPPORTED = (
    os.name != "nt"
    and hasattr(os, "O_DIRECTORY")
    and os.open in getattr(os, "supports_dir_fd", set())
)
NAME_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
APPROVED_DOMAIN_PREFIXES = (
    "agentforce", "automation", "automotive-cloud", "channel-revenue-management",
    "cme", "commerce", "communications", "consumer-goods", "crm-analytics",
    "data360", "design-systems", "dx", "education-cloud", "energy-and-utilities",
    "experience", "external", "field-service", "fsc", "health-cloud", "industries",
    "insurance", "integration", "life-sciences", "manufacturing", "marketing",
    "mobile", "net-zero", "non-profit", "omnistudio", "platform", "public-sector",
    "revenue", "sales", "service", "sf-skill", "tableau", "tableau-next",
)


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


def _has_control(value: str) -> bool:
    return any(unicodedata.category(char) in {"Cc", "Cf", "Zl", "Zp"} for char in value)


def _frontmatter_bytes(content: bytes, path: Path) -> list[str]:
    try:
        lines = content.decode("utf-8").splitlines()
    except UnicodeError as exc:
        raise RegistryError(f"{path}: cannot read SKILL.md: {exc}") from exc
    if not lines or lines[0].strip() != "---":
        raise RegistryError(f"{path}: missing opening frontmatter delimiter")
    try:
        end = next(index for index in range(1, len(lines)) if lines[index].strip() == "---")
    except StopIteration as exc:
        raise RegistryError(f"{path}: missing closing frontmatter delimiter") from exc
    return lines[1:end]


def _frontmatter(path: Path) -> list[str]:
    return _frontmatter_bytes(read_regular_file_bytes(path), path)


def _block_scalar(lines: list[str], start: int, style: str, path: Path) -> str:
    values: list[Optional[str]] = []
    for line in lines[start + 1:]:
        if line and not line[0].isspace():
            break
        if not line.strip():
            values.append(None)
        else:
            match = re.match(r"^(\s+)(.*)$", line)
            if not match:
                raise RegistryError(f"{path}: malformed description block")
            values.append(match.group(2))
    if not values or not any(value is not None for value in values):
        raise RegistryError(f"{path}: description block is empty")
    if style.startswith("|"):
        text = "\n".join("" if value is None else value for value in values)
    else:
        paragraphs: list[str] = []
        current: list[str] = []
        for value in values:
            if value is None:
                if current:
                    paragraphs.append(" ".join(current))
                    current = []
            else:
                current.append(value)
        if current:
            paragraphs.append(" ".join(current))
        text = "\n".join(paragraphs)
    return text + "\n" if style.endswith("+") or style in (">", "|") else text


def read_skill_bytes(content: bytes, path: Path) -> dict[str, str]:
    """Parse the bounded name and description subset from captured SKILL.md bytes."""
    lines = _frontmatter_bytes(content, path)
    fields: dict[str, str] = {}
    for index, line in enumerate(lines):
        if not line or line[0].isspace() or ":" not in line:
            continue
        key, raw = line.split(":", 1)
        if key not in ("name", "description"):
            continue
        value = raw.strip()
        if key == "description" and value in (">", ">-", ">+", "|", "|-", "|+"):
            fields[key] = _block_scalar(lines, index, value, path)
        elif value.startswith('"'):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError as exc:
                raise RegistryError(f"{path}: invalid double-quoted {key}: {exc.msg}") from exc
            if type(parsed) is not str:
                raise RegistryError(f"{path}: {key} must be a string")
            fields[key] = parsed
        elif key == "name" and NAME_PATTERN.fullmatch(value):
            fields[key] = value
        else:
            raise RegistryError(f"{path}: unsupported {key} scalar")
    if set(fields) != {"name", "description"}:
        raise RegistryError(f"{path}: missing required name or description")
    if fields["name"] != path.parent.name:
        raise RegistryError(f"{path}: frontmatter name does not match directory")
    if len(fields["name"]) > 64 or not 1 <= len(fields["description"]) <= 1024:
        raise RegistryError(f"{path}: name or description is outside supported bounds")
    if _has_control(fields["name"]) or _has_control(fields["description"]):
        raise RegistryError(f"{path}: name or description contains control characters")
    return fields


def read_skill(path: Path) -> dict[str, str]:
    """Read the bounded name and description subset from SKILL.md frontmatter."""
    return read_skill_bytes(read_regular_file_bytes(path), path)


def _access_scalar(raw: str, path: Path) -> str:
    """Parse a single accessCheck ``type``/``value`` scalar (quoted or bare)."""
    if raw.startswith('"'):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RegistryError(f"{path}: invalid quoted accessCheck scalar: {exc.msg}") from exc
        if type(parsed) is not str:
            raise RegistryError(f"{path}: accessCheck scalar must be a string")
        return parsed
    return raw


def read_access_check(path: Path) -> Optional[list[dict[str, str]]]:
    """Read the tri-state ``metadata.accessCheck`` from SKILL.md frontmatter.

    Returns ``None`` when accessCheck is undeclared (no ``metadata`` block or no
    ``accessCheck`` key), ``[]`` for an explicit empty array (applies to any
    org), or a list of ``{"type", "value"}`` entries when availability is
    conditional. Raises RegistryError on a present-but-malformed declaration so a
    broken accessCheck can never silently collapse into "undeclared" or "any
    org". Bounded hand parser (this module intentionally avoids a YAML
    dependency, matching ``read_skill``); shape is enforced by
    ``_valid_access_check``. Only inline ``[]`` / double-quoted JSON arrays and
    block-style ``- type:``/``value:`` entries are recognized; any other form
    fails loud.
    """
    lines = _frontmatter(path)
    meta_index = next(
        (index for index, line in enumerate(lines)
         if line and not line[0].isspace() and line.split(":", 1)[0].strip() == "metadata"),
        None,
    )
    if meta_index is None:
        return None
    block = []
    for line in lines[meta_index + 1:]:
        if line and not line[0].isspace():
            break
        block.append(line)
    ac_index = ac_indent = None
    inline = ""
    for index, line in enumerate(block):
        if not line.strip():
            continue
        if line.split(":", 1)[0].strip() == "accessCheck":
            ac_index = index
            ac_indent = len(line) - len(line.lstrip())
            inline = line.split(":", 1)[1].strip() if ":" in line else ""
            break
    if ac_index is None:
        return None
    if inline:
        try:
            parsed = json.loads(inline)
        except json.JSONDecodeError as exc:
            raise RegistryError(f"{path}: unsupported accessCheck value: {exc.msg}") from exc
        if type(parsed) is not list:
            raise RegistryError(f"{path}: accessCheck must be an array")
        return parsed
    entries: list[dict[str, str]] = []
    current: Optional[dict[str, str]] = None
    for line in block[ac_index + 1:]:
        if not line.strip():
            continue
        if len(line) - len(line.lstrip()) <= ac_indent:
            break
        stripped = line.strip()
        if stripped.startswith("-"):
            current = {}
            entries.append(current)
            stripped = stripped[1:].strip()
            if not stripped:
                continue
        if current is None or ":" not in stripped:
            raise RegistryError(f"{path}: malformed accessCheck entry")
        key, raw = stripped.split(":", 1)
        current[key.strip()] = _access_scalar(raw.strip(), path)
    if not entries:
        raise RegistryError(f"{path}: accessCheck is present but empty; use [] for any-org")
    return entries


EXCLUSION_CLAUSE = re.compile(
    r"\b(?:do\s+not\s+trigger|do\s+not\s+use|not\s+for|skip\s+when|does\s+not\s+apply)\b",
    re.IGNORECASE,
)
USER_INTENT_VERBS = {
    "add", "analyze", "apply", "assign", "audit", "build", "check", "configure",
    "connect", "create", "debug", "deploy", "enable", "find", "generate", "get",
    "help", "integrate", "migrate", "open", "query", "replace", "retrieve", "run",
    "review", "scan", "score", "search", "secure", "set", "ship", "show", "switch",
    "test", "validate", "verify",
}
CURATED_EXAMPLES = {
    "agentforce-generate": "Build an Agentforce agent for order-status help.",
    "platform-apex-generate": "Create an Apex service to query Accounts.",
    "platform-apex-test-generate": "Generate Apex tests for my selector class.",
    "platform-custom-object-generate": "Create a custom object for service visits.",
    "platform-deploy-validate": "Validate this deployment before I ship it.",
    "platform-environment-validate": "Check whether my environment is ready to build.",
    "platform-metadata-deploy": "Deploy my local changes to the scratch org.",
    "platform-soql-query": "Query the ten largest open opportunities.",
}


def is_user_prompt_like(phrase: str) -> bool:
    if not phrase or "\n" in phrase or len(phrase) > 140:
        return False
    if re.search(r"[<>/\\`{}\[\]]|__|\.[A-Za-z0-9]", phrase):
        return False
    words = re.findall(r"[A-Za-z][A-Za-z'-]*", phrase)
    return bool(
        len(words) >= 2
        and (len(words[0]) != 1 or words[0].lower() == "i")
        and words[0].lower() in USER_INTENT_VERBS | {"how", "i", "what", "when", "where", "why"}
    )


def example_prompt(name: str, description: str, domain: str) -> str:
    """Freeze a bounded display prompt while trusted source prose is in hand."""
    if name in CURATED_EXAMPLES:
        return CURATED_EXAMPLES[name]
    for trigger in re.finditer(r"\btriggers?\b|\buse when\b", description, re.IGNORECASE):
        prefix = description[max(0, trigger.start() - 24):trigger.start()]
        if re.search(r"\bdo\s+not\s+$", prefix, re.IGNORECASE):
            continue
        tail = EXCLUSION_CLAUSE.split(description[trigger.end():], maxsplit=1)[0]
        for match in re.finditer(r"['\"]([^'\"\n]{4,140})['\"]", tail):
            phrase = match.group(1).strip()
            if is_user_prompt_like(phrase):
                return phrase[0].upper() + phrase[1:]
    remainder = name[len(domain):].strip("-")
    parts = remainder.split("-") if remainder else []
    verb = parts[-1] if parts else "use"
    subject = " ".join(parts[:-1]) or domain.replace("-", " ")
    return f"Help me {verb} Salesforce {subject}."


def derive_domain(name: str) -> str:
    matches = [prefix for prefix in APPROVED_DOMAIN_PREFIXES if name == prefix or name.startswith(prefix + "-")]
    if not matches:
        raise RegistryError(f"skill {name!r}: no approved domain prefix")
    return max(matches, key=len)


def skill_directories(root: Path) -> dict[str, Path]:
    """Return strict one-level skill directories keyed by validated name."""
    if not root.is_dir():
        raise RegistryError(f"{root}: skills directory is missing")
    result: dict[str, Path] = {}
    for entry in sorted(root.iterdir(), key=lambda item: item.name):
        if not entry.is_dir() or entry.is_symlink():
            raise RegistryError(f"{entry}: skills inventory must contain only real directories")
        if not NAME_PATTERN.fullmatch(entry.name):
            raise RegistryError(f"{entry}: invalid skill directory name")
        skill_file = entry / "SKILL.md"
        record = read_skill(skill_file)
        if record["name"] != entry.name:
            raise RegistryError(f"{skill_file}: inventory name mismatch")
        result[entry.name] = entry
    return result


def normalize_public_repository(origin: str) -> str:
    """Return the canonical public identity for accepted GitHub origin forms.

    Error text deliberately never includes the supplied origin because HTTPS
    remotes may contain credentials.
    """
    accepted = False
    if re.fullmatch(r"git@github\.com:forcedotcom/sf-skills(?:\.git)?", origin):
        accepted = True
    else:
        try:
            parsed = urlsplit(origin)
            path = unquote(parsed.path).rstrip("/")
            if path.endswith(".git"):
                path = path[:-4]
            if parsed.scheme == "https":
                accepted = (
                    parsed.hostname == "github.com"
                    and parsed.port in (None, 443)
                    and path == "/forcedotcom/sf-skills"
                    and not parsed.query
                    and not parsed.fragment
                )
            elif parsed.scheme == "ssh":
                accepted = (
                    parsed.hostname == "github.com"
                    and parsed.port in (None, 22)
                    and parsed.username == "git"
                    and parsed.password is None
                    and path == "/forcedotcom/sf-skills"
                    and not parsed.query
                    and not parsed.fragment
                )
        except (TypeError, ValueError):
            accepted = False
    if not accepted:
        raise RegistryError("public checkout has an unsupported repository origin")
    return PUBLIC_REPOSITORY


def _git(checkout: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(checkout), *args], capture_output=True, text=True,
            timeout=30, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RegistryError(f"{checkout}: cannot inspect public git checkout") from exc
    if result.returncode != 0:
        raise RegistryError(f"{checkout}: public checkout git metadata is unavailable")
    return result.stdout.strip()


def _git_paths(checkout: Path, *args: str) -> set[str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(checkout), *args],
            capture_output=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RegistryError(f"{checkout}: cannot inspect public git checkout") from exc
    if result.returncode != 0:
        raise RegistryError(f"{checkout}: public checkout git metadata is unavailable")
    return {
        os.fsdecode(value)
        for value in result.stdout.split(b"\0")
        if value
    }


def _validate_tracked_skills_tree(checkout: Path) -> None:
    """Require every filesystem entry under ``skills/`` to exist in Git's tree."""
    tracked = _git_paths(checkout, "ls-files", "-z", "--cached", "--", "skills")
    tracked_directories = {
        parent.as_posix()
        for path in tracked
        for parent in Path(path).parents
        if parent.as_posix() not in (".", "")
    }
    actual_files: set[str] = set()
    actual_directories: set[str] = set()

    def visit(directory: Path) -> None:
        try:
            children = list(os.scandir(directory))
        except OSError as exc:
            raise RegistryError(f"{directory}: cannot validate tracked git tree") from exc
        for child in children:
            path = Path(child.path)
            relative = path.relative_to(checkout).as_posix()
            try:
                mode = path.lstat().st_mode
            except OSError as exc:
                raise RegistryError(f"{path}: cannot validate tracked git tree") from exc
            if stat.S_ISDIR(mode):
                actual_directories.add(relative)
                visit(path)
            else:
                actual_files.add(relative)

    skills = checkout / "skills"
    if not skills.is_dir() or skills.is_symlink():
        raise RegistryError(f"{skills}: skills root is not a tracked git tree")
    visit(skills)
    if actual_files != tracked or not actual_directories.issubset(tracked_directories):
        raise RegistryError(f"{skills}: filesystem entries must exactly match the tracked git tree")


def build_public_manifest(checkout: Path, release_ref: str) -> dict:
    """Build a path-free public release manifest from an exact tagged checkout."""
    checkout = Path(checkout)
    commit = _git(checkout, "rev-parse", "HEAD")
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise RegistryError(f"{checkout}: public commit is not a full SHA")
    if type(release_ref) is not str or not RELEASE_REF_PATTERN.fullmatch(release_ref):
        raise RegistryError("public release ref must be a numeric three-part release tag")
    tagged_commit = _git(checkout, "rev-parse", "--verify", f"refs/tags/{release_ref}^{{commit}}")
    if tagged_commit != commit:
        raise RegistryError("public release ref does not resolve to the recorded commit")
    repository = normalize_public_repository(_git(checkout, "remote", "get-url", "origin"))
    if _git(checkout, "status", "--porcelain", "--untracked-files=all"):
        raise RegistryError(f"{checkout}: public checkout must be clean at the recorded commit")
    _validate_tracked_skills_tree(checkout)
    inventory = skill_directories(checkout / "skills")
    rows = []
    for name, skill_dir in inventory.items():
        record = read_skill(skill_dir / "SKILL.md")
        domain = derive_domain(name)
        prompt = example_prompt(name, record["description"], domain)
        if not is_user_prompt_like(prompt) or _has_control(prompt):
            raise RegistryError(f"{skill_dir}: cannot freeze a safe example prompt")
        rows.append({
            "name": name,
            "domain": domain,
            "examplePrompt": prompt,
            "skillMdSha256": sha256_file(skill_dir / "SKILL.md"),
            "treeSha256": canonical_tree_sha256(skill_dir),
            "accessCheck": read_access_check(skill_dir / "SKILL.md"),
        })
    data = {
        "schemaVersion": PUBLIC_MANIFEST_SCHEMA,
        "channel": "public-release",
        "repository": repository,
        "commit": commit,
        "releaseRef": release_ref,
        "counts": {"public": len(rows)},
        "skills": rows,
    }
    validate_public_manifest(data, "generated public release manifest")
    return data


_MANIFEST_TOP_KEYS = {"schemaVersion", "channel", "repository", "commit", "releaseRef", "counts", "skills"}
_MANIFEST_ROW_KEYS = {"name", "domain", "examplePrompt", "skillMdSha256", "treeSha256", "accessCheck"}
_ACCESS_CHECK_TYPES = {"license", "userPerm", "orgPerm", "orgPref", "accessCheck"}


def _valid_hash(value) -> bool:
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _valid_access_check(value) -> bool:
    """Validate the tri-state accessCheck: ``None`` (undeclared) or a list of
    ``{type, value}`` entries (``[]`` = any org). Enforces the accessCheck schema
    directly: ``type`` in the fixed ``_ACCESS_CHECK_TYPES`` enum, ``value`` any
    string (no emptiness or control-character constraint), exact ``{type, value}``
    keys. ``None`` and ``[]`` are kept distinct — never collapsed."""
    if value is None:
        return True
    if type(value) is not list:
        return False
    return all(
        type(entry) is dict and set(entry) == {"type", "value"}
        and entry["type"] in _ACCESS_CHECK_TYPES and type(entry["value"]) is str
        for entry in value
    )


def validate_public_manifest(data, context: str) -> None:
    if type(data) is not dict or set(data) != _MANIFEST_TOP_KEYS:
        raise RegistryError(f"{context}: invalid top-level public manifest keys")
    if data["schemaVersion"] != PUBLIC_MANIFEST_SCHEMA or data["channel"] != "public-release":
        raise RegistryError(f"{context}: unsupported public manifest schema or channel")
    if data["repository"] != PUBLIC_REPOSITORY or not re.fullmatch(r"[0-9a-f]{40}", data["commit"] or ""):
        raise RegistryError(f"{context}: invalid public repository or commit")
    if type(data["releaseRef"]) is not str or not RELEASE_REF_PATTERN.fullmatch(data["releaseRef"]):
        raise RegistryError(f"{context}: invalid public release ref")
    if type(data["counts"]) is not dict or set(data["counts"]) != {"public"} or type(data["counts"]["public"]) is not int:
        raise RegistryError(f"{context}: invalid public manifest counts")
    if type(data["skills"]) is not list or data["counts"]["public"] != len(data["skills"]):
        raise RegistryError(f"{context}: public skill count mismatch")
    names: list[str] = []
    for index, row in enumerate(data["skills"]):
        row_context = f"{context}: public skill row {index}"
        if type(row) is not dict or set(row) != _MANIFEST_ROW_KEYS:
            raise RegistryError(f"{row_context}: invalid keys")
        name = row["name"]
        if type(name) is not str or not NAME_PATTERN.fullmatch(name) or len(name) > 64:
            raise RegistryError(f"{row_context}: invalid name")
        if row["domain"] != derive_domain(name):
            raise RegistryError(f"{row_context}: invalid domain")
        prompt = row["examplePrompt"]
        if (type(prompt) is not str or not 1 <= len(prompt) <= 140
                or _has_control(prompt) or not is_user_prompt_like(prompt)):
            raise RegistryError(f"{row_context}: invalid example prompt")
        if not _valid_hash(row["skillMdSha256"]) or not _valid_hash(row["treeSha256"]):
            raise RegistryError(f"{row_context}: invalid content hash")
        if not _valid_access_check(row["accessCheck"]):
            raise RegistryError(f"{row_context}: invalid accessCheck")
        names.append(name)
    if names != sorted(names) or len(names) != len(set(names)):
        raise RegistryError(f"{context}: public skill names must be unique and sorted")


def serialize(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def load_public_manifest_observation(path: Path) -> tuple[dict, bytes]:
    """Load and validate a manifest while retaining the exact verified bytes."""
    try:
        content = read_regular_file_bytes(Path(path), max_bytes=16 * 1024 * 1024)
        data = json.loads(content.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RegistryError(f"{path}: cannot load public release manifest: {exc}") from exc
    validate_public_manifest(data, str(path))
    return data, content


def load_public_manifest(path: Path) -> dict:
    return load_public_manifest_observation(path)[0]


def snapshot_public(checkout: Path, destination: Path, release_ref: str) -> Path:
    data = build_public_manifest(checkout, release_ref)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(serialize(data), encoding="utf-8")
    return destination


def check_public(checkout: Path, destination: Path, release_ref: str) -> bool:
    try:
        actual = read_regular_file_bytes(destination, max_bytes=16 * 1024 * 1024).decode("utf-8")
    except (OSError, UnicodeError, RegistryError) as exc:
        raise RegistryError(f"{destination}: public manifest is missing: {exc}") from exc
    expected = serialize(build_public_manifest(checkout, release_ref))
    if actual != expected:
        raise RegistryError(f"{destination}: public release manifest is stale")
    return True


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--snapshot-public", action="store_true")
    modes.add_argument("--check-public", action="store_true")
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--release-ref", required=True)
    parser.add_argument("--output", type=Path)
    options = parser.parse_args(argv)
    plugin_root = Path(__file__).resolve().parent.parent
    destination = options.output or plugin_root / PUBLIC_MANIFEST_RELATIVE
    try:
        if options.snapshot_public:
            snapshot_public(options.checkout, destination, options.release_ref)
            print(f"generated public release manifest: {destination}")
        else:
            check_public(options.checkout, destination, options.release_ref)
            print(f"public release manifest is current: {destination}")
    except RegistryError as exc:
        print(f"capability registry error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
