---
name: experience-cms-content-type-generate
description: "Salesforce CMS ContentTypeBundle creation skill. Use this skill ANY TIME a user request involves creating a ContentTypeBundle, and activate FIRST when CMS ContentTypeBundle creation is mentioned. Discovers existing types via metadata-grounding and produces a validator-correct two-file bundle that passes dry-run deploy. TRIGGER when: user wants to define, scaffold, generate, or set up a reusable content shape in Salesforce CMS — any domain — including phrasings like \"create a content type for X\", \"generate a schema for X in CMS\", or \"set up a content type for X\". DO NOT TRIGGER when: authoring a RECORD (use experience-cms-content-generate), publishing / managing records (use CMS UI), modifying / renaming / deleting an existing bundle, CMS brand (experience-cms-brand-apply), media search (experience-content-media-search), Custom Lightning Types (platform-custom-lightning-type-generate), or non-CMS metadata."
metadata:
  version: "1.0"
  domains: ["Experience"]
  minApiVersion: "64.0"
  relatedSkills:
    - "experience-cms-brand-apply"
    - "experience-cms-content-generate"
    - "experience-content-media-search"
    - "platform-custom-lightning-type-generate"
  cliTools:
    - tool: ["sf"]
      semver: ">=2.0.0"
  mcpTools:
    metadata-grounding: { tools: ["search_metadata", "query_metadata", "describe_metadata"], semver: ">=1.0.0" }
    content-readonly: { tools: ["get_content_types_for_workspace"], semver: ">=1.0.0" }
---

# experience-cms-content-type-generate

## What This Skill Does

- **DISCOVER** — checks local `<sfdx-source>/contentTypes/` and queries `metadata-grounding` for existing OOTB/custom ContentTypeBundles.
- **RECONCILE** — on existing pick/provided FQN, retrieves from org (custom only) and reconciles against local. Returns `{fqn, schema}` matching the org.
- **CREATE** — generates a validator-correct ContentTypeBundle (`schema.json`, `.contentTypeBundle-meta.xml`).
- **VALIDATE** — `sf project deploy start --dry-run` against the CLI default (or picked) org.
- **AUTO-FIX** — fixes schema issues, re-validates (max 3 attempts).
- **DEPLOY** — asks yes/no, deploys on yes.

**Create-only for new types**, **reconcile-only for existing**. Does not modify, rename, or delete existing bundles beyond replacing a local copy with the org copy on user consent; does not author content records. If the message asks to add/rename/remove a field on an existing type (verbs `add`/`append`/`remove`/`drop`/`rename`/`change`/`modify`/`update` targeting an FQN or named type), print ONE line before 1a: `This skill is create-only for new types and reconcile-only for existing. To modify "<fqn|name>", edit its schema.json and redeploy, or use the CMS UI.` — then continue discovery so the user lands on the type's summary (7.5). Do NOT silently proceed as if the modification happened.

## Invocation contract

Invoked directly by the user or delegated to by another skill (e.g. `experience-cms-content-generate`). Two halves: **input params** the caller supplies, and a **return outcome** emitted at every terminal state.

### Input params (all optional)

| Param | Type | Effect |
|---|---|---|
| `fqn` | string (`namespace__DeveloperName`) | Skip discovery entirely. Jump straight to step 1e (retrieve-and-reconcile) using this FQN. `intent` and the 1d pick prompt are bypassed. Use when the caller already knows exactly which type to resolve. |
| `intent` | string | The user's original message. Drives discovery keywords in step 1c and the "matching …" wording in 1d. Default when the skill is triggered by a natural-language user prompt. |
| `suppressCreateContentPrompt` | boolean, default `false` | Suppresses the trailing "Would you like to create content using this type now?" question at step 8. Callers that already drive their own content-creation flow MUST pass `true`. Direct user invocation leaves it `false` so the user gets the natural next-step offer. |
| `spaceId` | string | Workspace scope for the step 1c workspace-content-types check (`get_content_types_for_workspace`). Pass when the caller already resolved a content space. **Mutually exclusive with `baseType`** — see below. |
| `folderId` | string | Folder scope for the same check, as an alternative to `spaceId`. **Mutually exclusive with `baseType`** — see below. |
| `baseType` | string, default `"CONTENT"` | `baseType` argument to `get_content_types_for_workspace`. **Mutually exclusive with `spaceId`/`folderId`** — see below. |

**Workspace scope resolution — mutual exclusivity contract.** `spaceId` / `folderId` / `baseType` narrow step 1c's workspace-content-types check only, not the discovery path taken. **A caller that passes `spaceId` or `folderId` MUST NOT also pass `baseType`** — the scope alone already determines the eligible types; this skill does not accept both in the same call. Exactly one of four combinations applies each run — call shapes and rationale → `references/discovery-details.md#1c continued`:

1. `spaceId` only → `get_content_types_for_workspace({ spaceId })`.
2. `folderId` only → `get_content_types_for_workspace({ folderId })`.
3. `baseType` only → `get_content_types_for_workspace({ baseType })`.
4. None of the three → `get_content_types_for_workspace({ baseType: "CONTENT" })` (default).

Common invocation shapes:

- **Direct user** → `intent`, `suppressCreateContentPrompt` `false`. Full discovery + retrieve-and-reconcile + trailing prompt. No `spaceId`/`folderId`/`baseType` — falls to combination 4 above.
- **Delegated** → `{ intent | fqn, suppressCreateContentPrompt: true }`. Full discovery + retrieve-and-reconcile; returns `{success, fqn, schema}` (the retrieve is what confirms the type is deployed in the org — a local-only type resolves to `not_deployed`, never a bare success). Trailing prompt suppressed.
- **Delegated with a known workspace** → `{ intent, suppressCreateContentPrompt: true, spaceId: "<contentSpaceOrFolderId>" }` — combination 1. Pass this once the caller has already resolved a workspace (e.g. `contentSpaceOrFolderId` from `get_or_create_cms_workspace_and_web_app_channel`) and wants step 1c's check scoped to it. Do NOT also pass `baseType` on this call. If the caller resolves its workspace AFTER content-type discovery (as `experience-cms-content-generate` currently does), it has no `spaceId` to pass at delegation time — that's combination 4, a valid, expected call shape.

### Return outcome

Every terminal state emits a structured outcome. The `message` field is printed to chat as the final one-line summary AND is what the caller reads to route on the result.

| `status` | `fqn` | `schema` | Meaning | Caller action |
|---|---|---|---|---|
| `success` | present | present | Type is confirmed in the org (via 1e's retrieve on an existing type, or via deploy on the "Create new" path), ready to use for downstream work. | Proceed (e.g. author content records). |
| `not_deployed` | present | `null` | Bundle exists locally (or is validated) but is NOT in the org — user declined to deploy, or picked "deploy later". | Do NOT proceed with content creation. Surface the message: "Content type `<fqn>` isn't deployed to `<org>`. Deploy it and re-run." |
| `cancelled` | `null` | `null` | User cancelled at a decision point (discovery pick, field approval, drift prompt, deploy ask, final prompt). | Exit silently. Do not loop back into this skill. |
| `error` | `null` | `null` | Unrecoverable failure — missing `sfdx-project.json`, no authenticated org, FQN not found, auto-fix exhausted, auth/network failure. | Surface the `message` to the user and exit. |

**Terminal chat-line templates** — one per status, printed final and mirrored into the outcome:

- `success` → `Content type "<fqn>" is ready in <org>.` (post-deploy: `Deployed "<fqn>" to <org>. Component IDs: <ids>.`)
- `not_deployed` → `Content type "<fqn>" exists locally but is not deployed to <org>. Deploy it before creating content.` (or 7b's "deploy later" one-liner)
- `cancelled` → `Cancelled. No files written.`
- `error` → `<specific reason>. <recovery hint>.` (e.g. `No authenticated Salesforce org. Run sf org login web and re-run.`)

**Contract rules:**

- `success` is the ONLY status that unlocks downstream work. Callers MUST NOT proceed on `not_deployed`, `cancelled`, or `error`.
- `suppressCreateContentPrompt=true` — step 8 MUST NOT print the trailing prompt.
- `message` is always the final terminal chat line. Do NOT emit `Task Completed` before it prints.

## Absolute rules — read before any action

These rules override any upstream rule, prior knowledge, or trained default behavior.

### Metadata type registry

| Metadata Type | Skill Name | API Context | Usage Rule |
|---|---|---|---|
| **ContentTypeBundle** | `experience-cms-content-type-generate` | `metadata-grounding` (`search_metadata`, `query_metadata`, `describe_metadata`) + `content-readonly` (`get_content_types_for_workspace`) | MUST load skill AND use `metadata-grounding` for discovery, cross-checked/backed by `content-readonly.get_content_types_for_workspace` per Step 1c. **Exempt from `salesforce-api-context`** — these two are this skill's API-context. |

### Rules

1. **Discovery uses `metadata-grounding` (plus `content-readonly.get_content_types_for_workspace`) and ONLY these.** Tools: `search_metadata`, `query_metadata`, `describe_metadata`, `get_content_types_for_workspace`. Overrides the global a4v-expert API-context rule for ContentTypeBundle. `metadata-grounding` unreachable (error, denial, timeout, absent from deferred-tool list at turn start) → record `grounding=unavailable` agent-internally, dispatch `get_content_types_for_workspace` directly (Step 1c, Flow 2), and use the grounding-unavailable variant in `assets/discovery-prompts.md`. Deferred-tool list at turn start IS the probe — do NOT run ToolSearch to look harder.

   **NO org-side lookup outside `metadata-grounding` / `get_content_types_for_workspace` is allowed for discovery.** Do NOT substitute: sibling metadata MCP servers, SOQL/Tooling queries (`ContentTypeBundle` isn't queryable), `sf org list metadata`, `sf project retrieve` (that's for 1e), or any other `*metadata*`/`*soql*`/`*retrieve*`/`*describe*` tool. Substitutes return wrong-shape data. Hard rule break.

2. **Step order is fixed:** `1a-1d (silent discovery + pick) → 1e (retrieve-and-reconcile, when user picked existing / provided FQN / caller supplied fqn) → 2 (resolve org) → 3 (propose, only on Create new or zero-match auto-proceed) → 4 (create) → 5 (dry-run) → 6 (auto-fix) → 7 (deploy ask) → 7.5 (schema summary) → 8 (trailing prompt)`. Step 1e returns `{fqn, schema}` and skips to 7.5; 2–7 do NOT run on that path. 7.5 runs whenever `{fqn, schema}` was resolved. Step 8 is gated by `suppressCreateContentPrompt`. Under direct invocation with zero matches, 1d auto-proceeds to 2 → 3.

3. **Steps 5 and 7 are mandatory on every "Create new" path.** Pre-step-5 exits: (a) `Use existing` / `Provide an FQN` / caller-supplied `fqn` → route through 1e which returns `{fqn, schema}` with no files written; (b) `Cancel` at any pick. Do NOT emit `Task Completed` between steps 4 and 7's resolution. 1e's drift "Deploy local to org" branch also routes through 5 and 7.

4. **`Task Completed` is the LAST action** — skill is over once emitted. Deploy JSON's `deployUrl` is for reference, not an action prompt. Forbidden after: `open <deployUrl>`, `xdg-open`, `sf org open`, `sf project deploy report`, browser tabs, URL echo, "next step" prose.

5. **Step 1e retrieve is destructive for `schema.json`; drift MUST prompt the user.** `sf project retrieve start --metadata ContentTypeBundle:<Name>` overwrites local `schema.json`. Snapshot it into `localSchemaBefore` BEFORE every 1e retrieve (never meta.xml). Drift = parsed-JSON compare of `localSchemaBefore` vs. post-retrieve `schema.json`, left side ALWAYS `localSchemaBefore` — never diff the post-retrieve file against itself. On drift, the drift prompt is MANDATORY (chat diff, then `ask_user_tool`: `Deploy local to org` / `Overwrite local with org` / `Cancel`) — never reconcile silently. `Cancel` and `Deploy local to org` MUST restore `schema.json` from `localSchemaBefore` before emitting the outcome. Full snapshot/restore procedure + drift prompt template → `references/retrieve-and-reconcile.md`.

6. **Step 1d — show top 5 in a table, then ask.** Row count = `min(combined.length, 5)`, always — combined is local matches + every grounding row, deduped (Location `local, org`), never dropped as "irrelevant." Row-1 sort: OOTB first (`sfdc_cms__*` or grounding `isOOTB`), custom (`c__*`) follows in grounding rank. Row 1's FQN names the `Use existing:` option. 1+ rows → table (`FQN | Description | Location`) then `ask_user_tool`: `Use existing: <row-1 FQN>` / `Provide an FQN` / `Create new: <newName>` / `Cancel` (`<newName>` avoids colliding with any FQN in `combined`). Empty combined → NO TABLE, just `ask_user_tool`: `Create new: <contentTypeName>` / `Cancel` (+`Provide an FQN` when delegated/`fqn`-supplied). Never mix "no matches" wording with a table; no preamble; no `#`/`Name`/`Label` columns; never claim a type is "not in the org" — only 1e's retrieve is authoritative. Full prompt templates → `assets/discovery-prompts.md`.

Full agent checklist and tripwire list → `references/agent-checklist.md`.

## File paths (strict)

- Bundle directory: `<sfdx-source>/contentTypes/<ContentTypeName>/` — NOT `contentTypeBundles/<ContentTypeName>/`.
- Two files only: `schema.json` and `<ContentTypeName>.contentTypeBundle-meta.xml`.

## Output discipline

The user reads the chat. Most of this skill's machinery is for you, not them.

**Do not print**: status lines, task-progress checklists, planning prose (`I will now…`, `Per the skill's…`), anti-pattern reasoning, exemption explanations, "operation was denied; proceeded using…" notes, or suggestions that the user run validation/deploy themselves.

**Do print**, and only these: the 1d discovery summary, 1e drift prompt, 3b proposed-fields table + `ask_user_tool`, 2-line "files created" confirmation in step 4, 1-line validation result in step 5, 7a deploy ask, 7b/7e 1-line summary, 7.5 schema summary table (whenever `{fqn, schema}` resolved), and step 8 prompt (when `suppressCreateContentPrompt` is `false`/unset).

**Do NOT emit `Task Completed`, "Done", "All set"** until step 7 has resolved, 7.5's summary has printed, and step 8's gate has been evaluated. Premature completion silently kills the summary + deploy ask.

## Agent checklist and tripwires

The full mandatory progress checklist and the tripwire list are in `references/agent-checklist.md`. Copy the checklist agent-internally and tick each box only after the action is genuinely done. Do not print it to chat.

## Workflow (CREATE)

### 1. Discover existing types (silent — no user prompts in this step)

**1a. Resolve project context (agent-internal)**

Read `sfdx-project.json`. Take `packageDirectories[0].path` and append `/main/default` → `<sfdx-source>`. Bundles live at `<sfdx-source>/contentTypes/`. If `sfdx-project.json` is missing, emit `error` outcome per § Invocation contract with message `This is not an SFDX project — open the project root and re-run.`, print the message, and stop.

**Explicit-FQN fast-path (direct user).** Caller did NOT supply `fqn` but the message literally contains a `namespace__DeveloperName` token (e.g. `sfdc_cms__news`, `c__PressRelease`) → capture it as `fqn` and route directly to step 1e, skipping 1b/1c/1d. Mirror of the delegated `{fqn}` shape.

**Residual-intent capture (agent-internal).** Scan the message for a second clause joined by `and also`/`and then`/`then`, or a second imperative verb targeting a content record (e.g. `create <type> and also create a <thing> about X`). If present, stash as `residualIntent` — step 8's Yes branch forwards it as `intent`. Do NOT print or act on it before step 8.

**1b. Local discovery (silent)**

Use a directory-listing capability (`list_files` / `Glob` on `<sfdx-source>/contentTypes/*/schema.json` / IDE `list_directory`), NOT a content-search/grep tool — content-search misses folder-name-only matches. For each subfolder, read `schema.json` (`title` + `description`). **Match by intent semantically**: reason about content domains, not literal strings — a folder named `MarketPlace` IS a match for a marketplace request even with no literal property match. Return every semantically-matching local bundle into `combined` (step 1d's sort + 5-row cap handle the rest). Zero matches → return zero (auto-proceed on direct invocation).

Rationale, anti-patterns, tool-selection details → `references/discovery-details.md#1b`.

**1c. Org discovery (silent — dispatch `metadata-grounding.search_metadata`, backed by `content-readonly.get_content_types_for_workspace`)**

**Dispatch gate: 1c is a tool call, not a thought.** Do NOT skip because 1b found a local match — the org may still have a same-named bundle ("Name already exists" originates here). Unconditional; only real outage exempts a given tool. Never ask "should I search?".

**The `search_metadata` `query` parameter carries content-domain nouns only** — 3-5 English words describing what the content is ABOUT (news, article, product, press release). NOT an FQN, namespace hint, or copy of the message. `metadataType: "ContentTypeBundle"` already signals the kind. Never dispatch a query containing `sfdc_cms`, `c__`, `__`, `content type`, `bundle`, `metadata`, or `cms` — rebuild if it does. Full ruleset + concrete call-shape table (also referenced from `experience-cms-content-generate` as drift safety-net) → `references/discovery-query-rules.md`.

Server target: `metadata-grounding` (RULE 1). `limit=5`, sorted OOTB-first.

**Do NOT dispatch `query_metadata` in 1c.** `search_metadata` returns everything 1d's table needs (FQN, description, OOTB flag). `query_metadata` is load-bearing only for the OOTB-schema fetch in 1e — dispatch on-demand, for the ONE picked FQN. Per-row fan-out is N wasted round-trips.

**Workspace content-types check — dispatched every run, alongside or instead of grounding.** Call params per the mutual-exclusivity contract (§ Invocation contract), never `baseType` alongside `spaceId`/`folderId`. **Flow 1 (grounding available)** — also dispatch `get_content_types_for_workspace`; org candidate set = **intersection** of both FQN sets (empty is valid, do not widen/retry). **Flow 2 (grounding unavailable)** — dispatch it directly as the sole org signal, apply step 1b's semantic matching to its rows, record `groundingFallback=workspaceTypes` for 1d's TRUTH GATE. Neither tool substitutes for 1e's retrieve. Call shapes, unavailability handling, rationale → `references/discovery-details.md#1c continued`.

**1d. Always present discovery findings — including "no matches"**

Discovery is the first chat-visible signal. Always tell the user what was checked and found. Every case (A/B/C) surfaces a pick list via `ask_user_tool` and WAITS for the user's reply next turn.

**TRUTH GATE — 1d wording must match what actually happened in 1c.** Never claim a check that didn't run this turn; never disclose a skip that didn't happen either. Three cases:

- `search_metadata` dispatched (Flow 1, regardless of `get_content_types_for_workspace` outcome) → org was checked via grounding. No disclosure needed.
- `search_metadata` unavailable but `get_content_types_for_workspace` dispatched (Flow 2 / `groundingFallback=workspaceTypes`) → org WAS checked, just not via grounding. Append `(checked supported content types for this workspace — metadata-grounding unavailable)` per `assets/discovery-prompts.md`.
- Both unavailable → org genuinely not checked. Append `(org check skipped — grounding unavailable)` per `assets/discovery-prompts.md`.

See `references/discovery-details.md#1d`.

**`Provide an FQN` gating — compute `showFqnOption`.** Show when EITHER: (1) any results exist (local OR grounding ≥1) — user may want a match that isn't row 1; rows 2–5 and beyond-cap results surface in the FQN option parenthetical; OR (2) invocation is delegated (`suppressCreateContentPrompt === true` OR caller supplied `fqn`) — always available in the delegated no-matches variant.

Otherwise (direct invocation AND zero matches) → `showFqnOption = false`; skip the pick prompt, print an info line, auto-proceed to step 2. Offering FQN input when the direct user asked to create fresh and nothing matched switches their goal.

**Intent-sanity gate on direct-invocation zero-matches.** Before auto-proceeding, extract at least one recognizable content-domain noun from the message (real word, named entity, or compound domain vocabulary — not gibberish, not filler-only after stripping mechanic nouns like `content type`/`bundle`/`CMS`/`schema`/`metadata`). ≥1 recognizable noun → proceed to step 2 → 3, with the step 3 proposed name built ONLY from those tokens. Gibberish/filler-only → do NOT auto-proceed; ask `Your request "<original message>" doesn't name a content domain. What kind of content type would you like to create (e.g. news, blog, press release, product)?` with `Cancel` + free-text; free-text restarts 1b, `Cancel` → `cancelled`. Same gate applies when 1c's rebuilt query would be empty — do NOT dispatch a blank `search_metadata`. STRICTLY DO NOT fabricate a name from tokens absent from the message. Full rule + examples → `references/discovery-details.md#1d`.

**Prompt templates** (has-matches, zero-matches direct auto-proceed, zero-matches delegated, "Provide an FQN" follow-up) → `assets/discovery-prompts.md`. Copy verbatim.

**1d output shape — TWO separate outputs, never merged (the #1 reported UX defect):**

1. **Chat markdown FIRST** — the `Top <N> matching content types:` header + the `FQN | Description | Location` table (Output 1 in `assets/discovery-prompts.md`). Plain chat text, NOT the tool.
2. **THEN `ask_user_tool`** whose `question` is EXACTLY `Found matches. Pick one:` (verbatim, one short sentence) with the 4 FIXED options: `Use existing: <row-1 FQN>` / `Provide an FQN` / `Create new: <newName>` / `Cancel`.

**STRICTLY DO NOT:** write any preamble/prose sentence before or instead of the table; put the table, its columns, or the `(checked supported… / org check skipped…)` suffix INSIDE the `question` field (it renders as one flat line with no markdown — the reported broken wall of text); paraphrase or "make more helpful" the `question` (it is verbatim `Found matches. Pick one:`); add a `Use existing:` option per row (options are FIXED at 4 — extra rows are reached via `Provide an FQN`). Everything structured goes in the chat markdown of Output 1; the `question` field stays a single plain sentence. → `assets/discovery-prompts.md`, copy verbatim.

**Routing after the user replies:**

| User pick | Next action |
|---|---|
| `Use existing: <Name>` | Go to **step 1e** with `fqn = <namespace>__<Name>` (default namespace `c` for local matches whose folder isn't namespaced). |
| `Provide an FQN` (only present when `showFqnOption = true`) | Ask the follow-up in `assets/discovery-prompts.md`. On reply → **step 1e** with that FQN. |
| `Create new: <contentTypeName>` | Continue to step 2 → step 3. |
| `Cancel` | Emit `cancelled` outcome per § Invocation contract, print `Cancelled. No files written.`, then `Task Completed`. |

STRICTLY DO NOT print the pick list and announce "proceeding to create a new one" in the same message. The user picks, not you.

### 1e. Retrieve and reconcile

Reached when 1d resolves to a match / provided FQN, OR when the caller invoked with `{fqn}`. Goal: return `{fqn, schema}` matching the org.

**Namespace gate:**

- **Custom FQN** (`c__*`, non-platform namespace) → run `sf project retrieve start --metadata ContentTypeBundle:<DeveloperName> --target-org <alias> --json`. Always retrieve for custom.
- **OOTB FQN** (`sfdc_cms__*`) → skip `sf project retrieve start` (returns nothing usable). **This branch needs a live `metadata-grounding` schema, regardless of which flow surfaced the FQN** — `get_content_types_for_workspace` (Flow 2) never returns a schema, only `{fqn, name, description}`. If 1c already recorded `grounding=unavailable`, do NOT attempt `query_metadata` — go straight to the error below. Otherwise dispatch `query_metadata({ metadataType: "ContentTypeBundle", id: "<grounding row id from 1c>" })` NOW for the picked FQN only, and resolve the schema from its response (fall back to `describe_metadata` if it returns no schema payload). If that response is error/empty/non-schema, surface `Can't resolve OOTB FQN "<fqn>" without a real schema from metadata-grounding. Retry when grounding is back, or provide a custom FQN.` and exit with `error`. **Never fabricate OOTB schemas from training data** — "sfdc_cms__news typically has title/body/summary…" IS the bug thought that poisons 3–7. Fail closed. Full rule → `references/retrieve-and-reconcile.md` § Namespace gate.

**Reconciliation** — compare retrieved schema against `<sfdx-source>/contentTypes/<DeveloperName>/schema.json`. Full matrix + drift template + routing → `references/retrieve-and-reconcile.md`.

**Routing outcomes:**

- Not in local, retrieved → write local, return `{fqn, schema=retrieved}`.
- In both, match → return `{fqn, schema=local}`.
- In both, differ → drift prompt (`Deploy local to org` → step 5/7; `Overwrite local with org` → replace files, return; `Cancel` → exit).
- In local only → print step 7.5 summary first (user sees what they'd deploy), then offer deploy (5/7) or cancel.
- In neither → re-dispatch 1d pick with `Try a different FQN` option.

**On success, return `{fqn, schema}` and continue to 7.5 → 8.** No proposal-of-fields, no re-validation — reconciled schema is source of truth. Create-only for new; reconcile-only for existing.

"Create new" in 1d is the ONLY path that proceeds to step 2.

### 2. Resolve target org

Prefer the SF CLI default (alias from `sf config set target-org=<alias>` or `defaultUsername` in `sfdx-project.json`). Resolve to `<orgAlias>` and pass as `--target-org <orgAlias>` on every `sf` call. When a default is set, this step is silent.

**No default — fallback:** run `sf org list --json` (silent):

- **Zero authenticated orgs** → emit `error` with message `No authenticated Salesforce org found. Run sf org login web and re-run.`, print, stop.
- **Exactly one** → use silently as `<orgAlias>`. Do not modify `sf config`.
- **Two or more** → dispatch `ask_user_tool` with question `No default Salesforce org is set. Pick the org to use for this run:` and one option per org labelled `<alias> (<username>) [<devhub|sandbox|scratch|prod>]`, plus `Cancel`. On pick, use as `<orgAlias>` for this run only (do NOT run `sf config set target-org=…`). `Cancel` → emit `cancelled`, print `Cancelled. No files written.`, `Task Completed`.

The picked alias applies to every subsequent `sf` call this run (1e retrieve, 5 dry-run, 7 deploy).

### 3. Propose fields and get user approval

Preconditions: 1c dispatched `search_metadata` (or recorded `grounding=unavailable`), and 1d resolved to `Create new: <contentTypeName>` in the previous turn. Other 1d picks route elsewhere: `Use existing` / `Provide an FQN` → 1e; `Cancel` → emit `cancelled`.

If you just printed a pick list via `ask_user_tool` and the user hasn't replied, stop — your turn is over.

**3a. Determine field properties (agent-internal).** Set `apiName` (camelCase), `title` (human-readable), `lightning:type`, `required`. Default-minimal: no `lightning:textIndexed`, `lightning:localizable`, length/range bounds, `enum`, `const`, `placeholderText` unless the user asked.

**Content-type name must be derivable from the user's message.** `<contentTypeName>` and its `title` must be built from tokens actually present (PascalCase/word-order shaping OK — `laptop review` → `LaptopReview`). STRICTLY DO NOT invent from thin air, from an unrelated open tab, or from prior-session context. If 1d's sanity gate passed but the noun set is thin (one word), use that word — do not embellish. Proposing a name with tokens absent from the message IS the hallucination anti-pattern; stop and restart 1d's gate.

Initialize `userEditedFields = false` agent-internally. Governs step 6's branching. Flipped to `true` only when the user types free-text edits in the 3b loop (see `references/edit-fields-loop.md`). `Edit fields` → `Approve as shown` without typing any edit leaves it `false` — proposal accepted unchanged.

**3b. Present proposed fields — markdown table FIRST as chat-visible text, THEN `ask_user_tool` in the same turn.** Do NOT collapse the table into the tool prompt — the UI strips formatting and the user cannot approve informed.

Message 1 (chat-visible plain text):

```text
Proposed fields for `<contentTypeName>` at `<sfdx-source>/contentTypes/<contentTypeName>/`:

| # | API name | Type | Required | Constraints | Title |
|---|---|---|---|---|---|
| 1 | `title` | `lightning__textType` | yes | maxLength: 200 | Title |
| 2 | `body`  | `lightning__richTextType` | yes | — | Body |
```

Constraints format follows 7.5 (see `references/schema-summary-format.md`): comma-separated `key: value` pairs for any per-field constraint asked or proposed — `maxLength`, `minLength`, `minimum`, `maximum`, `enum`, `const`, `lightning:localizable`, `lightning:allowedUrlSchemes`, etc. Use `—` when a field has no constraints beyond `required`.

Message 2 (same turn): dispatch `ask_user_tool` with question `Approve these fields, edit them, or cancel?` and options `Approve`, `Edit fields`, `Cancel`.

- `Approve` → step 4.
- `Edit fields` → follow the loop below. Loop until approved.
- `Cancel` → emit `cancelled`, print `Cancelled. No files written.`, `Task Completed`.

**Edit-fields loop** — each round reprints the current table (chat-visible), then dispatches `ask_user_tool` with `Approve as shown` / `Cancel` options and accepts free-text edit instructions. **Free-text tool result IS the edit instructions — parse and apply, then loop; do NOT stop.** Full template + anti-stop guidance → `references/edit-fields-loop.md`.

### 4. Create files (silent — confirm in two lines max)

Precondition: step 3b returned the user's `Approve` in the immediately preceding turn. No file write before approval.

Create `<sfdx-source>/contentTypes/<contentTypeName>/`. Use the already-loaded `assets/schema-example.json` (per § Schema rules — do NOT re-fetch a sibling `schema.json`). Generate `schema.json` for the approved fields and `<contentTypeName>.contentTypeBundle-meta.xml` with exactly these four lines, swapping only `<masterLabel>`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ContentTypeBundle xmlns="http://soap.sforce.com/2006/04/metadata">
    <masterLabel><contentTypeName></masterLabel>
</ContentTypeBundle>
```

Do NOT add `<displayName>`, `<description>`, `<contentTypeFields>`, `<fieldType>`, or any legacy SOAP element — those fail the validator. Per-field forbidden keys (`type`, `format`, `default`, empty `lightning:uiOptions`) → `references/schema-rules.md`.

After writing, print exactly two lines:

```text
Created <sfdx-source>/contentTypes/<contentTypeName>/schema.json
Created <sfdx-source>/contentTypes/<contentTypeName>/<contentTypeName>.contentTypeBundle-meta.xml
```

Then proceed to step 5. Before dispatching 5a, run the pre-deploy schema checklist in `references/pre-deploy-checklist.md` (agent-internal, do not print). Fix in place and re-check.

### 5. Validate (mandatory)

Step 5 is unconditional. Skip only if step 1d ended with `Use existing`. `grounding=unavailable` does not skip step 5 (different auth path). Do not suggest the dry-run as a command for the user to run — you run it.

**5a. Run** (no preamble in chat):

```bash
sf project deploy start --source-dir <sfdx-source>/contentTypes/<contentTypeName> --target-org <orgAlias> --dry-run --json
```

**5b. Result handling:**

- `result.status === "Succeeded"` → print one line: `Validated against <org>: Succeeded (dry-run — nothing deployed yet).` This is NOT a terminal state — your next action is step 7a's `ask_user_tool`.
- `result.status === "Failed"` with `componentFailures` → step 6 (auto-fix).
- `result.status === "Failed"` with zero `componentFailures` → CLI/auth issue. Show the raw response, ask the user to verify `sf org list`, source path, and `sfdx-project.json`. Do not count as one of the 3 attempts.

### 6. Fix validator failures — silent auto-fix or ask-first, based on `userEditedFields`

Branches on `userEditedFields` (set in 3a). The split reflects who authored the broken schema:

- `false` → user accepted the agent's proposal unchanged. Validator failure is the agent's mistake. **Silent auto-fix.**
- `true` → user typed edits in 3b. Failure may reflect intent (e.g. `enum` on integer, `default` on text) only the user can resolve. **Show planned fixes, ask first.**

Both branches share the sweep-the-whole-schema principle and the 3-attempt cap on agent-driven fixes. Each attempt fixes every problem the validator could possibly flag across the whole schema, not one field at a time — validators only report 1–2 errors per pass; don't fall into one-field-per-attempt. Error-to-fix mapping (incl. safe vs. intent-changing `Kind`) → `references/deployment-errors.md`.

**6a. Silent auto-fix (`userEditedFields === false`)**

1. Read every `componentFailures[].problem`.
2. Sweep `properties` for the same class of issue. E.g. one `placeholderText missing` → audit all `lightning:uiOptions`; one `format` rejected → strip `type`/`format`/`default` from every field; one disallowed type-specific key → audit every field of that `lightning:type`.
3. Re-write once, re-run step 5 once. Counts as one of 3 attempts.

If still failing after 3 attempts: surface the last error and route to 6b's `Let me edit` follow-up. On abandon / exit without successful validation, emit `error` with the last validator error as `message`, stop.

**6b. Ask-before-fix (`userEditedFields === true`) — show planned fixes**

The user authored something the validator rejected. Do NOT silently rewrite their intent.

Message 1 (chat-visible plain text, NOT in `ask_user_tool`) — enumerate every `componentFailures[].problem`, look up fixes in `references/deployment-errors.md`:

```text
Validation failed on your edited schema. Planned fixes:

  ✗ <field>: <one-line error description>
      Planned: <fix> (<impact>)
  ✗ <field2>: …
      Planned: …
```

Include EVERY error this pass, grouped by field. When a fix drops/changes a user-authored constraint (`enum`, `const`, `lightning:localizable`, numeric bound, type swap), the parenthetical MUST state the concrete consequence — "loses numeric ordering", "no longer restricted to enum values", "text won't localize" — not "changes the type." Kind=safe fixes (`default` strip, `type`/`format` strip, `allowedUrlSchemes: ["https"]`) get the literal `safe: validator hygiene, no intent change`.

Message 2 (same turn) — dispatch `ask_user_tool` with question `How would you like to proceed?` and options `Apply these fixes and continue` / `Let me edit — I'll fix it, then re-validate` / `Cancel`.

Route:

- **`Apply these fixes and continue`** → apply exactly the fixes shown, re-write once, re-run 5 once. Counts as one of 3 attempts. Success → 7a. Fail → loop back to top of 6b with the new errors (`userEditedFields` stays `true`).
- **`Let me edit`** → print file paths from step 4's two-line confirmation and validator errors verbatim, dispatch `ask_user_tool` with question `Reply when you're done editing.` and options `Re-validate` / `Cancel`. `Re-validate` → re-run step 5 (user-driven cycles do NOT count against 3 attempts). `Cancel` → emit `cancelled`, print `Cancelled. Your edits remain at <sfdx-source>/contentTypes/<contentTypeName>/`, `Task Completed`. Do NOT delete the files.
- **`Cancel`** → emit `cancelled`, print `Cancelled. No files written.`, `Task Completed`.

If the 3-attempt cap on `Apply these fixes` is exhausted: surface the last error and route to the `Let me edit` follow-up (do NOT re-offer `Apply these fixes`). On subsequent `Cancel`, emit `error` with the last validator error as `message`, stop.

### 7. Deploy (yes/no — wait for the next user turn)

Step 5's success unlocks step 7; it does not replace it. Ask the user via `ask_user_tool` before any deploy or terminal marker.

**7a.** Dispatch `ask_user_tool`:
- Question: `Validation succeeded. Deploy "<contentTypeName>" to <org> now?`
- Options: `Yes - deploy now` / `No - I'll deploy later`

**7b. User says no**: emit `not_deployed` outcome and stop. Print one line —

```text
Validated. Nothing deployed. To deploy later: sf project deploy start --source-dir <sfdx-source>/contentTypes/<contentTypeName> --target-org <orgAlias>
```

Return outcome: `{ status: "not_deployed", fqn: "<namespace>__<contentTypeName>", schema: null, message: "<the line above>" }`. Do NOT run step 7.5 or step 8 — the type isn't in the org.

**7c. User says yes**: run

```bash
sf project deploy start --source-dir <sfdx-source>/contentTypes/<contentTypeName> --target-org <orgAlias> --json
```

**7d. Deploy errors:**

- With `componentFailures` (rare — occurs after manual edits between validate and deploy, or transient org-side state change): route to step 6's branch matching the current `userEditedFields` flag. Because reaching 7d always follows at least one user-visible turn (step 7a's `Yes - deploy now`), the flag is authoritative for who last authored the file. On successful re-validation, re-ask step 7a's deploy prompt. On unrecoverable failure (auto-fix exhausted then cancelled, or user cancelled in 6b), emit `error` outcome per § Invocation contract with the last validator error as the `message`, then stop.
- With zero `componentFailures` (auth/network): emit `error` outcome per § Invocation contract with the raw response summary as the `message`, then stop.

**7e. Success**: print one line — `Deployed <contentTypeName> to <org>. Component IDs: <ids>.` This is a `success` terminal state — the outcome to emit at task end is `{ status: "success", fqn: "<namespace>__<contentTypeName>", schema: <the just-deployed schema>, message: "<the line above>" }`. Continue to step 7.5. Do not run any other command between here and step 7.5 (see Rule 4).

### 7.5. Schema summary (on every resolved-schema path)

Runs whenever `{fqn, schema}` has resolved, regardless of source or of `suppressCreateContentPrompt` — informational, not a turn. Run ONCE per run — track `summaryPrinted` agent-internally; 1e's "local only" branch prints it before deploy-or-cancel, so a subsequent 7e must not re-trigger it.

Run when: 1e returned `{fqn, schema}` with non-null schema; 7e succeeded; 1e's drift-prompt "Deploy local to org" reached 7e; or 1e's "local only" branch before deploy-or-cancel. Apply the `summaryPrinted` gate.

Do NOT run when: user picked `Cancel`, 7b (deploy-later), any error path with no resolved schema, or `summaryPrinted === true`.

Print as chat text (NOT in `ask_user_tool`):

```text
Content type "<fqn>" is ready. Schema:

| # | API name | Type | Required | Constraints | Title |
|---|---|---|---|---|---|
| 1 | `title` | `lightning__textType` | yes | maxLength: 200 | Title |
| 2 | `body`  | `lightning__richTextType` | yes | — | Body |
```

Column definitions, constraint rules, sort/truncation (20-property cap), do-not-print list → `references/schema-summary-format.md`.

Continue immediately to step 8 (no separate turn, no intermediate prompt).

### 8. Trailing "create content?" prompt (gated by `suppressCreateContentPrompt`)

Reached only from `success` — step 8 controls only whether an extra prompt is shown after it. Gate: `suppressCreateContentPrompt === true` → skip entirely, emit `success` + `Task Completed` (the prompt would duplicate a turn the caller already drives). Otherwise run when success came via: 1e returned `{fqn, schema}`, 7e succeeded, or 1e drift-prompt "Deploy local to org" reached 7e. Do NOT run on `Cancel` (`cancelled`), 7b (`not_deployed`), or any error path (`error`).

Dispatch `ask_user_tool` with question `Would you like to create content using "<fqn>" now?` and options `Yes — create content now` / `No — I'm done`.

- `Yes` → hand off to `experience-cms-content-generate` with `{ fqn, schema, suppressCreateContentPrompt: true }`; also pass `intent: <residualIntent>` when 1a captured one (e.g. `create a news type and also create an article about our Q4 launch` → forward `create an article about our Q4 launch`). Omit `intent` when no residual. Don't loop back. Emit `success` + `Task Completed`.
- `No` → print `Done. FQN: <fqn>.`, emit `success`, `Task Completed`.

Do not run any command after step 8 resolves (Rule 4).

## Schema rules (validator truth)

CMS deploy validator is source of truth. Full ruleset → **`references/schema-rules.md`** (root, per-field keys, `lightning:uiOptions` sharp edge, per-type accepted keys, quirks). Load before step 4 and step 6.

**Also load `assets/schema-example.json` before step 4** — canonical shape reference, every supported `lightning:type` in default-minimal form. Do NOT use a sibling `schema.json` as reference just because step 1b/1e primed it in context — siblings carry user-specific constraints (`maxLength`, `lightning:localizable`, indexing) that would leak in without justification.

Non-negotiables: root has `unevaluatedProperties: false` (root only), no `$schema`; per-field only `title` / `description` / `lightning:type` / `lightning:uiOptions` + the type's accepted keys; never `type` / `format` / `default` / empty `lightning:uiOptions`; only `sfdc_cms:metadataContent` mixin.

## Anti-patterns

Full anti-pattern table (violation / rationalization / correct action) → `references/anti-patterns.md`. If you catch yourself thinking one of the "bug thoughts" listed there, STOP — that thought is the bug.

## Notes

- Folder name, `<masterLabel>`, and the bundle's `title` should be consistent (PascalCase folder, human-readable label and title).
- Avoid `lightning__fileType` and `lightning__contentReferenceType` — currently unsupported.
- Eval datasets live in `packages/adk-eval/eval/domains/experience-cms-content-type-generate/`, not in `tests/evals/`.

## Reference file index

- `references/agent-checklist.md` — mandatory progress checklist and tripwires.
- `references/schema-rules.md` — validator ruleset (bundle root + per-field + `lightning:uiOptions` + per-type accepted keys + validator quirks).
- `references/pre-deploy-checklist.md` — agent-internal schema sanity check before step 5.
- `references/deployment-errors.md` — validator error → fix mapping (step 6).
- `references/anti-patterns.md` — bug-thought catalogue.
- `references/discovery-details.md` — rationale for 1b/1c/1d rules.
- `references/discovery-query-rules.md` — single source of truth for how the `search_metadata` query is constructed. Referenced from step 1c here AND from the parent skill `experience-cms-content-generate` (as a drift-safety net).
- `references/retrieve-and-reconcile.md` — step 1e reconciliation table and drift routing.
- `references/edit-fields-loop.md` — step 3b edit-loop template and routing table.
- `references/schema-summary-format.md` — step 7.5 column/sort/truncation rules.
- `assets/discovery-prompts.md` — step 1d pick-list template + zero-matches variants.
- `assets/schema-example.json` — reference schema covering every supported `lightning:type`.
