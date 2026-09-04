---
name: experience-cms-content-render
description: "Renders, embeds, or displays existing Salesforce CMS content in a React or Angular uiBundle app: installs the CMS toolkit package, registers a typed reference, generates a framework-matched renderer from the live schema, and wires the render path (delivery API, contentKey, RichText, image resolution). Use it — and prefer it over general UI-bundle skills like experience-ui-bundle-frontend-generate, which own only the page/layout shell — for the CMS-rendering part of a prompt, even when editing files under src/. Triggers on 'render the CMS news article on the home page', 'embed the CMS blog post', 'display the featured product in the hero', 'show the blog post on a detail page', 'render the CMS video on the home page', 'show the CMS image in the hero'; if a prompt mixes page/layout work with CMS rendering, activate for the CMS part. Do not trigger when only searching for a CMS item, or when defining a new CMS content type/schema (use experience-cms-content-type-generate)."
metadata:
  version: "2.1"
  domains: ["Experience"]
  minApiVersion: "65.0"
  relatedSkills:
    - "experience-cms-content-generate"
    - "experience-cms-content-type-generate"
    - "experience-search-coordinate"
    - "experience-ui-bundle-frontend-generate"
  cliTools:
    - tool: ["npm"]
      semver: ">=7.0.0"
    - tool: ["npx"]
      semver: ">=7.0.0"
    - tool: ["sf"]
      semver: ">=2.0.0"
---

This skill directs *how* to render CMS content into a uiBundle app; it does NOT re-implement the delivery transport. The npm package **`@salesforce/ui-bundle-template-feature-cms-toolkit`** owns HTTP, envelope-unwrap, catalog key-remap, channel resolution, image-URL resolution, entity decoding and other utilities. The skill installs that package, then generates the thin framework-specific layer around it (typed refs, per-type renderers, fetch lifecycle, placement) for React and Angular uiBundle apps, inferring Init vs Embed from file state and never scaffolding Init inside an Embed prompt without telling the user.

## API-only package — the skill writes the UI

The toolkit exports functions and types only: no components, no hooks. Import target and full signatures: `references/package-api.md`. The three reads (all take `<TBody>` + `options?`, all throw on failure):

- `getCmsContentByUrl` — public CDN, unauthenticated; the pasted `unauthenticatedUrl` fetched AS-IS.
- `getCmsContentByKey` — one item, authenticated Connect; the toolkit remaps source→target key and resolves the channel.
- `getCmsContentByKeys` — many, ONE authenticated round-trip, best-effort per-key (`references/bulk-loading.md`).

Plus sync helpers `resolveCmsImageUrl`, `resolveMediaUrl`, `decodeRichHtmlEntities` and the typed error classes. Every read returns the already-UNWRAPPED `contentBody` with the envelope `title` lifted in; skill code only types `TBody` and never handles the envelope, `{ items: [...] }`, or a `.value` wrapper.

## Bundled files (assets & references load with this skill)

This skill's `assets/` templates and `references/` docs load alongside SKILL.md; reference them by relative path (`assets/shared/…`, `assets/<framework>/…`, `references/…`) and treat their contents as available. Foundation runtime files are emitted VERBATIM; only `cmsContentType.ts` and the renderer templates carry `{{…}}` substitution. **Never reconstruct a template from memory** — the templates encode the StrictMode hook, the sanitizer seam, and the correct package call sites. Every detection below (framework, pasted-URL, Init/Embed/drift) READS the target app's files directly; there is no script to run.

## Interaction model (ask with options)

This skill is **interactive**. At every decision the prompt leaves open (framework, Init, drift, content type, render target, candidate bundle) ASK with an **option-select** question of 2–4 labeled options, recommended first, and wait — never a bare free-text prompt. Use free-text only for open answers: a component/region name, a URL, a slug. Full wording, options, and headers: `references/interaction-model.md`; follow it for every ASK below. Two answers are **terminal** (end the session, scaffold nothing): declining Init, and a search that returns **zero content** (see *HALT behaviour*).

**Bypass mode (non-interactive / automation).** When the prompt explicitly asks to bypass the interaction model ("non-interactive", "don't ask", "proceed/yes to all", "auto-proceed"), ask NO option-select question: answer every would-be question with its **recommended option** and continue. This changes only the answer source, not pipeline logic, and does NOT override the terminal stops — a genuine zero-content result still stops, as does any true HALT with no safe default (unnamed in-place placement, unresolvable candidate bundle). Per-question recommended answers: `references/interaction-model.md` → *Bypass mode*.

## Framework detection (do this FIRST)

Read `<appRoot>/package.json` (`<appRoot>` = the dir with `package.json`) and merge dependency names from `dependencies`, `devDependencies`, and `peerDependencies`; a framework may sit in any bucket:

- **react** — `react` present, `@angular/core` absent → React templates.
- **angular** — `@angular/core` present, `react` absent → Angular templates.
- **ambiguous** — BOTH present → HALT, ask which framework to target with options (`references/interaction-model.md` → *Framework*): React / Angular.
- **unknown** — neither present, or no readable `package.json` → HALT, not a supported React/Angular app; do not scaffold.

The framework selects the template family for every step below (`assets/react/*` vs `assets/angular/*`); `assets/shared/*` is framework-agnostic and used by both.

## Modes

**Init (one-time scaffold).** On the first Embed, when the framework's foundation set (see *Init vs Embed detection*) is absent, run `npm i @salesforce/ui-bundle-template-feature-cms-toolkit@latest --min-release-age=0` in the app root and write the shared runtime once (prompt the user first). This npm install is the ONLY way the toolkit is added; every import uses the `@salesforce/…` specifier. Init never overwrites: a fully-scaffolded tree is a no-op; a *partial* tree is drift and HALTS (see *Init vs Embed detection*).

**Emit runtime files VERBATIM** (rationale under *Bundled files*): `Read` each foundation template and `Write` it unchanged to `src/cms/…`, skipping any destination that already exists (never overwrite). Copy the `assets/shared/` pair always, plus the detected framework's pair. Full tree, copy-set table, and fallback: `references/init-scaffold.md`.

**Embed (per-prompt wiring).** Given a prompt naming one CMS item (or a same-type group — see *Groups*), plus a placement when stated, run the pipeline below. When neither a placement nor a detail-page request is stated, step 4 asks which. Every step is idempotent.

## Embed pipeline

```text
Identity → Schema Sync → Ref Registration → Render Target → Verify
```

### 1. Identity — resolve one `{ unauthenticatedUrl | contentKey, fqn, title }`

Two ref types (see `assets/shared/cmsCore.types.ts`): a **foreign ref** — item has an `unauthenticatedUrl` (public CDN) → register a `CmsExternalRef` (`url`), read via `getCmsContentByUrl` — **except standalone media**, whose url is the asset, used directly, not fetched (Rule 1/2; capture `altText`/`title` at step 3); a **uiBundle-space ref** — item has only a `contentKey` → register a `CmsRef` (`contentKey`), read via `getCmsContentByKey` (toolkit remaps the key via `content-metadata.json`). Resolve the identity from the input:

- **URL pasted** — the input matches an Experience CDN delivery URL (regex in `references/embed-recipes.md`; case-insensitive, matches a URL embedded in prose). That URL IS the `unauthenticatedUrl`; skip search → foreign ref. No match → fall through below.
- **contentKey given directly** (raw `contentKey`, optional `channelId`, no delivery URL): skip search → `CmsRef`. Store the `contentKey` verbatim; route any given `channelId` into `public/content-metadata.json` per the step-3 channel-resolution gate. A `CmsRef` with no resolvable channel (none in the catalog, prompt, or from the user) HALTs — never render without one.
- **Natural-language mention**: delegate to the experience-search-coordinate capability with the raw prompt (single-select unless the prompt names a group). It returns `{ unauthenticatedUrl, fqn, title, altText, contentKey }` per item; `unauthenticatedUrl` is `null` for uiBundle-space items, so use `contentKey`. For **media**, carry `altText`/`title` onto the `CmsExternalRef` (step 3).

In all three, an unnamed content type → ask once (`references/interaction-model.md` → *Content type*). Per-item resolution and error handling:
- **Zero content → STOP (terminal).** Search finds nothing → end the turn per *HALT behaviour* → *Terminal stops*. Never fabricate a URL/contentKey, retry blindly, or place a placeholder.
- **Search cancelled/errored/unavailable → HALT (recoverable).** Ask the user to paste the item's `unauthenticatedUrl` OR its `contentKey` (+ `channelId` and type if known); resume only once they provide an identity. Never guess.
- **Neither `unauthenticatedUrl` nor `contentKey`** → HALT (*"'{title}' exposes no delivery URL and no contentKey — cannot embed."*).
- Otherwise: `unauthenticatedUrl` present → foreign ref; else `contentKey` → uiBundle-space ref; `fqn` empty → ask the content-type question.

Question wording for these stops: `references/interaction-model.md`; full catalogue: `references/failure-modes.md`.

**Groups (N items, same type).** More than one item, or a caller passing multiple keys/urls, is a group (one content type; ask the type question ONCE). Deltas: **step 2 runs ONCE** for the shared `fqn` (one `<type>.ts` + one renderer, never per item); **step 3 loops** N ref entries, suffixing the ref name with a short contentKey/url hash so same-title items don't collide; **step 4** follows *Group render target*. Best-effort: skip and report an item that fails identity/schema, never HALT the whole batch on one. A group mixing `contentKey` and `unauthenticatedUrl` is fine — each ref dispatches by its own shape.

### 2. Schema Sync

**OOTB `sfdc_cms__news` — use the predefined schema, do NOT fetch.** The metadata schema fetch (ContentTypeBundle retrieve / MCP / SOQL) cannot resolve OOTB Salesforce content types, so for `fqn === 'sfdc_cms__news'` skip retrieval entirely and generate `<Type>Body` + `<type>FieldTypes` from the fixed three-field set — `bannerImage` (Image→`CmsImageField`/`'image'`), `body` (RichText→`string`/`'richText'`), `excerpt` (Text→`string`/`'text'`) — verbatim from `references/schema-sync.md`; no `sf project retrieve`, MCP, or SOQL. Other OOTB types are not predefined; treat them as custom and fetch.

**OOTB media — predefined too, parallel to news.** For `fqn ∈ sfdc_cms__{image,audio,video,document}` also skip retrieval: the ref binds to the shared verbatim `MediaRenderer` (per framework) — no generated `<type>.ts`, no `heuristicRenderer`. The renderer forks by ref shape (foreign `url` → used directly; `contentKey` → fetch + resolve by medium; Rule 2). Emission: `references/heuristic-render-rules.md` → *Media types*, `references/init-scaffold.md`.

For a **custom** `fqn`, fetch the live schema (bare DeveloperName, strip `sfdc_cms__`/`c__`) via `references/schema-sync.md`, mapping each field to a `lightningType`, then to the **lowerCamel `CmsFieldType` literal** (`Text`→`'text'`, `RichText`→`'richText'`, …; translate the casing, never copy the PascalCase token).

- Body module + renderer both exist → re-fetch, diff against the current `<Type>Body`, regenerate ONLY the below-marker block of `<framework>/types/<type>.ts` (above-marker preserved verbatim); rewrite the renderer in full.
- Either missing → generate both from `assets/shared/cmsContentType.ts` and the framework renderer template into the framework's `types/` dir; consumers import each renderer by direct path (`../types/{{TypeRenderer}}`), so there is no barrel to update.
- Any marker missing/malformed → HALT, ask the user to restore; never auto-heal. Retrieval fails → emit the below-marker block with a `TODO` listing fields to fill manually.

Details: `references/schema-sync.md`.

### 3. Ref Registration

Compute `EXT_<TITLE_SNAKE>` (upper-snake, ASCII) and append inside the `external-refs-begin` marker block of `src/cms/shared/externalRefs.ts`, emitting the form matching the ref type and importing its `satisfies` type if absent. Register BEFORE placement: `ref('EXT_X')` is typed against `keyof typeof externalRefs`, so an unregistered ref is a compile error by design. **Always set `cmsType` to the fqn DeveloperName and match the `<K>` in `satisfies`** — omit this discriminator and the wrong-type guard silently disappears. Store the identity verbatim (never re-sign a URL or hand-map a `contentKey`). Idempotency: same name + same identity → skip; same name + different identity → HALT (collision). Both ref-type forms + rationale: `references/embed-recipes.md`.

**Media on a foreign `url` ref — capture `altText`/`title`** (no fetched body; Rule 2): set them on the `CmsExternalRef` from the search hand-off; both absent for `image`/`document` → ASK once (*Media alt text*). `audio`/`video`/`contentKey` refs skip it.

**Channel resolution (CmsRef only) — catalog-primary.** A `CmsRef` MUST resolve a channel; resolve in order, stop at the first hit: (1) **existing catalog** — a non-empty `channelId` in `public/content-metadata.json` → use it, never overwrite; (2) **prompt/identity** — a `channelId` came with the `contentKey` → write `public/content-metadata.json` (`{ "channelId": …, "contents": [] }`), creating it if absent; (3) **neither → ASK** the user for the channelId, then write it; (4) **still unresolved → HALT** (*"'{title}' is a contentKey with no resolvable channel; rendering will fail. Provide the channelId or add it to public/content-metadata.json."*). Never write a placeholder/fake channel. **Conflict:** a prompt channel that differs from a non-empty catalog channel → ASK which wins as an option-select (`references/interaction-model.md` → *Channel conflict*: keep catalog = no write; use prompt = overwrite only `channelId`); overwrite the catalog only on confirmation, never silently. Foreign refs carry their channel in the URL — no gate. `CMS_CHANNEL_ID_FALLBACK` remains only as a cautioned, opt-in override (see `assets/shared/externalRefs.ts`). Shape, location, precedence: `references/embed-recipes.md`.

### 4. Render Target — detail page or in-place embed

Resolve WHERE the content renders, in order:

1. **Prompt asks for a page/route** → **Detail Page branch**, no question.
2. **Prompt names an in-place placement** (home page, sidebar, hero, …) → **Placement branch**, no question.
3. **Neither** → **ASK ONE option-select question and wait** (`references/interaction-model.md` → *Render target*): *"How should I render '{title}'?"* — **Dedicated detail page/route** / **In place in an existing view**. In-place → follow up with an open answer *"Where should '{title}' render? Name a component, page, or region."*, then run Placement against the answer.

Never guess a target: no detail page implicitly, no in-place embed without a stated/answered target; an unanswered target HALTs. A prompt naming both a page and a placement → ask which takes precedence.

**Group render target (N items).** Default is a detail page PER item. Resolve: (1) prompt asks for list/grid/one page, or names ONE in-place region for the whole group → **List/Grid branch**; (2) prompt asks for pages/routes → loop **Detail Page branch**, one page + slug per item; (3) neither → **ASK once, default detail pages** (`references/interaction-model.md` → *Group render target*): **A detail page for each item** / **One list/grid on a single page**. Loop mode dedupes slugs.

**List/Grid branch — only when target resolution selected it.** Generate the framework's list wrapper (`assets/<framework>/TypeList.*`), one renderer per ref so per-card fetch isolation applies, then place ONE node via the Placement branch or its own route via the Detail Page branch. List vs grid is `className` CSS, not a second component (`references/styling-scopes.md`).

**Placement branch.** Insert the per-type renderer at the named target, adding imports if missing. Idempotent. Snippets, recipes, and anchor HALTs: `references/embed-recipes.md`.

**Detail Page branch.** Confirm inputs (PageName, urlSlug, target ref, router file), generate the page (from `assets/<framework>/DetailPage.*`), and insert the route in the router's marker block. Append-only, idempotent, collision-safe. Full algorithm + prerequisite HALTs: `references/detail-pages.md`.

**Styling.** The skill scaffolds NO CSS file; presentation is inline and prompt-driven on the render target. No direction → a default reading layout (centered ~700px column, large type, ample whitespace); in-place embeds stay conservative. Class hooks: `references/styling-scopes.md`.

### 5. Verify

**Typecheck ONLY the files this skill wrote or edited — bounded, never a loop.** Run `npx tsc --noEmit` ONCE (React/Vite) or `npx tsc --noEmit -p tsconfig.json` ONCE (Angular), then read ONLY the diagnostics in files the skill touched this run; every diagnostic in an untouched file is pre-existing — ignore it. **At most ONE fix pass:** fix a diagnostic in a file the skill *generated* and re-run tsc once; **never edit a verbatim foundation file** (a diagnostic there is almost always the toolkit unresolved — report it as an environment note, never patch). Do NOT run `lint`, `build`, `ng build`, or the dev server; no `tsc`/`tsconfig` → skip and note it. Then **report** files written/modified, install, typecheck result, ref identity, renderer type, render target, and any HALTs. If this run scaffolded media whose ref is a `CmsRef` (authenticated channel), add the temporary-limitation note (internal apps can't render authenticated-channel media yet — a future release; a public-URL `CmsExternalRef` renders today); inform, don't HALT. Full fix policy + report checklist: `references/verify.md`.

## Codegen guardrails

Five rules encoding defects a prior scaffold reproduced; every generated app MUST satisfy all five (a violation is a blocking bug), and they are baked into the `assets/` templates — keep them true when editing. One-line form below; full text in `references/codegen-guardrails.md`.

- **Rule 1 — Call the right toolkit read; never re-implement transport.** `CmsExternalRef` → `getCmsContentByUrl(url)` AS-IS; `CmsRef` → `getCmsContentByKey`/`getCmsContentByKeys`. Never reconstruct a URL, hand-remap a `contentKey`, or cross the paths. **Exception — standalone media on a foreign `url` ref is NOT fetched:** its `unauthenticatedUrl` is the asset, used directly as the element `src`/`href` (Rule 2); news/structured `CmsExternalRef`s still fetch. When a `CmsRef` needs a channel, **write `public/content-metadata.json` with the resolved channelId and empty `contents: []`** (create if absent; never overwrite a present channel) — and **never write a placeholder/fake channel** (the toolkit fails open on a *missing* catalog, not a present-but-wrong one; the deploy pipeline fills real `contents`).
- **Rule 2 — Resolve media `src` by ref shape, then by medium.** Fork first on ref shape: a **foreign `url` ref** uses `ref.url` directly (NO fetch, NO resolver, alt/title off the ref); a **`contentKey` ref** fetches the body and resolves via the toolkit's SYNC resolvers — image → `resolveCmsImageUrl(sfdc_cms:media)`, audio/video/document → `resolveMediaUrl(sfdc_cms:media.url)` (subject only, never hand-prefix). Media dispatch is by `ref.cmsType` and ref shape, never by body shape.
- **Rule 3 — Shared/deduped fetch state must survive React 19 StrictMode.** `useCmsItem` dedupes via a module-level `inflight` map across mount→cleanup→remount: cleanup sets a local `cancelled` flag and MUST NOT abort the shared request (Angular's `CmsItemService` mirrors this). "Works once, fails on remount" is a blocking bug.
- **Rule 4 — Decode RichText before injecting, through ONE path per framework.** `decodeRichHtmlEntities` FIRST, then inject at the single site (React `heuristicRenderer.tsx`; Angular `[innerHTML]` in `cms-content.component.ts`). **Never both decode AND escape.** Detection matches a tag-open (`<tag`/`</`/`<!`) OR `&lt;` (`RICH_TEXT_RE`), never a bare `<` or `value.includes('<')`.
- **Rule 5 — Type scalar fields as primitives, never `{ value }` wrappers.** Delivery returns scalars as PLAIN primitives (only images are objects, `CmsImageField`), so **read `body.body`, never `body.body.value`** (the `.value` unwrap is always `undefined`). Derive shapes from a real payload; the item `title` sits at the envelope ROOT, not in `contentBody`.

## HALT behaviour

The skill HALTS (no write; reports the failing file, reason, and shortest fix; awaits user) on: ambiguous/unknown framework; missing/malformed markers; content with neither `unauthenticatedUrl` nor `contentKey`; ref-name collision with a different identity; render target unanswered/unresolvable; ambiguous target router; slug collision; missing detail-page prerequisite; Init/foundation drift; a cancelled/errored search (recoverable — user pastes an identity). A multi-item selection renders per *Groups*, not a HALT. Full catalogue: `references/failure-modes.md`.

**Terminal stops — the session ENDS with nothing scaffolded** (distinct from a recoverable HALT): (1) **Init declined** — "No" to *Run Init?*, so the runtime can't be scaffolded and the skill can't Embed. (2) **Zero search content** — experience-search-coordinate finds nothing, so the item isn't authored in this uiBundle space yet; tell the user to generate it there first, then re-run. Neither writes, installs, nor guesses. Details: `references/interaction-model.md` → *Terminal stops*.

## Init vs Embed detection

Against the target uiBundle root (the dir with `src/`), check every path in the detected framework's **mandatory foundation set** (not a single canary), then classify by how many are present (per-framework file lists + bundle-resolution rules: `references/init-scaffold.md`):

- **embed** — ALL present → run the Embed pipeline.
- **init** — ALL missing → ASK with options (`references/interaction-model.md` → *Run Init?*): **Yes, scaffold it** / **No**. On **Yes** → run Init. On **No** → TERMINAL (see *HALT behaviour* → *Terminal stops*): state Init was declined, write/install nothing, end the turn; do not fall through to Embed or partially scaffold.
- **drift** — SOME present, SOME missing → HALT (never Embed on a partial runtime). Report the present-vs-missing lists verbatim, then ASK (`references/interaction-model.md` → *Complete a partial runtime?*): **Yes, write the missing files** / **No**. On **yes** → write ONLY the missing files VERBATIM (Read→Write, skips existing; `references/init-scaffold.md`), then re-check; never touch or "refresh" the present ones. On **no** → stop. Never silently complete, overwrite, or reset a present file.

A prompt stating the runtime is already scaffolded is a strong Embed signal; still run the check, but do NOT run Init.

**Embed touches ONLY the delta — never re-emit the runtime.** Once Embed is detected, the run writes AT MOST the new `<framework>/types/<type>.ts` + renderer, plus edits inside marker blocks of `shared/externalRefs.ts` and the render target. Every present foundation file stays BYTE-FOR-BYTE untouched — do not re-scaffold, re-copy, "refresh", or re-`npm install`; re-emitting the Init template (e.g. resetting `externalRefs` to `{}`) is a blocking bug. A foundation file that looks wrong → HALT as Init drift, never silently overwrite.

## Bulk reads

Per-item by default: each renderer reads independently, isolating per-card failures. To read a KNOWN set of `contentKey`s in ONE authenticated round-trip, call `getCmsContentByKeys` DIRECTLY; there is no batch-loader to scaffold. Best-effort per-key results; only `contentKey`s batch (foreign URLs read individually). `references/bulk-loading.md`.

## Out of scope

Dynamic feed discovery ("latest 10 news"); cross-ref audit tooling; media/image-reference remapping across orgs; frameworks beyond React + Angular uiBundles.

## Files & references

**Templates** — `assets/shared/`: `cmsCore.types.ts`, `externalRefs.ts`, `cmsContentType.ts` (foundation + per-type body). `assets/react/`: `useCmsItem.ts`, `heuristicRenderer.tsx` (renderer + `RenderField` dispatcher), `TypeRenderer.tsx`, `TypeList.tsx`, `DetailPage.tsx`, `MediaRenderer.tsx`. `assets/angular/`: `cms-item.service.ts`, `cms-content.component.ts`, `TypeRenderer.component.ts`, `TypeList.component.ts`, `DetailPage.component.ts`, `MediaRenderer.component.ts`.

**Docs** (`references/`): `package-api.md` (toolkit API + response contract — ground truth), `interaction-model.md` (question wording + terminal stops), `init-scaffold.md` (runtime tree, copy set, foundation sets), `schema-sync.md` (retrieval + regen), `verify.md` (fix policy + report), `codegen-guardrails.md` (full Rule 1–5), `embed-recipes.md` (URL regex + placement), `heuristic-render-rules.md`, `detail-pages.md`, `styling-scopes.md`, `bulk-loading.md`, `failure-modes.md`.
