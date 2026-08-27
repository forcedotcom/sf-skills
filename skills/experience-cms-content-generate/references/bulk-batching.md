# Bulk Dispatch Rules — `create_cms_content` / `update_cms_content_variant`

Single source of truth for how bulk operations are dispatched. Referenced from SKILL.md Step 5b.

## The rule in one sentence — HARD RULE

**Dispatch exactly ONE `create_cms_content` call per item, with a 1-element `inputs` array, and fan out all N calls in parallel in a single turn.** No exceptions, no thresholds, no batching, no grouping.

This applies for every N ≥ 1. Single content (N=1) is one call; bulk (N ≥ 2) is N calls, dispatched in parallel.

## Why one-call-per-item

- **Matches the server-side generation model.** Each `create_cms_content` runs the Vibes MC content pipeline for one record; keeping calls 1:1 with records means one server-side generation per wire call, which is how the pipeline is tuned.
- **Bounded blast radius = 1.** A dropped connection loses exactly one record. Retry is trivial — the same 1-element payload, redispatched.
- **Trivial partial-failure handling.** Each call's success or failure is independent and known individually. No need to walk an `outputs` array or reconcile which sub-item failed.
- **Simpler mental model for the skill.** No batch-size math, no balancing, no re-batching on retry.

## Do NOT

- **Do NOT put more than one element in `inputs`.** Even for N=2, do NOT send one `create_cms_content` with a 2-element `inputs` array. Every call is exactly one element.
- **Do NOT serialize.** For N ≥ 2, dispatch all N calls in the same turn in parallel — do not dispatch call 1, await, then dispatch call 2. Serialization defeats the parallelism this rule enables.
- **Do NOT batch on retry.** If items 3 and 7 failed, retry them as two separate parallel 1-element calls — never combine into a single 2-element `inputs` array.
- **Do NOT mention dispatch mechanics to the user.** The user asked for N content items — they see "N items." Do NOT mention parallel calls, `create_cms_content`, or the tool id. Say `Ready to create 7 items` — NOT `Ready to dispatch 7 parallel create_cms_content calls`.
- **Do NOT narrate tool preparation.** If the runtime lazy-loads `create_cms_content` at dispatch time, do the tool-schema fetch inside the same turn as 5b — no `"Let me load the content creation tool"`, no `"Loading tool schema"`, no `"Fetching create_cms_content"`. The user should see the dispatched results, not the plumbing that got you there.

## Same shape applies to `update_cms_content_variant`

Bulk edits (Step 8d) follow the same rule: one `update_cms_content_variant` call per selected item, 1-element `inputs`, all N dispatched in parallel. Each call carries its own `variantId` + its own `prompt`.

## Bulk topic generation + approval (Step 4, quantity > 1)

Referenced from SKILL.md Step 4 "Bulk Content". Runs before the parallel dispatch above.

**4.B.1. Generate topic prompts.** Generate N distinct topic prompts (N = explicit count, or 4–5 if unspecified), each a unique angle within the user's domain.

**4.B.2. Present topics for approval — TWO-PART output.**

Part 1 — print the topic list as formatted chat text (markdown) so line breaks and numbering render:

```markdown
I'll create **<N>** content items of type `<FQN>`. Here are the topics:

1. **<short title 1>** — <topic prompt 1>
2. **<short title 2>** — <topic prompt 2>
3. **<short title 3>** — <topic prompt 3>

You can approve as-is, remove items by number, add new topics, or rewrite any prompt.
```

Part 2 — immediately after the text, dispatch the Step 4.B.2 approval prompt from `assets/questions.md`. Never put the full topic list inside the `ask_user_tool` question (see `references/ux-rules.md`).

**4.B.3. Handle response.**
- `Looks good, create them` → proceed to 4.B.4 with the listed prompts.
- `Let me adjust` → wait for the user's modifications (remove / add / rewrite), then re-present the final list for a single confirmation. Do NOT loop more than once — after the second presentation, proceed with whatever the user confirms.

**4.B.4. Prepare N single-item payloads.** Use `assets/payloads/create-content-bulk.json` as the per-call shape — build N independent 1-element `inputs` payloads (one per approved topic). All share the same `contentType` and `contentSpaceOrFolderId`; each carries its own `title` (agent-generated for that topic) and `prompt` (that topic's approved prompt verbatim). Step 5b dispatches those N calls in parallel per the HARD RULE above.
