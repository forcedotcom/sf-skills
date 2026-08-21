# Error taxonomy and gotchas — Create the IT Service Employee Agent

Split from `references/cli-invocation.md` — that file documents the per-phase
CLI call shapes and the classifier contracts; this file collects the errors
those calls can return and the recurring foot-guns.

## Error taxonomy

- **Auth error / `401 Unauthorized`** — the org session is expired or the alias
  is wrong. Re-run `sf org login web` for the target org; there is no token to
  refresh by hand.
- **`401`/`403`/unexpected error body on the Phase-1 Studio-access read** — the
  preflight classifier maps this to `studio.signal="ERROR"` / `verdict="ERROR"`
  (distinct from a confirmed 404 gate). Surface the raw response and stop —
  do not proceed to Phase 2 even if the template read succeeded.
- **`403`/`404` on `createBundleWithVersion` / `publish` / `activate`** — the
  NGA authoring namespace isn't provisioned or enabled on the org. Trigger the
  Phase-1 hand-off offer.
- **`400 MISSING_ARGUMENT: agentType`** on `agent-templates` — the required
  `agentType` query param was omitted; pass `AgentforceEmployeeAgent`.
- **Build-script exit 3** — the template, its `agentScript`, or a successful
  `developer_name`/`agent_label` substitution wasn't found in the captured
  `agent-templates.json`; surface stderr, don't hand-author a body.
- **Classifier exit 3** on a `sf data query` read — the SOQL query failed
  (auth/malformed); surface the raw CLI error, do not treat as NOT-EXISTS.
- **Empty stdout from `activate`** — this is the SUCCESS response
  (`EmptyRepresentation`), not a failure; confirm via the Phase-7 verify SOQL.

## Gotchas

| Issue | Resolution |
|-------|------------|
| Legacy `createAgent` produces the wrong kind of agent | Never call `/connect/service-itsm/createAgent` — it creates a Setup-page bot with an external-link icon in Agentforce Studio. Use the three `/nextgen-authoring/*` calls in `references/cli-invocation.md` |
| `sf api request rest --method POST` with no `--body` flag | Fails with `No 'mode' found in 'body' entry`, even for `publish`/`activate` which ignore the body — always pass `--body '{}'` explicitly |
| `sf api request rest --json` errors | Don't pass `--json` there — the raw stdout body is already JSON. `--json` is for `sf data query` (which needs the `.result.records[]` envelope) |
| Confusing `bundleId` with `bundleVersionId` | The `createBundleWithVersion` response's `id` field is the bundle **version** Id used in publish/activate; `bundleId` is the parent bundle's Id and 404s if passed to `/bundle-versions/{...}` |
| Naive single-pass HTML-entity decode leaves compile errors | `&amp;quot;` (double-encoded) and `&#92;` (numeric, backslash) require a multi-pass decode covering both named and numeric entities — see `build-create-body.mjs` |
| Bundle's outer `apiName` diverging from the script's internal `config.developer_name` | Always substitute both via `build-create-body.mjs` before the create call — a divergence is exactly the kind of mismatch that produces confusing platform behavior |
| Hardcoding `IT_Service_Employee_Agent` in one call but collecting it in another | Thread the collected `<developerName>` through the idempotency SOQL, the bundle body (outer + internal), AND the verify SOQL — a mismatch creates the wrong agent |
| Bare `./scripts/classify-agent-existence.mjs` "not found" | Use the skill's absolute `<skill_dir>` in the `node` invocation |
| `agent-templates` → `400 MISSING_ARGUMENT: agentType` | The `agentType` query param is required — pass `AgentforceEmployeeAgent` |
| `agent-templates` returns empty `data[]` | Wrong `agentType` value — use `AgentforceEmployeeAgent`; empty results are not the same as "not provisioned" |
| Treating `activate`'s empty response as a failure | It's the documented success response (`EmptyRepresentation`) — verify via the Phase-7 SOQL instead of parsing this call's stdout |
| Tempted to token+curl for any of the three writes | Never — `sf api request rest --method POST --body @<file>` (or `--body '{}'`) handles auth for `/services/data/...` writes; token extraction is forbidden |
