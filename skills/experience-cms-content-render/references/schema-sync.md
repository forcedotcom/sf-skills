# Schema Sync

Every Embed fetches the content type's shape and emits typed TS. The per-type body
module is FRAMEWORK-AGNOSTIC (identical for React and Angular); the renderer is
framework-specific. Files under `src/cms/react/` or `src/cms/angular/`:

- `<framework>/types/<type>.ts` — **above-marker** region (user-editable: layouts,
  slots, className presets) + **below-marker** region (generated: `<Type>Body`
  interface and `<type>FieldTypes` map). Imports `CmsFieldType`/`CmsImageField` from
  `../../shared/cmsCore.types`.
- The renderer — no user region, regenerated in full. React
  `react/types/<Type>Renderer.tsx`, Angular `angular/types/<Type>Renderer.component.ts`.

## OOTB `sfdc_cms__news` — predefined, do NOT fetch

The metadata fetch cannot resolve OOTB Salesforce content types, so `sfdc_cms__news`
has a FIXED schema — skip retrieval and emit exactly these fields:

| field | lightningType | `<Type>Body` TS | `CmsFieldType` |
|-------|---------------|-----------------|----------------|
| `bannerImage` | Image | `CmsImageField` | `'image'` |
| `body` | RichText | `string` | `'richText'` |
| `excerpt` | Text | `string` | `'text'` |

No `sf project retrieve` / MCP / SOQL for news. Other OOTB types are not predefined —
treat them as custom and fetch below.

## Schema retrieval (custom types)

Retrieve the ContentTypeBundle from the org (bare DeveloperName — no `c__` /
`sfdc_cms__` prefix; relative `--output-dir` inside the project):

```bash
sf project retrieve start --metadata ContentTypeBundle:<DeveloperName> \
  --target-org <targetOrg> --output-dir retrieved-content-types --json
```

Resolve `<targetOrg>` via `sf config get target-org --json`; unset → HALT, ask the
user to `sf config set target-org=<alias>`. Read (with the `Read` tool, not `cat`)
`retrieved-content-types/contentTypes/<DeveloperName>/schema.json`; valid iff
`lightning:type === "lightning__objectType"` and `properties` is a non-empty object.

Map each `properties` entry to `{ name, lightningType (PascalCase: Text, RichText,
Image, …), required, localizable }`, then to the lowerCamel `CmsFieldType` literal
per the table below. Do NOT use Tooling/REST `/sobjects/` or Connect CMS —
ContentTypeBundle is Metadata-API only. Type not found → verify DeveloperName
(case-sensitive, no prefix); auth/session error → `sf org login web`. Retrieval
fails → emit the below-marker block with a `TODO` listing fields to fill manually.

## Markers

```ts
// <experience-cms-content-render:above-begin>
// … user-editable …
// <experience-cms-content-render:above-end>
// <experience-cms-content-render:below-begin>
// … generated …
// <experience-cms-content-render:below-end>
```

Line-comments only; never inside strings/JSX. Skill greps for exact begin/end
pairs and requires both.

## Regeneration algorithm

1. Read `<framework>/types/<type>.ts`; locate the four markers.
2. Any marker missing / duplicated / out of order → **HALT** with file+line and the
   expected marker. NEVER auto-heal — marker damage means a hand-edit the skill
   can't safely merge.
3. Extract the above region byte-for-byte.
4. Regenerate the below region from the schema: `<Type>Body` (one prop per field) +
   `<type>FieldTypes` (field → lowerCamel `CmsFieldType` literal).
5. Reassemble `[preamble][above as-read][below as-generated]`; write only if
   changed, else report "no drift".

## Field shapes — primitives, not wrappers (Rule 5)

Delivery returns SCALAR fields as PLAIN primitives, not `{ value }` wrappers. Map
`lightningType` → TS type accordingly:

| lightningType     | `<Type>Body` TS type | `CmsFieldType` literal | Delivery shape                     |
|-------------------|----------------------|------------------------|------------------------------------|
| Text              | `string`             | `'text'`               | `"title": "Berries"`               |
| RichText          | `string`             | `'richText'`           | `"body": "&lt;div&gt;…"` (encoded) |
| Url               | `string`             | `'url'`                | `"link": "https://…"`              |
| Date              | `string`             | `'date'`               | ISO string                         |
| DateTime          | `string`             | `'dateTime'`           | ISO string                         |
| Number            | `number`             | `'number'`             | `12`                               |
| Boolean           | `boolean`            | `'boolean'`            | `true`                             |
| Image             | `CmsImageField`      | `'image'`              | `{ url, altText, source }` — OBJECT |
| Reference         | see RenderField      | `'reference'`          | `{ ref: { contentKey } }`          |

`<type>FieldTypes` values are the **lowerCamel literals** in column 3, NOT the
PascalCase `lightningType` token — copying `'Text'`/`'RichText'` verbatim is a type
error against the `CmsFieldType` union in `cmsCore.types.ts`.

Only Image (and refs) are objects — NEVER emit `{ value: string }` for a scalar
(that bug made RichText render as nothing: `body.body.value` was `undefined`). The
renderer reads `body.<field>` directly, no `.value` unwrap. When the schema alone is
ambiguous, **confirm each field's shape against a real payload** (`unauthenticatedUrl`).

## Drift → below-region effect

New field → added; removed field → dropped (referencing code fails typecheck,
intentional); type changed → prop+entry change; rename → remove+add (user
reconciles); required flip → optional marker flips. Above region unaffected.

## No barrel

No per-type `index.ts`. Consumers import each renderer by its direct path — React
`import { NewsRenderer } from '../types/NewsRenderer'`, Angular
`import { NewsRendererComponent } from '../types/NewsRenderer.component'` — so
adding a type writes only `<type>.ts` + the renderer, and removing one is a plain
file delete (referencing imports then fail typecheck, intentional).
