"""Template library and payload builders for calculated fields.

Provides common formula templates and functions to build calculated measurement
and dimension payloads for Salesforce Tableau Next API.
"""

from typing import Dict, List, Optional, Tuple


# -- Template Functions ---------------------------------------------------------

def win_rate(won_field: str, total_field: str) -> str:
    """Generate win rate formula.

    Args:
        won_field: Field name for won count
        total_field: Field name for total count

    Returns:
        Tableau formula string
    """
    return f"SUM([{won_field}]) / SUM([{total_field}])"


def days_between(start_field: str, end_field: str) -> str:
    """Generate date difference formula.

    Args:
        start_field: Start date field name
        end_field: End date field name

    Returns:
        Tableau formula string
    """
    return f"DATEDIFF('day', [{start_field}], [{end_field}])"


def bucket_amount(field: str, small_threshold: int, medium_threshold: int) -> str:
    """Generate bucketing formula.

    Args:
        field: Field name to bucket
        small_threshold: Threshold for 'Small' bucket
        medium_threshold: Threshold for 'Medium' bucket

    Returns:
        Tableau formula string
    """
    return (
        f"IF [{field}] < {small_threshold} THEN 'Small' "
        f"ELSEIF [{field}] < {medium_threshold} THEN 'Medium' "
        f"ELSE 'Large' END"
    )


def is_equal(field: str, value: str) -> str:
    """Generate equality check formula.

    Args:
        field: Field name to check
        value: Value to compare against

    Returns:
        Tableau formula string
    """
    return f"[{field}] = '{value}'"


def count_distinct(field: str) -> str:
    """Generate distinct count formula.

    Args:
        field: Field name to count distinct values

    Returns:
        Tableau formula string
    """
    return f"COUNTD([{field}])"


def percentage_of_total(field: str) -> str:
    """Generate percentage of total formula.

    Args:
        field: Field name to calculate percentage for

    Returns:
        Tableau formula string
    """
    return f"SUM([{field}]) / TOTAL(SUM([{field}]))"


# -- Payload Builders -----------------------------------------------------------

def build_calculated_measurement(
    api_name: str,
    label: str,
    expression: str,
    aggregation_type: str = "UserAgg",
    data_type: str = "Number",
    decimal_place: int = 2,
    description: str = "",
    **kwargs
) -> Dict[str, any]:
    """Build calculated measurement payload.

    There are two ways to define aggregation in calculated measurements:
    
    1. **UserAgg (AggregateFunction level)**: When the expression contains aggregation 
       functions (SUM, AVG, COUNTD, etc.), use `aggregationType: "UserAgg"` and 
       `level: "AggregateFunction"`. Example: `"expression": "SUM([Amount])"`
    
    2. **Explicit aggregation (Row level)**: When the expression does NOT contain 
       aggregation functions, use explicit aggregation type (Sum, Avg, etc.) and 
       `level: "Row"`. Example: `"expression": "IF [Won] THEN [Amount] END"` with 
       `"aggregationType": "Sum"` applies Sum aggregation to the result.

    Args:
        api_name: API name (must end with _clc)
        label: Display label
        expression: Tableau formula expression
        aggregation_type: Aggregation type (Sum, Avg, Count, Min, Max, UserAgg, Median)
        data_type: Data type (Number, Text, Boolean, DateTime)
        decimal_place: Decimal places for Number fields
        description: Field description
        **kwargs: Additional optional fields (directionality, sentiment, totalAggregationType)

    Returns:
        Complete calculated measurement payload dict
    """
    # Detect if expression contains aggregation functions
    import re
    agg_functions = ["SUM", "AVG", "COUNTD", "COUNT", "MIN", "MAX", "MEDIAN", "STDEV", "VAR"]
    expression_upper = expression.upper()
    has_agg_in_expression = any(
        re.search(rf"\b{func}\s*\(", expression_upper) 
        for func in agg_functions
    )
    
    # Determine aggregation type and level
    if has_agg_in_expression:
        # Expression contains aggregation → use UserAgg + AggregateFunction
        final_agg_type = "UserAgg"
        level = "AggregateFunction"
        # Warn if user specified different aggregation_type
        if aggregation_type != "UserAgg":
            import warnings
            warnings.warn(
                f"Expression contains aggregation function (SUM, AVG, etc.), "
                f"so using UserAgg instead of '{aggregation_type}'. "
                f"If you want explicit aggregation, remove aggregation functions from expression."
            )
    else:
        # Expression does NOT contain aggregation → use explicit aggregation + Row
        final_agg_type = aggregation_type
        level = "Row"
        # Validate explicit aggregation types are allowed
        if final_agg_type not in ("Sum", "Avg", "Count", "Min", "Max", "Median", "UserAgg"):
            import warnings
            warnings.warn(
                f"Explicit aggregation type '{final_agg_type}' may not be supported. "
                f"Common types: Sum, Avg, Count, Min, Max, Median"
            )
    
    payload = {
        "aggregationType": final_agg_type,
        "apiName": api_name,
        "dataType": data_type,
        "decimalPlace": decimal_place,
        "directionality": kwargs.get("directionality", "Up"),
        "displayCategory": "Continuous",
        "expression": expression,
        "filters": [],
        "isOverrideBase": False,
        "isVisible": True,
        "label": label,
        "level": level,
        "overriddenProperties": [],
        "semanticDataType": "None",
        "sentiment": kwargs.get("sentiment", "SentimentTypeUpIsGood"),
        "shouldTreatNullsAsZeros": False,
        "sortOrder": "None",
        "totalAggregationType": kwargs.get("totalAggregationType", "Sum"),
    }
    # Only include description if provided (matches collection examples)
    if description:
        payload["description"] = description
    return payload


def build_calculated_dimension(
    api_name: str,
    label: str,
    expression: str,
    data_type: str = "Text",
    description: str = "",
    **kwargs
) -> Dict[str, any]:
    """Build calculated dimension payload.

    Args:
        api_name: API name (must end with _clc)
        label: Display label
        expression: Tableau formula expression
        data_type: Data type (Text, Boolean, Number, DateTime)
        description: Field description
        **kwargs: Additional optional fields (unused, reserved for future)

    Returns:
        Complete calculated dimension payload dict
    """
    payload = {
        "apiName": api_name,
        "dataType": data_type,
        "displayCategory": "Discrete",
        "expression": expression,
        "filters": [],
        "isOverrideBase": False,
        "isVisible": True,
        "label": label,
        "level": "Row",
        "overriddenProperties": [],
        "semanticDataType": "None",
        "sortOrder": "None",
    }
    # Only include description if provided (matches collection examples)
    if description:
        payload["description"] = description
    return payload


# -- Validation ----------------------------------------------------------------

def validate_calc_field(
    api_name: str,
    field_type: str,
    aggregation_type: Optional[str] = None,
    data_type: Optional[str] = None,
    expression: Optional[str] = None
) -> Tuple[bool, List[str]]:
    """Validate calculated field structure and optionally expression syntax.

    Args:
        api_name: API name to validate
        field_type: "measurement" or "dimension"
        aggregation_type: Aggregation type (for measurements)
        data_type: Data type
        expression: Optional expression to validate function names

    Returns:
        (is_valid, list_of_errors)
    """
    errors: List[str] = []

    # Check API name format
    if not api_name.endswith("_clc"):
        errors.append("API name must end with '_clc'")
    
    # Check for double underscores (Salesforce API restriction)
    if "__" in api_name:
        errors.append("API name cannot contain double underscores (__)")

    # Check aggregation type
    if field_type == "measurement" and aggregation_type:
        valid_agg = ["Sum", "Avg", "Count", "Min", "Max", "UserAgg", "Median"]
        if aggregation_type not in valid_agg:
            errors.append(f"aggregationType must be one of: {', '.join(valid_agg)}")

    # Check data type
    if data_type:
        valid_types = ["Number", "Text", "Boolean", "DateTime"]
        if data_type not in valid_types:
            errors.append(f"dataType must be one of: {', '.join(valid_types)}")
    
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

TEMPLATE_REGISTRY = {
    "win_rate": win_rate,
    "days_between": days_between,
    "bucket_amount": bucket_amount,
    "is_equal": is_equal,
    "count_distinct": count_distinct,
    "percentage_of_total": percentage_of_total,
}
