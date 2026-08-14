# Rules, Constraints, and Gotchas

Load-bearing invariants and the recovery/response for each recoverable
runtime failure. Read alongside `SKILL.md`; every rule below is a
skill-behavior invariant, not an authoring guideline.

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| Every `ConfigurationName` must pass Step B (describe returns 200 AND exposes a `Metadata` field) before any PATCH is planned for it | Guessing the sobject name silently updates the wrong record type; the describe gate is the only defense against a plausible-but-wrong derivation |
| Never insert; this skill updates existing records only | Creation is the metadata-generation flow's responsibility; a missing target record is an error to surface, not one to paper over |
| Confirm the target org alias explicitly before the first API call | Default org may be a production alias; a wrong org selection is the most expensive failure mode |
| Group entries by `ExecutionOrder`, then serialize phase boundaries | Same `ExecutionOrder` = parallel-eligible; different values = strict serial ordering (later phase may depend on earlier phase's effect) |
| Cap intra-phase concurrency at 5 by default | Salesforce REST API rate limits: bursts of concurrent requests trigger `REQUEST_LIMIT_EXCEEDED` |
| Every PATCH body wraps the change in a compound `Metadata` field with camelCase keys, preserving the full existing block | Top-level fields on these Tooling sobjects are read-only, and `Metadata` is replace-in-full — omitted keys are blanked |
| If the derived camelCase key is not present in the current `Metadata` block, mark `FIELD_MAP_UNKNOWN` and skip | Silent PATCH of a different key updates the wrong field or adds a phantom one |
| `IsActive: false` → `SKIPPED_INACTIVE` (no PATCH), plus a Follow-ups bullet | Silently deactivating a live integration is a much bigger blast radius than leaving it alone and flagging it |
| A single entry's failure does not abort the phase unless `continue-on-error` is false | Isolated failures (stale Label, deleted record) must not block unrelated entries |
| Never print raw access tokens or full `sf org display` output | Access tokens grant full org access; they must not be surfaced to the user or written to disk |
| Report every entry's outcome in the final summary, including successes | Silence on a success is indistinguishable from a skip — completeness makes the report auditable |

## Gotchas

| Issue | Resolution |
|-------|------------|
| `sf` CLI session expired | Prompt the user to re-run `sf org login web --alias <alias>`; never attempt interactive login on their behalf |
| Target org alias resolves to production | Stop and confirm before any PATCH |
| Describe returns 404, or 200 without a `Metadata` field | Mark every entry with that `ConfigurationName` as `API_NOT_IDENTIFIED`; do not attempt an educated-guess endpoint |
| SOQL lookup returns multiple rows | Mark `AMBIGUOUS`, list all Ids, do not PATCH |
| SOQL lookup returns zero rows | Mark `NOT_FOUND`; do not fall back to insert |
| HTTP 401 mid-run | Surface, ask the user to re-authenticate, offer to resume — do not silently retry with a stale token |
| HTTP 429 / `REQUEST_LIMIT_EXCEEDED` | Reduce intra-phase concurrency (e.g., 5 → 2) and continue |
| URL contains credentials (`https://user:token@host/...`) | Send verbatim to the API but mask in the summary (`https://user:***@host/...`) |
| OBM entry has `Fields.Action = "Delete"` | Surface `DELETE_NOT_SUPPORTED` — this skill does not delete records |
