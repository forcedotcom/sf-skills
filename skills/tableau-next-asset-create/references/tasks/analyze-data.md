# Task: Analyze data (natural-language question)

Answer an interpretive analytical question through `analyze_data`: breakdowns,
rankings, trends, and comparisons. The Analytics Agent picks the SDM — you do
not need to pin one. Do **not** use this for a plain count, total, or scalar
("how many orders", "what is total revenue") — that is `query-model.md` /
`run_semantic_query`, even when no model was named.

## Gates (assert before any tool call) → `../shared-gates.md`

Required: **G1** · Conditional: **G6** (◐, if the returned numbers' grain is unclear)

- **G1** (router-asserted): a `mcp__tableau-next-*__` tool must be connected.
- **Tool names are written bare** — invoke each under your client's name for that
  `tableau-next-*` server tool (`shared-gates.md`).
- **G6** (◐): if additivity/grain of the answer isn't understood, profile first
  (`../data-understanding.md`) — do not re-ingest.

## When **not** to use this tool

- **Figures** (count, total, scalar, "give / run me the numbers") →
  `query-model.md`. Discover the SDM with `list_semantic_models` if unnamed.
- **Named model + structured table** ("query Sales_Model for revenue by region",
  explicit `run_semantic_query`) → `query-model.md`.
- **Greenfield** — nothing modeled yet / CSV / "build a dashboard" →
  `build-end-to-end.md`.
- **Metadata discovery** (list SDMs, dashboards, fields, relationships) →
  `list_*` / `get_*`, not `analyze_data`.
- **Ongoing monitor** ("alert me when…", change/list/delete my alerts) →
  `manage-alert.md`. This tool answers once; it does not persist a watch.

## Steps

1. Call `analyze_data` with the user's question as the utterance.
2. **Do not pin `targetEntityNameOrId` or `targetEntityType`** unless the
   user explicitly named a specific SDM / data source. `targetEntityType` is
   `sdm` **only** when pinning.
3. If a complex question fails, break it into simpler questions and reason
   client-side.
4. **This tool does NOT automatically render visualizations.** If `vizMetadata`
   is returned and the user wants to see the chart, explicitly call
   `render_visualization` with that object. (Opposite of `edit_visualization`,
   which renders inline and must **not** be chased with `render_visualization`.)
5. Long-running / async: a slow answer polls in the background (up to several
   minutes) rather than timing out — wait; do not treat silence as failure.

This is a read/analysis entry point — it does not model, enrich, or persist a
chart. If the answer needs a saved visualization, continue to `create-viz.md`.
