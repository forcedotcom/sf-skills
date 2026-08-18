---
name: automation-sandbox-post-copy-configure
description: "Apply a Salesforce sandbox post-copy automation JSON config against a target org. For each entry, the skill derives the correct Tooling API sobject from the entry's `ConfigurationName`, verifies the derivation via a describe probe, resolves the record Id via SOQL-over-REST, then PATCHes the record via the compound `Metadata` field using `sf api request rest`. Use when the user asks to apply, run, execute, dry-run, or preview a post-copy or post-refresh config file (e.g. `post-copy-config.json`) against a sandbox. Trigger phrases: \"apply post-copy config\", \"run post-copy automation\", \"execute sandbox post-refresh JSON\", \"apply sandbox refresh config\", \"configure sandbox after refresh\". DO NOT TRIGGER for generating the config JSON from an SOP (delegate to `automation-sandbox-post-copy-config-generate`), or for deploying metadata XML."
allowed-tools: Bash Read Write
metadata:
  version: "1.0"
  domains: ["Automation"]
  cliTools:
    - tool: ["curl"]
      semver: ">=7.0.0"
    - tool: ["jq"]
      semver: ">=1.6"
    - tool: ["node"]
      semver: ">=18.0.0"
    - tool: ["sf"]
      semver: ">=2.0.0"
---

# Automation: Sandbox Post-Copy Configure

Apply a Salesforce sandbox post-copy automation JSON config to a target
org. The skill pins the Tooling API sobject **and** the record-lookup
SOQL filter for the two canonical `ConfigurationName` values it has
been calibrated against (`OutboundMessages`, `RemoteSiteSettings`); for
any other `ConfigurationName` it derives a candidate from the entry
value and verifies it against the live org's describe endpoint. Every
entry — pinned or derived — must still pass Step B (describe returns
200 with a `Metadata` compound field) before any PATCH is planned.
Entries whose API cannot be identified or verified are surfaced in the
summary and skipped — they are never guessed at.

## Tool Restrictions

**Use ONLY the Bash tool** to execute `sf` CLI commands (`sf data query
--use-tooling-api`, `sf api request rest`, `sf org display`). Do NOT
use MCP tools like `execute_soql` — ignore them completely; the
compound `Metadata` PATCH pattern this skill requires is not available
through MCP tool wrappers. If the target org alias is not explicitly
named by the user, invoke `sf` commands **without** `--target-org` —
the harness has already set the CLI's default target-org. Never pass
`--target-org default` — `default` is not an alias and will fail with
`NamedOrgNotFoundError`.

SOQL-over-REST (`sf data query --use-tooling-api ...`) is treated as
an API call — same OAuth session, same authorization boundary as the
subsequent PATCH. No direct database / non-Salesforce SQL access.

## STOP — do this before making any API call

Never call the org from memory. Before the first request:

1. Read the config JSON end-to-end from the exact path the user gave
   (default `./post-copy-config.json`). Every entry must have all five
   keys (`ConfigurationName`, `Label`, `Fields`, `IsActive`,
   `ExecutionOrder`). If any entry is malformed, abort and surface the
   file path + entry index — do **not** partially apply. **Do not
   invent entries.** If the file is missing, stop and ask; never
   fabricate a plan against synthetic labels.
2. For each distinct `ConfigurationName` in the config, run the
   derivation + describe-verify step (below) **before** planning any
   PATCH. An entry whose API cannot be verified must never appear as
   a planned PATCH — it is rejected up front.
3. Confirm the target org alias with the user unless they supplied one
   explicitly. This skill mutates a live org — writing to the wrong
   org (e.g., a production alias set as default) is the most expensive
   failure mode.

If you announce "I will apply … now" without having read the config
file and run the describe-verify for every distinct
`ConfigurationName`, stop and do those first.

---

## Per-entry procedure (the core of this skill)

The skill carries a pinned mapping for the canonical types below, and
a derive-then-verify path for anything else. Follow these steps **for
every entry**, in order. `Step B` (describe-verify) is mandatory
regardless of whether the mapping came from the pinned table or the
derive path — its HTTP status must appear in the summary.

### Step A — Resolve the Tooling API sobject and lookup filter

**Pinned canonicals (authoritative — use these exactly, do NOT
substitute a different sobject name):**

| ConfigurationName | Tooling API sobject | Record-lookup SOQL |
|-------------------|---------------------|--------------------|
| `OutboundMessages`   | `WorkflowOutboundMessage` | `SELECT Id, FullName FROM WorkflowOutboundMessage WHERE EntityDefinition.QualifiedApiName = '<Fields.Object>'` — then client-side pick the row whose `FullName == '<Fields.Object>.<Label>'`. SOQL cannot filter on `FullName` directly for this sobject. |
| `RemoteSiteSettings` | `RemoteProxy`             | `SELECT Id, SiteName FROM RemoteProxy WHERE SiteName = '<Label>'`. |

For canonical entries use the pinned sobject and SOQL as-is; skip
"derive". Do not invent `OutboundMessage`, `RemoteSiteSetting`, or
`MasterLabel` variants — plausible-looking but wrong.

Field-name resolution (overrides + case rule + existence check) is
owned by `scripts/map-metadata-key.mjs`.

**Non-canonical**: derive a candidate (usually singular of the
Metadata API type name, sometimes prefixed); Step B rules out wrong
guesses. Use the generic SOQL patterns in Step C.

### Step B — Verify the candidate exists and supports Metadata writes

For each candidate, GET the describe:

```bash
sf api request rest \
  "/services/data/v<apiVersion>/tooling/sobjects/<Candidate>/describe/"
```

Accept the candidate only if **both** are true:

- HTTP 200 (the sobject exists on this org's Tooling API), AND
- The describe response's `fields` array contains a field named
  `Metadata` (compound field — this is what PATCH writes through).

If no candidate passes both gates, mark the entry
`API_NOT_IDENTIFIED` and skip. **Do not guess a REST path** — the
wrong path 404s in the best case and updates the wrong record in the
worst case.

### Step C — Resolve the record Id (SOQL-over-REST)

**For pinned canonicals**: run the SOQL from the Step A table
verbatim (substituting `<Label>` / `<Fields.Object>`). Do not
substitute a different filter column such as `MasterLabel` — the
pinned SOQL is the tested-and-correct filter for that sobject.

**For non-canonical (derived) sobjects**: query the verified sobject
for the record identified by the entry's `Label` (and `Fields.Object`
when present):

```bash
# SOQL to a variable + separate jq call — avoids the most common
# shell-quoting failure in this skill.
SOQL='SELECT Id, FullName FROM <VerifiedSobject> WHERE <UniqueFilter>'
sf data query --use-tooling-api --json --query "$SOQL" \
  > /tmp/entry-<Slug>-lookup.json
ID=$(jq -r '.result.records[0].Id // empty' /tmp/entry-<Slug>-lookup.json)
```

Pick `<UniqueFilter>` based on the queryable fields shown in the
describe response from Step B. If the row contains a `FullName` field,
SOQL usually rejects a direct `FullName = ...` filter — filter by
whichever direct column the describe surfaces (e.g.
`EntityDefinition.QualifiedApiName`, `DeveloperName`, `SiteName`) and
apply the `FullName` match client-side (`jq -r
'.result.records[] | select(.FullName == "<Object>.<Label>") | .Id'`).

Outcomes:

- Zero rows → `NOT_FOUND` (never fall back to insert).
- Multiple rows after client-side filtering → `AMBIGUOUS` (surface
  all Ids in the summary and skip; a wrong Id is worse than no Id).
- Exactly one row → proceed to Step D.

### Step D — GET current Metadata, mutate, PATCH back

`Metadata` is **replace-in-full** — omitted keys are blanked on
PATCH. Preserve every existing key from the Step D-1 GET; overlay
only the mutated keys. The summary's "planned PATCH body" (apply
and dry-run) is this full merged object — verbose or org-specific
values may render as `"<preserved-from-GET>"` in dry-run, but
every key must be present.

Every Step D filename must include the record `<Id>` from Step C
(e.g. `/tmp/entry-<Id>-meta.json`) — phase-parallel entries share
the working directory and would clobber a shared name.

1. **GET** current `Metadata` → `/tmp/entry-<Id>-meta.json`.
2. **Resolve the mutation key** — for each `Fields.<Xxx>`, run
   `node scripts/map-metadata-key.mjs "<ConfigurationName>"
   "<ConfigFieldName>" /tmp/entry-<Id>-meta.json`. On
   `{"status":"OK","key":...}` use the returned key. On
   `{"status":"FIELD_MAP_UNKNOWN",...}` mark the entry and skip.
3. **PATCH** — heredoc-build `/tmp/entry-<Id>-mutation.json`, merge
   with `jq --slurpfile m /tmp/entry-<Id>-mutation.json
   '. + $m[0] | {Metadata: .}' /tmp/entry-<Id>-meta.json >
   /tmp/entry-<Id>-patch.json` (preserves JSON types), PATCH with
   `-b @/tmp/entry-<Id>-patch.json`, capture the response body to
   `/tmp/entry-<Id>-response.json`. Full bash in
   `references/api_endpoints.md` §Step D. Never use `--arg`
   (stringifies booleans/numbers, breaks on special chars). Wrap
   the PATCH in `for attempt in 1 2; do <cmd> && break; done` —
   retry once on shell/jq quoting failure (non-zero exit *before*
   the HTTP call goes out).
4. **Classify** — `node scripts/classify-patch-result.mjs
   "<httpCode>" /tmp/entry-<Id>-response.json`. Exit 0 → `SUCCESS`;
   exit 2 → `FAILED` (parsed error on stdout). 204 with a non-empty
   body is `FAILED`.

### Step E — Verify the change landed

Re-read the record to confirm the PATCH stuck:

- If the mutated field is a direct-queryable SOQL column on the
  sobject (rare — most `Metadata`-writable fields are not), a SELECT
  by Id is enough.
- Otherwise GET the record and inspect the corresponding key inside
  `.Metadata`.

If the read-back value doesn't match the requested value, record
`FAILED_VERIFY` — the PATCH returned 204 but the effect is not
visible (usually a naming or permission issue).

---

## IsActive semantics

- `IsActive: true`  → apply the PATCH as described in Steps A–E.
- `IsActive: false` → **do not PATCH**. Record `SKIPPED_INACTIVE`
  for the entry and add a bullet under **Follow-ups** in the summary
  file listing the entry's `ConfigurationName` + `Label` so the
  customer notices that a config-declared inactive record was left
  untouched on the target org.

Rationale: `IsActive: false` means "not active in this sandbox",
not "deactivate the existing record". Silently deactivating a live
integration is a much bigger blast radius than leaving it alone.

---

## Canonical output shape (always emit this)

Single Markdown summary written to `./post-copy-<mode>-summary.md`
(mode is `dry-run` or `apply`) AND printed to the user. No JSON
side-files (`plan/phases.json`, `requests/*.request.json`, etc.) —
inline every planned/actual request in the Markdown.

**Phase enumeration is script-owned.** Run `node scripts/plan-phases.mjs
<config.json>` and consume its `phases[]` output verbatim. Each entry
carries `ordinal` (1-indexed phase number) and `executionOrder` (raw
value, for the `(ExecutionOrder = <raw>)` heading annotation). Sparse
values collapse (`1, 2, 5` → ordinals `1, 2, 3`). `IsActive:false`
entries are pre-marked `SKIP_INACTIVE`. See
`references/execution_phasing.md` for the worked example.

For dry-run entries the `HTTP` column is `—` (em-dash). End the
summary with: `No PATCH requests were issued. To apply, re-run
without the dry-run flag.`

**Target-org resolution is script-owned.** Run `node
scripts/resolve-target-org.mjs`; substitute the returned `.alias`
into the header. Never emit `<env:SF_TARGET_ORG>` or `$SF_TARGET_ORG`
verbatim.

```markdown
# Post-Copy Configure Run — <N> entries <planned|applied> against `<alias>`

Config file: `<path>`
Target org: `<alias>`
Mode: <dry-run|apply>

## Phase <ExecutionOrder> — <count> entr(y|ies)

Planned request:
- Method: `PATCH`
- Path: `/services/data/v<apiVersion>/tooling/sobjects/<VerifiedSobject>/<Id>`
- Body: `<JSON — the FULL merged Metadata object: every existing key from the Step D-1 GET, overlaid with the mutated keys from the config. Preserved keys with verbose or org-specific values may appear as "<preserved-from-GET>" placeholder strings, but every key must be present. NEVER emit a minimal body containing only the mutated keys.>`

| ConfigurationName | Label | Object | Sobject | Describe | Outcome | HTTP |
|-------------------|-------|--------|---------|----------|---------|------|
| <name>            | <lbl> | <obj>  | <VerifiedSobject> | <200 or 404> | <outcome> | <code> |

## Totals

| Outcome | Count |
|---------|-------|
| <state> | <n>   |

## Follow-ups

- <bullet per SKIPPED_INACTIVE / API_NOT_IDENTIFIED / AMBIGUOUS / FIELD_MAP_UNKNOWN / NOT_FOUND entry>
```

Column semantics: `Object` = the entry's `Fields.Object` if present,
`—` otherwise. `Sobject` = the Step A resolved sobject. `Describe` =
the Step B describe HTTP status (`200` for verified, `404` for
`API_NOT_IDENTIFIED`) — mandatory so skipped Step Bs are visible at a
glance. Outcome vocabulary: `SUCCESS`, `NOT_FOUND`, `AMBIGUOUS`,
`API_NOT_IDENTIFIED`, `FIELD_MAP_UNKNOWN`, `FAILED`, `FAILED_VERIFY`,
`SKIPPED_INACTIVE`, `SKIPPED`, `DRY_RUN`, `DELETE_NOT_SUPPORTED`,
`NOT_ATTEMPTED`.

**Scripts are internal.** The `plan-phases.mjs`, `map-metadata-key.mjs`,
`classify-patch-result.mjs`, `resolve-target-org.mjs` invocations are
implementation detail — do **not** inline their raw stdout, JSON
output, or "I ran node …" narration into the summary Markdown or
the printed response. Consume the JSON, use the returned values, and
render the summary in the exact shape above.

## Scope

- **In scope**: Reading a post-copy config JSON (the shape produced
  by `automation-sandbox-post-copy-config-generate`), grouping entries
  into `ExecutionOrder` phases, deriving+verifying the Tooling API
  sobject for each entry, resolving Ids via SOQL-over-REST, PATCHing
  via compound `Metadata`, and reporting per-entry outcomes.
- **Out of scope**: Generating the config JSON from an SOP (delegate
  to `automation-sandbox-post-copy-config-generate`); deploying
  metadata XML; running the Async Task Framework (ATF) orchestrator
  itself (that is the platform-side Java implementation); inventing
  API paths for `ConfigurationName` values whose describe probe
  fails (surface as `API_NOT_IDENTIFIED` and stop).

Every API call is against a live org. Treat this skill as a mutation
tool: prefer `--dry-run` first, confirm the target org alias, and
never silently retry a failed entry against a different endpoint.

---

## Required Inputs

Gather or infer before applying:

- **Config file path**: Path to the JSON produced by
  `automation-sandbox-post-copy-config-generate` (default:
  `./post-copy-config.json` in the current directory). If the file
  does not exist, stop and ask.
- **Target org alias / username**: The `sf` CLI alias or username of
  the target sandbox. Never assume the default org — always confirm.
  If the user has not supplied one, list available orgs with `sf org
  list --json` and ask which to use.
- **Dry-run flag** (optional, default `false`): Semantics —
  **reads are ALLOWED, writes are FORBIDDEN**. Dry-run means the run
  produces no mutation on the target org; it does NOT mean "no
  network calls". You MUST still execute every read against the org:
  the describe probe (Step B, `GET`), the SOQL Id lookup (Step C,
  `sf data query`), and the record fetch (Step D-1, `GET`) — because
  the plan's "would-be PATCH body" can only be accurate if the
  agent has read the current `Metadata` block from the live record.
  The ONLY skipped calls are the writes: Step D-3 (`PATCH`) and
  Step E (post-PATCH verification). Never fabricate the current
  Metadata; never emit a body containing invented keys. If a read
  fails (401, 404, `NamedOrgNotFoundError`), surface the error and
  stop — do not fall back to a from-memory plan. Use dry-run on the
  first pass unless the user has explicitly asked to apply.
- **Continue-on-error** (optional, default `true`): When true, a
  failing entry does not abort the phase — the remaining entries in
  the phase still execute, and the failure is reported in the
  summary. When false, a failure aborts execution mid-phase.

If the user supplies a clear config path and target alias, proceed
without further questions.

---

## Workflow

Every step executes real `sf` CLI commands via the Bash tool. Do NOT
narrate the plan without actually running the commands — the point of
this skill is to mutate the target org, not to describe how.

1. **Read and validate the config JSON** — load the file with the
   Read tool. Every entry must be a JSON object with the five
   top-level keys (`ConfigurationName`, `Label`, `Fields`,
   `IsActive`, `ExecutionOrder`). Malformed entries are a hard stop.

2. **Resolve the target org and API version** — run
   `sf org display --json`. Parse the JSON to confirm the alias
   resolves and to capture `result.apiVersion` (e.g. `62.0`). Do not
   print the raw JSON — it contains the access token.

3. **Plan phases** — run `node scripts/plan-phases.mjs <config.json>`
   and iterate its `phases[]` output. See
   `references/execution_phasing.md` for the concurrency cap.

4. **Per-entry describe-verify pass** — for each distinct
   `ConfigurationName`, run Step A + Step B once and cache the
   verified sobject. Any `ConfigurationName` failing Step B marks
   every entry with that name as `API_NOT_IDENTIFIED`.

5. **Per-entry apply pass** — for each entry inside each phase:
   - Entries pre-marked `SKIP_INACTIVE` by plan-phases → record
     `SKIPPED_INACTIVE`, add a Follow-ups bullet, continue.
   - Else run Step C (resolve Id), then Step D (GET+mutate+PATCH),
     then Step E (verify). If `--dry-run` is true, still run Step C
     and D-1/D-2 so the printed plan reflects the real merged
     payload — skip only D-3 (the PATCH) and Step E, then record
     `DRY_RUN`.

6. **Between phases** — wait for every entry in the current phase to
   complete before starting the next.

7. **Write the summary file to disk** — the final deliverable is a
   Markdown file at `./post-copy-<mode>-summary.md`, following the
   shape in the "Canonical output shape" section. Also print it to
   the user. Never write access tokens or full `sf org display`
   output. If a URL contains embedded credentials, mask them in the
   summary (`https://user:***@host/...`); the actual PATCH body
   carries the verbatim URL.

---

## Rules and Gotchas

Load-bearing invariants (never insert; describe-gate every
`ConfigurationName`; compound `Metadata` PATCH preserves the full
existing block; `IsActive: false` → `SKIPPED_INACTIVE`; never print
raw access tokens; cap intra-phase concurrency at 5) and the
canonical response for each runtime failure (401 mid-run, 429,
credential-bearing URLs, `Fields.Action = "Delete"`, describe 404,
zero/many SOQL rows) live in `references/rules_gotchas.md`. Read
that file before deviating from the Step A–E procedure.

---

## Cross-Skill Integration

| Need | Delegate to |
|------|-------------|
| Turn a customer SOP into the JSON config this skill consumes | `automation-sandbox-post-copy-config-generate` |
| Deploy Salesforce metadata XML (Custom Labels, Named Credentials, etc.) that lives outside the compound-Metadata Tooling API pattern | The matching `generating-*` skill + a metadata deploy flow |
| Create new records that do not yet exist on the target org | `platform-metadata-deploy` after generating the metadata XML |
| Assign permission sets required to run the API calls | `dx-org-permission-set-assign` |

---

## Reference File Index

| File | When to read |
|------|-------------|
| `references/api_endpoints.md` | Steps A–E — the full generic recipe with worked examples (OBM, RSS) and the camelCase-field convention |
| `references/execution_phasing.md` | Step 3 (workflow) — the grouping rules and the intra-phase concurrency cap. `scripts/plan-phases.mjs` is the executable source-of-truth for phase enumeration; this file explains the model behind it |
| `scripts/plan-phases.mjs` | Step 3 (workflow) — deterministic phase planner (invoke, then read its output) |
| `scripts/map-metadata-key.mjs` | Step D-2 — deterministic Metadata-key resolver (override table + case rule + existence check) |
| `scripts/classify-patch-result.mjs` | Step D-4 — deterministic HTTP-outcome classifier (SUCCESS vs FAILED) |
| `scripts/resolve-target-org.mjs` | Canonical output shape — deterministic target-org alias resolver |
| `references/authentication.md` | Step 2 (workflow) — for the session-check recipe and how to handle 401 mid-run |
| `references/rules_gotchas.md` | Before deviating from Step A–E — load-bearing invariants and canonical runtime-failure responses |
| `assets/api_request_templates.json` | Steps A–E — the generic template for describe / lookup / GET+PATCH with placeholder keys |
| `examples/sample_config_input.json` | Step 1 (workflow) — shape of the config JSON this skill consumes |
| `examples/sample_execution_summary.md` | Step 7 (workflow) — the shape of the summary report shown to the user |
