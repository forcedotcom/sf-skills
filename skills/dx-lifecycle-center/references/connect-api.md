# DX Inspector Named Credential Connect API

All calls target the **development org** (where DX Inspector runs). This skill requires API v67.0 or later. The caller needs DevOps common API access (`USER_HAS_DEVOPS_COMMON_API_ACCESS`). Portal users are rejected.

Both calls are part of the DevOps Center Connect API (v67.0).

---

## `/connect/devops/environment` (deploy targets)

Creates the NC, the EC, **and the `DevopsEnvironment` row** that simple-deploy requires. `setupNamedCredential` never creates the row.

Part of the DevOps Center Connect API (v67.0).

| Method | Path | Body | Result |
|---|---|---|---|
| POST | `/connect/devops/environment` | `{envName, orgType, isDevEnv?, replaceEnvironmentId?}` | `{id, name, namedCredential, externalCredential, redirectUrl, orgType, isDevEnv}` |
| PATCH | `/connect/devops/environment/{id}` | optional query `registerWorkspaceAlias=true` (connect only) | `{id, organizationId, orgUrl, status, message}` after the login. `name` and `namedCredential` are not returned; keep them from the POST |
| GET | `/connect/devops/environment/{id}` | none | The environment, with a fresh `redirectUrl` pinned to the row's org URL: use it for the repair link |
| DELETE | `/connect/devops/environment/{id}` | none | Removes the NC/EC and the row |

- `envName` and `orgType` are required. `orgType` is `PRODUCTION`, `SANDBOX`, or `ORGFARM`; it maps to `ORG_TO_ORG`, `ORG_TO_SANDBOX_ORG`, `ORG_TO_ORGFARM_ORG`.
- The NC/EC name is generated as `<letters-of-envName>_<epochMillis>`.
- POST sets up the NC/EC, builds the OAuth `redirectUrl`, then inserts the row. The user logs in at `redirectUrl`; PATCH then reads `/services/oauth2/userinfo` through the NC, rewrites the callout URL to the real My Domain, and stores `organizationId` and `orgUrl` on the row.
- Errors are prefixed `TARGET_ORG_ENVIRONMENT_CREATION_FAILED`, `TARGET_ORG_AUTHENTICATION_STATUS_CHECK_FAILED` (401/403), `TARGET_ORG_AUTHENTICATION_TIMEOUT` (408/504), or `TARGET_ORG_UNKNOWN_ERROR`.

---

## `/connect/devops/setupNamedCredential` (hub)

The POST and PATCH take the same flat JSON body:

```json
{ "namedCredentialName": "<name>", "namedCredentialType": "<DevopsAuthType>" }
```

Use `ORG_TO_ORG`, `ORG_TO_SANDBOX_ORG`, or `ORG_TO_ORGFARM_ORG`. Any other value returns `400 namedCredentialType is not supported.`

### POST: create the credential and get the login URL

Server behavior (`setUpNamedCredentialsForDevops`, then `getOAuthCredentialAuthUrl`):

1. **External Credential.** If missing, it creates one with:
   - developer name and label set to `<name>`,
   - protocol **OAuth**,
   - `ExternalAuthIdentityProvider` set to the platform standard IdP for the type:

     | Type | IdP |
     |---|---|
     | `ORG_TO_ORG` | `sfdc.ALMDevOpsOrgStandardIdP` |
     | `ORG_TO_SANDBOX_ORG` | `sfdc.ALMDevOpsSandoxOrgStandardIdp` |
     | `ORG_TO_ORGFARM_ORG` | `sfdc.ALMDevOpsOrgFarmOrgStandardIdp` |

   - `AdditionalRefreshStatusCode` set to `403`,
   - one **PerUserPrincipal** (sequence 1).

   The IdP uses the authorization code flow with PKCE. The client id and secret come from the platform secrets store, so no per-org connected app is needed.
2. **Named Credential.** If missing, it creates a `SecuredEndpoint` NC linked to the EC, with:
   - `generateAuthorizationHeader=true`, `allowMergeFieldsInHeader=true`, `allowMergeFieldsInBody=false`,
   - a **placeholder** callout URL (the login host),
   - headers `target_org_auth_token: Bearer {!$Credential.OAuthToken}` and `x-salesforce-region`.
3. **Principal access.** Grants the EC principal to the permission set `AccessDevOpsCenterNamedCredentials` ("Access DevOps Center Named Credentials").
4. **Response.** Returns `{"redirectUrl": "<OAuth start URL>"}`, HTML-escaped, so you must replace `&amp;` with `&`.

The POST is **idempotent**: existing NCs and ECs are reused. Errors inside steps 1–3 are **logged and swallowed**, so a "successful" POST can still leave things half-created. Always verify with *Check credential status*. An empty `redirectUrl` means URL generation failed.

Error wrapping: `DOCE_AUTHENTICATION_FAILED:<msg>` or `DOCE_AUTH_UNKNOWN_ERROR:<msg>` (500), and `INVALID_INPUT` (400).

### Workspace alias registration (`registerWorkspaceAlias=true`)

After the PATCH commits, Core resolves the running workspace (the local container when the local-workspace gate is open, else the user's remote workspace and its proxy token), gets a fresh access token and instance URL from the Named Credential, and posts them from a background thread:

```text
POST {workspaceUrl}/auth-service/v1/auths/
{ "alias": "<envName>", "accessToken": "...", "instanceUrl": "...", "setDefault": false }
```

It retries up to 10 times on 502, 503, or 504 while the workspace boots and stops at once on any other error. Failures are logged and swallowed, so the PATCH response never shows them. The auth service validates the token against the org, stores the login in `~/.sfdx/<username>.json`, and maps the alias; an existing username just gets its token updated. To check from inside the workspace (never print the token):

```bash
sf alias list
sf org list --json            # the environment name appears as an alias
```

Builder Central itself registers only the signed-in org, as `default`. It does not create aliases for DevOps environments, so this PATCH is the only way a connected environment gets one. A token that has expired shows as `Session expired or invalid` on `sf`: repeat the PATCH once to overwrite it.

Two logins can go stale, and they are fixed differently:

| Login | Held by | Stale shows as | Fix |
|---|---|---|---|
| Workspace alias token | The workspace auth-service (`~/.sfdx`) | `sf` says `Session expired or invalid`; `resolve-environment.sh --check-sessions` reports `needs-refresh` | Repeat the PATCH once (no browser) |
| DX Inspector credential | The Named Credential and External Credential in the source org | Only at deploy time (`Bad_OAuth_Token`, `TARGET_ORG_SESSION_EXPIRED`), or the PATCH itself fails on auth | Repair path: sign-in button, login, PATCH |

The PATCH reads its token from the Named Credential, so a stale DX Inspector credential can never be fixed by repeating it; that is why a PATCH that fails on auth moves to the repair path.

### PATCH: finalize after the OAuth login

`/connect/devops/environment/{id}` also accepts the optional query `registerWorkspaceAlias=true`. When set, after the steps below Core registers the environment name as an org alias in the caller's running Builder Central workspace (same auth store as `default-org`). It is best effort and never changes the response or fails the PATCH.

Server behavior (`updateNamedCredentialsForDevops`):

1. Returns `404 Named credential does not exist: <name>` if the NC is missing.
2. Calls `callout:<name>/services/oauth2/userinfo` and takes the org URL from `urls.rest`. **This requires the OAuth token from the browser login.**
3. Pre-warms the remote API version cache (`GET /services/data`).
4. Rewrites the NC callout URL to the org URL. It keeps the label, type, callout options, and EC link.

The response is `{"namedCredentialName": "<name>", "calloutUrl": "<org url>", "redirectUrl": null}`.

On failure it returns `DOCE_CONNECTION_UPDATE_FAILED:<msg>` and **also clears the user's saved DX Inspector selections**. Unexpected failures return `DOCE_AUTH_UNKNOWN_ERROR:<msg>`.

---

## Check credential status

Use the standard Named Credentials Connect API in the dev org:

```bash
# External credential and its per-user principal status
sf api request rest "/services/data/v<ver>/named-credentials/external-credentials/<name>" \
  --target-org "<dev-org-alias>"
# → principals[].principalType == "PerUserPrincipal", principals[].authenticationStatus == "Configured" | "NotConfigured"

# Named credential callout URL
sf api request rest "/services/data/v<ver>/named-credentials/named-credential-setup/<name>" \
  --target-org "<dev-org-alias>"
# → calloutUrl  (placeholder login host before PATCH, org My Domain after); calloutStatus "Enabled"

# List named credentials (diagnostics only; deploy targets come from DevopsEnvironment)
sf data query --use-tooling-api \
  --query "SELECT DeveloperName FROM NamedCredential ORDER BY CreatedDate DESC" \
  --target-org "<dev-org-alias>" --json
```

Tooling `NamedCredential.Endpoint` is `null` for these `SecuredEndpoint` credentials, so always read `calloutUrl` from the `named-credential-setup` GET. DevOps-created target credentials match `<letters>_<millis>`. Never build the deploy-target list from this query.

A missing credential returns `NOT_FOUND` ("We couldn't access the credential(s)... might not exist") on either GET. That means the credential does not exist, or the user lacks access to it. `authenticationStatus` is reported **for the running user**: the token is per user, so another user's login does not count.

| EC principal | NC callout URL | State |
|---|---|---|
| — (404) | — (404) | Not created. Run POST. |
| `NotConfigured` | login host | Created, but login not done. Run browser login, then PATCH. |
| `Configured` | login host | Login done, PATCH missing. Run PATCH. |
| `Configured` | org My Domain | Ready. |

---

## How the flows consume the credential

| Flow | Dev-org endpoint | Credential use |
|---|---|---|
| Deploy | `POST /connect/devops/simple-deploy/deploy` with `{"namedCredential": "<name>", ...}` | Calls `userinfo` through the NC (refreshing the token if needed), then forwards the target token and instance URL to the deploy service. `TARGET_ORG_NAMED_CREDENTIAL_NOT_AUTHENTICATED` means the principal is not configured. |
| Hub type | `GET /connect/devops/doceConnectionType` | Reads the hub `DevHubSettings` through `ALMDevOpsCenterHub` and returns `CORE` or `MANAGED_PACKAGE`. |
