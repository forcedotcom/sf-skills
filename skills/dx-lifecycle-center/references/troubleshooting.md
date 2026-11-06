# Troubleshooting: DX Inspector org connection

Explain each problem to the user in plain language. Never echo raw JSON or tokens. Do not retry a failing call in a loop.

| Symptom | Likely cause | Fix |
|---|---|---|
| Deploy POST returns `TARGET_ORG_ENVIRONMENT_CREATION_FAILED:Invalid org type` | `orgType` is not valid | Use `PRODUCTION`, `SANDBOX`, or `ORGFARM`. `envName` must contain at least one letter. |
| Hub POST returns `400 namedCredentialType is not supported.` | Typo or wrong case in the type | Use one of `ORG_TO_ORG`, `ORG_TO_SANDBOX_ORG`, `ORG_TO_ORGFARM_ORG`. |
| POST returns 403 or "insufficient access" | User lacks DevOps API access in the dev org | Assign the DevOps Center permissions in the dev org. The user needs *Customize Application*. |
| POST succeeds but `redirectUrl` is empty | Setup or URL generation failed on the server; the errors were swallowed | **Hub:** check status; if the EC or NC exists, re-POST once. **Deploy:** the row already exists, so do not POST again (it would insert a second row). Get a fresh link with `GET /connect/devops/environment/<id>`, or delete the row (below) and start over. If it is still empty, tell the user setup failed server-side and stop. |
| Login page is `login.salesforce.com` but the target is a sandbox, or the reverse | Wrong `namedCredentialType` | **Deploy:** `DELETE /connect/devops/environment/<id>` (removes the NC, EC and row), then POST again with the correct `orgType`. **Hub:** delete the NC and EC in Setup, then re-run with the correct type. |
| OAuth page shows an error or loops back | The browser has no dev-org session, or the user denied access | Ask the user to sign in to the dev org in that browser, then give a fresh link (deploy: `GET /connect/devops/environment/<id>`; hub: re-run Step 1). Do not run `sf org open`. |
| EC principal still `NotConfigured` after the user says they're done | The login didn't finish, or a different Salesforce user completed it | The token is per user, so the same dev-org user must do the login. Give a fresh link (deploy: `GET /connect/devops/environment/<id>`; hub: re-run Step 1). |
| User can't use the credential | Missing **Access DevOps Center Named Credentials** (`AccessDevOpsCenterNamedCredentials`) | Assign that permission set to the user in the dev org. |
| Hub PATCH returns `404 Named credential does not exist` | POST never created the NC, or the name differs | Re-check the exact name (case-sensitive) and re-run Step 1. |
| Hub PATCH returns `DOCE_CONNECTION_UPDATE_FAILED` | The `userinfo` callout failed, usually because the OAuth token is missing or expired | Confirm the principal is `Configured`, then re-run Steps 1–4. The user's saved DX Inspector selections were cleared, so they must pick them again. |
| Deploy environment PATCH returns `TARGET_ORG_AUTHENTICATION_TIMEOUT` (408/504) | The target org or its login service did not answer in time. This says nothing about the credential | Wait about 10 seconds and PATCH once more. If it times out again, tell the user the org didn't respond and to try later. Do not give a sign-in link and do not delete or recreate anything. |
| Deploy environment PATCH returns `TARGET_ORG_AUTHENTICATION_STATUS_CHECK_FAILED` (401/403) | The login is missing, expired, or revoked | Confirm the principal is `Configured` and the `id` is the POST's. Give a fresh link and PATCH once. Do not loop. |
| Deploy environment PATCH returns `TARGET_ORG_UNKNOWN_ERROR` (includes "Environment record not found" and "does not have a named credential") | The id is wrong, or the connect never finished | Re-resolve the id from the environment list. If the row has no credential, use the repair path. Do not loop. |
| PATCH `calloutUrl` or `orgUrl` is still a login host | Unexpected `userinfo` response | Stop and report. Do not hand the NC to deploy. |
| Hub mode: `doceConnectionType` fails | The hub user lacks **DevOps Center User** | Assign the permission set in the Lifecycle Center org, then re-run the check. |
| Deploy: `TARGET_ORG_SESSION_EXPIRED` or `Bad_OAuth_Token` | The target refresh token was revoked or expired. A stale token is not visible in the environment list; it only shows at deploy time | Repair: fresh link from `GET /connect/devops/environment/<id>`, user logs in, PATCH once. |
| Connected, but `sf ... --target-org "<name>"` says the alias is unknown | The alias POST is best effort and its failure is swallowed (no running workspace, workspace still booting past the retries, or the environment name was blank, had spaces, or was `default-org`) | Repeat the connect PATCH with `?registerWorkspaceAlias=true` and `--body '{}'` once, then re-check with `resolve-environment.sh`. If it is still missing, say the org is connected and deploys still work, and stop. |
| `sf` with the alias says `Session expired or invalid` (also `INVALID_SESSION_ID`, `RefreshTokenAuthError`) | The token the workspace holds is short-lived and was not refreshed. This is the workspace login, not the DX Inspector credential | Map the alias to its environment, say "Your workspace login to `<name>` expired", repeat the same PATCH once (no browser needed), then retry the failed command once. If the PATCH fails on auth, the DX Inspector login is stale: repair path (fresh sign-in link, login, PATCH). Never retry with another org's alias or `default-org`. |
| Environment shows `alias-conflict` | An `sf` alias with the environment name already points at a different org in this workspace. Repeating the PATCH would overwrite that alias | Do not repeat the PATCH. Ask the user to remove or rename the other alias (`sf alias unset "<name>"`), or reconnect under a different name. |
| Environment shows `unauthenticated` (empty `OrgUrl` or `OrgIdentifier`) | The connect never finished: POST ran but login or PATCH did not | Same repair: fresh link, login, PATCH once. Do not POST again. |
| `Doce Hub Environment` row is missing from the environment list | By design: the resolver drops the hub row (credential `ALMDevOpsCenterHub`, empty `OrgUrl`) because it is the Lifecycle Center hub, not a deploy target | Nothing to repair. To deploy to that org, connect it as a deploy target with the Environment API. |
| Environment shows `expired` | `IsExpired` is set when an environment is retired or replaced by a swap; it is not an OAuth expiry | Do not repair it. Pick another environment or connect a new one. |

## Starting over

**Deploy target:** `DELETE /connect/devops/environment/<id>` (confirm with the user first). It removes the Named Credential, External Credential, and the `DevopsEnvironment` row. Do not delete credentials in Setup: that leaves an orphaned row that still looks selectable.

**Hub:** delete both the **Named Credential** and the **External Credential** named `ALMDevOpsCenterHub` in Setup → Named Credentials (and the External Credentials tab), and run the skill again.

For the hub, the **Remove DevOps Center Connection** option in DX Inspector does the same teardown.

## Org connected in DX Inspector, not in Builder Central

An environment connected through the DX Inspector UI (Lifecycle Center) has a `DevopsEnvironment` row and a credential but no workspace alias. It appears in the list with a **Sync** button; `sf ... --target-org "<name>"` fails until it is synced (`connect-org.md`, *Sync workspace access*). No sign-in is needed while the credential is `Configured`.

## Alias registration does not happen even after a sync

The PATCH succeeds but the alias never appears. The causes are on the server and invisible to the CLI: the feature gate is closed for the org, no workspace is running for the user, or the environment name is blank, contains whitespace, or is `default-org` in any casing. Repeat the sync once. If it still shows `needs-sync`, say the org is connected and deployable but has no CLI alias here, and stop.

## Org listed, but connected by another user

| Symptom | Cause | Fix |
|---|---|---|
| Row shows `needs-my-signin` (`userAuth: notConfigured`) | DX Inspector environments are shared by everyone with access to the dev org, but the OAuth login is per user and this user has not signed in | Use the "Sign in as me" button: fresh sign-in link, log in **as this user**, PATCH once (repair path in `connect-org.md`). Do not sync first |
| Sync or deploy returns 401/403 on an org someone else connected | Same cause, found late | Treat as `needs-my-signin` |
| `userAuth: unknown` on every row | The credential status call failed (API version, permission, network) | List as usual; if a click then fails with 401/403, go to the row above |
