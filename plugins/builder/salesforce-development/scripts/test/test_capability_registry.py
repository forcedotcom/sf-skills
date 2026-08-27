#!/usr/bin/env python3
"""Channel registry, canonical hashing, and public-release manifest contracts."""
from __future__ import annotations

import json
import os
import re
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _test_support import load_module

SCRIPTS = Path(__file__).resolve().parent.parent
PLUGIN_ROOT = SCRIPTS.parent
REPO_ROOT = PLUGIN_ROOT.parents[2]
REGISTRY_PATH = SCRIPTS / "capability_registry.py"
MANIFEST_PATH = PLUGIN_ROOT / "catalog/public-release-manifest.json"


class CapabilityRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = load_module(REGISTRY_PATH, "capability_registry_under_test")

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
        # check_public is the public-manifest digest-drift gate. Missing destination
        # → surfaced; a fresh snapshot → current; any byte change → stale. All fail
        # LOUD (RegistryError), never a silent "current".
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

    def test_checked_public_manifest_counts_and_access_check_tri_state(self):
        manifest = self.registry.load_public_manifest(MANIFEST_PATH)
        self.assertEqual(manifest["repository"], "https://github.com/forcedotcom/sf-skills.git")
        self.assertEqual(manifest["commit"], "32bf7846b96d4fcb1b2f5c7c06c09a1d9b3cea03")
        self.assertEqual(manifest["releaseRef"], "1.41.0")
        self.assertEqual(manifest["counts"], {"public": 157})
        self.assertEqual(len(manifest["skills"]), 157)
        # accessCheck travels through the manifest as a tri-state (Option A). Every
        # row carries the key; at 1.41.0 a fixed set of skills declare a conditional
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
            "platform-datamask-run": [
                {"type": "userPerm", "value": "PermissionsManageDataMaskPolicies"},
                {"type": "userPerm", "value": "PermissionsAccessDataMaskAndSeed"},
            ],
            "platform-sandbox-configure": [
                {"type": "userPerm", "value": "ManageSandboxes"},
            ],
            "service-catalog-template-deploy": [
                {"type": "accessCheck", "value": "IndustriesEpc.orgHasUnifiedCatalog"},
            ],
            "service-catalog-template-search": [
                {"type": "accessCheck", "value": "IndustriesEpc.orgHasUnifiedCatalog"},
            ],
            "service-concierge-portal-generate": [
                {"type": "license", "value": "Agentforce"},
            ],
            "service-itsm-agentic-setup-agentforce-coordinate": [
                {"type": "license", "value": "Agentforce"},
            ],
            "service-itsm-agentic-setup-agentforce-studio-configure": [
                {"type": "license", "value": "Agentforce"},
            ],
            "service-itsm-agentic-setup-agentforce-studio-validate": [
                {"type": "license", "value": "Agentforce"},
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
            "service-itsm-agentic-setup-employee-agent-configure": [
                {"type": "license", "value": "Agentforce"},
            ],
            "service-itsm-agentic-setup-fulfiller-agent-configure": [
                {"type": "license", "value": "Agentforce"},
            ],
            "service-itsm-agentic-setup-incident-sla-configure": [],
            "service-itsm-agentic-setup-itsm-agentforce-permset-assign": [
                {"type": "license", "value": "Agentforce"},
            ],
            "service-itsm-agentic-setup-uel-user-create": [
                {"type": "userPerm", "value": "ManageUsers"},
                {"type": "userPerm", "value": "ManageProfilesPermissionsets"},
                {"type": "userPerm", "value": "CustomizeApplication"},
                {"type": "userPerm", "value": "AssignPermissionSets"},
            ],
            "service-itsm-incident-mgmt-configure": [
                {"type": "userPerm", "value": "CustomizeApplication"},
                {"type": "orgPerm", "value": "IncidentMgmt.orgHasITSMOrgPermission"},
            ],
            "service-itsm-incident-priority-configure": [
                {"type": "userPerm", "value": "CustomizeApplication"},
            ],
            "service-itsm-swarming-configure": [
                {"type": "orgPref", "value": "ITSMTeamsEnabled"},
            ],
            "service-itsm-teams-configure": [
                {"type": "orgPerm", "value": "MSTeamsSetupAutomationAccess"},
            ],
            "service-itsm-teams-coordinate": [],
            "service-itsm-teams-debug": [
                {"type": "orgPref", "value": "ITSMTeamsEnabled"},
            ],
            "service-itsm-teams-employee-agent-configure": [
                {"type": "orgPref", "value": "ITSMTeamsEnabled"},
            ],
            "service-itsm-teams-itdesk-configure": [
                {"type": "orgPref", "value": "ITSMTeamsEnabled"},
            ],
            "service-itsm-teams-itservice-configure": [
                {"type": "orgPref", "value": "ITSMTeamsEnabled"},
            ],
        })

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
        public = {row["name"] for row in manifest["skills"]}
        foundation = {entry.name for entry in (PLUGIN_ROOT / "skills").iterdir() if entry.is_dir()}
        authoring = {entry.name for entry in (REPO_ROOT / "skills").iterdir() if entry.is_dir()}
        internal_only = authoring - (public | foundation)
        evidence_root = REPO_ROOT / "evidence/channel-registry"
        checked_files = [MANIFEST_PATH] + [
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
