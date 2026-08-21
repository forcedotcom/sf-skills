---
name: service-itsm-incident-mgmt-configure
description: "Reads and toggles the master Incident Management setting on a Salesforce ITSM org — the org-level switch that turns Incident Management on or off. Reads current state before writing, is idempotent, and requires explicit user confirmation before any change. Use when the user wants to enable, disable, toggle, view, or turn on/off Incident Management (Service ITSM) at the org level. DO NOT TRIGGER for Default Field Validations for Incidents, Auto Closure of Child Incidents, Email-to-Incident sub-toggles, Problem Management, Change Management, Case Management, ITSM External Client App setup, or Incident Priority Matrix configuration (use the service-itsm-incident-priority-configure skill)."
metadata:
  version: "1.1"
  domains: ["Service"]
  minApiVersion: "67.0"
  mcpTools:
    headless-360:
      tools: ["describe", "discover", "dispatch", "dispatch_readonly"]
      semver: ">=1.0.0"
  accessCheck:
    - type: "userPerm"
      value: "CustomizeApplication"
    - type: "orgPerm"
      value: "IncidentMgmt.orgHasITSMOrgPermission"
allowed-tools: |
  Read AskUserQuestion
  mcp__headless-360__discover
  mcp__headless-360__describe
  mcp__headless-360__dispatch
  mcp__headless-360__dispatch_readonly
---

# Configuring ITSM Incident Management (master toggle)

Read and toggle the **master Incident Management** setting on a Salesforce ITSM org. This is the org-level switch that turns Incident Management on or off. Enabling it also brings up its sub-features on the server side, so a full enablement is a single operation on the master.

Writes are **idempotent** (skipped when the current status already matches the requested state), the skill always **reads before it writes**, and an explicit **confirm-to-write** checkpoint is required before any mutation.

## What this skill controls

| Preference (Setup UI label) | In scope |
|-----------------------------|----------|
| Incident Management enablement (master) | Yes — read and toggle |
| Default Field Validations for Incidents, Auto Closure of Child Incidents, Email-to-Incident sub-toggles, Incident Priority Matrix, Problem/Change/Case Management, ITSM External Client App setup | No |

For the exact URLs, wire shapes, and worked examples for the master read and write, see `references/mcp-invocation.md`.

## Scope

- **In scope**: read and toggle the master Incident Management preference.
- **Out of scope**: Default Field Validations for Incidents (`IncidentValidationsEnabled`); Incident Priority Matrix configuration; Auto Closure of Child Incidents and Email-to-Incident sub-toggles; Problem Management; Change Management; Case Management; ITSM External Client App setup; other ITSM prefs (`IncidentTriageAgentEnabled`, `IncAssignWithAgentEnabled`, `AssignedGroupValidationEnabled`); broadcast-channel prefs; creation or configuration of Incident, Problem, or ChangeRequest records.

---

## Preconditions

Before the skill can call anything on `headless-360`, the target org and MCP client must be configured. If any of these are unmet, the tools will surface as `401`, `403`, or `404` on the first call; **do not fabricate state — surface the raw error and stop**.

1. **Server activated on the org**: Setup → MCP Servers → `headless-360` → **Activate**. Activation can take up to ~2 minutes.
2. **External Client App wired**: an ECA in the org with OAuth scopes `mcp_api` and `refresh_token`, JWT-based access tokens enabled, PKCE required. ECA propagation can take up to 30 minutes.
3. **API v67.0+**: required for the read and write routes this skill uses.
4. **MCP client registration**: the client (adk-eval / Claude Code) has an `additionalServers.headless-360` entry pointing to the correct env URL (see `references/mcp-invocation.md`).

If any precondition fails, the tools return one of:
- `401 Unauthorized` → ECA not propagated, wrong scopes, or expired token.
- `403 Forbidden` → user lacks perm, or org missing `IncidentMgmt.orgHasITSMOrgPermission`.
- `404 Not Found` → server not activated on the org.

Report the raw response verbatim rather than guessing which precondition failed.

---

## Architecture — How configuration works

| Step | What happens | Tool |
|------|--------------|------|
| Preflight | Confirm the target routes are reachable | `describe`, `dispatch_readonly` |
| Read schema | Fetch the request/response contract for the read and the write | `describe` |
| Read current state | Fetch the current status of the master preference | `dispatch_readonly` |
| Decide operation | View / enable / disable — inferred from the prompt | — |
| Confirm-to-write | Present `(status: current → requested)` and require explicit "yes" | — |
| Apply change | Enable or disable the master via the write route | `dispatch` |
| Verify | Re-read and compare against the requested state | `dispatch_readonly` |

**Idempotency**: after the Phase-3 read, if the current state already matches the requested state, skip Phase 5 and treat the operation as a no-op. `references/mcp-invocation.md` documents the exact status field and match rule.

**Read-only tool selection**: use `dispatch_readonly` for the read. Use `dispatch` for the write. The server refuses mutating operations through `dispatch_readonly`.

**Wire shape**: `dispatch` and `dispatch_readonly` both take `{"url": "/services/data/...", "method": "GET|POST|PATCH|...", "body"?: {...}, "query_params"?: {...}}`. See `references/mcp-invocation.md` for the exact request/response shapes; call `describe` at runtime to confirm.

---

## Clarifying Questions

Ask only what is not already in conversation context:

| Field | Description | Default |
|-------|-------------|---------|
| Requested direction | Explicit `enable` / `disable` (or `on` / `off`) | REQUIRED — no defaults; ask if the user only said "toggle" without a direction |
| Confirm write | Explicit "yes" before any `dispatch` mutation | **REQUIRED** — see Phase 4 |

If the user says "toggle" without specifying a direction, ask for the direction before Phase 4. Do not infer it from the current state.

---

## Workflow

All steps run against the `headless-360` MCP server; the tool namespace is `mcp__headless-360__<tool-name>`.

### Phase 0 — Reuse what the session already knows

Each preflight read below carries a **skip-if-already-known** clause. Before calling any
read endpoint, check whether an earlier turn in this session already produced the same
fact from a successful tool response tied to the current org (a prior invocation of this
skill, a parent orchestrator's live read, or an earlier `dispatch_readonly` this run).
**An explicit user statement is NOT a substitute** for a live read of the master
preference — user assertions can be stale or mistaken, and this skill relies on the read
being the source of truth for the confirmation payload and the Phase-6 idempotency verify.
When the only source is a user statement, re-read.

- **`describe` of the master read/write routes** — if the request/response schemas were
  already fetched against the current org this session, skip Phase 1 and Phase 2 and
  reuse the cached schema. `describe` output is stable within a session.
- **Current master preference state** — if the master `IncidentMgmtEnabled` value for
  the current org was already read this session **via a successful `dispatch_readonly`
  response** (Phase 3 result from an earlier run of this skill, or a parent orchestrator
  that already asked us to check), skip Phase 3 and reuse the recorded "before" value.
  A user's verbal claim that the switch is on or off is **not** cache-eligible.

**When in doubt, re-check.** Skip only when the earlier fact is unambiguously in context
AND you have not switched orgs — the `headless-360` MCP session binds to one org via the
JWT, so an org change is only possible if the session was re-authed mid-conversation. If
the user hints at a different org, or you cannot tell which org the earlier fact came
from, re-run the read. Note: any `dispatch` write elsewhere in the session that could
have flipped the master (this skill's Phase 5, or an admin change via another tool) also
invalidates the cache — re-read. A wrong skip on a live org write is worse than a
duplicated read.

### Phase 1 — Preflight (`discover` / `describe`)

1. *(Skip if the operation schemas were already verified this session — see Phase 0.)*
   Call `describe` on the read/write routes (or `discover` with a query like `"ITSM incident management setup discovery"` if the operation IDs are unknown). Confirm the operations exist and their argument schemas match `references/mcp-invocation.md`.
2. If any tool call returns `401` / `403` / `404`, halt and surface the raw error — the org or client is not configured correctly (see Preconditions).

### Phase 2 — Load Schemas (`describe`)

3. *(Skip if the schema for each operation is already cached this session — see Phase 0.)*
   For each operation the invocation will use, call `describe` and cache the returned request/response schema. **Do not hard-code the argument shape from the reference doc** — read it from `describe`; the docs are a working expectation, the runtime contract is whatever `describe` returns.

### Phase 3 — Read Current State (`dispatch_readonly`)

4. *(Skip if the current master state for this org was already read this session AND no
   write has flipped it since — see Phase 0.)*
   Read the current state of the master preference using the read route documented in `references/mcp-invocation.md`. Record the value as the "before" state for the Phase-4 confirmation and the Phase-6 verify.

   For a view-only request, stop after Phase 3 and go to Phase 7 to report.

### Phase 4 — Decide Operation + Confirm-to-Write (REQUIRED for any write)

5. Decide the operation from the user's prompt (view / enable / disable). If the user said "toggle" without a direction, ask for the direction first.

6. **Present the target payload** via `AskUserQuestion` as `(Master Incident Management: <current> → <requested>)`. Require an explicit "yes" before proceeding. **Proceed to Phase 5 ONLY on explicit "yes".** On "no", stop and report the current state without writing.

### Phase 5 — Apply the Change (skip for view-only)

7. Apply the idempotency rule from `references/mcp-invocation.md`: if the current state already matches the requested state, skip Phase 5 and mark the operation as an idempotent no-op.

8. Otherwise, dispatch the write via `dispatch` using the enable or disable route documented in `references/mcp-invocation.md`. Enabling the master brings up the Incident Management sub-features on the server side — no separate calls are needed to turn them on. Disabling the master leaves those sub-features at their last-set values.

9. On error (`4xx`, `5xx`), record the raw response verbatim and stop.

### Phase 6 — Verify (`dispatch_readonly`)

10. Re-issue the Phase-3 read and compare against the requested state per the rule in `references/mcp-invocation.md`. If they differ, treat it as a failed write and report the raw server response verbatim.

### Phase 7 — Report

11. Present a before/after summary:
    - View: `Master Incident Management: <current-status>`.
    - Toggle: `Master Incident Management: <before> → <after>` with verdict `SUCCEEDED` / `ALREADY-<state>` / `FAILED`.
    - On Phase-6 mismatch: `write FAILED — server state differs from request. Server response: <verbatim>`.

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| All operations run through the four hosted `headless-360` tools | The hosted MCP is the required transport |
| Read the argument schema for each operation via `describe` before calling `dispatch` / `dispatch_readonly` | The runtime contract is what `describe` returns; do not hard-code |
| Use `dispatch_readonly` for the read; use `dispatch` for the write | The server refuses mutating operations through `dispatch_readonly` |
| Always set/expect API **v67.0** minimum | The read and write routes require v67+ |
| Read live state before writing | The Phase-3 fetch is the source of truth for the confirmation prompt, the idempotency check, and the Phase-6 verify |
| **REQUIRED confirm-to-write checkpoint** before any `dispatch` mutation | Toggling this pref mutates org state; user must approve the exact plan |
| Idempotent — skip `dispatch` when the current state already matches the requested state | Avoids no-op writes; see `references/mcp-invocation.md` for the exact match rule |
| Report exact error text from the MCP tool response | The server surfaces the underlying error message verbatim |
| On `401` / `403` / `404` in Phase 1, halt and surface the raw error | The failing precondition is diagnosable only from the raw response |
| Do not put an orgId or Core URL in the `dispatch` arguments | The server derives the target org from the JWT issuer on the request |

---

## Verification Checklist

Before reporting completion of any mutation, confirm each of the following. If any item is unchecked, do not report success — surface what is missing.

- [ ] Phase 1 preflight (`describe` / `discover`) returned the operation without a `401` / `403` / `404`; if any was returned, the raw error was surfaced and the run halted.
- [ ] Phase 3 read against the master preference returned a status and that value was recorded as the "before" state.
- [ ] Phase 4 confirm-to-write presented `(Master Incident Management: <current> → <requested>)` via `AskUserQuestion` and the user replied with an explicit "yes" — no write dispatched on any other response (silence, "maybe", "looks good", implicit approval).
- [ ] Idempotency: if the current state already matched the requested state, Phase 5 was skipped and the run was reported as an idempotent no-op — no `dispatch` write was issued.
- [ ] Phase 5 write used `dispatch` (not `dispatch_readonly`) with the wire shape from `references/mcp-invocation.md`; on any `4xx` / `5xx`, the raw response was surfaced and the run halted.
- [ ] Phase 6 verify re-issued the Phase-3 read and the post-write state matched the user-approved target; any diff was reported as `write FAILED — server state differs from request`.
- [ ] The final report gave a before/after for the master preference with verdict `SUCCEEDED` / `ALREADY-<state>` / `FAILED`.

---

## Reference File Index

| File | When to read |
|------|--------------|
| `references/mcp-invocation.md` | Exact tool call shapes for the master read and write, MCP-client registration recipe for `headless-360` in `mcp-config.json`, External Client App setup checklist (`mcp_api` scope, PKCE, JWT), Headless-360 error taxonomy, and a worked enable/disable example |
