"""Tests for `main._iterate_wave_b` — iterative subflow + apex discovery.

The initial `_run_wave_b` only enumerates top-level flow refs from
`bundle_parsed`. When those flow bodies reference subflows (shared
utility flows like `handleFlowFault`) or new Apex classes, their bodies
were never fetched. `_iterate_wave_b` drives Wave B to a fixed point so
every reachable flow/apex body lands in the tree.

Assertions focus on observable behavior:
  * Convergence shape — no extra fetches when there are no new refs.
  * Correctness — a utility flow referenced from the top-level round is
    fetched in the next round and its metadata lands in the merged dict.
  * Safety — iteration cap surfaces remaining unfetched names via
    `unresolved`; fetch failures are tolerated without crashing.
  * Cross-kind discovery — a subflow's actionCall referencing a new
    Apex class adds that class to `apex_rows`.
  * Deduplication — the same subflow referenced twice is fetched once.
"""
from __future__ import annotations

import unittest
from unittest import mock

from . import _bootstrap  # noqa: F401

import main  # type: ignore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _creds_provider():
    return ("https://example.my.salesforce.com", "fake_token")


def _refresh_fn():
    return _creds_provider()


def _flow_def_row(dev_name: str, version_id: str) -> dict:
    """Shape matches what `fetch_flow_definition_ids_by_names` returns —
    the fields `_build_flow_children` + the pipeline downstream expect."""
    return {
        "Id": f"300{dev_name}",
        "DeveloperName": dev_name,
        "ActiveVersionId": version_id,
    }


def _flow_metadata_record(
    version_id: str,
    full_name: str,
    *,
    subflows: list[tuple[str, str]] | None = None,
    action_calls: list[dict] | None = None,
) -> dict:
    """Shape a synthetic Flow.Metadata record the way `fetch_flow_metadata`
    returns it — a dict with Id/FullName/Metadata. Subflow tuples are
    `(element_name, flow_name)`; action_calls are raw dicts."""
    md: dict = {}
    if subflows is not None:
        md["subflows"] = [
            {"name": elem, "flowName": target} for elem, target in subflows
        ]
    if action_calls is not None:
        md["actionCalls"] = action_calls
    return {"Id": version_id, "FullName": full_name, "Metadata": md}


def _apex_row(name: str) -> dict:
    """Shape matches `fetch_apex_bodies_by_names` output — `_iterate_wave_b`
    tracks already-fetched by `Name`."""
    return {"Id": f"01p_{name}", "Name": name, "Body": "public class ..."}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class IterativeWaveBTests(unittest.TestCase):
    def test_single_round_when_no_subflows(self):
        """Round 1 flow body references no subflows and no new apex →
        `_extract_refs_from_flow_metadata` returns empty sets →
        `_fetch_wave_b_by_names` is never invoked → initial wave_b passes
        through unchanged."""
        initial = {
            "apex_rows": [],
            "flow_def_rows": [_flow_def_row("TopFlow", "301TOP")],
            "flow_metadata": {
                "301TOP": _flow_metadata_record(
                    "301TOP", "TopFlow-1", subflows=[], action_calls=[],
                ),
            },
            "unresolved": [],
        }

        with mock.patch.object(main, "_fetch_wave_b_by_names") as mocked:
            out = main._iterate_wave_b(
                initial, _creds_provider, _refresh_fn,
                api_version="v60.0", org_alias="test-org",
                parallelism=2, max_iterations=5,
            )

        mocked.assert_not_called()
        self.assertEqual(
            {r["DeveloperName"] for r in out["flow_def_rows"]},
            {"TopFlow"},
        )
        self.assertEqual(out["unresolved"], [])

    def test_two_rounds_for_shared_utility_flow(self):
        """Round 1: a top-level flow body references subflow `handleFlowFault`.
        Round 2: fetches `handleFlowFault`'s metadata. Round 3: no new refs.
        Converges. Final flow_metadata contains BOTH flows.

        This is the real-org `MyAgent__v5` shape — `handleFlowFault`
        is shared across every flow and should be fetched in one extra
        round.
        """
        initial = {
            "apex_rows": [],
            "flow_def_rows": [_flow_def_row("AGNT_Top_Flow", "301TOP")],
            "flow_metadata": {
                "301TOP": _flow_metadata_record(
                    "301TOP", "AGNT_Top_Flow-1",
                    subflows=[("Handle_Flow_Fault", "handleFlowFault")],
                ),
            },
            "unresolved": [],
        }

        # Mock `_fetch_wave_b_by_names` for two rounds:
        # Round 1: flow_names=[handleFlowFault] → returns metadata whose
        # actionCalls reference a NEW apex (XCSF_FlowFaultMessage).
        # Round 2: apex_names=[XCSF_FlowFaultMessage] → apex row returned.
        # Round 3: no new refs → converge.
        calls: list[dict] = []

        def fake_fetch(**kwargs):
            calls.append({
                "flow_names": list(kwargs["flow_names"]),
                "apex_names": list(kwargs["apex_names"]),
            })
            if kwargs["flow_names"] == ["handleFlowFault"]:
                return {
                    "apex_rows": [],
                    "flow_def_rows": [
                        _flow_def_row("handleFlowFault", "301UTIL"),
                    ],
                    "flow_metadata": {
                        "301UTIL": _flow_metadata_record(
                            "301UTIL", "handleFlowFault-1",
                            subflows=[],
                            action_calls=[{
                                "name": "Parse_and_log_fault",
                                "actionType": "apex",
                                "actionName": "XCSF_FlowFaultMessage",
                            }],
                        ),
                    },
                    "unresolved": [],
                }
            if kwargs["apex_names"] == ["XCSF_FlowFaultMessage"]:
                return {
                    "apex_rows": [_apex_row("XCSF_FlowFaultMessage")],
                    "flow_def_rows": [],
                    "flow_metadata": {},
                    "unresolved": [],
                }
            raise AssertionError(f"unexpected fetch call: {kwargs}")

        with mock.patch.object(
            main, "_fetch_wave_b_by_names", side_effect=fake_fetch,
        ) as mocked:
            out = main._iterate_wave_b(
                initial, _creds_provider, _refresh_fn,
                api_version="v60.0", org_alias="test-org",
                parallelism=2, max_iterations=5,
            )

        # Exactly two rounds: round 1 picks up handleFlowFault, round 2
        # picks up the apex discovered in round 1's subflow body, round 3
        # converges without invoking the fetcher.
        self.assertEqual(mocked.call_count, 2)
        dev_names = {r["DeveloperName"] for r in out["flow_def_rows"]}
        self.assertEqual(dev_names, {"AGNT_Top_Flow", "handleFlowFault"})
        self.assertIn("301UTIL", out["flow_metadata"])
        apex_names_out = {r["Name"] for r in out["apex_rows"]}
        self.assertIn("XCSF_FlowFaultMessage", apex_names_out)
        # Call-order sanity: flow round precedes apex round.
        self.assertEqual(calls[0]["flow_names"], ["handleFlowFault"])
        self.assertEqual(calls[1]["apex_names"], ["XCSF_FlowFaultMessage"])

    def test_actioncall_discovers_new_apex(self):
        """A subflow body carries an actionCall referencing a new Apex
        class. Round 2 fetches that Apex. `wave_b["apex_rows"]` grows."""
        initial = {
            "apex_rows": [],
            "flow_def_rows": [_flow_def_row("TopFlow", "301TOP")],
            "flow_metadata": {
                "301TOP": _flow_metadata_record(
                    "301TOP", "TopFlow-1",
                    subflows=[],
                    action_calls=[{
                        "name": "Invoke_Helper",
                        "actionType": "apex",
                        "actionName": "NewApexHelper",
                    }],
                ),
            },
            "unresolved": [],
        }

        def fake_fetch(**kwargs):
            # Must be the apex-only round — no new flow names.
            self.assertEqual(kwargs["flow_names"], [])
            self.assertEqual(kwargs["apex_names"], ["NewApexHelper"])
            return {
                "apex_rows": [_apex_row("NewApexHelper")],
                "flow_def_rows": [],
                "flow_metadata": {},
                "unresolved": [],
            }

        with mock.patch.object(
            main, "_fetch_wave_b_by_names", side_effect=fake_fetch,
        ) as mocked:
            out = main._iterate_wave_b(
                initial, _creds_provider, _refresh_fn,
                api_version="v60.0", org_alias="test-org",
                parallelism=2, max_iterations=5,
            )

        self.assertEqual(mocked.call_count, 1)
        apex_names_seen = {r["Name"] for r in out["apex_rows"]}
        self.assertEqual(apex_names_seen, {"NewApexHelper"})

    def test_dedup_across_rounds(self):
        """The same subflow referenced from two parent flows is fetched
        exactly once. `_iterate_wave_b` diffs against already-fetched
        names — duplicates are filtered before dispatch."""
        initial = {
            "apex_rows": [],
            "flow_def_rows": [
                _flow_def_row("ParentA", "301A"),
                _flow_def_row("ParentB", "301B"),
            ],
            "flow_metadata": {
                "301A": _flow_metadata_record(
                    "301A", "ParentA-1",
                    subflows=[("Handle_A", "SharedUtility")],
                ),
                "301B": _flow_metadata_record(
                    "301B", "ParentB-1",
                    subflows=[("Handle_B", "SharedUtility")],
                ),
            },
            "unresolved": [],
        }

        call_log: list[list[str]] = []

        def fake_fetch(**kwargs):
            call_log.append(list(kwargs["flow_names"]))
            return {
                "apex_rows": [],
                "flow_def_rows": [_flow_def_row("SharedUtility", "301UTIL")],
                "flow_metadata": {
                    "301UTIL": _flow_metadata_record(
                        "301UTIL", "SharedUtility-1", subflows=[],
                    ),
                },
                "unresolved": [],
            }

        with mock.patch.object(
            main, "_fetch_wave_b_by_names", side_effect=fake_fetch,
        ) as mocked:
            main._iterate_wave_b(
                initial, _creds_provider, _refresh_fn,
                api_version="v60.0", org_alias="test-org",
                parallelism=2, max_iterations=5,
            )

        # Exactly ONE round of fetching — round 1 queries [SharedUtility]
        # (deduped across the two parents); round 2 finds no new refs.
        self.assertEqual(mocked.call_count, 1)
        self.assertEqual(call_log[0], ["SharedUtility"])

    def test_iteration_cap_surfaces_pending(self):
        """Pathological graph where every round introduces a new subflow
        reference (chain: F1 → F2 → F3 → ...). After `max_iterations`
        rounds, remaining unfetched names are surfaced in `unresolved`
        so the pipeline can degrade to PARTIAL_OK with a clear cause.

        Use `max_iterations=3` to keep the test fast; the shape is
        identical to the production cap of 5.
        """
        initial = {
            "apex_rows": [],
            "flow_def_rows": [_flow_def_row("F0", "301_V0")],
            "flow_metadata": {
                "301_V0": _flow_metadata_record(
                    "301_V0", "F0-1", subflows=[("Chain", "F1")],
                ),
            },
            "unresolved": [],
        }

        round_counter = {"i": 1}

        def fake_fetch(**kwargs):
            """Each round returns a flow whose body references the next
            flow in the chain — unbounded growth."""
            requested = kwargs["flow_names"][0]
            next_flow = f"F{round_counter['i'] + 1}"
            round_counter["i"] += 1
            return {
                "apex_rows": [],
                "flow_def_rows": [_flow_def_row(requested, f"301_V{requested}")],
                "flow_metadata": {
                    f"301_V{requested}": _flow_metadata_record(
                        f"301_V{requested}", f"{requested}-1",
                        subflows=[("Chain", next_flow)],
                    ),
                },
                "unresolved": [],
            }

        with mock.patch.object(
            main, "_fetch_wave_b_by_names", side_effect=fake_fetch,
        ) as mocked:
            out = main._iterate_wave_b(
                initial, _creds_provider, _refresh_fn,
                api_version="v60.0", org_alias="test-org",
                parallelism=2, max_iterations=3,
            )

        # We exhausted exactly max_iterations rounds.
        self.assertEqual(mocked.call_count, 3)
        # The unfetched chain-tail lands in `unresolved` with the cap
        # reason so the pipeline can reflect it in the RESULT block.
        iter_cap_entries = [
            u for u in out["unresolved"]
            if "wave-b-iteration-cap" in (u.get("reason") or "")
        ]
        self.assertTrue(iter_cap_entries)
        # The next-round flow reference (F4, unfetched) must be among them.
        pending_names = {u.get("api_name") for u in iter_cap_entries}
        self.assertIn("F4", pending_names)

    def test_fetch_failure_tolerated(self):
        """If the round-N fetch raises (managed-package flow not readable,
        permission denied, etc.), the iteration doesn't crash. The
        affected name stays absent from `flow_def_rows` and surfaces via
        the pending-fetches path downstream; other rounds continue.

        Concretely: we simulate the failure by having the mocked
        `_fetch_wave_b_by_names` append an `unresolved` entry instead of
        returning metadata for the troubled name, which is exactly the
        contract `_fetch_wave_b_by_names` follows internally (it
        catches RestClientError / SoqlParamError and logs to
        `unresolved` without raising).
        """
        initial = {
            "apex_rows": [],
            "flow_def_rows": [_flow_def_row("TopFlow", "301TOP")],
            "flow_metadata": {
                "301TOP": _flow_metadata_record(
                    "301TOP", "TopFlow-1",
                    subflows=[
                        ("Good_Sub", "GoodSubflow"),
                        ("Bad_Sub", "UnreachableFlow"),
                    ],
                ),
            },
            "unresolved": [],
        }

        def fake_fetch(**kwargs):
            # Only the reachable one resolves. The unreachable one is
            # reported via the `unresolved` channel by the inner fetcher.
            return {
                "apex_rows": [],
                "flow_def_rows": [_flow_def_row("GoodSubflow", "301GOOD")],
                "flow_metadata": {
                    "301GOOD": _flow_metadata_record(
                        "301GOOD", "GoodSubflow-1", subflows=[],
                    ),
                },
                "unresolved": [{
                    "kind": "FLOW",
                    "reason": "flow-def-by-name-failed:managed-package-403",
                }],
            }

        with mock.patch.object(
            main, "_fetch_wave_b_by_names", side_effect=fake_fetch,
        ):
            out = main._iterate_wave_b(
                initial, _creds_provider, _refresh_fn,
                api_version="v60.0", org_alias="test-org",
                parallelism=2, max_iterations=5,
            )

        dev_names = {r["DeveloperName"] for r in out["flow_def_rows"]}
        # GoodSubflow made it in; UnreachableFlow did not.
        self.assertIn("GoodSubflow", dev_names)
        self.assertNotIn("UnreachableFlow", dev_names)
        # The inner-fetch's unresolved entry propagates.
        reasons = [u.get("reason") or "" for u in out["unresolved"]]
        self.assertTrue(
            any("managed-package-403" in r for r in reasons),
            f"expected propagated failure reason; got {reasons}",
        )
        # UnreachableFlow is still referenced but not fetched — after
        # iteration converges on subsequent rounds (no new discoveries
        # because GoodSubflow is leaf), it lands as iteration-cap
        # pending. In this test max_iterations=5 and the chain stops at
        # round 1; UnreachableFlow is still missing from fetched names,
        # so the convergence scan at the end flags it? Actually no —
        # convergence only surfaces via the cap. Let's verify that the
        # pipeline's parse_wave path would still mark it as pending via
        # visited-vs-referenced — but that's out of scope for this unit
        # test. The contract here is: iteration doesn't crash, good
        # flows are merged, bad-flow signal propagates.


class ExtractRefsFromFlowMetadataTests(unittest.TestCase):
    """Direct coverage for `_extract_refs_from_flow_metadata` — the
    load-bearing extractor that drives iteration. Its permissiveness
    (tolerating missing/None/malformed records) is a correctness
    property: if it raised on edge cases, iteration would crash on any
    flow with a weird metadata shape."""

    def test_extracts_subflow_and_apex_names(self):
        flow_metadata = {
            "301A": _flow_metadata_record(
                "301A", "A-1",
                subflows=[("E1", "SubA"), ("E2", "SubB")],
                action_calls=[
                    {"name": "ApexCall", "actionType": "apex",
                     "actionName": "MyApex"},
                    # non-apex actionCall shouldn't appear in apex set
                    {"name": "StdCall", "actionType": "emailSimple",
                     "actionName": "SendEmail"},
                ],
            ),
        }
        subs, apex = main._extract_refs_from_flow_metadata(flow_metadata)
        self.assertEqual(subs, {"SubA", "SubB"})
        self.assertEqual(apex, {"MyApex"})

    def test_tolerates_missing_fields(self):
        """None records, non-dict metadata, missing keys, blank names —
        none of these should raise; they all drop silently."""
        flow_metadata = {
            "301A": None,
            "301B": {"Metadata": None},
            "301C": {"Metadata": "not-a-dict"},
            "301D": {"Metadata": {}},
            "301E": {"Metadata": {
                "subflows": [{"name": "noName"}, "not-a-dict",
                             {"name": "E", "flowName": ""}],
                "actionCalls": [{"actionType": "apex", "actionName": ""},
                                "not-a-dict"],
            }},
        }
        subs, apex = main._extract_refs_from_flow_metadata(flow_metadata)
        self.assertEqual(subs, set())
        self.assertEqual(apex, set())


if __name__ == "__main__":
    unittest.main()
