"""Tableau formula function reference and validation.

Based on Tableau Prep function reference, adapted for Tableau Next calculated fields.
Provides function lists, validation, and helper utilities for expression building.
"""

from typing import Dict, List, Set, Tuple, Optional
import re

# Tableau formula functions (from Tableau Prep reference, adapted for Tableau Next)
# Note: Some Prep-specific functions may not be available in Tableau Next

# Aggregation functions (must be used in LOD expressions or UserAgg calculated fields)
AGGREGATION_FUNCTIONS = {
    "SUM", "AVG", "COUNT", "COUNTD", "MIN", "MAX", "MEDIAN", 
    "STDEV", "STDEVP", "VAR", "VARP", "PERCENTILE"
}

# Level of Detail (LOD) functions
LOD_FUNCTIONS = {
    "FIXED", "INCLUDE", "EXCLUDE"
}

# Date functions
DATE_FUNCTIONS = {
    "DATE", "DATETIME", "DATEADD", "DATEDIFF", "DATENAME", "DATEPARSE",
    "DATEPART", "DATETRUNC", "DAY", "MONTH", "YEAR", "TODAY", "NOW",
    "MAKEDATE", "MAKEDATETIME", "MAKETIME"
}

# String functions
STRING_FUNCTIONS = {
    "ASCII", "CHAR", "CONTAINS", "ENDSWITH", "FIND", "FINDNTH",
    "LEFT", "LEN", "LOWER", "LTRIM", "MID", "PROPER", "REGEXP_EXTRACT",
    "REGEXP_EXTRACT_NTH", "REGEXP_MATCH", "REGEXP_REPLACE", "REPLACE",
    "RIGHT", "RTRIM", "SPACE", "SPLIT", "STARTSWITH", "STR", "TRIM", "UPPER"
}

# Logical functions
LOGICAL_FUNCTIONS = {
    "IF", "ELSEIF", "ELSE", "END", "AND", "OR", "NOT", "IFNULL", "IIF",
    "ISNULL", "ISDATE", "CASE", "WHEN", "THEN"
}

# Mathematical functions
MATH_FUNCTIONS = {
    "ABS", "ACOS", "ASIN", "ATAN", "ATAN2", "CEILING", "COS", "COT",
    "DEGREES", "DIV", "EXP", "FLOOR", "FLOAT", "INT", "LN", "LOG",
    "PI", "POWER", "RADIANS", "ROUND", "SIGN", "SIN", "SQRT", "SQUARE",
    "TAN", "ZN"
}

# Window/Analytic functions
WINDOW_FUNCTIONS = {
    "LOOKUP", "LAST_VALUE", "RANK", "RANK_DENSE", "RANK_MODIFIED",
    "RANK_PERCENTILE", "ROW_NUMBER", "RUNNING_AVG", "RUNNING_SUM", "NTILE"
}

# LOD/Analytic keywords
LOD_KEYWORDS = {
    "PARTITION", "ORDERBY", "ASC", "DESC"
}

# Type conversion functions
TYPE_FUNCTIONS = {
    "FLOAT", "INT", "STR", "DATE", "DATETIME"
}

# All valid functions
ALL_FUNCTIONS = (
    AGGREGATION_FUNCTIONS | LOD_FUNCTIONS | DATE_FUNCTIONS | 
    STRING_FUNCTIONS | LOGICAL_FUNCTIONS | MATH_FUNCTIONS | 
    WINDOW_FUNCTIONS | TYPE_FUNCTIONS
)

# Function categories for documentation
FUNCTION_CATEGORIES = {
    "Aggregation": AGGREGATION_FUNCTIONS,
    "LOD": LOD_FUNCTIONS,
    "Date": DATE_FUNCTIONS,
    "String": STRING_FUNCTIONS,
    "Logical": LOGICAL_FUNCTIONS,
    "Math": MATH_FUNCTIONS,
    "Window": WINDOW_FUNCTIONS,
    "Type": TYPE_FUNCTIONS,
}


def extract_functions(expression: str) -> Set[str]:
    """Extract function names from a Tableau expression.
    
    Args:
        expression: Tableau formula expression
        
    Returns:
        Set of function names found in the expression
    """
    # Pattern to match function calls: FUNCTION_NAME(
    pattern = r'\b([A-Z][A-Z0-9_]*)\s*\('
    matches = re.findall(pattern, expression.upper())
    return set(matches)


def validate_functions(expression: str) -> Tuple[bool, List[str], List[str]]:
    """Validate that all functions in expression are valid Tableau functions.
    
    Args:
        expression: Tableau formula expression
        
    Returns:
        (is_valid, invalid_functions, suggestions)
    """
    found_functions = extract_functions(expression)
    invalid = [f for f in found_functions if f not in ALL_FUNCTIONS]
    
    suggestions = []
    for invalid_func in invalid:
        # Find similar function names
        similar = [
            func for func in ALL_FUNCTIONS 
            if invalid_func in func or func.startswith(invalid_func[:3])
        ]
        if similar:
            suggestions.append(f"{invalid_func} -> {', '.join(similar[:3])}")
    
    return len(invalid) == 0, invalid, suggestions


def get_function_category(function: str) -> Optional[str]:
    """Get the category of a function.
    
    Args:
        function: Function name (case-insensitive)
        
    Returns:
        Category name or None if not found
    """
    func_upper = function.upper()
    for category, functions in FUNCTION_CATEGORIES.items():
        if func_upper in functions:
            return category
    return None


def has_aggregation_function(expression: str) -> bool:
    """Check if expression contains aggregation functions.
    
    Args:
        expression: Tableau formula expression
        
    Returns:
        True if expression contains aggregation functions
    """
    found = extract_functions(expression)
    return bool(found & AGGREGATION_FUNCTIONS)


def suggest_functions(partial: str, limit: int = 5) -> List[str]:
    """Suggest function names matching a partial string.
    
    Args:
        partial: Partial function name
        limit: Maximum number of suggestions
        
    Returns:
        List of matching function names
    """
    partial_upper = partial.upper()
    matches = [
        func for func in ALL_FUNCTIONS
        if func.startswith(partial_upper) or partial_upper in func
    ]
    return sorted(matches)[:limit]


def get_function_examples() -> Dict[str, str]:
    """Get example usage for common functions.
    
    Returns:
        Dictionary mapping function names to example expressions
    """
    return {
        "SUM": "SUM([Amount])",
        "AVG": "AVG([Price])",
        "COUNTD": "COUNTD([Customer_ID])",
        "IF": "IF [Profit] > 0 THEN 'Profitable' ELSE 'Loss' END",
        "CASE": "CASE [Stage] WHEN 'Won' THEN 1 WHEN 'Lost' THEN 0 ELSE NULL END",
        "DATEDIFF": "DATEDIFF('day', [Start_Date], [End_Date])",
        "CONTAINS": "CONTAINS([Name], 'Tech')",
        "LEFT": "LEFT([Name], 4)",
        "UPPER": "UPPER([Name])",
        "FIXED": "{FIXED [Region]: SUM([Sales])}",
    }
