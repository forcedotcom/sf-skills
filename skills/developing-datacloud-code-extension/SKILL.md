---
name: developing-datacloud-code-extension
description: "Develop and deploy Data Cloud Code Extensions using SF CLI plugin. Use this skill when writing or updating code extension scripts, creating new projects, scanning, testing, or deploying. Covers the full lifecycle: write, init, scan, run, and deploy."
metadata:
  version: "1.0"
---

# developing-datacloud-code-extension Skill

## Overview

This skill provides a complete workflow for developing, testing, and deploying custom Python code extensions to Salesforce Data Cloud. Code extensions allow you to write Python transformations that read from and write to Data Lake Objects (DLOs) and Data Model Objects (DMOs).

## When to Use

- User wants to write or update a code extension script (entrypoint.py)
- User wants to create a new code extension project
- User needs to test a code extension locally
- User wants to scan code for required permissions
- User needs to deploy a code extension to Data Cloud
- User wants to run a deployed code extension in the org
- User wants to query code extension logs in an org
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
   If Docker is not running, automatically launch it and wait for the daemon:
   ```bash
   open -a Docker && for i in $(seq 1 30); do docker ps > /dev/null 2>&1 && echo "Docker ready" && break || sleep 2; done
   ```

5. **Authenticated org**
   ```bash
   sf org display --target-org <org_alias> --json
   ```

## Skill Workflow

### Phase 1: Initialize Project

Create a new code extension project with scaffolding.

**If you are called within a salesforce project, initialize code extensions inside a `code-extensions/` folder** — never in the salesforce project root.

**NEVER manually write, edit, or create `config.json`** — only the scan command generates it (phase 3).

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
my-transform/              # Code extensions project root
├── payload/               # CRITICAL: This is what --package-dir must point to for deploy
│   ├── entrypoint.py      # Main transformation code
│   └── config.json        # Code extension configuration
├── requirements.txt       # Python dependencies
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

`client.read_dlo()` returns a **PySpark DataFrame**, not Pandas. Data Cloud's sandboxed Spark environment blocks certain operations (UDFs, `rdd.map()`, Arrow config). The safest pattern for row-level Python transformations is `.toPandas()` → transform → `spark.createDataFrame()`:

```python
from pyspark.sql import SparkSession

from datacustomcode.client import Client
from datacustomcode.io.writer.base import WriteMode

def main():
    client = Client()

    # Read from DLO (returns PySpark DataFrame)
    df = client.read_dlo('Employee__dll')

    # Convert to Pandas, transform, convert back
    pdf = df.toPandas()
    pdf['position__c'] = pdf['position__c'].str.upper()
    spark = SparkSession.builder.getOrCreate()
    df_result = spark.createDataFrame(pdf, schema=df.schema)

    # Write to output DLO
    client.write_to_dlo('Employee_Upper__dll', df_result, write_mode=WriteMode.APPEND)

if __name__ == "__main__":
    main()
```

For PySpark-native column operations that don't require Python UDFs (e.g., `withColumn`, `filter`, `select`), you can operate directly on the DataFrame without converting to Pandas.

**Function Example (Real-time):**
```python
from datacustomcode.function_client import FunctionClient

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
- `client.read_dlo('DLO_Name__dll')` - Read from DLO (returns PySpark DataFrame)
- `client.read_dmo('DMO_Name')` - Read from DMO (returns PySpark DataFrame)
- `client.write_to_dlo('DLO_Name__dll', df, write_mode=WriteMode.APPEND)` - Write to DLO
- `client.write_to_dlo('DLO_Name__dll', df, write_mode=WriteMode.OVERWRITE)` - Overwrite DLO
- `client.write_to_dmo('DMO_Name', df, write_mode=WriteMode.UPSERT)` - Upsert to DMO

**Sandbox Limitations (Data Cloud Spark Environment):**
- `spark.sql.execution.pythonUDF.arrow.enabled` config is **blocked** — PySpark UDFs will fail
- `rdd.map()` is **blocked** — cannot use RDD-level Python transformations
- Use `.toPandas()` for row-level Python logic, then convert back with `spark.createDataFrame()`
- PySpark-native column operations (`withColumn`, `filter`, `select`, SQL expressions) work fine without conversion

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
- Generates/updates `config.json` and `requirements.txt`

### Phase 4: Validate DLO Schema (MANDATORY Pre-Test Gate)

**This phase is BLOCKING. You MUST NOT proceed to Phase 5 until every check below passes. Present findings to the user as a validation checklist before continuing.**

#### Step 4a: Extract DLOs from config.json

Read the scan-generated `config.json` to identify all DLOs:

```bash
cat payload/config.json
```

List every DLO from the `read` and `write` permission blocks.

#### Step 4b: Validate Each DLO Schema Against the Org

**Use the `getting-datacloud-schema` skill to verify DLOs exist and check field names.**

For each DLO referenced in your code:

1. **Verify DLO exists in the target org** — query the org schema for the DLO name.

2. **Verify field names match exactly (case-sensitive)** — compare every field used in `entrypoint.py` against the DLO schema returned from the org.

3. **Verify data types are compatible** — confirm that string operations target string fields, numeric operations target numeric fields, etc.

#### Step 4c: Validation Checklist (Present to User)

Before proceeding to run, present this checklist with pass/fail for each item:

- [ ] All DLOs in config.json `read` permissions exist in target org
- [ ] All DLOs in config.json `write` permissions exist in target org
- [ ] All field names used in code exist in their respective DLO schemas (case-sensitive)
- [ ] Field data types are compatible with transformation operations

### Phase 5: Run and Test Locally

After validating DLO schemas, run the code extension locally.

If you arrived here because you were asked to run a code extension in the org skip to phases 7a and 7b.

#### Step 5a: Determine Target Org

**Infer the default org** by running:
```bash
sf config get target-org --json
```

If a default org is found, present it to the user for confirmation rather than asking them to provide one from scratch.

#### Step 5b: Run the Code Extension

**For script code extensions:**
```bash
sf data-code-extension script run --entrypoint <entrypoint_file> --target-org <org_alias> [options]
```

**For function code extensions (with model callouts):**
```bash
sf data-code-extension function run --entrypoint <entrypoint_file> --test-with <test_json> --target-org <org_alias>
```

**For function code extensions (no model callouts):**
```bash
sf data-code-extension function run --entrypoint <entrypoint_file> --test-with <test_json>
```

**Options:**
- `--target-org, -o` - SF CLI org alias (required for scripts only)
- `--test-with, -t` - Path to test.json input (required for functions only)
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

After this phase, choose 7a or 7b, depending if it's a script or a function.

### Phase 7a: Run a Batch Transform Script in the Org (needs Data 360 MCP server - https://github.com/forcedotcom/d360-mcp-server).

- A deployed code extension script creates a matching Data Transform in the org
- The transform status will initially be `PROCESSING` — wait ~30 seconds and poll `d360_transform_get` until it becomes `ACTIVE` before attempting running it
- Continue with the next instructions:

#### Step 7a.1: Find the Transform

Use `d360_transform_list` to find the deployed code extension by name:
```
mcp__data360__execute(toolName="d360_transform_list", paramsJson="{}")
```

Look for the transform matching your deployment name (the `--name` value from deploy). It will have `"creationSource": "Code Extension"` in the response.

#### Step 7a.2: Run the Transform

Use `d360_transform_run` with the transform name (the `name` field, not `label`):
```
mcp__data360__execute(toolName="d360_transform_run", paramsJson="{\"transformId\":\"<transform_name>\"}")
```

A successful response returns `{"success": true}`.

**Note:** After triggering a run, the transform status will change to `PROCESSING`. Poll with `d360_transform_get` to check `lastRunStatus` for completion. If the status was `PROCESSING` right after deploy, wait for `ACTIVE` before running.

#### Step 7a.3: Verify the Output

Once the run completes successfully (`lastRunStatus: "SUCCESS"`), query the target DLO to confirm data was written:

```sql
SELECT * FROM <target_DLO>__dll LIMIT 10
```

Use `d360_query_sql` to execute the query. Check that:
- Records exist in the target DLO
- The transformed fields contain expected values
- Row count matches expectations (compare with source DLO if applicable)

### Phase 7b: Use a Chunking Function in a Search Index (needs Data 360 MCP server - https://github.com/forcedotcom/d360-mcp-server).

A deployed **function-based** code extension can be used as a custom chunking strategy in a Data Cloud Search Index. The function runs automatically each time the search index processes data — there's no manual "run" step.

#### Step 7b.1: Verify the Function is Deployed and Active

Use `d360_transform_list` or check the code extension list to confirm the function is deployed. Note the exact deployment name (e.g., `text_chunking_v2`) — this is the `function_name` value you'll use.

#### Step 7b.2: Create a Search Index with Custom Code Chunking

Use `d360_search_index_create`. The key difference from standard search indexes is the chunking configuration — use strategy `custom_code` with a `function_name` parameter pointing to your deployed function:

```json
"chunkingConfiguration": {
  "fieldLevelConfigurations": [
    {
      "sourceDmoDeveloperName": "YourSource__dlm",
      "sourceDmoFieldDeveloperName": "your_text_field__c",
      "config": {
        "id": "custom_code",
        "userValues": [
          {
            "id": "function_name",
            "value": "<your_deployed_function_name>"
          }
        ]
      }
    }
  ]
}
```

The `function_name` value must exactly match the `--name` used during `sf data-code-extension function deploy`.

#### Step 7b.3: The Function Runs Automatically

Unlike batch script transforms (Phase 7a), function-based code extensions used in search indexes do **not** need to be triggered manually. The search index processing pipeline invokes the function automatically when:
- The index is first created (processes existing data)
- New data arrives in the source DMO (if `processingType` is `NEAR_REALTIME`)

#### Step 7b.4: Verify the Index Built Successfully

Check the search index status:
```
mcp__data360__execute(toolName="d360_search_index_get", paramsJson="{\"developerName\":\"<index_name>\"}")
```

Look for `activationStatus: "ACTIVE"` and check `d360_search_index_process_history` for build completion details.

#### Step 7b.5: Verify Chunks

Query the chunk DMO to confirm your function produced the expected output:
```sql
SELECT chunk_text__c, seq_no__c 
FROM <ChunkDMO>__dlm 
LIMIT 10
```

### Phase 8: Monitor Logs (needs Data 360 MCP server - https://github.com/forcedotcom/d360-mcp-server).

Code extension `print()` output, when it runs in an org, is stored in `DataCustomCodeLogs__dll`. Query logs after a run:

```sql
SELECT Message__c, Timestamp__c 
FROM DataCustomCodeLogs__dll 
WHERE ProcessDefinitionName__c = '<transform_name>' 
ORDER BY Timestamp__c DESC 
LIMIT 50
```

Key fields:
- `ExecutionId__c` — unique ID per code extension execution
- `DataCustomCodeName__c` — the code extension name
- `ProcessDefinitionName__c` — the transform that triggered the run
- `Message__c` — the log message (from `print()` statements)
- `Timestamp__c` — when the log was emitted

To get logs for a specific run, filter by `ExecutionId__c`. To find the latest execution:
```sql
SELECT DISTINCT ExecutionId__c, MAX(Timestamp__c) as last_log
FROM DataCustomCodeLogs__dll
WHERE ProcessDefinitionName__c = '<transform_name>'
GROUP BY ExecutionId__c
ORDER BY last_log DESC
LIMIT 1
```

### Common Issues and Solutions

| Error | Solution |
|-------|----------|
| `command data-code-extension not found` | `sf plugins install @salesforce/plugin-data-codeextension` |
| `datacustomcode CLI not found` | `pip install salesforce-data-customcode` |
| `Python version mismatch` | Use pyenv: `pyenv install 3.11.0 && pyenv local 3.11.0` |
| `Cannot connect to Docker daemon` | Run `open -a Docker` and wait for daemon readiness |
| `No org found for alias` | `sf org login web --alias <org_alias>` |
| `config.json not found` | `sf data-code-extension script scan --entrypoint ./payload/entrypoint.py` |
| `DLO not found` | Verify DLO exists (use getting-datacloud-schema skill), check spelling and `__dll` suffix |
| `Permission denied writing` | Re-run scan, verify target DLO exists and is writable |
| `Deploy fails - wrong directory` | Ensure `--package-dir` points to `payload/` directory, not project root |
| `DUPLICATES_DETECTED` on deploy | A code extension with that name already exists (even if its transform was deleted). Deploy with a different name |
| `spark.sql.execution.pythonUDF.arrow.enabled` permission denied | Sandbox blocks UDFs/Arrow. Use `.toPandas()` → transform → `spark.createDataFrame()` pattern instead |
| `rdd.map()` fails or transform shows FAILURE | RDD operations blocked in sandbox. Use `.toPandas()` pattern instead |
| Transform status is `PROCESSING` after deploy | Wait ~30 seconds, then poll `d360_transform_get` until status is `ACTIVE` before running |

## Best Practices

### Development
1. Always scan before testing — run scan after code changes (from inside the package directory)
2. Never manually edit `config.json` — let scan regenerate it from your code
3. Always validate DLO schemas (Phase 4) after scan, before local run
4. Test locally first — use `run` command before deploying
5. Use version control — git commit after each successful test
6. Version your deployments — use semantic versioning (1.0.0, 1.1.0, etc.)
7. Deploy from code extension project folder root with `--package-dir ./payload`

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
| `function scan` | Generate config | entrypoint file |
| `script run` | Test script locally | entrypoint file, --target-org |
| `function run` | Test function locally | entrypoint file, --test-with (--target-org only if using models) |
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
