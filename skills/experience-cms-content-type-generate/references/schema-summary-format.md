# Step 7.5 — schema summary format

Runs whenever `{fqn, schema}` has been resolved, regardless of source (local, grounding, retrieve, or new-and-deployed) or of `suppressCreateContentPrompt`. The user always sees what the type contains before the workflow ends or hands off. Callers that suppress the trailing prompt (step 8) still get the summary — the summary is informational, not a turn.

## When to run

- Step 1e returned `{fqn, schema}` (existing type reconciled — from local, from grounding, or from `sf project retrieve`).
- Step 7e succeeded (new type created and deployed — the schema is the one just written).
- Step 1e's drift-prompt "Deploy local to org" branch reached 7e.
- **Step 1e's "local only" branch** — BEFORE the `Deploy it? Yes / Cancel` prompt, print the summary of the LOCAL schema so the user sees what they'd be deploying (a local-only bundle is the most likely case to be stale or hand-edited). Header: `Local schema for "<fqn>" (not yet in the org):`.

## When NOT to run

- User picked `Cancel` at any point.
- Step 7b (user answered "No — I'll deploy later") — no resolved schema in the org, nothing to summarize.
- Any error path exited without a resolved `{fqn, schema}`.

## Format — one line + one markdown table

Printed as chat text (NOT inside an `ask_user_tool`):

```text
Content type "<fqn>" is ready. Schema:

| # | API name | Type | Required | Constraints | Title |
|---|---|---|---|---|---|
| 1 | `title` | `lightning__textType` | yes | maxLength: 200 | Title |
| 2 | `body`  | `lightning__richTextType` | yes | — | Body |
| 3 | `publishDate` | `lightning__dateType` | no | — | Publish Date |
| 4 | `ctaUrl` | `lightning__urlType` | no | allowedUrlSchemes: ["https"] | Call to Action |
| 5 | `heroImage` | `lightning__imageType` | no | — | Hero Image |
```

## Column rules

- **`#`** — 1-indexed order from `schema.properties` (JSON key order).
- **`API name`** — the property key, backticked.
- **`Type`** — the `lightning:type` value, backticked.
- **`Required`** — `yes` if the key is in `schema.required`, else `no`.
- **`Constraints`** — a compact, comma-separated summary of the property's declared constraints:
  - Include `minLength`, `maxLength`, `minimum`, `maximum`, `enum` (as `enum: [a, b, c]`, truncated to 3 with `…` if longer), `pattern` (as `pattern: <regex>`), `format`, `lightning:allowedUrlSchemes`, `readOnly`, `lightning:localizable`, `lightning:textIndexed`, `const`.
  - If a field has no declared constraints, emit `—` (em-dash), NOT an empty cell.
  - Do NOT include `lightning:type` here — it's already in the `Type` column.
  - Do NOT include `lightning:uiOptions.placeholderText` — it's not a constraint.
- **`Title`** — the property's `title` value, or the API name humanized if `title` is missing.

## Sort / truncation

- Preserve `schema.properties` insertion order.
- If the schema has more than 20 properties, print the first 20 and add a final row `| … | (N more properties) | | | | |` where N = total − 20.

## Do NOT print

- The raw JSON schema.
- Root-level metadata (`title`, `description`, `lightning:type`, `lightning:mixinTypes`).
- `unevaluatedProperties`.

Those are agent-internal details — the user cares about the field list, not the JSON.

After printing the table, continue immediately to step 8 (no separate turn, no user prompt between 7.5 and 8).
