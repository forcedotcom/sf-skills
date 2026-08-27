#!/usr/bin/env python3
"""Tests for resolve-package-directory.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("resolve-package-directory.py")


class ResolvePackageDirectoryTest(unittest.TestCase):
    def run_resolver(
        self, project: object | None, *, raw: str | None = None
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as directory:
            project_dir = Path(directory)
            if raw is not None:
                (project_dir / "sfdx-project.json").write_text(raw, encoding="utf-8")
            elif project is not None:
                (project_dir / "sfdx-project.json").write_text(
                    json.dumps(project), encoding="utf-8"
                )
            return subprocess.run(
                [sys.executable, str(SCRIPT), str(project_dir)],
                check=False,
                capture_output=True,
                text=True,
            )

    def test_selects_declared_default(self) -> None:
        result = self.run_resolver(
            {
                "packageDirectories": [
                    {"path": "packages/first"},
                    {"path": "packages/default", "default": True},
                ]
            }
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "packages/default\n")
        self.assertEqual(result.stderr, "")

    def test_falls_back_to_first_entry(self) -> None:
        result = self.run_resolver(
            {"packageDirectories": [{"path": "force-app/"}, {"path": "other"}]}
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "force-app\n")

    def test_rejects_missing_project_file(self) -> None:
        result = self.run_resolver(None)
        self.assertEqual(result.returncode, 1)
        self.assertIn("no sfdx-project.json", result.stderr)

    def test_rejects_empty_package_directories(self) -> None:
        result = self.run_resolver({"packageDirectories": []})
        self.assertEqual(result.returncode, 1)
        self.assertIn("no non-empty packageDirectories array", result.stderr)

    def test_rejects_malformed_json(self) -> None:
        result = self.run_resolver(None, raw="{not-json")
        self.assertEqual(result.returncode, 1)
        self.assertIn("cannot parse", result.stderr)

    def test_rejects_selected_entry_without_path(self) -> None:
        result = self.run_resolver(
            {"packageDirectories": [{"path": "first"}, {"default": True}]}
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("has no non-empty path", result.stderr)


if __name__ == "__main__":
    unittest.main()
