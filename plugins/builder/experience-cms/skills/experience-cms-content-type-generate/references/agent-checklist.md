# Agent execution checklist and tripwires

Copy this checklist agent-internally (do NOT print to chat). Tick each box only after the action is genuinely done.

## Mandatory progress checklist

- [ ] Step 1a: read `sfdx-project.json`, resolved `<sfdx-source>`
- [ ] Step 1b: ran directory-listing tool against `<sfdx-source>/contentTypes/`
- [ ] Step 1c: dispatched `metadata-grounding.search_metadata` (NOT `salesforce-api-context`)
       → `query` string is 3-5 English content-domain nouns (`news article announcement story headline`, not `sfdc_cms__news content type` or `bundle`). Confirmed no `sfdc_cms`, `c__`, `__` substring, `content type`, `bundle`, `metadata`, or `cms` in the query. See `discovery-query-rules.md` § Concrete tool calls.
       → recorded `grounding=complete` OR `grounding=unavailable` from a REAL `metadata-grounding` attempt
       → ALSO dispatched `content-readonly.get_content_types_for_workspace` per the mutual-exclusivity contract: `{ spaceId }` alone if the caller supplied `spaceId` — no `baseType` sent; `{ folderId }` alone if the caller supplied `folderId` — no `baseType` sent; `{ baseType }` if the caller supplied only that (no scope); `{ baseType: "CONTENT" }` if the caller supplied none of the three. If `grounding=complete`: took the intersection of the two responses' FQNs (Flow 1). If `grounding=unavailable`: this tool's semantically-matched rows ARE the org signal (Flow 2) — recorded `groundingFallback=workspaceTypes`. Only skip this dispatch if `get_content_types_for_workspace` itself is absent from the deferred-tool list this turn (record `workspaceTypes=unavailable`).
- [ ] Step 1d: presented findings to the user — has-matches variant emits exactly 4 options: ONE `Use existing: <row-1 FQN>` (row 1 = OOTB if any exists, else grounding's top rank), `Provide an FQN` (only when matches exist OR delegated invocation), `Create new`, and `Cancel`. Step 1d is always chat-visible and always waits for the user's pick.
- [ ] Step 1e (only when user picked `Use existing` or `Provide FQN`): retrieve-and-reconcile — namespace-gated `sf project retrieve` for custom FQNs, skipped for OOTB.
       → **BEFORE retrieve**: snapshotted `localSchemaBefore` (schema.json only, if it exists locally) into memory. Did NOT snapshot meta.xml — retrieve writes it correctly on its own.
       → **AFTER retrieve**: compared `localSchemaBefore` (pre-retrieve snapshot) against post-retrieve `schema.json` as parsed JSON trees. If they differ → dispatched drift prompt (`Deploy local` / `Overwrite local` / `Cancel`) and waited for user reply. Did NOT declare "reconciled" or "in sync" silently on schema drift.
       → **On drift-prompt Cancel or Deploy-local**: restored `localSchemaBefore` to `schema.json` BEFORE emitting outcome. Left meta.xml alone (retrieve wrote correct XML).
       On success returns `{fqn, schema}` and jumps to step 7.5.
- [ ] Step 2 (only on "Create new" path): SF CLI default org resolved (silent).
- [ ] Step 3b: presented proposed-fields markdown table, got user approval (this is the FIRST chat message — until now, only silent work).
- [ ] Step 4: wrote `schema.json` + `.contentTypeBundle-meta.xml`.
- [ ] Step 5: ran `sf project deploy start --dry-run --json` (mandatory — no exit before this except "use existing").
- [ ] Step 7a: asked the user yes/no to deploy via `ask_user_tool`.
- [ ] Step 7b/7e: deploy resolved.
- [ ] Step 7.5: printed the schema summary table (chat-visible) — always runs when `{fqn, schema}` was resolved, regardless of `suppressCreateContentPrompt`.
- [ ] Step 8 gate: read `suppressCreateContentPrompt`. If `true`, skip step 8 and emit `Task Completed` with `{fqn, schema}`. If `false`/unset AND `{fqn, schema}` was resolved, dispatch the trailing "create content?" prompt and route on the reply, THEN emit `Task Completed`.

## Tripwires — stop and restart from step 1a

- About to dispatch a discovery tool to any server other than `metadata-grounding` or `content-readonly.get_content_types_for_workspace` — including `salesforce-api-context`, `salesforce-metadata-experts`, `execute_metadata_action`, `run_soql_query`, `run_tooling_query`, `sf data query`, `sf org list metadata`, or a SOQL `SELECT … FROM ContentTypeBundle` → **Rule 1 violation.** These two are the ONLY allowed discovery paths. `get_content_types_for_workspace` is a sanctioned complement to grounding (Flow 1 intersection) and its sanctioned Flow 2 replacement when grounding is down — it is NOT a loophole for reaching any other server. If `metadata-grounding` isn't in the deferred-tool list at turn start, accept `grounding=unavailable`, still dispatch `get_content_types_for_workspace` (Flow 2), and use the matching variant in step 1d — do NOT reach for any OTHER substitute.
- About to dispatch `metadata-grounding.search_metadata` with a `query` containing `sfdc_cms`, `c__`, any `__` substring, `content type`, `bundle`, `metadata`, or `cms` → **query-construction violation.** The `query` is 3-5 English content-domain nouns; the kind is already carried by the `metadataType` argument. Rebuild before the tool call — see `discovery-query-rules.md` § Concrete tool calls for the shape.
- About to run `sf project retrieve start --metadata ContentTypeBundle:<Name>` in step 1e WITHOUT first reading local `schema.json` into memory as `localSchemaBefore` → **Rule 5 violation (5a).** Retrieve overwrites `schema.json` in place; if you skip the snapshot, drift is undetectable and Cancel becomes a lie.
- Reading local meta.xml into a `localMetaBefore` variable, or restoring meta.xml from any snapshot on the Cancel / Deploy-local branches → **do not do this.** Retrieve returns each of the two bundle files with its own correct content — meta.xml is not user-authored and has no reconciliation role. Snapshot and restore `schema.json` only.
- After step 1e retrieve, `localSchemaBefore` differs from the post-retrieve `schema.json` (JSON tree compare) AND you are about to declare "reconciled" / "in sync" / "local now matches org" / "no drift" WITHOUT dispatching the drift prompt → **Rule 5 violation (5b/5c).** `schema.json` drift = mandatory prompt with `Deploy local to org` / `Overwrite local with org` / `Cancel`. The user picks, not you.
- About to compare the post-retrieve `schema.json` against a fresh read of the SAME file (or against the retrieved bytes) → **Rule 5 violation (5b).** That's diffing a file against itself and will always return "no drift." Left-hand side of the compare is `localSchemaBefore` (pre-retrieve snapshot), full stop.
- About to emit `Cancelled. No files written.` from the step 1e drift-prompt Cancel branch, or route the `Deploy local to org` branch to step 5, WITHOUT first writing `localSchemaBefore` back to `schema.json` → **Rule 5 violation (5d).** The message is a promise about disk state; a Deploy-local without restore deploys the org copy back to org (no-op) instead of the user's original local.
- About to write "Proposed fields for …" without step 1c having dispatched `metadata-grounding.search_metadata` → **Rule 2 violation.**
- About to write any step 1d header or pick line that claims a content type is "not in the org", "not deployed", "local only", "missing from org", or equivalent → **Rule 6 violation.** Grounding is a heuristic index, not the org — its silence proves nothing about org state. `get_content_types_for_workspace` confirms workspace support, but that's also not a deploy-shape confirmation. Only step 1e's `sf project retrieve start` can confirm absence. Copy the exact case header from `assets/discovery-prompts.md` verbatim.
- About to append `(org check skipped — grounding unavailable)` when `get_content_types_for_workspace` actually ran this turn (Flow 2), or omit any disclosure at all when BOTH tools were unavailable → **TRUTH GATE violation.** Three distinct wordings for three distinct states — see SKILL.md Step 1d and `discovery-details.md#1d`. Picking the wrong one either overstates or understates what was actually checked.
- About to offer a "deploy it now?" prompt at step 1d (before retrieve has run) → **Rule 6 violation.** Deploy offers belong AFTER step 1e's retrieve confirms org absence. At step 1d, you only present the pick list.
- Step 1d output doesn't match `assets/discovery-prompts.md` verbatim — preamble text above the table, wrong columns, bare-FQN cells, table packed into `question`, multiple `Use existing:` options, or ad-libbed question wording → **Rule 6 violation.** Re-open `assets/discovery-prompts.md` and copy the has-matches / zero-matches shape exactly.
- About to emit `Task Completed` after step 4 without step 5 run → **Rule 3 violation.**
- About to dispatch `open <deployUrl>`, `sf org open`, or any command AFTER emitting `Task Completed` → **Rule 4 violation.**
- About to dispatch the step 8 trailing "create content?" prompt WITHOUT first checking `suppressCreateContentPrompt` from invocation params → **invocation-contract violation.** If the flag is `true`, step 8 is a no-op — return `{fqn, schema}` and emit `Task Completed`.
- About to print `intent=… | skill_selection=complete`, `grounding=…`, `mcp=…`, or any status line to chat → **output-discipline violation.** Agent-internal only, never printed.
- If you call any tool before step 1c is checked off → you are not following this skill correctly. Stop and start at step 1a.
- If your first chat message to the user contains "Proposed fields", "I'll create the files", "I'll attempt salesforce-api-context", or "Per the global rule" → you have skipped step 1. Stop and start at step 1a.
- If you emit `Task Completed` and step 5 (dry-run) or step 7 (deploy ask) is unchecked → you have violated Rule 3. Stop, run the missing steps.

If `metadata-grounding` is genuinely unreachable (real server error, not a misrouted call): record `grounding=unavailable` agent-internally, dispatch `get_content_types_for_workspace` directly (Flow 2), and continue silently to step 1d with whatever it returns.
