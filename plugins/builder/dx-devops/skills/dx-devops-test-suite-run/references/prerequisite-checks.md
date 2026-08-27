# Prerequisite Checks — Shared DevOps Center Gate

Shared environment gate for every DevOps Center testing skill. Run these checks **before** any query or system call. On any failure, surface the plain-language message and stop until the user resolves it — never proceed to a write with an unverified environment.

> **API version:** All DevOps testing system calls target Salesforce API **v67.0** (minimum required).

**Important:** All DevOps Center data (pipelines, stages, test suites, executions) lives in the Salesforce org — NOT in the local repository. Never search the filesystem for pipeline configuration. Always query the org using `sf data query` or `sf api request rest`.

**Object model — use the STANDARD objects, never the `sf_devops__` managed package:** DevOps Center testing data lives in standard platform objects — `DevopsPipeline`, `DevopsPipelineStage`, `DevopsPipelineStageTrigger`, `DevopsTestSuite`, `DevopsTestSuiteStage`, `DevopsTestSuiteExecution`, `DevopsProject`, `WorkItem`. Do **NOT** query the legacy managed-package objects (`sf_devops__Pipeline__c`, `sf_devops__Pipeline_Stage__c`, etc.) and do **NOT** gate on a `PackageLicense` / namespace check for `sf_devops`. "DevOps Center installed" is determined **solely** by whether `DevopsPipeline` is queryable and returns records (Prerequisite 4) — never by the presence of the `sf_devops__` namespace. If a `sf_devops__*` object is missing, that is expected and is NOT evidence that DevOps Center is uninstalled.

## How skills use this

Run Prerequisites 1–4 in order. Prerequisite 5 (stage) is run **only** when the operation targets a specific pipeline stage (configuring a gate, running/retriggering a suite, mapping a suite). Carry forward the resolved `doce-org-alias`, `pipelineId`, and (when applicable) `stageId`.

Resolve the **DevOps Center org alias** without asking the user unless genuinely ambiguous:
1. If the user named an org alias in their message, use it.
2. Otherwise, use the default org (`sf org display --json`, no `--target-org`).
3. Only if the default org has no `DevopsPipeline` records (Prereq 4 fails), ask: "Which org alias is your DevOps Center org?"

---

## Prerequisite 1 — Salesforce org: active login

```bash
sf org list --json
```

Look for at least one entry in `result.nonScratchOrgs`, `result.scratchOrgs`, or `result.sandboxes` with `"connectedStatus": "Connected"`.

- **Pass:** at least one org is Connected
- **Fail:** no orgs listed, or all show a non-connected status

**On fail:** "No authenticated Salesforce org found. Run `sf org login web --alias <your-alias>` in your terminal, then come back."

---

## Prerequisite 2 — Agentforce DX plugin installed

```bash
sf plugins --json
```

Look for a plugin entry whose `name` contains `plugin-agent`, `agentforce`, or `einstein` (case-insensitive).

- **Pass:** plugin found
- **Fail:** no matching entry

**On fail:** "The Agentforce DX Plugin is not installed. Run `sf plugins install @salesforce/plugin-agent`, then restart the IDE and try again."

---

## Prerequisite 3 — DevOps Center org authenticated

```bash
sf org display --target-org <doce-org-alias> --json
```

Check that `"connectedStatus"` is `"Connected"`.

- **Pass:** Connected
- **Fail:** expired session or error

**On fail:** "Your DevOps Center org session has expired. Run `sf org login web --alias <doce-org-alias>` to re-authenticate."

---

## Prerequisite 4 — Pipeline identified

```bash
sf data query \
  --query "SELECT Id, Name, CreatedDate FROM DevopsPipeline ORDER BY Name ASC" \
  --target-org <doce-org-alias> \
  --json
```

- **Pass (exactly one):** use it automatically — do NOT ask.
- **Pass (multiple):** if the user already named a pipeline, match by name. Otherwise display a numbered list and ask:
  ```text
  Found <N> pipelines:
  1. <Name>
  2. <Name>
  Which pipeline would you like to work with?
  ```
- **Fail (no records):** "No DevOps Center pipeline found. Create a project and pipeline in DevOps Center before using the DevOps Testing Skills."
- **Fail (unsupported object):** "DevOps Center does not appear to be installed on `<doce-org-alias>`. Check that you're pointing at the correct org."

---

## Prerequisite 5 — Pipeline stage identified (conditional)

Run **only** when the operation targets a specific stage (e.g. configuring a quality gate).

If the user's message already names a stage (e.g. "Integration", "Staging", "Production"), use that name directly — do NOT ask again. Look up its Id:

```bash
sf data query \
  --query "SELECT Id, Name FROM DevopsPipelineStage WHERE DevopsPipelineId = '<pipelineId>' AND Name = '<stageName>'" \
  --target-org <doce-org-alias> --json
```

Only if no stage is mentioned, fetch the full list and ask which one:

```bash
sf data query \
  --query "SELECT Id, Name FROM DevopsPipelineStage WHERE DevopsPipelineId = '<pipelineId>' ORDER BY Name ASC" \
  --target-org <doce-org-alias> --json
```

Then ask: "Which pipeline stage are we working with?" — do NOT ask for an org alias; stages are resolved by name from the pipeline.

- **Pass:** stage Id and Name confirmed
- **Deferred:** not required until the operation needs it
