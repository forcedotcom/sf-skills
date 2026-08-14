#!/usr/bin/env python3
"""Release documentation and design-link contracts for plugin 1.11.0."""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent
PLUGIN = TESTS.parent.parent
REPO = PLUGIN.parents[2]
DESIGN = REPO / "docs/design"
README = PLUGIN / "README.md"
CONFIG_DOC = PLUGIN / "docs/configuration.md"
CHANGELOG = PLUGIN / "CHANGELOG.md"
COMMAND = PLUGIN / "commands/discovery.md"
SKILL = PLUGIN / "skills/platform-capability-search/SKILL.md"
STAGES = "Connect → Project → Build → Test → Deploy → Observe"


class DocumentationContractTests(unittest.TestCase):
    def text(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")

    def test_release_version_minimum_and_changelog_are_reconciled(self):
        plugin = json.loads((PLUGIN / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(plugin["version"], "1.11.0")
        readme = self.text(README)
        self.assertIn("Claude Code 2.1.222 or later", readme)
        self.assertIn("## [1.11.0]", self.text(CHANGELOG))

    def test_current_docs_share_the_six_stage_contract(self):
        paths = [README, DESIGN / "README.md", DESIGN / "headless-360-pov.md",
                 DESIGN / "decision-log.md", COMMAND, SKILL]
        for path in paths:
            with self.subTest(path=path):
                text = self.text(path)
                self.assertIn(STAGES, text)
                self.assertNotIn("Setup · Connect · Build · Test · Deploy · Observe", text)
                self.assertNotIn("setup · connect · build · test · deploy · observe", text)
                self.assertNotIn("journey-rail-two-tier-redesign.md", text)

    def test_readme_links_to_configuration_reference(self):
        text = self.text(README)
        self.assertIn("docs/configuration.md", text)

    def test_configuration_doc_documents_modes_no_color_and_manual_status_line(self):
        text = self.text(CONFIG_DOC)
        for mode in ("`full`", "`compact`", "`plain`", "`off`"):
            self.assertIn(mode, text)
        self.assertIn("CLAUDE_PLUGIN_OPTION_UI_MODE", text)
        self.assertIn("NO_COLOR", text)
        self.assertIn("~/.claude/statusline/salesforce-development.py", text)
        self.assertIn("salesforce-statusline.py", text)
        self.assertRegex(text, r"(?i)never (?:edits|modify|writes) .*settings")
        self.assertRegex(text, r"(?i)explicit.*status.*setup.*discovery")

    def test_docs_cover_runtime_truth_and_schema_transitions(self):
        combined = "\n".join(self.text(path) for path in (
            README, DESIGN / "headless-360-pov.md", DESIGN / "decision-log.md"
        ))
        for phrase in (
            "manifest schema 2.0", "catalog schema 3.0", "same-scan exact bytes",
            "local-first", "prompt-dispatch", "post-bash", "current-org",
            "other-org", "unattributed", "journey inspect", "journey reset",
        ):
            self.assertIn(phrase, combined)

    def test_relative_markdown_links_in_design_docs_resolve(self):
        for path in DESIGN.glob("*.md"):
            for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", self.text(path)):
                if "://" in target or target.startswith("#"):
                    continue
                resolved = (path.parent / target.split("#", 1)[0]).resolve()
                self.assertTrue(resolved.exists(), f"broken link in {path}: {target}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
