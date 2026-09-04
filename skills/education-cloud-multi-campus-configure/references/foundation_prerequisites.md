# Step 0 — Foundation Prerequisites

This skill can run standalone, without any other Education Cloud setup skill running first. Verify
these before Step 1 — they are shared across the EDU skill family. A gap here is a missing
prerequisite to resolve, not a dead end — self-heal what's API-writable, ask/confirm before any
write, otherwise instruct manual Setup and wait for confirmation.

## Checks (in order — each can stop the workflow if unresolved)

1. **Org edition** — `GET /services/data/v68.0/query`, `queryParams: {"q": "SELECT OrganizationType FROM Organization"}`
   (singleton, no Id). Must be Enterprise, Performance, Unlimited, or Developer Edition. Cannot be
   fixed via API or Setup — if wrong edition, tell the user Education Cloud requires Enterprise+ and
   stop.

2. **Lightning Experience enabled** — no supported read API; if BusinessProfile/Account describe
   calls below succeed the org is on Lightning (Classic-only orgs can't run this skill). If any call
   in this section fails with an org-mode-related error, instruct: Setup → User Interface → Enable
   Lightning Experience. Wait for confirmation, retry.

3. **Education Cloud license provisioned** — permission set names for this vary by org/release
   (confirmed live: one org shipped `EducationCloudAccess`, `AgentforceForEducationCloudAccess`, and
   `EinsteinForEducationCloudAccess` — never `EducationCloudUser`). Do not match on a single exact
   name. `GET /services/data/v68.0/query`, `queryParams: {"q": "SELECT Id, Name FROM PermissionSet
   WHERE Name LIKE '%EducationCloud%'"}`. Rows found → provisioned, proceed. Zero rows → cross-check
   before concluding anything: `GET /services/data/v68.0/sobjects/BusinessProfile/describe` — if it
   404s or returns `createable:false`, license is genuinely not provisioned; tell the user and stop
   (cannot be fixed via API, they need to provision the license). If it 200s with `createable:true`
   despite the zero-row permission-set query, treat the license as provisioned and note the mismatch
   rather than trusting the permission-set name search alone.

4. **Running user has Education Cloud access** — `GET /services/data/v68.0/query`,
   `queryParams: {"q": "SELECT Id, PermissionSet.Name FROM PermissionSetAssignment WHERE
   AssigneeId='<running user Id>' AND PermissionSet.Name LIKE '%EducationCloud%'"}` (resolve the
   running user's Id first — ask for their username if unknown). No rows → no API route to
   self-assign. Instruct: Setup → Permission Sets → find the org's actual Education Cloud permission
   set (from Check 3's query results) → Manage Assignments → add the running user. Wait for
   confirmation, then re-run this check before proceeding.

5. **Education Cloud Foundation enabled** — `GET /headless/invoke/platform/education-cloud-settings`
   via `dispatch_readonly`, inspect `educationCloudEnabled`.
   - `true` → proceed to Step 1.
   - `false` → ⚠️ **IRREVERSIBLE — one-way by design.** Warn the user explicitly; do NOT promise a
     revert. Ask for confirmation: "Education Cloud Foundation isn't enabled on this org. Enable it
     now? This cannot be turned off afterward." On "No": stop — the hierarchy cannot be created
     without it. On "Yes": `PATCH /headless/invoke/platform/education-cloud-settings/enable-education-cloud`
     (empty body, write-enabled `dispatch`). Cold-verify by repeating the GET — confirm
     `educationCloudEnabled: true` on a fresh read.
   - **If the invoke endpoint errors, or cold-verify still shows `false`**: fall back to manual UI —
     Setup → Quick Find → "Set Up Education Cloud" → Select Set Up Education Cloud → Toggle "Enable
     Education Cloud" → Save. Wait for user confirmation, then cold-verify again before proceeding.

Do not proceed to Step 1 until all five checks pass.
