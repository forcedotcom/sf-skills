# Step 0 — intent routing: direct-entry UPDATE / PUBLISH / DELETE (full detail)

Step 0 of SKILL.md classifies the opening verb and routes. The routing table, the no-drift STOP summary, and the DELETE (0-D) exact message live in SKILL.md. This file holds the no-drift STOP message + per-route slot values, and the full procedural detail for the UPDATE (0-U) and PUBLISH (0-P) direct-entry paths — a record identified directly, possibly from any prior session.

## No-drift STOP rule — message + per-route slots

If a required `content-write` tool for the chosen route is not available on this bridge (`create_cms_content` for CREATE, `update_cms_content_variant` for UPDATE, `publish_content` for PUBLISH), **STOP.** Print the user-facing message below — filling the `<operation>` and `<tool>` slots for the current route — then end the turn. Do NOT substitute SOQL, `sf data`, a CLI call, a sibling tool, or the `contentBody` channel. Tool-unavailable and unsupported-operation are terminal — never a fallback trigger.

Slot values per route: CREATE → operation `create content`, tool `create_cms_content`; UPDATE → operation `update this content`, tool `update_cms_content_variant`; PUBLISH → operation `publish this content`, tool `publish_content`.

```text
I can't <operation> — this needs the Salesforce CMS content-write service, which isn't connected to your workspace right now. That service provides the `<tool>` tool this step requires, and without it I've stopped rather than risk changing the wrong record another way.

To continue: connect the content-write MCP server to this workspace (check your MCP / tool configuration), then re-run your request.
```

The message **MAY** name the CMS `content-write` service, the tool needed, and the fix (connect + re-run) — that lets the user self-serve. It **must NOT** quote the hard-stop rule or enumerate the rejected fallbacks (never "I can't substitute SOQL, CLI, or the contentBody channel").

## Step 0-U: UPDATE entry (record identified directly, may be from any prior session)

This is the direct-entry counterpart to the in-session edit at Step 8. This skill edits **any** existing record — one created this session OR in a prior session OR by another user. Editing is **not** session-only; a record you did not create is fully in scope. Do NOT conclude "the skill only edits session records, so I'll work with the tools directly" — that reasoning is the bug this step exists to prevent.

**Hard identifier gate — run BEFORE any tool call.** `update_cms_content_variant` targets one specific `managedContentVariantId`; the only ways to obtain it are (a) a session-registry entry for a record created/edited this session, or (b) an identifier the user typed. Decide in this order:

1. **Session-registry match?** If the user's phrasing clearly refers to an item already in the session content registry (e.g. "edit the one you just made", "change item 2"), use that entry's `managedContentVariantId` and route to **Step 8** — this is the in-session path, no user ID needed.
2. **Explicit identifier in the message?** If the user typed a content key (`MC…`), `managedContentId` (`20Y…`), or `managedContentVariantId` (`9Ps`), proceed to the resolve step below.
3. **Neither** — the user named the content by title/subject/description ("edit the Erling Haaland content", "update the vaccine article") with NO ID and it is NOT in the session registry → **STOP and ask.** Dispatch an `ask_user_tool`, answers `["Cancel"]`, `question` copied EXACTLY (one plain sentence — do NOT reformat into `- **Content Key**` bullets): `Which record should I work with? Paste the content key (starts with \`MC\`), the Managed Content ID (starts with \`20Y\`), or the Variant ID (starts with \`9Ps\`).` **You may NOT locate the record yourself** — do NOT call `search_content`, `get_spaces`, `get_content_types_for_workspace`, any discovery/listing tool, SOQL / `sf data query`, or a guessed variant ID. Searching the org to turn a name into an ID is forbidden — the ID comes from the user. Continue only after the user supplies an identifier.

Once an identifier is in hand (path 2, or path 3 after the user answers):

1. **Validate + resolve the `managedContentVariantId` by prefix, and retain the fetched body** — per `references/identifier-resolution.md` (`9Ps` → `get_content_variant`; `MC…`/`20Y…` → `get_content`). Keep the returned `contentBody` for the next step. Read fails → the ID is invalid, STOP and tell the user; do NOT edit blindly. Never run SOQL to look one up.
2. **Display the fetched content body — MANDATORY before asking for edits.** On this direct-entry path the user has not seen this record in the session, and a content type may carry a large number of properties. Print the current state using `assets/display-formats.md` — the single-content summary table followed by the content body table (iterate over every key in the fetched `contentBody`). This is what lets the user decide what to change. Do NOT print only the title / status — print the full body.
3. **Ask what to update** — dispatch the Step 8b edit-instructions prompt from `assets/questions.md` (the free-text, multi-property prompt). Wait for the user's response — that is the edit instruction. If the user's opening message already contained the edit instruction, skip the prompt and use it verbatim.
4. **Jump to Step 8c** with `{ variantId, prompt: <edit instruction> }` — the existing edit workflow (single-item path) handles payload build, dispatch, display, and the post-action loop. Do NOT run Steps 1–5 (no type discovery, no workspace resolution — the record already exists). Do NOT prompt for the render skill.
5. **Mandatory close — dispatch the dialog, never plain text.** After `update_cms_content_variant` succeeds and the body is displayed (Step 6), you MUST end the turn by dispatching the **Step 7 post-action `ask_user_tool` prompt** (single-content variant) from `assets/questions.md` — the clickable `Edit content / Publish content / End session` options. A plain-text "What's next?" line here is a regression — the direct-entry edit closes the same way the in-session edit does. Do not stop after the display.

## Step 0-P: PUBLISH entry (record identified directly, may be from any prior session)

Direct-entry counterpart to the in-session publish at Step 9. **The user may hand you any identifier for the content — a content key, a `managedContentId`, or a `managedContentVariantId`. Classify it by prefix, then validate + resolve it to a `managedContentVariantId` via the matching `content-readonly` read tool before publishing.** `publish_content` publishes by `variantIds`, so every path must end with a validated `managedContentVariantId`. Never publish an unvalidated ID — the read confirms the record exists first.

**Hard identifier gate — run BEFORE any tool call.** Same rule as Step 0-U: publishing needs a specific `managedContentVariantId` that comes from (a) the session registry or (b) an identifier the user typed. If the user's phrasing refers to a session-registry item, use it and route to **Step 9**. If the user typed an `MC…` / `20Y…` / `9Ps` identifier, proceed below. If the user named the content by title/subject with NO ID and it is NOT in the session registry → **STOP and dispatch an `ask_user_tool`, answers `["Cancel"]`, `question` copied EXACTLY (one plain sentence, no markdown bullets): `Which record should I work with? Paste the content key (starts with \`MC\`), the Managed Content ID (starts with \`20Y\`), or the Variant ID (starts with \`9Ps\`).` **Do NOT locate it yourself** — same no-org-search ban as Step 0-U (no discovery/listing tool, no SOQL, no guessed ID). Continue only once an identifier is in hand.

1. **Classify by prefix, validate + resolve to a `managedContentVariantId`** — per `references/identifier-resolution.md` (`9Ps` → `get_content_variant`; `MC…`/`20Y…` → `get_content`). Read fails / prefix unrecognized → STOP and ask the user for a valid identifier; do NOT publish blindly or guess. Never run SOQL.
2. **Jump to Step 9b** with that validated `managedContentVariantId` — the existing publish workflow handles dispatch and confirmation. Do NOT run Steps 1–5. Do NOT prompt for the render skill after publish on this direct-entry path.
3. **Close = the publish confirmation from `assets/display-formats.md`, then end the turn.** This direct-entry path is terminal — there is no Step 10 render handoff (no session `channelId` / UIBundle context for an externally-identified record). Do NOT append a plain-text "what's next" options list and do NOT dispatch a post-publish `ask_user_tool` — the confirmation statement is the final message.
