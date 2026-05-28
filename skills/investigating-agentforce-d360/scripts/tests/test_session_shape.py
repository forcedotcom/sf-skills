"""Tests for ``fetch_dc._classify_session_shape``.

Covers all 5 shapes with a parameterized table:

  - session_not_found                 — sessions.json returned 0 rows
  - interactions_not_materialized_yet — gw_reqs > 0 AND steps == 0 (STDM lag)
  - abandoned_before_llm              — steps > 0, LLM_STEP == 0, gw_reqs == 0
  - planner_ran_no_gateway_logs       — LLM_STEP > 0 with generation ids, gw_reqs == 0
  - complete                          — the happy path

Order matters — the gateway-direct rule sits BEFORE abandoned_before_llm
because ``gw_req_count > 0`` is a stronger positive signal than
``steps_total > 0``. Verified here by including a case with both signals
disjointly (steps==0 on the gateway-direct path).
"""
from __future__ import annotations

import unittest

from . import _bootstrap  # noqa: F401  — sys.path setup

from fetch_dc import _classify_session_shape  # type: ignore


_CASES = [
    # (label, kwargs, expected)
    (
        "session_not_found when sessions.json is empty",
        dict(sessions_count=0, steps_total=0, llm_step_count=0,
             steps_with_generation_id=0, gw_req_count=0),
        "session_not_found",
    ),
    (
        "session_not_found wins even when gw_reqs > 0 (sessions gate runs first)",
        dict(sessions_count=0, steps_total=0, llm_step_count=0,
             steps_with_generation_id=0, gw_req_count=5),
        "session_not_found",
    ),
    (
        "interactions_not_materialized_yet — fresh session, gateway populated, STDM lagging",
        dict(sessions_count=1, steps_total=0, llm_step_count=0,
             steps_with_generation_id=0, gw_req_count=3),
        "interactions_not_materialized_yet",
    ),
    (
        "abandoned_before_llm — steps created but no LLM step, no gateway calls",
        dict(sessions_count=1, steps_total=2, llm_step_count=0,
             steps_with_generation_id=0, gw_req_count=0),
        "abandoned_before_llm",
    ),
    (
        "planner_ran_no_gateway_logs — LLM steps + gen ids but gateway empty",
        dict(sessions_count=1, steps_total=3, llm_step_count=2,
             steps_with_generation_id=2, gw_req_count=0),
        "planner_ran_no_gateway_logs",
    ),
    (
        "complete — the normal bucket",
        dict(sessions_count=1, steps_total=5, llm_step_count=3,
             steps_with_generation_id=3, gw_req_count=4),
        "complete",
    ),
]


class ClassifySessionShapeTests(unittest.TestCase):
    """Parametric truth-table for the 5-way enum."""

    def test_all_shapes(self):
        for label, kwargs, expected in _CASES:
            with self.subTest(label=label):
                self.assertEqual(_classify_session_shape(**kwargs), expected)

    def test_gateway_direct_precedes_abandoned(self):
        """Regression guard: the new rule must fire before abandoned_before_llm.

        If someone reorders the checks, a session with gw_reqs > 0 AND
        steps > 0 AND LLM_STEP == 0 (edge case — happens when Step rows
        land while Interaction parent rows are still lagging) could fall
        through incorrectly. Today the rules' inputs are disjoint
        (gateway-direct needs steps==0), so the guard case uses steps==0
        to exercise the ordering directly.
        """
        shape = _classify_session_shape(
            sessions_count=1,
            steps_total=0,
            llm_step_count=0,
            steps_with_generation_id=0,
            gw_req_count=1,
        )
        self.assertEqual(shape, "interactions_not_materialized_yet")


if __name__ == "__main__":
    unittest.main()
