# DC Pipeline Contract

The DC pipeline for a single Agentforce session runs as three stages in
sequence:

```
fetch_dc.py → 24 dc.<name>.json artifacts + dc._session_manifest.json
assemble_dc.py → dc._session_tree.json (pure in-memory join)
render_dc.py → dc._session_summary.md (pure tree reader)
```

Each stage is independently runnable. `fetch_dc.py` chains the two
downstream stages by default; `--no-assemble` / `--no-render` opt out of
each. The renderer can also run standalone against a tree produced by a
prior invocation.

This document owns the shape + invariants of stages 2 and 3. For per-DMO
field reference of what stage 1 produces, see
[`dc_dmo_fields.md`](./dc_dmo_fields.md).

---

## 1. Pipeline overview

| Stage | Script | Input | Output | Scope |
|---|---|---|---|---|
| Fetch | `scripts/fetch_dc.py` | org + session id | 24 `dc.<name>.json` + `dc._session_manifest.json` | DC Query REST API, 5-wave waterfall |
| Assemble | `scripts/assemble_dc.py` | fetch outputs | `dc._session_tree.json` | pure in-memory join, no fetches |
| Render | `scripts/render_dc.py` | tree + manifest | `dc._session_summary.md` | pure tree reader, no DMO loads |

Nothing downstream of fetch issues DC queries. Everything after fetch is
pure compute over files on disk, which means the renderer can iterate
on markdown format without re-fetching.

---

## 2. Assembly stage

`scripts/assemble_dc.py` joins the fetched DC rows into a hierarchical
tree.

### 2.1 Purpose + scope

**Inputs:** 24 `dc.<name>.json` artifacts + `dc._session_manifest.json`
produced by `scripts/fetch_dc.py`, under `DATA_ROOT/<sid>/`.

**Output:** `dc._session_tree.json` — session-rooted hierarchical view.
Interaction → Step → Generation → GatewayRequest; audit rows (Tag,
ObjRecord, Metadata, LLM, Quality, Category, Feedback, FeedbackDetail)
nested under the right parent.

**Contract:** pure in-memory compute, no new DMO queries, forward-only
joins on already-fetched rows. Chain-orphan GW calls fall through to a
timestamp-window rule with an explicit `binding_method` flag.

### 2.2 Inputs

The assembler does **not** hard-code the 24 template names. It reads
`dc._session_manifest.json` first, then iterates
`manifest["queries"][*]["name"]` to populate the row map. When
`fetch_dc.py` adds a 25th template, the row loader picks it up
automatically — the tree logic only references names it knows how to
place, so a new DMO is loaded but not rendered until the assembler is
taught what to do with it.

Per-field schema for every DMO lives in
[`dc_dmo_fields.md`](./dc_dmo_fields.md).

### 2.3 Declared binding chain

The "normal" path that nests a `GatewayRequest` under its owning
`LLM_STEP` in the tree. Every edge is a platform-sanctioned forward FK:

```
Step.ssot__GenerationId__c → Generation.generationId__c
Generation.generationResponseId__c → GatewayResponse.generationResponseId__c
GatewayResponse.generationRequestId__c → GatewayRequest.gatewayRequestId__c
```

**Which Step types populate `ssot__GenerationId__c`?** Only `LLM_STEP`
(verified live). `ACTION_STEP`, `TOPIC_STEP`, `TRUST_GUARDRAILS_STEP`,
and `SESSION_END` always have `NOT_SET` here; the chain never resolves
for them.

**Expected declared-share on typical Agentforce sessions:** minority.
Most gateway calls on a real session land via the timestamp-window
fallback, not the declared chain. Sessions that rely on Flow-invoked
prompt-template actions produce zero declared bindings and many
timestamp_window bindings — normal, not a defect.

### 2.4 Timestamp-window fallback

Any `GatewayRequest` not reached via the declared chain is placed by
timestamp containment.

**Window semantics:**
- **Closed-closed:** `start_ts <= gw_req.timestamp__c <= end_ts`.
- **Null end_ts** (active session / interaction / step) is treated as
 `+∞`.
- **Missing start_ts**: fall through to the next preference tier; never
 match on start alone.
- Boundary ties bind to the earlier parent (Step) in preference to the
 later one (Interaction).

**Tier dominates containment.** Selection order is:

1. Find all Step windows containing the GW timestamp.
2. Restrict to the highest-preference tier present: `ACTION_STEP` →
 `TOPIC_STEP` → `TRUST_GUARDRAILS_STEP` → any other (catch-all:
 LLM_STEP without declared binding, SESSION_END, unknown types —
 never excluded).
3. Among those, pick the innermost (shortest-window) Step.
4. On exact window-size ties, pick the latest `start_ts`.

Example: if both a wide `ACTION_STEP` and a narrower nested `TOPIC_STEP`
contain the GW timestamp, the `ACTION_STEP` wins because its tier
dominates — even though TOPIC is innermost.

**Placement fallbacks:**
- If no Step window matches, attach to the enclosing `Interaction` as a
 `timestamp_bound_gateway_calls[]` entry (`bound_to_step_id` is null).
- If no Interaction window matches, land in
 `session.unbound_gateway_calls[]`.

**Never declared-bound twice.** A Step that already owns a GW via the
declared chain is excluded from timestamp-window candidates.

### 2.5 `binding_method` enum

Every GatewayRequest in the tree carries exactly one of these:

| Value | When emitted |
|---|---|
| `declared` | Placed under a Step via the declared chain in §2.3. |
| `timestamp_window` | Placed by §2.4 (under a Step or an Interaction). |
| `unbound` | Neither chain nor window matched; landed in `session.unbound_gateway_calls[]`. |

**Collision handling.** When two Steps' Generation chains resolve to
the same GatewayRequest (`Step.ssot__GenerationId__c` collisions at the
upstream DMO), first-step-wins: the earlier Step in walk order claims
the GW. Subsequent Steps get `"gateway_request": null` with an adjacent
`"gateway_request_collision": true` marker on the Step view, so readers
can see why the GW is absent. The session-level
`counts.gw_binding.declared_collisions` integer tracks the aggregate.
On observed data this is 0; non-zero values indicate a real defect in
the upstream DMO writers.

### 2.6 Moment placement

`session.moments[]` lives at the root of the session, not nested under
`Interaction`. Each moment carries `interaction_ids[]`, a sorted list
derived from `MomentInteraction` (the junction table). Rationale: the
schema supports many-to-many (one moment can span multiple
interactions; one interaction can belong to multiple moments), even
though observed live data is 1:N. Nesting under Interaction would
duplicate rows.

Moments are absent on orgs without Agent Optimization enabled; the
assembler never requires their presence.

### 2.7 1:1 audit chain invariant

For every `GatewayRequest` in the session, exactly one
`GatewayResponse` exists (in live data, modulo in-flight calls at
fetch time). `counts.audit_chain_1to1_ok` is `true` iff
`len(gateway_requests) == len(gateway_responses)`. Drift is flagged in
the counts block but does not crash the assembler — a caller
re-fetching during an active session can still produce a partial tree.

Note: this is Req↔Resp 1:1, not Req↔LLM_STEP. The typical session has
more GatewayRequests than LLM_STEPs because prompt-template /
plannerservice calls emit GatewayRequest rows without owning Step rows.

### 2.8 `session_shape` enum

Lifted verbatim from `dc._session_manifest.json.session_shape` into
`dc._session_tree.json counts.session_shape`. Six values, classified
by `fetch_dc.py` after the 5-wave waterfall; rules evaluated
top-to-bottom, first match wins:

| Value | Rule | Added |
|---|---|---|
| `session_not_found` | `sessions.json` returned 0 rows (bad sid or STDM not yet materialized) | original |
| `interactions_not_materialized_yet` | sessions row present, but interactions/steps/messages all 0 (fresh session — STDM hierarchy hasn't materialized yet, but gateway_requests may exist) — assembler takes the gateway-direct path; see §2.9 | |
| `gateway_requests_dropped_by_stdm` | DC `gateway_requests == 0` while runtime telemetry outside Data Cloud confirms ≥1 LLM call for the session — i.e. the STDM exporter has dropped writes the platform did emit. Distinct from `planner_ran_no_gateway_logs` (which means logging disabled at the source). This skill cannot disambiguate this state by itself; the operator must check runtime telemetry to reclassify. | |
| `abandoned_before_llm` | steps > 0, LLM_STEP count == 0, gw_reqs == 0 (user typed, planner didn't reach an LLM call) | original |
| `planner_ran_no_gateway_logs` | LLM_STEP > 0 AND steps_with_generation_id > 0 AND gw_reqs == 0 (Trust Layer gateway logging disabled; extra guard prevents misclassification from broken generations-IN clauses) | original |
| `complete` | everything else (the "normal" bucket, including partial chain-orphan sessions) | original |

The enum names only the operator-actionable states. For finer shape,
read `counts.gw_binding`: if `declared == 0` but `gateway_requests > 0`,
the session relied entirely on prompt-template / Flow-invoked LLM
calls — normal but worth noticing.

`gateway_requests_dropped_by_stdm` is the only shape that this skill
cannot definitively classify on its own — disambiguating from
`planner_ran_no_gateway_logs` requires a runtime telemetry probe
outside Data Cloud. In this skill the session is reported as
`planner_ran_no_gateway_logs`; the operator with access to the
platform's runtime LLM-gateway telemetry can check for a matching
gateway-call event to distinguish a real STDM exporter defect from
"logging genuinely disabled at the source."

### 2.9 Output: `dc._session_tree.json` schema

Root shape:

```jsonc
{
 "session": {
 "id": "<sid>",
 "_schema_version": 1, // see §2.9b
 "identity": { ... }, // see §2.9a
 "org": { "alias": "...", "instance_url": "..." },
 "start_ts": "...",
 "end_ts": null, // null while active
 "end_type": "Completed | Abandoned | ...",
 "channel": "...",
 "participants": [
 { "participant_id": "...", "role": "USER | AGENT",
 "agent_api_name": "<null for USER>",
 "agent_version": "...", "agent_type": "..." }
 ],
 "moments": [
 { "moment_id": "...",
 "agent_api_name": "...", "agent_version": "...",
 "request_summary_text": "...", "response_summary_text": "...",
 "interaction_ids": ["..."], // [] if no bridging rows; never omitted
 "start_ts": "...", "end_ts": "...",
 "tag_associations": [ ... ] // moment-scope only
 }
 ],
 "interactions": [
 {
 "id": "...", "type": "TURN | SESSION_END", "topic": "...",
 "trace_id": "...", // primary column or extracted from AttributeText
 "start_ts": "...", "end_ts": "...",
 "messages": [
 { "message_id": "...", "type": "Input | Output",
 "role": "USER | AGENT", // derived via participant join
 "participant_id": "...", "text": "...",
 "content_type": "...", "modality": "...", "ts": "..." }
 ],
 "telemetry_spans": [ ... ], // usually []
 "steps": [
 {
 "id": "...",
 "type": "LLM_STEP | ACTION_STEP | TOPIC_STEP | TRUST_GUARDRAILS_STEP | SESSION_END",
 "name": "...",
 "start_ts": "...", "end_ts": "...",
 "error_text": null, // NOT_SET → null
 "generation": { // present iff ssot__GenerationId__c != NOT_SET
 "generation_id": "...",
 "response_id": "...",
 "response_text": "...", "masked_response_text": "...",
 "feature": "...",
 "quality": [ ... ], // ContentQuality rows parented on generationId__c
 "categories": [ ... ], // ContentCategory rows parented on generationId__c
 "feedback": [
 { "feedback_id": "...", "feedback": "UP | DOWN", "action": "...",
 "details": [ ... ], "records": [ ... ] }
 ]
 },
 "gateway_request": { // present only when declared chain resolves
 "binding_method": "declared",
 "gateway_request_id": "...",
 "feature": "...", "model": "...", "provider": "...",
 "prompt_template_dev_name": "...", // "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0,
 "prompt_text": "...", // raw input prompt
 "response": { ... },
 "tags": [ ... ], "records": [ ... ],
 "metadata": [ ... ], "llm": []
 },
 "gateway_request_collision": true // present only when a prior step
 // claimed this step's declared GW;
 // gateway_request is null in this case
 }
 ],
 "timestamp_bound_gateway_calls": [ // chain-orphans placed by ts-window
 { "binding_method": "timestamp_window",
 "bound_to_step_id": "...", // null if bound to Interaction, not a Step
 "gateway_request_id": "...", "feature": "...", "model": "...",
 "response": { ... }, "tags": [...], "records": [...],
 "metadata": [...], "llm": [] }
 ],
 "tag_associations": [ ... ] // interaction-scope only
 }
 ],
 "session_tag_associations": [ ... ], // session-scope only
 "unbound_gateway_calls": [ // chain-orphans with no window match
 { "binding_method": "unbound", "gateway_request_id": "...", /* ... */ }
 ],
 "counts": {
 "interactions_total": 0, "interactions_turn": 0, "interactions_session_end": 0,
 "steps_total": 0,
 "steps_by_type": { "LLM_STEP": 0, "ACTION_STEP": 0, "TOPIC_STEP": 0,
 "TRUST_GUARDRAILS_STEP": 0, "SESSION_END": 0 },
 "generations": 0,
 "gateway_requests": 0, "gateway_responses": 0,
 "gateway_metadata": 0, "gateway_llm": 0,
 "gateway_records_grounded": 0, "gateway_records_feedback": 0,
 "feedback": 0,
 "audit_chain_1to1_ok": true,
 "gw_binding": { "declared": 0, "timestamp_window": 0, "unbound": 0,
 "declared_collisions": 0 },
 "session_shape": "complete | abandoned_before_llm | planner_ran_no_gateway_logs | gateway_requests_dropped_by_stdm | interactions_not_materialized_yet | session_not_found",
 "pk_collisions": [ ], // {dmo, key} records; first-write-wins applied
 "parse_warnings": [ ] // dc.<name>.json files that failed to parse
 }
 },
 "catalog": { // session-filtered, not full org vocabulary
 "agents_observed": [ "..." ],
 "tag_definitions": [ ... ],
 "tag_definition_associations": [ ... ],
 "tags": [ ... ]
 },
 "_doc": "Assembled from DATA_ROOT/<sid>/dc.*.json. See dc._session_manifest.json."
}
```

**Polymorphic dispatch:**
- `GenAIGtwyObjRecord.parent__c` — if in `gw_req_by_id` → attached as
 `GatewayRequest.records[]` (grounded attachments); if in
 `feedback_by_id` → attached as `Feedback.records[]`; else silently
 dropped.
- `GenAIContentCategory.parent__c` — if in `generations_by_id` →
 attached as `Generation.categories[]` (non-TOXICITY detectors); if
 in `quality_by_id` → nested under the Quality row as
 `_toxicity_subcategories[]`; else silently dropped.
- `GenAIAiAgentTagAssociation` — routed by which of the three scope FKs
 (`SessionId`, `InteractionId`, `MomentId`) is populated. Rows with
 none are silently dropped.

**Polymorphic dispatch failures are silent by design.** If these id
spaces collide in future (they don't today — `gatewayRequestId__c`,
`feedbackId__c`, `generationId__c`, and `quality.id__c` are all
distinct UUID namespaces), the first-branch-wins behavior records the
defect nowhere. Revisit if a real org ever shows a cross-namespace id.

#### 2.9a `session.identity` sub-object

Harvested from already-fetched rows. Fields that require values absent
from every observed DMO row come out as `null`. Every string harvested
from `tagValue__c` is piped through `html.unescape()` → quote-strip →
`_clean()` to coerce `""`/`NOT_SET`/`UNSET_VALUE` to `None`.

| Field | Source DMO | Source column / lookup |
|---|---|---|
| `org_id` | gateway_requests | `orgId__c`, first non-null after sort |
| `platform_user_id` | gateway_requests | `userId__c`, first non-null after sort |
| `planner_id` | gateway_requests | `plannerId__c`, first non-null after sort |
| `bot_version_id` | gateway_requests | `botVersionId__c`, first non-null after sort |
| `app_type` | gateway_requests | `appType__c`, first non-null after sort |
| `bot_id` | gateway_request_tags | `tagValue__c` where `tag__c == "bot_id"` |
| `bot_name` | gateway_request_tags | `tagValue__c` where `tag__c == "bot_name"` |
| `agent_api_name` | gateway_request_tags | `tagValue__c` where `tag__c == "agent_developer_name"` (no fallback; MyAgent has no developer-name tag — look at `bot_name` + `agent_label` instead) |
| `agent_label` | gateway_request_tags | `tagValue__c` where `tag__c == "agent_label"` |
| `agent_version` | gateway_request_tags | `tagValue__c` where `tag__c == "agent_version_api_name"`, fallback `"version_api_name"` |
| `agent_type` | gateway_request_tags | `tagValue__c` where `tag__c == "agent_type"` |
| `planner_name` | gateway_request_tags | `tagValue__c` where `tag__c == "planner_name"` |
| `planner_type` | gateway_request_tags | `tagValue__c` where `tag__c == "planner_type"` |
| `configured_model` | gateway_request_tags | `tagValue__c` where `tag__c == "configured_model_name"` |
| `messaging_session_id` | sessions[0] | `ssot__RelatedMessagingSessionId__c` |
| `messaging_end_user_id` | participants | `ssot__ParticipantId__c` on the first USER-role row (sorted by `ssot__Id__c`) |
| `voice_call_id` | sessions[0] | `ssot__RelatedVoiceCallId__c` |
| `individual_id` | sessions[0] | `ssot__IndividualId__c` |
| `bootstrap_variables` | sessions[0] | parsed from `ssot__VariableText__c` — channel-specific bootstrap key→value dict (e.g. `__resolved_locale__`, `__supports_result_display__`); empty `{}` when the column is null/empty/unparseable |
| `mode` | derived | one of `production_messaging` / `builder_previewer` / `voice` / `unknown` — derived from `(channel, RelatedMessagingSessionId__c, RelatedVoiceCallId__c, bootstrap_variables.keys)`. See `_derive_mode` + `_BUILDER_PREVIEWER_INDICATOR_KEYS` in `assemble_dc.py`. |

**Sorting (required for idempotence):**
- `gateway_requests` — sort by `(timestamp__c, gatewayRequestId__c)`
 ascending, then take first non-null.
- `gateway_request_tags` — sort by `(parent__c, tag__c, tagValue__c)`
 ascending, then filter by tag name and take first non-null.
- `participants` — sort by `ssot__Id__c` ascending, then take the first
 USER-role row.
- `sessions[0]` — by contract, one row per session; no sort needed.

**Trimmed fields:** `user_location`, `user_context` are not promoted
(low debugging value, opaque without a decoder ring).

**Minimal tree exclusion.** The session-not-found short-circuit path
(§2.11) does **not** emit an `identity` sub-object — identity
harvesters need non-empty gateway rows, which are guaranteed empty in
this branch. Renderer's minimal branch handles absent identity
gracefully.

#### 2.9b `session._schema_version`

Current value: `1`. Emitted on both the full tree and the minimal
session-not-found tree. Additive changes (new sub-objects, new fields)
do NOT bump this. Breaking changes (rename or remove a top-level key,
change the shape of `interactions[]`, etc.) bump it.

Renderer refuses to render a tree with an incompatible version; see
§3.10.

### 2.10 Idempotence

Running the assembler N times on the same `DATA_ROOT/<sid>/` produces
a byte-identical `dc._session_tree.json`. Rules:

- Arrays sort by source timestamp ascending; on ties, by primary-key
 string.
- Any set-derived array (`agents_observed`, `interaction_ids[]`, etc.)
 is emitted via `sorted(...)` before serialization.
- `json.dumps(..., sort_keys=True)` for all dict output.
- Identity harvest uses the explicit sort keys in §2.9a for
 first-non-null picks.
- Verified on the live test fixture: `diff` of two runs returns empty.

### 2.11 Session-not-found short-circuit

If `sessions.json` returned 0 rows, the assembler writes a minimal
tree with only `session.id`, `session.org`,
`session._schema_version: 1`, and
`counts.session_shape = "session_not_found"`. No `identity`, no
`interactions[]`, no `catalog{}`.

---

## 3. Render stage

`scripts/render_dc.py` turns `dc._session_tree.json` into a human
markdown file.

### 3.1 Purpose + scope

**Input:** `dc._session_tree.json` + `dc._session_manifest.json` (the
latter only for the Empties diagnostics section).

**Output:** `dc._session_summary.md` — 11 top-level sections, with `Session bootstrap` and `Planner LLM calls` conditionally suppressed (see §3.3).

**Contract:** pure tree reader. No DMO loads. No fetches. Everything
the renderer displays either lives directly on `tree.session.*` or is
composed from tree fields in the renderer's presentation layer.

### 3.2 Inputs

- `dc._session_tree.json` — primary input. Renderer SystemExits with a
 clear "tree not found" message if absent.
- `dc._session_manifest.json` — consulted for the Empties diagnostics
 section. If absent, that section renders empty.

The 24 raw `dc.<name>.json` artifacts are NOT loaded by the renderer.

### 3.3 Output: section order

The full-tree branch emits these top-level sections in order. The
gateway-direct branch (§2.8 `interactions_not_materialized_yet`) and
the minimal session-not-found branch use abbreviated section sets;
see `_render_gateway_direct` / `_render_minimal` in `render_dc.py`.

1. `## Session identity` — identity fields from `tree.session.identity`
 plus display-only cells (Agent, Total duration) composed in-renderer.
2. `## Session bootstrap` — channel mode + bootstrap variables
 (`identity.mode`, `identity.bootstrap_variables`). Surfaces these to
 make MIAW vs Builder Previewer distinguishable at-a-glance —
 `ssot__AiAgentChannelType__c` alone collides between the two. Section
 is suppressed (not rendered) when both `mode` and `bootstrap_variables`
 are absent — backwards-compat with older trees.
3. `## ID reference` — full UUIDs for everything truncated in the
 hierarchical trace.
4. `## Transcript` — USER ↔ AGENT narrative per TURN interaction.
 SESSION_END interactions have no messages and are skipped.
5. `## Complete hierarchical trace` — Interaction → Step → Generation →
 GatewayRequest, with `+start + duration = +end` math on Interaction
 and Step lines. Single timestamps on Generation and GatewayRequest
 (no computed latencies; see §3.6). UUIDs truncated to 8 chars + `…`;
 full forms in §2 above.
6. `## Per-turn summary` — one row per interaction.
7. `## Planner LLM calls (full prompts + responses)` — **opt-in via
 `--show-prompts`; suppressed by default**. Walks `interactions[].steps[]`, builds one
 `#### LLM call N — <short-id>` block per step that has a
 `gateway_request`. Renders the full input prompt (from
 `gateway_request.prompt_text`) and full response (from
 `generation.response_text`, HTML-unescaped) inside fenced code
 blocks. Per-payload display capped at 64 KB; full payloads always
 remain authoritative on disk in `dc.gateway_requests.json` /
 `dc.generations.json`. Off by default because multi-turn sessions
 with 30 KB+ prompts would dominate the summary.
8. `## Visual analysis` — gantt + LLM-call overlay.
9. `## Session counts` — engineer-facing table of manifest counts.
10. `## Empties diagnostics` — one row per DMO with `rows == 0` and a
 populated `_unavailable_reason` lifted verbatim from the manifest.
11. `## Catalog (session-filtered)` — TagDefinitions /
 TagDefinitionAssociations / Tags filtered to agents observed in the
 session.

DC alone does not expose per-turn LLM latency in a useful form, so this
skill emits no `## Latency rollups` section. Generation and
GatewayRequest carry single-write timestamps (see §3.6); they are not
start/end pairs.

### 3.4 Ellipsis rule

In the `## Complete hierarchical trace`:

- All UUIDs (interaction_id, step_id, generation_id,
 gateway_request_id) render as the first 8 characters followed by `…`.
- Full UUIDs live in the `## ID reference` table above, keyed by the
 same 8-char prefix.

This keeps the trace scannable while preserving the ability to
cross-reference by ID.

### 3.5 Session-end derivation

`session.end_ts` can be null for two reasons:

1. The session is still active.
2. The session ended but STDM hasn't materialized the `end_ts` column
 yet.

Renderer display rule: if `session.end_ts` is non-null, render it
directly with `✓ materialized` suffix. If null, look at the last
interaction by timestamp:

- If a SESSION_END interaction exists, use its `start_ts` as the
 derived end with `from SESSION_END interaction` suffix.
- Otherwise, use the last TURN interaction's `end_ts` (or `start_ts`
 if its end is null) with `session still open (last TURN)` suffix.

The derivation is display-only; the tree's `session.end_ts` is not
modified.

### 3.6 Why we don't compute latencies on generation/gateway_request

`Generation.timestamp__c` and `GatewayRequest.timestamp__c` are
single timestamps representing when the DC row was written. They are
NOT `start_ts`/`end_ts` pairs. Treating the delta between two of them
as a "latency" is misleading — the gap reflects how DC serialized the
audit, not how long the LLM call took.

Interaction and Step DMOs DO expose start_ts + end_ts pairs; the
renderer computes `+offset + duration = +end` math for those.

### 3.7 Empties diagnostics

Walk `manifest["queries"]` for entries with `rows == 0` and a
populated `_unavailable_reason`. Render each as a row:
`| <dmo_name> | <rows> | <verbatim reason> |`. The renderer does not
infer reasons.

Artifacts that failed to parse go into `tree.counts.parse_warnings` and
surface in the `## Session counts` section, not here.

### 3.8 Idempotence

Running `render_dc.py --session <sid>` N times on the same
`dc._session_tree.json` produces a byte-identical
`dc._session_summary.md`. Rules:

- All section builders walk tree arrays in the order the tree provides
 them; the tree itself is already sorted.
- No timestamps of "now" embedded in the output.
- No set-derived ordering; any set-to-list conversion goes through
 `sorted(...)`.
- Verified on the live test fixture: `diff` of two runs returns empty.

### 3.9 Session-not-found short-path

If the tree has `_schema_version: 1` but no `interactions[]` key, the
renderer emits a minimal markdown file:

```markdown
# Session <sid>

## Session identity

| Field | Value |
|---|---|
| Session id | <sid> |
| Session shape | session_not_found |

_No interactions resolved in Data Cloud. Check the session id, or
wait for STDM materialization._
```

No transcript, no trace, no counts, no catalog.

### 3.10 Tree schema version check

First check in `main_for_session()`:

- `tree.session._schema_version == 1` → render.
- `tree.session._schema_version` missing → stderr WARN, render anyway
 (treat as best-effort for older trees).
- Any other value → `SystemExit("render_dc: unsupported tree
 _schema_version=<v>; expected 1")`. Refuses rather than risking a
 silent schema mismatch.

---

## 4. Reading order for a new skill author

1. Read this file (contract).
2. Run the pipeline once against a fresh session: `python3
 scripts/fetch_dc.py --session <sid> --org <alias>`. Inspect
 `DATA_ROOT/<sid>/` — you get the 24 `dc.<name>.json`, the manifest,
 the tree, and the summary.
3. Open `dc._session_tree.json` and trace the declared chain for one
 LLM_STEP end-to-end.
4. Read the matching `dc._session_summary.md`.
5. Read `scripts/assemble_dc.py` (module docstring points back here),
 then `scripts/render_dc.py`.
6. Cross-reference [`dc_dmo_fields.md`](./dc_dmo_fields.md) when you
 hit a field whose origin is unclear.
