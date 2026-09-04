---
name: experience-cms-content-generate
description: "Creates, edits, and publishes Salesforce CMS content of any kind — any domain, any topic. Single and bulk: create many in parallel, edit one or many, publish all or a subset. Use this skill ANY TIME a user asks to create, generate, write, draft, author, or add content, OR to update, edit, or revise a content record, OR to publish it, OR to delete/remove a content record. Triggers like \"create a <thing> about X\", \"create 5 <things>\", \"update content <id>\", \"publish content <id>\", \"publish the record <id>\", \"make <id> live\", \"delete content <id>\" — where <thing> is any user-named content type. Activates FIRST whenever content authoring, editing, publishing, or deletion is mentioned, regardless of subject. Handles the full workflow: finding the content type, resolving the workspace, creating content, editing or publishing it — including a record identified by its variantId. Does not apply to defining a content type / schema (use experience-cms-content-type-generate), cloning, versioning, workspaces, or media."
metadata:
  version: "1.1"
  domains: ["Experience"]
  minApiVersion: "64.0"
  relatedSkills:
    - "experience-cms-content-type-generate"
    - "experience-cms-content-render"
  cliTools:
    - tool: ["sf"]
      semver: ">=2.0.0"
  mcpTools:
    content-write: { tools: ["create_cms_content", "update_cms_content_variant", "publish_content", "get_or_create_cms_workspace_and_web_app_channel"], semver: ">=1.0.0" }
    content-readonly: { tools: ["get_content", "get_content_variant"], semver: ">=1.0.0" }
    skill_bridge: { tools: ["load_skill", "search_skills"], semver: ">=1.0.0" }
---

# Creating CMS Content

Universal skill for creating Salesforce CMS content records — orchestrates type discovery, workspace resolution, and `create_cms_content` dispatch against an existing `ContentTypeBundle`.

**Content generation is server-side, always.** `create_cms_content` / `update_cms_content_variant` take the goal / edit instruction as `prompt`; the server generates + validates the body against the schema and returns the persisted record. Agent never walks the schema, assembles `contentBody`, pre-validates, or regenerates rejected fields (Principle 3).

## Scope

**Creates managed content records in Salesforce CMS** — instances authored against an existing `ContentTypeBundle`.

**Use when the user wants to:** create a content record of any kind (single or bulk) from a free-text prompt against an existing CMS type; edit/refine session items; **update/edit** OR **publish** a record identified directly by `managedContentVariantId` / `managedContentId` — even if NOT created this session (Step 0 → UPDATE / PUBLISH entry); publish all or a subset; **delete/remove a record** — this skill OWNS the delete request and routes to a hard stop (Step 0-D); never surface the internal reason.

**DO NOT use when the user wants to:** define a new content type / schema (use `experience-cms-content-type-generate`); unpublish, clone, or version a record; manage workspaces / folders / channels; attach images / media; apply branding.

**"Create image/media content" is NOT a pre-flight scope-out** (only literal binary file attach/upload is the excluded "attach media" above). Creating an image/video content *record* (e.g. from a URL) enters the normal flow — resolve type + workspace, dispatch `create_cms_content`, never refuse up front or propose a REST / UI workaround. `sfdc_cms__media` is server-decided: let the tool return the error, then hard-stop per Principle 15 (`references/error-recovery.md`).

## Before You Start

**Follow steps in order — do not skip or reorder.**

Every successful run MUST end by dispatching `create_cms_content` (≥1×), each carrying the goal via `prompt`.

Interaction-minimal — the only pre-dispatch question is Step 3 (workspace). Never ask for goal refinement, mode, or body details. **Step 1 is silent.** FQN in prompt → Step 2 fast-path; else Step 2a delegates with no intervening `ask_user_tool`. **Bulk exception:** Step 4 presents topic prompts for approval.

**VERBATIM QUESTION CONTRACT — EVERY `ask_user_tool`, no exceptions.** Full rule → `references/ux-rules.md`. Every question goes through `ask_user_tool` (never plain text); before ANY call, open `assets/questions.md` and copy BOTH the `question` string AND the `answers` array **character-for-character**, filling only `<placeholders>` — never reword/shorten the `question`, never add/drop/reorder `answers`, never put list content into an answer. No template covers it? STOP and re-read `assets/questions.md` — never compose one ad hoc.

## Workflow Overview

```text
- [ ] Step 1: Understand intent (silent — domain, count, FQN if present)
- [ ] Step 2: Resolve content type — fast-path (Buckets 1/2/3) or delegate → contentTypeFqn
- [ ] Step 3: Resolve workspace — UIBundle options or manual ID
- [ ] Step 4: Build payload — single or bulk (topic approval if bulk)
- [ ] Step 5: Dispatch create_cms_content (parallel for bulk)
- [ ] Step 6: Display content body + summary
- [ ] Step 7: Post-action loop — Edit / Publish / End
- [ ] Step 8: Edit — update_cms_content_variant
- [ ] Step 9: Publish — publish_content
- [ ] Step 10: Post-publish — Create more / Render (if UIBundle) / End
```

## Step 0: Route the Intent (run FIRST, always)

**Before Step 1, classify into exactly one intent and route.** update/publish/delete are first-class entry points — NOT only tails of the create flow. Opening with one of those verbs → do NOT freelance (pick tools by intuition, run SOQL, guess a variant ID). Read the opening verb and route:

| User intent (opening verb) | Route to |
|---|---|
| create, generate, write, draft, author, post, add, compose; "create N `<things>`" | **CREATE** — continue to Step 1 |
| update, edit, change, modify, revise an existing record | **UPDATE entry** — Step 0-U |
| publish an existing record | **PUBLISH entry** — Step 0-P |
| delete, remove, destroy a record | **DELETE** — Step 0-D (hard stop) |
| ambiguous (can't tell create vs update vs publish) | `ask_user_tool` disambiguation (Create new / Update existing / Publish existing / Cancel), route on the answer |

**No-drift STOP rule (every route).** If the route's required `content-write` tool (`create_cms_content`/`update_cms_content_variant`/`publish_content`) is unavailable on this bridge, **STOP**, print the actionable user-facing message, end the turn. Never substitute SOQL, `sf data`, CLI, a sibling tool, or the `contentBody` channel — tool-unavailable and unsupported-operation are terminal, never a fallback trigger. **Exact message + per-route slots + may/may-not-say → `references/intent-routing.md` § No-drift STOP rule.**

### Step 0-U (UPDATE) and Step 0-P (PUBLISH) — direct-entry paths

**Full procedural detail → `references/intent-routing.md`.** Direct-entry counterparts to in-session Step 8 (edit) / Step 9 (publish) — a record identified directly, possibly from a prior session or another user (editing/publishing is NOT session-only). Load-bearing invariants:

- **Hard identifier gate — BEFORE any tool call.** Target `managedContentVariantId` comes ONLY from (a) the session registry or (b) a user-typed identifier (`MC…`/`20Y…`/`9Ps`). Name-only, no ID, not in registry → **STOP and ask** via `ask_user_tool` ("Which record should I work with?" question, copied EXACTLY, answers `["Cancel"]`). **You may NOT locate the record yourself** — no `search_content`, discovery/listing tool, SOQL, or guessed ID.
- **Resolve by prefix + validate before acting** → `references/identifier-resolution.md` (`9Ps`→`get_content_variant`; `MC…`/`20Y…`→`get_content`). Read fails → STOP; never edit/publish blindly.
- **0-U** → Step 8c (after MANDATORY full-body display + edit-instructions prompt), closes via Step 7 dialog. **0-P** → Step 9b, closes with publish confirmation and **ends the turn** (no Step 10 — no session context). Neither runs Steps 1–5.

### Step 0-D: DELETE (hard stop)

Delete is not available (no delete capability — internal detail, do NOT surface). Print **exactly and only** this message, nothing else:

```text
Deleting content isn't supported here. To delete this content, open it in Salesforce CMS and use the Delete option there.
```

**Say NOTHING before or after** — no preamble, reasoning, rule-restatement, tool/server names, or meta-narration; the user sees only the plain message. End the turn. Do NOT offer `unpublish_content`, SOQL, or CLI as a substitute — the CMS UI is the only path to surface.

## Step 1: Understand Intent

**Silent step — NEVER ask anything here.** Extract agent-internally, then go straight to Step 2. No "Let me clarify…" turn, no `ask_user_tool`, no content-type menu — even a vague prompt (`generate new content for Q4 launch`) has everything Step 2 needs. About to dispatch a question in Step 1 (clarify, content-type menu, "type in mind?", "how many?")? That IS the bug — move to Step 2. Parse the message for:
- **Content domain** (article, blog, news, FAQ, …) — inferred as-is; no domain named is fine.
- **Quantity** — explicit count → that number; "multiple"/"several"/"a few"/"some" → agent chooses 4–5; no indicator → single.
- **Content-type reference** — capture any token that looks like a content type name (exact FQN, single-underscore near-miss, bare developer name, natural-language name) verbatim. Do NOT classify here — Step 2 assigns the bucket.

Do not strip or rewrite the message — the original is the creative direction for Step 4 topic prompts and what Step 2a passes to the sibling verbatim as `intent`.

**Multi-type gate — the ONE question Step 1 may raise.** If the prompt spans **≥2 distinct content TYPES** (each its own `ContentTypeBundle`, e.g. `grooming packages` AND `service area coverage`), you MUST ask the user to pick ONE before Step 2 (one type per run; two corrupts the delegation contract). Dispatch the Step 1 multi-type prompt VERBATIM (answers = distinct domains in the user's words + `Cancel`), carry ONLY the chosen domain forward as `intent`. SOLE exception to "never ask" — fires only on ≥2-distinct-types, never goal/mode/quantity. Multiple topics of ONE type (`5 blog posts`) do NOT trigger it (bulk). Rule + examples → `references/content-type-classification.md` § Multi-type gate.

## Step 2: Resolve the Content Type

**Classify Step 1's captured content-type reference** into one of four buckets — full detection rules, examples, routing → `references/content-type-classification.md`. Summary:

- **Bucket 1 — Exact FQN.** Matches `^[a-zA-Z_][a-zA-Z0-9_]*__[A-Za-z][A-Za-z0-9_]*$` (`c__BlogPost`). Capture `contentTypeFqn`, Step 3. **Silent.**
- **Bucket 2 — Auto-correctable near-miss.** Single-underscore between known namespace and name (`c_news`→`c__news`). Auto-correct, announce in chat (no `ask_user_tool`), Step 3.
- **Bucket 3 — Low-confidence FQN-ish.** Bare name (`BlogPost`→propose `c__BlogPost`) or unknown-namespace single-underscore. Dispatch the Step 2 FQN-correction prompt, route on the answer.
- **Invalid-FQN gate.** Token meant as FQN (has `__`) but malformed, not a Bucket 2 near-miss (`c__`, `__Foo`, `c__Blog Post`, `c__123`) → do NOT delegate as free text; dispatch the FQN-correction prompt (`Let me provide a different FQN`/`Cancel`), restart Step 2 on the new string.
- **Bucket 4 — Natural language or no token** (`blog post`). Delegate — Step 2a.

**Fast-path invariants (Buckets 1/2/3):** once the FQN is captured, do NOT verify it in the org, delegate, scan `contentTypes/`, dispatch `metadata-grounding`, retrieve, or read `schema.json`. A bad FQN fails deterministically as `INVALID_TYPE` at Step 5. On the delegated path the sibling owns scan, grounding, pick question, create-new + deploy, FQN construction, retrieve-and-reconcile.

### 2a–2d. Delegate to the sibling (Bucket 4 only)

**Full protocol → `references/delegation-protocol.md`.** In short: **2a** resolve workspace FIRST (Step 3 → `contentSpaceOrFolderId`), print banner `Resolving the content type for your request…`, invoke via `mcp__skill_bridge__load_skill("experience-cms-content-type-generate")` (NOT built-in `Skill` — returns `Unknown skill`), pass `{ intent: "<user message verbatim>", suppressCreateContentPrompt: true, <scope> }` (`<scope>` = `spaceId` `0Zu` OR `folderId` `9Pu`, exactly one, never `baseType`); no pre-delegation question. **2b** — while the sibling runs this skill is PAUSED (no Step 4+ call until a terminal outcome; interleaving corrupts its state machine). Consume `{ status, fqn, message }` (ignore any `schema`), route strictly on `status`:

| `status` | Action for this skill |
|---|---|
| `success` (`fqn` present) | **Print the sibling's `message` verbatim** (carries type + deploy line); if empty, print `Using content type \`<fqn>\`.` Then Step 2c. |
| `not_deployed` (`fqn` present) | **STOP.** Print `message` verbatim. Do NOT continue to Step 3 — `create_cms_content` fails `INVALID_TYPE` against a local-only bundle. |
| `cancelled` | **STOP silently.** Print `Session ended.` and exit. Do NOT loop back into the sibling. |
| `error` | **STOP.** Print `message` verbatim (carries reason + recovery hint). Do NOT retry or work around. |
| `load failed` (bridge `Unknown skill`/error — sibling never ran) | **STOP** per `references/delegation-protocol.md` § 2b (terminal, NOT a fallback — no local scan, grounding, or workspace call). Retry once via `search_skills`→`load_skill` first. |

**2c** (only on `success`) — verify `fqn` matches the FQN regex; missing/malformed → surface re-run message + `ask_user_tool` (`Retry with an explicit FQN`/`Cancel`); then capture `contentTypeFqn`, Step 3. **2d** — never call `metadata-grounding`, `sf project retrieve`, re-present/re-pick, or build FQNs from folder names (sibling owns all of that); five drift signals → hard-stop to the `load failed` row; never downgrade `not_deployed` to `success`. On a manual space the 2a call is the Layer-2 confirmation — invalid/not-found → HARD STOP, re-ask via the invalid-ID template.

## Step 3: Resolve the Workspace — Question 1

**When Step 3 runs depends on how Step 2 resolved the type:** **fast-path** (Buckets 1/2/3) → run it here, after Step 2. **Delegation path** (Bucket 4) → runs EARLY, first action of Step 2a before the sibling is dispatched, so `contentSpaceOrFolderId` scopes the sibling's discovery; do NOT re-run or re-ask after the sibling returns. Same resolution steps both cases.

Silently scan the local project for UIBundle directories, then present a single `ask_user_tool` question with all options. **Full discovery + routing + validation → `references/workspace-resolution.md`.** In short:

- **Discovery (silent):** scan `uiBundles/` under each `sfdx-project.json` package path (fallback: recursive), read each `<name>.uibundle-meta.xml` `<masterLabel>` → `{ developerName, masterLabel }`. Zero → "no local UIBundles" variant. Never invent a workspace, run SOQL, or read `ui-bundle.json`.
- **Ask (single question):** dispatch the "Step 3 — Workspace resolution" template from `assets/questions.md` via `ask_user_tool` (never plain text); copy `question` + `answers` **VERBATIM**, reword/rename/drop nothing. **No-UIBundle variant is fixed copy — `question`: `"Which content space or folder should I create the content in? Provide the ID (Content Space IDs start with `0Zu`; Folder IDs start with `9Pu`)."`, `answers`: `["Cancel"]`.** UIBundle-found, manual-ID, and invalid-ID variants → `assets/questions.md`.
- **UIBundle pick** → `get_or_create_cms_workspace_and_web_app_channel`(developerName, masterLabel); returned `spaceId` = `contentSpaceOrFolderId`; record `workspaceMethod=uibundle` + `channelId`; persist `channelId` to `uiBundles/<developerName>/public/content-metadata.json` (merge). Tool failure → retry prompt.
- **Manual ID** → record `workspaceMethod=manual` (no `channelId` → Step 10 render hidden); manual-ID prompt with "Go back". **Validate (prefix+length necessary NOT sufficient):** L1 `0Zu`→`spaceId` / `9Pu`→`folderId`, 15/18 alphanumeric. L2 on FIRST call touching the space (delegation: `get_content_types_for_workspace`; fast-path: `create_cms_content`) — invalid/not-found → STOP, surface verbatim, re-ask via **invalid-ID template**. No org picker.

## Step 4: Build the Create-Content Payload

**HARD ENTRY GATE — `contentTypeFqn` MUST come from Step 2** (Bucket 1/2/3 fast-path capture OR `status: success` sibling outcome). Not run Step 2 (and delegated on Bucket 4)? STOP, back to Step 2. Never invent, guess, or default a type — **picking `sfdc_cms__news` or any base/standard type without Step 2 is a regression.** No FQN → Bucket 4 → delegate FIRST. Front-loading the create tool via ToolSearch before Step 2 is the same bug.

Goal passes as `prompt`; server generates + validates the body. Agent only shapes the payload and generates a title. Inputs: `contentType` = Step 2 `contentTypeFqn`; `contentSpaceOrFolderId` = Step 3; `prompt` = `[USER GOAL]` (message verbatim for single, or Step 4.B.2-approved topic prompt for bulk). **Title stays agent-side** — concise, on-topic, customer-facing, reflecting `[USER GOAL]`.

- **Single (quantity = 1):** `assets/payloads/create-content-single.json`. Required: `contentType`, `contentSpaceOrFolderId`, `title`, `prompt` (verbatim). Optional (`urlName`, `contentKey`, `externalId`, `apiName`) only when the user named them. **Never include `contentBody`** — mutually exclusive with `prompt`.
- **Bulk (quantity > 1):** generate N distinct topic prompts, present for approval (two-part: markdown list + `ask_user_tool`), then build N independent 1-element payloads (shared `contentType`/`contentSpaceOrFolderId`; per-item `title` + `prompt`). **Never combine into one `inputs` array — one call per item.** Flow → `references/bulk-batching.md`.

Full schema → `references/content-write-tool.md`; payload walkthrough → `examples/create-content-call.md`.

## Step 5: Execute the Create Call

Dispatch `create_cms_content` with the Step 4 payload; the server generates + validates and returns the record. Complex types can be slower.

### Bulk Content

**5a. Pre-dispatch confirmation (blanket approval)** — one confirmation for all items (prevents per-call prompts). Print chat `Ready to create all **<N>** content items in your org. Proceed?`, dispatch the Step 5a approval prompt. `Yes, create all` → 5b; `Cancel` → end session.

**5b. Dispatch N parallel single-item calls** per `references/bulk-batching.md`: exactly N `create_cms_content` calls, each a 1-element `inputs` array, all fanned out in one turn. Partial failure → register successes, surface failures (topic + error), dispatch retry prompt (retry re-dispatches failed items as fresh parallel calls). Total failure → apply "Bulk total-failure retry guards" in `references/error-recovery.md` first (bulk total-failure branch only).

## Step 6: Display Content Body and Summary

On success, print the **summary + content-body tables** from `assets/display-formats.md` (real markdown, every field; same for create/edit). **NEVER collapse to one-line `title · status · id`** — summary table MUST carry Content Key + Managed Content ID (omit only fields the response lacks). On failure, use `references/error-recovery.md`; surface the error verbatim, ask via `ask_user_tool`: `Retry / Refine goal and retry / Cancel` — **EXCEPT type-class-unsupported** (`sfdc_cms__media` / image / video), a hard stop (Principle 15): print ONLY this fixed copy verbatim (no preamble/rewording), then end turn: `Content generation isn't supported for content type \`<fqn>\` (type class: \`<class>\`). This skill can't author that type class. To create or edit this content, use the Salesforce CMS UI directly.` Server owns validation.

## Step 7: Post-Action Loop

After displaying the content body (create or edit), dispatch the Step 7 prompt from `assets/questions.md` (single or bulk variant by quantity). Route:
- `Edit content` → Step 8
- `Publish content` / `Publish all` → Step 9 with all variant IDs
- `Publish subset` → ask which items by number via the publish-subset template in `assets/questions.md`, then Step 9 with selected variant IDs
- `End session` → print one line: `Session ended. Content saved as draft.` and exit.

## Steps 8, 9, 10: Edit / Publish / Post-Publish

**Full procedural detail → `references/edit-publish-workflow.md`.** All three **MCP-only — no SOQL, no CLI** (read via `content-readonly`, write via `content-write`). Load-bearing summary:

- **Step 8 — Edit** (`update_cms_content_variant`). 8a scope (single, or Step 8a prompt for bulk) → 8b edit-instructions prompt (verbatim, applies to all selected) → 8c payload (`variantId` from item's latest response OR the Step 0-U ID; `prompt` verbatim; re-emit `title` ONLY on rename) → 8d dispatch (bulk = N parallel) → 8e back to **Step 6**, display **full updated body, every field** (NOT a diff table; re-fetch via `get_content_variant` if the response lacks it), then **Step 7**. Failures → `Retry / Refine edit instruction and retry / Cancel`; bulk total-failure → error-recovery guards.
- **Step 9 — Publish** (`publish_content` via `variantIds`). 9a scope (all / subset / default all) → 9b dispatch (in-session IDs, or the Step 0-P validated ID — direct-entry ends the turn after confirmation, no Step 10) → 9c on success flip each published item's registry `publishStatus` draft→`published` (hard — Step 10 filters on it), print the `assets/display-formats.md` publish confirmation **VERBATIM (`Content published successfully.` + Title/Managed Content ID/Variant ID) — NOT reworded `Content is live`/deployment-id prose**, then **Step 10**. Partial/total-failure → error-recovery guards + retry prompt.
- **Step 10 — Post-Publish.** Dispatch the Step 10 prompt; options depend on `workspaceMethod` (`uibundle` includes render, `manual` hides it). **In-session publish ALWAYS dispatches this for BOTH methods** — skipping to `Session ended.` is a regression. `Create more content` → restart FULL flow at Step 1 (silent — no "what next?" ask, wait for user's next message) → Step 2 → Step 3; do NOT reuse this run's workspace. `Render…` → hand off to `experience-cms-content-render` with `channelId`, `contentKeys` (ONLY `publishStatus=published`), `contentTypeFqn`, `uiBundleDeveloperName`, `uiBundleMasterLabel`; zero published → print the "no published items" line + re-dispatch. `End session` → `Session ended.`

## Error Handling

`references/error-recovery.md` — full error-signal → response mapping: `create_cms_content` / `update_cms_content_variant` / `publish_content` server-side failures, bulk partial failures, sibling terminal states, out-of-scope requests.

## Cross-Skill Integration

- Discover / define a ContentTypeBundle (Step 2 delegation path only, not fast-path) → `experience-cms-content-type-generate` (payload + `status` routing in Step 2a–2d).
- Render published content to a UIBundle (Step 10) → `experience-cms-content-render` (handoff params + `workspaceMethod=uibundle` gate in Step 10).

## Key Principles

**Full text of all 15 → `references/principles.md`** (canonical index; each is ALSO enforced inline in its Step body above): (1) workflow in order, (2) dispatch is the work, (3) server-side generation only, (4) user goal verbatim, (5) sibling owns type on delegation, (6) workspace from user/UIBundle — never infer/SOQL, (7) cancel terminates, (8) consistent display, (9) session registry + stable variant ID, (10) post-action loop, (11) bulk = one call per item parallel, (12) publish defaults to all, (13) route intent FIRST + identifier gate, (14) no-drift STOP, (15) type-class-unsupported hard stop. Identifiers → `references/identifier-resolution.md`.
