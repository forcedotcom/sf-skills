#!/usr/bin/env python3
"""
Salesforce Metadata API - Section-Specific Loading Examples (Python)

This file demonstrates how to programmatically load only specific sections
from metadata JSON files, avoiding the token waste of loading entire files.

⚠️ CRITICAL: Do NOT use built-in Read tools on these JSON files!
Use this programmatic approach instead.
"""

import json
from pathlib import Path

# Resolve the data directory relative to this file, so the examples work
# regardless of the current working directory.
METADATA_DIR = Path(__file__).resolve().parent.parent / 'data' / 'metadata_api'


def load_single_section_example():
    """
    Example 1: Load ONLY the 'fields' section from CustomObject.json

    Token savings: ~70-80% compared to loading entire file
    """
    metadata_file = METADATA_DIR / 'CustomObject.json'

    with open(metadata_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

        # Extract only the 'fields' section
        fields_only = data.get('fields', {})

        # Use only 'fields', ignore wsdl_segment and other sections
        print(f"Loaded {len(fields_only)} fields from CustomObject")
        return fields_only


def load_multiple_sections_example():
    """
    Example 2: Load ONLY 'description' and 'fields' sections from Flow.json

    Token savings: ~60-75% compared to loading entire file
    """
    metadata_file = METADATA_DIR / 'Flow.json'

    with open(metadata_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

        # Extract only needed sections
        description = data.get('description', '')
        fields = data.get('fields', {})

        # Skip: wsdl_segment, declarative_metadata_sample_definition, etc.
        print(f"Loaded description and {len(fields)} fields from Flow")
        return {'description': description, 'fields': fields}


def load_with_section_check():
    """
    Example 3: Check available sections first, then load specific ones

    Best practice: Always check what sections are available
    """
    metadata_file = METADATA_DIR / 'Profile.json'

    with open(metadata_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

        # Check available sections
        available_sections = data.get('sections', [])
        print(f"Available sections: {available_sections}")

        # Load only specific sections you need
        result = {}
        if 'fields' in available_sections:
            result['fields'] = data.get('fields', {})
        if 'description' in available_sections:
            result['description'] = data.get('description', '')

        # Explicitly ignore verbose sections
        # - wsdl_segment (very large, rarely needed)
        # - file_information (not needed for field definitions)
        # - directory_location (not needed for field definitions)

        return result


def wrong_approach_example():
    """
    ❌ WRONG APPROACH - DO NOT USE

    This is what NOT to do - it loads the entire file into context:

    # Read tool approach (WRONG):
    # Read data/metadata_api/CustomObject.json  # Loads ALL sections!

    # This injects the entire file (including massive WSDL segments)
    # into your context, wasting 60-80% of tokens.
    """
    pass


if __name__ == '__main__':
    print("Example 1: Single section")
    load_single_section_example()

    print("\nExample 2: Multiple sections")
    load_multiple_sections_example()

    print("\nExample 3: Check sections first")
    load_with_section_check()
