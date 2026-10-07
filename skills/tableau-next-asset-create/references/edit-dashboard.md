# Editing an Existing Dashboard — `edit_dashboard`

Load this when the request mutates a dashboard that **already exists** (add,
replace, move, or remove a widget; add, rename, or delete a page) — not for
building a brand-new dashboard (`dashboard-authoring.md` §1 /
`tasks/build-dashboard.md` instead).

`edit_dashboard` is the **only supported tool** for dashboard widget/page
editing — never hand-build a dashboard-JSON PATCH.

> **Schema note (2026-09-07):** the tool's operations were renamed from
> `build_*_widget` to `upsert_*_widget` and the separate `edit_widget`
> operation was removed — a single `upsert_*_widget` op now both creates and
> fully replaces a widget, selected by whether you pass `widget.id`. `autosave`
> also moved from a per-operation field to a single top-level/batch-wide field.
> Facts below that carry an explicit "verified live" date predate this change
> and describe *behavior*, not the old field names — re-verify live if
> something here looks inconsistent with what the server actually returns.

> **Schema note (2026-09-09):** `remove_widget_from_dashboard` is now a native
> `edit_dashboard` operation — a true widget delete (definition + every page
> placement in one step), closing the gap this file previously documented as
> unsupported. See §6. Every widget also gained optional `actions`
> (click/select → navigate/run-a-flow/set-a-parameter/set-a-filter/record
> action) and `dynamicTokens` fields (identical shape across every
> `upsert_*_widget` op — see `schemas/edit-dashboard/_shared-widget-fields.json`),
> and `upsert_filter_widget`/`upsert_parameter_widget`'s `parameters` is now an
> explicit `oneOf` keyed by `viewType`. `save_dashboard` gained an optional
> `dashboardIdOrApiName` (defaults to the batch's own dashboard).

## Contents

- 1. Contract
- 2. Operation-type reference
- 3. Widget identity — `widget.name` and `widget.id`
- 4. Grid placement
- 5. Draft vs. persist
- 6. Deleting a widget — `remove_widget_from_dashboard`
- 7. Gotchas summary

---

## 1. Contract

`edit_dashboard` applies an ordered, **non-empty list of operations** to one
dashboard, atomically (all-or-nothing — one failing operation means none are
applied):

```jsonc
{
  "dashboardIdOrApiName": "Edit_Compare_Dashboard_175417",
  "minorVersion": -1,          // ALWAYS send this explicitly — see gotcha below
  "autosave": false,           // top-level, batch-wide — see §5. Ignored if a
                                // save_dashboard/undo/discard_dashboard op is present.
  "operations": [ /* ordered, discriminated by "operation" */ ]
}
```

**Always send `minorVersion: -1` explicitly.** The schema documents it as
`default: -1`, but that default is not auto-applied by every client — omitting
it can surface a live, verbatim error: `ILLEGAL_QUERY_PARAMETER_VALUE: Illegal
value for query parameter 'minorVersion': ''`. This bites `create_dashboard`
too (same parameter, same fix).

**Exact field shapes live in `schemas/edit-dashboard/`, split per operation.**
The tables below cover behavior and gotchas, not every field — for the
authoritative required/optional fields, enum values, and a worked example for
whichever operation(s) you're about to call, Read the matching
`schemas/edit-dashboard/<operation>.json` (e.g. `upsert_metric_widget.json`,
`place_widget_on_page.json`). The envelope itself (`dashboardIdOrApiName` /
`autosave` / `operations` / `minorVersion`) is
`schemas/edit-dashboard/_envelope.json`. Only read the file(s) for the
operation(s) in your batch — don't load the whole directory.

**Response shape.** Double-wrapped like several other dashboard tools:
`{"defaultExc": "<stringified JSON>", "responseCode": <number>}` — parse
`JSON.parse(response.defaultExc)` to get the dashboard body. A successful batch
returns `responseCode: 201` with the current (possibly still-draft) dashboard
state echoed back, including every widget/page the batch touched.

**Read-back quirk on text content.** Each Quill-delta content op you send is
echoed back with an extra `"rules": []` field appended, even though you never
sent one — harmless, but don't be surprised reading it back.

## 2. Operation-type reference

Every operation is one item in `operations`, selected by its `operation` field.
The **Schema** column is the file under `schemas/edit-dashboard/` with that
operation's exact required/optional fields and a worked example.

| Operation | Purpose | Sharpest constraint | Schema |
|---|---|---|---|
| `upsert_text_widget` | Create or fully replace a rich-text widget, Quill-delta `parameters.content` | No `source` — text has no data reference. | `upsert_text_widget.json` |
| `upsert_button_widget` | Create or fully replace a button widget | `parameters.text` is the caption; no `source`. | `upsert_button_widget.json` |
| `upsert_container_widget` | Create or fully replace a layout-grouping widget | Styling under `parameters.widgetStyle` (fill/border **and** an optional `backgroundSource` image asset + `widgetStyle.background` scale/alignment/opacity). | `upsert_container_widget.json` |
| `upsert_filter_widget` | Create or fully replace a per-widget filter | `parameters.filterOption.dataType` is a **capitalized enum**: `Text`/`Boolean`/`Geo`/`Date`/`DateTime`/`Number`/`Currency`/`Percentage`. Any other value (e.g. lowercase, or a raw JSON type) is rejected at render with `"Unsupported data type for filter"`. `parameters.isLabelHidden` is required at execution for `viewType: list`/`listcard` (not used by `toggle`). | `upsert_filter_widget.json` |
| `upsert_parameter_widget` | Create or fully replace a dashboard parameter | `parameters.parameterOption.dataType` is **lowercase**: `text`/`number`/`date`/`boolean`/`percentage` — a different casing convention than the filter widget's `dataType` above; don't copy one into the other. `parameters.isLabelHidden` is required at execution for `viewType: list`/`listcard`; optional for `input`/`inputcard`. | `upsert_parameter_widget.json` |
| `upsert_visualization_widget` | Create or fully replace a saved-viz tile | `source: {id, name}` + `parameters: {legendPosition, shareState}` — the full field set this operation exposes. | `upsert_visualization_widget.json` |
| `upsert_metric_widget` | Create or fully replace an SDM metric card | `parameters.metricOption: {sdmId, sdmApiName, showForecast?}`; `source` optionally references the metric. | `upsert_metric_widget.json` |
| `upsert_navigation_widget` | Create or fully replace an in-dashboard page nav | **Gated pilot type** — persisting (via `save_dashboard` or batch `autosave: true`) a dashboard holding one fails with `ACCESS_DENIED` unless the org has the navigation-widget pilot enabled. `parameters.navigationItems` is the ordered destination list; an empty/omitted list is just an empty nav bar. | `upsert_navigation_widget.json` |
| `place_widget_on_page` | Place an already-defined widget on a page | `placement.name` references the widget **by its `widget.name` key** — see §3. | `place_widget_on_page.json` |
| `remove_widget_from_page` | Unplace a widget from one page | Removes the placement only, leaves the definition behind (orphaned). Use this only for unplace-and-keep; for a full delete use `remove_widget_from_dashboard` below alone — it removes the definition and every placement in one step, no unplace needed first. See §6. | `remove_widget_from_page.json` |
| `remove_widget_from_dashboard` | Fully delete a widget — its definition **and** every placement across every page, in one step | Takes a bare `widgetName` string (not a `placement` object); source it from `render_dashboard` or an earlier upsert in this same draft/batch — never invent it. See §6. | `remove_widget_from_dashboard.json` |
| `move_widget_to_page` | Move a widget to a different page | Give the full target `placement` (name + coordinates) on the destination page. | `move_widget_to_page.json` |
| `move_widget` | Reposition a widget on its current page | New coordinates on the same page. | `move_widget.json` |
| `add_page` | Add a page to a layout | Keep the `page_N` sequence contiguous; `layoutName` optional (defaults to the first layout). | `add_page.json` |
| `rename_page` | Relabel an existing page | Identify by `page.name`, set the new `page.label`. | `rename_page.json` |
| `delete_page` | Delete a page | Identify by `page.name`. | `delete_page.json` |
| `save_dashboard` | Persist | Standalone: commits whatever's already staged. In a mixed batch: persists after the other operations in that batch succeed. `dashboardIdOrApiName` optional here — defaults to the batch's own dashboard. See §5. | `save_dashboard.json` |
| `undo` | Revert | Standalone: reverts the last staged change. In a mixed batch: cancels every operation in that batch. See §5. | `undo.json` |
| `discard_dashboard` | Drop the staged draft | Standalone: discards the whole staged draft. In a mixed batch: ignores every other operation in that batch — only the discard runs. See §5. | `discard_dashboard.json` |

All paths above are relative to `schemas/edit-dashboard/`.

**Every widget also accepts optional `actions` and `dynamicTokens`** (sibling
fields to `parameters`, identical shape across all 8 `upsert_*_widget` ops).
`actions` are click/select interactions — navigate (to a page, dashboard, URL,
or a metric's details), run a flow, set a parameter, set a filter, or fire a
record action. `dynamicTokens` are named dynamic value bindings referenced
elsewhere on the widget (e.g. from text content or a metric's `tokenSpec`).
Both are fully optional; exact shape (all 5 action types, `DynamicToken`) is in
`schemas/edit-dashboard/_shared-widget-fields.json`, alongside the style
blocks (`WidgetStyle`, `ButtonStyle`, …) and `receiveFilterSource`/
`receiveParameterSource` shapes that several `parameters` blocks below
reference.

## 3. Widget identity — `widget.name` and `widget.id`

There is no more a separate "create" vs. "edit" operation family. Every
`upsert_*_widget` call is a **complete definition** of the widget (omitted
fields are dropped, even on a replace) and is disambiguated by two nested
fields inside `widget`, not a sibling field:

- `widget.name` — the widget's stable key. Always required. On a replace it
  must match the name of the widget you're replacing.
- `widget.id` — **omit to create** a new widget. **Include to fully replace**
  an existing *persisted* widget (`widget.name`/`widget.type` must also match
  it). **Never invent this value** — only pass an `id` you actually read back
  from the dashboard. An **unsaved draft** widget has no `id` yet; replace it
  by matching `widget.name` alone, without an `id`.

**Call `render_dashboard` before replacing a persisted widget** — the tool's
current description names this explicitly as the pre-replace (and
pre-delete, see §6) read step, to fetch the widget's real `id`/`widgetName`
rather than guessing one. Verified live (2026-09-13): `render_dashboard` and
`get_dashboard` are two distinct, both-live tools, not aliases of one another —
`render_dashboard` bundles referenced viz/SDM assets and honors `showDraft`;
`get_dashboard` returns flat metadata only, with no such flags. Either can
source the id/`widgetName` for a replace/delete; prefer `render_dashboard` if
you also need to see the current staged draft (`get_dashboard` will not show
it).

Page/placement ops (`place_widget_on_page`, `remove_widget_from_page`,
`move_widget`, `move_widget_to_page`) still identify the widget by
`placement.name` — a third, separate location from `widget.name`/`widget.id`.
Keep widget names unique within the dashboard across all operations in a
batch, and don't confuse `placement.name` with `widget.id`.

## 4. Grid placement

Same conventions as dashboard creation (`dashboard-authoring.md` §2): **48
columns**, `rowHeight 20`, `maxWidth 1200`, **1-based** row/column (row 1,
column 1 is the top-left cell — NOT 0-based like the bulk-create `layouts`
shape on `create_dashboard`). `placement` = `{name, row, column, rowspan,
colspan}`.

**The target dashboard must already have a layout.** `add_page` /
`place_widget_on_page` operate *within* an existing layout — they do not create
the first one. Verified live (2026-08-31): a `create_dashboard` done with the
minimal-create pattern `layouts: []` yields a dashboard with **no layout at
all**, and the next `edit_dashboard` `add_page` fails with `INVALID_INPUT:
"Dashboard has no layout to add the page to"`. Seed the first page in the
`create_dashboard` `layouts` block up front — one layout carrying an (empty)
`page_1` (with its required `style` + `columnCount`) — then `edit_dashboard`
builds/places into it. Only pass `layouts: []` when you will not immediately
edit the dashboard.

## 5. Draft vs. persist

`autosave` is now a **single top-level, batch-wide** field (previously it was
set per-operation — if you see per-operation `autosave` anywhere, it's stale).
The following draft/staging mechanics were verified live on 2026-08-30 against
the *previous* (`build_*`/`edit_widget`) shape of this tool and describe
behavior that should still hold, but haven't been re-verified against the
current `upsert_*` shape:

- Leaving `autosave` unset (or `false`) on a batch stages the change as a
  **draft** — the response echoes the would-be dashboard state (that's the
  preview to show the user), but the dashboard read tool immediately after
  shows the dashboard **unchanged** (`widgets`/`layouts`/`lastModifiedDate` all
  the same as before the batch).
- The staged draft **accumulates** across multiple `edit_dashboard` calls on
  the same dashboard — a second draft-only batch's response included a widget
  defined in an earlier, still-unsaved batch, even though the read tool showed
  neither in between. Treat the draft as one running staging area per
  dashboard, not scoped to a single call.
- A successful `save_dashboard` persists the full accumulated draft:
  `lastModifiedDate` advances, and every staged widget gets server-assigned
  `id`s it didn't have as a draft.
- `undo` reverts the **last staged, unsaved** change — it has nothing to act on
  after a save: `RESOURCE_NOT_FOUND: "No staged draft to undo for dashboard
  <name>"`. `discard_dashboard` drops the whole staged draft the same way.

**Behavioral change from the tool's current description** (not yet
independently re-verified live): `save_dashboard`, `undo`, and
`discard_dashboard` are **no longer required to be the sole operation in a
batch**. Per the tool description:

- `save_dashboard` in a batch with other operations persists once, after those
  other operations succeed; standalone, it commits whatever draft was already
  staged.
- `undo` in a mixed batch **cancels all of that batch's incoming operations**
  (nothing else in the batch takes effect); standalone, it reverts the last
  staged change as before.
- `discard_dashboard` in a mixed batch **ignores all other operations in that
  batch** (only the discard runs); standalone, it discards the whole staged
  draft as before.
- The top-level `autosave` flag is ignored whenever one of these three control
  operations is present — they determine the outcome instead.

If you actually observe different behavior live, trust the live server over
this doc and flag it for a doc update.

**Never call `save_dashboard` automatically.** Show the draft, ask, and only
save on the user's explicit confirmation given *after* seeing it — even if the
original request already said "save it" in the same message as the edit (same
discipline as `edit_visualization` → `update_visualization`,
`edit-visualization.md` §8).

## 6. Deleting a widget — `remove_widget_from_dashboard`

Two distinct operations, easy to conflate:

- **`remove_widget_from_page`** only removes the widget's placement from one
  page's `widgets` array — the widget's definition stays behind, live, in the
  dashboard's top-level `widgets` map, now orphaned (unplaced on any page).
  Verified: after `remove_widget_from_page` + a save, the dashboard read tool
  showed the page's widget list empty but the widget still present, fully
  defined, under `widgets`.
- **`remove_widget_from_dashboard`** is the true delete: definition *and*
  every placement across every page, in one operation. Its only field is a
  bare `widgetName` string (not a `placement` object) — source it the same way
  as `widget.name` elsewhere: read it back via `render_dashboard`, or reuse
  the `widget.name` you supplied to an earlier `upsert_*_widget` in this same
  draft/batch. Never invent it. Schema: `remove_widget_from_dashboard.json`.

Like every other operation, `remove_widget_from_dashboard` stages into the
draft by default — it isn't persisted until a `save_dashboard` (or top-level
`autosave: true`) commits it (§5). This also closes the global-filter-removal
gap noted in `dashboard-authoring.md` §5: a global filter is a widget under
the hood, so `remove_widget_from_dashboard` fully removes one.

## 7. Gotchas summary

| Gotcha | Rule |
|---|---|
| Omitting `minorVersion` | Client-visible `ILLEGAL_QUERY_PARAMETER_VALUE` on an empty value — always send `minorVersion: -1` explicitly |
| Widget identity | `widget.name` always identifies the widget; add `widget.id` only to replace a *persisted* widget (never invent it); page ops use a third, separate `placement.name` — see §3 |
| `autosave` location | Batch-wide, top-level field now — NOT per-operation. Ignored when `save_dashboard`/`undo`/`discard_dashboard` is present in the batch |
| Upsert without place | An `upsert_*_widget` only defines a widget; it renders nowhere until `place_widget_on_page` in the same (or a later, pre-save) batch |
| `add_page`/place on a layout-less dashboard | Fails `INVALID_INPUT: "Dashboard has no layout to add the page to"` — a `create_dashboard` with `layouts: []` has no layout; seed `page_1` in the create `layouts` block before editing (see §4) |
| `save_dashboard`/`undo`/`discard_dashboard` in a mixed batch | No longer rejected — each has defined mixed-batch behavior now (§5); this supersedes an older "must be the only operation" rule |
| Draft state | Stages and **accumulates** across calls; the dashboard read tool does not reflect it; only the `edit_dashboard` response itself previews it |
| `undo` after a save | `RESOURCE_NOT_FOUND: "No staged draft to undo for dashboard <name>"` — nothing to revert once persisted |
| Deleting a widget | `remove_widget_from_page` only unplaces (orphans the definition); `remove_widget_from_dashboard` (bare `widgetName`) deletes the definition + every placement in one step — see §6 |
| `upsert_navigation_widget` | Gated pilot — persisting a dashboard holding one fails `ACCESS_DENIED` without the pilot enabled |
| `upsert_filter_widget` vs. `upsert_parameter_widget` `dataType` casing | Filter: capitalized enum (`Text`, `Date`, …); Parameter: lowercase (`text`, `date`, …) — do not cross-copy |
| `isLabelHidden` | Required at execution for filter/parameter widgets with `viewType: list`/`listcard`; not used by filter `toggle`; optional for parameter `input`/`inputcard` |
| `upsert_filter_widget`/`upsert_parameter_widget` `parameters` shape | `oneOf` keyed by `viewType` — send only the fields for your chosen `viewType` (`list`/`listcard`/`toggle` for filter; also `input`/`inputcard` for parameter); mixing another `viewType`'s fields in is rejected |
| Response wrapping | `edit_dashboard` double-wraps like `delete_dashboard` (`{defaultExc, responseCode}`) — `create_dashboard`, observed live, does not |
| Text-content read-back | Server appends `"rules": []` to each Quill-delta op you sent, even if you didn't include one |
| `render_dashboard` vs. `get_dashboard` | Both are live, distinct tools (verified 2026-09-13) — not aliases. `render_dashboard` is the pre-replace/pre-delete read step (fetch the real `id`/`widgetName`) and honors `showDraft`; `get_dashboard` returns flat metadata only and never shows a staged draft |
| `save_dashboard`'s `dashboardIdOrApiName` | Optional on this one operation — defaults to the dashboard the batch already targets; only pass it to target a different dashboard |
