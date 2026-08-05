#!/usr/bin/env python3
"""Channel-aware Salesforce capability registry primitives.

The public release manifest is the only release-channel input to the checked
catalog. Internal authoring inventory is read only for an explicitly gated,
in-memory preview and is never serialized by this module.

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

PUBLIC_MANIFEST_SCHEMA = "1.0"
PUBLIC_REPOSITORY = "https://github.com/forcedotcom/sf-skills.git"
RELEASE_REF_PATTERN = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+")
PUBLIC_MANIFEST_RELATIVE = Path("catalog/public-release-manifest.json")
TREE_HASH_FORMAT = b"sf-skill-tree-v1\0"
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


def sha256_file(path: Path) -> str:
    """Hash one regular file as raw bytes."""
    try:
        mode = path.lstat().st_mode
        if not stat.S_ISREG(mode):
            raise RegistryError(f"{path}: expected a regular file")
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError as exc:
        raise RegistryError(f"{path}: cannot hash file: {exc}") from exc


def _hash_field(digest, value: bytes) -> None:
    digest.update(len(value).to_bytes(8, "big"))
    digest.update(value)


def canonical_tree_sha256(root: Path, *, safety_root: Optional[Path] = None) -> str:
    """Return the canonical ``sf-skill-tree-v1`` hash for a directory tree.

    ``safety_root`` defaults to the hashed tree. Inventory callers may supply
    their containing checkout so intentional shared-file symlinks remain safe;
    links escaping that declared root are always rejected.
    """
    root = Path(root)
    safety_root = Path(safety_root) if safety_root is not None else root
    try:
        if root.is_symlink() or not root.is_dir() or safety_root.is_symlink() or not safety_root.is_dir():
            raise RegistryError(f"{root}: tree root and safety root must be real directories")
        tree_anchor = root.resolve(strict=True)
        anchor = safety_root.resolve(strict=True)
        tree_anchor.relative_to(anchor)
    except (OSError, ValueError) as exc:
        raise RegistryError(f"{root}: cannot resolve tree root inside safety root: {exc}") from exc

    entries: list[tuple[str, Path, os.stat_result]] = []

    def visit(directory: Path) -> None:
        try:
            children = list(os.scandir(directory))
        except OSError as exc:
            raise RegistryError(f"{directory}: cannot scan tree: {exc}") from exc
        for child in children:
            path = Path(child.path)
            try:
                metadata = path.lstat()
            except OSError as exc:
                raise RegistryError(f"{path}: cannot inspect tree entry: {exc}") from exc
            relative = path.relative_to(root).as_posix()
            entries.append((relative, path, metadata))
            if stat.S_ISDIR(metadata.st_mode):
                visit(path)

    visit(root)
    digest = hashlib.sha256()
    digest.update(TREE_HASH_FORMAT)
    for relative, path, metadata in sorted(entries, key=lambda item: item[0]):
        relative_bytes = relative.encode("utf-8")
        mode = metadata.st_mode
        if stat.S_ISDIR(mode):
            digest.update(b"D")
            _hash_field(digest, relative_bytes)
        elif stat.S_ISREG(mode):
            digest.update(b"F")
            _hash_field(digest, relative_bytes)
            digest.update(b"1" if mode & 0o111 else b"0")
            try:
                content = path.read_bytes()
            except OSError as exc:
                raise RegistryError(f"{path}: cannot read tree file: {exc}") from exc
            _hash_field(digest, content)
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
    return digest.hexdigest()


def _has_control(value: str) -> bool:
    return any(unicodedata.category(char) in {"Cc", "Cf", "Zl", "Zp"} for char in value)


def _frontmatter(path: Path) -> list[str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise RegistryError(f"{path}: cannot read SKILL.md: {exc}") from exc
    if not lines or lines[0].strip() != "---":
        raise RegistryError(f"{path}: missing opening frontmatter delimiter")
    try:
        end = next(index for index in range(1, len(lines)) if lines[index].strip() == "---")
    except StopIteration as exc:
        raise RegistryError(f"{path}: missing closing frontmatter delimiter") from exc
    return lines[1:end]


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


def read_skill(path: Path) -> dict[str, str]:
    """Read the bounded name and description subset from SKILL.md frontmatter."""
    lines = _frontmatter(path)
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


def source_variant(
    skill_dir: Path, *, safety_root: Optional[Path] = None
) -> dict[str, str]:
    record = read_skill(skill_dir / "SKILL.md")
    return {
        "description": record["description"],
        "skillMdSha256": sha256_file(skill_dir / "SKILL.md"),
        "treeSha256": canonical_tree_sha256(skill_dir, safety_root=safety_root),
    }


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
        rows.append({
            "name": name,
            "domain": derive_domain(name),
            "description": record["description"],
            "skillMdSha256": sha256_file(skill_dir / "SKILL.md"),
            "treeSha256": canonical_tree_sha256(skill_dir),
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
_MANIFEST_ROW_KEYS = {"name", "domain", "description", "skillMdSha256", "treeSha256"}


def _valid_hash(value) -> bool:
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


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
        description = row["description"]
        if type(description) is not str or not 1 <= len(description) <= 1024 or _has_control(description):
            raise RegistryError(f"{row_context}: invalid description")
        if not _valid_hash(row["skillMdSha256"]) or not _valid_hash(row["treeSha256"]):
            raise RegistryError(f"{row_context}: invalid content hash")
        names.append(name)
    if names != sorted(names) or len(names) != len(set(names)):
        raise RegistryError(f"{context}: public skill names must be unique and sorted")


def serialize(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def load_public_manifest(path: Path) -> dict:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RegistryError(f"{path}: cannot load public release manifest: {exc}") from exc
    validate_public_manifest(data, str(path))
    return data


def snapshot_public(checkout: Path, destination: Path, release_ref: str) -> Path:
    data = build_public_manifest(checkout, release_ref)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(serialize(data), encoding="utf-8")
    return destination


def check_public(checkout: Path, destination: Path, release_ref: str) -> bool:
    try:
        actual = destination.read_text(encoding="utf-8")
    except OSError as exc:
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
