# CMDT Records — Value Typing, Coercion, and Error Reference

Depth reference for `customMetadata/<Type>.<Record>.md-meta.xml`. Read this when a record deploy fails, or
when deciding whether an `xsi:type` mismatch is actually a problem.

Every error string in Section 3 is verbatim from `componentFailures[].problem` in
`sf project deploy start --json`.

---

## 1. The type check is asymmetric

There is **no single "types must match" rule.** Some mismatches are silently accepted, others are rejected.
Knowing which prevents both false alarms and missed bugs.

| Field type | `xsi:type` used | Outcome |
|---|---|---|
| Number | `xsd:double` | accepted (canonical) |
| Number | `xsd:int` | **accepted** |
| Number | `xsd:string` (`42`) | **accepted** |
| Number | `xsd:boolean` | rejected — `S Number: value not of required type: true` |
| Number | `xsd:double` with value `abc` | rejected at parse — `Error parsing file: 'abc' is not valid for the type xsd:double` |
| Date | `xsd:date` | accepted (canonical) |
| Date | `xsd:dateTime` | **accepted** |
| Date | `xsd:string` | rejected — `S Date: value not of required type: 2024-01-15` |
| DateTime | `xsd:dateTime` | accepted (canonical) |
| DateTime | `xsd:date` | **accepted** |
| DateTime | `xsd:string` | rejected — `S DateTime: value not of required type: 2024-01-15T10:30:00.000Z` |
| Checkbox | `xsd:boolean` | accepted (canonical) |
| Checkbox | `xsd:string` | rejected — `S Checkbox: value not of required type: true` |
| Checkbox | `xsd:int` | rejected — `S Checkbox: value not of required type: 1` |
| Text | `xsd:string` | accepted (canonical) |
| Text | `xsd:double` | rejected — `S Text: value not of required type: 42.5` |

**Summary of the pattern:** `Number` accepts `xsd:string` and `xsd:int`; Date and DateTime interconvert
freely; **Checkbox and Text are strict.** The most common real-world failure is a Date field given
`xsi:type="xsd:string"`. Only `Number` was probed among the numeric types — do not assume `Percent` behaves
identically.

Always emit the canonical type from the main skill's Section 4 table. The tolerances above are for
diagnosing existing files, not a licence to be loose in generated output.

### `Percent`, `Email`, `Phone`, `Url`, `TextArea`, `LongTextArea`

Their canonical types are confirmed correct by a successful all-fields record deploy, but they were not
individually probed with *wrong* types, so no per-field verbatim rejection string exists. The
`value not of required type` shape is expected to hold, since it held for Date, DateTime, Number, Checkbox,
and Text.

---

## 2. `xsd:picklist` — the documented type that must not be emitted

Salesforce's documentation lists `xsd:picklist` for Picklist fields. It is **not a valid XML Schema type**,
and the platform does not reject it cleanly: instead of a component-level validation error it fails the whole
deploy server-side with no component diagnostics, taking every other component in the deploy down with it.

**Always emit `xsi:type="xsd:string"` for a Picklist field's value; never `xsd:picklist`.** This is the
canonical typing from the main skill's Section 4 table, so following the generation rule avoids the failure
entirely.

---

## 3. Full record error catalog

| What was wrong | VERBATIM error string |
|---|---|
| Date field with `xsi:type="xsd:string"` | `S Date: value not of required type: 2024-01-15` |
| Checkbox field with `xsi:type="xsd:string"` | `S Checkbox: value not of required type: true` |
| Checkbox field with `xsi:type="xsd:int"` | `S Checkbox: value not of required type: 1` |
| Number field with `xsi:type="xsd:boolean"` | `S Number: value not of required type: true` |
| DateTime field with `xsi:type="xsd:string"` | `S DateTime: value not of required type: 2024-01-15T10:30:00.000Z` |
| Text field with `xsi:type="xsd:double"` | `S Text: value not of required type: 42.5` |
| `xsd:double` with non-numeric text | `Error parsing file: 'abc' is not valid for the type xsd:double` |
| Restricted Picklist, value not in the value set | `S Picklist: bad value for restricted picklist field: NotAValidEntry` |
| Text(255) given 300 characters | `S Text: data value too large: AAAA…AAAA (max length=255)` |
| `<value>` with no `xsi:type` | `Error parsing file:  Only the following configurations are supported : 1) if the type is mentioned i.g. type="xsi:boolean" 2) With metadata CRUD API with fullName required` |
| `<value xsi:nil="true"/>` on a **required** field | `Required fields are missing: [ReqText__c]` |
| Required field omitted entirely | `Required fields are missing: [ReqText__c]` |
| `<label>` omitted | `Required fields are missing: [MasterLabel]` |
| `<fullName>` inside a `<values>` block | `Error parsing file: Element {http://soap.sforce.com/2006/04/metadata}fullName invalid at this location in type CustomMetadataValue` |
| `<field>` naming a nonexistent field | `Probe01__mdt: could not find fields: Does_Not_Exist__c` |
| Record whose type doesn't exist and isn't in the deploy | `Custom metadata type Probe99__mdt is not available in this organization.` |
| DeveloperName starting with a digit, containing a space, or containing a hyphen | `Custom Metadata Record Name: The Probe01__mdt API Name can only contain underscores and alphanumeric characters. It must be unique, begin with a letter, not include spaces, not end with an underscore, and not contain two consecutive underscores.` |
| DeveloperName over 40 characters | `Value too long for field: fullName maximum length is:40` |

### Exact-text notes

These are easy to get wrong when matching strings:

- **Errors name the field by its Label, not its API name.** `S Date: …` where the API name is `S_Date__c`.
  Map errors back to files using the label, or the `fullName`/`fileName` on the failure object.
- The no-`xsi:type` error has **two spaces** after `Error parsing file:`, a **space before the colon** in
  `supported :`, and the typo `i.g.` rather than `e.g.`. Confusingly, the example it prints is
  `type="xsi:boolean"` even though the attribute you must write is `xsi:type="xsd:boolean"`.
- The `fullName invalid at this location` error has **one** space after `Error parsing file:` and no
  trailing period.
- The length error is the literal string `S Text: data value too large: `, then the full untruncated value,
  then ` (max length=255)`.
- The DeveloperName error names the type **with** the `__mdt` suffix even though the filename omits it.
- `maximum length is:40` has **no space** after the final colon. The limit is on the record DeveloperName.
- `Required fields are missing: [MasterLabel]` reports the sObject field name, not the metadata element
  name `label`.

---

## 4. Deploy ordering — precise

**There is no ordering constraint between a type and its records.** The only rule is that the type and every
referenced field must *resolve* — either already present in the org, or present in the same deploy.

| Case | Result |
|---|---|
| Records alone, type and fields already in the org | **Succeeds** |
| Type + fields + records in one deploy | **Succeeds** |
| Records alone, type does not exist anywhere | **Fails** — `Custom metadata type <Type>__mdt is not available in this organization.` |

The common claim that "the type must be in the same deploy as the records" is **not** a platform rule.
Including the type is one way to satisfy resolution; deploying it earlier is equally valid. That claim
usually comes from hitting the third row.

Two distinct errors distinguish the failure modes:

- `Custom metadata type <Type>__mdt is not available in this organization.` — the **type** is missing.
- `<Type>__mdt: could not find fields: <Field>__c` — the type exists, the **field** is missing.

---

## 5. Other record body rules

- `<protected>` is optional and defaults to `false`. The platform emits `<protected>false</protected>` on
  retrieve.
- `<value xsi:nil="true"/>` is what the platform itself emits for every unpopulated field on retrieve, so it
  is the canonical way to represent a null. On a required field it is rejected exactly as if the field were
  absent.
- Omitting `xsi:type` on a non-nil value is **always** fatal, including for string fields.
- Deploys are atomic. When a batch mixes good and bad components, the good ones appear in
  `componentSuccesses` but are still rolled back — a component listed as a success did not necessarily
  persist.
- `fileName` in the failure payload is the **MDAPI** path (`customMetadata/X.md`, `objects/Y.object`), never
  the source-format path you wrote. Do not pattern-match it expecting `-meta.xml`.

---

## 6. Filename convention — why the no-suffix form wins

Both `Type__mdt.Record.md-meta.xml` and `Type.Record.md-meta.xml` deploy successfully and create real
records, so the `__mdt` suffix is tolerated rather than required.

Salesforce's own tooling settles which to write. After records deployed under **both** spellings existed in
the org, `sf project retrieve start --metadata CustomMetadata` wrote:

```text
force-app/main/default/customMetadata/Probe01.Rec1.md-meta.xml
force-app/main/default/customMetadata/Probe01.Rec2.md-meta.xml
```

The record originally deployed *with* the suffix came back **without** it. Retrieve normalizes to the
no-suffix form, so writing the suffixed form guarantees git churn the first time anyone retrieves.

The MDAPI `fileName` in the deploy payload agrees: `customMetadata/Probe01.Rec1.md`.

Note that the platform still *reports* the type with the suffix in error text — a record file named
`Probe99.Orphan.md-meta.xml` errors with `Custom metadata type Probe99__mdt is not available in this
organization.`

---

## 7. Record DeveloperName sanitization — the deterministic transform

The DeveloperName is the second filename segment (`<Type>.<DeveloperName>.md-meta.xml`) and the key passed to
`getInstance('<DeveloperName>')`. The per-label transform is a pure function — the same label always yields
the same name (no divergence) — but it is **many-to-one**: different labels can map to the same name, so a
per-batch uniqueness check (step 7) is required on top of it. Apply these steps **in order**:

1. Replace every run of non-alphanumeric characters (spaces, punctuation, accents) with a single `_`.
2. Strip any leading `_`.
3. If the result now starts with a digit, prefix `X` (Salesforce's own convention for number-leading names).
4. Strip any trailing `_`.
5. Truncate to 40 characters, then strip a trailing `_` the cut may have introduced.
6. If the result is empty (an all-symbol or non-Latin label folds to nothing), emit the deterministic
   fallback `Record_<rowIndex>` (1-based source position) — never an empty name, and never a free-handed literal.
7. Across the **whole batch**, enforce uniqueness (see below) — steps 1–6 guarantee a *valid* name, not a
   *distinct* one.

Canonical implementation — invoke the skill-local script (same `$LABEL` at a given `$ROW` → same valid name;
the empty-guard lives **in the script**, not in prose):

```bash
scripts/sanitize-developer-name.sh "$LABEL" "$ROW"
```

Equivalent inline form of what the script runs:

```bash
name=$(printf '%s' "$LABEL" \
  | sed -E 's/[^A-Za-z0-9]+/_/g; s/^_+//; s/^([0-9])/X\1/; s/_+$//' \
  | cut -c1-40 | sed -E 's/_+$//')
[ -z "$name" ] && name="Record_$ROW"   # all-symbol / non-ASCII label collapsed to empty; $ROW = 1-based source position
printf '%s' "$name"
```

Worked examples:

| Source label | DeveloperName |
|---|---|
| `United States` | `United_States` |
| `Gold (EMEA)` | `Gold_EMEA` |
| `2024 Q1` | `X2024_Q1` |
| `ACME — West` | `ACME_West` |
| `Côte d'Ivoire` | `C_te_d_Ivoire` |

Every output satisfies the "Record DeveloperName rules" in the skill: letter-first, alphanumerics and single
underscores only, no leading/trailing underscore, ≤ 40 characters.

**The transform is ASCII-only and lossy for accented / non-Latin labels.** Step 1 folds any character outside
`[A-Za-z0-9]` to `_` — it does **not** transliterate — so `Côte d'Ivoire → C_te_d_Ivoire` (the `ô` becomes
`_`) and `中文 → Record_<rowIndex>` (via the step-6 fallback). Because the DeveloperName is the
`getInstance('<name>')` API key, this is lossy and collision-prone. When a label set relies on non-ASCII
distinctions, transliterate to ASCII first (e.g. `Côte → Cote`) or have the user supply explicit
DeveloperNames rather than deriving them.

### Uniqueness across the batch (step 7)

Steps 1–6 are **many-to-one**. `United States` and `United-States` both collapse to `United_States` (step 1
folds every punctuation/accent run to a single `_`), and step 5's 40-char cut makes any two labels sharing
their first 40 sanitized characters collide as well. Because each record is written to
`<Type>.<DeveloperName>.md-meta.xml`, a collision **silently overwrites** the earlier row — you lose a record
with no deploy error.

So after deriving names for **all** rows, detect duplicates before writing any file:

```bash
# pairs.tsv = one line per source row, "<derived_name>\t<source_label>", in source order
# Print each derived name produced by more than one label, with the source labels that collided:
sort pairs.tsv | awk -F'\t' '{g[$1]=g[$1] (g[$1]?", ":"") $2; n[$1]++} END{for (k in n) if (n[k]>1) print k" <= "g[k]}'
# e.g.  United_States <= United States, United-States
```

- **Nothing printed** → names are distinct; write the files.
- **Anything printed** → do **not** overwrite. Default action: **stop and report the colliding source labels**
  (e.g. `"United States" and "United-States" both → United_States`) so the user renames or supplies distinct
  keys. The DeveloperName is an API key used in `getInstance('<DeveloperName>')`, so silently renaming it can
  break consuming code — surface it rather than guess.
- **Only if the user asks you to auto-resolve**, append a deterministic, length-aware suffix: keep the first
  occurrence (in source order) unchanged, and for each later collision append `_2`, `_3`, … after truncating
  the base so `base + suffix ≤ 40`. Source order + fixed suffixes keep it deterministic — the same batch
  always produces the same names.

Collision example (needs step 7): `United States` → `United_States` and `United-States` → `United_States`;
after auto-resolution → `United_States` and `United_States_2`.
