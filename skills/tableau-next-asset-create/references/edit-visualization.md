# Editing an Existing Visualization — `edit_visualization` / `update_visualization`

Load this when the request mutates a visualization that **already exists** (add/
remove/replace/reorder a shelf field, filter, forecast, sort, mark encoding, mark
type, mark stacking/centering/connector, layout, fit, dual axis, reference line,
table calc, axis title, field label, field/axis/header visibility, header rotation
or size, number/date format, global style, Measure Values, Flow (sankey)
levels/link, or table totals) — not for building a new chart
(`viz-authoring.md`/`tasks/create-viz.md` instead).

## Contents

- Contract (skill-specific)
- Operation reference (synced from upstream): Operation types · Common conventions ·
  Field placement · Change field · Reorder fields · Label · Sort · Mark encoding ·
  Mark type · Mark stacking · Layout · Fit · Dual axis · Reference line · Table
  calculation · Axis title · Field label · Field label visibility · Axis visibility ·
  Number and date format · Global style · Forecast · Filters · Table shelf
  operations · Change field (table shelf) · Measure Values · Flow shelf
  operations · Table totals and subtotals · Field header · Field header sizing ·
  Mark labels · Mark size · Tooltip styling
- Persistence handoff — `update_visualization` (skill-specific)

**New in this sync:** Flow (sankey) changeFieldOnLevels / changeFieldOnLink,
sort on levels, and stylesheet operations on Flow (`LevelFieldLabelBox`);
field-label box selectors renamed to `RowFieldLabelBox` / `ColumnFieldLabelBox`;
`background.color` replaces `backgroundColor`; reference-line dash/width via the
`"ReferenceLine"` style rule; gridline/tick visibility, row banding, legend, and
curved-line styling.

---

## Contract

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
  Each operation's `params` shape is given in the operation reference below.
- Operations run **in order**, each seeing the previous one's result.
- The batch is **all-or-nothing** — one failing operation means none are applied.
- The result **renders inline automatically** — never call `render_visualization`
  afterward.
- The result is **never persisted**. The response's `outputValues.visualizationMetadata`
  holds the edited definition (for `update_visualization`, see Persistence handoff) —
  there is no separate top-level id field in the response. The server keeps
  per-`visualizationId` working state: reuse the **same `visualizationId`** you
  already have (no need to re-read it from the response) to chain straight into
  another `edit_visualization` call, and each call's edits accumulate on top of the
  previous ones for that id.

## Operation types

- addFieldToRowsOrColumns / removeFieldFromRowsOrColumns / replaceFieldFromRowsOrColumns — add, remove, or swap a field on the rows or columns shelf.
- changeFieldOnRowsOrColumns — change an existing shelf field's aggregation, discrete-vs-continuous display, and/or role (Dimension vs Measure); does not add/remove/swap.
- reorderFieldsOnRowsOrColumns — move a field already on the rows or columns shelf to a new position (adds or removes nothing).
- changeLabel — rename the visualization (its name, not the title drawn on it).
- addFilter / editFilter / removeFilter — add, update, or remove a filter.
- addForecast / editForecast / removeForecast — forecast a measure over time; predict future values.
- sortAscending / sortDescending / sortByField / clearSort — sort a shelf field.
- addFieldToEncoding / removeFieldFromEncoding / replaceFieldOnEncoding — assign, remove, or swap a marks encoding slot (Color, Label, Tooltip, Size, Detail, Angle, Range).
- changeMarkType — change the mark shape only (does not add or move fields).
- stackMarks — set how the marks stack: stacked, unstacked, or automatic (VizQL only).
- centerMarks — center the stacked value axis on zero (diverging stacked bar) vs. stacking from the baseline (VizQL only).
- changeMarkConnector — turn a mark's connector (Origami) on or off (VizQL only).
- changeLayout — switch the whole visualization between the Vizql (chart), Table, Packed (packed-bubble), and Flow (sankey) layouts, migrating the placed fields onto the new layout's shelves.
- changeVisualizationFit — set how the visualization scales to fit its container.
- addDualAxis / removeDualAxis / synchronizeAxis — overlay two adjacent continuous fields on one pane with two axes, split them apart, or change how the axes relate.
- addReferenceLine / removeReferenceLine / editReferenceLine — a reference line on an axis field already on a shelf (VizQL only). Its color, value, label, and scope are set here; its dash pattern and width are set with a `"ReferenceLine"` style rule instead.
- applyTableCalc / editTableCalc / removeTableCalc — a quick table calculation on a measure already on a shelf.
- editAxisTitle / resetAxisTitle — set or reset a field's axis title.
- editFieldLabel — rename a field's label (axis, row/column, or table header).
- showFieldLabel — show or hide the field labels on the shelf a field sits on (Rows, Columns, Groups, or Levels).
- showAxis — show or hide the axis for one continuous field on the rows or columns shelf.
- setFieldFormat — change how a field's values are displayed (currency, percent, abbreviated K/M/B, decimal places, or a date pattern).
- addFieldToGroupsOrColumns / removeFieldFromGroupsOrColumns / replaceFieldFromGroupsOrColumns / reorderFieldsOnGroupsOrColumns — add, remove, swap, or move a field on a TABLE visualization's Columns or Groups shelf (table layout only).
- addFieldToLevels / removeFieldFromLevels / replaceFieldOnLevels / reorderFieldsOnLevels — add, remove, swap, or move a field on a FLOW (sankey) visualization's Levels shelf (flow layout only).
- addFieldToLink / removeFieldFromLink / replaceFieldOnLink — set, clear, or swap the single measure on a FLOW (sankey) visualization's Link shelf (flow layout only).
- changeFieldOnLevels / changeFieldOnLink — change an existing FLOW level's aggregation, date function, and/or role, or the Link measure's aggregation (flow layout only); no display category (levels are always discrete, the link is always continuous).
- changeFieldOnGroupsOrColumns — change an existing TABLE shelf field's aggregation and/or role (Dimension vs Measure); does not add/remove/swap, and has no display category (table fields are always discrete).
- addFieldToMeasureValues / reorderFieldsOnMeasureValues / replaceFieldFromMeasureValues / removeFieldFromMeasureValues — manage the Measure Values shelf so multiple measures share one axis (VizQL only).
- showGrandTotals / editGrandTotalsLabel / showSubtotals / editSubtotalsLabel — show/hide/position or rename a TABLE visualization's grand-total or subtotal summary rows (table layout only).
- showHeader / rotateHeader — show or hide a field's header, or rotate its header text (rotate is VizQL only); the field must already be on a shelf.
- resizeHeader — set the pixel size of one field header (drag-resize); the field must already be on a shelf.
- showMarkLabel — show or hide the text labels drawn on the data-point marks (the value shown on each bar, point, or slice). Runs on Vizql and Packed layouts.
- changeMarkSize / resetMarkSize — set the size of the marks (bars, points) drawn in the visualization, or reset that size back to the automatic default. Size is either an absolute pixel value or a percentage of the cell.
- updateTooltipStyle — style the tooltip (the popover shown when hovering a mark): show/hide it, set its background color and transparency, toggle the built-in action links, and set the tooltip's custom text. Runs on Vizql, Table, and Packed layouts.
- addStyleRule — add a new stylesheet rule for a selector. `selector` names the element or group to style; `style` carries CSS-vocabulary properties (color, background, font, text, line) directly. Like CSS, a property that does not apply to the selector is stored rather than rejected, but colors must be a valid format (hex, rgb()/rgba(), or SLDS token) and enums a valid member. If the selector already has a rule, the style is merged onto it. Runs on VizQL, Table, Packed, and Flow layouts only.
- editStyleRule — merge the `style` block onto the selector's existing rule. Same `selector`/`style` shape as addStyleRule. If the selector has no rule yet, the rule is created. Runs on VizQL, Table, Packed, and Flow layouts only.
- clearStyles — remove ALL the style set for a selector, resetting it to the default. To set one property back (Auto, default, normal), use editStyleRule with that value instead. Takes `selector` (any style selector — a styleable element or group); leaves setFieldFormat styling untouched and is a no-op when the selector was never styled. Runs on VizQL, Table, Packed, and Flow layouts only.

## Common conventions

**Operation entry.** Every operation in the batch is `{operationType, params}`. Examples below write the operation name followed by its `params` only — addFilter `{filter: {...}}` means `{operationType: "addFilter", params: {filter: {...}}}`. Never use the operation name as a key (`{addFilter: {...}}` is invalid).

**Field object.** A field is `{fieldName, objectName?, function?}`. Filters instead reference fields as `{model: "Object.Field"}` or `{expression: "..."}` (see Filters). Encoding, dual-axis, reference-line, and rows/columns operations all nest the field under a `"field"` key (or named keys like `primaryField`, `targetField`, `existingField`/`newField`). The special Measure Names / Measure Values field has no name of its own — reference it as `{type: "MeasureNames"|"MeasureValues"}` in place of `{fieldName, ...}` (see Measure Values).

**`function`** sets aggregation or date bucketing — use these canonical `VisualizationFieldFunctionType` values, NEVER display words like "Year"/"Month":

- Aggregations: Sum, Avg, Median, Count, CountD, Min, Max, Stdev, Stdevp, Var, Varp, Attr. (Count/CountD/Min/Max also apply to dimensions; the rest are measures only.)
- Date parts (→ integer): DatePartYear, DatePartQuarter, DatePartMonth, DatePartWeek, DatePartDay, DatePartHour, DatePartMinute.
- Date truncations (→ date): DateTruncYear, DateTruncQuarter, DateTruncMonth, DateTruncWeek, DateTruncDay.
- Fiscal variants exist too (e.g. FiscalDatePartYear, FiscalDateTruncQuarter).
- Omit `function` to keep a measure's default aggregation. A date dimension on a shelf is bucketed by year, so use `DatePartYear` for "broken out by year"; for finer breakouts or date-part filtering use a DATEPART/DATETRUNC expression, not a shelf function.

**`occurrence`** (1-based) picks which copy when the same field sits on a shelf more than once under the same name/object/function. `function` alone distinguishes copies aggregated differently (Sum of Sales vs Avg of Sales).

**`shelfType`** (optional, on the per-field header, axis, and field-label operations: showHeader, rotateHeader, resizeHeader, showAxis, editAxisTitle, resetAxisTitle, editFieldLabel, showFieldLabel) names the shelf to look on ("rows", "columns", "groups", or "levels" — each operation allows only the shelves it supports) when the same field sits on more than one shelf. `occurrence` alone cannot say which shelf, so when a field is ambiguous across shelves, pass `shelfType` to pick the shelf; `occurrence` is then counted within that shelf. Omit both when the field is unique.

**Semantic models** contain data objects (e.g. "Orders") with dimensions and measures. Reference a field for filters as `{model: "Orders.Region"}`; elsewhere nest `{field: {fieldName: "Region", objectName: "Orders"}}`.

**Logical views (incl. hierarchical).** Structure: `semanticLogicalViews[]` → `semanticUnions[]` → `semanticMappedFields[]`. When a field appears under a union, ALWAYS use the logical view's apiName as `objectName`, never the union's (the view is queryable; unions are internal). Example: field "Full_Name20" in Manager_Union44 → `objectName: "Manager_oh"`.

- Hierarchical logical views (HLV) expose hierarchy fields. Me/My-team filters use hardcoded API names — Manager hierarchy `SemanticManagerUserIdPath`, Role hierarchy `SemanticRoleUserIdPath`:
  - Me: `{filter: {fields: [{model: "Manager_oh.SemanticManagerUserIdPath"}], operator: "EndsWithIgnoreCase", values: ["{expression: USERID18()}"]}, bucket: "filter"}`
  - My team: same with `operator: "ContainsIgnoreCase"`.
- Level-based display: add `hierarchyLevel` — `{fieldName: "Full_Name", hierarchyLevel: 1, objectName: "Manager_oh", displayCategory: "Discrete", role: "Dimension", type: "Field"}`.
- Per-level filters use `ANCESTOR_AT_LEVEL`: `{expression: "ANCESTOR_AT_LEVEL(1, [Manager_oh].[Full_Name])", operator: "In", values: ["Sarah Chen (CEO)"], includeNulls: false}`.

## Field placement (rows/columns shelf)

- addFieldToRowsOrColumns takes `{field, shelfType, insertPosition?}` where shelfType is "rows" or "columns" (insertPosition is 0-based, appended when omitted). removeFieldFromRowsOrColumns takes `{field, shelfType, occurrence?}`. replaceFieldFromRowsOrColumns takes `{existingField, newField, shelfType, occurrence?}`.
- To set up the shared-axis construct on an EMPTY visualization, add the special Measure Names or Measure Values field with `{field: {type: "MeasureNames"|"MeasureValues"}, shelfType}`; remove or replace it the same way. Once the construct exists, add measures with addFieldToMeasureValues (see Measure Values).
- A dimension with Count, CountD, Min, Max or Attr becomes a measure. Sum/Avg on a text dimension, and a date function on a non-date field, throw. Replacing a discrete field with a continuous one throws; remove the old field, then add the new one with insertPosition.
- Examples:
  - "Add Category to rows": addFieldToRowsOrColumns `{field: {fieldName: "Category", objectName: "Orders"}, shelfType: "rows"}`
  - "Add total Sales to columns": addFieldToRowsOrColumns `{field: {fieldName: "Sales", objectName: "Orders", function: "Sum"}, shelfType: "columns"}`
  - "Add count distinct of Order_ID to rows": addFieldToRowsOrColumns `{field: {fieldName: "Order_ID", objectName: "Orders", function: "CountD"}, shelfType: "rows"}`
  - "Add Order_Date to columns broken out by year": `{field: {fieldName: "Order_Date", objectName: "Orders", function: "DatePartYear"}, shelfType: "columns"}`
  - "Swap Category for Region on columns": replaceFieldFromRowsOrColumns `{existingField: {fieldName: "Category", objectName: "Orders"}, newField: {fieldName: "Region", objectName: "Orders"}, shelfType: "columns"}`
  - "Add Measure Values to columns" (empty visualization): addFieldToRowsOrColumns `{field: {type: "MeasureValues"}, shelfType: "columns"}`

## Change field (rows/columns shelf)

- changeFieldOnRowsOrColumns changes an EXISTING shelf field's aggregation, display category, and/or role, keeping it in place. Params: `{field, shelfType, occurrence?, function?, displayCategory?, role?}` — supply at least one of `function` (an aggregation), `displayCategory` ("Discrete"/"Continuous"), or `role` ("Dimension"/"Measure"); the omitted ones are unchanged. Changing to a Measure requires `function` (Sum, Avg, Median, Min, Max, Count, CountD, Stdev, Stdevp, Var, Varp); changing to a Dimension drops the function. The special Measure Names / Measure Values field cannot be changed — its aggregation, display category, and role are fixed.
- Use for "average Sales instead of total", "make Sales discrete", "use Sales as a dimension".
- Examples:
  - "average Sales instead of summing it" (Sales on columns): `{field: {fieldName: "Sales", objectName: "Orders", function: "Sum"}, shelfType: "columns", function: "Avg"}`
  - "make Sales on rows discrete": `{field: {fieldName: "Sales", objectName: "Orders"}, shelfType: "rows", displayCategory: "Discrete"}`
  - "turn Category into a measure counting distinct values": `{field: {fieldName: "Category", objectName: "Orders"}, shelfType: "columns", role: "Measure", function: "CountD"}`

## Reorder fields (rows/columns shelf)

- reorderFieldsOnRowsOrColumns moves ONE field already on the rows or columns shelf of a Vizql chart to a new position, reordering the shelf in place — it never adds or removes a field. Params: `{field, shelfType, insertPosition, occurrence?}`. `field` can be a semantic field or the special Measure Names / Measure Values field, referenced as `{type: "MeasureNames"|"MeasureValues"}`.
- `insertPosition` is the 0-based spot the field should land at, counted over the shelf's fields AFTER the moved field is taken out first — so any spot to the right of its old position shifts left by one; 0 is the front, the shelf's last index sends it to the back. `occurrence` (1-based) picks which copy to move when the field repeats.
- Examples (rows currently hold Region, Segment, Category):
  - "put Category first on rows": `{field: {fieldName: "Category", objectName: "Orders"}, shelfType: "rows", insertPosition: 0}`
  - "move Segment to the end of rows": `{field: {fieldName: "Segment", objectName: "Orders"}, shelfType: "rows", insertPosition: 2}`
  - "move Measure Values to the front of rows": `{field: {type: "MeasureValues"}, shelfType: "rows", insertPosition: 0}`

## Label

- changeLabel renames the visualization: `{label: "Sales by Region"}`. (The name, not the title text drawn on the visualization.) To rename a field's caption (axis, row/column, or table header), use editFieldLabel, not changeLabel.

## Sort (rows/columns, columns/groups, or levels shelf)

- Sorts apply to a discrete field ALREADY on a shelf, identified by `targetField` `{fieldName, objectName?, function?}` — the key is always `targetField`, never `field`. Every copy on the shelf stays in sync. Sort works on Vizql visualizations (rows/columns), tables (columns/groups), and FLOW visualizations (levels only). On a Flow, the Link cannot be sorted ("sort the flows by Sales" means sortByField on a level with byField Sales), a measure on Levels cannot be sorted, and `sortType` "Nested" is not supported.
- sortAscending / sortDescending sort by the field's OWN values (A→Z / Z→A). If the field is already sorted by another field, these keep that sort and only change direction; pass `sortType: "Alphabetic"` to force a plain alphabetic sort and drop an existing by-field sort.
- sortByField sorts `targetField` by the AGGREGATED value of `byField` `{fieldName, objectName?, function?}`. `byField.function` is the aggregation (default: measures keep their default, dimensions use "Count"; dimensions allow only Count/CountD/Min/Max). `sortType` "Field" (default) or "Nested" (ordered within each group). `descending` defaults true; set false for smallest first.
- clearSort removes the current sort.
- Examples:
  - "Sort Category A to Z": sortAscending `{targetField: {fieldName: "Category", objectName: "Orders"}}`
  - "Sort Category Z to A": sortDescending `{targetField: {fieldName: "Category", objectName: "Orders"}}`
  - "Sort Region to ascending alphabetic" (Region currently sorted by another field): sortAscending `{targetField: {fieldName: "Region", objectName: "Orders"}, sortType: "Alphabetic"}`
  - "Sort States by total Sales, largest first": sortByField `{targetField: {fieldName: "State", objectName: "Orders"}, byField: {fieldName: "Sales", objectName: "Orders", function: "Sum"}}`
  - "Nest a descending sort on Region by sum of Profit": sortByField `{targetField: {fieldName: "Region", objectName: "Orders"}, byField: {fieldName: "Profit", objectName: "Orders", function: "Sum"}, sortType: "Nested"}`
  - "Sort Category by count of Orders, smallest first": sortByField `{targetField: {fieldName: "Category", objectName: "Orders"}, byField: {fieldName: "Order_Id", objectName: "Orders", function: "Count"}, descending: false}`
  - "Clear the sort on States": clearSort `{targetField: {fieldName: "State", objectName: "Orders"}}`
  - "Order the Category nodes of the sankey by Sales" (Flow, Category is a level): sortByField `{targetField: {fieldName: "Category", objectName: "Orders"}, byField: {fieldName: "Sales", objectName: "Orders", function: "Sum"}}`

## Mark encoding

- `encodingType` selects the slot and its rules:
  - Color — color by a field. One field; adding replaces the existing. Valid on every mark type.
  - Label — annotate marks. Up to 3 fields; oldest dropped when full. Valid on every mark type.
  - Tooltip — extra data on hover. Unlimited; must be a measure. Valid on every mark type.
  - Size — size marks by a measure. One field; adding replaces the existing. Valid on Bar, Circle, Square, Donut only.
  - Detail — add granularity without changing other encodings. Unlimited. Valid on every mark type.
  - Angle — size donut/pie slices by a continuous measure. One field; must be a continuous measure; adding replaces the existing. **Donut marks only** — if the current mark is not Donut, call changeMarkType `{markType: "Donut"}` first in the same batch (do not put the field on Detail, Color, or Size instead).
  - Range — bar range (start/end) encoding. One field; must be continuous. **Bar marks only** — if the current mark is not Bar, call changeMarkType `{markType: "Bar"}` first (do not remap to another slot).
- Mark type → encodings: every mark accepts Color, Label, Tooltip, Detail. Size also needs Bar/Circle/Square/Donut. Angle also needs Donut. Range also needs Bar. An encoding that is illegal for the current mark type errors with "Change the mark type to … first".
- addFieldToEncoding / removeFieldFromEncoding take `{encodingType, field, targetField?, occurrence?}`; replaceFieldOnEncoding takes `{encodingType, existingField, newField, targetField?, occurrence?}`. `targetField` is optional, applies to all marks by default; set it to a field that already has its own mark (e.g. one measure of a multi-measure viz, or one column of a table) to edit only that mark, else the operation errors. When that measure is placed more than once (two identical sub-marks fieldName/objectName/function cannot tell apart), pass `occurrence` (1-based, counted by shelf position) with `targetField` to pick which one; `occurrence` without `targetField` errors.
- For removeFieldFromEncoding / replaceFieldOnEncoding, name the field CURRENTLY ON the slot (the one the viz is colored/labeled/sized by), not an arbitrary shelf field or column — naming a field not on the slot errors. If unsure, read the current encoding first.
- On a Table layout only "Color" and "Tooltip" are valid slots ("Label", "Size", "Detail", "Angle", "Range" error). On a Table, Color and Tooltip take only measures, so a dimension added to either is coerced to a measure (aggregated with Attr). With no `targetField` the encoding applies to every column; set `targetField` to color/tooltip only one column's mark.
- On a Packed (packed-bubble) layout the valid slots are "Color", "Detail", "Size", "Label", and "Tooltip" ("Angle" and "Range" error, since those need Donut/Bar marks). Color and Detail add a hierarchy level; Size sets the bubble magnitude by a measure (coerced to continuous); Label and Tooltip are nonstructural. A Packed viz has one panes mark for the whole visualization, so omit `targetField`.
- On a Flow (sankey) layout an encoding targets one of two marks, so set `markTarget` to "Nodes" or "Links" — required on Flow (omit it and the operation errors), and valid only on Flow (set it on any other layout and the operation errors). Nodes are the stage bars; links are the flows (ribbons) between stages. The valid slots differ by mark: **Nodes** take Color, Detail, Label; **Links** take Color, Detail, Tooltip (Label on links and Tooltip on nodes error, as do Size, Angle, and Range on either). **Never put a measure on a Nodes slot** (Color, Detail, or Label) — a Nodes slot takes a DIMENSION only, and a measure errors. Coloring, labeling, or detailing the nodes (stage bars) by a measure is not supported; tell the user it is not supported rather than moving the measure to the Link or a Links slot — the Link sizes the flows, so putting it there changes flow sizing, which is not what was asked. Links have no Label slot, so "label the links with <field>" means show that field on the links Tooltip (`markTarget` "Links") instead — never a Label. Use `markTarget` to pick the mark — `targetField` does not apply on Flow and errors.
- The special "Measure Names" field colors measures apart and has no name — reference it as `{field: {type: "MeasureNames"}}`, Color slot only (a dual axis adds it there).
- Examples:
  - "color the visualization by Region": addFieldToEncoding `{encodingType: "Color", field: {fieldName: "Region", objectName: "Orders"}}`
  - "stop coloring by Region": removeFieldFromEncoding `{encodingType: "Color", field: {fieldName: "Region", objectName: "Orders"}}`
  - "stop coloring the two measures apart" (remove the measure-names color a dual axis added): removeFieldFromEncoding `{encodingType: "Color", field: {type: "MeasureNames"}}`
  - "color by Region instead of by measure": replaceFieldOnEncoding `{encodingType: "Color", existingField: {type: "MeasureNames"}, newField: {fieldName: "Region", objectName: "Orders"}}`
  - "label the marks by Product": addFieldToEncoding `{encodingType: "Label", field: {fieldName: "Product", objectName: "Orders"}}`
  - "add Revenue to the tooltip": addFieldToEncoding `{encodingType: "Tooltip", field: {fieldName: "Revenue", objectName: "Orders"}}`
  - "size the bubbles by Sales": addFieldToEncoding `{encodingType: "Size", field: {fieldName: "Sales", objectName: "Orders"}}`
  - "break the marks down by Segment": addFieldToEncoding `{encodingType: "Detail", field: {fieldName: "Segment", objectName: "Orders"}}`
  - "color the table by Region" (Table layout): addFieldToEncoding `{encodingType: "Color", field: {fieldName: "Region", objectName: "Orders"}}`
  - "size the bubbles by Sales" (Packed layout): addFieldToEncoding `{encodingType: "Size", field: {fieldName: "Sales", objectName: "Orders"}}`
  - "break the bubbles down by Segment" (Packed layout): addFieldToEncoding `{encodingType: "Detail", field: {fieldName: "Segment", objectName: "Orders"}}`
  - "color the flow nodes by Segment" (Flow layout): addFieldToEncoding `{encodingType: "Color", field: {fieldName: "Segment", objectName: "Orders"}, markTarget: "Nodes"}`
  - "add Sales to the link tooltip" / "show Sales on the flows" (Flow layout): addFieldToEncoding `{encodingType: "Tooltip", field: {fieldName: "Sales", objectName: "Orders", function: "Sum"}, markTarget: "Links"}`
  - "add a tooltip to the nodes showing Sales" (Flow layout — Nodes have no Tooltip slot, so put it on the links): addFieldToEncoding `{encodingType: "Tooltip", field: {fieldName: "Sales", objectName: "Orders", function: "Sum"}, markTarget: "Links"}`
  - "label the links with Profit" (Flow layout — Links have no Label slot, so show it in the links tooltip): addFieldToEncoding `{encodingType: "Tooltip", field: {fieldName: "Profit", objectName: "Orders", function: "Sum"}, markTarget: "Links"}`
  - "stop coloring the flow nodes" (Flow layout, nodes colored by Segment): removeFieldFromEncoding `{encodingType: "Color", field: {fieldName: "Segment", objectName: "Orders"}, markTarget: "Nodes"}`
  - "add Region to color, Profit to angle" (not yet a donut): changeMarkType `{markType: "Donut"}`, then addFieldToEncoding `{encodingType: "Color", field: {fieldName: "Region", objectName: "Orders"}}`, then addFieldToEncoding `{encodingType: "Angle", field: {fieldName: "Profit", objectName: "Orders"}}`
  - "color the second Sales measure by Region" (Sales placed twice): addFieldToEncoding `{encodingType: "Color", field: {fieldName: "Region", objectName: "Orders"}, targetField: {fieldName: "Sales", objectName: "Orders", function: "Sum"}, occurrence: 2}`

## Mark type

- changeMarkType sets the mark shape for the whole visualization, or one measure's mark. It changes shape only — it does not move fields, so it won't by itself convert a chart to one needing a different layout.
- `markType`: "Bar", "Line", "Circle", "Square", "Donut", "Text", or "automatic" (lets the viz pick). `targetField` (optional) retypes only one field's mark; that field must already be a mark. When that measure is placed more than once (two identical sub-marks), pass `occurrence` (1-based, counted by shelf position) with `targetField` to pick which one; `occurrence` without `targetField` errors.
- On a Table layout only "Text" and "Bar" are valid; any other type (including "automatic") errors. On a Packed (packed-bubble) layout only "Square" (treemap) and "Circle" (bubble) are valid and "automatic" resolves to "Square"; any other type errors. A Packed viz has one panes mark for the whole visualization, so omit `targetField` (passing one errors). Vizql visualizations accept the full set.
- Examples: "draw the marks as lines" → `{markType: "Line"}`; "let the visualization choose" → `{markType: "automatic"}`; "show the table as text" (Table layout) → `{markType: "Text"}`; "show the bubbles as a treemap" (Packed layout) → `{markType: "Square"}`; "make the bubbles circles" (Packed layout) → `{markType: "Circle"}`; "make the second Sales a line" (Sales placed twice) → `{markType: "Line", targetField: {fieldName: "Sales", objectName: "Orders", function: "Sum"}, occurrence: 2}`.

## Mark stacking (VizQL visualizations only)

- These operations control how the marks stack. Each takes an optional `field`: omit it to affect all marks; pass it to target one field's mark (by fieldName, plus objectName/function when needed). `field` is never a field key. All apply to VizQL charts only.
- stackMarks sets how marks stack via two flags: `{isStacked, isAutomatic, field?, occurrence?}`. `isStacked: true` stacks the marks, `false` does not; `isAutomatic: true` lets the visualization decide the stacking. Both flags are required and mirror the mark's stack metadata: to stack pass `{isStacked: true, isAutomatic: false}`, to unstack pass `{isStacked: false, isAutomatic: false}`, and to let the visualization decide pass `{isStacked: true, isAutomatic: true}`.
- centerMarks sets whether the stacked value axis is centered on zero (a diverging stacked bar) vs. stacking from the baseline: `{centered, field?, occurrence?}`. This is distinct from stackMarks — use stackMarks to choose the stacking mode, and centerMarks to center an already-stacked axis.
- changeMarkConnector sets the mark's connector (the Origami line joining marks, e.g. across gaps in a line): `{connectorType?, field?, occurrence?}`. Pass `connectorType: "Origami"` to draw the connector, or omit `connectorType` to remove it. Use this when the query asks to show or hide the connector/connecting line between marks.
- When the same measure is placed more than once (two identical sub-marks that fieldName/objectName/function cannot tell apart), pass `occurrence` (1-based, counted by placement order) to pick which one; omit it when the field is unique.
- Examples:
  - "stack the bars": stackMarks `{isStacked: true, isAutomatic: false}`
  - "unstack the bars": stackMarks `{isStacked: false, isAutomatic: false}`
  - "let the chart decide whether to stack": stackMarks `{isStacked: true, isAutomatic: true}`
  - "center the stacked axis" / "make it a diverging stacked bar": centerMarks `{centered: true}`
  - "connect the marks" / "show the connector": changeMarkConnector `{connectorType: "Origami"}`
  - "hide the connector line": changeMarkConnector `{}`
  - "stack the second Sales": stackMarks `{isStacked: true, isAutomatic: false, field: {fieldName: "Sales", objectName: "Orders", function: "Sum"}, occurrence: 2}`

## Layout

- changeLayout switches the whole visualization between the Vizql, Table, Packed, and Flow layouts, migrating the placed fields onto the target layout's shelves. Unlike changeMarkType (which only changes the mark shape), it changes the layout itself. `targetLayout` is a canonical `VisualizationLayout` value: "Vizql", "Table", "Packed", or "Flow".
- Pick the layout by what the user wants to see: a bar/line/area/scatter graph → "Vizql"; a text table → "Table"; a packed-bubble chart → "Packed"; a sankey/flow diagram → "Flow". A donut or pie is still Vizql — set the mark type to "Donut" with changeMarkType (Angle encoding is Donut-only). This operation cannot switch to Map or Radial, so it accepts only "Vizql", "Table", "Packed", and "Flow".
- Packed and Flow convert directly to each other. Going Packed→Flow, the hierarchy dimensions become the flow levels and the first measure becomes the link; going Flow→Packed, the link measure becomes the Size bubble magnitude and the levels become Detail hierarchy.
- Examples: "turn this into a table" → `{targetLayout: "Table"}`; "make this a bar chart again" → `{targetLayout: "Vizql"}`; "show this as packed bubbles" → `{targetLayout: "Packed"}`; "turn this into a sankey" → `{targetLayout: "Flow"}`; "switch this flow diagram back to a bar chart" → `{targetLayout: "Vizql"}`; "turn these packed bubbles into a sankey" → `{targetLayout: "Flow"}`; "show this sankey as packed bubbles" → `{targetLayout: "Packed"}`.
- Chaining: run changeLayout BEFORE any layout-specific operation, so the fields have landed on the target layout's shelves first. e.g. "turn this into a table and add a grand total row" → changeLayout `{targetLayout: "Table"}`, then showGrandTotals `{isVisible: true}`.

## Fit (visualization sizing)

- changeVisualizationFit sets how the visualization scales to fit its container: `{fit: "Standard"|"Entire"|"RowHeadersWidth"}`. "Standard" is default sizing (VizQL and Table); "Entire" fills the whole view (VizQL only); "RowHeadersWidth" fits the row-header width (Table only).
- Examples: "make this chart fit the entire view" → `{fit: "Entire"}`; "fit the table to the row headers" → `{fit: "RowHeadersWidth"}`; "use standard fit" → `{fit: "Standard"}`.

## Dual axis

- A dual axis overlays two continuous fields (measures or dates, any combination) that are ALREADY adjacent on the SAME shelf. addDualAxis does not add fields — add the second with addFieldToRowsOrColumns first.
- `primaryField` is the LEFT field, `secondaryField` the RIGHT (their shelf order matters; the secondary moves onto the shared axis). Each is `{fieldName, objectName?, function?}`. Add `primaryOccurrence`/`secondaryOccurrence` (1-based) when name+object+function still repeat.
- `synchronization`: "None" (default; independent scales), "ZeroPosition" (zero lines align), or "FullRange" (shared range). Optional on addDualAxis; REQUIRED on synchronizeAxis. "ZeroPosition" is not allowed when both fields are dates of the same kind — use "FullRange" or "None".
- removeDualAxis and synchronizeAxis name the same (primary, secondary) pair.
- Examples:
  - "make Sales and Profit a dual axis" (both on columns, Sales left): addDualAxis `{primaryField: {fieldName: "Sales", objectName: "Orders"}, secondaryField: {fieldName: "Profit", objectName: "Orders"}}`
  - "overlay Profit on Sales with aligned zero lines": add `synchronization: "ZeroPosition"` to the above.
  - "make the Sales/Profit dual axis share one range": synchronizeAxis `{primaryField: {...Sales}, secondaryField: {...Profit}, synchronization: "FullRange"}`

## Reference line (VizQL visualizations only)

- A reference line marks a value on an axis `field` (`{fieldName, objectName?, function?}`) ALREADY on a shelf; these operations never add the field. When the same field is on the shelf under different aggregations, set `field.function` to pick the pill.
- Two different functions — do not confuse:
  - `field.function` selects the AXIS field (its shelf aggregation). "Sum of Sales" names THIS field.
  - `line.function` is the LINE's own computation (average line, max line). Set it only when the request names that statistic. So "add a reference line to Sum of Sales" attaches a default (average) line to the Sum-of-Sales pill — set `field.function: "Sum"` and OMIT `line`; it does NOT mean a sum line.
- Line kinds (`line`):
  - Computation line: `{valueType: "Computation", function}` where function is "Sum"/"Avg"/"Min"/"Max" (measure) or "Max"/"Min"/"Today"/"Now" (date). Omitting `line` on addReferenceLine defaults to an average line (measure) / latest-date line (date). To compute from a DIFFERENT field, set `line.computationField` `{fieldName, objectName?, function?}` (need not be on a shelf).
  - Constant line: `{valueType: "Value", value}` — a number (measure axis) or ISO date string (date axis).
- Optional label goes INSIDE `line`: `labelType` is "None"/"Value"/"Computation"/"Custom" (with `customLabel`). `scope` is "Table" (default)/"Pane"/"Cell". `lineColor` is a top-level hex (default gray), accepted by both add and edit.
- Selecting among multiple lines on a field: describe by `computationFunction`, `value`, `labelText`, `scope`, or `lineValueType` (use these when the request describes the line itself — "the average line" → `computationFunction: "Avg"`, "the line labeled Goal" → `labelText: "Goal"`); or pick by position with `lineOccurrence` (1-based). `lineOccurrence` picks WHICH LINE; `occurrence` picks WHICH SHELF PILL (only when the field repeats on the shelf). When no pill is named, `lineOccurrence` counts across all matching pills.
- removeReferenceLine removes every matching line (all lines on the field unless narrowed by `scope`). editReferenceLine changes exactly ONE line (errors if ambiguous) and changes only what you pass: set `scope`/`lineColor`/`labelType`+`customLabel` to change just those (keeps the value); set `line` to change the value/function (keeps the label unless you also pass label fields). A label passed at the top level wins over one nested inside `line`.
- Color versus dash and width — the same for "reference line" and "reference lines":
  - Color, value, label, and scope belong to each line: use editReferenceLine (`lineColor` for color). Never send a color in a `"ReferenceLine"` style rule; that rule is not tied to one line, so it would recolor every reference line.
  - Dash pattern (dotted, dashed, solid) and width (thicker, 2px) are NOT editReferenceLine settings; they are a global style rule on the `"ReferenceLine"` selector that styles every reference line (see Global style). editReferenceLine has no dash or width setting.
  - A request for both ("make the reference line red and dotted") is two operations: editReferenceLine with `lineColor`, plus the `"ReferenceLine"` style rule with `line.style`.
- Examples:
  - "add an average line to Sales": addReferenceLine `{field: {fieldName: "Sales", objectName: "Orders"}}`
  - "add a target line at 5000 on Sales": `{field: {fieldName: "Sales", objectName: "Orders"}, line: {valueType: "Value", value: 5000}}`
  - "add a line at 100 on avg of Sales labeled 'target' in green": `{field: {fieldName: "Sales", objectName: "Orders", function: "Avg"}, line: {valueType: "Value", value: 100, labelType: "Custom", customLabel: "target"}, lineColor: "#00FF00"}`
  - "add a sum line for Sales per pane": `{field: {fieldName: "Sales", objectName: "Orders"}, line: {valueType: "Computation", function: "Sum"}, scope: "Pane"}`
  - "add an average line on Sales computed using sum of Discount": `{field: {...Sales}, line: {valueType: "Computation", function: "Avg", computationField: {fieldName: "Discount", objectName: "Orders", function: "Sum"}}}`
  - "add a max line on the 1st Sum of Sales" (repeated pill → occurrence): `{field: {fieldName: "Sales", objectName: "Orders", function: "Sum"}, occurrence: 1, line: {valueType: "Computation", function: "Max"}}`
  - "make the Sales reference line red" (color only, omit `line`): editReferenceLine `{field: {...Sales}, lineColor: "#FF0000"}`
  - "make reference lines red" or "make the reference lines red" (one reference line, on Sales): editReferenceLine `{field: {...Sales}, lineColor: "#FF0000"}` — not a style rule, even when a `"ReferenceLine"` rule exists. Plural "lines" does not make color a style rule.
  - "make all the reference lines red" (two lines on Sales): two editReferenceLine operations in one call, `{field: {...Sales}, lineOccurrence: 1, lineColor: "#FF0000"}` and `{field: {...Sales}, lineOccurrence: 2, lineColor: "#FF0000"}`
  - "make the reference line dotted" or "make the reference lines dotted": addStyleRule `{selector: "ReferenceLine", style: {line: {style: "Dotted"}}}` (editStyleRule if a `"ReferenceLine"` rule exists) — not editReferenceLine
  - "remove the 2nd reference line on avg of Sales": removeReferenceLine `{field: {fieldName: "Sales", objectName: "Orders", function: "Avg"}, lineOccurrence: 2}`
  - "update the 2nd reference line on the 1st Sum of Sales to a max line" (BOTH selectors): editReferenceLine `{field: {fieldName: "Sales", objectName: "Orders", function: "Sum"}, occurrence: 1, lineOccurrence: 2, line: {valueType: "Computation", function: "Max"}}`

## Table calculation (on a measure already on a shelf)

- Works on both chart and table visualizations. Target a measure by `field` (`{fieldName, objectName?, function?}`, plus `occurrence` when it still repeats).
- `quickTableCalc.type`: RunningSum, RunningAvg, RunningMin, RunningMax, Difference, PercentDifference, PercentOfTotal, Rank, RankModified, RankDense, RankUnique, Percentile, MovingSum, MovingAverage, MovingMin, MovingMax.
  - Moving types accept `previousValues`, `nextValues`, `useCurrentValue`. MovingAverage defaults to 2/0/true; other moving types have no defaults.
  - Ranking types accept `order` ("Ascending"/"Descending"); Rank defaults "Descending".
- `computeUsing` (optional): `{type, useOrderByForExtraFields?}`. `type` is the direction — TableAcross, TableDown, TableAcrossThenDown, TableDownThenAcross, PaneAcross, PaneDown, PaneAcrossThenDown, PaneDownThenAcross, Cell. `useOrderByForExtraFields` (boolean) orders the extra (non-addressing) fields by the sort applied to them. applyTableCalc and editTableCalc take the same `computeUsing` shape.
- applyTableCalc adds; editTableCalc changes (errors if none); removeTableCalc clears (errors if none).
- Examples:
  - "show Sales as a running total": applyTableCalc `{field: {fieldName: "Sales", objectName: "Orders"}, quickTableCalc: {type: "RunningSum"}}`
  - "show a 3-period moving average of Sales": `{field: {...Sales}, quickTableCalc: {type: "MovingAverage", previousValues: 2, nextValues: 0, useCurrentValue: true}}`
  - "compute the running total down the table instead": editTableCalc `{field: {...Sales}, quickTableCalc: {type: "RunningSum"}, computeUsing: {type: "TableDown"}}`
  - "remove the table calculation from Sales": removeTableCalc `{field: {...Sales}}`

## Axis title

- editAxisTitle sets a custom axis label: `{field, axisTitle, occurrence?, shelfType?}`. resetAxisTitle reverts to default: `{field, occurrence?, shelfType?}`. Identify the axis by `field` (`fieldName`, `objectName`, optional `function`), not by its position (X/Y); `shelfType` is "rows" or "columns".
- The axis title is independent of the field's own label: editAxisTitle sets only that axis's title text, while editFieldLabel renames the field's caption wherever it appears (axis, headers). Use editAxisTitle when the request is about the axis title; use editFieldLabel when it renames the field itself.
- Examples: "Rename the Y axis to Revenue" → editAxisTitle `{field: {fieldName: "Sales", objectName: "Orders"}, axisTitle: "Revenue"}`; "Reset the Revenue axis title" → resetAxisTitle `{field: {fieldName: "Revenue", objectName: "Orders"}}`.

## Field label (rename)

- editFieldLabel renames a field's label — the caption shown wherever the field's name appears (axis, row/column header, table header): `{field, label, occurrence?, shelfType?}`. Pass `label` to rename; an empty string reverts to the default name. `shelfType` is "rows", "columns", "groups", or "levels". Works on any layout. Distinct from changeLabel (renames the visualization) and editAxisTitle (sets an axis title independent of the field's label).
- Examples: "Rename the Sales axis to Revenue" → `{field: {fieldName: "Sales", objectName: "Orders", function: "Sum"}, label: "Revenue"}`; "Reset the Sales label" → `{field: {...Sales}, label: ""}`.

## Field label visibility

- showFieldLabel shows or hides the field labels on the shelf a field sits on (per-shelf: affects every field on that shelf): `{field, isVisible, occurrence?, shelfType?}`. `shelfType` is "rows", "columns", "groups", or "levels". Only supported on the Rows, Columns, Groups, and Levels shelves (Vizql, Table, Flow), and only for discrete fields (depends on display category, so a discrete measure can be toggled but a continuous field errors).
- Example: "Hide the row field labels" → `{field: {fieldName: "Region", objectName: "Orders"}, isVisible: false}`.

## Axis visibility

- showAxis shows or hides the axis for one continuous field on the Rows or Columns shelf: `{field, isVisible, occurrence?, shelfType?}`. `shelfType` is "rows" or "columns".
- Example: "hide the Sales axis" → `{field: {fieldName: "Sales", objectName: "Orders", function: "Sum"}, isVisible: false}`.

## Number and date format

- setFieldFormat changes how a field's VALUES are displayed — not its aggregation/role/position (use changeFieldOnRowsOrColumns) or its axis name (editAxisTitle). `targetField` (`{fieldName, objectName?, function?}`) must already be on a shelf or a mark encoding; every copy of the field is reformatted together.
- Number format: `format: {type: "Number"|"Percentage"|"Currency"|"NumberShort"|"PercentageShort"|"CurrencyShort" (the "Short" forms abbreviate to K/M/B), decimalPlaces? (0 for whole numbers, 2 for cents), displayUnits? ("Auto"|"None"|"K"|"M"|"B"|"G"), prefix?, suffix?, negativeValuesFormat? ("Auto"|"Parenthesis"|"Minus"), includeThousandSeparator?}`.
- Date format: `format: {dateTemplate: "MM/dd/yyyy"|"yyyy-MM-dd"|...}`. A date/datetime field takes only a `dateTemplate`; a non-date field only a number format (mixing errors); a date measure accepts a `dateTemplate` only when aggregated with Min, Max, or Attr.
- Examples:
  - "Show Sales as currency": `{targetField: {fieldName: "Sales", objectName: "Orders", function: "Sum"}, format: {type: "Currency"}}`
  - "Format Discount as a percent with 1 decimal place": `{targetField: {fieldName: "Discount", objectName: "Orders"}, format: {type: "Percentage", decimalPlaces: 1}}`
  - "Abbreviate Sales to millions": `{targetField: {...Sales}, format: {type: "NumberShort", displayUnits: "M"}}`
  - "Show Order Date as MM/DD/YYYY": `{targetField: {fieldName: "Order_Date", objectName: "Orders"}, format: {dateTemplate: "MM/dd/yyyy"}}`

## Global style

- These operations style the visualization's chrome — its text, lines, background, and the look of every mark — not one field's data. Send only the properties the user asked to change, even when the rule is new — omitted properties keep their current look, so never send a full block. A property set to the value the element shows by default is removed from the rule rather than stored, so "set it back to the default" is the same request with the default value. A color may be a hex string, an `rgb()`/`rgba()` value, or an SLDS color token.
- A grand total, subtotal, or header font, color, or alignment is NEVER `"Global"`, `"Headings"`, or `"BodyText"`. `"Global"` changes every text element and stores only the properties sent, so `{selector: "Global", style: {font: {size: 20}}}` does not format the grand total label. "Grand total label" / "total row name" → `"GrandTotalLabel"`. "Grand total numbers" / "total values" → `"GrandTotalValue"`. The same split for subtotals. Say both only when the user names both the label and the numbers. Each of the four is its own rule: a `"GrandTotalLabel"` rule does not give `"GrandTotalValue"` one, so the first change to the numbers is addStyleRule even after the label was styled.
- addStyleRule and editStyleRule both take a `selector` and a `style` block. `selector` names the element or group; `style` carries the properties. Like CSS, a property that does not apply to the selector is stored rather than rejected, so prefer the property groups below. Choose by looking in `visualSpecification.stylesheet.rules` for a rule whose `selector` is exactly the selector you are sending: if there is none, use addStyleRule; if there is one, use editStyleRule (it merges onto that rule — top-level keys and the `font`/`text`/`line`/`border` sub-blocks). Both write the same way, so a wrong pick still works, but send the one that matches. Rules for other selectors never count, even closely related ones: a `"Global"` rule ("all the text") is NOT a `"Headings"` or `"BodyText"` rule, and a group rule is never a rule for one of its elements, so the first change to any of them is still addStyleRule.
  - Only `visualSpecification.stylesheet.rules` counts. Every visualization also carries built-in settings under `visualSpecification.style` — such as `style.fonts.fieldLabels`, `style.fonts.headers`, `style.fieldLabels` with a default size, color, or background, or `style.referenceLines` — and these are NEVER rules. A field label size of 13 in `style.fonts` does not mean `"FieldLabel"` has a rule, so "set the field label text size to 20" there is still addStyleRule.
  - Check the rules again for EVERY style request, even a follow-up about the same element. When `visualSpecification.stylesheet` is missing or its `rules` list is empty, no selector has a rule, so every style change is addStyleRule. Once an element has been styled, every later change to it is editStyleRule. The user's wording never decides it: "make", "change", "set", "update", and "now make" can all mean either one.
  - Inside one batch, an addStyleRule creates the rule for later operations, so a second change to the same selector in that batch is editStyleRule.
  - `selector` — a `StylableElementType` element or a `StyleElementGroup` group, one of the values below. Text: typography groups `"Global"`, `"Headings"`, `"BodyText"`; labels `"FieldLabel"`, `"RowFieldLabelBox"`, `"ColumnFieldLabelBox"`, `"LevelFieldLabelBox"` (Flow only), `"HeaderLabel"`, `"AxisTickLabel"`, `"MarkLabel"`, `"LegendLabel"`, `"GrandTotalLabel"`, `"SubtotalLabel"`; titles `"AxisTitle"`, `"LegendTitle"`; values `"GrandTotalValue"`, `"SubtotalValue"`. Lines: individual elements `"AxisLine"` (the axis's own line), `"AxisTick"` (the short tick-mark strokes, NOT their text), `"GridLine"` (lines across the plot at each tick; by default only for visible axes, but an explicit `GridLine` visibility rule draws them on every axis), `"ZeroLine"` (the line at the axis's zero value), `"SeparatorLine"` (the lines between header groups), `"ReferenceLine"` (only the dash pattern and width of every reference line; its color is editReferenceLine `lineColor`, and its label is not styled here); or the group `"VizLines"` (all line elements at once). Background/fill: `"Scene"` (whole background, the only background on a Packed visualization) and `"Header"` (the row and column header cells; `"Cell"` on a Table layout), and `"Row"` (Table only: alternating row stripes, see the banding bullet below). Marks: `"Mark"` (every data mark on a Vizql chart; see the marks bullet below).
  - Never send these selectors; they are not styled with these operations: `"HeaderBackground"`, `"FieldLabelBackground"`, `"RowFieldLabel"`, `"ColumnFieldLabel"`, `"LevelFieldLabel"`, `"SliceFieldLabel"`, and `"RingFieldLabel"` (old names; use `"Header"` and the field label selectors below), `"PackedContainer"`, `"Pane"`, `"TrendLine"`, `"ReferenceLineLabel"`. When the user asks to style one of these, say it cannot be styled instead of sending a rule for a different selector.
  - Picking the right line or tick selector: `"AxisTick"` is the tick-mark stroke, `"AxisTickLabel"` is the value text (the numbers) — route "tick marks" to `AxisTick`, and "tick labels", "axis values", or "the numbers on the axis" to `AxisTickLabel`. "Axis labels" means the axis titles (the field name beside each axis, called Axis Labels in the authoring UI), so route both "axis labels" and "axis titles" to `"AxisTitle"`, never `"AxisTickLabel"`. Restyling them is still a style rule; only renaming the text uses editAxisTitle. When the user names a single line element ("the axis line", "the gridlines"), use that element (`"AxisLine"`, `"GridLine"`), NOT the `"VizLines"` group; use `"VizLines"` only for "all the lines". A more specific element rule overrides the group, so prefer the element unless the user clearly means all lines.
  - `style` — `color` (text or line color), a `background` block (`background.color` is the fill color), a `font` block (`font.family`, `font.size`, `font.weight` `"Normal"`|`"Bold"`, `font.italic` and `font.underline` booleans), a `text` block (`text.wrap` boolean, `text.halign` `"Left"`|`"Center"`|`"Right"`|`"Auto"`, `text.valign` `"Top"`|`"Middle"`|`"Bottom"`, `text.textDirection` `"Horizontal"`|`"VerticalUp"`|`"VerticalDown"`|`"Auto"`, `text.rotation` degrees), a `line` block (`line.width`, `line.style` dash pattern `"Solid"`|`"Dashed"`|`"Dotted"`|`"WideGapDash"`|`"ShortDash"`), a `banding` block (`banding.color`, only on `"Row"`), and `visibility` `"Visible"`|`"Hidden"` (only on the line selectors below). Do not send `opacity` on text, header, background, or line selectors: none of them has an opacity setting, so there is no style rule for making text, totals, or headers transparent. Only `"GridLine"` and `"Mark"` take `opacity`.
- Lines (Vizql charts) — send only what was asked, on the selector for that line:
  - `"GridLine"` takes `color`, `line.width`, `line.style`, `opacity` (0 to 100, where 100 is solid), and `visibility`. "Show the gridlines" → `visibility: "Visible"`; "hide the gridlines" → `visibility: "Hidden"`.
  - `"AxisTick"` takes `color`, `line.width`, and `visibility`. Tick marks are hidden by default, so "show the axis ticks" → `visibility: "Visible"`, and "hide the axis ticks" → `visibility: "Hidden"`.
  - `"ReferenceLine"` takes only `line.width` and `line.style`, and styles every reference line at once. A dash pattern or width for a reference line ("make the reference line dotted", "thicker reference lines") is ALWAYS this style rule, even when there is only one reference line: editReferenceLine has no dash or width setting. NEVER send `color` on it, even when a `"ReferenceLine"` rule already exists: this rule is not tied to one line, so a color here would recolor every reference line. A reference line's color ("make the reference line red", "make the reference lines red") is always editReferenceLine `lineColor`, which is also how to change one line's value or type. Every reference line comes with its own built-in style in `visualSpecification.style.referenceLines`; that is not a rule, so the first dash or width change is addStyleRule unless `stylesheet.rules` already has a `"ReferenceLine"` rule.
  - `"AxisLine"`, `"ZeroLine"`, and `"SeparatorLine"` take `color` and `line.width`.
- Row banding (Table only): alternating row stripes ("shade alternate rows", "banded rows", "zebra stripes") are `"Row"` with `banding: {color}`, which fills every other row. `"Row"` takes nothing else and does nothing on other layouts.
- Legends: `"LegendTitle"` is the field name over a legend and `"LegendLabel"` is each item's text. Both take `color` and the `font` block, and nothing else.
- Header text versus one field's header: use `selector: "HeaderLabel"` when the query is about all the row and column headers ("make the header text vertical", "bold the headers"). When the query names one field's header ("rotate the Category header"), use rotateHeader instead — it changes only that field.
- clearStyles removes EVERY property a prior addStyleRule or editStyleRule set on the selector, resetting it to the visualization's default. Use it only when the user asks to reset all of that element's styling ("reset the field label formatting", "clear the header styles"). When the user sets ONE property back ("set the alignment back to auto", "make the text direction auto again", "back to the default size"), use editStyleRule with that property's Auto or default value — the value is then removed from the rule and the other properties stay. clearStyles there would also erase the color, size, and everything else on the rule. It takes `selector` (any style selector — a styleable element or group, such as the selectors listed above). Per-field formatting (setFieldFormat) is left untouched, and clearing a selector that was never styled is a no-op. Runs on VizQL, Table, Packed, and Flow layouts only, like addStyleRule and editStyleRule.
- Field labels (the shelf captions over the rows and columns, not the header values) are styled with these same operations, split across three selectors the way the authoring tools save them. They are three separate rules: styling one never creates the others, so a field label background does not give "FieldLabel" a rule.
  - Text — color, font (`family`, `size`, `weight`, `italic`, `underline`), `text.halign`, and `text.textDirection` — goes on `"FieldLabel"`.
  - The background goes on BOTH `"RowFieldLabelBox"` and `"ColumnFieldLabelBox"`: send one operation for each, in the same batch, with the same `background.color`. On a Flow it goes on `"LevelFieldLabelBox"` instead (see the Flow bullet below). Never put `background` on `"FieldLabel"`.
  - Field labels draw bold by default. To make them not bold, set `font: {weight: "Normal"}` on `"FieldLabel"` (addStyleRule when it has no rule yet, editStyleRule when its color, size, or other text was already styled); clearStyles would bring the default bold back, not remove it.
  - Field label text direction ("change the field label text direction to vertical up", "make the field labels horizontal") is `text.textDirection` on `"FieldLabel"`, never rotateHeader (that turns a field's header values, not its field label). It follows the same add-or-edit rule as the other text properties, including setting it back to Auto.
  - Field labels have no wrap, vertical alignment, `text.rotation` degrees, or line; do not send those.
  - Choose addStyleRule or editStyleRule separately for each selector, by whether that exact selector has a rule in `visualSpecification.stylesheet.rules`. A Table's built-in `visualSpecification.style.fieldLabels` (such as its default gray background) is not a rule, and switching layouts with changeLayout removes every style rule.
  - To reset field label styling, clearStyles each of the three selectors.
- Mark labels (the value text drawn on each bar, point, or slice; shown or hidden with showMarkLabel) are styled on `"MarkLabel"`, on Vizql and Packed visualizations. Use `"MarkLabel"` for "the mark labels", "the data labels", or "the value labels". `"BodyText"` and `"Global"` also restyle the mark labels, together with the other text, so use them only when the query means all body text or all text.
  - Font (`font.family`, `font.size`, `font.weight`, `font.italic`, `font.underline`), text color, `text.textDirection`, and `text.halign` go on `"MarkLabel"`. Send only what was asked. `text.halign` is saved but does not move the labels yet; still send it when asked.
  - Text color: by default mark labels pick black or white to stand out against each mark (auto contrast). A requested text color must always be sent together with `autoContrast: false`, in addStyleRule and in editStyleRule.
  - To go back to the automatic color ("make the mark label color automatic", "reset the mark label color"), send only `autoContrast: true`; the saved color is then removed.
  - Mark labels have no background, wrap, vertical alignment, `text.rotation` degrees, opacity, or line; do not send those. Styling the labels does not show them — if they are hidden, also send showMarkLabel `{isVisible: true}` in the same batch.
  - To reset mark label styling, clearStyles `{selector: "MarkLabel"}`.
- Mark style (the color, transparency, border, corners, or line dash of the data marks themselves) is one `"Mark"` rule on a Vizql chart. It always styles every mark; it cannot target one measure or one mark type. Do not send a `"Mark"` rule on a Table or Packed visualization; it has no effect there. Send only the properties the user asked for:
  - `color` — the mark color ("make the bars dark blue").
  - `opacity` — 0 to 100, where 100 is solid. "50% transparent" → `opacity: 50`; "80% opacity" → `opacity: 80`.
  - `border.width` — 0 to 10 pixels, where 0 means no border ("remove the mark borders" → `border: {width: 0}`). `border.color` — the border color. Send only the half the user named: a width alone or a color alone is fine, and editStyleRule keeps the other half. With no border color, the border follows the background color. A saved border color cannot be removed on its own, so for "make the border color match the background" or "set the border color to background", tell the user it is not supported yet; clearStyles on `"Mark"` does it but also resets every other mark style, so use it only if the user agrees.
  - `cornerRadius` — one of 0, 4, 8, 12, 20, or 9999, where 0 is square and 9999 is a fully rounded pill. Use 8 when the user asks for rounded corners without an amount. Bars are slightly rounded by default, so "square corners" is `cornerRadius: 0`.
  - `line.style` — `"Solid"`, `"Dashed"`, or `"Dotted"`, the dash pattern of a line chart's data line. Gridlines, axis lines, and other chart lines stay on their own line selectors.
  - `line.type` — `"Straight"` or `"Curved"`, the shape of a line chart's data line between points ("make the lines smooth" or "curved lines" → `line: {type: "Curved"}`).
  - Never send `font`, `text`, or `background` on `"Mark"`; mark label text is `"MarkLabel"`, a separate rule, so a `"MarkLabel"` rule does not mean `"Mark"` has one.
- Flow visualizations (levels joined by links) take only six selectors: `"Global"`, `"Headings"`, `"BodyText"`, `"Scene"`, `"FieldLabel"`, and `"LevelFieldLabelBox"`. These are the only selectors the Flow style panel covers, so do not send any other selector on Flow. A Flow has no headers, axes, totals, or lines. A solid node or link color ("make the nodes red") is not a style rule and is not supported on Flow yet: do not send `"Mark"`, `"FlowNode"`, or `"MarkLabel"`, and do not add a field to the Color encoding for it — make no operation and tell the user it isn't supported.
  - Text: `"Global"` restyles all the text. `"Headings"` covers the field labels over each level, the legend titles, and the node names. `"BodyText"` covers the legend labels and the values shown on the nodes. Use `"Headings"` for "the node names" or "the level names" and `"BodyText"` for "the node values". `"Global"`, `"Headings"`, and `"BodyText"` are three separate rules: a `"Global"` rule does not give `"Headings"` or `"BodyText"` one, so the first change to the node names or node values is addStyleRule.
  - Background: `"Scene"` is the whole background.
  - Field labels (the caption above each level): text goes on `"FieldLabel"`, exactly as on the other layouts. The background goes on `"LevelFieldLabelBox"` only — one operation, never `"RowFieldLabelBox"` or `"ColumnFieldLabelBox"`. A Flow's built-in `visualSpecification.style.fieldLabels.levels` is not a rule.
- Coloring the marks or data BY A FIELD is not a style operation — use addFieldToEncoding with the Color encoding, not addStyleRule.
- Examples:
  - "make axis titles bold 14pt dark blue" (not yet styled): addStyleRule `{selector: "AxisTitle", style: {font: {weight: "Bold", size: 14}, color: "#1A3D7C"}}`
  - "thin gray gridlines": addStyleRule `{selector: "GridLine", style: {color: "#CCCCCC", line: {width: 1}}}`
  - "make the axis line red": addStyleRule `{selector: "AxisLine", style: {color: "#FF0000"}}`
  - "make the axis tick marks 2px wide" (no stylesheet yet): addStyleRule, not editStyleRule — `{selector: "AxisTick", style: {line: {width: 2}}}`
  - "make the axis tick marks gray" right after their width was set ("AxisTick" has a rule): editStyleRule `{selector: "AxisTick", style: {color: "#999999"}}`
  - "make all the chart lines light gray": addStyleRule `{selector: "VizLines", style: {color: "#CCCCCC"}}`
  - "change the axis label color to red" (no "AxisTitle" rule): addStyleRule `{selector: "AxisTitle", style: {color: "#FF0000"}}` — not `"AxisTickLabel"`
  - "make the axis values smaller, 9pt" (no "AxisTickLabel" rule): addStyleRule `{selector: "AxisTickLabel", style: {font: {size: 9}}}`
  - "use the Arial font for the axis tick labels": addStyleRule `{selector: "AxisTickLabel", style: {font: {family: "Arial"}}}`
  - "white background": addStyleRule `{selector: "Scene", style: {background: {color: "#FFFFFF"}}}`
  - "bold the row and column headers": addStyleRule `{selector: "HeaderLabel", style: {font: {weight: "Bold"}}}`
  - "center the header text and make it read top to bottom": addStyleRule `{selector: "HeaderLabel", style: {text: {halign: "Center", textDirection: "VerticalDown"}}}`
  - "light blue header background": addStyleRule `{selector: "Header", style: {background: {color: "#D6ECFF"}}}` (`"Cell"` on a Table layout)
  - "shade alternate rows light gray" (Table, no "Row" rule): addStyleRule `{selector: "Row", style: {banding: {color: "#F3F3F3"}}}`
  - "show the gridlines, dashed and 50% transparent" (no "GridLine" rule): addStyleRule `{selector: "GridLine", style: {visibility: "Visible", line: {style: "Dashed"}, opacity: 50}}`
  - "hide the gridlines": addStyleRule `{selector: "GridLine", style: {visibility: "Hidden"}}`
  - "show the axis tick marks" (no "AxisTick" rule): addStyleRule `{selector: "AxisTick", style: {visibility: "Visible"}}`
  - "make the reference lines dotted and 2px" (no "ReferenceLine" rule): addStyleRule `{selector: "ReferenceLine", style: {line: {style: "Dotted", width: 2}}}`
  - "make the reference line dotted" (one reference line, no "ReferenceLine" rule): addStyleRule `{selector: "ReferenceLine", style: {line: {style: "Dotted"}}}` — not editReferenceLine
  - "make the zero line red": addStyleRule `{selector: "ZeroLine", style: {color: "#FF0000"}}`
  - "thicker separator lines between the header groups": addStyleRule `{selector: "SeparatorLine", style: {line: {width: 2}}}`
  - "bold the legend title": addStyleRule `{selector: "LegendTitle", style: {font: {weight: "Bold"}}}`
  - "make the legend items 10pt gray": addStyleRule `{selector: "LegendLabel", style: {font: {size: 10}, color: "#666666"}}`
  - "make the lines curved" (no "Mark" rule): addStyleRule `{selector: "Mark", style: {line: {type: "Curved"}}}`
  - "change headings text direction to vertical up" (no "Headings" rule): addStyleRule, not rotateHeader — `{selector: "Headings", style: {text: {textDirection: "VerticalUp"}}}`
  - "change body text direction to vertical up" (no "BodyText" rule; words like "change" or "set" do not mean a rule exists): addStyleRule `{selector: "BodyText", style: {text: {textDirection: "VerticalUp"}}}`
  - "use Georgia for all the text" (no "Global" rule): addStyleRule `{selector: "Global", style: {font: {family: "Georgia"}}}`
  - "also make the already-styled axis titles italic": editStyleRule `{selector: "AxisTitle", style: {font: {italic: true}}}`
  - "reset the axis titles back to default": clearStyles `{selector: "AxisTitle"}`
  - "set the field label text alignment back to auto" ("FieldLabel" has a color and size): editStyleRule `{selector: "FieldLabel", style: {text: {halign: "Auto"}}}` — not clearStyles, which would also remove the color and size
  - "set the headings text direction back to auto" ("Headings" has a rule): editStyleRule `{selector: "Headings", style: {text: {textDirection: "Auto"}}}`
  - "make the field labels bold and 14pt" (no "FieldLabel" rule): addStyleRule `{selector: "FieldLabel", style: {font: {size: 14, weight: "Bold"}}}`
  - "change the field label text color to red" (no field label rules at all): addStyleRule `{selector: "FieldLabel", style: {color: "#FF0000"}}`
  - "make the field labels not bold" (no "FieldLabel" rule): addStyleRule `{selector: "FieldLabel", style: {font: {weight: "Normal"}}}`
  - "make the field labels not bold" right after their font, size, or color was changed ("FieldLabel" has a rule): editStyleRule, not addStyleRule — `{selector: "FieldLabel", style: {font: {weight: "Normal"}}}`
  - "make the field label background blue" on a visualization with no stylesheet: addStyleRule, not editStyleRule, for each — `{selector: "RowFieldLabelBox", style: {background: {color: "#0000FF"}}}` and `{selector: "ColumnFieldLabelBox", style: {background: {color: "#0000FF"}}}`
  - "change the field label background to blue" (no "RowFieldLabelBox" or "ColumnFieldLabelBox" rule): addStyleRule `{selector: "RowFieldLabelBox", style: {background: {color: "#0000FF"}}}` and addStyleRule `{selector: "ColumnFieldLabelBox", style: {background: {color: "#0000FF"}}}`
  - "now make the field label background red" (both "RowFieldLabelBox" and "ColumnFieldLabelBox" have rules): editStyleRule on `"RowFieldLabelBox"` and editStyleRule on `"ColumnFieldLabelBox"`, each `{style: {background: {color: "#FF0000"}}}`
  - "change the field label text color to blue" right after a background change (rules exist for "RowFieldLabelBox" and "ColumnFieldLabelBox" but NOT for "FieldLabel"): addStyleRule, not editStyleRule — `{selector: "FieldLabel", style: {color: "#0000FF"}}`
  - "change the field label text direction to vertical up" (no "FieldLabel" rule): addStyleRule, not rotateHeader — `{selector: "FieldLabel", style: {text: {textDirection: "VerticalUp"}}}`
  - "change the field label text direction to horizontal" ("FieldLabel" has a rule): editStyleRule `{selector: "FieldLabel", style: {text: {textDirection: "Horizontal"}}}`
  - "make the grand total label font size 20" (no "GrandTotalLabel" rule): addStyleRule, NOT `"Global"` — `{selector: "GrandTotalLabel", style: {font: {size: 20}}}`
  - "make the grand total numbers 25pt" (no "GrandTotalValue" rule): addStyleRule `{selector: "GrandTotalValue", style: {font: {size: 25}}}`
  - "change the grand total label size to 25" ("GrandTotalLabel" has a rule): editStyleRule `{selector: "GrandTotalLabel", style: {font: {size: 25}}}`
  - "make the subtotal values vertical up" (no "SubtotalValue" rule): addStyleRule `{selector: "SubtotalValue", style: {text: {textDirection: "VerticalUp"}}}`
  - "right-align the subtotal labels" (no "SubtotalLabel" rule): addStyleRule `{selector: "SubtotalLabel", style: {text: {halign: "Right"}}}`
  - "make the grand total values red" right after the grand total label was styled (a "GrandTotalLabel" rule exists but NOT a "GrandTotalValue" one): addStyleRule, not editStyleRule — `{selector: "GrandTotalValue", style: {color: "#FF0000"}}`
  - "make the mark labels bold" (no "MarkLabel" rule): addStyleRule `{selector: "MarkLabel", style: {font: {weight: "Bold"}}}`
  - "make the data labels 16pt" (no "MarkLabel" rule): addStyleRule `{selector: "MarkLabel", style: {font: {size: 16}}}`
  - "make the mark labels red" (no "MarkLabel" rule): addStyleRule `{selector: "MarkLabel", style: {color: "#FF0000", autoContrast: false}}`
  - "turn the mark labels vertical up" (no "MarkLabel" rule): addStyleRule `{selector: "MarkLabel", style: {text: {textDirection: "VerticalUp"}}}`
  - "change the mark label font to Georgia" ("MarkLabel" has a rule): editStyleRule `{selector: "MarkLabel", style: {font: {family: "Georgia"}}}`
  - "set the mark label color back to automatic" ("MarkLabel" has a rule): editStyleRule `{selector: "MarkLabel", style: {autoContrast: true}}`
  - "make the mark labels bold" right after the marks were styled (a "Mark" rule exists but NOT a "MarkLabel" one): addStyleRule, not editStyleRule — `{selector: "MarkLabel", style: {font: {weight: "Bold"}}}`
  - "make the marks dark blue" (no "Mark" rule): addStyleRule `{selector: "Mark", style: {color: "#1A3D7C"}}`
  - "make the bars 50% transparent" (no "Mark" rule): addStyleRule `{selector: "Mark", style: {opacity: 50}}`
  - "add a 2 pixel border to the marks" (no "Mark" rule): addStyleRule `{selector: "Mark", style: {border: {width: 2}}}`
  - "make the mark border black" ("Mark" has a rule): editStyleRule `{selector: "Mark", style: {border: {color: "#000000"}}}`
  - "make the bars pill shaped" (no "Mark" rule): addStyleRule `{selector: "Mark", style: {cornerRadius: 9999}}`
  - "make the line dashed" on a line chart (no "Mark" rule): addStyleRule `{selector: "Mark", style: {line: {style: "Dashed"}}}`
  - "make the marks red" right after the mark labels were styled (a "MarkLabel" rule exists but NOT a "Mark" one): addStyleRule, not editStyleRule — `{selector: "Mark", style: {color: "#FF0000"}}`
  - "reset the mark style": clearStyles `{selector: "Mark"}`
  - "make the node names 16pt" on a Flow (no "Headings" rule): addStyleRule `{selector: "Headings", style: {font: {size: 16}}}`
  - "make the node names 20pt" on a Flow right after all the text was styled (a "Global" rule exists but NOT a "Headings" one): addStyleRule, not editStyleRule — `{selector: "Headings", style: {font: {size: 20}}}`
  - "make the node names 18pt bold" on a Flow right after "make all the text dark gray" (the only rule is `{selector: "Global", style: {color: "#404040"}}`): addStyleRule, not editStyleRule — `{selector: "Headings", style: {font: {size: 18, weight: "Bold"}}}`
  - "make the node values red" on a Flow (no "BodyText" rule): addStyleRule `{selector: "BodyText", style: {color: "#FF0000"}}`
  - "make the node values bold" on a Flow right after the node names were styled (a "Headings" rule exists but NOT a "BodyText" one): addStyleRule, not editStyleRule — `{selector: "BodyText", style: {font: {weight: "Bold"}}}`
  - "use Georgia for all the text" on a Flow (no "Global" rule): addStyleRule `{selector: "Global", style: {font: {family: "Georgia"}}}`
  - "light gray background" on a Flow: addStyleRule `{selector: "Scene", style: {background: {color: "#F5F5F5"}}}`
  - "change the field label background to light blue" on a Flow (no "LevelFieldLabelBox" rule): addStyleRule `{selector: "LevelFieldLabelBox", style: {background: {color: "#EEF4FF"}}}` — one operation, not RowFieldLabelBox and ColumnFieldLabelBox
  - "make the field labels italic" on a Flow (no "FieldLabel" rule): addStyleRule `{selector: "FieldLabel", style: {font: {italic: true}}}`
  - "reset the field label background" on a Flow: clearStyles `{selector: "LevelFieldLabelBox"}`

## Forecast

- addForecast requires `measureField` `{fieldName, objectName?, function?}` and `dateDimensionField` `{fieldName, objectName?}`. Optional:
  - `forecastInterval` `{value, timeUnit}` where timeUnit is "Minutes"/"Hours"/"Days"/"Weeks"/"Months"/"Quarters"/"Years"; defaults to 4 periods at the date field's granularity.
  - `forecastModel`: "HoltWinters" (default) or "RidgeRegression".
  - `includeBounds`: true (default)/false. `confidenceLevel`: 90/95 (default)/99. `ignoreLastPeriods`: number — excludes that many trailing (partial/incomplete) periods from the fit. `fillNullsWithZero`: true/false (default). `granularity`: only "InferFromData" is supported (the default; usually omit). `occurrence`: when the same measure appears more than once.
- editForecast updates an existing forecast (specify only what changes). removeForecast removes a specific forecast by `measureField`, or all forecasts when omitted. Forecasts require a time-series visualization (date on X, measure on Y).
- Examples:
  - "add a forecast for Sales": addForecast `{measureField: {fieldName: "Sales", objectName: "Orders"}, dateDimensionField: {fieldName: "OrderDate", objectName: "Orders"}}`
  - "forecast Sales for 6 months": add `forecastInterval: {value: 6, timeUnit: "Months"}`.
  - "forecast Revenue 12 months ahead using RidgeRegression": `{measureField: {fieldName: "Revenue"}, dateDimensionField: {fieldName: "Date"}, forecastInterval: {value: 12, timeUnit: "Months"}, forecastModel: "RidgeRegression"}`
  - "change the Sales forecast to 12 months": editForecast `{measureField: {fieldName: "Sales", objectName: "Orders"}, forecastInterval: {value: 12, timeUnit: "Months"}}`
  - "remove all forecasts": removeForecast `{}`; "remove the Sales forecast": removeForecast `{measureField: {fieldName: "Sales", objectName: "Orders"}}`
  - "add a forecast to the second Sales": add `occurrence: 2`.

## Filters

**Params shape.** addFilter / editFilter `params` are `{filter: {fields: [...], operator, values}, bucket?}` — the field reference (`{model:}` or `{expression:}`) goes inside the `fields` array of the `filter` object, NEVER as a bare `field:` key. `bucket` defaults to "filter" (standard) when omitted. Full operation entry:

```json
{
  "operationType": "addFilter",
  "params": {
    "bucket": "filter",
    "filter": {
      "fields": [{"model": "Orders.Region"}],
      "operator": "In",
      "values": ["East", "West"],
      "includeNulls": false
    }
  }
}
```

**Field reference — model vs expression:**

- Use `{model: "Object.Field"}` for a simple comparison on the raw field value (no aggregation). e.g. "sales > 1000" → `{fields: [{model: "Orders.Sales"}], operator: "GreaterThan", values: [1000]}`.
- Use `{expression: "SUM(...)"}` etc. ONLY when the user names an aggregate ("total", "sum of", "average", "count of"), with `bucket: "aggregateFilter"`. A bare measure name with NO aggregate keyword is NOT an aggregate: "sales of at least 2000", "profit over 500", "quantity more than 10" all use `{model: "Object.Field"}`, never `SUM(...)`. Without an explicit aggregate keyword, ALWAYS use `{model: "Object.Field"}`.
- Use `{expression: "DATEPART(...)"}` for year/month/quarter/etc. filtering.
- Use a table-calc expression (`RUNNING_SUM`/`RANK`/`WINDOW_*`/...) with `bucket: "tableCalcFilter"`.
- Field references in expressions use bracket notation `[Object].[Field]`.

**Expression forms:**

- Date (DATEPART → integer, DATETRUNC → date): `DATEPART('year'|'quarter'|'month'|'week'|'day', [Object].[Field])`; `DATETRUNC('year'|'month'|'quarter', [Object].[Field])`.
- Aggregate (`bucket: "aggregateFilter"`): SUM/AVG/MIN/MAX/COUNT/COUNTD/MEDIAN([Object].[Field]); ratios like `SUM([O].[Profit])/SUM([O].[Sales])`.
- Table calc (`bucket: "tableCalcFilter"`, always wrap an aggregate): RUNNING_SUM/RUNNING_AVG/RUNNING_MIN/RUNNING_MAX/RUNNING_COUNT(AGG(...)); RANK(AGG(...), 'ASC'|'DESC'); WINDOW_SUM/WINDOW_AVG(AGG(...), start, end).

**Operator rules:**

1. NEVER use Equals/DoesNotEquals — use In/NotIn ("Color is Red" → `operator: "In", values: ["Red"]`; supports multiple values).
2. ALWAYS use IgnoreCase string variants (ContainsIgnoreCase, StartsWithIgnoreCase, EndsWithIgnoreCase, DoesNotStartWithIgnoreCase, …) — users rarely mean case-sensitive.
3. NEVER put null/undefined in `values` — all values must be concrete. If you can't express both bounds concretely, choose another operator.
4. ALWAYS set `includeNulls` on an In/NotIn filter (`false` unless the user asks to keep nulls). The save (`updateVisualization`) rejects an In/NotIn filter without it with `INVALID_VISUALIZATION_METADATA`. Other operators do not need it.

**Operators by category:**

- Equality (multi-value): In, NotIn.
- Comparison: Between, LessThan, LessThanOrEqualTo, GreaterThan, GreaterThanOrEqualTo.
- String (IgnoreCase): ContainsIgnoreCase, NotContainsIgnoreCase, StartsWithIgnoreCase, DoesNotStartWithIgnoreCase, EndsWithIgnoreCase, DoesNotEndWithIgnoreCase.
- Null/Empty: IsNull, IsNotNull, IsEmpty, IsNotEmpty.
- Relative date (no values): CurrentDay/Week/Month/Quarter/Year, PreviousDay/Week/Month/Quarter/Year, NextDay/Week/Month/Quarter/Year.
- Relative date (`values: [N]`): LastNMinutes/Hours/Days/Weeks/Months/Quarters/Years, NextNDays/Weeks/Months/Quarters/Years.
- Fiscal (no values): CurrentFiscalWeek/Month/Quarter/Year. Fiscal (`values: [N]`): LastNFiscalWeeks/Months/Quarters/Years. Use fiscal ONLY when the user says "fiscal" — "this quarter" → CurrentQuarter, not CurrentFiscalQuarter.
- Date-to-date (uses `{model:...}`, no expression): CurrentYearToDate/MonthToDate/QuarterToDate/WeekToDate, PreviousYearToDate/MonthToDate/QuarterToDate/WeekToDate.
- TopN/BottomN: AdvancedDimension with `topBottomCriteria: {topBottomLimit, isTop, expression}` (isTop true for top N), `bucket: "advancedDimensionFilter"`. Always use this operator for any top/bottom-N request — never a value filter.
- Relative-date form selection: "last/next <period>" (no number) → singular (PreviousWeek, NextMonth); "last/next N <periods>" → LastN/NextN; "last 1 quarter" → LastN form with `values: [1]`.

**Buckets (execution order):** filter (standard dimension), contextFilter (before aggregation), aggregateFilter (aggregated values), tableCalcFilter (table calcs), advancedDimensionFilter (TopN/BottomN).

**editFilter** updates an existing filter's expression (same `params` shape as addFilter, matched against the existing filter's field); **removeFilter** removes it (`{filterField: {model: "Object.Field"}}`).

**Add-then-filter vs plain filter:**

- A query that only RESTRICTS data is ONE addFilter, even when it names a dimension: "filter to top 10 customers by sales" (TopN), "show orders from this year", "only show the West region". If the field is already on a shelf, just filter it.
- Add-then-filter applies ONLY when the user wants to SEE a dimension broken out by its values AND restrict which show, AND that dimension is not already on a shelf: FIRST addFieldToRowsOrColumns, THEN addFilter. e.g. "I want to see Region in East and West" (no Region on a shelf) →

```json
[
  {
    "operationType": "addFieldToRowsOrColumns",
    "params": {"field": {"fieldName": "Region", "objectName": "Orders"}, "shelfType": "rows"}
  },
  {
    "operationType": "addFilter",
    "params": {
      "filter": {
        "fields": [{"model": "Orders.Region"}],
        "operator": "In",
        "values": ["East", "West"],
        "includeNulls": false
      },
      "bucket": "filter"
    }
  }
]
```

- Distinguish intent: FILTER/RESTRICT verbs ("filter to", "only show", "where", "restrict to") → addFilter; DISPLAY/ADD verbs ("add to rows", "put on columns", "place on shelf") → addFieldToRowsOrColumns. "show"/"display" + a condition usually means addFilter.

**Filter examples:**

- "sales greater than 1000" (raw field): `{filter: {fields: [{model: "Orders.Sales"}], operator: "GreaterThan", values: [1000]}}`
- "orders from 2020 and 2021": `{filter: {fields: [{expression: "DATEPART('year', [Orders].[Order_Date])"}], operator: "In", values: [2020, 2021], includeNulls: false}}`
- "orders after June 2022" (DATETRUNC, ISO values): `{filter: {fields: [{expression: "DATETRUNC('month', [Orders].[Order_Date])"}], operator: "GreaterThan", values: ["2022-06-01"]}}`
- "where total sales > 10000" (aggregate): `{filter: {fields: [{expression: "SUM([Orders].[Sales])"}], operator: "GreaterThan", values: [10000]}, bucket: "aggregateFilter"}`
- "where profit margin > 15%": `{filter: {fields: [{expression: "SUM([Orders].[Profit])/SUM([Orders].[Sales])"}], operator: "GreaterThan", values: [0.15]}, bucket: "aggregateFilter"}`
- "where running sum of sales > 1000": `{filter: {fields: [{expression: "RUNNING_SUM(SUM([Orders].[Sales]))"}], operator: "GreaterThan", values: [1000]}, bucket: "tableCalcFilter"}`
- "top 10 states by sales": `{filter: {fields: [{model: "Orders.State"}], operator: "AdvancedDimension", topBottomCriteria: {topBottomLimit: 10, isTop: true, expression: "SUM([Orders].[Sales])"}}, bucket: "advancedDimensionFilter"}`

## Table shelf operations (TABLE visualizations only)

- A TABLE-layout visualization lays fields out in two shelves: Columns (the fields shown as table columns) and Groups (the fields those columns are grouped by). These are the table equivalent of the rows/columns operations and DO NOT apply to a VizQL chart — if the visualization is on a VizQL layout, convert it to a table first with changeLayout, or these operations error. `shelfType` names the shelf: "columns" or "groups"; the target field nests under a `"field"` object exactly like addFieldToRowsOrColumns, with `function` using the canonical values above.
- addFieldToGroupsOrColumns adds a field (`insertPosition`, 0-based, places it; appended when omitted). removeFieldFromGroupsOrColumns removes one (`occurrence`, 1-based, picks the copy). replaceFieldFromGroupsOrColumns swaps `existingField` for `newField`, keeping the replaced field's position (`occurrence` picks which copy of existingField). reorderFieldsOnGroupsOrColumns moves one field already on the shelf to a new position (`insertPosition` 0-based from 0 to the shelf's last index; `occurrence` picks the copy), adding or removing nothing.
- Examples:
  - "Add Region to the table columns": addFieldToGroupsOrColumns `{field: {fieldName: "Region", objectName: "Orders"}, shelfType: "columns"}`
  - "Add count distinct of Order_ID to the table columns": addFieldToGroupsOrColumns `{field: {fieldName: "Order_ID", objectName: "Orders", function: "CountD"}, shelfType: "columns"}`
  - "Group the table by Category": addFieldToGroupsOrColumns `{field: {fieldName: "Category", objectName: "Orders"}, shelfType: "groups"}`
  - "Add total Sales as the first table column": addFieldToGroupsOrColumns `{field: {fieldName: "Sales", objectName: "Orders", function: "Sum"}, shelfType: "columns", insertPosition: 0}`
  - "Remove Sales from the table columns": removeFieldFromGroupsOrColumns `{field: {fieldName: "Sales", objectName: "Orders", function: "Sum"}, shelfType: "columns"}`
  - "Swap Category for Segment in the table groups": replaceFieldFromGroupsOrColumns `{existingField: {fieldName: "Category", objectName: "Orders"}, newField: {fieldName: "Segment", objectName: "Orders"}, shelfType: "groups"}`
  - "Move Sales to the first table column": reorderFieldsOnGroupsOrColumns `{field: {fieldName: "Sales", objectName: "Orders"}, shelfType: "columns", insertPosition: 0}`

## Change field (table shelf, TABLE visualizations only)

- changeFieldOnGroupsOrColumns changes an EXISTING table shelf field's aggregation and/or role, keeping it in place. Params: `{field, shelfType, occurrence?, function?, role?}` — supply at least one of `function` (an aggregation) or `role` ("Dimension"/"Measure"); the omitted one is unchanged. Changing to a Measure requires `function` (Sum, Avg, Median, Min, Max, Count, CountD, Stdev, Stdevp, Var, Varp); changing to a Dimension drops the function. Unlike changeFieldOnRowsOrColumns there is NO `displayCategory` — table fields are always discrete.
- Examples:
  - "average Sales in the table instead of summing it" (Sum of Sales on columns): `{field: {fieldName: "Sales", objectName: "Orders", function: "Sum"}, shelfType: "columns", function: "Avg"}`
  - "aggregate the Category column as a count of distinct values": `{field: {fieldName: "Category", objectName: "Orders"}, shelfType: "columns", role: "Measure", function: "CountD"}`

## Measure Values (VizQL visualizations only)

- The Measure Values shelf holds a list of measures pivoted by a Measure Names field on rows or columns so multiple measures share one axis (e.g. "show Sum of Amount and Count on the same axis"). To set up the construct on an EMPTY visualization, add the special Measure Names or Measure Values field with addFieldToRowsOrColumns and `{field: {type: "MeasureNames"|"MeasureValues"}}` (only valid before any field is placed); remove it with removeFieldFromRowsOrColumns. Once it exists, add measures here.
- addFieldToMeasureValues adds a measure (`{field, insertPosition?}`; appends when `insertPosition` omitted; only measures — dimensions error). reorderFieldsOnMeasureValues moves one (`{field, insertPosition, occurrence?}`). replaceFieldFromMeasureValues swaps a measure already on the shelf (`existingField`) for another not on the shelf (`newField`), keeping the replaced measure's slot (`{existingField, newField, occurrence?}`). removeFieldFromMeasureValues removes one (`{field, occurrence?}`). The same measure can sit on the shelf more than once, so `occurrence` (1-based) picks which copy.
- Examples:
  - "Show Sum of Sales and Profit on the same axis" (Sum of Sales already on an axis, add Profit): addFieldToMeasureValues `{field: {fieldName: "Profit", objectName: "Orders", function: "Sum"}}`
  - "Add Measure Values to the columns" (empty visualization): addFieldToRowsOrColumns `{field: {type: "MeasureValues"}, shelfType: "columns"}`
  - "Add Profit at position 0 on Measure Values": addFieldToMeasureValues `{field: {fieldName: "Profit", objectName: "Orders", function: "Sum"}, insertPosition: 0}`
  - "Move Sales to position 1 on Measure Values": reorderFieldsOnMeasureValues `{field: {fieldName: "Sales", objectName: "Orders", function: "Sum"}, insertPosition: 1}`
  - "Replace Profit with Quantity on Measure Values" (Profit on the shelf, Quantity not): replaceFieldFromMeasureValues `{existingField: {fieldName: "Profit", objectName: "Orders", function: "Sum"}, newField: {fieldName: "Quantity", objectName: "Orders", function: "Sum"}}`
  - "Remove the second Sum of Sales from Measure Values": removeFieldFromMeasureValues `{field: {fieldName: "Sales", objectName: "Orders", function: "Sum"}, occurrence: 2}`

## Flow shelf operations (FLOW visualizations only)

- A FLOW-layout (sankey) visualization lays fields out in two shelves: Levels (an ordered list of discrete fields, one column of nodes each) and Link (ONE continuous measure that sizes the flows between the levels). Each shelf has its own operations, so there is no `shelfType` param; pick the operation by shelf. These DO NOT apply to a VizQL chart or a table — if the visualization is not on a Flow layout, convert it first with changeLayout, or these operations error. The target field nests under a `"field"` object exactly like addFieldToRowsOrColumns.
- Fields are converted to fit the shelf: a measure added to Levels becomes discrete, and a dimension added to the Link becomes a Count Distinct measure. The Link never takes Attr, and a text or date field on the Link takes only Count or CountD (Min or Max errors); leave `function` off and it defaults to CountD.
- Levels: addFieldToLevels adds a level (`{field, insertPosition?}`; `insertPosition`, 0-based, places it; appended when omitted). removeFieldFromLevels removes one (`{field, occurrence?}`). replaceFieldOnLevels swaps `existingField` for `newField`, keeping the replaced field's position (`{existingField, newField, occurrence?}`). reorderFieldsOnLevels moves one level to a new position (`{field, insertPosition, occurrence?}`; `insertPosition` 0-based from 0 to the last level), adding or removing nothing.
- Link: the Link holds a single field. addFieldToLink sets it when no link is set yet (`{field}`); when a link is already set, use replaceFieldOnLink (`{existingField, newField}`) instead, since adding a second link errors. removeFieldFromLink clears it (`{field}`).
- "Sizing" or "weighting" the flows, or showing flows "by" a measure, means the Link — never add that measure to Levels.
- Changing a field already on a Flow shelf, keeping it in place: use changeFieldOnLevels or changeFieldOnLink, NEVER changeFieldOnRowsOrColumns or changeFieldOnGroupsOrColumns (those error on Flow), and never remove-then-add.
  - changeFieldOnLevels `{field, occurrence?, function?, role?}` — supply at least one of `function` or `role` ("Dimension"/"Measure"); the omitted one is unchanged. Changing to a Measure requires `function` (Sum, Avg, Median, Min, Max, Count, CountD, Stdev, Stdevp, Var, Varp; Sum/Avg/etc. only on a number field — use Count or CountD for text). Changing to a Dimension drops the function. On a date field, a date part (DatePartYear, DatePartQuarter, DatePartMonth, DatePartDay, ...) or truncation (DateTruncYear, DateTruncMonth, ...) makes it a date dimension. There is NO `displayCategory`: a level always stays discrete. A measure level also takes Attr. On a dimension level, Attr needs `role: "Measure"` too (`{role: "Measure", function: "Attr"}`); Attr alone on a dimension errors.
  - changeFieldOnLink `{field, function}` — the link is always a continuous measure, so only its aggregation changes (same list as above, but a text field on the link only takes Count or CountD). There is no `role`, no date function, and no Attr on the link; to show flows by a different field, use replaceFieldOnLink instead.
  - The link can never be a dimension. If the user asks to make the link field a dimension (or discrete), do NOT call changeFieldOnLink or swap in another aggregation such as Count or CountD — that silently keeps it a measure. Make no change, and tell the user the link must stay a measure; to group by that field, add it to the Levels with addFieldToLevels.
- Examples:
  - "Add Region as a level": addFieldToLevels `{field: {fieldName: "Region", objectName: "Orders"}}`
  - "Make Segment the first level of the sankey": addFieldToLevels `{field: {fieldName: "Segment", objectName: "Orders"}, insertPosition: 0}`
  - "Remove Category from the levels": removeFieldFromLevels `{field: {fieldName: "Category", objectName: "Orders"}}`
  - "Swap Category for Segment in the levels": replaceFieldOnLevels `{existingField: {fieldName: "Category", objectName: "Orders"}, newField: {fieldName: "Segment", objectName: "Orders"}}`
  - "Move Region to the first level": reorderFieldsOnLevels `{field: {fieldName: "Region", objectName: "Orders"}, insertPosition: 0}`
  - "Size the flows by Sales" (no link yet): addFieldToLink `{field: {fieldName: "Sales", objectName: "Orders", function: "Sum"}}`
  - "Size the flows by Profit instead" (Sales is the link): replaceFieldOnLink `{existingField: {fieldName: "Sales", objectName: "Orders", function: "Sum"}, newField: {fieldName: "Profit", objectName: "Orders", function: "Sum"}}`
  - "Stop sizing the flows by Sales": removeFieldFromLink `{field: {fieldName: "Sales", objectName: "Orders", function: "Sum"}}`
  - "Use Category as a count distinct measure in the levels": changeFieldOnLevels `{field: {fieldName: "Category", objectName: "Orders"}, role: "Measure", function: "CountD"}`
  - "Show the Order Date level by month": changeFieldOnLevels `{field: {fieldName: "Order_Date", objectName: "Orders"}, function: "DatePartMonth"}`
  - "Size the flows by average Sales instead of the sum": changeFieldOnLink `{field: {fieldName: "Sales", objectName: "Orders", function: "Sum"}, function: "Avg"}`

## Table totals and subtotals (TABLE visualizations only)

- Two separate summary rows: GRAND TOTALS (one row summarizing the whole table — showGrandTotals; pick it for "total"/"grand total"/"total row"/"summary row" with no mention of groups) and SUBTOTALS (one row per group boundary — showSubtotals; pick it for "subtotal"/"group total"/"total for each group"/"totals per category"). These toggle ROW flags only — no columns parameter: column subtotals are never legal (showSubtotals rejects `columns: true`), and showGrandTotals preserves an existing column-grand-total flag but does not toggle it.
- `isVisible` (required) shows (true) or hides (false) the row. `position`? "Start" (above the table, or above each group) or "End" (below); map "top"/"above"/"first" → "Start", "bottom"/"below"/"last"/"at the end" → "End". Omit position when unsaid — grand totals default to "End", subtotals follow the grand totals. position is rewritten on EVERY call, so when only hiding a row, pass its current position to keep where it sits.
- editGrandTotalsLabel / editSubtotalsLabel rename the row (`{label: "text"}`; defaults read "Grand Total" / "Subtotal"). To reset to the default — "reset it", "clear the name", "remove the custom label" — send EMPTY params `{}` and leave `label` out; NEVER send `{label: ""}` (an empty or all-whitespace label is rejected). These only rename a row the table already has (shown or hidden), so emit the rename ALONE — add a showGrandTotals/showSubtotals first only when the table has no such row.
- Formatting a summary row — its font, color, alignment, or text direction — is a style change, not a rename or a show/hide: use addStyleRule (editStyleRule if already styled) with `selector` `"GrandTotalLabel"` or `"SubtotalLabel"` for the row name ("Grand Total", "Subtotal") and `"GrandTotalValue"` or `"SubtotalValue"` for the numbers in that row. Use editGrandTotalsLabel / editSubtotalsLabel only to change the label TEXT, and showGrandTotals / showSubtotals only to show, hide, or move the row. A style rule does not add the row: on a table with no such row, emit showGrandTotals / showSubtotals `{isVisible: true}` first, then the style rule. See Global style. Never use selector `"Global"` for a grand total or subtotal font, color, or alignment.
- DO NOT use these just because "total" appears — they add or rename a summary ROW, never a column or a per-row figure: a measure to display/aggregate → addFieldToGroupsOrColumns (or addFieldToRowsOrColumns) with function "Sum"; a per-row calc (running total, percent of total, rank, moving average) → applyTableCalc; a totals COLUMN → addFieldToGroupsOrColumns; renaming the viz → changeLabel.
- Examples:
  - "Add a grand total row to this table": showGrandTotals `{isVisible: true}`
  - "Show totals at the top of the table": showGrandTotals `{isVisible: true, position: "Start"}`
  - "Turn off the total row": showGrandTotals `{isVisible: false}`
  - "Rename the grand total row to 'Overall Total'": editGrandTotalsLabel `{label: "Overall Total"}`
  - "Reset the grand total label to the default": editGrandTotalsLabel `{}`
  - "Show subtotals for each group": showSubtotals `{isVisible: true}`
  - "Add group totals at the top of each group": showSubtotals `{isVisible: true, position: "Start"}`
  - "Rename the subtotal label to 'Group Total'": editSubtotalsLabel `{label: "Group Total"}`
  - "Clear the subtotal label" (a reset — params stay empty, NOT {label: ""}): editSubtotalsLabel `{}`

## Field header (show/hide, rotate text)

- showHeader shows or hides a single field's header (`{field, isVisible, occurrence?, shelfType?}`). Works on a Vizql or a Table visualization. `shelfType` is "rows", "columns", or "groups".
- rotateHeader rotates a single field's header text (`{field, textDirection, occurrence?, shelfType?}`); textDirection is "Horizontal", "VerticalUp", or "VerticalDown". VizQL only — rotating a header is not offered on a Table and errors there.
- Both edit an EXISTING header only: the field must already be placed on a shelf. If it has no header yet, they error rather than creating one. When the same field is placed more than once, pass a 1-based `occurrence` to pick which copy (1 is the first), or `shelfType` to name the shelf when the field spans shelves; omit both when the field is unique.
- Use these when the query asks to show/hide a column or row header, or to turn one named field's header text sideways/vertical. To change the text direction of all the headers at once (no field named), use addStyleRule with `selector: "HeaderLabel"` and `style: {text: {textDirection}}` instead — that also works on a Table. Headers are the field's values (such as "Furniture", "Technology"); field labels are the shelf captions (such as "Category"). A request about the FIELD LABEL text direction is never rotateHeader — it is addStyleRule/editStyleRule `text.textDirection` on `"FieldLabel"` (see Global style). "Headings" (as in "change the headings text direction") is the `"Headings"` style group, not headers, so it is never rotateHeader either: use addStyleRule/editStyleRule `text.textDirection` on `"Headings"`.
- Examples:
  - "Hide the Region header": showHeader `{field: {fieldName: "Region", objectName: "Orders"}, isVisible: false}`
  - "Show the header for Sum of Sales": showHeader `{field: {fieldName: "Sales", objectName: "Orders", function: "Sum"}, isVisible: true}`
  - "Rotate the Category header to vertical": rotateHeader `{field: {fieldName: "Category", objectName: "Orders"}, textDirection: "VerticalUp"}`

## Field header sizing (resize)

- resizeHeader sets the pixel size of one field header (`{field, size, occurrence?, shelfType?}`). Width vs height is derived from the shelf the header sits on: a field on rows or groups writes width; a field on columns writes height. `size` is a pixel value of zero or greater. `shelfType` is "rows", "columns", or "groups" — omit it when the field is unique among placed headers; pass it when the same field is on more than one shelf. `"groups"` is Table layout only.
- Works on a Vizql or a Table visualization. The field must already be on a shelf. To resize two headers, emit two operations.
- Errors (rather than silently ignoring) on: a Flow/Map/Radial layout; `shelfType: "groups"` on a Vizql visualization; a negative `size`; a field not on a header shelf; or an ambiguous field with no `shelfType`/`occurrence`.
- Use when the query asks to make a column wider, set a column to a pixel width, set a row height, or resize a header to a size.
- Examples:
  - "Make the Region column 220 pixels wide": resizeHeader `{field: {fieldName: "Region", objectName: "Orders"}, size: 220}`
  - "Set the row height for Product to 40": resizeHeader `{field: {fieldName: "Product", objectName: "Orders"}, size: 40}`
  - "Resize the Region group header to 150": resizeHeader `{field: {fieldName: "Region", objectName: "Orders"}, size: 150, shelfType: "groups"}`

## Mark labels (show/hide)

- A mark label is the text drawn ON a data-point mark — the value shown above each bar, next to each point, or on each slice. This is different from a field label (an axis/shelf caption; use showFieldLabel) and from a field header (use showHeader).
- showMarkLabel shows or hides those labels (`{field?, isVisible, occurrence?}`). Omit `field` to affect all marks; pass it to target one field's mark (by fieldName, plus objectName/function when needed). Runs on Vizql and Packed visualizations; every other layout errors. On a Packed visualization the labels toggle for all marks, so do NOT pass `field` there.
- When the same measure is placed on the shelves more than once (two identical sub-marks that fieldName/objectName/function cannot tell apart), pass `occurrence` (1-based, counted by shelf position) to pick which one; omit it when the field is unique.
- Use showMarkLabel when the query asks to show or hide data labels or value labels on the marks. Styling the mark labels (font, size, color, bold, italic, underline, alignment, text direction) is not showMarkLabel — it is addStyleRule/editStyleRule on `"MarkLabel"` (see Global style).
- Examples:
  - "Turn on data labels": showMarkLabel `{isVisible: true}`
  - "Hide the mark labels for Sales": showMarkLabel `{field: {fieldName: "Sales", objectName: "Orders", function: "Sum"}, isVisible: false}`
  - "Show the data labels on the second Sales": showMarkLabel `{field: {fieldName: "Sales", objectName: "Orders", function: "Sum"}, isVisible: true, occurrence: 2}`

## Mark size (set/reset)

- changeMarkSize sets the fixed size of the marks drawn in the visualization — the width of bars, the diameter of points/bubbles (`{sizeType, value, field?}`). `sizeType` is a canonical `VisualizationMarkSizeType` value: "Pixel" (an absolute size) or "Percentage" (a size relative to the cell). `value` is the size in that unit; it must fall within the allowed range for the mark type, and an out-of-range value errors.
- resetMarkSize clears a custom mark size and returns it to the automatic default for the mark type and layout (`{field?}`).
- `field` (`{fieldName, objectName?, function?}`) sizes only that field's mark; omit `field` to size every mark in the visualization. Both operations work on VizQL, Packed, and Table visualizations; every other layout errors.
- Only Bar, Circle, Square, and Donut marks can be sized; Line, Area, Text, and Spatial marks cannot, and sizing one errors. When sizing every mark (no `field`) and the visualization mixes sizable and unsizable mark types, that also errors — name a `field` that is a sizable mark to size just that one.
- When the same field is placed more than once (for example the same measure added twice), each copy draws its own mark that is sized on its own. Use `occurrence` (1-based, counted by shelf position) to pick which copy. Omit it when the field is unique — targeting a duplicate without `occurrence` errors.
- Use changeMarkSize when the query asks to make marks bigger/smaller, set a bar width, or set a point size; use resetMarkSize when the query asks to restore the default mark size.
- Near-miss routing: changeMarkSize sets one fixed size for the targeted marks. A query that asks to vary size by a field's values — "size the bubbles by Sales", "make bigger sales show as bigger points" — is a size encoding, not this operation; changeMarkSize does not map a field to size.
- Examples:
  - "Make the bars 40 pixels": changeMarkSize `{sizeType: "Pixel", value: 40}`
  - "Set the mark size to 60%": changeMarkSize `{sizeType: "Percentage", value: 60}`
  - "Make the Sales marks bigger, 50px": changeMarkSize `{sizeType: "Pixel", value: 50, field: {fieldName: "Sales", objectName: "Orders", function: "Sum"}}`
  - "Size the second Sales bars to 30px" (Sales on columns twice): changeMarkSize `{sizeType: "Pixel", value: 30, field: {fieldName: "Sales", objectName: "Orders", function: "Sum"}, occurrence: 2}`
  - "Reset the mark size to default": resetMarkSize `{}`

## Tooltip styling

- A tooltip is the popover shown when hovering a mark. updateTooltipStyle edits its styling on two levels; provide at least one field (`{isVisible?, color?, transparency?, showActions?, customText?, field?, occurrence?, headers?}`).
- To ADD A DATA FIELD to the tooltip — show a field's value on hover ("add a tooltip showing Sales", "put Profit in the tooltip", "show Quantity on hover") — use addFieldToEncoding with `encodingType: "Tooltip"` (see Mark encoding), NOT updateTooltipStyle. updateTooltipStyle only styles the popover (visibility, color, action links) and sets a fixed custom-text template; it does not add a field to the hover data.
- Visualization-level container — `isVisible` (show/hide the tooltip), `color` (background as a 6-digit hex string like `#FFFFFF`), and `transparency` (0 opaque to 100 fully transparent). Any omitted value keeps the current setting, so you can change one without resetting the others. A color that is not a 6-digit hex, or a transparency outside 0–100, errors. These apply to the whole visualization, so combining them with `field` errors; with `headers` they are allowed.
- Mark-level — `showActions` toggles the built-in action links, and `customText` sets the tooltip's custom content. Both are written to the mark(s) named by `field` (omit `field` to affect every mark). With `headers` true (Vizql and Table; cannot be combined with `field`), `showActions` goes to the shared headers mark and `customText` still fans out to every mark.
- `customText` is an ordered array of text values that make up the tooltip content. Each value is one of: plain text `{type: "Text", value: "Sales: "}`; a visualization field token `{type: "VisualizationFieldToken", fieldKey: "F1"}` (fieldKey must name a field on the visualization); an SDM field token `{type: "SdmFieldToken", apiName}`; or a property token `{type: "PropertyToken", tokenType}`. Any value may carry `properties` (font `family`/`size`/`bold`/`italic`/`underline`/`color`/`horizontalAlign`). A font `size` outside 10–128, a non-6-digit-hex `color`, a field token naming an absent field, or a total length over 4096 (each token counts as 1) errors. Pass an empty array to clear the custom text.
- `field` picks which mark the mark-level fields apply to, just like other mark operations: omit it to fan `showActions` and `customText` to every mark — the whole-visualization mark, each per-field mark, and the shared headers on Table (Packed keeps only the whole-visualization mark); set it (named by fieldName, plus objectName/function when needed) to write just that field's mark. A field on Packed, which has no per-field marks, errors. Pass `occurrence` alongside `field` when the same measure is placed more than once.
- Runs on Vizql, Table, and Packed; other layouts error.
- Use these when the query asks to turn tooltips on/off, restyle the tooltip background, show/hide the tooltip's action links, or set the tooltip's custom text.
- Examples:
  - "Hide the tooltips": updateTooltipStyle `{isVisible: false}`
  - "Make the tooltip background white and 20% transparent": updateTooltipStyle `{color: "#FFFFFF", transparency: 20}`
  - "Turn off the tooltip action links": updateTooltipStyle `{showActions: false}`
  - "Hide the action links on the Sales tooltip": updateTooltipStyle `{showActions: false, field: {fieldName: "Sales", objectName: "Orders", function: "Sum"}}`
  - "Hide the action links on the header tooltips": updateTooltipStyle `{showActions: false, headers: true}`
  - "Set the tooltip to say 'Revenue: <Sales>'": updateTooltipStyle `{customText: [{type: "Text", value: "Revenue: "}, {type: "VisualizationFieldToken", fieldKey: "F1"}]}`
  - "Clear the tooltip custom text": updateTooltipStyle `{customText: []}`

## Persistence handoff — `update_visualization`

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
directly in another `edit_visualization` call (see Contract) without a `get_visualization`
round trip; the server's working state for that id already reflects the saved edits.
