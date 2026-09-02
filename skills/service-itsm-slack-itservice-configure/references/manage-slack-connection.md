# Manage Slack Connection — status read (API) + approval (UI)

The Salesforce-side half of the Slack↔Salesforce connection. **Status is readable via API; approval
is not.** Headless users have no Setup UI, so always read status via API first rather than sending
them to Setup blind.

## Read connection status (API — do this every run)

```text
mcp__headless-360__dispatch_readonly(
  method: "GET",
  url:    "/services/data/v67.0/connect/slackbridge/connections"
)
```

Returns the live state (verified `200`):

```json
{
  "team": {
    "status": "CONNECTED",
    "teamName": "Slackfarm 1473",
    "teamDomain": "https://slackfarm-1473.enterprise.slack.com",
    "teamId": "E0…"
  },
  "currentUserMapping": { "salesforceUserId": "005…", "slackUserId": "U0…" }
}
```

Translate `team.status` to plain language:

- **`CONNECTED`** → workspace already approved and live. Name it by `teamName`; **skip the approval
  walkthrough** and move on. A `null` `currentUserMapping.salesforceUserId` means *this* user isn't
  mapped to a Slack user yet — mention it, but it doesn't block the connection.
- **`team: null` / not-connected / call errors** → **no *activated* connection is visible via API yet.**
  This endpoint populates `team` **only** once the connection reaches `CONNECTED` (activated, Slack Part
  3); during the requested/pending window it returns `{team: null}` **even though the connection exists**.
  A null is therefore *indeterminate*, **not** proof the request is absent — **never** tell the user it
  "didn't land" or "isn't on the Salesforce side". The pending/requested connection is visible only in
  **Setup → Manage Slack Connection** (`/lightning/setup/SlackWorkspaces/home`), an Aura-backed page with
  **no** public Connect/REST mirror (verified: `slackbridge/connections` is CONNECTED-only; the
  `slack-connect-api` Connect surface is reCAPTCHA/Web-to-Lead only — neither lists pending connections).
  Report "no activated connection visible via API yet", point the user at that Setup page to confirm the
  pending state, then run the guided approval below.

**Limits of the API here:** `/connect/slackbridge/connections` only *reads*. There is **no**
approve/activate write endpoint. The sibling `/connect/slackbridge/team/{teamId}/user-mappings` route
`404`s in a verified org — rely on `/connections`. The `SlackTeam` / `SlackAppAuthorization` /
`SlackTeamUserAuthorization` entities show `IsQueryable:true` in `EntityDefinition` but return
`INVALID_TYPE "not supported"` on both the Data and Tooling `query`/`describe` (Slack-package internal
entities) — do **not** try to SOQL them. `/connect/slack*` (non-bridge) is only reCAPTCHA keys +
Web-to-Lead settings, not connection management.

## Approve the connection (guided UI — no API)

Point the user to (substitute their My Domain host):

```text
https://<myDomain>.salesforce-setup.com/lightning/setup/SlackWorkspaces/home
```

or **Setup → Manage Slack Connection**. Then:

1. Find the pending connection (Status *"Waiting for approval"* / similar).
2. Under **User Account Mapping / User configuration**, select the **Salesforce Mapping Field**.
   **Default to `Email`** (matches `User.Email` to the Slack user's email — simplest, most common)
   unless the org authenticates via SAML SSO, in which case **`SAML NameID`** is the stable link. If
   unsure for a SAML org, ask — do not guess.
3. Tick terms-and-conditions, then **Approve**.

After approval the connection shows **Approved Connection** with the chosen mapping (e.g. *Email →
email*), then typically reads **"Waiting for activation by Slack admin"** — that's part 3, the final
Slack-side activation. Display this verbatim (Owners / Salesforce-admin system role in Slack can
activate):

```text
Last part — activate the connection back in Slack (Slack desktop app):
  1. Click your workspace name in the sidebar.
  2. Hover over Tools & settings, then click Manage Salesforce organisations.
  3. Select the pending connection.
  4. Review the connection details, then click Activate.
```

The Salesforce side is done once **Approved**; the Slack-side activation is the user's to perform.

> **No approve-API — do not fake it.** Reading status via `/connect/slackbridge/connections` is real;
> approving the connection and setting the org-wide mapping field are genuinely UI-only. Navigate the
> user there and hand them the exact clicks — don't invent a `/connect/slack…` approve call.
