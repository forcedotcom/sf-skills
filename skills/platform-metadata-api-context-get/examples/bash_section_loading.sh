#!/bin/bash
#
# Salesforce Metadata API - Section-Specific Loading Examples (Bash + jq)
#
# This file demonstrates how to programmatically load only specific sections
# from metadata JSON files using shell tools, avoiding the token waste of
# loading entire files.
#
# Prerequisites: jq (JSON processor) must be installed
#   - macOS: brew install jq
#   - Linux: apt-get install jq or yum install jq
#
# ⚠️ CRITICAL: Do NOT use built-in Read tools on these JSON files!
# Use this programmatic approach instead.
#

# Ensure jq is available before doing anything else
command -v jq >/dev/null 2>&1 || { echo "Error: jq is required but not installed." >&2; exit 1; }

METADATA_DIR="data/metadata_api"


# Example 1: Load ONLY the 'fields' section from CustomObject.json
#
# Token savings: ~70-80% compared to loading entire file
load_single_section_example() {
    echo "Example 1: Single section"

    local metadata_file="$METADATA_DIR/CustomObject.json"

    # Extract only the 'fields' section using jq
    local fields=$(jq '.fields' "$metadata_file")

    # Count fields
    local field_count=$(echo "$fields" | jq 'length')

    echo "Loaded $field_count fields from CustomObject"
    # Use only 'fields', ignore wsdl_segment and other sections
}


# Example 2: Load ONLY 'description' and 'fields' sections from Flow.json
#
# Token savings: ~60-75% compared to loading entire file
load_multiple_sections_example() {
    echo -e "\nExample 2: Multiple sections"

    local metadata_file="$METADATA_DIR/Flow.json"

    # Extract only needed sections using jq
    local description=$(jq -r '.description' "$metadata_file")
    local fields=$(jq '.fields' "$metadata_file")

    # Count fields
    local field_count=$(echo "$fields" | jq 'length')

    echo "Loaded description and $field_count fields from Flow"
    # Skip: wsdl_segment, declarative_metadata_sample_definition, etc.
}


# Example 3: Check available sections first, then load specific ones
#
# Best practice: Always check what sections are available
load_with_section_check() {
    echo -e "\nExample 3: Check sections first"

    local metadata_file="$METADATA_DIR/Profile.json"

    # Check available sections
    local available_sections=$(jq -r '.sections | join(", ")' "$metadata_file")
    echo "Available sections: $available_sections"

    # Load only specific sections you need
    if echo "$available_sections" | grep -q "fields"; then
        local fields=$(jq '.fields' "$metadata_file")
        echo "Loaded fields section"
    fi

    if echo "$available_sections" | grep -q "description"; then
        local description=$(jq -r '.description' "$metadata_file")
        echo "Loaded description section"
    fi

    # Explicitly ignore verbose sections:
    # - wsdl_segment (very large, rarely needed)
    # - file_information (not needed for field definitions)
    # - directory_location (not needed for field definitions)
}


# Example 4: Extract specific fields from a section
#
# Shows how to get even more granular
extract_specific_fields() {
    echo -e "\nExample 4: Extract specific fields"

    local metadata_file="$METADATA_DIR/CustomObject.json"

    # Get only specific field names from the fields section
    local field_names=$(jq -r '.fields | keys[]' "$metadata_file" | head -5)

    echo "First 5 field names:"
    echo "$field_names"

    # Get details for one specific field
    local label_field=$(jq '.fields.label' "$metadata_file")
    echo -e "\nLabel field details:"
    echo "$label_field"
}


# ❌ WRONG APPROACH - DO NOT USE
#
# This is what NOT to do - it loads the entire file into context:
#
# Read tool approach (WRONG):
# Read data/metadata_api/CustomObject.json  # Loads ALL sections!
#
# cat approach (WRONG):
# cat data/metadata_api/CustomObject.json  # Loads entire file!
#
# This injects the entire file (including massive WSDL segments)
# into your context, wasting 60-80% of tokens.


# Run examples
main() {
    echo "Salesforce Metadata API - Section-Specific Loading (Bash)"
    echo "=========================================================="
    echo ""

    load_single_section_example
    load_multiple_sections_example
    load_with_section_check
    extract_specific_fields
}

# Execute if run directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main
fi
