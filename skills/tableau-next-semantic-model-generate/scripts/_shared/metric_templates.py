"""Template library and payload builders for semantic metrics.

Provides common formula templates and functions to build semantic metric
payloads for Salesforce Tableau Next API.

Semantic metrics are simpler than calculated measurements - they only require
apiName, label, and expression (no aggregationType, dataType, decimalPlace, etc.).
"""

import re
from typing import Dict, List, Optional, Tuple


# -- Junk-date guard ------------------------------------------------------------
# A metric's time anchor must be a business-meaningful event date (Close_Date,
# Created_Date, Order_Date...). Anchoring on a system/plumbing column produces a
# metric whose time series tracks data-pipeline events, not the business — a
# silent correctness bug. These patterns match the non-business columns Data
# Cloud and ingestion add; matching is case-insensitive on the field apiName.
_JUNK_DATE_PATTERNS = (
    r"^cdp_sys_",        # cdp_sys_PartitionDate, cdp_sys_* plumbing columns
    r"_?partitiondate$",  # partition / load partitioning dates
    r"sourceversion",    # *_SourceVersion ingest-version timestamps
    r"^kq_",             # KQ_* Data Cloud key-qualifier system fields
    r"(^|_)(load|ingest|ingestion|sys|system)_?(date|time|timestamp|ts)$",
    r"datasource(object)?__c$",  # connector bookkeeping columns
)


def is_junk_date_field(field_name: str) -> bool:
    """Whether a field apiName looks like a non-business (plumbing) date.

    True for system/load/ingest columns (e.g. ``cdp_sys_PartitionDate``,
    ``X_SourceVersion``) that must not be used as a metric's time anchor.
    """
    if not field_name:
        return False
    name = field_name.strip().lower()
    return any(re.search(p, name) for p in _JUNK_DATE_PATTERNS)


# -- Template Functions ---------------------------------------------------------

def sum_metric(field: str) -> str:
    """Generate sum aggregation formula.

    Args:
        field: Field name to sum

    Returns:
        Tableau formula string
    """
    return f"SUM([{field}])"


def avg_metric(field: str) -> str:
    """Generate average aggregation formula.

    Args:
        field: Field name to average

    Returns:
        Tableau formula string
    """
    return f"AVG([{field}])"


def count_metric(field: str) -> str:
    """Generate count aggregation formula.

    Args:
        field: Field name to count

    Returns:
        Tableau formula string
    """
    return f"COUNT([{field}])"


def win_rate_metric(won_field: str, total_field: str) -> str:
    """Generate win rate formula.

    Args:
        won_field: Field name for won count
        total_field: Field name for total count

    Returns:
        Tableau formula string
    """
    return f"SUM([{won_field}]) / SUM([{total_field}])"


def conversion_rate_metric(converted_field: str, total_field: str) -> str:
    """Generate conversion rate formula.

    Args:
        converted_field: Field name for converted count
        total_field: Field name for total count

    Returns:
        Tableau formula string
    """
    return f"SUM([{converted_field}]) / SUM([{total_field}])"


def weighted_pipeline_metric(amount_field: str, probability_field: str) -> str:
    """Generate weighted pipeline value formula.

    Args:
        amount_field: Field name for amount
        probability_field: Field name for probability (0-1)

    Returns:
        Tableau formula string
    """
    return f"SUM([{amount_field}] * [{probability_field}])"


def sales_cycle_metric(start_field: str, end_field: str) -> str:
    """Generate sales cycle (days between) formula.

    Args:
        start_field: Start date field name
        end_field: End date field name

    Returns:
        Tableau formula string
    """
    return f"AVG(DATEDIFF('day', [{start_field}], [{end_field}]))"


# -- Filters -------------------------------------------------------------------

# Operators accepted in --filter specs, mapped to the metric filters[] operator
# enum. The enum was confirmed live against a real org:
# the server accepts the CamelCase forms below and REJECTS SQL-style names
# (EQUAL, GREATER_THAN_OR_EQUAL, NOT_EQUAL) and has NO >=, <=, or != operator.
# Both symbolic shortcuts and the canonical names are accepted as input.
FILTER_OPERATORS = {
    # equality
    "=": "Equals",
    "==": "Equals",
    "EQUALS": "Equals",
    # comparisons (no >= / <= on the server; only strict GT/LT and Between)
    ">": "GreaterThan",
    "GREATERTHAN": "GreaterThan",
    "<": "LessThan",
    "LESSTHAN": "LessThan",
    "BETWEEN": "Between",
    # set / string membership
    "IN": "In",
    "NOTIN": "NotIn",
    "CONTAINS": "Contains",
    "NOTCONTAINS": "NotContains",
    "STARTSWITH": "StartsWith",
}


def parse_metric_filter(spec: str) -> Dict:
    """Parse a ``"<Table>.<Field> <op> <value>"`` filter spec into a filters[] entry.

    Metric filter fields MUST be fully qualified (``Table.Field``); a bare
    field name makes the metric unqueryable with the server error
    ``Metric Definition Filter Field <Field> is not found in Metric
    Definition``. We reject bare fields up front.

    Args:
        spec: e.g. ``"Opportunity.Region = West"`` or ``"Opportunity.Amount > 1000"``

    Returns:
        The ``filters[]`` dict (``fieldName`` qualified, ``operator``, ``values``).

    Raises:
        ValueError: if the spec is malformed, unqualified, or uses an unknown operator.
    """
    parts = spec.split(None, 2)
    if len(parts) < 3:
        raise ValueError(
            f"Invalid --filter '{spec}'. Expected '<Table>.<Field> <op> <value>' "
            f"(e.g. 'Opportunity.Region = West')."
        )
    qualified_field, op, value = parts[0], parts[1], parts[2]

    if "." not in qualified_field:
        raise ValueError(
            f"Metric filter field '{qualified_field}' must be fully qualified as "
            f"'Table.Field'. A bare field name makes the metric unqueryable "
            f"(server error: 'Metric Definition Filter Field {qualified_field} is "
            f"not found in Metric Definition')."
        )

    op_key = op.upper() if op.upper() in FILTER_OPERATORS else op
    if op_key not in FILTER_OPERATORS:
        raise ValueError(
            f"Unsupported filter operator '{op}'. Supported: "
            f"{', '.join(sorted(FILTER_OPERATORS))}."
        )

    return {
        "fieldName": qualified_field,
        "operator": FILTER_OPERATORS[op_key],
        "values": [value],
    }


def _filter_field_to_dim_ref(field_name: str) -> Optional[Dict]:
    """Build an additionalDimensions-shaped ref from a qualified ``Table.Field``."""
    if "." not in field_name:
        return None
    table_name, fld = field_name.split(".", 1)
    return {"tableFieldReference": {"fieldApiName": fld, "tableApiName": table_name}}


def _filter_field_to_dim_key(field_name: str) -> Optional[Tuple]:
    """Map a ``filters[].fieldName`` (``Table.Field``) to a dim identity key."""
    if "." not in field_name:
        return None
    table_name, fld = field_name.split(".", 1)
    return ("table", fld, table_name)


def validate_additional_dimensions_superset(payload: Dict) -> None:
    """Enforce the additionalDimensions superset rule on an assembled payload.

    Every field referenced by ``insightsSettings.identifyingDimension``, each
    ``insightsSettings.insightsDimensionsReferences[]`` entry, and each
    ``filters[].fieldName`` MUST appear in top-level ``additionalDimensions[]``.

    Two distinct server failure modes this guards (quoted in the message):
    - Insight/identifying dims missing fail at *create*:
      ``Validation Failed: ... Insight dimension (<Table>.<Field>) is missing
      from the metric additional dimensions.``
    - Filter fields missing succeed at create but make the metric *unqueryable*:
      ``Metric Definition Filter Field <Field> is not found in Metric
      Definition.``

    Raises:
        ValueError: naming the offending field, quoting the server's text.
    """
    additional = payload.get("additionalDimensions", []) or []
    present = {_dim_ref_key(d) for d in additional}

    insights = payload.get("insightsSettings", {}) or {}

    # identifyingDimension
    ident = insights.get("identifyingDimension", {})
    ref = ident.get("identifierDimensionReference")
    if ref and _dim_ref_key(ref) not in present:
        field = _describe_dim_ref(ref)
        raise ValueError(
            f"Identifying dimension ({field}) is missing from the metric "
            f"additional dimensions. Add it to additionalDimensions "
            f"(server error: 'Insight dimension ({field}) is missing from the "
            f"metric additional dimensions')."
        )

    # insightsDimensionsReferences[]
    for dref in insights.get("insightsDimensionsReferences", []) or []:
        if _dim_ref_key(dref) not in present:
            field = _describe_dim_ref(dref)
            raise ValueError(
                f"Insight dimension ({field}) is missing from the metric "
                f"additional dimensions. Add it to additionalDimensions."
            )

    # filters[].fieldName
    for filt in payload.get("filters", []) or []:
        field_name = filt.get("fieldName", "")
        key = _filter_field_to_dim_key(field_name)
        if key is None or key not in present:
            bare = field_name.split(".", 1)[-1] if field_name else field_name
            raise ValueError(
                f"Filter field '{field_name}' is missing from the metric "
                f"additional dimensions; the metric would be unqueryable "
                f"(server error: 'Metric Definition Filter Field {bare} is not "
                f"found in Metric Definition'). Mirror it into "
                f"additionalDimensions."
            )


def _describe_dim_ref(ref: Dict) -> str:
    """Human-readable ``Table.Field`` (or calc name) for an error message."""
    if "tableFieldReference" in ref:
        t = ref["tableFieldReference"]
        return f"{t.get('tableApiName')}.{t.get('fieldApiName')}"
    if "calculatedFieldApiName" in ref:
        return ref["calculatedFieldApiName"]
    return repr(ref)


# -- Payload Builder -----------------------------------------------------------

def _dim_ref_key(dim: Dict) -> Tuple:
    """Return a comparable identity key for a dimension reference dict.

    Dimension references come in two shapes: a raw/table field
    (``{"tableFieldReference": {"fieldApiName", "tableApiName"}}``) or a calc
    field (``{"calculatedFieldApiName": ...}``). The key lets us de-dupe and
    membership-test dims regardless of surrounding dict structure.
    """
    if "tableFieldReference" in dim:
        ref = dim["tableFieldReference"]
        return ("table", ref.get("fieldApiName"), ref.get("tableApiName"))
    if "calculatedFieldApiName" in dim:
        return ("calc", dim["calculatedFieldApiName"])
    return ("raw", repr(sorted(dim.items())))


def build_default_insights_settings(
    additional_dimensions: Optional[List[Dict]] = None,
    sentiment: str = "SentimentTypeUpIsGood",
    identifying_dimension: Optional[Dict] = None,
) -> Dict[str, any]:
    """Build default insightsSettings structure based on collection patterns.

    Args:
        additional_dimensions: List of dimension references (optional)
        sentiment: Sentiment value (default: "SentimentTypeUpIsGood")
        identifying_dimension: Dimension reference (same shape as an
            additionalDimensions entry) used as the metric's identifying
            dimension. When provided, emit
            ``identifyingDimension.identifierDimensionReference`` — the Tableau
            Next metric UI dereferences this on load and crashes if it is
            absent (Feature 1).

    Returns:
        Complete insightsSettings dict
    """
    insights_dimensions_refs = []
    if additional_dimensions:
        # Match insightsDimensionsReferences to additionalDimensions
        for dim in additional_dimensions:
            if "tableFieldReference" in dim:
                insights_dimensions_refs.append({
                    "tableFieldReference": dim["tableFieldReference"]
                })

    settings: Dict[str, any] = {
        "insightTypes": [
            {"enabled": False, "type": "TopContributors"},
            {"enabled": False, "type": "ComparisonToExpectedRangeAlert"},
            {"enabled": True, "type": "TrendChangeAlert"},
            {"enabled": True, "type": "BottomContributors"},
            {"enabled": True, "type": "ConcentratedContributionAlert"},
            {"enabled": True, "type": "TopDrivers"},
            {"enabled": True, "type": "TopDetractors"},
            {"enabled": True, "type": "CurrentTrend"},
            {"enabled": False, "type": "OutlierDetection"},
            {"enabled": False, "type": "RecordLevelTable"}
        ],
        "insightsDimensionsReferences": insights_dimensions_refs,
        "pluralNoun": "",
        "sentiment": sentiment,
        "singularNoun": ""
    }

    # The TN metric UI dereferences insightsSettings.identifyingDimension on
    # load; emit it whenever we have a dimension to identify the metric by.
    if identifying_dimension:
        settings["identifyingDimension"] = {
            "identifierDimensionReference": identifying_dimension
        }

    return settings


def build_semantic_metric(
    api_name: str,
    label: str,
    calculated_field_api_name: str,
    time_dimension_field_name: str,
    time_dimension_table_name: str,
    description: str = "",
    aggregation_type: str = "UserAgg",
    filters: Optional[List[Dict]] = None,
    is_cumulative: bool = False,
    is_goal_editing_blocked: bool = False,
    time_grains: Optional[List[str]] = None,
    additional_dimensions: Optional[List[Dict]] = None,
    insights_settings: Optional[Dict[str, any]] = None,
    sentiment: str = "SentimentTypeUpIsGood",
    identifying_dimension: Optional[Dict] = None,
    allow_junk_time_anchor: bool = False,
) -> Dict[str, any]:
    """Build semantic metric payload.

    Semantic metrics reference calculated fields via measurementReference.
    Based on production examples (HR_Workforce1_package, Sales_Cloud12_package), metrics use:
    - measurementReference.calculatedFieldApiName (not expression)
    - aggregationType: "UserAgg"
    - timeDimensionReference (required)
    - timeGrains (required)
    - additionalDimensions (optional, for breakdown analysis)
    - insightsSettings (optional, auto-generated from additionalDimensions if not provided)
    - filters, isCumulative, isGoalEditingBlocked

    Args:
        api_name: API name (must end with _mtc)
        label: Display label
        calculated_field_api_name: API name of calculated field to reference
        time_dimension_field_name: Time dimension field API name (e.g., "Close_Date")
        time_dimension_table_name: Time dimension table API name (e.g., "Opportunity_TAB_Sales_Cloud")
        description: Optional field description
        aggregation_type: Aggregation type (default: "UserAgg")
        filters: Optional list of filter dictionaries
        is_cumulative: Whether metric is cumulative (default: False)
        is_goal_editing_blocked: Whether goal editing is blocked (default: False)
        time_grains: List of time grains (default: ["Day", "Week", "Month", "Quarter", "Year"])
        additional_dimensions: Optional list of dimension references for breakdown analysis
        insights_settings: Optional insightsSettings dict (auto-generated if not provided)
        sentiment: Sentiment value (default: "SentimentTypeUpIsGood")
        identifying_dimension: Optional dimension reference (same shape as an
            additionalDimensions entry) to use as the identifying dimension.
            Defaults to the first additionalDimensions entry. The chosen field
            is mirrored into additionalDimensions if not already present (the
            UI requires the identifying dimension to be an additional
            dimension). If there are no additional dimensions and no override,
            identifyingDimension is omitted (a no-breakdown metric needs none).

    Returns:
        Complete semantic metric payload dict
    """
    if time_grains is None:
        time_grains = ["Day", "Week", "Month", "Quarter", "Year"]

    # Guard the time anchor: a metric anchored on a system/plumbing date tracks
    # pipeline events, not the business. Reject by default; allow_junk_time_anchor
    # is the explicit escape hatch for the rare case the column really is the
    # intended anchor.
    if not allow_junk_time_anchor and is_junk_date_field(time_dimension_field_name):
        raise ValueError(
            f"Time anchor '{time_dimension_field_name}' looks like a non-business "
            "(system/load) date. Metrics should anchor on a business-meaningful "
            "event date (e.g. Close_Date, Created_Date). Pass "
            "allow_junk_time_anchor=True (CLI: --allow-junk-time-anchor) to override."
        )

    # Work on a mutable copy so an override / filter field can be mirrored into
    # the list without surprising the caller.
    if additional_dimensions is not None:
        additional_dimensions = list(additional_dimensions)

    # Auto-mirror filter fields into additionalDimensions. A metric filter whose
    # field is not also an additional dimension creates a metric that succeeds
    # at create but is unqueryable ("Metric Definition Filter Field <Field> is
    # not found in Metric Definition"). Mirroring keeps the metric queryable.
    if filters:
        for filt in filters:
            dim_ref = _filter_field_to_dim_ref(filt.get("fieldName", ""))
            if dim_ref is None:
                continue
            if additional_dimensions is None:
                additional_dimensions = []
            existing_keys = {_dim_ref_key(d) for d in additional_dimensions}
            if _dim_ref_key(dim_ref) not in existing_keys:
                additional_dimensions.append(dim_ref)

    # Resolve the identifying dimension: explicit override wins, else default
    # to the first additional dimension. An override not already in
    # additionalDimensions is mirrored in (the UI requires membership).
    if identifying_dimension is None and additional_dimensions:
        identifying_dimension = additional_dimensions[0]
    elif identifying_dimension is not None:
        if additional_dimensions is None:
            additional_dimensions = []
        existing_keys = {_dim_ref_key(d) for d in additional_dimensions}
        if _dim_ref_key(identifying_dimension) not in existing_keys:
            additional_dimensions.append(identifying_dimension)

    payload: Dict[str, any] = {
        "apiName": api_name,
        "label": label,
        "aggregationType": aggregation_type,
        "measurementReference": {
            "calculatedFieldApiName": calculated_field_api_name
        },
        "timeDimensionReference": {
            "tableFieldReference": {
                "fieldApiName": time_dimension_field_name,
                "tableApiName": time_dimension_table_name
            }
        },
        "timeGrains": time_grains,
        "filters": filters or [],
        "isCumulative": is_cumulative,
        "isGoalEditingBlocked": is_goal_editing_blocked,
    }

    # filterLogic is required alongside a non-empty filters[]. Auto-generate it
    # as "1 AND 2 AND ..." (1-based, in filter order) unless the caller already
    # supplied one on the filter list (not the current API, but future-proof).
    if filters:
        payload["filterLogic"] = " AND ".join(str(i + 1) for i in range(len(filters)))

    # Add additionalDimensions if provided
    if additional_dimensions:
        payload["additionalDimensions"] = additional_dimensions
    
    # Add insightsSettings (auto-generate if not provided and additionalDimensions exist, or if sentiment is explicitly set)
    if insights_settings:
        payload["insightsSettings"] = insights_settings
    elif additional_dimensions or sentiment != "SentimentTypeUpIsGood":
        # Auto-generate insightsSettings from additionalDimensions (or empty if none)
        # Also generate if sentiment is explicitly set to non-default value
        payload["insightsSettings"] = build_default_insights_settings(
            additional_dimensions=additional_dimensions,
            sentiment=sentiment,
            identifying_dimension=identifying_dimension,
        )
    
    # Only include description if provided
    if description:
        payload["description"] = description

    # Enforce the additionalDimensions superset rule before returning the
    # payload (fail fast, pre-POST, with the server's own error strings).
    validate_additional_dimensions_superset(payload)

    return payload


# -- Validation ----------------------------------------------------------------

def validate_metric(
    api_name: str,
    expression: Optional[str] = None
) -> Tuple[bool, List[str]]:
    """Validate semantic metric structure and optionally expression syntax.

    Args:
        api_name: API name to validate
        expression: Optional expression to validate function names

    Returns:
        (is_valid, list_of_errors)
    """
    errors: List[str] = []

    # Check API name format
    if not api_name.endswith("_mtc"):
        errors.append("API name must end with '_mtc'")

    # Check for double underscores (Salesforce API restriction)
    if "__" in api_name:
        errors.append("API name cannot contain double underscores (__)")

    # Validate expression functions if provided
    if expression:
        try:
            from .tableau_functions import validate_functions
            is_valid_funcs, invalid_funcs, suggestions = validate_functions(expression)
            if not is_valid_funcs:
                for invalid in invalid_funcs:
                    error_msg = f"Invalid function '{invalid}' in expression"
                    # Add suggestions if available
                    suggestion = next((s for s in suggestions if invalid in s), None)
                    if suggestion:
                        error_msg += f". Did you mean: {suggestion.split(' -> ')[1]}"
                    errors.append(error_msg)
        except ImportError:
            # tableau_functions module not available, skip function validation
            pass

    return len(errors) == 0, errors


# -- Template Registry ---------------------------------------------------------

METRIC_TEMPLATE_REGISTRY = {
    "sum": sum_metric,
    "avg": avg_metric,
    "count": count_metric,
    "win_rate": win_rate_metric,
    "conversion_rate": conversion_rate_metric,
    "weighted_pipeline": weighted_pipeline_metric,
    "sales_cycle": sales_cycle_metric,
}
