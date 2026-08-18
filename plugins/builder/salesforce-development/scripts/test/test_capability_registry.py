#!/usr/bin/env python3
"""Channel registry, canonical hashing, and internal-preview contracts."""
from __future__ import annotations

import io
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from _test_support import load_module

SCRIPTS = Path(__file__).resolve().parent.parent
PLUGIN_ROOT = SCRIPTS.parent
REPO_ROOT = PLUGIN_ROOT.parents[2]
REGISTRY_PATH = SCRIPTS / "capability_registry.py"
CATALOG_PATH = SCRIPTS / "discovery_catalog.py"
MANIFEST_PATH = PLUGIN_ROOT / "catalog/public-release-manifest.json"
NOTICE = "INTERNAL PREVIEW — not publicly supported"


class CapabilityRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = load_module(REGISTRY_PATH, "capability_registry_under_test")
        cls.catalog = load_module(CATALOG_PATH, "channel_catalog_under_test")

    def test_windows_path_descriptor_identity_ignores_incompatible_ctime(self):
        path_stat = mock.Mock(
            st_dev=1, st_ino=2, st_mode=3, st_nlink=1, st_size=4,
            st_mtime_ns=5, st_ctime_ns=6,
        )
        descriptor_stat = mock.Mock(
            st_dev=1, st_ino=2, st_mode=3, st_nlink=1, st_size=4,
            st_mtime_ns=5, st_ctime_ns=7,
        )
        with mock.patch.object(self.registry.os, "name", "nt"):
            self.assertEqual(
                self.registry._tree_identity(path_stat, path_descriptor_boundary=True),
                self.registry._tree_identity(descriptor_stat, path_descriptor_boundary=True),
            )
            self.assertNotEqual(
                self.registry._tree_identity(path_stat),
                self.registry._tree_identity(descriptor_stat),
            )

    def test_tree_hash_can_use_canonical_executable_paths(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "skill"
            root.mkdir()
            script = root / "scripts/run.sh"
            script.parent.mkdir()
            script.write_text("#!/bin/sh\n", encoding="utf-8")
            script.chmod(script.stat().st_mode & ~0o111)
            non_executable = self.registry.canonical_tree_sha256(
                root, executable_paths=set()
            )
            executable = self.registry.canonical_tree_sha256(
                root, executable_paths={"scripts/run.sh"}
            )
            self.assertNotEqual(non_executable, executable)

    def test_canonical_tree_hash_is_order_independent_and_tracks_bytes_type_and_execute_bit(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "skill"
            root.mkdir()
            (root / "z.txt").write_bytes(b"z\x00bytes")
            (root / "a.txt").write_bytes(b"alpha")
            first = self.registry.canonical_tree_sha256(root)
            self.assertEqual(first, self.registry.canonical_tree_sha256(root))
            (root / "a.txt").chmod((root / "a.txt").stat().st_mode | stat.S_IXUSR)
            executable = self.registry.canonical_tree_sha256(root)
            self.assertNotEqual(first, executable)
            (root / "a.txt").chmod((root / "a.txt").stat().st_mode & ~0o111)
            self.assertEqual(first, self.registry.canonical_tree_sha256(root))
            (root / "z.txt").write_bytes(b"changed")
            self.assertNotEqual(first, self.registry.canonical_tree_sha256(root))

    def test_hash_rejects_special_files_and_unsafe_symlinks(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "skill"
            root.mkdir()
            (root / "SKILL.md").write_text("safe", encoding="utf-8")
            (root / "outside").symlink_to(Path(td).parent)
            with self.assertRaisesRegex(self.registry.RegistryError, "symlink"):
                self.registry.canonical_tree_sha256(root)
            (root / "outside").unlink()
            fifo = root / "pipe"
            os.mkfifo(fifo)
            with self.assertRaisesRegex(self.registry.RegistryError, "special"):
                self.registry.canonical_tree_sha256(root)

    def test_tree_scan_bounds_entries_depth_file_and_total_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "skill"
            root.mkdir()
            (root / "SKILL.md").write_text("safe", encoding="utf-8")
            (root / "extra.txt").write_text("extra", encoding="utf-8")
            with mock.patch.object(self.registry, "TREE_SCAN_MAX_ENTRIES", 1, create=True):
                with self.assertRaisesRegex(self.registry.RegistryError, "entry limit"):
                    self.registry.inspect_skill_tree(root)
            with mock.patch.object(self.registry, "TREE_SCAN_MAX_DEPTH", 0, create=True):
                nested = root / "nested"
                nested.mkdir()
                with self.assertRaisesRegex(self.registry.RegistryError, "depth limit"):
                    self.registry.inspect_skill_tree(root)
                nested.rmdir()
            with mock.patch.object(self.registry, "TREE_SCAN_MAX_FILE_BYTES", 3, create=True):
                with self.assertRaisesRegex(self.registry.RegistryError, "file byte limit"):
                    self.registry.inspect_skill_tree(root)
            with mock.patch.object(self.registry, "TREE_SCAN_MAX_TOTAL_BYTES", 7, create=True):
                with self.assertRaisesRegex(self.registry.RegistryError, "total byte limit"):
                    self.registry.inspect_skill_tree(root)
            with self.assertRaisesRegex(self.registry.RegistryError, "aggregate tree entry limit"):
                self.registry.inspect_skill_tree(root, budget={
                    "entries": 0, "bytes": 0, "maxEntries": 1, "maxBytes": 1024,
                })
            with self.assertRaisesRegex(self.registry.RegistryError, "aggregate tree byte limit"):
                self.registry.inspect_skill_tree(root, budget={
                    "entries": 0, "bytes": 0, "maxEntries": 100, "maxBytes": 3,
                })

    def test_tree_scan_rejects_hardlinked_regular_files(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "skill"
            root.mkdir()
            outside = Path(td) / "outside.md"
            outside.write_text("safe", encoding="utf-8")
            os.link(outside, root / "SKILL.md")
            with self.assertRaisesRegex(self.registry.RegistryError, "hardlink"):
                self.registry.inspect_skill_tree(root)

    def test_tree_scan_detects_directory_entry_added_after_inventory(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "skill"
            root.mkdir()
            (root / "SKILL.md").write_text("safe", encoding="utf-8")
            real_scandir = self.registry.os.scandir
            calls = 0

            def racing_scandir(path):
                nonlocal calls
                entries = list(real_scandir(path))
                calls += 1
                if calls == 1:
                    (root / "late.txt").write_text("late", encoding="utf-8")
                return entries

            with mock.patch.object(self.registry.os, "scandir", side_effect=racing_scandir):
                with self.assertRaisesRegex(self.registry.RegistryError, "parent directory changed"):
                    self.registry.inspect_skill_tree(root)

    def test_tree_scan_does_not_follow_regular_file_replaced_by_symlink_before_open(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "skill"
            root.mkdir()
            skill = root / "SKILL.md"
            skill.write_text("safe", encoding="utf-8")
            outside = Path(td) / "outside"
            outside.write_text("outside secret bytes", encoding="utf-8")
            original = root / "original"
            real_open = self.registry.os.open
            swapped = False

            def racing_open(path, flags, *args, **kwargs):
                nonlocal swapped
                if Path(path).name == skill.name and not swapped:
                    skill.rename(original)
                    skill.symlink_to(outside)
                    swapped = True
                return real_open(path, flags, *args, **kwargs)

            with mock.patch.object(self.registry.os, "open", side_effect=racing_open):
                with self.assertRaisesRegex(self.registry.RegistryError, "cannot open .*tree file"):
                    self.registry.inspect_skill_tree(root)
            self.assertTrue(swapped, "the test must exercise the pre-open replacement race")

    def test_tree_scan_pins_parent_directory_before_reading_files(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            root = base / "skill"
            root.mkdir()
            (root / "SKILL.md").write_text("safe", encoding="utf-8")
            replacement = base / "replacement"
            replacement.mkdir()
            (replacement / "SKILL.md").write_text("outside secret bytes", encoding="utf-8")
            moved = base / "moved"
            real_open = self.registry.os.open
            swapped = False

            def racing_open(path, flags, *args, **kwargs):
                nonlocal swapped
                if (Path(path) == root and flags & getattr(os, "O_DIRECTORY", 0)
                        and not swapped):
                    root.rename(moved)
                    root.symlink_to(replacement, target_is_directory=True)
                    swapped = True
                return real_open(path, flags, *args, **kwargs)

            with mock.patch.object(self.registry.os, "open", side_effect=racing_open):
                with self.assertRaisesRegex(self.registry.RegistryError, "parent directory"):
                    self.registry.inspect_skill_tree(root)
            self.assertTrue(swapped, "the test must replace the inventoried tree root")

    def test_skill_inventory_rejects_symlinked_skill_markdown(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "skills"
            skill = root / "platform-widget-search"
            skill.mkdir(parents=True)
            outside = Path(td) / "outside.md"
            outside.write_text(
                '---\nname: platform-widget-search\n'
                'description: "Use this outside fixture to prove inventory containment."\n'
                '---\n',
                encoding="utf-8",
            )
            (skill / "SKILL.md").symlink_to(outside)
            with self.assertRaisesRegex(self.registry.RegistryError, "symlink|regular"):
                self.registry.skill_directories(root)

    def _public_checkout_fixture(self, root: Path, origin: str) -> Path:
        checkout = root / "checkout"
        checkout.mkdir()
        subprocess.run(["git", "init", "-q", str(checkout)], check=True)
        subprocess.run(["git", "-C", str(checkout), "config", "user.email", "fixture@example.invalid"], check=True)
        subprocess.run(["git", "-C", str(checkout), "config", "user.name", "Fixture"], check=True)
        skill = checkout / "skills/platform-widget-search"
        skill.mkdir(parents=True)
        skill.joinpath("SKILL.md").write_text(
            '---\nname: platform-widget-search\ndescription: "Use this public fixture to search for platform widgets safely and deterministically."\n---\nbody\n',
            encoding="utf-8",
        )
        # Two more skills exercise the accessCheck tri-state through the real
        # snapshot path: an explicit empty list (applies to any org) and a
        # conditional license/preference gate. platform-widget-search stays the
        # undeclared (no metadata block) case.
        empty_access = checkout / "skills/platform-empty-access-search"
        empty_access.mkdir(parents=True)
        empty_access.joinpath("SKILL.md").write_text(
            '---\nname: platform-empty-access-search\ndescription: "Use this public fixture to confirm an explicit empty accessCheck marks a skill as applying to any org."\nmetadata:\n  version: "1.0"\n  accessCheck: []\n---\nbody\n',
            encoding="utf-8",
        )
        gated = checkout / "skills/platform-gated-search"
        gated.mkdir(parents=True)
        gated.joinpath("SKILL.md").write_text(
            '---\nname: platform-gated-search\ndescription: "Use this public fixture to confirm a conditional accessCheck list survives the snapshot as license and preference gates."\nmetadata:\n  version: "1.0"\n  accessCheck:\n    - type: "license"\n      value: "FixtureLicense"\n    - type: "orgPref"\n      value: "FixturePref"\n---\nbody\n',
            encoding="utf-8",
        )
        subprocess.run(["git", "-C", str(checkout), "add", "."], check=True)
        subprocess.run(["git", "-C", str(checkout), "commit", "-qm", "fixture"], check=True)
        subprocess.run(
            ["git", "-C", str(checkout), "tag", "--no-sign", "-m", "fixture", "1.32.0"],
            check=True,
        )
        subprocess.run(["git", "-C", str(checkout), "remote", "add", "origin", origin], check=True)
        return checkout

    def test_public_snapshot_rejects_ignored_entries_under_skills(self):
        with tempfile.TemporaryDirectory() as td:
            checkout = self._public_checkout_fixture(
                Path(td), "https://github.com/forcedotcom/sf-skills.git"
            )
            checkout.joinpath(".git/info/exclude").write_text("skills/**/ignored.bin\n", encoding="utf-8")
            checkout.joinpath("skills/platform-widget-search/ignored.bin").write_bytes(b"absent from commit")
            with self.assertRaisesRegex(self.registry.RegistryError, "tracked git tree"):
                self.registry.build_public_manifest(checkout, "1.32.0")

    def test_public_origin_normalizes_supported_github_forms_without_echoing_tokens(self):
        accepted = (
            "https://github.com/forcedotcom/sf-skills.git",
            "https://github.com/forcedotcom/sf-skills",
            "git@github.com:forcedotcom/sf-skills.git",
            "ssh://git@github.com/forcedotcom/sf-skills.git",
            "https://x-access-token:do-not-echo@github.com/forcedotcom/sf-skills.git",
        )
        for origin in accepted:
            with self.subTest(origin=origin):
                self.assertEqual(self.registry.normalize_public_repository(origin), self.registry.PUBLIC_REPOSITORY)
        for origin in (
            "https://github.com/other/sf-skills.git",
            "https://gitlab.com/forcedotcom/sf-skills.git",
            "http://github.com/forcedotcom/sf-skills.git",
        ):
            with self.subTest(origin=origin):
                with self.assertRaises(self.registry.RegistryError) as caught:
                    self.registry.normalize_public_repository(origin)
                self.assertNotIn(origin, str(caught.exception))
                self.assertNotIn("do-not-echo", str(caught.exception))

    def test_public_release_ref_is_strict_and_resolves_to_recorded_commit(self):
        with tempfile.TemporaryDirectory() as td:
            checkout = self._public_checkout_fixture(Path(td), "git@github.com:forcedotcom/sf-skills.git")
            manifest = self.registry.build_public_manifest(checkout, "1.32.0")
            self.assertEqual(manifest["releaseRef"], "1.32.0")
            self.assertEqual(manifest["repository"], self.registry.PUBLIC_REPOSITORY)
            for release_ref in ("v1.32.0", "main", "1.32", "1.32.0^{commit}"):
                with self.subTest(release_ref=release_ref):
                    with self.assertRaises(self.registry.RegistryError):
                        self.registry.build_public_manifest(checkout, release_ref)

    def test_public_manifest_carries_accesscheck_tristate(self):
        # The snapshot must preserve the accessCheck tri-state distinctly: undeclared
        # (None, no metadata block), any-org ([]), and conditional (a typed list).
        # None and [] are both falsy — a truthiness collapse here is the documented
        # "falsely claims org-agnostic" bug, so this asserts them as separate values.
        with tempfile.TemporaryDirectory() as td:
            checkout = self._public_checkout_fixture(
                Path(td), "git@github.com:forcedotcom/sf-skills.git"
            )
            manifest = self.registry.build_public_manifest(checkout, "1.32.0")
            access = {row["name"]: row["accessCheck"] for row in manifest["skills"]}
            for row in manifest["skills"]:
                self.assertIn("accessCheck", row)
            self.assertIsNone(access["platform-widget-search"])
            self.assertEqual(access["platform-empty-access-search"], [])
            self.assertEqual(
                access["platform-gated-search"],
                [
                    {"type": "license", "value": "FixtureLicense"},
                    {"type": "orgPref", "value": "FixturePref"},
                ],
            )

    def test_read_access_check_reads_tristate_and_fails_loud_on_damage(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "SKILL.md"

            def parse(body: str):
                path.write_text(body, encoding="utf-8")
                return self.registry.read_access_check(path)

            # Undeclared: no metadata block, and a metadata block without the key.
            self.assertIsNone(parse('---\nname: x\ndescription: "d"\n---\nbody\n'))
            self.assertIsNone(parse('---\nname: x\ndescription: "d"\nmetadata:\n  version: "1.0"\n---\n'))
            # Any-org: explicit inline empty list.
            self.assertEqual(parse('---\nname: x\ndescription: "d"\nmetadata:\n  accessCheck: []\n---\n'), [])
            # Conditional: block-style typed entries and an inline JSON array.
            self.assertEqual(
                parse('---\nname: x\ndescription: "d"\nmetadata:\n  accessCheck:\n    - type: "license"\n      value: "Foo"\n    - type: "orgPref"\n      value: "Bar"\n---\n'),
                [{"type": "license", "value": "Foo"}, {"type": "orgPref", "value": "Bar"}],
            )
            self.assertEqual(
                parse('---\nname: x\ndescription: "d"\nmetadata:\n  accessCheck: [{"type": "userPerm", "value": "Baz"}]\n---\n'),
                [{"type": "userPerm", "value": "Baz"}],
            )
            # Fail loud, never silently "undeclared": a present-but-empty bare key
            # (must be [] for any-org), a malformed block entry, and an inline scalar.
            with self.assertRaisesRegex(self.registry.RegistryError, r"\[\] for any-org"):
                parse('---\nname: x\ndescription: "d"\nmetadata:\n  accessCheck:\n---\n')
            with self.assertRaisesRegex(self.registry.RegistryError, "malformed accessCheck"):
                parse('---\nname: x\ndescription: "d"\nmetadata:\n  accessCheck:\n    type: "license"\n---\n')
            with self.assertRaisesRegex(self.registry.RegistryError, "must be an array"):
                parse('---\nname: x\ndescription: "d"\nmetadata:\n  accessCheck: "license"\n---\n')

    def test_public_check_detects_missing_snapshot_and_drift(self):
        # check_public is the public-manifest digest-drift gate (the analog of
        # discovery_catalog.check). Missing destination → surfaced; a fresh snapshot
        # → current; any byte change → stale. All fail LOUD (RegistryError), never a
        # silent "current".
        with tempfile.TemporaryDirectory() as td:
            checkout = self._public_checkout_fixture(
                Path(td), "git@github.com:forcedotcom/sf-skills.git"
            )
            dest = Path(td) / "public-release-manifest.json"
            with self.assertRaisesRegex(self.registry.RegistryError, "missing"):
                self.registry.check_public(checkout, dest, "1.32.0")
            self.registry.snapshot_public(checkout, dest, "1.32.0")
            self.assertTrue(self.registry.check_public(checkout, dest, "1.32.0"))
            dest.write_text(dest.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            with self.assertRaisesRegex(self.registry.RegistryError, "stale"):
                self.registry.check_public(checkout, dest, "1.32.0")

    def test_checked_public_manifest_and_v3_catalog_counts_and_sets(self):
        manifest = self.registry.load_public_manifest(MANIFEST_PATH)
        self.assertEqual(manifest["repository"], "https://github.com/forcedotcom/sf-skills.git")
        self.assertEqual(manifest["commit"], "ba78d3871d54196e86dbde6bbd9f9a79944ff07f")
        self.assertEqual(manifest["releaseRef"], "1.38.0")
        self.assertEqual(manifest["counts"], {"public": 138})
        self.assertEqual(len(manifest["skills"]), 138)
        # accessCheck travels through the manifest as a tri-state (Option A). Every
        # row carries the key; at 1.38.0 a fixed set of skills declare a conditional
        # gate and the rest are undeclared (None) — never silently [], which would
        # falsely claim org-agnostic before the backfill lands.
        for row in manifest["skills"]:
            self.assertNotIn("description", row)
            self.assertIn("examplePrompt", row)
            self.assertTrue(self.registry.is_user_prompt_like(row["examplePrompt"]))
            self.assertIn("accessCheck", row)
            self.assertTrue(self.registry._valid_access_check(row["accessCheck"]))
        gated = {row["name"]: row["accessCheck"] for row in manifest["skills"] if row["accessCheck"] is not None}
        self.assertEqual(gated, {
            "dx-devops-pipeline-manage": [
                {"type": "orgPref", "value": "ALMDevopsCorePref"},
                {"type": "userPerm", "value": "UserHasDevOpsCore"},
            ],
            "dx-devops-promote": [
                {"type": "orgPref", "value": "ALMDevopsCorePref"},
                {"type": "userPerm", "value": "UserHasDevOpsCore"},
            ],
            "dx-org-devhub-configure": [
                {"type": "userPerm", "value": "ModifyAllData"},
            ],
            "experience-ui-bundle-2gp-deploy": [
                {"type": "orgPref", "value": "Package2Enabled"},
            ],
            "experience-ui-bundle-features-generate": [
                {"type": "license", "value": "Experience Cloud (Customer Community / Customer Community Plus)"},
                {"type": "orgPref", "value": "Sites"},
            ],
            "experience-ui-bundle-mfa-configure": [
                {"type": "license", "value": "Experience Cloud (Customer Community / Customer Community Login)"},
            ],
            "platform-sandbox-configure": [
                {"type": "userPerm", "value": "ManageSandboxes"},
            ],
            "service-itsm-agentic-setup-cmdb-bundle-deploy": [
                {"type": "orgPerm", "value": "ITSrvcsCnfgMgmnt"},
                {"type": "orgPref", "value": "CMDBEnabled"},
            ],
            "service-itsm-agentic-setup-cmdb-configure": [
                {"type": "orgPerm", "value": "ITSrvcsCnfgMgmnt"},
            ],
            "service-itsm-agentic-setup-cmdb-coordinate": [
                {"type": "orgPerm", "value": "ITSrvcsCnfgMgmnt"},
            ],
            "service-itsm-agentic-setup-cmdb-discovery-configure": [
                {"type": "orgPerm", "value": "ITSrvcsCnfgMgmnt"},
            ],
            "service-itsm-incident-priority-configure": [
                {"type": "userPerm", "value": "CustomizeApplication"},
                {"type": "orgPref", "value": "ITSMIncidentMgmtEnabled"},
            ],
        })
        data = self.catalog.load_catalog(PLUGIN_ROOT)
        self.assertEqual(data["schemaVersion"], "3.0")
        self.assertEqual(data["channel"], "public")
        self.assertEqual(data["counts"], {
            "public": 138,
            "foundation": 41,
            "overlap": 31,
            "publicStandaloneAddable": 107,
            "foundationOnly": 10,
            "visibleUnion": 148,
        })
        public = {row["name"] for row in manifest["skills"]}
        foundation = {entry.name for entry in (PLUGIN_ROOT / "skills").iterdir() if entry.is_dir()}
        rows = {row["name"]: row for row in data["skills"]}
        self.assertEqual(set(rows), public | foundation)
        self.assertEqual({name for name, row in rows.items() if row["publicAvailable"]}, public)
        self.assertEqual({name for name, row in rows.items() if row["foundationInstalled"]}, foundation)
        for name, row in rows.items():
            self.assertEqual(set(row["variants"]), ({"public"} if name in public else set()) | ({"foundation"} if name in foundation else set()))
            for source, variant in row["variants"].items():
                self.assertRegex(variant["skillMdSha256"], r"^[0-9a-f]{64}$")
                self.assertRegex(variant["treeSha256"], r"^[0-9a-f]{64}$")
                self.assertNotIn("description", variant)
                self.assertIn("accessCheck", variant)
                self.assertTrue(self.registry._valid_access_check(variant["accessCheck"]))
                # Foundation skills (plugin dialect, no metadata block) are always
                # structurally undeclared; only the public channel can carry a gate.
                if source == "foundation":
                    self.assertIsNone(variant["accessCheck"])
        self.assertEqual(
            rows["experience-ui-bundle-features-generate"]["variants"]["public"]["accessCheck"],
            [
                {"type": "license", "value": "Experience Cloud (Customer Community / Customer Community Plus)"},
                {"type": "orgPref", "value": "Sites"},
            ],
        )
        overlap = next(rows[name] for name in sorted(public & foundation))
        public_record = next(row for row in manifest["skills"] if row["name"] == overlap["name"])
        self.assertEqual(overlap["examplePrompt"], public_record["examplePrompt"])

    def test_public_manifest_loader_rejects_schema_count_order_and_hash_damage(self):
        baseline = self.registry.load_public_manifest(MANIFEST_PATH)
        cases = []
        damaged = json.loads(json.dumps(baseline))
        damaged["extra"] = True
        cases.append(damaged)
        damaged = json.loads(json.dumps(baseline))
        damaged["counts"]["public"] -= 1
        cases.append(damaged)
        damaged = json.loads(json.dumps(baseline))
        damaged["releaseRef"] = "main"
        cases.append(damaged)
        damaged = json.loads(json.dumps(baseline))
        damaged["skills"][0]["treeSha256"] = "bad"
        cases.append(damaged)
        damaged = json.loads(json.dumps(baseline))
        damaged["skills"][0], damaged["skills"][1] = damaged["skills"][1], damaged["skills"][0]
        cases.append(damaged)
        # accessCheck damage: a missing key (the tri-state must be explicit, never
        # omitted), a non-list scalar, and a malformed entry. [] is intentionally
        # NOT a damage case — it is the valid any-org signal.
        damaged = json.loads(json.dumps(baseline))
        del damaged["skills"][0]["accessCheck"]
        cases.append(damaged)
        damaged = json.loads(json.dumps(baseline))
        damaged["skills"][0]["accessCheck"] = "license"
        cases.append(damaged)
        damaged = json.loads(json.dumps(baseline))
        damaged["skills"][0]["accessCheck"] = [{"type": "bogus", "value": "x"}]
        cases.append(damaged)
        damaged = json.loads(json.dumps(baseline))
        damaged["skills"][0]["accessCheck"] = [{"type": "license"}]
        cases.append(damaged)
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "manifest.json"
            for data in cases:
                path.write_text(json.dumps(data), encoding="utf-8")
                with self.assertRaises(self.registry.RegistryError):
                    self.registry.load_public_manifest(path)

    def test_public_artifacts_do_not_leak_internal_only_names_or_descriptions(self):
        manifest = self.registry.load_public_manifest(MANIFEST_PATH)
        self.catalog.load_catalog(PLUGIN_ROOT)
        public = {row["name"] for row in manifest["skills"]}
        foundation = {entry.name for entry in (PLUGIN_ROOT / "skills").iterdir() if entry.is_dir()}
        authoring = {entry.name for entry in (REPO_ROOT / "skills").iterdir() if entry.is_dir()}
        internal_only = authoring - (public | foundation)
        evidence_root = REPO_ROOT / "evidence/channel-registry"
        checked_files = [MANIFEST_PATH, PLUGIN_ROOT / "catalog/discovery.json"] + [
            path for path in evidence_root.rglob("*") if path.is_file()
        ]
        blob = "\n".join(path.read_text(encoding="utf-8") for path in checked_files)
        for name in internal_only:
            self.assertNotIn(f'"{name}"', blob)
            self.assertIsNone(re.search(rf"(?<![a-z0-9-]){re.escape(name)}(?![a-z0-9-])", blob))
            description = self.registry.read_skill(REPO_ROOT / "skills" / name / "SKILL.md")["description"]
            self.assertNotIn(description, blob)
        self.assertNotIn(str(REPO_ROOT), blob)
        self.assertNotIn("internal-aggregates.json", blob)
        for forbidden in ("internalOmitted", "flatRepo", "authoringSha", "holdPolicy"):
            self.assertNotIn(forbidden, blob)

    def test_publishable_plugin_tree_has_no_public_only_or_internal_description_leakage(self):
        manifest = self.registry.load_public_manifest(MANIFEST_PATH)
        public = {row["name"] for row in manifest["skills"]}
        foundation = {entry.name for entry in (PLUGIN_ROOT / "skills").iterdir() if entry.is_dir()}
        authoring = {entry.name for entry in (REPO_ROOT / "skills").iterdir() if entry.is_dir()}
        files = [
            path for path in PLUGIN_ROOT.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
        ]
        blobs = [(path, path.read_bytes()) for path in files]
        for name in sorted((public - foundation) | (authoring - public - foundation)):
            source = REPO_ROOT / "skills" / name / "SKILL.md"
            if not source.is_file():
                continue
            description = self.registry.read_skill(source)["description"].encode("utf-8")
            leaked = [str(path.relative_to(PLUGIN_ROOT)) for path, blob in blobs if description in blob]
            self.assertEqual(leaked, [], f"{name} description leaked into publishable plugin tree")

    def test_standalone_records_tolerates_missing_standalone_dirs(self):
        # A user (or CI's clean checkout) without ~/.claude/skills / .agents/skills
        # must not crash the internal overlay. iterdir() is a lazy generator whose
        # os.listdir runs on first iteration, so a missing dir has to be guarded
        # before iterating — regression for the Python-3.12 FileNotFoundError that
        # escaped the try/except and only surfaced on CI's clean tree.
        with tempfile.TemporaryDirectory() as td:
            cwd, home = Path(td) / "cwd", Path(td) / "home"
            cwd.mkdir()
            home.mkdir()  # both exist, but neither has .claude/skills or .agents/skills
            result = self.catalog._standalone_records(cwd, home, {"platform-widget-search": {}})
        self.assertEqual(result, {"platform-widget-search": {"records": [], "observations": []}})

    def test_internal_overlay_scans_standalone_roots_and_reports_variant_provenance(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo, plugin = root / "repo", root / "plugin"
            authoring = repo / "skills/platform-widget-search"
            public_source = root / "public/platform-widget-search"
            for skill_dir, description, body in (
                (authoring, "Use this authoring fixture to search platform widgets safely in internal preview.", "authoring"),
                (public_source, "Use this public fixture to search platform widgets safely in internal preview.", "public"),
            ):
                skill_dir.mkdir(parents=True)
                skill_dir.joinpath("SKILL.md").write_text(
                    f'---\nname: platform-widget-search\ndescription: "{description}"\n---\n{body}\n',
                    encoding="utf-8",
                )
            repo.joinpath("config.yml").write_text("internal: []\n", encoding="utf-8")
            plugin.joinpath("skills").mkdir(parents=True)
            manifest_path = plugin / self.registry.PUBLIC_MANIFEST_RELATIVE
            manifest_path.parent.mkdir(parents=True)
            public_variant = self.registry.source_variant(public_source)
            manifest = {
                "schemaVersion": self.registry.PUBLIC_MANIFEST_SCHEMA,
                "channel": "public-release",
                "repository": self.registry.PUBLIC_REPOSITORY,
                "commit": "a" * 40,
                "releaseRef": "1.32.0",
                "counts": {"public": 1},
                "skills": [{
                    "name": "platform-widget-search",
                    "domain": "platform",
                    "examplePrompt": "Search for platform widgets safely.",
                    "skillMdSha256": public_variant["skillMdSha256"],
                    "treeSha256": public_variant["treeSha256"],
                    "accessCheck": None,
                }],
            }
            manifest_path.write_text(self.registry.serialize(manifest), encoding="utf-8")
            cwd, home = root / "project", root / "home"
            project_install = cwd / ".claude/skills/platform-widget-search"
            project_install.parent.mkdir(parents=True)
            shutil.copytree(authoring, project_install)

            overlay = self.catalog.build_internal_overlay(repo, plugin, cwd=cwd, home=home)
            row = overlay["skills"][0]
            self.assertEqual(row["installedProvenance"]["state"], "authoring-exact")

            user_install = home / ".claude/skills/platform-widget-search"
            user_install.parent.mkdir(parents=True)
            shutil.copytree(public_source, user_install)
            overlay = self.catalog.build_internal_overlay(repo, plugin, cwd=cwd, home=home)
            self.assertEqual(overlay["skills"][0]["installedProvenance"]["state"], "conflict")

            shutil.rmtree(project_install)
            overlay = self.catalog.build_internal_overlay(repo, plugin, cwd=cwd, home=home)
            self.assertEqual(overlay["skills"][0]["installedProvenance"]["state"], "public-exact")
            user_install.joinpath("changed.txt").write_text("changed", encoding="utf-8")
            overlay = self.catalog.build_internal_overlay(repo, plugin, cwd=cwd, home=home)
            self.assertEqual(overlay["skills"][0]["installedProvenance"]["state"], "modified")
            shutil.rmtree(user_install)
            overlay = self.catalog.build_internal_overlay(repo, plugin, cwd=cwd, home=home)
            self.assertEqual(overlay["skills"][0]["installedProvenance"]["state"], "unknown")

    def test_internal_preview_requires_both_gate_and_internal_checkout(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for env in ({}, {"SF_SKILLS_INTERNAL_PREVIEW": "1"}):
                out, err = io.StringIO(), io.StringIO()
                with mock.patch.dict(os.environ, env, clear=True), redirect_stdout(out), redirect_stderr(err):
                    code = self.catalog.run_discovery(
                        ["internal-preview", "overview", "--json"],
                        plugin_root=root / "plugin", cwd=root, home=root / "home",
                    )
                self.assertNotEqual(code, 0)
                self.assertEqual(out.getvalue(), "")
                self.assertNotIn("held", err.getvalue().lower())

    def test_internal_preview_axes_banner_and_nonexecuting_install_plan(self):
        held = self.catalog.read_internal_holds(REPO_ROOT / "config.yml")
        public = {row["name"] for row in self.registry.load_public_manifest(MANIFEST_PATH)["skills"]}
        foundation = {entry.name for entry in (PLUGIN_ROOT / "skills").iterdir() if entry.is_dir()}
        authoring = {entry.name for entry in (REPO_ROOT / "skills").iterdir() if entry.is_dir()}
        candidates = sorted((authoring & held) - public - foundation)
        if not candidates:
            self.skipTest("no locally-present internal[] skill to test against")
        candidate = candidates[0]
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.dict(os.environ, {"SF_SKILLS_INTERNAL_PREVIEW": "1"}, clear=False), redirect_stdout(out), redirect_stderr(err):
            code = self.catalog.run_discovery(
                ["internal-preview", "skill", candidate, "--json"],
                plugin_root=PLUGIN_ROOT, cwd=REPO_ROOT, home=REPO_ROOT / ".test-home",
            )
        self.assertEqual((code, err.getvalue()), (0, ""))
        detail = json.loads(out.getvalue())
        self.assertEqual(detail["notice"], NOTICE)
        self.assertEqual(detail["presence"], {"authoring": True, "foundation": False, "public": False})
        self.assertIn(detail["holdPolicy"], {"held", "not-held"})
        self.assertEqual(detail["publicMatch"], "not-public")
        self.assertEqual(detail["evalEvidence"], "unverified")
        self.assertEqual(detail["promotion"], "not-requested")
        self.assertEqual(detail["installer"], "internal-preview-installable")
        self.assertIn("authoring", detail["contentHashes"])

        out = io.StringIO()
        with mock.patch.dict(os.environ, {"SF_SKILLS_INTERNAL_PREVIEW": "1"}, clear=False), redirect_stdout(out):
            code = self.catalog.run_discovery(
                ["internal-preview", "install-plan", candidate, "--json"],
                plugin_root=PLUGIN_ROOT, cwd=REPO_ROOT, home=REPO_ROOT / ".test-home",
            )
        plan = json.loads(out.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(plan["notice"], NOTICE)
        self.assertFalse(plan["execute"])
        self.assertEqual(plan["classification"], "internal-preview-installable")
        self.assertEqual(plan["plan"]["command"], "npx")
        self.assertEqual(plan["plan"]["args"][0], "skills@1.5.20")
        self.assertEqual(plan["plan"]["source"], str(REPO_ROOT / "skills"))
        self.assertIn("--copy", plan["plan"]["args"])
        self.assertIn("--yes", plan["plan"]["args"])
        self.assertEqual(plan["plan"]["scope"], "project")
        overlay = self.catalog.build_internal_overlay(
            REPO_ROOT, PLUGIN_ROOT, cwd=REPO_ROOT, home=REPO_ROOT / ".test-home"
        )
        frozen = [row for row in overlay["skills"] if row["holdPolicy"] == "held" and row["presence"]["public"]]
        self.assertTrue(frozen)
        self.assertTrue(all(row["label"] == "public-frozen" for row in frozen))
        frozen_different = [row for row in frozen if row["publicMatch"] == "different" and not row["presence"]["foundation"]]
        self.assertTrue(frozen_different)
        self.assertTrue(all(row["installer"] == "internal-preview-installable" for row in frozen_different))
        ordinary_unheld = [
            row for row in overlay["skills"]
            if row["holdPolicy"] == "not-held" and row["presence"]["authoring"]
            and not row["presence"]["foundation"] and row["publicMatch"] in {"different", "not-public"}
        ]
        self.assertTrue(ordinary_unheld)
        self.assertTrue(all(row["installer"] != "internal-preview-installable" for row in ordinary_unheld))
        self.assertTrue(held)


if __name__ == "__main__":
    unittest.main(verbosity=2)
