# Task: Edit an existing dashboard

Modify a dashboard that already exists — add/edit/move/remove a widget, or
add/rename/delete a page — via the atomic `edit_dashboard` batch tool, and only
persist the change on explicit request. For building a brand-new dashboard, use
`build-dashboard.md` instead. Entry point 20 ("add/edit a widget on an existing
dashboard" — see `build-dashboard.md`'s entry-point list).

## Gates (assert before any tool call) → `../shared-gates.md`

Required: **G1** · Conditional: **G3** (◐, only if placing a viz/metric widget
whose `id`/apiName you have not read back this session) · **G8** (◐, only if the
edit changes the narrative structure — e.g. adding a new KPI/chart — not a pure
reposition/rename)

- **G1** (router-asserted): a `mcp__tableau-next-*__` tool must be connected.
- **Tool names are written bare** — invoke each under your client's name for that `tableau-next-*` server tool (`shared-gates.md`).
- **No G2/G7 by default.** Repositioning, renaming, or removing an
  already-placed widget mutates layout, not data — the data-presence and
  query-returns-real-data gates don't re-apply. They DO apply transitively when
  the edit places a **new** viz/metric widget: that widget's underlying query
  must have returned real rows first (same rule as `build-dashboard.md`).
- **G8** (◐): reposition-only edits don't need a restated narrative; adding a
  widget that changes the story (a new KPI, a new breakdown) does — confirm it
  still fits the KPIs → trends → breakdowns → correlations order.

## Steps

The operation-type table, every `upsert_*_widget` shape, the widget-identity
rule, grid conventions, and draft-vs-persist mechanics are in
**`../edit-dashboard.md`**.

- **Before building a payload, Read the operation's schema file.**
  `../edit-dashboard.md` §2's table names the exact
  `../schemas/edit-dashboard/<operation>.json` for whichever operation(s) you're
  about to send (e.g. `upsert_metric_widget.json`, `move_widget.json`) — it has
  the authoritative required/optional fields, enums, and a worked example. Read
  only the file(s) for this batch, not the whole directory.
- **Always pass `minorVersion: -1` explicitly** on every `edit_dashboard` call —
  the schema shows it as a default, but it is not auto-applied; omitting it can
  surface `ILLEGAL_QUERY_PARAMETER_VALUE: Illegal value for query parameter
  'minorVersion': ''`.
- **Upsert → place, same discipline as viz creation.** An `upsert_*_widget`
  operation only *defines* a widget (create or full replace) — it renders
  nowhere until paired with `place_widget_on_page` (same batch, or a later one
  before you save) unless it's replacing an already-placed widget. Never
  define a new widget without also placing it.
- **Widget identity.** `widget.name` always identifies the widget inside an
  `upsert_*_widget` call; add `widget.id` only to fully replace an already
  *persisted* widget (never invent this value — read it back first, e.g. via
  `render_dashboard`/`get_dashboard`), and omit it to create a new widget. An
  unsaved draft widget has no `id` — replace it by `widget.name` alone. Page
  ops (`place_widget_on_page`/`remove_widget_from_page`/`move_widget`/
  `move_widget_to_page`) use a third, separate field: `placement.name`. Full
  detail: `../edit-dashboard.md` §3.
- **`autosave` is now top-level and batch-wide** (a sibling of `operations`,
  not a per-operation field). Leave it unset (default `false`) to stage a
  draft. The batch response IS the preview — show it, then ask before
  persisting. Drafts **accumulate** across successive `edit_dashboard` calls on
  the same dashboard until saved/discarded; the dashboard read tool will NOT
  show a staged draft.
- **Persist only on explicit confirmation.** `save_dashboard` may now appear
  standalone (commits whatever draft is already staged) or after other
  mutations in the same batch (persists once they succeed) — it's no longer
  required to be the batch's sole operation. Regardless of batch shape, only
  send it after the user confirms **having seen** the draft — even if the
  original request already said "save it" in the same message as the edit.
- **To revert an unsaved draft:** `undo` (standalone: reverts the last staged
  change; in a mixed batch: cancels every operation in that batch) or
  `discard_dashboard` (standalone: drops the whole staged draft; in a mixed
  batch: ignores every other operation in that batch). `undo` only works while
  a draft is staged — after a save there's nothing to undo (`RESOURCE_NOT_FOUND:
  "No staged draft to undo for dashboard <name>"`).
- **To fully delete a widget (not just unplace it):** use
  `remove_widget_from_dashboard` — a bare `widgetName`, deletes the definition
  and every placement across every page in one operation, in the same batch as
  any other `edit_dashboard` operations. `remove_widget_from_page` alone only
  removes the page placement, leaving an orphaned widget definition in the
  dashboard's `widgets` map — see `edit-dashboard.md` §6.
- No existing dashboard to edit? Route to **`build-dashboard.md`** instead.
