# Toolkit package API + delivery response contract

Ground truth for reading CMS content. Transport, envelope-unwrap, catalog remap, channel resolution, image-URL resolution, and entity-decoding all live in the npm package **`@salesforce/ui-bundle-template-feature-cms-toolkit`**. 
Generated code CALLS this API — never re-implement HTTP, unwrap, or URL building, and never reconstruct an endpoint or response from memory.

## Public API surface (the single import target)

```ts
import {
  getCmsContentByUrl,   // (url, options?)        → Promise<TBody>   public CDN, unauthenticated; THROWS
  getCmsContentByKey,   // (contentKey, options?) → Promise<TBody>   one item, authenticated Connect; THROWS
  getCmsContentByKeys,  // (keys[], options?)     → Promise<CmsBulkResult<TBody>[]>  many, authenticated, ONE round-trip; BEST-EFFORT (per-key error, never throws except on abort). See references/bulk-loading.md
  resolveCmsImageUrl,   // (field, options?)      → string | undefined   image field → loadable src (SYNC); pass no options — resolves relative urls itself
  resolveMediaUrl,      // (url, options?)         → string | undefined   media url string → loadable src (SYNC); pass no options
  getCmsInstanceOrigin, // ()                      → string | undefined   instance origin (SYNC); no longer needed by generated code
  decodeRichHtmlEntities, // (encoded)            → string   decode RichText before injection (SYNC)
  resolveEffectiveContentKey, // (key, catalogUrl?) → Promise<string>   source→target key remap
  getCmsDefaultChannelId,     // (catalogUrl?)     → Promise<string|undefined>   catalog default channel (fail-open)
  // errors (stable for instanceof):
  CmsDeliveryError, CmsDeliveryNotFoundError, ConnectApiError, CmsNotFoundError,
} from '@salesforce/ui-bundle-template-feature-cms-toolkit';

import type {
  CmsContentBody, CmsReadOptions, CmsBulkResult, CmsContentCatalog, CmsImageField, CmsImageOptions,
} from '@salesforce/ui-bundle-template-feature-cms-toolkit';
```

Every read takes a required positional subject (url / key / keys) plus ONE optional `CmsReadOptions = { signal?: AbortSignal; channelId?: string }` (`channelId` is for authenticated reads only and overrides the catalog default). 
New params arrive as new OPTIONAL fields — no call site ever breaks.

Both `byUrl` and `byKey` return the already-UNWRAPPED `contentBody` typed as `TBody` — there is no envelope handling in skill code. 
`byKey` also remaps source→target and resolves the channel first.

## Delivery response contract (what `TBody` describes)

Both transports return the SAME managed content item DIRECTLY (NOT wrapped in
`{ items }`, `data`, or `result`). Real `news` payload, pre-unwrap:

```jsonc
{
  "contentBody": {                          // ← per-type renderable fields (this is <Type>Body)
    "body": "A powerful earthquake…",        // RichText/Text → primitive (Rule 5)
    "excerpt": "A devastating earthquake…",
    "bannerImage": { "source": { "type": "url", "ref": "https://cdn.…/x.svg" } }  // Image → object
  },
  "contentKey": "MCVIWPYY…",
  "title": "News Content on Venezuela Earthquake",   // ← ENVELOPE-level, NOT in contentBody
  "contentType": { "fullyQualifiedName": "sfdc_cms__news" }
}
```

- **`contentBody` IS the per-type body**, and its keys VARY BY TYPE — derive
  `<Type>Body` from the schema / a real payload (`references/schema-sync.md`), never
  hard-code. `getCmsContentByUrl<TBody>` / `getCmsContentByKey<TBody>` return it.
- **`title` is ENVELOPE-level** (root, not in `contentBody`). The toolkit LIFTS it
  into the body when the body lacks one, so `body.title` works — keep room in
  `<Type>Body`'s index signature; do NOT emit `title` as a schema field.
- A root `channelSummary` block may appear — ignore it.

## Image field — `CmsImageField` + `resolveCmsImageUrl`

Images are OBJECTS, not primitives — never use one as a `src` directly; pass it to `resolveCmsImageUrl(field)`. 
Pass NO options object — the resolver resolves a relative Connect-API url on its own. It is SYNCHRONOUS — resolve inline, there is no async image component. Three cases the resolver handles:

- **CMS image** (`source.type === "imageReference"`) — has a ROOT-RELATIVE top-level
  `url`; the resolver returns it resolved to a loadable src (a relative Connect-API
  url now works as-is — no instance-origin prefix needed).
- **Foreign image** (`source.type === "url"`) — no top-level `url`; the absolute URL
  is the STRING `source.ref`, returned as-is.
- **Fallback** — `imageReference` with no top-level `url`. Rare; the common payload
  inlines the media `url`.

Standalone media (audio/video/document) on a **`contentKey` ref** uses the sibling
`resolveMediaUrl(url)`, given the body `sfdc_cms:media.url` string directly (same
no-options, relative-safe contract). A **foreign `url` media ref** skips this entirely —
its `unauthenticatedUrl` is the asset itself and is set directly as the element
`src`/`href`, with no fetch and no resolver (Rule 1/Rule 2). The resolvers apply only
when a body was fetched.

The field also carries an optional `altText` string — bind it to the `<img alt>`
(`resolveImageAlt`), falling back to `''` (decorative, WCAG 1.1.1) when absent.
`resolveCmsImageUrl` returns only the `src`, so read `altText` off the field object.

## RichText & scalars

RichText arrives entity-encoded (`"&lt;div&gt;…"`) — decode with
`decodeRichHtmlEntities` before injecting, through ONE path per framework (Rule 4,
`references/heuristic-render-rules.md`). Scalar `contentBody` fields are primitives,
never `{ value }` (Rule 5, `references/schema-sync.md`). Symptoms if either is
violated: `references/failure-modes.md`.

## `content-metadata.json` — the catalog the skill writes (Rule 1)

The `byKey` path loads a public `content-metadata.json` to supply a default `channelId` and remap each baked-in `sourceContentKey` → the org's `targetContentKey`. 
Loaded once, memoized, and **FAIL-OPEN**: missing / unreachable / malformed → treated as `{}` (no channel, keys used verbatim). Served from the uiBundle base at `${BASE_URL}content-metadata.json` (override with `VITE_CONTENT_CATALOG_URL`); with Vite the web root is `public/`, so the file lives at `<appRoot>/public/content-metadata.json`.

**The skill writes it — catalog-primary channel resolution.** When a `CmsRef` needs a channel and the catalog is absent, the skill creates `public/content-metadata.json` with the resolved `channelId` and an **empty `contents: []`**:

```jsonc
{ "channelId": "0apSG0000000ExampleChannel", "contents": [] }
```

Only `channelId` (string) and `contents` (`{ sourceContentKey, targetContentKey }` pairs; entries missing either key are skipped) are read — the empty `contents` is safe because per-entry remap fails open to the baked-in `contentKey`. Write it **on demand at the first `CmsRef` embed** that needs a channel, not at Init; idempotent (present channel → never overwrite; absent → create; present-but-empty → fill).

Write **only a known channel** (catalog / prompt / user) — a placeholder with a fake `channelId` breaks every `byKey` read, because fail-open triggers on a MISSING file, not a present-but-wrong one; a present-but-wrong catalog is worse than none. It is a **regenerable data seam, not source of truth**: the deploy pipeline always regenerates it against the target org (filling real `contents`), which is why the catalog is cross-org-safe where a baked-in `CMS_CHANNEL_ID_FALLBACK` source constant is not. Precedence when reading: explicit option > `CMS_CHANNEL_ID_FALLBACK` (see `externalRefs.ts`, a cautioned opt-in override) > catalog `channelId` > the toolkit throws.
Failure modes: `references/failure-modes.md`.