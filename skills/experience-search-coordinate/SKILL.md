---
name: experience-search-coordinate
description: "Searches for and retrieves existing content and media (articles, blogs, news, FAQs, events, products, images, logos, icons, photos, graphics, banners, hero images, audio clips, videos, documents) from Salesforce CMS or other connected sources. Use this skill ANY TIME a user says \"find\", \"search\", \"get\", \"fetch\", \"retrieve\", \"look up\", \"locate\", \"show me\", \"list\", or \"I need\" followed by content or media words like \"blog\", \"article\", \"news\", \"FAQ\", \"event\", \"product page\", \"image\", \"logo\", \"icon\", \"photo\", \"banner\", \"audio\", \"video\", \"document\". Also use for requests that mix both, like \"reuse existing assets\" for a page. Routes each intent to the correct sub-workflow — structured content search or media search — and can run both in the same request. Does not apply when the request is to generate NEW content or images from scratch, define content type schemas, or apply brand guidelines."
metadata:
  version: "1.0"
  domains: ["Experience"]
  relatedSkills:
    - "experience-cms-brand-apply"
    - "experience-cms-content-generate"
    - "experience-cms-content-render"
    - "experience-cms-content-type-generate"
  mcpTools:
    content-readonly:
      tools:
        - get_content_types_for_workspace
        - search_content_cms_channels
        - search_electronic_media
        - search_media_cms_channels
      semver: ">=1.0.0"
    metadata-grounding:
      tools:
        - query_metadata
        - search_metadata
      semver: ">=1.0.0"
    skill_bridge:
      tools:
        - load_skill
      semver: ">=1.0.0"
  cliTools:
    - tool: ["sf"]
      semver: ">=2.0.0"
---

# Search Coordinator

Routes search requests to the correct sub-workflow — structured CMS content or media — and runs both when a request mixes the two.

**A `→ Read` pointer below is a required action, not FYI** — open that file before continuing past that point; this skill has drifted before from steps followed off memory.

## Scope

**This skill is for SEARCHING FOR existing content or media, not creating new content or images.**

**Use this skill when the user wants to:**

- Search for articles, blog posts, news, FAQs, events, products, or custom content
- Search for images, logos, icons, photos, graphics, banners, hero images, audio clips, videos, or documents
- Reuse existing assets instead of creating new ones, or any combination of the above in one request

**DO NOT use this skill when the user wants to:**

- Generate new content (use `experience-cms-content-generate`)
- Generate new images (use image generation tools)
- Define content type schemas (use `experience-cms-content-type-generate`)
- Apply brand guidelines (use `experience-cms-brand-apply`)
- Create, edit, or publish content records

## Step 1: Determine Channel Scope

**Mandatory on every request that reaches it — never skip straight to Step 2.** No phrasing of the request ("just find me an article," a plain keyword search, etc.) skips this step's local-file scan. If you're about to call `search_metadata` in Step 2 without having scanned for `uiBundles/*/public/content-metadata.json` this turn, STOP and come back here first.

1. **Explicit `channelId` given** — use it directly, skip discovery entirely, proceed to the scope rule below.
2. **Named uiBundle/app, no `channelId`** — resolve that uiBundle's `channelId`; if it doesn't resolve, fall through to point 3 as if nothing was named.
3. **Otherwise, discover from the local project** — scan every `uiBundles/*/public/content-metadata.json` file (never gate this on server-side deployment status) and collect the `channelId`s found. Zero → public channels only. Exactly one → public plus that channel. More than one → ask the user which one via `ask_followup_question`.

→ Read `references/scope-resolution.md` § "Step 1 points 1-3" for the full discovery mechanics before acting on points 1-3 above. Proceed to Step 2 once scope is determined.

**Scope rule (applies whether the `channelId` was user-provided or discovered):** scope is always public channels (`contentAccessScope: "Public"`, no `channelIds` field) plus that one `channelId` (a separate call with `channelIds` set to it, no `contentAccessScope` field) — never resolve a separate ID to represent "public," and never send `contentAccessScope` and `channelIds` in the same call. **This scope decides how many search calls Steps 3 and 4 make:** no `channelId` in scope → one search call (public channels only). A `channelId` in scope → two search calls (public channels, then that specific `channelId`), with results merged before presenting.

## Step 2: Determine Content Type and Route

**Precondition: Step 1 must have already run in this turn** (its channel-scope result is what point 5 below carries into Step 3/4). Step 1 runs unconditionally — even for a plain keyword search with no obvious channel angle, not only when the request names a channel or app.

1. **Identify one or more distinct search intents** in the request (e.g. "find a press release about our launch and a hero image for the page" is two intents). Run the rest of this step once per intent.

   **If intents span both routes, sequence the routes — never interleave or merge them:** run the Media Route (Step 4) to full completion for every media intent first, then the Content Route (Step 3) for every content intent. See Step 5.
2. **Call `search_metadata`** on the `metadata-grounding` MCP server using the intent itself as the query. **No `filters` array support** — `metadataType` is the only narrowing parameter, passed top-level:

   ```javascript
   search_metadata({ query: "<the user's intent>", metadataType: "ContentTypeBundle", limit: 100 })
   ```

  Each candidate already includes a full composite identifier (e.g. `00DVW00000CfBQP2A3::0T1VW000008sow60AA::ContentTypeBundle`) — use it as returned; never reconstruct it.

   **Check the outcome before doing anything else:**
   - **`metadata-grounding` is unavailable (the call errors/times out)** — you MUST call `get_content_types_for_workspace` (the workspace content-type fallback) before any Step 3/4 search tool; do not attempt `query_metadata`, there's nothing to look up, and do not skip straight to a search tool on an assumed FQN.
   - **Zero candidates returned** — ask the user one clarifying question to narrow the intent (`ask_followup_question`, same question/options as the "intent itself is ambiguous" case at the end of this step), then retry `search_metadata` once with the clarified query:
     - **Still zero candidates after that one retry** — apply the workspace content-type fallback. Do not ask a second clarifying question.
     - **One or more candidates on the retry** — continue to point 3.
   - **One or more candidates on the first call** — continue to point 3.

   **Fallback chain when `search_metadata` doesn't produce a usable candidate list** → Read `references/content-type-discovery.md` before running it: "Workspace content-type fallback" first, then "Wording fallback" as a last resort.

3. **Call `query_metadata`** with each candidate's identifier from point 2 (cap at top 5, batched into one `metadataIdentifiers` array):

   ```javascript
   query_metadata({ metadataIdentifiers: ["00DVW00000CfBQP2A3::0T1VW000008sow60AA::ContentTypeBundle"] })
   ```

   Read each entry's `typeDetails[].properties` — `mixins`, `typeClasses`, and `apiName` live there, not in the `search_metadata` response.

4. **Filter for supported types first, THEN decide the route among survivors — do not conflate the two:**
   - **Discard** any candidate whose `properties.mixins` lacks `sfdc_cms:deliveryApiEnabled` — only delivery-API-enabled types are searchable.
   - **Of the remainder, discard any whose `properties.typeClasses` lacks `sfdc_cms__structured`.** This is the single "supported for search" gate, not a content/media split — `sfdc_cms__structured` appears on both structured-content types and media types, so it only separates searchable types from unsearchable ones (e.g. `sfdc_cms__email` carries `sfdc_cms__content` but not `sfdc_cms__structured`, and must be discarded).
   - **Zero survive** — tell the user which types were found but aren't supported, then stop (don't guess a route). **Some, but not all, survive** — tell the user which got filtered out (plain statement, not a question), then continue with survivors. **All survive** — no message needed. → Read `references/content-type-discovery.md` § "Filter-result messages" for exact wording.
   - **Route on the top-ranked survivor's `properties.typeClasses`** (order returned by `search_metadata`): contains `sfdc_cms__media` → Media Route (Step 4); otherwise → Content Route (Step 3).
   - **Collect the FQN(s)** — the top-ranked survivor's `properties.apiName`. Add other surviving candidates' FQNs too if clearly relevant to the same intent and sharing the same classification, passing all as one comma-separated `contentTypeFqn` value rather than searching per type.
5. **Carry the scope from Step 1** (public channels only, or public channels plus a `channelId`) into whichever route is invoked — see the `channelIds` field in each route below.

**If intent itself is ambiguous** (e.g. "find me some content" with no hint of type or subject) → Read `references/content-type-discovery.md` § "Intent itself is ambiguous" for the exact question/options before calling `search_metadata`. Do not guess.

## Step 3: Content Route

Follow this sequence for each intent Step 2 routed here. The content type FQN(s) are already known from Step 2.

1. **Build the search query:**
   - **Extract keywords** — concrete nouns and named subjects that would appear in the content's title or body. Use domain-specific synonyms, max 10 terms, joined with ` OR `. E.g. "blog posts about sustainable business practices" → `sustainable OR sustainability OR business OR environmental`.
   - **Extract taxonomies** — descriptive qualities, categories, or topical tags only (adjectives, categories, attributes — not concrete nouns). Stringify as `{"OR": ["term1", "term2"]}`, or `"{}"` if none apply. E.g. "sustainable business practices and environmental responsibility" → `{"OR": ["Business", "Corporate", "Environment", "Responsibility"]}`; "FAQs about password resets" → `"{}"` (no descriptive/categorical terms).
   - Load `assets/search-payload-template.json` for the request payload structure. Set `contentTypeFqn` to the comma-separated FQN list collected in Step 2. `contentAccessScope` and `channelIds` are **mutually exclusive** — never send both in the same call — so they're set per-call in point 3 below, not here.
2. **Confirm with the user** — required two-message pattern (labeled-parameters chat message, then `ask_followup_question` with `Yes - search now` / `Edit search` / `Cancel`). Never put the labeled list inside `ask_followup_question`'s text — it strips formatting. → Read `references/content-route.md` § "Confirming the query before searching" for templates.
3. **Execute the search call(s)** per the scope from Step 1 — one call for public-only scope, two (public + channel-scoped) when a `channelId` is in scope. → Read `references/content-route.md` § "Executing the search call(s)" before parsing results — array/merge rules.
4. **Present up to 5 unique results total** (de-duplicated by `managedContentKey` for display only — an item found under more than one channel still appears once here), grouped by content type, with a `Load More` option if more remain. Each item shows its **Channel** as a per-item field — never the grouping key:

   ```text
   I found 3 content items:

   Editorial (c__Editorial):
   1. <title> — Channel: Public
   2. <title> — Channel: <uiBundle>

   Blog (sfdc_cms__blog):
   3. <title> — Channel: Public
   ```

   Only one content type FQN in scope → the heading may be omitted (still one group); the per-item Channel field is always shown. If an item exists under multiple channels, show its first/primary channel here — the choice between channels happens after selection (point 5), not at presentation time.

5. **User selects** one, several, or all items. **For each selected item whose delivery-details array has more than one entry**, ask which channel's copy to use — one `ask_followup_question` option per entry, named from `managedContentChannelDetails.name` — before displaying its details; items with zero or one entry go straight to display. Show `managedContentId`, `managedContentKey`, `language`, channel, and — only for a `PUBLIC_UNAUTHENTICATED`/`COMMUNITY` entry with a `contentUrl`, never a `WEB_APP` one — the full **Unauthenticated URL** (all query parameters). → Read `references/content-route.md` § "Disambiguating channel at selection" before asking — pass the channel names as `ask_followup_question`'s `options` array, never inline them in the question text.
6. **If the channelId in scope came from uiBundle discovery** (skip entirely for public-only scope or a user-supplied `channelId` with no uiBundle), offer the `experience-cms-content-render` hand-off using the same two-message pattern, passing each item's `title`, content type FQN, its chosen entry's `managedContentChannelDetails.id` (channel ID) **only when it has a delivery entry — omit for a zero-entry item, never a placeholder**, and either its Unauthenticated URL or, if absent, its `managedContentKey` **as `contentKey`** (the receiving skill's field name). → Read `references/content-route.md` § "Offering the render hand-off" for the full procedure.

→ Read `references/content-route.md` for the complete end-to-end worked example.

## Step 4: Media Route

Follow this sequence for each intent Step 2 routed here. The media content type FQN (e.g. `sfdc_cms__image`, `sfdc_cms__audio`, `sfdc_cms__video`, `sfdc_cms__document`) is already known from Step 2 — never assume it's an image; use whatever FQN Step 2 discovered for this intent.

1. **Present available search sources via `ask_followup_question` — no other tool calls yet.** Only the sources whose tools you actually have (via introspection), plus "Other", each as its own option. Wait for the user's selection before any tool call. → Read `references/media-route.md` § "Presenting available search sources" for the full template.
2. **Build the query, then confirm with the user before searching — required two-message pattern**, in the same turn:
   - **Search using keywords** (`search_media_cms_channels`): extract keywords (concrete nouns, max 10 terms) and taxonomies (descriptive/style/mood/category terms — extract every one the query actually contains; don't default to empty just because keywords were found). E.g. "luxury apartment with river view" → keywords `apartment OR villa OR penthouse OR residence`, taxonomies `{"OR": ["Luxury", "Premium", "Waterfront", "Riverside"]}`; "car" → taxonomies `"{}"` (no descriptive terms). Build the payload with `contentTypeFqn` set to the FQN(s) from Step 2, `searchLanguage` set to a locale (`en_US`, `es_MX`, ... — default `en_US`; **required, never null/omitted**), `searchLimit: 5`. → Read `references/media-route.md` for full worked examples.
   - **Search using Data 360 hybrid search** (`search_electronic_media`) — pass the user's query as-is to `searchQuery`, no extraction needed.
   - **Other** — ask for a direct URL, asset library path, or specific system to check (no confirmation step, since no tool is called).

   → Read `references/media-route.md` § "Confirming the query before searching" for the confirmation message templates (labeled-parameters chat message, then `ask_followup_question` with `Yes - search now` / `Edit search` / `Cancel`).
3. **Execute the search call(s)** per the scope from Step 1 — one call for public-only scope, two (public + channel-scoped) when a `channelId` is in scope; Data 360 hybrid search ignores channel scope entirely. → Read `references/media-route.md` § "Executing the search call(s)" before parsing results — array/merge rules.
4. **Present all unique results via `ask_followup_question`, grouped by content type** — one option per result (de-duplicated by unique identifier for display only — an item found under more than one channel still appears once here), labeled with title, content type, and channel (e.g. `Product Launch Hero Banner (sfdc_cms__image) — Public`). Mirrors the Content Route: content type is the grouping key, channel is a per-item field. Never auto-select.
5. **User selects** an item. **If its delivery-details array has more than one entry**, ask which channel's copy to use — one option per entry, named from `managedContentChannelDetails.name` — before displaying details. Show Content Name, Content Type, channel, and — only for a `PUBLIC_UNAUTHENTICATED`/`COMMUNITY` entry with a `contentUrl`, never a `WEB_APP` one — the full **Unauthenticated URL** (all query parameters). → Read `references/media-route.md` § "Disambiguating channel at selection" before asking — pass the channel names as `ask_followup_question`'s `options` array, never inline them in the question text.
6. **Offer the render hand-off** — always, with no uiBundle gating (unlike the Content Route's offer, which only appears when a uiBundle channel was in scope). Same two-message pattern: plain-text mention of the item, then `ask_followup_question` with `Yes` / `No`. On `Yes`, dispatch via `mcp__skill_bridge__load_skill("experience-cms-content-render")` — never the built-in Skill tool (separate registry, returns `Unknown skill`) — passing the selected item's `title`, content type FQN, the chosen entry's `managedContentChannelDetails.id` (channel ID) **only when it has a delivery entry — this route explicitly supports zero-entry items, so omit the channel ID for those rather than reading `.id` off nothing**, and either its Unauthenticated URL or, if absent, its `managedContentKey` **as `contentKey`** (the receiving skill's field name). If the load call fails, tell the user the hand-off failed and stop. On `No`, stop — the search is complete; do not apply the URL yourself as a fallback.

→ Read `references/media-route.md` for the complete worked example.

## Step 5: Present Combined Results

When a request mixes media and content intents, run the two routes **sequentially, each to full completion, not interleaved and not merged into one combined presentation**:

1. **Media Route first** — for every media intent, run Step 4 in full: present sources, build/confirm the query, search, present results, let the user select, and (point 6) offer the `experience-cms-content-render` hand-off (Yes/No). Finish this entire route — including the offer — before starting the Content Route.
2. **Content Route second** — for every content intent, run Step 3 in full: build/confirm the query, search, present results grouped by content type (channel shown per-item), let the user select, and (point 6) offer the `experience-cms-content-render` hand-off if a uiBundle channel is in scope.

Each route's results are labeled and presented on their own (e.g. "Images:" for the Media Route's output, then "Articles:" for the Content Route's) — never merge the two into one undifferentiated list, and never hold Media Route's results back to present alongside Content Route's.

## Error Handling

| Error | Response |
|---|---|
| No `search_content_cms_channels`/`search_media_cms_channels` tools found via introspection | "No content search connection is configured. Please connect a content-readonly MCP server." |
| Neither media tool available | "No automated media search sources are currently configured. Please provide a direct URL or asset library path." |
| `metadata-grounding` unavailable or no content types match | Apply the fallback chain in `references/content-type-discovery.md` — do not block or ask for an FQN |
| No search results (either route) | "No [content/media] found. Try broader keywords, removing descriptive terms, or a different [content type/source]." |
| Invalid user selection | Re-display options and ask again |
| Tool returns error (invalid input, missing argument, or otherwise) | Show error message, offer retry with corrected parameters **on that same tool — never fall through to the other route's search tool as a workaround** (see Key Principle 3) |
| Search tool on the connected server returns a server error (5xx, timeout, connection failure — not "no results") | **Fail the call — do NOT silently retry against a different server.** Tell the user to check that server's connection/session and wait before retrying. |

**Never silently fail on a route the user asked for.** If one route in a mixed request comes up empty, still present the other route's results and say so explicitly. This does not mean substituting a different server when the connected one errors — see the server-error row above.

## Key Principles

1. **Resolve channel scope first** — determine channel scope (Step 1) before any content-type discovery or search
2. **Search first, route second** — `search_metadata` + `query_metadata` decide the route; fall back to `get_content_types_for_workspace`, then intent wording, only when that comes up empty (Step 2)
3. **Never cross-route, including on failure** — content requests never hit media search tools and vice versa; if a route's search tool errors for any reason, fix and retry that same tool or stop and report the error — never fall through to the other route's tool as a workaround
4. **Metadata grounding is mandatory for content** — discover content type FQNs dynamically, never hardcode them
5. **Media route starts text-only** — present sources and wait before any tool call
6. **Confirm before searching (both routes)** — user approves query parameters before execution
7. **Never auto-select** — always wait for user choice, across channel scope and both routes
8. **Run mixed requests sequentially, Media Route first** — complete it fully (including the render offer) before starting the Content Route; present each route's results as its own labeled set, never merged
9. **Handle errors gracefully** — clear feedback and alternatives, per route
10. **Offer to render, don't assume** — both routes require Yes/No confirmation before the hand-off; only the gating differs — Content Route offers it only when a uiBundle channel was actually in scope, Media Route always offers it
11. **Never fail over to a different server on a server error** — fail the call and tell the user to check that server's session; don't silently retry elsewhere
12. **Group by content type, never by channel** — in both routes, channel is always a per-item field, never the group heading
13. **Disambiguate channel at selection, not before** — an item is shown once at presentation regardless of its delivery-details array length; only after selection do you ask which channel's copy to use, one option per entry by `managedContentChannelDetails.name`, in both routes
14. **Unauthenticated URL is public-channel-only** — `PUBLIC_UNAUTHENTICATED`/`COMMUNITY` entries only; never a `WEB_APP` (uiBundle) entry's `contentUrl`, in either route
