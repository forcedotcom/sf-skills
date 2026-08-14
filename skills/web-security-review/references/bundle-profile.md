# Bundle / React-JSX source profile (v0 — starter)

> Status: starter. The LWS grounding guide (`lws-grounding.md`) was written for
> LWC `.js`, but it states the code under analysis does not have to be LWC. This
> profile maps **framework idioms** onto the DOM sinks the groundings already
> describe, so the reviewer applies the same rules to React/JSX bundle source.
> It does not introduce new rules — it tells the reviewer where the same dangers
> hide in non-LWC code. Per the design doc §4 / §6, this is a shared concern with
> the parallel a11y scanner; expand deliberately.

## Targeting

- Review **source** (`src/`), never built/minified `dist/` output.
- File types beyond LWC `.js`: `.jsx`, `.tsx`, `.ts`, `.mjs`, `.cjs`.

## Framework sink → existing grounding

| React / JSX idiom | Maps to grounding topic |
|---|---|
| React's raw-HTML escape-hatch prop (the one carrying an `__html` payload) | Block Insecure HTML Injection — same as assigning untrusted HTML to a DOM element |
| A `ref` used to reach a real DOM node, then raw-HTML assignment / insertion on it | Block Insecure HTML Injection |
| Rendering a script element, or injecting script via a library | Block Direct Script Element Creation |
| Inline-frame `srcdoc`, or a dynamic frame source, in JSX | Restrict Iframe Security |
| Link/source attributes or programmatic window-open targets built from variables | Restrict URL Schemes (block `javascript:`, `data:`, etc.) |
| Code-evaluation sinks (string evaluator, the Function constructor, string-arg timers) inside hooks or handlers | Block eval |
| Object/URL blob creation for downloads | Restrict URL.createObjectURL |

## Inference notes

- React escapes text children by default; the danger is the **raw-HTML escape
  hatches** above and direct DOM access via refs — focus there.
- Trace the payload's provenance: props, state, fetch/API responses, and event
  data are untrusted sources (mirrors the "Avoid Mutating Unknown Objects"
  provenance reasoning in the guide).
- Server-side / build-time codegen (e.g. MIYO page generation) is still source —
  scan it the same way.

## Open (track with design doc §6/§7)

- Where this profile lands long-term (shared with the a11y scanner).
- Vue / static-HTML coverage beyond React.
