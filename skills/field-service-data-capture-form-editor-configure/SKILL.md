---
name: field-service-data-capture-form-editor-configure
description: "Patch an existing Data Capture Flow that's already deployed in a connected Salesforce org. Retrieves the live Flow Metadata JSON via the Tooling API, applies the user's requested change, and PATCHes it back. Use when the user names an existing flow and asks to add/remove/rename a field, change visibility, fix a bug, add visual polish, or swap a placeholder for a real component ('add a Notes field to Inventory_Transfer', 'fix the visibility rule on Work_Order_Number', 'make the parts repeater optional', 'replace the Signature placeholder with the real dcSignature component'). Do NOT use this skill to build a brand-new flow — that's fs-data-capture-form-designer followed by fs-data-capture-form-deployer."
user-invocable: false
metadata:
  version: "1.0"
  domains: ["Field Service"]
---

# Edit a Data Capture Form (in an org)

This skill patches a flow that already exists in a connected org. The source of truth is the deployed flow's `Metadata` JSON, retrieved live from the Tooling `Flow` sObject — there is no spec file, no `.flow-meta.xml`, no zip, no SFDX project. The skill retrieves the JSON, edits it in memory, and PATCHes it back.

> **Runtime contract:** every org interaction in this skill is a REST call
> dispatched through the Codey runtime (`execute_api` locally / the hosted
> Headless 360 MCP in shared surfaces). This skill has **no dependency on the
> execution environment** — no `sf` CLI, no local Python, no temp files, no
> scratch SFDX project. Auth probes, the flow retrieve, and the redeploy are
> single REST calls; the JSON patch is authored by the agent inline. Do not
> shell out.

## When this skill fires

- The user names an existing flow (`Inventory_Transfer`, `Asset_Inspection`, etc.) and asks for a change.
- The user pastes a Flow Builder URL and asks for a change.
- The user describes a deploy error or runtime bug in a deployed flow.

If the user is starting from scratch (prose, PDF, image), route to a `design-*` skill instead.

## Workflow

### 1. Verify org auth

Confirm the connected org is reachable with a cheap auth probe — dispatch `SELECT Id FROM Organization LIMIT 1` (`GET /services/data/vXX.0/query`):

- 2xx with `totalSize=1` → the session token is live; continue.
- 401/403 → the org needs re-authentication. Surface that to the user and **stop**. (The Codey runtime resolves and refreshes the connected org — this skill does not manage org aliases.)

### 2. Retrieve the live flow's Metadata JSON

The Tooling `Flow` sObject exposes the flow definition as a JSON `Metadata` field — the same shape the deployer assembles and POSTs. Retrieving is a two-call round-trip, no CLI and no file:

1. **Resolve the latest version id from the API name.** Dispatch `GET /services/data/vXX.0/tooling/query` with:

   ```sql
   SELECT Id, ActiveVersionId, LatestVersionId FROM FlowDefinition WHERE DeveloperName = '<FlowApiName>'
   ```

   Edit the **latest** version (`LatestVersionId`) so the patch builds on the newest draft, not a stale active version. If `LatestVersionId` is null, fall back to `ActiveVersionId`.

2. **Read the Metadata blob.** Dispatch `GET /services/data/vXX.0/tooling/sobjects/Flow/<versionId>` and take the `Metadata` object from the response. This JSON is the flow — screens, choices, decisions, variables, and the post-screen chain. See [../fs-data-capture-form-deployer/reference/flow-metadata-json.md](../fs-data-capture-form-deployer/reference/flow-metadata-json.md) for the shape.

If the FlowDefinition query returns zero rows, the API name is wrong or the user is pointed at the wrong org. Confirm with the user before retrying. List the candidate flows in the org if useful — dispatch `GET /services/data/vXX.0/tooling/query` with `SELECT DeveloperName FROM FlowDefinition ORDER BY DeveloperName`.

### 3. Read the retrieved Metadata JSON and the rule sheet

Before patching, **read** the retrieved `Metadata` JSON to understand the current structure, then read [fs-data-capture-reference/SKILL.md](../fs-data-capture-reference/SKILL.md) for the platform's hard constraints. The constraints are identical whether the flow is expressed as XML or JSON — a repeated XML element is a JSON array, so "grouping" becomes "the array" (see the JSON↔XML mapping rule in [../fs-data-capture-form-deployer/reference/flow-metadata-json.md](../fs-data-capture-form-deployer/reference/flow-metadata-json.md)). Pay particular attention to:

- **Element arrays**: `screens`, `choices`, `decisions`, `recordLookups`, `recordCreates`, `recordUpdates`, `loops`, `assignments`, `variables` are each a single JSON array. Add a new element by appending to the right array — never introduce a duplicate top-level key.
- **CUD ordering**: no record-lookup or screen after any CUD (recordCreate/recordUpdate/recordDelete) in the connector chain. No decision between sequential CUDs.
- **`.AllItems` vs `.AddedItems` Repeater accessor** — use what the deployed flow uses, don't change it.
- **Visibility rules**: in a `visibilityRule.conditions` entry, `leftValueReference` is the *choice* api-name, not the parent field's name.
- **Required-field behind visibility-rule** anti-pattern (see `fs-data-capture-reference` SKILL.md).
- **`isLlmTargetable`**: carried as a `{ "stringValue": "true" }`-style wrapper, not a raw JSON boolean — match whatever the retrieved flow uses.

The prohibited-patterns table at the bottom of [fs-data-capture-reference/SKILL.md](../fs-data-capture-reference/SKILL.md) is the fastest reference for "what would break this patch".

### 4. Plan the patch and confirm with the user

Before editing, tell the user:

1. **What you're going to change** — specific element, specific lines (cite `path:line` references), and what the result will look like.
2. **Whether the change requires schema reordering** — e.g. adding a new `<recordLookups>` element when none exist requires placing it in the right group. Call this out.
3. **Activation status risk** — patches deploy as a new draft version of the flow. The active version (if any) keeps running until the user activates the new draft in Flow Builder. Tell the user this.
4. **Anything you noticed that's worth flagging** — pre-existing issues, deprecated patterns, validation rules that look broken. Don't auto-fix unrelated issues; surface them.

Use `AskUserQuestion` to gate the edit. Options:
- **Apply and deploy** — proceed.
- **Show me the change first** — present the before/after of just the edited JSON subtree (the specific field, screen, or rule you're touching) inline in the chat, then ask again. No file is written; the patch lives in memory until the user approves the PATCH.
- **Cancel** — stop without deploying.

Do not proceed to step 5 without explicit approval.

### 5. Apply the patch

Edit the in-memory `Metadata` JSON object retrieved in step 2. Some specific guidelines:

- **Append to the right array.** If you're adding a screen, append to the `screens` array; a choice, to `choices`; a variable, to `variables`. Never create a second top-level key of the same name.
- **Booleans and numbers stay JSON scalars.** `"isRequired": true`, `"locationX": 0` — not strings. Typed value wrappers keep their key (`{ "stringValue": "X" }`, `{ "booleanValue": true }`, `{ "elementReference": "Foo" }`).
- **Preserve `locationX` / `locationY`** for existing elements. For new elements set both to `0` — Flow Builder re-layouts on open.
- **If the change touches a Repeater, preserve the existing `.AllItems` / `.AddedItems` accessor in any loops** — switching accessors will break runtime behavior.
- **If you add a new field, copy the shape from a sibling field** in the same flow (label inputParameter, `inputsOnNextNavToAssocScrn`, `storeOutputAutomatically`, `styleProperties`, `isRequired`). Don't compose from memory — the rules at [fs-data-capture-reference/SKILL.md](../fs-data-capture-reference/SKILL.md) show what's required per component, but the deployed flow already has working examples.
- **If the change requires a new `choices` entry**, dedupe — check whether a choice with the same `value` already exists in the `choices` array.
- **Never emit a `required` inputParameter** on a screen component — some `dc*` components (`dcName`, `dcSignature`) reject it. Carry requiredness via the field's `isRequired` key only.

### 6. Redeploy via a Tooling PATCH

Push the edited flow back as a new draft version with a single Tooling API call — dispatch `PATCH /services/data/vXX.0/tooling/sobjects/Flow/<versionId>` with body:

```json
{ "Metadata": { "...the full edited Metadata object..." } }
```

- Send the **complete** `Metadata` object, not a partial patch — Tooling replaces the whole blob.
- A 204 (No Content) is success. On a 400, the response body's `message` carries the Flow validation error — diagnose against step 7's table.
- This creates a new **draft** version of the flow. Existing active versions keep running until the user activates the new draft in Flow Builder. (To activate on save instead, set `Metadata.status: "Active"` — default is to leave it Draft.)

### 7. Report back

On success:
- State plainly what changed (e.g. "Added `Notes` ShortText field to `Header_Information` screen").
- Print the Flow Builder URL so the user can review and activate. Look up the FlowDefinition Id with a Tooling API query — dispatch `GET /services/data/vXX.0/tooling/query` with `SELECT Id, ActiveVersionId FROM FlowDefinition WHERE DeveloperName = '<FlowApiName>'` → `<instanceUrl>/builder_platform_interaction/flowBuilder.app?flowId=<id>`
- Remind the user the active version hasn't changed yet — they need to activate the new draft in Flow Builder.

On failure (the `PATCH` returned a 400 — read the error from the response body's `message`):
- Cross-reference the prohibited-patterns table at [fs-data-capture-reference/SKILL.md](../fs-data-capture-reference/SKILL.md). Common diagnoses for edits: element-array grouping violation, CUD ordering, `Element X doesn't exist` (typo'd reference), `extension not found` (wrong component name), `'Range' is not a valid value` (slider not supported), `We can't find this input attribute: 'required'` (drop the `required` inputParameter — use `isRequired`).
- If the error is about an element you didn't touch, the retrieved flow might have been in a broken state already. Re-read the current version's Metadata and compare against the active version (`GET /tooling/sobjects/Flow/<ActiveVersionId>`).
- Don't loop more than twice without showing the user.

## Out of scope

- Building a new flow — `fs-data-capture-form-designer` + `fs-data-capture-form-deployer`.
- Bulk migrations across many flows.
- Replacing a flow with a wholly different structure (delete + rebuild is cleaner).
- Editing flows that aren't `processType=DataCaptureFlow` — this skill assumes the FSL Mobile runtime.

## Related skills

- **`fs-data-capture-reference`** (library) — read this *before* every edit. Source of truth for valid flow patterns, prohibited patterns + exact deploy errors, visual polish HTML, supporting CustomObject/PermissionSet/CustomTab deploy.
- **`fs-data-capture-form-deployer`** — creates flows via the same Tooling `Flow` JSON round-trip this skill uses to patch them. Its [reference/flow-metadata-json.md](../fs-data-capture-form-deployer/reference/flow-metadata-json.md) is the authoritative `Metadata` shape for both skills.

## Files in this skill

This skill has **no executable scripts**. The auth probe, the flow retrieve (`GET /tooling/sobjects/Flow/{id}`), and the redeploy (`PATCH /tooling/sobjects/Flow/{id}`) are all single REST calls dispatched through the Codey runtime. The JSON patch is authored by the agent inline against [../fs-data-capture-form-deployer/reference/flow-metadata-json.md](../fs-data-capture-form-deployer/reference/flow-metadata-json.md).
