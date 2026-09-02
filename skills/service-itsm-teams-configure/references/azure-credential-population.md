# Populating the Azure credentials, inbound SSO, and portal-user access (Step 5 detail)

Reference for `service-itsm-teams-configure` Step 5. Once the org has an external credential named
`MSTeamsSetupClientCredentialsEC` and the user has supplied their Azure **Client ID** and **Tenant
ID** (non-secret identifiers, given in chat) and written the **Client Secret** to a **gitignored
secret file** via the Step 4a copy-paste command (**never ask for the secret in chat**; do NOT use an
`export`-to-env-var route — an interactive `!`-prefix export runs in a different shell than the
agent's tool calls, so the value never reaches the agent), these are the Salesforce-side writes that
populate the outbound Graph credential, the inbound-SSO Auth Provider, and the portal-user access
that make the Teams IT Service / IT Desk apps actually work. Read the secret from that file at write
time (`cat <secret-file>` into an in-memory variable); never print, echo, or log its value, and never
send a literal `$TEAMS_ENTRA_CLIENT_SECRET` token to an API — always resolve it to its actual value
first (see the Secret-substitution note in Step 2). Do all of these yourself — the user's manual
responsibility ends at the Azure admin center.

## Populating `MSTeamsSetupClientCredentialsEC` given a user-supplied client ID/secret

**Once the user supplies the Client ID and Tenant ID (in chat) and the Client Secret is available in
the gitignored secret file (Step 4a — never in chat), write them into
Salesforce yourself via the calls below. Do not respond by telling the user to open Setup and enter
the values manually — that defeats the purpose of this skill.** The user's manual responsibility
ends at the Azure admin center (Step 4a); every Salesforce-side write, including this one, is this
skill's job.

1. Fix the `AuthProviderUrl` parameter (it ships with a literal `{tenant_id}` placeholder):
   ```text
   mcp__headless-360__dispatch(
     method: "PUT",
     url:    "/services/data/v67.0/named-credentials/external-credentials/MSTeamsSetupClientCredentialsEC",
     body:   { /* GET the record first, then re-PUT its full parameters[]/principals[] with
                  AuthProviderUrl set to https://login.microsoftonline.com/<tenant id>/oauth2/v2.0/token */ }
   )
   ```
   This endpoint is full-replace — GET the EC first and mutate, don't send a partial body.
2. Set the principal's client ID + secret (both required together in one call; there is no
   partial-update path for just the client ID):
   **Secret substitution — read this first.** The credential API body is JSON, **not a shell**: it
   does **not** expand any `$TEAMS_ENTRA_CLIENT_SECRET`-style token. Passing such a literal string in
   the body stores that literal text as the OAuth client secret and Graph authentication then fails
   after an apparently-successful configuration. You must read the secret's **actual value from the
   gitignored secret file** (Step 4a) and place that value into `clientSecret.value` at call time. Do
   it with a **non-logging** read — `cat <secret-file>` captured into an in-memory variable, or build
   the JSON body with a small script that reads the file (as done for the `MSTeamsSetupClientCredentialsEC`
   POST) — never `echo`/print it, never place the resolved secret in any text you emit to the user or
   into a log, and delete any temp body file that held it immediately after the call. The `<secret
   value read from the secret file>` placeholder below denotes that resolved value, not a literal to
   send:
   ```text
   mcp__headless-360__dispatch(
     method: "POST",   // or PUT (update-credential) if credentials already exist for this principal
     url:    "/services/data/v67.0/named-credentials/credential",
     body:   {
       "externalCredential": "MSTeamsSetupClientCredentialsEC",
       "principalName": "NamedAuthPrincipal",
       "principalType": "NamedPrincipal",
       "authenticationProtocol": "OAuth",
       "authenticationProtocolVariant": "ClientCredentialsClientSecretBasic",
       // clientSecret.value MUST be the actual secret read from the gitignored secret file (Step 4a)
       // — NOT a literal "$TEAMS_ENTRA_CLIENT_SECRET" token (the JSON body does not expand variables).
       // Read it in memory via a non-logging read (cat the file); never echo it.
       "credentials": { "clientId": {"value": "<client id>"}, "clientSecret": {"value": "<secret value read from the secret file>"} }
     }
   )
   ```
3. Verify: `GET /services/data/v67.0/named-credentials/external-credentials/MSTeamsSetupClientCredentialsEC`
   should show `authenticationStatus: "Configured"`.
4. If `MSTeamsSetupAutomationAccess` (the EC principal's access-gating permission set) is
   unassigned for the running user, assign it via `POST /services/data/v67.0/sobjects/PermissionSetAssignment`
   (`AssigneeId`, `PermissionSetId`) before retrying Step 5 — it auto-provisions but is not
   auto-assigned.

## Populating the `microsoft_auth_provider` Auth Provider (inbound SSO — do NOT skip)

Enabling the Teams feature also provisions a Microsoft-type **Auth Provider** named
`microsoft_auth_provider` (Setup → Identity → Auth Providers), left **empty** (no Consumer Key,
Consumer Secret, or endpoint URLs). This is the **inbound SSO** side — it authenticates employees
logging into the Experience Cloud portal that the Teams IT Service app embeds. It is a *separate
artifact* from the outbound-Graph `MSTeamsSetupClientCredentialsEC` Named Credential, but takes the
**same three values** the user supplied (secret read from the gitignored secret file, never chat). Populate it automatically in the same pass — a previous run
of this skill forgot this step, leaving portal SSO login broken even though the Named Credential
was configured.

**Key constraint (verified):** `AuthProvider.ConsumerSecret` is `createable` but **NOT
`updateable`** on the SObject — so `sf data update` / a Connect PATCH **cannot** set the secret on
the already-provisioned (empty) record, and headless-360 `discover` exposes **no** Connect route
that writes an Auth Provider secret. The working path is the **Metadata API**: `AuthProvider` is a
full MDAPI type whose `<consumerSecret>` round-trips on deploy. Author a source-format file and
deploy it (this sets every field, including the secret, with no UI):

```xml
<!-- force-app/main/default/authproviders/microsoft_auth_provider.authprovider-meta.xml -->
<?xml version="1.0" encoding="UTF-8"?>
<AuthProvider xmlns="http://soap.sforce.com/2006/04/metadata">
    <authorizeUrl>https://login.microsoftonline.com/<TENANT_ID>/oauth2/v2.0/authorize</authorizeUrl>
    <consumerKey><CLIENT_ID></consumerKey>
    <consumerSecret>__SECRET_PLACEHOLDER__</consumerSecret>
    <defaultScopes>openid profile email offline_access https://graph.microsoft.com/.default</defaultScopes>
    <friendlyName>microsoft_auth_provider</friendlyName>
    <includeOrgIdInIdentifier>false</includeOrgIdInIdentifier>
    <providerType>Microsoft</providerType>
    <sendAccessTokenInHeader>true</sendAccessTokenInHeader>
    <sendClientCredentialsInHeader>false</sendClientCredentialsInHeader>
    <tokenUrl>https://login.microsoftonline.com/<TENANT_ID>/oauth2/v2.0/token</tokenUrl>
</AuthProvider>
```

```bash
sf project deploy start --source-dir force-app --target-org <org-alias>
```

**Secret handling:** substitute `<TENANT_ID>` / `<CLIENT_ID>` (non-secret) directly, but inject the
`<consumerSecret>` value **read from the gitignored secret file** (Step 4a) at build time into a
gitignored temp copy under a scratch dir, deploy that, then delete the whole scratch dir. A verified
non-logging way to do the substitution (the secret only ever lives in a transient shell var and the
scratch file, never in emitted text):
```bash
# template has __SECRET_PLACEHOLDER__ where <consumerSecret> should be; <TENANT_ID>/<CLIENT_ID> already filled in
SECRET="$(cat <secret-file>)" perl -pe 's/__SECRET_PLACEHOLDER__/$ENV{SECRET}/' template.xml \
  > force-app/main/default/authproviders/microsoft_auth_provider.authprovider-meta.xml
sf project deploy start --source-dir force-app --target-org <org-alias>
rm -f force-app/main/default/authproviders/microsoft_auth_provider.authprovider-meta.xml   # shred secret-bearing file
```
**Never commit the populated file** and never echo the secret. The secret comes from the gitignored
secret file — not from chat, and not from an env var (the interactive `!`-prefix export does not
reach the agent's shell).

Notes:
- Use the **tenant-specific** `/…/<TENANT_ID>/oauth2/v2.0/…` endpoints, not `/common/` or
  `/organizations/` — single-tenant Azure apps reject the generic endpoints.
- `--metadata-dir` (MDAPI format) proved flaky here ("named in package.xml but not found in zipped
  directory"); the **source-format `--source-dir` deploy is the reliable route** — include a minimal
  `sfdx-project.json` with `sourceApiVersion`.
- `<executionUser>` is optional for a Microsoft SSO Auth Provider (only needed when a registration
  handler runs Apex); it may not bind on deploy and that is fine.
- **Verify** with `sf data query "SELECT ConsumerKey, AuthorizeUrl, TokenUrl, DefaultScopes FROM
  AuthProvider WHERE DeveloperName = 'microsoft_auth_provider'"`. The **Consumer Secret is
  write-only and will not read back** — a null secret in the query is expected, not a failure;
  confirm the ConsumerKey and URLs populated.
- **After populating, give the user the Auth Provider's Callback URL to register in Azure.** (The
  callback URL is not a secret.) The redirect URI the Azure app must trust is the OAuth callback endpoint on the org's My
  Domain: `https://<my-domain>/services/authcallback/microsoft_auth_provider` (get `<my-domain>` from
  `sf org display --json` → `instanceUrl`, or read the "OAuth-Only Initialization URL" from the Auth
  Provider's Salesforce Configuration section in Setup). This is a **manual Azure step** — no
  Salesforce API reaches Azure — so paste the exact URL and tell the user: **portal.azure.com → the
  app registration → Authentication → add a platform → *Web* → add this Redirect URI → Save.**
- **Register the redirect URI under the "Web" platform, NOT "Single-page application" (SPA) — verified.**
  This Auth Provider is a **confidential client**: it does a server-side token exchange using the
  ConsumerSecret. Azure rejects secret-based token requests against a redirect URI registered as SPA,
  so if the callback is added under the SPA platform the login *appears* to start (Salesforce even logs
  a `LoginHistory` "Success" and mints `OauthToken` rows) but the callback round-trip fails at
  `.../services/authcallback/microsoft_auth_provider` with **`OAUTH_APPROVAL_ERROR_GENERIC`**. Moving
  the same redirect URI from the SPA platform to the Web platform in the Azure app fixes it. When you
  emit the callback URL, explicitly tell the user it must go under **Web**, not SPA.
- Optionally also give the Single Logout URL (`https://<my-domain>/services/auth/rp/oidc/logout`) for
  the app's Front-channel logout URL. Without the redirect URI registered on the Azure side, portal SSO
  login fails with a redirect-mismatch error even though the Auth Provider is fully populated.

## Making a portal user resolvable to the signed-in Microsoft user (Username = MS email — verified)

Populating the Auth Provider and its callback is not enough for a person to actually log into the
embedded Experience Cloud portal from the Teams IT Service (Employee) or IT Desk app. When a user
signs in through Microsoft, a custom Apex registration handler bound to `microsoft_auth_provider` —
**`MsTeamsItsmSSOHandler`** (Core module `service-itsm-teams-impl`) — resolves *which* Salesforce user
they are. Its logic (verified against Core source):

```apex
global boolean canCreateUser(Auth.UserData data) { return false; }        // no JIT
global User createUser(Id portalId, Auth.UserData data) {
    String loginValue = data.email;                                       // the Microsoft email/UPN claim
    List<User> users = [SELECT Id FROM User WHERE Username = :loginValue LIMIT 2];
    if (users.isEmpty() || users.size() > 1) return null;                 // 0 or >1 match → no login
    return users[0];
}
```

So the **Microsoft `email`/UPN claim must exactly equal a Salesforce `User.Username`** — not
`User.Email`, not `FederationIdentifier`. Exactly one active user must match; zero matches or a
duplicate both return `null`, and the app then shows **"you don't have access to the Microsoft account
in Salesforce."** There is **one handler / one Microsoft Auth Provider for the whole module** — both
the IT Service (Employee) and IT Desk (Fulfiller) apps use it; the Employee-vs-Fulfiller split lives
only in notification/adaptive-card routing, never in user resolution.

**Do this automatically** (this is a Salesforce-side write — do not defer it to the user): once you
know the Microsoft UPN the person signs in with, ensure the intended portal user's `Username` equals
it. First confirm no other user already holds that Username (a duplicate breaks the match too), then
set it via `PATCH /services/data/v67.0/sobjects/User/<userId>` body `{"Username": "<ms-upn>"}`. In this
session the empPortal user's Username was renamed to the tenant UPN (e.g. `admin@<tenant>.onmicrosoft.com`)
and login then resolved. Note UEL "Unified Employee" users are `UserType=Standard` internal users added
directly as Experience Cloud `NetworkMember`s (ContactId can be null) — they are **not** external
CspLitePortal users; the Username-match rule is the same regardless.

## Granting the portal user API Enabled for the Teams Connect APIs (verified)

Even with SSO resolving correctly, the Teams IT Service (Employee) app calls Connect (Chatter) APIs
on the embedded portal — e.g.
`/empPortal/services/data/v66.0/connect/it-service/permissions/EmployeeApp?networkId=<networkId>`.
If the signed-in user lacks the **API Enabled** user permission, these calls fail with
**`API_DISABLED_FOR_ORG`** ("...or user type") and the browser Network tab shows **403 Forbidden** —
the app UI then fails to load its data even though login itself succeeded.

The managed permission sets the child skills assign (`TeamsForEmployeeUser`, `EmployeeHubEmployeeUser`)
do **not** grant `ApiEnabled`, and being managed-package permission sets they **cannot be edited** — a
Metadata API retrieve reports "cannot be found" and a direct SObject PATCH fails with "invalid record
id." The working fix is to **create a new *unmanaged* permission set with `ApiEnabled` only, deploy it,
and assign it** to the portal user. Do this yourself (Salesforce-side write):

```xml
<!-- force-app/main/default/permissionsets/Teams_Employee_ApiAccess.permissionset-meta.xml -->
<?xml version="1.0" encoding="UTF-8"?>
<PermissionSet xmlns="http://soap.sforce.com/2006/04/metadata">
    <label>Teams Employee API Access</label>
    <description>Grants API Enabled to Unified Employee users so the MS Teams IT Service/Employee app can call Connect APIs. Added during ITSM Teams setup.</description>
    <hasActivationRequired>false</hasActivationRequired>
    <userPermissions><enabled>true</enabled><name>ApiEnabled</name></userPermissions>
</PermissionSet>
```

```bash
sf project deploy start --source-dir force-app --target-org <org-alias>
```

Then assign it: `POST /services/data/v67.0/sobjects/PermissionSetAssignment` with `AssigneeId` (the
portal user) and `PermissionSetId` (the new set). **Grant `ApiEnabled` only — do NOT also add
`ChatterInternalUser`:** the Unified Employee license permits `ApiEnabled` but forbids
`ChatterInternalUser`, and including it makes the whole assignment fail with "user license doesn't allow
the permission: ChatterInternalUser." Verify with a query on `PermissionSet` /
`PermissionSetAssignment` (`PermissionsApiEnabled = true`).
