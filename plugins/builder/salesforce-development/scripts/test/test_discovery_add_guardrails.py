#!/usr/bin/env python3
"""Guardrails for agent-executed, catalog-authorized one-step skill enablement."""
from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from _test_support import load_module

SCRIPTS = Path(__file__).resolve().parent.parent
PLUGIN_ROOT = SCRIPTS.parent
REPO_ROOT = PLUGIN_ROOT.parents[2]
SKILL_DOC = PLUGIN_ROOT / "skills/platform-capability-search/SKILL.md"
COMMAND_DOC = PLUGIN_ROOT / "commands/discovery.md"
CATALOG_PATH = SCRIPTS / "discovery_catalog.py"
EXPECTED = "npx skills@1.5.20 add forcedotcom/sf-skills#1.32.0 --skill {name} --agent claude-code --yes"


catalog = load_module(CATALOG_PATH, "discovery_add_catalog")


class DiscoveryAddGuardrailTests(unittest.TestCase):
    def run_discovery(self, args, cwd, home):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = catalog.run_discovery(args, plugin_root=PLUGIN_ROOT, cwd=cwd, home=home)
        return code, out.getvalue(), err.getvalue()

    def test_only_available_library_skill_emits_exact_add_instruction(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            rows = catalog.load_catalog(PLUGIN_ROOT)["skills"]
            available = next(row for row in rows if row["publicAvailable"] and not row["foundationInstalled"])
            foundation = next(row for row in rows if row["foundationInstalled"])
            code, out, _ = self.run_discovery(["skill", available["name"], "--json"], root, root / "home")
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)["installInstruction"], EXPECTED.format(name=available["name"]))
            code, out, _ = self.run_discovery(["skill", foundation["name"], "--json"], root, root / "home")
            self.assertEqual(code, 0)
            self.assertNotIn("installInstruction", json.loads(out))

    def test_unknown_and_held_names_cannot_emit_add_instruction(self):
        # Derive held names through the catalog's own manifest reader; never hardcode a draft name.
        held_names = catalog.read_internal_holds(REPO_ROOT / "config.yml")
        self.assertTrue(held_names)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for name in ["not-a-catalog-skill", sorted(held_names)[0]]:
                with self.subTest(name=name):
                    code, out, err = self.run_discovery(["skill", name, "--json"], root, root / "home")
                    self.assertNotEqual(code, 0)
                    self.assertEqual(out, "")
                    self.assertNotIn("npx skills", err)

    def test_skill_doc_requires_guarded_explicit_add_but_browsing_never_installs(self):
        text = SKILL_DOC.read_text(encoding="utf-8")
        self.assertIn("EXPLICITLY asks to add or enable", text)
        self.assertIn("discovery skill <name> --json", text)
        self.assertIn("catalog-emitted `installInstruction`", text)
        self.assertIn("execute that exact instruction once", text)
        self.assertIn("current project", text)
        self.assertIn("rerun", text.lower())
        self.assertIn("fresh Claude session", text)
        self.assertIn("Never install while browsing", text)
        self.assertIn("unknown, held/internal, foundation-installed", text)
        self.assertNotIn("never execute installation from this skill", text)

    def test_discovery_command_handles_natural_language_add_without_shell_argument_interpolation(self):
        text = COMMAND_DOC.read_text(encoding="utf-8")
        self.assertIn("add <name>", text)
        self.assertIn("discovery skill <name> --json", text)
        self.assertIn("execute that exact instruction once", text)
        self.assertIn("Never install for `overview`", text)
        self.assertNotIn("discovery $ARGUMENTS", text)
        self.assertIn("Do not execute arbitrary user text", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
