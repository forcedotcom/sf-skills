# Init scaffold — runtime tree, verbatim copy, foundation sets

Detail for the **Init** mode and **Init vs Embed detection** (SKILL.md → *Modes*,
*Init vs Embed detection*). SKILL.md holds the decision rules; this file holds the
file tree, the Read→Write copy mechanics, and the per-framework foundation sets used
for detection.

## Runtime tree (framework-scoped under `src/cms/`)

Init writes the shared runtime once, plus the detected framework's pair:

```text
src/cms/
  shared/                       ← framework-agnostic, always written
    cmsCore.types.ts                 ← CmsExternalRef, CmsRef, AnyCmsRef, CmsFieldType; re-exports CmsImageField
    externalRefs.ts             ← ref catalog + CMS_CHANNEL_ID_FALLBACK (marker-blocked)
  react/                        ← written ONLY when framework=react
    useCmsItem.ts               ← item hook: cache + inflight dedup (StrictMode-safe)
    heuristicRenderer.tsx       ← schema-less renderer: field-pick + value-shape dispatch + sanitizer plug + resolveImageSrc (the ONE RichText injection site)
  angular/                      ← written ONLY when framework=angular
    cms-item.service.ts         ← item service: shared cache + inflight dedup
    cms-content.component.ts    ← schema-less renderer (the ONE RichText injection site)
```

Per-type generated code lands under the framework's `types/` dir, created on the
first Embed; each renderer imports its sibling by direct path, so there is no barrel
to maintain. Detail pages land under `src/pages/<type>/`. The skill never creates
tests, CSS files, router files, or app entry; `main.tsx`/`App.tsx` / Angular
bootstrap must pre-exist.

The toolkit's `content-metadata.json` catalog (`<appRoot>/public/content-metadata.json`)
is written **on demand at the first `CmsRef` embed that needs a channel** — NOT at Init,
and NOT for foreign-ref-only apps (Rule 1; shape + policy in `references/package-api.md`).
It is a pipeline-regenerated data seam (the deploy pipeline overwrites it per target org),
so it is **explicitly NOT part of the foundation detection sets below** — otherwise every
pre-existing app that already carries a catalog would mis-classify as drift.

## Emit runtime files VERBATIM — Read→Write, don't retype

The foundation files are pure copies: never reconstruct API behaviour from memory
(the templates encode the StrictMode hook, the sanitizer seam, and the correct
package call sites). Only `cmsContentType.ts` and the renderer templates carry
`{{…}}` substitution — those are handled in Embed, not here.

For each file in the set, **`Read` the template by its skill-relative path and
`Write` it unchanged to the destination**. The harness loads `assets/` alongside
SKILL.md, so no CWD, absolute path, or shell command is involved. **Skip any
destination that already exists — never overwrite**, so this is safe for Init *and*
the drift-complete branch. If a `Read` fails because the asset is not loadable in
this harness, FALL BACK to the byte-by-byte VERBATIM copy for that file.

| `Read` (skill-relative) | `Write` (under `<appRoot>/`) |
|-------------------------|------------------------------|
| `assets/shared/cmsCore.types.ts` | `src/cms/shared/cmsCore.types.ts` |
| `assets/shared/externalRefs.ts` | `src/cms/shared/externalRefs.ts` |
| `assets/react/useCmsItem.ts` *(react)* | `src/cms/react/useCmsItem.ts` |
| `assets/react/heuristicRenderer.tsx` *(react)* | `src/cms/react/heuristicRenderer.tsx` |
| `assets/angular/cms-item.service.ts` *(angular)* | `src/cms/angular/cms-item.service.ts` |
| `assets/angular/cms-content.component.ts` *(angular)* | `src/cms/angular/cms-content.component.ts` |

Copy the shared pair always, plus the detected framework's pair. This NEVER touches
the `{{…}}`-substituted templates (`cmsContentType.ts`, the per-type renderers,
detail pages).

No dev proxy is scaffolded: the CMS delivery backend serves CORS headers, so the
browser fetches the CDN directly in dev and `vite.config.ts` stays the standard
React config. (The former dev-proxy rule was removed; SKILL.md → *Codegen
guardrails*.)

## Media renderer — VERBATIM, emitted on the first media embed

Standalone media (`sfdc_cms__{image,audio,video,document}`) is a predefined type: it
renders through one shared, verbatim `MediaRenderer` per framework, not a generated
per-type renderer. On the FIRST media embed, `Read`→`Write` the framework's media
renderer (skip if it already exists — never overwrite):

| `Read` (skill-relative) | `Write` (under `<appRoot>/`) |
|-------------------------|------------------------------|
| `assets/react/MediaRenderer.tsx` *(react)* | `src/cms/react/MediaRenderer.tsx` |
| `assets/angular/MediaRenderer.component.ts` *(angular)* | `src/cms/angular/MediaRenderer.component.ts` |

The media types (`CmsMediaBody`, `CmsMediaField`, `CmsMediaType`) ship inside the
always-written `shared/cmsCore.types.ts`, so a media embed onto an existing runtime
needs only the one renderer file plus the ref entry — provided the runtime's
`cmsCore.types.ts` carries the media exports (a pre-media scaffold that lacks them is
Init drift on that file; HALT, don't silently patch). On the `contentKey` path URL
resolution is entirely toolkit-owned (`resolveCmsImageUrl` / `resolveMediaUrl`); no
local prefix helper ships. On the foreign `url` path the renderer uses `ref.url`
directly — no resolver, no fetch (Rule 1/Rule 2).

**The media renderer is NOT in the foundation sets below.** Init/Embed detection is
unchanged: a runtime scaffolded before media existed is still a complete `embed`
runtime, and the media renderer is written lazily on the first media embed exactly
like a per-type `<type>.ts`. Do not add `MediaRenderer.*` to the detection sets, or
every pre-media app would mis-classify as drift.

## Foundation sets (used by Init vs Embed detection)

Check every path for existence against the target uiBundle root (the dir with
`src/`), then classify by how many are present — not a single canary:

- **React foundation set:** `src/cms/shared/cmsCore.types.ts`,
  `src/cms/shared/externalRefs.ts`, `src/cms/react/heuristicRenderer.tsx`,
  `src/cms/react/useCmsItem.ts`.
- **Angular foundation set:** `src/cms/shared/cmsCore.types.ts`,
  `src/cms/shared/externalRefs.ts`, `src/cms/angular/cms-content.component.ts`,
  `src/cms/angular/cms-item.service.ts`.

The app root is inside a uiBundle, not the SFDX project root, so foundation files
resolve to `force-app/main/default/uiBundles/<bundleName>/src/cms/…`. Run the check
against the target bundle when known; otherwise scan each subdir of
`force-app/main/default/uiBundles/` and pick the scaffolded one, asking the user
with options if multiple qualify (`references/interaction-model.md` →
*Candidate uiBundle*).

### Drift-complete branch

On a **drift** classification, when the user answers **Yes, write the missing
files**: write ONLY the missing files VERBATIM from `assets/…` via the Read→Write
copy set above (it skips destinations that already exist), then re-check. Never
touch or "refresh" the present ones; never silently complete, overwrite, or reset a
present file.
