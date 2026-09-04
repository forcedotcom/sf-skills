# Content Route — Full Reference

## Confirming the query before searching

Required two-message pattern, same turn:

**Message 1 (chat-visible plain text — NOT inside `ask_followup_question`):** print the parameters as a labeled list, one field per line:

```text
I'll search for content with these parameters:

  Content Type: <label> (<fqn>[, <label2> (<fqn2>), ...])
  Keywords: <keyword1 OR keyword2 OR ...>
  Taxonomies: <term1, term2, ...>
  Language: <en_US>
  Channels: Public[, plus <uiBundle> channel]
```

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
  "managedContentId": "20YVW000001miuD",
  "managedContentKey": "MCICPC4X5KE5ATHMTN4EYK5DOCYM",
  "managedContentChannelDeliveryDetails": [
    {
      "contentUrl": "https://.../channels/0apVW000000Z25NYAS/contents/20YVW000001miuD?language=en_US",
      "managedContentChannelDetails": { "id": "0apVW000000Z25N", "name": "testinternalapp", "type": "WEB_APP" }
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
    { "contentUrl": "https://.../0apVW000000TsHxYAK/...", "managedContentChannelDetails": { "id": "0apVW000000TsHx", "name": "Test CMS Channel", "type": "PUBLIC_UNAUTHENTICATED" } },
    { "contentUrl": "https://.../0apVW000000VUt3YAG/...", "managedContentChannelDetails": { "id": "0apVW000000VUt3", "name": "testLWR", "type": "COMMUNITY" } },
    { "contentUrl": "https://.../0apVW000000ZYoPYAW/...", "managedContentChannelDetails": { "id": "0apVW000000ZYoP", "name": "Test Channel 2", "type": "PUBLIC_UNAUTHENTICATED" } },
    { "contentUrl": "https://.../0apVW000000ZYq1YAG/...", "managedContentChannelDetails": { "id": "0apVW000000ZYq1", "name": "Test Channel 3", "type": "PUBLIC_UNAUTHENTICATED" } },
    { "contentUrl": "https://.../0apVW000000ZYrdYAG/...", "managedContentChannelDetails": { "id": "0apVW000000ZYrd", "name": "Test Channel 4", "type": "PUBLIC_UNAUTHENTICATED" } },
    { "contentUrl": "https://.../0apVW000000ZYtFYAW/...", "managedContentChannelDetails": { "id": "0apVW000000ZYtF", "name": "Test Channel 5", "type": "PUBLIC_UNAUTHENTICATED" } }
  ]
}
```

The multi-channel case is not "one entry from the public call, one from the channel-scoped call" — it's whatever the array actually contains, however many entries that is.

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

Keyword/taxonomy extraction rule: see `SKILL.md` Step 3 point 1 (the Media Route uses the same split — see `media-route.md` for media-specific examples). Additional worked examples for content:
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

This returns candidate matches only — no `jsonAttributes`, so routing and delivery-API filtering aren't possible yet. Each candidate already includes a full composite identifier, e.g. `00DVW00000CfBQP2A3::0T1VW000008sow60AA::ContentTypeBundle` (name `sfdc_cms__blog`) among others — use it as returned.

Call `query_metadata` with each candidate's identifier from above, as-is, batched into one `metadataIdentifiers` array:
```json
{
  "metadataIdentifiers": [
    "00DVW00000CfBQP2A3::0T1VW000008sow60AA::ContentTypeBundle"
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

On `Yes`, dispatch delegation via `mcp__skill_bridge__load_skill("experience-cms-content-render")` — never the built-in Skill tool, which doesn't know about MCP-bridge skills and returns `Unknown skill`. Pass each selected item's `title`, content type FQN (e.g. `sfdc_cms__blog`), and its chosen entry's channel ID (`managedContentChannelDetails.id`, e.g. `0apVW000000TsHx`) **when it has one** — items 1 and 2 above each have exactly one entry, so their channel ID is included; item 5 has zero entries (empty `managedContentChannelDeliveryDetails`), so its channel ID is omitted entirely rather than read off a nonexistent entry. Also pass either its Unauthenticated URL (item 1/2 above) or, when absent, its `managedContentKey` renamed to `contentKey` (item 5 above) — the receiving skill's `SKILL.md` names this field `contentKey`. If the load call fails, tell the user the hand-off failed and stop — do not attempt the render yourself.
