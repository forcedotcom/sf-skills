"""Verify a calculated field / metric returns data, via the semantic engine.

A calc field (``_clc``) or metric (``_mtc``) is defined at the SDM layer, so its
"does this actually return data?" check goes through the semantic-engine gateway
(``sf_api.semantic_query_endpoint``), not the raw ``/ssot/query-sql`` path used
for object row counts. This is the post-create verify step: after a create
succeeds, confirm the new field/metric returns non-empty data before declaring
it done — and STOP (do not proceed to dashboards) when it is genuinely empty.

The gateway takes a camelCase ``structuredSemanticQuery`` body and returns a
top-level ``status: "SUCCESS"`` with ``queryResults.queryData.rows``. The HTTP call reuses
``sf_api.sf_post``; the parsing helper is a pure function for unit testing.
"""

import sys
from typing import Any, Dict, Optional, Tuple

from .sf_api import get_credentials, semantic_query_endpoint, sf_post

# A handful of rows is enough to prove non-empty; this is a verify, not a report.
VERIFY_LIMIT = 5


def build_calc_field_query(
    sdm_api_name: str,
    calculated_field_api_name: str,
    limit: int = VERIFY_LIMIT,
) -> Dict[str, Any]:
    """Build a semantic query that selects a single calculated field.

    Uses the ``calculatedField`` expression shape (calc fields are model-level,
    addressed by name with no table). camelCase, single-wrap.
    """
    return {
        "semanticModelApiName": sdm_api_name,
        "structuredSemanticQuery": {
            "fields": [
                {
                    "expression": {"calculatedField": {"name": calculated_field_api_name}},
                    "alias": "verify_value",
                }
            ],
            "options": {"limitOptions": {"limit": limit}},
        },
    }


def build_metric_query(
    sdm_api_name: str,
    metric_api_name: str,
    time_grain: str = "Month",
) -> Dict[str, Any]:
    """Build a metric-driven query (structuredMetricQuery).

    Querying a defined metric directly lets the engine resolve the metric's
    measure + time dimension, so the verify doesn't have to re-address fields.
    """
    return {
        "semanticModelApiName": sdm_api_name,
        "structuredMetricQuery": {
            "submetricDefinition": {"metricApiName": metric_api_name},
            "timeGrain": time_grain,
        },
    }


def semantic_query_returned_rows(response: Optional[dict]) -> Optional[bool]:
    """Whether a semantic-engine response carried at least one data row.

    Returns ``True``/``False`` when the query succeeded, or ``None`` when the
    result is indeterminate (no SUCCESS status / unparseable) so the caller can
    degrade to "inconclusive" rather than claiming a false empty.
    """
    if not isinstance(response, dict):
        return None
    if response.get("status") != "SUCCESS":
        return None
    query_results = response.get("queryResults")
    if not isinstance(query_results, dict) or "queryData" not in query_results:
        # SUCCESS but no queryData block at all — can't read it, indeterminate.
        return None
    # A successful query with queryData present is readable. An empty-source
    # metric/field returns queryData={} (or rows=[]) — that is a DEFINITE empty,
    # not indeterminate: the query ran fine, there is simply no data.
    rows = query_results.get("queryData", {}).get("rows")
    if not isinstance(rows, list):
        return False
    # A row counts as data only if it has at least one non-null value.
    for row in rows:
        values = row.get("values") if isinstance(row, dict) else None
        if isinstance(values, list) and any(v is not None for v in values):
            return True
    return False


def post_semantic_query(body: Dict[str, Any]) -> Tuple[Optional[dict], Optional[str]]:
    """POST a structured semantic query to the gateway. Returns (json, error)."""
    token, instance = get_credentials()
    return sf_post(token, instance, semantic_query_endpoint(), body)


def verify_calc_field_has_data(
    sdm_api_name: str,
    calculated_field_api_name: str,
) -> Tuple[Optional[bool], Optional[str]]:
    """Query a calc field and report whether it returned non-empty data.

    Returns ``(has_data, error)``. ``has_data`` is ``None`` when the check is
    indeterminate (query failed / inconclusive) — distinct from a real empty.
    """
    body = build_calc_field_query(sdm_api_name, calculated_field_api_name)
    response, err = post_semantic_query(body)
    if err:
        return None, err
    has_data = semantic_query_returned_rows(response)
    if has_data is None:
        return None, "Verify query did not return a readable SUCCESS result"
    return has_data, None


def verify_metric_has_data(
    sdm_api_name: str,
    metric_api_name: str,
    time_grain: str = "Month",
) -> Tuple[Optional[bool], Optional[str]]:
    """Query a metric and report whether it returned non-empty data.

    Returns ``(has_data, error)`` with the same indeterminate semantics as
    ``verify_calc_field_has_data``.
    """
    body = build_metric_query(sdm_api_name, metric_api_name, time_grain)
    response, err = post_semantic_query(body)
    if err:
        return None, err
    has_data = semantic_query_returned_rows(response)
    if has_data is None:
        return None, "Verify query did not return a readable SUCCESS result"
    return has_data, None


def report_verification(
    kind: str,
    api_name: str,
    has_data: Optional[bool],
    err: Optional[str],
    stream=None,
    created: bool = True,
) -> int:
    """Print a verification verdict and return a process exit code.

    - has_data True  → verified-done (exit 0)
    - has_data False → NOT-shippable, genuine empty (exit 1; do not proceed)
    - has_data None  → inconclusive (exit 0, but warn — verification couldn't run)

    The caller uses the return value as its exit code so an empty field/metric
    never reports success. ``created`` controls the wording: True after a fresh
    create, False for a --verify-only re-check of an existing field/metric.
    """
    # Resolve at call time (not import time) so a redirected sys.stderr is honored.
    if stream is None:
        stream = sys.stderr
    if has_data is True:
        print(f"✓ Verified: {kind} '{api_name}' returns data.", file=stream)
        return 0
    if has_data is False:
        lead = "was created but returns" if created else "returns"
        print(
            f"✗ NOT shippable: {kind} '{api_name}' {lead} NO data. "
            "Do not build dashboards on it — investigate the source/expression "
            "(see empty-source-handling) before using it.",
            file=stream,
        )
        return 1
    # Indeterminate — could not confirm data.
    verb = "Created" if created else "Checked"
    print(
        f"⚠ {verb} {kind} '{api_name}', but could not verify it returns data "
        f"({err}). Treat as unconfirmed: verify before building on it.",
        file=stream,
    )
    return 0
