# Failure Modes

## Rich-text sanitizer plug (React only)

The RichText mechanics (decode-then-inject, why the default is pass-through) live in
Rule 4 / `references/heuristic-render-rules.md`. The one actionable extra: apps add
DOMPurify for defense-in-depth by registering a sanitizer once at entry — a runtime
plug, not a hard dep, so the choice is visible at the app boundary:

```ts
import DOMPurify from 'dompurify';
import { setRichTextSanitizer } from './cms/react/heuristicRenderer';
setRichTextSanitizer(DOMPurify.sanitize);
```

Angular has no such seam — `[innerHTML]` runs through `DomSanitizer` automatically.

## Terminal stops (session ends — nothing scaffolded)

Distinct from the recoverable HALTs below: these END the session. See
`references/interaction-model.md` → *Terminal stops*.

| Trigger | What the skill does |
|---------|---------------------|
| **Init declined** — user answers "No" to the *Run Init?* option question | State Init was declined → skill HALTS and the session ends. Nothing installed or written; end the turn. Do not fall through to Embed. |
| **Zero search content** — experience-search-coordinate succeeds but returns zero content for the phrase | The item isn't authored in this uiBundle space yet. Stop and tell the user to generate the content there first (author + publish, e.g. via experience-cms-content-generate / experience-cms-content-type-generate), then re-run. Do not guess an identity or scaffold. |

## HALT catalogue

| Trigger | Fix |
|---------|-----|
| Missing/malformed marker in managed file | User restores the marker line. Skill never auto-heals. |
| Ref name collision, different URL/key | User renames or removes the existing entry. |
| Init drift (scaffold differs from template) | User accepts (regenerate) or keeps their edit. |
| Foundation drift — some foundation files present, some missing | User restores the missing files or removes the partial set; the skill never Embeds onto a partial runtime. |
| Ambiguous framework — both `react` and `@angular/core` are deps | User names which framework to target. |
| Unknown framework — neither `react` nor `@angular/core` (or no `package.json`) | Not a supported React/Angular app; skill does not scaffold. |
| Router marker ambiguous / missing | User removes stale markers, or pastes the marker block. |
| Slug collision | User picks a different slug or removes the existing route. |
| Render target unanswered (step 4) — "in place" chosen but no placement named, or no anchor found | User names a component/page/region to render into. Skill never guesses a placement. |
| Detail-page prerequisite missing (renderer/ref) | User runs Embed for the type first. |
| Detail-page file exists with different content | User deletes or renames. |
| Content has neither `unauthenticatedUrl` nor `contentKey` | User pastes a public delivery URL or picks another item. (A `contentKey`-only item is supported — register a `CmsRef`.) |
| Multi-item selection when Embed needs one | User re-runs and picks a single item. |
| `CmsRef` with no resolvable channel — none in `public/content-metadata.json`, none in the prompt, and (bypass) no user to ask | User provides the channelId or adds it to `public/content-metadata.json`. The skill never invents or placeholders a channel; a `CmsRef` cannot render without one. |
| channelId conflict — a prompt-provided channel differs from a non-empty `channelId` already in `public/content-metadata.json` | ASK which wins as an option-select (`references/interaction-model.md` → *Channel conflict*): keep the catalog channel (no write) or use the prompt channel (overwrite only `channelId`, preserve `contents`). The skill overwrites the catalog only on confirmation, never silently. |

## Runtime failures (renderer-level)

Surfaced via `useCmsItem`'s `error` state (React) / `CmsItemService.load`'s
returned `error` (Angular), and the renderer's `role="alert"` branch. The toolkit
raises typed errors — `CmsDeliveryError` / `CmsDeliveryNotFoundError` (public CDN)
and `ConnectApiError` / `CmsNotFoundError` (authenticated Connect) — which the
hook/service pass through unchanged.

| Symptom | Cause | User action |
|---------|-------|-------------|
| HTTP 404 on a foreign ref | Unpublished, truncated URL, OR URL rewritten (doubled version, wrong host — Rule 1) | Verify the `unauthenticatedUrl`; the toolkit's `getCmsContentByUrl` fetches it AS-IS. |
| HTTP 401 on a foreign ref | Foreign-ref URL not actually public | For public delivery it must be truly public; a non-public uiBundle item should be a `CmsRef` (`contentKey`) read via `getCmsContentByKey`, not a `CmsExternalRef`. |
| `CmsNotFoundError` on a `CmsRef` | `contentKey` not published in this org, or the catalog remapped to a stale `targetContentKey` | Verify the item is published; check `content-metadata.json` maps the source key to a live target (or omit the entry to fall back to the baked-in key). |
| `CmsNotFoundError` / Connect error on EVERY `CmsRef` | Channel could not be resolved — no `channelId` in `public/content-metadata.json`, empty `CMS_CHANNEL_ID_FALLBACK`, AND no explicit option | Add `channelId` to `public/content-metadata.json` (the primary, cross-org-safe seam); the cautioned `CMS_CHANNEL_ID_FALLBACK` in `externalRefs.ts` is an opt-in override only. Precedence: explicit option > fallback > catalog > the toolkit throws. |
| "No content found." / empty render, either transport | Body typed wrong — the toolkit returns the already-UNWRAPPED `contentBody` (envelope `title` lifted in), NOT `{ items: [...] }` or the raw envelope | Type the read as `getCmsContentBy*<TBody>` where `TBody` is the `contentBody` shape. Never re-implement unwrap or read `items[0]`. Contract: `references/package-api.md`. |
| Content renders but the TITLE is missing | `<Type>Body` read `contentBody.title`, but delivery returns `title` at the ENVELOPE ROOT | The toolkit lifts the root `title` into the returned body (when the body lacks one) so `pickTitle`/layouts see it. Do not emit `title` as a `<Type>Body` schema field. Contract: `references/package-api.md`. |
| Image silently missing, url IS present in the payload | The field was used directly as `src` instead of going through the resolver | Never use an image field as a `src`. Pass it to `resolveCmsImageUrl(field)` (React `resolveImageSrc`; Angular's `resolveImageSrc` method) — it handles both the top-level-`url` (CMS `imageReference`) and `source.ref`-string (foreign `url`) variants, with no options. Shape: `CmsImageField`; contract: `references/package-api.md`. |
| CMS image doesn't load | An image field was used directly as `src` instead of going through the resolver | Resolve via `resolveCmsImageUrl(field)` — it resolves a relative Connect-API url on its own and passes absolute urls through. Pass NO options; it is SYNC, so resolve inline (no async image component). |
| Standalone media (audio/video/document) 404s **on a `contentKey` ref** | The body `sfdc_cms:media.url` was used directly as the element `src` instead of going through the resolver | Resolve via `resolveMediaUrl(sfdc_cms:media.url)` (Rule 2) — the toolkit resolves a relative Connect-API url itself. Pass NO options and never hand-prefix the url. Images use `resolveCmsImageUrl` instead. (This is the CONTENTKEY path only — a foreign `url` media ref uses `ref.url` directly with no fetch and no resolver; see the next row.) |
| Standalone media on a foreign `url` ref renders blank / doesn't load | The renderer fetched the `unauthenticatedUrl` (or ran it through a resolver) instead of using it directly | A media `unauthenticatedUrl` is the ASSET itself — set `ref.url` straight onto the element `src`/`href`, NO `getCmsContentByUrl` and NO resolver (Rule 1/Rule 2). If the url genuinely 404s, verify it is the direct asset url (all query params intact) and the item is published. |
| Media image on a foreign `url` ref has no alt text / a document link reads "Download" | `altText`/`title` weren't threaded onto the `CmsExternalRef` (direct-URL path has no body to read them from) | Capture `altText`/`title` at Ref Registration from the search hand-off, or ASK the user (`references/interaction-model.md` → *Media alt text*). `audio`/`video` need no alt. |
| Public-CDN fetch fails in dev (either framework) | Something OTHER than CORS — the CMS delivery backend serves CORS headers, so a direct cross-origin fetch from `localhost` works with no proxy | No dev proxy is needed or scaffolded (the former proxy rule was removed). Check the `unauthenticatedUrl` is correct and reachable, and that the item is published; a genuine failure here is a 404/401 or a network error, not a CORS block. |
| RichText renders as literal `<tags>` | Entity-encoded HTML injected without decoding; OR (React) the default `richTextSanitizer` was made escape-only and re-escaped already-decoded HTML | Decode via the toolkit's `decodeRichHtmlEntities` before injecting; React keeps the default sanitizer pass-through; never both decode AND escape the same string (Rule 4). |
| Malformed body | Schema drift | Re-run Embed (Schema Sync detects drift). |
| Empty render | Field names don't match priority lists | Pass a `fields={[…]}` (React) / `[fields]="[…]"` (Angular) whitelist. |
| One card in a bulk list is missing / errors | A `getCmsContentByKeys` best-effort read returns a per-key `error` (e.g. `CmsNotFoundError`) for an unpublished/wrong-channel key | Expected — `getCmsContentByKeys` isolates per-key failures rather than throwing; render the `error` rows distinctly. `references/bulk-loading.md`. |
| A `unauthenticatedUrl` card won't batch | Foreign CDN ref has no `contentKey` and often a different channel — structurally can't join a bulk read | Expected: foreign refs degrade to their individual `getCmsContentByUrl` fetch; only `CmsRef` keys batch (`references/bulk-loading.md`). |

## React 19 StrictMode

StrictMode intentionally mounts → cleans up → remounts. A hook that dedupes
through a shared `inflight` map (`useCmsItem`) must survive this. The classic
regression: cleanup aborts the SHARED in-flight request, the remount reuses the
now-dead promise, and every double-mount fails. Fix (baked into
`assets/react/useCmsItem.ts`, Rule 3): cleanup sets a `cancelled` flag and gates
`setState` (never aborts the shared request); shared requests get no abort
signal; `inflight` is self-cleaning via `.finally()` at creation. Treat "works
once, fails on remount" as a blocking bug. The Angular `CmsItemService`
(`assets/angular/cms-item.service.ts`) uses the same shared `cache`/`inflight`
maps and a stale-ref guard in `ngOnChanges`.

## Not failure modes

- StrictMode double-mount → single network request (dedup + suppress-not-abort). By design.
- Undefined per-embed `layout="…"` → falls through to `detail`/`list`; not a HALT.
- Stale ref after source content removed → runtime 404; skill does not prune refs.
- `content-metadata.json` missing / 404 / invalid JSON / entry absent → the toolkit
  fails open to the baked-in `contentKey` (and no catalog channel). A missing
  catalog is the normal local-dev state, not an error.
