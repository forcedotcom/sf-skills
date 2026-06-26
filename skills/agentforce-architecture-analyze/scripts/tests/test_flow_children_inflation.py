"""Tests for `main._build_flow_children` + end-to-end FLOW-child inflation.

Closes the Batch-1 placeholder that left `flow_children = {}` unconditionally —
every FLOW leaf shipped with `children: []` regardless of the subflow /
actionCall content present in the fetched `Flow.Metadata`.

Assertions focus on observable behavior:
  * actionCalls are classified into the correct `kind` + carry `element_name`
    (the flow-XML `<name>` that identifies WHICH Flow element invokes the
    target — load-bearing for the rendered tree view).
  * subflows become `{"kind": "FLOW", ...}` child refs with correct target.
  * The output dict is keyed by FlowDefinition.DeveloperName (what
    `walk_and_inflate` looks up), NOT by ActiveVersionId.
  * Defensive skips on missing ActiveVersionId / missing `Metadata` payload.
  * End-to-end: a mocked Wave B with populated Flow.Metadata produces a tree
    where the FLOW node actually has descendants (the load-bearing integration
    test).
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from . import _bootstrap  # noqa: F401

import config  # type: ignore
import soql_loader  # type: ignore
import main  # type: ignore
from tests.fixtures import genai_payloads as fx  # type: ignore

# Re-point SOQL lookup into the repo source (same recipe as test_main_pipeline).
_REPO_SOQL_DIR = Path(__file__).resolve().parent.parent.parent / "assets" / "soql"
config.SOQL_DIR = _REPO_SOQL_DIR
soql_loader.SOQL_DIR = _REPO_SOQL_DIR


# ---------------------------------------------------------------------------
# Unit tests — _build_flow_children
# ---------------------------------------------------------------------------


class BuildFlowChildrenTests(unittest.TestCase):
    def test_actioncalls_classified_correctly(self):
        """Each actionType (apex / generatePromptResponse / other / empty)
        must route through `classify_action_call` and produce the correct
        `kind` + preserve `element_name` + `api_name`."""
        flow_metadata = {
            "301VF001": {
                "Id": "301VF001", "FullName": "MixedFlow-1",
                "Metadata": {
                    "actionCalls": [
                        {"name": "Call_Apex",
                         "actionType": "apex",
                         "actionName": "MyApexHandler"},
                        {"name": "Generate_Output",
                         "actionType": "generatePromptResponse",
                         "actionName": "MyPromptTemplate"},
                        {"name": "Send_Email",
                         "actionType": "emailSimple",
                         "actionName": "SendSimpleEmail"},
                        {"name": "Unknown_Element",
                         "actionType": "",
                         "actionName": ""},
                    ],
                },
            },
        }
        flow_def_rows = [
            {"Id": "300VF001", "DeveloperName": "MixedFlow",
             "ActiveVersionId": "301VF001"},
        ]

        out = main._build_flow_children(flow_metadata, flow_def_rows)
        self.assertIn("MixedFlow", out)
        kids = out["MixedFlow"]
        self.assertEqual(len(kids), 4)

        by_element = {k["element_name"]: k for k in kids}

        self.assertEqual(by_element["Call_Apex"]["kind"], "APEX")
        self.assertEqual(by_element["Call_Apex"]["api_name"], "MyApexHandler")

        self.assertEqual(by_element["Generate_Output"]["kind"], "PROMPT_TEMPLATE")
        self.assertEqual(by_element["Generate_Output"]["api_name"], "MyPromptTemplate")

        self.assertEqual(by_element["Send_Email"]["kind"], "STANDARD_ACTION")
        self.assertEqual(by_element["Send_Email"]["api_name"], "SendSimpleEmail")
        # `invocation_type` (schema 3.1 canonical name) is preserved for
        # STANDARD_ACTION so render layers can surface the actionType
        # qualifier (emailSimple, etc.) — e.g. `SendSimpleEmail (emailSimple)`
        # in the rendered tree.
        self.assertEqual(by_element["Send_Email"]["invocation_type"], "emailSimple")

        # Empty actionType + empty actionName → UNKNOWN. `classify_action_call`
        # substitutes "?" for the api_name when both are blank.
        self.assertEqual(by_element["Unknown_Element"]["kind"], "UNKNOWN")

    def test_subflows_become_flow_children(self):
        """Two subflow entries → two `{"kind": "FLOW", ...}` child refs with
        their `<subflows><name>` as `element_name` and `<flowName>` as
        `api_name`. These are the load-bearing fields for the recursive
        inflation step."""
        flow_metadata = {
            "301VF001": {
                "Id": "301VF001", "FullName": "ParentFlow-1",
                "Metadata": {
                    "subflows": [
                        {"name": "Handle_Fault",
                         "flowName": "handleFlowFault"},
                        {"name": "Run_Subroutine",
                         "flowName": "mySubroutineFlow"},
                    ],
                },
            },
        }
        flow_def_rows = [
            {"Id": "300VF001", "DeveloperName": "ParentFlow",
             "ActiveVersionId": "301VF001"},
        ]

        out = main._build_flow_children(flow_metadata, flow_def_rows)
        kids = out["ParentFlow"]
        self.assertEqual(len(kids), 2)
        self.assertTrue(all(k["kind"] == "FLOW" for k in kids))

        by_element = {k["element_name"]: k for k in kids}
        self.assertEqual(by_element["Handle_Fault"]["api_name"], "handleFlowFault")
        self.assertEqual(by_element["Run_Subroutine"]["api_name"], "mySubroutineFlow")

    def test_keyed_by_developer_name_not_version_id(self):
        """The dict MUST be keyed by FlowDefinition.DeveloperName — that's
        what `walk_and_inflate` looks up via `flow_children[leaf.api_name]`.
        Keying by ActiveVersionId would silently return `{}` and the tree
        would stay flat."""
        flow_metadata = {
            "301VF_A": {"Id": "301VF_A", "FullName": "FlowA-1",
                       "Metadata": {"actionCalls": [
                           {"name": "ac1", "actionType": "apex",
                            "actionName": "ApexA"},
                       ]}},
            "301VF_B": {"Id": "301VF_B", "FullName": "FlowB-1",
                       "Metadata": {"actionCalls": [
                           {"name": "ac1", "actionType": "apex",
                            "actionName": "ApexB"},
                       ]}},
        }
        flow_def_rows = [
            {"Id": "300VF_A", "DeveloperName": "FlowAlpha",
             "ActiveVersionId": "301VF_A"},
            {"Id": "300VF_B", "DeveloperName": "FlowBeta",
             "ActiveVersionId": "301VF_B"},
        ]
        out = main._build_flow_children(flow_metadata, flow_def_rows)
        self.assertEqual(set(out.keys()), {"FlowAlpha", "FlowBeta"})
        # Not the version IDs.
        self.assertNotIn("301VF_A", out)
        self.assertNotIn("301VF_B", out)

    def test_missing_active_version_id_skipped(self):
        """Inactive flows have no ActiveVersionId. They should be silently
        skipped — not raise KeyError, not pollute `flow_children`."""
        flow_metadata = {
            "301VF001": {"Id": "301VF001", "FullName": "ActiveFlow-1",
                        "Metadata": {"actionCalls": []}},
        }
        flow_def_rows = [
            # Active flow: normal row.
            {"Id": "300VF001", "DeveloperName": "ActiveFlow",
             "ActiveVersionId": "301VF001"},
            # Inactive flow: no ActiveVersionId. Must not raise.
            {"Id": "300VF002", "DeveloperName": "InactiveFlow",
             "ActiveVersionId": None},
        ]
        out = main._build_flow_children(flow_metadata, flow_def_rows)
        self.assertIn("ActiveFlow", out)
        self.assertNotIn("InactiveFlow", out)

    def test_empty_wave_b_produces_empty_dict(self):
        """Zero flows → empty dict, no crash."""
        self.assertEqual(main._build_flow_children({}, []), {})
        self.assertEqual(main._build_flow_children(None or {}, None or []), {})

    def test_missing_metadata_field_tolerated(self):
        """A Flow record that for some reason lacks `Metadata` (empty dict,
        None, or the key omitted entirely) must degrade to an empty child
        list — never raise. `walk_and_inflate` treats an empty list and
        "no key" identically, so we can be permissive and emit empty lists
        in all three cases; the invariant is "does not raise + does not
        fabricate children"."""
        flow_metadata = {
            "301VF001": {"Id": "301VF001", "FullName": "Empty-1", "Metadata": {}},
            "301VF002": {"Id": "301VF002", "FullName": "None-1", "Metadata": None},
            "301VF003": {"Id": "301VF003", "FullName": "NoKey-1"},
        }
        flow_def_rows = [
            {"Id": "300VF001", "DeveloperName": "EmptyFlow",
             "ActiveVersionId": "301VF001"},
            {"Id": "300VF002", "DeveloperName": "NoneFlow",
             "ActiveVersionId": "301VF002"},
            {"Id": "300VF003", "DeveloperName": "NoKeyFlow",
             "ActiveVersionId": "301VF003"},
        ]
        out = main._build_flow_children(flow_metadata, flow_def_rows)
        for name in ("EmptyFlow", "NoneFlow", "NoKeyFlow"):
            self.assertIn(name, out)
            self.assertEqual(out[name], [])

    def test_subflow_missing_flow_name_dropped(self):
        """A subflow entry without `flowName` has no api_name to descend
        into — drop it silently rather than emit a broken child ref."""
        flow_metadata = {
            "301VF001": {"Id": "301VF001", "FullName": "Parent-1",
                        "Metadata": {"subflows": [
                            {"name": "BadSubflow"},  # missing flowName
                            {"name": "GoodSubflow", "flowName": "TargetFlow"},
                        ]}},
        }
        flow_def_rows = [
            {"Id": "300VF001", "DeveloperName": "ParentFlow",
             "ActiveVersionId": "301VF001"},
        ]
        out = main._build_flow_children(flow_metadata, flow_def_rows)
        self.assertEqual(len(out["ParentFlow"]), 1)
        self.assertEqual(out["ParentFlow"][0]["element_name"], "GoodSubflow")


# ---------------------------------------------------------------------------
# Integration test — end-to-end tree inflation through _run_parse_wave
# ---------------------------------------------------------------------------


def _mock_auth_probe():
    org_display_payload = {
        "status": 0,
        "result": {
            "instanceUrl": "https://example.my.salesforce.com",
            "accessToken": "00Dxx0000000000!AQ_fake_token_value",
            "id": "00Dxx0000000000AAA",
            "apiVersion": "60.0",
        },
    }
    return [
        mock.patch.object(main, "run_sf", return_value=org_display_payload),
        mock.patch.object(main, "probe_channels", return_value=fx.probe_ok_payload()),
    ]


def _mock_bot_resolution():
    return [
        mock.patch.object(
            main, "fetch_bot_versions",
            return_value=fx.make_bot_versions("MyAgent", ("v5",), "v5"),
        ),
        mock.patch.object(main, "fetch_bot_definition_details",
                          return_value=fx.BOT_DEFINITION_DETAIL_CLASSIC),
    ]


class EndToEndInflationTests(unittest.TestCase):
    """Load-bearing integration test.

    Runs the full pipeline with a synthetic Flow.Metadata that has one
    actionCall (apex) + one subflow. Asserts the resulting
    `declared_action_tree.json` has a FLOW node whose `children` list
    is NON-empty and carries the expected `element_name`. This is the
    behavior the bug fix restores.
    """

    def test_end_to_end_inflation_produces_nested_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "work"
            data_root = Path(tmp) / "data"
            cache_root = Path(tmp) / "cache"

            # Single classic bot with one topic + one flow action. The
            # flow's Metadata carries one actionCall (apex) + one subflow.
            planner = dict(fx.CLASSIC_PLANNER)
            plugins = [{
                "Id": "1VyVF000000TOP1",
                "DeveloperName": "OrderTopic",
                "MasterLabel": "Order Topic",
                "Description": None,
                "PluginType": "Custom",
                "Scope": "Order management",
                "IsLocal": True,
                "CanEscalate": False,
                "Source": "Declarative",
                "ParentId": planner["Id"],
                "LocalDeveloperName": "OrderTopic",
            }]
            functions = [{
                "Id": "1VuVF0000000F01",
                "DeveloperName": "LookupOrderFn",
                "MasterLabel": "LookupOrderFn",
                "Description": None,
                "InvocationTargetType": "flow",
                "InvocationTarget": "LookupOrder",
                "IsLocal": True,
                "IsConfirmationRequired": False,
                "IsIncludeInProgressIndicator": False,
                "ProgressIndicatorMessage": None,
                "Source": "Declarative",
                "PluginId": plugins[0]["Id"],
                "PlannerId": None,
                "ParentId": None,
                "LocalDeveloperName": "LookupOrderFn",
            }]
            plugin_fn_join = [{
                "Id": "pfj1", "PluginId": plugins[0]["Id"],
                "Function": functions[0]["Id"],
            }]
            flow_defs = [{
                "Id": "300VF001", "DeveloperName": "LookupOrder",
                "ActiveVersionId": "301VF001",
            }]
            flow_metadata_record = {
                "Id": "301VF001", "FullName": "LookupOrder-1",
                "Metadata": {
                    "actionCalls": [{
                        "name": "Call_The_Apex_Helper",
                        "actionType": "apex",
                        "actionName": "OrderLookupApex",
                    }],
                    "subflows": [{
                        "name": "Run_Subflow",
                        "flowName": "OrderLookupSubflow",
                    }],
                },
            }

            patches = [
                *_mock_auth_probe(),
                *_mock_bot_resolution(),
                mock.patch.object(main, "fetch_planner_definition", return_value=planner),
                mock.patch.object(main, "fetch_plugins_by_planner", return_value=plugins),
                mock.patch.object(main, "fetch_planner_bundle_functions", return_value=[]),
                mock.patch.object(main, "fetch_functions_by_plugins",
                                  return_value=functions),
                mock.patch.object(main, "fetch_plugin_instructions", return_value=[]),
                mock.patch.object(main, "fetch_plugin_functions",
                                  return_value=plugin_fn_join),
                mock.patch.object(main, "fetch_planner_attrs", return_value=[]),
                mock.patch.object(main, "fetch_apex_bodies_by_names", return_value=[]),
                mock.patch.object(main, "fetch_apex_bodies_by_ids", return_value=[]),
                mock.patch.object(main, "fetch_flow_definition_ids_by_names",
                                  return_value=flow_defs),
                mock.patch.object(main, "fetch_flow_definition_by_ids", return_value=[]),
                mock.patch.object(
                    main, "fetch_flow_metadata",
                    side_effect=lambda vid, *a, **kw: (
                        flow_metadata_record if vid == "301VF001" else None
                    ),
                ),
                mock.patch.object(main, "build_agent_data_dir",
                                  side_effect=lambda o, a, v: data_root / o / f"{a}__{v}"),
                mock.patch.object(main, "build_agent_cache_dir",
                                  side_effect=lambda o, a, v: cache_root / o / f"{a}__{v}"),
            ]
            for p in patches:
                p.start()
            try:
                rc = main.main([
                    "--org-alias", "test-org",
                    "--agent", "MyAgent",
                    "--work-dir", str(work_dir),
                    "--parallelism", "2",
                ])
            finally:
                for p in patches:
                    p.stop()

            self.assertEqual(rc, 0)
            tree = json.loads((work_dir / "declared_action_tree.json").read_text())

            # Locate the FLOW leaf under the topic's GEN_AI_FUNCTION.
            topic = tree["root"]["children"][0]
            gen_ai_fn = topic["children"][0]
            flow_leaf = gen_ai_fn["children"][0]
            self.assertEqual(flow_leaf["kind"], "FLOW")
            self.assertEqual(flow_leaf["api_name"], "LookupOrder")

            # BUG FIX ASSERTION: the FLOW node now has non-empty children.
            # Before the fix, `flow_children = {}` meant every FLOW leaf
            # shipped with `children: []` regardless of actionCalls /
            # subflows content.
            self.assertEqual(len(flow_leaf["children"]), 2)

            element_names = {c["element_name"] for c in flow_leaf["children"]}
            self.assertIn("Call_The_Apex_Helper", element_names)
            self.assertIn("Run_Subflow", element_names)

            # Kinds are correctly classified — APEX for the actionCall,
            # FLOW for the subflow.
            by_element = {c["element_name"]: c for c in flow_leaf["children"]}
            self.assertEqual(by_element["Call_The_Apex_Helper"]["kind"], "APEX")
            self.assertEqual(
                by_element["Call_The_Apex_Helper"]["api_name"],
                "OrderLookupApex",
            )
            self.assertEqual(by_element["Run_Subflow"]["kind"], "FLOW")
            self.assertEqual(
                by_element["Run_Subflow"]["api_name"],
                "OrderLookupSubflow",
            )

    def test_nested_subflow_subtree_populated_via_iteration(self):
        """iterative Wave B must expand shared
        utility-flow leaves.

        Before the iteration pass: the top-level flow `LookupOrder`
        referenced a subflow `handleFlowFault`, which landed as an empty
        FLOW leaf because its body was never queried. This test pushes
        end-to-end through `main()` and asserts the `handleFlowFault`
        node in the tree has CHILDREN — specifically the Apex class
        `XCSF_FlowFaultMessage` referenced by its own body.
        """
        with tempfile.TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "work"
            data_root = Path(tmp) / "data"
            cache_root = Path(tmp) / "cache"

            planner = dict(fx.CLASSIC_PLANNER)
            plugins = [{
                "Id": "1VyVF000000TOP1",
                "DeveloperName": "OrderTopic",
                "MasterLabel": "Order Topic",
                "Description": None,
                "PluginType": "Custom",
                "Scope": "Order management",
                "IsLocal": True,
                "CanEscalate": False,
                "Source": "Declarative",
                "ParentId": planner["Id"],
                "LocalDeveloperName": "OrderTopic",
            }]
            functions = [{
                "Id": "1VuVF0000000F01",
                "DeveloperName": "LookupOrderFn",
                "MasterLabel": "LookupOrderFn",
                "Description": None,
                "InvocationTargetType": "flow",
                "InvocationTarget": "LookupOrder",
                "IsLocal": True,
                "IsConfirmationRequired": False,
                "IsIncludeInProgressIndicator": False,
                "ProgressIndicatorMessage": None,
                "Source": "Declarative",
                "PluginId": plugins[0]["Id"],
                "PlannerId": None,
                "ParentId": None,
                "LocalDeveloperName": "LookupOrderFn",
            }]
            plugin_fn_join = [{
                "Id": "pfj1", "PluginId": plugins[0]["Id"],
                "Function": functions[0]["Id"],
            }]

            # Flow registry keyed by DeveloperName → (FlowDefinition row,
            # Flow.Metadata record). The mock fetcher consults this on
            # each iteration round.
            flow_registry = {
                "LookupOrder": (
                    {"Id": "300VF001", "DeveloperName": "LookupOrder",
                     "ActiveVersionId": "301VF001"},
                    {"Id": "301VF001", "FullName": "LookupOrder-1",
                     "Metadata": {
                         "actionCalls": [],
                         "subflows": [{
                             "name": "Handle_Flow_Fault",
                             "flowName": "handleFlowFault",
                         }],
                     }},
                ),
                "handleFlowFault": (
                    {"Id": "300VF002", "DeveloperName": "handleFlowFault",
                     "ActiveVersionId": "301VF002"},
                    {"Id": "301VF002", "FullName": "handleFlowFault-1",
                     "Metadata": {
                         "actionCalls": [{
                             "name": "Parse_and_log_fault",
                             "actionType": "apex",
                             "actionName": "XCSF_FlowFaultMessage",
                         }],
                         "subflows": [],
                     }},
                ),
            }

            def fake_flow_def_by_names(names, *a, **kw):
                return [
                    flow_registry[n][0] for n in names if n in flow_registry
                ]

            def fake_flow_metadata(vid, *a, **kw):
                for _name, (fd, fm) in flow_registry.items():
                    if fd["ActiveVersionId"] == vid:
                        return fm
                return None

            # Apex bodies: XCSF_FlowFaultMessage is discovered via the
            # subflow's actionCall in iteration round 2.
            def fake_apex_by_names(names, *a, **kw):
                apex_registry = {
                    "XCSF_FlowFaultMessage": {
                        "Id": "01pVF001", "Name": "XCSF_FlowFaultMessage",
                        "Body": "public class XCSF_FlowFaultMessage { }",
                    },
                }
                return [apex_registry[n] for n in names if n in apex_registry]

            patches = [
                *_mock_auth_probe(),
                *_mock_bot_resolution(),
                mock.patch.object(main, "fetch_planner_definition", return_value=planner),
                mock.patch.object(main, "fetch_plugins_by_planner", return_value=plugins),
                mock.patch.object(main, "fetch_planner_bundle_functions", return_value=[]),
                mock.patch.object(main, "fetch_functions_by_plugins",
                                  return_value=functions),
                mock.patch.object(main, "fetch_plugin_instructions", return_value=[]),
                mock.patch.object(main, "fetch_plugin_functions",
                                  return_value=plugin_fn_join),
                mock.patch.object(main, "fetch_planner_attrs", return_value=[]),
                mock.patch.object(main, "fetch_apex_bodies_by_names",
                                  side_effect=fake_apex_by_names),
                mock.patch.object(main, "fetch_apex_bodies_by_ids", return_value=[]),
                mock.patch.object(main, "fetch_flow_definition_ids_by_names",
                                  side_effect=fake_flow_def_by_names),
                mock.patch.object(main, "fetch_flow_definition_by_ids", return_value=[]),
                mock.patch.object(main, "fetch_flow_metadata",
                                  side_effect=fake_flow_metadata),
                mock.patch.object(main, "build_agent_data_dir",
                                  side_effect=lambda o, a, v: data_root / o / f"{a}__{v}"),
                mock.patch.object(main, "build_agent_cache_dir",
                                  side_effect=lambda o, a, v: cache_root / o / f"{a}__{v}"),
            ]
            for p in patches:
                p.start()
            try:
                rc = main.main([
                    "--org-alias", "test-org",
                    "--agent", "MyAgent",
                    "--work-dir", str(work_dir),
                    "--parallelism", "2",
                ])
            finally:
                for p in patches:
                    p.stop()

            self.assertEqual(rc, 0)
            tree = json.loads((work_dir / "declared_action_tree.json").read_text())

            topic = tree["root"]["children"][0]
            gen_ai_fn = topic["children"][0]
            top_flow = gen_ai_fn["children"][0]
            self.assertEqual(top_flow["api_name"], "LookupOrder")

            # LookupOrder → Handle_Flow_Fault (FLOW leaf, pre-iteration
            # this was empty). Post-iteration, it must carry children.
            handle_flow_fault = top_flow["children"][0]
            self.assertEqual(handle_flow_fault["kind"], "FLOW")
            self.assertEqual(handle_flow_fault["api_name"], "handleFlowFault")

            # Core assertion: the shared utility flow's subtree is now
            # populated via iterative Wave B fetching its body.
            self.assertTrue(
                handle_flow_fault["children"],
                "handleFlowFault subtree is empty — iterative Wave B "
                "did not fetch its body. This is the bug.",
            )
            apex_kids = [
                c for c in handle_flow_fault["children"]
                if c["kind"] == "APEX" and c["api_name"] == "XCSF_FlowFaultMessage"
            ]
            self.assertEqual(len(apex_kids), 1)
            self.assertEqual(apex_kids[0]["element_name"], "Parse_and_log_fault")


if __name__ == "__main__":
    unittest.main()
