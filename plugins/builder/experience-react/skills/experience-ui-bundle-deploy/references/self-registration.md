# Self-registration — site derivation, license gate, and record creation

Detail for the **selfReg** step. Source of truth: reference `org-setup.mjs`
`enableSelfRegistration` (576-737), `checkSelfRegLicense` (895-926),
`resolveGuestUsername` (845-880), and `deriveSiteName` (414-437).

Run this step **only** when self-registration is configured
(`selfRegistration: { selfRegProfile, accountName }` in `org-setup.config.json`).
If absent, no-op cleanly. **Ask the user** for `selfRegProfile` and `accountName`
if they are not already in config.

## Config shape

```json
{ "selfRegistration": { "selfRegProfile": "<Profile API name>",
                         "accountName": "<display name>" } }
```

There is **no** `siteName` field — the site is derived (below). There is **no**
license field — the required license is derived from `selfRegProfile`.

## Site derivation (`deriveSiteName`)

The site is the base name of the **single** `*.network-meta.xml` file under
`<packageDir>/main/default/networks/`. If there are zero or more than one, STOP:
the reference implementation throws rather than guessing (lines 414-437). Validate
the derived name against the SOQL-name whitelist before using it in any query.

## License pre-check (soft skip)

Before doing any work, check that the org has a seat on the UserLicense the
`selfRegProfile` belongs to (`checkSelfRegLicense`, 895-926). Query:

```sql
SELECT UserLicense.LicenseDefinitionKey, UserLicense.Name, UserLicense.Status,
       UserLicense.TotalLicenses, UserLicense.UsedLicenses
FROM Profile WHERE Name = '<selfRegProfile>'
```

Seat math is done client-side (SOQL can't compare two fields): the license must
be **Active** and have either `UsedLicenses < TotalLicenses` or `TotalLicenses ===
-1` (the "unlimited" sentinel). A query failure, zero rows, inactive license, or
no free seats is a **soft skip** — warn the user with the specific reason and
record the step skipped. It is **not** a setup failure.

The profile name here is **validate-and-fail** (a `'`, `\`, or control char
throws a config error), because it is developer config, not user input.

## Enablement sequence

1. **XML edits + deploy** — apply `assets/network-selfreg-xml-recipe.md`
   (enable `<selfRegistration>`, set `<selfRegProfile>`, add the profile to
   `<networkMemberGroups>`), then deploy only that network file. Idempotent: if
   self-reg is already enabled / profile already present, skip the edit and the
   deploy (lines 592-617).
2. **Account** (idempotent) — query
   `SELECT Id FROM Account WHERE Name = '<accountName-escaped>' LIMIT 1`. If it
   exists, reuse it; otherwise create via `assets/network-selfreg.apex` 3a. Create
   via Apex, NOT `sf data create record --values`, because `accountName` is
   free-form and may contain spaces/quotes/`&` the CLI's key=value parser can't
   carry (lines 619-670).
3. **Network Id** — `SELECT Id FROM Network WHERE Name = '<siteName>'`. If not
   found, that is a hard error (the site isn't in the org) (lines 672-690).
4. **NetworkSelfRegistration** (idempotent) — query
   `SELECT Id FROM NetworkSelfRegistration WHERE NetworkId = '<networkId>'`. If a
   row exists, skip; otherwise create via `assets/network-selfreg.apex` 3b
   (lines 692-736).

## Guest-user resolution (used by BOTH self-reg and permset)

When a permission set's assignee is `guestUser`, resolve the site's guest
username with an **exact** profile-name match (`resolveGuestUsername`, 845-880):

```sql
SELECT Username FROM User
WHERE Profile.Name = '<siteName> Profile' AND UserType = 'Guest'
```

- Salesforce auto-creates a guest profile named `"<Site> Profile"`. Use exact
  equality, not `LIKE '%<siteName>%'` — a substring match collides across sites
  (e.g. `shop` also matches `shop-admin`'s guest profile).
- SOQL string equality is case-insensitive, so label-casing differences still
  match.
- **Return null (soft skip) on**: query failure, zero rows, or >1 row (ambiguous —
  refuse to guess). Log the specific reason. On a non-English org the localized
  " Profile" suffix may not match; that soft-skips rather than crashing.
