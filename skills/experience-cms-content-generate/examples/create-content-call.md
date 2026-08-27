# Example `create_cms_content` payload

> **Read this first.** `sfdc_cms__article` and `0ZuKZ00000XXXXXXXX` below are **shape illustrations**, not defaults. The `contentType` FQN must come from `experience-cms-content-type-generate` against the live org — never copy the FQN from this file. The `contentSpaceOrFolderId` value comes from the user's answer to the Step 3 workspace question — never from a local file. A workspace will reject any type it isn't configured to support, so picking an FQN from training data or this example will fail with `"These content type(s) X are not supported by this space"`.

The `experience-cms-content-generate` skill dispatches `create_cms_content` with the user's goal on the **`prompt` channel**. The server-side pipeline (Vibes MC content pipeline) generates and validates the body against the type's schema. The agent generates only the `title` and shapes the payload.

## Example

User asked: *"Draft an article announcing our Q4 product launch — make it about the new analytics dashboard. Cover the problem it solves, three headline features (real-time KPIs, drill-down by segment, export to spreadsheet), availability date, and a call-to-action linking to the product page."*

Assume `experience-cms-content-type-generate` returned `contentTypeFqn: sfdc_cms__article`.

Agent generates only a title from `[USER GOAL]`:

- **Title:** `Q4 Launch — Analytics Dashboard`

Payload:

```json
{
  "inputs": [
    {
      "contentType": "sfdc_cms__article",
      "contentSpaceOrFolderId": "0ZuKZ00000XXXXXXXX",
      "title": "Q4 Launch — Analytics Dashboard",
      "prompt": "Draft an article announcing our Q4 product launch — make it about the new analytics dashboard. Cover the problem it solves, three headline features (real-time KPIs, drill-down by segment, export to spreadsheet), availability date, and a call-to-action linking to the product page."
    }
  ]
}
```

Notes:

- **`title` reflects `[USER GOAL]`.** Not the user's message verbatim — the message was an authoring instruction, not a title.
- **`prompt` is `[USER GOAL]` verbatim.** Do not paraphrase, trim, or reformat — the server-side pipeline parses it directly.
- **No `contentBody` field.** `prompt` and `contentBody` are mutually exclusive; sending both fails. This skill never sends `contentBody`.
- **No client-side pre-flight validation.** The server owns validation.
- Single-element `inputs` array — the skill creates one record per element. **Bulk creation dispatches N separate `create_cms_content` calls in parallel, each with a 1-element `inputs` array** — one call per item is the hard rule (never combine items into a multi-element `inputs` array). See SKILL.md Step 5b and `references/bulk-batching.md`.

### Optional fields

These pass through only when the user explicitly named them:

```json
{
  "inputs": [
    {
      "contentType": "<from-sibling>",
      "contentSpaceOrFolderId": "<from-user-step-3>",
      "title": "<agent-generated>",
      "prompt": "<[USER GOAL] verbatim>",
      "urlName": "q4-launch-analytics-dashboard"
    }
  ]
}
```

### Successful response (abridged)

```json
{
  "outputs": [
    {
      "managedContentId": "20YKZ00000XXXXXXXX",
      "managedContentVersionId": "20XKZ00000XXXXXXXX",
      "managedContentVariantId": "20ZKZ00000XXXXXXXX",
      "contentKey": "MCRT_a1B2c3D4",
      "contentFqn": "sfdc_cms__article",
      "title": "Q4 Launch — Analytics Dashboard",
      "urlName": "q4-launch-analytics-dashboard",
      "apiName": "Q4_Launch_Analytics_Dashboard",
      "contentSpace": { "id": "0ZuKZ00000XXXXXXXX", "label": "Marketing" },
      "createdBy":    { "id": "005KZ00000XXXXXXXX", "name": "Jane Doe" },
      "createdDate":  "2026-11-01T17:42:08.000Z",
      "contentBody":  { "title": "Q4 Launch — Analytics Dashboard", "body": "<h2>…</h2>", "excerpt": "…" }
    }
  ]
}
```

The skill surfaces (at minimum) `title`, `contentKey`, `managedContentId`, `contentFqn`, and `contentSpace.label` — those are what the user needs to find the record again. Response latency is server-side-generation dependent — not guaranteed sub-second like a pure persist path.
