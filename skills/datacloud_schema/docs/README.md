# datacloud_schema Skill

## Overview

A Claude Code skill that retrieves Data Lake Object (DLO) and Data Model Object (DMO) schema information from Salesforce Data Cloud using REST APIs.

## Installation

The skill is now installed at:
```
/home/codebuilder/dx-project/.a4drules/skills/datacloud_schema/
```

## Usage

### Using the Skill in Claude Code

Simply ask Claude to get DLO or DMO information:

**List all DLOs:**
```
"Show me all DLOs in afvibe org"
"List Data Lake Objects in myorg"
```

**Get specific DLO schema:**
```
"Get the schema for Employee__dll in afvibe"
"What fields does the Employee__dll DLO have in myorg?"
```

**List all DMOs:**
```
"Show me all DMOs in afvibe org"
"List Data Model Objects in myorg"
```

**Get specific DMO schema:**
```
"Get the schema for Individual__dlm in afvibe"
"What fields does the Individual__dlm DMO have in myorg?"
```

### Direct Script Usage

You can also run the scripts directly:

```bash
# List all DLOs
python3 ./scripts/get_dlo_schema.py <org_alias>

# Get specific DLO schema
python3 ./scripts/get_dlo_schema.py <org_alias> <dlo_name>

# List all DMOs
python3 ./scripts/get_dmo_schema.py <org_alias>

# Get specific DMO schema
python3 ./scripts/get_dmo_schema.py <org_alias> <dmo_name>
```

**Examples:**
```bash
# List all DLOs in afvibe org
python3 ./scripts/get_dlo_schema.py afvibe

# Get Employee__dll schema from afvibe
python3 ./scripts/get_dlo_schema.py afvibe Employee__dll

# List all DMOs in afvibe org
python3 ./scripts/get_dmo_schema.py afvibe

# Get Individual__dlm schema from afvibe
python3 ./scripts/get_dmo_schema.py afvibe Individual__dlm
```

## Prerequisites

1. **SF CLI Installed**
   ```bash
   sf --version
   ```

2. **Authenticated to Target Org**
   ```bash
   sf org login web --alias <org_alias>
   ```

3. **Python 3 and Dependencies**
   ```bash
   pip install requests pyyaml
   ```

4. **Data Cloud Enabled**
   - Org must have Data Cloud provisioned
   - User must have Data Cloud permissions

## What It Does

### List All DLOs
- Calls: `GET /services/data/v64.0/ssot/data-lake-objects`
- Returns: All DLOs with name, label, category, ID, record count
- Shows paginated results

### Get DLO Schema
- Calls: `GET /services/data/v64.0/ssot/data-lake-objects/{dlo_name}`
- Returns: Detailed field schema including:
  - Field names and labels
  - Data types (Text, Number, DateTime, etc.)
  - Primary key indicators
  - Nullable status
  - Field metadata

### List All DMOs
- Calls: `GET /services/data/v64.0/ssot/data-model-objects`
- Returns: All DMOs with name, label, category, ID
- Shows paginated results

### Get DMO Schema
- Calls: `GET /services/data/v64.0/ssot/data-model-objects/{dmo_name}`
- Returns: Detailed field schema including:
  - Field names and labels
  - Data types (Text, Number, DateTime, etc.)
  - Primary key indicators
  - Nullable status
  - Field metadata

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/services/data/v64.0/ssot/data-lake-objects` | GET | List all DLOs |
| `/services/data/v64.0/ssot/data-lake-objects/{name}` | GET | Get DLO schema |
| `/services/data/v64.0/ssot/data-model-objects` | GET | List all DMOs |
| `/services/data/v64.0/ssot/data-model-objects/{name}` | GET | Get DMO schema |

## Output Format

### DLO List
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
```

### DLO Schema
```
DLO: Employee__dll
Label: Employee
Category: Profile
Status: ACTIVE
Records: 12

Fields (9 total):
  • id__c (Text) - Primary Key
  • name__c (Text)
  • position__c (Text)
  • manager_id__c (Number)
  • DataSource__c (Text)
  • InternalOrganization__c (Text)
  [...]
```

### DMO List
```
Found 10 DMOs in org 'afvibe':

1. Individual__dlm
   Label: Individual
   Category: Profile

2. ContactPointEmail__dlm
   Label: Contact Point Email
   Category: Profile
```

### DMO Schema
```
DMO: Individual__dlm
Label: Individual
Category: Profile

Fields (8 total):
  • Id__c (Text) - Primary Key
  • FirstName__c (Text)
  • LastName__c (Text)
  • BirthDate__c (DateTime)
  [...]
```

## Files

```
datacloud_schema/
├── SKILL.md              # Skill definition and instructions
├── docs/
│   └── README.md         # This file
└── scripts/
    ├── get_dlo_schema.py # Python script for DLO REST APIs
    └── get_dmo_schema.py # Python script for DMO REST APIs
```

## Troubleshooting

**Issue: "Org not connected"**
```bash
sf org login web --alias <org_alias>
sf org list  # Verify
```

**Issue: "Module not found: requests"**
```bash
pip install requests pyyaml
```

**Issue: "DLO not found"**
- Verify DLO name ends with `__dll` suffix
- List all DLOs first to confirm exact name

**Issue: "DMO not found"**
- Verify DMO name ends with `__dlm` suffix
- List all DMOs first to confirm exact name

**Issue: "Permission denied"**
- Verify user has Data Cloud permissions
- Check org has Data Cloud enabled

## Related Skills

- `aisuite_datakit_workflow` - For DMO mapping operations
- `aisuite_datakit_validation` - For validating datakit configs

## Next Steps After Getting Schema

1. **Query DLO Data**
   ```sql
   SELECT * FROM Employee__dll LIMIT 10
   ```

2. **Create Segments**
   - Use fields to build audience segments

3. **Set Up Data Streams**
   - Create ingestion pipelines

4. **Create DMO Mappings**
   - Map DLO fields to Data Model Objects

5. **Build Calculated Insights**
   - Aggregate data from DLO fields

## Version

- **Version**: 1.0
- **Created**: 2026-03-26
- **API Version**: v64.0
- **Python**: 3.9+
