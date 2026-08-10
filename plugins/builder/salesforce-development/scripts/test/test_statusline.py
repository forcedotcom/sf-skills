#!/usr/bin/env python3
"""Local-only privacy and portability contracts for the opt-in status line."""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unicodedata
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
HELPER = SCRIPTS / "salesforce-statusline.py"


def terminal_cells(value: str) -> int:
    return sum(
        0 if unicodedata.combining(ch) else
        2 if unicodedata.east_asian_width(ch) in {"W", "F"} or 0x1F000 <= ord(ch) <= 0x1FAFF else 1
        for ch in value
    )


class SalesforceStatusLineTests(unittest.TestCase):
    def run_helper(self, payload, *, cwd=None):
        return subprocess.run(
            ["python3", str(HELPER)],
            input=payload if isinstance(payload, str) else json.dumps(payload),
            text=True,
            capture_output=True,
            cwd=cwd,
            timeout=2,
            check=False,
            env={"PATH": os.environ.get("PATH", "")},
        )

    def project(self, root: Path, *, name="Acme CRM") -> Path:
        root.mkdir(parents=True, exist_ok=True)
        (root / "sfdx-project.json").write_text(json.dumps({
            "name": name,
            "sourceApiVersion": "67.0",
            "packageDirectories": [
                {"path": "force-app", "default": True},
                {"path": "packages/shared"},
            ],
        }), encoding="utf-8")
        nested = root / "force-app/main/default"
        nested.mkdir(parents=True)
        return nested

    def test_project_payload_emits_one_bounded_privacy_minimal_line(self):
        with tempfile.TemporaryDirectory() as td:
            nested = self.project(Path(td) / "project")
            result = self.run_helper({
                "workspace": {"current_dir": str(nested)},
                "model": {"display_name": "Claude"},
                "orgAlias": "secret-sandbox",
                "username": "user@example.com",
                "instanceUrl": "https://secret.example.com",
            })
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertEqual(result.stdout, "SF · Acme CRM · API 67.0 · 2 packages\n")
        for secret in ("secret-sandbox", "user@example.com", "secret.example.com"):
            self.assertNotIn(secret, result.stdout)
        self.assertLessEqual(terminal_cells(result.stdout.rstrip("\n")), 80)

    def test_nonproject_malformed_oversized_and_missing_input_are_silent(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for payload in ({"workspace": {"current_dir": str(root)}}, "{bad", "x" * 70000, ""):
                with self.subTest(kind=type(payload).__name__):
                    result = self.run_helper(payload, cwd=root)
                    self.assertEqual(result.returncode, 0)
                    self.assertEqual((result.stdout, result.stderr), ("", ""))

    def test_hostile_descriptor_text_is_single_line_and_clipped(self):
        with tempfile.TemporaryDirectory() as td:
            nested = self.project(
                Path(td) / "project",
                name="Acme\n\x1b[31m" + "界" * 100 + "\u202e",
            )
            result = self.run_helper({"cwd": {"current_dir": str(nested)}})
        self.assertEqual(result.returncode, 0)
        self.assertEqual(len(result.stdout.splitlines()), 1)
        self.assertNotIn("\x1b", result.stdout)
        self.assertNotIn("\u202e", result.stdout)
        self.assertLessEqual(terminal_cells(result.stdout.rstrip("\n")), 80)

    def test_symlinked_descriptor_is_silent(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symlinks unavailable")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "project"
            root.mkdir()
            outside = Path(td) / "outside.json"
            outside.write_text('{"name":"Do not read"}', encoding="utf-8")
            (root / "sfdx-project.json").symlink_to(outside)
            result = self.run_helper({"cwd": str(root)})
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "", ""))


if __name__ == "__main__":
    unittest.main(verbosity=2)
