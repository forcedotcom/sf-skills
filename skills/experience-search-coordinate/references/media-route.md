# Media Route — Full Reference

Worked payload examples for the media route (Step 4 of SKILL.md).

**Media is not limited to images.** Step 2's `search_metadata` + `query_metadata` calls discover the actual FQN for the intent — it may be `sfdc_cms__image`, `sfdc_cms__audio`, `sfdc_cms__video`, `sfdc_cms__document`, or another `sfdc_cms__media`-typed FQN. Use whatever FQN was discovered; never default to `sfdc_cms__image`.

## Presenting available search sources

Reached at Step 4 point 1. Check your own tool list (introspection, not a tool call) for `search_media_cms_channels` and `search_electronic_media`. Include only the sources whose tools you actually have, plus "Other" as the last option, each as its own **option** in `ask_followup_question`'s `options` array — never as numbered lines inside the question text:

```text
Question: "Where would you like to search for that?"
Options:
  - Search using keywords — Search Salesforce CMS by keywords and taxonomies
  - Search using Data 360 hybrid search — Semantic search across Salesforce CMS and connected DAMs
  - Other — Provide your own URL or path
```

Wait for the user's selection. Do not call any tool before this point. **Other** — ask for a direct URL, asset library path, or specific system to check (no confirmation step needed, since no tool is called).

## Executing the search call(s)

Per the scope from Step 1. `contentAccessScope` and `channelIds` are **mutually exclusive fields — never include both in the same call**: no `channelId` in scope → one call with `contentAccessScope: "Public"` and no `channelIds`; a `channelId` in scope → two calls — one with `contentAccessScope: "Public"` and no `channelIds`, one with `channelIds` set to `"<channelId>"` and no `contentAccessScope`. Each result item already carries its own list of channel deliveries in `managedContentChannelDeliveryDetails` — same shape, and same "can hold many entries for one item" reality, as the Content Route (see `content-route.md` "Executing the search call(s)" for a real six-entry API response). Each entry's `managedContentChannelDetails.type` is `PUBLIC_UNAUTHENTICATED`, `COMMUNITY`, or `WEB_APP` (the channel-scoped call's uiBundle channel). **If the same item (by its unique identifier) appears in both responses, merge their `managedContentChannelDeliveryDetails` arrays** rather than picking one response and discarding the other — de-duplicate only exact repeats of the same channel id. Presentation still shows the item once; the channel choice is made after selection — see "Disambiguating channel at selection" below. (Data 360 hybrid search ignores channel scope entirely — no `channelIds`/`contentAccessScope` field, no channel to label.)

**The Unauthenticated URL is public-channel-only** — see "Handing off the selected media item" below: only a `PUBLIC_UNAUTHENTICATED` or `COMMUNITY` entry's `contentUrl` is ever surfaced; a `WEB_APP` entry's `contentUrl` never is, even though the field is present in the response.

## Search using keywords (`search_media_cms_channels`)

Keyword/taxonomy extraction rule: see `SKILL.md` Step 4 point 2. Extract taxonomy whenever the query contains a genuine descriptive/style/mood/category term — do not default to an empty taxonomy just because keywords were already found. Additional worked examples for media:
- "modern minimalist company logo" → keywords: logo, emblem, corporate logo; taxonomies: Modern, Minimalist, Clean
- "customer testimonial clips" → keywords: testimonial, customer, feedback, review; taxonomies: _(empty — no descriptive terms)_
- "bright spacious room" → keywords: _(empty — no concrete nouns)_; taxonomies: Bright, Spacious, Open, Airy, Light

**Process:**

1. **Analyze the query** — understand what the user is searching for (subject, attributes, domain)
2. **Determine locale** — format `en_US`, `es_MX`, `fr_FR` (default: `en_US`)
3. **Build the JSON payload:**

```json
{
  "inputs": [{
    "searchKeyword": "keyword1 OR keyword2 OR keyword3",
    "taxonomyExpression": "{\"OR\": [\"Taxonomy1\", \"Taxonomy2\"]}",
    "searchLanguage": "en_US",
    "contentAccessScope": "Public",
    "contentTypeFqn": "<fqn discovered in Step 2, e.g. sfdc_cms__image, sfdc_cms__audio, sfdc_cms__video, sfdc_cms__document>",
    "pageOffset": 0,
    "searchLimit": 5
  }]
}
```

**Field rules:**
- `searchKeyword`: join keywords with ` OR `. Empty string if no keywords.
- `taxonomyExpression`: stringified JSON `{"OR": ["term1", "term2"]}`. `"{}"` if no taxonomies.
- `contentAccessScope` / `channelIds`: **mutually exclusive — never send both in the same call.** The public-channels call sets `contentAccessScope: "Public"` and omits `channelIds` entirely. If Step 1 also found one or more `channelId`s, issue a **second** call with `channelIds` set to those values (comma-separated if more than one, e.g. `"0apXX0000001001,0apXX0000001002"`) and omit `contentAccessScope` entirely — merge/de-duplicate the two calls' results.
- `contentTypeFqn`: the FQN(s) discovered in Step 2 — never hardcode `sfdc_cms__image`.
- `pageOffset`: start at `0`, increment by `searchLimit` for pagination.
- `searchLimit`: default `5`, adjust if user requests more.

**Worked example — "luxury apartment with river view" (discovered FQN: `sfdc_cms__image`):**

```json
{
  "inputs": [{
    "searchKeyword": "apartment OR villa OR penthouse OR residence",
    "taxonomyExpression": "{\"OR\": [\"Luxury\", \"Premium\", \"Waterfront\", \"Riverside\"]}",
    "searchLanguage": "en_US",
    "contentAccessScope": "Public",
    "contentTypeFqn": "sfdc_cms__image",
    "pageOffset": 0,
    "searchLimit": 5
  }]
}
```

**Worked example — "car images" (no descriptive terms, discovered FQN: `sfdc_cms__image`):**

```json
{
  "inputs": [{
    "searchKeyword": "car OR automobile OR vehicle OR auto",
    "taxonomyExpression": "{}",
    "searchLanguage": "en_US",
    "contentAccessScope": "Public",
    "contentTypeFqn": "sfdc_cms__image",
    "pageOffset": 0,
    "searchLimit": 5
  }]
}
```

**Worked example — "customer testimonial audio clips" (discovered FQN: `sfdc_cms__audio`):**

```json
{
  "inputs": [{
    "searchKeyword": "testimonial OR customer success OR product satisfaction OR feedback OR review",
    "taxonomyExpression": "{}",
    "searchLanguage": "en_US",
    "contentAccessScope": "Public",
    "contentTypeFqn": "sfdc_cms__audio",
    "pageOffset": 0,
    "searchLimit": 5
  }]
}
```

## Search using Data 360 hybrid search (`search_electronic_media`)

1. Use the user's query **as-is** — no keyword extraction or transformation needed
2. Call `search_electronic_media(searchQuery="<user's query>")`

Example: user query "modern luxury apartment with natural lighting" → `search_electronic_media(searchQuery="modern luxury apartment with natural lighting")`

## Confirming the query before searching

Regardless of method, confirm the built query with the user before calling the search tool — this is the same required two-message pattern used by the Content Route (see `SKILL.md` Step 3, point 2). Never put the parameter list inside `ask_followup_question`'s `question` text; it strips line breaks and collapses everything into one paragraph.

**Message 1 (plain chat text):**

```text
I'll search for media with these parameters:

  Content Type: Image (sfdc_cms__image)
  Keywords: apartment OR villa OR penthouse OR residence
  Taxonomies: Luxury, Premium, Waterfront, Riverside
  Language: en_US
  Channels: Public
```

**Message 2 (immediately after):** `ask_followup_question` with options `Yes - search now` / `Edit search` / `Cancel`.

## Presenting Search Results

1. **Parse each call's response** — Extract all results (title and content type) and each item's full `managedContentChannelDeliveryDetails` array, merged across calls if the item appears in more than one response (per "Executing the search call(s)" above — nothing is dropped as a duplicate).
2. **Use `ask_followup_question`** to present ALL results as selectable **unique** options (one option per item, by identifier), grouped by content type — same grouping key as the Content Route (see `content-route.md` Step 6), never by channel. Show the title, content type, and channel on each option — do not display the URL. If an item's `managedContentChannelDeliveryDetails` array has more than one entry, show the **first** entry's channel name here as a lightweight hint only; the actual choice between channels is made after selection (see "Disambiguating channel at selection" below), not here. If more than one content type FQN is in scope, order the options by content type (the tool has no native grouping — approximate it by ordering and, where the UI allows a label, prefixing the option text with the content type). Regardless of grouping, always include the channel as a per-item suffix, e.g. `Product Launch Hero Banner (sfdc_cms__image) — Public`.
3. **Receive the user's selection** from the tool response

## Disambiguating channel at selection

Reached at Step 4 point 5, only when the selected item's (merged) `managedContentChannelDeliveryDetails` array has more than one entry. Build one option per entry from `managedContentChannelDetails.name`, in the order the array returns them — not a fixed two-option choice. **Call `ask_followup_question` with these as its actual `question` and `options` parameters — never concatenate the channel list into the question string itself**, the same rule every other question in this skill follows:

```text
question: "Which channel would you like to use for 'Modern Minimalist Logo'?"
options: ["Public", "landing-page"]
```

Wait for the reply before displaying the item's details (below) — use the record from the **chosen** entry, never assume entry `[0]` is the right one. If the array has zero entries, skip this question and display with the Unauthenticated URL line omitted; if it has exactly one entry, skip the question and use that entry directly. See `content-route.md` "Disambiguating channel at selection" for a real six-channel example — the array can hold far more than two entries.

**A `WEB_APP` entry is still a valid, selectable option here** — it's excluded only from the Unauthenticated URL line at display time (see "Handing off the selected media item" below), not from the channel choice itself.

## Handing off the selected media item

1. **Confirm the selection**, displaying:
   - **Content Name** — `title`
   - **Content Type** — `contentType` (e.g. `sfdc_cms__image`, `sfdc_cms__audio`, `sfdc_cms__video`, `sfdc_cms__document`)
   - **Channel** — the channel of the entry that was used (the item's only entry, or the one chosen in "Disambiguating channel at selection" above)
   - **Unauthenticated URL** — shown **only when that entry's `managedContentChannelDetails.type` is `PUBLIC_UNAUTHENTICATED` or `COMMUNITY` AND it has a `contentUrl`** — the complete URL including all query parameters (CMS and DAM URLs rely on them for authentication, resizing, and CDN routing; dropping them breaks the media item). E.g. `https://cms.example.com/media/img.jpg?oid=00D&refid=0EM&v=2` must be used in full. **Never shown for a `WEB_APP` (uiBundle) channel entry, even when `contentUrl` is present** — that URL isn't meant for public consumption. Omit the line entirely whenever either condition fails (absent `contentUrl`, `WEB_APP` type, or no entries at all) — do not show it blank or with a placeholder.
2. **Offer the render hand-off — always, no uiBundle gating** (unlike the Content Route's offer, which only appears when a uiBundle channel was in scope; see `content-route.md` "Offering the render hand-off"). Same required two-message pattern:

   **Message 1 (plain text):**

   ```text
   I can render "<title>" (<content type label>) using the experience-cms-content-render skill.
   ```

   **Message 2 (immediately after):** `ask_followup_question` with options `Yes` / `No`. Never restate the item's details inside the question text — the question stays generic (`"Invoke the render skill for this item?"`).

3. **On `Yes`** — dispatch via `mcp__skill_bridge__load_skill("experience-cms-content-render")` — never the built-in Skill tool (separate registry, returns `Unknown skill`). Pass the item's `title`, content type FQN, and the chosen entry's `managedContentChannelDetails.id` (channel ID) **only when the item has a delivery entry** — this route explicitly supports zero-entry items (see "Disambiguating channel at selection" above), and the render hand-off is always offered regardless, so a zero-entry item reaches this step with no entry to read `.id` from. **Omit the channel ID for it entirely — never a placeholder or `null`** — `experience-cms-content-render`'s own documented channel-resolution flow asks the user for the channel (or HALTs) when none is supplied. Also pass either its Unauthenticated URL (if present) or, if absent, its `managedContentKey` renamed to `contentKey` — `experience-cms-content-render`'s own `SKILL.md` names the field `contentKey`, not `managedContentKey`. If the load call fails, tell the user the hand-off failed and stop.
4. **On `No`** — stop; the search is complete. Do not apply the URL yourself as a fallback.
