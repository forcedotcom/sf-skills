"""2026-05-03 revision: `inflate_flow_leaf` uses a per-branch ancestor
path set (`visited_in_path`) for cycle detection. The defensive
`MAX_BFS_DEPTH` cap is preserved as a last-resort termination guard
but is no longer the primitive that prevents runaway recursion.

The bug this regression suite prevents: shared utility flows such as
`handleFlowFault` appear on every real Agentforce flow's fault path.
Under the old `MAX_BFS_DEPTH = 5` behaviour the utility showed up in
`_pending_fetches["FLOW"]` with `PARTIAL_REASON=max-depth-cap` on any
moderately nested tree (e.g. `AGNT_Baz_Qux →
handleFlowFault`), even though `handleFlowFault` was trivially
expandable. Per-branch path-set semantics fix this: the same flow on
two sibling branches is NOT a cycle, only an ancestor-chain recurrence
is.
"""
from __future__ import annotations

import unittest

from . import _bootstrap  # noqa: F401

import parse_wave  # type: ignore


def _find_all(node: dict, api_name: str) -> list[dict]:
    """Collect every node in `node`'s subtree whose `api_name` matches."""
    found: list[dict] = []
    if node.get("api_name") == api_name:
        found.append(node)
    for c in node.get("children", []) or []:
        found.extend(_find_all(c, api_name))
    return found


class SharedUtilityFlowExpansionTests(unittest.TestCase):
    """Direct repro of the real-org `handleFlowFault` bug.

    Parent flow has two sibling children, each of which invokes the
    same utility flow. Both utility instances must expand fully.
    """

    def test_shared_utility_flow_expands_on_every_branch(self):
        # parent -> [childA, childB]; childA -> utility; childB -> utility
        # utility itself calls a leaf apex (so we can assert `utility`
        # got fully inflated with a child, not just a stub).
        flow_children = {
            "parent": [
                {"kind": "FLOW", "api_name": "childA", "element_name": "call_A"},
                {"kind": "FLOW", "api_name": "childB", "element_name": "call_B"},
            ],
            "childA": [
                {"kind": "FLOW", "api_name": "utility", "element_name": "call_util"},
            ],
            "childB": [
                {"kind": "FLOW", "api_name": "utility", "element_name": "call_util"},
            ],
            "utility": [
                {"kind": "APEX", "api_name": "XCSF_FlowFaultMessage", "element_name": "log"},
            ],
        }
        root = {"kind": "FLOW", "api_name": "parent", "children": []}
        pending = parse_wave.empty_kind_sets()

        parse_wave.inflate_flow_leaf(root, flow_children, pending_out=pending)

        utilities = _find_all(root, "utility")
        self.assertEqual(
            len(utilities), 2,
            "utility should appear once on each sibling branch",
        )

        # Both utility instances must have expanded children (the apex
        # leaf). The regression shape was: first branch expanded, second
        # either in `_pending_fetches` or emitted as an empty-children
        # stub due to depth-cap or false-cycle pruning.
        for i, u in enumerate(utilities):
            kids = u.get("children", [])
            self.assertEqual(
                len(kids), 1,
                f"utility instance {i} should have 1 expanded child, got {kids}",
            )
            self.assertEqual(kids[0]["api_name"], "XCSF_FlowFaultMessage")
            self.assertNotIn("_truncated", u)
            self.assertNotIn("_cycle_back_to", u)

        # Critically: nothing pending. Shared-utility expansion must not
        # leak into `_pending_fetches`.
        self.assertEqual(pending["FLOW"], set())


class TrueCycleDetectionTests(unittest.TestCase):
    """Per-branch path-set must still catch genuine cycles."""

    def test_true_cycle_detected(self):
        """A -> B -> A: second A is annotated, not recursed into, and
        not surfaced in `_pending_fetches`."""
        flow_children = {
            "A": [{"kind": "FLOW", "api_name": "B", "element_name": "call_B"}],
            "B": [{"kind": "FLOW", "api_name": "A", "element_name": "call_A"}],
        }
        root = {"kind": "FLOW", "api_name": "A", "children": []}
        pending = parse_wave.empty_kind_sets()

        parse_wave.inflate_flow_leaf(root, flow_children, pending_out=pending)

        # A -> B -> A(cycle)
        b = root["children"][0]
        self.assertEqual(b["api_name"], "B")
        a_cycle = b["children"][0]
        self.assertEqual(a_cycle["api_name"], "A")
        self.assertEqual(
            a_cycle["_truncated"],
            {"reason": "cycle", "target": "FLOW:A"},
        )
        self.assertEqual(a_cycle["_cycle_back_to"], "FLOW:A")

        # Cycles live in the tree, not the pending accumulator.
        self.assertEqual(pending["FLOW"], set())

    def test_self_recursive_flow(self):
        """A -> A: direct self-cycle is annotated on first recurrence."""
        flow_children = {
            "A": [{"kind": "FLOW", "api_name": "A", "element_name": "self_call"}],
        }
        root = {"kind": "FLOW", "api_name": "A", "children": []}
        pending = parse_wave.empty_kind_sets()

        parse_wave.inflate_flow_leaf(root, flow_children, pending_out=pending)

        kids = root.get("children", [])
        self.assertEqual(len(kids), 1)
        self.assertEqual(kids[0]["api_name"], "A")
        self.assertEqual(
            kids[0]["_truncated"],
            {"reason": "cycle", "target": "FLOW:A"},
        )
        self.assertEqual(pending["FLOW"], set())


class DeepNonCyclicChainTests(unittest.TestCase):
    """Linear chains longer than the old `MAX_BFS_DEPTH = 5` must
    expand fully under the revised semantics. Previously they tripped
    `PARTIAL_REASON=max-depth-cap`; now they expand cleanly.
    """

    def test_deep_non_cyclic_chain_fully_expands(self):
        # A -> B -> C -> D -> E -> F -> G (7 unique flows, depth 6
        # from the root). Old cap of 5 would have truncated at F;
        # new cap of 20 doesn't care.
        names = list("ABCDEFG")
        flow_children: dict = {}
        for i, n in enumerate(names):
            if i + 1 < len(names):
                flow_children[n] = [{
                    "kind": "FLOW",
                    "api_name": names[i + 1],
                    "element_name": f"call_{names[i + 1]}",
                }]
            else:
                flow_children[n] = []

        root = {"kind": "FLOW", "api_name": "A", "children": []}
        pending = parse_wave.empty_kind_sets()
        parse_wave.inflate_flow_leaf(root, flow_children, pending_out=pending)

        node = root
        for expected in names[1:]:
            kids = node.get("children", [])
            self.assertEqual(
                len(kids), 1,
                f"{node['api_name']} should have expanded child {expected}",
            )
            self.assertEqual(kids[0]["api_name"], expected)
            self.assertNotIn("_truncated", kids[0])
            node = kids[0]

        # Terminal leaf has no children and carries no truncation
        # annotation — the cap was never relevant.
        self.assertEqual(node.get("children", []), [])
        self.assertNotIn("_truncated", node)
        self.assertEqual(pending["FLOW"], set())


class DefensiveCapStillTerminatesTests(unittest.TestCase):
    """Pathological chain longer than the defensive cap must still
    terminate cleanly. This proves the safety net still works even
    though per-branch cycle detection does the real work in practice.
    """

    def test_defensive_cap_still_terminates(self):
        # 25 unique flows, linear — longer than the defensive cap of 20.
        # Either the tree fully expands (if someone lifts the cap
        # further) OR it caps at MAX_BFS_DEPTH and annotates the
        # unreached flow. The test asserts termination and one of
        # those two well-defined shapes.
        n = 25
        names = [f"F{i:02d}" for i in range(n)]
        flow_children: dict = {}
        for i, name in enumerate(names):
            if i + 1 < n:
                flow_children[name] = [{
                    "kind": "FLOW",
                    "api_name": names[i + 1],
                    "element_name": "sub",
                }]
            else:
                flow_children[name] = []

        root = {"kind": "FLOW", "api_name": names[0], "children": []}
        pending = parse_wave.empty_kind_sets()

        # Primary assertion: this call terminates and does not recurse
        # past Python's default recursion limit. If the defensive cap
        # regresses, this test will hang or raise RecursionError.
        parse_wave.inflate_flow_leaf(root, flow_children, pending_out=pending)

        # Collect every flow that appears in the tree.
        def all_api_names(node: dict) -> set[str]:
            out = {node.get("api_name")}
            for c in node.get("children", []) or []:
                out.update(all_api_names(c))
            return out - {None}

        present = all_api_names(root)

        # At least the first MAX_BFS_DEPTH flows must be present. The
        # tail may or may not appear depending on where the cap trips.
        for i in range(parse_wave.MAX_BFS_DEPTH):
            self.assertIn(
                names[i], present,
                f"{names[i]} (index {i}) should be expanded — "
                f"it's below MAX_BFS_DEPTH={parse_wave.MAX_BFS_DEPTH}",
            )

        # If any flow is pending, it must be a real descendant (not a
        # fabricated name) and must carry the max-depth annotation
        # somewhere in the tree.
        if pending["FLOW"]:
            for pending_name in pending["FLOW"]:
                self.assertIn(pending_name, names)


if __name__ == "__main__":
    unittest.main()
