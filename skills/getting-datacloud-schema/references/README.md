# getting-datacloud-schema Skill

## Overview

A skill that retrieves Data Lake Object (DLO) and Data Model Object (DMO) schema information from Salesforce Data Cloud using REST APIs.

## Usage

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
python3 scripts/get_dlo_schema.py <org_alias>

# Get specific DLO schema
python3 scripts/get_dlo_schema.py <org_alias> <dlo_name>

# List all DMOs
python3 scripts/get_dmo_schema.py <org_alias>

# Get specific DMO schema
python3 scripts/get_dmo_schema.py <org_alias> <dmo_name>
```

**Examples:**
```bash
# List all DLOs in afvibe org
python3 scripts/get_dlo_schema.py afvibe

# Get Employee__dll schema from afvibe
python3 scripts/get_dlo_schema.py afvibe Employee__dll

# List all DMOs in afvibe org
python3 scripts/get_dmo_schema.py afvibe

# Get Individual__dlm schema from afvibe
python3 scripts/get_dmo_schema.py afvibe Individual__dlm
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
- Returns: Detailed field schema including field names, data types, primary key indicators, nullable status

### List All DMOs
- Calls: `GET /services/data/v64.0/ssot/data-model-objects`
- Returns: All DMOs with name, label, category, ID
- Shows paginated results

### Get DMO Schema
- Calls: `GET /services/data/v64.0/ssot/data-model-objects/{dmo_name}`
- Returns: Detailed field schema including field names, data types, primary key indicators, nullable status

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
  - id__c (Text) - Primary Key
  - name__c (Text)
  - position__c (Text)
  - manager_id__c (Number)
  - DataSource__c (Text)
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
  - Id__c (Text) - Primary Key
  - FirstName__c (Text)
  - LastName__c (Text)
  - BirthDate__c (DateTime)
  [...]
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Org not connected | `sf org login web --alias <org_alias>` |
| Module not found: requests | `pip install requests pyyaml` |
| DLO not found | Verify name ends with `__dll`, list all DLOs first |
| DMO not found | Verify name ends with `__dlm`, list all DMOs first |
| Permission denied | Verify user has Data Cloud permissions |

## Related Skills

- **datakit workflow**: For DMO mapping operations
- **datakit validation**: For validating datakit configurations
- Use this skill before creating DMO mappings to understand source DLO structure
