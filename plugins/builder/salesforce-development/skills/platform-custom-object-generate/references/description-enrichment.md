<!-- Parent: platform-custom-object-generate/SKILL.md -->

# Object Description Enrichment

The `<description>` on a Custom Object must read like human-written documentation.

---

## When & How — always compose, confirm the text, write

A `<description>` is **mandatory** — always compose one. Do it when **creating** the object and again on **any** change: adding, updating, or deleting a field **or a validation rule** (keeps it from going stale). Validation-rule changes count exactly like field changes — the change isn't done until the description is refreshed. Never ask *whether* to add a description; the only thing to confirm is the **wording**.

**Confirm per change.** Propose and confirm on **each** change separately. A prior "keep current" applies to that one change only — it is never standing permission to skip the proposal on a later change.

Why confirm the wording: an existing description may be hand-authored by an admin (carrying context the schema can't reveal) or generated earlier — you can't tell which from the file, so don't overwrite it silently.

**Compose** the description (Steps 1–2 below). If one already exists, use it as a **strong signal** — preserve its business context and fold the new field/rule in; don't discard good prose. Then branch:

- **No existing description (brand-new object):** nothing to overwrite — just write the composed description. **Do not prompt.**
- **An existing description (update / delete / any re-enrichment):** never overwrite it silently. Show the proposal, ask, and **STOP — wait for the user's reply before writing:**
   ```text
   Proposed description for <Object>:
   <enriched description>
   Current: <existing description>
   Use this? (yes / keep current / edit)
   ```
   **Do NOT write the `<description>` until the user replies** — showing the diff is not approval, even when the change looks obvious. Then act: *yes* → write proposed · *keep current* → leave untouched · *edit* → use the user's wording.

Always end with a `<description>` written.

---

## Step 1 — Classify Description Signals

Each field is classified by how it should appear in the enriched description:

| Classification | Criteria | Enriched output |
|---------------|----------|--------------------|
| **Constrained** | required, unique, externalId, restricted picklist | Selective parenthetical: `VIN (required, external ID)`, `Color (Red/Green only)` |
| **Behavioral** | formula / calculated, roll-up summary | Dedicated clause describing behavior: "the Age Years field auto-calculates vehicle age", "Total Service Cost summarizes related service records" — never formula syntax |
| **Relationship** | master-detail, lookup | Woven context: "as a child of Account", "links to User" — never "(Master-Detail to Account)" |
| **Standard** | everything else | Label only, no annotation |

When selecting which fields to surface, prioritize **constrained > behavioral > relationship > standard**.

Plus two non-field signals:
- **Business purpose** — from the user's words ("track projects", "manage inventory") or inferred from object name + key fields. Becomes the opening.
- **Common use cases** — infer 2-3 practical uses from purpose, fields, and relationships ("fleet management", "service scheduling"); `helpText` and conversation context are hints.

---

## Step 2 — Compose the Description

Compose in this order:

```text
1 (Purpose):    "The {Object_Label} object {verb_phrase}."
2 (Key fields): "It captures {labels with selective context}."
3 (Computed):   "The {Label} field auto-calculates {what}, while {Label} summarizes {what}."
4 (Rules):      "Validation rules enforce {human-readable constraints}."
5 (Use cases):  "Commonly used for {use_case_1}, {use_case_2}, and {use_case_3}."
```

Sentences 1 and 2 are always included. Apply these conditions to 3–5:
- **Sentence 3 (Computed):** include only if the object has formula or roll-up fields; omit if it has none.
- **Sentence 4 (Rules):** include only if the object has validation rules; omit if it has none.
- **Sentence 5 (Use cases):** always include — unless the description would exceed 50 words, in which case drop it first (it is the lowest-priority element).

**Writing rules:**
- Field **labels**, never API names (`Year`, not `Year__c`)
- Selective annotations only — annotate non-obvious attributes (required, external ID, restricted values); standard fields get label only
- Formulas/rollups → behavior, not syntax ("auto-calculates vehicle age", not `YEAR(TODAY()) - Year__c`)
- Validations → business rules ("require VIN"), not `ISBLANK(...)`
- Relationships → context ("as a child of Account"), not metadata notation
- Open in third person ("The X object..."), never "Tracks X" or "Object used to..."
- No "Contains N fields including"
- Clear professional prose; no markdown/backticks/special characters
- **Hard ceiling: under 50 words.** If over, tighten wording first; if still over, drop in priority order: sentence 5 (use cases) first, then sentence 4 (rules), then sentence 3 (computed); never drop sentences 1–2.
- The result must read like human-written documentation, comprehensible without the schema.

---

## Field & Validation Prioritization

**Large field lists:** surface only the top 5-6 most notable by label + "along with additional tracking fields". Tier order when deciding what carries the most signal:
- **Tier 1 — Structure & Logic:** relationships, master-detail, roll-up summaries, formulas, picklists
- **Tier 2 — Contextual:** helpText, PII flag, externalId, trackHistory
- **Tier 3 — Standard:** everything else

**Many validation rules:** reference only active rules. If >20, prioritize complex/business-logic rules (compound conditions, cross-field comparisons) over trivial single-field null checks; summarize the 1-3 most important as business rules — never enumerate all.

---

## Junction & Child Objects

- **Junction:** mention both parents in the opening — "The {Label} object connects {ParentA} and {ParentB}, enabling many-to-many tracking between them."
- **Child:** weave the parent into the purpose sentence — "The {Label} object tracks {purpose} as a child of {Parent}."

---

## Examples

**❌ Generic template** — `Object used to track and manage Projects within the organization.` (no specifics)

**❌ Mechanical metadata dump** — `Tracks customer projects. Contains 2 fields including Status__c (Picklist: Planning, Active, Complete), Account__c (Master-Detail to Account)...` (API names, parenthetical type dump, "Contains N fields" boilerplate)

**✅ Good (Project, 48 words):**
```xml
<description>The Project object tracks customer projects through completion, as a child of Account. It captures Status, Budget, Actual Cost, Start Date, and Project Manager; the Budget Variance field auto-calculates planned-vs-actual spend. End Date must be after Start Date. Commonly used for project tracking, budget management, and resource planning.</description>
```

**✅ Excellent (Car, 46 words):**
```xml
<description>The Car object tracks vehicle inventory and maintenance. It captures Year, VIN (required, external ID), Color (Red/Green only), and Location; the Age Years field auto-calculates vehicle age. VIN is required and Black cars cannot be sold. Commonly used for fleet management, inventory tracking, and service scheduling.</description>
```

---

## Edge Cases

| Scenario | Output |
|----------|--------|
| Bare object, no fields | `The Vehicle object tracks vehicle information.` |
| Junction object | `The Position Candidate object connects Position and Candidate, enabling many-to-many tracking between them.` |
| Only computed fields | Each formula/rollup gets a behavioral clause; no empty field list. |
