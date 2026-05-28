"""Tests for the `gateway_requests_dropped_by_stdm` session_shape enum value.

This is the case where LLM_STEPs ran but neither gateway_requests nor
generations wrote (frequently observed on Atlas-routed sessions where
the STDM exporter dropped writes).
"""
from __future__ import annotations

import unittest

from . import _bootstrap  # noqa: F401  — sys.path setup

from fetch_dc import _classify_session_shape  # type: ignore


class ClassifySessionShapeTests(unittest.TestCase):
    """All 6 shapes plus disambiguation between the two zero-gw shapes."""

    def test_session_not_found_when_zero_sessions(self):
        out = _classify_session_shape(
            sessions_count=0, steps_total=0, llm_step_count=0,
            steps_with_generation_id=0, gw_req_count=0,
        )
        self.assertEqual(out, "session_not_found")

    def test_interactions_not_materialized_when_gw_present_steps_empty(self):
        out = _classify_session_shape(
            sessions_count=1, steps_total=0, llm_step_count=0,
            steps_with_generation_id=0, gw_req_count=5,
        )
        self.assertEqual(out, "interactions_not_materialized_yet")

    def test_abandoned_before_llm_when_steps_present_no_llm(self):
        out = _classify_session_shape(
            sessions_count=1, steps_total=3, llm_step_count=0,
            steps_with_generation_id=0, gw_req_count=0,
        )
        self.assertEqual(out, "abandoned_before_llm")

    def test_gateway_requests_dropped_by_stdm_when_llm_steps_no_gens_no_gw(self):
        """LLM_STEPs ran, but neither generations nor gateway_requests
        wrote. STDM exporter dropped both — frequently observed on
        Atlas-routed sessions."""
        out = _classify_session_shape(
            sessions_count=1, steps_total=10, llm_step_count=4,
            steps_with_generation_id=0, gw_req_count=0,
        )
        self.assertEqual(out, "gateway_requests_dropped_by_stdm")

    def test_planner_ran_no_gateway_logs_when_gens_present_gw_absent(self):
        """Distinct from the new STDM-drop shape: generations DID write,
        gateway_requests didn't. Narrower defect."""
        out = _classify_session_shape(
            sessions_count=1, steps_total=10, llm_step_count=4,
            steps_with_generation_id=4, gw_req_count=0,
        )
        self.assertEqual(out, "planner_ran_no_gateway_logs")

    def test_complete_when_everything_present(self):
        out = _classify_session_shape(
            sessions_count=1, steps_total=10, llm_step_count=4,
            steps_with_generation_id=4, gw_req_count=4,
        )
        self.assertEqual(out, "complete")

    def test_new_shape_takes_priority_over_planner_ran_no_gateway_logs(self):
        """When steps_with_generation_id == 0 (and other guards align),
        the new gateway_requests_dropped_by_stdm shape catches the case
        before planner_ran_no_gateway_logs's stricter check."""
        out_drop = _classify_session_shape(
            sessions_count=1, steps_total=10, llm_step_count=4,
            steps_with_generation_id=0, gw_req_count=0,
        )
        self.assertEqual(out_drop, "gateway_requests_dropped_by_stdm")
        # Single-row diff — set steps_with_generation_id > 0 — picks the
        # other shape, confirming the two are distinguishable.
        out_logs = _classify_session_shape(
            sessions_count=1, steps_total=10, llm_step_count=4,
            steps_with_generation_id=4, gw_req_count=0,
        )
        self.assertEqual(out_logs, "planner_ran_no_gateway_logs")


if __name__ == "__main__":
    unittest.main()
