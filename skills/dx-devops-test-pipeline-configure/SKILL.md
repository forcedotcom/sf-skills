---
name: dx-devops-test-pipeline-configure
description: "Configures DevOps Center pipeline testing infrastructure: enables a test provider so its suites become available, re-syncs a configured provider to pull in new suites, or creates a quality gate with rules on a stage. Routes by intent across three modes after running shared prerequisite checks and an explicit confirmation gate. Use this skill when a user wants to set up, configure, enable, sync, or refresh a test provider, or set/configure a quality gate or coverage threshold on a DevOps Center pipeline stage. TRIGGER when: the user wants to configure/enable/add/set up a test provider, re-sync or refresh a provider's suite list, pull in new suites, or set/configure a quality gate, coverage threshold, or testing benchmark on a stage. DO NOT TRIGGER when: assigning existing suites to a stage (use dx-devops-test-suite-assignments-configure), running or retriggering a suite (use dx-devops-test-suite-run), or non-DevOps-Center work."
metadata:
  cliTools:
    - tool: ["sf"]
      semver: ">=2.67.0"
  relatedSkills:
    - "dx-devops-test-failures-analyze"
    - "dx-devops-test-suite-assignments-configure"
    - "dx-devops-test-suite-run"
  version: "1.0"
  domains: ["Developer Experience"]
  minApiVersion: "67.0"
---

# Configure DevOps Center Pipeline Testing Infrastructure

Sets up and configures a DevOps Center pipeline's testing infrastructure. This skill handles three closely related "configure your pipeline" operations that share the same org context, prerequisites, and entity scope (the pipeline level). Pick the mode that matches the user's intent.

> **API version:** All DevOps testing system calls target Salesforce API **v67.0** (minimum required).

**Important:** All DevOps Center data (pipelines, stages, providers, suites, gates) lives in the Salesforce org — NOT the local repo. Never search the filesystem for pipeline configuration. Always query the org with `sf data query` or `sf api request rest`.

---

## Step 1 — Run prerequisites first (always)

Before any query or system call, run the prerequisite checks in `references/prerequisite-checks.md`. On any failure, surface the plain-language message and stop — never write to an unverified environment.

- **Modes A & B (provider configure/sync):** run Prerequisites 1–4 (org login, Agentforce DX plugin, DevOps Center org auth, pipeline identified). Prerequisite 5 (stage) is **not** required — providers are configured at the pipeline level.
- **Mode C (quality gate):** run Prerequisites 1–4 **and** Prerequisite 5 (stage). Prereq 5 gives the `DevopsPipelineStage` only — the target `DevopsTestSuiteStage` record Id is resolved separately in Mode C's Step 0 (trigger → suite-stage row).

Carry forward the resolved `doce-org-alias`, `pipelineId`, and (Mode C) `stageId` / `testSuiteStageId`.

---

## Step 2 — Select the mode

| If the user wants to… | Mode | Follow |
|---|---|---|
| Enable / set up / add a provider that is **not yet configured** | **A — Configure a test provider** | `references/configuring-test-provider.md` |
| Re-sync / refresh an **already-configured** provider to pull in new suites | **B — Sync a configured provider** | `references/syncing-test-providers.md` |
| Set / configure a quality gate, coverage threshold, or testing benchmark on a stage | **C — Configure a quality gate** | `references/configuring-quality-gate.md` |

**Disambiguating A vs B (the critical decision):** First fetch the pipeline's providers (`GET .../testProviders?status=all`) — both modes start there. Then:

- Provider is **Available** (not configured) → **Mode A** (configure).
- Provider is **Configured** but suites are stale/missing → **Mode B** (sync).
- Provider is **Configured** and the user can't see suites *when assigning to a stage* → this is a **stage-assignment gap, not a configuration gap**. Redirect to `dx-devops-test-suite-assignments-configure`.

⚠ **Never POST to the configure endpoint for an already-configured provider** — it creates duplicate `DevopsPipelineTestProvider` records. See `references/gotchas.md`.

---

## Step 3 — Confirmation gate (required in every mode)

Every mode mutates org state and **must** show a confirmation gate before any write. Each mode's reference file contains its exact gate wording (Mode C additionally requires a mandatory impact preview before the gate). Do not call any write API until the user gives an affirmative response. If the user declines, stop without writing.

---

## Step 4 — Execute and report

Follow the chosen reference file for the exact API calls, success messages, and error handling:

- `references/configuring-test-provider.md` — Mode A
- `references/syncing-test-providers.md` — Mode B
- `references/configuring-quality-gate.md` — Mode C
- `references/error-handling.md` — consolidated status-code → plain-language tables for all modes
- `references/gotchas.md` — duplicate-provider trap, API-name differences, trigger-type rules

Never expose raw API errors, stack traces, or JSON payloads to the user — always translate to plain language.

---

## Related skills

- **`dx-devops-test-suite-assignments-configure`** — after configuring/syncing a provider, assign or map its suites to a stage; also recommends which suites to run for a commit.
- **`dx-devops-test-suite-run`** — run a suite, or retrigger a quality gate after fixes meet the threshold.
- **`dx-devops-test-failures-analyze`** — explain failures from a run and optionally create a fix work item.
