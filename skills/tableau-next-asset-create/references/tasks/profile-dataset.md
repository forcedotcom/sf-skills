# Task: Profile / discover / verify a dataset (read-only diagnostics)

Understand data before modeling it, discover what's available, or triage an empty
source. All read-only — no mutation. Entry points 2, 3, 4, 5, 6.

## Gates (assert before any tool call) → `../shared-gates.md`

This guide serves five read-only intents; required gates differ per intent:

- **Profile / understand dataset (entry 2):** Required **G1, G6** · Conditional
  **G2** (◐, when cardinality/additivity depends on a row count).
- **Infer a large/wide/cryptic flat file's schema (entry 3):** Required **G1,
  G6** — same profiling rule as entry 2, starting with `infer_object_schema` as
  described in `../large-flat-file-handling.md`.
- **Discover data assets (entry 4):** Required **G1**.
- **Verify presence / triage empty (entry 5):** Required **G1, G2** — you must
  `COUNT(*)`; presence is the whole question.
- **Confirm join keys (entry 6):** Required **G1, G2** · Conditional **G3**
  (◐, only if you're about to persist a join with the keys you find).

- **G1** (router-asserted): a `mcp__tableau-next-*__` tool must be connected.
- **Tool names are written bare** — invoke each under your client's name for that `tableau-next-*` server tool (`shared-gates.md`).
- **G6:** profile the five things — grain, field roles, cardinality, additivity,
  date roles (`../data-understanding.md`). This applies over an already-modeled
  dataset too, whenever you don't yet understand what the numbers mean. For a
  large/wide/cryptic flat file, use the infer-first variant (infer fields/types,
  decode the naming grammar, verify one number after ingest —
  `../large-flat-file-handling.md`).
- **G2** (◐): when the ask is "does this source have data?", run `SELECT COUNT(*)`
  — `count>0` usable, `count=0` empty, `does not exist`/`42P01` unmaterialized (a
  distinct case — `../empty-source-handling.md`).

## Steps (read-only — do NOT mutate)

- **Discover sources** — `browse_data_assets` (a label/keyword match is a
  *candidate list*, not the answer; calling convention + gotchas —
  `../sdm-tool-reference.md`).
- **Verify presence / triage empty** — `SELECT COUNT(*)`; distinguish empty from
  unmaterialized per `../empty-source-handling.md`.
- **Confirm join keys** — run a real JOIN row-count between two objects; a key
  matching ~0 rows is as broken as no relationship (this is diagnostic here — the
  persisted join lives in `edit-sdm.md`).
- **Profile** — grain / field roles / cardinality / additivity / date roles
  (`../data-understanding.md`); large/cryptic files → `../large-flat-file-handling.md`.

This guide is diagnostic only. When you move on to *persist* structure, route to
`edit-sdm.md`; to *enrich*, `enrich-model.md`; to *query*, `query-model.md`.
