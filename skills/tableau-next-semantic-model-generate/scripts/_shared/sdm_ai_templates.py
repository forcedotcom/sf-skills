"""Payload builders for SDM AI-readiness + metric updates.

Two builders, both fixture-pure (no network) so they unit-test cleanly:

- ``build_model_ai_payload(...)`` — the **model-level** AI-readiness PATCH body.
  Emits ONLY the allowlist fields the caller explicitly set (a partial PATCH;
  the server merges onto the existing model). Allowlist mirrors the verified
  REST surface (see references/sdm-ai-readiness-api.md §1).

- ``build_metric_put_payload(existing_metric, changes)`` — the **metric** PUT
  body via resolve-and-merge. Metric update is a FULL-PAYLOAD PUT: the body
  replaces the definition, so a single-field change must re-send the COMPLETE
  metric or `insightsSettings` / `additionalDimensions` / `identifyingDimension`
  are silently dropped. This starts from the full resolved metric, strips the
  server read-only fields, overlays the requested change, and guarantees the
  four required fields (`label`, `measurementReference`, `timeDimensionReference`,
  `insightsSettings`) are present.

The description cap (255 on the RAW input — the server HTML-encodes for storage
but measures what you send) is enforced by the CLI guard in update_sdm.py, not
here; this module only assembles payloads.
"""

from typing import Any, Dict, List, Optional

# The model-level update allowlist — the fields the REST PATCH accepts.
MODEL_AI_ALLOWLIST = (
    "app",
    "sourceCreation",
    "isAiDrafted",
    "queryUnrelatedDataObjects",
    "businessPreferences",
    "description",
    "agentEnabled",
    "currency",
    "label",
    "categories",
)

# Server-assigned read-only fields present on a metric GET that the PUT rejects /
# must not echo back. Strip these before assembling the PUT body.
METRIC_READONLY_FIELDS = (
    "id",
    "createdBy",
    "createdDate",
    "lastModifiedBy",
    "lastModifiedDate",
    "url",
)

# The fields the full-payload metric PUT must always carry (the regression guard:
# omitting any of these drops it server-side). insightsSettings carries the
# identifyingDimension the TN metric UI dereferences on load.
METRIC_REQUIRED_PUT_FIELDS = (
    "label",
    "measurementReference",
    "timeDimensionReference",
    "insightsSettings",
)

# Server-assigned read-only fields on a base dimension/measurement GET to strip
# before the PUT (a base field is updated by full-payload PUT — PATCH is 405).
BASE_FIELD_READONLY_FIELDS = (
    "id",
    "createdBy",
    "createdDate",
    "lastModifiedBy",
    "lastModifiedDate",
    "url",
)

# Read-only / server-derived fields on a data-object GET to strip before the PUT.
# Beyond the usual audit fields, the nested ``*Url`` sub-resource links are
# server-derived. The nested ``semanticDimensions``/``semanticMeasurements``
# arrays are re-sent as-is (the full PUT echoes them back unchanged).
DATA_OBJECT_READONLY_FIELDS = (
    "id",
    "createdBy",
    "createdDate",
    "lastModifiedBy",
    "lastModifiedDate",
    "url",
    "semanticDimensionsUrl",
    "semanticMeasurementsUrl",
)

# Sentinel so a caller can DISTINGUISH "field not provided" (skip it) from
# "field provided as None/empty" (emit it). Plain None means "not provided".
_UNSET = object()


def build_model_ai_payload(
    *,
    agent_enabled: Any = _UNSET,
    description: Any = _UNSET,
    business_preferences: Any = _UNSET,
    categories: Any = _UNSET,
    label: Any = _UNSET,
    app: Any = _UNSET,
    source_creation: Any = _UNSET,
    is_ai_drafted: Any = _UNSET,
    query_unrelated_data_objects: Any = _UNSET,
    currency: Any = _UNSET,
) -> Dict[str, Any]:
    """Build the model-level AI-readiness PATCH body (only the SET fields).

    Every parameter defaults to the ``_UNSET`` sentinel; a field is included in
    the returned payload ONLY when the caller passes it. This keeps the PATCH
    partial — we never null out a field the user did not mention (idempotent:
    re-running with the same inputs yields the same body). Only allowlist fields
    are emitted.

    ``categories`` must be a list (the server stores a JSON array, e.g. ``[]`` or
    ``["Sales"]``) — a comma string is the CLI's job to split before calling.

    Raises:
        ValueError: if no fields were provided (an empty PATCH body is a no-op /
            the server NPEs on a truly empty body).
    """
    payload: Dict[str, Any] = {}

    # Map kwarg -> allowlist key. Order follows MODEL_AI_ALLOWLIST for a stable
    # payload shape.
    candidates = {
        "app": app,
        "sourceCreation": source_creation,
        "isAiDrafted": is_ai_drafted,
        "queryUnrelatedDataObjects": query_unrelated_data_objects,
        "businessPreferences": business_preferences,
        "description": description,
        "agentEnabled": agent_enabled,
        "currency": currency,
        "label": label,
        "categories": categories,
    }
    for key in MODEL_AI_ALLOWLIST:
        value = candidates.get(key, _UNSET)
        if value is not _UNSET:
            payload[key] = value

    if not payload:
        raise ValueError(
            "No fields to update. Provide at least one of: "
            f"{', '.join(MODEL_AI_ALLOWLIST)}."
        )
    return payload


def strip_metric_readonly(metric: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of a resolved metric without the server read-only fields."""
    return {k: v for k, v in metric.items() if k not in METRIC_READONLY_FIELDS}


def _dim_ref_from_spec(spec: str) -> Dict[str, Any]:
    """Parse a ``Field:Object`` (or ``Field``) identifying-dimension spec.

    Cross-object form ``fieldApiName:tableApiName`` -> a tableFieldReference with
    both names. A bare ``fieldApiName`` is rejected — an identifying dimension
    must name its table (the TN metric UI resolves it as ``Table.Field``).

    Raises:
        ValueError: if the spec has no ``:`` separator.
    """
    if ":" not in spec:
        raise ValueError(
            f"Invalid identifying-dimension '{spec}'. Expected 'Field:Object' "
            f"(fieldApiName:tableApiName), e.g. 'position_title:qb_hw_position'."
        )
    field_name, table_name = spec.split(":", 1)
    field_name, table_name = field_name.strip(), table_name.strip()
    if not field_name or not table_name:
        raise ValueError(
            f"Invalid identifying-dimension '{spec}'. Both the field and object "
            f"are required as 'Field:Object'."
        )
    return {"tableFieldReference": {"fieldApiName": field_name, "tableApiName": table_name}}


def build_metric_put_payload(
    existing_metric: Dict[str, Any],
    *,
    identifying_dimension: Optional[str] = None,
    primary_comparison: Optional[str] = None,
    secondary_comparison: Optional[str] = None,
    description: Optional[str] = None,
    extra_changes: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Assemble the full-payload metric PUT body via resolve-and-merge.

    Starts from the COMPLETE resolved metric (``existing_metric``, as returned by
    GET .../metrics/{metric}), strips the server read-only fields, then overlays
    only the requested change(s). The result re-sends the entire definition so
    the PUT (a full replace) never drops ``insightsSettings`` /
    ``additionalDimensions`` / ``identifyingDimension`` — the regression a naive
    partial PUT causes (additionalDimensions dropped to empty).

    Args:
        existing_metric: full metric definition resolved from a GET.
        identifying_dimension: ``Field:Object`` spec. Sets
            ``insightsSettings.identifyingDimension.identifierDimensionReference``.
            The chosen field is also mirrored into ``additionalDimensions`` if not
            already present (the UI requires the identifying dim to be a member).
        primary_comparison / secondary_comparison: top-level time-comparison
            values (siblings of ``timeGrains``); set only when provided.
        description: replace the metric description when provided.
        extra_changes: any further top-level fields to overlay verbatim.

    Returns:
        The complete PUT body (read-only fields stripped, change overlaid,
        required fields guaranteed present).

    Raises:
        ValueError: if the existing metric is missing a required field (so the
            PUT would null it) — the caller passed a non-full resolved metric.
    """
    payload = strip_metric_readonly(dict(existing_metric))

    # Overlay simple top-level changes.
    if description is not None:
        payload["description"] = description
    if primary_comparison is not None:
        payload["primaryTimeComparison"] = primary_comparison
    if secondary_comparison is not None:
        payload["secondaryTimeComparison"] = secondary_comparison
    if extra_changes:
        payload.update(extra_changes)

    # Ensure insightsSettings exists before we touch identifyingDimension.
    insights = dict(payload.get("insightsSettings") or {})

    if identifying_dimension is not None:
        dim_ref = _dim_ref_from_spec(identifying_dimension)
        insights["identifyingDimension"] = {"identifierDimensionReference": dim_ref}
        # The identifying dim MUST be a member of additionalDimensions (superset
        # rule). Mirror it in if absent.
        additional = list(payload.get("additionalDimensions") or [])
        if not _dim_ref_in(dim_ref, additional):
            additional.append(dim_ref)
        payload["additionalDimensions"] = additional
        # Keep insightsDimensionsReferences in sync (mirrors additionalDimensions).
        idr = list(insights.get("insightsDimensionsReferences") or [])
        if not _dim_ref_in(dim_ref, idr):
            idr.append(dim_ref)
        insights["insightsDimensionsReferences"] = idr

    if insights:
        payload["insightsSettings"] = insights

    # Guard: a full PUT must carry the required fields, or the server drops them.
    missing = [f for f in METRIC_REQUIRED_PUT_FIELDS if f not in payload]
    if missing:
        raise ValueError(
            "Metric PUT body is missing required field(s) "
            f"{missing} — the resolved metric was not a full definition. A "
            "full-payload PUT must re-send "
            f"{', '.join(METRIC_REQUIRED_PUT_FIELDS)} or they are dropped "
            "server-side. Fetch the metric via GET .../metrics/{name} first."
        )
    return payload


def strip_base_field_readonly(field: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of a resolved base field without the server read-only fields."""
    return {k: v for k, v in field.items() if k not in BASE_FIELD_READONLY_FIELDS}


def build_base_field_put_payload(
    existing_field: Dict[str, Any],
    *,
    description: Optional[str] = None,
    label: Optional[str] = None,
    extra_changes: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Assemble the full-payload PUT body for a base dimension/measurement.

    A base field's description (and label) is updated by re-sending its COMPLETE
    definition with PUT — PATCH on the sub-resource is rejected (405). This
    starts from the resolved field, strips read-only fields, and overlays the
    change, so the PUT preserves ``dataType`` / ``aggregationType`` /
    ``dataObjectFieldName`` etc. rather than nulling them.

    Args:
        existing_field: full base-field definition resolved from a GET.
        description: replace the field description when provided.
        label: replace the field label when provided.
        extra_changes: any further fields to overlay verbatim.

    Returns:
        The complete PUT body (read-only fields stripped, change overlaid).

    Raises:
        ValueError: if the field's identity (``apiName``) is missing — the caller
            passed a non-full resolved field, so the PUT would be malformed.
    """
    payload = strip_base_field_readonly(dict(existing_field))
    if description is not None:
        payload["description"] = description
    if label is not None:
        payload["label"] = label
    if extra_changes:
        payload.update(extra_changes)
    if not payload.get("apiName"):
        raise ValueError(
            "Base-field PUT body is missing 'apiName' — the resolved field was "
            "not a full definition. Fetch it via GET "
            ".../data-objects/{obj}/dimensions|measurements/{name} first."
        )
    return payload


def strip_data_object_readonly(obj: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of a resolved data object without server read-only fields."""
    return {k: v for k, v in obj.items() if k not in DATA_OBJECT_READONLY_FIELDS}


def build_data_object_put_payload(
    existing_object: Dict[str, Any],
    *,
    description: Optional[str] = None,
    label: Optional[str] = None,
    extra_changes: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Assemble the full-payload PUT body for a data object (description/label).

    A data object's description (and label) is updated by re-sending its COMPLETE
    definition with PUT — PATCH on the sub-resource is rejected (405). This starts
    from the resolved object, strips read-only / server-derived fields (incl. the
    ``*Url`` sub-resource links), and overlays the change — preserving
    ``dataObjectName`` / ``dataObjectType`` / ``tableType`` and the nested field
    arrays.

    Args:
        existing_object: full data-object definition resolved from a GET.
        description: replace the object description when provided.
        label: replace the object label when provided.
        extra_changes: any further fields to overlay verbatim.

    Returns:
        The complete PUT body (read-only fields stripped, change overlaid).

    Raises:
        ValueError: if the object's identity (``apiName``) is missing.
    """
    payload = strip_data_object_readonly(dict(existing_object))
    if description is not None:
        payload["description"] = description
    if label is not None:
        payload["label"] = label
    if extra_changes:
        payload.update(extra_changes)
    if not payload.get("apiName"):
        raise ValueError(
            "Data-object PUT body is missing 'apiName' — the resolved object was "
            "not a full definition. Fetch it via GET .../data-objects/{name} first."
        )
    return payload


def _dim_ref_in(dim_ref: Dict[str, Any], dims: List[Dict[str, Any]]) -> bool:
    """Whether a tableFieldReference dim is already in a dims list (by identity)."""
    target = _dim_key(dim_ref)
    return any(_dim_key(d) == target for d in dims)


def _dim_key(dim: Dict[str, Any]):
    """Comparable identity key for a dimension reference dict."""
    if "tableFieldReference" in dim:
        ref = dim["tableFieldReference"]
        return ("table", ref.get("fieldApiName"), ref.get("tableApiName"))
    if "calculatedFieldApiName" in dim:
        return ("calc", dim["calculatedFieldApiName"])
    return ("raw", repr(sorted(dim.items())))
