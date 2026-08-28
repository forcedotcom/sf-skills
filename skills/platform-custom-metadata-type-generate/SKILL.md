---
name: platform-custom-metadata-type-generate
description: "Use this skill when users need to create, generate, or validate Salesforce Custom Metadata Type metadata — the __mdt object, its fields, and its deployable records. Trigger when users mention custom metadata types, CMDT, __mdt objects, custom metadata records, .md-meta.xml files, or reference/config data that must ship between orgs. Also trigger for admin-maintained mapping, lookup, or crosswalk tables and field mappings (\"map fields from A to B\", code lookups) — config admins change without a code deploy belongs in a CMDT, never hardcoded in Apex or Flow — and when troubleshooting CMDT record/type deploy errors. DO NOT TRIGGER for Custom Settings — route to platform-custom-setting-generate; for regular custom objects holding business records — use platform-custom-object-generate; or for secrets and API keys — recommend a Named Credential, which this skill never generates."
metadata:
  version: "1.0"
  minApiVersion: "60.0"
  domains: ["Platform"]
  relatedSkills:
    - "platform-custom-field-generate"
    - "platform-custom-object-generate"
    - "platform-custom-setting-generate"
  cliTools:
    - tool: ["sf"]
      semver: ">=2.136.8"
---

# Salesforce Custom Metadata Type Generator and Validator

## When to Use This Skill

Use this skill when you need to:

- Create a Custom Metadata Type (`__mdt`)
- Generate or validate CMDT fields, including `MetadataRelationship` fields
- Generate CMDT **records** as deployable `.md-meta.xml` files
- Troubleshoot CMDT deployment errors

---

## 1. Overview and Purpose

A Custom Metadata Type produces **two separate artifact families**, and most requests need both:

| Artifact | Path | Metadata type |
|---|---|---|
| Type definition | `objects/<Name>__mdt/<Name>__mdt.object-meta.xml` | `CustomObject` |
| Fields | `objects/<Name>__mdt/fields/<Field>__c.field-meta.xml` | `CustomField` |
| Records | `customMetadata/<Name>.<Record>.md-meta.xml` | `CustomMetadata` |

**API name suffix:** `__mdt` on the type; fields still end in `__c`.

**The defining advantage over a custom setting: CMDT records are metadata and therefore deploy between
orgs.** When a user says configuration should "ship with the package" or "be the same in every org," CMDT
is the right answer.

> **The root element is `<CustomObject>`, but almost none of a custom object's rules apply.** `sharingModel`,
> `nameField`, and `deploymentStatus` are required or normal on a regular custom object and are **hard
> errors** here. Do not carry assumptions across from `platform-custom-object-generate`.

---

## 2. Syntactic Essentials — Type Definition (Tier 1)

### Required and Allowed Elements

| Element | Requirement | Notes |
|---------|-------------|-------|
| `<label>` | **Required** | Singular UI name |
| `<pluralLabel>` | **Required** | Omitting it gives `Must specify a non-empty plural label for the CustomObject` |
| `<visibility>` | Always include | `Public`, or `Protected`/`PackageProtected` only in dev/sandbox/scratch (Section 6) |
| `<description>` | Always include | What this type configures and who owns it |

`<pluralLabel>` being **required here but forbidden on a custom setting** is the most commonly inverted
rule between the two families. Neither failure mentions the other family's rule.

### Forbidden Elements

Every element below produces `Cannot specify: <element> for Custom Metadata Type` — reusing a regular custom
object's skeleton (with `sharingModel`, `deploymentStatus`, a `nameField` block, or `enableSearch`) is the
usual cause:

`sharingModel`, `nameField`, `deploymentStatus`, `enableActivities`, `enableReports`, `enableHistory`,
`enableSearch`

**CORRECT** — minimum valid `__mdt` type:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
  <label>Partner Tier</label>
  <pluralLabel>Partner Tiers</pluralLabel>
  <description>Discount and threshold configuration per partner tier. Ships with the package; edited by the revenue ops team.</description>
  <visibility>Public</visibility>
</CustomObject>
```

---

## 3. Field Rules

**This skill owns the CMDT-specific deltas only** — the type allowlist, `fieldManageability`, and
`MetadataRelationship` below. For generic field mechanics (`<fullName>` derivation, `<label>`,
`<description>`, `<inlineHelpText>`, precision/scale, `<length>`, `visibleLines`), follow
`platform-custom-field-generate`.

### Supported Field Types

`Checkbox`, `Date`, `DateTime`, `Email`, `Number`, `Percent`, `Phone`, `Picklist`, `Text`, `TextArea`,
`LongTextArea`, `Url`, plus `MetadataRelationship`.

### Unsupported Field Types

`Currency`, `AutoNumber`, `MasterDetail`, `Summary`, `Location`, `Time`, `EncryptedText`, `Html`,
`MultiselectPicklist`. Each fails with a precise, well-formed error:

```text
Type {TypeName} of CustomMetadataField {Object}__mdt.{Field}__c is not supported for the Entity {Object}__mdt
```

(There is no trailing period.) Example: `Type Currency of CustomMetadataField Partner_Tier__mdt.Discount__c is not supported for the Entity Partner_Tier__mdt`

**Currency is the common trap** — it works on a custom setting but not here. Use `Number` with
`<precision>`/`<scale>` and put the currency in the label or help text.

**Formula fields are unsupported**, but they break the pattern above. A `<formula>` element on an otherwise
legal type gives only:

```text
Invalid data type.
```

### `Lookup` is silently coerced — CRITICAL

`<type>Lookup</type>` on a `__mdt` **does not fail** when its `referenceTo` resolves to a real sObject: the
deploy is green and the platform silently rewrites the field to `MetadataRelationship`. A later retrieve
shows a field the user never wrote:

```xml
<type>MetadataRelationship</type>   <!-- was deployed as Lookup -->
```

**Always write `MetadataRelationship` explicitly.** Emitting `Lookup` produces a green deploy and a
source-vs-org mismatch that churns in git the first time anyone retrieves. (Reproduced on a live deploy: a
resolvable `Lookup` returns as `MetadataRelationship`; a non-resolvable `referenceTo` is cleanly rejected.)

### `MetadataRelationship`

Three targets, all valid. `referenceTo` selects which.

| `<referenceTo>` | Purpose | Extra requirement |
|---|---|---|
| Another `__mdt` type | Link two custom metadata types | Must be a *different* type |
| `EntityDefinition` | Point at an sObject | None |
| `FieldDefinition` | Point at a field | **Requires `<metadataRelationshipControllingField>`** |

```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
  <fullName>Target_Field__c</fullName>
  <label>Target Field</label>
  <type>MetadataRelationship</type>
  <referenceTo>FieldDefinition</referenceTo>
  <metadataRelationshipControllingField>Partner_Tier__mdt.Target_Object__c</metadataRelationshipControllingField>
  <relationshipLabel>Target Field</relationshipLabel>
  <relationshipName>Target_Field</relationshipName>
</CustomField>
```

The controlling field must be an `EntityDefinition` relationship **on the same type**, referenced as
`Type__mdt.Field__c`. Omitting it gives `Metadata relationships to Field Definition require a controlling field.`

**Self-references are impossible.** Pointing a `MetadataRelationship` at its own parent type fails with
`Cannot add a self-lookup relationship child with cascade or restrict options to the object itself` (verbatim
from a live `__mdt` deploy) — use a second type.

### `<fieldManageability>`

**Optional. It defaults to `DeveloperControlled`** — do not add it unless the user wants a different value.
Valid values are `DeveloperControlled`, `SubscriberControlled`, and `Locked`.

It is valid **only** on `__mdt` fields. On a regular custom object field or a custom setting field:

```text
Field manageability cannot be set on this entity.
```

---

## 4. CMDT Records (`.md-meta.xml`)

### Filename convention

Write `customMetadata/<TypeNameWithout__mdt>.<RecordDeveloperName>.md-meta.xml`.

```text
customMetadata/Partner_Tier.Bronze_AMER.md-meta.xml
```

The `__mdt` suffix in the filename also deploys and creates a real record, so it is tolerated — but
Salesforce's retrieve normalizes to the no-suffix form, so always write it without `__mdt` to avoid git
churn (detail in `references/cmdt-records.md`).

### Required namespaces

All three are mandatory on the root element — `xsi:type` on values will not resolve without them.

```xml
<CustomMetadata xmlns="http://soap.sforce.com/2006/04/metadata"
                xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
```

### `xsi:type` mapping — every value needs one

| Field type | Correct `xsi:type` | Example value |
|---|---|---|
| Checkbox | `xsd:boolean` | `true` |
| Date | `xsd:date` | `2024-01-15` |
| DateTime | `xsd:dateTime` | `2024-01-15T10:30:00.000Z` |
| Number, Percent | `xsd:double` | `42.0` |
| Text, TextArea, LongTextArea | `xsd:string` | `some text` |
| Email, Phone, Url | `xsd:string` | `a@b.com` |
| **Picklist** | **`xsd:string`** | `Beta` |
| MetadataRelationship → `EntityDefinition` | `xsd:string` | `Account` |
| MetadataRelationship → `FieldDefinition` | `xsd:string` | `Account.Name` |
| *any type, null* | *no `xsi:type`* — write `<value xsi:nil="true"/>` | |

A value pointing at **another `__mdt` type** via `MetadataRelationship` was not verified — expect
`xsd:string` with the target's DeveloperName, but confirm.

### `xsd:picklist` must not be emitted — CRITICAL

**Salesforce's own documentation tells you to use `xsd:picklist` for Picklist fields. It is wrong** — it is
not a valid XML Schema type. Instead of a clean validation error, the platform fails the entire deploy
server-side with no component-level diagnostics, taking every other component down with it. **Always emit
`xsd:string` for a Picklist field's value; never `xsd:picklist`.** See `references/cmdt-records.md` §2.

### Record body rules

- `<label>` is **required**. Omitting it gives `Required fields are missing: [MasterLabel]` — note it reports
  the sObject field name `MasterLabel`, not `label`.
- `<protected>` is optional and defaults to `false`.
- Never put `<fullName>` inside a `<values>` block — it is a hard parse error.
- `<value xsi:nil="true"/>` works on optional fields. On a **required** field it is rejected exactly as if
  the field were absent. Omitting `xsi:type` on a non-nil value is always fatal, including for text fields.

**CORRECT** — a complete record:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomMetadata xmlns="http://soap.sforce.com/2006/04/metadata"
                xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <label>Bronze AMER</label>
  <protected>false</protected>
  <values>
    <field>Discount_Percent__c</field>
    <value xsi:type="xsd:double">5.0</value>
  </values>
  <values>
    <field>Region__c</field>
    <value xsi:type="xsd:string">AMER</value>
  </values>
  <values>
    <field>Effective_Date__c</field>
    <value xsi:type="xsd:date">2024-01-15</value>
  </values>
  <values>
    <field>Notes__c</field>
    <value xsi:nil="true"/>
  </values>
</CustomMetadata>
```

### Record DeveloperName rules

The name is the second segment of the filename. It must begin with a letter, contain only alphanumerics and
underscores, not end with an underscore, not contain two consecutive underscores, and be **at most 40
characters**. Violations give:

```text
Custom Metadata Record Name: The <Type>__mdt API Name can only contain underscores and alphanumeric characters. It must be unique, begin with a letter, not include spaces, not end with an underscore, and not contain two consecutive underscores.
```

Over 40 characters gives `Value too long for field: fullName maximum length is:40` (no space after the colon).

### Deploy ordering

**No ordering constraint** — the type and every referenced field only need to *resolve* (already in the org,
or present in the same deploy). Two failures tell you what is missing:
`Custom metadata type <Type>__mdt is not available in this organization.` (the type is missing) and
`<Type>__mdt: could not find fields: <Field>__c` (the type exists but the field does not).

→ Full record-value error catalog and the `xsi:type` coercion asymmetry: **`references/cmdt-records.md`**.

### Generating records from user input

Record data arrives three ways; in each case emit **one `<Type>.<Record>.md-meta.xml` per row**, mapping
columns to `<field>`/`<value>` pairs with the right `xsi:type`:

- **Inline list/table** — map columns straight to fields.
- **CSV** — header = field API names (or map labels to them), each line = one record; take the DeveloperName
  from a key column.
- **Prose** — infer the rows ("Bronze at 5%, Gold at 15%") and confirm the field mapping before generating.

Derive every DeveloperName **deterministically** from the key column or label — never free-hand one. For each
row, run `scripts/sanitize-developer-name.sh "<LABEL>" <ROW>` **before** writing its record file (same input →
same valid name; empty/all-symbol/non-Latin labels fall back to `Record_<ROW>`).

The transform is **many-to-one** — `United States` and `United-States` both yield `United_States`, and since
each record is `<Type>.<DeveloperName>.md-meta.xml`, a collision silently overwrites a row. After deriving the
whole batch, check duplicates **before writing**; on any collision **stop and report the colliding source
labels** rather than overwrite (append a deterministic `_2`/`_3` suffix only if the user asks to auto-resolve).
Ordered algorithm, ASCII-only limitation, uniqueness check, and worked examples: **`references/cmdt-records.md` §7**.

### Consuming records in Apex

Records are read through the generated typed class — **no SOQL, no query rows consumed**, safe in loops and
triggers:

```apex
Map<String, Partner_Tier__mdt> all = Partner_Tier__mdt.getAll();
Partner_Tier__mdt bronze = Partner_Tier__mdt.getInstance('Bronze_AMER');  // by DeveloperName
```

**Accessor truncation — CRITICAL for `LongTextArea`.** `getAll()`/`getInstance()` return only the **first
255 characters** of any field; longer `LongTextArea` values are silently truncated for those callers and
must be read via SOQL (`SELECT ... FROM Partner_Tier__mdt`). Say so whenever you put a `LongTextArea` on a
CMDT.

---

## 5. Choosing the Right Component

Before generating, confirm a CMDT is what the user needs.

| If the config is… | Use | Why |
|---|---|---|
| Reference data that must **deploy between orgs** with its records | **CMDT** (this skill) | Records are metadata |
| An admin-maintained **mapping / lookup / crosswalk** table (field↔field, code↔code, "map A to B") | **CMDT** (this skill) | Editable reference data, one record per pair |
| Admin-editable per profile/user, or org-local | `platform-custom-setting-generate` | Values are data and stay in one org |
| Business records users create and edit at runtime | `platform-custom-object-generate` | CMDT records are not transactional data |
| Translatable UI text | Custom Label — not generated here | Labels are the translation surface |
| Credentials, API keys, tokens | Named Credential / External Credential — not generated here | See Section 6 |
| A permission check in Apex or a flow | Custom Permission — not generated here | Boolean access belongs in the permission model |

The distinction that matters most: **CMDT records deploy, custom setting values do not.** If the user needs
admins to edit values per profile at runtime, that is a custom setting, not a CMDT.

> **Field-mapping and lookup tables are a canonical CMDT use case.** When a user asks to "map fields from A
> to B," maintain a code-to-code lookup, or keep a crosswalk admins can edit, model it as a CMDT — one record
> per pair (e.g. `Lead_Field__c`/`Target_Field__c`, or `MetadataRelationship` fields to `FieldDefinition`) —
> **never** a hardcoded Apex `Map`, constant, or Flow decision. Phrasing like "for conversion" or "for our
> integration" does not make it code: if admins maintain the pairs without a deploy, it is CMDT reference data.

---

## 6. Visibility, Secrets, and the No-Silent-Downgrade Rule

### `Protected` and `PackageProtected` are org-type dependent

Both deploy only in a developer, sandbox, or scratch org. Anywhere else:

```text
You can't set the visibility for a Custom Metadata Type to Protected unless you are in a developer, sandbox, or scratch org.
```

`PackageProtected` gives the same string with `PackageProtected` substituted. The failure is confirmed in a
production-like org; that these values *succeed* in a dev, sandbox, or scratch org is taken from the message
text rather than separately tested.

### The no-silent-downgrade rule — CRITICAL

**If `Protected` fails because of the org type, never "fix" it by switching to `Public`.** Stop and tell the
user. A silent downgrade turns a deliberate confidentiality choice into a world-readable component with a
green deploy and no warning — the worst possible outcome, because nothing signals that anything changed.

Report the situation instead: the org does not permit `Protected`, so the options are to deploy to a
dev/sandbox/scratch org or to accept `Public`. Let the user choose.

This applies to any narrowing of visibility, not only this error.

### Secrets do not belong in a CMDT

A CMDT is **not** a secret store. `Protected` restricts access from outside the namespace, but it is not
encryption and it does not protect the value from code or admins inside it.

When a user asks to store an API key, password, token, client secret, or certificate in a CMDT:

1. **Warn prominently and first** — before generating anything — that a CMDT is the wrong home for a
   credential, and that `Protected` is not encryption.
2. **Recommend the right component** — a **Named Credential** with an **External Credential**. Say plainly
   that this skill does not generate them.
3. **If the user still insists, comply** — generate the CMDT with `Protected` visibility where the org
   allows it, and keep the warning in the response. Do not silently refuse, and do not silently obey.

**The two rules compose, and the order matters.** If the user insists on a CMDT for a secret *and* the org
rejects `Protected`, the no-silent-downgrade rule is what prevents the key from landing in a `Public`
component. Stop and report — never downgrade a secret-bearing type to `Public`.

---

## 7. Deployment Error Reference

Every type- and field-level error string is stated inline in Sections 2–4, next to the mistake that causes
it (`Cannot specify: <element> for Custom Metadata Type`, the unsupported-type string, `Invalid data type.`
for a formula, `Field manageability cannot be set on this entity.`, the `MetadataRelationship` controlling-
field and self-lookup errors, and the `Must specify a non-empty plural label` case).

The **full verbatim record-value catalog** — every wrong-`xsi:type` rejection, `Required fields are missing:
[MasterLabel]`, nil-on-required, the DeveloperName rules, and the exact-text traps (field named by Label not
API name, the doubled space and `i.g.` typo in the no-`xsi:type` error, `maximum length is:40` with no
space) — is in **`references/cmdt-records.md`**.

One matching caution: the suffix here is `for Custom Metadata Type` (spaced, title case); custom settings
use `for CustomSettings`. Do not assume a shared template when matching these strings.

---

## 8. Verification Checklist

### Type Definition Checks
- [ ] Are `<label>`, `<pluralLabel>`, and `<visibility>` all present?
- [ ] Is `<description>` present and specific?
- [ ] Are `<sharingModel>`, `<nameField>`, and `<deploymentStatus>` ABSENT?
- [ ] Are `<enableActivities>`, `<enableReports>`, `<enableHistory>`, and `<enableSearch>` ABSENT?
- [ ] Does the directory and filename end in `__mdt`?

### Field Checks
- [ ] Is every field type in the supported list (Section 3)?
- [ ] Is `Currency` absent? (unsupported here — use `Number`)
- [ ] Is every `<formula>` element absent?
- [ ] Is `<type>Lookup</type>` absent, written as `MetadataRelationship` instead? CRITICAL — `Lookup` deploys silently and is rewritten
- [ ] For `FieldDefinition` relationships, is `<metadataRelationshipControllingField>` present?
- [ ] Does no `MetadataRelationship` point at its own parent type?
- [ ] Is `<fieldManageability>` omitted unless a non-default value was requested?

### Record Checks CRITICAL
- [ ] Is the filename `<Type>.<Record>.md-meta.xml` **without** `__mdt`?
- [ ] Are all three namespaces (`xmlns`, `xmlns:xsd`, `xmlns:xsi`) on the root element?
- [ ] Does every non-nil `<value>` carry an `xsi:type`?
- [ ] Is `xsi:type="xsd:picklist"` absent everywhere? (crashes the whole deploy — use `xsd:string`)
- [ ] Does each `xsi:type` match the field type per the Section 4 table?
- [ ] Is `<label>` present on every record?
- [ ] Is `<fullName>` absent from every `<values>` block?
- [ ] Is every required field given a real value rather than `xsi:nil="true"`?
- [ ] Is every record DeveloperName ≤ 40 characters, starting with a letter, no spaces or hyphens?
- [ ] If records came from a batch/list/CSV, are all derived DeveloperNames distinct (checked with `sort | uniq -d`), with any collision reported rather than silently overwriting a row? CRITICAL — a collision loses a record with no deploy error
- [ ] Does every `<field>` name a field that exists on the type or is in this deploy?
- [ ] If records came from a list, CSV, or prose description, is there exactly one file per row with the columns mapped to the right fields?

### Consumption Checks
- [ ] If the user asked how to read the records, was an Apex snippet given using `getAll()` / `getInstance(developerName)`?
- [ ] If any record populates a `LongTextArea`, was the user warned the accessors truncate to 255 characters and that SOQL is needed for the full value?

### Security Checks CRITICAL
- [ ] If the request involves a secret, key, token, or password, was the warning given **before** generating, with a Named Credential recommended?
- [ ] Was `Protected` left intact rather than silently downgraded to `Public` on an org-type failure?

### Component-Choice Checks
- [ ] If admins need to edit values per profile or user at runtime, was `platform-custom-setting-generate` recommended instead?
- [ ] If the data is really transactional business records, was `platform-custom-object-generate` recommended instead?

---

## Reference File Index

| File | When to read |
|------|-------------|
| `references/cmdt-records.md` | Debugging a CMDT record deploy — full verbatim record-value error catalog, the type-coercion asymmetry (which `xsi:type` mismatches the platform silently accepts), and worked record examples |
