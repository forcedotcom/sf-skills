"""Generate stub Flow XML for .agent file action targets."""

from __future__ import annotations

# Mapping from .agent types to Flow variable dataTypes
_TYPE_MAP = {
    "string": "String",
    "number": "Number",
    "boolean": "Boolean",
    "date": "Date",
    "datetime": "DateTime",
    "id": "String",
    "object": "Apex",
}

# Mapping from complex_data_type_name to Flow variable dataTypes (for action I/O)
_COMPLEX_TYPE_MAP = {
    "lightning__integerType": "Number",
    "lightning__numberType": "Number",
    "lightning__doubleType": "Number",
    "lightning__currencyType": "Currency",
    "lightning__dateTimeStringType": "DateTime",
    "lightning__recordInfoType": "SObject",
    "lightning__objectType": "Apex",
    "lightning__listType": "Apex",
    "lightning__textType": "String",
}

API_VERSION = "63.0"


def generate_flow_xml(
    api_name: str,
    inputs: list[dict] | None = None,
    outputs: list[dict] | None = None,
    process_type: str = "AutoLaunchedFlow",
) -> str:
    """Generate a stub Flow XML with matching input/output variables.

    Produces a minimal .flow-meta.xml that:
    - Declares input variables matching action inputs
    - Declares output variables matching action outputs
    - Merges bidirectional variables (isInput=true, isOutput=true)
    - Uses Active status so flows are immediately callable
    - Has a single Assignment element as placeholder logic

    Args:
        api_name: The flow API name.
        inputs: Action input definitions (list of dicts with 'name', 'type' keys).
        outputs: Action output definitions (list of dicts with 'name', 'type' keys).
        process_type: Flow process type (default: AutoLaunchedFlow).

    Returns:
        Flow XML string.
    """
    inputs = inputs or []
    outputs = outputs or []

    input_names = {inp["name"] for inp in inputs}
    bidirectional_names = input_names & {out["name"] for out in outputs}

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<Flow xmlns="http://soap.sforce.com/2006/04/metadata">',
        f'    <apiVersion>{API_VERSION}</apiVersion>',
        f'    <label>{api_name.replace("_", " ")}</label>',
        f'    <processType>{process_type}</processType>',
        '    <status>Active</status>',
        '    <interviewLabel>{!$Flow.CurrentDateTime}</interviewLabel>',
    ]

    # Input variables
    for inp in inputs:
        flow_type = _COMPLEX_TYPE_MAP.get(inp.get("complex_data_type_name", ""), _TYPE_MAP.get(inp.get("type", "string"), "String"))
        is_output = inp["name"] in bidirectional_names
        lines.extend([
            '    <variables>',
            f'        <name>{inp["name"]}</name>',
            f'        <dataType>{flow_type}</dataType>',
        ])
        if flow_type == "Number":
            lines.append(f'        <scale>{_infer_scale(inp["name"])}</scale>')
        lines.extend([
            '        <isCollection>false</isCollection>',
            '        <isInput>true</isInput>',
            f'        <isOutput>{"true" if is_output else "false"}</isOutput>',
        ])
        if inp.get("description"):
            lines.append(f'        <description>{_escape_xml(inp["description"])}</description>')
        lines.append('    </variables>')

    # Output-only variables
    for out in outputs:
        if out["name"] in bidirectional_names:
            continue
        flow_type = _COMPLEX_TYPE_MAP.get(out.get("complex_data_type_name", ""), _TYPE_MAP.get(out.get("type", "string"), "String"))
        lines.extend([
            '    <variables>',
            f'        <name>{out["name"]}</name>',
            f'        <dataType>{flow_type}</dataType>',
        ])
        if flow_type == "Number":
            lines.append(f'        <scale>{_infer_scale(out["name"])}</scale>')
        lines.extend([
            '        <isCollection>false</isCollection>',
            '        <isInput>false</isInput>',
            '        <isOutput>true</isOutput>',
        ])
        if out.get("description"):
            lines.append(f'        <description>{_escape_xml(out["description"])}</description>')
        lines.append('    </variables>')

    # Placeholder variable if no outputs
    if not outputs:
        lines.extend([
            '    <variables>',
            '        <name>placeholder_result</name>',
            '        <dataType>String</dataType>',
            '        <isCollection>false</isCollection>',
            '        <isInput>false</isInput>',
            '        <isOutput>true</isOutput>',
            '    </variables>',
        ])

    # Placeholder assignment
    lines.extend([
        '    <assignments>',
        '        <name>Placeholder_Assignment</name>',
        '        <label>Placeholder Assignment</label>',
        '        <locationX>176</locationX>',
        '        <locationY>158</locationY>',
    ])

    for out in outputs:
        flow_type = _COMPLEX_TYPE_MAP.get(out.get("complex_data_type_name", ""), _TYPE_MAP.get(out.get("type", "string"), "String"))
        lines.extend([
            '        <assignmentItems>',
            f'            <assignToReference>{out["name"]}</assignToReference>',
            '            <operator>Assign</operator>',
            f'            <value>{_default_value_element_by_flow_type(flow_type)}</value>',
            '        </assignmentItems>',
        ])

    if not outputs:
        lines.extend([
            '        <assignmentItems>',
            '            <assignToReference>placeholder_result</assignToReference>',
            '            <operator>Assign</operator>',
            '            <value><stringValue>TODO</stringValue></value>',
            '        </assignmentItems>',
        ])

    lines.extend([
        '    </assignments>',
        '    <start>',
        '        <locationX>50</locationX>',
        '        <locationY>0</locationY>',
        '        <connector>',
        '            <targetReference>Placeholder_Assignment</targetReference>',
        '        </connector>',
        '    </start>',
        '</Flow>',
    ])

    return "\n".join(lines) + "\n"


def _infer_scale(name: str) -> int:
    """Infer decimal scale from variable name. Currency/amount/price → 2, else 0."""
    currency_hints = {"balance", "amount", "price", "cost", "total", "credit", "fee", "rate", "pct", "percent", "utilization"}
    lower = name.lower()
    for hint in currency_hints:
        if hint in lower:
            return 2
    return 0


def _escape_xml(text: str) -> str:
    """Escape XML special characters."""
    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _default_value_element(type_name: str) -> str:
    """Return a type-appropriate XML value element for a placeholder assignment."""
    if type_name == "boolean":
        return "<booleanValue>false</booleanValue>"
    if type_name == "number":
        return "<numberValue>0</numberValue>"
    if type_name == "date":
        return "<stringValue>2000-01-01</stringValue>"
    if type_name == "datetime":
        return "<stringValue>2000-01-01T00:00:00Z</stringValue>"
    return "<stringValue>TODO</stringValue>"


def _default_value_element_by_flow_type(flow_type: str) -> str:
    """Return a type-appropriate XML value element based on resolved Flow dataType."""
    if flow_type == "Boolean":
        return "<booleanValue>false</booleanValue>"
    if flow_type in ("Number", "Currency"):
        return "<numberValue>0</numberValue>"
    if flow_type == "Date":
        return "<stringValue>2000-01-01</stringValue>"
    if flow_type == "DateTime":
        return "<stringValue>2000-01-01T00:00:00Z</stringValue>"
    return "<stringValue>TODO</stringValue>"
