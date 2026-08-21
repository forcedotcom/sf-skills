# Report Generation

How to render the validation report after running a checklist, plus special-case notes and the
optional swarming OAuth-token clear.

---

## The report table

Render a table with **all four columns** — never omit `Configured Value`:

- `#` — check number
- `Check` — check description
- `Status` — OK, FAIL, or MANUAL verification required
- **`Configured Value`** — the actual value read from the org (CORS URLs, Enabled/Disabled, app name, PSL assignment, etc.)
- `Action Required` — the remediation for any FAIL / MANUAL (Setup path from the checklist)

## Status rendering rules

| Recorded status | Render as | Display text |
|---|---|---|
| `OK` | OK | correctly configured |
| `MISCONFIGURED` / `MISSING` / `DISABLED` / `ERROR` | FAIL | needs to be fixed (include the exact Setup path) |
| `MANUAL_CHECK_REQUIRED` | MANUAL | requires manual verification |

**Critical:** `MANUAL_CHECK_REQUIRED` is always MANUAL and "requires manual verification" — **never**
render it as FAIL/MISCONFIGURED, even when the cause is a missing optional input (e.g. no Tenant ID
provided for the Azure app check). Note that the user can re-run with that input to complete it.
Only `MISCONFIGURED`, `MISSING`, `DISABLED`, `ERROR` are FAIL.

## Special cases

**Azure AD App check when `MANUAL_CHECK_REQUIRED`** (Tenant ID not provided) — after the table add:

> **Note —** The Azure AD App check requires manual verification. Re-run and provide the Azure AD
> Tenant ID to validate the Azure app, or verify it manually per the Salesforce help doc for
> configuring the Teams fulfiller-hub app.

**Swarming per-user OAuth token when `MISSING`** — the token is minted on the user's first swarm
attempt. Tell the user to: open Microsoft Teams → the **Salesforce IT Desk app** (the fulfiller
app, NOT the IT Service employee app) → attempt to create/join a swarm → complete the Microsoft
login when prompted → the token is stored and swarming should work.

## Closing note

**If all checks passed (0 failed, 0 manual):**

> **All checks passed.** The Salesforce backend is correctly configured. If the issue persists,
> reload the Teams app: in Microsoft Teams, click the **⋯** on the Salesforce IT Desk or IT Service
> app → **Reload app**. If it's still unresolved, escalate to the ITSM support team.

**If any check failed (1+ failed or manual):** do NOT add the reload note — the per-check
`Action Required` steps are the fix.

## Example report

```text
=== VALIDATION REPORT ===
Problem reported: IT Desk login not working
Checklist applied: LOGIN_DESK
Org: https://yourorg.my.salesforce.com

| # | Check                                     | Status      | Configured Value                                   | Action Required
|---|-------------------------------------------|-------------|------------------------------------------------------|----------------
| 1 | CORS OAuth endpoints enabled              | OK          | Enabled                                            |
| 2 | CORS Allowed Origins                      | OK          | cdn.scs.static.lightning.force.com, teams.cloud.microsoft |
| 3 | External Client App: ServiceCloudTeamsEca | OK          | ServiceCloudTeamsEca                               |
| 4 | Microsoft Teams for Employee Service      | OK          | Enabled                                            |
| 5 | Salesforce IT Desk Feature                | OK          | Enabled                                            |
| 6 | User PSL: TeamsForITSrvcsPsl assigned     | FAIL MISSING | user@org.com — NOT assigned                        | Setup → Users → open user → PSL Assignments → add Teams for IT Services

Summary: 5 passed | 1 failed | 0 require manual verification
```

---

## Optional: clear the swarming OAuth token (SWARMING checklist, all checks passed)

Only when the checklist was `SWARMING` **and** all checks passed, offer to clear and re-mint the
per-user OAuth token for the `MSTeamsBrowserFlowEC` external credential (a stale token can block
swarming even when config is correct). Ask first with `AskUserQuestion`; only proceed on an
explicit "yes."

This is the **one state-changing action** in this skill. Perform it as the end-user (the person
with the swarming issue):

1. **Check current token:**
   `dispatch_readonly GET /services/data/v65.0/named-credentials/credential?principalType=PerUserPrincipal&externalCredential=MSTeamsClientCredentialsEC`
2. **Clear it:**
   `dispatch DELETE /services/data/v65.0/named-credentials/credential?principalType=PerUserPrincipal&externalCredential=MSTeamsBrowserFlowEC`

- **DELETE 200/204:** "OK — Token cleared. Retry swarming — you'll be prompted to re-authenticate
  with Microsoft on the next swarm attempt."
- **DELETE failed:** "FAIL — Couldn't clear the token: `<error>`. Clear it manually in Setup → Named
  Credentials → MSTeamsBrowserFlowEC."
