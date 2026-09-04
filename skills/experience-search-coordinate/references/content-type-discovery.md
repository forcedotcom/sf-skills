# Content Type Discovery — Fallback Chains

Reached from `SKILL.md` Step 2 point 2 whenever `search_metadata` doesn't produce a usable candidate list.

## Workspace content-type fallback

Only reached when `search_metadata` never produced a usable candidate list — the server was unavailable, or it returned zero candidates even after one retry with a clarified query.

- Call `get_content_types_for_workspace` passing `baseType: "content"` **instead of** `spaceId` — omitting `spaceId` and passing `baseType` returns every applicable content type across the org rather than one workspace's subset. Also pass `typeClassFullyQualifiedNames: ["sfdc_cms__structured"]` and `mixinFullyQualifiedNames: ["sfdc_cms:deliverySearch"]` — this pre-filters the response to the same "supported for search" set the primary path gates on in Step 2 point 4, so the fallback doesn't have to hand back unsupported types for you to filter after the fact:

  ```javascript
  get_content_types_for_workspace({
    inputs: [{
      baseType: "content",
      typeClassFullyQualifiedNames: ["sfdc_cms__structured"],
      mixinFullyQualifiedNames: ["sfdc_cms:deliverySearch"]
    }]
  })
  ```

- Each returned entry has `developerName`, `namespace`, and `description` — the type-class/mixin filtering above is applied server-side to the candidate set, but individual entries still don't carry `typeClasses`/`mixins` fields themselves, so **media-vs-content routing** is still judgment-based (reading the description), not a field check like `query_metadata`'s.
- **Read each candidate's `developerName`/`description` against the search intent** and pick at most the 5 most relevant. For each: if it's clearly an image, audio, video, or document type (by name/description) → media candidate, go to Step 4 (Media Route); otherwise → content candidate, go to Step 3 (Content Route). Construct the FQN as `<namespace>__<developerName>` (e.g. `c__BookReview`, `sfdc_cms__image`) — the same convention `experience-cms-content-generate` uses for FQN construction.
- **Can't confidently classify, or can't narrow to relevant candidates** — ask the user one clarifying question (`ask_followup_question`) listing the candidates (label + description) as options, and route on their reply. This is a separate, one-shot ask from Step 2 point 2's clarifying question (that one narrows the search query before this fallback ever runs; this one disambiguates among this fallback's own candidates) — don't skip it just because point 2 already asked once.
- **Zero candidates returned here too** — apply the wording fallback below; there's nothing left to ground the route in.

## Wording fallback

Last resort — only reached when both `search_metadata` and the workspace content-type fallback failed to produce a usable candidate list.

- **Media wording** (e.g. image, photo, logo, icon, banner, graphic, picture, audio, clip, sound, recording, video, document, PDF, file, asset, media) — go to Step 4 (Media Route) with an empty `contentTypeFqn` (`""`).
- **Content wording** (e.g. article, blog, post, news, FAQ, event, product, page, press release) — go to Step 3 (Content Route) with an empty `contentTypeFqn` (`""`).
- **Still unclear either way** — fall back to the Content Route with an empty `contentTypeFqn` (`""`), since structured content is the more common case.
- In every one of these cases, search silently across all types for that route — do not block or ask the user again just because `search_metadata` and the workspace content-type fallback both came up empty.

## Filter-result messages (Step 2 point 4)

**Zero candidates survive the supported-type filters:**

```text
I found these content types for "<intent>", but none of them are supported for search: <label1> (<fqn1>), <label2> (<fqn2>).
```

**Some, but not all, candidates survive** (plain-text statement, not a question — don't wait for a reply):

```text
<label1> (<fqn1>) isn't supported for search, so I'll continue with: <label2> (<fqn2>).
```

## "Intent itself is ambiguous" question

Reached from `SKILL.md` Step 2 when the request gives no hint of type or subject (e.g. "find me some content") — asked before ever calling `search_metadata`.

`ask_followup_question` with the question `"What are you looking for?"` and one **option** per choice in the tool's `options` array — never as numbered lines inside the question text:

`Articles / Blog posts`, `News`, `FAQs`, `Events`, `Products`, `Images / logos / photos`, `Audio clips`, `Videos`, `Documents`, `Other (describe what you need)`.

Wait for the reply before proceeding. Do not guess.
