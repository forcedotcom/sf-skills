# Heuristic Render Rules

Field-selection + value-shape rules for rendering an already-fetched, already-
unwrapped `contentBody` when there's no typed renderer. The SAME rules run in both
frameworks, in parallel implementations:

- **React** — `heuristicRenderer.tsx`: field selection (which fields, in what
  order) plus the internal `RenderField` dispatcher (how one value renders), in one
  file.
- **Angular** — one standalone `CmsContentComponent` (`cms-content`); `buildCells`
  picks fields, `classify` maps each value to a `Cell` the `@switch` template
  renders.

Neither fetches — a container (`useCmsItem` / `CmsItemService`) passes `body`,
`loading`, `error` in. Image-URL resolution is the toolkit's job
(`resolveCmsImageUrl`, SYNCHRONOUS), so images render as a plain `<img>` with no
async component in either framework.

## Field selection

**Whitelist mode** — caller passes `fields` (React `fields={[…]}`, Angular
`[fields]="[…]"`): iterate in order, render one field each, nothing else.

**Heuristic mode** — no whitelist, pick by priority list:

```text
IMAGE_PRIORITY   = ['bannerImage','featuredImage','heroImage','coverImage','thumbnail','image']
EXCERPT_PRIORITY = ['excerpt','summary','description','subtitle']
```

1. Title — field named `title`, else first string key matching `/title/i`.
2. Image — first `IMAGE_PRIORITY` field with an image shape.
3. Excerpt — first `EXCERPT_PRIORITY` string.
4. Overflow — `layout='detail'` renders remaining fields in order; `list` drops them.

Layout: `list` → `<h2>` title, no overflow; `detail` → `<h1>` title, overflow
shown. In React, slot overrides `components={{ Title, Image, RichText }}` win over
defaults (per-embed prop > type slot > default); Angular has no slot props (style
via class hooks + the container).

## Value-shape decision table

React `RenderField(name, value, layout, resolveRef, …slots)` / Angular
`classify(name, value)` → `Cell`:

| Value shape | Rendering |
|-------------|-----------|
| `null`/`undefined` | skip |
| string matching `RICH_TEXT_RE` (`<tag`/`</`/`<!` OR `&lt;` OR `&#60;`/`&#x3c;`) | rich text — see below |
| `^\d{4}-\d{2}-\d{2}` AND parseable | `<time>` via `Intl.DateTimeFormat({dateStyle:'medium'})`; unparseable → fall through |
| `^https?://` | `<a target=_blank rel="noopener noreferrer">` |
| string, name `/title/i` | heading (h1 detail / h2 list); React TitleSlot wins |
| string (else) | `<p>` |
| number | `<span>` via `Intl.NumberFormat` |
| boolean | `<span class="badge">` Yes/No |
| array (React) | recurse each element as `${name}[${i}]` |
| object `.dateTime` | `<time>` dateStyle+timeStyle, optional `.timeZone` |
| object image-shaped | `resolveCmsImageUrl` → `src`, `field.altText ?? ''` → `alt` → `<img loading=lazy>` (React ImageSlot wins) |
| object `.ref.contentKey` | `resolveRef` → title, else contentKey |
| else | skip |

An object is "image-shaped" when it has a top-level string `url` OR a `source`
with a string `type` (`isImageObject`).

## RichText — decode, then inject through ONE path

Delivery sends RichText entity-encoded (`&lt;div&gt;…`), so the match MUST include
`&lt;` — a `<`-only test never fires and tags render as literal text. The literal
side matches a tag-open (`<` followed by a letter, `/`, or `!`), NOT a bare `<`, so
plain prose like `"Q4 < projected"` stays a `<p>` instead of being dropped by the
browser's HTML parser. Decode with
the toolkit's `decodeRichHtmlEntities` BEFORE injecting; never HTML-escape a
decoded string (decode + escape cancel out). Injection is a single site per
framework:

- **React** — `richTextSanitizer(decodeRichHtmlEntities(value))` → `dangerouslySet
  InnerHTML` in the `RenderField` dispatcher inside `heuristicRenderer.tsx`.
  Delivery RichText is TRUSTED, so the default
  sanitizer is pass-through; apps add DOMPurify via `setRichTextSanitizer` for
  defense-in-depth (an escape-only default would undo the decode).
- **Angular** — `decodeRichHtmlEntities(value)` → `[innerHTML]` in
  `cms-content.component.ts`. Angular's `DomSanitizer` sanitizes the binding
  automatically — do NOT `bypassSecurityTrustHtml`.

Rule 4 in `SKILL.md`; symptoms in `references/failure-modes.md`.

## Image URL resolution (toolkit-owned)

Never use an image field directly as a `src` — pass it to the toolkit's
`resolveCmsImageUrl(field)` (React helper `resolveImageSrc`; the Angular component's
private `resolveImageSrc`). It handles both variants and the references-bag fallback,
and resolves a relative CMS media url on its own; absolute/CDN urls pass through.
Pass NO options object — the resolver needs no instance origin. The call is
synchronous — resolve inline, render nothing when it returns `undefined`. Field shape
+ the two variants: `references/package-api.md`.

For the `alt` attribute, read the field's authored `altText` (`resolveImageAlt`);
`resolveCmsImageUrl` returns only the `src` string and drops the field, so read
`altText` from the original field object, not the resolved URL. Fall back to `''` 

## Media types — a dedicated renderer, NOT the heuristic path

Standalone CMS media (`sfdc_cms__{image,audio,video,document}`) is a PREDEFINED type
parallel to `news`, and a single asset rather than a field bag — so it does NOT run
through this heuristic renderer at all. A media ref (`cmsType` ∈ `image`/`audio`/
`video`/`document`) binds to the shared **`MediaRenderer`** (React
`assets/react/MediaRenderer.tsx`; Angular `assets/angular/MediaRenderer.component.ts`),
which switches on `cmsType` to one element. It **forks first by ref shape** for how the
`src` is obtained (Rule 1/Rule 2):

- **Foreign `url` ref** — `ref.url` IS the asset, so it goes directly onto the element
  `src`/`href`: NO fetch, NO resolver. `alt`/document-label come off the ref
  (`ref.altText` / `ref.title`), since there is no body to read them from.
- **`contentKey` ref** — fetch the uniform `CmsMediaBody` (`sfdc_cms:media` + optional
  `altText`) via `useCmsItem` / `CmsItemService`, then resolve the src by medium.

| cmsType | Element | Src — `url` ref | Src — `contentKey` ref |
|---|---|---|---|
| `image` | `<img src alt loading="lazy">` | `ref.url` | `resolveCmsImageUrl(sfdc_cms:media)` |
| `audio` | `<audio controls src>` (no `altText`) | `ref.url` | `resolveMediaUrl(url)` |
| `video` | `<video controls src>` | `ref.url` | `resolveMediaUrl(url)` |
| `document` | `<a href download>` — download link only, no inline preview | `ref.url` | `resolveMediaUrl(url)` |

Dispatch is by `cmsType` (known at ref-registration time) and ref shape, **never by body
shape** — so audio/video/document never enter this file's `isImageObject` branch and
can't be mis-rendered as an `<img>`. On the `contentKey` path, src resolution splits by
medium: image reuses the toolkit image resolver; audio/video/document pass the body `url`
to the toolkit's `resolveMediaUrl`. Both take only the subject and no options — the
toolkit resolves a relative Connect-API url itself (Rule 2,
`references/codegen-guardrails.md`). `mimeType` inside `source` is available for finer
intra-medium choices but is NOT the type discriminator.
