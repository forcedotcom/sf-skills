---
name: data360-code-extension-generate
description: "Create, develop, test, and deploy Data 360 (Data Cloud) Code Extensions with the sf CLI data-code-extension plugin and the salesforce-data-customcode Python SDK. Use this skill when creating or writing a code extension script or function (for example one that reads a DLO and writes a DLO), creating custom PySpark transformations for Data 360, editing an existing code extension payload/entrypoint.py, setting up a local code extension environment, scanning, running locally, deploying, or redeploying code extensions. Supports environment setup, init, scan, run, zip, and deploy for script and function packages."
metadata:
  version: "2.0.0"
  domains: ["Data 360", "Developer Experience"]
  cliTools:
    - tool: ["docker"]
      semver: ">=20.0.0"
    - tool: ["git"]
      semver: ">=2.0.0"
    - tool: ["java"]
      semver: ">=11.0.0"
    - tool: ["jq"]
      semver: ">=1.6.0"
    - tool: ["npm"]
      semver: ">=8.0.0"
    - tool: ["pip", "pip3"]
      semver: ">=23.0.0"
    - tool: ["python3.11", "python3"]
      semver: ">=3.11.0"
    - tool: ["sf"]
      semver: ">=2.0.0"
---

# data360-code-extension-generate

## Overview

A Data 360 code extension is customer-owned Python (PySpark) that runs inside Data 360:

| Type | Purpose | Local test |
|---|---|---|
| **script** | Batch transformation deployed as a **data transform**. Reads and writes DLOs or DMOs. | `script run` against real org data |
| **function** | Custom node for **Search Index Chunking** (`--use-in-feature SearchIndexChunking`). | `function run --test-with test.json` |

Workflow: environment check → init → discover schemas → develop → scan → run locally → deploy → run the deployed transform. The skill needs only a shell, file editing, and the ability to ask the user questions. It works with a project venv or with a single system Python 3.11 (cloud workspaces, containers).

Use it to set up a code extension environment, create a script or function package, change `payload/entrypoint.py`, scan, run locally, deploy, redeploy, or clean up.

## Agent Rules (apply to every phase)

1. **Pass `--target-org <ORG_ALIAS>` explicitly** to `run`, `deploy` and every `sf org` / `sf api` command, even when it's the CLI default. `init`, `scan` and `zip` reject it (`Nonexistent flag: --target-org`).
2. **Shell state doesn't persist.** Start every block that runs `sf data-code-extension`, `python3` or `pip` with the `<PY_ENV>` line from Phase 0b; other commands don't need it. Write `<ORG_ALIAS>`, `<PROJECT_DIR>`, `<API_VERSION>` and `<package_name>` literally. Never use `$(…)`, backticks or `eval`: some hosts (for example Code Builder) ask for approval on each one. Copy `PY_ENV` and `API_VERSION` exactly as `check_env.sh` prints them.
3. **Check before you install**, and skip anything already present.
4. **Confirm with the user before changing the org**: deploy, delete, or running a deployed transform.
5. **Hand interactive or privileged steps to the user**: `sf org login web`, enabling Code Extension, installing or starting Docker Desktop, `sudo`, installing Homebrew.
6. **Never print secrets** (access tokens, session IDs, OAuth client IDs or consumer keys).
7. **Resolve, print, proceed.** Don't ask for values the environment determines (Phase 0a). Ask only when a value is missing or ambiguous. If your shell can't prompt, ask in the conversation and write the files yourself.
8. **Schema first, then code** (Phase 2). Never write code first and ask the user to check the schema afterwards.
9. **Data 360 MCP server first for org lookups** (schemas, queries, runs, deletes). Do the MCP check (Phase 0b) once per session before the first lookup, even if Phase 0 was skipped. Fall back to `sf api` or the UI only when it isn't connected or a call fails, and say which you used. On `Session not found` (404), retry once before falling back. Details: [references/mcp-integration.md](references/mcp-integration.md).
10. **stderr:** when piping `sf … --json` into `jq`, use `2>/dev/null`, never `2>&1` (warnings break the JSON). Never redirect stderr on `scan`, `run` or `deploy`; their errors and tracebacks go there.

## Phase 0: Environment and Org Readiness

### 0a. Resolve parameters

Take what the user already gave and pass `""` for the rest; `check_env.sh` (0b) resolves it:

| Parameter | Resolution order (first match wins) |
|---|---|
| `PROJECT_DIR` | User value → `$D360_PROJECT_DIR` → `/home/codebuilder/dx-project` if it exists (Code Builder) → current folder |
| `ORG_ALIAS` | User value → `$D360_TARGET_ORG` → CLI default org if Connected → the only Connected org. Alias, or username if there's no alias |
| `<package_name>` | User value, else a snake_case name from the request (for example `employee_upper`) |

Tell the user the values in one line and continue without waiting ("Using org `…` and project `…`. Say so if you want different ones."). Stop and ask only if several orgs are Connected with no Connected default (show them), or if none is Connected (ask for the My Domain URL and hand the browser login to the user: environment-setup.md §2).

### 0b. Run the read-only check

The plugin needs **exactly Python 3.11** and uses whatever `python3` is on `PATH`. The check picks **system mode** (`python3` is 3.11 and pip isn't blocked; `<PY_ENV>` puts the user-base `bin` folder on `PATH`) or **venv mode** (`<PROJECT_DIR>/.venv`; `<PY_ENV>` activates it). An existing `.venv` always means venv mode. Details: [references/environment-setup.md](references/environment-setup.md) §3.

```bash
bash <SKILL_DIR>/scripts/check_env.sh "<PROJECT_DIR or empty>" "<ORG_ALIAS or empty>"   # optional 3rd argument: system | venv
```

It changes nothing. It prints ✅/❌ for `sf` and the plugin, Python 3.11 (after `<PY_ENV>`), pip or venv state, `salesforce-data-customcode` and `pipreqs`, Java, Docker and the org connection, then `PROJECT_DIR=`, `ORG_ALIAS=`, `MODE=`, `PY_ENV=` and `API_VERSION=`. Use the printed `PY_ENV` and `API_VERSION` from here on.

For each ❌, follow environment-setup.md in this order, then rerun the check:

1. `sf` can't run in this shell: your host's sandbox blocks it. Rerun with permission to run outside the sandbox; until then, ignore the other ❌s.
2. Venv mode: create the venv with `python3.11 -m venv .venv` (not `uv venv`), then run `bash <SKILL_DIR>/scripts/venv_hook.sh "<PROJECT_DIR>"`.
3. Install the SDK **and** `pipreqs` in one command with `python3 -m pip` (never bare `pip3`), as the check prints it. The first install downloads PySpark (about 300 MB); let it finish.

**Don't start Phase 1 until every ❌ except Docker (deploy only) is fixed.** If an install fails (for example, no network), stop and tell the user. Use only this project's Python; never borrow another project's venv. Java: JDK 17 is recommended (11 works); JDK 21 works except for `toPandas()` and pandas UDFs (environment-setup.md §Java).

**MCP check (once, here).** Look at your own tool list, including deferred tools listed by name only, for a server whose name contains `d360` or `data360` and whose tools end in `search`, `payload_examples` and `execute`. Load them if your host requires it, then print `MCP: available (<server>)` or `MCP: not connected`. Reuse this answer for the rest of the session.

### 0c. Enable Code Extension (manual, UI only)

There's no API or CLI for this. Before deploying, ask the user to turn on **Data Cloud Setup → Feature Manager → Code Extension** and confirm. The user also needs Data 360 admin permissions.

## Phase 1: Initialize

Use `script` unless the user asks for a function or mentions Search Index Chunking. Print the choice and continue.

```bash
<PY_ENV>
cd <PROJECT_DIR>
sf data-code-extension script init --package-dir <package_name>
# function: sf data-code-extension function init --package-dir <package_name> --use-in-feature SearchIndexChunking
```

The package root `<package_name>/` holds `payload/entrypoint.py`, `payload/config.json` (written by `scan`) and `requirements.txt`. Run `scan`, `run` and `deploy` from the package root (Command Reference). Full layout: [references/quick-reference.md](references/quick-reference.md).

**The stock entrypoint reads `Account_std__dll` and writes `Account_std_copy__dll`, which usually don't exist** (`table does not exist`). Replace them with real objects (Phase 2).

## Phase 2: Discover Source and Target Schemas (before writing code)

Do this **every time before you write or edit `entrypoint.py`**, including follow-ups such as "update entrypoint.py to read X and write Y". You can reuse schemas already fetched in this session.

1. Identify the source and target objects. If one isn't named, ask.
2. Get each object's fields and types. If MCP is available you must use it: `payload_examples` for `d360_dlo_get`, then `execute`, one DLO per call. Otherwise use the `sf api` fallback. Say which you used. Commands and response shapes: [references/schema-discovery.md](references/schema-discovery.md).
3. If the logic filters or joins, look at about 20 rows of input data first (MCP `d360_query_sql`, or the fallback in schema-discovery.md), especially for self-joins and root conditions (null vs `0`).
4. Print the field mapping, one line per target column: `<target column> ← <source field or expression>`. Then write the code.

**Mapping rules:**

- Take column names from the **target schema**, not from the request wording. Match on the same or a similar name first, then on what the request asks for. Never invent a column.
- **Lowercase only.** The SDK lowercases the columns it reads, and writes accept only lowercase names. Leave out target fields with capitals, such as the standard ingestion fields `KQ_id__c`, `DataSource__c`, `DataSourceObject__c`, `InternalOrganization__c` and `cdp_sys_SourceVersion__c`, and say why. If the user needs one, they must add a lowercase field to the target DLO in Data Cloud.
- **Stop before writing code** if a DLO doesn't exist, if no target column can hold a requested value, or if the user named a column the target doesn't have. If several columns fit, ask. Offer the options (add the field in Data Cloud, use another column or DLO, change the logic). Never create or change DLOs yourself.

Checklist before Phase 3:

- [ ] Mapping printed; every read and write object and every field exists
- [ ] The code will end with a `select()` of lowercase target columns only
- [ ] Join keys have the same type. A Number reads as `1.0`, so cast it before comparing with Text: `F.col("<key>").cast("long").cast("string")`
- [ ] No other data transform writes to the output DLO

## Phase 3: Develop the Transformation

Write the code from the Phase 2 mapping, using only names it returned. `read_dlo` and `read_dmo` return **PySpark** DataFrames, not pandas.

```python
from pyspark.sql.functions import col, upper

from datacustomcode.client import Client
from datacustomcode.io.writer.base import WriteMode


def main():
    client = Client()

    df = client.read_dlo("<SOURCE_DLO>")

    # One expression per target column, in the order of the Phase 2 mapping.
    result = df.select(
        col("<source_field_a>").alias("<target_column_a>"),
        upper(col("<source_field_b>")).alias("<target_column_b>"),
    )

    client.write_to_dlo("<TARGET_DLO>", result, WriteMode.OVERWRITE)


if __name__ == "__main__":
    main()
```

**SDK rules (`scan` enforces them):** read DLOs **or** DMOs, never both; DLO→DLO or DMO→DMO only; at least one read, with the object name as a string literal; the output DLO must exist and match the columns you write.

Use `WriteMode.OVERWRITE` for a full recompute. `APPEND`, `MERGE` and `MERGE_UPSERT_DELETE` are also available; `OVERWRITE_PARTITIONS` raises an error. More patterns, write modes and the optional SDK helpers (LLM text generation, Einstein predictions, bundled files): [references/quick-reference.md](references/quick-reference.md). For a function, implement `function(request: SearchIndexChunkingV1Request, runtime: Runtime) -> SearchIndexChunkingV1Response` from the generated template.

## Phase 4: Scan

```bash
<PY_ENV>
cd <PROJECT_DIR>/<package_name>
sf data-code-extension script scan --entrypoint ./payload/entrypoint.py
```

`scan` rewrites `payload/config.json` (read and write permissions) and `requirements.txt` (with `pipreqs`). Rerun it after every code change, and check that `permissions.read` and `permissions.write` list exactly the Phase 2 objects. On `PipreqsScanError`, install `pipreqs` and rerun. **Don't use `--no-requirements`** unless the user asks: the deployed transform would be missing packages.

## Phase 5: Run Locally

```bash
<PY_ENV>
cd <PROJECT_DIR>/<package_name>
sf data-code-extension script run --entrypoint ./payload/entrypoint.py --target-org <ORG_ALIAS>
# function: sf data-code-extension function run --entrypoint ./payload/entrypoint.py --test-with ./payload/tests/test.json
```

- `run` reads real org data (1,000 rows per read) and **prints** the output instead of writing it, so the target DLO stays empty. That's expected.
- An empty printed table usually means the filter or join matched nothing. Check the input data (Phase 2) before changing the code.
- On Java 21, the `Arrow optimization ... DirectByteBuffer` `UserWarning` is harmless.

## Phase 6: Deploy

**This changes the org. Confirm with the user first.** Docker must be running (`docker info`), and Code Extension must be enabled (0c).

```bash
<PY_ENV>
cd <PROJECT_DIR>/<package_name>
sf data-code-extension script deploy \
  --target-org <ORG_ALIAS> \
  --name <name> \
  --package-dir ./payload \
  --package-version 0.0.1 \
  --description "<description>" \
  [--cpu-size CPU_L|CPU_XL|CPU_2XL|CPU_4XL]
```

- `-d` is `--description`, not the directory. `--package-dir` is always `./payload`, never the package root. `--cpu-size` defaults to `CPU_2XL`. `function deploy` takes the same flags.
- **Redeploy:** a second `deploy` with the same `--name` fails with `DeploymentExists`, even with a new `--package-version`. Delete the **data transform**, then the **code extension** (UI or MCP, confirming each delete), then deploy again.
- An output DLO can belong to only one data transform (`Output objects ... are already in use`).

## Phase 7: Run the Deployed Transform and Verify

Writing to the DLO happens only when the deployed transform runs. **Confirm with the user first.** Start it from Data Cloud → **Data Transforms** → `<name>` → **Run Now** (runs take about 10 minutes), or with the MCP transform tools. Then check the output DLO in the UI or with an MCP query.

After every run, successful or not, read the run's messages and tracebacks in the system DLO **`DataCustomCodeLogs__dll`**: filter on `DataCustomCodeName__c = '<name>'` and take the latest `ExecutionId__c`. The query and how to read the rows: [references/run-logs.md](references/run-logs.md). To trace a deployed run, add `print()` or `logging` calls and redeploy.

**Cleanup:** delete the data transform, then the code extension, confirming each delete with the user.

## Error Handling (most common)

| Error | Fix |
|---|---|
| `PythonVersionMismatch` / `PYTHON_VERSION_MISMATCH` | Start the block with `<PY_ENV>`. Venv mode: rerun `scripts/venv_hook.sh <PROJECT_DIR>` |
| `PipreqsScanError` | Install `pipreqs` with `python3 -m pip`, start the block with `<PY_ENV>`, and rerun `scan` |
| `table does not exist` | Wrong DLO name (for example the stock `Account_std__dll`). See Phase 2 |
| `ValueError: The following columns are not present in the DLO` | The listed columns have capital letters. Apply the lowercase rule (Phase 2) |
| `DeploymentExists` | Delete the transform, then the code extension, then redeploy |
| Deployed run fails or writes nothing | Read `DataCustomCodeLogs__dll` (Phase 7) |

Everything else: [references/troubleshooting.md](references/troubleshooting.md).

## Command Reference

| Command | Run from | Required flags | Optional flags |
|---|---|---|---|
| `script init` / `function init` | Parent folder | `-p/--package-dir <package_name>` | function: `-u/--use-in-feature SearchIndexChunking` |
| `script scan` / `function scan` | Package root | (`-e/--entrypoint ./payload/entrypoint.py`) | `-d/--dry-run`, `-n/--no-requirements`, `--config-file` |
| `script run` | Package root | `-e/--entrypoint`, `-o/--target-org` | `--config-file`, `--dependencies` |
| `function run` | Package root | `-e/--entrypoint`, `-t/--test-with` | `--target-org`, `--config-file`, `--dependencies` |
| `script zip` / `function zip` | Package root | `-p/--package-dir` | `-n/--network` |
| `script deploy` / `function deploy` | Package root | `-n/--name`, `--package-version`, `-d/--description`, `-p/--package-dir ./payload`, `-o/--target-org` | `--cpu-size`, `--network` (Jupyter packages only) |

Verified against plugin `data-code-extension` 1.4.1 and SDK `salesforce-data-customcode` 6.1.0. If the plugin version differs, check with `sf data-code-extension <type> <command> --help`.

## Resources

- SF CLI plugin: https://github.com/salesforcecli/plugin-data-code-extension
- Python SDK: https://github.com/forcedotcom/datacloud-customcode-python-sdk (PyPI: `salesforce-data-customcode`)
- Hosted MCP servers (optional setup): https://developer.salesforce.com/docs/platform/hosted-mcp-servers/overview
