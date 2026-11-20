# Content Route — Full Reference

## Step 3: Content Route

Follow this sequence for each intent Step 2 routed here. The content type FQN(s) are already known from Step 2.

1. **Present search sources via `ask_followup_question` before any tool call** — only sources whose tools you have, plus "Other"; wait for the choice. → Read `references/content-route.md` § "Presenting available search sources".
2. **Build the query, then confirm with the user before searching — required two-message pattern**, in the same turn:
   - **Search using keywords** (`search_content_cms_channels`):
     - **Extract keywords** — concrete nouns and named subjects likely in the title or body, plus domain synonyms; max 10, joined with ` OR `. E.g. "blog posts about sustainable business practices" → `sustainable OR sustainability OR business OR environmental`.
     - **Extract taxonomies** — descriptive qualities, categories, or topical tags only (not concrete nouns), stringified as `{"OR": ["term1", "term2"]}`, or `"{}"` if none.
     - Payload: `assets/search-payload-template.json`, `contentTypeFqn` = the comma-separated FQN list from Step 2. `contentAccessScope` and `channelIds` are **mutually exclusive** — never both in one call — so they're set per call in point 3.
   - **Search using Data 360 hybrid search** (`search_digital_content`): verbatim `searchQuery`; bare ISO `searchLanguage` only if the schema lists it; confirm first. On zero results or a language error, ask the user before one retry without it → `references/content-route.md`.
   - **Other** — ask for a direct URL, asset library path, or specific system to check (no confirmation step, since no tool is called).

   → Read `references/content-route.md` § "Confirming the query before searching" for the confirmation message templates (labeled-parameters chat message, then `ask_followup_question` with `Yes - search now` / `Edit search` / `Cancel`).
3. **Execute the search call(s)** — keyword search: one call for public-only scope, two (public + channel-scoped) when a `channelId` is in scope. Hybrid: one call, no channel scope. → Read `references/content-route.md` § "Executing the search call(s)" (keyword) or the hybrid section (field mapping) before parsing results.
4. **Present up to 5 unique results total** (de-duplicated by `managedContentKey` for display only — an item found under more than one channel still appears once here), grouped by content type, with a `Load More` option if more remain (keyword search only). Each item shows its **Channel** as a per-item field — never the grouping key:

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


## Presenting available search sources

Before any tool call, dispatch `ask_followup_question` offering only the sources whose tools you actually have (via introspection), plus "Other". Each is its own option — never numbered lines inside the question text:

```text
question: "How would you like to search for content?"
options:
  - "Search using keywords — Search Salesforce CMS by keywords and taxonomies"
  - "Search using Data 360 hybrid search — Semantic (vector + keyword) search across Salesforce CMS and connected DAMs"
  - "Other — Provide your own URL, asset library path, or system to check"
```

Wait for the user's selection. Do not call any tool before this point. Then follow the matching branch:
- **Search using keywords** → `search_content_cms_channels` (build keywords + taxonomies, confirm, execute per scope — see below).
- **Search using Data 360 hybrid search** → `search_digital_content` (verbatim query + bare ISO `searchLanguage` when the schema lists it — see "Search using Data 360 hybrid search" below).
- **Other** → ask for a direct URL, asset library path, or specific system to check. No confirmation step, since no tool is called.

## Confirming the query before searching

Required two-message pattern, same turn — regardless of which source the user picked. The Message 1 template depends on the source: keyword search lists the full parameter set, Data 360 hybrid search lists only the verbatim query and detected language.

**Message 1 — keyword search (chat-visible plain text — NOT inside `ask_followup_question`):** print the parameters as a labeled list, one field per line:

```text
I'll search for content with these parameters:

  Content Type: <label> (<fqn>[, <label2> (<fqn2>), ...])
  Keywords: <keyword1 OR keyword2 OR ...>
  Taxonomies: <term1, term2, ...>
  Language: <en_US>
  Channels: Public[, plus <uiBundle> channel]
```

**Message 1 — Data 360 hybrid search variant** (surface the detected language so the user can catch a mis-detection before the search runs — language detection is the most error-prone step of this route):

```text
I'll search Data 360 hybrid search with:

  Query: trouve-moi un article sur les pinceaux depuis le CMS
  Content Type: Blog (sfdc_cms__blog)
  Language: fr   (auto-detected — tell me if this is wrong)
```

Show `Query` exactly as the user wrote it (verbatim), `Content Type` as the FQN(s) you'll send as `contentTypeFqn` (omit the line when you won't send it), and `Language` as the bare code you'll send. When the code came from a language the user named (step 2 of "Search using Data 360 hybrid search") rather than from the query's wording, label it `(requested)` instead of `(auto-detected — tell me if this is wrong)`, so the user sees the query and language differ on purpose. This route has no `Keywords` / `Taxonomies` / `Channels` lines — it ignores channel scope and does its own semantic matching.

**Message 2 (immediately after, same turn):** dispatch `ask_followup_question` with a short question and options — `Yes - search now` / `Edit search` / `Cancel`.

**Never put the labeled list inside `ask_followup_question`'s `question` text.** That UI strips line breaks and formatting, which is exactly what collapses the parameters back into a single paragraph.

## Executing the search call(s)

Per the scope determined in Step 1. `contentAccessScope` and `channelIds` are **mutually exclusive fields — never include both in the same call**:
- **No `channelId` in scope (public channels only)** — one call to `search_content_cms_channels` with `contentAccessScope: "Public"` and no `channelIds` field at all.
- **A `channelId` is in scope** — two calls: one with `contentAccessScope: "Public"` and no `channelIds` (public channels), and one with `channelIds` set to the discovered `channelId` and no `contentAccessScope` field at all. Each result item already carries its own list of channel deliveries in `managedContentChannelDeliveryDetails` — this array can hold many entries for a single item (a public-unauthenticated channel, a Community channel, several uiBundle channels, etc. — see the real API response below), independent of how many calls were made. **If the same item (by `managedContentKey`) appears in both responses, merge their `managedContentChannelDeliveryDetails` arrays** rather than picking one response and discarding the other — de-duplicate only exact repeats of the same `managedContentChannelDetails.id`. Presentation (Step 3 point 4) still shows the item once; selection (Step 3 point 5) is where the channel choice actually gets made — see "Disambiguating channel at selection" below.

From each response, parse `outputValues.searchResults[]`, extracting `title`, `contentType`, `managedContentId`, `managedContentKey`, `language`, and the **full `managedContentChannelDeliveryDetails` array** — never just index `[0]`. Each entry pairs a `contentUrl` with `managedContentChannelDetails.{id, name, type}` (the channel it's delivered to). `type` is one of `PUBLIC_UNAUTHENTICATED`, `COMMUNITY`, or `WEB_APP` (a uiBundle-scoped channel — this is what the channel-scoped call in Step 1 discovers). A single item's array can be empty (not yet delivered to any channel — omit the Unauthenticated URL line entirely for that item), have one entry (use it directly, no question needed), or have several (ask which channel — see "Disambiguating channel at selection" below).

**The Unauthenticated URL is public-channel-only.** Only a `PUBLIC_UNAUTHENTICATED` or `COMMUNITY` entry's `contentUrl` is ever shown to the user as the Unauthenticated URL. A `WEB_APP` entry's `contentUrl` is **never** surfaced — omit the URL line entirely when the chosen (or only) entry's type is `WEB_APP`, even though the field is present in the response. This applies after channel disambiguation (below), not before — a `WEB_APP` entry is still offered as a selectable channel option; it just never produces a displayed URL once chosen.

**Real API response — `WEB_APP` (uiBundle) channel, from the channel-scoped call:**

```json
{
  "title": "Apple Inc.",
  "contentType": "c__StockMarket",
  "managedContentId": "20Yxx0000000001",
  "managedContentKey": "MCICPC4X5KE5ATHMTN4EYK5DOCYM",
  "managedContentChannelDeliveryDetails": [
    {
      "contentUrl": "https://.../channels/0apxx0000000001AAA/contents/20Yxx0000000001?language=en_US",
      "managedContentChannelDetails": { "id": "0apxx0000000001", "name": "testinternalapp", "type": "WEB_APP" }
    }
  ]
}
```

Even though `contentUrl` is present, this item's only entry is `WEB_APP` — the Unauthenticated URL line is omitted for it. Only `managedContentId`, `managedContentKey`, `language`, and channel (`testinternalapp`) are shown.

**Real API response** (one item, six delivery entries, from a single call — no second channel-scoped call was even involved):

```json
{
  "title": "Housing Prices In Japan",
  "contentType": "sfdc_cms__news",
  "managedContentKey": "MCVL5CJAB4NBBBRPTMY2N3DALBB4",
  "managedContentChannelDeliveryDetails": [
    { "contentUrl": "https://.../0apxx0000000002AAA/...", "managedContentChannelDetails": { "id": "0apxx0000000002", "name": "Test CMS Channel", "type": "PUBLIC_UNAUTHENTICATED" } },
    { "contentUrl": "https://.../0apxx0000000003AAA/...", "managedContentChannelDetails": { "id": "0apxx0000000003", "name": "testLWR", "type": "COMMUNITY" } },
    { "contentUrl": "https://.../0apxx0000000004AAA/...", "managedContentChannelDetails": { "id": "0apxx0000000004", "name": "Test Channel 2", "type": "PUBLIC_UNAUTHENTICATED" } },
    { "contentUrl": "https://.../0apxx0000000005AAA/...", "managedContentChannelDetails": { "id": "0apxx0000000005", "name": "Test Channel 3", "type": "PUBLIC_UNAUTHENTICATED" } },
    { "contentUrl": "https://.../0apxx0000000006AAA/...", "managedContentChannelDetails": { "id": "0apxx0000000006", "name": "Test Channel 4", "type": "PUBLIC_UNAUTHENTICATED" } },
    { "contentUrl": "https://.../0apxx0000000007AAA/...", "managedContentChannelDetails": { "id": "0apxx0000000007", "name": "Test Channel 5", "type": "PUBLIC_UNAUTHENTICATED" } }
  ]
}
```

The multi-channel case is not "one entry from the public call, one from the channel-scoped call" — it's whatever the array actually contains, however many entries that is.

## Search using Data 360 hybrid search (`search_digital_content`)

Chosen when the user picked "Search using Data 360 hybrid search" at the source step. Data 360 hybrid search (vector + keyword) runs across Salesforce CMS and any connected third-party CMS/DAM.

1. Pass `searchQuery` **verbatim** — same language, same script as the user wrote it. No translation, no keyword extraction, no ` OR `-joining, no `taxonomyExpression`, no `channelIds`, no pagination (the backend returns at most 5 results). Translating first only makes step 2 harder, since you'd be detecting the language of your own translation instead of the user's actual words. When the request has more than one search intent (`SKILL.md` Step 2 point 1), this intent's query is only the user's own words for this intent, cut out as written — never the whole message, and never reworded or translated.
2. **Determine language** — once per intent, as a short ISO code, in this order:
   - **The user names the language of the content they want** ("the French article about X", "images labeled in Japanese", "en español") → use that language, even when the request itself is written in another language. `searchQuery` stays verbatim; only `searchLanguage` follows the named language.
   - **Otherwise** → the language of this intent's own `searchQuery` text (point 1), read directly off the user's literal wording before any translation happens in your reasoning. In a request that mixes languages across intents, each intent gets its own code — never one code for the whole message. E.g. "trouve-moi un article sur les pinceaux, and also a hero image of a beach" → `fr` for the article (Content Route), `en` for the image (Media Route).

   Bare 2-letter codes (`en`, `fr`, `de`, `es`, `ja`, ...) cover most languages and are the validated, simpler form; a few regional splits need a country suffix instead (`pt_BR`, `zh_CN`, `zh_TW`, ...). Default to `en` only when the message is genuinely ambiguous (e.g. a bare product name) — never because translating felt natural. Use the bare 2-letter form whenever one exists — the backend accepts only the platform's own language codes, so `fr` works but `fr_FR` is rejected as invalid (`en` and `en_US` both work because `en_US` is itself a platform code).
3. **Data 360 hybrid search ignores channel scope entirely** — there is no public vs. channel-scoped split. Make a **single call** regardless of whether a `channelId` is in scope from Step 1: `search_digital_content(searchQuery="<verbatim query>", contentTypeFqn="<Step 2 FQN(s)>", searchLanguage="<language code>")`. Don't send `contentAccessScope`: the tool accepts only `Public`, and it would widen results to guest-accessible community sites.
   - **`contentTypeFqn`** — the same comma-separated FQN list Step 2 produced for keyword search (e.g. `sfdc_cms__blog,sfdc_cms__news`). The backend filters to those types before searching, so both sources answer the same question. An FQN that doesn't exist in the org fails the whole call with `INVALID_API_INPUT`, so send only FQNs Step 2 actually discovered — if Step 2 found none, omit the field and the backend searches all content types.
   - **`searchLanguage`** — **only send it if the tool's input schema actually lists it** — orgs without language-variant search enabled don't declare the input at all. When it's absent, call without it, skip the language line in the confirmation message, and skip steps 4–5 (the backend searches primary-language content only).
4. **Offer one retry with `searchLanguage` omitted entirely — ask the user first, never retry silently — but only when the first call either:**
   - returns **zero results**, **or**
   - fails with an **input-validation error about the language value itself** — an unrecognized language code errors the whole call (for example, `INVALID_API_INPUT` / "Specify a valid language code, such as en_US, fr, or de.") rather than returning an empty list.

   **Do NOT offer this retry on a server or transport error (5xx, timeout, connection failure).** Those must fail per `SKILL.md`'s Error Handling table — omitting the language cannot fix them and would mask the real failure. The retry exists only for the two language-specific cases above.

   Offer it before concluding nothing exists and before suggesting broader keywords: tell the user what happened in plain chat text (e.g. "No results found in French."), then `ask_followup_question` with options `Yes - search without language filter` / `No - stop here`. The retry is a second backend call the user didn't confirm, so they decide whether it runs. Skip the question only if the user already said, in this conversation, to fall back to any language when nothing matches theirs — then retry directly. This is the same policy as the Media Route's hybrid search (`media-route.md`). Omitting the field makes the backend fall back to each item's own primary/default language variant instead of the requested one — so an item that only has, say, a French variant still surfaces on the retry even when the user asked in English. Only fall through to "no results" / broadening suggestions if the user declines, or the retry also comes back empty.
5. **Read each result item's `language` field to know which language variant you actually got** (a locale string such as `en_US` or `fr`). If it differs from the language the user asked for — typically after the retry — say so explicitly when presenting that item, e.g. "No French version exists for this item — here's the original in English." Never present a fallback-language result as if it were the requested-language match; the user needs to know a substitution happened.

   If `language` is **absent** on the results of a call that sent `searchLanguage`, the backend couldn't apply the language filter (for example, the org's search index predates language-variant support) and silently returned primary-language content instead — even on the first call, with no error and no empty list. Don't claim the results are in the requested language; tell the user the search couldn't be restricted to that language.

This is a **strict** filter, not soft ranking like the keyword route: the backend only returns items carrying that exact language variant, and it does **not** fall back to English (or any other language) per item on its own — that's why step 4's retry exists as an explicit, user-approved second call, not something the backend does silently.

Example — French input "trouve-moi un article sur les pinceaux depuis le CMS" (Step 2 discovered `sfdc_cms__blog`) → `search_digital_content(searchQuery="trouve-moi un article sur les pinceaux depuis le CMS", contentTypeFqn="sfdc_cms__blog", searchLanguage="fr")`.

Example of the retry — English input "give me a blog post about a snowboard from the CMS" → first call `search_digital_content(searchQuery="give me a blog post about a snowboard from the CMS", contentTypeFqn="sfdc_cms__blog", searchLanguage="en")` returns zero results (the only snowboard article in the org has a French variant, not English) → tell the user "No results found in English." and ask whether to search without the language filter → user picks `Yes - search without language filter` → retry `search_digital_content(searchQuery="give me a blog post about a snowboard from the CMS", contentTypeFqn="sfdc_cms__blog")` with `searchLanguage` omitted → the item surfaces with `language: "fr"` → tell the user: "No English version exists for this item — here's the original in French."

Still confirm first via the two-message pattern before this single call — use the **Data 360 hybrid search variant** of Message 1 (`Query` / `Content Type` / `Language`, no `Keywords` / `Taxonomies` / `Channels`) shown under § "Confirming the query before searching" above, then `ask_followup_question` with `Yes - search now` / `Edit search` / `Cancel`, exactly as for keyword search.

### Parsing the `search_digital_content` response

The response shape differs from `search_content_cms_channels`. Map each result to the same content-route fields the rest of this reference uses, so "Disambiguating channel at selection", display, and the render hand-off all work unchanged:

| `search_digital_content` field | Content-route equivalent |
|---|---|
| `contentName` | `title` |
| `contentId` | `managedContentId` |
| `contentKey` | `managedContentKey` |
| `contentTypeFqn` | `contentType` |
| `contentUrls[]` → each `{ channelName, channelId, url }` | `managedContentChannelDeliveryDetails[]` → each `{ contentUrl: url, managedContentChannelDetails: { id: channelId, name: channelName } }` |
| `contentUrl` (a single string, sent instead of `contentUrls[]` on orgs without all-channel URLs) | one `managedContentChannelDeliveryDetails[]` entry `{ contentUrl }` — no channel ID or name comes with it, so skip channel disambiguation and leave the Channel line out |
| `language` | `language` — present when language-variant search applied; use it per step 5 above |
| `searchScore` | _(extra — hybrid-only relevance score; optional to surface)_ |

Results are under `outputValues.searchResults[]`. Only `contentId` and `contentKey` are always present; any other field is left out when it has no value — never sent as `null` or `[]`.

**Omissions to account for:** if neither `contentUrls` nor `contentUrl` is present, the item has no public delivery — map it to an empty `managedContentChannelDeliveryDetails` and omit the Unauthenticated URL line. A `contentUrls[]` entry's `channelName` can be missing when the name couldn't be resolved — label that channel by its `channelId`. If `language` is absent, omit the Language line for that item (and, if the call sent `searchLanguage`, tell the user the search couldn't be restricted to the requested language — see step 5).

**Channel type.** The hybrid response carries no channel `type`, and doesn't need one: the backend only builds `contentUrls[]` entries for public channels, so treat every mapped entry as `PUBLIC_UNAUTHENTICATED` — its `url` is the Unauthenticated URL. uiBundle (`WEB_APP`) channels never appear in hybrid results.

**Content types.** When the call sent `contentTypeFqn`, every result is already one of Step 2's types — no client-side filtering. When it was omitted (Step 2 found no FQN), results can be any content type; group them by their own `contentTypeFqn`.

After mapping, the `managedContentChannelDeliveryDetails` array behaves identically to the keyword case (zero / one / many entries), so everything downstream — channel disambiguation, display, and the render hand-off — is reused as-is.

## Disambiguating channel at selection

Reached at Step 3 point 5, only for a selected item whose (merged, per "Executing the search call(s)" above) `managedContentChannelDeliveryDetails` array has more than one entry. Build one option per entry, using that entry's `managedContentChannelDetails.name`, in the order the array returns them — not a fixed two-option choice. **Call `ask_followup_question` with these as its actual `question` and `options` parameters — never concatenate the channel list into the question string itself**, the same rule every other question in this skill follows:

```text
question: "Which channel would you like to use for 'Sustainability Report 2024'?"
options: ["Public", "landing-page"]
```

Wait for the reply before displaying that item's details, and use the record from the **chosen** entry — never assume entry `[0]` is the right one. An item selected alongside it whose array has zero or one entry does **not** get a question — zero entries goes straight to display with the Unauthenticated URL line omitted; one entry goes straight to display using that entry. Once every multi-entry item in the selection has been resolved (or immediately, if none were), display all selected items' details (Step 7 below).

**Real-world scale** — the "Housing Prices In Japan" response above would produce:

```text
question: "Which channel would you like to use for 'Housing Prices In Japan'?"
options: ["Test CMS Channel", "testLWR", "Test Channel 2", "Test Channel 3", "Test Channel 4", "Test Channel 5"]
```

Ask from the full array every time, however many entries it has — don't special-case it down to "Public vs. the one uiBundle channel." All six names go in the `options` array; the `question` string stays that one short sentence.

**A `WEB_APP` entry is still a valid, selectable option here** — it's excluded only from the Unauthenticated URL line at display time (see "Executing the search call(s)" above), not from the channel choice itself.

## Offering the render hand-off

Only when the channelId in scope came from uiBundle discovery (skip entirely for public-only scope, or a user-supplied `channelId` with no associated uiBundle). Same required two-message pattern as the search confirmation above:

**Message 1 (plain text):**

```text
I can render the following in the <uiBundle> app:

  1. <title> (<content type label>)
  2. <title> (<content type label>)
```

**Message 2 (immediately after):** `ask_followup_question` with options `Yes` / `No`. Never restate the item list or count inside the question text — the question stays generic (`"Render this content in the <uiBundle> app?"`).

- **Yes** — dispatch via `mcp__skill_bridge__load_skill("experience-cms-content-render")` — never the built-in Skill tool (separate registry, returns `Unknown skill`). Pass each selected item's `title`, content type FQN, its chosen entry's `managedContentChannelDetails.id` (channel ID) **only when that item's (merged) `managedContentChannelDeliveryDetails` array has an entry** — use the chosen entry if the array had more than one, or the sole entry if it had exactly one. **An item with zero entries has no entry to read `.id` from — omit the channel ID field for it entirely, never a placeholder or `null`**; `experience-cms-content-render`'s own documented channel-resolution flow asks the user for the channel (or HALTs) when none is supplied, so this is safe to leave out. Also pass either its Unauthenticated URL or, if absent, its `managedContentKey` renamed to `contentKey` — `experience-cms-content-render`'s own `SKILL.md` names the field `contentKey`, not `managedContentKey`. If the load call fails, tell the user the hand-off failed and stop — don't render yourself.
- **No** — stop; the search is complete.

## Building the search query

Keyword/taxonomy extraction rule: see Step 3 point 2 at the top of this file (the Media Route uses the same split — see `media-route.md` for media-specific examples). Additional worked examples for content:
- "press release about our product launch" → keywords: launch, announcement, release, product launch; taxonomies: Launch, Announcement, News
- "FAQs about password resets" → keywords: password, reset, login, account; taxonomies: _(empty — no descriptive/categorical terms)_

1. **Determine locale** — format `en_US`, `es_MX`, `fr_FR` (default: `en_US`)
2. **Build the JSON payload** — `searchKeyword` joins keywords with ` OR `; `taxonomyExpression` is a stringified `{"OR": ["term1", "term2"]}`, or `"{}"` if none.

## Complete End-to-End Example

**User Request:**
> "I need to find blog posts about sustainable business practices and environmental responsibility for our company website."

---

**Step 1: Determine Search Intent**

Intent parsed:
- Content type: Blog posts
- Keywords: sustainable, business, practices, environmental, responsibility
- Clear intent → proceed to Step 2

---

**Step 2: Discover Content Types**

Call `search_metadata` — this tool has no `filters` array; `metadataType` is the only accepted narrowing parameter:
```json
{
  "query": "blog post article",
  "metadataType": "ContentTypeBundle",
  "limit": 100
}
```

This returns candidate matches only — no `jsonAttributes`, so routing and delivery-API filtering aren't possible yet. Each candidate already includes a full composite identifier, e.g. `00Dxx0000000000AAA::0T1xx0000000001AAA::ContentTypeBundle` (name `sfdc_cms__blog`) among others — use it as returned.

Call `query_metadata` with each candidate's identifier from above, as-is, batched into one `metadataIdentifiers` array:
```json
{
  "metadataIdentifiers": [
    "00Dxx0000000000AAA::0T1xx0000000001AAA::ContentTypeBundle"
  ]
}
```

For each entry, read `typeDetails[].properties` — `mixins`, `typeClasses`, and `apiName` live there. Filter in two steps, **before** deciding content-vs-media routing:

1. Discard any candidate whose `properties.mixins` lacks `sfdc_cms:deliveryApiEnabled`.
2. Of the remainder, discard any candidate whose `properties.typeClasses` does not contain `sfdc_cms__structured`. **This is a "supported for search" gate, not a content/media split** — `sfdc_cms__structured` is present on both structured-content types (`sfdc_cms__blog`) and media types (`sfdc_cms__image`), so a surviving candidate could still turn out to be either. **`sfdc_cms__content` alone is not sufficient** here — it's a shared parent class for both structured content and media types (e.g. `sfdc_cms__email` has `sfdc_cms__content` in its `typeClasses` but not `sfdc_cms__structured`, and must be discarded, not routed to content search).

Only after this filtering do you inspect the survivors' `typeClasses` again to route: `sfdc_cms__media` present → Media Route (see `media-route.md`); otherwise → Content Route (this file). Rank the content-route survivors.

Result: Found `sfdc_cms__blog` content type (single match here after filtering; if multiple relevant types had matched, e.g. `sfdc_cms__blog` and `c__Article`, they would be passed together as `"sfdc_cms__blog,c__Article"`)

---

**Step 3: Build Search Query**

Extract:
- Keywords: `sustainable OR sustainability OR environmental OR responsibility OR green OR eco OR carbon`
- Taxonomies: `{"OR": ["Business", "Corporate", "Environment", "Responsibility"]}`
- Language: `en_US`

Construct payload (public-channels scope only here — no `channelId` was discovered, so `contentAccessScope` is set and `channelIds` is omitted entirely; the two fields are mutually exclusive):
```json
{
  "inputs": [{
    "searchKeyword": "sustainable OR sustainability OR environmental OR responsibility OR green OR eco OR carbon",
    "taxonomyExpression": "{\"OR\": [\"Business\", \"Corporate\", \"Environment\", \"Responsibility\"]}",
    "searchLanguage": "en_US",
    "contentAccessScope": "Public",
    "contentTypeFqn": "sfdc_cms__blog",
    "pageOffset": 0,
    "searchLimit": 5
  }]
}
```

---

**Step 4: Confirm Query**

Present to user:
```text
I'll search for content with these parameters:

  Content Type: Blog (sfdc_cms__blog)
  Keywords: sustainable OR sustainability OR environmental OR responsibility OR green OR eco OR carbon
  Taxonomies: Business, Corporate, Environment, Responsibility
  Language: en_US
  Channels: Public

Proceed with this search?
```

User: "Yes - search now"

---

**Step 5: Execute Search**

Call `search_content_cms_channels` with the payload

---

**Step 6: Present Results**

Results are grouped by content type, with channel shown as a per-item field. This example ran with only one content type FQN (`sfdc_cms__blog`) and public-channels-only scope, so there's only one group and the content-type heading is omitted — but the per-item `Channel:` field is still shown:

```text
I found 5 content items:

1. Our Journey to Carbon Neutrality
   Content Type: Blog (sfdc_cms__blog) — Channel: Public

2. Building a Sustainable Supply Chain
   Content Type: Blog (sfdc_cms__blog) — Channel: Public

3. Renewable Energy: Powering Our Future
   Content Type: Blog (sfdc_cms__blog) — Channel: Public

4. Green Office Initiatives That Work
   Content Type: Blog (sfdc_cms__blog) — Channel: Public

5. Sustainability Report 2024
   Content Type: Blog (sfdc_cms__blog) — Channel: Public

---
6. Load More (showing 5 of 8)
7. Done

Select one or more items (e.g., "1, 3" or "all"), Load More, or Done:
```

If a `landing-page` uiBundle channel had also been in scope and returned hits, the channel would still just be a per-item field — it would NOT create a new group, since content type is the only grouping key. But if a second content type (e.g. `c__Article`) had also matched, results would be grouped and numbered continuously by content type instead, e.g.:

```text
I found 3 content items:

Blog (sfdc_cms__blog):
1. Our Journey to Carbon Neutrality — Channel: Public
2. Internal Sustainability Metrics Q3 — Channel: landing-page

Article (c__Article):
3. Building a Sustainable Supply Chain — Channel: Public
```

User: "1, 2, 5"

---

**Step 7: Display Content Details**

```text
Selected content:

1. Our Journey to Carbon Neutrality
   Content Type: Blog (sfdc_cms__blog)
   Channel: Public
   Content ID: 20YXX000000010
   Content Key: MCBT7N9K5WX2QPFR4VHD8JLZ6MGY
   Language: en_US
   Unauthenticated URL: https://example.my.salesforce-sites.com/blog/carbon-neutrality-journey

2. Building a Sustainable Supply Chain
   Content Type: Blog (sfdc_cms__blog)
   Channel: Public
   Content ID: 20YXX000000011
   Content Key: MCQJ3P8TK6DWL9XN5VHR2FZ4GBY7
   Language: en_US
   Unauthenticated URL: https://example.my.salesforce-sites.com/blog/sustainable-supply-chain

5. Sustainability Report 2024
   Content Type: Blog (sfdc_cms__blog)
   Channel: Public
   Content ID: 20YXX000000014
   Content Key: MCHZ8P3T7FN5XDWK2QJVR6GMLBY9
   Language: en_US
```

Item 5's `managedContentChannelDeliveryDetails` array is empty (not yet delivered to any channel), so its URL line is omitted rather than shown blank. Items 1 and 2 have one entry each, so their URLs are shown in full. (This example's scope was public-channels-only with no `channelId` discovered — see SKILL.md Step 1 — so no item here has more than one delivery entry; for a worked multi-entry disambiguation, see "Disambiguating channel at selection" above.)

---

**Step 8: Offer to Render (only if a uiBundle channel was in scope)**

This example ran with public-channels-only scope (SKILL.md Step 1 found zero uiBundle `channelId`s), so this step is skipped entirely — the results from Step 7 are the final output. If SKILL.md Step 1 had found, say, a `landing-page` uiBundle with a `channelId`, the agent would instead use the same two-message pattern as Step 4's search confirmation — the item list as its own plain-text message, never folded into `ask_followup_question`'s question text:

**Message 1 (plain chat text):**

```text
I can render the following in the landing-page app:

  1. Our Journey to Carbon Neutrality (Blog)
  2. Building a Sustainable Supply Chain (Blog)
```

**Message 2 (immediately after):** `ask_followup_question` with the question `"Render this content in the landing-page app?"` and options `Yes` / `No`. Note the question stays generic — it does NOT restate "these two items" or the count; that's exactly the kind of detail Message 1's list already carries, and stuffing it into the question text is the failure mode this pattern avoids (same reasoning as Step 4's search-confirmation message, which strips line breaks/formatting from anything placed inside `ask_followup_question`).

On `Yes`, dispatch delegation via `mcp__skill_bridge__load_skill("experience-cms-content-render")` — never the built-in Skill tool, which doesn't know about MCP-bridge skills and returns `Unknown skill`. Pass each selected item's `title`, content type FQN (e.g. `sfdc_cms__blog`), and its chosen entry's channel ID (`managedContentChannelDetails.id`, e.g. `0apxx0000000002`) **when it has one** — items 1 and 2 above each have exactly one entry, so their channel ID is included; item 5 has zero entries (empty `managedContentChannelDeliveryDetails`), so its channel ID is omitted entirely rather than read off a nonexistent entry. Also pass either its Unauthenticated URL (item 1/2 above) or, when absent, its `managedContentKey` renamed to `contentKey` (item 5 above) — the receiving skill's `SKILL.md` names this field `contentKey`. If the load call fails, tell the user the hand-off failed and stop — do not attempt the render yourself.

---

## Complete End-to-End Example — Data 360 hybrid search

Same skill and request domain as the keyword example above, but the user picked **Search using Data 360 hybrid search** at Step 3 point 1, and asked in French. **Steps 1–2 (intent + content-type discovery) are identical to the keyword example** — `search_metadata` + `query_metadata` discover `sfdc_cms__blog` — with one scope difference carried in from `SKILL.md` Step 1: a `landing-page` uiBundle was discovered, so its `channelId` is in scope. The hybrid call itself ignores it; it only makes the render offer fire at Step 8. Only the hybrid-specific steps are shown below.

**User Request (French):**
> "trouve-moi des articles de blog sur les pratiques commerciales durables pour notre site"

---

**Step 3: Build Search Query (hybrid — no keyword/taxonomy extraction)**

Pass the query verbatim; read the language off the user's literal words; reuse Step 2's FQN (see "Search using Data 360 hybrid search" above):
- Query (verbatim): `trouve-moi des articles de blog sur les pratiques commerciales durables pour notre site`
- Content type: `sfdc_cms__blog`
- Language: `fr`

---

**Step 4: Confirm Query (hybrid variant)**

```text
I'll search Data 360 hybrid search with:

  Query: trouve-moi des articles de blog sur les pratiques commerciales durables pour notre site
  Content Type: Blog (sfdc_cms__blog)
  Language: fr   (auto-detected — tell me if this is wrong)
```

Then `ask_followup_question` with options `Yes - search now` / `Edit search` / `Cancel`. User: "Yes - search now". (Note: no `Keywords` / `Taxonomies` / `Channels` lines — hybrid ignores channel scope and does its own semantic matching.)

---

**Step 5: Execute Search — with language retry**

First call:
```text
search_digital_content(searchQuery="trouve-moi des articles de blog sur les pratiques commerciales durables pour notre site", contentTypeFqn="sfdc_cms__blog", searchLanguage="fr")
```
→ **zero results** (no French variants exist). Per "Search using Data 360 hybrid search" step 4, don't conclude "nothing exists" yet — tell the user in plain text and offer exactly one retry:

```text
No results found in French.
```
Then `ask_followup_question` with options `Yes - search without language filter` / `No - stop here`. User picks `Yes`. Retry with `searchLanguage` **omitted entirely** — `contentTypeFqn` stays:
```text
search_digital_content(searchQuery="trouve-moi des articles de blog sur les pratiques commerciales durables pour notre site", contentTypeFqn="sfdc_cms__blog")
```
→ returns three blog results, each in its own primary-language variant.

---

**Step 6: Map the response**

The hybrid shape differs from the keyword call — each result carries `contentUrls[]` (when it has a public delivery), a `searchScore`, and a per-item `language` (see "Parsing the `search_digital_content` response" above):
```json
{
  "outputValues": {
    "searchResults": [
      {
        "contentId": "20Yxx0000000010AAA",
        "contentKey": "MCBT7N9K5WX2QPFR4VHD8JLZ6MGY",
        "contentName": "Our Journey to Carbon Neutrality",
        "searchScore": 0.91,
        "contentUrls": [
          { "channelId": "0apxx0000000004", "channelName": "Public",         "url": "https://example.my.site.com/cms/delivery/v66.0/0apxx0000000004AAA/contents/20Yxx0000000010AAA?oid=00Dxx0000000000AAA&language=en_US" },
          { "channelId": "0apxx0000000005", "channelName": "Test Channel 3", "url": "https://example.my.site.com/cms/delivery/v66.0/0apxx0000000005AAA/contents/20Yxx0000000010AAA?oid=00Dxx0000000000AAA&language=en_US" }
        ],
        "contentTypeFqn": "sfdc_cms__blog",
        "language": "en_US"
      },
      {
        "contentId": "20Yxx0000000011AAA",
        "contentKey": "MCQJ3P8TK6DWL9XN5VHR2FZ4GBY7",
        "contentName": "Building a Sustainable Supply Chain",
        "searchScore": 0.86,
        "contentUrls": [
          { "channelId": "0apxx0000000004", "channelName": "Public", "url": "https://example.my.site.com/cms/delivery/v66.0/0apxx0000000004AAA/contents/20Yxx0000000011AAA?oid=00Dxx0000000000AAA&language=en_US" }
        ],
        "contentTypeFqn": "sfdc_cms__blog",
        "language": "en_US"
      },
      {
        "contentId": "20Yxx0000000012AAA",
        "contentKey": "MCX4R8TQ2NWL7ZK5VHD3JPF6GBY9",
        "contentName": "Green Packaging Draft",
        "searchScore": 0.72,
        "contentTypeFqn": "sfdc_cms__blog",
        "language": "en_US"
      }
    ]
  }
}
```

The third result has no `contentUrls` key at all — it isn't delivered to any public channel.

Map each result to the content-route fields the rest of this reference uses:

| hybrid field | → content-route field |
|---|---|
| `contentName` | `title` |
| `contentId` | `managedContentId` |
| `contentKey` | `managedContentKey` |
| `contentTypeFqn` | `contentType` |
| `language` | `language` |
| each `contentUrls[]` `{ channelId, channelName, url }` | one `managedContentChannelDeliveryDetails[]` entry `{ contentUrl: url, managedContentChannelDetails: { id: channelId, name: channelName, type: "PUBLIC_UNAUTHENTICATED" } }` |
| no `contentUrls` / `contentUrl` key | empty `managedContentChannelDeliveryDetails` |

Every entry is public (see "Channel type" above), so each `url` is that entry's Unauthenticated URL. The `landing-page` uiBundle channel doesn't appear in any result — hybrid never returns `WEB_APP` channels. No content-type filtering is needed: the call sent `contentTypeFqn`, so every result is already a blog.

---

**Step 6b & 7: Present results, then display**

The results came back in `en_US` even though the user asked in French (the retry fell back per-item), so flag the substitution when presenting. Group by content type (one blog group here), channel as a per-item hint, no URL at presentation:

```text
I found 3 content items (no French version exists — these are the English originals):

1. Our Journey to Carbon Neutrality
   Content Type: Blog (sfdc_cms__blog) — Channel: Public

2. Building a Sustainable Supply Chain
   Content Type: Blog (sfdc_cms__blog) — Channel: Public

3. Green Packaging Draft
   Content Type: Blog (sfdc_cms__blog)
```

User: "1, 2". Item 1's mapped array has two entries → ask which channel (`Public` / `Test Channel 3`); user picks `Public`. Item 2 has one → use it directly. Display details, with the chosen entry's `url` as the Unauthenticated URL:

```text
Selected content:

1. Our Journey to Carbon Neutrality
   Content Type: Blog (sfdc_cms__blog)
   Channel: Public
   Content ID: 20Yxx0000000010AAA
   Content Key: MCBT7N9K5WX2QPFR4VHD8JLZ6MGY
   Language: en_US
   Unauthenticated URL: https://example.my.site.com/cms/delivery/v66.0/0apxx0000000004AAA/contents/20Yxx0000000010AAA?oid=00Dxx0000000000AAA&language=en_US

2. Building a Sustainable Supply Chain
   Content Type: Blog (sfdc_cms__blog)
   Channel: Public
   Content ID: 20Yxx0000000011AAA
   Content Key: MCQJ3P8TK6DWL9XN5VHR2FZ4GBY7
   Language: en_US
   Unauthenticated URL: https://example.my.site.com/cms/delivery/v66.0/0apxx0000000004AAA/contents/20Yxx0000000011AAA?oid=00Dxx0000000000AAA&language=en_US
```

---

**Step 8: Offer to Render**

A `landing-page` uiBundle channel was in scope, so the render offer fires (same two-message pattern as the keyword example). On `Yes`, dispatch `mcp__skill_bridge__load_skill("experience-cms-content-render")`, passing each item's `title`, content type FQN (`sfdc_cms__blog`), the chosen entry's channel ID, and its Unauthenticated URL — exactly as in the keyword example. Had the user also picked item 3 (no `contentUrls` key, so no entry), you'd omit its channel ID and pass its `managedContentKey` as `contentKey` instead.
