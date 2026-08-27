# Step 2 delegation protocol (Bucket 4) — full detail

SKILL.md Step 2 keeps the classification-bucket summary, the fast-path invariants, and the 2b `status` routing table (load-bearing). This file holds the full procedural detail for the delegated path: 2a (hand over the intent), 2c (handoff validation), and 2d (what NOT to do).

## 2a. Hand over the intent — first tool call after Step 1, no user turn between

**Only reached on Bucket 4 (natural-language or no content-type reference).** If Bucket 1/2/3 resolved the FQN, you are at Step 3 — do not enter Step 2a.

**Resolve the workspace FIRST, before delegating.** The sibling scopes discovery via `get_content_types_for_workspace`, so it needs the space up front. Run Step 3 now — the workspace question and (for a UIBundle pick) `get_or_create_cms_workspace_and_web_app_channel` — to capture `contentSpaceOrFolderId` before the sibling call. That workspace question is the ONE `ask_user_tool` allowed before delegation; a vague prompt (`generate new content for Q4 launch`) is a valid intent, not a reason to clarify. Then delegate.

**Print a one-line banner BEFORE delegating** so the user sees the handoff (the sibling runs silently): `Resolving the content type for your request…`. One line, no planning prose.

**Invocation — use the MCP skill bridge, not the built-in `Skill` tool.** Dispatch via `mcp__skill_bridge__load_skill("experience-cms-content-type-generate")`. The built-in `Skill` tool uses a separate registry that returns `Unknown skill` for bridge skills. Load failure → route as `load failed` in Step 2b; do NOT do the sibling's work here.

Pass `{ intent: "<user's original message verbatim>", suppressCreateContentPrompt: true, <scope> }` — `<scope>` is the resolved `contentSpaceOrFolderId` keyed by prefix: `0Zu` → `spaceId: "<id>"`; `9Pu` → `folderId: "<id>"`. This scopes the sibling's `get_content_types_for_workspace` so it offers only types that space supports. **This call is the Layer-2 server confirmation of a manual space** — an invalid/not-found error (`INVALID_API_INPUT` / "must be a valid ManagedContentSpace id" / space-not-found) is a **HARD STOP: do NOT let the sibling build/deploy a type on a bad space.** Surface verbatim, re-ask via the invalid-ID template before re-dispatch. → `references/workspace-resolution.md` § Validate. **Pass exactly one of `spaceId`/`folderId`, never also `baseType`** (mutually exclusive). The sibling runs discovery, disambiguates, offers create-new if nothing matches. **Pass the message verbatim — no paraphrase, no "The user wants…" prefix.**

**Anti-pattern — no pre-delegation question.** The moment you have `intent` verbatim, the sibling call goes out. Do NOT confirm intent, ask if they have a type in mind, or run a "few clarifying questions" preamble — documented regressions. Delegate.

## 2b. Consume the structured outcome — delegation boundary

**Delegation boundary — do not execute any later step while the sibling is running.** Once Step 2a dispatches the sibling, this skill is paused: do NOT run Step 4 or any later step until the sibling emits a terminal outcome. Interleaving is sequencing drift — parent and child share one thread; any parent tool call mid-delegation corrupts the sibling's state machine. Wait for the sibling's next turn.

The sibling emits every terminal state as a structured outcome. **This skill consumes `{ status, fqn, message }` — the sibling may also emit `schema`, but this skill ignores it (server-side generation does not need it).** The `status` routing table lives in SKILL.md § Step 2b.

The `load failed` row (bridge returned `Unknown skill` / bridge error — sibling never ran): **STOP.** Print: `Cannot proceed — the required sibling skill experience-cms-content-type-generate is not available on this bridge. Exit and re-run once the sibling is registered.` Sibling-unavailable is a terminal failure, NOT a fallback trigger. Do NOT scan `contentTypes/` locally, do NOT `cat schema.json`, do NOT dispatch `metadata-grounding.search_metadata` for `ContentTypeBundle`, do NOT call `get_or_create_cms_workspace_and_web_app_channel`, do NOT continue to Step 3. If the initial load-via-name failed but the sibling is discoverable via `mcp__skill_bridge__search_skills`, retry once via `mcp__skill_bridge__load_skill` with the exact name from the search result before treating it as terminal.

## 2c. Handoff validation (defensive — only on `status: success`)

Even under `success`, verify `fqn` is usable before continuing — a malformed handoff must not silently poison Step 4:

- **`fqn`** — non-empty string matching `^[a-zA-Z_][a-zA-Z0-9_]*__[A-Za-z][A-Za-z0-9_]*$`. If missing or malformed, surface: `Received a success outcome from experience-cms-content-type-generate but the FQN is missing or malformed. Re-run, or provide the FQN directly.` — then `ask_user_tool`: `Retry with an explicit FQN` / `Cancel`.

Only after the check passes, capture `contentTypeFqn` and continue to Step 3.

## 2d. What NOT to do

**Do not** call `metadata-grounding`, run `sf project retrieve`, re-present candidate lists, ask the user to re-pick a type, or construct FQNs from folder names — the sibling owns discovery, FQN-provide, retrieve-and-reconcile, and drift resolution. **Drift-safety net — five signals, any one means delegation is broken; hard-stop and route to Step 2b's `load failed` row → `references/content-type-classification.md` § Drift-safety net.** Do NOT downgrade `not_deployed` to `success` — a local-only bundle fails `INVALID_TYPE`.
