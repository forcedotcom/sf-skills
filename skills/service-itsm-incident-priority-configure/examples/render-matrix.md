# Rendering the Matrix

Format the rows returned by `SELECT ... FROM ServiceOpPriorityConfig` (via `sf data query --use-tooling-api`) as an aligned Impact × Urgency grid. Use this layout both for the initial "view" operation and for the before/after snapshots around a mutation.

## Input

Tooling SOQL result body (`sf data query --json ...`):

```json
{
  "result": {
    "records": [
      { "Id": "1NHSG00000007374AA", "ReferenceObject": "Incident", "Impact": "High",   "Urgency": "High",   "Priority": "Critical" },
      { "Id": "1NHSG00000007384AA", "ReferenceObject": "Incident", "Impact": "High",   "Urgency": "Medium", "Priority": "High"     },
      { "Id": "1NHSG00000007394AA", "ReferenceObject": "Incident", "Impact": "Medium", "Urgency": "High",   "Priority": "High"     }
    ]
  }
}
```

Row keys are PascalCase (`Id`, `ReferenceObject`, `Impact`, `Urgency`, `Priority`) — these are Tooling SObject field names.

Plus the active picklist values fetched from the Incident describe (used for the axes).

## Output layout

```text
Priority Matrix — Incident   (3 of 9 cells configured)

Impact \ Urgency    High      Medium     Low
------------------------------------------------
High               Critical   High       ·
Medium             High       ·          ·
Low                ·          ·          ·

Configured rows:
  Impact=High     Urgency=High     -> Priority=Critical
  Impact=High     Urgency=Medium   -> Priority=High
  Impact=Medium   Urgency=High     -> Priority=High
```

Layout rules:

- Rows are the entity's `Impact` picklist values, columns are `Urgency` — both ordered as returned by describe (typically High → Medium → Low; do not reorder).
- Fill each cell with the matching row's `Priority`, or `·` if no row exists for that `(Impact, Urgency)` coordinate.
- Total cells expected = `|Impact| × |Urgency|`. Show `<configured>/<total>` in the header — do not hardcode 9.
- After the grid, list configured rows for easy copy/paste when composing a mutation.

## When to render

- **Phase 2** — the view operation and the before-snapshot for any mutation.
- **Phase 5** — after a write, render again as the after-snapshot.

Present both before and after when a mutation ran; users need the diff.
