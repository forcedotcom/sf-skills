# Advanced Picklist Reference

Detailed rules and worked examples for picklist CustomFields that go beyond a
simple inline value list. All XML uses the `http://soap.sforce.com/2006/04/metadata`
namespace with a `<CustomField>` root, exactly like the simple-picklist examples in
the main skill.

Covered here:

1. [Value Set References (`<valueSetName>`)](#1-value-set-references-valuesetname)
2. [Controlling / Dependent Picklists](#2-controlling--dependent-picklists)
3. [Enhanced Value Attributes (`color`, `isActive`, value-level `<description>`)](#3-enhanced-value-attributes)
4. [Picklist Validation Rules](#4-picklist-validation-rules)
5. [Scoping a Picklist to a Record Type](#5-scoping-a-picklist-to-a-record-type)

---

## 1. Value Set References (`<valueSetName>`)

A picklist field can either define its values **inline** or **reference an existing
value set** (a Global Value Set or a Standard Value Set). The shared set is defined
once and reused across many fields.

### ⭐ HARD RULE: `<valueSet>` is EITHER a reference OR inline — never both

A `<valueSet>` element must contain **exactly one** of:

- `<valueSetName>` — references an existing value set (this section), **OR**
- `<valueSetDefinition>` — defines values inline (the simple-picklist case).

Including both in the same `<valueSet>` is a deployment error.

#### ❌ INCORRECT — both reference and inline definition:

```xml
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
  <fullName>Priority__c</fullName>
  <label>Priority</label>
  <type>Picklist</type>
  <valueSet>
    <restricted>true</restricted>
    <valueSetName>Priority_Levels</valueSetName>   <!-- WRONG: reference … -->
    <valueSetDefinition>                            <!-- WRONG: … AND inline -->
      <sorted>false</sorted>
      <value>
        <fullName>High</fullName>
        <default>false</default>
        <label>High</label>
      </value>
    </valueSetDefinition>
  </valueSet>
</CustomField>
```

**Error:** `Value set must reference a value set name or define a value set, but not both.`

#### ✅ CORRECT — reference a Global Value Set:

```xml
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
  <fullName>Priority__c</fullName>
  <label>Priority</label>
  <description>Account priority drawn from the shared Priority Levels value set</description>
  <inlineHelpText>Select the priority defined by the central Priority Levels list</inlineHelpText>
  <type>Picklist</type>
  <valueSet>
    <restricted>true</restricted>
    <valueSetName>Priority_Levels</valueSetName>
  </valueSet>
</CustomField>
```

### Same `<valueSetName>` element — Global vs. Standard value sets

The SAME `<valueSetName>` element is used to reference both kinds of value set; only
the name you put inside it differs.

| Referenced set | `<valueSetName>` value | Suffix |
|----------------|------------------------|--------|
| **StandardValueSet** (platform-defined, e.g. Industry, LeadSource) | Bare enum name | NO `__c`, NO `__gvs` → `<valueSetName>Industry</valueSetName>` |
| **GlobalValueSet** | Bare developer name | NO `__c`, **NO `__gvs`** → `<valueSetName>Priority_Levels</valueSetName>` |

> **Rule: always use the bare developer name — never add `__gvs`.** In API 57.0+ orgs the
> platform stores/displays a GlobalValueSet's name with a `__gvs` suffix internally, but the
> **Metadata API (deploy AND retrieve) uses the bare name** (the suffix came from a patched-out
> Winter '23 change that broke deploys). So `<valueSetName>Priority_Levels</valueSetName>`, never
> `Priority_Levels__gvs`. A retrieve showing `__gvs` (or a "returned from org but not found in
> local project" warning) is expected org-storage display — keep local metadata on the bare name.
> Never append `__c` to a value-set name either.

#### ✅ CORRECT — reference a Standard Value Set (bare name, no suffix):

```xml
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
  <fullName>Industry__c</fullName>
  <label>Industry</label>
  <description>Industry classification from the standard Industry value set</description>
  <inlineHelpText>Pick the industry that best describes this account</inlineHelpText>
  <type>Picklist</type>
  <valueSet>
    <restricted>true</restricted>
    <valueSetName>Industry</valueSetName>
  </valueSet>
</CustomField>
```

### A value-set-backed field is `<restricted>` by design

When a field references a value set, its values can only change by editing the value
set itself — the field cannot define ad-hoc values. Set `<restricted>true</restricted>`
on these fields. Leaving it unrestricted is meaningless for a referenced set.

### Cross-reference: creating the value set itself

This skill only **references** an existing value set. **Creating** the GlobalValueSet
or editing a StandardValueSet (the `.globalValueSet-meta.xml` / `.standardValueSet-meta.xml`
metadata) is the job of the `platform-value-set-generate` skill. If the value set does not yet
exist, generate it there first, then reference it here.

---

## 2. Controlling / Dependent Picklists

A **dependent** picklist filters its available values based on the selected value of a
**controlling** field (another picklist, or a checkbox). The dependency lives on the
**dependent** field via a `<controllingField>` element plus one `<valueSettings>` block
per (controlling value → dependent value) pair.

### ⭐ Use the MODERN API 38.0+ form ONLY

| Form | Elements | Status |
|------|----------|--------|
| **Modern (API 38.0+)** | `<valueSet>` → `<controllingField>` + `<valueSetDefinition>` + `<valueSettings>` (`<controllingFieldValue>` + `<valueName>`) | ✅ USE THIS |
| **Legacy (API ≤ 37.0)** | `<picklist>` / `<picklistValues>` / `<controllingFieldValues>` | ❌ DEPRECATED — do NOT generate |

Never emit the legacy `<picklist>`, `<picklistValues>`, or `<controllingFieldValues>`
tags. They are not valid against the modern Metadata API and will fail deployment.

### ⭐ HARD RULE: both the controlling and dependent field must be `<restricted>true</restricted>`

A field dependency requires a fixed, admin-defined value set on **both** ends. **Always emit
`<restricted>true</restricted>` inside the `<valueSet>` of the controlling field AND the
dependent field** — even when the request does not mention "restricted". Omitting it produces
an unrestricted picklist, which cannot reliably participate in a field dependency and diverges
from the expected metadata. This is non-negotiable for dependent picklists: if you write a
`<controllingField>` or `<valueSettings>`, the same `<valueSet>` must also carry
`<restricted>true</restricted>`.

### Structure of a dependent picklist

Inside the dependent field's `<valueSet>`, in this order:

1. `<controllingField>` — API name of the controlling field (e.g. `Country__c`).
2. `<valueSetDefinition>` — defines the dependent field's own values (as usual). The dependency
   mapping does **NOT** go in here.
3. one or more `<valueSettings>` blocks — **siblings** of `<valueSetDefinition>`, NOT nested
   inside it or inside any `<value>`. One block **per (controlling value, dependent value) pair**:
   - `<controllingFieldValue>` — a controlling-field value that enables this dependent value.
   - `<valueName>` — the dependent value that becomes available.

> ### ⛔ THE #1 MISTAKE: do NOT put `<controllingFieldValue>` inside `<value>`
> The mapping lives in **separate `<valueSettings>` blocks**, never as a child of a
> `<value>` in `<valueSetDefinition>`. Putting `<controllingFieldValue>` inside a `<value>`
> fails deployment with `Element controllingFieldValue invalid at this location in type CustomValue`.
>
> ```xml
> <!-- ❌ WRONG — controllingFieldValue nested in the value definition -->
> <valueSetDefinition>
>   <value>
>     <fullName>USA</fullName><label>USA</label><default>false</default>
>     <controllingFieldValue>Americas</controllingFieldValue>   <!-- INVALID HERE -->
>   </value>
> </valueSetDefinition>
>
> <!-- ✅ CORRECT — values defined plainly; mapping in SEPARATE valueSettings siblings -->
> <valueSetDefinition>
>   <value><fullName>USA</fullName><label>USA</label><default>false</default></value>
> </valueSetDefinition>
> <valueSettings>
>   <controllingFieldValue>Americas</controllingFieldValue>
>   <valueName>USA</valueName>
> </valueSettings>
> ```
>
> **One `<valueSettings>` per pair.** With multiple controlling values (Americas→USA,Canada;
> EMEA→UK,Germany) you emit **one block for each (controllingValue, dependentValue) pair** — four
> pairs = four `<valueSettings>` blocks. And remember: both fields carry `<restricted>true</restricted>`.

### ✅ CORRECT — State dependent on Country (USA → California, Texas)

**Controlling field — `Country__c` (a plain restricted picklist):**

```xml
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
  <fullName>Country__c</fullName>
  <label>Country</label>
  <description>Country used to filter the dependent State picklist</description>
  <inlineHelpText>Select the country first; the State list filters to match</inlineHelpText>
  <type>Picklist</type>
  <valueSet>
    <restricted>true</restricted>
    <valueSetDefinition>
      <sorted>false</sorted>
      <value>
        <fullName>USA</fullName>
        <default>false</default>
        <label>USA</label>
      </value>
      <value>
        <fullName>Canada</fullName>
        <default>false</default>
        <label>Canada</label>
      </value>
    </valueSetDefinition>
  </valueSet>
</CustomField>
```

**Dependent field — `State__c`, controlled by `Country__c`:**

```xml
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
  <fullName>State__c</fullName>
  <label>State</label>
  <description>State filtered by the selected Country</description>
  <inlineHelpText>Available states depend on the Country you picked</inlineHelpText>
  <type>Picklist</type>
  <valueSet>
    <controllingField>Country__c</controllingField>
    <restricted>true</restricted>
    <valueSetDefinition>
      <sorted>false</sorted>
      <value>
        <fullName>California</fullName>
        <default>false</default>
        <label>California</label>
      </value>
      <value>
        <fullName>Texas</fullName>
        <default>false</default>
        <label>Texas</label>
      </value>
    </valueSetDefinition>
    <valueSettings>
      <controllingFieldValue>USA</controllingFieldValue>
      <valueName>California</valueName>
    </valueSettings>
    <valueSettings>
      <controllingFieldValue>USA</controllingFieldValue>
      <valueName>Texas</valueName>
    </valueSettings>
  </valueSet>
</CustomField>
```

> Each dependent value gets its own `<valueSettings>` block per enabling controlling
> value. If California were also valid under a second country, you would add another
> `<valueSettings>` block with that country's `<controllingFieldValue>` and
> `<valueName>California</valueName>`.

### ❌ INCORRECT — deprecated legacy form:

```xml
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
  <fullName>State__c</fullName>
  <label>State</label>
  <type>Picklist</type>
  <picklist>                                <!-- WRONG: deprecated wrapper -->
    <controllingField>Country__c</controllingField>
    <picklistValues>                        <!-- WRONG: use valueSetDefinition/value -->
      <fullName>California</fullName>
      <controllingFieldValues>USA</controllingFieldValues>  <!-- WRONG: use valueSettings -->
    </picklistValues>
  </picklist>
</CustomField>
```

**Error:** `Element {http://soap.sforce.com/2006/04/metadata}picklist is not allowed` — the
legacy dependency elements are not valid in the modern `<valueSet>` structure.

---

## 3. Enhanced Value Attributes

### ⭐ Value-name fidelity — do NOT underscore picklist value names

A **picklist value's `<fullName>` is NOT a field API name** and must NOT be transformed.
Use the value text **exactly as the user spelled it**, spaces and all. A value the user
calls `Closed Won` is `<fullName>Closed Won</fullName>` and `<label>Closed Won</label>` —
**never** `Closed_Won`. Picklist value `<fullName>` permits spaces (and is not required to
carry `__c`); the space-to-underscore + `__c` rule applies ONLY to the **field**
`<fullName>` (e.g. field `Total Contract Value` → `Total_Contract_Value__c`), not to the
values inside it. Underscoring a value name changes the value's identity, diverges from what
the user asked for, and breaks any RecordType `<picklistValues>` / `<valueSettings>` that
reference the value by its real name.

| Element | Spaces? | `__c` suffix? | Example for "Closed Won" |
|---|---|---|---|
| **Field** `<fullName>` | ❌ replace with `_` | ✅ required | (field named) `Status__c` |
| **Picklist value** `<fullName>` | ✅ keep as written | ❌ never | `Closed Won` |
| **Picklist value** `<label>` | ✅ keep as written | ❌ never | `Closed Won` |

> ❌ `<fullName>Closed_Won</fullName>`  ✅ `<fullName>Closed Won</fullName>`
> When a RecordType filters this value it must also reference `Closed Won` (with the space)
> in `<values><fullName>` — the names must match exactly across field and record type.

Inline `<value>` entries (CustomValue subfields) support more than `<fullName>`,
`<default>`, and `<label>`. The common extras:

| Subfield | Type | Notes |
|----------|------|-------|
| `<color>` | Hex string | UI chart/badge color, e.g. `#FF0000`. Include the leading `#`. |
| `<isActive>` | Boolean | `false` retires a value without deleting it (preserves history). Inactive values still count toward the 1,000-value restricted limit. |
| `<description>` | String | Value-level documentation, distinct from the field-level `<description>`. |

These are independent of `<default>` and `<label>` and may be combined freely.

### ✅ CORRECT — Status picklist with colors and an inactive value

```xml
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
  <fullName>Status__c</fullName>
  <label>Status</label>
  <description>Lifecycle status of the record</description>
  <inlineHelpText>Select the current lifecycle stage</inlineHelpText>
  <type>Picklist</type>
  <valueSet>
    <restricted>true</restricted>
    <valueSetDefinition>
      <sorted>false</sorted>
      <value>
        <fullName>Cancelled</fullName>
        <default>false</default>
        <label>Cancelled</label>
        <color>#FF0000</color>
        <isActive>true</isActive>
        <description>Work was stopped before completion</description>
      </value>
      <value>
        <fullName>Complete</fullName>
        <default>false</default>
        <label>Complete</label>
        <color>#00FF00</color>
        <isActive>true</isActive>
        <description>All work finished and accepted</description>
      </value>
      <value>
        <fullName>Draft</fullName>
        <default>false</default>
        <label>Draft</label>
        <isActive>false</isActive>
        <description>Legacy draft state, retired from new records</description>
      </value>
    </valueSetDefinition>
  </valueSet>
</CustomField>
```

---

## 4. Picklist Validation Rules

The Metadata API rejects malformed picklist values at deploy time. Two common failures:

### Duplicate value names

Two `<value>` entries with the same `<fullName>` inside one `<valueSetDefinition>` are
rejected.

#### ❌ INCORRECT — duplicate value:

```xml
<valueSetDefinition>
  <sorted>false</sorted>
  <value>
    <fullName>Open</fullName>
    <default>false</default>
    <label>Open</label>
  </value>
  <value>
    <fullName>Open</fullName>              <!-- WRONG: duplicate fullName -->
    <default>false</default>
    <label>Open (again)</label>
  </value>
</valueSetDefinition>
```

**Error:** `duplicate value found: Open is defined multiple times`

### Invalid API-name format

A picklist `<value>`'s `<fullName>` must start with a letter and must NOT contain
hyphens or begin with a digit. Unlike field API names, spaces ARE permitted (e.g.
`Closed Won`, `United Kingdom`) — see §3 value-name fidelity; do NOT underscore them.
The `__c` suffix is not required on value `<fullName>` values.

The stricter "only alphanumerics and single underscores, no leading digit, no double
or trailing underscore" rule applies to the *field* `<fullName>` (the `__c`-suffixed
API name), not to picklist value fullNames.

#### ❌ INCORRECT — invalid value API name:

```xml
<value>
  <fullName>1st-Choice</fullName>          <!-- WRONG: starts with digit, has hyphen -->
  <default>false</default>
  <label>1st Choice</label>
</value>
```

**Error:** `Invalid fullName: must begin with a letter and use only alphanumeric characters and underscores`

#### ✅ CORRECT:

```xml
<value>
  <fullName>First Choice</fullName>          <!-- fixed: letter-first, hyphen removed, space preserved -->
  <default>false</default>
  <label>1st Choice</label>
</value>
```

---

## 5. Scoping a Picklist to a Record Type

> **Scope note.** This section covers ONLY the picklist seam between a CustomField and a
> RecordType — i.e. "expose a subset of *this field's* values for a given record type." It
> is NOT a general record-type authoring guide. Record types also carry compact layouts,
> page-layout assignments, branding, and more, which are out of scope here and owned by the
> record-type / UI metadata area. When a request goes beyond picklist value visibility, say
> so and defer the broader record-type work rather than guessing.

A common follow-on to creating a picklist field is "…and for the *X* record type, only show
values A and B." That visibility is expressed on the **RecordType**, not the field — the
field keeps its full value set; the record type filters which values appear.

### Picklist value filtering

Add one `<picklistValues>` block per filtered field inside the `<RecordType>`:

| Element | Requirement | Notes |
|---|---|---|
| `<picklistValues>` | One per filtered picklist | Repeat per field you filter |
| `<picklist>` | Required | The field API name (e.g. `Status__c`, or `StageName` for a standard field) |
| `<values>` | One per **exposed** value | List ONLY the values this record type should show; omitted values are hidden (NOT deleted from the field) |
| `<values><fullName>` | Required | The picklist value's API name |
| `<values><default>` | Required | `true` on exactly one value, `false` on the rest |

### The RecordType file always carries its own `<fullName>`

Unlike a CustomObject (whose name is derived from the folder/filename), a `<RecordType>` **must
include a `<fullName>`** element — the record type's developer name (e.g. `<fullName>Internal</fullName>`),
matching the filename `Internal.recordType-meta.xml`. It's bare (no object prefix); the object
comes from the `objects/<Object>/` folder path.

### ⭐ STEP 1 — Decide if this object needs a BusinessProcess (do this BEFORE writing files)

A record type on a **BusinessProcess-gated object — Opportunity, Lead, Case, or Solution —
will NOT deploy without a `<businessProcess>` reference**, even when it only filters a *custom*
picklist and never touches the standard status field (`Required field is missing: businessProcess`).
**Every other object — all custom objects (`*__c`) and other standard objects like Account or
Contact — needs NO BusinessProcess.** Decide first:

| Object | BusinessProcess? | Files to emit |
|---|---|---|
| Opportunity / Lead / Case / Solution | **REQUIRED** | BusinessProcess file **+** RecordType that references it (two files) |
| Custom object (`*__c`), Account, Contact, everything else | **None** | RecordType alone (one file) |

For the gated four, a suitable BusinessProcess may already exist in the org — reference its
developer name instead of generating a new one (confirm via the grounding MCP's `search_metadata`
if available; otherwise generate a minimal one). For everything else, **do not invent a
BusinessProcess** — adding one to a custom-object record type is wrong.

#### ✅ CORRECT — Opportunity "Enterprise" record type, two deployable files

```xml
<!-- File 1: objects/Opportunity/businessProcesses/Enterprise_Sales_Process.businessProcess-meta.xml -->
<BusinessProcess xmlns="http://soap.sforce.com/2006/04/metadata">
  <fullName>Enterprise_Sales_Process</fullName>   <!-- BARE — see the api-context translation note below -->
  <isActive>true</isActive>
  <values><fullName>Prospecting</fullName></values>      <!-- these are Opportunity STAGE (StageName) values, NOT Status__c — the BP governs the standard stage picklist. Do NOT add <default> (fails: "Cannot specify a default on: Opportunity") -->
  <values><fullName>Qualification</fullName></values>
  <values><fullName>Closed Won</fullName></values>
  <values><fullName>Closed Lost</fullName></values>
</BusinessProcess>
```

> ⛔ **`<fullName>` is BARE in the source file — strip the entity prefix that api-context gives you.**
> The metadata grounding / api-context for `BusinessProcess` reports the fullName in its **API
> form**, entity-qualified: `Opportunity.Enterprise_Sales_Process`. That is correct for the API —
> but in the **source/DX-format file you author**, the entity is already conveyed by the
> `objects/Opportunity/` folder path, so the `<fullName>` element is the **bare process name**:
> `Enterprise_Sales_Process`, NOT `Opportunity.Enterprise_Sales_Process`. (Same API-vs-source split
> as the GlobalValueSet `__gvs` suffix in §1.) Writing the entity-qualified form makes the
> RecordType's bare `<businessProcess>Enterprise_Sales_Process</businessProcess>` reference fail to
> resolve → `no BusinessProcess named Opportunity.Enterprise_Sales_Process found`. **When you pull
> the BP name from api-context and it looks like `Opportunity.X`, write `X` in the file.** The BP
> file's `<fullName>` and the RecordType's `<businessProcess>` must be the identical bare string.

```xml
<!-- File 2: objects/Opportunity/recordTypes/Enterprise.recordType-meta.xml -->
<RecordType xmlns="http://soap.sforce.com/2006/04/metadata">
  <fullName>Enterprise</fullName>
  <label>Enterprise</label>
  <active>true</active>
  <businessProcess>Enterprise_Sales_Process</businessProcess>  <!-- REQUIRED; must precede <picklistValues> -->
  <picklistValues>
    <picklist>Status__c</picklist>
    <values>
      <fullName>Qualified</fullName>
      <default>true</default>
    </values>
    <values>
      <fullName>Closed Won</fullName>
      <default>false</default>
    </values>
  </picklistValues>
</RecordType>
```

#### ❌ INCORRECT — BusinessProcess file emitted but NOT referenced (most common failure)

```xml
<!-- File 1 (businessProcesses/Enterprise_Sales_Process...) was generated correctly, BUT -->
<!-- File 2, the RecordType, FORGOT the <businessProcess> element: -->
<RecordType xmlns="http://soap.sforce.com/2006/04/metadata">
  <fullName>Enterprise</fullName>
  <active>true</active>
  <label>Enterprise</label>
  <!-- WRONG: no <businessProcess> here → the BP file is orphaned and the deploy fails -->
  <picklistValues> ... </picklistValues>
</RecordType>
```

**Error:** `Required field is missing: businessProcess`. Generating the BusinessProcess file is
only half the job — the `<RecordType>` MUST also carry the `<businessProcess>NameMatchingTheFile</businessProcess>`
element. Both, every time, for Opportunity/Lead/Case/Solution.

**BusinessProcess gotchas (these block deployment):**
- **`<fullName>` is BARE — never object-qualified.** Inside
  `objects/Opportunity/businessProcesses/Enterprise_Sales_Process.businessProcess-meta.xml`, the
  `<fullName>` is just `Enterprise_Sales_Process` — NOT `Opportunity.Enterprise_Sales_Process`.
  The object comes from the folder path. Qualifying it (`<fullName>Opportunity.Enterprise_Sales_Process</fullName>`)
  makes the RecordType's bare `<businessProcess>Enterprise_Sales_Process</businessProcess>`
  reference unresolvable → `no BusinessProcess named Opportunity.Enterprise_Sales_Process found`.
  The BP file's `<fullName>` and the RecordType's `<businessProcess>` value must be the **same
  bare string**.
- **Two coupled parts** — (1) the `businessProcesses/<Name>.businessProcess-meta.xml` file AND
  (2) a `<businessProcess><Name></businessProcess>` element inside the `<RecordType>`. The
  developer name must match. Doing only one is the #1 deploy failure.
- **Element order** — `<businessProcess>` must appear **before** `<picklistValues>` inside
  `<RecordType>` (it follows `<active>`). Out-of-order elements fail schema validation.
- **No `<default>` on Opportunity BP values** — specifying `<default>` on a `<values>` entry
  fails with `Cannot specify a default on: Opportunity`. (Lead / Case / Solution DO allow a
  BP default; Opportunity is the exception.)

### Deployment ordering

```text
GlobalValueSet / StandardValueSet  (if the field draws from a value set)
        ↓
CustomField  (the picklist field, with its full value set)
BusinessProcess  (REQUIRED for Opportunity/Lead/Case/Solution record types)
        ↓
RecordType   (filters the field's values; references the BusinessProcess)
```

- The CustomField (and ALL the values the record type references) MUST deploy **before** the
  RecordType, or you get `Cannot find the picklist value: <X>`.
- For Opportunity/Lead/Case/Solution, the `<businessProcess>` must exist (same package or
  already in the org) before the RecordType.

### ⭐ UI-sync gotcha — values may not auto-display after API deploy

When `<picklistValues>` are loaded via the Metadata API, the values are correctly associated
under the hood, **but they may not automatically appear as "Selected Values" in the Record
Type editing screen in Setup.** The API deploy succeeds; this is a platform UI-sync
limitation, not a deployment error. Tell the user they may need to: **Setup → Object Manager →
[Object] → Record Types → [Record Type] → Edit next to the picklist → move values into
Selected Values → Save.** Always call this out when delivering record-type picklist filtering.

### Common failures

| Error / Symptom | Cause | Fix |
|---|---|---|
| `Required field is missing: businessProcess` | Opportunity/Lead/Case/Solution record type without a `<businessProcess>` | Add a BusinessProcess (deploy it first or reference an existing one) |
| `Cannot specify a default on: Opportunity` | `<default>` set on an Opportunity BusinessProcess value | Remove `<default>` from the Opportunity BP `<values>` |
| `Cannot find the picklist value: <X>` | A value in `<picklistValues>` doesn't exist on the field | Deploy the field with that value first; check spelling/case |
| Filtered values still show full set in UI | API-loaded values not promoted to Selected Values | Perform the manual Setup step above |
