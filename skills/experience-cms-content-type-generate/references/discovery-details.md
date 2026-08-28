# Discovery internals — steps 1b–1d rationale

Load this only when you need the full rationale for a rule you're about to apply or a check you're about to skip. SKILL.md has the short version of each rule; this file has the "why" and the anti-patterns.

## 1b. Local discovery — semantic intent match

Use whichever directory-listing capability your environment exposes — pick the first that exists and call it without narration:

- `list_files` (takes a directory path)
- `Glob` (pattern: `<sfdx-source>/contentTypes/*/schema.json`)
- a local `list_directory` tool wired into your IDE

**STRICTLY DO NOT use a content-search / regex / grep tool here** (e.g. `search_files`, IDE text-search-in-files). Those tools look for literal string matches inside file contents and will MISS a folder named `MarketPlace` when the literal string `"MarketPlace"` doesn't appear in the schema's contents. Use a directory-listing tool to enumerate the subfolders of `<sfdx-source>/contentTypes/`, then read each `schema.json`.

For each subfolder, read `schema.json` (`title` + `description` fields). **Match by intent semantically** — your job is to reason about content domains, not to text-match. The user request implies a domain (a "marketplace content type" → e-commerce/listings/products/sellers domain; a "press release" → news/announcements domain; a "customer story" → case-study/testimonial domain). Surface bundles whose folder name OR `title` OR `description` is in the SAME content domain as the user's request, even if no literal string matches. A folder named `MarketPlace` IS a match for a marketplace request — folder-name match alone is sufficient.

Return every semantically-matching local bundle — they all feed `combined`, which step 1d's 5-row table cap and Row-1 sort handle downstream. If zero bundles match the user's intent, return zero — step 1d's zero-matches variant handles the rest (auto-proceed on direct invocation; delegated invocation still gets a pick list). Listing every bundle as a candidate (e.g. surfacing Product, JobListing, Webinar when the user asked for an unrelated type) is one regression to prevent — filter by intent, not by count. Missing an obvious folder-name match (e.g. saying "no local matches" when a `MarketPlace` folder exists for a marketplace request) is the OTHER regression to prevent.

Last-resort fallback if no directory-listing tool exists: `ls -1 <sfdx-source>/contentTypes 2>/dev/null` — single command, no pipes.

## 1c. Org discovery — dispatch gate

**Step 1c is a tool call, not a thought.** The primary way to satisfy 1c is to actually invoke `metadata-grounding.search_metadata` and receive its response. If `search_metadata` itself is unreachable, 1c is NOT automatically incomplete — dispatch `content-readonly.get_content_types_for_workspace` directly (Flow 2) as the fallback org signal before concluding no check happened. You are NOT permitted to write any step 1d header that implies a check happened when neither tool ran, nor to disclose a skip when one of them did (see 1d's Truth Gate). `search_metadata` dispatched → standard variant. `search_metadata` down, `get_content_types_for_workspace` dispatched → the Flow-2 variant (org WAS checked). Both down → the grounding-unavailable-skip variant.

**STRICTLY DO NOT skip 1c just because 1b found a local match.** A local hit does NOT mean the org is clean — the org may already have a bundle with the same name (the "Name already exists" deploy failure originates here, not in 1b). Step 1c is unconditional: it runs on zero local matches AND on N local matches. The `grounding=unavailable` outage path (real metadata-grounding server error) does NOT exempt 1c from running — it routes to `get_content_types_for_workspace` instead (Flow 2). Only when BOTH tools are unreachable must you record the outage agent-internally and disclose it with the `(org check skipped — grounding unavailable)` suffix from the grounding-unavailable variant in step 1d.

Rationalizations the agent uses to justify skipping — all violations:

- "Local found a match, no need to also check the org." → No. 1c MUST still run. Its purpose is the org-side check that local cannot do.
- "Grounding was unavailable last turn, I'll skip it this turn." → No. Re-attempt every run. Outages are per-turn.
- "User said 'use existing' before I dispatched 1c." → That can't happen — 1d (where the user picks) runs AFTER 1c. If you're already at "user said use existing," you skipped 1c. STOP and start over from 1c.

Just call it. Do NOT ask the user "should I search?" — the search is unconditional, and asking IS the violation:

```javascript
search_metadata({ metadataType: "ContentTypeBundle", query: "<2-5 keywords from user request>", limit: 100 })
```

Then for each top match:

```javascript
query_metadata({ metadataType: "ContentTypeBundle", id: "<id>" })
```

**Server target:** `metadata-grounding` (per RULE 1 and the registry table).

Apply the same intent matching. **Historically** (before `get_content_types_for_workspace` existed) every grounding result fed straight into the step 1d table, unfiltered — that behavior now only applies when the workspace-content-types check itself is unavailable (see below); when both tools returned, the intersection computed in "1c continued" is what feeds the table, capped at 5, with the remainder surfacing inline in the FQN option's parenthetical. Tag matches `[org]` — or `[org, OOTB]` when the namespace / grounding response identifies the type as OOTB (`sfdc_cms__*` or grounding's `isOOTB` flag).

**OOTB-first row ordering.** If any grounding result is OOTB (`sfdc_cms__*` or `isOOTB === true`), it goes in **row 1** of the step 1d table — and therefore becomes the single `Use existing:` option's FQN. Custom (`c__*`) rows follow in grounding's original rank order. If no OOTB result exists, custom rows use grounding's rank order as-is. This is a deterministic sort, not a judgment call — row 1's FQN is what `Use existing:` names, and only that ONE option is emitted regardless of how many rows the table has.

**If `metadata-grounding` is unavailable** (server error, denial, timeout, or empty result): do NOT stop at local-only. Dispatch `content-readonly.get_content_types_for_workspace` directly (Flow 2, below) as the org-discovery signal for this turn. Record `grounding=unavailable` agent-internally regardless — this drives step 1e's OOTB-schema fail-closed rule, which is unaffected by Flow 2. Do not ask the user. `metadata-grounding` unavailability does not block step 5 or step 7 — those use the SF CLI default org via a separate auth path.

## 1c continued. `get_content_types_for_workspace` — why it exists and how it combines

Grounding is a search index over metadata descriptions — it can surface a type that sounds right without knowing whether that type is actually usable in the caller's target workspace (a workspace may be scoped to a subset of base types, e.g. `CONTENT` only, or to a specific space/folder). `get_content_types_for_workspace` answers the complementary question: "what can I actually create here?" Neither question alone is sufficient — grounding without workspace-scoping can propose a type the user can't use; workspace-scoping without grounding can't rank by relevance to the user's intent. Combining them is more precise than either alone.

**Call params — resolved from the caller's invocation params per the mutual-exclusivity contract (SKILL.md § Invocation contract):**

```javascript
// caller passed spaceId
get_content_types_for_workspace({ spaceId })
// caller passed folderId
get_content_types_for_workspace({ folderId })
// caller passed baseType alone
get_content_types_for_workspace({ baseType })
// caller passed none of the three (direct/standalone default)
get_content_types_for_workspace({ baseType: "CONTENT" })
```

Never send `baseType` alongside `spaceId`/`folderId`, not even as a default — the space/folder scope already determines the eligible types, and layering a base-type filter on top narrows for no reason the caller asked for.

**Flow 1 — grounding ran.** After `search_metadata` returns, ALSO dispatch `get_content_types_for_workspace`. Take the intersection of both responses' FQNs. Rationale for intersection over union: a row that grounding likes but the workspace doesn't support would fail deploy/create later (wrong scope); a row the workspace supports but grounding didn't surface is not relevant to what the user asked for. Only rows satisfying BOTH are genuinely "a good match AND usable here." An empty intersection is not a failure state — it means nothing in this workspace matches the user's intent, which step 1d already has a zero-matches variant for. Do not treat empty as a signal to retry or loosen the query. If `get_content_types_for_workspace` itself is unavailable this turn (grounding still fine): record `workspaceTypes=unavailable` agent-internally and fall back to the raw `search_metadata` results, unfiltered — the org check already happened truthfully via grounding, so no 1d header wording changes.

**Flow 2 — grounding unavailable.** Do NOT skip the org check — dispatch `get_content_types_for_workspace` directly (same params) as the sole org-discovery signal. Since there's no grounding rank to intersect against, apply the same semantic intent-match reasoning used in step 1b (domain reasoning, not literal string match) directly to the `name`/`description` of each row it returns, keeping only rows in the same content domain as the request. These become the org candidate rows for step 1d. Record `groundingFallback=workspaceTypes` agent-internally — step 1d's TRUTH GATE uses this to pick accurate wording (the org WAS checked, just not via grounding). If `get_content_types_for_workspace` is ALSO unavailable: record `workspaceTypes=unavailable` too — org discovery produced zero signal this turn, so use the grounding-unavailable-skip wording. This is the only case where the org genuinely was not checked.

**Local matches (1b) are never intersected or filtered by this tool.** The workspace-content-types check is scoped to org-side candidates only; a local `contentTypes/` folder match is assumed deployable as-is and always survives into `combined` untouched, per the same logic as any other local match.

**Neither tool substitutes for 1e's retrieve.** Grounding is a heuristic index; `get_content_types_for_workspace` confirms workspace support for this session — neither is authoritative on org deploy-shape. A `search_metadata` hit is high-signal, a miss is low-signal — NEVER conclude "the org does not have `<Name>`" from grounding alone. Only step 1e's `sf project retrieve start` confirms org presence/absence.

## 1d. Truth gate

STRICTLY DO NOT print a step 1d header that implies a check ran when it didn't, and do NOT disclose a skip that didn't happen. Three distinct states, not two:

1. **`search_metadata` dispatched this turn (Flow 1).** The org was checked via grounding — no disclosure suffix needed, regardless of whether `get_content_types_for_workspace` also ran.
2. **`search_metadata` unavailable, `get_content_types_for_workspace` dispatched instead (Flow 2).** The org WAS checked — just through the workspace tool, not grounding. Saying "org check skipped" here would itself be fabrication in the other direction (claiming less happened than actually did). Append `(checked supported content types for this workspace — metadata-grounding unavailable)` per `assets/discovery-prompts.md`.
3. **Both unavailable.** No org signal was obtained this turn. Append `(org check skipped — grounding unavailable)` per `assets/discovery-prompts.md`.

Implying a check happened without a real dispatch is fabrication — the user trusts the header as evidence a check ran, and writing it falsely is the worst kind of regression because it's silent. Equally, describing a real dispatch (case 2) with skip-wording understates the actual coverage and could make the user think a match was missed when it wasn't checked at all — pick the wording that matches what was ACTUALLY dispatched this turn, not just whether grounding specifically ran.

## 1d. Intent-sanity gate (direct-invocation zero-matches)

Before auto-proceeding to step 2 on zero matches, extract at least one recognizable content-domain noun from the message:

- **Recognizable** = a real English word, a named entity (brand, sport, industry term), or compound domain vocabulary (`pet grooming`, `job listing`, `product review`).
- **Gibberish** = keyboard mash, no real words.
- **Filler-only** = the message contains ONLY mechanic nouns after stripping `content type(s)`, `bundle`, `CMS`, `schema`, `metadata`, `record`, `entity` — e.g. `create a content type bundle for our CMS` names the mechanic, not the domain.

**≥1 recognizable noun** → proceed to step 2 → 3. The step 3 proposed name MUST be built from user-message tokens only (`foo laptop bar` → `Laptop`) — do NOT introduce nouns absent from the message; `GovernmentGO`-out-of-nowhere is the hallucination anti-pattern. If the noun set is thin (one word), use that word as-is — do not embellish.

**Gibberish OR filler-only** → do NOT auto-proceed. Dispatch `ask_user_tool` with question `Your request "<original message>" doesn't name a content domain. What kind of content type would you like to create (e.g. news, blog, press release, product)?` and options `Cancel` (plus free-text). Free-text reply → treat as fresh `intent`, restart from 1b. `Cancel` → emit `cancelled`, print `Cancelled. No files written.`, `Task Completed`.

**Empty-query implication:** if 1c's rebuilt `query` is empty after stripping forbidden tokens (`content type`, `bundle`, `CMS`, `metadata`, `sfdc_cms`, `c__`, `__`), route directly to this gate — do NOT dispatch a blank `search_metadata`, do NOT record `grounding=unavailable`.

No verb-parsing on the message otherwise — results + invocation context determine `showFqnOption`. `Cancel` is always present; `Use existing:` is present when a semantically-relevant match exists.

Discovery is the user's first chat-visible signal that the skill is doing real work. **Always tell the user what was checked and what was found**, even when zero matches. This is the user's chance to redirect to an existing type before any files are written.
