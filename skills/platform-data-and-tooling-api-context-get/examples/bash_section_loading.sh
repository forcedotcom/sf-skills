#!/bin/bash
#
# Salesforce Data + Tooling API - Section-Specific Loading Examples (Bash + jq)
#
# Demonstrates how to programmatically load only the sections you need from the
# enterprise (SOQL/DML sObject) and Tooling (developer record) JSON files, and
# how to traverse this skill's surface-specific structure:
#   - enterprise fields carry query/DML `properties` (Create/Filter/Sort/Group/
#     Nillable/Update) plus relationship metadata (relationship_name / refers_to)
#   - `field_reference` is a SEPARATE catalog, not a subset of `fields`
#   - Tooling records expose supported_rest_api_http_methods / supported_soap_calls
#
# Prerequisites: jq
#   - macOS: brew install jq   Linux: apt-get install jq
#
# CRITICAL: Do NOT Read/cat these JSON files whole — Account.json etc. carry a
# huge wsdl_segment. Extract only the section you need.
#

ENTERPRISE_DIR="assets/enterprise_api"
TOOLING_DIR="assets/tooling_api"


# Example 1: Load ONLY the 'fields' section from an enterprise sObject
load_fields_section() {
    echo "Example 1: enterprise fields section"

    local f="$ENTERPRISE_DIR/Account.json"
    local field_count=$(jq '.fields | length' "$f")

    echo "Account has $field_count fields in the 'fields' section"
    # Skip: wsdl_segment (verbose), field_reference (load separately if needed)
}


# Example 2: Find filterable fields (usable in a SOQL WHERE clause)
#
# The `properties` string controls capability: Filter -> WHERE, Sort -> ORDER BY,
# Group -> GROUP BY, Create/Update -> DML. Verify before writing the query.
find_filterable_fields() {
    echo -e "\nExample 2: filterable fields (WHERE-safe)"

    local f="$ENTERPRISE_DIR/Opportunity.json"

    echo "First 5 filterable Opportunity fields:"
    jq -r '.fields | to_entries[]
             | select(.value.properties // "" | test("Filter"))
             | .key' "$f" | head -5
}


# Example 3: Traverse a relationship (reference field -> parent object)
#
# For a reference field, relationship_name is the SOQL traversal path and
# refers_to names the target object(s): SELECT Owner.Name FROM Account.
traverse_relationship() {
    echo -e "\nExample 3: relationship traversal"

    local f="$ENTERPRISE_DIR/Contact.json"

    # Show the relationship metadata for the AccountId lookup
    jq -r '.fields.AccountId
             | "AccountId -> relationship_name=\(.relationship_name) refers_to=\(.refers_to)"' "$f"
    echo "SOQL: SELECT Id, Account.Name FROM Contact"
}


# Example 4: Check BOTH catalogs — field_reference is NOT a subset of fields
#
# System/audit fields (Id, CreatedDate, ...) frequently live ONLY in
# field_reference. If a field isn't in `fields`, check `field_reference` before
# concluding it doesn't exist.
check_both_catalogs() {
    echo -e "\nExample 4: fields vs field_reference (dual catalog)"

    local f="$ENTERPRISE_DIR/Account.json"

    local fields_n=$(jq '.fields | length' "$f")
    local ref_n=$(jq '.field_reference | length' "$f")
    echo "Account: fields=$fields_n  field_reference=$ref_n"

    echo "Fields present ONLY in field_reference (first 5):"
    jq -r '[(.field_reference | keys[]) as $k
             | select((.fields | has($k)) | not) | $k][:5][]' "$f"
}


# Example 5: Tooling record — check supported HTTP methods before querying
#
# Tooling objects are queried against /services/data/vXX.0/tooling/query, not the
# regular Data API. Many are read-only; check the supported methods first.
tooling_supported_methods() {
    echo -e "\nExample 5: Tooling API supported methods"

    local f="$TOOLING_DIR/ApexClass.json"

    local methods=$(jq -r '.supported_rest_api_http_methods' "$f")
    echo "ApexClass REST methods: $methods"
    echo "First 5 ApexClass fields:"
    jq -r '.fields | keys[:5][]' "$f"
}


# WRONG APPROACH - DO NOT USE
#
#   Read assets/enterprise_api/Account.json   # loads the huge wsdl_segment!
#   cat  assets/enterprise_api/Account.json   # loads the entire file!
#
# Extract only the section you need instead.


main() {
    echo "Salesforce Data + Tooling API - Section-Specific Loading (Bash)"
    echo "=============================================================="
    echo ""

    load_fields_section
    find_filterable_fields
    traverse_relationship
    check_both_catalogs
    tooling_supported_methods
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main
fi
