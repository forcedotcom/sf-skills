"""Tests for ``parse_wave`` classifiers + BFS step helper.

Targets the high-density branch surface in ``classify_bundle_action``
(Flow / Apex / PromptTemplate / StandardAction / Unknown) and
``classify_action_call`` (apex / generatePromptResponse / other / empty).
Plus the central ``bfs_step`` helper that drives wave-level fetches.
"""
from __future__ import annotations

import unittest

from . import _bootstrap  # noqa: F401  — sys.path setup

import parse_wave  # type: ignore


# -----------------------------------------------------------------------------
# classify_bundle_action — every branch
# -----------------------------------------------------------------------------


class ClassifyBundleActionTests(unittest.TestCase):

    def test_no_target_returns_none_pair(self):
        unwraps, leaf = parse_wave.classify_bundle_action({
            "invocationTarget": "",
            "invocationTargetType": "flow",
        })
        self.assertIsNone(unwraps)
        self.assertIsNone(leaf)

    def test_flow_branch(self):
        unwraps, leaf = parse_wave.classify_bundle_action({
            "invocationTarget": "MyFlow",
            "invocationTargetType": "flow",
        })
        self.assertEqual(unwraps["kind"], "FLOW")
        self.assertEqual(unwraps["api_name"], "MyFlow")
        self.assertEqual(leaf["children"], [])

    def test_apex_branch(self):
        unwraps, leaf = parse_wave.classify_bundle_action({
            "invocationTarget": "MyClass.method",
            "invocationTargetType": "apex",
        })
        self.assertEqual(unwraps["kind"], "APEX")
        self.assertEqual(leaf["api_name"], "MyClass.method")

    def test_prompt_template_via_generatepromptresponse(self):
        unwraps, _ = parse_wave.classify_bundle_action({
            "invocationTarget": "MyPrompt",
            "invocationTargetType": "generatepromptresponse",
        })
        self.assertEqual(unwraps["kind"], "PROMPT_TEMPLATE")

    def test_prompt_template_via_prompt_prefix(self):
        unwraps, _ = parse_wave.classify_bundle_action({
            "invocationTarget": "MyPrompt",
            "invocationTargetType": "prompt-template",
        })
        self.assertEqual(unwraps["kind"], "PROMPT_TEMPLATE")

    def test_prompt_template_via_genai_prefix(self):
        unwraps, _ = parse_wave.classify_bundle_action({
            "invocationTarget": "MyPrompt",
            "invocationTargetType": "genaifunction",
        })
        self.assertEqual(unwraps["kind"], "PROMPT_TEMPLATE")

    def test_standard_invocable_action_branch(self):
        unwraps, leaf = parse_wave.classify_bundle_action({
            "invocationTarget": "createRecord",
            "invocationTargetType": "standardinvocableaction",
        })
        self.assertEqual(unwraps["kind"], "STANDARD_ACTION")
        self.assertEqual(unwraps["invocation_type"], "standardinvocableaction")
        self.assertEqual(leaf["api_name"], "createRecord")

    def test_unknown_action_type_falls_to_unknown(self):
        unwraps, leaf = parse_wave.classify_bundle_action({
            "invocationTarget": "MysteryAction",
            "invocationTargetType": "MYSTERY",
        })
        self.assertEqual(unwraps["kind"], "UNKNOWN")
        self.assertEqual(unwraps["invocation_type"], "mystery")  # lowercased
        self.assertEqual(leaf["kind"], "UNKNOWN")

    def test_invocationTargetType_missing_normalizes_to_empty_string(self):
        unwraps, _ = parse_wave.classify_bundle_action({
            "invocationTarget": "MyAction",
            # no invocationTargetType — coerced to ""
        })
        self.assertEqual(unwraps["kind"], "UNKNOWN")
        self.assertEqual(unwraps["invocation_type"], "")


# -----------------------------------------------------------------------------
# classify_action_call — every branch
# -----------------------------------------------------------------------------


class ClassifyActionCallTests(unittest.TestCase):

    def test_apex_branch(self):
        out = parse_wave.classify_action_call("apex", "MyClass", "callA")
        self.assertEqual(out["kind"], "APEX")
        self.assertEqual(out["api_name"], "MyClass")
        self.assertEqual(out["element_name"], "callA")

    def test_generate_prompt_response_branch(self):
        out = parse_wave.classify_action_call(
            "generatePromptResponse", "MyPrompt", "callB",
        )
        self.assertEqual(out["kind"], "PROMPT_TEMPLATE")
        self.assertEqual(out["api_name"], "MyPrompt")

    def test_other_action_type_falls_to_standard_action(self):
        out = parse_wave.classify_action_call("emailAlert", "MyAlert", "callC")
        self.assertEqual(out["kind"], "STANDARD_ACTION")
        self.assertEqual(out["invocation_type"], "emailAlert")
        self.assertEqual(out["api_name"], "MyAlert")

    def test_other_action_type_uses_action_type_when_name_missing(self):
        out = parse_wave.classify_action_call("emailAlert", "", "callC")
        self.assertEqual(out["api_name"], "emailAlert")

    def test_empty_action_type_falls_to_unknown(self):
        out = parse_wave.classify_action_call("", "MyName", "callD")
        self.assertEqual(out["kind"], "UNKNOWN")
        self.assertEqual(out["api_name"], "MyName")

    def test_unknown_with_no_name_falls_to_question_mark(self):
        out = parse_wave.classify_action_call("", "", "callE")
        self.assertEqual(out["api_name"], "?")


# -----------------------------------------------------------------------------
# bfs_step — pure helper
# -----------------------------------------------------------------------------


class BfsStepTests(unittest.TestCase):

    def test_new_refs_added_to_pending(self):
        pending = parse_wave.empty_kind_sets()
        visited = parse_wave.empty_kind_sets()
        new_refs = {
            "FLOW": {"FlowA", "FlowB"},
            "APEX": {"ApexA"},
            "PROMPT_TEMPLATE": set(),
            "STANDARD_ACTION": set(),
        }
        merged, cycles = parse_wave.bfs_step(pending, visited, new_refs)
        self.assertEqual(merged["FLOW"], {"FlowA", "FlowB"})
        self.assertEqual(merged["APEX"], {"ApexA"})
        self.assertEqual(cycles, [])

    def test_visited_refs_recorded_as_cycles(self):
        pending = parse_wave.empty_kind_sets()
        visited = parse_wave.empty_kind_sets()
        visited["FLOW"].add("FlowA")
        new_refs = {
            "FLOW": {"FlowA", "FlowB"},
            "APEX": set(), "PROMPT_TEMPLATE": set(), "STANDARD_ACTION": set(),
        }
        merged, cycles = parse_wave.bfs_step(pending, visited, new_refs)
        self.assertEqual(merged["FLOW"], {"FlowB"})
        self.assertIn(("FLOW", "FlowA"), cycles)

    def test_cross_kind_same_name_stays_distinct(self):
        pending = parse_wave.empty_kind_sets()
        visited = parse_wave.empty_kind_sets()
        new_refs = {
            "FLOW": {"Foo"}, "APEX": {"Foo"},
            "PROMPT_TEMPLATE": set(), "STANDARD_ACTION": set(),
        }
        merged, _ = parse_wave.bfs_step(pending, visited, new_refs)
        self.assertEqual(merged["FLOW"], {"Foo"})
        self.assertEqual(merged["APEX"], {"Foo"})

    def test_existing_pending_preserved_via_merge(self):
        pending = parse_wave.empty_kind_sets()
        pending["FLOW"].add("FlowExisting")
        visited = parse_wave.empty_kind_sets()
        new_refs = {
            "FLOW": {"FlowNew"},
            "APEX": set(), "PROMPT_TEMPLATE": set(), "STANDARD_ACTION": set(),
        }
        merged, _ = parse_wave.bfs_step(pending, visited, new_refs)
        self.assertEqual(merged["FLOW"], {"FlowExisting", "FlowNew"})

    def test_unknown_kind_raises(self):
        pending = parse_wave.empty_kind_sets()
        visited = parse_wave.empty_kind_sets()
        with self.assertRaises(ValueError) as ctx:
            parse_wave.bfs_step(
                pending, visited,
                {"BOGUS_KIND": {"x"}},
            )
        self.assertIn("unknown BFS kind", str(ctx.exception))


# -----------------------------------------------------------------------------
# empty_kind_sets — fresh dict per call
# -----------------------------------------------------------------------------


class EmptyKindSetsTests(unittest.TestCase):

    def test_returns_one_set_per_BFS_KIND(self):
        out = parse_wave.empty_kind_sets()
        self.assertEqual(set(out.keys()), set(parse_wave.BFS_KINDS))
        for v in out.values():
            self.assertEqual(v, set())

    def test_each_call_returns_fresh_dict(self):
        a = parse_wave.empty_kind_sets()
        a["FLOW"].add("x")
        b = parse_wave.empty_kind_sets()
        self.assertEqual(b["FLOW"], set())


if __name__ == "__main__":
    unittest.main()
