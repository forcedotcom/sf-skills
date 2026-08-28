# Discovery Query Rules — `metadata-grounding.search_metadata` for ContentTypeBundle

**Single source of truth for how the ContentTypeBundle discovery query is constructed.** Owned by `experience-cms-content-type-generate` (referenced from its Step 1c). Also referenced from `experience-cms-content-generate`'s Step 2 — the parent skill should not construct a discovery query itself (delegation drift bug), but if drift happens, the query must still be built by these rules.

## The call

```javascript
search_metadata({ metadataType: "ContentTypeBundle", query: "<3-5 domain nouns>", limit: 5 })
```

`search_metadata` alone returns everything discovery (Step 1c/1d) needs — FQN, description, OOTB flag — for all top matches. Do NOT dispatch `query_metadata` per match here: per-row fan-out is N wasted round-trips. `query_metadata` is load-bearing only in Step 1e, on-demand, for the single picked OOTB FQN. See `SKILL.md` § 1c/1e.

Server target: `metadata-grounding` — no other server, no SOQL, no `sf project retrieve`, no `sf org list metadata`.

## The `query` value in one line

**3-5 English content-domain nouns.** That's it. Not an FQN, not a namespace, not a copy of the user's message.

- The `metadataType: "ContentTypeBundle"` argument already tells grounding the kind — the query only carries the domain.
- Words about the CMS machinery (`content type`, `bundle`, `metadata`, `cms`) belong in `metadataType`, not `query`.
- Namespaces (`sfdc_cms`, `sfdc_cms__`, `c__`, `<anything>__`) belong in an FQN, not `query`.
- Years (`2023`, `Q4`), one-off proper names (product SKUs, campaign codenames like `Project Nova`, `Dreamforce 2025 Keynote`), and meta-instructions (`please`, `help me`) don't describe a type shape — drop them.

## The transform — 5 minute mental model

**User's message → 3-5 content-domain nouns.** Keep the shape noun (news, article, product, case study, whitepaper, event, webinar, announcement, story, page, blog, press release, FAQ, bio, profile, earnings report), then add 2-4 neighbors along the same real-world axis. Never send a one-word query.

If the user pasted an FQN, take ONLY the DeveloperName portion, word-split it, and expand:
- `sfdc_cms__news` → shape = `news` → query = `news article announcement story headline`
- `c__PressRelease` → shape = `press release` → query = `press release announcement news statement corporate`

## Concrete tool calls — this is what dispatch should look like

Copy the shape, adapt to the domain. Read left-to-right: user message, then the exact `search_metadata` call.

| User message | `search_metadata` call |
|---|---|
| `create a content type for health insurance` | `search_metadata({ metadataType: "ContentTypeBundle", query: "health insurance policy claim benefit", limit: 5 })` |
| `set up a bundle for press releases` | `search_metadata({ metadataType: "ContentTypeBundle", query: "press release announcement news statement corporate", limit: 5 })` |
| `webinar content type with abstract and speakers` | `search_metadata({ metadataType: "ContentTypeBundle", query: "webinar event session speaker agenda", limit: 5 })` |
| `create content on Q4 2025 product launch` | `search_metadata({ metadataType: "ContentTypeBundle", query: "news article announcement launch product", limit: 5 })` |
| `create a news content type` | `search_metadata({ metadataType: "ContentTypeBundle", query: "news article announcement story headline", limit: 5 })` |
| `use sfdc_cms__news for this` | `search_metadata({ metadataType: "ContentTypeBundle", query: "news article announcement story headline", limit: 5 })` |
| `create content for our upcoming enterprise CRM announcement` | `search_metadata({ metadataType: "ContentTypeBundle", query: "announcement news product launch release", limit: 5 })` |
| `create content type for Q4 2025 earnings report` | `search_metadata({ metadataType: "ContentTypeBundle", query: "earnings report financial results quarterly revenue", limit: 5 })` |
| `pet grooming products in our store` | `search_metadata({ metadataType: "ContentTypeBundle", query: "product pet grooming catalog listing", limit: 5 })` |
| `add something for our upcoming launch` | `search_metadata({ metadataType: "ContentTypeBundle", query: "announcement launch news release event", limit: 5 })` |
| `blog posts about AI safety` | `search_metadata({ metadataType: "ContentTypeBundle", query: "blog post article author publication", limit: 5 })` |
| `FAQ page for our support site` | `search_metadata({ metadataType: "ContentTypeBundle", query: "faq question answer support help", limit: 5 })` |

Notice: no query contains `sfdc_cms`, `c__`, `__`, `content type`, `bundle`, `metadata`, `cms`, a year, or a one-off proper name. Every query is 3-5 English content-domain nouns.

## Wrong queries — do not dispatch these

If your composed query looks like ANY of the following, rebuild it before the tool call.

| ❌ Wrong query | Why it's wrong |
|---|---|
| `sfdc_cms__news content type` | Namespace + filler. Both belong elsewhere. Correct: `news article announcement story headline`. |
| `sfdc_cms news content type` | Namespace fragment + filler. Correct: `news article announcement story headline`. |
| `c__PressRelease bundle` | Namespace + filler. Correct: `press release announcement news statement corporate`. |
| `news content type` | Filler `content type` — kind is already implied by `metadataType`. Correct: `news article announcement story headline`. |
| `CMS content type bundle` | All filler, no domain. Correct: fill in domain nouns from the user's message. |
| `dreamforce 2025 keynote` | One-off proper name + year + no shape noun. Correct: `event keynote announcement session agenda`. |
| `launch` | Single word, under-recalls. Correct: `announcement launch news release event`. |

## Pre-dispatch check

Before calling `search_metadata`, read your composed `query` string. If it contains any of these tokens, rebuild:

- `content type`, `contenttype`, `bundle`, `metadata`, `cms`, `record`, `object` — filler; drop.
- `sfdc_cms`, `sfdc`, `c__`, or any `__` substring, or any `<prefix>__` token — namespace; drop.
- Years (`2023`, `Q4`, `November`), one-off proper names (SKUs, event codenames), meta-instructions (`please`, `can you`) — noise; drop.

Then dispatch. Do not re-dispatch a "corrected" query in the same turn — grounding rate-limits repeat queries; take what it returned and continue to step 1d.

## Grounding is a heuristic, not the org

A grounding hit is high-signal (the org very likely has that type). A grounding miss is low-signal (grounding may lag org state). NEVER conclude "the org does not have `<Name>`" from grounding's response, and NEVER print that conclusion at Step 1d. Only Step 1e's `sf project retrieve start` can confirm org presence or absence.

## Related

- Full Step 1c rationale and skip-rationalization anti-patterns → `discovery-details.md#1c`
- Step 1d table + pick-list prompt templates → `../assets/discovery-prompts.md`
- Step 1e retrieve-and-reconcile → `retrieve-and-reconcile.md`
