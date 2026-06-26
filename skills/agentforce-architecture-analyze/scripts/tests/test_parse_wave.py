"""Tests for parse_wave BFS + inflate uses (kind, canonical_name)
tuple-keyed visited tracking. A flat per-name visited set would silently
drop the second of two same-named different-kind nodes (Flow Foo + Apex Foo),
and would infinite-loop / depth-cap on self-cycles without annotation.
"""
from __future__ import annotations

import unittest

from . import _bootstrap  # noqa: F401

import parse_wave  # type: ignore


class BfsStepTupleKeyingTests(unittest.TestCase):
    """Same-name, different-kind refs must not collide."""

    def test_flow_and_apex_same_name_are_distinct(self):
        pending = {k: set() for k in parse_wave._BFS_KINDS}
        visited = {k: set() for k in parse_wave._BFS_KINDS}
        new_refs = {"FLOW": {"Foo"}, "APEX": {"Foo"}}

        merged, cycles = parse_wave.bfs_step(pending, visited, new_refs)

        self.assertIn("Foo", merged["FLOW"])
        self.assertIn("Foo", merged["APEX"])
        self.assertEqual(cycles, [])

    def test_already_visited_ref_skipped_and_recorded_as_cycle(self):
        pending = {k: set() for k in parse_wave._BFS_KINDS}
        visited = {k: set() for k in parse_wave._BFS_KINDS}
        visited["FLOW"] = {"Foo"}  # simulate prior wave visit
        new_refs = {"FLOW": {"Foo", "Bar"}}

        merged, cycles = parse_wave.bfs_step(pending, visited, new_refs)

        self.assertNotIn("Foo", merged["FLOW"])  # filtered out
        self.assertIn("Bar", merged["FLOW"])
        self.assertIn(("FLOW", "Foo"), cycles)

    def test_cross_type_cycle_is_distinct(self):
        """Flow Foo visited does not mask Apex Foo on the same wave."""
        pending = {k: set() for k in parse_wave._BFS_KINDS}
        visited = {k: set() for k in parse_wave._BFS_KINDS}
        visited["FLOW"] = {"Foo"}
        new_refs = {"FLOW": {"Foo"}, "APEX": {"Foo"}}

        merged, cycles = parse_wave.bfs_step(pending, visited, new_refs)

        self.assertEqual(merged["FLOW"], set())  # Foo is visited
        self.assertEqual(merged["APEX"], {"Foo"})  # distinct kind → keeps
        self.assertIn(("FLOW", "Foo"), cycles)
        self.assertNotIn(("APEX", "Foo"), cycles)

    def test_empty_initial_pending_terminates(self):
        pending = {k: set() for k in parse_wave._BFS_KINDS}
        visited = {k: set() for k in parse_wave._BFS_KINDS}
        merged, cycles = parse_wave.bfs_step(pending, visited, {})
        self.assertEqual(cycles, [])
        for k in parse_wave._BFS_KINDS:
            self.assertEqual(merged[k], set())

    def test_unknown_kind_raises(self):
        """unknown BFS kinds raise ValueError — bfs_step is an
        internal API and a typo in a caller is a programming error, not a
        runtime condition we can silently paper over. Silent-drop produced
        false confidence: the ref was never fetched and no log mentioned it.
        """
        pending = {k: set() for k in parse_wave._BFS_KINDS}
        visited = {k: set() for k in parse_wave._BFS_KINDS}
        new_refs = {"NOT_A_KIND": {"X"}}

        with self.assertRaises(ValueError) as ctx:
            parse_wave.bfs_step(pending, visited, new_refs)

        self.assertIn("unknown BFS kind", ctx.exception.args[0])


class InflateCycleDetectionTests(unittest.TestCase):
    """`inflate_flow_leaf` must terminate on self-cycles and annotate
    `_cycle_back_to` on the repeat node."""

    def test_self_cycle_flow_a_calls_subflow_a(self):
        """Flow A → subflow A — one real node + a stub child with cycle tag."""
        flow_children = {
            "A": [
                {"kind": "FLOW", "element_name": "recurse", "api_name": "A"},
            ],
        }
        leaf = {"kind": "FLOW", "api_name": "A", "children": []}

        parse_wave.inflate_flow_leaf(leaf, flow_children)

        self.assertEqual(len(leaf["children"]), 1)
        child = leaf["children"][0]
        self.assertEqual(child["kind"], "FLOW")
        self.assertEqual(child["api_name"], "A")
        self.assertEqual(child.get("_cycle_back_to"), "FLOW:A")
        # Must NOT have expanded children on the cycle stub.
        self.assertEqual(child.get("children", []), [])

    def test_cross_type_cycle_flow_a_to_apex_b_to_flow_a(self):
        """Flow A → Apex B (leaf) → nothing (Apex doesn't recurse in inflate).

        The inflate layer only descends through FLOW→FLOW. A cycle through
        Apex would be caught at the BFS layer (bfs_step), not here. This
        test confirms the inflate layer doesn't misclassify a FLOW→APEX
        edge as a cycle and doesn't over-recurse on it.
        """
        flow_children = {
            "A": [
                {"kind": "APEX", "element_name": "callApex", "api_name": "B"},
            ],
        }
        leaf = {"kind": "FLOW", "api_name": "A", "children": []}

        parse_wave.inflate_flow_leaf(leaf, flow_children)

        self.assertEqual(len(leaf["children"]), 1)
        self.assertEqual(leaf["children"][0]["kind"], "APEX")
        self.assertNotIn("_cycle_back_to", leaf["children"][0])

    def test_three_layer_linear_graph_fully_expanded(self):
        """A → B → C — each Flow visited once, no false cycle tags."""
        flow_children = {
            "A": [{"kind": "FLOW", "element_name": "callB", "api_name": "B"}],
            "B": [{"kind": "FLOW", "element_name": "callC", "api_name": "C"}],
            "C": [],
        }
        leaf = {"kind": "FLOW", "api_name": "A", "children": []}

        parse_wave.inflate_flow_leaf(leaf, flow_children)

        # A has one child: B
        self.assertEqual(len(leaf["children"]), 1)
        b = leaf["children"][0]
        self.assertEqual(b["api_name"], "B")
        self.assertNotIn("_cycle_back_to", b)
        # B has one child: C
        self.assertEqual(len(b["children"]), 1)
        c = b["children"][0]
        self.assertEqual(c["api_name"], "C")
        self.assertNotIn("_cycle_back_to", c)
        # C has no children (empty list in flow_children)
        self.assertEqual(c.get("children", []), [])

    def test_sibling_flows_sharing_target_not_cross_contaminated(self):
        """If Flow X is called by two different siblings, both sibling
        branches must fully expand X — not prune the second as a cycle.

        Frozenset path-visited semantics protect this: siblings don't see
        each other's descent. A mutable shared set would cause the second
        sibling to treat X as a cycle.
        """
        flow_children = {
            "Root": [
                {"kind": "FLOW", "element_name": "a", "api_name": "Sib1"},
                {"kind": "FLOW", "element_name": "b", "api_name": "Sib2"},
            ],
            "Sib1": [{"kind": "FLOW", "element_name": "shared", "api_name": "Shared"}],
            "Sib2": [{"kind": "FLOW", "element_name": "shared", "api_name": "Shared"}],
            "Shared": [],
        }
        leaf = {"kind": "FLOW", "api_name": "Root", "children": []}

        parse_wave.inflate_flow_leaf(leaf, flow_children)

        self.assertEqual(len(leaf["children"]), 2)
        for sib in leaf["children"]:
            # Each sibling must have Shared as a fully-expanded child —
            # NOT a cycle stub.
            self.assertEqual(len(sib["children"]), 1)
            shared = sib["children"][0]
            self.assertEqual(shared["api_name"], "Shared")
            self.assertNotIn("_cycle_back_to", shared)

    def test_empty_flow_children_returns_immediately(self):
        """No data for this leaf → preserve existing children (no-op)."""
        leaf = {"kind": "FLOW", "api_name": "X", "children": [{"kind": "APEX", "api_name": "Y"}]}
        parse_wave.inflate_flow_leaf(leaf, {})  # empty map
        # Preserved unchanged
        self.assertEqual(leaf["children"], [{"kind": "APEX", "api_name": "Y"}])

    def test_non_flow_leaf_ignored(self):
        """Only FLOW kind is inflated."""
        leaf = {"kind": "APEX", "api_name": "X"}
        parse_wave.inflate_flow_leaf(leaf, {"X": [{"kind": "FLOW", "api_name": "Z"}]})
        self.assertNotIn("children", leaf)


class CycleKeyTests(unittest.TestCase):
    """Unit test for the tuple-key helper — safety net on schema drift."""

    def test_tuple_shape(self):
        self.assertEqual(
            parse_wave._cycle_key({"kind": "FLOW", "api_name": "Foo"}),
            ("FLOW", "Foo"),
        )

    def test_missing_kind_or_name_safe(self):
        self.assertEqual(parse_wave._cycle_key({}), ("", ""))


def _linear_flow_chain(names: list[str]) -> dict:
    """Build a flow_children graph: FLOW[i] → FLOW[i+1], last flow has no kids.

    Returns the `flow_children` mapping that inflate_flow_leaf consumes.
    """
    graph: dict = {}
    for i, n in enumerate(names):
        if i + 1 < len(names):
            graph[n] = [
                {"kind": "FLOW", "element_name": f"call_{names[i+1]}",
                 "api_name": names[i+1]},
            ]
        else:
            graph[n] = []
    return graph


class DepthCapPartialTests(unittest.TestCase):
    """`MAX_BFS_DEPTH` is a defensive guard,
    not a functional chain-depth limit. Fixtures here push past the cap
    to prove it still terminates and still populates `pending_out` when
    it trips. Cycle semantics live in per-branch ancestor tracking and
    are covered by `test_per_branch_visited.py`.
    """

    def _deep_linear_names(self, n: int) -> list[str]:
        return [f"F{i}" for i in range(1, n + 1)]

    def test_chain_under_cap_fully_expanded(self):
        """A linear chain shorter than `MAX_BFS_DEPTH` fully expands with
        no pending. Prior to the revision this used a 5-flow chain; with
        a defensive cap of 20, 5 is trivially under-cap but the shape of
        the assertion is unchanged.
        """
        names = ["F1", "F2", "F3", "F4", "F5"]
        graph = _linear_flow_chain(names)
        leaf = {"kind": "FLOW", "api_name": "F1", "children": []}
        pending: dict[str, set[str]] = {k: set() for k in parse_wave._BFS_KINDS}

        parse_wave.inflate_flow_leaf(leaf, graph, pending_out=pending)

        node = leaf
        for expected in names[1:]:
            kids = node.get("children", [])
            self.assertEqual(len(kids), 1, f"expected one child under {node['api_name']}")
            self.assertEqual(kids[0]["api_name"], expected)
            node = kids[0]
        self.assertEqual(node.get("children", []), [])

        for k in parse_wave._BFS_KINDS:
            self.assertEqual(pending[k], set())

    def test_chain_at_exact_cap_trips_and_records_pending(self):
        """A linear chain of MAX_BFS_DEPTH+1 unique flows trips the
        defensive cap: the last flow must NOT be expanded AND must land
        in `pending_out["FLOW"]`. This is the only functional invariant
        of the cap after the revision.
        """
        n = parse_wave.MAX_BFS_DEPTH + 1
        names = self._deep_linear_names(n)
        graph = _linear_flow_chain(names)
        leaf = {"kind": "FLOW", "api_name": names[0], "children": []}
        pending: dict[str, set[str]] = {k: set() for k in parse_wave._BFS_KINDS}

        parse_wave.inflate_flow_leaf(leaf, graph, pending_out=pending)

        # Walk down to the flow at `MAX_BFS_DEPTH - 1` index (last one
        # before the cap trips on its child). All prior flows must have
        # been fully expanded.
        node = leaf
        for expected in names[1:parse_wave.MAX_BFS_DEPTH]:
            kids = node.get("children", [])
            self.assertEqual(len(kids), 1)
            self.assertEqual(kids[0]["api_name"], expected)
            node = kids[0]

        # The last flow in the chain (the (MAX_BFS_DEPTH+1)-th) must be
        # in pending_out.
        self.assertIn(names[-1], pending["FLOW"])

    def test_deep_chain_with_tail_self_loop_terminates_via_cycle_detection(self):
        """Long chain with a self-loop at the tail terminates via
        per-branch cycle detection (the revised primitive), NOT the
        defensive cap. The self-loop flow appears once with children
        expanded, its self-reference annotated `_cycle_back_to`.
        """
        # Chain of 7 unique flows, each pointing to the next, then the
        # last one points at itself — 7 is well under the cap of 20 so
        # this proves cycle detection, not depth, terminates the walk.
        names = ["F1", "F2", "F3", "F4", "F5", "F6", "F7"]
        graph = _linear_flow_chain(names)
        # Rewrite F7 to self-loop instead of empty.
        graph["F7"] = [{"kind": "FLOW", "api_name": "F7", "element_name": "self"}]

        leaf = {"kind": "FLOW", "api_name": "F1", "children": []}
        pending: dict[str, set[str]] = {k: set() for k in parse_wave._BFS_KINDS}

        # Must not hang / recurse infinitely.
        parse_wave.inflate_flow_leaf(leaf, graph, pending_out=pending)

        # Walk to F7.
        node = leaf
        for expected in names[1:]:
            node = node["children"][0]
            self.assertEqual(node["api_name"], expected)

        # F7 has ONE child — the cycle-annotated self-reference.
        f7_kids = node.get("children", [])
        self.assertEqual(len(f7_kids), 1)
        self.assertEqual(f7_kids[0]["api_name"], "F7")
        self.assertEqual(f7_kids[0]["_cycle_back_to"], "FLOW:F7")
        self.assertEqual(
            f7_kids[0]["_truncated"],
            {"reason": "cycle", "target": "FLOW:F7"},
        )

        # Nothing in pending — cycle is annotated, not pended.
        self.assertEqual(pending["FLOW"], set())

    def test_chain_under_cap_with_legacy_pending_none(self):
        """Callers pre-dating pass no `pending_out`. An under-cap
        chain still expands fully — no crash on `None`, no spurious
        truncation. The pre-revision form of this test asserted cap=5
        behavior; now it asserts that a short chain expands cleanly when
        the cap plays no role.
        """
        names = ["F1", "F2", "F3", "F4", "F5", "F6"]
        graph = _linear_flow_chain(names)
        leaf = {"kind": "FLOW", "api_name": "F1", "children": []}

        # No pending_out — legacy call shape. Must not crash.
        parse_wave.inflate_flow_leaf(leaf, graph)

        # All flows expanded to the terminal leaf.
        node = leaf
        for expected in names[1:]:
            kids = node.get("children", [])
            self.assertEqual(len(kids), 1, f"{node['api_name']} should have one child")
            self.assertEqual(kids[0]["api_name"], expected)
            node = kids[0]
        self.assertEqual(node.get("children", []), [])

    def test_partial_and_unresolved_coexist(self):
        """_unresolved + _partial-reason must both be reported.

        Simulate: finalize_cap drains some pending into _unresolved, but
        depth-cap already set _partial_reason=max-depth-cap. Finalize must
        NOT clobber the depth-cap reason.
        """
        tree = {
            "_partial": True,
            "_partial_reason": "max-depth-cap",
            "_pending_fetches": {
                "FLOW": ["LateFlow"],
                "APEX": [],
                "PROMPT_TEMPLATE": [],
                "STANDARD_ACTION": [],
            },
            "_unresolved": [{"kind": "APEX", "api_name": "PriorUnresolved",
                             "reason": "resolve_invocation_target failed"}],
        }

        parse_wave.finalize_cap(tree)

        # Pending drained into unresolved.
        self.assertEqual(tree["_pending_fetches"]["FLOW"], [])
        self.assertEqual(len(tree["_unresolved"]), 2)
        # Depth-cap reason preserved (NOT overwritten by max-wave-depth).
        self.assertEqual(tree["_partial_reason"], "max-depth-cap")
        self.assertTrue(tree["_partial"])


class MaxBfsDepthConstantTests(unittest.TestCase):
    """`MAX_BFS_DEPTH` is a defensive guard,
    not a functional chain-depth limit. The constant must match
    `scripts/config.py::MAX_BFS_DEPTH` exactly (duplicated intentionally
    — see comment there on the "no intra-skill imports" convention).
    """

    def test_max_bfs_depth_matches_config(self):
        """Cross-module consistency. If someone bumps one literal they
        must bump the other."""
        import config  # type: ignore
        self.assertEqual(parse_wave.MAX_BFS_DEPTH, config.MAX_BFS_DEPTH)

    def test_max_bfs_depth_is_defensive_not_functional(self):
        """The cap should be comfortably larger than any realistic
        production flow-chain depth, so that per-branch cycle detection
        — not the cap — terminates the walk in practice. `>= 15` is a
        loose sanity bound; if someone quietly tightens it below 15
        they're probably reintroducing the shared-utility-flow bug."""
        self.assertGreaterEqual(parse_wave.MAX_BFS_DEPTH, 15)

    def test_legacy_alias_tracks_new_constant(self):
        """MAX_INFLATE_DEPTH is retained as an alias."""
        self.assertEqual(parse_wave.MAX_INFLATE_DEPTH, parse_wave.MAX_BFS_DEPTH)


class PublicSymbolPromotionTests(unittest.TestCase):
    """`_BFS_KINDS` and `_empty_kind_sets` were
    promoted to public names (`BFS_KINDS`, `empty_kind_sets`) so the
    in-process `main.py` orchestrator doesn't have to reach across the
    leading-underscore boundary that closed for `redact_text`.
    The underscore forms remain as deprecated aliases for one more minor
    version.
    """

    def test_public_bfs_kinds_importable(self):
        """`parse_wave.BFS_KINDS` exists, is a tuple, and carries the
        expected four tokens in the same order as before promotion.
        """
        self.assertTrue(hasattr(parse_wave, "BFS_KINDS"))
        self.assertIsInstance(parse_wave.BFS_KINDS, tuple)
        self.assertEqual(
            parse_wave.BFS_KINDS,
            ("FLOW", "APEX", "PROMPT_TEMPLATE", "STANDARD_ACTION"),
        )

    def test_public_empty_kind_sets_importable_and_callable(self):
        """`parse_wave.empty_kind_sets()` returns a fresh {kind: set()}
        mapping keyed by every BFS_KINDS entry. Each call yields an
        independent dict — callers must not share buckets across waves.
        """
        self.assertTrue(hasattr(parse_wave, "empty_kind_sets"))
        d1 = parse_wave.empty_kind_sets()
        d2 = parse_wave.empty_kind_sets()
        self.assertEqual(set(d1.keys()), set(parse_wave.BFS_KINDS))
        for kind in parse_wave.BFS_KINDS:
            self.assertEqual(d1[kind], set())
        # Independence: mutating one must not affect the other.
        d1["FLOW"].add("X")
        self.assertEqual(d2["FLOW"], set())

    def test_underscore_aliases_still_work_for_backcompat(self):
        """Legacy `_BFS_KINDS` / `_empty_kind_sets` imports continue to
        resolve. They are deprecated but not yet removed — existing
        tests and any external callers must keep working through the
        migration window.
        """
        self.assertTrue(hasattr(parse_wave, "_BFS_KINDS"))
        self.assertTrue(hasattr(parse_wave, "_empty_kind_sets"))
        # Same object (alias, not a copy) so equality holds structurally.
        self.assertIs(parse_wave._BFS_KINDS, parse_wave.BFS_KINDS)
        self.assertIs(parse_wave._empty_kind_sets, parse_wave.empty_kind_sets)


class FetchableKindsTests(unittest.TestCase):
    """STANDARD_ACTION is declared-only, never fetched.
    Must stay out of `_pending_fetches` even though it remains a BFS kind
    for tree counts + visited dedup."""

    def test_fetchable_kinds_excludes_standard_action(self):
        """FETCHABLE_KINDS = (FLOW, APEX, PROMPT_TEMPLATE). STANDARD_ACTION
        must be in BFS_KINDS (tree bookkeeping) but NOT in
        FETCHABLE_KINDS (body-fetch eligibility)."""
        self.assertIn("STANDARD_ACTION", parse_wave.BFS_KINDS)
        self.assertNotIn("STANDARD_ACTION", parse_wave.FETCHABLE_KINDS)
        self.assertEqual(
            parse_wave.FETCHABLE_KINDS,
            ("FLOW", "APEX", "PROMPT_TEMPLATE"),
        )

    def test_build_root_children_skips_standard_action_refs(self):
        """A GenAiFunction whose unwrap is STANDARD_ACTION must NOT land
        in new_refs. Before this fix, `streamKnowledgeSearch` landed in
        `new_refs["STANDARD_ACTION"]` → merged into pending → never
        visited → surfaced in _pending_fetches (pollution)."""
        bundle = {
            "topics": [{
                "name": "T",
                "actions": [{
                    "name": "A1",
                    "invocationTarget": "streamKnowledgeSearch",
                    "invocationTargetType": "standardInvocableAction",
                }],
            }],
            "plannerActions": [],
        }
        visited = parse_wave.empty_kind_sets()
        aux_visited: set = set()
        children, new_refs = parse_wave.build_root_children(
            bundle, visited, aux_visited,
        )
        # Children list is built normally — tree still has the leaf.
        self.assertEqual(len(children), 1)
        # But new_refs["STANDARD_ACTION"] is empty → nothing to pend on.
        self.assertEqual(new_refs["STANDARD_ACTION"], set())
        self.assertEqual(new_refs["FLOW"], set())
        self.assertEqual(new_refs["APEX"], set())
        self.assertEqual(new_refs["PROMPT_TEMPLATE"], set())

    def test_build_root_children_still_captures_flow_apex_prompt_refs(self):
        """Positive control — fetchable kinds still accumulate into
        new_refs. The FOLLOWUP-2 gate is on STANDARD_ACTION only."""
        bundle = {
            "topics": [{
                "name": "T",
                "actions": [
                    {"name": "F1", "invocationTarget": "FlowA",
                     "invocationTargetType": "flow"},
                    {"name": "A1", "invocationTarget": "ApexA",
                     "invocationTargetType": "apex"},
                    {"name": "P1", "invocationTarget": "PromptA",
                     "invocationTargetType": "generatePromptResponse"},
                ],
            }],
            "plannerActions": [],
        }
        visited = parse_wave.empty_kind_sets()
        aux_visited: set = set()
        _, new_refs = parse_wave.build_root_children(
            bundle, visited, aux_visited,
        )
        self.assertIn("FlowA", new_refs["FLOW"])
        self.assertIn("ApexA", new_refs["APEX"])
        self.assertIn("PromptA", new_refs["PROMPT_TEMPLATE"])
        self.assertEqual(new_refs["STANDARD_ACTION"], set())


class UnifiedTruncationAnnotationTests(unittest.TestCase):
    """both cycle and max-depth code paths annotate truncated
    nodes with the unified `_truncated = {reason, target}` sub-object.
    `_cycle_back_to` is preserved as a deprecated alias (backcompat)."""

    def test_truncation_constants_are_exposed(self):
        """Public constants let consumers match on strings without
        duplicating the literal values."""
        self.assertEqual(parse_wave.TRUNCATION_CYCLE, "cycle")
        self.assertEqual(parse_wave.TRUNCATION_MAX_DEPTH, "max-depth")
        self.assertIn(
            parse_wave.TRUNCATION_CYCLE, parse_wave.TRUNCATION_REASONS,
        )
        self.assertIn(
            parse_wave.TRUNCATION_MAX_DEPTH, parse_wave.TRUNCATION_REASONS,
        )

    def test_cycle_emits_unified_truncated_and_legacy_alias(self):
        """Cycle annotations carry BOTH the unified `_truncated` and the
        legacy `_cycle_back_to` string (same target). Consumers that
        haven't migrated still work; new consumers read one field."""
        flow_children = {
            # A simple A → A self-cycle inside one expansion.
            "A": [{"kind": "FLOW", "api_name": "A", "element_name": "loop"}],
        }
        leaf = {"kind": "FLOW", "api_name": "A", "children": []}
        parse_wave.inflate_flow_leaf(leaf, flow_children)

        # Find the cycle-annotated child (second encounter of A).
        kids = leaf.get("children") or []
        self.assertEqual(len(kids), 1)
        cycle_node = kids[0]

        # Unified annotation present.
        self.assertIn("_truncated", cycle_node)
        self.assertEqual(
            cycle_node["_truncated"],
            {"reason": "cycle", "target": "FLOW:A"},
        )

        # Legacy annotation still present for backcompat.
        self.assertEqual(cycle_node["_cycle_back_to"], "FLOW:A")

    def test_depth_cap_emits_unified_truncated_on_leaf(self):
        """When MAX_BFS_DEPTH trips, the truncated FLOW leaf picks up
        `_truncated = {reason: 'max-depth', target: 'FLOW:<name>'}`.
        Before the leaf carried no per-node signal at all — only
        the tree-level `_partial_reason` and the `pending_out`
        accumulator identified it.

        2026-05-03: since the cap was bumped from 5 to 20 (defensive
        guard, not functional limit), the chain here is built
        programmatically at `MAX_BFS_DEPTH + 1` unique flows so the
        test tracks the constant instead of hard-coding chain length.
        """
        n = parse_wave.MAX_BFS_DEPTH + 1  # one past the cap
        names = [f"F{i}" for i in range(n)]
        flow_children: dict[str, list[dict]] = {}
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
        pending_out = parse_wave.empty_kind_sets()
        parse_wave.inflate_flow_leaf(root, flow_children, pending_out=pending_out)

        # Walk down the chain to the terminal (unreached) flow.
        def walk(n, name):
            if n.get("api_name") == name:
                return n
            for c in n.get("children") or []:
                found = walk(c, name)
                if found:
                    return found
            return None

        tail = walk(root, names[-1])
        self.assertIsNotNone(tail, f"{names[-1]} should appear as a leaf in the tree")

        # Unified annotation on the depth-capped leaf.
        self.assertIn("_truncated", tail)
        self.assertEqual(
            tail["_truncated"],
            {"reason": "max-depth", "target": f"FLOW:{names[-1]}"},
        )

        # The capped leaf should NOT also carry _cycle_back_to — this
        # is a depth-cap, not a cycle.
        self.assertNotIn("_cycle_back_to", tail)

        # pending_out still picks up the unreached name — existing
        # contract preserved.
        self.assertIn(names[-1], pending_out["FLOW"])

    def test_non_flow_leaf_depth_cap_no_annotation(self):
        """The cap is scoped to FLOW leaves. Non-FLOW leaves at
        cap depth are just no-op returns — no spurious `_truncated`."""
        flow_children = {
            "X": [{"kind": "APEX", "api_name": "SomeApex"}],
        }
        # Build an APEX leaf that we try to "inflate" at depth = MAX.
        # inflate_flow_leaf with a non-FLOW leaf at depth >= MAX does
        # nothing and emits no annotation.
        leaf = {"kind": "APEX", "api_name": "SomeApex"}
        pending_out = parse_wave.empty_kind_sets()
        parse_wave.inflate_flow_leaf(
            leaf, flow_children,
            depth=parse_wave.MAX_BFS_DEPTH,
            pending_out=pending_out,
        )
        self.assertNotIn("_truncated", leaf)
        self.assertEqual(pending_out["FLOW"], set())


if __name__ == "__main__":
    unittest.main()
