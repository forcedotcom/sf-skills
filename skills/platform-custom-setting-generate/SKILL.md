---
name: platform-custom-setting-generate
description: "Use this skill when users need to create, generate, or validate Salesforce Custom Setting metadata. Trigger when users mention custom settings (hierarchy or list), customSettingsType, SetupOwnerId, per-profile/per-user config overrides, feature flags, feature toggles, kill switches, or on/off switches admins flip to enable/disable behavior, e.g. bypass triggers/automation during a data load. Also use for \"create a custom setting\" or errors like \"Cannot specify: pluralLabel for CustomSettings\" or a setting that silently deployed as a regular custom object. A trigger bypass or kill switch is just a checkbox on a hierarchy custom setting — generate ONLY the setting, never an Apex trigger/handler. DO NOT TRIGGER for Custom Metadata Types or __mdt objects — route to platform-custom-metadata-type-generate; for business-record objects — use platform-custom-object-generate; for secrets, API keys, passwords, or tokens — recommend a Named Credential, never generated here."
metadata:
  version: "1.0"
  minApiVersion: "60.0"
  domains: ["Platform"]
  relatedSkills:
    - "platform-custom-field-generate"
    - "platform-custom-metadata-type-generate"
    - "platform-custom-object-generate"
  cliTools:
    - tool: ["sf"]
      semver: ">=2.136.8"
---

# Salesforce Custom Setting Generator and Validator

## When to Use This Skill

Use this skill when you need to:

- Create a Hierarchy or List custom setting
- Generate custom setting metadata XML
- Add or validate fields on an existing custom setting
- Populate custom setting **values** (these are data, not metadata — see Section 6)
- Troubleshoot custom setting deployment errors

> **A trigger bypass / kill switch is a Custom Setting — not Apex and not a `__mdt`.** When the user wants a
> switch admins can flip to turn behavior on or off — "disable my Account triggers during a data load", a
> feature toggle, a maintenance-mode flag — generate **only** a hierarchy custom setting with a `Checkbox`
> field (e.g. `Disable_Triggers__c` / `Bypass__c`). Do **not** author the Apex trigger, handler, or test
> that reads it, and do **not** model it as a Custom Metadata Type: the per-profile/per-user override a
> bypass flag needs is exactly what a hierarchy custom setting gives you and a `__mdt` does not. The Apex
> that checks the flag is the developer's to write — this skill generates the setting only.

---

## 1. Overview and Purpose

This document defines the mandatory constraints for generating Custom Setting metadata. A custom setting is
a `CustomObject` with `<customSettingsType>` set — it is **not** a distinct metadata type.

**File extension:** `.object-meta.xml`
**File path:** `force-app/main/default/objects/<Name>__c/<Name>__c.object-meta.xml`
**API name suffix:** `__c` (identical to a regular custom object — the suffix does **not** distinguish them)

> **Values are data, not metadata.** You can generate the setting's *definition* as XML, but you cannot
> deploy its *values* that way. There is no source-format equivalent of `customMetadata/` for custom
> settings. Never generate a file that claims to carry setting values — see **Section 6** for what to do
> instead.

---

## 2. Syntactic Essentials (Tier 1)

### `<customSettingsType>` is mandatory — CRITICAL

**This is the single highest-severity rule in this skill.** Omitting `<customSettingsType>` does not
produce a "you forgot customSettingsType" error. The component silently stops being a custom setting and
is validated as a plain custom object.

The failure is dangerous because it is *recoverable in the wrong direction*: an agent that omits the
element, then obediently fixes each error the platform reports, ends up with a **green deploy and
completely the wrong kind of component**.

| What you see | What it means |
|---|---|
| `Must specify a non-empty plural label for the CustomObject` | You are **NOT** building a custom setting. `customSettingsType` is missing. Add it — do **not** add `pluralLabel`. |
| `Cannot specify: nameField for CustomSettings` | You **ARE** building a custom setting. Remove the named element. |

These two strings are mutually exclusive tells. The giveaway in the first is the phrase
**`for the CustomObject`** and the absence of any mention of custom settings.

**If a deploy reports `Must specify a non-empty plural label for the CustomObject` on something the user
asked to be a custom setting, never satisfy that error by adding `<pluralLabel>`.** Adding it (plus
`nameField`, `deploymentStatus`, and `sharingModel`) makes the deploy succeed and creates a regular custom
object that the user did not ask for.

### Required and Allowed Elements

| Element | Requirement | Notes |
|---------|-------------|-------|
| `<customSettingsType>` | **Required** | `Hierarchy` or `List` — see Section 3 |
| `<label>` | **Required** | Singular UI name |
| `<visibility>` | Always include | `Public`, or `Protected` only in a dev/sandbox/scratch org (Section 5) |
| `<description>` | Always include | Explain what the setting controls and who edits it |
| `<enableFeeds>` | Optional | Accepted |
| `<listViews>` | Optional | Accepted — permitted despite `recordTypes` and `compactLayouts` being forbidden |

### Forbidden Elements

Every element below produces `Cannot specify: <element> for CustomSettings`:

| Forbidden element | Note |
|---|---|
| `<pluralLabel>` | **Required on a regular custom object, forbidden here.** Exactly inverted. |
| `<nameField>` | The `Name` field exists implicitly on List settings |
| `<deploymentStatus>` | |
| `<sharingModel>` | Custom settings are not shared records |
| `<enableActivities>` `<enableReports>` `<enableHistory>` `<enableSearch>` | |
| `<validationRules>` | Enforce these in Apex instead |
| `<recordTypes>` | |
| `<compactLayouts>` | |

**INCORRECT** — carries a regular custom object's required elements:

```xml
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
  <customSettingsType>Hierarchy</customSettingsType>
  <label>Feature Flags</label>
  <pluralLabel>Feature Flags</pluralLabel>        <!-- WRONG: forbidden on custom settings -->
  <sharingModel>ReadWrite</sharingModel>          <!-- WRONG: forbidden -->
  <deploymentStatus>Deployed</deploymentStatus>   <!-- WRONG: forbidden -->
  <nameField>                                    <!-- WRONG: forbidden -->
    <label>Name</label>
    <type>Text</type>
  </nameField>
  <visibility>Public</visibility>
</CustomObject>
```

**Errors:** `Cannot specify: pluralLabel for CustomSettings` · `Cannot specify: sharingModel for CustomSettings` · `Cannot specify: deploymentStatus for CustomSettings` · `Cannot specify: nameField for CustomSettings`

**CORRECT** — minimum valid custom setting:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
  <customSettingsType>Hierarchy</customSettingsType>
  <label>Feature Flags</label>
  <description>Per-profile and per-user toggles for beta features in the ordering app. Edited by admins in Setup.</description>
  <visibility>Public</visibility>
</CustomObject>
```

Note there is no `<fullName>`. A root-level one is tolerated and ignored, but omit it — the API name comes
from the directory and filename.

`<customSettingsType>List</customSettingsType>` deployed without needing the "Manage List Custom Settings
Type" toggle in Setup. That toggle exists in some orgs, so if a List setting is rejected on a
`customSettingsType` grounds in a different org, check Schema Settings before assuming the XML is wrong.

---

## 3. List vs Hierarchy Decision (Tier 2)

`<customSettingsType>` has exactly two values, and the choice changes how rows are addressed.

| | `Hierarchy` | `List` |
|---|---|---|
| **Use when** | The value can vary per profile or per user, with an org-wide fallback | The setting is a small keyed reference table, the same for everyone |
| **Row key** | `SetupOwnerId` (Organization, Profile, or User) | `Name` |
| **Resolution** | User value → Profile value → org default | Look up by `Name` |
| **Apex read** | `MySetting__c.getInstance()` / `getOrgDefaults()` | `MySetting__c.getValues('Key')` / `getAll()` |
| **Typical case** | Feature flags, per-profile limits, debug toggles | Country codes, tax rates by region, integration endpoints by key |

**Default to `Hierarchy`** when the user describes toggles, limits, or anything that "can be overridden."
Choose `List` when they describe a lookup table with named rows.

If the user asks for a keyed reference table that should be **deployable between orgs**, a List custom
setting is usually the wrong answer — its rows are data and will not travel with the deploy. Route to
`platform-custom-metadata-type-generate` instead (Section 7).

---

## 4. Field Rules

Fields on a custom setting are ordinary `CustomField` components at
`objects/<Name>__c/fields/<Field>__c.field-meta.xml`.

**This skill owns the custom-setting-specific deltas only** — the supported-type allowlist and the
`fieldManageability` prohibition below. For everything generic (`<fullName>` derivation, `<label>`,
`<description>`, `<inlineHelpText>`, precision/scale, `<length>`, `externalId`), follow
`platform-custom-field-generate`.

### Supported Field Types

`Checkbox`, `Currency`, `Date`, `DateTime`, `Email`, `Number`, `Percent`, `Phone`, `Text`, `TextArea`, `Url`

`required`, `unique`, `externalId`, and `defaultValue` are accepted on custom setting fields. Whether a
given one applies to a given type is a generic field rule — defer to `platform-custom-field-generate`.

### Unsupported Field Types

`Picklist`, `MultiselectPicklist`, `LongTextArea`, `Html`, `Lookup`, `MasterDetail`, `AutoNumber`,
`Location`, `Time`, `EncryptedText`, and **Formula** (a `<formula>` element on any type).

Every one of these fails with the same bare, uninformative string:

```text
Invalid data type.
```

**This error names neither field nor type.** On a multi-field deploy, read `componentFailures[].fullName`
from the `--json` output to find the culprit — do not guess.

**Roll-up summary fields are structurally impossible here** — a `Summary` needs a master-detail child, and
`MasterDetail` is itself rejected on a custom setting. Don't generate one; the error text varies, so don't
match on a specific string.

**Picklist is the common trap.** Users frequently ask for a picklist on a custom setting. It is not
supported. Use `Text` and enforce the allowed values in Apex, or route the request to
`platform-custom-metadata-type-generate` — CMDT *does* support Picklist.

Near-inversion vs CMDT: `Currency` works here but not on CMDT; `Picklist`/`LongTextArea` work on CMDT but
not here. Never carry field-type assumptions across the two families.

### `<fieldManageability>` is forbidden

That element belongs to CMDT fields only. On a custom setting field it fails with:

```text
Field manageability cannot be set on this entity.
```

---

## 5. Visibility, Secrets, and the No-Silent-Downgrade Rule

### `Protected` is org-type dependent

`<visibility>Protected</visibility>` deploys only in a developer, sandbox, or scratch org. Anywhere else:

```text
You can't set the visibility for a Custom Setting to Protected unless you are in a developer, sandbox, or scratch org.
```

### The no-silent-downgrade rule — CRITICAL

**If `Protected` fails because of the org type, never "fix" it by switching to `Public`.** A silent
downgrade turns a deliberate confidentiality choice into a world-readable component with no signal. Report
it plainly: the org does not permit `Protected`, so the options are a dev/sandbox/scratch org or accepting
`Public` — let the user decide. This applies to any visibility narrowing, not just this error.

### Secrets do not belong in a custom setting

Custom settings are **not** a secret store. Values are readable by anyone who can query the object, and
`Protected` does not change that for code in the same namespace.

When a user asks to store an API key, password, token, client secret, or certificate in a custom setting:

1. **Warn prominently and first** — before generating anything — that a custom setting is the wrong place
   for a credential and the value will be readable.
2. **Recommend the right component** — a **Named Credential** with an **External Credential** for callout
   auth. Say plainly that this skill does not generate those.
3. **If the user still insists, comply** — generate the setting but keep the warning in the response. Do not
   silently refuse, and do not silently obey.

Never route a secret to `Protected` visibility as a compromise: if `Protected` is unavailable (above),
the no-silent-downgrade rule applies with full force, because the downgrade would publish the secret.

---

## 6. Setting Values Are Data, Not Metadata

**A custom setting's rows cannot be deployed as XML.** There is no `customMetadata/`-style folder for them.
Only the object definition and its fields are metadata.

When a user asks to create a setting *with values* — "add a feature flag setting with Beta enabled for
admins" — do all of the following:

1. Generate the object and field XML as normal.
2. **State the limitation in one line:** setting values are data, not metadata, so they are not deployed.
3. **Give ready-to-run commands inline in the chat response**, fully substituted with the real object and
   field API names and the actual values — not a placeholder template, and not written to a file.

All three shapes below are verified working.

### Hierarchy — org-wide default row

**Omit `SetupOwnerId`.** It defaults to the Organization Id, which is exactly the org-default row. No Id
lookup is needed.

```bash
sf data create record --sobject Feature_Flags__c \
  --values "Enable_Beta__c=true Max_Retries__c=3" \
  --target-org <alias>
```

### Hierarchy — profile or user override

This one **does** need an Id, so it is two steps. A user-level override uses the same shape with a `User` Id
in place of the Profile Id (extrapolated from the profile case, not separately verified).

```bash
sf data query --query "SELECT Id FROM Profile WHERE Name='System Administrator'" --target-org <alias>

sf data create record --sobject Feature_Flags__c \
  --values "SetupOwnerId=00eXXXXXXXXXXXXXXX Enable_Beta__c=false" \
  --target-org <alias>
```

An override row coexists with the org-default row; it does not replace it.

### List — one row per key

`Name` is the row key and is required.

```bash
sf data create record --sobject Country_Codes__c \
  --values "Name='US' Iso_Code__c='USA' Dial_Prefix__c='+1'" \
  --target-org <alias>
```

### Quoting

Wrap the whole `--values` argument in double quotes; single-quote any value with a space or shell-special
character (`Environment_Label__c='org default'`). Plain numbers, booleans, and Ids need no inner quotes.

### Consuming a setting in Apex

Values are read through the generated typed class — cached, so reads cost **no SOQL** and are safe inside
loops and triggers. For a **Hierarchy** setting:

```apex
Feature_Flags__c cfg = Feature_Flags__c.getInstance();        // running user: user → profile → org default
Feature_Flags__c org = Feature_Flags__c.getOrgDefaults();     // org-default row only, no hierarchy
Feature_Flags__c forProfile = Feature_Flags__c.getInstance(profileId);  // a User Id works too
Boolean beta = cfg.Enable_Beta__c;
```

`getInstance()` and `getOrgDefaults()` **never return null** (API ≥ 22) — a missing record comes back as an
empty row, so test `org.Id != null` when you need to know whether a real record actually exists. For a
**List** setting, use `getValues('Key')` for one row or `getAll()` for the `Map<String, Feature_Flags__c>`
of every row.

### The in-transaction DML rule

Populating or changing values is **runtime DML** (Apex `insert`/`update`/`upsert`, or the `sf` commands
above) — there is no metadata path. That is the operational face of "values are data," and it has two
consequences worth stating to the user:

- **Writes count against DML governor limits; reads do not.** In a trigger over 200 records, never `upsert`
  the setting once per record — hoist the write out of the loop and do it once.
- **Cross-transaction propagation lags.** After a write, other transactions may briefly read the previous
  value while the org cache propagates; within the same transaction the new value is visible immediately.

---

## 7. Choosing the Right Component

Before generating, confirm a custom setting is actually what the user needs. If it is not, say so and name
the right skill rather than building the wrong thing.

| If the config is… | Use | Why |
|---|---|---|
| Admin-editable per profile/user, or a small keyed table that stays in one org | **Custom Setting** (this skill) | Values are data; they do not travel with a deploy |
| Reference data that must **deploy between orgs** with its records | `platform-custom-metadata-type-generate` | CMDT records are metadata and are deployable |
| Business records users create and edit at runtime | `platform-custom-object-generate` | Custom settings are configuration, not transactional data |
| Translatable UI text | Custom Label — this skill does not generate it | Labels are the supported translation surface |
| Credentials, API keys, tokens, endpoints with auth | Named Credential / External Credential — this skill does not generate them | See Section 5 |
| A permission check in Apex or a flow | Custom Permission — this skill does not generate it | Boolean access checks belong in the permission model |

The distinction that matters most: **CMDT records deploy, custom setting values do not.** If the user says
"and it should ship with these values" or "the same in every org," that is a CMDT request.

---

## 8. Common Deployment Errors

| Error Message | Cause | Fix |
|---|---|---|
| `Must specify a non-empty plural label for the CustomObject` | `<customSettingsType>` is missing, so this is being validated as a regular custom object | Add `<customSettingsType>`. **Do NOT add `<pluralLabel>`** (Section 2) |
| `Cannot specify: pluralLabel for CustomSettings` | `<pluralLabel>` present | Remove it — required on custom objects, forbidden here |
| `Cannot specify: <element> for CustomSettings` (`<element>` = `nameField`, `sharingModel`, `deploymentStatus`, `validationRules`, `recordTypes`, or `compactLayouts`) | A custom-object-only element is present | Remove it (enforce validation logic in Apex instead) |
| `Invalid data type.` | Unsupported field type (Section 4) | Read `componentFailures[].fullName` to find the field; switch to a supported type |
| `Field manageability cannot be set on this entity.` | `<fieldManageability>` on a setting field | Remove it — CMDT only |
| `You can't set the visibility for a Custom Setting to Protected unless you are in a developer, sandbox, or scratch org.` | `Protected` in a production-like org | Report to the user; **never silently switch to `Public`** (Section 5) |

The `Cannot specify:` suffix is `for CustomSettings` (one word) versus CMDT's `for Custom Metadata Type`,
and the visibility error uses `for a Custom Setting` (spaced, singular). Do not assume a shared template
when matching these strings.

---

## 9. Verification Checklist

Before generating custom setting XML, verify:

### Component Identity Checks CRITICAL
- [ ] Is `<customSettingsType>` present and set to `Hierarchy` or `List`?
- [ ] Is the choice between Hierarchy and List justified by the request (overridable vs keyed table)?
- [ ] If a deploy reported `Must specify a non-empty plural label for the CustomObject`, was it fixed by adding `<customSettingsType>` rather than by adding `<pluralLabel>`?
- [ ] **After a successful deploy of a new setting**, was it confirmed to actually *be* a custom setting? Inspecting the XML cannot catch this failure, because the wrong-component outcome deploys green. Run `sf sobject describe --sobject <Name>__c --target-org <alias>` and verify `customSetting` is `true`.

### Syntactic Checks
- [ ] Are `<label>` and `<visibility>` present?
- [ ] Is `<description>` present and specific about what the setting controls?
- [ ] Is `<pluralLabel>` ABSENT?
- [ ] Are `<nameField>`, `<sharingModel>`, and `<deploymentStatus>` ABSENT?
- [ ] Are `<enableActivities>`, `<enableReports>`, `<enableHistory>`, and `<enableSearch>` ABSENT?
- [ ] Are `<validationRules>`, `<recordTypes>`, and `<compactLayouts>` ABSENT?
- [ ] Does the filename match the intended API name, ending in `__c`?

### Field Checks
- [ ] Is every field type in the supported list (Section 4)?
- [ ] Is `Picklist` absent? (unsupported — use `Text`, or route to CMDT)
- [ ] Is every `<formula>` element absent? (formulas are unsupported)
- [ ] Is `<fieldManageability>` ABSENT on every field?
- [ ] Do generic field attributes follow `platform-custom-field-generate`?

### Values Checks
- [ ] If the user asked for values, was the data-not-metadata limitation stated explicitly?
- [ ] Were `sf` commands given **inline in the response**, fully substituted with real API names and real values — not written to a file, not left as a template?
- [ ] For a Hierarchy org default, is `SetupOwnerId` omitted rather than guessed?
- [ ] For a List row, is `Name` supplied?

### Consumption Checks
- [ ] If the user asked how to read the setting, was an Apex snippet given using the generated accessors (`getInstance` / `getOrgDefaults` for Hierarchy, `getValues` / `getAll` for List)?
- [ ] Was the in-transaction DML rule stated — writes are DML that count against limits (bulkify, hoist out of loops), reads are free, and cross-transaction cache propagation lags?

### Security Checks CRITICAL
- [ ] If the request involves a secret, key, token, or password, was the warning given **before** generating, with a Named Credential recommended?
- [ ] Was `Protected` left intact rather than silently downgraded to `Public` on an org-type failure?

### Component-Choice Checks
- [ ] If the values must deploy between orgs, was `platform-custom-metadata-type-generate` recommended instead?
- [ ] If the request is really business records, was `platform-custom-object-generate` recommended instead?
