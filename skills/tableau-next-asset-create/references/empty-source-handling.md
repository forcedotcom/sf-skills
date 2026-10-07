# Empty Source Handling

How to detect empty source objects and what to tell the user. Load this when
a *discovered* candidate source returns zero rows or zero fields in Step 2.
(A DMO you just created and mapped in this flow is not a *discovered* empty
source — see the self-created mapping gate below.)

## Two different "empty" conditions

They look similar in the builder UI but behave oppositely.

### Empty of rows (fields present, 0 rows)

- The object exposes dimensions/measures, so it CAN be added and joined.
- Every query against it returns nothing → blank visualizations.
- Example from the real incident: `AccountHome` had 66 fields and 0 rows. A
  dashboard built on it rendered "No results to show" on every widget. Adding
  a relationship did not help — the table itself was empty.

Detection (run the count against the source table, suffixed by type — `__dll`
DLO, `__dlm` DMO, `__dlc` CIO):

```sql
SELECT COUNT(*) AS n FROM <name>__dll   -- DLO; use __dlm for a DMO, __dlc for a CIO. returns 0
```

**A DMO you did not create is empty until its mapping has rows.** For an
*externally discovered* candidate, `hasExternalDataLakeObjectMappings: false`
and `SELECT COUNT(*) FROM <dmo>__dlm` returning 0 mean do not build on it —
gate on row count just like any other discovered source (G2).

**Self-created mapping (this flow).** When you just created the DMO and mapped
it yourself (`create_data_model_object` then `create_dlo_to_dmo_mapping`):

- **`get_dlo_to_dmo_mapping_status` `ACTIVE` is not query-ready.** It means
  mapping metadata deployed; it does **not** mean `<dmo>__dlm` exists. Use
  that tool to inspect field mappings and to detect `ERROR` / `INACTIVE`.
- **Authoritative gate:** poll `run_query` `SELECT 1 FROM <dmo>__dlm LIMIT 1`
  (or `SELECT COUNT(*)`). `42P01` / "table does not exist" = NOT-READY —
  keep polling. Any success, **including `COUNT = 0`**, = READY — proceed
  to the SDM. Do **not** treat that `COUNT = 0` as a discovered empty source
  (G2). Do **not** proceed to SDM while the table is still missing.
- Also query the mapped fields — a bad/partial field mapping often surfaces
  only when that field is selected.
- Only fall back to querying the raw DLO if a query through the semantic
  model itself, later (at the viz/query stage), fails with table-not-found.

### Empty of fields (unmaterialized)

- The object exposes **zero** semantic dimensions/measures.
- It cannot be joined at all — a relationship criterion needs a named field on
  each side, and there is none.
- The underlying Data Cloud table may not even exist yet (`run_query` returns
  `table "ssot__Activity__dlm" does not exist`).
- Example: `ssot__Activity` and `ssot__ActivityParticipant` were unmaterialized
  standard DMOs with 0 fields.

Detection: `list_semantic_model_data_objects` shows empty
`semanticDimensions` / `semanticMeasurements`, or `run_query` errors that the
table does not exist.

## Decision matrix

| Candidate state | Build on it? | Can be joined? |
|---|---|---|
| rows > 0, fields > 0 | Yes | Yes |
| rows = 0, fields > 0 (discovered) | No (would render blank) | Yes, but pointless |
| fields = 0 / `table does not exist` (discovered) | No | No |
| self-created + mapped this flow; `42P01` / table missing | Not yet — keep polling `run_query` | n/a |
| self-created + mapped this flow; `run_query` succeeds (`COUNT = 0` ok) | Yes — table exists; proceed to SDM | n/a |

When the user's request matches both a populated source and an empty one,
choose the populated source — regardless of whether the empty one is a more
"canonical" DMO.

## What to tell the user

Do not silently build on empty sources or silently drop them. Surface the
finding so the user can fix the data or pick a different source.

When the only matching sources are empty:

> The objects that match your request — `Activity` and `ActivityParticipant` —
> have no data (0 rows; `Activity` appears unmaterialized in Data Cloud). A
> semantic model built on them would render empty visualizations. I can either
> (a) build the model on a populated source instead, or (b) hold until those
> objects are populated. Which would you prefer?

When some sources are populated and some are empty:

> I built the model on the populated objects (`Account`, `Opportunities`). I
> left out `Activity` and `ActivityParticipant` because they have no data
> rows yet — adding them would not contribute to any visualization. Say the
> word and I'll wire them in once they're populated.

## Why field count misleads

The Tableau Next builder shows a parenthetical count next to each object
(e.g. "Account Home (66)"). That is the number of **fields**, not **rows**. An
object with a high field count can have zero rows. Always confirm rows with
`run_query SELECT COUNT(*)`; never infer data presence from the field count.
Exception: a DMO you just created and mapped in this flow — poll `run_query`
until the `__dlm` table exists (`COUNT = 0` is READY; `42P01` is not).
`get_dlo_to_dmo_mapping_status` `ACTIVE` is not that gate.
