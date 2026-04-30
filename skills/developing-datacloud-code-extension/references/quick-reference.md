# Data Cloud Code Extension - Quick Reference

## Command Cheat Sheet

### Initialize Project
```bash
# Create script project
sf data-code-extension script init --package-dir <directory>

# Create function project
sf data-code-extension function init --package-dir <directory>

# Examples
sf data-code-extension script init --package-dir .
sf data-code-extension script init --package-dir my-transform
```

### Scan for Permissions
```bash
# Basic scan
sf data-code-extension script scan --entrypoint ./payload/entrypoint.py

# Preview without saving
sf data-code-extension script scan --entrypoint ./payload/entrypoint.py --dry-run

# Custom config location
sf data-code-extension script scan --entrypoint ./payload/entrypoint.py --config ./custom-config.json

# Skip requirements.txt
sf data-code-extension script scan --entrypoint ./payload/entrypoint.py --no-requirements
```

### Run Locally
```bash
# Basic run
sf data-code-extension script run --entrypoint ./payload/entrypoint.py --target-org <org_alias>

# With custom config
sf data-code-extension script run --entrypoint ./payload/entrypoint.py -o <org_alias> -c custom-config.json

# Examples
sf data-code-extension script run --entrypoint ./payload/entrypoint.py --target-org afvibe
sf data-code-extension script run --entrypoint ./payload/entrypoint.py -o afvibe
```

### Deploy
```bash
# Minimal deployment (MUST include --package-dir ./payload)
sf data-code-extension script deploy \
  --target-org <org_alias> \
  --name <name> \
  --package-version <version> \
  --description "<description>" \
  --package-dir ./payload

# Full options
sf data-code-extension script deploy \
  --target-org <org_alias> \
  --name <name> \
  --package-version <version> \
  --description "<description>" \
  --cpu-size <CPU_L|CPU_XL|CPU_2XL|CPU_4XL> \
  --package-dir ./payload

# Examples (CRITICAL: Always include --package-dir ./payload)
sf data-code-extension script deploy \
  --target-org afvibe \
  --name Employee_Upper \
  --package-version 1.0.0 \
  --description "Uppercase employee positions" \
  --package-dir ./payload
```

## Common Workflows

### New Project from Scratch
```bash
# 1. Create directory
mkdir my-transform && cd my-transform

# 2. Initialize
sf data-code-extension script init --package-dir .

# 3. Edit payload/entrypoint.py with your transformation

# 4. Scan
sf data-code-extension script scan --entrypoint ./payload/entrypoint.py

# 5. Test
sf data-code-extension script run --entrypoint ./payload/entrypoint.py --target-org afvibe

# 6. Deploy (MUST include --package-dir ./payload)
sf data-code-extension script deploy \
  --target-org afvibe \
  --name MyTransform \
  --package-version 1.0.0 \
  --description "My transformation" \
  --package-dir ./payload
```

### Update Existing Code Extension
```bash
# 1. Edit payload/entrypoint.py

# 2. Re-scan
sf data-code-extension script scan --entrypoint ./payload/entrypoint.py

# 3. Test
sf data-code-extension script run --entrypoint ./payload/entrypoint.py -o afvibe

# 4. Deploy with new version (include --package-dir ./payload)
sf data-code-extension script deploy \
  -o afvibe \
  -n MyTransform \
  --package-version 1.1.0 \
  --description "Updated transformation" \
  --package-dir ./payload
```

## Python Code Patterns

### Read/Write DLO
```python
from datacustomcode import Client

client = Client()

# Read
df = client.read_dlo('Employee__dll')

# Transform
df['new_field'] = df['old_field'].str.upper()

# Write (modes: 'overwrite', 'append')
client.write_to_dlo('Output__dll', df, 'overwrite')
```

### Read/Write DMO
```python
# Read
df = client.read_dmo('EmployeeDMO')

# Write (modes: 'upsert', 'insert')
client.write_to_dmo('EmployeeDMO', df, 'upsert')
```

### Multiple DLO Operations
```python
# Read multiple
employees = client.read_dlo('Employee__dll')
departments = client.read_dlo('Department__dll')

# Join
merged = employees.merge(departments, on='dept_id')

# Write multiple
client.write_to_dlo('Enriched__dll', merged, 'overwrite')
client.write_to_dmo('EmployeeDMO', merged, 'upsert')
```

### Data Transformations
```python
import pandas as pd

# Filter
active = df[df['status'] == 'Active']

# Computed column
df['full_name'] = df['first'] + ' ' + df['last']

# Aggregate
summary = df.groupby('dept')['salary'].mean()

# Conditional
df['grade'] = df['position'].apply(
    lambda x: 'Senior' if 'VP' in x else 'Junior'
)
```

## Option Reference

### --cpu-size
- `CPU_L` - Small datasets (< 1M records)
- `CPU_XL` - Medium datasets (1M-5M)
- `CPU_2XL` - Large datasets (5M-10M) **[default]**
- `CPU_4XL` - Very large (> 10M records)

### Write Modes
- `overwrite` - Replace all data
- `append` - Add to existing data
- `upsert` - Update or insert (DMO only)
- `insert` - Insert only (DMO only)

## Troubleshooting Quick Fixes

```bash
# Plugin not found
sf plugins install @salesforce/plugin-data-codeextension

# Python SDK missing
pip install salesforce-data-customcode

# Verify Python version (must be 3.11.x)
python --version

# Org not connected
sf org login web --alias <org_alias>

# Config missing
sf data-code-extension script scan --entrypoint ./payload/entrypoint.py

# Docker not running (for deploy)
# Start Docker Desktop
```

## File Structure

```
my-project/
├── payload/
│   ├── entrypoint.py      # Main code
│   ├── config.json        # Auto-generated permissions
│   └── requirements.txt   # Auto-generated dependencies
└── README.md
```

## config.json Format

```json
{
  "version": "1.0",
  "permissions": {
    "read": ["Employee__dll", "Department__dll"],
    "write": ["Enriched__dll"]
  },
  "resources": {
    "cpu_size": "CPU_2XL"
  }
}
```

## Common Errors

| Error | Quick Fix |
|-------|-----------|
| Plugin not found | `sf plugins install @salesforce/plugin-data-codeextension` |
| Python SDK missing | `pip install salesforce-data-customcode` |
| Wrong Python version | Use pyenv to install 3.11.0 |
| Org not connected | `sf org login web --alias <alias>` |
| Config missing | Run scan command |
| DLO not found | Check DLO name, use getting-datacloud-schema skill |
| Docker error | Start Docker Desktop |

## Deployment Checklist

- [ ] Code written in entrypoint.py
- [ ] Scanned for permissions
- [ ] Tested locally
- [ ] Version number decided
- [ ] Description added
- [ ] CPU size chosen
- [ ] Docker running
- [ ] Org authenticated

## Resources

- Plugin: https://github.com/salesforcecli/plugin-data-code-extension
- Python SDK: https://github.com/forcedotcom/datacloud-customcode-python-sdk
- Data Cloud Docs: https://help.salesforce.com/s/articleView?id=sf.c360_a_intro.htm
