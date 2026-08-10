#!/usr/bin/env python3
"""Cell-width and byte-stability contracts for discovery human rendering."""
from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from _test_support import load_module

SCRIPTS = Path(__file__).resolve().parent.parent
PLUGIN_ROOT = SCRIPTS.parent
CATALOG_PATH = SCRIPTS / "discovery_catalog.py"

catalog = load_module(CATALOG_PATH, "discovery_human_bounds_catalog")


class DiscoveryHumanBoundsTests(unittest.TestCase):
    def run_discovery(self, args, cwd, home):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = catalog.run_discovery(args, plugin_root=PLUGIN_ROOT, cwd=cwd, home=home)
        return code, out.getvalue(), err.getvalue()

    def assert_bounded(self, output: str, install_command: str | None = None):
        for line in output.splitlines():
            if install_command is not None and line == install_command:
                continue
            self.assertLessEqual(
                catalog._terminal_cell_width(line), 80, f"over-wide line: {line!r}"
            )

    def test_largest_real_domain_and_complete_index_are_cell_bounded(self):
        artifact = catalog.load_catalog(PLUGIN_ROOT)
        domains = {}
        for row in artifact["skills"]:
            domains.setdefault(row["domain"], []).append(row["name"])
        largest, names = max(domains.items(), key=lambda item: len(item[1]))
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            code, domain_out, err = self.run_discovery(
                ["domain", largest], root, root / "home"
            )
            self.assertEqual((code, err), (0, ""))
            self.assert_bounded(domain_out)
            for name in names:
                self.assertIn(name, domain_out)

            code, index_out, err = self.run_discovery(["index"], root, root / "home")
            self.assertEqual((code, err), (0, ""))
            self.assert_bounded(index_out)
            for row in artifact["skills"]:
                self.assertIn(row["name"], index_out)

    def test_longest_real_installed_description_is_complete_and_cell_bounded(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _, rows = catalog._runtime_rows(PLUGIN_ROOT, root, root / "home")
            row = max(
                (item for item in rows if "description" in item),
                key=lambda item: len(item["description"]),
            )
            code, out, err = self.run_discovery(
                ["skill", row["name"]], root, root / "home"
            )
        self.assertEqual((code, err), (0, ""))
        self.assert_bounded(out)
        self.assertIn(
            " ".join(catalog._sanitize_dynamic_text(row["description"]).split()),
            " ".join(out.split()),
        )
        self.assertIn(row["provenance"]["state"], out)
        self.assertIn(row["provenance"]["scope"], out)

    def test_two_byte_escape_sequences_do_not_consume_safe_following_text(self):
        for value in ("A\x1b7B", "A\x1bcB"):
            with self.subTest(value=repr(value)):
                self.assertEqual(catalog._sanitize_dynamic_text(value), "AB")

    def test_leading_cluster_extenders_wrap_without_loss_or_source_displacement(self):
        for extender in ("\u0301", "\ufe0f", "\U0001f3fb", "\u200d"):
            with self.subTest(extender=f"U+{ord(extender):04X}"):
                value = extender + "A" * 90
                chunk, remainder = catalog._take_cells(value, 4)
                self.assertEqual(chunk + remainder, value)
                self.assertEqual(chunk, extender + "A" * 4)
                self.assertEqual(remainder, "A" * 86)

                lines = catalog._wrapped_dynamic_lines(value, subsequent="  ")
                reconstructed = lines[0] + "".join(line[2:] for line in lines[1:])
                self.assertEqual(reconstructed, value)
                self.assertTrue(all(catalog._terminal_cell_width(line) <= 80 for line in lines))

    def test_synthetic_unicode_and_controls_are_sanitized_wrapped_not_executed(self):
        hostile = (
            "請勿執行" * 30
            + "\nINJECTED\t"
            + "\x1b]8;;https://evil.invalid\x07click\x1b]8;;\x07"
            + "\u202e"
            + "👩🏽\u200d💻" * 20
        )
        row = {
            "name": "platform-synthetic-search",
            "domain": "platform",
            "examplePrompt": hostile,
            "publicAvailable": False,
            "foundationInstalled": True,
            "variants": {"foundation": {"skillMdSha256": "a" * 64, "treeSha256": "b" * 64}},
            "status": "installed",
            "provenance": {
                "state": hostile,
                "scope": hostile,
                "records": [],
                "observations": [],
            },
            "description": hostile,
        }
        release = {"publicRelease": {"releaseRef": "1.32.0"}}
        for args in (["domain", "platform"], ["skill", row["name"]], ["index"]):
            with self.subTest(args=args), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                with mock.patch.object(catalog, "_runtime_rows", return_value=(release, [row])):
                    code, out, err = self.run_discovery(args, root, root / "home")
                self.assertEqual((code, err), (0, ""))
                self.assert_bounded(out)
                self.assertNotIn("\x1b", out)
                self.assertNotIn("\nINJECTED", out)
                self.assertNotIn("\t", out)
                self.assertNotIn("\u202e", out)
                self.assertIn("請勿執行", out)

    def test_json_mode_snapshots_and_public_install_command_bytes_are_unchanged(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cat, rows = catalog._runtime_rows(PLUGIN_ROOT, root, root / "home")
            domain = max(
                {row["domain"] for row in rows},
                key=lambda value: sum(row["domain"] == value for row in rows),
            )
            group = [row for row in rows if row["domain"] == domain]
            available = next(
                row for row in rows
                if row["status"] == "available"
                and row["publicAvailable"]
                and not row["foundationInstalled"]
            )
            compact = [{
                "name": row["name"], "domain": row["domain"], "status": row["status"],
                "provenance": {
                    "state": row["provenance"]["state"],
                    "scope": row["provenance"]["scope"],
                },
                "examplePrompt": row["examplePrompt"],
            } for row in rows]
            expected_domain = json.dumps(
                {"mode": "domain", "domain": domain, "skills": group},
                ensure_ascii=False, separators=(",", ":"),
            ) + "\n"
            detail = {"mode": "skill", **available}
            command = catalog.INSTALL_TEMPLATE.format(
                name=available["name"], release_ref=cat["publicRelease"]["releaseRef"]
            )
            detail["installInstruction"] = command
            detail["sessionRequirement"] = catalog.SESSION_REQUIREMENT
            expected_skill = json.dumps(
                detail, ensure_ascii=False, separators=(",", ":")
            ) + "\n"
            expected_index = json.dumps(
                {"mode": "index", "skills": compact},
                ensure_ascii=False, separators=(",", ":"),
            ) + "\n"

            for args, expected in (
                (["domain", domain, "--json"], expected_domain),
                (["skill", available["name"], "--json"], expected_skill),
                (["index", "--json"], expected_index),
            ):
                with self.subTest(args=args):
                    code, out, err = self.run_discovery(args, root, root / "home")
                    self.assertEqual((code, err, out), (0, "", expected))

            # Frozen public JSON key contracts, independent of the current-row
            # construction above, catch additive/removal regressions explicitly.
            _, domain_raw, _ = self.run_discovery(["domain", domain, "--json"], root, root / "home")
            _, skill_raw, _ = self.run_discovery(["skill", available["name"], "--json"], root, root / "home")
            _, index_raw, _ = self.run_discovery(["index", "--json"], root, root / "home")
            self.assertEqual(set(json.loads(domain_raw)), {"mode", "domain", "skills"})
            self.assertEqual(set(json.loads(skill_raw)), {
                "mode", "name", "domain", "examplePrompt", "publicAvailable",
                "foundationInstalled", "variants", "status", "catalogMetadataNotice",
                "provenance", "installInstruction", "sessionRequirement",
            })
            self.assertEqual(set(json.loads(index_raw)), {"mode", "skills"})
            self.assertEqual(set(json.loads(index_raw)["skills"][0]), {
                "name", "domain", "status", "provenance", "examplePrompt",
            })

            code, human, err = self.run_discovery(
                ["skill", available["name"]], root, root / "home"
            )
        self.assertEqual((code, err), (0, ""))
        self.assertEqual([line for line in human.splitlines() if line == command], [command])
        self.assert_bounded(human, install_command=command)


if __name__ == "__main__":
    unittest.main(verbosity=2)
