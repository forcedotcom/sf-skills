# Authoring a DataMaskPolicy

`DataMaskPolicy` is a **thin Metadata API shell**. Only three elements serialize into its
metadata — `<label>`, `<description>`, `<runOnRefresh>`. Object and field membership is **NOT**
part of the Metadata API shape (`DataMaskPolicy` has `childXmlNames: []` — there is no inline
`<policyObjects>` / `<policyFields>`). Membership lives in two separate **Tooling API** entities,
`DataMaskPolicyObject` and `DataMaskPolicyField`, which you insert as rows.

Authoring a complete, runnable policy from scratch is therefore a **two-step** operation:

1. **Metadata API deploy** the thin `DataMaskPolicy` shell. This is what creates the policy *with
   an active revision* — the child rows in step 2 depend on it.
2. **Tooling API insert** the `DataMaskPolicyObject` (one per target object) and its
   `DataMaskPolicyField` rows (one per masked field).

> **Order matters.** If you create the parent via the Tooling API instead of a Metadata deploy,
> it has no active revision, and the child insert fails with
> `INSUFFICIENT_ACCESS_ON_CROSS_REFERENCE_ENTITY`. Always Metadata-deploy the shell first.

Reuse an existing policy when one fits; author a new one only when needed.

## Reuse first
```bash
sf data query --use-tooling-api --target-org <alias> \
  --query "SELECT Id, DeveloperName, MasterLabel FROM DataMaskPolicy"
```
If a policy already targets the object/fields you need, use its `Id` and skip authoring.

## Step 1 — Metadata-deploy the thin shell

The `.dataMaskPolicy` metadata file carries ONLY these three elements. `<masterLabel>`,
`<developerName>`, `<sampleSize>`, and any membership element are **rejected** — they are not part
of the type. (There is **no `sampleSize` field anywhere** on `DataMaskPolicy` — to mask only a
subset of records, use the row filter on `DataMaskPolicyObject`; see "Masking only a subset" below.)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<DataMaskPolicy xmlns="http://soap.sforce.com/2006/04/metadata">
    <label>Contact PII Mask</label>
    <description>Masks core Contact PII in sandbox.</description>
    <runOnRefresh>false</runOnRefresh>
</DataMaskPolicy>
```

Deploy it in **mdapi (metadata) format** with a `package.xml`. `DataMaskPolicy` has **no
source-format SDR registry entry**, so a `--source-dir` deploy fails with *"Could not infer a
metadata type"*. Lay the file out as `dataMaskPolicies/Contact_PII_Mask.dataMaskPolicy` alongside
a `package.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types>
        <members>Contact_PII_Mask</members>
        <name>DataMaskPolicy</name>
    </types>
    <version>67.0</version>
</Package>
```

```bash
sf project deploy start --metadata-dir <mdapi-dir> --target-org <alias>
```

The developer name of the created policy is the metadata member name (`Contact_PII_Mask`). Resolve
its Id before step 2:
```bash
sf data query --use-tooling-api --target-org <alias> \
  --query "SELECT Id FROM DataMaskPolicy WHERE DeveloperName = 'Contact_PII_Mask'"
```

## Step 2 — Tooling-insert the object + field membership

Insert one `DataMaskPolicyObject` per target object, then one `DataMaskPolicyField` per masked
field against that object's Id.

```bash
# One object row
sf data create record --use-tooling-api --sobject DataMaskPolicyObject --target-org <alias> \
  --values "ParentPolicyId=<policyId> ObjectReference=Contact FilterEnabled=false RunInSerialMode=false"
# → returns the DataMaskPolicyObject Id, use it as <objectId> below

# One field row per masked field
sf data create record --use-tooling-api --sobject DataMaskPolicyField --target-org <alias> \
  --values "ParentPolicyObjectId=<objectId> FieldReference=FirstName MaskingCategory=library MaskValue=first_name"
```

### Field treatment columns

Each `DataMaskPolicyField` carries a `MaskingCategory` plus a `MaskValue` — there is **no
`MaskingRuleType` column** (older docs claiming values like `RandomEmail` / `RandomPhoneNumber`
were wrong; that column does not exist).

- `MaskingCategory` — `library` (pick a value from the built-in library, the common case) or
  `replaceRandom` (random replacement).
- `MaskValue` — a snake_case library token identifying the value set. Verified tokens include:
  `first_name`, `last_name`, `email`, `phone`, `street`, `city`, `state`, `postal_code`,
  `country`, `account_name`, `URL`.

## Choosing treatments

Match the `MaskValue` to the field's semantics — do **not** apply one blanket replacement:

| Field | MaskingCategory | MaskValue |
|-------|-----------------|-----------|
| FirstName | `library` | `first_name` |
| LastName | `library` | `last_name` |
| Email | `library` | `email` |
| Phone / MobilePhone | `library` | `phone` |
| MailingStreet | `library` | `street` |
| MailingCity | `library` | `city` |
| MailingState | `library` | `state` |
| MailingPostalCode | `library` | `postal_code` |
| MailingCountry | `library` | `country` |

Do not mask system fields (`Id`, `CreatedDate`, `OwnerId`, etc.).

## Editing membership

To **add** a field, insert another `DataMaskPolicyField` row. To **remove** one, delete its row:
```bash
sf data delete record --use-tooling-api --sobject DataMaskPolicyField \
  --record-id <fieldRowId> --target-org <alias>
```
The parent `DataMaskPolicy` shell does not need to be redeployed to change membership.

## Masking only a subset of records (a "sample" run)

There is **no `sampleSize`** on `DataMaskPolicy`, and **there is no `LIMIT`** — Data Mask has no
row-cap concept. To process only a subset of an object's rows, you write a **selective `WHERE`
predicate** that genuinely matches fewer rows, on the **`DataMaskPolicyObject`** row (not on the
policy). The masked count equals however many rows satisfy that predicate — so the predicate itself
*is* the subset. Three columns control it:

| Column | Type | Purpose |
|--------|------|---------|
| `FilterEnabled` | boolean | `true` turns the row filter on (default `false` = mask the whole object) |
| `WhereCriteria` | string, **max 40 chars** | A SOQL-style predicate — the human-readable form, e.g. `LastName LIKE '%son%'` |
| `RawFilterData` | textarea (JSON) | The **structured** form the engine actually executes (see the op list below) |

> **The engine masks exactly the rows the predicate matches — there is no `LIMIT`.** A `LIMIT`
> clause in `WhereCriteria` is silently ignored: `LastName != 'X' LIMIT 20` masked **all 407**
> Contacts, because `LastName != 'X'` matches every row and the `LIMIT` did nothing. To mask a
> subset you must pick a predicate that is **actually selective** — e.g. `LastName LIKE '%son%'`
> (25 rows) or `MailingState = 'NY'` (3 rows), verified with a `SELECT COUNT()` first. An
> always-true predicate is **not** a subset.
>
> **`RawFilterData` is what runs — its `operation` must be one of the engine's supported ops:**
> `eq`, `ne`, `lt`, `gt`, `ge`, `le`, `contains`, `not_contains`, `in`, `not_in`. Anything else
> (e.g. `startsWith`) fails the run with a `422` `literal_error`. `LIKE '%son%'` maps to
> `{"operation":"contains","value":"son"}`; `= 'NY'` maps to `{"operation":"eq","value":"NY"}`.
> `WhereCriteria` and `RawFilterData` must express the **same** predicate.
>
> **The predicate must also be valid SOQL** (Data Mask runs a planning `SELECT count() FROM <object>
> WHERE <predicate>` from it). **Do NOT filter on `Id`.** `Id != 'null'` fails with `invalid ID
> field: null` / `INVALID_QUERY_FILTER_OPERATOR` and makes the whole **job fail** with 0 records
> masked. Filter on a text field (`LastName`, `MailingState`, …), not `Id`.

Set them when you insert (or update) the object row. Example — mask the Contacts whose last name
contains `son` (a real subset; verify the count with `SELECT count() FROM Contact WHERE LastName
LIKE '%son%'` first). `RawFilterData` mirrors it with `operation: contains`:
```bash
sf data create record --use-tooling-api --sobject DataMaskPolicyObject --target-org <alias> \
  --values "ParentPolicyId=<policyId> ObjectReference=Contact RunInSerialMode=false \
FilterEnabled=true WhereCriteria=\"LastName LIKE '%son%'\" \
RawFilterData={\"type\":\"and\",\"filters\":[{\"type\":\"field_filter\",\"field\":\"LastName\",\"operation\":\"contains\",\"value\":\"son\"}]}"
```
To turn an existing object row into a subset run, update it instead:
```bash
sf data update record --use-tooling-api --sobject DataMaskPolicyObject --record-id <objectId> \
  --target-org <alias> --values "FilterEnabled=true WhereCriteria=\"LastName LIKE '%son%'\" \
RawFilterData={\"type\":\"and\",\"filters\":[{\"type\":\"field_filter\",\"field\":\"LastName\",\"operation\":\"contains\",\"value\":\"son\"}]}"
```
After the run, confirm the masked count in `DataMaskPolicyJobRunDtl` matches the predicate's row
count and is **less than** `SELECT COUNT() FROM Contact` — proving it masked a subset, not the whole
table. `WhereCriteria` is only **40 characters**, so keep the predicate short.

## Verifying the policy after creation
```bash
# Confirm the object + field membership landed
sf data query --use-tooling-api --target-org <alias> \
  --query "SELECT Id, FieldReference, MaskingCategory, MaskValue FROM DataMaskPolicyField \
           WHERE ParentPolicyObjectId = '<objectId>'"
```
Use the policy `Id` as `<policyId>` in the run/abort sequence (`run-and-abort.md`).
