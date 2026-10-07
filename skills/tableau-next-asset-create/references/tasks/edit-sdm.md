# Task: Edit the semantic model — add a raw object / field / join / logical view

Create a model, or add a **raw** data object, dimension, measure, relationship,
logical view, or parameter to one. (For **calculated** dimensions/measures/metrics, use
`enrich-model.md`.) Entry points 7, 8, 9, 10.

## Gates (assert before any tool call) → `../shared-gates.md`

This guide serves five mutating intents; required gates differ per intent:

- **Create new model (entry 7):** Required **G1, G2, G5** · Conditional **G6**
  (◐). Nested explicit fields mean you control apiNames at create; still
  light-confirm with `list_*` before relationships (G3).
- **Add data object (entry 8):** Required **G1, G2, G3, G5** · Conditional **G4**
  (◐, once ≥2 objects — no islands), **G6** (◐).
- **Add dimension / measure (entry 9):** Required **G1, G2, G3, G5** ·
  Conditional **G6** (◐). Use this only to add a *single extra field* to an
  already-bound object — not for the initial bind.
- **Add relationship / join (entry 10):** Required **G1, G2, G3, G4, G7**. A raw
  join creates no metadata, so G5 does not apply.
- **Add logical view (HardJoin / Union / CustomSQL):** Required **G1, G2, G3, G5**.
  Field apiNames are assigned at first save — read them back with
  `get_semantic_model_logical_view` before joining. `Hierarchy` is **not
  currently supported via MCP**.

- **G1** (router-asserted): a `mcp__tableau-next-*__` tool must be connected.
- **Tool names are written bare** — invoke each under your client's name for that `tableau-next-*` server tool (`shared-gates.md`).
- **G2:** COUNT(*) the source object before adding it — never add a 0-row object.
- **G3:** read apiNames back with `list_*` before writing any relationship criteria
  or field reference (semantic apiName + `leftFieldType: "TableField"`). For a
  logical view, read assigned names from `get_semantic_model_logical_view`.
- **G4:** once ≥2 objects exist, no islands — ◐ when adding an object (entry 8),
  **required** when adding a relationship (entry 10).
- **G5** (create model / add object / add field / add logical view — not raw
  joins): set the required metadata at creation and prefer **nested explicit
  fields** on `create_semantic_model` / `add_semantic_model_data_object`
  (`shouldIncludeAllFields: false`) — full metadata list in `shared-gates.md`
  G5. CustomSQL **requires** explicit fields (`shouldIncludeAllFields` does
  not satisfy validation).
- **G7** (add-relationship): after adding, confirm the join key matches real rows
  with a JOIN row-count — ~0 rows = broken.
- **G6** (◐): if a column's role/type isn't understood, profile first
  (`../data-understanding.md`) — but do NOT re-run Step 0 ingest on a pre-existing
  model.

## Steps

Tool-by-tool input shapes, suffix rules, the apiName-mutation gotcha, and
logical-view shapes are in **`../sdm-tool-reference.md`**; the numbered spine
(create model with nested fields, add objects, add relationships) is
`../build-workflow.md` Steps 4–6.

- **Create model** — `create_semantic_model` + `update_semantic_model` (Step 4).
  Nested `semanticDataObjects[].label` is REQUIRED. Bind fields **in this
  call**: `shouldIncludeAllFields: false` plus explicit
  `semanticDimensions[]` / `semanticMeasurements[]` (fetch fields first;
  include join keys). Relationships, metrics, calcs, parameters, and logical
  views are still post-create `add_semantic_model_*`. **Extend a Model** uses
  the same tool with `baseModels[]` of `{ "apiName": "<existing SDM>" }` in
  the same `dataspace` (typical label `"<Base Label> (Extended)"`; payload in
  **`../sdm-tool-reference.md`**). Prefer **anchor-plus-nested-fields create**,
  then incremental `add_semantic_model_data_object` with the same nested
  arrays. If a table has no FK to the anchor, add the intermediate first,
  then bridge through it. Bulk-create timeout (`postSemanticModelCollection`)
  may still persist the SDM — wait ~30s and `list_semantic_models` before
  retrying (naive retry → Unique constraint violated). Optional sanity check:
  `get_semantic_model` with `includeModelContent=true`.
- **Add data object** — `add_semantic_model_data_object` (`dataObjectType:"Dmo"`,
  name `*__dlm`) with nested `semanticDimensions[]` /
  `semanticMeasurements[]` (`shouldIncludeAllFields: false`). Omit
  `primaryNameField` at create (G5 known gap).
- **Add dimension / measure** — `add_semantic_model_dimension` / `_measure`
  only for a *single extra field* on an already-bound object. Do **not** use
  these for the initial bind (that is the nested create / add-data-object
  path above).
- **Add relationship / join** — `add_semantic_model_relationship`
  (`leftFieldType:"TableField"`, `joinType:"Auto"`, `label` required even though
  schema marks it optional). Validate the join with a real JOIN row-count (G7).
- **Add / update a parameter** — post-create only (`add_semantic_model_parameter`;
  cannot be created inline on `create_semantic_model`). Updates are PUT, not
  PATCH — re-send `label`/`type`/`dataType`/`defaultValue` even for a
  description-only change. `List` needs `values` and a matching `defaultValue`.
  Shapes: **`../sdm-tool-reference.md`** (Parameters).
- **Add logical view** — `add_semantic_model_logical_view`. Enumerate existing
  views via `get_semantic_model` (`semanticLogicalViews[]`) first. `label` is
  required. Rules and reference payloads: **`../sdm-tool-reference.md`**
  (Logical views).
  - **HardJoin 3-step:** objects only → GET assigned apiNames → relationship
    with LV `joinType` `Left`/`Right`/`Inner`/`Full` (**not** `Auto`). Prefix
    LV object apiNames `LV_`.
  - **Union:** exactly one `semanticUnions[]` entry. **Do NOT pass
    `"semanticViewTypeEnum": "Union"`**. Mapped-field apiNames are
    **locally-scoped** on that ULV object.
  - **CustomSQL:** `customSQLV2`; exactly one `CustomSQL` data object with
    **explicit** dims/measures.
  - **Update (PATCH):** `update_semantic_model_logical_view` only persists
    `description`, `filterLogic`, and `filters`. Empty body `{}` is rejected.
    GET via `get_semantic_model_logical_view` first before replacing filters.
    **Label is silently ignored** (API accepts it, never persists). SQL or
    view-type changes require delete-and-recreate — do not treat a 2xx PATCH
    as a successful rename or SQL edit.
  To remove a logical view, see **`../sdm-tool-reference.md`** (Deleting) —
  a blocked LV delete is HTTP 500 `DEPENDENCY_EXISTS` (do not retry).

Do NOT re-profile from scratch or re-ingest on an already-built model — assume the
model exists and touch only what the request names.
