# Designer-Native UI Section

The Recipe Designer detects old-style `ui` sections (old `position: {x,y}` format, empty `connectors: []`, no `type` on nodes) and shows the "Can't Load the Recipe" repair popup on every open. Always use the Designer-native format below.

## Node type mappings

| Recipe node | UI `type` |
|-------------|-----------|
| `load` | `LOAD_DATASET` |
| `filter` | `FILTER` |
| `join` | `JOIN` |
| `formula` (all chained) | Grouped inside a `TRANSFORM` UI node |
| `extractGrains` | Inside the `AGGREGATE` UI node's inner `graph` |
| `aggregate` | Inside the `AGGREGATE` UI node's inner `graph` |
| `save` | `OUTPUT` |

## Rules for grouping formula nodes into TRANSFORM

- ALL consecutive formula nodes go into a single `TRANSFORM0` UI node.
- The inner `graph` lists every formula node name with `{ "parameters": { "type": "BASE_FORMULA_UI" } }`.
- The inner `connectors` list the formula→formula chain.
- The outer `connectors` only reference UI node names (TRANSFORM0, AGGREGATE0, etc.), never individual internal formula node names.
- Always insert `EXTRACT0` (`extractGrains`) inside the AGGREGATE UI node's `graph`. The aggregate node must source from EXTRACT0, not the last formula node.

## Template (filter → join → 2 formula nodes → aggregate → save)

```json
"ui": {
  "nodes": {
    "LOAD_OPPORTUNITY": { "label": "Opportunity", "type": "LOAD_DATASET", "top": 112, "left": 112, "parameters": { "sampleSize": 2000 } },
    "LOAD_ACCOUNT":     { "label": "Account",     "type": "LOAD_DATASET", "top": 252, "left": 252, "parameters": { "sampleSize": 2000 } },
    "FILTER_CLOSED_WON": { "label": "FILTER_CLOSED_WON", "type": "FILTER", "top": 112, "left": 252 },
    "JOIN_ACCOUNT":      { "label": "JOIN_ACCOUNT",      "type": "JOIN",   "top": 112, "left": 392 },
    "TRANSFORM0": {
      "label": "TRANSFORM0", "type": "TRANSFORM", "top": 112, "left": 532,
      "graph": {
        "COMPUTE_YEAR":  { "parameters": { "type": "BASE_FORMULA_UI" } },
        "COMPUTE_MONTH": { "parameters": { "type": "BASE_FORMULA_UI" } }
      },
      "connectors": [{ "source": "COMPUTE_YEAR", "target": "COMPUTE_MONTH" }]
    },
    "AGGREGATE0": {
      "label": "AGGREGATE0", "type": "AGGREGATE", "top": 112, "left": 672,
      "graph": { "EXTRACT0": null, "AGGREGATE_NODE": null },
      "connectors": [{ "source": "EXTRACT0", "target": "AGGREGATE_NODE" }]
    },
    "OUTPUT_DATASET": { "label": "OUTPUT_DATASET", "type": "OUTPUT", "top": 112, "left": 812 }
  },
  "connectors": [
    { "source": "LOAD_OPPORTUNITY",  "target": "FILTER_CLOSED_WON" },
    { "source": "FILTER_CLOSED_WON", "target": "JOIN_ACCOUNT" },
    { "source": "LOAD_ACCOUNT",      "target": "JOIN_ACCOUNT" },
    { "source": "JOIN_ACCOUNT",      "target": "TRANSFORM0" },
    { "source": "TRANSFORM0",        "target": "AGGREGATE0" },
    { "source": "AGGREGATE0",        "target": "OUTPUT_DATASET" }
  ],
  "hiddenColumns": []
}
```

Also add at the top level of `recipeDefinition`:
- `"runMode": "full"`

Add on load nodes: `"mode": "SYNCED"`, `"preserveCurrencyFields": []`, `"sampleDetails": {"type":"TopN","sortBy":[]}`

Add on save node: `"measuresToCurrencies": []`

Add on aggregate node: `"nodeType": "STANDARD"`, `"pivots": []`
