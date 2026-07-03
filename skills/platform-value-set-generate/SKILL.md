---
name: platform-value-set-generate
description: "Use this skill when users need to create, generate, or validate a Salesforce global value set or customize a standard value set. Trigger when users mention a global value set, GlobalValueSet, standard value set, StandardValueSet, a reusable picklist, a picklist value set shared across fields, or customizing standard picklists like Industry, Lead Source, or Opportunity Stage. Also use when users hit deployment errors adding values to a standard picklist, referencing a value set from a custom field, or working with .globalValueSet-meta.xml or .standardValueSet-meta.xml files. DO NOT TRIGGER for an inline one-off picklist on a single field with no reuse, or for general custom field metadata work that does not involve a GlobalValueSet or StandardValueSet — use platform-custom-field-generate instead."
metadata:
  version: "1.0"
  minApiVersion: "60.0"
  cliTools:
    - tool: ["sf"]
      semver: ">=2.0.0"
---

## Overview

Generates and validates the two reusable picklist value-set metadata types — **GlobalValueSet** (a new reusable set shared across fields) and **StandardValueSet** (customizing a built-in catalog picklist like Industry or Lead Source) — and wires a CustomField to one via `<valueSetName>`.

### Scope

- **In scope:** creating a GlobalValueSet, customizing a StandardValueSet, referencing either from a field, and the related deployment errors.
- **Out of scope:** a one-off inline picklist on a single field with no reuse → use **`platform-custom-field-generate`** (inline `<valueSetDefinition>`). Generating the *field* that references a value set is also `platform-custom-field-generate`'s job; this skill produces the value set itself.

**Two different metadata types — do not confuse them:**

| Concern | GlobalValueSet | StandardValueSet |
|---------|----------------|------------------|
| Folder | `globalValueSets/` | `standardValueSets/` |
| File suffix | `.globalValueSet-meta.xml` | `.standardValueSet-meta.xml` |
| Root element | `<GlobalValueSet>` | `<StandardValueSet>` |
| Name source | filename (dev name) | `<fullName>` = fixed catalog name |
| Value element | `<customValue>` | `<standardValue>` |
| Can add NEW values? | Yes | No — modify existing only |
| Can create a new NAME? | Yes | No — only the fixed catalog |
| `*` wildcard in package.xml | Supported | Not supported |

---

## Specification

### 1. Purpose

This document defines the mandatory constraints for generating value-set metadata XML. The agent must verify these constraints before outputting XML to prevent Metadata API deployment errors.

- **GlobalValueSet** — a reusable, named set of picklist values defined once and referenced by any number of picklist/multi-select fields. Use when the same value list is shared across multiple fields.
- **StandardValueSet** — the value list behind a Salesforce-defined standard picklist (Industry, Lead Source, etc.). You can only **modify** the values in a fixed catalog of named sets; you cannot invent a new set or add brand-new values.

---

### 2. GlobalValueSet — Syntactic Essentials

**File:** `globalValueSets/<DeveloperName>.globalValueSet-meta.xml`

The developer name comes from the **filename**, not a `<fullName>` tag.

#### Required Elements

| Element | Requirement | Notes |
|---------|-------------|-------|
| `<masterLabel>` | Required | UI label for the value set |
| `<sorted>` | Required | `true` = alphabetize values in the UI; `false` = preserve listed order |
| `<customValue>` | Required (≥1) | One per value (see below) |

#### `<customValue>` Sub-Elements

| Sub-element | Requirement | Notes |
|-------------|-------------|-------|
| `<fullName>` | Required | The value's API name. Use the value text **as the user spelled it** — spaces are allowed and must be preserved (e.g. `Closed Won`, not `Closed_Won`). Must start with a letter. This is a value name, NOT a field API name, so do not append `__c` or replace spaces with underscores. |
| `<default>` | Optional | At most one value `true`. Omit it (or use `false`) on the rest — it is not required on every value. |
| `<label>` | Required | UI label for the value |
| `<color>` | Optional | Hex color, e.g. `#FF0000` |
| `<isActive>` | Optional | Omit (active) or `false` to deactivate |
| `<description>` | Optional | Per-value description |

#### The `__gvs` Suffix — do NOT use it in metadata

**Rule: reference a GlobalValueSet by its bare developer name. Never add `__gvs`.**

In API 57.0+ orgs the platform *stores/displays* a GlobalValueSet's developer name with a `__gvs` suffix internally, but the **Metadata API (deploy and retrieve) always uses the bare name** — `<valueSetName>Priority_Levels</valueSetName>`, not `Priority_Levels__gvs`. The suffix was briefly emitted by a Winter '23 change that caused deploy failures and was patched out. So:

- The file is `globalValueSets/Priority_Levels.globalValueSet-meta.xml` — **no `__gvs`** in the filename.
- A field references it as `<valueSetName>Priority_Levels</valueSetName>` — **no `__gvs`**.
- If a retrieve shows `Priority_Levels__gvs` in the org or you see a "returned from org but not found in local project" warning, that's the expected org-storage display — keep your local metadata on the bare name.

#### CORRECT — GlobalValueSet

```xml
<?xml version="1.0" encoding="UTF-8"?>
<GlobalValueSet xmlns="http://soap.sforce.com/2006/04/metadata">
    <masterLabel>Priority Levels</masterLabel>
    <sorted>false</sorted>
    <customValue>
        <fullName>Critical</fullName>
        <default>false</default>
        <label>Critical</label>
    </customValue>
    <customValue>
        <fullName>High</fullName>
        <default>false</default>
        <label>High</label>
    </customValue>
    <customValue>
        <fullName>Medium</fullName>
        <default>true</default>
        <label>Medium</label>
    </customValue>
    <customValue>
        <fullName>Low</fullName>
        <default>false</default>
        <label>Low</label>
    </customValue>
</GlobalValueSet>
```

#### INCORRECT — GlobalValueSet

```xml
<GlobalValueSet xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Priority_Levels</fullName>      <!-- WRONG: name comes from the filename -->
    <masterLabel>Priority Levels</masterLabel>
    <!-- WRONG: <sorted> is required and missing -->
    <standardValue>                            <!-- WRONG: GVS uses <customValue>, not <standardValue> -->
        <fullName>Critical</fullName>
    </standardValue>
</GlobalValueSet>
```

**Errors:** missing required `sorted`; unknown element `standardValue`; root `fullName` is rejected because the name is derived from the filename.

---

### 3. StandardValueSet — Syntactic Essentials CRITICAL

**File:** `standardValueSets/<Name>.standardValueSet-meta.xml`

#### HARD CONSTRAINTS — read before generating

1. **You can ONLY modify values inside the fixed catalog of named standard value sets.** You **cannot** add a brand-new value, and you **cannot** create a new StandardValueSet name. The Metadata API will reject both.
2. The root carries a `<fullName>` whose value is the **fixed enum name** (e.g. `Industry`), NOT a `masterLabel`. The filename must match this name.
3. Values are `<standardValue>` entries — **not** `<customValue>`.
4. **Emit ONLY the values the request explicitly names — a surgical, minimal change.** Include a `<standardValue>` block for each value the user asks you to activate, deactivate, relabel, or reorder, and **nothing else**. Do **not** enumerate the full picklist or emit `<standardValue>` entries for values the request did not mention. A StandardValueSet deployment is a partial update: unlisted values keep their current org state untouched. Reproducing every value (e.g. all 30+ Industry entries) is noise and risks clobbering org state — it is wrong even when the request says "keep *only* X active," which means "set the named ones; leave the rest as-is," not "enumerate and deactivate everything else." If you use the grounding MCP to discover existing values, use it only to confirm the named values exist and to get their exact `<fullName>`/`<label>` — not as a list to reproduce in full.

#### `<standardValue>` — Modifiable Sub-Elements

| Sub-element | Modifiable? | Notes |
|-------------|-------------|-------|
| `<fullName>` | Identifies the value (must already exist) | Cannot introduce a new one |
| `<label>` | Yes | Relabel the value's UI text |
| `<isActive>` | Yes | `false` deactivates; omit or `true` keeps active |
| `<default>` | Yes | At most one value `true` |
| `<groupingString>` | Yes | Category grouping (used by some standard picklists) |

#### Canonical StandardValueSet Names (partial)

`Industry`, `LeadSource`, `OpportunityStage`, `OpportunityType`, `AccountType`, `AccountRating`, `LeadStatus`, `CaseStatus`, `CaseOrigin`, `CasePriority`, `CaseReason`, `TaskStatus`, `TaskPriority`, `QuoteStatus`, `Product2Family`, `Salutation`, `AccountOwnership`, `ContractStatus`, `OrderStatus`, `PartnerRole`.

> Full appendix: the complete list of valid standard value set names is at
> `https://developer.salesforce.com/docs/atlas.en-us.api_meta.meta/api_meta/standardvalueset_names.htm`.
> If the name is not in that appendix, it is **not** a StandardValueSet — it is either a GlobalValueSet or an inline CustomField picklist.

#### CORRECT — StandardValueSet (modify existing values only)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<StandardValueSet xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Industry</fullName>
    <standardValue>
        <fullName>Technology</fullName>
        <default>false</default>
        <label>Technology</label>
        <isActive>true</isActive>
    </standardValue>
    <standardValue>
        <fullName>Agriculture</fullName>
        <default>false</default>
        <label>Agriculture</label>
        <isActive>false</isActive>   <!-- deactivated, but kept in the set -->
    </standardValue>
</StandardValueSet>
```

#### INCORRECT — StandardValueSet

```xml
<StandardValueSet xmlns="http://soap.sforce.com/2006/04/metadata">
    <masterLabel>Industry</masterLabel>     <!-- WRONG: StandardValueSet uses <fullName>, not masterLabel -->
    <customValue>                           <!-- WRONG: uses <standardValue>, not customValue -->
        <fullName>Renewable Energy</fullName> <!-- WRONG: cannot ADD a new value to a standard set -->
        <label>Renewable Energy</label>
    </customValue>
</StandardValueSet>
```

**Errors:** unknown element `masterLabel`/`customValue`; adding a value not already in the standard catalog fails deployment.

---

### 4. Never Invent Values — Verify, Don't Hallucinate CRITICAL

When customizing a **StandardValueSet** (or extending a shared GlobalValueSet), **only modify values that already exist** — never invent the value list of a standard picklist. The hard rule is about what you EMIT: a `<standardValue>` whose `<fullName>` is not a real catalog value will fail deployment.

For well-known standard picklists you already know the canonical values (e.g. `Industry`, `LeadSource`, `OpportunityStage`). When you are unsure a named value exists, you can confirm it against the live org — but treat lookup as a *confirmation* step, not a required first call:

- **Grounding MCP** (if available) exposes `search_metadata` and `query-metadata` to look up live metadata. Use them only to confirm a named value's exact `<fullName>`/`<label>` — not to pull the full list to reproduce.
- **CLI fallback** — query the Tooling API directly:

```bash
sf data query --use-tooling-api \
  --query "SELECT MasterLabel, Metadata FROM StandardValueSet WHERE MasterLabel = '<name>'"
```

> **The point is the output, not the lookup:** emit modifications ONLY to values you know exist. A generated StandardValueSet that introduces unseen values is a hallucination and will fail deployment. (This pairs with the minimal-scope rule in §3: confirm the *named* values; don't enumerate the whole set.)

---

### 5. Referencing a Value Set from a CustomField

A picklist/multi-select CustomField references a value set via `<valueSetName>` inside `<valueSet>` (instead of an inline `<valueSetDefinition>`).

```xml
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Priority__c</fullName>
    <label>Priority</label>
    <type>Picklist</type>
    <valueSet>
        <restricted>true</restricted>
        <valueSetName>Priority_Levels</valueSetName>  <!-- bare developer name, NO __gvs; see §2 -->
    </valueSet>
</CustomField>
```

- For a **GlobalValueSet**, `<valueSetName>` is the **bare developer name** (e.g. `Priority_Levels`) — **never** add `__gvs`. The suffix is an org-storage display artifact; the Metadata API uses the bare name for both deploy and retrieve (see §2).
- A field bound to a value set must **not** also declare an inline `<valueSetDefinition>` — choose one or the other.

---

### 6. Validation Rules

The agent must **reject** and explain — not silently "fix" by inventing metadata — the following:

| Violation | Action / Message |
|-----------|------------------|
| Add a NEW value to a **StandardValueSet** | Reject. "Standard value sets cannot accept new values. Create a **GlobalValueSet** (reusable) or an inline picklist on a **CustomField** instead." |
| Create a NEW StandardValueSet name | Reject. The name must be in the standard catalog appendix. Otherwise it is a GlobalValueSet. |
| **Value set developer name** with spaces / invalid chars | Convert spaces to underscores; must start with a letter; alphanumeric + underscore only. `Priority Levels` → `Priority_Levels`. (This applies to the value SET name and the field API name — NOT to individual `<customValue><fullName>` values, which keep spaces as written.) |
| Duplicate value `fullName` within one set | Reject. Each `fullName` must be unique within the value set. |
| More than one `<default>true</default>` | Reject. At most one default value per set. |

#### INCORRECT — adding a value to a standard set

> "Add a `Cryptocurrency` value to the Industry picklist."

Do not emit a `<standardValue>` with `fullName` `Cryptocurrency`. Respond that standard value sets are a fixed catalog and propose a GlobalValueSet (if reused across fields) or an inline restricted picklist on a single CustomField.

---

### 7. Deployment Ordering

A value set must deploy **before** any CustomField that references it.

- Deploy the `GlobalValueSet` / `StandardValueSet` first, then the CustomField whose `<valueSetName>` points at it.
- A field referencing a value set that does not yet exist fails with `valueSetName ... does not exist` (or a "not found" error).
- In `package.xml`: `GlobalValueSet` **supports** the `*` wildcard; `StandardValueSet` does **not** — list each standard set member explicitly.

---

### 8. Common Deployment Errors

| Error / Symptom | Cause | Fix |
|-----------------|-------|-----|
| Value not added to standard picklist | Tried to ADD a value to a `StandardValueSet` | Standard sets are fixed; use GlobalValueSet or inline CustomField picklist |
| `Required field missing: sorted` | GlobalValueSet missing `<sorted>` | Add `<sorted>true</sorted>` or `<sorted>false</sorted>` |
| Unknown element `masterLabel` (StandardValueSet) | Used `masterLabel` instead of `fullName` | StandardValueSet root uses `<fullName>` = catalog name |
| Unknown element `customValue` (StandardValueSet) | Used `customValue` instead of `standardValue` | Use `<standardValue>` in standard sets |
| `valueSetName ... does not exist` | Field deployed before its value set, or `__gvs` wrongly added to the reference | Deploy the value set first; reference it by the **bare** developer name with NO `__gvs` (§2) |
| Duplicate value name | Two `<customValue>` entries share a `fullName` | Make each `fullName` unique within the set (spaces in a value name are allowed — do NOT underscore them) |

---

## Verification Checklist

Before generating value-set XML, verify:

### Type Selection
- [ ] Is this a reusable set shared across fields (GlobalValueSet) or a built-in standard picklist (StandardValueSet)?
- [ ] If StandardValueSet: is the name in the standard catalog appendix? If not, it must be a GlobalValueSet or inline picklist.

### GlobalValueSet Checks
- [ ] Is the root `<GlobalValueSet>` with namespace `http://soap.sforce.com/2006/04/metadata`?
- [ ] Is `<masterLabel>` present?
- [ ] Is `<sorted>` present (`true` or `false`)?
- [ ] Is there at least one `<customValue>`, each with `<fullName>` and `<label>` (at most one carrying `<default>true</default>`)?
- [ ] Is there NO root `<fullName>` (name comes from the filename)?
- [ ] When referencing from a field, is `<valueSetName>` the **bare** developer name with NO `__gvs` suffix?

### StandardValueSet Checks CRITICAL
- [ ] Are you emitting modifications ONLY to values you know exist (confirmed from known standard catalogs, or via grounding `search_metadata`/`query-metadata` / Tooling API if unsure) — never invented values?
- [ ] Is the root `<StandardValueSet>` with the correct namespace?
- [ ] Does the root use `<fullName>` set to the fixed catalog name (NOT `masterLabel`)?
- [ ] Are values `<standardValue>` entries (NOT `customValue`)?
- [ ] Are you ONLY modifying values that already exist (no new `fullName`)?
- [ ] Did you avoid adding a brand-new value or a new set name?

### Shared Checks
- [ ] At most one value has `<default>true</default>`?
- [ ] Are all value `fullName`s unique within the set? (Spaces in a value name are fine — preserve them as written; only the value-SET developer name and field API name use underscores.)
- [ ] Does the value set deploy BEFORE any CustomField that references it?
- [ ] Does the filename match the intended name?
