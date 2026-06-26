"""Tests for ``summarize_tree`` — declared-action-tree → markdown summary.

Covers:
- ``render_tree``  recursive box-drawing renderer
- ``main``         CLI orchestration via argv (tree_json + out_md + built_at)
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from . import _bootstrap  # noqa: F401  — sys.path setup

import summarize_tree  # type: ignore


# -----------------------------------------------------------------------------
# render_tree — pure dict → list[str]
# -----------------------------------------------------------------------------


class RenderTreeTests(unittest.TestCase):

    def test_single_leaf_uses_last_connector(self):
        # is_last=True (default) → "└── "; no children → no recursion.
        out = summarize_tree.render_tree({"kind": "TOPIC", "api_name": "T1"})
        self.assertEqual(out, ["└── [TOPIC] T1"])

    def test_first_of_two_siblings_uses_branch_connector(self):
        # render at top-level isn't the natural use, but the function
        # accepts is_last=False → "├── ".
        out = summarize_tree.render_tree(
            {"kind": "TOPIC", "api_name": "T1"}, is_last=False
        )
        self.assertEqual(out, ["├── [TOPIC] T1"])

    def test_bot_definition_with_version_includes_version_in_label(self):
        agent = {"version": "v3"}
        out = summarize_tree.render_tree(
            {"kind": "BOT_DEFINITION", "api_name": "MyAgent"},
            agent_=agent,
        )
        self.assertEqual(out, ["└── [BOT_DEFINITION] MyAgent (v3)"])

    def test_bot_definition_without_version_omits_version_suffix(self):
        out = summarize_tree.render_tree(
            {"kind": "BOT_DEFINITION", "api_name": "MyAgent"},
            agent_={},
        )
        self.assertEqual(out, ["└── [BOT_DEFINITION] MyAgent"])

    def test_gen_ai_function_includes_unwraps_arrow(self):
        out = summarize_tree.render_tree({
            "kind": "GEN_AI_FUNCTION",
            "api_name": "GAF1",
            "unwraps_to": {"kind": "FLOW", "api_name": "FlowA"},
        })
        self.assertEqual(out, ["└── [GEN_AI_FUNCTION] GAF1 → FLOW:FlowA"])

    def test_gen_ai_function_without_unwraps_omits_arrow(self):
        out = summarize_tree.render_tree({
            "kind": "GEN_AI_FUNCTION",
            "api_name": "GAF1",
        })
        self.assertEqual(out, ["└── [GEN_AI_FUNCTION] GAF1"])

    def test_standard_action_uses_invocation_type_when_present(self):
        out = summarize_tree.render_tree({
            "kind": "STANDARD_ACTION",
            "api_name": "SA1",
            "invocation_type": "standardinvocableaction",
        })
        self.assertEqual(
            out, ["└── [STANDARD_ACTION] SA1 (standardinvocableaction)"]
        )

    def test_standard_action_falls_back_to_legacy_invocation_keys(self):
        # raw_invocation_type wins when invocation_type missing.
        with self.subTest("raw_invocation_type"):
            out = summarize_tree.render_tree({
                "kind": "STANDARD_ACTION",
                "api_name": "SA1",
                "raw_invocation_type": "legacyA",
            })
            self.assertIn("legacyA", out[0])
        with self.subTest("raw_action_type"):
            out = summarize_tree.render_tree({
                "kind": "UNKNOWN",
                "api_name": "U1",
                "raw_action_type": "legacyB",
            })
            self.assertIn("legacyB", out[0])

    def test_element_name_appended_for_non_bot_kinds(self):
        out = summarize_tree.render_tree({
            "kind": "FLOW",
            "api_name": "FlowA",
            "element_name": "callX",
        })
        self.assertEqual(out, ["└── [FLOW] FlowA  — element:callX"])

    def test_element_name_skipped_on_bot_definition(self):
        out = summarize_tree.render_tree({
            "kind": "BOT_DEFINITION",
            "api_name": "MyAgent",
            "element_name": "should-not-appear",
        }, agent_={"version": "v1"})
        self.assertNotIn("should-not-appear", out[0])

    def test_nested_children_recurse_with_correct_prefix(self):
        out = summarize_tree.render_tree({
            "kind": "TOPIC",
            "api_name": "T1",
            "children": [
                {"kind": "STANDARD_ACTION", "api_name": "A1"},
                {"kind": "STANDARD_ACTION", "api_name": "A2"},
            ],
        })
        # Top-level (is_last=True) gets " " continuation prefix.
        self.assertEqual(out, [
            "└── [TOPIC] T1",
            "    ├── [STANDARD_ACTION] A1",
            "    └── [STANDARD_ACTION] A2",
        ])

    def test_branch_node_uses_pipe_continuation_for_children(self):
        # is_last=False at parent → "│ " continuation prefix.
        out = summarize_tree.render_tree({
            "kind": "TOPIC",
            "api_name": "T1",
            "children": [{"kind": "APEX", "api_name": "A1"}],
        }, is_last=False)
        self.assertEqual(out, [
            "├── [TOPIC] T1",
            "│   └── [APEX] A1",
        ])


# -----------------------------------------------------------------------------
# main — argv-based CLI
# -----------------------------------------------------------------------------


def _minimal_tree() -> dict:
    return {
        "agent": {
            "api_name": "MyAgent", "version": "v1", "bot_id": "0Xx000000000",
            "master_label": "My Agent", "generation": "nga",
            "planner_name": "MyPlanner", "planner_type": "Atlas__Reasoning",
            "_version_auto_picked": False,
        },
        "node_count": 2,
        "depth": 1,
        "_kind_counts": {"TOPIC": 1, "STANDARD_ACTION": 1},
        "_partial": False,
        "root": {
            "kind": "BOT_DEFINITION", "api_name": "MyAgent",
            "children": [{"kind": "TOPIC", "api_name": "Greetings"}],
        },
    }


class MainTests(unittest.TestCase):

    def test_main_returns_one_when_argv_count_wrong(self):
        with mock.patch.object(summarize_tree, "sys") as fake_sys:
            fake_sys.argv = ["summarize_tree.py"]  # missing args
            fake_sys.stderr.write = lambda *_a, **_kw: None
            rc = summarize_tree.main()
        self.assertEqual(rc, 1)

    def test_main_returns_one_when_tree_json_unreadable(self):
        with TemporaryDirectory() as t:
            tmp = Path(t)
            with mock.patch.object(summarize_tree, "sys") as fake_sys:
                fake_sys.argv = [
                    "summarize_tree.py",
                    str(tmp / "missing.json"),
                    str(tmp / "out.md"),
                    "2026-05-09T00:00:00Z",
                ]
                fake_sys.stderr.write = lambda *_a, **_kw: None
                rc = summarize_tree.main()
            self.assertEqual(rc, 1)

    def test_main_writes_summary_md_with_expected_sections(self):
        with TemporaryDirectory() as t:
            tmp = Path(t)
            tree_path = tmp / "tree.json"
            tree_path.write_text(json.dumps(_minimal_tree()))
            out_path = tmp / "out.summary.md"

            with mock.patch.object(summarize_tree, "sys") as fake_sys:
                fake_sys.argv = [
                    "summarize_tree.py",
                    str(tree_path), str(out_path),
                    "2026-05-09T00:00:00Z",
                ]
                fake_sys.stderr.write = lambda *_a, **_kw: None
                rc = summarize_tree.main()

            self.assertEqual(rc, 0)
            content = out_path.read_text()
            self.assertIn("# MyAgent v1 — declared action tree", content)
            self.assertIn("## Kind counts", content)
            self.assertIn("## Declared action tree", content)
            # tree section is wrapped in ``` fence
            self.assertIn("```\n└── [BOT_DEFINITION] MyAgent (v1)", content)
            # 2026-05-09 timestamp surfaced
            self.assertIn("2026-05-09T00:00:00Z", content)

    def test_main_appends_unresolved_section_when_present(self):
        with TemporaryDirectory() as t:
            tmp = Path(t)
            tree = _minimal_tree()
            tree["_unresolved"] = [
                {"kind": "FLOW", "api_name": "Missing", "reason": "404"},
            ]
            tree_path = tmp / "tree.json"
            tree_path.write_text(json.dumps(tree))
            out_path = tmp / "out.summary.md"

            with mock.patch.object(summarize_tree, "sys") as fake_sys:
                fake_sys.argv = [
                    "summarize_tree.py",
                    str(tree_path), str(out_path),
                    "2026-05-09T00:00:00Z",
                ]
                fake_sys.stderr.write = lambda *_a, **_kw: None
                summarize_tree.main()

            content = out_path.read_text()
            self.assertIn("## Unresolved", content)
            self.assertIn("`FLOW`/`Missing` — 404", content)


if __name__ == "__main__":
    unittest.main()
