# `create_cms_content` / `update_cms_content_variant` / `publish_content` — error → fix mapping

When a call fails, read the returned error before retrying. Most failures are structural (wrong FQN, wrong workspace id, permission issue) — blind retries waste attempts.

This skill dispatches exclusively via the `prompt` channel; the server owns generation and validation. Field-level schema-validation errors are the server's responsibility. If any surface to the client, they are shown to the user via `ask_user_tool` (`Retry / Refine goal and retry / Cancel`) — the agent does NOT parse or regenerate rejected fields client-side.

## Common errors

| Error signal | Likely cause | Fix |
|--------------|--------------|-----|
| `INVALID_TYPE` / "Content type not found" / 404 on type | `contentType` value is the masterLabel (not the FQN); or the type isn't deployed in the target org; or, on the Step-2 fast-path, the user-provided FQN doesn't resolve in this org. | Surface the error verbatim. Then dispatch `ask_user_tool`: `Try a different FQN` / `Discover a type via natural language (delegates to experience-cms-content-type-generate)` / `Cancel`. On "Try a different FQN" — collect via `ask_user_tool` and re-run from Step 3 with the new FQN. On "Discover a type…" — invoke `experience-cms-content-type-generate` with the original user intent (as if the fast-path had not fired). Do NOT retry the same FQN silently. |
| `INVALID_ID` / "Content space not found" / 404 on space | `contentSpaceOrFolderId` is wrong, stale, or from a different org. | Ask the user to confirm the workspace ID they provided belongs to the connected org — do NOT read `ui-bundle.json`. Don't reuse an id from an example or another tenant. |
| `UNKNOWN_EXCEPTION` / "These content type(s) X are not supported by this space" | The type is deployed in the org but not configured on the workspace's allowed-types list. | Stop and ask the user. Three viable paths: **(a)** different workspace that supports the type, **(b)** different type from the workspace's supported list (re-run discovery filtered to this workspace if possible), or **(c)** deploy a new type and update workspace channel config (the deploy is delegated to `experience-cms-content-type-generate`; the workspace-config update is **out of scope** — surface that the user must do it manually or via workspace tooling). Do **not** retry the same payload — it will keep failing. |
| Server-side schema/content validation error (any field-level rejection surfaced to the client) | The server-side generation pipeline could not produce a valid body from the `prompt`, or the user's edit instruction violated the type's schema. | Surface the error verbatim. Ask via `ask_user_tool`: `Retry / Refine goal and retry / Cancel`. On "Refine goal and retry" — collect a revised `[USER GOAL]` or edit instruction via `ask_user_tool` and redispatch. Do NOT parse the error or regenerate specific fields client-side. |
| `INSUFFICIENT_ACCESS` / 403 | The current user lacks CMS authoring permission in this workspace. | Surface the error and exit — this is an org-permission concern the skill can't fix. |
| Empty/garbage content from the server | The user's `[USER GOAL]` was too sparse. | Surface the result and ask the user to re-run with more detail via `ask_user_tool`: `Refine goal and retry / Cancel`. |
| Tool returns an unfamiliar shape | The MCP server's surface may differ across IDE namespaces. | Re-read `references/content-write-tool.md`. Confirm the canonical tool id is `create_cms_content`. |
| `UNKNOWN_EXCEPTION` / "Content generation is not supported for content type '<fqn>' (type class: '<class>')" | The type belongs to a type class that `create_cms_content` / `update_cms_content_variant` cannot generate a body for at all — e.g. `sfdc_cms__media` (`sfdc_cms__image`, `sfdc_cms__video`, and other media-class types). This is a fixed capability limit of the type class, not a per-request, per-org, or per-workspace problem. Rewording the prompt, retrying, switching workspaces, or picking a different FQN for the *same* type will never succeed — and there is no in-scope way to complete the original request. | **Terminal — hard stop, same shape as Step 0-D.** Print **exactly and only** this message, with `<fqn>` and `<class>` filled in from the server error, nothing else: <br>`Content generation isn't supported for content type \`<fqn>\` (type class: \`<class>\`). This skill can't author that type class. To create or edit this content, use the Salesforce CMS UI directly.` <br>**Say NOTHING before or after the message** — no preamble, no reasoning, no alternatives, no meta-narration. Do NOT propose the Connect REST API, a direct `contentBody` payload, or any other client-side workaround — Principle 3 means this agent never constructs `contentBody` itself, and suggesting that path is a bigger violation than the original error. Do NOT dispatch the standard `Retry / Refine goal and retry / Cancel` prompt — refining the goal cannot change what the type class supports. Do NOT delegate to `experience-cms-content-type-generate` (this is not a type-discovery or schema gap) and do NOT auto-substitute a different FQN. Then end the turn. If the user wants to try an unrelated content type, that is a new request — resume at Step 2 only if they explicitly name one. |

## Workflow-level errors (create/update/publish + orchestration)

| Error signal | Response |
|---|---|
| Sibling returned `status: not_deployed` | Bundle is local-only; `create_cms_content` will fail with `INVALID_TYPE` against a type that isn't in the org. STOP. Print the sibling's `message` verbatim ("Content type `<fqn>` isn't deployed to `<org>`. Deploy it and re-run."). Do NOT retry with a guessed FQN, do NOT continue to Step 3. |
| Sibling returned `status: cancelled` | User cancelled at a decision point inside the sibling. STOP silently. Print `Session ended.` and exit. Do NOT re-invoke the sibling. |
| Sibling returned `status: error` | Unrecoverable sibling failure (missing `sfdx-project.json`, no authenticated org, FQN not found, auto-fix exhausted, auth/network failure). STOP. Print the sibling's `message` verbatim — it already carries the specific reason and recovery hint. Do NOT retry or attempt a workaround. |
| Sibling returned `status: success` but `fqn` is missing or malformed | Contract violation from the sibling. STOP dispatch. Ask via `ask_user_tool`: `Retry with an explicit FQN / Cancel`. Do NOT invent an FQN from folder names or training data. |
| `metadata-grounding` unreachable during sibling discovery | Handled entirely by the sibling — it records `grounding=unavailable` and either routes to create-new or surfaces its own error message. This skill only reads the resulting `status`. |
| User asks to attach an image | Out of scope for this skill. Point the user to the CMS UI. |
| `get_content` returns `INVALID_ID_FIELD` on a `9Ps` value | Wrong read tool for a variant ID. `get_content` does not accept variant IDs — a `9Ps` identifier must be validated via `get_content_variant` (param `variantId`). Re-route to `get_content_variant`; do NOT publish/edit the ID blindly. |
| Direct-entry read (`get_content` / `get_content_variant`) fails — not-found, `INVALID_ID_FIELD`, or empty | The identifier the user supplied did not resolve to a real record. STOP. Tell the user the identifier didn't resolve and ask for a valid content key, `managedContentId`, or `managedContentVariantId`. Do NOT fall back to publishing/editing the unvalidated ID. |
| Identifier prefix matches no known form (`MC…` / `20Y…` / `9Ps`) | Cannot classify. Ask via `ask_user_tool` for a content key, `managedContentId`, or `managedContentVariantId`. Do NOT guess the read tool or the identifier form. |
| `update_cms_content_variant` returns 404 on `variantId` | The variant ID may be stale or from a different org. Surface error and ask user to verify. |
| `publish_content` returns channel not configured | The content type is not enabled for any channel. Ask user to check channel settings in CMS setup. |
| `publish_content` returns permission denied | User lacks CMS publish permissions. Surface error and suggest verifying permissions. |
| `publish_content` returns content validation failure | Surface the specific validation error. Ask via `ask_user_tool`: `Retry / Edit content / End session`. |
| Bulk `create_cms_content` partial failure — some of the N parallel calls succeeded, others failed | Register the successful items in the session content registry. Surface each failed item with its `[USER GOAL]` and error message. Ask via `ask_user_tool`: `Retry failed / Skip / End session`. When retrying, redispatch ONLY the failed items — each as its own fresh 1-element parallel `create_cms_content` call. Do NOT combine retries into a multi-item `inputs` array. Do NOT re-dispatch the successful items. |
| Bulk `create_cms_content` — a single call timed out or dropped connection | Only that one item is affected (blast radius = 1); every other parallel call is unaffected and its result already in hand. Retry just that item's payload as a fresh 1-element `create_cms_content` call. If the same item fails repeatedly, ask the user via `ask_user_tool`: `Refine goal and retry / Skip this item / End session`. |
| Bulk dispatch built a multi-element `inputs` array instead of N parallel 1-element calls | Documented regression — Step 5b requires exactly one `create_cms_content` call per item, each with a 1-element `inputs` array, all N dispatched in parallel. Do NOT dispatch. Rebuild as N separate 1-element payloads and fan them out in parallel in a single turn. Combining items into one `inputs` array violates the hard rule regardless of N (even N=2). |
| Bulk dispatch serialized the N calls (dispatch call 1, await, dispatch call 2, …) instead of fanning them out in parallel | Documented regression — Step 5b requires all N calls dispatched in the SAME turn in parallel. Serialization multiplies wall-clock by N and defeats the purpose. Rebuild as a single-turn parallel fan-out. |
| Bulk `update_cms_content_variant` partial failure | Register successful edits, surface failed items. Ask via `ask_user_tool`: `Retry failed / Skip / End session`. |
| Bulk `publish_content` partial failure | Surface successes and failures separately. Ask via `ask_user_tool`: `Retry failed / Skip / End session`. |

## Bulk total-failure retry guards

These two guards apply **ONLY** to the bulk-operation total-failure branch — all N parallel `create_cms_content` / `update_cms_content_variant` / `publish_content` calls failed in the same dispatch turn. They do NOT apply to partial-failure branches, single-content flows, or per-item errors. Partial success bypasses both guards entirely.

**Guard A — Uniform-error short-circuit.** Before dispatching any total-failure retry prompt, compare the failure signatures across all N failed calls. Two errors share a signature when their primary error signal matches — prefer the server's error code / status field (e.g. all `INVALID_TYPE`, all `INSUFFICIENT_ACCESS`, all `INVALID_ID`, all `UNKNOWN_EXCEPTION`); fall back to full error message-string equality when no code is present. Do NOT normalize whitespace or case — exact match keeps the check cheap and deterministic. Any doubt → fall through to Guard B.

- **All N errors share the same signature** → print chat text: `All <N> items failed with the same error: <verbatim error message>. This looks like a systemic issue rather than a per-item problem. Retrying is unlikely to help until it's resolved.` Then dispatch the **"Total failure — uniform error"** prompt from `assets/questions.md` (`End session` only). Do NOT offer `Retry all`.
- **Errors differ across the N calls** → fall through to Guard B.

**Guard B — Retry counter (mixed-error total failure).** Track a `totalFailureRetryCount` in session state, scoped to the current bulk-operation instance (one instance = the current run of Step 5b for create, Step 8d for edit, or Step 9b for publish). Counter starts at 0 on fresh entry and increments each time the user clicks `Retry all` and re-dispatch produces another total failure.

| Retry attempt | Counter value on entry to total-failure branch | Prompt to dispatch |
|---|---|---|
| Retry #1 (first total failure) | 0 | Standard **"Total failure"** prompt from `assets/questions.md` (`Retry all` / `End session`). |
| Retry #2 | 1 | Print chat text: `This is retry #2 with all <N> items still failing. Consider ending the session if the underlying issue isn't resolved.` Then dispatch the standard **"Total failure"** prompt. |
| Retry #3+ | ≥ 2 | Dispatch the **"Total failure — retry exhausted"** prompt from `assets/questions.md` (`End session` only). Do NOT offer `Retry all`. |

**Counter reset rules — refactor-safety.** The counter is per-bulk-operation-instance and must be reset to 0 in every one of these cases so no state leaks across independent bulk cycles:

- A new bulk operation starts (fresh entry into Step 5b, Step 8d, or Step 9b).
- Any dispatch produces a partial success (some of the N calls succeeded). Partial success routes to the partial-failure prompt, which is out of scope for these guards — the counter is discarded.
- The user selects `End session` at any total-failure prompt.
- The bulk cycle ends normally (transitions to Step 6 / Step 7 with all items in the registry).

The counter does NOT carry across separate bulk operations within the same session (e.g. bulk create followed by bulk edit — each gets its own counter).

**Guard application order.** Always check Guard A first (cheap comparison, deterministic exit). If Guard A does not fire, check Guard B. Never dispatch a `Retry all` option when either guard says to hide it.

**Scope reminder.** These guards live inside the total-failure branch only. The partial-failure branch (`Retry failed items` / `Skip and continue` / `End session`) is untouched — that flow already retries only the failed subset and does not enter this guard logic.
