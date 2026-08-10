#!/usr/bin/env python3
"""Privacy-minimal opt-in Claude Code status line for Salesforce DX projects."""
from __future__ import annotations

import json
import os
import re
import stat
import sys
import unicodedata
from pathlib import Path
from typing import Optional

_MAX_INPUT = 64 * 1024
_MAX_DESCRIPTOR = 64 * 1024
_MAX_ANCESTORS = 24
_ANSI = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\)?)")
_BIDI = frozenset(
    {"\u061c", "\u200e", "\u200f", *map(chr, range(0x202A, 0x202F)),
     *map(chr, range(0x2066, 0x2070))}
)


def _codepoint_cells(ch: str) -> int:
    if unicodedata.combining(ch) or unicodedata.category(ch) in {"Mn", "Me"}:
        return 0
    if unicodedata.east_asian_width(ch) in {"W", "F"} or 0x1F000 <= ord(ch) <= 0x1FAFF:
        return 2
    return 1


def terminal_cells(value: str) -> int:
    return sum(_codepoint_cells(ch) for ch in value)


def clip_cells(value: str, limit: int) -> str:
    if terminal_cells(value) <= limit:
        return value
    kept: list[str] = []
    used = 0
    for ch in value:
        width = _codepoint_cells(ch)
        if used + width > max(0, limit - 1):
            break
        kept.append(ch)
        used += width
    return "".join(kept).rstrip() + "…"


def sanitize(value: object, limit: int = 48) -> str:
    text = _ANSI.sub("", value if isinstance(value, str) else "")
    safe = "".join(
        ch for ch in text
        if unicodedata.category(ch) not in {"Cc", "Cf", "Zl", "Zp"} and ch not in _BIDI
    )
    return clip_cells(" ".join(safe.split()), limit)


def payload_cwd(payload: dict) -> Optional[Path]:
    candidates = [payload.get("cwd")]
    workspace = payload.get("workspace")
    if isinstance(workspace, dict):
        candidates.extend((workspace.get("current_dir"), workspace.get("project_dir")))
    cwd = payload.get("cwd")
    if isinstance(cwd, dict):
        candidates.extend((cwd.get("current_dir"), cwd.get("project_dir")))
    for candidate in candidates:
        if isinstance(candidate, str) and candidate:
            try:
                return Path(candidate).resolve(strict=True)
            except (OSError, RuntimeError):
                return None
    return None


def find_descriptor(start: Path) -> Optional[Path]:
    current = start if start.is_dir() else start.parent
    for _ in range(_MAX_ANCESTORS):
        descriptor = current / "sfdx-project.json"
        try:
            if descriptor.is_symlink():
                return None
            metadata = descriptor.lstat()
        except OSError:
            pass
        else:
            if stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1:
                return descriptor
            return None
        if current == current.parent:
            break
        current = current.parent
    return None


def read_descriptor(path: Path) -> Optional[dict]:
    try:
        before = path.lstat()
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                or before.st_size > _MAX_DESCRIPTOR):
            return None
        flags = os.O_RDONLY
        for name in ("O_CLOEXEC", "O_NOFOLLOW", "O_NONBLOCK", "O_BINARY"):
            flags |= getattr(os, name, 0)
        fd = os.open(path, flags)
        try:
            opened = os.fstat(fd)
            if (opened.st_dev, opened.st_ino, opened.st_mode, opened.st_size) != (
                before.st_dev, before.st_ino, before.st_mode, before.st_size
            ):
                return None
            content = os.read(fd, _MAX_DESCRIPTOR + 1)
            if len(content) > _MAX_DESCRIPTOR:
                return None
            finished = os.fstat(fd)
        finally:
            os.close(fd)
        current = path.lstat()
        if (finished.st_size, finished.st_mtime_ns, finished.st_ctime_ns) != (
            current.st_size, current.st_mtime_ns, current.st_ctime_ns
        ):
            return None
        data = json.loads(content.decode("utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        return None


def render(payload: dict) -> str:
    cwd = payload_cwd(payload)
    if cwd is None:
        return ""
    descriptor = find_descriptor(cwd)
    if descriptor is None:
        return ""
    project = read_descriptor(descriptor)
    if project is None:
        return ""
    name = sanitize(project.get("name")) or sanitize(descriptor.parent.name) or "project"
    api = sanitize(project.get("sourceApiVersion"), 12) or "?"
    packages = project.get("packageDirectories")
    count = len(packages) if isinstance(packages, list) else 0
    line = f"SF · {name} · API {api} · {count} package{'s' if count != 1 else ''}"
    return sanitize(line, 80)


def main() -> int:
    try:
        raw = sys.stdin.read(_MAX_INPUT + 1)
        if not raw or len(raw) > _MAX_INPUT:
            return 0
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            return 0
        line = render(payload)
        if line:
            print(line)
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
