# MCP Action Integration — Examples & Reference

Two MCP actions provide component discovery and schema retrieval. Call them via `execute_metadata_action`.

## discoverUiComponents

Discovers components available for a page type in the user's org.

**When to call:** Tier 2 discovery — after local scan finds no match.

**Input:**
```json
execute_metadata_action({
  "actionName": "DISCOVER_UI_COMPONENTS",
  "metadataType": "FLEXI_PAGE",
  "parameters": {
    "pageType": "RECORD_PAGE",
    "pageContext": { "entityName": "Account" },
    "searchQuery": "related list"
  }
})
```

**Parameters:**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| pageType | String | Yes | `RECORD_PAGE`, `APP_PAGE`, or `HOME_PAGE` |
| pageContext | JSON | Conditional | Required for RECORD_PAGE: `{"entityName": "ObjectApiName"}` |
| searchQuery | String | No | Natural language search from user intent |

**Output:**
```json
{
  "componentDefinitions": [
    {
      "definition": "lst/dynamicRelatedList",
      "label": "Dynamic Related List",
      "description": "Shows related records...",
      "attributes": [{"name": "parentFieldApiName", "description": "..."}]
    }
  ]
}
```

**Notes:**
- Output uses forward-slash delimiter (`namespace/blockName`), but XML uses colon (`namespace:blockName`)
- Only returns components compatible with the page type and accessible in the org
- May return empty list if no match — proceed to Tier 3

**When multiple components are returned:**
1. **Best-match selection:** If one component clearly matches user intent (label/description aligns with the request), auto-select it
2. **Ambiguous results:** If multiple components could satisfy the request, present the top candidates to the user with their labels and descriptions, and ask which one to use
3. **Refinement:** If results are too broad, refine the `searchQuery` parameter with more specific keywords from user intent and retry once before prompting the user

## getUiComponentSchemas

Retrieves the full property schema for one or more components.

**When to call:** Tier 2 (org-discovered) components only — skip for Tier 1 (local) and Tier 3 (generated) components; read @api properties from source instead.

**Input:**
```json
execute_metadata_action({
  "actionName": "GET_UI_COMPONENT_SCHEMAS",
  "metadataType": "FLEXI_PAGE",
  "parameters": {
    "pageType": "RECORD_PAGE",
    "pageContext": { "entityName": "Account" },
    "componentDefinitions": ["lst/dynamicRelatedList", "flexipage/richText"],
    "includeKnowledge": true
  }
})
```

**Parameters:**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| pageType | String | Yes | `RECORD_PAGE`, `APP_PAGE`, or `HOME_PAGE` |
| pageContext | JSON | Conditional | Required for RECORD_PAGE |
| componentDefinitions | List | Yes | Component FQNs (forward-slash format) |
| includeKnowledge | Boolean | No | Include component guidance text (default: true) |

**Output:**
```json
{
  "componentSchemas": [
    {
      "definition": "lst/dynamicRelatedList",
      "success": true,
      "schema": "{...JSON Schema string...}",
      "knowledge": "Optional guidance text for this component"
    }
  ]
}
```

**Notes:**
- Supports **partial failures** — each component has its own `success` boolean
- On failure: `{"definition": "...", "success": false, "error": "reason"}`
- When a component schema fails, fall through to Step 3 (smart defaults + LLM inference)
- `knowledge` provides platform-curated guidance — use it alongside instructions files
- Component definition format: always `namespace/blockName` (forward-slash)
