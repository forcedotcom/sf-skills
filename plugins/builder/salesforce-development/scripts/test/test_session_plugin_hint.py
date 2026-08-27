#!/usr/bin/env python3
"""Focused offline tests for `_detect_signals` in session_plugin_hint.py.

Covers the denylist-pruned single-walk replacement for the previous
`Path.glob("**/...")`-per-pattern scan (see PR #1521 review comment): a
signal match inside a denylisted directory must not count, and an absent
signal must not require walking into one.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from _test_support import load_module

SCRIPTS = Path(__file__).resolve().parent.parent
MODULE_PATH = SCRIPTS / "session_plugin_hint.py"

hint = load_module(MODULE_PATH, "session_plugin_hint_under_test")


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()


class DetectSignalsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def labels(self):
        return {label for label, _ in hint._detect_signals(self.project)}

    def test_no_signals_in_an_empty_project(self):
        self.assertEqual(hint._detect_signals(self.project), [])

    def test_lwc_signal_matches_js_under_lwc_dir(self):
        _touch(self.project / "force-app/main/default/lwc/foo/foo.js")
        self.assertIn("Lightning Web Components in this project", self.labels())

    def test_lwc_signal_matches_any_js_meta_xml_regardless_of_directory(self):
        proj = Path(tempfile.mkdtemp())
        _touch(proj / "force-app/main/default/classes/Foo.js-meta.xml")
        self.assertIn(
            "Lightning Web Components in this project",
            {label for label, _ in hint._detect_signals(proj)},
        )

    def test_react_signal_matches_any_tsx_file_not_only_curated_subpaths(self):
        # The original globs special-cased uiBundles/appLayout.tsx/routes.tsx as
        # subsets of **/*.tsx; a bare .tsx anywhere must still match.
        _touch(self.project / "src/whatever/Widget.tsx")
        self.assertIn("a React UI bundle in this project", self.labels())

    def test_agentforce_signal_matches_agent_file_at_any_depth(self):
        _touch(self.project / "onboarding.agent")
        self.assertIn("Agentforce agent files in this project", self.labels())

    def test_cms_signal_matches_any_of_the_three_curated_directories(self):
        for dirname in ("managedContentTypes", "contentassets", "stockimages"):
            with self.subTest(dirname=dirname):
                proj = Path(tempfile.mkdtemp())
                _touch(proj / "force-app" / dirname / "asset.txt")
                self.assertIn(
                    "Salesforce CMS content or media in this project",
                    {label for label, _ in hint._detect_signals(proj)},
                )

    def test_denylisted_directories_are_pruned_from_the_walk(self):
        # A signal file that only exists inside a denylisted directory must not
        # be treated as a project signal -- it's vendored/build output, not the
        # user's own project, and walking it defeats the point of pruning.
        for dirname in hint._DENYLIST_DIRS:
            with self.subTest(dirname=dirname):
                proj = Path(tempfile.mkdtemp())
                _touch(proj / dirname / "nested" / "Widget.tsx")
                self.assertEqual(hint._detect_signals(proj), [])

    def test_signal_outside_denylist_is_still_found_alongside_denylisted_noise(self):
        _touch(self.project / "node_modules/some-pkg/Component.tsx")
        _touch(self.project / "src/Widget.tsx")
        self.assertIn("a React UI bundle in this project", self.labels())

    def test_multiple_signals_are_all_detected_in_original_signal_order(self):
        _touch(self.project / "force-app/main/default/lwc/foo/foo.js")
        _touch(self.project / "src/Widget.tsx")
        _touch(self.project / "onboarding.agent")
        _touch(self.project / "force-app/managedContentTypes/asset.txt")
        got = hint._detect_signals(self.project)
        self.assertEqual([label for label, _ in got], [label for label, _, _ in hint._SIGNALS])


if __name__ == "__main__":
    unittest.main(verbosity=2)
