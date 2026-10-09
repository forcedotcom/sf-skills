# Dataset Hygiene and Dashboard Auditing

## Finding unused dataset fields

Run `scripts/find_unused_dataset_fields.js <alias> <DatasetName>`. It:

1. Resolves the dataset → fetches its main XMD → enumerates `dimensions ∪ measures ∪ dates` → set of canonical field names.
2. Pages through `GET /wave/dashboards?pageSize=200`.
3. For each dashboard, `GET /wave/dashboards/{id}` → concatenates every `state.steps[*].query`.
4. Keeps only dashboards whose SAQL contains `load "<DatasetName>"` (tolerates `&quot;` HTML-encoded form).
5. Extracts every single-quoted token from SAQL, intersects with the field-name set.
6. Outputs the unused set.

**Caveats:**
- Compound steps referencing fields with the same name across multiple datasets will look "used" against any dataset with a matching field name.
- Aggregateflex steps store column references in a structured `columns` block, not in a SAQL `query`. The scanner only handles SAQL steps — extend the extractor for `state.steps[*].columns[*].field` if needed.
- Dashboards in retired/archived apps still count as "users" unless you filter by folder.

## Finding where a field is used

Same scanner, inverted: for a single field name, list every (dashboard, step) whose SAQL token set contains it. Adapt `find_unused_dataset_fields.js` — replace the field-set intersection with a single-field membership test.

## Detecting SAQL re-encoding decay

Dashboards edited via PATCH without first decoding SAQL accumulate `&amp;quot;`, `&amp;amp;quot;`, etc. Detection: GET every dashboard in the target app, count occurrences of the substring `&amp;` in each `state.steps[*].query`. Anything > 0 means at least one extra encoding layer. (Single-level `&quot;` is normal and expected.)

Fix: apply the `decodeAll` helper from `references/dashboard-authoring.md` to every affected step's query, then PATCH the dashboard with the decoded state.
