"""Tests for ``finalize`` — declared-action-tree finalization + cache write.

Covers:
- ``sort_tree_in_place``  pure tree mutation (TOPIC-first, alphabetical-by-api_name)
- ``main``                WORK_DIR / DATA_DIR / CACHE_DIR orchestration

The pure-function tests build small dict trees inline. ``main`` tests
construct a minimal WORK_DIR layout under ``tmp_path`` so the orchestration
runs end-to-end without any external metadata fixtures.
"""
from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from . import _bootstrap  # noqa: F401  — sys.path setup

import finalize  # type: ignore


# -----------------------------------------------------------------------------
# sort_tree_in_place — pure tree mutation
# -----------------------------------------------------------------------------


class SortTreeInPlaceTests(unittest.TestCase):
    """Per docstring: TOPIC nodes first, then non-topic plannerActions.
    Within each tier, sorted by kind then api_name (case-insensitive).
    Each TOPIC's own children: alphabetical by api_name (case-insensitive).
    FLOW children are NOT sorted.
    """

    def test_empty_tree_is_noop(self):
        root = {}
        finalize.sort_tree_in_place(root)
        self.assertEqual(root, {})

    def test_root_with_no_children_is_noop(self):
        root = {"children": []}
        finalize.sort_tree_in_place(root)
        self.assertEqual(root["children"], [])

    def test_non_dict_root_is_safe(self):
        # Non-dict input shouldn't blow up.
        finalize.sort_tree_in_place(None)  # type: ignore[arg-type]
        finalize.sort_tree_in_place([])  # type: ignore[arg-type]

    def test_topics_come_before_non_topics_at_root(self):
        root = {"children": [
            {"kind": "STANDARD_ACTION", "api_name": "actA"},
            {"kind": "TOPIC", "api_name": "topicZ"},
            {"kind": "APEX", "api_name": "apexA"},
            {"kind": "TOPIC", "api_name": "topicA"},
        ]}
        finalize.sort_tree_in_place(root)
        kinds = [c["kind"] for c in root["children"]]
        # Two TOPICs first, then non-topics
        self.assertEqual(kinds[:2], ["TOPIC", "TOPIC"])
        self.assertNotIn("TOPIC", kinds[2:])

    def test_topics_sort_alphabetical_case_insensitive(self):
        root = {"children": [
            {"kind": "TOPIC", "api_name": "Zeta"},
            {"kind": "TOPIC", "api_name": "alpha"},
            {"kind": "TOPIC", "api_name": "Beta"},
        ]}
        finalize.sort_tree_in_place(root)
        names = [c["api_name"] for c in root["children"]]
        self.assertEqual(names, ["alpha", "Beta", "Zeta"])

    def test_non_topics_sort_by_kind_then_name(self):
        root = {"children": [
            {"kind": "STANDARD_ACTION", "api_name": "z_act"},
            {"kind": "APEX", "api_name": "z_apex"},
            {"kind": "STANDARD_ACTION", "api_name": "a_act"},
            {"kind": "APEX", "api_name": "a_apex"},
        ]}
        finalize.sort_tree_in_place(root)
        # Tier 1 sorted by (kind, api_name): APEX rows before STANDARD_ACTION
        kinds = [c["kind"] for c in root["children"]]
        self.assertEqual(kinds, ["APEX", "APEX", "STANDARD_ACTION", "STANDARD_ACTION"])
        names_apex = [c["api_name"] for c in root["children"][:2]]
        self.assertEqual(names_apex, ["a_apex", "z_apex"])

    def test_topic_children_sorted_alphabetical_case_insensitive(self):
        root = {"children": [{
            "kind": "TOPIC",
            "api_name": "T1",
            "children": [
                {"kind": "STANDARD_ACTION", "api_name": "Zebra"},
                {"kind": "STANDARD_ACTION", "api_name": "apple"},
                {"kind": "STANDARD_ACTION", "api_name": "Banana"},
            ],
        }]}
        finalize.sort_tree_in_place(root)
        names = [c["api_name"] for c in root["children"][0]["children"]]
        self.assertEqual(names, ["apple", "Banana", "Zebra"])

    def test_topic_with_no_children_is_safe(self):
        root = {"children": [{"kind": "TOPIC", "api_name": "T1"}]}
        finalize.sort_tree_in_place(root)
        self.assertEqual(root["children"][0]["api_name"], "T1")

    def test_missing_api_name_treated_as_empty(self):
        # Should sort to the front under casefold of empty string.
        root = {"children": [
            {"kind": "TOPIC", "api_name": "Beta"},
            {"kind": "TOPIC"},  # no api_name
        ]}
        finalize.sort_tree_in_place(root)
        names = [c.get("api_name", "") for c in root["children"]]
        self.assertEqual(names[0], "")  # empty/missing comes first


# -----------------------------------------------------------------------------
# main — orchestration via env vars + WORK_DIR
# -----------------------------------------------------------------------------


def _build_workdir(tmp: Path, *, planner_name: str = "MyPlanner",
                   pending: dict | None = None,
                   unresolved: list | None = None) -> tuple[Path, Path, Path]:
    """Construct a minimal WORK_DIR + DATA_DIR + CACHE_DIR triple.

    Returns (work_dir, data_dir, cache_dir). Caller passes these as env
    vars before invoking finalize.main().
    """
    work_dir = tmp / "work"
    data_dir = tmp / "data" / "ALPHA0000000000" / "MyAgent__v1"
    cache_dir = tmp / "cache" / "ALPHA0000000000" / "MyAgent__v1"
    work_dir.mkdir(parents=True)

    tree = {
        "agent": {"api_name": "MyAgent", "version": "v1"},
        "node_count": 1,
        "depth": 1,
        "_schema_version": "3.1",
        "_kind_counts": {"TOPIC": 1},
        "_pending_fetches": pending or {},
        "_unresolved": unresolved or [],
        "root": {"children": [{"kind": "TOPIC", "api_name": "Greetings"}]},
    }
    (work_dir / "declared_action_tree.json").write_text(json.dumps(tree))
    return work_dir, data_dir, cache_dir


class MainTests(unittest.TestCase):

    def _run_main(self, work_dir: Path, data_dir: Path, cache_dir: Path,
                  *, planner_name: str = "MyPlanner") -> int:
        old = dict(os.environ)
        os.environ.update({
            "WORK_DIR": str(work_dir),
            "DATA_DIR": str(data_dir),
            "CACHE_DIR": str(cache_dir),
            "AGENT_API_NAME": "MyAgent",
            "AGENT_VERSION": "v1",
            "PLANNER_NAME": planner_name,
        })
        try:
            return finalize.main()
        finally:
            os.environ.clear()
            os.environ.update(old)

    def test_main_writes_tree_and_manifest_and_returns_zero(self):
        with TemporaryDirectory() as t:
            tmp = Path(t)
            work_dir, data_dir, cache_dir = _build_workdir(tmp)
            rc = self._run_main(work_dir, data_dir, cache_dir)
            self.assertEqual(rc, 0)
            tree_file = data_dir / "MyAgent_v1_metadata_tree.json"
            self.assertTrue(tree_file.exists())
            self.assertTrue((data_dir / "last_built_at.txt").exists())
            manifest = json.loads((cache_dir / "manifest.json").read_text())
            self.assertEqual(manifest["agent"]["api_name"], "MyAgent")
            self.assertEqual(manifest["partial"], False)
            self.assertEqual(manifest["unresolved_count"], 0)

    def test_main_marks_partial_when_planner_name_empty(self):
        # Empty PLANNER_NAME → _partial=True, _partial_reason="no-planner".
        with TemporaryDirectory() as t:
            tmp = Path(t)
            work_dir, data_dir, cache_dir = _build_workdir(tmp)
            rc = self._run_main(work_dir, data_dir, cache_dir, planner_name="")
            self.assertEqual(rc, 0)
            tree = json.loads(
                (data_dir / "MyAgent_v1_metadata_tree.json").read_text()
            )
            self.assertTrue(tree["_partial"])
            self.assertEqual(tree["_partial_reason"], "no-planner")

    def test_main_marks_partial_when_unresolved_present(self):
        # Planner OK, _pending empty, but _unresolved non-empty
        # → _partial=True, _partial_reason="unresolved-refs".
        with TemporaryDirectory() as t:
            tmp = Path(t)
            work_dir, data_dir, cache_dir = _build_workdir(
                tmp, unresolved=[{"reason": "404"}]
            )
            rc = self._run_main(work_dir, data_dir, cache_dir)
            self.assertEqual(rc, 0)
            tree = json.loads(
                (data_dir / "MyAgent_v1_metadata_tree.json").read_text()
            )
            self.assertTrue(tree["_partial"])
            self.assertEqual(tree["_partial_reason"], "unresolved-refs")

    def test_main_marks_partial_when_pending_present(self):
        # Planner OK, _unresolved empty, but _pending non-empty
        # → _partial=True, _partial_reason="pending-refs".
        with TemporaryDirectory() as t:
            tmp = Path(t)
            work_dir, data_dir, cache_dir = _build_workdir(
                tmp, pending={"flows": ["FlowA"]}
            )
            rc = self._run_main(work_dir, data_dir, cache_dir)
            self.assertEqual(rc, 0)
            tree = json.loads(
                (data_dir / "MyAgent_v1_metadata_tree.json").read_text()
            )
            self.assertTrue(tree["_partial"])
            self.assertEqual(tree["_partial_reason"], "pending-refs")

    def test_main_returns_one_when_env_missing(self):
        old = dict(os.environ)
        # Wipe required envs. Set only one.
        for k in ("WORK_DIR", "DATA_DIR", "CACHE_DIR",
                  "AGENT_API_NAME", "AGENT_VERSION"):
            os.environ.pop(k, None)
        try:
            rc = finalize.main()
        finally:
            os.environ.clear()
            os.environ.update(old)
        self.assertEqual(rc, 1)

    def test_main_returns_one_when_tree_json_missing(self):
        with TemporaryDirectory() as t:
            tmp = Path(t)
            work_dir = tmp / "work"
            data_dir = tmp / "data"
            cache_dir = tmp / "cache"
            work_dir.mkdir()
            # No declared_action_tree.json — finalize should bail.
            rc = self._run_main(work_dir, data_dir, cache_dir)
            self.assertEqual(rc, 1)

    def test_main_strips_visited_from_durable_artifact(self):
        with TemporaryDirectory() as t:
            tmp = Path(t)
            work_dir, data_dir, cache_dir = _build_workdir(tmp)
            tree_path = work_dir / "declared_action_tree.json"
            tree = json.loads(tree_path.read_text())
            tree["_visited"] = {"some": "internal-state"}
            tree_path.write_text(json.dumps(tree))
            rc = self._run_main(work_dir, data_dir, cache_dir)
            self.assertEqual(rc, 0)
            written = json.loads(
                (data_dir / "MyAgent_v1_metadata_tree.json").read_text()
            )
            self.assertNotIn("_visited", written)

    def test_main_seeds_gitignore_on_data_and_cache_roots(self):
        with TemporaryDirectory() as t:
            tmp = Path(t)
            work_dir, data_dir, cache_dir = _build_workdir(tmp)
            self._run_main(work_dir, data_dir, cache_dir)
            # data_dir.parent.parent == tmp/data; cache_dir.parent.parent == tmp/cache
            self.assertTrue((data_dir.parent.parent / ".gitignore").exists())
            self.assertTrue((cache_dir.parent.parent / ".gitignore").exists())


if __name__ == "__main__":
    unittest.main()
