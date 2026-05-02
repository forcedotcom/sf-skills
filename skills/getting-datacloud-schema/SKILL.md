---
name: getting-datacloud-schema
description: "Retrieve Data Lake Object (DLO) and Data Model Object (DMO) schema information from Salesforce Data Cloud using REST APIs. Use this skill when you need to inspect DLO or DMO field definitions, data types, or metadata. Takes org alias and optional DLO/DMO name as parameters."
---

# getting-datacloud-schema Skill


## Overview

This skill retrieves Data Lake Object (DLO) and Data Model Object (DMO) schema information from Salesforce Data Cloud using the SSOT REST API. It can list all DLOs or DMOs in an org, or retrieve detailed schema for a specific DLO or DMO.

## When to Use

- User wants to see all DLOs or DMOs in a Data Cloud org
- User needs field schema for a specific DLO or DMO
- User is exploring Data Cloud data structures
- User needs to understand DLO or DMO field types and metadata

## Prerequisites

- SF CLI installed and authenticated to target org
- Org has Data Cloud enabled
- User has appropriate Data Cloud permissions

## Skill Execution

### Parameters

1. **org_alias** (required): The SF CLI org alias (e.g., 'afvibe', 'myorg')
2. **dlo_name** (optional): Specific DLO developer name (e.g., 'Employee__dll')
3. **dmo_name** (optional): Specific DMO developer name (e.g., 'Individual__dlm')

### Step 1: Discover Connected Org

First, run `sf org list` to find out which org is connected and extract the alias to use for all subsequent calls:

```bash
sf org list
```

Example output:
```
┌────┬───────┬──────────────────────────┬────────────────────┬───────────┐
│    │ Alias │ Username                 │ Org Id             │ Status    │
├────┼───────┼──────────────────────────┼────────────────────┼───────────┤
│ 🍁 │ myorg │ chandresh@afvidedemo.org │ 00DKZ00000b80NT2AY │ Connected │
└────┴───────┴──────────────────────────┴────────────────────┴───────────┘
```

Extract the **Alias** value (e.g., `myorg`) from the output and use it as the `<org_alias>` for all subsequent calls. Use `--all` to see expired and deleted scratch orgs as well.

### Step 2: Validate SF CLI Authentication

Before making API calls, verify the org is connected:

```bash
sf org display --target-org <org_alias> --json
```

If not connected, inform user to run:
```bash
sf org login web --alias <org_alias>
```

### Step 3a: Execute DLO Schema Script

Use the Python script to retrieve DLO information:

**To list all DLOs:**
```bash
python3 ./scripts/get_dlo_schema.py <org_alias>
```

**To get specific DLO schema:**
```bash
python3 ./scripts/get_dlo_schema.py <org_alias> <dlo_name>
```

### Step 3b: Execute DMO Schema Script

Use the Python script to retrieve DMO information:

**To list all DMOs:**
```bash
python3 ./scripts/get_dmo_schema.py <org_alias>
```

**To get specific DMO schema:**
```bash
python3 ./scripts/get_dmo_schema.py <org_alias> <dmo_name>
```

### Step 4: Present Results

Parse and present the results in a user-friendly format:

**For DLO List:**
- Show DLO name, label, category, and ID
- Indicate total count
- Highlight DLOs with data (totalRecords > 0)

**For DLO Schema:**
- Show basic info (name, label, category, status)
- List all fields with:
  - Field name
  - Data type
  - Primary key indicator
  - Nullable status
- Highlight custom fields (exclude system fields like DataSource__c, cdp_sys_*)
- Show record count if available

**For DMO List:**
- Show DMO name, label, category, and ID
- Indicate total count

**For DMO Schema:**
- Show basic info (name, label, category, description)
- List all fields with:
  - Field name
  - Data type
  - Primary key indicator
  - Nullable status
- Show dataspace information if available

### Step 5: Offer Next Steps

After displaying results, suggest relevant follow-up actions:
- Query data from the DLO
- Create calculated insights
- Build segments
- Set up data streams
- Create DMO mappings

## API Endpoints Used

### List All DLOs
```
GET /services/data/v64.0/ssot/data-lake-objects
```

Response structure:
```json
{
  "dataLakeObjects": [
    {
      "name": "Employee__dll",
      "label": "Employee",
      "category": "Profile",
      "id": "1dlXXXXXXXXXXXXXXX",
      "status": "ACTIVE",
      "totalRecords": 12,
      "fields": [...]
    }
  ],
  "totalSize": 5
}
```

### Get DLO Schema
```
GET /services/data/v64.0/ssot/data-lake-objects/{dlo_name}
```

Response structure (same as individual object in list response, but wrapped in paginated format).

### List All DMOs
```
GET /services/data/v64.0/ssot/data-model-objects
```

Response structure:
```json
{
  "dataModelObjects": [
    {
      "name": "Individual__dlm",
      "label": "Individual",
      "category": "Profile",
      "id": "0dmXXXXXXXXXXXXXXX",
      "fields": [...]
    }
  ],
  "totalSize": 10
}
```

### Get DMO Schema
```
GET /services/data/v64.0/ssot/data-model-objects/{dmo_name}
```

Response structure (same as individual object in list response, but wrapped in paginated format).

## Error Handling

**Common Issues:**

1. **Org not connected**
   - Message: "Org not connected"
   - Solution: Ask user to authenticate via SF CLI

2. **DLO not found**
   - Message: "DLO 'XYZ__dll' not found"
   - Solution: List all DLOs first to verify name

5. **DMO not found**
   - Message: "DMO 'XYZ__dlm' not found"
   - Solution: List all DMOs first to verify name

3. **Permission issues**
   - Message: HTTP 403 errors
   - Solution: Verify user has Data Cloud permissions

4. **API version mismatch**
   - Current: v64.0
   - Solution: Script can be updated for newer API versions

## Example Usage

**Example 1: List all DLOs**
```
User: "Show me all DLOs in afvibe org"

Response:
1. Run sf org list to discover connected org alias
2. Authenticate to afvibe
3. Run: python3 ./scripts/get_dlo_schema.py afvibe
4. Display formatted list of DLOs
```

**Example 2: Get specific DLO schema**
```
User: "Get the schema for Employee__dll in afvibe"

Response:
1. Run sf org list to discover connected org alias
2. Authenticate to afvibe
3. Run: python3 ./scripts/get_dlo_schema.py afvibe Employee__dll
4. Display field schema with types and metadata
```

**Example 3: Explore DLOs then get schema**
```
User: "What DLOs exist in myorg and show me the schema for the Employee one"

Response:
1. Run sf org list to discover connected org alias
2. List all DLOs in myorg
3. Identify Employee__dll
4. Get detailed schema for Employee__dll
5. Present both results
```

**Example 4: List all DMOs**
```
User: "Show me all DMOs in afvibe org"

Response:
1. Run sf org list to discover connected org alias
2. Authenticate to afvibe
3. Run: python3 ./scripts/get_dmo_schema.py afvibe
4. Display formatted list of DMOs
```

**Example 5: Get specific DMO schema**
```
User: "Get the schema for Individual__dlm in afvibe"

Response:
1. Run sf org list to discover connected org alias
2. Authenticate to afvibe
3. Run: python3 ./scripts/get_dmo_schema.py afvibe Individual__dlm
4. Display field schema with types and metadata
```

**Example 6: Explore DMOs then get schema**
```
User: "What DMOs exist in myorg and show me the schema for the Individual one"

Response:
1. Run sf org list to discover connected org alias
2. List all DMOs in myorg
3. Identify Individual__dlm
4. Get detailed schema for Individual__dlm
5. Present both results
```

## Output Format

### DLO List Output
```
Found 5 DLOs in org 'afvibe':

1. DataCustomCodeLogs__dll
   Label: DataCustomCodeLogs
   Category: Engagement
   Records: 233

2. Employee__dll
   Label: Employee
   Category: Profile
   Records: 12

[...]
```

### DLO Schema Output
```
DLO: Employee__dll
Label: Employee
Category: Profile
Status: ACTIVE
Records: 12

Custom Fields:
  • id__c (Text) - Primary Key
  • name__c (Text)
  • position__c (Text)
  • manager_id__c (Number)

System Fields:
  • DataSource__c (Text)
  • InternalOrganization__c (Text)
  • cdp_sys_SourceVersion__c (Text)

Next steps:
- Query data: SELECT * FROM Employee__dll LIMIT 10
- Create segment based on position field
- Set up data stream for real-time updates
```

### DMO List Output
```
Found 10 DMOs in org 'afvibe':

1. Individual__dlm
   Label: Individual
   Category: Profile

2. ContactPointEmail__dlm
   Label: Contact Point Email
   Category: Profile

[...]
```

### DMO Schema Output
```
DMO: Individual__dlm
Label: Individual
Category: Profile
Description: Represents an individual person

Fields:
  • Id__c (Text) - Primary Key
  • FirstName__c (Text)
  • LastName__c (Text)
  • BirthDate__c (DateTime)

Next steps:
- Query data: SELECT * FROM Individual__dlm LIMIT 10
- View DLO mappings to this DMO
- Create calculated insights
```

## Notes

- DLO names always end with `__dll` suffix
- DMO names always end with `__dlm` suffix
- Field names always end with `__c` suffix
- System fields (DataSource__c, KQ_*, cdp_sys_*) are automatically added
- Primary key fields are required for DLO and DMO queries
- API supports pagination (limit/offset) for large result sets

## Related Skills

- **datakit_workflow**: For DMO mapping operations
- **datakit_validation**: For validating datakit configurations
- Use this skill before creating DMO mappings to understand source DLO structure
