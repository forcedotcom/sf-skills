"""Tests for ``parse_wave.main`` orchestrator + tree-walking helpers.

Covers:
- ``walk_and_inflate``        recursive Flow inflation
- ``inflate_flow_leaf``       cycle + depth-cap behavior
- ``build_root_children``     bundle → root children + new_refs
- ``main`` (full path)        env-driven pipeline against a tmp WORK_DIR
- ``main --finalize-cap``     drain pending → unresolved
"""
from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from . import _bootstrap  # noqa: F401  — sys.path setup

import parse_wave  # type: ignore


_FLOW_NS = "http://soap.sforce.com/2006/04/metadata"


# -----------------------------------------------------------------------------
# walk_and_inflate
# -----------------------------------------------------------------------------


class WalkAndInflateTests(unittest.TestCase):

    def test_no_op_for_non_FLOW_non_GEN_AI_FUNCTION_node(self):
        node = {"kind": "TOPIC", "api_name": "T1", "children": []}
        flow_children: dict = {}
        # Should not raise; should not mutate.
        parse_wave.walk_and_inflate(node, flow_children)
        self.assertEqual(node["children"], [])

    def test_inflates_flow_leaf_under_gen_ai_function(self):
        # GEN_AI_FUNCTION wraps a FLOW leaf — walker recurses into it.
        node = {
            "kind": "GEN_AI_FUNCTION",
            "api_name": "GAF1",
            "children": [{"kind": "FLOW", "api_name": "MyFlow", "children": []}],
        }
        flow_children = {"MyFlow": [
            {"kind": "APEX", "element_name": "callA", "api_name": "MyClass"},
        ]}
        parse_wave.walk_and_inflate(node, flow_children)
        # FLOW leaf got inflated with the APEX child
        flow_leaf = node["children"][0]
        self.assertEqual(len(flow_leaf["children"]), 1)
        self.assertEqual(flow_leaf["children"][0]["kind"], "APEX")

    def test_recursively_walks_through_topic_to_inflate_flow(self):
        # Walker should descend through TOPIC/non-special nodes too.
        node = {
            "kind": "BOT_DEFINITION", "api_name": "Agent",
            "children": [{
                "kind": "TOPIC", "api_name": "T1",
                "children": [{
                    "kind": "GEN_AI_FUNCTION", "api_name": "GAF1",
                    "children": [{"kind": "FLOW", "api_name": "DeepFlow",
                                  "children": []}],
                }],
            }],
        }
        flow_children = {"DeepFlow": [
            {"kind": "APEX", "element_name": "callA", "api_name": "DeepClass"},
        ]}
        parse_wave.walk_and_inflate(node, flow_children)
        # DeepFlow got the APEX child
        deep_flow = node["children"][0]["children"][0]["children"][0]
        self.assertEqual(deep_flow["children"][0]["api_name"], "DeepClass")

    def test_pending_out_collects_depth_cap_truncations(self):
        # Build a chain longer than MAX_BFS_DEPTH so the cap trips.
        # Generate 25 flows that each subflow into the next.
        flow_children: dict = {}
        for i in range(25):
            next_name = f"F{i+1}" if i < 24 else None
            kids = []
            if next_name:
                kids.append({"kind": "FLOW", "element_name": f"sub_{i}",
                             "api_name": next_name})
            flow_children[f"F{i}"] = kids
        node = {"kind": "FLOW", "api_name": "F0", "children": []}
        pending: dict = parse_wave.empty_kind_sets()
        parse_wave.walk_and_inflate(node, flow_children, pending_out=pending)
        # Some subflow ended up in pending due to the depth cap (>= MAX_BFS_DEPTH).
        self.assertTrue(any(pending[k] for k in parse_wave.BFS_KINDS))


# -----------------------------------------------------------------------------
# inflate_flow_leaf — cycle detection
# -----------------------------------------------------------------------------


class InflateFlowLeafCycleTests(unittest.TestCase):

    def test_self_recursion_marked_as_cycle(self):
        # Flow A subflows back to A itself → cycle.
        flow_children = {"A": [
            {"kind": "FLOW", "element_name": "self", "api_name": "A"},
        ]}
        leaf = {"kind": "FLOW", "api_name": "A", "children": []}
        parse_wave.inflate_flow_leaf(leaf, flow_children)
        # The recursive child got annotated with _truncated.
        kid = leaf["children"][0]
        self.assertIn("_truncated", kid)
        self.assertEqual(kid["_truncated"]["reason"],
                         parse_wave.TRUNCATION_CYCLE)

    def test_unknown_flow_no_inflation(self):
        # leaf.api_name not in flow_children → nothing to inflate.
        leaf = {"kind": "FLOW", "api_name": "Missing", "children": []}
        parse_wave.inflate_flow_leaf(leaf, {})
        self.assertEqual(leaf["children"], [])


# -----------------------------------------------------------------------------
# build_root_children
# -----------------------------------------------------------------------------


class BuildRootChildrenTests(unittest.TestCase):

    def test_topics_become_root_children(self):
        bundle = {
            "topics": [
                {"name": "Greetings", "actions": [
                    {"name": "Hello", "invocationTarget": "MyFlow",
                     "invocationTargetType": "flow"},
                ]},
            ],
        }
        visited = parse_wave.empty_kind_sets()
        aux: set = set()
        children, new_refs = parse_wave.build_root_children(bundle, visited, aux)
        self.assertEqual(len(children), 1)
        self.assertEqual(children[0]["kind"], "TOPIC")
        self.assertEqual(children[0]["api_name"], "Greetings")
        # GEN_AI_FUNCTION wrapping the action
        self.assertEqual(children[0]["children"][0]["kind"], "GEN_AI_FUNCTION")
        # FLOW ref harvested into new_refs
        self.assertIn("MyFlow", new_refs["FLOW"])
        # Topic + action recorded in aux_visited
        self.assertIn(("TOPIC", "Greetings"), aux)
        self.assertIn(("GEN_AI_FUNCTION", "Hello"), aux)

    def test_skips_already_visited_refs(self):
        bundle = {
            "topics": [{"name": "T", "actions": [
                {"name": "A1", "invocationTarget": "FlowA",
                 "invocationTargetType": "flow"},
            ]}],
        }
        visited = parse_wave.empty_kind_sets()
        visited["FLOW"].add("FlowA")
        aux: set = set()
        _, new_refs = parse_wave.build_root_children(bundle, visited, aux)
        # FlowA already visited → not added to new_refs
        self.assertNotIn("FlowA", new_refs["FLOW"])

    def test_standard_action_does_not_pollute_new_refs(self):
        # STANDARD_ACTION is declared-only, must NOT
        # land in new_refs (would pollute _pending_fetches).
        bundle = {
            "topics": [{"name": "T", "actions": [
                {"name": "A1", "invocationTarget": "createRecord",
                 "invocationTargetType": "standardinvocableaction"},
            ]}],
        }
        visited = parse_wave.empty_kind_sets()
        aux: set = set()
        _, new_refs = parse_wave.build_root_children(bundle, visited, aux)
        self.assertNotIn("createRecord", new_refs["STANDARD_ACTION"])

    def test_empty_bundle_returns_empty_children(self):
        children, new_refs = parse_wave.build_root_children(
            {}, parse_wave.empty_kind_sets(), set(),
        )
        self.assertEqual(children, [])
        for v in new_refs.values():
            self.assertEqual(v, set())


# -----------------------------------------------------------------------------
# main() — happy path + finalize-cap branch
# -----------------------------------------------------------------------------


def _setup_workdir(tmp: Path, *, bundle: dict | None = None) -> Path:
    """Plant a WORK_DIR with _bundle_parsed.json + minimal sf_meta layout."""
    work_dir = tmp / "work"
    work_dir.mkdir()
    bundle = bundle or {
        "plannerName": "MyPlanner",
        "plannerType": "Atlas__Reasoning",
        "generation": "nga",
        "topics": [{"name": "Greetings", "actions": [
            {"name": "SayHi", "invocationTarget": "GreetingsFlow",
             "invocationTargetType": "flow"},
        ]}],
    }
    (work_dir / "_bundle_parsed.json").write_text(json.dumps(bundle))
    # Empty sf_meta is fine — harvest_waves returns empty when missing.
    return work_dir


def _run_main(*, work_dir: Path, argv_extra: list[str] | None = None,
              env_extra: dict | None = None) -> int:
    """Invoke parse_wave.main with controlled env + argv."""
    saved_env = dict(os.environ)
    saved_argv = list(parse_wave.sys.argv)
    try:
        os.environ.update({
            "WORK_DIR": str(work_dir),
            "AGENT_API_NAME": "DemoAgent",
            "AGENT_VERSION": "v3",
            "BOT_ID": "0Xx000000000ABC",
            "BOT_MASTER_LABEL": "Demo Agent",
            "VERSION_AUTO_PICKED": "false",
        })
        if env_extra:
            os.environ.update(env_extra)
        parse_wave.sys.argv = ["parse_wave.py", *(argv_extra or [])]
        return parse_wave.main()
    finally:
        os.environ.clear()
        os.environ.update(saved_env)
        parse_wave.sys.argv = saved_argv


class MainHappyPathTests(unittest.TestCase):

    def test_main_writes_declared_action_tree_json(self):
        with TemporaryDirectory() as t:
            tmp = Path(t)
            work_dir = _setup_workdir(tmp)
            with mock.patch.object(parse_wave.sys, "stderr"):
                rc = _run_main(work_dir=work_dir)
            self.assertEqual(rc, 0)
            tree_path = work_dir / "declared_action_tree.json"
            self.assertTrue(tree_path.is_file())
            tree = json.loads(tree_path.read_text())
            # Tree has the expected shape
            self.assertEqual(tree["_schema_version"], "3.1")
            self.assertEqual(tree["agent"]["api_name"], "DemoAgent")
            self.assertEqual(tree["root"]["kind"], "BOT_DEFINITION")
            # One topic became a root child
            kinds = [c["kind"] for c in tree["root"]["children"]]
            self.assertIn("TOPIC", kinds)

    def test_main_records_pending_for_unfetched_flow(self):
        with TemporaryDirectory() as t:
            tmp = Path(t)
            work_dir = _setup_workdir(tmp)
            with mock.patch.object(parse_wave.sys, "stderr"):
                _run_main(work_dir=work_dir)
            tree = json.loads(
                (work_dir / "declared_action_tree.json").read_text()
            )
        # GreetingsFlow not on disk → in _pending_fetches.FLOW
        self.assertIn("GreetingsFlow", tree["_pending_fetches"]["FLOW"])
        self.assertTrue(tree["_partial"])
        # _partial_reason populated on first run when pending refs exist
        # but no depth cap was tripped.
        self.assertEqual(tree["_partial_reason"], "pending-refs")

    def test_main_writes_pending_refs_reason_when_initial_reason_is_none(self):
        # init_tree seeds `_partial_reason=None`. The writer's elif branch
        # must populate it with "pending-refs" when any pending bucket is
        # non-empty and the depth cap did not trip — a setdefault against
        # `None` is a no-op, which is the bug this guards.
        with TemporaryDirectory() as t:
            tmp = Path(t)
            work_dir = _setup_workdir(tmp)
            with mock.patch.object(parse_wave.sys, "stderr"):
                _run_main(work_dir=work_dir)
            tree = json.loads(
                (work_dir / "declared_action_tree.json").read_text()
            )
        # Sanity: pending exists, depth cap was NOT tripped.
        self.assertIn("GreetingsFlow", tree["_pending_fetches"]["FLOW"])
        # The fix: a None-valued reason gets promoted to "pending-refs".
        self.assertEqual(tree["_partial_reason"], "pending-refs")

    def test_main_preserves_existing_partial_reason_when_pending_refs(self):
        # init_tree primes _partial_reason=None; setdefault used to be a
        # no-op against that None and left the reason blank. Today the
        # writer treats None as "unset" and fills in "pending-refs".
        # When a prior reason exists (e.g. "max-depth-cap" from a previous
        # wave), the writer must NOT overwrite it.
        with TemporaryDirectory() as t:
            tmp = Path(t)
            work_dir = _setup_workdir(tmp)
            # Plant a tree on disk that mimics a previously-suspended run:
            # _partial_reason="max-depth-cap" and empty root children, so
            # main() enters the fresh-tree branch and re-collects bundle
            # refs (GreetingsFlow pending) yet sees the prior reason.
            tree_path = work_dir / "declared_action_tree.json"
            tree_path.write_text(json.dumps({
                "_schema_version": "3.1",
                "agent": {"api_name": "DemoAgent", "version": "v3"},
                "root": {"kind": "BOT_DEFINITION", "api_name": "DemoAgent",
                         "children": []},
                "_partial": True,
                "_partial_reason": "max-depth-cap",
                "_pending_fetches": {k: [] for k in parse_wave.BFS_KINDS},
                "_unresolved": [],
                "_visited": [],
            }))
            with mock.patch.object(parse_wave.sys, "stderr"):
                _run_main(work_dir=work_dir)
            tree2 = json.loads(tree_path.read_text())
        # GreetingsFlow is pending → any_pending=True → elif branch runs.
        self.assertIn("GreetingsFlow", tree2["_pending_fetches"]["FLOW"])
        # Existing more-specific reason is preserved.
        self.assertEqual(tree2["_partial_reason"], "max-depth-cap")

    def test_main_returns_one_when_work_dir_env_missing(self):
        saved_env = dict(os.environ)
        try:
            for k in ("WORK_DIR", "AGENT_API_NAME", "AGENT_VERSION"):
                os.environ.pop(k, None)
            with mock.patch.object(parse_wave.sys, "argv", ["parse_wave.py"]):
                with mock.patch.object(parse_wave.sys, "stderr"):
                    rc = parse_wave.main()
        finally:
            os.environ.clear()
            os.environ.update(saved_env)
        self.assertEqual(rc, 1)

    def test_main_returns_one_when_bundle_missing(self):
        with TemporaryDirectory() as t:
            tmp = Path(t)
            work_dir = tmp / "work"
            work_dir.mkdir()
            # No _bundle_parsed.json
            with mock.patch.object(parse_wave.sys, "stderr"):
                rc = _run_main(work_dir=work_dir)
        self.assertEqual(rc, 1)

    def test_main_reparses_existing_tree(self):
        # Two-pass: first run creates the tree, second re-uses it.
        with TemporaryDirectory() as t:
            tmp = Path(t)
            work_dir = _setup_workdir(tmp)
            with mock.patch.object(parse_wave.sys, "stderr"):
                _run_main(work_dir=work_dir)
                # Second invocation should load + augment without crashing
                rc = _run_main(work_dir=work_dir)
        self.assertEqual(rc, 0)


class MainFinalizeCapTests(unittest.TestCase):

    def test_finalize_cap_drains_pending_into_unresolved(self):
        with TemporaryDirectory() as t:
            tmp = Path(t)
            work_dir = _setup_workdir(tmp)
            # First run produces a tree with pending FLOW=GreetingsFlow.
            with mock.patch.object(parse_wave.sys, "stderr"):
                _run_main(work_dir=work_dir)
                # --finalize-cap drains pending → unresolved
                rc = _run_main(
                    work_dir=work_dir, argv_extra=["--finalize-cap"],
                )
            self.assertEqual(rc, 0)
            tree = json.loads(
                (work_dir / "declared_action_tree.json").read_text()
            )
            # All buckets emptied
            for kind in parse_wave.BFS_KINDS:
                self.assertEqual(tree["_pending_fetches"][kind], [])
            # GreetingsFlow now in _unresolved
            api_names = [u["api_name"] for u in tree["_unresolved"]]
            self.assertIn("GreetingsFlow", api_names)

    def test_finalize_cap_with_no_existing_tree_is_noop(self):
        with TemporaryDirectory() as t:
            tmp = Path(t)
            work_dir = tmp / "work"
            work_dir.mkdir()
            with mock.patch.object(parse_wave.sys, "stderr"):
                rc = _run_main(
                    work_dir=work_dir, argv_extra=["--finalize-cap"],
                )
        # No tree file → noop, exit 0.
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
