---
name: service-itsm-agentic-setup-cmdb-coordinate
description: "Orchestrator skill for enabling CMDB (Configuration Management Database) end-to-end in Service Cloud ITSM against a production or sandbox org. Use when the user asks to set up CMDB, enable Configuration Management Database, configure the ITSM CMDB, onboard CMDB from scratch, wants a guided walkthrough of CMDB enablement, or asks what CMDB setup steps are available. Triggers on: set up CMDB, enable CMDB, configure CMDB, CMDB onboarding, Configuration Management Database setup, ITSM CMDB walkthrough. DO NOT TRIGGER when: the user asks about a specific CMDB sub-step directly (e.g. only installing a bundle, only assigning permission sets), CMDB record CRUD (creating CIs, relationships), Discovery/Service Graph Connector configuration, or general ITSM queries without CMDB setup intent."
metadata:
  version: "1.0"
  domains: ["Service"]
  relatedSkills:
    - "service-itsm-agentic-setup-cmdb-access-assign"
    - "service-itsm-agentic-setup-cmdb-bundle-deploy"
    - "service-itsm-agentic-setup-cmdb-configure"
    - "service-itsm-agentic-setup-cmdb-discovery-configure"
  accessCheck:
    - type: "orgPerm"
      value: "ITSrvcsCnfgMgmnt"
allowed-tools: AskUserQuestion
---

# CMDB Setup Orchestrator (Service Cloud ITSM)

Guide the user through enabling the **Configuration Management Database (CMDB)** in Service Cloud
ITSM by presenting the ordered setup layers, delegating each to a specialized child skill, and
tracking progress until CMDB is usable end-to-end. Each child skill runs through the
**Salesforce-hosted Headless-360 MCP server**, so the same flow works against **production** and
sandbox — the org is bound to the current MCP session, with no per-user MCP install.

## Goal

Act as the top-level coordinator for CMDB enablement. Present the user with the ordered layers,
invoke the appropriate child skill for each, verify the layer succeeded before moving on, and after
each layer completes return to the menu with updated progress until CMDB is ready or the user stops.

## The CMDB prerequisite stack (why order matters)

CMDB is gated by a 4-layer stack. Every CMDB Connect API checks `orgHasCMDBEnabled`, which is
`orgHasCMDBPermission && OrgPreferences.CMDBEnabled`. Failing the gate returns
`403 FUNCTIONALITY_NOT_ENABLED`. The layers must be satisfied **in order**:

```text
Layer 0  Org SKU / license      Org perm ITSrvcsCnfgMgmnt must already be granted (edition/
                                license/template). NOT settable by any API — verify only.
Layer 1  Tenant provisioning    ITOM tenant must reach status PROVISIONED (async).
Layer 2  Feature enable         Enable feature service-cloud-itsm-cmdb-integration. This is
                                what internally sets CMDBEnabled and lifts the 403 gate.
Layer 3  User access            Assign the PSL + CMDB permission sets to the user(s).
Layer 4  Content bundles        Install the CMDB Foundation (base) content bundle.
Layer 5  Asset Discovery        Enable feature service-cloud-itsm-discovery-integration and grant
                                Discovery page access (IT Service Discovery Manager permission set).
                                Runs last — depends on the base CMDB feature and earlier layers.
```

Layer 0 is a hard prerequisite: if the org was not born with the CMDB SKU, **no API can grant it**
and setup cannot proceed. The orchestrator surfaces this clearly and stops.

## Behavior

### 1. Extract context from conversation

Before presenting options, scan chat history for:

- The target org (alias/username) — required by every child skill
- Which layers are already done (skip or mark as done)
- Any constraints the user mentioned (e.g. "just enable it, we'll assign users later")

Derive layer status from the **most recent** layer activity in the transcript. On a long or **resumed** conversation (e.g. a headless session continued later), do not treat an earlier-highlighted layer as still current — re-derive which layer is active from the latest child-skill result, and if it is ambiguous, re-confirm with the user before re-presenting the menu.

### 2. Confirm the target org

CMDB enablement performs **writes against a real org** (tenant provisioning, feature enable,
permission-set assignment, bundle install). Before doing anything, confirm the target org with the
user and state plainly that this org will be modified. Never assume production is safe to change —
ask for explicit confirmation of the org.

### 3. Present the CMDB setup menu

Show the ordered layers and their status:

```text
CMDB Setup (via service-itsm-agentic-setup-cmdb-coordinate)

Target org: <org>   (all steps below run against this org)

CMDB is enabled in ordered layers. Each must succeed before the next:
```

| #   | Layer                    | What it does                                                 | Status  |
| --- | ------------------------ | ------------------------------------------------------------ | ------- |
| 0   | License check            | Confirm this org is licensed for CMDB (set by edition/license — can't be turned on) | Pending |
| 1–2 | Provision & enable CMDB  | Set up the CMDB service, then turn on the CMDB feature so it's available to use | Pending |
| 3   | Assign user access       | Grant CMDB access to the chosen users                        | Pending |
| 4   | Install content bundle   | Install the CMDB Foundation (base) content                   | Pending |
| 5   | Enable Asset Discovery   | Turn on asset discovery and grant Discovery page access (final step — needs the steps above done first) | Pending |

```text
I recommend running these in order. Where would you like to start (or shall I run 1 → 5)?
```

Render one row per layer with a single-line cell — do not split a layer across stacked rows or wrap
a cell onto a second line. Present the combined provision-and-enable step as the single row `1–2`.
Only show layers that have a corresponding, working child skill. Do NOT show placeholder layers.

### 4. Delegate to child skills

| Layer | Child skill |
|-------|-------------|
| 0 (org SKU check) + 1 (tenant provisioning) + 2 (feature enable) | `service-itsm-agentic-setup-cmdb-configure` |
| 3 (user access) | `service-itsm-agentic-setup-cmdb-access-assign` |
| 4 (content bundle) | `service-itsm-agentic-setup-cmdb-bundle-deploy` |
| 5 (asset discovery) | `service-itsm-agentic-setup-cmdb-discovery-configure` |

`service-itsm-agentic-setup-cmdb-configure` owns the Layer 0 gate. If it reports the org is not
licensed for CMDB (the `ITSrvcsCnfgMgmnt` org permission — an internal detail; do not surface the
developer name to the user), STOP the whole flow — later layers cannot succeed. Relay its
plain-language message and do not attempt Layers 3 or 4.

### 5. After each layer completes

1. **Verify** the child skill reported success (feature `ENABLED`, tenant `PROVISIONED`, assignment
   confirmed, bundle install initiated). If it failed, stop and surface the failure — do not advance.
2. **Update status** — mark the completed layer as "Done".
3. **Suggest the next step** in dependency order.
4. **Re-present the menu** with updated status.

### 6. Completion summary

When all available layers are done (or the user stops), present a final summary:

```text
CMDB Setup — Complete (via service-itsm-agentic-setup-cmdb-coordinate)

Target org: <org>
```

| #   | Layer                    | Status |
| --- | ------------------------ | ------ |
| 0   | License check            | Done   |
| 1–2 | Provision & enable CMDB  | Done   |
| 3   | User access              | Done   |
| 4   | Content bundle (base)    | Done   |
| 5   | Asset Discovery + access | Done   |

```text
CMDB is enabled and ready. Users with the assigned permission sets can now work with
Configuration Items. Next, you can model CIs, identification rules, and relationships.
```

---

## Feature dependencies & recommended order

```text
0. Org SKU check          (prerequisite — hard stop if missing; no API can grant it)
1. Tenant provisioning    (async infra; must reach PROVISIONED)
2. CMDB feature enable     (sets CMDBEnabled; lifts the 403 gate — bundles/CI APIs stay 403 until this)
3. User access             (PSL + permission sets; without these users can't see CMDB)
4. Content bundle          (CMDB Foundation base; requires Layer 2 — bundle APIs 403 until enabled)
5. Asset Discovery         (enable service-cloud-itsm-discovery-integration and grant Discovery page
                           access via the IT Service Discovery Manager permission set; final layer —
                           requires the base CMDB feature and earlier layers; blocked until done)
```

Layers 1 and 2 are handled together by `service-itsm-agentic-setup-cmdb-configure` because Layer 2
cannot succeed until Layer 1 reaches `PROVISIONED`. Present them as one step.

---

## Rules

- ALWAYS show "(via service-itsm-agentic-setup-cmdb-coordinate)" in the header so the user knows this skill is active
- ALWAYS confirm the target org before any layer runs, and state that the org will be modified
- ALWAYS present the menu before acting — do not assume which layer the user wants
- NEVER run a layer without the user selecting it (or confirming "run all")
- NEVER advance past a failed layer — stop, explain in plain language, and offer next steps
- If Layer 0 fails (org lacks `ITSrvcsCnfgMgmnt`), STOP entirely and explain that this is a
  license/edition prerequisite that no API can grant
- If a child skill reports a prerequisite gap or a failure, relay it to the user in friendly,
  actionable terms — do not bury the error
- Track progress across the conversation — do not re-present completed layers as "Pending". Re-derive the current layer from the latest child-skill activity, not from a previously rendered highlight; on a resumed or long conversation, do not assume the last-highlighted layer is still current — if ambiguous, re-confirm with the user
- Do NOT expose internal technical jargon in user-facing output. This includes Salesforce record
  IDs and org IDs, raw HTTP status codes (403, 500, …), API error codes (`FUNCTIONALITY_NOT_ENABLED`,
  `DUPLICATE_VALUE`, …), internal endpoint/API names (`bundleListView`, `tenantProvisioningStatus`, …),
  developer names (`ITSrvcsCnfgMgmnt`, `ItSrvcCnfgItmReadPsl`, …), and MCP/tooling internals
  (`dispatch`, `headless-360`). Translate everything to plain, human-readable language — e.g.
  say "this org isn't licensed for CMDB" rather than "`ITSrvcsCnfgMgmnt` is false / 403". Child-skill
  names shown as next-step pointers are fine. Keep all such technical detail in your own reasoning,
  not on screen.

---

## Adding new layers

When new CMDB child skills are created (e.g. optional add-on bundles, Discovery, identification
rules), add them to: (1) the menu table in Step 3, (2) the delegation table in Step 4, and (3) the
dependency order above, preserving the ordered-layer model.
