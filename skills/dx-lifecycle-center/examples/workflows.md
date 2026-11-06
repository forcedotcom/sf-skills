# Lifecycle Center Examples

Worked prompts, grouped by operation (`SKILL.md`, Operations). Listing, status checks, and polling are **read-only**. Connecting and deploying change an org, so they wait for the user's confirmation first (a validate run does not change the target).

---

## A. List orgs

**A1. "Show the list of connected orgs I can deploy to."**

```bash
bash scripts/resolve-environment.sh my-dev-org
```

Run the resolver with `--check-sessions`. Reply with the table of usable orgs, the action buttons (Sync / Re-sync / Refresh, and **Sync all N** when two or more rows need it), the one left-out line when some rows are `needs-signin` or `retired`, and the closing sentence (`references/list-orgs.md`, section 4). There is no status column. The Lifecycle Center org is not part of the deploy targets. The list never syncs by itself.

**A2. "What org am I in?"**

Answer from the `source` block: alias, username, URL, and org id. Nothing else.

**A3. The query fails because the session expired.**

The script reports "query failed, not an enablement problem". Say the error plainly and tell them to reconnect the source org (Reconnect prompt in Builder Central, or `sf org login web --alias "<alias>"` on a local CLI), then try again. Never say DX Inspector is disabled.

**A4. The query fails because DX Inspector is off.**

The script reports "DevOps Center not enabled or no access". Reply only: "DX Inspector isn't enabled for this org or user, so there are no environments to list or deploy to. An admin needs to enable it." Stop.

**A5. "Show my DevOps Center orgs."**

The phrase is plural, so it is not the Lifecycle Center org. List the environments (A1). The hub appears only as its labelled row, when connected.

**A6. Org connected in DX Inspector, not in Builder Central.**

The row is listed (the list reads DX Inspector environments) but the resolver says `needs-sync`: no workspace CLI alias exists. The row gets a **Sync `<name>`** button. A click sends `Sync workspace access for <name>`, which runs the sync procedure (`references/connect-org.md`, *Sync workspace access*): one PATCH with `?registerWorkspaceAlias=true`, no sign-in, a check after about 5 seconds, then the list again.

**A7. "Sync all" with a mix of states.**

Three rows: `QA` needs-sync, `UAT` needs-refresh, `Prod` ready. Buttons: **Sync all 2**, **Refresh UAT**, **Sync QA**, **Re-sync Prod**. Sync all runs QA then UAT, one PATCH each and never in parallel, and reports one line each. A failure on one does not stop the other.

**A8. Name clash.**

An alias named `UAT` already points at a different org, so the row is `alias-conflict` and gets **Fix name UAT**. Do not PATCH: it would overwrite the other org's alias. Offer `sf alias unset UAT` then a sync, or connecting under another name.

**A9. The user replies with an action.**

The actions under the table are plain text. A reply such as `Sync DevSand` or `Sync all 3` is the confirmation: run the sync procedure for those rows, then show the list again.

---

## B. Connect an org

**B1. "Connect a new sandbox."**

1. Ask for the environment name. The type is `SANDBOX`; confirm it.
2. Check the org is not already connected (`references/connect-org.md`, Step 0).
3. After the user confirms, `POST /connect/devops/environment`.
4. Show the sign-in as in `connect-org.md` Step 2 and wait for **done**. Never say a browser was opened.
5. `PATCH /connect/devops/environment/<id>?registerWorkspaceAlias=true --body '{}'` (the CLI rejects a PATCH with no body), then list again and confirm the new row shows its URL and org id (if the resolver reports `needs-sync`, wait about 5 seconds once and check again; if it still does, say the org is connected and deployable but has no CLI alias here).

**B2. "Connect https://mydomain--qa.sandbox.my.salesforce.com."**

The host contains `.sandbox.`, so the type is `SANDBOX` without asking. Ask only for the environment name.

**B3. "Connect my org."**

The type is not decided by anything the user said. Ask: "Is it a sandbox or scratch org, a production org, or an OrgFarm org?" Never default. A scratch org is handled exactly like a sandbox (`SANDBOX`).

**B4. "Connect the org I'm already in."**

The identifier is the source org. Say it cannot be connected as its own deploy target and ask which other org they mean.

**B5. The environment exists but was never finished.**

The row shows as not authenticated. Do not POST again. Get a fresh link with `GET /connect/devops/environment/<id>`, wait for **done**, then PATCH once.

**B6. What the user sees while connecting.**

Sign-in (Step 2), a heading, one line of instructions, and a single **Sign in to `QA`** link that opens the login page:

> **Connect `QA`**
>
> Sign in with the user DX Inspector should act as, and approve access. Then come back here and reply **done**.
>
> `[ Sign in to QA ]`

The link is the full `redirectUrl`, also repeated once as "Link not working? Copy it".

Connected (Step 5):

> **✅ `QA` is connected**
>
> | Org | Type | Status |
> |---|---|---|
> | `mydomain--qa.sandbox.my.salesforce.com` | Sandbox | Ready to deploy to |

The Lifecycle Center org uses the same two layouts with its own heading, button text, and a Hub type column.

**B7. "sf command failed: Session expired or invalid" on `--target-org "QA"`.**

Run the sync procedure for `QA`: resolve the row from the alias, PATCH once with `?registerWorkspaceAlias=true`, check after about 5 seconds, then retry the command once. If the PATCH fails with 401 or 403, the stored sign-in is stale: show a fresh sign-in link, wait for **done**, PATCH once. If the alias is not a DX Inspector environment, offer to connect it; do not PATCH anything. Never retry with another alias or `default-org`.

**B8. The PATCH times out.**

`TARGET_ORG_AUTHENTICATION_TIMEOUT` (408/504) is transient. Wait about 10 seconds and PATCH once more. If it times out again, say "`QA` didn't respond in time. Try again in a few minutes." Do not show a sign-in button and do not call the credential stale.

**B9. Sync succeeds but the alias never appears.**

The PATCH returns success, yet the resolver still says `needs-sync` after one repeat. Registration is best effort on the server: the feature may be off for the org, no workspace may be running, or the name has spaces (Core may still skip those) or is `default-org`. Say the org is connected and deploys work, but its CLI alias isn't available here. Stop; do not loop.

**B10. Environment name with a space.**

"Connect `My UAT`." Accept `My UAT` as is. If the sync leaves it `needs-sync`, Core skipped the spaced name: say the org is connected but has no CLI alias, and offer `MyUAT` only as an optional rename. Every command uses `--target-org "My UAT"`.

---

## C. Lifecycle Center org

**C1. "Connect me to the hub org."**

1. "Hub org" is an ambiguous name, so ask: "Do you mean the Lifecycle Center org (the Lifecycle Center hub)?" ("Connect the Lifecycle Center org" is a certain name: skip the question.)
2. On yes, check the credential. If it is configured, reply only: "The Lifecycle Center org is already configured." Stop.
3. If it is not configured, confirm, create the credential, and give the login link labeled **Connect to Lifecycle Center org** (`references/connect-org.md`, hub mode).

**C5. "connect to lifecyclecenter org", "lifecycle-center", "connect lifecycle_center".**

These are spelling variants of the same name. Normalize (lowercase, drop spaces and punctuation), find `lifecyclecenter`, and handle it as C1 without asking which org is meant.

**C6. Wording variants of the other operations.**

After normalizing, these route the same way as the plain phrase: "Pls push AccountService into my QA-sandbox", "ship my flows to prod", "publish AccountService to my QA sandbox", "deployment to org-farm env", "dry run to my sandbox" → **D**. "Hook up a new scratch-org", "add sandbx", "sign in to prod", "set up an orgfarm env" → **B** (scratch and `sandbx` are `SANDBOX`, prod is `PRODUCTION`). "which envs can I use", "show linked orgs", "where can I deploy" → **A**.

**C2. "Is the Lifecycle Center org connected?"**

Check the credential. Configured: "The Lifecycle Center org is already configured." Not configured: "The Lifecycle Center org is not configured. Want me to connect it?"

**C3. "Deploy AccountService to the Lifecycle Center org."**

Make no API call. Ask: "Do you mean the Lifecycle Center org, or a different org?" For the Lifecycle Center org, explain that a deploy cannot go there because it is the Lifecycle Center hub, and offer to connect an org as a regular deploy target. For a different org, ask which and continue at `references/deploy.md`, Step 2.

**C4. "Why isn't the Lifecycle Center org in my list?"**

Say it is the Lifecycle Center hub, kept separate from deploy targets, and is never a deploy target.

---

## D. Deploy

**D1. "Deploy AccountService to https://mydomain--mysandbox.sandbox.my.salesforce.com."**

```bash
bash scripts/resolve-environment.sh my-dev-org https://mydomain--mysandbox.sandbox.my.salesforce.com
```

- `matched` and `selectable`: confirm the row back with name, URL, and org id, build the request, show the Step 4 confirmation, then submit.
- `not-connected`: say so and offer to connect it, carrying the URL into the connect flow (D2).

The same call works with an alias (`my-sandbox`), an org id (`00D5g000001AbCd`), or an environment name (`MySandbox`).

**D2. Deploy to an org that is not connected yet.**

**User prompt:** "Deploy AccountService to my QA sandbox."

1. The lookup says `not-connected`. Offer to connect it. The user agrees.
2. Run the connect flow (B1). When it finishes, say: "`QA` is now connected. I'll continue deploying `AccountService` to it."
3. Go straight to the Step 4 confirmation. Nothing is deployed until the user says yes.

**D3. "Deploy."**

Make no API call. Ask one question: which components to deploy. Then ask for the target.

**D4. "Validate AccountService against production," then quick deploy.**

State what you will validate, then submit with `"isCheckDeploy": true` (`references/request-body.md`), then:

```bash
bash scripts/poll-deploy-status.sh <requestId> "my-dev-org" 10 100
# Exit codes: 0 succeeded, 2 failed or not found, 3 timeout, 1 usage or call error (4 only with --once)
```

On success, report the validation id from `metadata.deployId` and offer a quick deploy with it. For the quick deploy, send only `isQuickDeploy` and `checkDeployIdentifier`. If it is still running after 2 minutes, see D9; never resubmit.

**D5. "Check request `<requestId>`" or a `requestId` from earlier.**

Skip the component and target steps. Poll once:

```bash
bash scripts/poll-deploy-status.sh --once <requestId> "my-dev-org"
# Exit 4 means still processing: report the status and step
```

**D9. The deploy takes more than 2 minutes.**

The poll exits `3`. Reply: "Your deploy is still running. Request id: `<requestId>`. Send me this id and I'll check its status." Stop polling. When the user sends the id, run `bash scripts/poll-deploy-status.sh --once <requestId> "my-dev-org"` and report the status in plain language.

**D8. The user gives only an id starting `0Af`.**

It is a validation id, not a `requestId`: never poll it. Ask whether to quick deploy it and to which target, then show the quick-deploy confirmation (`references/deploy.md`, Step 4).

**D6. The user names two targets.**

Deploy to the first, report, then ask before starting the second. Each target gets its own confirmation.

**D7. The target answers `Bad_OAuth_Token` or `TARGET_ORG_SESSION_EXPIRED`.**

The stored login for that environment is stale. Say so, reconnect that environment (`references/connect-org.md`, repair path), and ask before trying the deploy again.

### A10. Org connected by another user

User: "list my orgs". The resolver returns `UatOrg` with `userAuth: notConfigured` (`needs-my-signin`) and `DevSand` as `needs-sync`.

Reply: the table, then buttons **Sign in as me: UatOrg** and **Sync DevSand**, and the line "1 org was connected by someone else; sign in to use it." No Sync button for UatOrg, and it is not in Sync all. On the sign-in click, run the repair path (fresh link, login as this user, PATCH once), then rebuild the list.
