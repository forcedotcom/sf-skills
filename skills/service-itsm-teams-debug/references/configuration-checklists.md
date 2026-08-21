# MS Teams for Employee Service — Configuration Checklists

The exact setup each Teams ITSM feature requires. Match the user's reported problem to a checklist
via the **Feature Map**, then run that checklist's checks **in order**. Each check lists what to
verify, the query / API field, the pass condition, and the exact Setup remediation when it fails.

> Run reads via headless-360 `dispatch_readonly` (SOQL through `GET /services/data/vXX.0/query`,
> Connect/REST endpoints directly). A few checks require the **SOAP Metadata API** (noted inline) —
> those read metadata not exposed to REST/Tooling. Always use the full `/services/data/vXX.0/...`
> version prefix.

---

## Feature Map

| User says… | Feature | Checklist |
|---|---|---|
| "Can't log in to IT Desk app" / "Salesforce Desk app not working" / "IT Desk login" | Login to Salesforce IT Desk app | `LOGIN_DESK` |
| "UEL user can't log in to IT Service app" / "UEL login not working" | Login to IT Service — UEL user | `LOGIN_SERVICE_UEL` |
| "CCP user can't log in to IT Service" / "IT Service not working" / "IT Service login" | Login to IT Service — CCP user | `LOGIN_SERVICE_CCP` |
| "Login" / "Can't log in" (generic, no app named) | Generic login | `LOGIN` (then ask: IT Desk or IT Service?) |
| "Agentforce not working" / "Teams AgentForce issue" | Agentforce embedded service + messaging channel | `AGENTFORCE` |
| "Swarming not working" / "Collaboration tool not set" | Swarming collaboration tool + Auth Provider | `SWARMING` |
| "MS Teams not showing" / "Teams tab missing" / "feature enablement" / "Teams not enabled" | MS Teams feature not visible | `MSTEAMS_CORE` |
| "Teams not loading" / "Lightning app not embedding" | Lightning Out / embedding | `LIGHTNING_OUT` |
| "CI Hub / Service Catalog / Employee Enablement / My Assets tab not loading" | Tab loading (IT Desk or IT Service) | `TAB_LOADING` |
| "SSO not working" / "single sign-on failing" | Single Sign-On | `SSO` |

> **ECA naming:** the External Client App the login checks look for is **`ServiceCloudTeamsEca`**.
> Some orgs surface a related packaged instance (e.g. `ServiceCloudMSTeamsEca`); match the ECA that
> actually backs the Teams login. A missing app usually means the feature needs to be turned OFF
> then ON again from Salesforce Go.

---

## Checklist: LOGIN_DESK
*Applies to: "Not able to login to IT Desk app", "Salesforce Desk app not working"*

1. **CORS → Enable CORS for OAuth endpoints** — must be **ON**
   (Tooling: `SessionSettings.IsOauthCorsPolicyEnabled = true`)
2. **CORS Allowed Origins** — both URLs must be present (`CorsWhitelistEntry.UrlPattern`):
   - `https://cdn.scs.static.lightning.force.com`
   - `https://teams.cloud.microsoft`
3. **External Client App: `ServiceCloudTeamsEca`** — must exist
4. **Microsoft Teams for Employee Service Feature** — must be **ON**
   - Checked via the FulfillerApp permissions API (see `MSTEAMS_CORE` check 3)
   - Setup → Salesforce Go → Feature Sets → Deliver IT Services Across Channels → View all features → Microsoft Teams for Employee Service
5. **Salesforce IT Desk Feature** — must be **ON** (required specifically for IT Desk login)
6. **User PSL: `TeamsForITSrvcsPsl` assigned** *(requires end-user's Salesforce username)*
   - SOQL: `SELECT Id FROM PermissionSetLicenseAssign WHERE AssigneeId = '<userId>' AND PermissionSetLicense.DeveloperName = 'TeamsForITSrvcsPsl' LIMIT 1`
   - If not assigned: Setup → Users → open user → Permission Set License Assignments → Edit → add **Microsoft Teams for IT Services** → Save
   - If username not provided: `MANUAL_CHECK_REQUIRED` (MANUAL) — re-run with the end-user's username

---

## Checklist: LOGIN_SERVICE_UEL
*Applies to: "UEL user not able to login to IT Service app", "UEL login not working"*

1. **CORS → Enable CORS for OAuth endpoints** — must be **ON**
2. **CORS Allowed Origins** — both URLs present (`cdn.scs.static.lightning.force.com` + `teams.cloud.microsoft`)
3. **External Client App: `ServiceCloudTeamsEca`** — must exist
4. **Microsoft Teams for Employee Service Feature** — must be **ON**
5. **Salesforce IT Service Feature** — must be **ON** (required specifically for IT Service login)
6. **Allow OAuth for employees** *(SOAP Metadata API — `ProfileSessionSetting`)*
   - Setup → Profiles → Unified Employee → Session Settings → check **"Allow OAuth for employees"** → Save
   - Read via SOAP `listMetadata(ProfileSessionSetting)` → `readMetadata` on the fullName containing `unified`
   - Field `allowOauthForEmployees`: `true` = ENABLED (OK), `false` = DISABLED (FAIL), absent = NOT CONFIGURED (FAIL)
   - **Not queryable via REST or Tooling API — Metadata API only.** **UEL users only.**
7. **User PSL: `TeamsForEmployeePsl` assigned** *(requires UEL end-user's username)*
   - PSL DeveloperName `TeamsForEmployeePsl` (MasterLabel "Teams for Employee"); linked permission set `TeamsForEmployeeUser`
   - SOQL: `SELECT Id FROM PermissionSetLicenseAssign WHERE AssigneeId = '<userId>' AND PermissionSetLicense.DeveloperName = 'TeamsForEmployeePsl' LIMIT 1`
   - If not assigned: Setup → Users → open user → Permission Set License Assignments → Edit → add **Teams for Employee** → Save
   - **UEL users only.**

---

## Checklist: LOGIN_SERVICE_CCP
*Applies to: "CCP user not able to login to IT Service app", "IT Service app not working" (non-UEL)*

1. **CORS → Enable CORS for OAuth endpoints** — must be **ON**
2. **CORS Allowed Origins** — both URLs present
3. **External Client App: `ServiceCloudTeamsEca`** — must exist
4. **Microsoft Teams for Employee Service Feature** — must be **ON**
5. **Salesforce IT Service Feature** — must be **ON**
6. **User API Enabled permission** *(requires CCP end-user's username)*
   - SOQL: `SELECT Id, Username FROM User WHERE Username = '<username>' AND IsActive = true LIMIT 1`, then check the user's Profile or Permission Sets for the **API Enabled** system permission
   - If not enabled: Setup → Users → open user → Profile or Permission Sets → verify **API Enabled** is granted
   - **CCP users only** — UEL users use the `TeamsForEmployeePsl` PSL (above) instead.

---

## Checklist: LOGIN
*Applies to: Generic login issues where no specific app is mentioned. Ask which app, then switch to LOGIN_DESK / LOGIN_SERVICE_*.*

1. **CORS → Enable CORS for OAuth endpoints** — must be **ON**
2. **CORS Allowed Origins** — both URLs present
3. **External Client App: `ServiceCloudTeamsEca`** — must exist
4. **Microsoft Teams for Employee Service Feature** — must be **ON**

---

## Checklist: TAB_LOADING
*Applies to: "CI Hub / Service Catalog / Employee Enablement / My Assets tab not loading" — both IT Desk and IT Service apps*

1. **Session token for 3rd-party embedding** — must be **ON**
   - Setup → Session Settings → check **"When embedding a Lightning application in a third-party site, use a session token instead of a session cookie"** → Save
   - Tooling: `SELECT SidToken3rdPartyAuraApp FROM SessionSettings LIMIT 1` → `true` = OK
2. **My Domain: Require first-party cookies** — must be **OFF**
   - Setup → Company Settings → My Domain → **uncheck** "Require first-party use of Salesforce cookies" → Save
   - Tooling: `SELECT IsFirstPartyCookieUseRequired FROM MyDomainSettings LIMIT 1` → `false` = OK

---

## Checklist: MSTEAMS_CORE
*Applies to: MS Teams feature not visible, Teams tab not showing, cannot enable the feature, feature-enablement issues*

1. **API Connectivity** — verify the org is reachable via REST.
2. **`TeamsForITSrvcsPsl` License** — present and Active
   - SOQL: `SELECT DeveloperName, MasterLabel, Status, TotalLicenses, UsedLicenses FROM PermissionSetLicense WHERE DeveloperName = 'TeamsForITSrvcsPsl' LIMIT 1`
   - `Status` must be `Active`. If missing, the `TeamsITSrvcsAddOn` license isn't provisioned — contact Salesforce to add it. If disabled, contact support to reactivate.
3. **Feature Enabled** — `GET /services/data/v66.0/connect/it-service/permissions/FulfillerApp`
   - If the API returns `FUNCTIONALITY_NOT_ENABLED`: the `IServiceItsmTeamsFamily` feature family is disabled at the org level → turn on **Microsoft Teams for Employee Service** in Salesforce Go.
   - Otherwise validate these flags (all must be `true`):
     - `orgHasTeamsAllowed` — MS Teams allowed for this org
     - `orgHasTeamsFullfillerHubEnabled` — Salesforce IT Desk feature enabled
     - `orgHasTeamsEmployeeHubEnabled` — Employee Hub feature enabled
     - `userHasTeamsFulfillerHubAllowed` — current user has `TeamsForITSrvcsPsl` PSL
     - `teamsUserHasAccessToSwarm` — user has swarming access
     - `orgHasEmployeeOrITServiceTeamsAllowed` — org-level Teams access for Employee/IT Service
   - Also surfaces `TEAMS_LO2_APP` (app id) and `Agents` count (Agentforce agents configured).
   - Fix `orgHasTeamsFullfillerHubEnabled=false`: Salesforce Go → Feature Sets → Deliver IT Services Across Channels → Salesforce IT Desk → Turn On.
   - Fix `userHasTeamsFulfillerHubAllowed=false`: Setup → Users → open user → PSL Assignments → add `TeamsForITSrvcsPsl`.

---

## Checklist: LIGHTNING_OUT
*Applies to: Lightning app not embedding in Teams, blank tab, loading errors*

1. **Session Settings — session token for third-party embedding** — enable **"When embedding a Lightning application in a third-party site, use a session token instead of a session cookie"** (Setup → Session Settings).
2. **My Domain — disable first-party cookie requirement** — **uncheck** "Require first-party use of Salesforce cookies" (Setup → Company Settings → My Domain).

---

## Checklist: SWARMING
*Applies to: "Swarming not working", "collaboration tool not set", "Teams not showing in Swarming"*

1. **Swarming Collaboration Tool** — Setup → Swarming → Select a Collaboration Tool → must be **Teams** (manual verification).
2. **Microsoft Auth Provider** — must exist with full metadata
   - SOQL: `SELECT Id, DeveloperName, FriendlyName, ProviderType, ConsumerKey, ConsumerSecret FROM AuthProvider WHERE DeveloperName = 'microsoft_auth_provider' LIMIT 1`
   - `ProviderType = Microsoft`; `ConsumerKey` = Azure AD Client ID, `ConsumerSecret` = Azure AD Client Secret (both readable via SOQL — SOAP returns a placeholder)
   - `CallbackUrl` is NOT a SOQL field — construct it as `{orgUrl}/services/authcallback/microsoft_auth_provider`
3. **Azure AD App Verification** *(requires Azure AD Tenant ID)*
   - Get a Graph token: `POST https://login.microsoftonline.com/<tenantId>/oauth2/v2.0/token` (client credentials, using `ConsumerKey` + `ConsumerSecret`). If it fails → the client secret is invalid; report the exact `AADSTS...` error.
   - Look up the app: `GET https://graph.microsoft.com/v1.0/servicePrincipals?$filter=appId eq '<clientId>'` (use `/servicePrincipals`, not `/applications` — the latter needs `Application.Read.All`).
   - Validate: **Client ID match** (`appId` == `ConsumerKey`); **Client Secret** valid (token issued); **Multi-tenant** (`signInAudience = AzureADMultipleOrgs`); **Redirect URI** (the constructed callback URL is in `replyUrls`); and **17 delegated API permissions** granted (`GET /v1.0/servicePrincipals/{id}/oauth2PermissionGrants`):
     `Channel.Create`, `Channel.ReadBasic.All`, `ChannelMember.Read.All`, `ChannelMember.ReadWrite.All`, `ChannelMessage.Edit`, `ChannelMessage.Read.All`, `ChannelMessage.ReadWrite`, `ChannelMessage.Send`, `email`, `Group.Read.All`, `Group.ReadWrite.All`, `offline_access`, `openid`, `profile`, `Team.Create`, `Team.ReadBasic.All`, `User.Read`
   - If Tenant ID not provided: `MANUAL_CHECK_REQUIRED` (MANUAL) — not a failure.

---

## Checklist: SSO
*Applies to: SSO not working with MS Teams. Trigger keywords: sso, single sign-on, federated login, identity provider, idp, oidc, entra id / azure ad login, okta / adfs sso.*

When an app is named, also run the app's login checklist (`LOGIN_DESK` or `LOGIN_SERVICE_CCP` /
`LOGIN_SERVICE_UEL`); skip duplicate checks. Total ≈ 14 checks for IT Desk/CCP, 16 for UEL.

1. **API Connectivity** — org reachable via REST (HTTP 200).
2. **External Client App: `ServiceCloudTeamsEca`** — exists
   - `SELECT Id, DeveloperName, MasterLabel FROM ExternalClientApplication WHERE DeveloperName = 'ServiceCloudTeamsEca' LIMIT 1`
   - If missing: turn ON the Teams for Employee Service feature from Salesforce Go, verify it appears in Setup → External Client App Manager; if the feature is already on, toggle it OFF then ON.
3. **PREFERRED_SITE (Experience Site)** — configured, valid, and **Live**
   - `GET /services/data/v65.0/setup/org/values/SLACK_PREFERRED_SITE` → site Id
   - `GET /services/data/v62.0/connect/communities/{siteId}` → status `Live`; construct the **full site URL** from `baseUrl` + `urlPathPrefix` (e.g. `https://<org>.my.site.com/ITSMPortal`) — used for the Azure callback + Graph extension checks.
   - If failed: Setup → Digital Experiences → All Sites → configure the preferred site; ensure it's published and Live.
4. **Auth Provider: `microsoft_auth_provider`** — Microsoft type, ClientId/Secret set, **Registration Handler = `MsTeamsItsmSSOHandler`**, **Execute As = System Administrator**
   - `SELECT Id, DeveloperName, ProviderType, ConsumerKey, ConsumerSecret, RegistrationHandlerId, ExecutionUserId FROM AuthProvider WHERE DeveloperName = 'microsoft_auth_provider' LIMIT 1`
   - Resolve: `SELECT Name FROM ApexClass WHERE Id = '<RegistrationHandlerId>'` and `SELECT Profile.Name FROM User WHERE Id = '<ExecutionUserId>'`
   - If misconfigured: Setup → Auth. Providers → microsoft_auth_provider → Edit → Registration Handler Type = Apex class, Registration Handler = `MsTeamsItsmSSOHandler`, Execute Registration As = an admin (System Administrator profile) → Save.
5. **Azure AD App (multi-tenant, callback URLs, perms)** *(requires Tenant ID)*
   - `POST https://login.microsoftonline.com/{tenantId}/oauth2/v2.0/token` then `GET https://graph.microsoft.com/v1.0/applications?$filter=appId eq '{clientId}'`
   - Expect `signInAudience = AzureADMultipleOrgs`; `web.redirectUris` contains **both** the org callback (`{orgUrl}/services/authcallback/microsoft_auth_provider`) and the site callback (`{siteFullUrl}/services/authcallback/microsoft_auth_provider`); `requiredResourceAccess` includes `Organization.ReadWrite.All` (application permission).
   - If failed: Azure Portal → App Registrations → your app → Authentication (add redirect URIs, set Multitenant) → API Permissions (add `Organization.ReadWrite.All`, grant admin consent).
   - If Tenant ID not provided: `MANUAL_CHECK_REQUIRED` (MANUAL).
6. **Named Credential: `MSGraphApplicationNC`** + External Credential `MSTeamsClientCredentialsEC`
   - NC exists, URL = `https://graph.microsoft.com`, linked to EC `MSTeamsClientCredentialsEC`.
   - EC: protocol `OAuth`, flow **Client Credentials with Client Secret**, scope `https://graph.microsoft.com/.default`, IdP URL `https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token`, principal `NamedAuthPrincipal`, **Authentication Status `Configured`**.
   - Read: SOAP `readMetadata(NamedCredential, 'MSGraphApplicationNC')` + `readMetadata(ExternalCredential, 'MSTeamsClientCredentialsEC')`; and `GET /services/data/v65.0/named-credentials/external-credentials?externalCredential=MSTeamsClientCredentialsEC` to confirm the principal's Authentication Status is `Configured`.
   - If status ≠ Configured: Setup → External Credentials → MSTeamsClientCredentialsEC → Principals → NamedAuthPrincipal → set Client ID + Client Secret from the Azure app.
7. **Microsoft Graph Organization Extension** *(requires Tenant ID)*
   - `GET https://graph.microsoft.com/v1.0/organization/{tenantId}/extensions` → extension id matching `{tenant}-*`; `sfOrgUrl` matches the org URL, `sfSiteUrl` matches the full PREFERRED_SITE URL (no trailing slashes).
   - If failed: the extension is created/updated via the SSO setup flow; org + site URLs must match exactly.
8. **ApexClass: `MsTeamsItsmSSOHandler`** — exists and Active
   - `SELECT Id, Name, ApiVersion, Status FROM ApexClass WHERE Name = 'MsTeamsItsmSSOHandler' LIMIT 1` → `Status = Active`
   - If inactive: Setup → Apex Classes → MsTeamsItsmSSOHandler → Edit → Status Active → Save. If missing: verify the Teams for Employee Service managed package is installed.
9. **User Mapping (FederationIdentifier)** *(requires end-user username)*
   - `SELECT Id, Username, Email, FederationIdentifier, IsActive FROM User WHERE Username = '<username>' LIMIT 1` → user Active and `FederationIdentifier` set to the Azure AD UPN (must match the `upn` claim exactly).
   - If blank: Setup → Users → open user → Edit → set **Federation ID** to the Azure AD UPN → Save.

---

## Checklist: AGENTFORCE
*Applies to: "Agentforce not working in MS Teams", "Teams_AgentForce issue"*

1. **API Connectivity** — org reachable.
2. **`Teams_AgentForce` Embedded Service Deployment** — exists, `DeploymentType = API`, `IsEnabled = true`
   - Read via **SOAP `readMetadata(EmbeddedServiceConfig, 'Teams_AgentForce')`** — this one call returns `deploymentType`, `isEnabled`, and the nested `<messagingChannel>` name (Tooling SOQL can't reach the nested `embeddedServiceMessagingChannel` block). A quick existence check is Tooling `SELECT Id FROM EmbeddedServiceConfig WHERE DeveloperName='Teams_AgentForce'`.
   - **If this returns 0 rows, the ESD is MISSING — this is the #1 cause of "IT Service login works but the agent never replies."** The Teams client loads the deployment by `esDeveloperName=Teams_AgentForce`; if it doesn't exist, the agent can't respond even when the channel, flow, agent, and permsets are all correct. Remediation: create + publish it (Metadata-deploy an API-type ESD, then Connect `POST /connect/embeddedservice/embeddedserviceconfig/publish/<esdId>`) — see `service-itsm-teams-employee-agent-configure`'s "Create + publish the `Teams_AgentForce` ESD headlessly (verified)".
   - **Published state is not readable via any query field** — no field distinguishes published vs unpublished for API-type EmbeddedMessaging deployments. The publish *call* returning `{"isSuccess": true}` is the only confirmation; if in doubt, re-run publish (idempotent).
3. **Linked Messaging Channel exists and is active** — channel `DeveloperName` from `<messagingChannel>` (any name; extracted dynamically); REST `MessagingChannel WHERE DeveloperName = '<name>'`, `IsActive = true`.
4. **Messaging Channel Configuration** — `MessageType`/`ConsentType` (REST); `sessionHandlerType`/`sessionHandlerFlow`/`sessionHandlerQueue` (SOAP v62); flow active via Tooling `FlowDefinition.ActiveVersionId`; queue exists via REST `Group WHERE Type='Queue'`.
5. **Only one ESD, and it is `Teams_AgentForce` (type API)** — verified live (Aug 19 2026): there is a **single** `EmbeddedServiceConfig` for this integration, `Teams_AgentForce`, `DeploymentType = API`, `site = null`. **Do NOT look for a second, Web-type ESD keyed on the channel's DeveloperName** — none exists, and querying for one produces a false FAIL. The custom-client deployment is stored as `API` even though the Setup wizard flow is labelled "Web / custom client." If check #2 found the `Teams_AgentForce` ESD (type API, enabled), this check is satisfied.
6. **Linked Agentforce Agent Active** — SOAP `sessionHandlerFlow` → Tooling `FlowDefinition.ActiveVersionId` → REST Tooling `GET /tooling/sobjects/Flow/{id}` → `actionCalls[routeWork].inputParameters.agentforceEmployeeAgentId`; then `BotDefinition` + `BotVersion WHERE BotDefinitionId = '<id>'` with `BotVersion.Status = Active`.
7. **User Verification Configuration** — from `MessagingChannel.embeddedConfig` via **SOAP v62** (`authMode`, `messagingAuthorizations.enabled`, `authorizationType`, `publicKeyCertificateSetName`, `authIdentifier`, `verifiedUserJwtExpirationTime`). **CRITICAL: SOAP v60 silently omits `<embeddedConfig>` — use v62+.**
8. **JWT Issuer matches Experience Site URL** — read `PublicKeyCertificateSet` (SOAP v62): `jwksEndPoint` must be `{orgUrl}/id/keys` (normalise `lightning.force.com` ↔ `my.salesforce.com`); `jwtIssuer` must match the Employee Experience Site URL provided at runtime (skipped if not provided).

> For the runtime "agent joins then leaves / won't reply" fix — auth mode **ON** backed by a
> **`JWKS_URL` Key Set** (`jwksEndPoint = {orgUrl}/id/keys`, `jwtIssuer` = the Employee Site URL),
> plus the **Agent Access** permission set on the portal user — hand off to
> `service-itsm-teams-employee-agent-configure`. (A build with auth ON but **no** Key Set attached
> is the one that produces the scrt2 "Set the auth mode to false" error — attach the Key Set, don't
> turn auth off.)

---

## Status codes

- `OK` — correct
- `MISCONFIGURED` (FAIL) — exists but wrong
- `MISSING` (FAIL) — component doesn't exist
- `DISABLED` (FAIL) — feature off
- `ERROR` (FAIL) — API call/validation failed
- `MANUAL_CHECK_REQUIRED` (MANUAL) — needs manual verification, or an optional input (Tenant ID/username) wasn't provided

---

## API Field Reference

| Check | API / Object | Field |
|---|---|---|
| CORS OAuth enabled | Tooling: `SessionSettings` | `IsOauthCorsPolicyEnabled` |
| CORS Allowed Origins | REST: `CorsWhitelistEntry` | `UrlPattern` |
| Lightning Out session token | Tooling: `SessionSettings` | `SidToken3rdPartyAuraApp` |
| My Domain first-party cookies | Tooling: `MyDomainSettings` | `IsFirstPartyCookieUseRequired` |
| External Client App | REST: `ExternalClientApplication` | `DeveloperName = 'ServiceCloudTeamsEca'` |
| MS Teams for IT Services license | REST: `PermissionSetLicense` | `DeveloperName = 'TeamsForITSrvcsPsl'`, `Status`, `TotalLicenses`, `UsedLicenses` |
| FulfillerApp permissions | REST Connect: `GET /services/data/v66.0/connect/it-service/permissions/FulfillerApp` | `orgHasTeamsAllowed`, `orgHasTeamsFullfillerHubEnabled`, `orgHasTeamsEmployeeHubEnabled`, `userHasTeamsFulfillerHubAllowed`, `teamsUserHasAccessToSwarm`, `orgHasEmployeeOrITServiceTeamsAllowed`, `TEAMS_LO2_APP`, `Agents` — returns `FUNCTIONALITY_NOT_ENABLED` when `IServiceItsmTeamsFamily` is disabled |
| Teams for Employee license (UEL) | REST: `PermissionSetLicense` | `DeveloperName = 'TeamsForEmployeePsl'`, `Status`, `TotalLicenses`, `UsedLicenses` |
| User PSL assignment (IT Desk) | REST: `PermissionSetLicenseAssign` | `AssigneeId`, `PermissionSetLicense.DeveloperName = 'TeamsForITSrvcsPsl'` |
| User PSL assignment (IT Service/UEL) | REST: `PermissionSetLicenseAssign` | `AssigneeId`, `PermissionSetLicense.DeveloperName = 'TeamsForEmployeePsl'` |
| Allow OAuth for employees | SOAP v62: `listMetadata(ProfileSessionSetting)` → `readMetadata` on fullName containing `unified` | `allowOauthForEmployees` — `true`=ENABLED, `false`=DISABLED, absent=NOT CONFIGURED |
| Microsoft Auth Provider (Swarming) | REST: `AuthProvider` | `DeveloperName = 'microsoft_auth_provider'`, `ProviderType`, `ConsumerKey` (= Azure ClientId) |
| Microsoft Auth Provider (SSO) | REST: `AuthProvider` | + `ConsumerSecret`, `RegistrationHandlerId`, `ExecutionUserId` → resolve `ApexClass.Name` and `User.Profile.Name` |
| Azure AD App — multi-tenant + callbacks + perms | MS Graph: `GET /v1.0/applications?$filter=appId eq '<clientId>'` | `signInAudience` (`AzureADMultipleOrgs`), `web.redirectUris` (org + site callbacks), `requiredResourceAccess` (`Organization.ReadWrite.All`) |
| Azure AD App — API perms (Swarming) | MS Graph: `GET /v1.0/servicePrincipals/{id}/oauth2PermissionGrants` | `scope` (space-separated delegated permission names) |
| Auth Provider secret | SOQL: `AuthProvider` | `ConsumerSecret` (readable via SOQL; SOAP returns `Placeholder_Value`) |
| Auth Provider org callback URL | Constructed | `{SF_BASE_URL}/services/authcallback/microsoft_auth_provider` |
| Auth Provider site callback URL | Constructed from PREFERRED_SITE | `{SITE_FULL_URL}/services/authcallback/microsoft_auth_provider` |
| PREFERRED_SITE full URL | REST: `GET /services/data/v62.0/connect/communities/{siteId}` | `baseUrl` + `urlPathPrefix` |
| MS Graph Organization Extension | MS Graph: `GET /v1.0/organization/{tenantId}/extensions` | extension id `{tenant}-*`, `sfOrgUrl`, `sfSiteUrl` |
| ApexClass: MsTeamsItsmSSOHandler | REST: `ApexClass` | `SELECT Id, Name, ApiVersion, Status ... WHERE Name = 'MsTeamsItsmSSOHandler'` — `Status = Active` |
| User Mapping (FederationIdentifier) | REST: `User` | `SELECT Id, Username, Email, FederationIdentifier, IsActive ... WHERE Username = '<username>'` — `FederationIdentifier` set (= Azure AD UPN) |
| Embedded Service Deployment + channel name | SOAP v62: `readMetadata EmbeddedServiceConfig` | `deploymentType`, `isEnabled`, `<messagingChannel>` |
| Messaging Channel active | REST: `MessagingChannel` | `DeveloperName`, `IsActive`, `MasterLabel`, `MessageType`, `ConsentType` |
| Omni-Channel routing + flow + queue | SOAP v62: `MessagingChannel` | `sessionHandlerType`, `sessionHandlerFlow`, `sessionHandlerQueue` |
| Flow active | Tooling: `FlowDefinition` | `ActiveVersionId` (non-null = active) |
| Agent id from flow | REST Tooling: `GET /tooling/sobjects/Flow/{activeVersionId}` | `Metadata.actionCalls[routeWork].inputParameters.agentforceEmployeeAgentId` |
| Agent active | REST: `BotDefinition` + `BotVersion` | `BotVersion.Status = 'Active'` |
| Single ESD is `Teams_AgentForce` (type API) | Tooling: `EmbeddedServiceConfig` | one row only; `DeveloperName = 'Teams_AgentForce'`, `DeploymentType = 'API'`, `IsEnabled = true` (no separate Web-type channel ESD exists) |
| User verification (authMode, cert, expiry) | SOAP v62: `MessagingChannel.embeddedConfig` | `authMode`, `messagingAuthorizations.*`, `verifiedUserJwtExpirationTime` (v60 omits `<embeddedConfig>`) |
| JWT JWKS endpoint / Issuer | SOAP v62: `PublicKeyCertificateSet` | `jwksEndPoint` (`{orgUrl}/id/keys`), `jwtIssuer` (= Experience Site URL) |

---

## Environment note

Production login `https://login.salesforce.com`; Sandbox/scratch `https://test.salesforce.com`.
Non-production (e.g. `*.pc-rnd.salesforce.com`) uses the test login host.
