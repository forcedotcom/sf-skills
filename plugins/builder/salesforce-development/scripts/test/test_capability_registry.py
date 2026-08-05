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

    def test_checked_public_manifest_and_v2_catalog_counts_and_sets(self):
        manifest = self.registry.load_public_manifest(MANIFEST_PATH)
        self.assertEqual(manifest["repository"], "https://github.com/forcedotcom/sf-skills.git")
        self.assertEqual(manifest["commit"], "7baeb07b36799eada4dce06d85664c0c16a269a8")
        self.assertEqual(manifest["releaseRef"], "1.32.0")
        self.assertEqual(manifest["counts"], {"public": 102})
        self.assertEqual(len(manifest["skills"]), 102)
        data = self.catalog.load_catalog(PLUGIN_ROOT)
        self.assertEqual(data["schemaVersion"], "2.0")
        self.assertEqual(data["channel"], "public")
        self.assertEqual(data["counts"], {
            "public": 102,
            "foundation": 40,
            "overlap": 29,
            "publicStandaloneAddable": 73,
            "foundationOnly": 11,
            "visibleUnion": 113,
        })
        public = {row["name"] for row in manifest["skills"]}
        foundation = {entry.name for entry in (PLUGIN_ROOT / "skills").iterdir() if entry.is_dir()}
        rows = {row["name"]: row for row in data["skills"]}
        self.assertEqual(set(rows), public | foundation)
        self.assertEqual({name for name, row in rows.items() if row["publicAvailable"]}, public)
        self.assertEqual({name for name, row in rows.items() if row["foundationInstalled"]}, foundation)
        for name, row in rows.items():
            self.assertEqual(set(row["variants"]), ({"public"} if name in public else set()) | ({"foundation"} if name in foundation else set()))
            for variant in row["variants"].values():
                self.assertRegex(variant["skillMdSha256"], r"^[0-9a-f]{64}$")
                self.assertRegex(variant["treeSha256"], r"^[0-9a-f]{64}$")
        overlap = next(rows[name] for name in sorted(public & foundation))
        public_record = next(row for row in manifest["skills"] if row["name"] == overlap["name"])
        self.assertEqual(overlap["variants"]["public"]["description"], public_record["description"])

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
                    "description": self.registry.read_skill(public_source / "SKILL.md")["description"],
                    "skillMdSha256": public_variant["skillMdSha256"],
                    "treeSha256": public_variant["treeSha256"],
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
        candidate = sorted((authoring & held) - public - foundation)[0]
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
