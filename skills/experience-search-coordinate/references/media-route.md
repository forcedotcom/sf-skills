# Media Route — Full Reference

## Step 4: Media Route

Follow this sequence for each intent Step 2 routed here. The media content type FQN (e.g. `sfdc_cms__image`, `sfdc_cms__audio`, `sfdc_cms__video`, `sfdc_cms__document`) is already known from Step 2 — never assume it's an image; use whatever FQN Step 2 discovered for this intent.

1. **Present available search sources via `ask_followup_question` — no other tool calls yet.** Only the sources whose tools you actually have (via introspection), plus "Other", each as its own option. Wait for the user's selection before any tool call. → Read `references/media-route.md` § "Presenting available search sources" for the full template.
2. **Build the query, then confirm with the user before searching — required two-message pattern**, in the same turn:
   - **Search using keywords** (`search_media_cms_channels`): extract keywords (concrete nouns, max 10 terms) and taxonomies (descriptive/style/mood/category terms — extract every one the query actually contains; don't default to empty just because keywords were found). E.g. "luxury apartment with river view" → keywords `apartment OR villa OR penthouse OR residence`, taxonomies `{"OR": ["Luxury", "Premium", "Waterfront", "Riverside"]}`; "car" → taxonomies `"{}"` (no descriptive terms). Build the payload with `contentTypeFqn` set to the FQN(s) from Step 2, `searchLanguage` set to a locale (`en_US`, `es_MX`, ... — default `en_US`; **required, never null/omitted**), `searchLimit: 5`. → Read `references/media-route.md` for full worked examples.
   - **Search using Data 360 hybrid search** (`search_electronic_media`): verbatim `searchQuery`; bare ISO `searchLanguage` only if the schema lists it; confirm first. On zero results or a language error, ask the user before one retry without it; never retry after a server error → `references/media-route.md`.
   - **Other** — ask for a direct URL, asset library path, or specific system to check (no confirmation step, since no tool is called).

   → Read `references/media-route.md` § "Confirming the query before searching" for the confirmation message templates (labeled-parameters chat message, then `ask_followup_question` with `Yes - search now` / `Edit search` / `Cancel`).
3. **Execute the search call(s)** per the scope from Step 1 — one call for public-only scope, two (public + channel-scoped) when a `channelId` is in scope; Data 360 hybrid search ignores channel scope entirely. → Read `references/media-route.md` § "Executing the search call(s)" before parsing results — array/merge rules.
4. **Present all unique results via `ask_followup_question`, grouped by content type** — one option per result (de-duplicated by unique identifier for display only — an item found under more than one channel still appears once here), labeled with title, content type, and channel (e.g. `Product Launch Hero Banner (sfdc_cms__image) — Public`). Mirrors the Content Route: content type is the grouping key, channel is a per-item field. Never auto-select.
5. **User selects** an item. **If its delivery-details array has more than one entry**, ask which channel's copy to use — one option per entry, named from `managedContentChannelDetails.name` — before displaying details. Show Content Name, Content Type, channel, and — only for a `PUBLIC_UNAUTHENTICATED`/`COMMUNITY` entry with a `contentUrl`, never a `WEB_APP` one — the full **Unauthenticated URL** (all query parameters). → Read `references/media-route.md` § "Disambiguating channel at selection" before asking — pass the channel names as `ask_followup_question`'s `options` array, never inline them in the question text.
6. **Offer the render hand-off** — always, with no uiBundle gating (unlike the Content Route's offer, which only appears when a uiBundle channel was in scope). Same two-message pattern: plain-text mention of the item, then `ask_followup_question` with `Yes` / `No`. On `Yes`, dispatch via `mcp__skill_bridge__load_skill("experience-cms-content-render")` — never the built-in Skill tool (separate registry, returns `Unknown skill`) — passing the selected item's `title`, content type FQN, the chosen entry's `managedContentChannelDetails.id` (channel ID) **only when it has a delivery entry — this route explicitly supports zero-entry items, so omit the channel ID for those rather than reading `.id` off nothing**, and either its Unauthenticated URL or, if absent, its `managedContentKey` **as `contentKey`** (the receiving skill's field name). If the load call fails, tell the user the hand-off failed and stop. On `No`, stop — the search is complete; do not apply the URL yourself as a fallback.

→ Read `references/media-route.md` for the complete worked example.


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

Keyword/taxonomy extraction rule: see Step 4 point 2 at the top of this file. Extract taxonomy whenever the query contains a genuine descriptive/style/mood/category term — do not default to an empty taxonomy just because keywords were already found. Additional worked examples for media:
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

1. Pass `searchQuery` **verbatim** — same language, same script as the user wrote it. No translation, no keyword extraction: translating first only makes step 2 harder, since you'd be detecting the language of your own translation instead of the user's actual words. When the request has more than one search intent (`SKILL.md` Step 2 point 1), this intent's query is only the user's own words for this intent, cut out as written — never the whole message, and never reworded or translated.
2. **Determine language** — once per intent, as a short ISO code, in this order:
   - **The user names the language of the content they want** ("the French article about X", "images labeled in Japanese", "en español") → use that language, even when the request itself is written in another language. `searchQuery` stays verbatim; only `searchLanguage` follows the named language.
   - **Otherwise** → the language of this intent's own `searchQuery` text (point 1), read directly off the user's literal wording before any translation happens in your reasoning. In a request that mixes languages across intents, each intent gets its own code — never one code for the whole message. E.g. "trouve-moi un article sur les pinceaux, and also a hero image of a beach" → `fr` for the article (Content Route), `en` for the image (Media Route).

   Bare 2-letter codes (`en`, `fr`, `de`, `es`, `ja`, ...) cover most languages and are the validated, simpler form; a few regional splits need a country suffix instead (`pt_BR`, `zh_CN`, `zh_TW`, ...). Default to `en` only when the message is genuinely ambiguous (e.g. a bare product name) — never because translating felt natural. Use the bare 2-letter form whenever one exists — the backend accepts only the platform's own language codes, so `fr` works but `fr_FR` is rejected as invalid (`en` and `en_US` both work because `en_US` is itself a platform code).
3. Call `search_electronic_media(searchQuery="<verbatim query>", searchLanguage="<language code>")`. **Only send `searchLanguage` if the tool's input schema actually lists it** — orgs without language-variant search enabled don't declare the input at all. When it's absent, call with `searchQuery` alone, skip the language line in the confirmation message, and skip steps 4–5 (the backend searches primary-language content only).
4. **Offer one retry with `searchLanguage` omitted entirely — ask the user first, never retry silently — but only when the first call either:**
   - returns **zero results**, **or**
   - fails with an **input-validation error about the language value itself** — an unrecognized language code errors the whole call (for example, `INVALID_API_INPUT` / "Specify a valid language code, such as en_US, fr, or de.") rather than returning an empty list.

   **Do NOT offer this retry on a server or transport error (5xx, timeout, connection failure).** Those must fail per `SKILL.md`'s Error Handling table — omitting the language cannot fix them and would mask the real failure. The retry exists only for the two language-specific cases above.

   Offer it before concluding nothing exists and before suggesting broader keywords: tell the user what happened in plain chat text (e.g. "No results found in French."), then `ask_followup_question` with options `Yes - search without language filter` / `No - stop here`. The retry is a second backend call the user didn't confirm, so they decide whether it runs. Skip the question only if the user already said, in this conversation, to fall back to any language when nothing matches theirs — then retry directly. Omitting the field makes the backend fall back to each item's own primary/default language variant instead of the requested one — so an item that only has, say, a French variant still surfaces on the retry even when the user asked in English. Only fall through to "no results" / broadening suggestions if the user declines, or the retry also comes back empty.
5. **Read each result item's `language` field to know which language variant you actually got** (a locale string such as `en_US` or `fr`). If it differs from the language the user asked for — typically after the retry — say so explicitly when presenting that item, e.g. "No French version exists for this item — here's the original in English." Never present a fallback-language result as if it were the requested-language match; the user needs to know a substitution happened.

   If `language` is **absent** on the results of a call that sent `searchLanguage`, the backend couldn't apply the language filter (for example, the org's search index predates language-variant support) and silently returned primary-language content instead — even on the first call, with no error and no empty list. Don't claim the results are in the requested language; tell the user the search couldn't be restricted to that language.

This is a **strict** filter, not soft ranking like the keyword route: the backend only returns items carrying that exact language variant, and it does **not** fall back to English (or any other language) per item on its own — that's why step 4's retry exists as an explicit, user-approved second call, not something the backend does silently.

Example — French input "trouve-moi une image de pinceaux depuis le CMS" → `search_electronic_media(searchQuery="trouve-moi une image de pinceaux depuis le CMS", searchLanguage="fr")`.

Example of the retry — English input "give me an image of a snowboard from the CMS" → first call `search_electronic_media(searchQuery="give me an image of a snowboard from the CMS", searchLanguage="en")` returns zero results (the only snowboard item in the org has a French variant, not English) → tell the user "No results found in English." and ask whether to search without the language filter → user picks `Yes - search without language filter` → retry `search_electronic_media(searchQuery="give me an image of a snowboard from the CMS")` with `searchLanguage` omitted → the item surfaces with `language: "fr"` → tell the user: "No English version exists for this item — here's the original in French."

## Confirming the query before searching

Regardless of method, confirm the built query with the user before calling the search tool — this is the same required two-message pattern used by the Content Route (see `content-route.md` Step 3, point 2). Never put the parameter list inside `ask_followup_question`'s `question` text; it strips line breaks and collapses everything into one paragraph.

**Message 1 (plain chat text):**

```text
I'll search for media with these parameters:

  Content Type: Image (sfdc_cms__image)
  Keywords: apartment OR villa OR penthouse OR residence
  Taxonomies: Luxury, Premium, Waterfront, Riverside
  Language: en_US
  Channels: Public
```

**Message 1 — Data 360 hybrid search variant** (surface the detected language so the user can catch a mis-detection before the search runs — language detection is the most error-prone step of this route):

```text
I'll search Data 360 hybrid search with:

  Query: trouve-moi une image de pinceaux depuis le CMS
  Language: fr   (auto-detected — tell me if this is wrong)
```

Show `Query` exactly as the user wrote it (verbatim) and `Language` as the bare code you'll send. When the code came from a language the user named (step 2 of "Search using Data 360 hybrid search") rather than from the query's wording, label it `(requested)` instead of `(auto-detected — tell me if this is wrong)`, so the user sees the query and language differ on purpose. This route has no `Content Type` / `Keywords` / `Taxonomies` / `Channels` lines — it ignores channel scope and does its own semantic matching.

**Message 2 (immediately after):** `ask_followup_question` with options `Yes - search now` / `Edit search` / `Cancel`.

## Presenting Search Results

1. **Parse each call's response** — Extract all results (title and content type) and each item's full `managedContentChannelDeliveryDetails` array, merged across calls if the item appears in more than one response (per "Executing the search call(s)" above — nothing is dropped as a duplicate). Data 360 hybrid search results have a different shape: each item carries `mediaUrl` (or a `mediaUrls` list of `{channelId, channelName, url}`) instead of `managedContentChannelDeliveryDetails`, plus a `language` field when language-variant search applied — use `language` per step 5 of "Search using Data 360 hybrid search" above.
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
