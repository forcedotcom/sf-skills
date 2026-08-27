#!/usr/bin/env python3
"""Print the active Salesforce package directory from sfdx-project.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import NoReturn


def fail(message: str) -> NoReturn:
    print(f"resolve-package-directory: {message}", file=sys.stderr)
    raise SystemExit(1)


def resolve(project_dir: Path) -> str:
    project_file = project_dir / "sfdx-project.json"
    if not project_file.is_file():
        fail(f"no sfdx-project.json found in '{project_dir}'")

    try:
        data = json.loads(project_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        fail(f"cannot parse '{project_file}': {exc}")

    if not isinstance(data, dict):
        fail("sfdx-project.json must contain a JSON object")

    package_directories = data.get("packageDirectories")
    if not isinstance(package_directories, list) or not package_directories:
        fail("sfdx-project.json has no non-empty packageDirectories array")

    selected = next(
        (
            entry
            for entry in package_directories
            if isinstance(entry, dict) and entry.get("default") is True
        ),
        package_directories[0],
    )
    if not isinstance(selected, dict):
        fail("selected packageDirectories entry must be an object")

    package_path = selected.get("path")
    if not isinstance(package_path, str) or not package_path.strip():
        fail("selected packageDirectories entry has no non-empty path")

    return package_path.strip().rstrip("/") or "."


def main() -> int:
    if len(sys.argv) > 2:
        fail("usage: resolve-package-directory.py [project-dir]")
    project_dir = Path(sys.argv[1] if len(sys.argv) == 2 else ".")
    print(resolve(project_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
