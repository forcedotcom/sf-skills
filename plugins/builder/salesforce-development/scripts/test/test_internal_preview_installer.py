#!/usr/bin/env python3
"""Offline tests for the guarded internal-preview project installer."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _test_support import load_module

SCRIPTS = Path(__file__).resolve().parent.parent
PLUGIN_ROOT = SCRIPTS.parent
REPO_ROOT = PLUGIN_ROOT.parents[2]
MODULE_PATH = SCRIPTS / "internal_preview_installer.py"
CATALOG_PATH = SCRIPTS / "discovery_catalog.py"


installer = load_module(MODULE_PATH, "internal_preview_installer_under_test")
catalog = load_module(CATALOG_PATH, "internal_preview_catalog_under_test")


class InternalPreviewInstallerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        manifest = installer.registry.load_public_manifest(
            PLUGIN_ROOT / "catalog/public-release-manifest.json"
        )
        cls.public = {row["name"]: row for row in manifest["skills"]}
        cls.authoring = installer.registry.skill_directories(REPO_ROOT / "skills")
        cls.foundation = installer.registry.skill_directories(PLUGIN_ROOT / "skills")
        cls.held = catalog.read_internal_holds(REPO_ROOT / "config.yml")
        if cls.held - set(cls.authoring):
            raise unittest.SkipTest("internal[] hold list references skills absent from local checkout")
        eligible_iter = (
            name for name, path in cls.authoring.items()
            if name in cls.held and name not in cls.foundation and (
                name not in cls.public
                or installer.registry.canonical_tree_sha256(path, safety_root=REPO_ROOT)
                != cls.public[name]["treeSha256"]
            )
        )
        cls.eligible = next(eligible_iter, None)
        if cls.eligible is None:
            raise unittest.SkipTest("no locally-present internal[] skill to test against")
        cls.unheld_candidate = next(
            name for name, path in cls.authoring.items()
            if name not in cls.held and name not in cls.foundation and (
                name not in cls.public
                or installer.registry.canonical_tree_sha256(path, safety_root=REPO_ROOT)
                != cls.public[name]["treeSha256"]
            )
        )
        cls.public_frozen_different = next(
            name for name, path in cls.authoring.items()
            if name in cls.held and name not in cls.foundation and name in cls.public
            and installer.registry.canonical_tree_sha256(path, safety_root=REPO_ROOT)
            != cls.public[name]["treeSha256"]
        )
        cls.public_exact = next(
            name for name, path in cls.authoring.items()
            if name not in cls.foundation and name not in cls.held and name in cls.public
            and installer.registry.canonical_tree_sha256(path, safety_root=REPO_ROOT)
            == cls.public[name]["treeSha256"]
        )
        cls.foundation_name = next(name for name in cls.authoring if name in cls.foundation)

    def project(self, root: Path) -> Path:
        project = root / "project"
        project.mkdir()
        (project / "sfdx-project.json").write_text("{}\n", encoding="utf-8")
        return project

    def successful_runner(self, project: Path, *, mutate=None, symlink=False, outside=False):
        calls = []

        def run(argv, **kwargs):
            calls.append((argv, kwargs))
            source = Path(argv[4]) / self.eligible
            target = project / ".claude/skills" / self.eligible
            target.parent.mkdir(parents=True, exist_ok=True)
            if outside:
                external = project.parent / "outside"
                shutil.copytree(source, external)
                target.symlink_to(external, target_is_directory=True)
            elif symlink:
                target.symlink_to(source, target_is_directory=True)
            else:
                shutil.copytree(source, target)
                if mutate:
                    mutate(target)
            return subprocess.CompletedProcess(argv, 0, stdout=b"installed", stderr=b"")

        return run, calls

    def install(self, project: Path, **kwargs):
        env = kwargs.pop("env", {"SF_SKILLS_INTERNAL_PREVIEW": "1"})
        name = kwargs.pop("name", self.eligible)
        return installer.install_internal_preview(
            name,
            repo_root=REPO_ROOT,
            plugin_root=PLUGIN_ROOT,
            cwd=project,
            env=env,
            **kwargs,
        )

    def test_success_uses_one_exact_argv_without_shell_and_reports_authoring_provenance(self):
        with tempfile.TemporaryDirectory() as td:
            project = self.project(Path(td))
            runner, calls = self.successful_runner(project)
            code, result = self.install(project, runner=runner, timeout_seconds=17)
        self.assertEqual(code, 0)
        self.assertEqual(result["notice"], "INTERNAL PREVIEW — not publicly supported")
        self.assertEqual(result["name"], self.eligible)
        self.assertEqual(result["status"], "installed")
        self.assertEqual(result["provenance"], "authoring-exact")
        self.assertEqual(result["sourceChannel"], "internal-preview")
        self.assertIs(result["freshSessionRequired"], True)
        self.assertIs(result["skillsLockPresent"], False)
        self.assertNotIn("installInstruction", result)
        self.assertNotIn(str(REPO_ROOT), json.dumps(result))
        self.assertEqual(calls[0][0], [
            "npx", "--yes", "skills@1.5.20", "add", str(REPO_ROOT / "skills"),
            "--skill", self.eligible, "--agent", "claude-code", "--copy", "--yes",
        ])
        self.assertEqual(calls[0][1]["cwd"], project.resolve())
        self.assertEqual(calls[0][1]["timeout"], 17)
        self.assertIs(calls[0][1]["shell"], False)
        self.assertIs(calls[0][1]["capture_output"], True)
        self.assertIs(calls[0][1]["check"], False)
        self.assertNotIn("SF_SKILLS_INTERNAL_PREVIEW", calls[0][1]["env"])

    def test_subprocess_environment_is_an_explicit_minimal_allowlist(self):
        with tempfile.TemporaryDirectory() as td:
            project = self.project(Path(td))
            runner, calls = self.successful_runner(project)
            supplied = {
                "SF_SKILLS_INTERNAL_PREVIEW": "1", "PATH": "/safe/bin", "HOME": "/safe/home",
                "LANG": "en_US.UTF-8", "LC_ALL": "C", "TMPDIR": "/safe/tmp",
                "npm_config_registry": "https://registry.npmjs.org/",
                "NPM_CONFIG_CAFILE": "/safe/ca.pem", "SECRET_TOKEN": "must-not-pass",
                "AWS_SECRET_ACCESS_KEY": "must-not-pass", "HTTP_PROXY": "http://secret@proxy",
                "NODE_OPTIONS": "--require malicious.js", "UNRELATED": "must-not-pass",
            }
            code, _ = self.install(project, runner=runner, env=supplied)
        self.assertEqual(code, 0)
        child_env = calls[0][1]["env"]
        self.assertEqual(child_env, {
            "PATH": "/safe/bin", "HOME": "/safe/home", "LANG": "en_US.UTF-8",
            "LC_ALL": "C", "TMPDIR": "/safe/tmp",
            "npm_config_registry": "https://registry.npmjs.org/",
            "NPM_CONFIG_CAFILE": "/safe/ca.pem",
        })

    def test_exact_real_project_copy_is_a_safe_noop_and_records_lock_presence(self):
        with tempfile.TemporaryDirectory() as td:
            project = self.project(Path(td))
            target = project / ".claude/skills" / self.eligible
            target.parent.mkdir(parents=True)
            shutil.copytree(REPO_ROOT / "skills" / self.eligible, target)
            (project / "skills-lock.json").write_text("{}\n", encoding="utf-8")
            runner = mock.Mock()
            code, result = self.install(project, runner=runner)
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "already-installed")
        self.assertEqual(result["provenance"], "authoring-exact")
        self.assertIs(result["skillsLockPresent"], True)
        runner.assert_not_called()

    def test_all_authorization_and_project_gates_fail_before_execution(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project = self.project(root)
            runner = mock.Mock()
            cases = [
                ("bad env", self.eligible, project, {}),
                ("bad env value", self.eligible, project, {"SF_SKILLS_INTERNAL_PREVIEW": "true"}),
                ("bad name", "Not-Kebab", project, {"SF_SKILLS_INTERNAL_PREVIEW": "1"}),
                ("unknown", "platform-not-a-real-skill", project, {"SF_SKILLS_INTERNAL_PREVIEW": "1"}),
                ("foundation", self.foundation_name, project, {"SF_SKILLS_INTERNAL_PREVIEW": "1"}),
                ("ordinary public exact", self.public_exact, project, {"SF_SKILLS_INTERNAL_PREVIEW": "1"}),
                ("ordinary unheld candidate", self.unheld_candidate, project, {"SF_SKILLS_INTERNAL_PREVIEW": "1"}),
            ]
            no_project = root / "not-project"
            no_project.mkdir()
            cases.append(("not project", self.eligible, no_project, {"SF_SKILLS_INTERNAL_PREVIEW": "1"}))
            for label, name, cwd, env in cases:
                with self.subTest(label=label):
                    code, result = installer.install_internal_preview(
                        name, repo_root=REPO_ROOT, plugin_root=PLUGIN_ROOT,
                        cwd=cwd, env=env, runner=runner,
                    )
                    self.assertNotEqual(code, 0)
                    self.assertEqual(result["status"], "error")
                    self.assertNotIn("installed", result.get("message", "").lower())
            runner.assert_not_called()

    def test_held_public_frozen_different_variant_is_authorized(self):
        with tempfile.TemporaryDirectory() as td:
            project = self.project(Path(td))
            calls = []

            def runner(argv, **kwargs):
                calls.append(argv)
                target = project / ".claude/skills" / self.public_frozen_different
                target.parent.mkdir(parents=True)
                shutil.copytree(REPO_ROOT / "skills" / self.public_frozen_different, target)
                return subprocess.CompletedProcess(argv, 0, stdout=b"ok", stderr=b"")

            code, result = self.install(
                project, name=self.public_frozen_different, runner=runner
            )
        self.assertEqual(code, 0)
        self.assertEqual(result["provenance"], "authoring-exact")
        self.assertEqual(len(calls), 1)

    def test_existing_nonexact_destination_is_denied_before_subprocess(self):
        cases = ("modified", "malformed", "file", "symlink", "dangling-symlink", "unknown")
        for label in cases:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                project = self.project(root)
                target = project / ".claude/skills" / self.eligible
                target.parent.mkdir(parents=True)
                if label in {"modified", "malformed"}:
                    shutil.copytree(REPO_ROOT / "skills" / self.eligible, target)
                    if label == "modified":
                        (target / "changed.txt").write_text("changed\n", encoding="utf-8")
                    else:
                        (target / "SKILL.md").write_text("malformed\n", encoding="utf-8")
                elif label == "file":
                    target.write_text("not a directory\n", encoding="utf-8")
                elif label == "symlink":
                    target.symlink_to(REPO_ROOT / "skills" / self.eligible, target_is_directory=True)
                elif label == "dangling-symlink":
                    target.symlink_to(root / "missing", target_is_directory=True)
                else:
                    target.mkdir()
                    (target / "SKILL.md").write_text(
                        '---\nname: platform-unknown-search\ndescription: "Use this unknown fixture for safe test coverage only."\n---\n',
                        encoding="utf-8",
                    )
                runner = mock.Mock()
                code, result = self.install(project, runner=runner)
                self.assertNotEqual(code, 0)
                self.assertEqual(result["status"], "error")
                runner.assert_not_called()

    def test_existing_parent_symlink_or_nondirectory_is_denied_before_subprocess(self):
        for label in ("claude-symlink", "skills-symlink", "claude-file", "skills-file"):
            with self.subTest(label=label), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                project = self.project(root)
                outside = root / "outside"
                outside.mkdir()
                if label == "claude-symlink":
                    (project / ".claude").symlink_to(outside, target_is_directory=True)
                else:
                    (project / ".claude").mkdir()
                    if label == "skills-symlink":
                        (project / ".claude/skills").symlink_to(outside, target_is_directory=True)
                    elif label == "claude-file":
                        (project / ".claude").rmdir()
                        (project / ".claude").write_text("not a directory\n", encoding="utf-8")
                    else:
                        (project / ".claude/skills").write_text("not a directory\n", encoding="utf-8")
                runner = mock.Mock()
                code, result = self.install(project, runner=runner)
                self.assertNotEqual(code, 0)
                self.assertEqual(result["status"], "error")
                runner.assert_not_called()
                self.assertEqual(list(outside.iterdir()), [])

    def test_invalid_checkout_is_denied_without_leaking_its_path(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project = self.project(root)
            fake_repo = root / "private-checkout"
            fake_repo.mkdir()
            code, result = installer.install_internal_preview(
                self.eligible, repo_root=fake_repo, plugin_root=PLUGIN_ROOT,
                cwd=project, env={"SF_SKILLS_INTERNAL_PREVIEW": "1"}, runner=mock.Mock(),
            )
        self.assertNotEqual(code, 0)
        self.assertEqual(result["status"], "error")
        self.assertNotIn(str(fake_repo), json.dumps(result))

    def test_timeout_nonzero_and_malformed_streams_return_metadata_without_text(self):
        def timeout_runner(argv, **kwargs):
            raise subprocess.TimeoutExpired(argv, kwargs["timeout"], output=b"at /tmp/private/source", stderr=b"token=secretvalue123")

        class Odd:
            def __str__(self):
                raise RuntimeError("cannot stringify")

        runners = [
            timeout_runner,
            lambda argv, **kwargs: subprocess.CompletedProcess(argv, 9, stdout=b"/Users/person/private", stderr=b"failed"),
            lambda argv, **kwargs: subprocess.CompletedProcess(argv, 0, stdout=Odd(), stderr=Odd()),
        ]
        for index, runner in enumerate(runners):
            with self.subTest(index=index), tempfile.TemporaryDirectory() as td:
                project = self.project(Path(td))
                code, result = self.install(project, runner=runner)
                blob = json.dumps(result)
                self.assertNotEqual(code, 0)
                self.assertEqual(result["status"], "error")
                self.assertNotIn("/tmp/private", blob)
                self.assertNotIn("/Users/person", blob)
                self.assertNotIn("secretvalue123", blob)
                if "execution" in result:
                    execution = result["execution"]
                    self.assertEqual(
                        set(execution),
                        {"exitCode", "timedOut", "stdoutBytes", "stdoutTruncated", "stderrBytes", "stderrTruncated"},
                    )
                    self.assertNotIn("text", blob)
                self.assertLess(len(blob), 2000)

    def test_postconditions_reject_missing_symlink_escape_bad_frontmatter_and_hash_mismatch(self):
        def missing(argv, **kwargs):
            return subprocess.CompletedProcess(argv, 0, stdout=b"ok", stderr=b"")

        def malformed(target: Path):
            (target / "SKILL.md").write_text("malformed\n", encoding="utf-8")

        def changed(target: Path):
            (target / "unexpected.txt").write_text("changed\n", encoding="utf-8")

        cases = [
            ("missing", lambda project: missing),
            ("symlink", lambda project: self.successful_runner(project, symlink=True)[0]),
            ("escape", lambda project: self.successful_runner(project, outside=True)[0]),
            ("frontmatter", lambda project: self.successful_runner(project, mutate=malformed)[0]),
            ("hash", lambda project: self.successful_runner(project, mutate=changed)[0]),
        ]
        for label, make_runner in cases:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as td:
                project = self.project(Path(td))
                code, result = self.install(project, runner=make_runner(project))
                self.assertNotEqual(code, 0)
                self.assertEqual(result["status"], "error")
                self.assertNotEqual(result.get("provenance"), "authoring-exact")

    def test_skill_and_command_docs_authorize_only_the_reviewed_gated_subcommand(self):
        skill = (PLUGIN_ROOT / "skills/platform-capability-search/SKILL.md").read_text(encoding="utf-8")
        command = (PLUGIN_ROOT / "commands/discovery.md").read_text(encoding="utf-8")
        for text in (skill, command):
            self.assertIn("internal-preview install <name>", text)
            self.assertIn("SF_SKILLS_INTERNAL_PREVIEW", text)
            self.assertIn("never set", text.lower())
            self.assertIn("freshSessionRequired", text)
            self.assertIn("public add flow", text.lower())
        self.assertIn("The helper alone launches the fixed argv", command)
        self.assertIn("Never install while browsing", skill)

    def test_catalog_command_executes_only_explicit_install_and_public_discovery_stays_blind(self):
        internal_only = self.held - set(self.public) - set(self.foundation)
        self.assertTrue(internal_only)
        candidate = sorted(internal_only)[0]
        with tempfile.TemporaryDirectory() as td:
            project = self.project(Path(td))
            out = __import__("io").StringIO()
            err = __import__("io").StringIO()
            with mock.patch.dict(os.environ, {"SF_SKILLS_INTERNAL_PREVIEW": "1"}), \
                    mock.patch.object(catalog, "_run_internal_install", return_value=(0, {
                        "notice": catalog.INTERNAL_NOTICE, "name": candidate,
                        "status": "installed", "provenance": "authoring-exact",
                        "sourceChannel": "internal-preview", "freshSessionRequired": True,
                        "skillsLockPresent": False,
                    })) as execute, \
                    __import__("contextlib").redirect_stdout(out), \
                    __import__("contextlib").redirect_stderr(err):
                code = catalog.run_discovery(
                    ["internal-preview", "install", candidate, "--json"],
                    plugin_root=PLUGIN_ROOT, cwd=project, home=Path(td) / "home",
                )
            self.assertEqual((code, err.getvalue()), (0, ""))
            execute.assert_called_once()
            self.assertNotIn("installInstruction", out.getvalue())
            public_out = __import__("io").StringIO()
            public_err = __import__("io").StringIO()
            with __import__("contextlib").redirect_stdout(public_out), __import__("contextlib").redirect_stderr(public_err):
                public_code = catalog.run_discovery(
                    ["skill", candidate, "--json"], plugin_root=PLUGIN_ROOT,
                    cwd=project, home=Path(td) / "home",
                )
            self.assertNotEqual(public_code, 0)
            self.assertEqual(public_out.getvalue(), "")
            self.assertNotIn(candidate, public_err.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
