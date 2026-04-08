#!/usr/bin/env python3
"""
List all Data Lake Objects and retrieve schema for one DLO using REST API.
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


def list_all_dlos(instance_url, access_token, api_version='v64.0'):
    """
    List all Data Lake Objects using SSOT REST API.

    Args:
        instance_url: Salesforce instance URL
        access_token: OAuth access token
        api_version: API version (default: v64.0)

    Returns:
        List of DLO dictionaries
    """
    url = f"{instance_url}/services/data/{api_version}/ssot/data-lake-objects"

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    print("📋 Fetching all Data Lake Objects...")
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        raise Exception(f"API Error: HTTP {response.status_code}\n{response.text[:500]}")

    response_data = response.json()

    # Extract DLO list from paginated response
    if isinstance(response_data, dict) and 'dataLakeObjects' in response_data:
        dlos = response_data['dataLakeObjects']
        total_size = response_data.get('totalSize', len(dlos))
        print(f"✅ Found {len(dlos)} DLOs (Total: {total_size})\n")
    else:
        # Fallback if response format is different
        dlos = response_data if isinstance(response_data, list) else []
        print(f"✅ Found {len(dlos)} DLOs\n")

    return dlos


def get_dlo_schema(instance_url, access_token, dlo_name, api_version='v64.0'):
    """
    Get detailed schema for a specific DLO.

    Args:
        instance_url: Salesforce instance URL
        access_token: OAuth access token
        dlo_name: DLO developer name (e.g., 'Employee__dll')
        api_version: API version (default: v64.0)

    Returns:
        DLO detail dictionary with full schema
    """
    url = f"{instance_url}/services/data/{api_version}/ssot/data-lake-objects/{dlo_name}"

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    print(f"🔍 Fetching schema for DLO: {dlo_name}...")
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        raise Exception(f"API Error: HTTP {response.status_code}\n{response.text[:500]}")

    response_data = response.json()

    # Extract DLO from paginated response
    if isinstance(response_data, dict) and 'dataLakeObjects' in response_data:
        dlos = response_data['dataLakeObjects']
        if dlos:
            return dlos[0]  # Return first (should be only) DLO
        else:
            raise Exception(f"DLO '{dlo_name}' not found")
    else:
        # Fallback if response format is different
        return response_data


def display_dlo_list(dlos):
    """Display summary of all DLOs."""
    print("=" * 80)
    print("📊 DATA LAKE OBJECTS")
    print("=" * 80)

    for idx, dlo in enumerate(dlos, 1):
        print(f"\n{idx}. {dlo.get('name', 'Unknown')}")
        print(f"   Label: {dlo.get('label', 'N/A')}")
        print(f"   Category: {dlo.get('category', 'N/A')}")
        if 'id' in dlo:
            print(f"   ID: {dlo['id']}")


def display_dlo_schema(dlo_detail):
    """Display detailed schema information for a DLO."""
    print("\n" + "=" * 80)
    print(f"🔍 SCHEMA DETAILS FOR: {dlo_detail.get('name')}")
    print("=" * 80)

    print(f"\n📝 Basic Information:")
    print(f"   Name: {dlo_detail.get('name')}")
    print(f"   Label: {dlo_detail.get('label')}")
    print(f"   Category: {dlo_detail.get('category')}")
    print(f"   Description: {dlo_detail.get('description', 'N/A')}")

    if 'dataspaceInfo' in dlo_detail:
        dataspaces = dlo_detail['dataspaceInfo']
        dataspace_names = [ds.get('name', 'Unknown') for ds in dataspaces]
        print(f"   Dataspaces: {', '.join(dataspace_names)}")

    # Display field schema
    fields = dlo_detail.get('fields', [])

    if fields:
        print(f"\n🔧 Fields ({len(fields)} total):")
        print("-" * 80)

        # Show all fields with detailed info
        for field in fields:
            print(f"\n   • {field.get('name')}")
            print(f"     Label: {field.get('label', 'N/A')}")
            print(f"     Data Type: {field.get('dataType', 'Unknown')}")
            print(f"     Primary Key: {field.get('isPrimaryKey', False)}")
            print(f"     Nullable: {field.get('isNullable', True)}")

            if 'length' in field:
                print(f"     Length: {field['length']}")
            if 'precision' in field:
                print(f"     Precision: {field['precision']}")
            if 'scale' in field:
                print(f"     Scale: {field['scale']}")
    else:
        print("\n   ⚠️  No fields found in schema")

    # Show full JSON (optional, can be commented out)
    print("\n" + "=" * 80)
    print("📄 FULL SCHEMA (JSON):")
    print("=" * 80)
    print(json.dumps(dlo_detail, indent=2))


def main():
    """Main execution function."""
    if len(sys.argv) < 2:
        print("Usage: python list_dlos_and_schema.py <org_alias> [dlo_name]")
        print("\nExamples:")
        print("  python list_dlos_and_schema.py afvibe")
        print("  python list_dlos_and_schema.py afvibe Employee__dll")
        sys.exit(1)

    org_alias = sys.argv[1]
    specific_dlo = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        # Step 1: Authenticate
        instance_url, access_token, username = authenticate_to_org(org_alias)

        # Step 2: List all DLOs
        dlos = list_all_dlos(instance_url, access_token)
        display_dlo_list(dlos)

        # Step 3: Get schema for a specific DLO
        if specific_dlo:
            # User specified a DLO name
            dlo_detail = get_dlo_schema(instance_url, access_token, specific_dlo)
            display_dlo_schema(dlo_detail)
        elif dlos:
            # Get schema for the first DLO
            first_dlo = dlos[0]
            dlo_name = first_dlo.get('name')
            dlo_detail = get_dlo_schema(instance_url, access_token, dlo_name)
            display_dlo_schema(dlo_detail)
        else:
            print("\n⚠️  No DLOs found in this org")

        print("\n✅ Done!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
