"""Tests for Section-7 signature stamping.

Previously, every flow and every Apex class in the rendered architecture
report's Section 7 showed `_Signature not captured._` because Wave B
fetched `SymbolTable` + `Flow.Metadata` but we never projected that data
onto the tree nodes the renderer reads. These tests pin the three
helpers that close the gap:

  * `_derive_apex_signature` — SymbolTable → one-line method signature
  * `_derive_flow_signature` — Flow.Metadata → `in:/out:` param list
  * `_stamp_signatures`     — walks the tree and writes `node["signature"]`

The renderer at `render_architecture.py` reads `node.get("signature")`
already; no renderer change was required.
"""
from __future__ import annotations

import unittest

from . import _bootstrap  # noqa: F401

import main  # type: ignore


# ---------------------------------------------------------------------------
# _derive_apex_signature
# ---------------------------------------------------------------------------


class DeriveApexSignatureTests(unittest.TestCase):
    def test_invocable_method_is_preferred(self):
        """@InvocableMethod is what Flow / Agentforce actually call. If
        present, it MUST be picked over any other method — otherwise the
        rendered signature points at a private helper instead of the
        public entry point."""
        apex_row = {
            "Name": "OrderLookup",
            "SymbolTable": {
                "methods": [
                    {
                        "name": "helper",
                        "returnType": "void",
                        "modifiers": ["private"],
                        "parameters": [{"name": "x", "type": "String"}],
                        "annotations": [],
                    },
                    {
                        "name": "run",
                        "returnType": "List<Result>",
                        "modifiers": ["public", "static"],
                        "parameters": [
                            {"name": "input", "type": "List<Request>"},
                        ],
                        "annotations": [{"name": "InvocableMethod"}],
                    },
                ],
            },
        }
        sig = main._derive_apex_signature(apex_row)
        self.assertEqual(sig, "public static List<Result> run(List<Request> input)")

    def test_no_invocable_falls_back_to_global(self):
        """Without `@InvocableMethod`, a `global` method wins over a
        `private` helper."""
        apex_row = {
            "Name": "Utility",
            "SymbolTable": {
                "methods": [
                    {
                        "name": "privateHelper",
                        "returnType": "void",
                        "modifiers": ["private"],
                        "parameters": [],
                        "annotations": [],
                    },
                    {
                        "name": "publicEntry",
                        "returnType": "String",
                        "modifiers": ["global"],
                        "parameters": [{"name": "id", "type": "Id"}],
                        "annotations": [],
                    },
                ],
            },
        }
        sig = main._derive_apex_signature(apex_row)
        self.assertEqual(sig, "global String publicEntry(Id id)")

    def test_empty_symbol_table_returns_none(self):
        """`SymbolTable = null` is the common case for classes the org
        couldn't compile a symbol table for. Must not raise, must return
        None so the renderer falls back to the `_Signature not captured._`
        placeholder."""
        self.assertIsNone(
            main._derive_apex_signature({"Name": "X", "SymbolTable": None})
        )
        self.assertIsNone(
            main._derive_apex_signature({"Name": "X", "SymbolTable": {}})
        )
        self.assertIsNone(
            main._derive_apex_signature(
                {"Name": "X", "SymbolTable": {"methods": []}}
            )
        )

    def test_no_candidate_methods_returns_none(self):
        """A class whose only method is private AND not invocable has no
        sensible public signature to surface; return None rather than
        expose internal detail."""
        apex_row = {
            "Name": "PrivateOnly",
            "SymbolTable": {
                "methods": [
                    {
                        "name": "hidden",
                        "returnType": "void",
                        "modifiers": ["private"],
                        "parameters": [],
                        "annotations": [],
                    },
                ],
            },
        }
        self.assertIsNone(main._derive_apex_signature(apex_row))


# ---------------------------------------------------------------------------
# _derive_flow_signature
# ---------------------------------------------------------------------------


class DeriveFlowSignatureTests(unittest.TestCase):
    def test_input_and_output_both_present(self):
        """Both sides rendered with ` | ` separator.

        Flow.Metadata exposes a flat `variables[]` list; each item carries
        boolean `isInput` / `isOutput` flags. We partition the list by
        those flags rather than reading the non-existent
        `inputParameters` / `outputParameters` fields.
        """
        record = {
            "Metadata": {
                "variables": [
                    {"name": "caseId", "dataType": "String",
                     "isInput": True, "isOutput": False},
                    {"name": "priority", "dataType": "String",
                     "isInput": True, "isOutput": False},
                    {"name": "result", "dataType": "String",
                     "isInput": False, "isOutput": True},
                ],
            },
        }
        sig = main._derive_flow_signature(record)
        self.assertEqual(
            sig,
            "in: caseId: String, priority: String | out: result: String",
        )

    def test_only_input_side(self):
        """outputs empty → only `in:` side rendered, no trailing ` | `."""
        record = {
            "Metadata": {
                "variables": [
                    {"name": "caseId", "dataType": "String",
                     "isInput": True, "isOutput": False},
                ],
            },
        }
        sig = main._derive_flow_signature(record)
        self.assertEqual(sig, "in: caseId: String")

    def test_no_parameters_returns_none(self):
        """No variables at all → None (render falls back to placeholder)."""
        record = {"Metadata": {"variables": []}}
        self.assertIsNone(main._derive_flow_signature(record))
        self.assertIsNone(main._derive_flow_signature({"Metadata": {}}))
        self.assertIsNone(main._derive_flow_signature({}))

    def test_collection_type_rendered_as_list(self):
        """`isCollection: True` on a variable → `List<DataType>` (and for
        sObject variables, the `objectType` feeds the inner type rather
        than the literal `SObject`; case-insensitive match on
        `dataType`)."""
        record = {
            "Metadata": {
                "variables": [
                    {
                        "name": "ids",
                        "dataType": "String",
                        "isCollection": True,
                        "isInput": True,
                        "isOutput": False,
                    },
                    {
                        "name": "cases",
                        "dataType": "sObject",
                        "objectType": "Case",
                        "isCollection": True,
                        "isInput": True,
                        "isOutput": False,
                    },
                    {
                        "name": "result",
                        "dataType": "SObject",   # upper-case variant
                        "objectType": "Account",
                        "isInput": False,
                        "isOutput": True,
                    },
                ],
            },
        }
        sig = main._derive_flow_signature(record)
        self.assertEqual(
            sig,
            "in: ids: List<String>, cases: List<Case> | out: result: Account",
        )

    def test_round_trip_variable_appears_on_both_sides(self):
        """A variable with `isInput: True` AND `isOutput: True` is a
        round-trip — flows use this for parameters the caller passes in
        and the flow mutates back out. It must appear on BOTH sides of
        the rendered signature."""
        record = {
            "Metadata": {
                "variables": [
                    {"name": "payload", "dataType": "String",
                     "isInput": True, "isOutput": True},
                ],
            },
        }
        sig = main._derive_flow_signature(record)
        self.assertEqual(
            sig,
            "in: payload: String | out: payload: String",
        )

    def test_derive_flow_signature_local_variables_ignored(self):
        """A variable with `isInput: False` AND `isOutput: False` is a
        flow-local — it exists only inside the flow's execution and is
        not part of its public surface. It must not appear in either
        side of the signature."""
        record = {
            "Metadata": {
                "variables": [
                    {"name": "scratch", "dataType": "String",
                     "isInput": False, "isOutput": False},
                    {"name": "caseId", "dataType": "String",
                     "isInput": True, "isOutput": False},
                ],
            },
        }
        sig = main._derive_flow_signature(record)
        self.assertEqual(sig, "in: caseId: String")

    def test_derive_flow_signature_handlefaultfault_shape(self):
        """Real-org fixture modeled on `handleFlowFault` from the
        my-org-alias org: 8 variables → 5 inputs, 3 outputs. Pins the
        exact expected signature string end-to-end so that any future
        regression in partitioning, rendering, or ordering surfaces
        immediately."""
        record = {
            "Metadata": {
                "variables": [
                    {"name": "alwaysLogError", "dataType": "Boolean",
                     "isCollection": False, "isInput": True,
                     "isOutput": False, "objectType": None},
                    {"name": "errorCode", "dataType": "String",
                     "isCollection": False, "isInput": False,
                     "isOutput": True, "objectType": None},
                    {"name": "errorMessage", "dataType": "String",
                     "isCollection": False, "isInput": False,
                     "isOutput": True, "objectType": None},
                    {"name": "flowFaultMessage", "dataType": "String",
                     "isCollection": False, "isInput": True,
                     "isOutput": False, "objectType": None},
                    {"name": "flowName", "dataType": "String",
                     "isCollection": False, "isInput": True,
                     "isOutput": False, "objectType": None},
                    {"name": "flowObject", "dataType": "String",
                     "isCollection": False, "isInput": True,
                     "isOutput": False, "objectType": None},
                    {"name": "flowSection", "dataType": "String",
                     "isCollection": False, "isInput": True,
                     "isOutput": False, "objectType": None},
                    {"name": "isFatal", "dataType": "Boolean",
                     "isCollection": False, "isInput": False,
                     "isOutput": True, "objectType": None},
                ],
            },
        }
        sig = main._derive_flow_signature(record)
        self.assertEqual(
            sig,
            "in: alwaysLogError: Boolean, flowFaultMessage: String, "
            "flowName: String, flowObject: String, flowSection: String | "
            "out: errorCode: String, errorMessage: String, isFatal: Boolean",
        )

    def test_derive_flow_signature_apex_type_uses_apexclass(self):
        """Apex-typed variables (e.g. Flow invocable action return rows)
        carry the concrete class name in `apexClass`, not `dataType`
        (which is the generic literal `Apex`). The signature MUST render
        the concrete class so authors can trace the type back to real
        code — `List<Apex>` is useless."""
        record = {
            "Metadata": {
                "variables": [
                    {
                        "name": "OrgList",
                        "dataType": "Apex",
                        "apexClass": "CX_OrgSelector.Org",
                        "isCollection": True,
                        "isInput": False,
                        "isOutput": True,
                    },
                ],
            },
        }
        sig = main._derive_flow_signature(record)
        self.assertEqual(sig, "out: OrgList: List<CX_OrgSelector.Org>")

    def test_derive_flow_signature_apex_type_without_apexclass_falls_through(self):
        """Defensive fallback: if `apexClass` is missing/blank on an
        Apex-typed variable we render the literal `Apex` so the surface
        still reports *something* — losing the signature entirely would
        regress today's behavior."""
        record = {
            "Metadata": {
                "variables": [
                    {
                        "name": "rows",
                        "dataType": "Apex",
                        "apexClass": None,
                        "isCollection": True,
                        "isInput": False,
                        "isOutput": True,
                    },
                ],
            },
        }
        sig = main._derive_flow_signature(record)
        self.assertEqual(sig, "out: rows: List<Apex>")

    def test_bare_metadata_dict_accepted(self):
        """Test convenience: callers can pass the `Metadata` dict
        directly (what they'd get from `record["Metadata"]`) without
        wrapping it in the outer Tooling row. Exercised by several
        sibling tests; pin the contract explicitly."""
        bare = {
            "variables": [
                {"name": "caseId", "dataType": "String",
                 "isInput": True, "isOutput": False},
            ],
        }
        sig = main._derive_flow_signature(bare)
        self.assertEqual(sig, "in: caseId: String")


# ---------------------------------------------------------------------------
# _stamp_signatures — walks tree, writes node["signature"]
# ---------------------------------------------------------------------------


class StampSignaturesTests(unittest.TestCase):
    def test_stamp_applies_to_tree(self):
        """APEX + FLOW nodes whose api_name matches the sigs dicts get
        `node["signature"]` populated; unmatched nodes are left alone."""
        tree_root = {
            "kind": "AGENT",
            "api_name": "MyAgent",
            "children": [
                {
                    "kind": "APEX",
                    "api_name": "OrderLookup",
                    "children": [],
                },
                {
                    "kind": "APEX",
                    "api_name": "UnmatchedApex",
                    "children": [],
                },
                {
                    "kind": "FLOW",
                    "api_name": "LookupOrder",
                    "children": [
                        {
                            "kind": "APEX",
                            "api_name": "OrderLookup",
                            "children": [],
                        },
                    ],
                },
            ],
        }
        apex_sigs = {
            "OrderLookup": "public static List<Result> run(List<Request> input)",
        }
        flow_sigs = {
            "LookupOrder": "in: caseId: String | out: result: String",
        }

        main._stamp_signatures(tree_root, apex_sigs, flow_sigs)

        self.assertEqual(
            tree_root["children"][0]["signature"],
            "public static List<Result> run(List<Request> input)",
        )
        # Unmatched Apex stays bare.
        self.assertNotIn("signature", tree_root["children"][1])
        # Flow node gets its signature.
        self.assertEqual(
            tree_root["children"][2]["signature"],
            "in: caseId: String | out: result: String",
        )
        # Apex nested under the flow also stamped.
        self.assertEqual(
            tree_root["children"][2]["children"][0]["signature"],
            "public static List<Result> run(List<Request> input)",
        )
        # Root itself (neither APEX nor FLOW) is untouched.
        self.assertNotIn("signature", tree_root)

    def test_stamp_preserves_shared_utility_across_branches(self):
        """Shared utility flows (e.g. handleFlowFault referenced from N
        places) must get the SAME signature stamped on every occurrence —
        they reference the same FlowDefinition / ApexClass by name."""
        tree_root = {
            "kind": "AGENT",
            "api_name": "Agent",
            "children": [
                {
                    "kind": "FLOW",
                    "api_name": "BranchA",
                    "children": [
                        {
                            "kind": "FLOW",
                            "api_name": "handleFlowFault",
                            "children": [],
                        },
                    ],
                },
                {
                    "kind": "FLOW",
                    "api_name": "BranchB",
                    "children": [
                        {
                            "kind": "FLOW",
                            "api_name": "handleFlowFault",
                            "children": [],
                        },
                    ],
                },
            ],
        }
        flow_sigs = {"handleFlowFault": "in: fault: String"}
        main._stamp_signatures(tree_root, {}, flow_sigs)

        stamp_a = tree_root["children"][0]["children"][0]["signature"]
        stamp_b = tree_root["children"][1]["children"][0]["signature"]
        self.assertEqual(stamp_a, "in: fault: String")
        self.assertEqual(stamp_b, "in: fault: String")
        self.assertEqual(stamp_a, stamp_b)


if __name__ == "__main__":
    unittest.main()
