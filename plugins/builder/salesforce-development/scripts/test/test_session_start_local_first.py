#!/usr/bin/env python3
"""Behavior proofs for bounded, subprocess-free SessionStart discovery."""
from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from _test_support import load_module, strip_ansi

SCRIPTS = Path(__file__).resolve().parent.parent
sfx = load_module(SCRIPTS / "sf_context.py", "session_start_local_first_context")


class SessionStartLocalFirstTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.project = self.root / "project"
        self.home = self.root / "home"
        self.project.mkdir()
        self.home.mkdir()
        self.old_cwd = Path.cwd()
        os.chdir(self.project)
        self.home_patch = mock.patch.dict(os.environ, {"HOME": str(self.home)}, clear=False)
        self.home_patch.start()

    def tearDown(self):
        self.home_patch.stop()
        os.chdir(self.old_cwd)
        self.tmp.cleanup()

    def make_project(self):
        (self.project / "sfdx-project.json").write_text(json.dumps({
            "name": "local-first",
            "sourceApiVersion": "64.0",
            "packageDirectories": [{"path": "force-app"}],
        }), encoding="utf-8")

    def configure_target(self, alias="local-dev"):
        config = self.project / ".sf" / "config.json"
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text(json.dumps({"target-org": alias}), encoding="utf-8")

    def add_auth_fact(self):
        auth = self.home / ".sfdx" / "user@example.invalid.json"
        auth.parent.mkdir(parents=True, exist_ok=True)
        auth.write_text(json.dumps({"accessToken": "not-used-by-startup"}), encoding="utf-8")

    def detect(self, source="startup"):
        output = io.StringIO()
        payload = io.StringIO(json.dumps({"source": source, "session_id": "local-first"}))
        with mock.patch.object(sfx.sys, "stdin", payload), redirect_stdout(output):
            self.assertEqual(sfx.cmd_detect(), 0)
        return json.loads(output.getvalue())

    def test_startup_variants_make_zero_external_calls(self):
        cases = ("connected", "configured", "no-target", "non-project", "compact")
        for case in cases:
            with self.subTest(case=case):
                for child in tuple(self.project.iterdir()):
                    if child.is_dir():
                        import shutil
                        shutil.rmtree(child)
                    else:
                        child.unlink()
                self.make_project()
                source = "startup"
                if case in ("connected", "configured"):
                    self.configure_target()
                if case == "connected":
                    self.add_auth_fact()
                if case == "non-project":
                    (self.project / "sfdx-project.json").unlink()
                if case == "compact":
                    source = "compact"

                forbidden = AssertionError("external work on SessionStart")
                with mock.patch.object(sfx.subprocess, "run", side_effect=forbidden) as external, \
                        mock.patch.object(sfx.subprocess, "Popen", side_effect=forbidden) as popen, \
                        mock.patch.object(sfx.os, "system", side_effect=forbidden) as os_system, \
                        mock.patch.object(sfx.urllib.request, "urlopen", side_effect=forbidden) as network, \
                        mock.patch.object(sfx, "fetch_org_info_via_node", side_effect=forbidden) as node_helper, \
                        mock.patch.object(sfx, "get_target_org", side_effect=forbidden) as cli_target, \
                        mock.patch.object(sfx, "get_org_list", side_effect=forbidden) as org_list, \
                        mock.patch.object(sfx, "get_org_display", side_effect=forbidden) as org_display:
                    result = self.detect(source)
                for forbidden_call in (
                    external, popen, os_system, network, node_helper, cli_target,
                    org_list, org_display
                ):
                    self.assertEqual(forbidden_call.call_count, 0)
                if case == "non-project":
                    self.assertNotIn("systemMessage", result)
                elif case == "compact":
                    self.assertNotIn("systemMessage", result)
                else:
                    self.assertIn("systemMessage", result)

    def test_configured_target_is_named_but_never_passively_claimed_reachable(self):
        self.make_project()
        self.configure_target("local-dev")
        result = self.detect()
        visible = strip_ansi(result["systemMessage"])
        context = result["hookSpecificOutput"]["additionalContext"]
        self.assertIn("local-dev", visible)
        self.assertIn("configured", visible.lower())
        self.assertIn("unprobed", visible.lower())
        self.assertNotRegex(visible.lower(), r"\breachable\b|\bunreachable\b")
        state = sfx._derive_journey_state(
            self.project, has_project=True, target="local-dev",
            target_error="unprobed", org_display=None)
        org_cell = sfx._journey_org_cell(state["context"])
        self.assertEqual(org_cell, "org: local-dev (unprobed)")
        self.assertIn("state=configured-unprobed", context)

    def test_no_target_keeps_local_project_inventory_and_login_guidance(self):
        self.make_project()
        source = self.project / "force-app" / "main" / "default" / "classes"
        source.mkdir(parents=True)
        (source / "Widget.cls").write_text("public class Widget {}", encoding="utf-8")
        result = self.detect()
        visible = strip_ansi(result["systemMessage"])
        self.assertIn("org: none set", visible)   # lean no-org line, not a titled band
        self.assertIn("local-first", visible)
        self.assertIn("Apex 1 src / 0 test", visible)
        self.assertIn("/salesforce-development:login", visible)

    def test_explicit_status_still_invokes_live_resolver(self):
        self.make_project()
        org = {"alias": "local-dev", "edition": "Developer", "apiVersion": "64.0"}
        with mock.patch.object(sfx, "resolve_executable", return_value="/usr/bin/sf"), \
                mock.patch.object(sfx, "get_target_org_detailed", return_value=("local-dev", "")) as target, \
                mock.patch.object(sfx, "resolve_org_info", return_value=org) as resolver, \
                mock.patch.object(sfx, "git_status_line", return_value=""), redirect_stdout(io.StringIO()):
            self.assertEqual(sfx.cmd_status(), 0)
        target.assert_called_once_with()
        resolver.assert_called_once_with("local-dev")


class ProjectStatsSingleWalkTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.old_cwd = Path.cwd()
        os.chdir(self.root)
        self.write_descriptor([{"path": "force-app"}])

    def tearDown(self):
        os.chdir(self.old_cwd)
        self.tmp.cleanup()

    def write_descriptor(self, package_directories):
        (self.root / "sfdx-project.json").write_text(json.dumps({
            "name": "inventory-test",
            "sourceApiVersion": "64.0",
            "packageDirectories": package_directories,
        }), encoding="utf-8")

    def write_metadata(self, relative, contents="fixture"):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents, encoding="utf-8")

    def test_ordinary_project_counts_match_existing_inventory_contract_in_one_walk(self):
        paths = (
            "force-app/main/default/classes/Widget.cls",
            "force-app/main/default/classes/WidgetTest.cls",
            "force-app/main/default/triggers/Widget.trigger",
            "force-app/main/default/lwc/widget/widget.js-meta.xml",
            "force-app/main/default/aura/card/card.cmp-meta.xml",
            "force-app/main/default/objects/Widget__c/Widget__c.object-meta.xml",
            "force-app/main/default/permissionsets/Widget.permissionset-meta.xml",
            "force-app/main/default/flows/Widget.flow-meta.xml",
        )
        for relative in paths:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("fixture", encoding="utf-8")
        real_walk = os.walk
        real_descriptor_read = sfx._read_project_descriptor
        with mock.patch.object(sfx.os, "walk", wraps=real_walk) as walk, \
                mock.patch.object(
                    sfx, "_read_project_descriptor", wraps=real_descriptor_read
                ) as descriptor_read:
            stats = sfx.project_stats()
        self.assertEqual(walk.call_count, 1)
        self.assertEqual(descriptor_read.call_count, 1)
        self.assertEqual(stats, {
            "apex_src": 1, "apex_test": 1, "triggers": 1, "lwc": 1,
            "aura": 1, "objects": 1, "permsets": 1, "flows": 1,
        })

    def test_metadata_outside_declared_package_directories_is_ignored(self):
        self.write_metadata("force-app/main/default/classes/Inside.cls")
        self.write_metadata("scripts/Outside.cls")
        self.write_metadata("other/main/default/flows/Outside.flow-meta.xml")

        stats = sfx.project_stats()

        self.assertEqual(stats["apex_src"], 1)
        self.assertEqual(stats["flows"], 0)

    def test_multiple_nested_and_duplicate_package_roots_count_each_file_once(self):
        self.write_descriptor([
            {"path": "packages/alpha/nested"},
            {"path": "packages/beta"},
            {"path": "packages/alpha"},
            {"path": "packages/alpha"},
        ])
        self.write_metadata("packages/alpha/main/default/classes/Alpha.cls")
        self.write_metadata("packages/alpha/nested/main/default/classes/Nested.cls")
        self.write_metadata("packages/beta/main/default/classes/Beta.cls")
        self.write_metadata("packages/gamma/main/default/classes/Outside.cls")

        real_walk = os.walk
        with mock.patch.object(sfx.os, "walk", wraps=real_walk) as walk:
            stats = sfx.project_stats()

        self.assertEqual(walk.call_count, 1)
        self.assertEqual(stats["apex_src"], 3)

    def test_declared_package_beneath_excluded_directory_is_counted(self):
        self.write_descriptor([{"path": "vendor/pkg"}])
        self.write_metadata("vendor/pkg/main/default/classes/Declared.cls")
        self.write_metadata("vendor/undeclared/main/default/classes/Outside.cls")

        stats = sfx.project_stats()

        self.assertEqual(stats["apex_src"], 1)

    def test_nested_declared_root_survives_parent_root_and_excluded_ancestor(self):
        self.write_descriptor([{"path": "."}, {"path": "vendor/pkg"}])
        self.write_metadata("force-app/main/default/classes/Parent.cls")
        self.write_metadata("vendor/pkg/main/default/classes/Nested.cls")
        self.write_metadata("vendor/undeclared/main/default/classes/Outside.cls")

        stats = sfx.project_stats()

        self.assertEqual(stats["apex_src"], 2)

    def test_many_roots_prune_undeclared_siblings_with_bounded_traversal(self):
        roots = [f"packages/pkg-{index:03d}" for index in range(50)]
        self.write_descriptor([{"path": path} for path in roots])
        for relative in roots:
            (self.root / relative).mkdir(parents=True)
        for index in range(200):
            sibling = self.root / "packages" / f"sibling-{index:03d}"
            (sibling / "deep" / "tree").mkdir(parents=True)
            (sibling / "deep" / "tree" / "Ignored.cls").write_text(
                "fixture", encoding="utf-8"
            )

        real_scandir = os.scandir
        scanned = []

        def counted_scandir(path):
            scanned.append(Path(path).resolve())
            return real_scandir(path)

        with mock.patch.object(sfx.os, "scandir", side_effect=counted_scandir):
            stats = sfx.project_stats()

        self.assertEqual(stats["apex_src"], 0)
        self.assertLessEqual(len(scanned), 52)  # root + packages + 50 accepted roots
        self.assertFalse(any("sibling-" in path.name for path in scanned), scanned)

    def test_absolute_escaping_non_string_and_missing_package_paths_are_rejected(self):
        absolute = self.root / "absolute-package"
        self.write_descriptor([
            {"path": str(absolute)},
            {"path": "../escaping-package"},
            {"path": 42},
            {},
            "force-app",
            None,
            {"path": "force-app"},
        ])
        self.write_metadata("absolute-package/main/default/classes/Absolute.cls")
        self.write_metadata("force-app/main/default/classes/Inside.cls")

        stats = sfx.project_stats()

        self.assertEqual(stats["apex_src"], 1)

    def test_escaping_package_path_is_rejected_directly(self):
        roots = sfx._validated_package_roots(self.root.resolve(), {
            "packageDirectories": [{"path": "../escaping-package"}],
        })

        self.assertEqual(roots, [])

    def test_missing_package_path_is_rejected_directly(self):
        roots = sfx._validated_package_roots(self.root.resolve(), {
            "packageDirectories": [{"path": "missing-package"}],
        })

        self.assertEqual(roots, [])

    def test_regular_file_package_path_is_rejected_directly(self):
        package_file = self.root / "not-a-package-directory"
        package_file.write_text("fixture", encoding="utf-8")
        roots = sfx._validated_package_roots(self.root.resolve(), {
            "packageDirectories": [{"path": package_file.name}],
        })

        self.assertEqual(roots, [])

    @unittest.skipIf(os.name == "nt", "symlink creation is not reliably available on Windows")
    def test_symlink_package_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as outside:
            outside_package = Path(outside) / "pkg"
            outside_package.mkdir()
            (self.root / "linked-outside").symlink_to(outside_package, target_is_directory=True)

            roots = sfx._validated_package_roots(self.root.resolve(), {
                "packageDirectories": [{"path": "linked-outside"}],
            })

        self.assertEqual(roots, [])

    def test_undeclared_tree_cannot_consume_shared_file_or_entry_caps(self):
        self.write_metadata("a-undeclared/one.txt")
        self.write_metadata("a-undeclared/two.txt")
        for index in range(20):
            (self.root / "a-undeclared" / f"dir-{index}").mkdir()
        self.write_metadata("force-app/main/default/classes/Inside.cls")

        with mock.patch.object(sfx, "_PROJECT_STATS_FILE_CAP", 2), \
                mock.patch.object(sfx, "_PROJECT_STATS_ENTRY_CAP", 5):
            stats = sfx.project_stats()

        self.assertEqual(stats["apex_src"], 1)

    def test_file_cap_is_shared_across_declared_package_roots(self):
        self.write_descriptor([{"path": "alpha"}, {"path": "beta"}])
        self.write_metadata("alpha/One.cls")
        self.write_metadata("alpha/Two.trigger")
        self.write_metadata("beta/Three.cls")

        with mock.patch.object(sfx, "_PROJECT_STATS_FILE_CAP", 2):
            stats = sfx.project_stats()

        self.assertEqual(stats["apex_src"], 1)
        self.assertEqual(stats["triggers"], 1)

    def test_entry_cap_is_shared_across_declared_package_roots(self):
        self.write_descriptor([{"path": "alpha"}, {"path": "beta"}])
        self.write_metadata("alpha/One.cls")
        self.write_metadata("beta/Three.cls")
        self.write_metadata("beta/Two.trigger")

        with mock.patch.object(sfx, "_PROJECT_STATS_ENTRY_CAP", 4):
            stats = sfx.project_stats()

        self.assertEqual(stats["apex_src"], 1)
        self.assertEqual(stats["triggers"], 0)

    def test_depth_cap_applies_to_each_declared_package_root(self):
        self.write_descriptor([{"path": "alpha"}, {"path": "beta"}])
        self.write_metadata("alpha/Shallow.cls")
        self.write_metadata("beta/nested/TooDeep.cls")

        with mock.patch.object(sfx, "_PROJECT_STATS_DEPTH_CAP", 1):
            stats = sfx.project_stats()

        self.assertEqual(stats["apex_src"], 1)

    def test_project_meta_ignores_malformed_package_entries(self):
        self.write_descriptor([
            None, "force-app", 42, {}, {"path": None}, {"path": ["bad"]},
            {"path": ""}, {"path": "force-app"}, {"path": "other"},
        ])
        self.assertEqual(sfx.project_meta()["package_dirs"], "force-app, other")

        for malformed in (None, "force-app", 42, {"path": "force-app"}):
            with self.subTest(package_directories=malformed):
                self.write_descriptor(malformed)
                self.assertEqual(sfx.project_meta()["package_dirs"], "force-app")

    def test_excluded_fifty_thousand_file_tree_is_pruned_before_descent(self):
        (self.root / "force-app").mkdir()

        def synthetic_walk(_root, topdown=True, onerror=None, followlinks=False):
            dirs = ["force-app", "vendor", "node_modules", ".git", ".sf", ".sfdx"]
            yield str(self.root), dirs, []
            self.assertEqual(dirs, ["force-app"])
            yield str(self.root / "force-app"), [], ["Widget.cls"]
            # If an excluded directory survives pruning it represents a 50k-file tree.
            if "vendor" in dirs:
                yield str(self.root / "vendor"), [], [f"junk-{i}.cls" for i in range(50_000)]

        with mock.patch.object(sfx.os, "walk", side_effect=synthetic_walk):
            stats = sfx.project_stats()
        self.assertEqual(stats["apex_src"], 1)

    def test_empty_directory_entries_are_bounded_and_cap_order_is_deterministic(self):
        self.write_descriptor([{"path": "."}])
        yielded = 0

        def empty_tree(_root, topdown=True, onerror=None, followlinks=False):
            nonlocal yielded
            dirs = [f"d-{index:04d}" for index in range(100)]
            yielded += 1
            yield str(self.root), dirs, []
            yielded += 1
            yield str(self.root / "d-0000"), [], []

        with mock.patch.object(sfx, "_PROJECT_STATS_ENTRY_CAP", 10, create=True), \
                mock.patch.object(sfx.os, "walk", side_effect=empty_tree):
            sfx.project_stats()
        self.assertEqual(yielded, 1)

        def ordered(files):
            def walk(_root, topdown=True, onerror=None, followlinks=False):
                yield str(self.root), [], list(files)
            with mock.patch.object(sfx, "_PROJECT_STATS_FILE_CAP", 2), \
                    mock.patch.object(sfx.os, "walk", side_effect=walk):
                return sfx.project_stats()

        files = ["z-junk", "Widget.cls", "a-junk"]
        self.assertEqual(ordered(files), ordered(reversed(files)))

    def test_cap_and_walk_error_return_bounded_partial_counts(self):
        self.write_descriptor([{"path": "."}])

        def capped_walk(_root, topdown=True, onerror=None, followlinks=False):
            yield str(self.root), [], ["One.cls", "Two.trigger", "a", "b", "c"]

        with mock.patch.object(sfx, "_PROJECT_STATS_FILE_CAP", 3), \
                mock.patch.object(sfx.os, "walk", side_effect=capped_walk):
            stats = sfx.project_stats()
        self.assertEqual(stats["apex_src"], 1)
        self.assertEqual(stats["triggers"], 1)

        def failing_walk(_root, topdown=True, onerror=None, followlinks=False):
            yield str(self.root), [], ["One.cls"]
            raise OSError("synthetic read failure")

        with mock.patch.object(sfx.os, "walk", side_effect=failing_walk):
            partial = sfx.project_stats()
        self.assertEqual(partial["apex_src"], 1)


if __name__ == "__main__":
    unittest.main()
