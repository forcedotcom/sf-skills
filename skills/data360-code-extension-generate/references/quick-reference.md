# Data 360 Code Extension: Quick Reference

Every block assumes it starts with the `<PY_ENV>` line from SKILL.md Phase 0b, in the same shell command:

- system mode: `export PATH="<user-base>/bin:$PATH"`, with the literal folder printed by `check_env.sh` (for example `/home/codebuilder/.local/bin`)
- venv mode: `source <PROJECT_DIR>/.venv/bin/activate`

Replace `<ORG_ALIAS>` and `<PROJECT_DIR>` with the real values.

## Commands

### Initialize
```bash
sf data-code-extension script init --package-dir my_transform
sf data-code-extension function init --package-dir my_chunker --use-in-feature SearchIndexChunking
```

### Scan (run from the package root)
```bash
sf data-code-extension script scan --entrypoint ./payload/entrypoint.py
sf data-code-extension script scan --entrypoint ./payload/entrypoint.py --dry-run           # preview only
sf data-code-extension script scan --entrypoint ./payload/entrypoint.py --no-requirements   # keep requirements.txt (only when asked; never to get past PipreqsScanError)
sf data-code-extension script scan --entrypoint ./payload/entrypoint.py --config-file ./alt-config.json
```

### Run locally
```bash
sf data-code-extension script run --entrypoint ./payload/entrypoint.py --target-org <ORG_ALIAS>
sf data-code-extension script run --entrypoint ./payload/entrypoint.py --target-org <ORG_ALIAS> --config-file ./alt-config.json

sf data-code-extension function run --entrypoint ./payload/entrypoint.py --test-with ./payload/tests/test.json
```

### Deploy (Docker running, Code Extension enabled, user confirmed)
```bash
sf data-code-extension script deploy \
  --target-org <ORG_ALIAS> \
  --name my_transform \
  --package-dir ./payload \
  --package-version 0.0.1 \
  --description "My transformation" \
  --cpu-size CPU_2XL
```

`function deploy` takes the same flags. `script zip --package-dir ./payload` only builds the archive; `deploy` packages it for you.

## Package Layout

```text
<package_name>/             # package root: run scan, run, deploy from here
├── payload/                # what --package-dir points to on deploy
│   ├── entrypoint.py       # your transformation
│   └── config.json         # generated and updated by scan
├── examples/               # SDK sample (employee_hierarchy)
├── requirements.txt        # updated by scan
├── requirements-dev.txt
├── Dockerfile, Dockerfile.dependencies, build_native_dependencies.sh
├── account.ipynb, jupyterlab.sh
└── README.md
```

A function package has `payload/entrypoint.py`, `payload/utility.py`, `payload/config.json`, plus `example/` folders with `tests/test.json` inputs.

## Workflows

### New project
```bash
<PY_ENV>
cd <PROJECT_DIR>
sf data-code-extension script init --package-dir my_transform
cd my_transform
# edit payload/entrypoint.py with real DLO names (the stock Account_std__dll usually doesn't exist)
sf data-code-extension script scan --entrypoint ./payload/entrypoint.py
sf data-code-extension script run  --entrypoint ./payload/entrypoint.py --target-org <ORG_ALIAS>
# confirm with the user, then deploy (see above)
```

### Change code that's already deployed
A second `deploy` with the same `--name` fails with `DeploymentExists`, even with a new `--package-version`.

1. Edit, `scan`, and `run` locally.
2. With the user's confirmation, delete the **data transform**, then the **code extension**. Use the UI or the Data 360 MCP delete tools.
3. Deploy again. You can keep the same name.

## PySpark Patterns

These patterns use made-up DLO and field names to show PySpark shapes. Never copy the names: use the source and target fields fetched in SKILL.md Phase 2.

`read_dlo` / `read_dmo` return **PySpark** DataFrames.

```python
from pyspark.sql.functions import col, concat_ws, upper, when, avg

from datacustomcode.client import Client
from datacustomcode.io.writer.base import WriteMode

client = Client()
```

### Select, rename, computed column
```python
df = client.read_dlo("Employee__dll")
out = (
    df.select("id__c", "first_name__c", "last_name__c", "position__c")
      .withColumn("full_name__c", concat_ws(" ", col("first_name__c"), col("last_name__c")))
      .withColumn("position_upper__c", upper(col("position__c")))
)
client.write_to_dlo("Employee_Enriched__dll", out, WriteMode.OVERWRITE)
```

### Filter and conditional
```python
active = df.filter(col("status__c") == "Active")
graded = active.withColumn(
    "grade__c", when(col("position__c").contains("VP"), "Senior").otherwise("Junior")
)
```

### Join two DLOs
```python
employees = client.read_dlo("Employee__dll")
departments = client.read_dlo("Department__dll").select(
    col("id__c").alias("dept_id"), col("name__c").alias("department_name__c")
)
merged = employees.join(departments, employees["dept_id__c"] == col("dept_id"), "left").drop("dept_id")
client.write_to_dlo("Employee_With_Dept__dll", merged, WriteMode.OVERWRITE)
```

### Aggregate
```python
summary = df.groupBy("department__c").agg(avg("salary__c").alias("avg_salary__c"))
```

### DMO to DMO
```python
ind = client.read_dmo("ssot__Individual__dlm")
client.write_to_dmo("Custom_Individual_Out__dlm", ind.select("ssot__Id__c", "ssot__FirstName__c"), WriteMode.MERGE)
```

### Layer rules (enforced by `scan`)
- Read DLOs **or** DMOs in one entry point, never both.
- DLO→DLO or DMO→DMO only. **Never read DLOs and write a DMO**, or the reverse.
- Pass object names as string literals so `scan` can detect them.

## Write Modes (`WriteMode`)

| Mode | Use |
|---|---|
| `APPEND` | Add rows |
| `OVERWRITE` | Replace all rows (full recompute) |
| `MERGE` | Merge on the primary key |
| `MERGE_UPSERT_DELETE` | Row-level `UPSERT`/`DELETE` via a `_merge_record_type` column |
| `OVERWRITE_PARTITIONS` | Deprecated, raises an error |

## Optional SDK Helpers

See the template docstring in `payload/entrypoint.py`.

- `llm_gateway_generate_text_col(...)` generates column values with a configured model.
- `einstein_predict_col(...)` scores rows with an Einstein Studio model.
- `client.find_file_path("name")` resolves files bundled under `payload/files/`.

## `--cpu-size`

| Size | Guidance |
|---|---|
| `CPU_L` | Small datasets (< 1M records) |
| `CPU_XL` | Medium (1M–5M) |
| `CPU_2XL` | Large (5M–10M), **default** |
| `CPU_4XL` | Very large (> 10M) |

Higher sizes may use more quota or credits.

## `config.json` (generated by scan)

```json
{
  "sdkVersion": "6.1.0",
  "entryPoint": "entrypoint.py",
  "dataspace": "default",
  "permissions": {
    "read":  { "dlo": ["Employee__dll", "Department__dll"] },
    "write": { "dlo": ["Employee_With_Dept__dll"] }
  }
}
```

Don't hand-edit `permissions`; rerun `scan`. Edit `dataspace` only if you use a non-default data space.

## Deployment Checklist

- [ ] `check_env.sh` all ✅ (Docker running)
- [ ] **Code Extension** enabled in Data Cloud Setup → Feature Manager (manual)
- [ ] Source and target schemas fetched and field mapping printed before the code was written (Phase 2)
- [ ] `scan` rerun after the last code change
- [ ] Local `run` succeeds
- [ ] Output DLO not used by another data transform
- [ ] No existing code extension with the same `--name` (or it was deleted)
- [ ] User confirmed the deploy
