---
name: developing-datacloud-code-extension
description: "Develop and deploy Data Cloud Code Extensions using SF CLI plugin. Use this skill when creating custom Python transformations for Data Cloud, deploying code extensions, or testing data transformations. Supports init, run, scan, and deploy operations."
---

# developing-datacloud-code-extension Skill

## Overview

This skill provides a complete workflow for developing, testing, and deploying custom Python code extensions to Salesforce Data Cloud. Code extensions allow you to write Python transformations that read from and write to Data Lake Objects (DLOs) and Data Model Objects (DMOs).

## When to Use

- User wants to create a new code extension project
- User needs to test a code extension locally
- User wants to scan code for required permissions
- User needs to deploy a code extension to Data Cloud
- User is working with Data Cloud transformations
- User wants to read/write DLO or DMO data programmatically

## Prerequisites Check

Before executing any code extension commands, verify prerequisites:

1. **SF CLI with plugin installed**
   ```bash
   sf plugins --core | grep data-code-extension
   ```
   If not installed:
   ```bash
   sf plugins install @salesforce/plugin-data-codeextension
   ```

2. **Python 3.11**
   ```bash
   python --version  # Should show 3.11.x
   ```

3. **Data Cloud Custom Code SDK**
   ```bash
   pip list | grep salesforce-data-customcode
   ```
   If not installed:
   ```bash
   pip install salesforce-data-customcode
   ```

4. **Docker running** (for deploy only)
   ```bash
   docker ps
   ```

5. **Authenticated org**
   ```bash
   sf org display --target-org <org_alias> --json
   ```

## Skill Workflow

### Phase 1: Initialize Project

Create a new code extension project with scaffolding.

**Commands:**

For **script-based** code extensions (batch transformations):
```bash
sf data-code-extension script init --package-dir <directory>
```

For **function-based** code extensions (real-time):
```bash
sf data-code-extension function init --package-dir <directory>
```

**Required Option:**
- `--package-dir, -p` - Directory path where the package will be created

**What it creates:**
```
my-transform/              # Project root
├── payload/               # CRITICAL: This is what --package-dir must point to for deploy
│   ├── entrypoint.py      # Main transformation code
│   ├── requirements.txt   # Python dependencies
│   └── config.json        # Code extension configuration
└── README.md
```

## Directory Context During Workflow

**IMPORTANT:** Understanding the directory structure is critical for successful deployment.

**Commands and their directory requirements:**

| Command | Run From | Path/File Argument |
|---------|----------|-------------------|
| `init` | Parent directory | `<project-name>` or `.` |
| `scan` | Project root | `./payload/entrypoint.py` |
| `run` | Project root | `./payload/entrypoint.py` |
| `deploy` | Project root | `--package-dir ./payload` (**REQUIRED**) |

**CRITICAL: The `--package-dir` argument in deploy command MUST point to the `payload` directory, not the project root.**

### Phase 2: Develop Transformation

Edit `payload/entrypoint.py` with transformation logic.

**Script Example (Batch):**
```python
from datacustomcode import Client

client = Client()

# Read from DLO
df = client.read_dlo('Employee__dll')

# Transform data (uppercase position field)
df['position_upper'] = df['position'].str.upper()

# Write to output DLO
client.write_to_dlo('Employee_Upper__dll', df, 'overwrite')
```

**Function Example (Real-time):**
```python
from datacustomcode import FunctionClient

def transform(event, context):
    client = FunctionClient(context)
    input_data = event['data']
    output = {
        'name': input_data['name'].upper(),
        'status': 'processed'
    }
    return output
```

**Common Operations:**
- `client.read_dlo('DLO_Name__dll')` - Read from DLO
- `client.read_dmo('DMO_Name')` - Read from DMO
- `client.write_to_dlo('DLO_Name__dll', df, 'overwrite')` - Write to DLO
- `client.write_to_dmo('DMO_Name', df, 'upsert')` - Write to DMO

### Phase 3: Scan for Permissions

Scan the entrypoint file to detect required permissions and generate config.json.

**Command:**
```bash
sf data-code-extension script scan --entrypoint ./payload/entrypoint.py
```

**What it detects:**
- Read permissions for DLOs/DMOs
- Write permissions for DLOs/DMOs
- Python package dependencies
- Updates `config.json` and `requirements.txt`

### Phase 4: Validate DLO Schema (Pre-Test Check)

**CRITICAL: Before running tests locally, validate that all DLOs used in your code exist and have the expected fields.**

#### Step 4a: Extract DLOs from config.json

After scanning, review the generated `config.json` to identify all DLOs:

```bash
cat payload/config.json
```

#### Step 4b: Validate Each DLO Schema

**Use the `getting-datacloud-schema` skill to verify DLOs exist and check field names.**

For each DLO referenced in your code:

1. **Verify DLO exists:**
   ```bash
   python3 scripts/get_dlo_schema.py <org_alias> <dlo_name>
   ```

2. **Verify field names match** — compare fields used in your `entrypoint.py` against the DLO schema.

3. **Check all DLOs:**
   - Validate all DLOs in `read` permissions
   - Validate all DLOs in `write` permissions
   - Check field names match exactly (case-sensitive)
   - Verify data types are compatible with operations

#### Step 4c: Validation Checklist

Before proceeding to run, ensure:

- [ ] All DLOs in config.json exist in target org
- [ ] All field names used in code exist in DLO schemas
- [ ] Field data types match your transformation logic
- [ ] Primary key fields are correctly identified
- [ ] Write target DLOs are created and accessible

### Phase 5: Test Locally

After validating DLO schemas, run the code extension locally against your Data Cloud org.

**Command:**
```bash
sf data-code-extension script run --entrypoint <entrypoint_file> --target-org <org_alias> [options]
```

**Options:**
- `--target-org, -o` - SF CLI org alias (required)
- `--config-file, -c` - Custom config file path

**If you get errors:**
- Re-validate DLO schemas
- Check field names are exact matches
- Verify data types are compatible
- Review error messages for field/DLO issues

### Phase 6: Deploy to Data Cloud

Deploy the code extension to Data Cloud for scheduled or on-demand execution.

**CRITICAL: You MUST specify `--package-dir ./payload` to point to the payload directory created by init.**

**Command:**
```bash
sf data-code-extension script deploy --target-org <org_alias> --name <name> --package-dir ./payload --package-version <version> --description <description> [options]
```

**Required Options:**
- `--target-org, -o` - SF CLI org alias
- `--name, -n` - Name for code extension deployment
- `--package-dir` - Path to payload directory (**REQUIRED** - must be `./payload` when running from project root)
- `--package-version` - Version string (default: 0.0.1)
- `--description` - Description of code extension

**Optional Options:**
- `--cpu-size` - CPU size: CPU_L, CPU_XL, CPU_2XL (default), CPU_4XL
- `--function-invoke-opt` - Function invoke options (for function type)
- `--network` - Docker network (default: default)

**After deployment:**
- Navigate to Data Cloud in Salesforce UI
- Go to Data Transforms section
- Find your deployment by name
- Click "Run Now" to execute
- Schedule for recurring execution

## Error Handling

### Common Issues and Solutions

| Error | Solution |
|-------|----------|
| `command data-code-extension not found` | `sf plugins install @salesforce/plugin-data-codeextension` |
| `datacustomcode CLI not found` | `pip install salesforce-data-customcode` |
| `Python version mismatch` | Use pyenv: `pyenv install 3.11.0 && pyenv local 3.11.0` |
| `Cannot connect to Docker daemon` | Start Docker Desktop |
| `No org found for alias` | `sf org login web --alias <org_alias>` |
| `config.json not found` | `sf data-code-extension script scan --entrypoint ./payload/entrypoint.py` |
| `DLO not found` | Verify DLO exists (use getting-datacloud-schema skill), check spelling and `__dll` suffix |
| `Permission denied writing` | Re-run scan, verify target DLO exists and is writable |
| `Deploy fails - wrong directory` | Ensure `--package-dir` points to `payload/` directory, not project root |

## Best Practices

### Development
1. Always scan before testing — run scan after code changes
2. Test locally first — use `run` command before deploying
3. Use version control — git commit after each successful test
4. Version your deployments — use semantic versioning (1.0.0, 1.1.0, etc.)
5. Deploy from project root with `--package-dir ./payload`

### Performance
- **CPU_L**: Small datasets (< 1M records)
- **CPU_2XL**: Medium datasets (1M-10M records)
- **CPU_4XL**: Large datasets (> 10M records)

### Security
1. No hardcoded credentials — use SF CLI authentication only
2. Validate input data — check for nulls and data types
3. Limit write permissions — only grant necessary DLO/DMO access

## Integration with Other Skills

**Use with getting-datacloud-schema skill (CRITICAL for validation):**

The `getting-datacloud-schema` skill is **required** for validating DLOs before testing code extensions.

**Use with Datakit Workflow:**
1. Create DLO via code extension
2. Map DLO to DMO using datakit workflow
3. Use DMO in segments and activations

## Command Reference

| Command | Purpose | Required Args |
|---------|---------|---------------|
| `script init` | Create new script project | --package-dir |
| `function init` | Create new function project | --package-dir |
| `script scan` | Generate config | entrypoint file |
| `script run` | Test locally | entrypoint file, --target-org |
| `script deploy` | Deploy to Data Cloud | --target-org, --name, --package-dir, --package-version, --description |

## Resources

- SF CLI Plugin: https://github.com/salesforcecli/plugin-data-code-extension
- Python SDK: https://github.com/forcedotcom/datacloud-customcode-python-sdk
- Data Cloud Docs: https://help.salesforce.com/s/articleView?id=sf.c360_a_intro.htm
- Python SDK PyPI: https://pypi.org/project/salesforce-data-customcode/

## Notes

- Code extensions run in isolated Python 3.11 environment
- Docker is required only for deployment, not for local testing
- Use SF CLI authentication only (no separate credential files)
- Scan command auto-detects permissions from code
- Local run uses actual Data Cloud data (not mocked)
- Deployments are versioned and can be rolled back in UI
