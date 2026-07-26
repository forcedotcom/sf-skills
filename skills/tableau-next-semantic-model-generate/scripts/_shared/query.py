"""Data 360 SQL query helpers for data-presence checks.

A thin wrapper over the ``/ssot/query-sql`` gateway (see
``sf_api.query_sql_endpoint``) for one job: prove that an object — or a field /
metric — actually returns rows before authoring builds on it. This is a
presence / small-validation path (row counts, a handful of rows), **not** a
query engine: no pagination, no large-result handling.

The HTTP call reuses ``sf_api.sf_post`` + env-var bearer auth. The parsing
helpers (``extract_count``, ``response_has_rows``) are pure functions so they can
be unit-tested against captured response shapes without a network call.
"""

import sys
from typing import Any, Dict, List, Optional, Tuple

from .sf_api import get_credentials, query_sql_endpoint, sf_post


class EmptyDataError(Exception):
    """Raised by assert_has_rows when an object is confirmed to have 0 rows.

    A definite, query-confirmed empty — distinct from an indeterminate count
    (which the gate degrades to a warning rather than raising).
    """

# Completion states that mean the result set is populated and readable. The
# gateway also returns "Running" for an async query whose results aren't ready;
# we treat that as indeterminate rather than empty (see QuerySqlStatus).
_READY_STATUSES = {"Finished", "ResultsProduced"}

# A sane cap for a presence/validation query — never the row source for a viz.
DEFAULT_ROW_LIMIT = 10


def build_query_body(sql: str, row_limit: int = DEFAULT_ROW_LIMIT) -> Dict[str, Any]:
    """Build the (single, un-wrapped) request body for ``/ssot/query-sql``.

    camelCase keys, no double-wrap. ``rowLimit`` must be > 0 per the API.
    """
    if row_limit <= 0:
        row_limit = DEFAULT_ROW_LIMIT
    return {"sql": sql, "rowLimit": row_limit}


def run_sql(
    sql: str,
    row_limit: int = DEFAULT_ROW_LIMIT,
    dataspace: Optional[str] = None,
) -> Tuple[Optional[dict], Optional[str]]:
    """Execute a SQL statement against ``/ssot/query-sql``.

    Returns ``(response_json, error_message)`` — mirrors ``sf_post`` so callers
    can distinguish "ran, here is the result" from "could not run" (the latter
    is *indeterminate*, not *empty*).
    """
    token, instance = get_credentials()
    body = build_query_body(sql, row_limit)
    return sf_post(token, instance, query_sql_endpoint(dataspace), body)


def extract_count(response: Optional[dict]) -> Optional[int]:
    """Pull the scalar from a ``SELECT COUNT(*)`` response.

    The gateway returns ``data`` as an array of bare row arrays (column order
    follows ``metadata``); a count query yields a single cell at ``data[0][0]``.
    Returns the integer count, or ``None`` if the response can't be parsed as a
    count (caller treats ``None`` as indeterminate, never as zero).
    """
    if not isinstance(response, dict):
        return None
    data = response.get("data")
    if not isinstance(data, list) or not data:
        return None
    first = data[0]
    # Rows are bare arrays; defensively accept the spec's {"row": [...]} variant.
    if isinstance(first, dict):
        first = first.get("row")
    if not isinstance(first, list) or not first:
        return None
    value = first[0]
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def response_has_rows(response: Optional[dict]) -> Optional[bool]:
    """Whether a (non-count) query response returned at least one row.

    Returns ``True``/``False`` when the query reached a ready state, or ``None``
    when the state is indeterminate (still ``Running``, or unparseable) so the
    caller can degrade to a warning rather than a false "empty".
    """
    if not isinstance(response, dict):
        return None
    status = (response.get("status") or {}).get("completionStatus")
    # An explicit not-ready status is indeterminate, not empty.
    if status is not None and status not in _READY_STATUSES:
        return None
    returned = response.get("returnedRows")
    if isinstance(returned, int):
        return returned > 0
    data = response.get("data")
    if isinstance(data, list):
        return len(data) > 0
    return None


def count_rows(
    object_name: str,
    dataspace: Optional[str] = None,
) -> Tuple[Optional[int], Optional[str]]:
    """Row count for a DLO/DMO object via ``SELECT COUNT(*)``.

    Returns ``(count, error)``. ``count`` is ``None`` when the count could not
    be obtained (HTTP error, or an unparseable / not-ready response) — an
    *indeterminate* result the caller must distinguish from a real ``0``.
    """
    safe = _quote_identifier(object_name)
    response, err = run_sql(f"SELECT COUNT(*) FROM {safe}", row_limit=1, dataspace=dataspace)
    if err:
        return None, err
    count = extract_count(response)
    if count is None:
        return None, f"Could not parse a row count from the query response for {object_name}"
    return count, None


def query_returns_rows(
    sql_or_object: str,
    dataspace: Optional[str] = None,
    is_object: bool = False,
) -> Tuple[Optional[bool], Optional[str]]:
    """Whether a query (or a bare object) returns any rows.

    Pass a full ``SELECT`` as ``sql_or_object``, or set ``is_object=True`` to
    have a ``SELECT * FROM <object> LIMIT n`` issued for you. Returns
    ``(has_rows, error)`` where ``has_rows`` is ``None`` when indeterminate.
    """
    if is_object:
        sql = f"SELECT * FROM {_quote_identifier(sql_or_object)}"
    else:
        sql = sql_or_object
    response, err = run_sql(sql, row_limit=DEFAULT_ROW_LIMIT, dataspace=dataspace)
    if err:
        return None, err
    has_rows = response_has_rows(response)
    if has_rows is None:
        return None, "Query did not reach a readable state (indeterminate)"
    return has_rows, None


def assert_has_rows(
    object_name: str,
    dataspace: Optional[str] = None,
    warn: bool = True,
) -> bool:
    """Pre-flight data-presence gate: confirm an object has rows before authoring.

    **Field-richness is not data-presence.** An object can have dozens of fields
    and still return zero rows — every widget built on it renders "No results to
    show." Call this before building a viz/dashboard or authoring fields on a
    source.

    Advisory-strict, per the three states a count can land in:

    - **count > 0** → returns ``True`` (proceed).
    - **count == 0** (definite, query-confirmed) → raises ``EmptyDataError``
      (hard block — do not build on a known-empty object).
    - **count indeterminate** (the count query failed / was unreadable) → does
      NOT hard-block: emits a warning to stderr and returns ``False`` so the
      caller can proceed with caution. A transient query failure must not
      false-block a legitimate build.

    Args:
        object_name: DLO/DMO object to check (e.g. ``Account_Home__dll``).
        dataspace: optional dataspace; omit for the org default.
        warn: when True (default), print the warning to stderr on the
            indeterminate path. Set False to stay silent (e.g. under test).

    Returns:
        True when rows are present; False when the count is indeterminate.

    Raises:
        EmptyDataError: when the object is confirmed to have 0 rows.
    """
    count, err = count_rows(object_name, dataspace=dataspace)
    if count is None:
        # Indeterminate — degrade to a warning, never a hard stop.
        if warn:
            print(
                f"Warning: could not confirm data presence for '{object_name}' "
                f"({err}). Proceeding without a data-presence guarantee — verify "
                "the object has rows before trusting the result.",
                file=sys.stderr,
            )
        return False
    if count == 0:
        raise EmptyDataError(
            f"'{object_name}' returned 0 rows. Field-richness is not "
            "data-presence: an object can have many fields and still be empty, "
            "and anything built on it will render 'No results to show.' Pick a "
            "populated source, or confirm the object is materialized before "
            "building. (See empty-source-handling.)"
        )
    return True


def _quote_identifier(name: str) -> str:
    """Double-quote a table identifier unless the caller already quoted it.

    The dialect double-quotes identifiers that are reserved words or contain
    spaces; quoting a plain ``foo__dll`` is harmless and protects odd names.
    A name that already starts with a quote is passed through untouched.
    """
    name = name.strip()
    if name.startswith('"'):
        return name
    return f'"{name}"'
