# SignupRequest Field Reference

Trial-org creation is performed by inserting a **`SignupRequest`** sObject (key prefix `0SR`, `minApiVersion` 182). Source of truth: `core/udd-xml/java/resources/udd/SignupRequest.entity.xml` in the core repo (`gitcore.soma.salesforce.com/core-2206/core-266-public`). Owned by the **Signup and ISV Tools** team.

## Required fields

| Field | Type | Meaning / Notes |
|---|---|---|
| `LastName` | Text(80) | Admin user last name |
| `Username` | Text(80) | Admin username. Globally unique, must be email-format. Lowercased on set. |
| `SignupEmail` | Email | Admin user email |
| `Company` | Text(80) | Company / org name |
| `Country` | Text(3) | ISO country code (e.g. `US`). `DefaultSignupRequest` defaults to `US`. |

## Common optional fields

| Field | Type | Meaning |
|---|---|---|
| `FirstName` | Text | Admin first name |
| `TemplateId` | Text(15) | Trialforce Template ID (`0TT…`) — the trial product/template to clone |
| `Edition` | StaticEnum `Edition` (minApi 198) | Org edition, e.g. `Developer`, `Enterprise`/`PlanOrgEE`, `PlanOrgPE`, `PlanOrgDE`. Mutually exclusive with clone/source-org. Confirm exact API values against `udd-*.xml` if enumerating. |
| `TrialDays` | Integer | Days until trial expiry. Resolved server-side post-commit if not set. |
| `PreferredLanguage` | StaticEnum `Language` (minApi 198) | Default locale. Invalid values silently scrubbed (`scrubLanguageField`). Default `en_US`. |
| `Subdomain` | Text (minApi 186) | Requested My Domain subdomain |
| `ConnectedAppConsumerKey` | Text(120) (minApi 184) | Return an OAuth auth code for this Connected App |
| `ConnectedAppCallbackUrl` | StringPlusClob(2000) (minApi 184) | OAuth callback URL |
| `IsSignupEmailSuppressed` | Boolean (minApi 186) | Suppress welcome email. Server default applied if not explicitly set. |
| `SignupSource` | Text(60) (minApi 200) | Free-text signup source tag |

## Perm-gated / advanced fields

Require additional org/user permissions; only set when the host org is entitled.

| Field | Type | Gate |
|---|---|---|
| `IsSyncLogin` | Boolean (minApi 194) | `SignupRequestSyncLogin` perm. Synchronous login; populates `LoginUrl`. |
| `IsTso` | Boolean (minApi 200) | `isHubMasterAndPartner` / TMO |
| `ShouldConnectToEnvHub` | Boolean (minApi 198) | Env Hub membership |
| `CloneFromOrg` | Text(15) (minApi 204) | Clone from existing org (Env Hub / Sayonara) |
| `AuthProviderType` | StaticEnum (minApi 236) | `SocialSignup` perm |
| `Instance` | Text(8) (minApi 210) | `SetSignupDestination` perm — force target instance |
| `EmailBrandId` / `LoginBrandId` | Text(15) (minApi 202) | TMO-only branding |
| `ArtifactAncestors` | StringPlusClob(2000) (minApi 206) | Perm-gated artifact ancestry |
| `InternalForceSync` | Boolean (minApi 202) | Internal/test only (`isDevInternal`/`isUiTier`) |
| `TrialSourceOrgId` | Text(15) | System-set, read-only |

## System-set / read-only output fields

`createAccess="UserType.AUTOMATED_PROCESS;isDevInternal"` — you read these back from the record after create, you do not set them:

`Status`, `ErrorCode`, `CreatedOrgId`, `CreatedOrgInstance`, `ResolvedTemplateId`, `TemplateDescription`, `AuthCode`, `LoginUrl`.

## Validation rules to respect

- Send **exactly one** of `Edition` or `TemplateId`. Both → `redundantTemplateId`; neither → `missingEdition` (both under `ApiErrorCodes.INVALID_SIGNUP_OPTION`).
- `TemplateId`/`Edition` cannot coexist with clone (`CloneFromOrg`) or source-org fields.
- Partner/Trialforce editions require the host org's partner/TMC perm → otherwise `noPartnerAccess`.
- Daily / active signup rate limits (`dailyLimitExceeded`, `activeScratchLimitExceeded`).
- Invalid username (email-format + globally unique) / country (ISO code) / templateId (`0TT`) / subdomain; subdomain-in-use.
- **Terms / subscription-agreement acceptance is NOT a field on this sObject** — it is enforced at the higher-level WebForm / `SignupConfigItem` layer (public developer signup forms). This skill targets the authenticated `SignupRequest` sObject path, not the public web-form config layer.

## Authentication summary

- Not public/unauthenticated. Authenticate as a user in a **host org**.
- Org gate: the host org must be **entitled to create trial orgs**. The `SignupRequest` entity is only exposed on an entitled org.
- The skill does not run a separate entitlement check — the `sf data create record` call is the definitive gate. On an unentitled org the entity is not exposed and the create fails with `NOT_FOUND` or `INVALID_TYPE`; surface the raw CLI error and point the user to Salesforce support — do not diagnose the missing permission. (Entity accessibility does map exactly to entitlement, so a `SELECT Id FROM SignupRequest LIMIT 1` probe would work as a fail-fast check, but it only duplicates the create-time gate.)
- User gate: the invoking user must be authenticated and have sufficient access on the host org to create the record.
- Auth: log into the host org once with `sf org login web` (or `sf org login`), then reference it by username or alias with `--target-org` (`-o`) on each `sf data create record` / `sf data get record` call. The CLI carries the auth for you.
- Always pass `-o` explicitly and confirm the target host org with the user first. Without `-o` the CLI falls back to the configured default org (`target-org` config / `SF_TARGET_ORG`), or errors with `NoDefaultEnvError` if none is set — it never auto-selects among connected orgs. The default may be an unrelated org, so an omitted `-o` risks provisioning against the wrong org. Verify the chosen org shows `Connected` in `sf org list`.
