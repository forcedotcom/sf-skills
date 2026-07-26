#!/usr/bin/env python3
"""Discover Semantic Data Models and their fields via the Salesforce REST API.

Usage:
    python scripts/discover_sdm.py --list
    python scripts/discover_sdm.py --sdm Sales_Intelligence_Model
    python scripts/discover_sdm.py --sdm Sales_Intelligence_Model --json
"""

import argparse
import json
import sys
from typing import Any, Dict, List

from _shared.sf_api import get_credentials, sdm_list_endpoint, sdm_detail_endpoint, sf_get


def list_sdms(token: str, instance: str, as_json: bool) -> None:
    data = sf_get(token, instance, sdm_list_endpoint())
    if data is None:
        sys.exit(1)

    models = data.get("semantic_models") or data.get("items") or []
    if as_json:
        print(json.dumps(models, indent=2))
        return

    if not models:
        print("No Semantic Data Models found.")
        return

    print(f"{'API Name':<40} {'Label':<40} {'Dataspace'}")
    print("-" * 100)
    for m in models:
        api = m.get("apiName", "")
        label = m.get("label", "")
        ds = m.get("dataspace", "")
        print(f"{api:<40} {label:<40} {ds}")


def show_sdm(token: str, instance: str, sdm_name: str, as_json: bool) -> None:
    data = sf_get(token, instance, sdm_detail_endpoint(sdm_name))
    if data is None:
        print(f"Error: SDM '{sdm_name}' not found or API error.", file=sys.stderr)
        sys.exit(1)

    if as_json:
        print(json.dumps(_structured_output(data), indent=2))
        return

    print(f"SDM: {data.get('apiName', sdm_name)}")
    print(f"Label: {data.get('label', '')}")
    print()

    for obj in data.get("semanticDataObjects", []):
        obj_name = obj.get("apiName", "")
        print(f"Object: {obj_name}")

        dims = obj.get("semanticDimensions", [])
        if dims:
            print("  Dimensions:")
            for d in dims:
                api = d.get("apiName", "")
                dtype = d.get("dataType", "")
                print(f"    {api:<35} ({dtype:<12}) objectName={obj_name}")

        measures = obj.get("semanticMeasurements", [])
        if measures:
            print("  Measures:")
            for m in measures:
                api = m.get("apiName", "")
                agg = m.get("aggregationType", "Sum")
                print(f"    {api:<35} ({agg:<12}) objectName={obj_name}")
        print()

    calc_dims = data.get("semanticCalculatedDimensions", [])
    if calc_dims:
        print("Calculated Dimensions:")
        for d in calc_dims:
            api = d.get("apiName", "")
            dtype = d.get("dataType", "")
            print(f"  {api:<37} ({dtype:<12}) objectName=null")
        print()

    calc_measures = data.get("semanticCalculatedMeasurements", [])
    if calc_measures:
        print("Calculated Measures:")
        for m in calc_measures:
            api = m.get("apiName", "")
            agg = m.get("aggregationType", "Sum")
            note = "  <-- NOT Sum!" if agg != "Sum" else ""
            print(f"  {api:<37} ({agg:<12}) objectName=null{note}")
        print()

    metrics = data.get("semanticMetrics", [])
    if metrics:
        print("Metrics:")
        for m in metrics:
            api = m.get("apiName", "")
            label = m.get("label", "")
            agg = m.get("aggregationType", "")
            print(f"  {api:<37} ({agg:<12}) label={label}")
        print()

    relationships = data.get("semanticRelationships", [])
    if relationships:
        print("Relationships:")
        for rel in relationships:
            api = rel.get("apiName", "")
            card = rel.get("cardinality", "")
            left = rel.get("leftSemanticDefinitionApiName", "")
            right = rel.get("rightSemanticDefinitionApiName", "")
            queryable = rel.get("isQueryable", "")
            print(f"  {api:<37} ({card:<12}) {left} <-> {right}  [{queryable}]")
            for crit in rel.get("criteria", []):
                lf = crit.get("leftSemanticFieldApiName", "")
                rf = crit.get("rightSemanticFieldApiName", "")
                op = crit.get("joinOperator", "")
                print(f"      {lf} {op} {rf}")
        print()


def _structured_output(data: Dict[str, Any]) -> Dict[str, Any]:
    """Build a machine-readable summary of an SDM.
    
    Args:
        data: Raw SDM detail response from API
        
    Returns:
        Structured dict with apiName, label, objects, calculatedDimensions,
        calculatedMeasures, and metrics
    """
    result: Dict[str, Any] = {
        "apiName": data.get("apiName", ""),
        "label": data.get("label", ""),
        "objects": [],
        "calculatedDimensions": [],
        "calculatedMeasures": [],
        "metrics": [],
        "relationships": [],
    }

    for obj in data.get("semanticDataObjects", []):
        obj_entry: dict = {
            "objectName": obj.get("apiName", ""),
            "dimensions": [],
            "measures": [],
        }
        for d in obj.get("semanticDimensions", []):
            obj_entry["dimensions"].append({
                "fieldName": d.get("apiName", ""),
                "dataType": d.get("dataType", ""),
                "objectName": obj.get("apiName", ""),
                "role": "Dimension",
                "displayCategory": "Discrete",
                "function": None,
            })
        for m in obj.get("semanticMeasurements", []):
            obj_entry["measures"].append({
                "fieldName": m.get("apiName", ""),
                "aggregationType": m.get("aggregationType", "Sum"),
                "objectName": obj.get("apiName", ""),
                "role": "Measure",
                "displayCategory": "Continuous",
                "function": m.get("aggregationType", "Sum"),
            })
        result["objects"].append(obj_entry)

    for d in data.get("semanticCalculatedDimensions", []):
        result["calculatedDimensions"].append({
            "fieldName": d.get("apiName", ""),
            "dataType": d.get("dataType", ""),
            "objectName": None,
            "role": "Dimension",
            "displayCategory": "Discrete",
            "function": None,
        })

    for m in data.get("semanticCalculatedMeasurements", []):
        result["calculatedMeasures"].append({
            "fieldName": m.get("apiName", ""),
            "aggregationType": m.get("aggregationType", "Sum"),
            "objectName": None,
            "role": "Measure",
            "displayCategory": "Continuous",
            "function": m.get("aggregationType", "Sum"),
        })

    for m in data.get("semanticMetrics", []):
        result["metrics"].append({
            "apiName": m.get("apiName", ""),
            "label": m.get("label", ""),
            "aggregationType": m.get("aggregationType", ""),
        })

    for rel in data.get("semanticRelationships", []):
        result["relationships"].append({
            "apiName": rel.get("apiName", ""),
            "label": rel.get("label", ""),
            "joinType": rel.get("joinType", ""),
            "cardinality": rel.get("cardinality", ""),
            "isQueryable": rel.get("isQueryable", ""),
            "leftObject": rel.get("leftSemanticDefinitionApiName", ""),
            "rightObject": rel.get("rightSemanticDefinitionApiName", ""),
            "criteria": [
                {
                    "leftField": c.get("leftSemanticFieldApiName", ""),
                    "rightField": c.get("rightSemanticFieldApiName", ""),
                    "leftFieldType": c.get("leftFieldType", ""),
                    "rightFieldType": c.get("rightFieldType", ""),
                    "joinOperator": c.get("joinOperator", ""),
                }
                for c in rel.get("criteria", [])
            ],
        })

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover Tableau Next Semantic Data Models")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true", help="List all available SDMs")
    group.add_argument("--sdm", type=str, help="Show fields for a specific SDM (by API name)")
    parser.add_argument("--json", action="store_true", help="Output as JSON (machine-readable)")
    args = parser.parse_args()

    token, instance = get_credentials()

    if args.list:
        list_sdms(token, instance, args.json)
    elif args.sdm:
        show_sdm(token, instance, args.sdm, args.json)


if __name__ == "__main__":
    main()
