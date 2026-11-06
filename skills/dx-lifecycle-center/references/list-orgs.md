# List connected orgs (Operation A)

Shows the orgs that can receive a deploy: the **DX Inspector environments** stored in the source org. The same lookup resolves a target the user names (alias, URL, org id, or name) for Deploy and Connect.

The targets are the DX Inspector environments, **not** the orgs authorized on this machine. Never build the list from `sf org list` or local aliases: an org can be authorized locally yet not connected, and the reverse.

## 1. Run the resolver

```bash
bash scripts/resolve-environment.sh "<source-org-alias>" ["<identifier>"] [--check-sessions]
```

Add `--check-sessions` when showing the list (section 4). It probes each workspace login that belongs to a listed environment with one cheap query and fills `session`. Leave it off when only resolving a target for Deploy or Connect: the session probes are skipped there (the per-user sign-in check and the hub read still run, in parallel with a timeout), so that path needs no extra org calls.

`<source-org-alias>` is the alias the user named, else the default org from `sf org display --json`. Pass `identifier` exactly as the user gave it. It accepts:

| The user gives | Example |
|---|---|
| Environment name | `MySandbox` |
| Local `sf` alias | `my-sandbox` |
| Org URL (My Domain, setup, or lightning host) | `https://mydomain--mysandbox.sandbox.my.salesforce.com` |
| Org id (15 or 18 characters) | `00D5g000001AbCd` |

The script runs `SELECT Id, Name, NamedCredential, OrgType, IsExpired, OrgUrl, OrgIdentifier FROM DevopsEnvironment ORDER BY Name` and prints one JSON document:

- `source`: `alias`, `username`, `orgId`, `instanceUrl` of the source org.
- `environments[]`: each row with `state` (`selectable`, `expired`, `unauthenticated`) and the workspace fields. `workspaceAlias` is `registered`, `missing`, or `unknown`, and `workspaceAliasName` is the `sf` alias that holds the login (named like the environment, or any alias on the same org). `session` is `valid`, `expired`, or `unknown` (only with `--check-sessions`; `unknown` also covers a probe that timed out). `userAuth` is `configured`, `notConfigured`, or `unknown`: whether the **current user** has signed in to that environment (rows are shared by everyone with access to the dev org, the login is per user; `unknown` means the check failed, never treated as not signed in). `aliasConflict` is `true` when an alias named like the environment points at a different org. `readiness` combines them: `ready`, `needs-sync`, `needs-refresh`, `alias-conflict`, `needs-my-signin`, `needs-signin`, `retired`, or `unverified`. `needs-my-signin` wins over every sync state: the row is connected, but not by this user. Aliases are never used to choose a target.
- With an identifier: `matchStatus`, `matches[]`, `match`, and `sourceMatched`.

The Lifecycle Center org's own row is never in `environments[]`. The resolver reports it separately as `hub` (`label`, `url`, `userAuth`, `workspaceAlias` as `registered`, `missing`, `conflict` or `unknown`, `cliAlias`, `isDeployTarget: false`), present only when the hub is connected: its row exists or its credential is readable (see `hub-org.md`).

## 2. If the script fails

It exits `1` and prints one reason on stderr. Say only what the reason supports:

| Script says | Tell the user | Then |
|---|---|---|
| `DevOps Center not enabled or no access` | "DX Inspector isn't enabled for this org or user, so there are no environments to list or deploy to. An admin needs to enable it." | Stop. Do not run another query, do not fall back to `sf org list`, and do not offer a deploy. |
| `query failed, not an enablement problem` | The error in plain words (often an expired session). | Tell them to reconnect the source org (in Builder Central use the Reconnect prompt; running the CLI locally, `sf org login web --alias "<alias>"`), then try again. Never say DX Inspector is disabled. |
| `unexpected query result` | The environment lookup returned something unreadable. | Report that and stop. Do not guess a list. |
| `cannot read source org` | The source org is not authorized on this machine. | Ask which org they build in. If it is not authorized, reconnect it the same way as above, then start again. |
| `jq required` | `jq` is missing from the environment. | Report it and stop. |

## 3. Read the match (only when an identifier was passed)

**First check `sourceMatched`.** If it is `true`, the identifier is the source org (this also covers a row with `isSource: true`): say it cannot be its own deploy target and ask for a different org. Ignore `matchStatus` in that case.

| `matchStatus` | Do |
|---|---|
| `matched` and `state` is `selectable` | Use that row. Confirm it back with name, URL, and org id. |
| `matched` and `state` is `unauthenticated` | Connect never finished. Offer to finish it (`connect-org.md`, repair path). |
| `matched` and `state` is `expired` | Retired or replaced by an environment swap. Not deployable and not repairable: pick another or connect a new one. |
| `ambiguous` | Show `matches` and ask which one. |
| `not-connected` | Not in DX Inspector. Offer to connect it (`connect-org.md`). If the identifier was an alias, URL, or org id, carry it into the connect flow so only the missing inputs are asked. |
| `none-requested` | No target named: show the list (section 4). |

When the identifier is an alias that is not connected, `sf org display --target-org "<alias>" --json` gives its URL, which sets the `orgType` by the host table in `connect-org.md`. Use the alias as the suggested environment name and still ask the user to confirm the type if the host does not decide it.

## 4. Show the list

Show the orgs the user can use, then say in one line what is left out.

**Table** (columns `#`, `Name`, `Type`, `URL`, `Org id`): one row per environment with `state = selectable`. **Never list the current (source) org.** It is not a deploy target, so leave out any row with `isSource: true` and do not append a row for `source`. Mention the current org only if the user asks about it (section 5).

- **Lifecycle Center row.** When `hub` is present and `hub.userAuth` is `configured`, add one last row: Name `Lifecycle Center (Production Org)`, Type `Production`, URL from `hub.url`, Org id `—`. Follow the table with: "Lifecycle Center (Production Org) is the Lifecycle Center hub. It is not a deploy target." It gets no button and is never in Sync all. If `hub` is null or not `configured`, say nothing about it.
- Always include the `Org id` column. Write `—` for any empty cell.
- **Same org under several names.** Environments are separate connections, so two or more can point at one org (same `Org id`). Keep each row, but add one line after the table: "`<A>`, `<B>` and `<C>` are three connections to the same org (`<Org id>`)." Tell the user this whenever they ask to copy or move something between two of them: it would do nothing or create a duplicate, so offer a genuinely different org instead.
- Never show row ids or credential names. If several rows share a name, tell them apart by URL.
- There is no status column. The state is shown as the **action button** under the table (below), so the user fixes a row with one click instead of reading a status.

**Where the list comes from.** Rows are the DX Inspector environments, so an org connected in DX Inspector (the Lifecycle Center UI) is listed even though it was never connected from Builder Central chat. Such an org has a credential but **no workspace CLI alias**, so `sf ... --target-org "<name>"` fails here until it is synced. An org connected from Builder Central chat gets both the row and the alias. The buttons cover both cases.

**Actions.** Under the table, offer one text action per selectable row, plus the batch action, as a short list. The user replying with the action (or the message shown) is their confirmation. The label depends on `readiness`:

| `readiness` | Button label | Message sent on click | What the click does |
|---|---|---|---|
| `needs-sync` | Sync `<name>` | `Sync workspace access for <name>` | Sync procedure (`connect-org.md`, *Sync workspace access*) |
| `unverified` | Sync `<name>` | same | same |
| `needs-refresh` | Refresh `<name>` | `Refresh workspace access for <name>` | same procedure |
| `ready` | Re-sync `<name>` | `Sync workspace access for <name>` | same procedure (safe: it overwrites the same alias with a fresh token) |
| `alias-conflict` | Fix name `<name>` | `Fix the workspace alias name for <name>` | Do **not** PATCH. Explain the clash and offer `sf alias unset` or a different name (`troubleshooting.md`) |
| `needs-my-signin` | Sign in as me: `<name>` | `Sign me in to <name>` | Per-user sign-in: repair path in `connect-org.md` (fresh link, login as this user, PATCH once). No sync before it; a sync would fail with 401/403 |
| `needs-signin` | Finish sign-in `<name>` | `Finish connecting <name>` | Repair path in `connect-org.md` |
| `retired` | none | | Not repairable; goes in the left-out line |

- When **two or more** rows are `needs-sync`, `needs-refresh`, or `unverified`, add a first button **Sync all N** (message `Sync workspace access for all connected orgs`). The batch runs the sync procedure for each of those rows in turn, one PATCH each, never in parallel, and reports one line per org.
- The source org row has no button.
- **Orgs connected by someone else.** Everyone with access to the dev org sees the same environments, but the sign-in belongs to one user. A `needs-my-signin` row is listed with its "Sign in as me" button, and one line goes after the table: "N orgs were connected by someone else; sign in to use them." Never offer Sync (or include the row in Sync all) for such a row. Do not claim it is unusable: deploys use the signed-in user's credential, so it is not deployable for this user until they sign in.
- No selectable row needs an action: skip the list. Otherwise, if the list would be long, add one sentence after the table naming the rows that need syncing and asking if they want them synced.
- Deploys run through DX Inspector's credential, not the workspace alias, so a row that needs a sync is still deployable. Say so only if the user asks.
- **Never sync by itself while listing.** A list is read-only. The sync runs only after a button click or an explicit request.

After a click the agent runs the procedure, then **shows the list again**, so the user sees the result. The list is rebuilt from a fresh resolver run, not from memory.

**Left-out line** (only if any row is `needs-signin` or `retired`; one sentence, placed after the table): "Not shown as usable: `<name>` (sign-in not finished), `<name>` (retired or replaced)." Details only if the user asks.

**Example** (table, then the button row):

| # | Name | Type | URL | Org id |
|---|---|---|---|---|
| 1 | MySandbox | Sandbox | mydomain--mysandbox.sandbox.my.salesforce.com | 00D5g000001AbCd |
| 2 | QaSandbox | Sandbox | mydomain--qa.sandbox.my.salesforce.com | 00D5g000001QqQq |

The current org (`my-alias`) is not listed. Buttons: **Sync all 2**, **Re-sync MySandbox**, **Refresh QaSandbox**.

Not shown as usable: OldSandbox (retired or replaced).

End the list with exactly this sentence and nothing after it:

> Want to deploy to an org that isn't listed? I can help you connect a new one.

Do not add any other offer, summary, or follow-up. The action buttons are the only addition.

| Situation | Reply instead of the table |
|---|---|
| No environments | "No environments are connected to DX Inspector in `<source-org-alias>` yet." Then the closing sentence. |
| No row has `state = selectable` | "None of the connected environments can accept a deploy right now: <names and reasons>." Then the closing sentence. |

## 5. Current-org details

When the user asks about the current org itself, answer from `source`: alias, username, URL, and org id. Add nothing else.

## Carrying a chosen row forward

For Deploy, take `id` → `targetEnvironmentId` and `namedCredential` → `namedCredential` from the **same** row. The API rejects a mismatched pair. Never deploy to a row whose `state` is not `selectable`.
