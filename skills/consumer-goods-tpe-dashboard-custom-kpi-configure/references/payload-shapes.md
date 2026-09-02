# Payload shapes — captured from a live test org (2026-08-17)

Captured against a live TPM test org (namespaced install, org apiVersion `68.0`). **API version note:** `v64.0` (assumed in the original SKILL.md draft) returns
`DOWNGRADE_VERSION_ERROR` on `GET /tableau/visualizations/{id}` in this org — "uses features that
aren't available in this version of the API." The initial capture pass used `v68.0` (the org's own
apiVersion at the time). **Per standing instruction, `scripts/clone-tpe-dashboards.js` and SKILL.md
now pin every call to `v67.0` instead of resolving the org's own apiVersion** — the `v68.0` examples
below reflect the original discovery capture and remain valid shape references, but the driver
script itself always sends `v67.0`.

## How to find the real artifact ids — don't guess names, walk the app's asset list

`GET /services/data/v68.0/app-framework/apps?templateSourceId=sfdc_internal__Trade_Promotion_Effectiveness`
returns the installed TPE_Analytics app(s) (`applicationStatus: "SuccessStatus"`). Each app object
has an `assetUrl` (`/services/data/v68.0/app-framework/apps/{appId}/assets`). GET that — it returns
every asset the install created, typed and named:

```json
{"appId":"...", "assets":[
  {"id":"1zB...","type":"Dataspace", ...},
  {"id":"1zB...","type":"Workspace","templateAssetSourceName":"Trade_Promotion_Effectiveness_Analytics", ...},
  {"id":"1zB...","type":"SemanticModel","templateAssetSourceName":"Trade_Promotion_Management_Analytics", ...},
  {"id":"1zB...","type":"SemanticModel","templateAssetSourceName":"Extended_Trade_Promotion_Management_Analytics","assetIdOrName":"2SMVW000000BkJT4A0","assetIdOrName2":"Extended_Trade_Promotion_Managemen_4a9"},
  {"id":"1zB...","type":"Visualization","templateAssetSourceName":"Promotion_Performance_Measures","assetIdOrName":"1AKVW000004YvHl4AK", ...},
  {"id":"1zB...","type":"Visualization","templateAssetSourceName":"Tactic_Performance_Measures", ...},
  {"id":"1zB...","type":"Dashboard","templateAssetSourceName":"PromotionAnalysis","assetIdOrName":"0TrVW0000004Fi10AE", ...},
  {"id":"1zB...","type":"Dashboard","templateAssetSourceName":"TacticAnalysis","assetIdOrName":"0TrVW0000004Fi20AE", ...},
  ... 17 more Visualization assets ...
]}
```

Each asset's `assetIdOrName` is the real record Id to `GET` directly (e.g.
`/tableau/visualizations/{assetIdOrName}`, `/tableau/dashboards/{assetIdOrName}`, or
`/ssot/semantic/models/{assetIdOrName}`). This is the authoritative way for Phase 0 to resolve
"which Extended SDM / which base dashboards / which base visualizations" for a given org — never
hardcode an id or api-name across orgs.

## Extended TPM Analytics SDM — GET the whole model, not per-parameter

`GET /services/data/v68.0/ssot/semantic/models/{modelId}` (e.g. `2SMVW000000BkJT4A0`) returns the
**entire model** in one response — there is no working single-parameter GET confirmed; read the
whole model and index into `semanticParameters[]` / `semanticCalculatedMeasurements[]` by
`apiName`. Top-level keys of interest: `apiName`, `semanticParameters`, `semanticCalculatedMeasurements`,
`semanticCalculatedDimensions`, `semanticDataObjects`, `semanticMetrics`, `semanticRelationships`.

### `semanticParameters[]` — exactly 5 entries in the base Extended model, one per slot

```json
{
  "allowedValues": [
    {"displayName": "Actual Gross Profit", "value": "PATP"},
    {"displayName": "Actual Gross Revenue", "value": "TARE"},
    {"displayName": "Actual Incr. Gross Revenue", "value": "PAIR"},
    {"displayName": "Actual Non-Promo Spend", "value": "PATL"},
    {"displayName": "Actual Profit Margin %", "value": "PAPM"},
    {"displayName": "Actual Total Promo Spend", "value": "PAPS"},
    {"displayName": "Actual Total Volume", "value": "TAVO"},
    {"displayName": "LE Gross Profit", "value": "PLTP"},
    {"displayName": "LE Gross Revenue", "value": "PLTR"},
    {"displayName": "LE Incr. Gross Revenue", "value": "PLIR"},
    {"displayName": "LE Non-Promo Spend", "value": "PLTL"},
    {"displayName": "LE Total Promo Spend", "value": "PLPS"},
    {"displayName": "LE Total Volume", "value": "PLTV"}
  ],
  "apiName": "Promotion_Measure_1_prm",
  "baseModelApiName": "Trade_Promotion_Management_Analyti_4a9",
  "dataType": "Text",
  "defaultValue": "Actual Total Promo Spend",
  "id": "1DOVW000000pMdP4AU",
  "label": "Promotion Measure 1",
  "type": "List",
  "values": []
}
```

**Corrected understanding — this is NOT a single measure-code field to overwrite.** A slot
parameter is a **List** parameter whose `allowedValues` is the full menu of KPI measure codes the
end user can pick at runtime (`value` = 4-char measure code, `displayName` = label shown in the UI),
and `defaultValue` is which `displayName` is preselected. The 13 entries above already cover the
base model's standard KPIs — these are **not customer input**, they're what ships.

**What "customer measure code + display name" actually means for this skill:** the customer is
either (a) picking a **different existing** `allowedValues` entry as the new default (a pure
`defaultValue` swap, no new entry needed), or (b) introducing a **genuinely new** KPI not in the
base 13, which requires **appending** a new `{displayName, value}` entry to `allowedValues` *and*
setting `defaultValue` to that new `displayName`. Either way, the underlying `value` (measure code)
must resolve against real data already reachable from the semantic model (the `Measure_Definition`
dimension referenced by the calculated measurement below) — this skill does not create that
underlying data; it assumes `setup-rtr-datacloud-export`/data-kit setup already populated it.
Never guess whether a code is "new" — check it against the base `allowedValues` first.

### `semanticCalculatedMeasurements[]` — the field a visualization actually references

Each slot has a matching calculated measurement (`Promotion_Measure_1_value`,
`Promotion_Measure_2_value`, `Promotion_Measure_3_value`, and presumably `Tactic_Measure_1_value`,
`Tactic_Measure_2_value` on the Tactic side — confirm both dashboards' sets during a real run):

```json
{
  "aggregationType": "Sum",
  "apiName": "Promotion_Measure_1_value",
  "baseModelApiName": "Trade_Promotion_Management_Analyti_4a9",
  "dataType": "Number",
  "directionality": "Up",
  "expression": "IF [Parameters].[Promotion_Measure_1_prm] == [Measure_Definition].[Measure_Code] THEN [Promotion_Product_Measure].[Measure_Value]\nELSE null\nEND",
  "id": "1DOVW000000pMct4AE",
  "isOverrideBase": false,
  "isQueryable": "Queryable",
  "isVisible": true,
  "label": "Promotion Measure 1",
  "level": "Row",
  "sentiment": "SentimentTypeUpIsGood",
  "shouldTreatNullsAsZeros": false,
  "totalAggregationType": "Sum"
}
```

**This is the critical corrected finding versus the original SKILL.md draft: visualizations and
dashboard `parameter` widgets reference the *parameter* directly by `apiName`
(`Promotion_Measure_1_prm`), but visualizations reference the *calculated measurement* by `apiName`
(`Promotion_Measure_1_value`) — two different artifacts, two different apiNames, linked to each
other only through the measurement's `expression` string** (`[Parameters].[Promotion_Measure_1_prm]`).
**Cloning a slot means cloning BOTH the parameter and its calculated measurement** — the cloned
measurement's `expression` must be rewritten to reference the cloned parameter's new apiName, not
the base one.

Create endpoints (unverified against a live POST in this pass — confirm request-body shape matches
the GET shape above before relying on it, per SKILL.md Phase 0 Rules):
- `POST /services/data/v68.0/ssot/semantic/models/{modelApiName}/parameters`
- `POST /services/data/v68.0/ssot/semantic/models/{modelApiName}/calculated-measurements`

## Visualization — `GET /services/data/v68.0/tableau/visualizations/{id}`

Top-level keys: `createdBy`, `createdDate`, `dataSource`, `description`, `fields`, `id`,
`interactions`, `label`, `lastModifiedBy`, `lastModifiedDate`, `name`, `permissions`,
`sourceVersion`, `templateSource`, `view`, `visualSpecification`, `workspace`.

- `dataSource.name` — the semantic model's apiName (`Extended_Trade_Promotion_Managemen_4a9`).
  Stays the same for a customer clone (same Extended model, not a new one).
- `fields.{F1..Fn}` — each field entry may have a `fieldName` pointing at a calculated measurement
  apiName (e.g. `"fieldName": "Promotion_Measure_1_value"`) plus a `label` that's a cosmetic string
  literally embedding the *parameter's* **label** (not its apiName), e.g.
  `"<[Parameters].[Promotion Measure 1]>"` (stored HTML-double-escaped as
  `"&amp;lt;[Parameters].[Promotion Measure 1]&amp;gt;"`). **Confirmed live this must be updated,
  not left as-is — see the `Cust5` section below.** An apiName-only string replace never touches
  this text (it contains no apiName substring), so it silently keeps showing the base parameter's
  label after a clone unless the parameter's label is *also* replaced inside the
  `[Parameters].[<label>]` pattern.
- **The `Promotion_Measure_1_value` apiName string can also appear inside expression strings**,
  e.g. `view.viewSpecification.aggregateFilter.filters[].filter.fields[].expression`:
  `"SUM([Promotion_Measure_1_value])"`. **A structural find-and-replace on `fields[].fieldName`
  alone is not sufficient** — Phase 3's clone-and-swap must do a full-JSON string replace of the
  base calculated-measurement apiName with the new cloned one, not just patch `fieldName` fields.
  Do the replace on the longest/most-specific apiNames first to avoid partial-substring collisions
  if slot-count ever grows past single digits (not an issue with the current 5 slots, still good
  practice).
- Fields to strip before POSTing a clone: `id`, `createdBy`, `createdDate`, `lastModifiedBy`,
  `lastModifiedDate`, `permissions`, `templateSource`, `sourceVersion`, `view.id`,
  `view.viewSpecification` sub-ids if present — **unconfirmed which fields the create endpoint
  actually rejects vs. ignores; verify with a real trial POST before assuming this strip list is
  complete or correct.**
- `name` is the visualization's unique apiName — must be suffixed for the clone
  (`Promotion_Performance_Measures` → `Promotion_Performance_Measures_<Suffix>`).

Create endpoint (unverified against a live POST in this pass):
`POST /services/data/v68.0/tableau/visualizations`

## Dashboard — `GET /services/data/v68.0/tableau/dashboards/{id}`

Top-level keys: `createdBy`, `createdDate`, `customViews`, `description`, `id`, `label`,
`lastModifiedBy`, `lastModifiedDate`, `layouts`, `name`, `permissions`, `style`, `templateSource`,
`url`, `widgets`, `workspaceIdOrApiName`.

`widgets` is a map keyed by widget name (`visualization_1`, `parameter_3`, `filter_2`, `text_18`,
`container_1`, ...). **Three widget `type`s matter for the swap:**

- **`type: "visualization"`** — `widget.source = {id, label, name, type: "Visualization"}` points
  at the base visualization by `id`/`name`. Must be repointed at the Phase 3 cloned visualization's
  new `id`/`name`.
- **`type: "parameter"`** — this is the on-dashboard KPI picker control the end user interacts
  with. `widget.parameters.parameterName = "Promotion_Measure_1_prm"` (the parameter's apiName,
  directly — not the measurement). `widget.source` points at the SemanticModel (unchanged — same
  Extended model). Must repoint `parameterName` at the Phase 2 cloned parameter's new apiName.
  Confirmed 3 such widgets on `PromotionAnalysis` (`parameter_3/4/5` → `Promotion_Measure_1/2/3_prm`
  respectively) with human-friendly `label`s ("Primary Measure", "Compare Measure", "Measure For
  Bubble Plot") distinct from the parameter's own `label` — preserve those dashboard-widget labels
  as-is on clone unless the customer wants them renamed too.
- **`type: "text"`** with a `dynamicTokens` map — cosmetic KPI-value callouts
  (`"label": "Sum(Promotion_Measure_1_value)"`, `source.name` = the Extended model). References a
  calculated-measurement apiName inside the token's generated label/expression. Not required for
  the dashboard to function correctly post-swap, but leaving these unswapped means the on-dashboard
  text callouts still show the *base* KPI's computed value/label instead of the customer's chosen
  one — cosmetic drift, not a functional bug. Decide during implementation whether to swap these
  too for full fidelity, or explicitly document them as a known-cosmetic gap.
- `layouts[].pages[].widgets[]` reference widgets **by `name`** (the same key as in the `widgets`
  map) — since a clone keeps the same widget names/layout, **layouts require no changes**, only
  the referenced widgets' `source`/`parameterName` do.

Fields to strip before POSTing a clone: `id`, `createdBy`, `createdDate`, `lastModifiedBy`,
`lastModifiedDate`, `permissions`, `templateSource`, `url` — **unverified, confirm with a live trial
POST.**

Create endpoint (unverified against a live POST in this pass):
`POST /services/data/v68.0/tableau/dashboards`

## CORRECTED: Tactic-side calculated measurements are named `_clc`, not `_value`

Confirmed live (2026-08-17, second real trial-write pass): the Promotion slots' calculated
measurements are `Promotion_Measure_{1,2,3}_value`, but the **Tactic slots' calculated measurements
are `Tactic_Measure_1_clc` / `Tactic_Measure_2_clc`** — a different suffix, not the `_value` pattern
assumed by symmetry in the first discovery pass. There is no `Tactic_Measure_1_value` /
`Tactic_Measure_2_value` in the base model. Their `expression`s also reference a different measure
object (`[Promotion_Offer_Product_Measure2].[Measure_Value3]`, not
`[Promotion_Product_Measure].[Measure_Value]`). Confirmed via
`GET /ssot/semantic/models/Extended_Trade_Promotion_Managemen_4a91` and cross-checked against the
`Tactic_Performance_Measures` visualization's `fields[].fieldName`, which reference `_clc` apiNames
directly. **Never assume Tactic mirrors Promotion's `_value` naming — always resolve both slots'
measurement apiNames from the live model, per slot, never by pattern.**

## CONFIRMED: real POST body shapes (live trial writes, 2026-08-17)

All four create endpoints were exercised for a full 5-slot clone (suffix `Cust`) and succeeded.
**The create body is a small curated subset of the GET shape — not the GET response minus
`id`/audit fields.** Passing extra GET-only fields causes `JSON_PARSER_ERROR` (`"Unrecognized
field ..."`), one field at a time (Jackson strict deserialization — it reports only the first
unrecognized field per request, so a naive strip-and-retry loop surfaces one bad field per attempt).

### `POST /ssot/semantic/models/{modelApiName}/parameters`

Minimal accepted body — no `id`, `baseModelApiName`, `createdBy/Date`, `lastModifiedBy/Date`,
`overriddenProperties`, `values`:
```json
{
  "apiName": "Promotion_Measure_1_prm_Cust",
  "label": "Promotion Measure 1",
  "type": "List",
  "dataType": "Text",
  "allowedValues": [ /* full array, base entries + any new/changed entry */ ],
  "defaultValue": "Actual Total Promo Spend Cust"
}
```
Response echoes back the full GET shape (adds `id`, `createdBy`, etc.) — HTTP 200, synchronous, no
poll needed.

### `POST /ssot/semantic/models/{modelApiName}/calculated-measurements`

Minimal accepted body — no `id`, `baseModelApiName`, `createdBy/Date`, `lastModifiedBy/Date`,
`overriddenProperties`, `filters`, `decimalPlace`, `displayCategory`, `semanticDataType`,
`sortOrder`:
```json
{
  "apiName": "Promotion_Measure_1_value_Cust",
  "label": "Promotion Measure 1",
  "dataType": "Number",
  "aggregationType": "Sum",
  "totalAggregationType": "Sum",
  "level": "Row",
  "isQueryable": "Queryable",
  "isVisible": true,
  "directionality": "Up",
  "sentiment": "SentimentTypeUpIsGood",
  "shouldTreatNullsAsZeros": false,
  "expression": "IF [Parameters].[Promotion_Measure_1_prm_Cust] == [Measure_Definition].[Measure_Code] THEN [Promotion_Product_Measure].[Measure_Value]\nELSE null\nEND"
}
```
Create the parameter first — the expression must reference the parameter's *final* apiName.
Synchronous, HTTP 200, no poll needed.

### `POST /tableau/visualizations`

Take the full GET response and:
1. `del(.id, .createdBy, .createdDate, .lastModifiedBy, .lastModifiedDate, .permissions, .sourceVersion, .templateSource, .view.id, .view.isOriginal)`
2. Recursively (`walk`) `del(.id, .url, .permissions, .createdBy, .createdDate, .lastModifiedBy, .lastModifiedDate, .sourceVersion, .templateSource)` at every nested object.
3. Do the full-JSON string replace of every base calculated-measurement apiName with its clone
   (covers `fields[].fieldName` and the `aggregateFilter` expression string in one pass).
4. Set `.name` to the suffixed apiName.
`dataSource` stays the same Extended model reference (with only `.name` surviving the strip — no
`.url`). Synchronous, HTTP 200, no poll needed.

### `POST /tableau/dashboards`

Take the full GET response and:
1. `del(.customViews)` — rejected outright, not just its `id`/audit sub-fields.
2. Recursively `del(.id, .url, .permissions, .createdBy, .createdDate, .lastModifiedBy, .lastModifiedDate, .sourceVersion, .templateSource, .status)` at every nested object — `.status` ("Ok") on every widget is rejected.
3. Recursively, for any object whose `.type` is `"Visualization"` or `"SemanticModel"` (i.e. every
   `source`/`dynamicTokens[].source` reference), `del(.label, .type)` — these ref objects accept
   **only `.name`** (plus `.id` if you want to also pass it, but it's optional/ignored on create;
   this pass omitted it after the generic id-strip and it worked). **Do NOT delete `.type` on the
   widget object itself** (`widgets.*.type`, e.g. `"text"`/`"visualization"`/`"parameter"`/`"filter"`/`"container"`)
   — that one is the required polymorphic discriminator
   (`sfdc.unified.analytics.connect.api.input.widgets.AnalyticsWidgetInputRepresentation`); deleting
   it errors with `"missing property 'type' that is to contain type id"`.
4. String-replace every base parameter/measurement apiName occurrence (parameter widgets'
   `parameters.parameterName`, text widgets' `dynamicTokens.*.tokenSpec.fieldName` and `.label`,
   and the same string inside `content[].insert.token.label`) with the suffixed one.
5. Patch the specific `visualization`-type widget(s)' `source.name` to the new cloned visualization
   name (leave everything else about that widget, including its own `id`→already-stripped, alone).
6. Set `.name` to the suffixed apiName.
`layouts[]` needs no changes — it references widgets only by their unchanged `name` keys, confirmed
on both dashboards. Synchronous, HTTP 200, no poll needed.

## Resolved open questions

- **POST body shapes**: confirmed above for all four endpoints, via a real 5-slot clone (Promotion
  Measure 1-3 + Tactic Measure 1-2, suffix `Cust`) that ran end-to-end and was re-verified with GETs.
- **Synchronous vs. async**: all four create calls return the created resource directly, HTTP 200 —
  no polling needed for any of the four (unlike the `app-framework/apps` install flow elsewhere in
  this skill family).
- **apiName uniqueness**: confirmed — enforced. A same-suffix re-run against already-cloned
  `apiName`s fails on the parameters POST with `CREATE_SEMANTIC_ENTITY_FAILED`. Always use a suffix
  that hasn't been used before in that model, or delete the prior clone set first.
- **Tactic dashboard/visualization shape symmetry**: confirmed — `TacticAnalysis`/`Tactic_Performance_Measures`
  follow the same widget/field shapes as the Promotion side, with the one naming difference noted
  above (`_clc` vs `_value`).

## CONFIRMED (2026-08-17, second real end-to-end run, suffix `Cust3`): two more real-write bugs found and fixed

The full `scripts/clone-tpe-dashboards.js` driver (see that file) was run for real, twice, after the
manual `Cust` pass above. Both runs surfaced additional real errors not caught by the manual pass —
manual jq/curl trial-and-error does not automatically generalize into working reusable code; always
re-verify a generalized script against a real write, not just a dry-run.

1. **Parameter/measurement `label` must also be suffixed — it's uniqueness-checked, not just `apiName`.**
   A second parameter clone reusing the base `label` verbatim (`"Promotion Measure 1"`, matching the
   shape shown for `Cust` above) failed on a *third* create with `ENTITY_NOT_VALID` /
   `CREATE_SEMANTIC_ENTITY_FAILED`: `"The Promotion Measure 1 label already exists in parameter:
   Promotion Measure 1."` The base parameter and the first (`Cust`) clone apparently got away with a
   shared label, but a second clone with the same label did not — behavior that looks order/count
   dependent, not deterministic, so don't rely on "it worked once" for the label field. **Fix: always
   suffix the label too** (`` `${baseParam.label} ${suffix}` ``, `` `${baseMeasurement.label} ${suffix}` ``),
   not just the `apiName`. The `Cust`-suffixed artifacts created earlier in this file's capture have
   an unsuffixed label and were not corrected retroactively — a future consumer should treat that
   specific `Cust` pass as label-non-conformant, and only the `_clc`/`_value` naming + body-shape
   findings from it as authoritative.
2. **The visualization body's `dataSource` ref must keep its `.type` — the dashboard-only strip rule
   does not apply to visualizations.** Applying the dashboard's "strip `.label`/`.type` from any
   object whose own `.type` is `Visualization`/`SemanticModel`" rule (section above) to the
   visualization POST body too (reusing the same helper function) strips `dataSource.type`
   (`"SemanticModel"`) and fails with `INVALID_INPUT: "Value required for [type]."` The visualization
   create body needs only the generic `id/url/permissions/createdBy/createdDate/lastModifiedBy/
   lastModifiedDate/sourceVersion/templateSource/status` strip (recursive) plus `view.isOriginal` —
   never the source-ref `.label`/`.type` strip. That stricter rule is dashboard-widget-specific only.

Both fixes are applied in `scripts/clone-tpe-dashboards.js`; a full real run with a fresh suffix
(`Cust3`) after these fixes created 5 parameters, 5 measurements, 2 visualizations, and 2 dashboards
successfully end-to-end, and a follow-up GET on the cloned Tactic dashboard confirmed its
`visualization`-type widget's `source.name` and both `parameter`-type widgets' `parameterName` all
correctly point at the new `_Cust3` artifacts. **This "2 visualizations" count and the "every
unrelated widget left untouched" framing were both wrong — see the `Cust4` section below**, which
corrects a real functional gap this `Cust3` verification pass missed (it only checked the one
designated viz widget, not every widget on the dashboard).

## CORRECTED (2026-08-17, third real end-to-end run, suffix `Cust4`): must clone EVERY visualization on the dashboard, not just one "designated" one

The original design assumption — one app-asset visualization per dashboard
(`templateAssetSourceName: "Promotion_Performance_Measures"` / `"Tactic_Performance_Measures"`) is
"the" slot visualization to clone — is **wrong**. Confirmed live by scanning every `visualization`-type
widget on both base dashboards (`PromotionAnalysis1`: 9 widgets; `TacticAnalysis1`: 7 widgets) for
occurrences of any of the 5 base calculated-measurement apiNames: **every single one** of those 16
visualizations (top/bottom performers, trend charts, category/product breakdowns — not just the
one obviously-named "Performance_Measures" viz) references at least one of the 5 slot measurements
in its `fields[]`. A `Cust3`-generation clone that only cloned and repointed the one designated viz
left the other 8 (Promotion) / 6 (Tactic) charts on the cloned dashboard still bound to the **base**
measurement/parameter — those charts would silently keep reflecting the base KPI selection, out of
sync with the customer's chosen measure code, even though the dashboard itself was a "clone."

**Fix, now in `scripts/clone-tpe-dashboards.js`:** for each dashboard, walk its base `widgets{}`
directly (never a hardcoded/guessed viz template name), collect every distinct `visualization`-type
widget's source viz, GET each one, and clone **only those whose JSON contains at least one of that
dashboard's slot measurement apiNames** (a widget with no such reference is genuinely unrelated —
e.g. a purely-narrative chart with no KPI binding — and is correctly left pointing at its base viz,
though no such widget was actually found on either TPE dashboard in this org). Then, when building
the cloned dashboard body, repoint **every** `visualization`-type widget whose base source name has
a clone, not just the one previously assumed.

A full real run with suffix `Cust4` created 5 parameters, 5 measurements, **16 visualizations** (9
Promotion + 7 Tactic), and 2 dashboards. A follow-up GET scanning every widget on both cloned
dashboards confirmed **100% of visualization widgets (9/9 Promotion, 7/7 Tactic) and all 5 parameter
widgets** point at `_Cust4` clones, with zero widgets left pointing at a base artifact.

## FIXED (2026-08-17, fourth real end-to-end run, suffix `Cust5`): cosmetic `fields[].label` text was not being updated

Reported by direct inspection of `Promotion_Performance_Measures2_Cust4`: its `fieldName`s were
correctly repointed to `_Cust4` measurement apiNames, but every field's `label` still read the
unreplaced base text `"&amp;lt;[Parameters].[Promotion Measure 1]&amp;gt;"` (displays as
`<[Parameters].[Promotion Measure 1]>`) — the base parameter's **label**, not its apiName. Root
cause: `replaceApiNamesInJson`'s replacement pairs were built only from apiNames
(`baseParamApi`→`newParamApi`, `baseMeasurementApi`→`newMeasurementApi`); this cosmetic label string
contains neither, so it was never a match.

**Fix, now in `scripts/clone-tpe-dashboards.js`:** the plan now also carries `baseParamLabel` /
`newParamLabel` (`` `${baseParam.label} ${suffix}` ``, matching the already-suffixed parameter
`label` used in the create body). A third replacement-pair list, `labelReplacements`, replaces
`` `[Parameters].[${baseParamLabel}]` `` with `` `[Parameters].[${newParamLabel}]` `` (scoped to the
exact `[Parameters].[<label>]` bracket pattern, not a bare label substring, to avoid clobbering
unrelated text that happens to contain the same words). These pairs are folded into both the
per-visualization replacement pass (added to `relevantReplacements` whenever a viz's JSON contains
that pattern) and the dashboard body's `allReplacements`.

A full real run with suffix `Cust5` created 5 parameters, 5 measurements, 16 visualizations, and 2
dashboards. Follow-up GETs on `Promotion_Performance_Measures2_Cust5` and
`Tactic_Performance_Measures2_Cust5` confirmed every field's `label` now reads e.g.
`<[Parameters].[Promotion Measure 1 Cust5]>` / `<[Parameters].[Tactic Measure 1 Cust5]>` — matching
the suffixed parameter label — alongside the already-correct `fieldName` repointing.

## CONFIRMED (2026-08-17, fifth real end-to-end run, suffix `Cust6`): `--overrides` accepts a genuinely arbitrary customer-chosen measure code + display name

Every prior real run (`Cust`-`Cust5`) only exercised the *no-override* fallback path (base measure
code, base display name + suffix) — the `--overrides` path itself had never been exercised in a real
write. Ran `--overrides '{"Promotion_Measure_1":{"measureCode":"TARE","displayName":"My Custom KPI
Name"}}'` (an existing base allowedValues code, `TARE`/"Actual Gross Revenue", paired with a display
name unrelated to the suffix or the base label) end-to-end for real. Confirmed:
- `newParamBody.allowedValues` correctly appended `{"displayName":"My Custom KPI Name","value":"TARE"}`
  alongside the base 13 entries, with `defaultValue: "My Custom KPI Name"`.
- The other 4 slots (no override supplied) fell back to the base-code + suffixed-label default, as
  designed — overrides are per-slot, not all-or-nothing.
- Both dashboards, all repointed visualizations, and both parameter widgets built successfully with
  the customer-chosen value in place. Mechanism: `slotOverride()` just substitutes the given
  `measureCode`/`displayName` into the same `allowedValues`-append + `defaultValue` logic used for the
  no-override case — there is no dependency anywhere on the value containing or matching the suffix.

## Added (2026-08-17): `--max-vizs-per-dashboard` debug flag

Added to `clone-tpe-dashboards.js` for faster local iteration — caps how many distinct
visualizations get cloned per dashboard; widgets beyond the cap are left pointing at base (same
code path as a genuinely-unrelated widget). Confirmed live with suffix `Dbg1` and
`--max-vizs-per-dashboard 1`: exactly 1 visualization cloned per dashboard (2 total, vs. the normal
16), every other visualization widget correctly left on base, both dashboards still created
successfully. Debug-only — never use on a real customer deliverable, since it leaves most charts
still bound to base measurements.

## CONFIRMED (2026-08-17, sixth/seventh real end-to-end runs, suffixes `Dbg1`/`Dbg2`): two overrides features added — full-list replace mode, and append-mode upsert-by-measureCode

Two follow-up feature requests after the `Cust6` override test:

1. **REPLACE mode** — a slot's `--overrides` entry can now be `{allowedValues: [{displayName, value}, ...], defaultValue?}` instead of `{measureCode, displayName}`. In this mode the customer's array *replaces* the base parameter's allowedValues wholesale (not merged) — for when the customer wants their own complete measure-code menu instead of the base 5-14-entry standard list per slot. `defaultValue` must match one of the supplied entries' `displayName` (defaults to the first entry if omitted) — validated with a thrown error if it doesn't match, not a silent fallback.
2. **APPEND mode now upserts by `measureCode`, not a blind array push.** `allowedValues[].value` (the measure code) is unique within a parameter's menu — the original `Cust6` test appended a *second* `{displayName: "My Custom KPI Name", value: "TARE"}` entry alongside the base `{displayName: "Actual Gross Revenue", value: "TARE"}` entry, leaving two entries sharing the same code with different labels. Fixed: append mode now does `baseParam.allowedValues.filter(v => v.value !== resolved.measureCode)` before appending the new/changed entry — so choosing an *existing* code just relabels that entry in place (list count unchanged), while a genuinely new code still appends normally (list count +1). Confirmed live (`Dbg2`, same `TARE`/"My Custom KPI Name" override as `Cust6`): the created parameter's `allowedValues` has exactly one `TARE` entry (count 13, same as base), `defaultValue: "My Custom KPI Name"` — no duplicate.

Both modes are chosen per-slot by which fields are present in that slot's override object — a single `--overrides` payload can mix append-mode slots and replace-mode slots freely.

## Open item: dashboard selection is not currently configurable

`DASHBOARDS` in `clone-tpe-dashboards.js` is a fixed constant (`Promotion` + `Tactic`) — the main
loop always clones both, regardless of which slots have overrides. There is no `--dashboards` flag
or other mechanism to clone only one. This was an intentional carryover from the original plan's
"always produce all 5 slots' worth of clones, never skipped" rule, extended to dashboards — but if a
customer only cares about one dashboard, this will still always clone both.
