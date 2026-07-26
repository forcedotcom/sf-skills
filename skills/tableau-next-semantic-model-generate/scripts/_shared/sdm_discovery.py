"""Semantic Data Model (SDM) discovery and field extraction.

Provides functions for discovering SDMs, listing available models,
and extracting field definitions from SDM responses.
"""

import sys
from typing import Any, Dict, List, Optional

from .sf_api import (
    base_field_endpoint,
    data_object_endpoint,
    get_credentials,
    metric_endpoint,
    sdm_detail_endpoint,
    sdm_list_endpoint,
    sf_get,
)


def discover_sdm_fields(sdm_name: str) -> Optional[Dict[str, Dict[str, Any]]]:
    """Discover all fields from an SDM.
    
    Retrieves SDM details from Salesforce API and builds a flattened
    dictionary mapping field names to field definitions.
    
    Args:
        sdm_name: SDM API name (e.g., "Sales_Cloud12_backward")
        
    Returns:
        Dict mapping field names to field definitions with keys:
        - fieldName: Field API name
        - objectName: Object API name (None for calculated fields)
        - role: "Dimension" or "Measure"
        - displayCategory: "Discrete" or "Continuous"
        - dataType: Field data type (e.g., "Text", "Number", "Date")
        - function: Aggregation function for measures (e.g., "Sum", "Avg")
        - label: Field display label
        - description: Field description
        Or None if SDM not found or API error
        
    Example:
        >>> fields = discover_sdm_fields("Sales_Model")
        >>> print(fields["Account_Industry"]["label"])
        "Account Industry"
    """
    token, instance = get_credentials()
    data = sf_get(token, instance, sdm_detail_endpoint(sdm_name))
    
    if data is None:
        print(f"✗ Error: SDM '{sdm_name}' not found", file=sys.stderr)
        return None
    
    # Build flattened field dict
    fields: Dict[str, Dict[str, Any]] = {}
    
    # Add fields from semantic data objects
    for obj in data.get("semanticDataObjects", []):
        obj_name = obj.get("apiName", "")
        
        for d in obj.get("semanticDimensions", []):
            field_name = d.get("apiName", "")
            fields[field_name] = {
                "fieldName": field_name,
                "objectName": obj_name,
                "role": "Dimension",
                "displayCategory": "Discrete",
                "dataType": d.get("dataType", ""),
                "function": None,
                "label": d.get("label", ""),
                "description": d.get("description", ""),
            }
        
        for m in obj.get("semanticMeasurements", []):
            field_name = m.get("apiName", "")
            fields[field_name] = {
                "fieldName": field_name,
                "objectName": obj_name,
                "role": "Measure",
                "displayCategory": "Continuous",
                "aggregationType": m.get("aggregationType", "Sum"),
                "function": m.get("aggregationType", "Sum"),
                "label": m.get("label", ""),
                "description": m.get("description", ""),
            }
    
    # Add calculated dimensions
    for d in data.get("semanticCalculatedDimensions", []):
        field_name = d.get("apiName", "")
        fields[field_name] = {
            "fieldName": field_name,
            "objectName": None,
            "role": "Dimension",
            "displayCategory": "Discrete",
            "dataType": d.get("dataType", ""),
            "function": None,
            "label": d.get("label", ""),
            "description": d.get("description", ""),
        }
    
    # Add calculated measures
    for m in data.get("semanticCalculatedMeasurements", []):
        field_name = m.get("apiName", "")
        fields[field_name] = {
            "fieldName": field_name,
            "objectName": None,
            "role": "Measure",
            "displayCategory": "Continuous",
            "aggregationType": m.get("aggregationType", "Sum"),
            "function": m.get("aggregationType", "Sum"),
            "label": m.get("label", ""),
            "description": m.get("description", ""),
        }
    
    return fields


def list_sdms() -> List[Dict[str, Any]]:
    """List all available Semantic Data Models.
    
    Returns:
        List of SDM dicts with keys: apiName, label, dataspace
    """
    token, instance = get_credentials()
    data = sf_get(token, instance, sdm_list_endpoint())
    
    if data is None:
        return []
    
    models = data.get("semantic_models") or data.get("items") or []
    return models


def get_sdm_details(sdm_name: str) -> Optional[Dict[str, Any]]:
    """Get full SDM details including all fields and metadata.

    Args:
        sdm_name: SDM API name

    Returns:
        Full SDM response dict from API, or None if not found
    """
    token, instance = get_credentials()
    return sf_get(token, instance, sdm_detail_endpoint(sdm_name))


def extract_ai_readiness(data: Dict[str, Any]) -> Dict[str, Any]:
    """Pull the model-level AI-readiness fields from an SDM detail response.

    Surfaces whether a model is agent-queryable and its authored AI context, so a
    session can see the current state before a resolve-and-merge update (and to
    confirm an update landed). Reads the model-level AI fields:
    ``agentEnabled`` (expose-to-AI), ``businessPreferences`` (the context block —
    HTML-encoded as stored), ``description``, ``categories``; plus the related
    ``isAiDrafted`` (provenance — distinct from agentEnabled),
    ``queryUnrelatedDataObjects``, and ``label`` for context.

    Args:
        data: raw SDM detail response (from get_sdm_details / sf_get).

    Returns:
        Dict with keys: apiName, label, agentEnabled, businessPreferences,
        description, categories, isAiDrafted, queryUnrelatedDataObjects.
    """
    return {
        "apiName": data.get("apiName", ""),
        "label": data.get("label", ""),
        "agentEnabled": data.get("agentEnabled"),
        "businessPreferences": data.get("businessPreferences"),
        "description": data.get("description"),
        "categories": data.get("categories", []),
        "isAiDrafted": data.get("isAiDrafted"),
        "queryUnrelatedDataObjects": data.get("queryUnrelatedDataObjects"),
    }


def discover_sdm_ai_readiness(sdm_name: str) -> Optional[Dict[str, Any]]:
    """Fetch an SDM and return its model-level AI-readiness fields.

    Args:
        sdm_name: SDM API name.

    Returns:
        Dict (see extract_ai_readiness), or None if the SDM is not found / error.
    """
    data = get_sdm_details(sdm_name)
    if data is None:
        return None
    return extract_ai_readiness(data)


def get_metric_definition(sdm_name: str, metric_name: str) -> Optional[Dict[str, Any]]:
    """Fetch a metric's FULL definition for resolve-and-merge before a PUT update.

    Returns the complete metric (incl. ``insightsSettings.identifyingDimension``,
    ``additionalDimensions``, ``timeDimensionReference``, time-comparison
    settings) — the body the metric update (full-payload PUT) must re-send in
    full so a single-field change does not drop these. See
    references/sdm-ai-readiness-api.md §3.

    Args:
        sdm_name: SDM API name.
        metric_name: metric API name (e.g. ``Headcount_mtc``).

    Returns:
        Full metric definition dict, or None if not found / API error.
    """
    token, instance = get_credentials()
    return sf_get(token, instance, metric_endpoint(sdm_name, metric_name))


def get_base_field_definition(
    sdm_name: str, object_name: str, field_role: str, field_name: str
) -> Optional[Dict[str, Any]]:
    """Fetch a base dimension/measurement's FULL definition for resolve-and-merge.

    A raw base field's description is updated via a full-payload PUT on its
    sub-resource (PATCH is not allowed), so the updater must resolve the complete
    definition first, then re-send it with the change. See
    references/sdm-ai-readiness-api.md.

    Args:
        sdm_name: SDM apiName.
        object_name: data-object apiName.
        field_role: ``"dimensions"`` or ``"measurements"``.
        field_name: the base field's apiName.

    Returns:
        Full base-field definition dict, or None if not found / API error.
    """
    token, instance = get_credentials()
    return sf_get(
        token, instance, base_field_endpoint(sdm_name, object_name, field_role, field_name)
    )


def get_data_object_definition(sdm_name: str, object_name: str) -> Optional[Dict[str, Any]]:
    """Fetch a data object's FULL definition for resolve-and-merge before a PUT.

    A data object's description is updated via a full-payload PUT on its
    sub-resource (PATCH is not allowed), so the updater must resolve the complete
    definition first, then re-send it with the change. See
    references/sdm-ai-readiness-api.md.

    Args:
        sdm_name: SDM apiName.
        object_name: data-object apiName.

    Returns:
        Full data-object definition dict, or None if not found / API error.
    """
    token, instance = get_credentials()
    return sf_get(token, instance, data_object_endpoint(sdm_name, object_name))


def extract_relationships(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract model-level relationships (joins) from an SDM detail response.

    Reads the ``semanticRelationships`` array (added for SDM-creation support —
    discovery previously surfaced objects/dims/measures/calc-fields/metrics but
    NOT relationships). Each relationship carries the join-field apiNames the
    structural authoring (add_relationship) references.

    Args:
        data: raw SDM detail response (from get_sdm_details / sf_get).

    Returns:
        List of relationship dicts with keys:
        - apiName, label, joinType, cardinality, isQueryable
        - leftObject / rightObject: the two data-object apiNames
        - criteria: list of {leftField, rightField, leftFieldType,
          rightFieldType, joinOperator} using the resolved semantic apiNames
    """
    relationships: List[Dict[str, Any]] = []
    raw = data.get("semanticRelationships") or data.get("relationships") or []
    for rel in raw:
        criteria = []
        for crit in rel.get("criteria", []):
            criteria.append({
                "leftField": crit.get("leftSemanticFieldApiName", ""),
                "rightField": crit.get("rightSemanticFieldApiName", ""),
                "leftFieldType": crit.get("leftFieldType", ""),
                "rightFieldType": crit.get("rightFieldType", ""),
                "joinOperator": crit.get("joinOperator", ""),
            })
        relationships.append({
            "apiName": rel.get("apiName", ""),
            "label": rel.get("label", ""),
            "joinType": rel.get("joinType", ""),
            "cardinality": rel.get("cardinality", ""),
            "isQueryable": rel.get("isQueryable", ""),
            "leftObject": rel.get("leftSemanticDefinitionApiName", ""),
            "rightObject": rel.get("rightSemanticDefinitionApiName", ""),
            "criteria": criteria,
        })
    return relationships


def discover_sdm_relationships(sdm_name: str) -> Optional[List[Dict[str, Any]]]:
    """Fetch an SDM and return its model-level relationships.

    Args:
        sdm_name: SDM API name.

    Returns:
        List of relationship dicts (see extract_relationships), or None if the
        SDM is not found / API error.
    """
    data = get_sdm_details(sdm_name)
    if data is None:
        return None
    return extract_relationships(data)


def extract_object_field_apinames(data: Dict[str, Any]) -> Dict[str, Dict[str, List[str]]]:
    """Map each data object to its server-stored (suffixed) field apiNames.

    Surfaces the suffixed apiNames structural authoring needs as join keys —
    e.g. ``{"qb_hw_employee": {"dimensions": [...], "measures": ["position_id2", ...]}}``.

    Args:
        data: raw SDM detail response.

    Returns:
        Dict object-apiName -> {"dimensions": [...], "measures": [...]} of the
        stored (possibly suffixed) field apiNames.
    """
    result: Dict[str, Dict[str, List[str]]] = {}
    for obj in data.get("semanticDataObjects", []):
        obj_name = obj.get("apiName", "")
        result[obj_name] = {
            "dimensions": [d.get("apiName", "") for d in obj.get("semanticDimensions", [])],
            "measures": [m.get("apiName", "") for m in obj.get("semanticMeasurements", [])],
        }
    return result
