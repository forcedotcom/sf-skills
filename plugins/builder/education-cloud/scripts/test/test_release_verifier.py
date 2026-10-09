"""Negative release packaging checks; do not trust an unsafe or drifted mirror."""
import importlib.util
import os
import shutil
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
PLUGIN = Path(__file__).resolve().parents[2]
ROOT = PLUGIN.parents[2]
spec = importlib.util.spec_from_file_location("education_release", PLUGIN / "scripts/verify-public-plugin-release.py")
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)

class AuthoringRepositoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (ROOT / "config.yml").is_file():
            raise unittest.SkipTest("release integration tests require the trusted authoring repository sanitizer")

class ReleaseVerifierTests(AuthoringRepositoryTests):
    def test_roster_matches_marketplace_sources(self):
        entry = next(e for e in json.loads((ROOT / ".claude-plugin/marketplace.json").read_text())["plugins"]
                     if e["name"] == "education-cloud")
        roster = json.loads((PLUGIN / "scripts/skill-roster.json").read_text())
        self.assertEqual(sorted(entry["metadata"]["sources"]["skills"]), sorted(roster))

    def test_public_tests_skip_authoring_only_checks_without_internal_dependencies(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "plugins/builder/education-cloud"
            shutil.copytree(PLUGIN, target)
            marketplace = Path(td) / ".claude-plugin/marketplace.json"
            marketplace.parent.mkdir()
            marketplace.write_text('{"plugins":[{"name":"education-cloud","metadata":{}}]}')
            for name in ("test_release_verifier.py", "test_education_discovery.py"):
                result = subprocess.run([sys.executable, str(target / "scripts/test" / name)],
                                        text=True, capture_output=True, env={**os.environ,
                                        "PYTHONDONTWRITEBYTECODE": "1"})
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertIn("skipped", result.stderr)

    def test_current_tree_passes(self):
        self.assertGreater(verifier.verify(PLUGIN, ROOT / "skills")["files"], 0)

    def assert_rejected(self, mutate, message):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "education-cloud"
            shutil.copytree(PLUGIN, target)
            mutate(target)
            with self.assertRaisesRegex(verifier.ReleaseGateError, message):
                verifier.verify(target, ROOT / "skills")

    def test_symlink_rejected(self):
        self.assert_rejected(lambda p: (p / "link").symlink_to("/etc/passwd"), "link or special")

    def test_transient_tree_rejected(self):
        self.assert_rejected(lambda p: (p / ".sf").mkdir(), "transient")

    def test_manifest_identity_rejected(self):
        self.assert_rejected(lambda p: (p / ".claude-plugin/plugin.json").write_text('{"name":"wrong"}'), "does not match")

    def test_missing_skill_rejected(self):
        self.assert_rejected(lambda p: shutil.rmtree(p / "skills/education-cloud-domain-configure"), "roster")

    def test_supporting_reference_drift_rejected(self):
        self.assert_rejected(lambda p: (p / "skills/education-cloud-multi-campus-configure/references/mcp-invocation.md").write_text("drift"), "content parity")

    def test_supporting_file_mode_drift_rejected(self):
        self.assert_rejected(lambda p: (p / "skills/education-cloud-domain-configure/SKILL.md").chmod(0o600), "mode parity")

    def test_extra_asset_rejected(self):
        self.assert_rejected(lambda p: (p / "skills/education-cloud-domain-configure/unapproved.txt").write_text("extra"), "path parity")

class PublicTreeTests(AuthoringRepositoryTests):
    def copy_public(self, base, sanitize=False):
        target = Path(base) / "plugins/builder/education-cloud"
        shutil.copytree(PLUGIN, target)
        for sidecar in target.rglob("sor.yaml"):
            sidecar.unlink()
        if sanitize:
            subprocess.run(
                ["node", str(ROOT / "scripts/release-ci/sanitize-public-skills.mjs"),
                 *[str(f) for f in target.rglob("SKILL.md")]],
                check=True, capture_output=True)
        return target

    def test_first_publish_after_sidecar_removal_passes_cli(self):
        with tempfile.TemporaryDirectory() as td:
            target = self.copy_public(td)
            public_root = Path(td) / "skills"
            self.assertEqual(0, verifier.main([
                "--plugin-root", str(target), "--authoring-root", str(ROOT / "skills"),
                "--public-root", str(public_root)]))

    def test_already_sanitized_public_copy_passes(self):
        with tempfile.TemporaryDirectory() as td:
            target = self.copy_public(td, sanitize=True)
            for skill in target.glob("skills/*/SKILL.md"):
                self.assertNotIn("distribution:", skill.read_text(encoding="utf-8"))
            self.assertGreater(verifier.verify(target, ROOT / "skills", Path(td) / "skills")["files"], 0)

    def test_mixed_first_publish_and_previously_sanitized_skills_pass(self):
        with tempfile.TemporaryDirectory() as td:
            target = self.copy_public(td)
            skill = next(target.glob("skills/*/SKILL.md"))
            subprocess.run(["node", str(ROOT / "scripts/release-ci/sanitize-public-skills.mjs"),
                            str(skill)], check=True, capture_output=True)
            verifier.verify(target, ROOT / "skills", Path(td) / "skills")

    def test_public_root_must_identify_the_copied_plugin_destination(self):
        with tempfile.TemporaryDirectory() as td:
            target = self.copy_public(td)
            with self.assertRaisesRegex(verifier.ReleaseGateError, "public plugin destination"):
                verifier.verify(target, ROOT / "skills", Path(td) / "different/skills")

    def test_source_mode_still_requires_sidecars(self):
        with tempfile.TemporaryDirectory() as td:
            target = self.copy_public(td)
            with self.assertRaisesRegex(verifier.ReleaseGateError, "path parity"):
                verifier.verify(target, ROOT / "skills")

    def test_source_pre_copy_check_stays_strict_with_public_root(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td)
            sanitizer = source / "scripts/release-ci/sanitize-public-skills.mjs"
            sanitizer.parent.mkdir(parents=True)
            shutil.copy2(ROOT / "scripts/release-ci/sanitize-public-skills.mjs", sanitizer)
            canonical = source / "skills"
            shutil.copytree(PLUGIN / "skills", canonical)
            target = source / "plugins/builder/education-cloud"
            shutil.copytree(PLUGIN, target)
            verifier.verify(target, canonical, source / "public/skills")
            next(target.rglob("sor.yaml")).unlink()
            with self.assertRaisesRegex(verifier.ReleaseGateError, "path parity"):
                verifier.verify(target, canonical, source / "public/skills")

    def test_unquoted_public_visibility_and_withheld_source(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td)
            canonical = source / "skills"
            shutil.copytree(PLUGIN / "skills", canonical)
            sanitizer = source / "scripts/release-ci/sanitize-public-skills.mjs"
            sanitizer.parent.mkdir(parents=True)
            shutil.copy2(ROOT / "scripts/release-ci/sanitize-public-skills.mjs", sanitizer)
            target = source / "plugins/builder/education-cloud"
            shutil.copytree(PLUGIN, target)
            name = "education-cloud-domain-configure"
            original = canonical / name / "SKILL.md"
            mirror = target / "skills" / name / "SKILL.md"
            unquoted = original.read_text(encoding="utf-8").replace('visibility: "public"', 'visibility: public')
            original.write_text(unquoted, encoding="utf-8")
            mirror.write_text(unquoted, encoding="utf-8")
            verifier.verify(target, canonical)
            withheld = unquoted.replace("visibility: public", "visibility: pre-release")
            original.write_text(withheld, encoding="utf-8")
            mirror.write_text(withheld, encoding="utf-8")
            with self.assertRaisesRegex(verifier.ReleaseGateError, "trusted public skill sanitization"):
                verifier.verify(target, canonical)

    def test_public_mode_rejects_sidecar_leaks(self):
        with tempfile.TemporaryDirectory() as td:
            target = self.copy_public(td)
            (target / "skills/education-cloud-domain-configure/sor.yaml").write_text("leak", encoding="utf-8")
            with self.assertRaisesRegex(verifier.ReleaseGateError, "internal sor.yaml"):
                verifier.verify(target, ROOT / "skills", Path(td) / "skills")

    def test_public_mode_rejects_changes_beyond_sanitization(self):
        for relative in ["skills/education-cloud-domain-configure/SKILL.md",
                         "skills/education-cloud-multi-campus-configure/references/mcp-invocation.md"]:
            with self.subTest(path=relative), tempfile.TemporaryDirectory() as td:
                target = self.copy_public(td, sanitize=True)
                file = target / relative
                file.write_text(file.read_text(encoding="utf-8") + "\nUnreviewed change\n", encoding="utf-8")
                with self.assertRaisesRegex(verifier.ReleaseGateError, "content parity"):
                    verifier.verify(target, ROOT / "skills", Path(td) / "skills")

    def test_invalid_rosters_fail_closed(self):
        for roster in [[], {}, ["education-cloud-domain-configure"] * 2, [None],
                       ["../escape"], ["education-cloud-"]]:
            with self.subTest(roster=roster), tempfile.TemporaryDirectory() as td:
                target = self.copy_public(td)
                (target / "scripts/skill-roster.json").write_text(json.dumps(roster), encoding="utf-8")
                with self.assertRaisesRegex(verifier.ReleaseGateError, "nonempty roster"):
                    verifier.verify(target, ROOT / "skills")

    def test_roster_is_source_and_disk_membership_is_exact(self):
        with tempfile.TemporaryDirectory() as td:
            target = self.copy_public(td)
            roster = ["education-cloud-domain-configure"]
            (target / "scripts/skill-roster.json").write_text(json.dumps(roster), encoding="utf-8")
            with self.assertRaisesRegex(verifier.ReleaseGateError, "roster mismatch"):
                verifier.verify(target, ROOT / "skills", Path(td) / "skills")
            for skill in (target / "skills").iterdir():
                if skill.name not in roster:
                    shutil.rmtree(skill)
            verifier.verify(target, ROOT / "skills", Path(td) / "skills")
            (target / "skills/unexpected.txt").write_text("extra", encoding="utf-8")
            with self.assertRaisesRegex(verifier.ReleaseGateError, "roster mismatch"):
                verifier.verify(target, ROOT / "skills", Path(td) / "skills")

if __name__ == "__main__":
    unittest.main()
