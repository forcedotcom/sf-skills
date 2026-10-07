# Task: Edit an existing visualization

Modify a visualization that already exists — add/remove/replace a shelf field,
filter, forecast, sort, mark encoding, mark type, dual axis, reference line, table
calc, or axis title — and, only on explicit request, save the result. For building a
brand-new chart, use `create-viz.md` instead.

## Gates (assert before any tool call) → `../shared-gates.md`

Required: **G1** · Conditional: **G3** (◐, only if an operation references a field/
apiName you have not read back this session — e.g. adding a brand-new shelf field)

- **G1** (router-asserted): a `mcp__tableau-next-*__` tool must be connected.
- **Tool names are written bare** — invoke each under your client's name for that `tableau-next-*` server tool (`shared-gates.md`).
- **No G2/G7/G8 by default.** You are mutating an already-created, already-verified
  visualization — this is not a fresh build from a new query, so the data-presence,
  query-returns-real-data, and narrative-design gates that gate `create_visualization`
  do not re-apply here.

## Steps

The `editOperations` operation-type reference, filter-operator rules, the
`{model:}`/`{expression:}` decision rule, and the reference-line `field.function` vs
`line.function` disambiguation are in **`../edit-visualization.md`**.

- Obtain the current `visualizationId` — from `get_visualization`, or from a
  prior `edit_visualization`/`update_visualization` call. Do **not** pass a
  `visualizationMetadata` blob into `edit_visualization` or `update_visualization`.
- Build the `editOperations` array per `../edit-visualization.md`; JSON-stringify the
  whole array into a single string — never pass a raw array.
- Call `edit_visualization` with `visualizationId` + that string. Its result
  renders inline automatically — do **not** call `render_visualization` on it.
- **Never call `update_visualization` automatically.** After `edit_visualization`
  renders the preview, ask the user whether to save; call `update_visualization`
  only on their confirmation *after seeing that preview*, passing **only**
  `visualizationId` (the server persists its working state for that id). This
  applies even if the user's original request already said to save it — the
  edit still renders a preview first, and only a confirmation given after that
  preview authorizes the persist.
- No existing chart to edit? Route to **`create-viz.md`** instead.
