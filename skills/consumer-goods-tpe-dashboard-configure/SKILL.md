---
name: consumer-goods-tpe-dashboard-configure
description: "End-to-end headless setup of Trade Promotion Effectiveness (TPE) dashboards for a Trade Promotion Management (TPM) Cloud org, covering tenant pairing checks, permission sets, SSOT and Tableau Next enablement, C360 SDM verification, the TPM Accruals data kit install, business-period export, RTR Data Cloud export configuration, the TPM_PROMOTION_MEASURE Data Transform, TPE Analytics app install, and optional KPI dashboard customization. Use when a customer or admin wants to set up TPE dashboards, enable Trade Promotion Effectiveness, install the TPE analytics app, or set up and customize TPE dashboards with their own KPIs."
metadata:
  version: "1.0"
  minApiVersion: "67.0"
  domains: ["Consumer Goods"]
  relatedSkills:
    - "consumer-goods-rtr-datacloud-export-configure"
    - "consumer-goods-tpe-dashboard-custom-kpi-configure"
    - "consumer-goods-tpe-datakit-deploy"
  cliTools:
    - tool: ["node"]
      semver: ">=20.0.0"
    - tool: ["sf"]
      semver: ">=2.0.0"
---

# Consumer Goods TPE Dashboard Configure

Bring a TPM org from bare state to a running TPE dashboard in one guided session, driven entirely by `sf` CLI + REST/anonymous-Apex against an already-authenticated org — never a password or interactive login on the user's behalf.

Persona: a **Salesforce TPM System Admin** setting up TPE dashboards for their org.

Delegates three of its twelve steps to standalone sibling skills (own `SKILL.md`, own inputs, self-contained per this repo's skills architecture rules — no shared files):

- Step 7 → `consumer-goods-tpe-datakit-deploy`
- Step 9 → `consumer-goods-rtr-datacloud-export-configure`
- Step 12 → `consumer-goods-tpe-dashboard-custom-kpi-configure` (optional, only if the customer wants custom KPIs on the base dashboards)

Every other step runs directly in this skill.

## Inputs to collect first

Ask before starting. Do not guess.

1. **TPM System Admin username** — must already be authenticated via `sf` CLI. Verify with `node ./scripts/sf-rest.js org-status --target-org <username>` (never `sf org display --json` directly — see `references/phases-1-6.md`).
2. **Dry-run?** — offer by default. In dry-run, every read/verify/check step still runs; every write/trigger/install step is skipped and recorded as `pending — not run (dry-run)`.

Also detect the installed package namespace and version-gate the org (Consumer Goods Cloud >= 262.2 required) before Phase 1 — see "Namespace detection" in `references/phases-1-6.md`.

## Phase list

| Phase | Step | Summary | Details |
|---|---|---|---|
| Setup | — | Collect inputs, detect namespace, version-gate the org | `references/phases-1-6.md` |
| 1 | Tenant pairing | Ask user to confirm Hyperforce Processing Service pairing (not verifiable programmatically) | `references/phases-1-6.md` |
| 2 | TPM Admin permission set(s) | Ask user to confirm org-specific persona permission sets are assigned | `references/phases-1-6.md` |
| 3 | GenieAdmin / TableauEinsteinAdmin | Query, and on confirmation assign, these two permission sets | `references/phases-1-6.md` |
| 4 | SSOT package | Verify the `ssot` managed package is installed | `references/phases-1-6.md` |
| 5 | Enable Tableau Next | Ask user to confirm manual UI enablement (not verifiable programmatically) | `references/phases-1-6.md` |
| 6 | C360 SDM | Verify or trigger + poll the C360 Unified Semantic Model app install | `references/phases-1-6.md` |
| 7 | TPM Accruals Data Kit | **Delegated** to `consumer-goods-tpe-datakit-deploy` | `references/phases-7-12.md` |
| 8 | Business Period export | Anonymous-Apex export via a Hyperforce-substrate Sales Org, poll, then confirm the `tpmbusinessperiod` Data Stream sync | `references/phases-7-12.md` |
| 9 | RTR Data Cloud export | **Delegated** to `consumer-goods-rtr-datacloud-export-configure` | `references/phases-7-12.md` |
| 10 | TPM_PROMOTION_MEASURE Data Transform | Ask (credit consumption), then run and poll the Data Transform | `references/phases-7-12.md` |
| 11 | TPE Analytics App install | Trigger + poll the async app-framework install (~15-20 min) | `references/phases-7-12.md` |
| 12 | Customize KPIs (optional) | **Delegated** to `consumer-goods-tpe-dashboard-custom-kpi-configure`, only if requested | `references/phases-7-12.md` |

`references/phases-7-12.md` also documents the shared `scripts/poll-status.js` poller and the full set of hard Rules (never authenticate on the user's behalf, never hardcode a namespace or Sales Org, never claim success on anything but a terminal success status, a poll timeout is not a failure, etc.) that apply across every phase.

## Scripts

- `scripts/sf-rest.js` — authenticated REST calls; also exposes `org-status` (strips `accessToken` before printing).
- `scripts/poll-status.js` — generic async-status poller, reused by Phases 6 and 11.
- `scripts/find-failure-reason.js` — extracts the actual per-requirement failure reason for a `FailedStatus` app-framework install (Phase 11), including "DMO not available" detection.
- `scripts/render-apex.js` — renders an anonymous-Apex template with `--var` substitutions; loads `scripts/soql-escape.js` to escape substituted literals.
- `scripts/soql-escape.js` — escapes a value for safe interpolation into a single-quoted SOQL/Apex string literal.
- `scripts/run-data-transform.js` — triggers and polls a named Data Transform (Phase 10).
- `scripts/schedule-business-period-export.apex` — anonymous-Apex template for Phase 8.

## Report

At the end of a run, give the user a structured status per phase (1-12): pass / blocked / pending, with the specific blocking reason and remediation click-path where applicable. Call out anything skipped due to dry-run, a declined confirmation, or (Phase 12) the customer opting out of KPI customization.
