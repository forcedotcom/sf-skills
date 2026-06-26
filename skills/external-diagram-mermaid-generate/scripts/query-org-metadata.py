#!/usr/bin/env python3
"""
Query Salesforce org for ERD metadata enrichment.

Retrieves:
1. Record counts for LDV detection (>2M = LDV)
2. OWD (Org-Wide Default) sharing settings
3. Object type (Standard/Custom/External)

Usage:
    python3 query-org-metadata.py --objects Account,Contact,Invoice__c --target-org myorg
    python3 query-org-metadata.py --objects Account,Contact --target-org myorg --output table
    python3 query-org-metadata.py --objects Account --target-org myorg --output json

Output:
    JSON or table with object metadata for diagram generation
"""

import subprocess
import json
import sys
import argparse
from typing import Optional

LDV_THRESHOLD = 2_000_000  # 2 million records


def run_sf_command(cmd: list[str], timeout: int = 30) -> Optional[dict]:
    """Run an sf CLI command and return parsed JSON result."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        pass
    except json.JSONDecodeError:
        pass
    except Exception:
        pass
    return None


def query_record_count(sobject: str, target_org: str) -> int:
    """Query record count using sf data query."""
    # External objects don't support COUNT()
    if sobject.endswith("__x"):
        return -1

    cmd = [
        "sf", "data", "query",
        "--query", f"SELECT COUNT() FROM {sobject}",
        "--target-org", target_org,
        "--json"
    ]

    data = run_sf_command(cmd)
    if data:
        return data.get("result", {}).get("totalSize", -1)
    return -1


def query_object_describe(sobject: str, target_org: str) -> dict:
    """Get object metadata (label, custom flag) via sobject describe."""
    cmd = [
        "sf", "sobject", "describe",
        "--sobject", sobject,
        "--target-org", target_org,
        "--json"
    ]

    data = run_sf_command(cmd)
    if data:
        result_data = data.get("result", {})
        return {
            "is_custom": result_data.get("custom", False),
            "key_prefix": result_data.get("keyPrefix", ""),
            "label": result_data.get("label", sobject),
        }
    return {}


def query_owd_bulk(objects: list[str], target_org: str) -> dict[str, dict]:
    """
    Query OWD for multiple objects using Tooling API EntityDefinition.

    This is the correct way to get OWD - sf sobject describe returns null
    for sharingModel, but EntityDefinition via Tooling API works.
    """
    # Build IN clause for SOQL
    quoted_objects = ", ".join([f"'{obj}'" for obj in objects])
    query = f"SELECT QualifiedApiName, InternalSharingModel, ExternalSharingModel FROM EntityDefinition WHERE QualifiedApiName IN ({quoted_objects})"

    cmd = [
        "sf", "data", "query",
        "--query", query,
        "--target-org", target_org,
        "--use-tooling-api",
        "--json"
    ]

    data = run_sf_command(cmd, timeout=60)
    result = {}

    if data:
        records = data.get("result", {}).get("records", [])
        for record in records:
            api_name = record.get("QualifiedApiName", "")
            result[api_name] = {
                "internal_owd": record.get("InternalSharingModel", "Unknown"),
                "external_owd": record.get("ExternalSharingModel", "Unknown"),
            }

    return result


def get_object_type(sobject: str, describe: dict) -> str:
    """Determine object type: STD, CUST, or EXT."""
    if sobject.endswith("__x"):
        return "EXT"
    elif sobject.endswith("__c") or describe.get("is_custom"):
        return "CUST"
    return "STD"


def format_ldv(count: int) -> str:
    """Format record count for LDV display."""
    if count < 0:
        return ""
    if count >= LDV_THRESHOLD:
        if count >= 1_000_000:
            return f"LDV[~{count // 1_000_000}M]"
        else:
            return f"LDV[~{count // 1_000}K]"
    return ""


def format_owd(sharing_model: str) -> str:
    """Format OWD for display."""
    owd_map = {
        "Private": "Private",
        "Read": "Read",
        "ReadWrite": "ReadWrite",
        "ReadWriteTransfer": "Full",
        "ControlledByParent": "Parent",
        "FullAccess": "Full",
        "Unknown": "Unknown"
    }
    return owd_map.get(sharing_model, sharing_model)


def format_count(count: int) -> str:
    """Format record count with commas."""
    if count < 0:
        return "N/A"
    return f"{count:,}"


def print_table_output(results: dict) -> None:
    """Print results as formatted table."""
    print()
    print("=" * 78)
    print(f"{'Object':<25} {'Type':<6} {'Records':<14} {'LDV':<12} {'OWD':<15}")
    print("-" * 78)

    for obj, data in results.items():
        count_str = format_count(data['record_count'])
        ldv = data['ldv_indicator'] or "-"
        owd = f"OWD:{data['owd']}"
        print(f"{obj:<25} {data['object_type']:<6} {count_str:<14} {ldv:<12} {owd:<15}")

    print("=" * 78)
    print()


def print_mermaid_hints(results: dict) -> None:
    """Print Mermaid flowchart style hints."""
    print("Mermaid Style Hints:")
    print("-" * 40)

    for obj, data in results.items():
        obj_type = data['object_type']
        if obj_type == "STD":
            color = "fill:#bae6fd,stroke:#0369a1"
        elif obj_type == "CUST":
            color = "fill:#fed7aa,stroke:#c2410c"
        else:  # EXT
            color = "fill:#a7f3d0,stroke:#047857"

        # Build label parts
        label_parts = []
        if data['ldv_indicator']:
            label_parts.append(data['ldv_indicator'])
        label_parts.append(f"OWD:{data['owd']}")

        label = f"{obj}<br/>{' | '.join(label_parts)}"
        safe_id = obj.replace("__", "_")

        print(f'    {safe_id}["{label}"]')
        print(f"    style {safe_id} {color},color:#1f2937")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Query Salesforce org for ERD metadata (LDV, OWD, object type)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s --objects Account,Contact,Opportunity --target-org myorg
    %(prog)s --objects Account,Invoice__c --target-org myorg --output table
    %(prog)s --objects Account --target-org myorg --mermaid
        """
    )
    parser.add_argument(
        "--objects", "-o",
        required=True,
        help="Comma-separated object API names (e.g., Account,Contact,Invoice__c)"
    )
    parser.add_argument(
        "--target-org", "-u",
        required=True,
        help="Salesforce org alias or username"
    )
    parser.add_argument(
        "--output", "-f",
        default="table",
        choices=["json", "table"],
        help="Output format (default: table)"
    )
    parser.add_argument(
        "--mermaid", "-m",
        action="store_true",
        help="Include Mermaid style hints in output"
    )

    args = parser.parse_args()

    objects = [o.strip() for o in args.objects.split(",")]
    results = {}

    # Show progress for table output
    if args.output == "table":
        print(f"\nQuerying {len(objects)} objects from org: {args.target_org}")
        print("-" * 50)

    # Bulk query OWD for all objects at once (much faster)
    if args.output == "table":
        print("  [0] Querying OWD via Tooling API...", end=" ", flush=True)
    owd_data = query_owd_bulk(objects, args.target_org)
    if args.output == "table":
        print(f"OK ({len(owd_data)} found)")

    for i, obj in enumerate(objects, 1):
        if args.output == "table":
            print(f"  [{i}/{len(objects)}] Querying {obj}...", end=" ", flush=True)

        count = query_record_count(obj, args.target_org)
        describe = query_object_describe(obj, args.target_org)
        obj_type = get_object_type(obj, describe)

        # Get OWD from bulk query result
        obj_owd = owd_data.get(obj, {})
        internal_owd = obj_owd.get("internal_owd", "Unknown")

        results[obj] = {
            "record_count": count,
            "ldv_indicator": format_ldv(count),
            "object_type": obj_type,
            "owd": format_owd(internal_owd),
            "external_owd": format_owd(obj_owd.get("external_owd", "Unknown")),
            "label": describe.get("label", obj),
        }

        if args.output == "table":
            status = "OK" if describe else "WARN"
            print(status)

    # Output results
    if args.output == "json":
        print(json.dumps(results, indent=2))
    else:
        print_table_output(results)
        if args.mermaid:
            print_mermaid_hints(results)


if __name__ == "__main__":
    main()
