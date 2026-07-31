---
name: platform-sandbox-configure
description: "MUST USE this skill for ANY sandbox request — including simply getting a sandbox's details, status, license type, or pending-activation state by name or ID. TRIGGER when the user: types \"sandbox -help\"/\"sandbox help\"; mentions a sandbox ID (07E prefix); asks to list or show sandboxes; asks for the details, status, license type, or config of a sandbox by name or ID; activates or discards a completed refresh; deletes a sandbox; verifies activation or deletion; creates or refreshes a sandbox. DO NOT TRIGGER when: the user wants to clone a sandbox."
metadata:
  version: "1.0"
  minApiVersion: "66.0"
  accessCheck:
    - type: "userPerm"
      value: "ManageSandboxes"
  cliTools:
    - tool: ["sf"]
      semver: ">=2.0.0"
---

# Sandbox Lifecycle Management

Manage Salesforce sandbox environments through Connect REST API — list inventory, activate or discard completed refreshes, create and refresh sandboxes, and permanently delete sandboxes.

## When This Skill Owns the Task

Use `platform-sandbox-configure` when the work involves:
- Listing or retrieving all sandboxes (GET /sandbox/reports)
- Getting details or status of a specific sandbox by name or by ID (07E prefix)
- Activating a sandbox after a refresh completes (applying the refresh)
- Discarding a completed refresh (keeping existing sandbox data unchanged)
- Permanently deleting a sandbox to free up licenses
- Verifying activation or deletion completed
- Creating a new sandbox (Developer, Developer Pro, Partial Copy, or Full)
- Refreshing an existing sandbox with latest production data

Delegate elsewhere when the user is:
- Cloning a sandbox → Tooling API (`SandboxInfo` sObject)

---

## Help (Interactive Menu)

When the user types `sandbox -help` or `sandbox help`, respond with ONLY a text message showing the numbered operation list below. **Do NOT call any API or tool — just display this menu and wait for the user to reply with a number.**

The agent MUST respond with this exact markdown (not in a code block — render it directly as a bullet list):

**Sandbox Lifecycle Management**

**1. Inventory & Details**
- a. List all sandboxes — Names, types, statuses, IDs
- b. Get details (by name) — Status, license, config
- c. Get details (by ID) — Provide a 07E ID directly

**2. Create & Refresh**
- a. Create a new sandbox — Dev, Dev Pro, Partial, Full
- b. Refresh a sandbox — Latest production data

**3. Activate, Discard & Delete**
- a. Activate a sandbox — Apply a completed refresh
- b. Discard a refresh — Reject, keep existing data
- c. Delete a sandbox — Permanent removal

**4. Verify & Monitor**
- a. Verify activation status — Check if activate completed
- b. Verify deletion status — Check if delete completed

Reply with a code (e.g. "3a") or describe what you need.

**After the user replies, ask for the required input:**

| Selection | Follow-up question |
|---|---|
| 1a | No input needed — proceed immediately |
| 1b | "What's the sandbox name?" |
| 1c | "What's the sandbox ID? (starts with 07E)" |
| 2a | "What name for the new sandbox, and what license type? (Developer, Developer_Pro, Partial_Copy, Full)" |
| 2b | "Which sandbox do you want to refresh? Optionally, provide a new name and/or description." |
| 3a | "Which sandbox? Provide a name or 07E ID." |
| 3b | "Which sandbox? Provide a name or 07E ID." |
| 3c | "Which sandbox? Provide a name or 07E ID." |
| 4a | "Which sandbox did you activate? Provide a name or 07E ID." |
| 4b | "Which sandbox did you delete? Provide a name or 07E ID." |

Execute the corresponding operation from the Operations section below.

---

## API Base

**CRITICAL:** For sandbox operations in this skill, use the Connect REST API. Two discovery paths exist:
- **By name:** Call `GET /sandbox/reports` to list all sandboxes and find the matching one by `sandboxName`.
- **By ID (07E prefix):** Call `GET /sandbox/sandboxes/{sandboxId}` directly — do NOT call `/sandbox/reports`.

Both paths return sandbox records with `sandboxId` (prefix `07E`) which is required for all lifecycle mutation operations.

```bash
# List all sandboxes (Connect REST API)
sf api request rest "/services/data/v66.0/sandbox/reports" --method GET

# Response format:
# {
#   "count": 3,
#   "sandboxes": [
#     {
#       "sandbox": {
#         "sandboxId": "07E...",        # Required for all operations
#         "sandboxName": "mybox",       # Top-level field — use this for name lookup
#         "license": "Developer",
#         "isPendingActivation": false,
#         "canActivate": true,
#         "canDelete": true,
#         ...
#       }
#     }
#   ]
# }
```

**IMPORTANT:** Do NOT use Tooling API (`SandboxInfo` or `SandboxProcess`) for sandbox discovery. The mutation endpoints (activate/discard/delete) require the `sandboxId` (07E prefix) from the Connect REST API response, NOT the `SandboxInfo.Id` (0GQ prefix) or `SandboxProcess.Id` (0GR prefix).

**NEVER use SOQL / `run_soql_query` / `sf data query` for sandbox lifecycle reads — status, inventory, details, license, or pending-activation state (e.g. a "get details / status / license / pending-activation for sandbox X" request).** This data lives ONLY in the Connect REST API response (`GET /sandbox/reports` for name lookup, `GET /sandbox/sandboxes/{07E-id}` for ID lookup); there is no SObject that returns it correctly. (`sf data query --use-tooling-api` on `SandboxInfo` remains valid for the Create and Refresh flows in Operations 7 and 8, which look up the `SandboxInfo` record to mutate it — that is not a lifecycle read.) If a name lookup returns an empty inventory (`count: 0`), the sandbox does not exist — report an honest `not_found`; do NOT retry the lookup via SOQL and do NOT fabricate details.

**Report the API result exactly as it comes back — never invent an error or a cause.** A `count: 0` response is a *successful* result meaning the sandbox is absent: record it directly as `not_found` with the endpoint and empty inventory as evidence. Do NOT reinterpret an empty list as an API failure. If the Connect REST API genuinely returns an error, capture that error body verbatim as the outcome — but do NOT speculate about *why* (e.g. "this must be a scratch org", "sandbox endpoints aren't supported here"). This endpoint does not report the org's edition or type, so any such explanation is a fabrication and must not appear in the output.

**Discovery Patterns:**

**When user provides a sandbox NAME:**
1. Call `GET /sandbox/reports` to get the full list
2. Iterate through `sandboxes[]` array
3. Check `sandbox.sandboxName` (top-level field) to find the matching sandbox
4. Extract `sandbox.sandboxId` from that record
5. Use the `sandboxId` in subsequent mutation operations

**When user provides a sandboxId (07E prefix) directly:**
1. Call `GET /sandbox/sandboxes/{sandboxId}` to verify it exists and check current status
2. Use the same `sandboxId` directly in the mutation endpoint — do NOT call `/sandbox/reports`

Required permission: `ManageSandboxes`

---

## Operations

### 1. List Sandbox Inventory

**Endpoint:** `GET /services/data/v66.0/sandbox/reports`

Returns a list of all sandboxes with their IDs, names, statuses, and license types.

```bash
sf api request rest "/services/data/v66.0/sandbox/reports" --method GET
```

**Response format:**
```json
{
  "count": 3,
  "sandboxes": [
    {
      "sandbox": {
        "sandboxId": "07E...",
        "sandboxName": "DevBox1",
        "license": "Developer",
        "isPendingActivation": false,
        "canActivate": true,
        "canDelete": true,
        "canDiscard": false
      }
    }
  ]
}
```

**Use when:** User asks "show me all sandboxes", "how many sandboxes do I have", "what's the status of my sandboxes"

**Key response fields:**
- `sandbox.sandboxId` (07E prefix) — Required for all mutation operations
- `sandbox.sandboxName` — The sandbox name (top-level field)
- `sandbox.license` — Developer, Developer Pro, Partial Copy, Full
- `sandbox.isPendingActivation` — true if refresh is pending activation
- `sandbox.canActivate` / `canDelete` / `canDiscard` — Permission flags

---

### 2. Get Sandbox Details

**Endpoint:** `GET /services/data/v66.0/sandbox/sandboxes/{sandboxId}`

Returns detailed info for a specific sandbox.

**Use when:** User asks about a specific sandbox's status, configuration, or metadata.

**Key response fields:**
- `status` — Active, Pending Activation, Activating, Completed, etc.
- `isPendingActivation` — true if a refresh completed and awaits user decision
- `sandboxType` — Developer, DeveloperPro, PartialCopy, Full
- `sourceId` — ID of the source org

---

### 3. Activate Sandbox (Apply Refresh)

**Endpoint:** `PATCH /services/data/v66.0/sandbox/activate/{sandboxId}`

**CRITICAL DOMAIN RULE:** This operation ONLY applies to sandboxes with a completed refresh in "Pending Activation" state. It applies the refreshed data to the sandbox. It does NOT "bring an inactive sandbox online" or "start" a sandbox.

**Pre-conditions:**
- Sandbox must be in `Pending Activation` status
- A refresh must have completed successfully
- User must have `ManageSandboxes` permission

**Before calling PATCH /activate:**
- [ ] Confirmed sandbox is in `Pending Activation` status via GET `/sandbox/sandboxes/{id}` (`isPendingActivation: true`)
- [ ] Confirmed a refresh has completed successfully

**Use when:** User says "activate it", "apply the refresh", "use the latest data"

**After activation:** The sandbox runs with the newly refreshed production data.

---

### 4. Verify Activation

**Endpoint:** `GET /services/data/v66.0/sandbox/sandboxes/{sandboxId}`

Poll this endpoint after activation to confirm status changed to `Active`. This is a verification step, not a standalone user action.

**Use when:** Agent needs to confirm activation completed (called automatically after activate).

---

### 5. Discard Sandbox (Reject Refresh)

**Endpoint:** `DELETE /services/data/v66.0/sandbox/discardsandbox/{sandboxId}`

**CRITICAL DOMAIN RULE:** This operation ONLY applies to sandboxes with a completed refresh in "Pending Activation" state. It rejects the refresh — the existing sandbox continues running with its current data unchanged. It does NOT:
- Free up licenses
- Soft-delete or hide the sandbox
- Reset the sandbox to match production

**Pre-conditions:**
- Sandbox must be in `Pending Activation` status
- A refresh must have completed

**Before calling DELETE /discardsandbox:**
- [ ] Confirmed sandbox is in `Pending Activation` status via GET `/sandbox/sandboxes/{id}` (`isPendingActivation: true`)
- [ ] Confirmed this is a discard (reject refresh), NOT a delete (permanent removal)

**Use when:** User says "discard the refresh", "keep existing data", "don't apply the refresh", "reject the refresh"

**WARNING:** Discard is not reversible. The user will need to trigger a new refresh if they want fresh production data later.

---

### 6. Delete Sandbox (Permanent)

**Endpoint:** `DELETE /services/data/v66.0/sandbox/deletesandbox/{sandboxId}`

Permanently removes a sandbox and frees the license.

**Pre-conditions:**
- Sandbox must exist
- User must have `ManageSandboxes` permission

**Before calling DELETE /deletesandbox:**
- [ ] Surfaced sandbox details (name, license, status) with user and received explicit delete approval

**Use when:** User says "delete this sandbox", "remove it permanently", "free up the license"

**WARNING:** This is irreversible. Always confirm with the user before executing. Surface the sandbox name, license, and status as a safety check.

---

### 7. Create a New Sandbox

Creates a new sandbox from scratch. Two approaches are supported — pick based on the user's preference; default to Approach A unless the user asks for a definition file or a repeatable DX blueprint.

#### Approach A — Tooling API record (direct)

**API:** Tooling API — `SandboxInfo` sObject

**Required inputs:**
- `SandboxName` — Name for the new sandbox (alphanumeric, max 10 chars)
- `LicenseType` — One of: `Developer`, `Developer_Pro`, `Partial_Copy`, `Full`

**Optional inputs:**
- `Description` — Description of the sandbox purpose
- `Features` — `true` to upgrade sandbox data storage to 400 MB (WARNING: once enabled, cannot be decreased)
- `ApexClassId` — ID of an Apex class that implements `SandboxPostCopy` interface (runs after creation completes)
- `ActivationUserGroupId` — ID of a Group that determines which users can access the sandbox

```bash
# Create a Developer sandbox
sf data create record --sobject SandboxInfo --use-tooling-api --values "SandboxName='mybox' LicenseType='Developer'"
```

#### Approach B — Sandbox definition file (Salesforce CLI)

The DX-native path: write a JSON definition file (a reusable blueprint), then create the sandbox from it with `sf org create sandbox`. Prefer this when the user wants a checked-in, repeatable config or name-based Apex/group references (no ID lookups).

```json
// config/dev-sandbox-def.json
{
  "sandboxName": "mybox",
  "licenseType": "Developer"
}
```

```bash
sf org create sandbox --definition-file config/dev-sandbox-def.json --alias mybox --target-org prod
```

**Definition file fields:**

| Field | Required | Notes |
|-------|----------|-------|
| `sandboxName` | Yes | Alphanumeric, max 10 chars |
| `licenseType` | Yes | `Developer`, `Developer_Pro`, `Partial`, `Full` — **note: `Partial`, not `Partial_Copy`** in the definition file |
| `description` | No | Purpose of the sandbox (≤1000 chars) |
| `apexClassName` / `apexClassId` | No | Apex class implementing `SandboxPostCopy`; the definition file adds the *Name* variant so no ID lookup is needed |
| `activationUserGroupName` / `activationUserGroupId` | No | Public group controlling sandbox access; *Name* variant avoids an ID lookup |
| `features` | No | `"['SandboxStorage']"` to upgrade data storage (Developer → 400 MB, Dev Pro → 2 GB); not for Partial/Full |
| `templateId` | Partial (required), Full (optional) | Sandbox template (15-char ID beginning `1ps`) selecting which objects to copy |
| `historyDays` / `copyChatter` / `copyArchivedActivities` | No | Full sandboxes only |

**Pre-conditions:**
- Available license of the requested type must exist in the org
- Sandbox name must be unique and not already in use
- User must have `ManageSandboxes` permission

**After creation:** A `SandboxProcess` record is created with Status = `Processing`. The sandbox copy begins immediately.

---

### 8. Refresh an Existing Sandbox

Refreshes a sandbox with the latest production data. Two approaches are supported — pick based on the user's preference; default to Approach A unless the user asks for a definition file.

#### Approach A — Tooling API record (direct)

**API:** Tooling API — `SandboxInfo` sObject (PATCH)

Refreshes by updating the existing `SandboxInfo` record.

**Required inputs:**
- Sandbox name — to look up the `SandboxInfo` record ID (0GQ prefix)

**Optional inputs:**
- `SandboxName` — New name for the refreshed sandbox (if user wants to rename it; alphanumeric, max 10 chars)
- `Description` — New or updated description for the sandbox
- `AutoActivate` — `true` to auto-activate when refresh completes (default: false)
- `Features` — `true` to upgrade sandbox data storage to 400 MB (WARNING: once enabled, cannot be decreased)
- `ApexClassId` — ID of an Apex class that implements `SandboxPostCopy` interface (runs after refresh completes)
- `ActivationUserGroupId` — ID of a Group that determines which users can access the sandbox

**Ask the user:** "Which sandbox do you want to refresh? Optionally, provide a new name and/or description if you'd like to change them."

**Steps:**

```bash
# 1. Look up the SandboxInfo record Id by name
sf data query --query "SELECT Id, SandboxName, LicenseType, Description FROM SandboxInfo WHERE SandboxName = '<name>'" --use-tooling-api --json

# 2. Update the record to trigger refresh (PATCH the SandboxInfo record)
# Include SandboxName and Description only if the user provided new values
sf data update record --sobject SandboxInfo --use-tooling-api --record-id <0GQ-id> --values "AutoActivate=true SandboxName='<newName>' Description='<description>'"
```

**Note:** Only include `SandboxName` in `--values` if the user wants to rename. Only include `Description` if the user provides one. Always include `AutoActivate`.

#### Approach B — Sandbox definition file (Salesforce CLI)

Refresh from the same JSON definition-file blueprint used for create (see Operation 7 for the full field table), using `sf org refresh sandbox`. Use the existing sandbox's name; the definition file supplies any changed settings (e.g., `autoActivate`, `apexClassName`).

```json
// config/dev-sandbox-def.json
{
  "sandboxName": "mybox",
  "licenseType": "Developer",
  "autoActivate": true
}
```

```bash
sf org refresh sandbox --name mybox --definition-file config/dev-sandbox-def.json --target-org prod
```

**Pre-conditions:**
- Sandbox must exist and be in a refreshable state
- Refresh interval must have elapsed (Developer = 1 day, Dev Pro = 1 day, Partial = 5 days, Full = 29 days)
- User must have `ManageSandboxes` permission

**After refresh:** A new `SandboxProcess` record is created with Status = `Processing`. If `AutoActivate=true`, the sandbox activates automatically when done. Otherwise it enters `Pending Activation` state.

---

## Decision Guide for Agents

### When user provides a sandbox NAME (lookup required)

| User says... | Operation | Key check |
|---|---|---|
| "Show all my sandboxes" | GET /sandbox/reports | — |
| "What's the status of X?" | GET /sandbox/reports, filter by sandboxName | — |
| "Activate sandbox sbxtest" | 1. GET /sandbox/reports to find sandboxId by name<br>2. PATCH /sandbox/activate/{sandboxId} | Must be isPendingActivation: true |
| "Discard the refresh on sbxtest" | 1. GET /sandbox/reports to find sandboxId by name<br>2. DELETE /sandbox/discardsandbox/{sandboxId} | Must be isPendingActivation: true |
| "Delete sandbox sbxtest" | 1. GET /sandbox/reports to find sandboxId by name<br>2. DELETE /sandbox/deletesandbox/{sandboxId} | Confirm with user first |

### When user provides a sandboxId (07E prefix) directly

| User says... | Operation | Key check |
|---|---|---|
| "Get details for 07E..." | GET /sandbox/sandboxes/{sandboxId} | — |
| "Activate sandbox 07E..." | 1. GET /sandbox/sandboxes/{sandboxId} to verify status<br>2. PATCH /sandbox/activate/{sandboxId} | Must be isPendingActivation: true |
| "Discard refresh on 07E..." | 1. GET /sandbox/sandboxes/{sandboxId} to verify status<br>2. DELETE /sandbox/discardsandbox/{sandboxId} | Must be isPendingActivation: true |
| "Delete sandbox 07E..." | 1. GET /sandbox/sandboxes/{sandboxId} to verify existence<br>2. DELETE /sandbox/deletesandbox/{sandboxId} | Confirm with user first |

---

## Common Mistakes to Avoid

| Mistake | Correct understanding |
|---|---|
| Using activate to "start" any sandbox | Activate ONLY applies completed refreshes |
| Using discard to "hide" or "soft-delete" | Discard ONLY rejects a pending refresh |
| Activating without checking status first | Always verify isPendingActivation = true |
| Activating without user confirmation | Always confirm with the user before applying a refresh — this replaces existing sandbox data |
| Discarding without user confirmation | Always confirm with the user before discarding — this is irreversible and the refresh data is lost |
| Deleting without user confirmation | Always show sandbox info and ask for explicit confirmation |
