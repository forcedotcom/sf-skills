"""Business-friendly name generation and validation utilities.

Provides functions for generating business-friendly visualization names,
validating names, and cleaning field names for display.
"""

import sys
from typing import Any, Dict, Optional, Tuple


def validate_business_friendly_name(name: str, label: str) -> Tuple[bool, Optional[str]]:
    """Validate that name and label are business-friendly.
    
    Checks for technical suffixes and ensures names are descriptive.
    
    Args:
        name: Visualization API name (e.g., "Sales_Trend_Over_Time")
        label: Visualization display label (e.g., "Sales Performance Over Time")
        
    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if name is business-friendly, False otherwise
        - error_message: Error message if invalid, None if valid
        
    Example:
        >>> is_valid, error = validate_business_friendly_name("Sales_Trend", "Sales Trend")
        >>> print(is_valid)
        True
    """
    technical_suffixes = ["_Clc", "_clc", "_Mtc", "_mtc", "_MTC", "_CLC"]
    
    # Check name
    for suffix in technical_suffixes:
        if suffix in name:
            return False, f"Name '{name}' contains technical suffix '{suffix}'. Use business-friendly names."
    
    # Check label
    if len(label) < 5:
        return False, f"Label '{label}' is too short. Use descriptive business labels."
    
    # Check label for technical suffixes (case-insensitive)
    label_lower = label.lower()
    for suffix in technical_suffixes:
        if suffix.lower() in label_lower:
            return False, f"Label '{label}' contains technical suffix '{suffix}'. Use business-friendly labels."
    
    return True, None


def clean_field_name_for_display(field_name: str, sdm_fields: Dict[str, Dict[str, Any]]) -> str:
    """Clean field name for display, using SDM label if available.
    
    Strips technical suffixes (_Clc, _mtc, etc.) and uses SDM field labels
    when available. Falls back to cleaned field name if label not available.
    
    Args:
        field_name: Raw field name (e.g., "Pipeline_Generation_Clc")
        sdm_fields: Dict of SDM field definitions
        
    Returns:
        Cleaned business-friendly name (e.g., "Pipeline Generation")
        
    Example:
        >>> sdm_fields = {"Pipeline_Generation_Clc": {"label": "Pipeline Generation", ...}}
        >>> cleaned = clean_field_name_for_display("Pipeline_Generation_Clc", sdm_fields)
        >>> print(cleaned)
        "Pipeline Generation"
    """
    # Try to use SDM label first
    if field_name in sdm_fields:
        label = sdm_fields[field_name].get("label", "")
        if label:
            return label
    
    # Clean field name: strip technical suffixes
    cleaned = field_name
    technical_suffixes = ["_Clc", "_clc", "_Mtc", "_mtc", "_MTC", "_CLC"]
    for suffix in technical_suffixes:
        if cleaned.endswith(suffix):
            cleaned = cleaned[:-len(suffix)]
            break
    
    # Convert to title case, replacing underscores with spaces
    cleaned = cleaned.replace("_", " ").title()
    
    # Remove trailing spaces
    cleaned = cleaned.strip()
    
    return cleaned


def generate_business_friendly_name(
    template: str, 
    fields: Dict[str, str],
    sdm_fields: Dict[str, Dict[str, Any]]
) -> Tuple[str, str]:
    """Generate business-friendly name and label from template and fields.
    
    Uses SDM field labels and strips technical suffixes to ensure business-friendly names.
    Maps template types to business intent descriptions.
    
    Args:
        template: Template name (e.g., "multi_series_line", "revenue_by_category")
        fields: Dict mapping template field names to SDM field names
        sdm_fields: Dict of SDM field definitions (for labels)
        
    Returns:
        Tuple of (api_name, display_label)
        
    Example:
        >>> fields = {"category": "Account_Industry", "amount": "Total_Amount"}
        >>> sdm_fields = discover_sdm_fields("Sales_Model")
        >>> name, label = generate_business_friendly_name("revenue_by_category", fields, sdm_fields)
        >>> print(label)
        "Account Industry Analysis"
    """
    # Map template to business intent/description
    intent_map = {
        "multi_series_line": "Trend Over Time",
        "trend_over_time": "Trend Over Time",
        "revenue_by_category": "Analysis by",
        "stacked_bar_by_dimension": "Breakdown by",
        "bar_multi_measure": "Comparison by",
        "heatmap_grid": "Analysis",
        "scatter_correlation": "Correlation Analysis",
        "market_share_donut": "Distribution",
        "conversion_funnel": "Pipeline by",
        "dot_matrix": "Multi-Dimensional Analysis",
        "top_n_leaderboard": "Rankings",
        "geomap_location_only": "Locations Map",
        "geomap_points": "Map by",
        "geomap_advanced": "Map by",
        "flow_sankey": "Flow from",
        "flow_simple": "Flow from",
        "flow_simple_measure_on_marks": "Flow from",
        "flow_sankey_measure_on_marks": "Flow from",
        "flow_package_base": "Flow from",
        "flow_package_single_color": "Flow from",
        "flow_package_link_color_nodes_color": "Flow from",
        "flow_package_colors_variations": "Flow from",
        "flow_package_three_level": "Flow from",
    }
    
    # Get primary field for context (using cleaned field names)
    if "category" in fields:
        main_field = clean_field_name_for_display(fields["category"], sdm_fields)
        intent = intent_map.get(template, "Analysis")
        if intent == "Analysis by":
            label = f"{main_field} Analysis"
        elif intent == "Breakdown by":
            label = f"{main_field} Breakdown"
        elif intent == "Comparison by":
            label = f"{main_field} Comparison"
        elif intent == "Distribution":
            label = f"{main_field} Distribution"
        elif intent == "Pipeline by":
            label = f"Sales Pipeline by {main_field}"
        else:
            label = f"{main_field} {intent}"
        name = label.replace(" ", "_")
        
    elif "date" in fields:
        measure_name = fields.get("measure", "Value")
        measure = clean_field_name_for_display(measure_name, sdm_fields) if measure_name in sdm_fields else measure_name.replace("_", " ").title()
        intent = intent_map.get(template, "Trend")
        if "multi_series" in template or "color_dim" in fields:
            color_dim_name = fields.get("color_dim", "")
            color_dim = clean_field_name_for_display(color_dim_name, sdm_fields) if color_dim_name and color_dim_name in sdm_fields else color_dim_name.replace("_", " ").title()
            if color_dim:
                label = f"{measure} Trend by {color_dim}"
            else:
                label = f"{measure} {intent}"
        else:
            label = f"{measure} {intent}"
        name = label.replace(" ", "_")
        
    elif "row_dim" in fields and "col_dim" in fields:
        row_name = fields["row_dim"]
        col_name = fields["col_dim"]
        row = clean_field_name_for_display(row_name, sdm_fields)
        col = clean_field_name_for_display(col_name, sdm_fields)
        measure_name = fields.get("measure", "Performance")
        measure = clean_field_name_for_display(measure_name, sdm_fields) if measure_name in sdm_fields else measure_name.replace("_", " ").title()
        if template == "heatmap_grid":
            label = f"{measure} by {row} and {col}"
        elif template == "dot_matrix":
            label = f"{measure} Analysis: {row} vs {col}"
        else:
            label = f"{row} by {col}"
        name = label.replace(" ", "_")
        
    elif "x_measure" in fields and "y_measure" in fields:
        x_measure_name = fields["x_measure"]
        y_measure_name = fields["y_measure"]
        x_measure = clean_field_name_for_display(x_measure_name, sdm_fields)
        y_measure = clean_field_name_for_display(y_measure_name, sdm_fields)
        category_name = fields.get("category", "")
        category = clean_field_name_for_display(category_name, sdm_fields) if category_name and category_name in sdm_fields else category_name.replace("_", " ").title()
        if category:
            label = f"{x_measure} vs {y_measure} by {category}"
        else:
            label = f"{x_measure} vs {y_measure}"
        name = label.replace(" ", "_")
        
    elif "stage" in fields:
        stage_name = fields["stage"]
        stage = clean_field_name_for_display(stage_name, sdm_fields)
        count_name = fields.get("count", "Value")
        measure = clean_field_name_for_display(count_name, sdm_fields) if count_name in sdm_fields else count_name.replace("_", " ").title()
        label = f"{measure} by {stage}"
        name = label.replace(" ", "_")

    elif template == "geomap_location_only" and "latitude" in fields and "longitude" in fields:
        label = "Locations (Map)"
        name = label.replace(" ", "_")

    elif "latitude" in fields and "longitude" in fields and "label_dim" in fields:
        lab_name = fields["label_dim"]
        lab = clean_field_name_for_display(lab_name, sdm_fields) if lab_name in sdm_fields else lab_name.replace("_", " ").title()
        measure_name = fields.get("measure", "Value")
        measure = clean_field_name_for_display(measure_name, sdm_fields) if measure_name in sdm_fields else measure_name.replace("_", " ").title()
        if template == "geomap_advanced":
            label = f"{measure} on map by {lab} (color & size)"
        else:
            label = f"{measure} by {lab} (Map)"
        name = label.replace(" ", "_")

    elif "level1" in fields and "level2" in fields:
        l1n, l2n = fields["level1"], fields["level2"]
        l1 = clean_field_name_for_display(l1n, sdm_fields) if l1n in sdm_fields else l1n.replace("_", " ").title()
        l2 = clean_field_name_for_display(l2n, sdm_fields) if l2n in sdm_fields else l2n.replace("_", " ").title()
        label = f"Flow from {l1} to {l2}"
        name = label.replace(" ", "_")
        
    else:
        # Fallback: use template name with field context
        intent = intent_map.get(template, template.replace("_", " ").title())
        if fields:
            first_field_name = list(fields.values())[0]
            first_field = clean_field_name_for_display(first_field_name, sdm_fields) if first_field_name in sdm_fields else first_field_name.replace("_", " ").title()
            label = f"{first_field} {intent}"
        else:
            label = intent
        name = label.replace(" ", "_")
    
    return name, label
