"""Tests for ``parse_wave`` standalone helpers — non-classifier surface.

Covers:
- ``compute_stats``        node count + depth + per-kind counter
- ``finalize_cap``         drains pending → unresolved + sets partial
- ``atomic_write_json``    tmp + os.replace
- ``init_tree``            bundle + bot_def shape
- ``harvest_waves``        Flow XML walking with subflows + actionCalls
"""
from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from . import _bootstrap  # noqa: F401  — sys.path setup

import parse_wave  # type: ignore


_FLOW_NS = "http://soap.sforce.com/2006/04/metadata"


# -----------------------------------------------------------------------------
# compute_stats
# -----------------------------------------------------------------------------


class ComputeStatsTests(unittest.TestCase):

    def test_empty_root_returns_zero_counts(self):
        n, d, counts = parse_wave.compute_stats({})
        self.assertEqual(n, 0)
        self.assertEqual(d, 0)
        self.assertEqual(counts, {})

    def test_single_node_counts_kind(self):
        n, d, counts = parse_wave.compute_stats({"kind": "BOT_DEFINITION"})
        self.assertEqual(n, 1)
        self.assertEqual(counts["BOT_DEFINITION"], 1)
        self.assertEqual(d, 0)

    def test_nested_tree_returns_max_depth(self):
        root = {
            "kind": "BOT_DEFINITION",
            "children": [
                {"kind": "TOPIC", "children": [
                    {"kind": "FLOW", "children": [
                        {"kind": "APEX"},
                    ]},
                ]},
                {"kind": "STANDARD_ACTION"},
            ],
        }
        n, d, counts = parse_wave.compute_stats(root)
        self.assertEqual(n, 5)
        self.assertEqual(d, 3)
        self.assertEqual(counts["BOT_DEFINITION"], 1)
        self.assertEqual(counts["TOPIC"], 1)
        self.assertEqual(counts["FLOW"], 1)
        self.assertEqual(counts["APEX"], 1)
        self.assertEqual(counts["STANDARD_ACTION"], 1)


# -----------------------------------------------------------------------------
# finalize_cap
# -----------------------------------------------------------------------------


class FinalizeCapTests(unittest.TestCase):

    def test_drains_pending_into_unresolved(self):
        tree = {
            "_pending_fetches": {
                "FLOW": ["FlowA", "FlowB"],
                "APEX": ["ClassA"],
                "PROMPT_TEMPLATE": [], "STANDARD_ACTION": [],
            },
            "_unresolved": [],
        }
        out = parse_wave.finalize_cap(tree)
        self.assertEqual(len(out["_unresolved"]), 3)
        # Pending wiped per-kind
        for kind in parse_wave.BFS_KINDS:
            self.assertEqual(out["_pending_fetches"][kind], [])
        # _partial flipped
        self.assertTrue(out["_partial"])
        self.assertEqual(out["_partial_reason"], "max-wave-depth")

    def test_does_not_overwrite_existing_partial_reason(self):
        tree = {
            "_pending_fetches": {"FLOW": ["FlowA"], "APEX": [],
                                  "PROMPT_TEMPLATE": [], "STANDARD_ACTION": []},
            "_unresolved": [],
            "_partial_reason": "max-depth-cap",  # earlier-set, more specific
        }
        out = parse_wave.finalize_cap(tree)
        # Reason kept; depth-cap wins priority over wave-depth.
        self.assertEqual(out["_partial_reason"], "max-depth-cap")

    def test_no_pending_no_changes(self):
        tree = {
            "_pending_fetches": {k: [] for k in parse_wave.BFS_KINDS},
            "_unresolved": [],
            "_partial": False,
            "_partial_reason": None,
        }
        out = parse_wave.finalize_cap(tree)
        self.assertEqual(out["_unresolved"], [])
        # Nothing drained, _partial untouched
        self.assertFalse(out["_partial"])

    def test_unresolved_entry_shape(self):
        tree = {
            "_pending_fetches": {"FLOW": ["FlowA"], "APEX": [],
                                  "PROMPT_TEMPLATE": [], "STANDARD_ACTION": []},
            "_unresolved": [],
        }
        out = parse_wave.finalize_cap(tree)
        entry = out["_unresolved"][0]
        self.assertEqual(entry["kind"], "FLOW")
        self.assertEqual(entry["api_name"], "FlowA")
        self.assertEqual(entry["reason"], "max-wave-depth exceeded")


# -----------------------------------------------------------------------------
# atomic_write_json
# -----------------------------------------------------------------------------


class AtomicWriteJsonTests(unittest.TestCase):

    def test_writes_indented_json(self):
        with TemporaryDirectory() as t:
            target = Path(t) / "out.json"
            parse_wave.atomic_write_json(target, {"a": 1, "b": [1, 2]})
            data = json.loads(target.read_text())
        self.assertEqual(data, {"a": 1, "b": [1, 2]})

    def test_overwrites_existing(self):
        with TemporaryDirectory() as t:
            target = Path(t) / "out.json"
            target.write_text("old")
            parse_wave.atomic_write_json(target, {"new": True})
            data = json.loads(target.read_text())
        self.assertEqual(data, {"new": True})

    def test_no_tmp_left_behind(self):
        with TemporaryDirectory() as t:
            target = Path(t) / "out.json"
            parse_wave.atomic_write_json(target, {"x": 1})
            tmp_sibling = target.with_suffix(target.suffix + ".tmp")
        self.assertFalse(tmp_sibling.exists())


# -----------------------------------------------------------------------------
# init_tree
# -----------------------------------------------------------------------------


class InitTreeTests(unittest.TestCase):

    def _setup_env(self, **overrides) -> dict:
        defaults = {
            "AGENT_API_NAME": "DemoAgent",
            "AGENT_VERSION": "v3",
            "BOT_ID": "0Xx000000000ABC",
            "BOT_MASTER_LABEL": "Demo Agent",
            "VERSION_AUTO_PICKED": "false",
        }
        defaults.update(overrides)
        return defaults

    def _run(self, *, work_dir: Path, env: dict, bundle: dict) -> dict:
        old = dict(os.environ)
        try:
            os.environ.update(env)
            return parse_wave.init_tree(work_dir, bundle)
        finally:
            os.environ.clear()
            os.environ.update(old)

    def test_initial_tree_shape(self):
        with TemporaryDirectory() as t:
            tree = self._run(
                work_dir=Path(t),
                env=self._setup_env(),
                bundle={"generation": "nga", "plannerName": "MyPlanner",
                        "plannerType": "Atlas__Reasoning"},
            )
        self.assertEqual(tree["_schema_version"], "3.1")
        self.assertEqual(tree["agent"]["api_name"], "DemoAgent")
        self.assertEqual(tree["agent"]["version"], "v3")
        self.assertEqual(tree["agent"]["generation"], "nga")
        self.assertEqual(tree["agent"]["planner_name"], "MyPlanner")
        self.assertEqual(tree["root"]["kind"], "BOT_DEFINITION")
        self.assertEqual(tree["root"]["children"], [])
        self.assertTrue(tree["_partial"])
        self.assertIsNone(tree["_partial_reason"])
        # _pending_fetches has all 4 BFS kinds
        for kind in parse_wave.BFS_KINDS:
            self.assertIn(kind, tree["_pending_fetches"])

    def test_pulls_bot_definition_metadata_from_disk(self):
        with TemporaryDirectory() as t:
            work_dir = Path(t)
            (work_dir / "_bot_definition.json").write_text(json.dumps({
                "result": {"records": [{
                    "DeveloperName": "DemoAgent",
                    "MasterLabel": "Demo (from disk)",
                    "Description": "via _bot_definition.json",
                    "AgentType": "Internal",
                    "Type": "AiCopilot",
                    "AgentTemplate": "TPL",
                    "BotSource": "AgentforceAgentCopilot",
                }]},
            }))
            tree = self._run(
                work_dir=work_dir,
                env=self._setup_env(),
                bundle={"generation": "classic"},
            )
        # MasterLabel from _bot_definition.json wins over env
        self.assertEqual(tree["agent"]["master_label"], "Demo (from disk)")
        self.assertEqual(tree["agent"]["description"], "via _bot_definition.json")
        self.assertEqual(tree["agent"]["agent_type"], "Internal")

    def test_version_auto_picked_flag_propagates(self):
        with TemporaryDirectory() as t:
            tree = self._run(
                work_dir=Path(t),
                env=self._setup_env(VERSION_AUTO_PICKED="true"),
                bundle={"generation": "nga"},
            )
        self.assertTrue(tree["agent"]["_version_auto_picked"])


# -----------------------------------------------------------------------------
# harvest_waves
# -----------------------------------------------------------------------------


def _flow_xml(*, name: str, action_calls: list[dict] | None = None,
              subflows: list[str] | None = None) -> str:
    """Build a minimal Flow XML body."""
    acs = "".join(
        f"""  <actionCalls>
    <name>{ac['name']}</name>
    <actionType>{ac['actionType']}</actionType>
    <actionName>{ac['actionName']}</actionName>
  </actionCalls>
"""
        for ac in (action_calls or [])
    )
    subs = "".join(
        f"""  <subflows>
    <name>sub_{i}</name>
    <flowName>{fn}</flowName>
  </subflows>
"""
        for i, fn in enumerate(subflows or [])
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Flow xmlns="{_FLOW_NS}">
  <fullName>{name}</fullName>
{acs}{subs}</Flow>
"""


class HarvestWavesTests(unittest.TestCase):

    def _setup_wave(self, work_dir: Path, *, flow_files: dict[str, str],
                    apex_class_names: list[str] | None = None,
                    prompt_template_names: list[str] | None = None) -> None:
        """Plant a wave1/unpackaged/{flows,classes,genAiPromptTemplates}/
        directory tree under work_dir/sf_meta/."""
        wave = work_dir / "sf_meta" / "wave1" / "unpackaged"
        flows_dir = wave / "flows"
        flows_dir.mkdir(parents=True)
        for filename, body in flow_files.items():
            (flows_dir / filename).write_text(body)
        if apex_class_names:
            classes_dir = wave / "classes"
            classes_dir.mkdir()
            for n in apex_class_names:
                (classes_dir / f"{n}.cls-meta.xml").write_text("<x/>")
        if prompt_template_names:
            prompt_dir = wave / "genAiPromptTemplates"
            prompt_dir.mkdir()
            for n in prompt_template_names:
                (prompt_dir / f"{n}.genAiPromptTemplate").write_text("<x/>")

    def test_returns_empty_when_no_sf_meta(self):
        with TemporaryDirectory() as t:
            flow_children, vis, pend, cycles = parse_wave.harvest_waves(Path(t))
        self.assertEqual(flow_children, {})
        self.assertEqual(cycles, [])
        for v in vis.values():
            self.assertEqual(v, set())

    def test_harvests_flow_action_calls_and_subflows(self):
        with TemporaryDirectory() as t:
            work_dir = Path(t)
            self._setup_wave(work_dir, flow_files={
                "MainFlow.flow": _flow_xml(
                    name="MainFlow",
                    action_calls=[
                        {"name": "callA", "actionType": "apex",
                         "actionName": "MyClass"},
                        {"name": "callB", "actionType": "generatePromptResponse",
                         "actionName": "MyPrompt"},
                    ],
                    subflows=["NestedFlow"],
                ),
            })
            flow_children, visited, pending, _cycles = parse_wave.harvest_waves(work_dir)
        # MainFlow visited
        self.assertIn("MainFlow", visited["FLOW"])
        # Apex + prompt-template + nested flow ref harvested into pending
        self.assertIn("MyClass", pending["APEX"])
        self.assertIn("MyPrompt", pending["PROMPT_TEMPLATE"])
        self.assertIn("NestedFlow", pending["FLOW"])
        # MainFlow's children include the apex + prompt-template + subflow
        self.assertEqual(len(flow_children["MainFlow"]), 3)

    def test_apex_classes_marked_visited(self):
        with TemporaryDirectory() as t:
            work_dir = Path(t)
            self._setup_wave(
                work_dir,
                flow_files={"F.flow": _flow_xml(name="F")},
                apex_class_names=["AlreadyApex"],
            )
            _, visited, _, _ = parse_wave.harvest_waves(work_dir)
        self.assertIn("AlreadyApex", visited["APEX"])

    def test_prompt_templates_marked_visited(self):
        with TemporaryDirectory() as t:
            work_dir = Path(t)
            self._setup_wave(
                work_dir,
                flow_files={"F.flow": _flow_xml(name="F")},
                prompt_template_names=["AlreadyPrompt"],
            )
            _, visited, _, _ = parse_wave.harvest_waves(work_dir)
        self.assertIn("AlreadyPrompt", visited["PROMPT_TEMPLATE"])

    def test_already_visited_apex_pruned_from_pending(self):
        """When pass-2/3 marks an Apex class visited AFTER pass-1 routed it
        into pending, the post-pass prune drops it from pending."""
        with TemporaryDirectory() as t:
            work_dir = Path(t)
            self._setup_wave(work_dir,
                             flow_files={"F.flow": _flow_xml(
                                 name="F",
                                 action_calls=[{
                                     "name": "callA", "actionType": "apex",
                                     "actionName": "ClassX",
                                 }],
                             )},
                             apex_class_names=["ClassX"])
            _, visited, pending, _ = parse_wave.harvest_waves(work_dir)
        self.assertIn("ClassX", visited["APEX"])
        # Pruned because already-visited (Apex class file present this wave)
        self.assertNotIn("ClassX", pending["APEX"])

    def test_malformed_flow_xml_returns_empty_children(self):
        with TemporaryDirectory() as t:
            work_dir = Path(t)
            self._setup_wave(work_dir, flow_files={
                "Broken.flow": "<<<not xml>>>",
            })
            flow_children, _, _, _ = parse_wave.harvest_waves(work_dir)
        self.assertEqual(flow_children["Broken"], [])


if __name__ == "__main__":
    unittest.main()
