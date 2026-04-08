#!/usr/bin/env python3
"""
List all Data Model Objects and retrieve schema for one DMO using REST API.
Uses SF CLI for authentication.
"""

import subprocess
import json
import sys
import requests


def authenticate_to_org(org_alias):
    """
    Authenticate to Salesforce org using SF CLI.

    Args:
        org_alias: SF CLI org alias (e.g., 'afvibe')

    Returns:
        Tuple of (instance_url, access_token, username)
    """
    print(f"🔐 Authenticating to Salesforce org '{org_alias}'...")

    try:
        result = subprocess.run(
            ['sf', 'org', 'display', '--target-org', org_alias, '--json'],
            capture_output=True,
            text=True,
            check=True
        )

        org_data = json.loads(result.stdout)

        if org_data.get('status') != 0:
            raise Exception(f"SF CLI returned error: {org_data}")

        org_info = org_data['result']

        if org_info.get('connectedStatus') != 'Connected':
            raise Exception(f"Org '{org_alias}' is not connected. Run: sf org login web --alias {org_alias}")

        instance_url = org_info['instanceUrl']
        access_token = org_info['accessToken']
        username = org_info.get('username', 'Unknown')

        print(f"✅ Authenticated as: {username}")
        print(f"📍 Instance: {instance_url}\n")

        return instance_url, access_token, username

    except subprocess.CalledProcessError as e:
        raise Exception(f"SF CLI command failed: {e.stderr}")
    except (json.JSONDecodeError, KeyError) as e:
        raise Exception(f"Failed to parse SF CLI output: {e}")


def list_all_dmos(instance_url, access_token, api_version='v64.0'):
    """
    List all Data Model Objects using SSOT REST API.

    Args:
        instance_url: Salesforce instance URL
        access_token: OAuth access token
        api_version: API version (default: v64.0)

    Returns:
        List of DMO dictionaries
    """
    url = f"{instance_url}/services/data/{api_version}/ssot/data-model-objects"

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    print("📋 Fetching all Data Model Objects...")
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        raise Exception(f"API Error: HTTP {response.status_code}\n{response.text[:500]}")

    response_data = response.json()

    # Extract DMO list from paginated response
    if isinstance(response_data, dict) and 'dataModelObject' in response_data:
        dmos = response_data['dataModelObject']
        total_size = response_data.get('totalSize', len(dmos))
        print(f"✅ Found {len(dmos)} DMOs (Total: {total_size})\n")
    else:
        # Fallback if response format is different
        dmos = response_data if isinstance(response_data, list) else []
        print(f"✅ Found {len(dmos)} DMOs\n")

    return dmos


def get_dmo_schema(instance_url, access_token, dmo_name, api_version='v64.0'):
    """
    Get detailed schema for a specific DMO.

    Args:
        instance_url: Salesforce instance URL
        access_token: OAuth access token
        dmo_name: DMO developer name (e.g., 'Individual__dlm')
        api_version: API version (default: v64.0)

    Returns:
        DMO detail dictionary with full schema
    """
    url = f"{instance_url}/services/data/{api_version}/ssot/data-model-objects/{dmo_name}"

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    print(f"🔍 Fetching schema for DMO: {dmo_name}...")
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        raise Exception(f"API Error: HTTP {response.status_code}\n{response.text[:500]}")

    response_data = response.json()

    # Single DMO endpoint returns the object directly (not wrapped in an array)
    return response_data


def display_dmo_list(dmos):
    """Display summary of all DMOs."""
    print("=" * 80)
    print("📊 DATA MODEL OBJECTS")
    print("=" * 80)

    for idx, dmo in enumerate(dmos, 1):
        print(f"\n{idx}. {dmo.get('name', 'Unknown')}")
        print(f"   Label: {dmo.get('label', 'N/A')}")
        print(f"   Category: {dmo.get('category', 'N/A')}")
        print(f"   Creation Type: {dmo.get('creationType', 'N/A')}")
        print(f"   Data Space: {dmo.get('dataSpaceName', 'N/A')}")


def display_dmo_schema(dmo_detail):
    """Display detailed schema information for a DMO."""
    print("\n" + "=" * 80)
    print(f"🔍 SCHEMA DETAILS FOR: {dmo_detail.get('name')}")
    print("=" * 80)

    print(f"\n📝 Basic Information:")
    print(f"   Name: {dmo_detail.get('name')}")
    print(f"   Label: {dmo_detail.get('label')}")
    print(f"   Category: {dmo_detail.get('category')}")
    print(f"   Creation Type: {dmo_detail.get('creationType', 'N/A')}")
    print(f"   Data Space: {dmo_detail.get('dataSpaceName', 'N/A')}")

    # Display field schema
    fields = dmo_detail.get('fields', [])

    if fields:
        print(f"\n🔧 Fields ({len(fields)} total):")
        print("-" * 80)

        # Show all fields with detailed info
        for field in fields:
            print(f"\n   • {field.get('name')}")
            print(f"     Label: {field.get('label', 'N/A')}")
            print(f"     Data Type: {field.get('type', 'Unknown')}")
            print(f"     Primary Key: {field.get('isPrimaryKey', False)}")
            print(f"     Creation Type: {field.get('creationType', 'N/A')}")
            print(f"     Usage Tag: {field.get('usageTag', 'N/A')}")

            if 'length' in field:
                print(f"     Length: {field['length']}")
            if 'precision' in field:
                print(f"     Precision: {field['precision']}")
            if 'scale' in field:
                print(f"     Scale: {field['scale']}")
    else:
        print("\n   ⚠️  No fields found in schema")

    # Show full JSON
    print("\n" + "=" * 80)
    print("📄 FULL SCHEMA (JSON):")
    print("=" * 80)
    print(json.dumps(dmo_detail, indent=2))


def main():
    """Main execution function."""
    if len(sys.argv) < 2:
        print("Usage: python get_dmo_schema.py <org_alias> [dmo_name]")
        print("\nExamples:")
        print("  python get_dmo_schema.py afvibe")
        print("  python get_dmo_schema.py afvibe Individual__dlm")
        sys.exit(1)

    org_alias = sys.argv[1]
    specific_dmo = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        # Step 1: Authenticate
        instance_url, access_token, username = authenticate_to_org(org_alias)

        # Step 2: List all DMOs
        dmos = list_all_dmos(instance_url, access_token)
        display_dmo_list(dmos)

        # Step 3: Get schema for a specific DMO
        if specific_dmo:
            # User specified a DMO name
            dmo_detail = get_dmo_schema(instance_url, access_token, specific_dmo)
            display_dmo_schema(dmo_detail)
        elif dmos:
            # Get schema for the first DMO
            first_dmo = dmos[0]
            dmo_name = first_dmo.get('name')
            dmo_detail = get_dmo_schema(instance_url, access_token, dmo_name)
            display_dmo_schema(dmo_detail)
        else:
            print("\n⚠️  No DMOs found in this org")

        print("\n✅ Done!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
