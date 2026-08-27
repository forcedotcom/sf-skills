# Steps 8, 9, 10 — full detail (edit, publish, post-publish)

SKILL.md keeps the entry rule and route summary for each of these steps. This file holds the full procedural detail. All three are **MCP-only — no SOQL, no CLI.**

## Step 8: Edit Workflow

**MCP-only — no SOQL, no CLI.** Read via `content-readonly` (`get_content`/`get_content_variant`), write via `content-write` `update_cms_content_variant`. Never `sf data query`, SOQL, or CLI to find/read/update a record. Resolving by name is not permitted (Step 0-U gate).

**8a. Determine edit scope.** For single content (or if user names a specific item by number): edit that one item. For bulk content: dispatch the Step 8a scope prompt from `assets/questions.md`. If the user selects "Specific items (by number)", follow up with the item-number prompt.

**8b. Get edit instructions from user.** Dispatch the Step 8b edit-instructions prompt from `assets/questions.md`. Wait for the user's response — this is the edit instruction. The same instruction applies to all selected items; the server-side pipeline adapts it against each item's existing content.

**8c. Build the update payload.** Use `assets/payloads/update-content.json`. Per selected item:
- `variantId` — the `managedContentVariantId` from that item's latest `create_cms_content`/`update_cms_content_variant` response, **or the ID captured at Step 0-U** (direct-entry, record not created this session). Either source, same shape.
- `prompt` — the edit instruction verbatim; the server reads the existing `contentBody` for that variant and applies it.
- `title` — re-emit ONLY when the edit clearly targets the title ("rename to X"); otherwise omit so the server keeps the existing value. Never regenerate `title` on unrelated edits.
- Optional (`urlName`, `apiName`) only when the user named them.

**8d. Dispatch `update_cms_content_variant`.** One call per selected item; for bulk, all N in parallel (each carries its own `variantId` + `prompt`).

**8e. Check the result.** On success: go back to **Step 6** — display the **full updated content body**, every field, using the single-content summary + content-body tables from `assets/display-formats.md` (the same format used at fetch time). **Do NOT print a change-summary / diff table** (a "Field | Change" list of only what changed) in place of the body — the user must see the complete post-edit record, all properties, not just the edited ones. Source the body correctly: if `update_cms_content_variant`'s response echoes the full `contentBody`, display that; if the response carries only IDs / partial fields, **re-fetch the variant with `content-readonly` `get_content_variant` (param `variantId`) and display that body.** Never reconstruct the body from memory or from the edit instruction — display server-returned values only. Then proceed to **Step 7** (post-action loop). This allows iterative editing. **Step 7 dispatches the `ask_user_tool` post-action prompt — clickable options, never a plain-text "what's next" line.** The turn does not end at the display; it ends at the dispatched dialog.

On partial failure (bulk): register successful edits, surface failures, and dispatch the retry prompt from `assets/questions.md`.

On failure: surface the error and ask the user via `ask_user_tool`: `Retry / Refine edit instruction and retry / Cancel`. If unrecoverable **on a bulk edit** (all N `update_cms_content_variant` calls failed in the same dispatch turn), apply the "Bulk total-failure retry guards" in `references/error-recovery.md` before dispatching a retry prompt — the guards select the correct total-failure prompt variant from `assets/questions.md`. Single-content edit failures use the plain `Retry / Refine edit instruction and retry / Cancel` prompt unchanged.

## Step 9: Publish Workflow

**MCP-only — no SOQL, no CLI.** Resolve/confirm via `content-readonly`, publish via `content-write` `publish_content`. Never `sf data query`, SOQL, or CLI to find/publish a record.

**9a. Determine publish scope.**

- `Publish content` / `Publish all` → publish all items in the session content registry.
- `Publish subset` → user has already specified which items by number; use those variant IDs.
- Default behavior (no explicit scope) → publish all items.

**9b. Dispatch `publish_content`.** Use `assets/payloads/publish-content.json`. `publish_content` accepts `variantIds` (array of `managedContentVariantId`) or `contentIds` (array of `managedContentId`); this skill uses `variantIds`. In-session items carry a `managedContentVariantId` from their create/edit response; pass those (single content = one-element array; bulk = all selected variant IDs from the session content registry). **On the Step 0-P direct-entry path**, pass the validated `managedContentVariantId` resolved in Step 0-P (via `get_content` for a content key / `managedContentId`, or via `get_content_variant` for a `9Ps` variant ID). On this direct-entry path, after the publish confirmation, end the turn — do NOT proceed to Step 10's render handoff (there is no session `channelId` / UIBundle context for an externally-identified record).

**9c. Check the result and update the registry.** On success: for every `managedContentVariantId` that `publish_content` reports as published, update its registry entry's `publishStatus` from `draft` to `published`. This is a hard requirement — Step 10's render handoff filters on `publishStatus=published`, so items not marked published will be excluded from the render call. Then print a confirmation using `assets/display-formats.md` (single or bulk variant) and proceed to **Step 10**.

On partial failure (some items published, some failed): mark the successful items as `publishStatus=published` in the registry — leave the failed items at `publishStatus=draft`. Surface successes and failures separately, then dispatch the retry prompt from `assets/questions.md`. If the user retries, mark newly-published items on the retry response the same way.

On failure: surface the error. Common publish errors (channel not configured, permission denied, content validation failure) and their responses → `references/error-recovery.md`.

On a bulk publish total failure (every `managedContentVariantId` in the batch failed to publish), apply the "Bulk total-failure retry guards" in `references/error-recovery.md` before dispatching a retry prompt — the guards select the correct total-failure prompt variant from `assets/questions.md`. Single-content publish failures use the standard `Retry / Cancel` flow from the error-recovery rows above.

## Step 10: Post-Publish

After successful publish, dispatch the Step 10 prompt from `assets/questions.md`. The options depend on `workspaceMethod` recorded in Step 3 (`uibundle` variant includes the render option; `manual` variant hides it because there is no resolved `channelId` — the manual-workspace prompt tells the user why).

**In-session publish ALWAYS dispatches this prompt — both `workspaceMethod` values.** `manual` hides only the render option; it does NOT skip Step 10. Jumping straight to `Session ended.` after an in-session publish is a regression — the user loses `Create more content`. The `manual` variant still offers `Create more content / End session`. (The ONLY publish path that ends without Step 10 is the Step 0-P direct-entry path — a record not created this session, no session context.)

**Route on user response:**
- `Create more content` → restart the FULL workflow from **Step 1** as a fresh content creation — exactly as if the user had opened a new request. **Step 1 stays silent: do NOT ask "What would you like to create next?" or dispatch any `ask_user_tool`; end the turn and wait for the user's next message, then run Step 1 → Step 2 (type) → Step 3 (workspace) → create.** Do NOT reuse this run's resolved `contentSpaceOrFolderId`/`workspaceMethod` and do NOT print a "same space confirmed" line — Step 3 re-resolves the workspace normally on the new request. (The "don't re-ask workspace" rule applies ONLY within a single run's delegation path, never across a Create-more loop-back.)
- `Render it to the UI Bundle (...)` → collect the following data from the session and hand off to skill `experience-cms-content-render`:
  - `channelId` — the channel ID returned by `get_or_create_cms_workspace_and_web_app_channel` in Step 3
  - `contentKeys` — array of `contentKey` values from **only** the registry items with `publishStatus=published`. Draft items (never published, or failed to publish in Step 9c) MUST be excluded — a UI Bundle render is a live-content operation and drafts have no rendered URL. If a partial publish left some items as drafts, they are silently omitted from the handoff; the confirmation preceding this handoff should already have shown the user which items published successfully.
  - `contentTypeFqn` — the content type FQN captured in Step 2
  - `uiBundleDeveloperName` — the selected UIBundle's `developerName`
  - `uiBundleMasterLabel` — the selected UIBundle's `masterLabel`

  **If the filter produces zero `contentKeys`** (every item is still `draft` — e.g. every item in a bulk publish failed), do NOT invoke the render handoff. Print chat text: `No published items available to render. Publish at least one item before rendering.` Then re-dispatch the Step 10 prompt from `assets/questions.md`.
- `End session` → print one line: `Session ended.` and exit.
