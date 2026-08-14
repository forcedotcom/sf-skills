---
name: service-itsm-incident-priority-configure
description: "Configures the Incident Priority Matrix for Salesforce ITSM through the sf CLI — enabling or disabling the matrix, shaping the Impact x Urgency grid that derives Priority on Incident records, toggling the manual-override preference, and reading or setting the default fallback priority. Reads every value before writing, is idempotent, and requires explicit user confirmation before any mutation. Use when the user wants to view, enable, disable, set up, seed, add to, change, or remove priority matrix configuration for Incident records, change the default incident priority, or asks about incident priority setup, impact/urgency mapping, override, or the ITSM incident priority matrix. DO NOT TRIGGER for Problem or ChangeRequest priority matrices, Case priority fields, standard Priority picklists outside ITSM, SLA or milestone configuration, or enabling Incident Management itself (use the service-itsm-incident-mgmt-configure skill)."
metadata:
  version: "1.0"
  minApiVersion: "67.0"
  cliTools:
    - tool: ["sf"]
      semver: ">=2.60.0"
  accessCheck:
    - type: "userPerm"
      value: "CustomizeApplication"
    - type: "orgPref"
      value: "ITSMIncidentMgmtEnabled"
allowed-tools: |
  Read AskUserQuestion Bash
---

# Configuring the Incident Priority Matrix (sf CLI)

Configures the **Incident Priority Matrix** for Salesforce ITSM — the grid that derives an Incident's **Priority** from its **Impact** and **Urgency**. Covers viewing the matrix, enabling / disabling it, adding / changing / removing / seeding cells, toggling the manual-override preference, and reading / setting the default (fallback) priority.

Every read and write dispatches through the **`sf` CLI** — no MCP dispatcher, no `/headless/invoke/*` route, no Aura controller. This means the skill works on any org with the Incident Management license enabled, without the `api.agentic.access.enableHeadless360McpServer` gate.

Writes are **idempotent** (skipped when the current state already matches the target), the skill always **reads before it writes**, and an explicit **confirm-to-write** checkpoint is required before any mutation.

## Scope

- **In scope** (Incident only): view the matrix; enable / disable it; add, change, remove, or
  seed matrix cells; toggle manual override; read / set the default (fallback) priority.
- **Out of scope**: `Problem` and `ChangeRequest` matrices; non-ITSM Priority pickers;
  SLA / milestone / entitlement setup; enabling Incident Management itself. If the user
  asks about `Problem` or `ChangeRequest`, stop and say so.

---

## Preconditions

1. `sf` CLI ≥ 2.60 (verify with `sf --version`).
2. The target org is authenticated with `sf` — one of `sf org list` should show it as `Connected`.
3. Incident Management is enabled on the org (`ITSMIncidentMgmtEnabled` org pref). Confirmed at
   preflight time via the Incident `describe`; if it 404s, direct the user to enable Incident
   Management first (use the `service-itsm-incident-mgmt-configure` skill).
4. The calling user has `CustomizeApplication` (View Setup + Setup Admin).

If any precondition is unmet, the CLI surfaces the raw error verbatim — **do not fabricate state,
surface the raw error and stop.**

---

## Routes at a glance

Every route is called through `sf` — no `curl`, no MCP server. Full method / path / body / response
details, the picklist extraction recipe, and gotchas live in `references/sf-cli-invocation.md`.

| Concern | Transport | HTTP status |
|---------|-----------|-------------|
| Matrix enable flag (read/write) | `sf api request rest` on `/services/data/v67.0/setup/org/preferences/IncPriorityMatrixEnabled` | 200 |
| Manual override (read/write) | `sf api request rest` on `/services/data/v67.0/setup/org/preferences/IncPriorityOverrideEnabled` | 200 |
| Matrix rows (read) | `sf data query --use-tooling-api` on `ServiceOpPriorityConfig` | 200 |
| Matrix rows (add) | `sf api request rest` POST on `/services/data/v67.0/tooling/sobjects/ServiceOpPriorityConfig` | 201 |
| Matrix rows (change) | `sf api request rest` PATCH on `/services/data/v67.0/tooling/sobjects/ServiceOpPriorityConfig/<Id>` | 204 |
| Matrix rows (remove) | `sf data delete record --use-tooling-api` on `ServiceOpPriorityConfig` | 200 |
| Default fallback priority (read) | `sf api request rest` GET on `/services/data/v67.0/tooling/query/?q=...StandardValueSet...` | 200 |
| Default fallback priority (write) | `sf project retrieve start` + edit + `sf project deploy start` on `StandardValueSet:IncidentPriority` | deploy Succeeded |
| Picklist values (Incident) | `sf api request rest` GET on `/services/data/v67.0/sobjects/Incident/describe` | 200 |

**Path prefixes are load-bearing — do NOT strip them.** Setup Connect API paths MUST start with
`/services/data/v67.0/`. Tooling REST paths MUST start with `/services/data/v67.0/tooling/`.

---

## Clarifying Questions

Ask only what you cannot infer:

- **Which org?** `sf` CLI alias or username (`--target-org <alias>`). Default: the org's default target.
- **What operation?** View; enable / disable the matrix; toggle manual override; set the default priority; add / change / remove a cell; seed a full matrix.
- **For add / change:** the `Impact` + `Urgency` coordinates and the resulting `Priority` (validated against the fetched picklist values).
- **For set-default-priority:** the target Priority value. If the user did **not** name one, dispatch `AskUserQuestion` with the org's active `Incident.Priority` picklist values as options — never guess.

---

## Workflow

All steps are sequential. **Always read before you write.** All calls go through `sf` CLI.

### Phase 1 — Preflight

1. `sf --version` to confirm the CLI is available.
2. `sf api request rest "/services/data/v67.0/sobjects/Incident/describe" --method GET --target-org <alias>`. A **200** with `Impact` / `Urgency` / `Priority` picklist fields confirms Incident Management is enabled. Extract active picklist values for later validation. If the describe response is large, dispatch a subagent (haiku tier) to extract just the three picklists.

### Phase 2 — Show current state (read-only)

Dispatch these reads (all expected to return 200):

3. `sf api request rest "/services/data/v67.0/setup/org/preferences/IncPriorityMatrixEnabled" --method GET --target-org <alias>` — matrix enable flag. Body: `{"isPreferenceEnabled": <bool>}`.
4. `sf api request rest "/services/data/v67.0/setup/org/preferences/IncPriorityOverrideEnabled" --method GET --target-org <alias>` — manual-override flag. Same body shape.
5. Matrix rows — `sf data query --use-tooling-api --target-org <alias> --query "SELECT Id, DeveloperName, ReferenceObject, Urgency, Impact, Priority FROM ServiceOpPriorityConfig WHERE ReferenceObject = 'Incident'"`. Returns zero or more rows. `DeveloperName` is required so the add step can derive a fresh unique suffix.
6. Default fallback priority — `sf api request rest "/services/data/v67.0/tooling/query/?q=SELECT+Id,MasterLabel,Metadata+FROM+StandardValueSet+WHERE+MasterLabel='IncidentPriority'" --method GET --target-org <alias>`. Read `records[0].Metadata.standardValue`, find the entry with `default: true`, take its `valueName` — that is the fallback priority.

Format the rows as an Impact × Urgency grid (see `examples/render-matrix.md`). Steps 3–6 together are the "view" operation and the before-snapshot.

**Duplicate-coordinate detection (load-bearing for Change / Remove):** group the Phase-2 rows by `(ReferenceObject, Urgency, Impact)`. If any group has more than one row, the matrix already contains duplicates (the server does not enforce uniqueness). For every operation whose target coordinate is duplicated, halt Phase 3 for that concern — do NOT ask the user to confirm a Change or Remove until they either name an explicit `Id` or approve a consolidation plan (see `Phase 4 → Change a cell` and `Phase 4 → Remove a cell`). Add is unaffected — the Phase-4 add path already refuses any coordinate already present in the snapshot.

### Phase 3 — Confirm target (`AskUserQuestion`, REQUIRED before any write)

Present the intended change as `(Concern: <before> → <after>)` and require an explicit "yes" via `AskUserQuestion`. Proceed to Phase 4 **only** on explicit "yes". On "no", stop and report the current state without writing.

### Phase 4 — Apply the change (skip for view-only)

Read the current value of the same concern first (Phase 2 covers this), confirm the target with the user (Phase 3), then dispatch. Payload shapes and full CLI invocations for every operation live in `examples/matrix-operations.md`.

- **Enable / disable the matrix** — `sf api request rest` PATCH on `IncPriorityMatrixEnabled` with body `{"desiredState": <bool>}`. PATCH response echoes `{"isPreferenceEnabled": <bool>}`; no separate re-read needed.
- **Toggle manual override** — `sf api request rest` PATCH on `IncPriorityOverrideEnabled` with body `{"desiredState": <bool>}`. Does **not** touch matrix rows or the default priority.
- **Add a cell** — `sf api request rest` POST on `/services/data/v67.0/tooling/sobjects/ServiceOpPriorityConfig` with body `{"ReferenceObject": "Incident", "Urgency": "<val>", "Impact": "<val>", "Priority": "<val>", "DeveloperName": "<unique>", "MasterLabel": "<same>"}`. Payload must have `ReferenceObject == "Incident"` — the SObject is shared with Problem / ChangeRequest and the server accepts any string. Validate every `Urgency` / `Impact` / `Priority` against the fetched picklists first — the Tooling endpoint does NOT enforce picklist validation. Deduplicate against the Phase-2 snapshot: the server does NOT reject duplicates on `(ReferenceObject, Urgency, Impact)`, so a second POST on the same coordinate silently persists as a second row and the runtime picks between them non-deterministically.
- **Change a cell** — read Phase-2 rows, find the row(s) matching `(ReferenceObject=Incident, Urgency, Impact)`. If **exactly one row matches**, `sf api request rest` PATCH on `/services/data/v67.0/tooling/sobjects/ServiceOpPriorityConfig/<Id>` with body `{"Priority": "<new val>"}`. If **zero rows match**, this is an add — not a change; surface and ask. If **more than one row matches** (duplicates were detected in Phase 2), do NOT dispatch — report the duplicate rows with their `Id` / `DeveloperName` / current `Priority`, and require the user to either name the exact `Id` to change or approve a consolidation plan (delete the extras, then change the survivor).
- **Remove a cell** — read Phase-2 rows, find the row(s) matching `(ReferenceObject=Incident, Urgency, Impact)`. If **exactly one row matches**, `sf data delete record --sobject ServiceOpPriorityConfig --record-id <Id> --use-tooling-api --target-org <alias>`. If **zero rows match**, short-circuit with "nothing to remove". If **more than one row matches**, do NOT dispatch — report the duplicates and require the user to either name the exact `Id`(s) to remove or explicitly confirm "remove all rows at this coordinate".
- **Seed a full matrix** — see `examples/seed-full-matrix.md`. Validate values first, then POST each row.
- **Set the default fallback priority** — `sf project retrieve start --metadata "StandardValueSet:IncidentPriority" --target-org <alias>`, edit the file to set `<default>true</default>` on the target value and `<default>false</default>` on every other, then `sf project deploy start --metadata "StandardValueSet:IncidentPriority" --target-org <alias> --wait 10`. Verify with `Succeeded` in the deploy result.

### Phase 5 — Verify and present

7. Re-read the concern that was mutated (matrix rows via Tooling SOQL; default priority via `StandardValueSet` query; prefs are echoed on PATCH response). If the observed state does not match the requested state, treat it as a failed write and report the raw server response verbatim.
8. Present before/after (Impact × Urgency grid via `examples/render-matrix.md`) plus a one-line summary (e.g. `Incident matrix: High/High → Critical added`). Matrix changes affect only Incidents created **after** the write; disabling the matrix does not clear stored rows or the default priority.

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| All operations run through `sf` CLI | The user-selected transport for this skill; no MCP dispatcher; no `/headless/invoke/*` route |
| Always API v67.0 minimum | The Setup Connect API pref routes require v67+ |
| Read live state before writing | The Phase-2 snapshot is the source of truth for the confirmation prompt, the idempotency check, and the Phase-5 verify |
| **REQUIRED confirm-to-write checkpoint** before any mutation | Toggling prefs or changing matrix rows mutates org state; user must approve the exact plan |
| Idempotent — skip the write when the current state already matches the requested state | Avoids no-op writes; see `references/sf-cli-invocation.md` for the exact match rule per concern |
| Validate every `Impact`, `Urgency`, `Priority` against the org's live picklist before dispatch | The Tooling REST endpoint does NOT enforce picklist validation; the runtime matrix evaluator does. Skipping this validation lets garbage rows into the matrix |
| Deduplicate rows client-side against the Phase-2 snapshot before add | The server does NOT enforce `(ReferenceObject, Urgency, Impact)` uniqueness — a second POST on the same coordinate persists as a separate row. Client-side dedup is the only guard against duplicate cells. |
| Refuse any `ReferenceObject` other than `Incident` (`Problem`, `ChangeRequest`, anything else) | `ServiceOpPriorityConfig` is shared with the Problem / ChangeRequest matrices at the wire level — the server accepts any `ReferenceObject` string. Scope to `Incident` is skill-enforced only. |
| On Change / Remove, if the target coordinate resolves to more than one row, do NOT dispatch — require an explicit `Id` or a confirmed consolidation plan | The server allows duplicate `(ReferenceObject, Urgency, Impact)` rows. Picking "the row Id" arbitrarily would mutate one duplicate and leave the other in place, keeping the matrix non-deterministic. |
| Report exact error text from the CLI response | The CLI surfaces the underlying error message verbatim |

---

## Verification Checklist

Before reporting completion of any mutation, confirm each of the following. If any item is unchecked, do not report success — surface what is missing.

- [ ] Phase 1 preflight (`sf api request rest` on Incident describe) returned 200 with active `Impact` / `Urgency` / `Priority` picklists; if 404, the raw error was surfaced and the run halted.
- [ ] Phase 2 read against every concern the write plans to touch returned 200 (or a raw error was surfaced) and each observed value was recorded as the "before" state. For Change / Remove, the Phase-2 rows were grouped by `(ReferenceObject, Urgency, Impact)` and any duplicate coordinates on the mutation target were surfaced to the user — no Change / Remove was dispatched until an explicit `Id` or a confirmed consolidation plan resolved the duplication.
- [ ] Phase 3 confirm-to-write presented `(<concern>: <current> → <requested>)` via `AskUserQuestion` and the user replied with an explicit "yes" — no write dispatched on any other response (silence, "maybe", "looks good", implicit approval).
- [ ] Idempotency: if the current state already matched the requested state, Phase 4 was skipped for that concern and reported as an idempotent no-op — no write was dispatched.
- [ ] Every `Impact`, `Urgency`, `Priority` in any add / change payload was validated against the Phase-1 picklist values before dispatch. Duplicates on `(ReferenceObject, Urgency, Impact)` were caught client-side against the Phase-2 snapshot — the server does NOT reject duplicates. Every add payload had `ReferenceObject == "Incident"`.
- [ ] Phase 4 writes used the exact CLI invocations from `references/sf-cli-invocation.md`; on any `4xx` / `5xx` (or non-`Succeeded` deploy), the raw response was surfaced and the run halted.
- [ ] Phase 5 verify re-read the affected concerns; any diff was reported as `write FAILED — server state differs from request` with the raw response.
- [ ] The final report gave a before/after with the Impact × Urgency grid and a one-line summary.

---

## Reference File Index

| File | When to read |
|------|--------------|
| `references/sf-cli-invocation.md` | Exact `sf` CLI invocations, response envelopes, picklist extraction, idempotency rules, and gotchas |
| `examples/render-matrix.md` | Impact × Urgency grid layout |
| `examples/matrix-operations.md` | Full CLI-invocation templates for enable, override, default, add / change / remove |
| `examples/seed-full-matrix.md` | Seed a full matrix (validate picklist values first) |
