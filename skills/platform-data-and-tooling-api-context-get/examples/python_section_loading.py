#!/usr/bin/env python3
"""
Salesforce Data + Tooling API - Section-Specific Loading Examples (Python)

Demonstrates loading only the sections you need from the enterprise (SOQL/DML
sObject) and Tooling (developer record) JSON files, and how to traverse this
skill's surface-specific structure:
  - enterprise `fields` carry query/DML `properties` (Create/Filter/Sort/Group/
    Nillable/Update) plus relationship metadata (relationship_name / refers_to)
  - `field_reference` is a SEPARATE catalog, not a subset of `fields`
  - Tooling records expose supported_rest_api_http_methods / supported_soap_calls

CRITICAL: Do NOT Read/cat these JSON files whole — Account.json etc. carry a
huge wsdl_segment. Extract only the section you need.
"""

import json
from pathlib import Path

ENTERPRISE_DIR = Path('assets/enterprise_api')
TOOLING_DIR = Path('assets/tooling_api')


def _load(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_fields_section():
    """Example 1: Load ONLY the 'fields' section from an enterprise sObject."""
    data = _load(ENTERPRISE_DIR / 'Account.json')
    fields = data.get('fields', {})
    # Skip wsdl_segment (verbose) and field_reference (load separately if needed)
    print(f"Account has {len(fields)} fields in the 'fields' section")
    return fields


def find_filterable_fields():
    """Example 2: Find filterable fields (usable in a SOQL WHERE clause).

    The `properties` string controls capability: Filter -> WHERE, Sort ->
    ORDER BY, Group -> GROUP BY, Create/Update -> DML. Compare case-insensitively.
    """
    data = _load(ENTERPRISE_DIR / 'Opportunity.json')
    filterable = [
        name for name, meta in data.get('fields', {}).items()
        if 'filter' in (meta.get('properties', '') or '').lower()
    ]
    print(f"Opportunity has {len(filterable)} filterable fields; first 5: {filterable[:5]}")
    return filterable


def traverse_relationship():
    """Example 3: Traverse a relationship (reference field -> parent object).

    relationship_name is the SOQL traversal path; refers_to names the target.
    """
    data = _load(ENTERPRISE_DIR / 'Contact.json')
    account = data.get('fields', {}).get('AccountId', {})
    print(f"AccountId -> relationship_name={account.get('relationship_name')} "
          f"refers_to={account.get('refers_to')}")
    print("SOQL: SELECT Id, Account.Name FROM Contact")
    return account


def check_both_catalogs():
    """Example 4: Check BOTH catalogs — field_reference is NOT a subset of fields.

    System/audit fields (Id, CreatedDate, ...) frequently live ONLY in
    field_reference. If a field isn't in `fields`, check `field_reference`.
    """
    data = _load(ENTERPRISE_DIR / 'Account.json')
    fields = set(data.get('fields', {}))
    ref = set(data.get('field_reference', {}))
    only_in_ref = sorted(ref - fields)
    print(f"Account: fields={len(fields)} field_reference={len(ref)}")
    print(f"Only in field_reference (first 5): {only_in_ref[:5]}")
    return only_in_ref


def tooling_supported_methods():
    """Example 5: Tooling record — check supported HTTP methods before querying.

    Tooling objects query against /services/data/vXX.0/tooling/query, not the
    regular Data API. Many are read-only; check the methods first.
    """
    data = _load(TOOLING_DIR / 'ApexClass.json')
    methods = data.get('supported_rest_api_http_methods', '')
    field_names = list(data.get('fields', {}).keys())[:5]
    print(f"ApexClass REST methods: {methods}")
    print(f"First 5 ApexClass fields: {field_names}")
    return methods


if __name__ == '__main__':
    print("Example 1: enterprise fields section")
    load_fields_section()

    print("\nExample 2: filterable fields (WHERE-safe)")
    find_filterable_fields()

    print("\nExample 3: relationship traversal")
    traverse_relationship()

    print("\nExample 4: fields vs field_reference (dual catalog)")
    check_both_catalogs()

    print("\nExample 5: Tooling API supported methods")
    tooling_supported_methods()
