# developing-datacloud-code-extension Skill

## Overview

A skill that provides a complete workflow for developing, testing, and deploying custom Python code extensions to Salesforce Data Cloud using the SF CLI plugin.

## What It Does

This skill helps you create Data Cloud Code Extensions through a complete workflow:

1. **Init** - Create new code extension project with scaffolding
2. **Develop** - Write Python transformation logic
3. **Scan** - Auto-detect permissions and generate config
4. **Run** - Test locally against Data Cloud org
5. **Deploy** - Package and deploy to Data Cloud

## Usage

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
sf data-code-extension script init --package-dir <directory>

# Scan for permissions
sf data-code-extension script scan --entrypoint ./payload/entrypoint.py

# Test locally
sf data-code-extension script run --entrypoint ./payload/entrypoint.py --target-org <org_alias>

# Deploy
sf data-code-extension script deploy --target-org <org_alias> --name <name> --package-version <version> --description <description> --package-dir ./payload
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
sf data-code-extension script init --package-dir .

# 2. Edit payload/entrypoint.py with your transformation

# 3. Scan for permissions
sf data-code-extension script scan --entrypoint ./payload/entrypoint.py

# 4. Test locally
sf data-code-extension script run --entrypoint ./payload/entrypoint.py --target-org afvibe

# 5. Deploy (MUST include --package-dir ./payload)
sf data-code-extension script deploy \
  --target-org afvibe \
  --name Employee_Upper \
  --package-version 1.0.0 \
  --description "Uppercase employee positions" \
  --package-dir ./payload
```

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

## Troubleshooting

| Error | Quick Fix |
|-------|-----------|
| Plugin not found | `sf plugins install @salesforce/plugin-data-codeextension` |
| Python SDK missing | `pip install salesforce-data-customcode` |
| Wrong Python version | Use pyenv to install 3.11.0 |
| Org not connected | `sf org login web --alias <alias>` |
| Config missing | Run scan command |
| DLO not found | Check DLO name, use getting-datacloud-schema skill |
| Docker error | Start Docker Desktop |

## CPU Size Selection

| CPU Size | Use Case | Data Volume |
|----------|----------|-------------|
| CPU_L | Small datasets | < 1M records |
| CPU_XL | Medium datasets | 1M-5M records |
| CPU_2XL | Large datasets (default) | 5M-10M records |
| CPU_4XL | Very large datasets | > 10M records |

## Resources

- **SF CLI Plugin**: https://github.com/salesforcecli/plugin-data-code-extension
- **Python SDK**: https://github.com/forcedotcom/datacloud-customcode-python-sdk
- **Data Cloud Docs**: https://help.salesforce.com/s/articleView?id=sf.c360_a_intro.htm
- **SDK on PyPI**: https://pypi.org/project/salesforce-data-customcode/
