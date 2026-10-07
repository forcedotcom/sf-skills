# Editing an Existing Visualization — `edit_visualization` / `update_visualization`

Load this when the request mutates a visualization that **already exists** (add/
remove/replace a shelf field, filter, forecast, sort, mark encoding, mark type, dual
axis, reference line, quick table calc, axis title, field label, field/axis
visibility, number/date format, table layout/totals, or fit) — not for building a new
chart (`viz-authoring.md`/`tasks/create-viz.md` instead).

## Contents

- 1. Contract
- 2. Operation-type quick reference
- 3. Filter-operator rules
- 4. Filter buckets and `{model:}` vs `{expression:}`
- 5. Add-then-filter heuristic
- 6. Sort operations — `targetField` vs `byField`
- 7. Reference lines: `field.function` vs `line.function`
- 8. Table-layout shelf operations (Columns/Groups)
- 9. Table totals and subtotals
- 10. Layout and fit
- 11. Field label, field-label visibility, axis visibility, number/date format
- 12. Measure Values shelf editing
- 13. Table calcs — `quickTableCalc` types and `computeUsing`
- 14. Logical views and HLV field naming
- 15. Persistence handoff — `update_visualization`

---

## 1. Contract

`edit_visualization`'s **required inputs are `visualizationId` and
`editOperations`** — never pass a raw `visualizationMetadata` blob as input, the
server resolves the metadata itself from the id:

- `visualizationId` — the id from `get_visualization` or a prior edit's response.
  After `create_visualization`, call `get_visualization` first — create returns
  only `{id, label, name}`, no editable metadata to chain from. If a call reports
  the id was **not found**, call `get_visualization` with that id to reload it,
  then retry.
- `editOperations` is a **JSON string** encoding an array of `{operationType, params}`
  objects — build the array, then `JSON.stringify` it; never pass a raw array.
- Operations run **in order**, each seeing the previous one's result.
- The batch is **all-or-nothing** — one failing operation means none are applied.
- The result **renders inline automatically** — never call `render_visualization`
  afterward.
- The result is **never persisted**. The response's `outputValues.visualizationMetadata`
  holds the edited definition (for `update_visualization`, see §15) — there is no
  separate top-level id field in the response. The server keeps per-`visualizationId`
  working state: reuse the **same `visualizationId`** you already have (no need to
  re-read it from the response) to chain straight into another `edit_visualization`
  call, and each call's edits accumulate on top of the previous ones for that id.

## 2. Operation-type quick reference

Every operation targets a field already on a shelf/encoding/axis by
`{fieldName, objectName?, function?}` (`function` disambiguates same-name copies
under different aggregations, e.g. Sum vs Avg of the same measure — never a display
word like "Year", use the canonical values in the Field-functions note below).

| Category | Operations | Sharpest constraint |
|---|---|---|
| Shelf fields | `addFieldToRowsOrColumns`, `removeFieldFromRowsOrColumns`, `replaceFieldFromRowsOrColumns`, `changeFieldOnRowsOrColumns`, `reorderFieldsOnRowsOrColumns` | `changeFieldOnRowsOrColumns` changes an existing field's aggregation, discrete-vs-continuous display, and/or role in place — never adds/removes/swaps. Params `{field, shelfType, occurrence?, function?, displayCategory?, role?}` — supply at least one of `function` (an aggregation), `displayCategory` (`Discrete`/`Continuous`), or `role` (`Dimension`/`Measure`); omitted ones unchanged. Changing to a Measure requires a `function` (`Sum`/`Avg`/`Median`/`Min`/`Max`/`Count`/`CountD`/`Stdev`/`Stdevp`/`Var`/`Varp`); changing to a Dimension drops it. Examples: "average Sales instead of summing it" → `{field: {fieldName: "Sales", objectName: "Orders", function: "Sum"}, shelfType: "columns", function: "Avg"}`; "make Sales on rows discrete" → `{field: {...Sales}, shelfType: "rows", displayCategory: "Discrete"}`; "turn Category into a measure counting distinct values" → `{field: {fieldName: "Category", objectName: "Orders"}, shelfType: "columns", role: "Measure", function: "CountD"}`. Use `occurrence` (1-based) when the same field repeats on a shelf. `addFieldToRowsOrColumns` takes an optional 0-based `insertPosition` (appended when omitted). `reorderFieldsOnRowsOrColumns` moves a field already on the shelf to a new `insertPosition` without adding/removing anything — `insertPosition` is counted over the shelf's fields **after the moved field is taken out first**, so any spot right of its old position shifts left by one; `0` is the front, the shelf's last index the back. |
| Label | `changeLabel` | Renames the **visualization**, not on-chart title text. For a *field's* displayed caption use `editFieldLabel` (§11), not this. |
| Filters | `addFilter`, `editFilter`, `removeFilter` | See §3-5. The field reference lives inside a **`fields` array nested under a `filter` object** — `params: {filter: {fields: [...], operator, values}, bucket}` — never a bare `field:` key. |
| Forecasts | `addForecast`, `editForecast`, `removeForecast` | Timeseries-only (date field + measure). Omitting `forecastInterval` defaults to 4 periods at the date field's own granularity; `forecastInterval` is `{value, timeUnit}` with `timeUnit` ∈ `Minutes`/`Hours`/`Days`/`Weeks`/`Months`/`Quarters`/`Years` to override the period unit explicitly. Other defaults: `forecastModel` → `HoltWinters` (alternative: `RidgeRegression`); `includeBounds` → `true`; `confidenceLevel` → `95` (also `90`/`99`); `fillNullsWithZero` → `false`; `granularity` supports only `InferFromData`. `ignoreLastPeriods` (int) excludes trailing partial/incomplete periods from the fit. Use `occurrence` (1-based) when the target measure repeats on the shelf. `removeForecast` with no `measureField` removes ALL forecasts. Examples: "forecast Sales for 6 months" → `addForecast {measureField: {fieldName: "Sales", objectName: "Orders"}, dateDimensionField: {fieldName: "OrderDate", objectName: "Orders"}, forecastInterval: {value: 6, timeUnit: "Months"}}`; "forecast Revenue 12 months ahead using RidgeRegression" → `addForecast {measureField: {fieldName: "Revenue"}, dateDimensionField: {fieldName: "Date"}, forecastInterval: {value: 12, timeUnit: "Months"}, forecastModel: "RidgeRegression"}`; "change the Sales forecast to 12 months" → `editForecast {measureField: {fieldName: "Sales", objectName: "Orders"}, forecastInterval: {value: 12, timeUnit: "Months"}}`; "remove all forecasts" → `removeForecast {}`. |
| Sort | `sortAscending`, `sortDescending`, `sortByField`, `clearSort` | Only **discrete** fields can be sorted. Target is keyed **`targetField`**, never `field`. See §6. |
| Mark encodings | `addFieldToEncoding`, `removeFieldFromEncoding`, `replaceFieldOnEncoding` | `encodingType` ∈ Color(1 field)/Label(≤3, oldest dropped)/Tooltip(measure only, unlimited)/Size(1 field)/Detail(unlimited). On a **Table** layout only Color/Tooltip are valid slots (Label/Size/Detail error); a dimension dropped onto Color/Tooltip on a Table is coerced to a measure via `Attr`. "Measure Names" is named as `{field: {type: "MeasureNames"}}`, Color-only. `removeFieldFromEncoding`/`replaceFieldOnEncoding` must name the field **currently on that slot** — an arbitrary shelf field errors; read the current encoding first if unsure. Optional `targetField` edits/retypes only ONE field's mark on a multi-measure viz — that field must already be a mark on the visualization or the operation errors; omit it to apply to all marks. Examples: "color by Region" → `addFieldToEncoding {encodingType: "Color", field: {fieldName: "Region", objectName: "Orders"}}`; "add Revenue to the tooltip" → `addFieldToEncoding {encodingType: "Tooltip", field: {fieldName: "Revenue", objectName: "Orders"}}`; "size the bubbles by Sales" → `addFieldToEncoding {encodingType: "Size", field: {fieldName: "Sales", objectName: "Orders"}}`; "color by Region instead of by measure" → `replaceFieldOnEncoding {encodingType: "Color", existingField: {type: "MeasureNames"}, newField: {fieldName: "Region", objectName: "Orders"}}`. |
| Mark type | `changeMarkType` | Only changes shape (`Bar`/`Line`/`Circle`/`Square`/`Donut`/`Text`/`automatic`) — never moves/adds fields, so it cannot alone turn one chart type into another that needs a different shelf layout. Same optional `targetField` single-mark-only mechanism as mark encodings above. On a Table layout only `Text`/`Bar` are valid — any other type (including `automatic`) errors. Examples: "draw the marks as lines" → `{markType: "Line"}`; "let the visualization choose" → `{markType: "automatic"}`; "show the table as text" (Table layout) → `{markType: "Text"}`. |
| Layout and fit | `changeLayout`, `changeVisualizationFit` | See §10. |
| Dual axis | `addDualAxis`, `removeDualAxis`, `synchronizeAxis` | Both fields must already be **adjacent continuous fields on the same shelf** — add the second field first if missing. `primaryField` is the LEFT field, `secondaryField` the RIGHT (shelf order matters; the secondary moves onto the shared axis). `synchronization` ∈ `"None"` (default; independent scales) / `"ZeroPosition"` (zero lines align) / `"FullRange"` (shared range) — optional on `addDualAxis`, **required on `synchronizeAxis`**. `"ZeroPosition"` is invalid when both fields are the same kind of date function (use `FullRange`/`None`). `removeDualAxis`/`synchronizeAxis` name the same (primary, secondary) pair. When the same name+object+function pair still repeats on the shelf (can't disambiguate primary/secondary otherwise), add `primaryOccurrence`/`secondaryOccurrence` (1-based) to pick which copy. |
| Reference lines | `addReferenceLine`, `removeReferenceLine`, `editReferenceLine` | VizQL only. See §7 — the single trickiest disambiguation in this tool. |
| Table calcs | `applyTableCalc`, `editTableCalc`, `removeTableCalc` | Target must already be a shelf measure. `edit`/`removeTableCalc` error if the field has no existing calc. See §13 for `quickTableCalc.type` enum values and `computeUsing`. |
| Axis titles | `editAxisTitle`, `resetAxisTitle` | Target by field, not by axis position. |
| Field label | `editFieldLabel` | Renames a field's displayed caption (axis, row/column header, table header) — distinct from `changeLabel` (renames the viz). See §11. |
| Field-label visibility | `showFieldLabel` | Shows/hides the field labels on a whole shelf. Discrete fields only. See §11. |
| Axis visibility | `showAxis` | Shows/hides the axis for one continuous rows/columns field. See §11. |
| Number/date format | `setFieldFormat` | Currency/percentage/abbreviated/decimal-places number formats, or a date template. See §11. |
| Table-shelf fields | `addFieldToGroupsOrColumns`, `removeFieldFromGroupsOrColumns`, `replaceFieldFromGroupsOrColumns`, `reorderFieldsOnGroupsOrColumns`, `changeFieldOnGroupsOrColumns` | TABLE layout only — the table equivalent of the rows/columns ops above. See §8. |
| Table totals | `showGrandTotals`, `showSubtotals`, `editGrandTotalsLabel`, `editSubtotalsLabel` | TABLE layout only. See §9 — includes a reset-semantics gotcha (`{}` vs `{label:""}`). |
| Measure Values | `addFieldToMeasureValues`, `reorderFieldsOnMeasureValues`, `replaceFieldFromMeasureValues`, `removeFieldFromMeasureValues` | VizQL only, and only once the Measure Names/Measure Values construct already exists on the shelf. See §12. |

**Field functions** (the `function` on a field object) — use canonical values, never
display words: aggregations `Sum/Avg/Median/Count/CountD/Min/Max/Stdev/Stdevp/Var/
Varp/Attr` (`Count`/`CountD`/`Min`/`Max` also apply to dimensions; the rest are
measures only); date parts `DatePart{Year,Quarter,Month,Week,Day,Hour,Minute}`; date
truncations `DateTrunc{Year,Quarter,Month,Week,Day}`; fiscal variants of both exist
(`FiscalDatePartYear`, `FiscalDateTruncQuarter`, …). A date dropped onto a shelf buckets
by year by default — use `DatePartYear` explicitly for a "broken out by year" ask; for
finer/date-part filtering use a `DATEPART`/`DATETRUNC` expression (§4), not a shelf
function.

## 3. Filter-operator rules

1. **Never `Equals`/`DoesNotEquals`.** Always `In`/`NotIn` — `In` with one value is
   the equivalent. "Color is Red" → `operator: "In", values: ["Red"]`.
2. **Always the `IgnoreCase` string variant** — `ContainsIgnoreCase`,
   `StartsWithIgnoreCase`, `EndsWithIgnoreCase`, `DoesNotStartWithIgnoreCase`, etc.
   Users almost never intend case-sensitive matching.
3. **Never `null`/`undefined` in `values`.** If both bounds of a range can't be
   expressed with concrete values, pick a different operator.

Other operator families: comparison (`Between`, `LessThan(OrEqualTo)`,
`GreaterThan(OrEqualTo)`); null/empty (`IsNull`, `IsNotNull`, `IsEmpty`, `IsNotEmpty`);
relative-date (no values: `CurrentWeek`/`PreviousMonth`/`NextYear`… · with `values:[N]`:
`LastNDays`/`NextNWeeks`… — "last/next `<period>`" with no number → singular form,
with a number → `LastN`/`NextN` form, **except** "last 1 quarter" still uses the `LastN`
form with `values:[1]`); fiscal-date variants exist but only fire on an explicit
"fiscal" in the request ("this quarter" ≠ "this fiscal quarter"); date-to-date
(`CurrentYearToDate`, `PreviousQuarterToDate`, …, plain `{model:}`, no expression);
Top/Bottom-N (`operator: "AdvancedDimension"`, `bucket: "advancedDimensionFilter"`,
`topBottomCriteria: {topBottomLimit, isTop, expression}` — always this operator for
any top/bottom-N ask, never a value filter).

## 4. Filter buckets and `{model:}` vs `{expression:}`

Execution order / bucket meaning: `filter` (standard) → `contextFilter` (pre-
aggregation) → `aggregateFilter` (post-aggregation, e.g. `SUM(Sales) > 1000`) →
`tableCalcFilter` (on a table calc) → `advancedDimensionFilter` (Top/Bottom-N).

Decision rule for the filter's field reference:

- **`{model: "Object.Field"}`** — plain row-level comparison, no aggregation keyword.
  "sales > 1000" → `{model: "Orders.Sales"}`.
- **`{expression: "SUM/AVG/…(...)"}`, `bucket: "aggregateFilter"`** — only when the
  request names an aggregate concept explicitly ("total", "sum of", "average", "count
  of"). Without one of those keywords, always use `{model:}`.
- **`{expression: "DATEPART(...)"}`/`"DATETRUNC(...)"`** — date-part/date-trunc
  phrasing ("orders from 2020 and 2021", "after June 2022"). `DATEPART` returns an
  integer; `DATETRUNC` returns a date (values as ISO strings).
- **`{expression: "RUNNING_*/RANK/WINDOW_*(...)"}`, `bucket: "tableCalcFilter"`** —
  running total/avg/rank/window/moving/cumulative phrasing. These always wrap an
  aggregate expression as their inner argument (e.g. `RANK(SUM([Orders].[Profit]),
  'ASC')`).

**Whole-`params` shape.** The field reference (`{model:}` or `{expression:}`) is never
passed alone — it sits inside a **`fields` array**, itself nested under a **`filter`**
object, which is a sibling of `bucket` at the top of `params`:

```json
{"operationType": "addFilter", "params": {
  "bucket": "filter",
  "filter": {"fields": [{"model": "Orders.Region"}], "operator": "In", "values": ["East", "West"]}
}}
```

Full worked examples, each showing the complete `params` object:

- "sales greater than 1000" (raw field):
  `{filter: {fields: [{model: "Orders.Sales"}], operator: "GreaterThan", values: [1000]}, bucket: "filter"}`
- "orders from 2020 and 2021":
  `{filter: {fields: [{expression: "DATEPART('year', [Orders].[Order_Date])"}], operator: "In", values: [2020, 2021]}, bucket: "filter"}`
- "orders after June 2022" (DATETRUNC, ISO values):
  `{filter: {fields: [{expression: "DATETRUNC('month', [Orders].[Order_Date])"}], operator: "GreaterThan", values: ["2022-06-01"]}, bucket: "filter"}`
- "where total sales > 10000" (aggregate):
  `{filter: {fields: [{expression: "SUM([Orders].[Sales])"}], operator: "GreaterThan", values: [10000]}, bucket: "aggregateFilter"}`
- "where profit margin > 15%":
  `{filter: {fields: [{expression: "SUM([Orders].[Profit])/SUM([Orders].[Sales])"}], operator: "GreaterThan", values: [0.15]}, bucket: "aggregateFilter"}`
- "where running sum of sales > 1000":
  `{filter: {fields: [{expression: "RUNNING_SUM(SUM([Orders].[Sales]))"}], operator: "GreaterThan", values: [1000]}, bucket: "tableCalcFilter"}`
- "top 10 states by sales":
  `{filter: {fields: [{model: "Orders.State"}], operator: "AdvancedDimension", topBottomCriteria: {topBottomLimit: 10, isTop: true, expression: "SUM([Orders].[Sales])"}}, bucket: "advancedDimensionFilter"}`

`editFilter` updates an existing filter's expression (same `params` shape, matched
against the current filter's field). `removeFilter` removes one by field reference:
`{filterField: {model: "Object.Field"}}`.

## 5. Add-then-filter heuristic

Add a field to a shelf **before** filtering it only when the user wants to *display*
that dimension broken out by value **and** restrict which values show, and it isn't
already on a shelf. A pure restriction ("filter to top 10 customers", "only show the
West region", "show orders from this year") is a single `addFilter` — never add a
field just because a filter names a dimension. If the field is already on a shelf,
filter/sort it in place.

Example (add-then-filter, two chained operations): "I want to see Region in East and
West" (no Region on a shelf yet) →
```json
[
  {"operationType": "addFieldToRowsOrColumns", "params": {"field": {"fieldName": "Region", "objectName": "Orders"}, "shelfType": "rows"}},
  {"operationType": "addFilter", "params": {"filter": {"fields": [{"model": "Orders.Region"}], "operator": "In", "values": ["East", "West"]}, "bucket": "filter"}}
]
```

## 6. Sort operations — `targetField` vs `byField`

Sorts apply to a **discrete** field already on a shelf (chart rows/columns, or table
columns/groups — sort works on both layouts). The field being sorted is keyed
**`targetField`** — never `field` — `{fieldName, objectName?, function?}`. Every copy
of the field on the shelf stays in sync.

- **`sortAscending`/`sortDescending`** sort by the target field's OWN values (A→Z /
  Z→A). If the field is already sorted by another field, these keep that by-field
  sort and only flip direction; pass `sortType: "Alphabetic"` to force a plain
  alphabetic sort and drop an existing by-field sort.
- **`sortByField`** sorts `targetField` by the AGGREGATED value of a second field,
  `byField` `{fieldName, objectName?, function?}`. `byField.function` is the
  aggregation — measures keep their default when omitted, dimensions default to
  `Count` (dimensions allow only `Count`/`CountD`/`Min`/`Max`). `sortType`: `"Field"`
  (default) or `"Nested"` (ordered within each group). `descending` (boolean) defaults
  `true` — set `false` for smallest-first.
- **`clearSort`** removes the current sort — just `{targetField}`.

Worked examples:

- "Sort Category A to Z": `sortAscending {targetField: {fieldName: "Category", objectName: "Orders"}}`
- "Sort Category Z to A": `sortDescending {targetField: {fieldName: "Category", objectName: "Orders"}}`
- "Sort Region to ascending alphabetic" (Region currently sorted by another field):
  `sortAscending {targetField: {fieldName: "Region", objectName: "Orders"}, sortType: "Alphabetic"}`
- "Sort States by total Sales, largest first":
  `sortByField {targetField: {fieldName: "State", objectName: "Orders"}, byField: {fieldName: "Sales", objectName: "Orders", function: "Sum"}}`
- "Nest a descending sort on Region by sum of Profit":
  `sortByField {targetField: {fieldName: "Region", objectName: "Orders"}, byField: {fieldName: "Profit", objectName: "Orders", function: "Sum"}, sortType: "Nested"}`
- "Sort Category by count of Orders, smallest first":
  `sortByField {targetField: {fieldName: "Category", objectName: "Orders"}, byField: {fieldName: "Order_Id", objectName: "Orders", function: "Count"}, descending: false}`
- "Clear the sort on States": `clearSort {targetField: {fieldName: "State", objectName: "Orders"}}`

## 7. Reference lines: `field.function` vs `line.function`

The reference-line operations' single trickiest gotcha — two different `function`
fields that are easy to conflate:

- **`field.function`** selects *which shelf pill* the line attaches to (its own
  aggregation) — e.g. when Sum-of-Sales and Avg-of-Sales are both on the shelf.
  A phrase like **"sum of sales"** in a reference-line request names *this* field,
  not the line's statistic.
- **`line.function`** is the line's *own* computed statistic (an average line, a max
  line) — set it only when the request explicitly names the line's statistic
  ("add an **average** line", "a **max** line").

So "add a reference line to Sum of Sales" means: attach to the Sum-of-Sales pill and
use the *default* line (which is an average line when omitted) — it does **not**
mean a sum line. Two kinds of line: `{valueType: "Computation", function}` (a
statistic — `function` ∈ `Sum`/`Avg`/`Min`/`Max` for a measure axis or
`Max`/`Min`/`Today`/`Now` for a date axis; defaults to average for a measure /
latest-date for a date field when `line` is omitted entirely) or `{valueType:
"Value", value}` (a constant — a number for a measure axis or ISO date string for a
date axis). `line.computationField` (`{fieldName, objectName?, function?}`, need not
be on a shelf) lets the line compute from a *different* field than the one it's drawn
on. An optional label lives INSIDE `line`: `labelType` ∈ `None`/`Value`/`Computation`/
`Custom` (with `customLabel`); `scope` ∈ `Table` (default)/`Pane`/`Cell`; `lineColor`
is a top-level hex (default gray), accepted by both add and edit. Position a specific line among several on the same field
with `lineOccurrence` (1-based, counts lines); `occurrence` instead picks which
*shelf pill* when the field repeats — the two are independent and both may be needed
("2nd reference line on the 2nd Sum of Sales" → `occurrence: 2, lineOccurrence: 2`).
Beyond position, a line can also be disambiguated by matching its current
`computationFunction`, `value`, `labelText`, `scope`, or `lineValueType` — useful
when the request describes the line itself ("the average line", "the line labeled
Goal") rather than its position.
`removeReferenceLine` with no scope removes every matching line on the field.
`editReferenceLine` changes exactly ONE line and **errors if the description
matches more than one** — narrow with `occurrence`/`lineOccurrence`/`scope`/one of
the descriptive selectors above until it's unambiguous. Each attribute on
`editReferenceLine` edits independently: omitting `line` keeps the line's current
value/function; a `line` change keeps the current label unless you also pass
`labelType`/`customLabel`; passing only `scope` or `lineColor` changes just that
attribute and leaves everything else (value, label) untouched. A label passed at
the top level of `params` wins over one nested inside `line`.

Worked examples:

- "add an average line to Sales" (default line): `addReferenceLine {field: {fieldName: "Sales", objectName: "Orders"}}`
- "add a target line at 5000 on Sales" (constant): `addReferenceLine {field: {fieldName: "Sales", objectName: "Orders"}, line: {valueType: "Value", value: 5000}}`
- "add a line at 100 on avg of Sales labeled 'target' in green": `addReferenceLine {field: {fieldName: "Sales", objectName: "Orders", function: "Avg"}, line: {valueType: "Value", value: 100, labelType: "Custom", customLabel: "target"}, lineColor: "#00FF00"}`
- "add a sum line for Sales per pane": `addReferenceLine {field: {fieldName: "Sales", objectName: "Orders"}, line: {valueType: "Computation", function: "Sum"}, scope: "Pane"}`
- "add an average line on Sales computed using sum of Discount": `addReferenceLine {field: {...Sales}, line: {valueType: "Computation", function: "Avg", computationField: {fieldName: "Discount", objectName: "Orders", function: "Sum"}}}`
- "make the Sales reference line red" (color only, omit `line`): `editReferenceLine {field: {...Sales}, lineColor: "#FF0000"}`
- "remove the 2nd reference line on avg of Sales": `removeReferenceLine {field: {fieldName: "Sales", objectName: "Orders", function: "Avg"}, lineOccurrence: 2}`
- "update the 2nd reference line on the 1st Sum of Sales to a max line" (BOTH selectors): `editReferenceLine {field: {fieldName: "Sales", objectName: "Orders", function: "Sum"}, occurrence: 1, lineOccurrence: 2, line: {valueType: "Computation", function: "Max"}}`

## 8. Table-layout shelf operations (Columns/Groups)

TABLE-layout visualizations use two shelves — **Columns** (fields shown as table
columns) and **Groups** (fields those columns are grouped by) — instead of
rows/columns. These operations are the table equivalent of §2's shelf-field row and
**do not apply to a VizQL chart** — convert to Table first with `changeLayout` (§10),
or these error. `shelfType` names the shelf: `"columns"` or `"groups"`; the target
field nests under a `"field"` object exactly like `addFieldToRowsOrColumns`, using
the same canonical `function` values.

- `addFieldToGroupsOrColumns` — `{field, shelfType, insertPosition?}` (0-based;
  appended when omitted).
- `removeFieldFromGroupsOrColumns` — `{field, shelfType, occurrence?}` (1-based,
  picks the copy).
- `replaceFieldFromGroupsOrColumns` — `{existingField, newField, shelfType,
  occurrence?}`, keeping the replaced field's position.
- `reorderFieldsOnGroupsOrColumns` — `{field, shelfType, insertPosition, occurrence?}`
  — moves a field already on the shelf; adds/removes nothing.
- `changeFieldOnGroupsOrColumns` — changes an EXISTING table-shelf field's
  aggregation and/or role in place: `{field, shelfType, occurrence?, function?,
  role?}` — supply at least one of `function` (an aggregation) or `role`
  (`"Dimension"`/`"Measure"`); the omitted one is unchanged. Changing to a Measure
  requires `function` (`Sum`/`Avg`/`Median`/`Min`/`Max`/`Count`/`CountD`/`Stdev`/
  `Stdevp`/`Var`/`Varp`); changing to a Dimension drops the function. **No
  `displayCategory` param** (unlike `changeFieldOnRowsOrColumns`) — table fields are
  always discrete.

Worked examples:

- "Add Region to the table columns": `addFieldToGroupsOrColumns {field: {fieldName: "Region", objectName: "Orders"}, shelfType: "columns"}`
- "Group the table by Category": `addFieldToGroupsOrColumns {field: {fieldName: "Category", objectName: "Orders"}, shelfType: "groups"}`
- "Add total Sales as the first table column": `addFieldToGroupsOrColumns {field: {fieldName: "Sales", objectName: "Orders", function: "Sum"}, shelfType: "columns", insertPosition: 0}`
- "Remove Sales from the table columns": `removeFieldFromGroupsOrColumns {field: {fieldName: "Sales", objectName: "Orders", function: "Sum"}, shelfType: "columns"}`
- "Swap Category for Segment in the table groups": `replaceFieldFromGroupsOrColumns {existingField: {fieldName: "Category", objectName: "Orders"}, newField: {fieldName: "Segment", objectName: "Orders"}, shelfType: "groups"}`
- "Move Sales to the first table column": `reorderFieldsOnGroupsOrColumns {field: {fieldName: "Sales", objectName: "Orders"}, shelfType: "columns", insertPosition: 0}`
- "Average Sales in the table instead of summing it" (Sum of Sales on columns): `changeFieldOnGroupsOrColumns {field: {fieldName: "Sales", objectName: "Orders", function: "Sum"}, shelfType: "columns", function: "Avg"}`
- "Aggregate the Category column as a count of distinct values": `changeFieldOnGroupsOrColumns {field: {fieldName: "Category", objectName: "Orders"}, shelfType: "columns", role: "Measure", function: "CountD"}`

## 9. Table totals and subtotals

TABLE layout only. Two separate summary rows — **do not confuse them**:

- **Grand totals** (`showGrandTotals`, `editGrandTotalsLabel`) — ONE row summarizing
  the whole table. Pick this for "total"/"grand total"/"total row"/"summary row" with
  no mention of groups.
- **Subtotals** (`showSubtotals`, `editSubtotalsLabel`) — one row PER GROUP boundary.
  Pick this for "subtotal"/"group total"/"total for each group"/"totals per category".

Both toggle ROW flags only — there is no `columns` parameter; column subtotals are
never legal (`showSubtotals` rejects `columns: true`), and `showGrandTotals` preserves
an existing column-grand-total flag but does not toggle it.

- `isVisible` (required) shows (`true`) or hides (`false`) the row.
- `position` (optional): `"Start"` (above the table, or above each group) or `"End"`
  (below) — map "top"/"above"/"first" → `"Start"`, "bottom"/"below"/"last"/"at the
  end" → `"End"`. Omit when unsaid — grand totals default to `"End"`; subtotals
  follow the grand totals. **`position` is rewritten on EVERY call** — when only
  hiding a row, pass its current position to keep where it sits.
- `editGrandTotalsLabel`/`editSubtotalsLabel` rename the row (`{label: "text"}`;
  defaults read "Grand Total"/"Subtotal"). **To reset to the default** — "reset it",
  "clear the name", "remove the custom label" — send **EMPTY params `{}`** and leave
  `label` out entirely; **NEVER send `{label: ""}`** (an empty or all-whitespace
  label is rejected). These only rename a row the table already has (shown or
  hidden), so emit the rename ALONE — add a `showGrandTotals`/`showSubtotals` first
  only when the table has no such row yet.
- **Don't reach for these just because "total" appears** — they add/rename a summary
  ROW only, never a column or a per-row figure: a measure to display/aggregate →
  `addFieldToGroupsOrColumns` (or `addFieldToRowsOrColumns`) with `function: "Sum"`;
  a per-row calc (running total, percent of total, rank, moving average) →
  `applyTableCalc` (§13); a totals COLUMN → `addFieldToGroupsOrColumns`; renaming the
  viz → `changeLabel`.

Worked examples:

- "Add a grand total row to this table": `showGrandTotals {isVisible: true}`
- "Show totals at the top of the table": `showGrandTotals {isVisible: true, position: "Start"}`
- "Turn off the total row": `showGrandTotals {isVisible: false}`
- "Rename the grand total row to 'Overall Total'": `editGrandTotalsLabel {label: "Overall Total"}`
- "Reset the grand total label to the default": `editGrandTotalsLabel {}`
- "Show subtotals for each group": `showSubtotals {isVisible: true}`
- "Add group totals at the top of each group": `showSubtotals {isVisible: true, position: "Start"}`
- "Rename the subtotal label to 'Group Total'": `editSubtotalsLabel {label: "Group Total"}`
- "Clear the subtotal label" (a reset — params stay empty, NOT `{label: ""}`): `editSubtotalsLabel {}`

## 10. Layout and fit

- **`changeLayout`** switches the WHOLE visualization between the `Vizql` (chart) and
  `Table` layouts, migrating placed fields onto the target layout's shelves. Unlike
  `changeMarkType` (mark shape only), this changes the layout itself. `targetLayout`
  is a canonical value: `"Vizql"` or `"Table"` — nothing else (a donut/pie is the
  Radial layout and a sankey the Flow layout; this operation cannot switch to either).
  Pick by what the user wants to see: a bar/line/area/scatter graph → `"Vizql"`; a
  text table → `"Table"`.
  - "Turn this into a table" → `{targetLayout: "Table"}`
  - "Make this a bar chart again" → `{targetLayout: "Vizql"}`
- **`changeVisualizationFit`** sets how the viz scales to fit its container: `{fit:
  "Standard"|"Entire"|"RowHeadersWidth"}`. `"Standard"` is default sizing (VizQL and
  Table); `"Entire"` fills the whole view (VizQL only); `"RowHeadersWidth"` fits the
  row-header width (Table only).
  - "Make this chart fit the entire view" → `{fit: "Entire"}`
  - "Fit the table to the row headers" → `{fit: "RowHeadersWidth"}`

Chaining example: "Turn this into a table and add a grand total row" →
`changeLayout {targetLayout: "Table"}`, then `showGrandTotals {isVisible: true}` (fields
must land on the table's shelves before any table-specific operation references them).

## 11. Field label, field-label visibility, axis visibility, number/date format

Four distinct single-field cosmetic operations — do not conflate them with
`changeLabel` (renames the visualization itself, §2) or `editAxisTitle`/
`resetAxisTitle` (sets a custom axis title text, independent of the field's own
label).

- **`editFieldLabel`** renames a field's displayed CAPTION — wherever the field's
  name appears (axis, row/column header, table header): `{field, label,
  occurrence?}`. Pass `label` to rename; an empty string reverts to the default
  name. Works on any layout.
  - "Rename the Sales axis to Revenue" → `{field: {fieldName: "Sales", objectName: "Orders", function: "Sum"}, label: "Revenue"}`
  - "Reset the Sales label" → `{field: {...Sales}, label: ""}`
- **`showFieldLabel`** shows/hides the field labels on the WHOLE SHELF a field sits
  on (affects every field on that shelf, not just the one named): `{field,
  isVisible, occurrence?}`. Only supported on Rows, Columns, Groups, and Levels
  shelves (VizQL/Table/Flow), and only for DISCRETE fields (a discrete measure can be
  toggled; a continuous field errors).
  - "Hide the row field labels" → `{field: {fieldName: "Region", objectName: "Orders"}, isVisible: false}`
- **`showAxis`** shows/hides the axis for one CONTINUOUS field on the Rows or Columns
  shelf: `{field, isVisible, occurrence?}`.
  - "Hide the Sales axis" → `{field: {fieldName: "Sales", objectName: "Orders", function: "Sum"}, isVisible: false}`
- **`setFieldFormat`** changes how a field's VALUES are displayed — not its
  aggregation/role/position (`changeFieldOnRowsOrColumns`) or its axis title
  (`editAxisTitle`). Target is keyed **`targetField`** (`{fieldName, objectName?,
  function?}`) and must already be on a shelf or mark encoding; every copy of the
  field is reformatted together.
  - Number format: `format: {type: "Number"|"Percentage"|"Currency"|"NumberShort"|
    "PercentageShort"|"CurrencyShort" (the "Short" forms abbreviate to K/M/B),
    decimalPlaces? (0 for whole numbers, 2 for cents), displayUnits? ("Auto"|"None"|
    "K"|"M"|"B"|"G"), prefix?, suffix?, negativeValuesFormat? ("Auto"|"Parenthesis"|
    "Minus"), includeThousandSeparator?}`.
  - Date format: `format: {dateTemplate: "MM/dd/yyyy"|"yyyy-MM-dd"|...}`. A
    date/datetime field takes only a `dateTemplate`; a non-date field only a number
    format (mixing errors); a date MEASURE accepts a `dateTemplate` only when
    aggregated with `Min`, `Max`, or `Attr`.
  - "Show Sales as currency" → `{targetField: {fieldName: "Sales", objectName: "Orders", function: "Sum"}, format: {type: "Currency"}}`
  - "Format Discount as a percent with 1 decimal place" → `{targetField: {fieldName: "Discount", objectName: "Orders"}, format: {type: "Percentage", decimalPlaces: 1}}`
  - "Abbreviate Sales to millions" → `{targetField: {...Sales}, format: {type: "NumberShort", displayUnits: "M"}}`
  - "Show Order Date as MM/DD/YYYY" → `{targetField: {fieldName: "Order_Date", objectName: "Orders"}, format: {dateTemplate: "MM/dd/yyyy"}}`

## 12. Measure Values shelf editing

The Measure Values shelf holds a list of measures pivoted by a Measure Names field on
rows or columns so multiple measures share one axis (e.g. "show Sum of Amount and
Count on the same axis"). VizQL only. **Creating** the construct on a brand-new,
empty visualization is covered in `viz-authoring.md` (add the special Measure Names/
Measure Values field via `addFieldToRowsOrColumns` with `{field: {type:
"MeasureNames"|"MeasureValues"}}` — only valid before any field is placed). Once the
construct exists, EDIT it with these operations:

- `addFieldToMeasureValues` — `{field, insertPosition?}` (appends when omitted; only
  measures — dimensions error).
- `reorderFieldsOnMeasureValues` — `{field, insertPosition, occurrence?}` (moves a
  measure already on the shelf).
- `replaceFieldFromMeasureValues` — `{existingField, newField, occurrence?}` — swaps a
  measure already on the shelf for one that is not, keeping the replaced measure's
  slot.
- `removeFieldFromMeasureValues` — `{field, occurrence?}`.
- The same measure can sit on the shelf more than once — `occurrence` (1-based)
  picks which copy.

Worked examples:

- "Show Sum of Sales and Profit on the same axis" (Sum of Sales already on an axis, add Profit): `addFieldToMeasureValues {field: {fieldName: "Profit", objectName: "Orders", function: "Sum"}}`
- "Add Profit at position 0 on Measure Values": `addFieldToMeasureValues {field: {fieldName: "Profit", objectName: "Orders", function: "Sum"}, insertPosition: 0}`
- "Move Sales to position 1 on Measure Values": `reorderFieldsOnMeasureValues {field: {fieldName: "Sales", objectName: "Orders", function: "Sum"}, insertPosition: 1}`
- "Replace Profit with Quantity on Measure Values" (Profit on the shelf, Quantity not): `replaceFieldFromMeasureValues {existingField: {fieldName: "Profit", objectName: "Orders", function: "Sum"}, newField: {fieldName: "Quantity", objectName: "Orders", function: "Sum"}}`
- "Remove the second Sum of Sales from Measure Values": `removeFieldFromMeasureValues {field: {fieldName: "Sales", objectName: "Orders", function: "Sum"}, occurrence: 2}`

## 13. Table calcs — `quickTableCalc` types and `computeUsing`

`applyTableCalc`/`editTableCalc`/`removeTableCalc` target a measure already on a
shelf. `applyTableCalc` adds; `editTableCalc` changes (errors if the field has no
existing calc); `removeTableCalc` clears (errors if none).

`quickTableCalc.type` — canonical values: `RunningSum`, `RunningAvg`, `RunningMin`,
`RunningMax`, `Difference`, `PercentDifference`, `PercentOfTotal`, `Rank`,
`RankModified`, `RankDense`, `RankUnique`, `Percentile`, `MovingSum`, `MovingAverage`,
`MovingMin`, `MovingMax`.

- **Moving types** (`MovingSum`/`MovingAverage`/`MovingMin`/`MovingMax`) accept
  `previousValues`, `nextValues`, `useCurrentValue`. `MovingAverage` defaults to
  `previousValues: 2, nextValues: 0, useCurrentValue: true`; the other moving types
  have no defaults — supply them explicitly.
- **Ranking types** (`Rank`/`RankModified`/`RankDense`/`RankUnique`) accept `order`
  (`"Ascending"`/`"Descending"`). `Rank` defaults to `"Descending"`; the other
  ranking types have no default.

`computeUsing` (optional on `applyTableCalc`/`editTableCalc`) — `{type,
useOrderByForExtraFields?}`. `type` is the calc's addressing direction:
`TableAcross`, `TableDown`, `TableAcrossThenDown`, `TableDownThenAcross`, `PaneAcross`,
`PaneDown`, `PaneAcrossThenDown`, `PaneDownThenAcross`, `Cell`. `useOrderByForExtraFields`
(boolean) orders the extra (non-addressing) fields by whatever sort is applied to
them.

Worked examples:

- "show Sales as a running total": `applyTableCalc {field: {fieldName: "Sales", objectName: "Orders"}, quickTableCalc: {type: "RunningSum"}}`
- "show a 3-period moving average of Sales": `applyTableCalc {field: {...Sales}, quickTableCalc: {type: "MovingAverage", previousValues: 2, nextValues: 0, useCurrentValue: true}}`
- "compute the running total down the table instead": `editTableCalc {field: {...Sales}, quickTableCalc: {type: "RunningSum"}, computeUsing: {type: "TableDown"}}`
- "remove the table calculation from Sales": `removeTableCalc {field: {...Sales}}`

## 14. Logical views and HLV field naming

When a field lives under `semanticLogicalViews[].semanticUnions[].
semanticMappedFields[]`, use the **logical view's** apiName as `objectName` — never
the union's; the logical view is the queryable object (e.g. field "Full_Name20" in
`Manager_Union44` → `objectName: "Manager_oh"`). Hierarchical logical views (HLVs)
additionally expose:

- **Me/My-team filters** via two hardcoded field names: `SemanticManagerUserIdPath`
  (manager hierarchy) / `SemanticRoleUserIdPath` (role hierarchy) — "Me" uses
  `EndsWithIgnoreCase`, "My team" uses `ContainsIgnoreCase`, both against
  `{expression: USERID18()}`. Me example: `{filter: {fields: [{model:
  "Manager_oh.SemanticManagerUserIdPath"}], operator: "EndsWithIgnoreCase", values:
  ["{expression: USERID18()}"]}, bucket: "filter"}` (My team: same with
  `ContainsIgnoreCase`).
- **Level-based display** via `hierarchyLevel` on a field object — e.g.
  `{fieldName: "Full_Name", hierarchyLevel: 1, objectName: "Manager_oh",
  displayCategory: "Discrete", role: "Dimension", type: "Field"}`.
- **Per-level filters** via `ANCESTOR_AT_LEVEL(n, [Object].[Field])` expressions —
  e.g. `{expression: "ANCESTOR_AT_LEVEL(1, [Manager_oh].[Full_Name])", operator:
  "In", values: ["Sarah Chen (CEO)"]}`.

## 15. Persistence handoff — `update_visualization`

`edit_visualization` never saves — every edit (or chain of edits) is a preview only.
**Never call `update_visualization` as an automatic follow-up.** After every
successful `edit_visualization` call — even small or chained edits — your very next
reply MUST end by asking, verbatim: **"Do you want to save the visualization?"**
Call `update_visualization` **only** on confirmation given *after seeing that
preview* (e.g. "yes", "save it") — this applies even when the
original request already said "save it" in the same message as the edit; that
upfront wording does not substitute for a confirmation given after the preview
renders. See `tasks/edit-viz.md` for the full flow.

**`update_visualization` takes only `visualizationId` — never pass a `visualizationMetadata`
body.** The server tracks the latest working definition for that id server-side (whatever
`edit_visualization` last produced for it) and persists that; there's nothing else to
pass. It does not accept or need the workspace/SDM info — those are already fixed on the
existing visualization record. Its response is just `{updateStatus: "SUCCESS"}` — no
metadata, no id.

**Update is in-place only — it does not relocate the viz.** It writes back over the
same visualization (by `visualizationId`), so it updates rather than creates a copy,
and it does NOT move the viz to another workspace or re-point it at a different
semantic model.

**Round-trips back into `edit_visualization` without a re-fetch.** You already have the
`visualizationId` from before calling `update_visualization` — reuse that same id
directly in another `edit_visualization` call (§1) without a `get_visualization`
round trip; the server's working state for that id already reflects the saved edits.
