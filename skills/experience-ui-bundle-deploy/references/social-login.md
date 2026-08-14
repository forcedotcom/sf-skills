# Social login — auth-provider linking, external profiles, community access

Detail for the **socialLogin** step (SKILL.md step 6b). Source of truth: reference
`org-setup.mjs` `loadSocialLoginConfig` (547-555), `enableExternalProfiles`
(569-617), `enableAuthProvidersForSite` (638-833), `addCommunityMemberProfile`
(847-917), `assignPermsetToCommunityUsers` (929-991), and the `main()` social-login
step (2124-2168). Config schema: `org-setup-config-schema.mjs` (65-81, strict).

Verbatim assets this step applies (do not hand-write — parity with the self-reg /
data steps): `assets/Communities.settings-meta.xml` (sub-step 1) and
`assets/social-login-auth-providers.apex` (sub-step 2). Sub-steps 3–4 are plain
`sf data query`/`create record` calls, given below.

Run this step **only** when `socialLogin` is configured in `org-setup.config.json`.
If the block is absent, `loadSocialLoginConfig` returns null and the step is hidden
— no-op cleanly. Unlike self-registration and data import, this step is
**non-destructive and idempotent**, so it does **not** require asking first.

## Why this is programmatic (not a Setup click-path)

On React (Site Container) Experience sites the SSO admin UI is hidden, so auth
providers cannot be linked to the site by clicking through Setup → Login &
Registration. The linking is done by creating `AuthConfigProviders` junction
records that tie each `AuthProvider`/`SamlSsoConfig` to the site's `AuthConfig`.
DML is not allowed on `AuthConfigProviders`, so the linking is done via Anonymous
Apex issuing REST callouts — shipped verbatim as
`assets/social-login-auth-providers.apex` (ported from `enableAuthProvidersForSite`,
638-833). `AuthConfig.AuthOptionsAuthProvider` auto-flips to true when the
junctions are inserted — no separate update needed.

Apply the `assets/` templates **verbatim**, exactly like the self-reg and data
steps — the Apex encodes the all-or-nothing pre-check, REST-callout insert
(DML-not-allowed workaround), and idempotency that are easy to get wrong by hand.
Do NOT invent your own social-login Apex.

Once linked, the site's built-in Social Login component (shipped in 264) renders a
button per configured provider on the React login page.

## Config shape

```json
{ "socialLogin": {
    "communityMemberProfile": "Customer Community User",
    "authProviderNames": ["Google", "My_SAML_Provider"],
    "communityUserPermset": "myapp_Guest_User_Api_Access"
} }
```

- **`communityMemberProfile`** (required) — profile added to
  `NetworkMemberGroup` so SSO-registered users can access the community. Also the
  profile whose community users receive `communityUserPermset` (if set).
- **`authProviderNames`** (required, non-empty) — the **DeveloperNames** of
  `AuthProvider` (OAuth) and/or `SamlSsoConfig` (SAML) records to link. These are
  DeveloperNames, not friendly labels.
- **`communityUserPermset`** (optional) — permset assigned to SSO-created community
  users so `getCurrentUser()` (`/chatter/users/me`, via `/sf/api/`) works; the
  standard community profile lacks `ApiEnabled`. Typically the app's
  `*_Guest_User_Api_Access` permset.

There is **no `siteName`** — the site is derived (below). All three string values
are validated against the SOQL-name whitelist before use in any query or generated
Apex (same guard the permset/self-reg paths use); a `'`, `\`, or control char is a
config error.

## Site derivation (`deriveSiteName`, 418-441)

The site is the base name of the **single** `*.network-meta.xml` under
`<packageDir>/main/default/networks/`. Zero or more than one → STOP (ambiguous; the
reference throws rather than guessing). Social login needs the site to resolve its
`AuthConfig` (matched via `AuthConfig.Url LIKE '%<siteName>%'`).

## Enablement sequence (mirrors `main()` 2124-2168)

Runs **after** self-registration (step 6) and **before** data import / GraphQL.
Every sub-step is idempotent — run its query first and skip work that already
exists. Substitute `<org>` with the target-org alias throughout. All three config
string values (`communityMemberProfile`, each `authProviderNames` entry,
`communityUserPermset`) MUST be validated against the SOQL-name whitelist before
use in any query/Apex below — reject any value containing `'`, `\`, or a control
char (same guard the permset/self-reg paths use); such a value is a config error.

### 1. Enable "Allow standard external profiles" (`enableExternalProfiles`, 569-617)

An org setting required so SSO registration handlers can create users on standard
community profiles; without it, auth providers return `FIELD_INTEGRITY_EXCEPTION`
on user insert. It deploys via Metadata API (REST/Tooling approaches fail on many
org types), so the `CommunitiesSettings` file needs a minimal throwaway sfdx
project. Read `assets/Communities.settings-meta.xml` and stage it in a temp dir:

```bash
TMP=$(mktemp -d)
mkdir -p "$TMP/force-app/main/default/settings"
printf '{"packageDirectories":[{"path":"force-app","default":true}],"sourceApiVersion":"68.0"}' > "$TMP/sfdx-project.json"
cp skills/experience-ui-bundle-deploy/assets/Communities.settings-meta.xml \
   "$TMP/force-app/main/default/settings/Communities.settings-meta.xml"
sf project deploy start --target-org <org> --source-dir "$TMP/force-app" --json
rm -rf "$TMP"
```

A deploy warning that the setting is already active is a **non-fatal skip** — the
setting may already be on. Continue to sub-step 2.

### 2. Link Auth Providers to the site `AuthConfig` (`enableAuthProvidersForSite`, 638-833)

Apply `assets/social-login-auth-providers.apex` **verbatim** — do not hand-write
this. Substitute its placeholders: `<siteName>` (derived above), `<ProviderNamesList>`
(the whitelisted `authProviderNames` as a comma-separated single-quoted list, e.g.
`'Google', 'My_SAML_Provider'` — identical in both the `IN (...)` clauses and the
requested-name loop), and `<ApiVersion>` (e.g. `62.0`). Then run it as ONE call:

```bash
sf apex run --target-org <org> --file assets/social-login-auth-providers.apex
```

Read the `|DEBUG|` output lines (match `|DEBUG|` only — `sf apex run` echoes the
source, which would otherwise false-positive):

| `|DEBUG|` line | Meaning → action |
|----------------|------------------|
| `ERROR_NO_AUTHCONFIG` | No `AuthConfig` for the site → **fail**: "no AuthConfig found for site `<siteName>`". Publish/activate the site; confirm the derived name matches the org Network. |
| `ERROR_NO_PROVIDERS` | None of the names resolved → **fail**: none found for those names; create them in Setup first. |
| `MISSING_PROVIDERS:<names>` | Strict subset resolved → **fail**: "some configured auth providers were not found: `<names>`". Nothing was linked (all-or-nothing; the check runs before any insert). Create/fix them or fix the DeveloperName(s) and re-run. |
| `INSERT_FAILED:<name>:<type>:<code>:<body>` | A junction insert failed → **fail** after reporting each; `<code>`/`<body>` explain why. |
| `INSERTED:<name>:<type>` | Newly linked (report `+ <name>`). |
| `ALREADY_LINKED:<name>:<type>` / `ALL_ALREADY_LINKED` | Idempotent skip — already linked; report and continue. |
| `TOTAL_INSERTED:<n>` | Success — `<n>` providers newly linked. |

Matching is **case-insensitive** (SOQL `DeveloperName IN (...)` is), so a stored
name differing only in case is not "missing."

### 3. Add the community member profile to `NetworkMemberGroup` (`addCommunityMemberProfile`, 847-917)

Without it, users created by the SSO registration handler hit `NO_ACCESS: User was
not authorized for the community`. Resolve the Network + Profile Ids, skip if the
membership already exists, else create it (idempotent):

```bash
# Resolve Ids (<siteName> derived above; <communityMemberProfile> from config)
sf data query --target-org <org> --json \
  --query "SELECT Id FROM Network WHERE Name = '<siteName>'"                 # -> <NetworkId>
sf data query --target-org <org> --json \
  --query "SELECT Id FROM Profile WHERE Name = '<communityMemberProfile>'"   # -> <ProfileId>
# Idempotency check — skip the create if this returns any record
sf data query --target-org <org> --json \
  --query "SELECT Id FROM NetworkMemberGroup WHERE NetworkId = '<NetworkId>' AND ParentId = '<ProfileId>'"
# Create only if absent
sf data create record --target-org <org> --sobject NetworkMemberGroup \
  --values "NetworkId='<NetworkId>' ParentId='<ProfileId>'" --json
```

### 4. (Optional) Assign `communityUserPermset` to community users (`assignPermsetToCommunityUsers`, 929-991)

Only when `communityUserPermset` is configured. Grants `ApiEnabled` so
`getCurrentUser()` (`/chatter/users/me` via `/sf/api/`) works for SSO-created
users. Find active community users on `communityMemberProfile` who lack the
permset, and assign it (idempotent; no users yet → skip, not fatal):

```bash
# Resolve the permset Id
sf data query --target-org <org> --json \
  --query "SELECT Id FROM PermissionSet WHERE Name = '<communityUserPermset>'"   # -> <PermSetId>
# Find users on the profile who do NOT already have it
sf data query --target-org <org> --json \
  --query "SELECT Id, Username FROM User WHERE Profile.Name = '<communityMemberProfile>' AND IsActive = true AND UserType IN ('CspLitePortal','CustomerSuccess','PowerCustomerSuccess') AND Id NOT IN (SELECT AssigneeId FROM PermissionSetAssignment WHERE PermissionSetId = '<PermSetId>')"
# For each returned user Id, assign (treat DUPLICATE_VALUE as an already-assigned skip)
sf data create record --target-org <org> --sobject PermissionSetAssignment \
  --values "PermissionSetId='<PermSetId>' AssigneeId='<UserId>'" --json
```

## Gotchas

| Symptom | Cause | Fix |
|---------|-------|-----|
| No social-login buttons on the login page | `socialLogin` block absent or step skipped | Add the block and run step 6b; it links providers to the site `AuthConfig` |
| "some configured auth providers were not found: X" | A DeveloperName in `authProviderNames` has no `AuthProvider`/`SamlSsoConfig` record | Create it in Setup first, or fix the DeveloperName. Nothing is linked until all resolve |
| `no AuthConfig found for site "<name>"` | Site not published/active, or name mis-derived | Publish the site; confirm the single `*.network-meta.xml` base name matches the org's Network name |
| SSO user: `NO_ACCESS: User was not authorized for the community` | `communityMemberProfile` not in `NetworkMemberGroup` | Ensure sub-step 3 ran (profile added to member groups) |
| SSO user insert fails with `FIELD_INTEGRITY_EXCEPTION` | "Allow standard external profiles" org setting off | Ensure sub-step 1 ran (`enableExternalProfiles`) |
| `getCurrentUser()` / `/chatter/users/me` fails for SSO users | Community profile lacks `ApiEnabled` | Set `communityUserPermset` so sub-step 4 assigns API access |
