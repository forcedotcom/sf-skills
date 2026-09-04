# Embed Recipes

## Pasted delivery-URL detection (Identity, step 1)

The input carries a CMS delivery URL when it matches an Experience CDN delivery URL
`https://<host>.salesforce-experience.com/cms/delivery/<ver>/<channel>/contents/<id>`.
Match with this case-insensitive regex; the whitespace-free host segment lets a URL
embedded in surrounding prose still match:

```text
https:\/\/[^\s/]+\.salesforce-experience\.com\/cms\/delivery\/[^\s]*\/contents\/[^\s]+
```

On a match, that URL IS the `unauthenticatedUrl` → skip search, foreign ref. No match
→ fall through to the contentKey / natural-language paths.

---

Placement patterns for the in-place branch of Render Target (SKILL.md step 4).
Every recipe assumes the ref is registered and the renderer exists (earlier
pipeline steps), and that a placement target was stated in the prompt or answered
to the step-4 question.

Base snippet — the per-type renderer takes a `ref`:

**React** (`react/types/{{TypeRenderer}}.tsx`, selector-less component):

```tsx
import { {{Type}}Renderer } from '../cms/react/types/{{TypeRenderer}}';
import { ref } from '../cms/shared/externalRefs';

<{{Type}}Renderer ref={ref('{{REF_CONST}}')} />
```

**Angular** (`angular/types/{{Type}}Renderer.component.ts`, selector `cms-{{type}}`):
import `{{Type}}RendererComponent` into the host component's `imports`, then:

```html
<cms-{{type}} [ref]="itemRef"></cms-{{type}}>   <!-- itemRef = ref('{{REF_CONST}}') on the host class -->
```

Idempotency (all recipes): if the same renderer for the same `{{REF_CONST}}`
already exists inside the anchor element, skip.

| Recipe | Prompt shape | Anchor | Extra prop |
|--------|--------------|--------|------------|
| Named component/page | "add X to `<Component>`" | JSX/template return: `cms:embed` placeholder comment, else append to top element's children | — |
| List/grid item | "add X as a card in the list" | static sibling list → append; **dynamic `.map`/`@for` list → HALT** (add to data source instead) | `layout="card"` |
| Sidebar | "put X in the sidebar" | first `<aside>`; none → HALT for a target | `layout="card"` |
| Hero | "show X as the hero" | top-level element or first `<header>` | `layout="detail"` |
| Custom layout | "use my `card-large` layout" | as named; layout must exist in `{{type}}Layouts` else HALT | `layout="card-large"` |
| Fields whitelist | "only show title and image" | as named | React `fields={['title','bannerImage']}` / Angular `[fields]="['title','bannerImage']"` |
| Slot override (React only) | "render the title as a link" | as named; **always HALTs to show diff first** (creates a component in parent scope) | `components={{ Title: … }}` |

Angular has no `components` slot prop — for a custom title/image treatment, style
via the class hooks (`references/styling-scopes.md`) or customize the renderer.

## Ref-registration forms (Embed step 3)

Append inside the `external-refs-begin` marker block of `src/cms/shared/externalRefs.ts`;
emit the form matching the ref type and ensure the `satisfies` type is imported:

```ts
// Foreign ref (unauthenticatedUrl):
EXT_FOOD_BERRIES: { name: 'EXT_FOOD_BERRIES', url: 'https://…/cms/delivery/…/contents/…?oid=…', cmsType: 'news' } satisfies CmsExternalRef<'news'>,
// uiBundle-space ref (contentKey — remapped at runtime via content-metadata.json):
EXT_LAUNCH_NEWS: { name: 'EXT_LAUNCH_NEWS', contentKey: 'M3ASD4KHASDB73', cmsType: 'news' } satisfies CmsRef<'news'>,
// Foreign MEDIA ref (unauthenticatedUrl IS the asset — not fetched; alt/title on the ref):
EXT_HERO_PHOTO: { name: 'EXT_HERO_PHOTO', url: 'https://…cdn….salesforce-experience.com/…/hero.jpg?oid=…', cmsType: 'image', altText: 'Team on launch day' } satisfies CmsExternalRef<'image'>,
```

`cmsType` MUST equal the fqn DeveloperName and match the `<K>` in `satisfies` — this
discriminator is what makes a wrong-typed `ref` a compile error against the renderer;
omit it and the guard silently disappears. Store the identity verbatim: a foreign
`url` (never re-sign, strip `oid`, or bump version) or the `sourceContentKey` (the
toolkit owns source→target remap).

**Media on a foreign `url` ref carries `altText`/`title`.** The direct-URL media path
does not fetch a body, so the accessible name lives on the ref: `altText` (image alt /
audio-video aria-label) and `title` (document download-link label), sourced from the
search hand-off or the *Media alt text* ask (`references/interaction-model.md`).
`audio`/`video` need no `altText`. These fields are ignored on non-media refs and on
`contentKey` media refs (which read alt/title from the fetched body).

### Channel resolution (CmsRef only)

A `CmsRef` MUST resolve a channel — the catalog is primary. Resolve in order, stop at
the first hit:

1. **Existing catalog** — read `public/content-metadata.json`; a non-empty `channelId`
   → use it, do NOT overwrite.
2. **Prompt / identity** — a `channelId` accompanied the `contentKey` → write it into
   `public/content-metadata.json`, creating the file if absent:
   ```jsonc
   { "channelId": "0apSG0000000ExampleChannel", "contents": [] }
   ```
   (`public/` is Vite's web root, so the toolkit's default `${BASE_URL}content-metadata.json`
   resolves to `<appRoot>/public/content-metadata.json`. Empty `contents: []` is safe —
   per-entry remap fails open; the deploy pipeline fills the real pairs.)
3. **Neither → ASK** the user for the channelId (`references/interaction-model.md` →
   *Channel ID*), then write it per step 2.
4. **Still unresolved → HALT**: *"'{title}' is a contentKey with no resolvable channel;
   rendering will fail. Provide the channelId or add it to public/content-metadata.json."*
   Never write a placeholder/fake channel.

**Conflict:** a prompt-provided channel that DIFFERS from a non-empty channel already in
the catalog → ASK which wins with an option-select (`references/interaction-model.md` →
*Channel conflict*), never a silent overwrite. On **keep the catalog** → leave
`content-metadata.json` unchanged (no write). On **use the prompt channel** → overwrite
ONLY the `channelId` (preserve the existing `contents` array). Same/empty → use/write.
Idempotent: present channel → skip; absent → create; present-but-empty → fill.

`CMS_CHANNEL_ID_FALLBACK` in `externalRefs.ts` is a **cautioned, opt-in override** only
(the skill no longer auto-fills it; it is baked into source and does not travel per-org).
Precedence when the toolkit reads: explicit option > `CMS_CHANNEL_ID_FALLBACK` > catalog
`channelId` > the toolkit throws. Foreign refs carry their channel in the URL — no gate.

## Anchor detection failure

No recipe applies (no top-level component, JSX/template return, list, or aside) →
HALT and report the file's markup structure so the user names a concrete anchor.

## Non-goals

No Storybook, no test scaffolding, no wrapper components (`<Suspense>`,
`<CmsBoundary>`) — the renderer handles loading/error internally (React
`useCmsItem`, Angular `CmsItemService`).
