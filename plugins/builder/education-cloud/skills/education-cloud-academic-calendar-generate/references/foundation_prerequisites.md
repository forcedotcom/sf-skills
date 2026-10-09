# Foundation Prerequisites (Step 0)

Run before Step 1 on every standalone invocation. Shared across the EDU skill family (also required by `education-cloud-multi-campus-configure`). Do not create any Academic Year/Term/Session record until every check below passes.

All checks use the org REST transport resolved in Execution Transport — no `sf`/`sfdx`/`curl`.

## 1. Org edition

`GET /services/data/<ver>/query` with `queryParams: {"q": "SELECT OrganizationType FROM Organization"}`.

Education Cloud requires Enterprise, Performance, Unlimited, or Developer edition. If the org is a different edition (e.g. Group, Professional), STOP — this is not fixable via API. Tell the user the org edition doesn't support Education Cloud.

## 2. Lightning Experience enabled

No dedicated read API for this. Infer it from other calls in this checklist succeeding normally. If a call unexpectedly errors in a way consistent with Classic-mode restrictions, tell the user to enable Lightning Experience manually (Setup → Lightning Experience → turn it on) and re-run this checklist.

## 3. Education Cloud license provisioned

`GET /services/data/<ver>/query` with `queryParams: {"q": "SELECT Id, Name FROM PermissionSet WHERE Name LIKE '%EducationCloud%'"}`.

- One or more rows → license is provisioned, continue to check 4.
- Zero rows → cross-check before concluding it's absent: `GET /services/data/<ver>/sobjects/BusinessProfile/describe`. If the describe succeeds and `createable:true`, the license is present despite the empty query (permission set naming varies by org) — continue to check 4.
- Still zero rows AND describe fails/`createable:false` → genuinely absent. STOP — this is not fixable via API. Tell the user Education Cloud needs to be provisioned on this org (Setup → licenses).

## 4. Running user has EDU access

Resolve the running user's Id first — `GET /services/oauth2/userinfo` and read `user_id`/`sub`, or ask for their username if that endpoint isn't reachable through the resolved transport. Then:

`GET /services/data/<ver>/query` with `queryParams: {"q": "SELECT Id FROM PermissionSetAssignment WHERE AssigneeId = '<resolved running user Id>' AND PermissionSet.Name LIKE '%EducationCloud%'"}`.

- One or more rows → continue to check 5.
- Zero rows → tell the user the running user needs an Education Cloud permission set assigned (Setup → Users → Permission Set Assignments), wait for confirmation, then re-run this query before proceeding.

## 5. Education Cloud Foundation enabled

`GET /headless/invoke/platform/education-cloud-settings` → read `educationCloudEnabled`.

- `true` → all checks pass, proceed to Step 1.
- `false` → this flips the org into Education Cloud mode and is **IRREVERSIBLE**. Warn the user explicitly and ask for confirmation before enabling. On confirmation: `PATCH /headless/invoke/platform/education-cloud-settings/enable-education-cloud`, then cold-verify with a fresh `GET /headless/invoke/platform/education-cloud-settings` (a `success:true` on the PATCH is not proof — re-read `educationCloudEnabled`). If the API path fails, fall back to the manual path: Setup → "Set Up Education Cloud" → toggle → Save, wait for the user to confirm, then re-verify with the same GET.
- If the user declines to enable it, STOP — do not proceed to Step 1.
