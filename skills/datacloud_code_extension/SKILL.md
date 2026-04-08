---
name: datacloud_code_extension
description: Develop and deploy Data Cloud Code Extensions using SF CLI plugin. Use this skill when creating custom Python transformations for Data Cloud, deploying code extensions, or testing data transformations. Supports init, run, scan, and deploy operations.
---

# datacloud_code_extension Skill

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

**Examples:**
```bash
# Create script project in new directory
sf data-code-extension script init --package-dir ./my-transform

# Create function project in current directory
sf data-code-extension function init --package-dir .
```

**What it creates:**
```
my-transform/              # ← Project root
├── payload/               # ← CRITICAL: This is what --package-dir must point to for deploy
│   ├── entrypoint.py      # Main transformation code
│   ├── requirements.txt   # Python dependencies
│   └── config.json        # Code extension configuration
└── README.md
```

## Directory Context During Workflow

**IMPORTANT:** Understanding the directory structure is critical for successful deployment.

After running `init`, your structure looks like:

```
my-transform/              # ← Project root (run commands from here)
├── payload/               # ← THIS directory contains deployable code
│   ├── entrypoint.py
│   ├── config.json
│   └── requirements.txt
└── README.md
```

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

    # Process incoming record
    input_data = event['data']

    # Transform
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
sf data-code-extension script scan --entrypoint <entrypoint_file>
```

**Example:**
```bash
# Scan and update config.json
sf data-code-extension script scan --entrypoint ./payload/entrypoint.py
```

**What it detects:**
- Read permissions for DLOs/DMOs
- Write permissions for DLOs/DMOs
- Python package dependencies
- Updates `config.json` and `requirements.txt`

**Example config.json:**
```json
{
  "version": "1.0",
  "permissions": {
    "read": ["Employee__dll"],
    "write": ["Employee_Upper__dll"]
  },
  "resources": {
    "cpu_size": "CPU_2XL"
  }
}
```

### Phase 4: Validate DLO Schema (Pre-Test Check)

**CRITICAL: Before running tests locally, validate that all DLOs used in your code exist and have the expected fields.**

This prevents runtime errors and ensures your transformation will work with the actual Data Cloud schema.

#### Step 4a: Extract DLOs from config.json

After scanning, review the generated `config.json` to identify all DLOs:

```bash
cat payload/config.json
```

Look for DLOs in the `permissions` section:
```json
{
  "permissions": {
    "read": ["Employee__dll", "Department__dll"],
    "write": ["Employee_Upper__dll"]
  }
}
```

#### Step 4b: Validate Each DLO Schema

**Use the `datacloud_schema` skill to verify DLOs exist and check field names.**

For each DLO referenced in your code:

1. **Verify DLO exists:**
   ```
   Ask Claude: "Use datacloud_schema skill to check if Employee__dll exists in afvibe"
   ```

   Or manually:
   ```bash
   python3 ~/.a4drules/skills/datacloud_schema/scripts/get_dlo_schema.py afvibe Employee__dll
   ```

2. **Verify field names match:**

   Compare fields used in your `entrypoint.py` against the DLO schema:

   **In your code:**
   ```python
   df['position_upper'] = df['position'].str.upper()
   ```

   **Verify in schema:**
   - Check that `position` field exists in Employee__dll
   - Check data type is Text
   - Verify you have read permissions

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

**Common Issues to Check:**

| Issue | Check | Fix |
|-------|-------|-----|
| DLO doesn't exist | Use datacloud_schema skill | Create DLO first or update code |
| Field name typo | Compare code vs. schema | Fix field name in entrypoint.py |
| Wrong data type | Check schema data type | Update transformation logic |
| Missing permissions | Check config.json | Re-run scan |

**Example Validation Workflow:**

```bash
# 1. Check what DLOs are used
cat payload/config.json

# 2. Validate source DLO exists and get schema
python3 ~/.a4drules/skills/datacloud_schema/scripts/get_dlo_schema.py afvibe Employee__dll

# 3. Verify field 'position' exists in schema output
# Look for: name: position__c (or position)

# 4. Check target DLO exists
python3 ~/.a4drules/skills/datacloud_schema/scripts/get_dlo_schema.py afvibe Employee_Upper__dll

# 5. If all checks pass, proceed to run
```

### Phase 5: Test Locally

After validating DLO schemas, run the code extension locally against your Data Cloud org.

**Command:**
```bash
sf data-code-extension script run --entrypoint <entrypoint_file> --target-org <org_alias> [options]
```

**Options:**
- `--target-org, -o` - SF CLI org alias (required)
- `--config-file, -c` - Custom config file path

**Example:**
```bash
# Run with default config (after schema validation)
sf data-code-extension script run --entrypoint ./payload/entrypoint.py --target-org afvibe

# Run with custom config
sf data-code-extension script run --entrypoint ./payload/entrypoint.py -o afvibe -c custom-config.json
```

**What it does:**
- Executes transformation locally
- Reads/writes data from/to actual Data Cloud org
- Shows execution logs and errors
- Tests logic before deployment

**Monitor output for:**
- Data read/write operations
- Transformation results
- Errors or warnings
- Execution time

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

**Example from project root:**
```bash
# Basic deployment (MUST include --package-dir ./payload)
sf data-code-extension script deploy \
  --target-org afvibe \
  --name Employee_Upper \
  --package-version 1.0.0 \
  --description "Uppercase employee positions" \
  --package-dir ./payload

# Full deployment with all options
sf data-code-extension script deploy \
  --target-org afvibe \
  --name Employee_Upper \
  --package-version 1.0.0 \
  --description "Uppercase employee positions" \
  --cpu-size CPU_4XL \
  --package-dir ./payload
```

**Example with full path (if not in project root):**
```bash
sf data-code-extension script deploy \
  --target-org afvibe \
  --name Employee_Upper \
  --package-version 1.0.0 \
  --description "Uppercase employee positions" \
  --package-dir /full/path/to/my-transform/payload
```

**What it does:**
- Packages code with dependencies using Docker
- Uploads to Data Cloud
- Creates deployment record
- Makes code available for execution in UI

**After deployment:**
- Navigate to Data Cloud in Salesforce UI
- Go to Data Transforms section
- Find your deployment by name
- Click "Run Now" to execute
- Schedule for recurring execution

## Complete Workflow Example

Here's a complete end-to-end example for creating an Employee uppercase transformation:

```bash
# 1. Create project directory (or use existing directory)
mkdir employee-transform && cd employee-transform

# 2. Initialize script project
sf data-code-extension script init --package-dir .

# 3. Edit payload/entrypoint.py (see code below)

# 4. Scan for permissions
sf data-code-extension script scan --entrypoint ./payload/entrypoint.py

# 5. Validate DLO schemas (CRITICAL: check before testing)
# Check config.json for DLOs used
cat payload/config.json
# Validate Employee__dll exists and has 'position' field
python3 ~/.a4drules/skills/datacloud_schema/scripts/get_dlo_schema.py afvibe Employee__dll
# Validate Employee_Upper__dll exists (target DLO)
python3 ~/.a4drules/skills/datacloud_schema/scripts/get_dlo_schema.py afvibe Employee_Upper__dll

# 6. Test locally (after DLO validation passes)
sf data-code-extension script run --entrypoint ./payload/entrypoint.py --target-org afvibe

# 7. Deploy to Data Cloud (CRITICAL: include --package-dir ./payload)
sf data-code-extension script deploy \
  --target-org afvibe \
  --name Employee_Upper \
  --package-version 1.0.0 \
  --description "Uppercase employee positions" \
  --package-dir ./payload
```

**entrypoint.py code:**
```python
from datacustomcode import Client

client = Client()

# Read employee data
employees = client.read_dlo('Employee__dll')

# Transform - uppercase position field
employees['position_upper'] = employees['position'].str.upper()

# Select relevant columns
output = employees[['id', 'name', 'position_upper']]

# Write to output DLO
client.write_to_dlo('Employee_Upper__dll', output, 'overwrite')

print(f"Processed {len(output)} employee records")
```

## Error Handling

### Common Issues and Solutions

**1. SF CLI Plugin Not Found**
```
Error: command data-code-extension not found
```
Solution:
```bash
sf plugins install @salesforce/plugin-data-codeextension
```

**2. Python SDK Not Installed**
```
Error: datacustomcode CLI not found
```
Solution:
```bash
pip install salesforce-data-customcode
datacustomcode version  # Verify
```

**3. Wrong Python Version**
```
Error: Python version mismatch
```
Solution:
```bash
python --version  # Should show 3.11.x
# Use pyenv to manage Python versions
pyenv install 3.11.0
pyenv local 3.11.0
```

**4. Docker Not Running**
```
Error: Cannot connect to Docker daemon
```
Solution:
- Start Docker Desktop
- Or start Docker service: `sudo systemctl start docker`

**5. Org Not Authenticated**
```
Error: No org found for alias 'afvibe'
```
Solution:
```bash
sf org login web --alias afvibe
sf org list  # Verify
```

**6. Config.json Missing**
```
Error: config.json not found
```
Solution:
```bash
sf data-code-extension scan ./payload/entrypoint.py
```

**7. DLO Not Found During Run**
```
Error: DLO 'Employee__dll' not found
```
Solution:
- Verify DLO exists in org (use DLO Schema skill)
- Check spelling and suffix (__dll)
- Ensure proper read permissions in config.json

**8. Permission Denied During Write**
```
Error: Permission denied writing to 'Employee_Upper__dll'
```
Solution:
- Run scan to update permissions: `sf data-code-extension script scan ./payload/entrypoint.py`
- Verify target DLO exists and is writable
- Check Data Cloud permissions in org

**9. Deploy Fails - Wrong Directory Path**
```
Error: Cannot find entrypoint.py or config.json
Error: No such file or directory: './entrypoint.py'
Error: Deploy failed - invalid path
```
Solution:
**CRITICAL:** Ensure `--package-dir` argument points to the `payload` directory, not the project root.

```bash
# WRONG - Missing --package-dir argument
sf data-code-extension script deploy -o afvibe -n MyTransform

# WRONG - Pointing to project root instead of payload
sf data-code-extension script deploy -o afvibe -n MyTransform --package-dir .

# CORRECT - From project root, point to payload directory, includes package-version
sf data-code-extension script deploy -o afvibe -n MyTransform --package-dir ./payload --package-version 1.0.0 --description "Uppercase employee positions" 

# CORRECT - With full path
sf data-code-extension script deploy -o afvibe -n MyTransform --package-version 1.0.0 --package-dir /full/path/to/project/payload --description "Uppercase employee positions"
```

Check your current directory:
```bash
pwd  # Should be in project root
ls   # Should see 'payload' directory
ls payload/  # Should see entrypoint.py, config.json, requirements.txt
```

## Best Practices

### Development
1. **Always scan before testing**: Run scan after code changes
2. **Test locally first**: Use `run` command before deploying
3. **Use version control**: Git commit after each successful test
4. **Version your deployments**: Use semantic versioning (1.0.0, 1.1.0, etc.)
5. **Deploy from project root with --package-dir ./payload**: ALWAYS specify the payload directory explicitly in deploy commands

### Code Organization
1. **Keep entrypoint.py focused**: Main transformation logic only
2. **Extract helpers**: Create separate modules for reusable functions
3. **Add logging**: Use print statements for debugging
4. **Handle errors**: Add try/except blocks for data operations

### Performance
1. **Choose appropriate CPU size**:
   - CPU_L: Small datasets (< 1M records)
   - CPU_2XL: Medium datasets (1M-10M records)
   - CPU_4XL: Large datasets (> 10M records)
2. **Filter early**: Read only needed columns/rows
3. **Batch operations**: Process data in chunks for large datasets

### Security
1. **No hardcoded credentials**: Use SF CLI authentication only
2. **Validate input data**: Check for nulls and data types
3. **Limit write permissions**: Only grant necessary DLO/DMO access

## Integration with Other Skills

**Use with DLO Schema Skill (CRITICAL for validation):**

The `datacloud_schema` skill is **required** for validating DLOs before testing code extensions.

**Workflow Integration:**
```
1. List all DLOs: "Show me all DLOs in afvibe"
   → Verify target DLOs exist in org

2. Get DLO schema: "What's the schema for Employee__dll?"
   → Validate field names used in code

3. Check field types: Review schema output for data types
   → Ensure transformation logic is compatible

4. Validate before test: Use schema validation BEFORE running locally
   → Prevents runtime errors from missing fields/DLOs

5. Create code extension: "Create a code extension to read Employee__dll"
   → Design transformation based on actual schema
```

**Example Integrated Workflow:**
```bash
# Step 1: Check what DLOs exist
python3 ~/.a4drules/skills/datacloud_schema/scripts/get_dlo_schema.py afvibe

# Step 2: Get schema for source DLO
python3 ~/.a4drules/skills/datacloud_schema/scripts/get_dlo_schema.py afvibe Employee__dll

# Step 3: Design code extension based on schema
# (Write entrypoint.py using fields from schema)

# Step 4: Scan for permissions
sf data-code-extension script scan --entrypoint ./payload/entrypoint.py

# Step 5: Validate all DLOs referenced in config.json
cat payload/config.json
python3 ~/.a4drules/skills/datacloud_schema/scripts/get_dlo_schema.py afvibe Employee__dll
python3 ~/.a4drules/skills/datacloud_schema/scripts/get_dlo_schema.py afvibe Employee_Upper__dll

# Step 6: Test locally (after validation passes)
sf data-code-extension script run --entrypoint ./payload/entrypoint.py --target-org afvibe

# Step 7: Deploy
sf data-code-extension script deploy --target-org afvibe --name Employee_Upper --package-dir ./payload --package-version 1.0.0 --description "Uppercase employee positions"
```

**Use with Datakit Workflow:**
```
1. Create DLO via code extension
2. Map DLO to DMO using datakit workflow
3. Use DMO in segments and activations
```

## Output Interpretation

### Scan Output
```
Scanning ./payload/entrypoint.py...
Found permissions:
  Read: Employee__dll
  Write: Employee_Upper__dll
Found dependencies:
  pandas==2.0.0
  numpy==1.24.0
Updated: payload/config.json
Updated: payload/requirements.txt
```

### Run Output
```
Reading from Employee__dll...
Records read: 12
Transforming data...
Writing to Employee_Upper__dll...
Records written: 12
Execution completed in 2.3s
```

### Deploy Output
```
Building Docker image...
Packaging dependencies...
Uploading to Data Cloud...
Deployment 'Employee_Upper' created successfully
ID: 2dgXXXXXXXXXXXXXXX
Version: 1.0.0
Status: ACTIVE
```

## Advanced Usage

### Custom Dependencies
Add to `requirements.txt`:
```txt
pandas==2.0.0
numpy==1.24.0
scikit-learn==1.3.0
```

### Multiple DLO Operations
```python
# Read from multiple DLOs
employees = client.read_dlo('Employee__dll')
departments = client.read_dlo('Department__dll')

# Join data
merged = employees.merge(departments, on='dept_id')

# Write to multiple outputs
client.write_to_dlo('Employee_Enriched__dll', merged, 'overwrite')
client.write_to_dmo('EmployeeDMO', merged, 'upsert')
```

### Conditional Logic
```python
# Read data
df = client.read_dlo('Employee__dll')

# Apply transformations based on conditions
df['grade'] = df['position'].apply(lambda x:
    'Senior' if 'Director' in x or 'VP' in x else 'Junior'
)

# Filter and write
senior_employees = df[df['grade'] == 'Senior']
client.write_to_dlo('Senior_Employees__dll', senior_employees, 'overwrite')
```

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
