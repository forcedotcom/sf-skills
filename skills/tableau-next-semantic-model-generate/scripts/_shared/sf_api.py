"""Lightweight Salesforce API helper for Tableau Next authoring scripts.

Reads SF_TOKEN and SF_INSTANCE from environment variables.
Adapted from tabnext-tools-main/backend/lib/salesforce_api.py.
"""

import json
import os
import re
import sys
import time
from typing import Any, Dict, Optional, Tuple

import requests

MAJOR_VERSION = "v67.0"
MINOR_VERSION = "10"


def get_credentials() -> Tuple[str, str]:
    """Return (access_token, instance_url) from environment variables."""
    token = os.environ.get("SF_TOKEN")
    instance = os.environ.get("SF_INSTANCE")
    if not token or not instance:
        print(
            "Error: SF_TOKEN and SF_INSTANCE environment variables are required.\n"
            "Set them with:\n"
            "  export SF_ORG=myorg\n"
            '  export SF_TOKEN=$(sf org auth show-access-token --target-org $SF_ORG --json | jq -r \'.result.accessToken\')\n'
            '  export SF_INSTANCE=$(sf org display --target-org $SF_ORG --json | jq -r \'.result.instanceUrl\')',
            file=sys.stderr,
        )
        sys.exit(1)
    return token, instance.rstrip("/")


# -- Endpoint builders --------------------------------------------------------

def sdm_list_endpoint() -> str:
    return f"/services/data/{MAJOR_VERSION}/ssot/semantic/models"


def sdm_detail_endpoint(sdm_name: str) -> str:
    return f"/services/data/{MAJOR_VERSION}/ssot/semantic/models/{sdm_name}"


def visualization_endpoint(viz_name: Optional[str] = None) -> str:
    base = f"/services/data/{MAJOR_VERSION}/tableau/visualizations"
    if viz_name:
        return f"{base}/{viz_name}?minorVersion={MINOR_VERSION}"
    return f"{base}?minorVersion={MINOR_VERSION}"


def dashboard_endpoint(dashboard_name: Optional[str] = None) -> str:
    base = f"/services/data/{MAJOR_VERSION}/tableau/dashboards"
    if dashboard_name:
        return f"{base}/{dashboard_name}?minorVersion={MINOR_VERSION}"
    return f"{base}?minorVersion={MINOR_VERSION}"


def sdm_create_endpoint() -> str:
    """Endpoint for creating an SDM (POST). Same path as the list endpoint.

    POST /ssot/semantic/models -> 201. No minorVersion.
    """
    return f"/services/data/{MAJOR_VERSION}/ssot/semantic/models"


def sdm_data_objects_endpoint(sdm_name: str) -> str:
    """Endpoint for adding a data object to an SDM (POST).

    POST .../models/{sdm}/data-objects -> 200. No minorVersion.
    """
    return f"/services/data/{MAJOR_VERSION}/ssot/semantic/models/{sdm_name}/data-objects"


def sdm_dimensions_endpoint(sdm_name: str, object_name: str) -> str:
    """Endpoint for adding a base dimension to a data object (POST).

    POST .../data-objects/{obj}/dimensions -> 201. No minorVersion.
    """
    return (
        f"/services/data/{MAJOR_VERSION}/ssot/semantic/models/{sdm_name}"
        f"/data-objects/{object_name}/dimensions"
    )


def sdm_measurements_endpoint(sdm_name: str, object_name: str) -> str:
    """Endpoint for adding a base measure to a data object (POST).

    POST .../data-objects/{obj}/measurements -> 201. No minorVersion.
    """
    return (
        f"/services/data/{MAJOR_VERSION}/ssot/semantic/models/{sdm_name}"
        f"/data-objects/{object_name}/measurements"
    )


def sdm_relationships_endpoint(sdm_name: str) -> str:
    """Endpoint for adding a model-level relationship (join) to an SDM (POST).

    POST .../models/{sdm}/relationships -> 201. No minorVersion.
    """
    return f"/services/data/{MAJOR_VERSION}/ssot/semantic/models/{sdm_name}/relationships"


def semantic_query_endpoint() -> str:
    """Endpoint for the semantic-query gateway (POST, camelCase body).

    POST /semantic-engine/gateway -> 201, status SUCCESS.
    Used to verify a cross-object query spans an authored relationship.
    """
    return f"/services/data/{MAJOR_VERSION}/semantic-engine/gateway"


def query_sql_endpoint(dataspace: Optional[str] = None) -> str:
    """Endpoint for the Data 360 SQL query gateway (POST, camelCase body).

    POST /ssot/query-sql -> 200. No minorVersion. Body is a single, un-wrapped
    object: ``{"sql": "<SELECT ...>", "rowLimit": <int>}`` (PostgreSQL-like Hyper
    SQL; double-quote identifiers that are reserved words or contain spaces).
    The response carries ``data`` (array of bare row arrays, column order
    matching ``metadata``), ``metadata`` (``[{name, type, ...}]``),
    ``returnedRows`` (int), and ``status.completionStatus``
    (``Finished`` | ``ResultsProduced`` | ``Running``).

    Returns only the first chunk — this is a presence/validation path, not a
    query engine (no pagination). ``dataspace`` is an optional query param;
    omit for the org default.
    """
    base = f"/services/data/{MAJOR_VERSION}/ssot/query-sql"
    if dataspace:
        return f"{base}?dataspace={dataspace}"
    return base


def sdm_update_endpoint(sdm_name: str) -> str:
    """Endpoint for the model-level AI-readiness update (PATCH).

    PATCH .../ssot/semantic/models/{sdm} -> 200. No minorVersion. Partial body
    (only the changed allowlist fields); the server merges and echoes the full
    model back. See references/sdm-ai-readiness-api.md §1.
    """
    return f"/services/data/{MAJOR_VERSION}/ssot/semantic/models/{sdm_name}"


def metric_endpoint(sdm_name: str, metric_name: str) -> str:
    """Endpoint for a single metric — GET (resolve) and PUT (full update).

    GET  .../models/{sdm}/metrics/{metric} -> 200 (full metric definition).
    PUT  .../models/{sdm}/metrics/{metric} -> 200 (full-payload replace; omitted
    fields are dropped — re-send the complete definition). No minorVersion.
    See references/sdm-ai-readiness-api.md §3.
    """
    return (
        f"/services/data/{MAJOR_VERSION}/ssot/semantic/models/{sdm_name}"
        f"/metrics/{metric_name}"
    )


def base_field_endpoint(
    sdm_name: str, object_name: str, field_role: str, field_name: str
) -> str:
    """Endpoint for a single base dimension/measurement — GET (resolve) and PUT.

    GET  .../data-objects/{obj}/dimensions|measurements/{field} -> 200.
    PUT  same path -> 200 (full-payload replace). PATCH is NOT allowed (405);
    a raw base-field's description is updated by re-sending its complete
    definition with PUT. No minorVersion.

    Args:
        sdm_name: SDM apiName.
        object_name: data-object apiName (e.g. ``qb_hw_calendar``).
        field_role: ``"dimensions"`` or ``"measurements"``.
        field_name: the base field's apiName.
    """
    if field_role not in ("dimensions", "measurements"):
        raise ValueError(
            f"field_role must be 'dimensions' or 'measurements', got {field_role!r}"
        )
    return (
        f"/services/data/{MAJOR_VERSION}/ssot/semantic/models/{sdm_name}"
        f"/data-objects/{object_name}/{field_role}/{field_name}"
    )


def data_object_endpoint(sdm_name: str, object_name: str) -> str:
    """Endpoint for a single data object — GET (resolve) and PUT (full update).

    GET  .../data-objects/{obj} -> 200 (full object incl. its description).
    PUT  same path -> 200 (full-payload replace). PATCH is NOT allowed (405);
    a data object's description is updated by re-sending its complete definition
    with PUT. No minorVersion. (Distinct from sdm_data_objects_endpoint, which is
    the collection POST for adding an object.)
    """
    return (
        f"/services/data/{MAJOR_VERSION}/ssot/semantic/models/{sdm_name}"
        f"/data-objects/{object_name}"
    )


def calculated_field_endpoint(
    sdm_name: str,
    field_type: str,
    field_name: Optional[str] = None
) -> str:
    """Build calculated field endpoint.

    Args:
        sdm_name: Semantic model API name
        field_type: "measurements", "dimensions", or "metrics"
        field_name: Optional field name for GET/PATCH operations

    Returns:
        Full endpoint path
    """
    endpoint_map = {
        "measurements": "calculated-measurements",
        "dimensions": "calculated-dimensions",
        "metrics": "metrics"
    }

    endpoint_suffix = endpoint_map.get(field_type)
    if not endpoint_suffix:
        raise ValueError(
            f"Invalid field_type '{field_type}'. "
            f"Must be one of: {list(endpoint_map.keys())}"
        )

    base = f"/services/data/{MAJOR_VERSION}/ssot/semantic/models/{sdm_name}/{endpoint_suffix}"
    if field_name:
        return f"{base}/{field_name}"
    return base


# -- HTTP helpers -------------------------------------------------------------

def sf_get(access_token: str, instance_url: str, path: str, timeout: int = 120) -> Optional[dict]:
    """Perform an authenticated GET against the Salesforce REST API."""
    url = f"{instance_url}{path}"
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except requests.Timeout:
        print(f"Error: Request to {path} timed out after {timeout}s", file=sys.stderr)
        return None
    except requests.HTTPError as exc:
        _print_http_error(exc, path)
        return None
    except requests.RequestException as exc:
        print(f"Error: Request to {path} failed: {exc}", file=sys.stderr)
        return None


def sf_post(
    access_token: str,
    instance_url: str,
    path: str,
    payload: dict,
    timeout: int = 120,
) -> Tuple[Optional[dict], Optional[str]]:
    """Perform an authenticated POST against the Salesforce REST API.

    Returns (response_json, error_message).
    """
    url = f"{instance_url}{path}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
        resp.raise_for_status()
        return resp.json(), None
    except requests.Timeout:
        return None, f"Request to {path} timed out after {timeout}s"
    except requests.HTTPError as exc:
        msg = _format_http_error(exc, path)
        return None, msg
    except requests.RequestException as exc:
        return None, f"Request to {path} failed: {exc}"


def sf_delete(
    access_token: str,
    instance_url: str,
    path: str,
    timeout: int = 120,
) -> Tuple[bool, Optional[str]]:
    """Perform an authenticated DELETE against the Salesforce REST API.

    Returns (success, error_message).
    """
    url = f"{instance_url}{path}"
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        resp = requests.delete(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        return True, None
    except requests.Timeout:
        return False, f"Request to {path} timed out after {timeout}s"
    except requests.HTTPError as exc:
        msg = _format_http_error(exc, path)
        return False, msg
    except requests.RequestException as exc:
        return False, f"Request to {path} failed: {exc}"


def sf_patch(
    access_token: str,
    instance_url: str,
    path: str,
    payload: dict,
    timeout: int = 120,
) -> Tuple[Optional[dict], Optional[str]]:
    """Perform an authenticated PATCH against the Salesforce REST API.

    Returns (response_json, error_message).
    """
    url = f"{instance_url}{path}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    try:
        resp = requests.patch(url, headers=headers, json=payload, timeout=timeout)
        resp.raise_for_status()
        return resp.json(), None
    except requests.Timeout:
        return None, f"Request to {path} timed out after {timeout}s"
    except requests.HTTPError as exc:
        msg = _format_http_error(exc, path)
        return None, msg
    except requests.RequestException as exc:
        return None, f"Request to {path} failed: {exc}"


def sf_put(
    access_token: str,
    instance_url: str,
    path: str,
    payload: dict,
    timeout: int = 120,
) -> Tuple[Optional[dict], Optional[str]]:
    """Perform an authenticated PUT against the Salesforce REST API.

    Mirrors ``sf_patch``'s shape. PUT is the full-payload replace verb — used by
    the metric update, where the body must be the COMPLETE metric definition
    (omitted fields are dropped server-side; see metric_endpoint /
    references/sdm-ai-readiness-api.md §3).

    Returns (response_json, error_message).
    """
    url = f"{instance_url}{path}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    try:
        resp = requests.put(url, headers=headers, json=payload, timeout=timeout)
        resp.raise_for_status()
        return resp.json(), None
    except requests.Timeout:
        return None, f"Request to {path} timed out after {timeout}s"
    except requests.HTTPError as exc:
        msg = _format_http_error(exc, path)
        return None, msg
    except requests.RequestException as exc:
        return None, f"Request to {path} failed: {exc}"


_READONLY_ROOT_KEYS = {
    "url", "id", "createdBy", "createdDate", "lastModifiedBy",
    "lastModifiedDate", "permissions", "sourceVersion", "workspaceIdOrApiName",
}

_READONLY_NESTED = {
    "dataSource": {"id", "url"},
    "view": {"id", "url", "isOriginal"},
}


def strip_readonly_fields(payload: dict) -> dict:
    """Remove read-only fields that the API rejects on PATCH."""
    out = {k: v for k, v in payload.items() if k not in _READONLY_ROOT_KEYS}

    for section, keys in _READONLY_NESTED.items():
        if section in out and isinstance(out[section], dict):
            out[section] = {k: v for k, v in out[section].items() if k not in keys}

    if "fields" in out and isinstance(out["fields"], dict):
        out["fields"] = {
            fk: {k: v for k, v in fdef.items() if k != "id"}
            for fk, fdef in out["fields"].items()
        }

    return out


def workspace_endpoint(ws_name: Optional[str] = None) -> str:
    base = f"/services/data/{MAJOR_VERSION}/tableau/workspaces"
    if ws_name:
        return f"{base}/{ws_name}"
    return base


# -- Error interpretation -----------------------------------------------------

# The server's over-length rejection looks like:
#   "... caused by: Description: data value too large: AAAA... (max length=255)"
# Match it so callers can re-surface actionable guidance instead of the raw 400.
_TOO_LARGE_RE = re.compile(
    r"(?:caused by:\s*)?(?P<field>[A-Za-z ]+?):\s*data value too large.*?max length=(?P<max>\d+)",
    re.IGNORECASE | re.DOTALL,
)


def parse_too_large_error(err: Optional[str]) -> Optional[Tuple[Optional[str], Optional[int]]]:
    """Detect the server's 'data value too large (max length=N)' 400.

    Returns ``(field, max_len)`` when ``err`` is a length-cap rejection — ``field``
    is the offending field name (e.g. ``"Description"``) or None if the message
    only carried the generic phrase, and ``max_len`` is the limit (or None).
    Returns ``None`` when ``err`` is not a length-cap error, so callers fall back
    to the raw message. Shared by the update CLIs to translate the cap uniformly.
    """
    if not err:
        return None
    m = _TOO_LARGE_RE.search(err)
    if m:
        return m.group("field").strip(), int(m.group("max"))
    if "data value too large" in err.lower():
        return None, None  # generic phrase, no field/length parsed
    return None  # not a length-cap error at all


# -- Error formatting ---------------------------------------------------------

def _format_http_error(exc: requests.HTTPError, path: str) -> str:
    status = exc.response.status_code
    try:
        body = exc.response.json()
        # Handle array of errors (common in Salesforce API)
        if isinstance(body, list) and body:
            errors = []
            for err in body:
                msg = err.get("message", err.get("errorCode", "Unknown error"))
                fields = err.get("fields", [])
                error_code = err.get("errorCode", "")
                if fields:
                    errors.append(f"{msg} (fields: {', '.join(fields)})")
                elif error_code:
                    errors.append(f"{error_code}: {msg}")
                else:
                    errors.append(msg)
            return f"HTTP {status} on {path}: {'; '.join(errors)}"
        # Handle single error object
        if isinstance(body, dict):
            msg = body.get("message") or body.get("localizedMessage") or body.get("error", "")
            error_code = body.get("errorCode", "")
            fields = body.get("fields", [])
            if fields:
                return f"HTTP {status} on {path}: {error_code}: {msg} (fields: {', '.join(fields)})"
            elif error_code:
                return f"HTTP {status} on {path}: {error_code}: {msg}"
            elif msg:
                return f"HTTP {status} on {path}: {msg}"
    except (ValueError, json.JSONDecodeError):
        pass
    return f"HTTP {status} on {path}: {exc.response.text[:300]}"


def _print_http_error(exc: requests.HTTPError, path: str) -> None:
    print(f"Error: {_format_http_error(exc, path)}", file=sys.stderr)
