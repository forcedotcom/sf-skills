#!/usr/bin/env python3
"""Offline release-gate tests for the publishable Salesforce plugin tree."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Optional

from _test_support import load_module

SCRIPTS = Path(__file__).resolve().parent.parent
PLUGIN_ROOT = SCRIPTS.parent
REPO_ROOT = PLUGIN_ROOT.parents[2]
WORKFLOW = REPO_ROOT / ".github/workflows/release-to-public.yml"


class PublicReleaseGateTests(unittest.TestCase):
    def copy_release_candidate(self, destination: Path) -> None:
        shutil.copytree(
            PLUGIN_ROOT,
            destination,
            ignore=shutil.ignore_patterns(".sf", ".pytest_cache", "__pycache__", "*.pyc"),
        )

    def run_gate(self, plugin_root: Path, *, public_root: Optional[Path] = None):
        command = [
            "python3", str(plugin_root / "scripts/verify-public-plugin-release.py"),
            "--plugin-root", str(plugin_root),
            "--authoring-root", str(REPO_ROOT / "skills"),
        ]
        if public_root is not None:
            command += ["--public-root", str(public_root)]
        return subprocess.run(
            command,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_current_publishable_tree_passes_catalog_and_description_gate(self):
        with tempfile.TemporaryDirectory() as td:
            plugin = Path(td) / "salesforce-development"
            self.copy_release_candidate(plugin)
            result = self.run_gate(plugin)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("public plugin release gate passed", result.stdout)

    def test_public_only_description_anywhere_in_release_tree_fails(self):
        with tempfile.TemporaryDirectory() as td:
            plugin = Path(td) / "salesforce-development"
            self.copy_release_candidate(plugin)
            public_only = REPO_ROOT / "skills/agentforce-architecture-analyze/SKILL.md"
            registry = load_module(SCRIPTS / "capability_registry.py", "release_gate_registry")
            description = registry.read_skill(public_only)["description"]
            (plugin / "LEAK.txt").write_text(description, encoding="utf-8")
            result = self.run_gate(plugin)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("description leak", result.stderr.lower())
        self.assertIn("LEAK.txt", result.stderr)

    def test_previous_public_description_from_public_tree_is_protected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            plugin = root / "salesforce-development"
            self.copy_release_candidate(plugin)
            public_root = root / "public-skills"
            skill = public_root / "agentforce-architecture-analyze"
            skill.mkdir(parents=True)
            description = (
                "Use this previous public release description to review Salesforce "
                "architecture safely without exposing stale catalog prose to runtime consumers."
            )
            (skill / "SKILL.md").write_text(
                f'---\nname: {skill.name}\ndescription: "{description}"\n---\nbody\n',
                encoding="utf-8",
            )
            (plugin / "STALE.md").write_text(description, encoding="utf-8")
            result = self.run_gate(plugin, public_root=public_root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("description leak", result.stderr.lower())
        self.assertIn("STALE.md", result.stderr)

    def test_json_escaped_full_description_fails(self):
        # A protected description present ONLY in JSON-escaped form — its raw UTF-8
        # bytes never appear verbatim — must still be caught, via the JSON-*decoded*
        # string check rather than the raw-bytes check. Escaping one interior space to
        # a backslash-u-0020 unicode escape makes the raw description provably absent,
        # isolating the decoded path.
        with tempfile.TemporaryDirectory() as td:
            plugin = Path(td) / "salesforce-development"
            self.copy_release_candidate(plugin)
            registry = load_module(SCRIPTS / "capability_registry.py", "release_gate_json_registry")
            source = REPO_ROOT / "skills/automation-sandbox-post-copy-config-generate/SKILL.md"
            description = registry.read_skill(source)["description"]
            self.assertIn(" ", description)
            literal = json.dumps(description).replace(" ", "\\u0020", 1)
            leak = plugin / "LEAK.json"
            leak.write_text('{"nested": [' + literal + "]}", encoding="utf-8")
            self.assertNotIn(description.encode("utf-8"), leak.read_bytes())
            result = self.run_gate(plugin)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("description leak", result.stderr.lower())
        self.assertIn("LEAK.json", result.stderr)

    def test_malformed_json_in_release_tree_fails_closed(self):
        # A publishable .json that won't parse can't be scanned for a JSON-escaped
        # leak, so the gate must fail closed — not fall back to the raw-bytes check
        # alone (which would miss an escaped form).
        with tempfile.TemporaryDirectory() as td:
            plugin = Path(td) / "salesforce-development"
            self.copy_release_candidate(plugin)
            (plugin / "broken.json").write_text('{"nested": [', encoding="utf-8")
            result = self.run_gate(plugin)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unparseable json", result.stderr.lower())
        self.assertIn("broken.json", result.stderr)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_symlink_in_release_tree_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            plugin = Path(td) / "salesforce-development"
            self.copy_release_candidate(plugin)
            os.symlink("/etc/hostname", plugin / "LINK.md")
            result = self.run_gate(plugin)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("link or special file", result.stderr.lower())

    @unittest.skipUnless(hasattr(os, "link"), "hardlinks unavailable")
    def test_hardlinked_release_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            plugin = Path(td) / "salesforce-development"
            self.copy_release_candidate(plugin)
            os.link(plugin / "README.md", plugin / "HARDLINK.md")
            result = self.run_gate(plugin)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("link or special file", result.stderr.lower())

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFOs unavailable")
    def test_special_file_in_release_tree_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            plugin = Path(td) / "salesforce-development"
            self.copy_release_candidate(plugin)
            os.mkfifo(plugin / "PIPE")
            result = self.run_gate(plugin)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("link or special file", result.stderr.lower())

    def test_release_tree_depth_limit_is_enforced(self):
        with tempfile.TemporaryDirectory() as td:
            plugin = Path(td) / "salesforce-development"
            self.copy_release_candidate(plugin)
            deep = plugin.joinpath(*(["d"] * 34))  # exceeds _RELEASE_MAX_DEPTH (32)
            deep.mkdir(parents=True)
            (deep / "f.txt").write_text("x", encoding="utf-8")
            result = self.run_gate(plugin)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("depth limit", result.stderr.lower())

    def test_transient_directory_is_rejected_not_silently_excluded(self):
        with tempfile.TemporaryDirectory() as td:
            plugin = Path(td) / "salesforce-development"
            self.copy_release_candidate(plugin)
            leak = plugin / ".sf/LEAK.txt"
            leak.parent.mkdir()
            leak.write_text("not publishable", encoding="utf-8")
            result = self.run_gate(plugin)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("transient", result.stderr.lower())
        self.assertIn(".sf", result.stderr)

    def test_stale_discovery_catalog_fails(self):
        with tempfile.TemporaryDirectory() as td:
            plugin = Path(td) / "salesforce-development"
            self.copy_release_candidate(plugin)
            artifact = plugin / "catalog/discovery.json"
            artifact.write_text(artifact.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            result = self.run_gate(plugin)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("stale", result.stderr.lower())

    def test_publish_workflow_runs_source_pre_copy_and_copied_gates_in_order(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        command = "verify-public-plugin-release.py"
        source_gate = workflow.index("Verify source plugin release tree")
        clone = workflow.index("git clone ")
        self.assertIn("Verify previous public descriptions before copy", workflow)
        pre_copy_gate = workflow.index("Verify previous public descriptions before copy")
        bootstrap = workflow.index("# Idempotent bootstrap:")
        copied_gate = workflow.index("Verify copied public plugin release tree")
        self.assertGreaterEqual(workflow.count(command), 3)
        self.assertLess(source_gate, clone)
        self.assertLess(clone, pre_copy_gate)
        self.assertLess(pre_copy_gate, bootstrap)
        self.assertLess(bootstrap, copied_gate)
        pre_copy_block = workflow[pre_copy_gate:bootstrap]
        self.assertIn('--public-root "skills"', pre_copy_block)


if __name__ == "__main__":
    unittest.main(verbosity=2)
