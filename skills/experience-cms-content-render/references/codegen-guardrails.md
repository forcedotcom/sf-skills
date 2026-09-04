# Codegen guardrails — Rules 1–5 (full)

Five rules encoding defects a prior scaffold reproduced. Every generated app MUST
satisfy all five; a violation is a blocking bug, not a style nit. They are baked into
the templates under `assets/shared/`, `assets/react/`, `assets/angular/`; keep them
true when editing. SKILL.md carries the one-line form of each rule — this file is the
full text.

## Rule 1 — Call the right toolkit read; never re-implement transport

Dispatch on ref type: a `CmsExternalRef` (public `unauthenticatedUrl`) →
`getCmsContentByUrl(url)`, fetched AS-IS; a `CmsRef` (`contentKey`) →
`getCmsContentByKey`/`getCmsContentByKeys`, authenticated Connect. Do NOT reconstruct
a delivery URL, prepend the instance URL / `/services/data/vXX`, hand-remap a
`contentKey`, or route a CDN URL through Connect or vice versa; the package owns all
of that.

**Exception — standalone media on a foreign `url` ref is NOT fetched.** A media
`unauthenticatedUrl` (`sfdc_cms__{image,audio,video,document}`) is the ASSET itself,
not a delivery-JSON endpoint, so `MediaRenderer` sets `ref.url` directly onto the
element `src`/`href` and calls neither `getCmsContentByUrl` nor a resolver (Rule 2).
There is no fetched body, so alt text / document label ride on the ref (`altText` /
`title`, threaded from the search hand-off or asked at Ref Registration). This is
media-only: a `CmsExternalRef` for news/structured content is still fetched via
`getCmsContentByUrl`, and a `contentKey` media ref still fetches via
`getCmsContentByKey`.

When a `CmsRef` needs a channel, **write `public/content-metadata.json`** with
the resolved `channelId` and empty `contents: []` (create if absent; never overwrite a
present channel). Write only a KNOWN channel (catalog / prompt / user) — **never a
placeholder or fake `channelId`**: the toolkit fails open on a *missing* catalog, but a
present-but-wrong one breaks every `byKey` read. The deploy pipeline regenerates the
catalog per target org and fills the real `contents`. Endpoint + response contract +
catalog shape: `references/package-api.md`.

## Rule 2 — Resolve media `src` by ref shape, then by medium

`MediaRenderer` forks first on **ref shape**, then (on the fetched path) by medium.

**Foreign `url` ref — direct, no fetch, no resolver.** A media `unauthenticatedUrl`
is the asset itself, so `ref.url` goes straight onto the element `src`/`href`. No
`getCmsContentByUrl`, no `resolveCmsImageUrl`/`resolveMediaUrl`, no body. Alt text /
document label come off the ref (`altText`/`title`). Emitting an `<img>` `src` from
the resolver here is wrong — the url needs no resolution.

**`contentKey` ref — fetch the body, then resolve by medium.** The `src` comes from
the fetched body's `sfdc_cms:media` field, and the resolution SPLITS by medium — each
side calls a toolkit SYNC resolver with ONLY its subject, no options object:

- **image** → `resolveCmsImageUrl(body['sfdc_cms:media'])` — the SAME resolver the
  heuristic renderer uses for image fields; media reuses it, not a parallel copy.
- **audio / video / document** → `resolveMediaUrl(body['sfdc_cms:media'].url)` — the
  toolkit's media resolver, given the body `url` string directly.

The toolkit resolves the relative Connect-API url on its own — a relative media url
works as-is and must NOT be hand-prefixed (no instance origin, no org origin, no
`{ instanceOrigin }` option). Pass no second argument to either resolver. There is no
local URL-prefixing helper; skill code never builds a media URL by hand. Media
dispatch is by `ref.cmsType` and ref shape, never by body shape, so audio/video/document
never enter the heuristic renderer's `isImageObject` path (SKILL.md §B1).

## Rule 3 — Shared/deduped fetch state must survive React 19 StrictMode

The React hook `useCmsItem` dedupes through a module-level `inflight` map and must
survive mount→cleanup→remount: cleanup sets a local `cancelled` flag gating
`setState` and MUST NOT abort the shared request; shared requests get no abort signal;
`inflight` self-cleans via `.finally(delete)` at creation. The Angular
`CmsItemService` uses the same shared `cache`/`inflight` maps and a stale-ref guard in
`ngOnChanges`. Treat "works once, fails on remount" as a blocking bug.

## Rule 4 — Decode RichText before injecting, through ONE path per framework

Delivery returns RichText entity-encoded (`"&lt;div&gt;…"`), so injecting it raw
renders literal tags. Decode with the toolkit's `decodeRichHtmlEntities` FIRST, then
inject at the single site:

- **React** — `richTextSanitizer(decodeRichHtmlEntities(value))` → raw-HTML injection
  in the `RenderField` dispatcher inside `heuristicRenderer.tsx`. Delivery RichText is
  TRUSTED, so the default `richTextSanitizer` is **pass-through**; apps add DOMPurify
  via `setRichTextSanitizer` at entry. The default MUST NOT be escape-only: the value
  is already decoded, so escaping undoes the decode (**never both decode AND escape**).
  Per-type renderers MUST forward into `heuristicRenderer`, never inline their own
  injection.
- **Angular** — `decodeRichHtmlEntities(value)` → `[innerHTML]` in
  `cms-content.component.ts`. Angular's `DomSanitizer` sanitizes the binding
  automatically; do NOT `bypassSecurityTrustHtml`.

Detection must catch the encoded form: match a tag-open (`<tag`/`</`/`<!`) OR `&lt;`
(`RICH_TEXT_RE`), not `value.includes('<')`. A bare `<` in prose (`"Q4 < projected"`)
must NOT match, or the browser's HTML parser silently drops everything after it.

## Rule 5 — Type scalar fields as primitives, never `{ value }` wrappers

Delivery returns SCALAR fields (Text, RichText, Date, Number, URL) as PLAIN
primitives (`"body": "&lt;div&gt;…"`, `"title": "Berries"`), NOT `{ value: "…" }`.
Only images arrive as objects (`CmsImageField`). A prior scaffold assumed a uniform
`{ value: string }` and read `body.body.value`, always `undefined`, so RichText
rendered as nothing.

- **Generated `<Type>Body` uses primitives.** Text/RichText/URL → `string`;
  Date/DateTime → `string`; Number → `number`; Boolean → `boolean`; Image →
  `CmsImageField`. Never `{ value: T }`. Template: `assets/shared/cmsContentType.ts`.
- **Read fields directly.** `body.body`, never `body.body.value`. The renderer
  dispatches on the primitive's shape; per-type renderers delegate and MUST NOT unwrap
  `.value`.
- **Derive shapes from a real payload.** Confirm each field against an actual delivery
  response: an inline sample in the prompt, a fetched `unauthenticatedUrl`, or the
  schema. For a `contentKey` ref with no URL to fetch, an inline sample is the primary
  source. Read field shapes from `contentBody`; the item `title` is at the envelope
  ROOT, not a `contentBody` field. `references/schema-sync.md`; envelope contract in
  `references/package-api.md`.
