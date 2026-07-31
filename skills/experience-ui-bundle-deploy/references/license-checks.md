# License pre-checks

Two license gates guard steps that fail with cryptic errors when the org lacks
the right UserLicense. Both are derived from the **self-reg profile** — there is
no separate license config, so the requirement can't drift from the profile the
flow actually assigns. Both only apply **when self-registration is configured**.

Source of truth: reference `org-setup.mjs` `checkDeployLicense` (956-992),
`readProfileUserLicense` (938-944), `checkSelfRegLicense` (895-926), and
`evaluateLicenseRows` (`org-setup-utils.mjs` ~224+).

## Gate 1 — deploy license (pre-deploy, HARD block)

Runs **before** `sf project deploy start` (lines 1478-1483). The profile isn't in
the org yet pre-deploy, so querying `Profile` would only report "profile
missing" — instead, read the required license NAME straight from the local
profile source:

`<packageDir>/main/default/profiles/<selfRegProfile>.profile-meta.xml` →
`<userLicense>...</userLicense>`.

- If the profile file or `<userLicense>` element is absent → nothing to gate on;
  let deploy proceed (line 960).
- Otherwise query the org:
  ```sql
  SELECT LicenseDefinitionKey, Name, Status, TotalLicenses, UsedLicenses
  FROM UserLicense WHERE Name = '<licenseName-escaped>'
  ```
- Zero rows → **block the deploy** with a message NAMING the missing license
  (`required license "<name>" is not present in the org — add it before
  deploying`). Query/parse failure → block. Otherwise run the seat/status check.

This is a hard block (a `StepError`) because deploying without the license fails
anyway, but with an unhelpful error.

## Gate 2 — self-reg license (pre-selfReg, SOFT skip)

Runs **before** the self-reg step (lines 1598-1601). Query the license via the
profile:

```sql
SELECT UserLicense.LicenseDefinitionKey, UserLicense.Name, UserLicense.Status,
       UserLicense.TotalLicenses, UserLicense.UsedLicenses
FROM Profile WHERE Name = '<selfRegProfile>'
```

A query failure, zero rows, inactive license, or no free seats is a **soft skip**:
warn with the specific reason and record the step skipped. Self-registration
being unavailable is not a setup failure.

## Seat / status math (`evaluateLicenseRows`)

Done client-side because SOQL can't compare two fields. The license is
**satisfied** only when it is **Active** and either `UsedLicenses < TotalLicenses`
or `TotalLicenses === -1` (the documented "unlimited" sentinel — treat it as
always having free seats). Report the specific reason (missing / inactive / no
seats) so the user knows exactly what to fix.

## SOQL-safety of the profile name

- In Gate 2 the profile name is **validate-and-fail**: a `'`, `\`, or control
  char throws a config error rather than being escaped (developer config, not
  user input).
- In Gate 1 the license NAME read from the profile XML is **escaped** for the
  SOQL literal (`escapeSoqlString`).
