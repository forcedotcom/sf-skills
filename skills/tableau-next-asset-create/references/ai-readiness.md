# AI Readiness Reference for Semantic Data Models

Load this file when creating or reviewing a semantic model for AI readiness.
It is the authoritative checklist for all AI readiness requirements that must
be met before a model is used by Concierge / Agentforce for Analytics.

Source: Salesforce Help — "Design an AI-Ready Semantic Model"
(analytics.tua_ai_sm_design.htm)

## Contents

- Why AI Readiness Matters
- AI Readiness Checklist
- Description Quality Guide
- Field-Level Description Quality
- Label Quality Guide
- API Name Quality Guide
- Ambiguity Management
- Field Type Accuracy
- businessPreferences Examples
- businessPreferences read / write tools

---

## Why AI Readiness Matters

Agents consume the semantic layer in **priority order**:
**Metrics first → Calculated fields → Raw fields**

A well-enriched metric set matters more to answer quality than raw field
coverage. Agents interpret fields in the context of the objects they belong
to — the combination of object name, description, and field label drives
semantic clarity.

---

## AI Readiness Checklist

### Model Level (`create_semantic_model` / `update_semantic_model`)

- [ ] `description` — 1–2 sentences covering the model's goals and primary
  use cases. Agents incorporate model descriptions to reason about content.
  Example: `"Tracks open pipeline opportunities and associated account data
  for sales forecasting and rep performance analysis"`
- [ ] `agentEnabled: true` — gates whether AI agents can use this model.
  Set explicitly; do not rely on any default.
- [ ] `categories[]` — product category (`Sales`, `Marketing`, `Commerce`,
  `Service`, or `Other`) where determinable.
- [ ] `businessPreferences` — domain-specific context statements. At
  minimum describe what the core measure means and any non-obvious
  terminology. **Read** with `get_semantic_model_business_preferences`
  (`includeModelContent=false`). **Write** with
  `update_semantic_model_business_preferences` (full replacement of `# `-
  prefixed lines — see below). Fallback: `update_semantic_model` with the
  same `# `-prefixed-line format. Example:

  ```text
  # Revenue = sum of Amount on closed-won opportunities only
  # Stage names: 0-Prospecting through 6-Closed Won
  # Region = sales territory, not geographic region
  ```

### Data Object Level (`add_semantic_model_data_object`)

- [ ] `description` — what this entity represents and how it is used. For
  custom objects, this is required. For standard Salesforce objects, the
  default is acceptable — only enhance, never contradict.
  Example: `"Active sales opportunities with stage, amount, and close date.
  Used in pipeline forecasting and rep performance analysis."`
- [ ] `primaryNameField` — the original (pre-suffix) column name that
  identifies records in insight narratives (e.g. `"Name"`, `"Account_Name"`).
  This is the field Concierge uses to name records in generated text
  (e.g. "Acme Corp is the top contributor").

### Calculated Dimension (`add_semantic_model_calculated_dimension`)

- [ ] `description` — 1–2 sentences explaining the grouping's purpose and
  usage. Example: `"Fiscal quarter extracted from close date, used for
  quarterly pipeline grouping and period-over-period comparison"`
- [ ] Unique purpose — only create if this calculation has a clearly
  differentiated analytical purpose not already covered by another field.
- [ ] Pre-creation check — call `list_semantic_model_calculated_dimensions`
  before creating. If an existing dimension covers the same source field,
  identify how the new one differs before proceeding.

### Calculated Measure (`add_semantic_model_calculated_measure`)

- [ ] `description` — what this measure calculates and its business purpose.
  Example: `"Gross margin as a percentage: (Revenue - Cost) / Revenue.
  Used in profitability analysis across product lines."`
- [ ] `sentiment` — set explicitly (do not rely on server default):
    - `"SentimentTypeUpIsGood"` — higher is better (revenue, margin, win rate)
    - `"SentimentTypeUpIsBad"` — higher is worse (churn, cost, error rate)
    - `"SentimentTypeNone"` — directionless (e.g. a count or ratio with no
      inherent good/bad direction)
- [ ] Unique purpose — only create if this measure has a clearly
  differentiated analytical purpose.
- [ ] Pre-creation check — call `list_semantic_model_calculated_measures`
  AND `list_semantic_model_metrics` before creating. A calc measure that
  duplicates a metric creates cross-priority ambiguity (agents see both as
  candidates); decline and point to the existing metric instead.

### Metric (`add_semantic_model_metric`)

- [ ] `description` — what this KPI measures and its business context.
  Example: `"Total open pipeline amount, summed across active opportunities
  in Stages 1–5. Used for weekly forecast review."`
- [ ] `sentiment` (top-level) — `SentimentTypeUpIsGood` or
  `SentimentTypeUpIsBad`
- [ ] `insightsSettings.sentiment` — mirror the top-level sentiment value
- [ ] `insightsSettings.identifyingDimension` — REQUIRED; point at the
  grain's primary key. A metric without this **crashes the Tableau Next
  metric UI**.
- [ ] `insightsSettings.singularNoun` / `insightsSettings.pluralNoun` —
  the business unit name (e.g. `"opportunity"` / `"opportunities"`). These
  appear verbatim in AI-generated insight text.
- [ ] `insightsSettings.insightsDimensionsReferences` — 2–4 most analytically
  useful dimensions (e.g. region, stage, owner). Tells Concierge which
  dimensions to use for contributor breakdown.
- [ ] `additionalDimensions[]` — must mirror every field in
  `insightsSettings.identifyingDimension`, `insightsDimensionsReferences`, and
  `filters`. Omitting an insight/identifying dim fails create (`Insight
  dimension (...) is missing from the metric additional dimensions`); omitting
  a filter field makes the metric unqueryable. **Exception: the server rejects
  `Date`-type fields in `additionalDimensions`** (`"Field should have one of
  these data types: Text, Number, Boolean, Email, PhoneNumber, Url"`). Do not
  add Date-type filter fields to `additionalDimensions`.
- [ ] **Contextual filtering** (optional but recommended for business-scoped
  KPIs) — add `filters` to scope the metric to the correct business context
  (e.g. a "Closed Won Revenue" metric should filter on `Stage = 'Closed Won'`,
  not sum all opportunities). Use `filterLogic` alongside `filters`. Mirror
  every non-Date filter field into `additionalDimensions[]`. Confirmed valid
  filter operators: `GreaterThan`, `Equals`. `GreaterThanOrEqual` and `After`
  are invalid and will be rejected by the server.
- [ ] **Display formatting** — set `decimalPlace` and currency/unit context
  in the metric description so agents can format answers correctly (e.g.
  `"Expressed in USD, rounded to the nearest dollar"`). The API does not
  enforce display format, but including format context in the description
  produces better AI-generated narratives.
- [ ] Unique purpose — only create for high-impact, frequently used KPIs.
  Near-identical metrics differing only by a minor filter must be clearly
  differentiated in label, description, and purpose.

### Pre-Handoff (before exposing model to AI users)

- [ ] **Similarity scan** — Run the Semantic Model AI Optimization similarity
  scan in Tableau Next's Semantic Model Builder UI. A `modelHealth: Low` result
  indicates overlapping or ambiguous components that agents will struggle to
  differentiate. Resolve by improving descriptions or removing redundant
  components. **Do not declare a model AI-ready without recommending this scan**
  — metadata completeness alone is not sufficient.

---

## Description Quality Guide

A good description covers three things:

1. **Business context** — what business process/entity does this represent?
   Example: `"Purchase Date represents the date the invoice was printed or
   sent to the user."`
2. **How it is used** — where and how is this field/metric used in analysis?
   Example: `"Used as the default date filter in Purchasing and Costing
   analysis."`
3. **Specific data values** — any values with a distinct meaning.
   Example: `"'NA' represents transactions where the purchase was not yet
   confirmed, aligning with Transaction Status = 'Pending'."`
   **When the user provides specific value definitions, always include them
   verbatim in the description.** Do not paraphrase to "values include X, Y,
   Z" without stating what each value means.

**Standard vs. Custom fields:**
- Standard Salesforce objects/fields: default description is acceptable.
  Add context if needed, but never contradict existing known meaning.
- Custom objects/fields: a clear description is required. It should reflect
  what the data represents, align with industry standards, and explain any
  internal-specific meanings.

**Anti-patterns:**
- Copy-pasted descriptions across similar fields → ambiguity
- Descriptions that only state the field name → useless
- Identical descriptions on two fields → agents cannot distinguish them

---

## Field-Level Description Quality

Before moving to metrics, do a quick self-review of every business field
description. For each description, verify it covers **at least two of three**:

1. **Business context** — what business concept does this field represent?
2. **How it's used** — where does it appear in analysis?
3. **Specific values** — do any values have a distinct meaning?

If a description only restates the field name, improve it or ask the user one
targeted question.

**Updating an existing description.** Descriptions (unlike apiNames) are
editable after creation, so you can help the user fix weak or missing ones in
place — no delete-and-recreate needed:
- Dimensions → `update_semantic_model_dimension`
- Measures → `update_semantic_model_measure`
- Metrics → `update_semantic_model_metric`
- Model-level `businessPreferences` →
  `get_semantic_model_business_preferences` then
  `update_semantic_model_business_preferences` (dedicated pair below).
  `agentEnabled` and other model fields → `update_semantic_model`.
  `update_semantic_model` is the fallback for prefs if the dedicated tools
  are unavailable.

Send a **sparse** update for dimensions/measures — only the fields you're
changing (e.g. just `description`), but always echo `isVisible` and
`dataObjectFieldName`. First read the exact apiName back with the matching
`list_*` call (`list_semantic_model_dimensions` / `_measures` / `_metrics`);
a sparse update aimed at an assumed or suffixed name silently misses (see
gate G3). Prefs write is the opposite: full replacement of the string, not
sparse.

**Anti-patterns to catch:**
- `"This field contains the region."` → restates the field name → bad
- Same description on two fields → ambiguity → bad
- `"Values: A, B, C"` without stating what A/B/C mean → incomplete

---

## Label Quality Guide

- The combination of **object name + field label** must unambiguously
  identify the field's role and purpose.
- Bare labels like `"ID"` or `"Name"` are acceptable on well-named objects
  (e.g. `Customer.ID` is interpretable). On ambiguously named objects, they
  cause confusion.
- Avoid abbreviations — agents are trained on full words, not internal codes.
- Never use generic labels like `"Calc1"`, `"Measure2"`, `"Field3"`.

## API Name Quality Guide

- **apiNames are immutable after creation** — they cannot be edited in the
  semantic model after the object or field is created. Choose them
  thoughtfully; the only fix for a bad apiName is delete-and-recreate.
- Choose **descriptive apiNames**, not just syntactically valid ones. An
  apiName like `Gross_Margin_Pct` is more interpretable to agents than `GM1`
  or `Calc3` even if both are valid. The API name is used by agents alongside
  the label.
- This applies to model apiNames, data object apiNames, and calculated
  field/metric apiNames — all are immutable post-create.

---

## Ambiguity Management

Agents analyze the full set of component properties when interpreting a
semantic model. Ambiguity commonly arises from:

- **Overlapping descriptions** — vague or identical descriptions that fail to
  clarify distinct roles. Common cause: copy-pasting.
- **Similar business context** — same concept appearing in multiple tables
  (e.g. "Customer Region" on Orders Header vs. Order Line). Differentiate in
  description which table's version to use for which analysis.
- **Similar calculations** — calculated fields with overlapping formulas, or
  metrics differing only by a filter. Agents read formula definitions directly
  and can be confused even when labels are clear.
- **Synonyms** — two fields with different names representing the same concept
  (e.g. `Revenue` and `Total_Sales` meaning the same thing). Use one; hide or
  remove the other, or describe clearly which is the canonical field. When
  asked to create two fields in the same request with the same or equivalent
  formula, identify one as canonical, decline the other, or ask the user which
  to keep — do not silently create both.
- **Homonyms** — two fields with the same or similar names representing
  different concepts (e.g. `Date` meaning Purchase Date on one object and
  Transaction Date on another). Disambiguate with object-qualified descriptions
  that clarify which date is meant on each object.
- **Same object, different purpose** — a generic `Date` field in the model
  used for both Purchase Date and Transaction Date contexts. Split into two
  calculated dimensions with distinct labels and descriptions.
- **Same object, different granularity** — a fact table that appears twice at
  different grain levels (e.g. Order Lines for detail drill-down vs. an
  aggregated Order Lines for performance). Differentiate them explicitly in
  the object description and label; state which grain each represents.
- **Island objects** — objects with no relationships to the rest of the model.
  Agents may attempt to query them as if they were connected.

**Mitigation:** Run the Semantic Model AI Optimization similarity scan
periodically. Resolve `modelHealth: Low` before deploying to AI users.

---

## Field Type Accuracy

Agentforce for Analytics evaluates eight properties per field when interpreting
a model: Object Name, Object Description, Field Display Name, Field
Descriptions, Field Data Type, Field Role, Sample Values, and
object/field relationships. Ensure each is correct.

- **Data type:** Date columns must use `dataType: "Date"` or `"DateTime"`, not
  `"Text"`. Agents cannot perform time-based analysis on dates stored as strings.
- **Semantic role (measure vs. dimension):** Numeric measures must be classified
  as measures, not dimensions. This signals how agents should apply the field —
  aggregate vs. filter. A numeric field typed as a dimension will not aggregate
  correctly in agent-generated queries.
- **Sample values:** Agents use sample values to infer the meaning and range of
  a field when descriptions are vague. Ensure the underlying data is populated
  (Step 2 row gate) — agents cannot reason about an empty field.
- Validate all field mappings before marking a model AI-ready.

---

## businessPreferences Examples

The `businessPreferences` field is a single string: **one preference per
line, each line beginning with `# `** (hash + space), matching the Edit
Business Preferences UI and the dedicated get/update tools. Do not join
statements with inline `#` delimiters.

```text
# Revenue = sum of Amount on closed-won opportunities only
# Stage names are 0-Prospecting, 1-Qualification, 2-Value Proposition, 3-Id. Decision Makers, 4-Perception Analysis, 5-Proposal/Price Quote, 6-Closed Won
# Region refers to the sales territory assignment on the Account record, not the billing address geography
```

Set this via `create_semantic_model` (if the API accepts it at create time)
or, after creation, via the dedicated read/write pair below. Same `# `-
prefixed-line format on either path. `update_semantic_model` is the
fallback if the dedicated tools are unavailable.

## businessPreferences read / write tools

Prefer these over `get_semantic_model` / `update_semantic_model` when the
only change is preferences — they leave the rest of the model untouched.

**Read — `get_semantic_model_business_preferences`.** Always pass
`includeModelContent=false` so only the profile is returned, not the full
model. Returns `businessPreferences` (a single string: one preference per
line, each line beginning with `# `, matching the Edit Business Preferences
UI) and `isBusinessPreferencesInherited` (`true` when the value comes from
a base model, `false` when this model has its own, **absent** when the
model extends nothing). Prefer this over `get_semantic_model` when you
don't need model content. To draft a candidate without saving, use
`generate_business_preference`, then persist with the dedicated write tool
below.

**Write — `update_semantic_model_business_preferences`.** FULL REPLACEMENT
of the preferences string, not a merge — GET first, then send back the
complete new value. Send **only** `businessPreferences` (do not include
label, description, data objects, etc.). One preference per line, each
beginning with `# `. Up to 30000 characters. Empty string **clears** all
preferences; **omitting** the field leaves them unchanged. Writing
preferences on a model that inherits them overrides the inherited value
rather than editing the base model — the result has
`isBusinessPreferencesInherited: false`. Not for changing the model graph
(`add_semantic_model_*` / `update_semantic_model_*` entity tools).

Both tools may double-wrap as
`{"defaultExc": "<stringified JSON>", "responseCode": <number>}` — parse
`JSON.parse(response.defaultExc)` for the body.