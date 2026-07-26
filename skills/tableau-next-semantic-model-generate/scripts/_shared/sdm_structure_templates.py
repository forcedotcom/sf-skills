"""Payload builders for SDM structural authoring (create + add object/field/relationship).

Builds the request bodies for the five SDM-creation operations (see
``skills/tableau-next-semantic-model-generate/references/sdm-creation-api.md``):

1. create SDM (anchor-only)         -> ``build_create_sdm``
2. add data object (incremental)    -> ``build_data_object``
3. add base dimension               -> ``build_base_dimension``
4. add base measure                 -> ``build_base_measure``
5. add relationship (model join)    -> ``build_relationship``

Parallel to ``lib/calc_field_templates.py`` / ``lib/metric_templates.py`` — these
construct payloads only; the CLI scripts (``create_sdm.py``, ``add_data_object.py``,
``add_relationship.py``) own the POSTing and apiName resolution.

Semantic structural endpoints omit ``minorVersion`` and return the body directly.
"""

import re
from typing import Any, Dict, List, Optional, Tuple


# -- apiName / source-name rules ----------------------------------------------

# SDM apiName rule: begin with a letter, alphanumeric + single underscores, no
# trailing underscore, no consecutive "__", 1-80 chars.
SDM_API_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,79}$")

# Data-object source-name suffix -> dataObjectType.
SOURCE_SUFFIX_TO_TYPE = {
    "__dll": "Dlo",  # Data Lake Object
    "__dlm": "Dmo",  # Data Model Object
    "__dlc": "Cio",  # Calculated Insight
}

VALID_DATA_OBJECT_TYPES = set(SOURCE_SUFFIX_TO_TYPE.values())

VALID_CARDINALITIES = {
    "OneToOne",
    "OneToMany",
    "ManyToOne",
    "ManyToMany",
    "Unspecified",
}

# dataType -> allowed base-measure aggregationType.
_NUMERIC_AGGS = {"Sum", "Avg", "Count", "CountDistinct", "Min", "Max"}
_NONNUMERIC_AGGS = {"Count", "CountDistinct", "Min", "Max"}
MEASURE_AGG_ALLOWLIST: Dict[str, set] = {
    "Number": _NUMERIC_AGGS,
    "Percent": _NUMERIC_AGGS,
    "Currency": _NUMERIC_AGGS,
    "Text": _NONNUMERIC_AGGS,
    "Boolean": _NONNUMERIC_AGGS,
    "Date": _NONNUMERIC_AGGS,
    "DateTime": _NONNUMERIC_AGGS,
}


def validate_sdm_api_name(api_name: str) -> Tuple[bool, Optional[str]]:
    """Validate an SDM apiName against the naming rule.

    Returns (is_valid, error_message) — validating client-side so the caller
    never round-trips an obviously invalid name to the server.
    """
    if not api_name:
        return False, "apiName is required."
    if " " in api_name:
        return False, (
            f"apiName '{api_name}' contains a space. The SDM apiName must begin "
            f"with a letter and contain only letters, digits, and single "
            f"underscores (no spaces)."
        )
    if api_name[0].isdigit():
        return False, (
            f"apiName '{api_name}' begins with a digit. The SDM apiName must "
            f"begin with a letter."
        )
    if "__" in api_name:
        return False, (
            f"apiName '{api_name}' contains consecutive underscores. The SDM "
            f"apiName cannot contain two consecutive underscores."
        )
    if api_name.endswith("_"):
        return False, (
            f"apiName '{api_name}' ends with an underscore. The SDM apiName "
            f"cannot end with an underscore."
        )
    if not SDM_API_NAME_RE.match(api_name):
        return False, (
            f"apiName '{api_name}' is invalid. It must begin with a letter and "
            f"contain only letters, digits, and underscores (1-80 chars)."
        )
    return True, None


def infer_data_object_type(data_object_name: str) -> Optional[str]:
    """Infer dataObjectType from the source-name suffix (__dll/__dlm/__dlc)."""
    for suffix, do_type in SOURCE_SUFFIX_TO_TYPE.items():
        if data_object_name.endswith(suffix):
            return do_type
    return None


def validate_data_object_name(data_object_name: str) -> Tuple[bool, Optional[str]]:
    """Validate a data-object source name carries a known type suffix."""
    if infer_data_object_type(data_object_name) is None:
        return False, (
            f"dataObjectName '{data_object_name}' is missing a type suffix. Use "
            f"'__dll' (DLO), '__dlm' (DMO), or '__dlc' (Calculated Insight). "
            f"Bare names are rejected with 'DMO/CI/DLO does not exist'."
        )
    return True, None


def validate_measure_aggregation(
    data_type: str, aggregation_type: str
) -> Tuple[bool, Optional[str]]:
    """Validate a base-measure dataType/aggregationType combo against the allow-list."""
    allowed = MEASURE_AGG_ALLOWLIST.get(data_type)
    if allowed is None:
        return True, None  # unknown dataType — let the server decide
    if aggregation_type not in allowed:
        return False, (
            f"aggregationType '{aggregation_type}' is not valid for a "
            f"'{data_type}' measure. Allowed for {data_type}: "
            f"{', '.join(sorted(allowed))}."
        )
    return True, None


# -- Payload builders ---------------------------------------------------------

def build_data_object(
    api_name: str,
    data_object_name: str,
    label: Optional[str] = None,
    data_object_type: Optional[str] = None,
    table_type: str = "Standard",
    should_include_all_fields: bool = True,
) -> Dict[str, Any]:
    """Build a data-object payload (anchor or incremental add).

    Args:
        api_name: SDM-level object apiName (e.g. "qb_hw_employee").
        data_object_name: source name with type suffix (e.g. "qb_hw_employee__dlm").
        label: display label (defaults to api_name).
        data_object_type: "Dlo"/"Dmo"/"Cio" (inferred from suffix if omitted).
        table_type: "Standard" (default).
        should_include_all_fields: bind every source column (auto-suffixes apiNames).

    Returns the object dict used both as ``semanticDataObjects[0]`` in a create
    payload and as the body of an add-data-object POST.
    """
    resolved_type = data_object_type or infer_data_object_type(data_object_name)
    return {
        "apiName": api_name,
        "label": label or api_name,
        "dataObjectName": data_object_name,
        "dataObjectType": resolved_type,
        "tableType": table_type,
        "shouldIncludeAllFields": should_include_all_fields,
    }


def build_create_sdm(
    api_name: str,
    label: str,
    anchor: Dict[str, Any],
    dataspace: str = "default",
    description: str = "",
) -> Dict[str, Any]:
    """Build a create-SDM payload with a single anchor data object.

    Args:
        api_name: SDM apiName (validate with validate_sdm_api_name first).
        label: SDM display label.
        anchor: a data-object dict from build_data_object().
        dataspace: "default" unless multi-dataspace.
        description: optional model description.

    Returns the POST body for ``/ssot/semantic/models``.
    """
    payload: Dict[str, Any] = {
        "apiName": api_name,
        "label": label,
        "dataspace": dataspace,
        "semanticDataObjects": [anchor],
    }
    if description:
        payload["description"] = description
    return payload


def build_base_dimension(
    api_name: str,
    data_object_field_name: str,
    label: Optional[str] = None,
    data_type: str = "Text",
    display_category: str = "Discrete",
    description: str = "",
) -> Dict[str, Any]:
    """Build a base (non-calc) dimension payload with a caller-controlled apiName.

    Binding a single field by hand preserves ``apiName`` verbatim (no auto-suffix),
    unlike ``shouldIncludeAllFields``. ``data_object_field_name`` is the raw source
    column (e.g. "position_title__c").
    """
    payload: Dict[str, Any] = {
        "apiName": api_name,
        "label": label or api_name,
        "dataObjectFieldName": data_object_field_name,
        "dataType": data_type,
        "displayCategory": display_category,
    }
    if description:
        payload["description"] = description
    return payload


def build_base_measure(
    api_name: str,
    data_object_field_name: str,
    label: Optional[str] = None,
    data_type: str = "Number",
    aggregation_type: str = "Sum",
    decimal_place: int = 2,
    display_category: str = "Continuous",
    description: str = "",
) -> Dict[str, Any]:
    """Build a base (non-calc) measure payload with a caller-controlled apiName.

    ``data_object_field_name`` is the raw source column. Validate the
    dataType/aggregationType combo with validate_measure_aggregation first.
    """
    payload: Dict[str, Any] = {
        "apiName": api_name,
        "label": label or api_name,
        "dataObjectFieldName": data_object_field_name,
        "dataType": data_type,
        "aggregationType": aggregation_type,
        "decimalPlace": decimal_place,
        "displayCategory": display_category,
    }
    if description:
        payload["description"] = description
    return payload


def build_join_criterion(
    left_field_api_name: str,
    right_field_api_name: str,
    join_operator: str = "Equals",
    left_field_type: str = "TableField",
    right_field_type: str = "TableField",
) -> Dict[str, Any]:
    """Build one relationship criterion using resolved semantic apiNames.

    The field references MUST be the resolved (server-assigned) semantic apiNames
    (e.g. "position_id2"), NOT the raw "__c" source column (which fails with
    "field could not be found").
    """
    return {
        "joinOperator": join_operator,
        "leftFieldType": left_field_type,
        "leftSemanticFieldApiName": left_field_api_name,
        "rightFieldType": right_field_type,
        "rightSemanticFieldApiName": right_field_api_name,
    }


def build_relationship(
    api_name: str,
    label: str,
    left_object: str,
    right_object: str,
    criteria: List[Dict[str, Any]],
    cardinality: str = "ManyToOne",
    join_type: str = "Auto",
) -> Dict[str, Any]:
    """Build a model-level relationship (join) payload.

    Args:
        api_name: relationship apiName.
        label: REQUIRED display label (server rejects an empty label).
        left_object / right_object: the two SDM-level data-object apiNames.
        criteria: list of build_join_criterion() dicts.
        cardinality: OneToOne/OneToMany/ManyToOne/ManyToMany/Unspecified.
        join_type: "Auto" for model-level joins (the only valid value here).

    Returns the POST body for ``/ssot/semantic/models/{sdm}/relationships``.
    """
    return {
        "apiName": api_name,
        "label": label,
        "joinType": join_type,
        "cardinality": cardinality,
        "leftSemanticDefinitionApiName": left_object,
        "rightSemanticDefinitionApiName": right_object,
        "criteria": criteria,
    }


def validate_relationship(payload: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate a relationship payload against the documented rules.

    Catches the most common errors pre-POST: empty label, non-Auto joinType,
    bad cardinality, missing/empty criteria, and a raw "__c" source-column
    reference (the #1 relationship error).
    """
    errors: List[str] = []

    if not payload.get("label"):
        errors.append(
            "label is REQUIRED for a relationship (the schema marks it optional, "
            "but the server rejects an empty label)."
        )
    if payload.get("joinType") != "Auto":
        errors.append(
            f"joinType must be 'Auto' for a model-level relationship (got "
            f"'{payload.get('joinType')}'). Left/Right/Inner/Full are valid only "
            f"inside a logical view (out of scope)."
        )
    cardinality = payload.get("cardinality")
    if cardinality not in VALID_CARDINALITIES:
        errors.append(
            f"cardinality '{cardinality}' is invalid. Use one of: "
            f"{', '.join(sorted(VALID_CARDINALITIES))}."
        )

    criteria = payload.get("criteria") or []
    if not criteria:
        errors.append("criteria[] must contain at least one join condition.")
    for crit in criteria:
        for side in ("leftSemanticFieldApiName", "rightSemanticFieldApiName"):
            field_ref = crit.get(side, "")
            if not field_ref:
                errors.append(f"criteria.{side} is required.")
            elif field_ref.endswith("__c"):
                errors.append(
                    f"criteria.{side} '{field_ref}' looks like a raw source "
                    f"column (ends with '__c'). Use the resolved semantic "
                    f"apiName instead (e.g. from discover_sdm.py --json) — a "
                    f"'__c' reference fails with 'field could not be found'."
                )

    return len(errors) == 0, errors
