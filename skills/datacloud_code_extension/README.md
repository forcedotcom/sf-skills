# datacloud_code_extension Skill

## Overview

A Claude Code skill that provides complete workflow for developing, testing, and deploying custom Python code extensions to Salesforce Data Cloud using the SF CLI plugin.

## Installation

The skill is now installed at:
```
/home/codebuilder/dx-project/.a4drules/skills/datacloud_code_extension/
```

## What It Does

This skill helps you create Data Cloud Code Extensions through a complete workflow:

1. **Init** - Create new code extension project with scaffolding
2. **Develop** - Write Python transformation logic
3. **Scan** - Auto-detect permissions and generate config
4. **Run** - Test locally against Data Cloud org
5. **Deploy** - Package and deploy to Data Cloud

## Usage

### In Claude Code Conversations

Simply ask Claude naturally:

**Initialize a project:**
```
"Create a new Data Cloud code extension project called employee-transform"
"Initialize a code extension to transform employee data"
```

**Test locally:**
```
"Run the code extension in my-transform directory against afvibe org"
"Test the entrypoint.py file locally"
```

**Scan for permissions:**
```
"Scan the entrypoint.py to generate config"
"Update permissions in config.json"
```

**Deploy:**
```
"Deploy Employee_Upper code extension to afvibe"
"Deploy this transform with package-version 1.0.0"
```

### Direct Command Usage

```bash
# Initialize project
sf data-code-extension init <directory> --code-type script

# Scan for permissions
sf data-code-extension scan ./payload/entrypoint.py

# Test locally
sf data-code-extension run ./payload/entrypoint.py --target-org <org_alias>

# Deploy
sf data-code-extension deploy --target-org <org_alias> --name <name> --package-version <version> --description <description> --package-dir <directory_location>
```

## Prerequisites

1. **SF CLI with Plugin**
   ```bash
   sf plugins install @salesforce/plugin-data-codeextension
   ```

2. **Python 3.11**
   ```bash
   python --version  # Must be 3.11.x
   ```

3. **Data Cloud Custom Code SDK**
   ```bash
   pip install salesforce-data-customcode
   ```

4. **Docker** (for deploy only)
   - Docker Desktop or equivalent

5. **Authenticated Org**
   ```bash
   sf org login web --alias <org_alias>
   ```

## Quick Start

### Complete End-to-End Example

```bash
# 1. Create project
mkdir employee-transform && cd employee-transform
sf data-code-extension init . --code-type script

# 2. Edit payload/entrypoint.py with your transformation

# 3. Scan for permissions
sf data-code-extension scan ./payload/entrypoint.py

# 4. Test locally
sf data-code-extension run ./payload/entrypoint.py --target-org afvibe

# 5. Deploy
sf data-code-extension deploy \
  --target-org afvibe \
  --name Employee_Upper \
  --version 1.0.0 \
  --description "Uppercase employee positions"
```

## Command Reference

### Init
```bash
sf data-code-extension init <directory> --code-type <script|function>
```
Creates project structure with entrypoint.py, config.json, requirements.txt.

### Scan
```bash
sf data-code-extension scan <entrypoint_file> [--config <path>] [--dry-run] [--no-requirements]
```
Detects read/write permissions and Python dependencies.

### Run
```bash
sf data-code-extension run <entrypoint_file> --target-org <org_alias> [--config-file <path>]
```
Executes transformation locally using real Data Cloud data.

### Deploy
```bash
sf data-code-extension deploy \
  --target-org <org_alias> \
  --name <name> \
  [--version <version>] \
  [--description <description>] \
  [--cpu-size <CPU_L|CPU_XL|CPU_2XL|CPU_4XL>] \
  [--path <payload_dir>]
```
Packages and deploys to Data Cloud.

## Example Transformation

**Read from DLO, transform, write to DLO:**

```python
from datacustomcode import Client

client = Client()

# Read employee data from DLO
employees = client.read_dlo('Employee__dll')

# Transform - uppercase position field
employees['position_upper'] = employees['position'].str.upper()

# Select output columns
output = employees[['id', 'name', 'position_upper']]

# Write to output DLO
client.write_to_dlo('Employee_Upper__dll', output, 'overwrite')

print(f"Processed {len(output)} employee records")
```

## Project Structure

After `init`, you'll have:

```
my-transform/
├── payload/
│   ├── entrypoint.py      # Your transformation code
│   ├── config.json        # Permissions and configuration
│   └── requirements.txt   # Python dependencies
└── README.md
```

## Common Operations

### Read/Write DLOs
```python
# Read
df = client.read_dlo('Employee__dll')

# Write (modes: 'overwrite', 'append')
client.write_to_dlo('Employee_Upper__dll', df, 'overwrite')
```

### Read/Write DMOs
```python
# Read
df = client.read_dmo('EmployeeDMO')

# Write (modes: 'upsert', 'insert')
client.write_to_dmo('EmployeeDMO', df, 'upsert')
```

### Data Transformations
```python
import pandas as pd

# Filter
active_employees = df[df['status'] == 'Active']

# Add computed column
df['full_name'] = df['first_name'] + ' ' + df['last_name']

# Aggregate
summary = df.groupby('department').agg({'salary': 'mean'})

# Join
merged = employees.merge(departments, on='dept_id')
```

## Troubleshooting

### Plugin Not Found
```bash
sf plugins install @salesforce/plugin-data-codeextension
```

### Python SDK Missing
```bash
pip install salesforce-data-customcode
datacustomcode version  # Verify
```

### Wrong Python Version
```bash
# Use pyenv to manage versions
pyenv install 3.11.0
pyenv local 3.11.0
python --version  # Verify 3.11.x
```

### Docker Not Running
- Start Docker Desktop
- Or: `sudo systemctl start docker` (Linux)

### Org Not Connected
```bash
sf org login web --alias <org_alias>
sf org list  # Verify
```

### Config.json Missing
```bash
sf data-code-extension scan ./payload/entrypoint.py
```

### DLO Not Found
- Use DLO Schema skill to list DLOs
- Verify DLO name ends with `__dll`
- Check read permissions in config.json

## CPU Size Selection

Choose based on data volume:

| CPU Size | Use Case | Data Volume |
|----------|----------|-------------|
| CPU_L | Small datasets | < 1M records |
| CPU_XL | Medium datasets | 1M-5M records |
| CPU_2XL | Large datasets (default) | 5M-10M records |
| CPU_4XL | Very large datasets | > 10M records |

## Integration with Other Skills

### With DLO Schema Skill
```
1. "Show me all DLOs in afvibe"
2. "Get schema for Employee__dll"
3. "Create a code extension to read Employee__dll and transform it"
```

### With Datakit Workflow
```
1. Create DLO via code extension
2. Map DLO to DMO using datakit workflow
3. Create segments from DMO
```

## Example Use Cases

### 1. Data Enrichment
Read employee data, lookup additional info, write enriched data back.

### 2. Data Cleansing
Read raw data, standardize formats, remove duplicates, write clean data.

### 3. Aggregation
Read transaction data, calculate summaries, write aggregated metrics.

### 4. Multi-Source Join
Read from multiple DLOs, join on keys, write unified view.

### 5. Data Validation
Read data, check quality rules, write valid records and flag errors.

## Best Practices

### Development
1. Always scan after code changes
2. Test locally before deploying
3. Use semantic versioning
4. Add descriptive deployment names

### Code Quality
1. Add print statements for logging
2. Handle errors with try/except
3. Validate input data types
4. Document transformation logic

### Performance
1. Choose appropriate CPU size
2. Filter data early in pipeline
3. Select only needed columns
4. Process in batches for large datasets

### Security
1. Never hardcode credentials
2. Use SF CLI authentication only
3. Validate all input data
4. Limit write permissions in config

## Files Created

```
datacloud_code_extension/
├── SKILL.md              # Complete skill documentation
├── README.md             # This file
└── quick-reference.md    # Command cheat sheet
```

## Resources

- **SF CLI Plugin**: https://github.com/salesforcecli/plugin-data-code-extension
- **Python SDK**: https://github.com/forcedotcom/datacloud-customcode-python-sdk
- **Data Cloud Docs**: https://help.salesforce.com/s/articleView?id=sf.c360_a_intro.htm
- **SDK on PyPI**: https://pypi.org/project/salesforce-data-customcode/

## Command Flow

```
┌─────────────────────────────────────────────────────┐
│  1. INIT                                            │
│  sf data-code-extension init my-project             │
│  Creates: entrypoint.py, config.json, requirements  │
└─────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────┐
│  2. DEVELOP                                         │
│  Edit payload/entrypoint.py                         │
│  Write transformation logic                         │
└─────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────┐
│  3. SCAN                                            │
│  sf data-code-extension scan --entrypoint ./payload/entrypoint.py│
│  Updates: config.json, requirements.txt             │
└─────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────┐
│  4. RUN (Local Test)                                │
│  sf data-code-extension run --entrypoint            │
│  ./payload/entrypoint.py --target-org afvibe        │
└─────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────┐
│  5. DEPLOY                                          │
│  sf data-code-extension deploy --target-org afvibe  │
│  --name Employee_Upper --package-version 1.0.0      │
|  --description "Upper case Employee position column"│
│  --package-dir ./payload                            │
└─────────────────────────────────────────────────────┘
```

## Version History

- **v1.0** (2026-03-26) - Initial release
  - Complete init/scan/run/deploy workflow
  - Comprehensive error handling
  - Integration with DLO Schema skill
  - Full documentation

## Support

For issues or questions:
- SF CLI Plugin: https://github.com/salesforcecli/plugin-data-code-extension/issues
- Python SDK: https://github.com/forcedotcom/datacloud-customcode-python-sdk/issues

## The Skill is Ready! 🚀

Try it now:
```
"Create a code extension to uppercase employee positions"
"Deploy my transform to Data Cloud"
```
