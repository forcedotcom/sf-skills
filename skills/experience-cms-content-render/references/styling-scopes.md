# Styling Scopes

The skill NEVER scaffolds a CSS file, a design system, or CSS variables. Two things
carry presentation, and only these two:

1. **Stable class hooks** the render always emits (below) — selector anchors for the
   app's own stylesheet.
2. **Presentation applied ON TOP of the render**, per the user's prompt, at the
   render target the skill writes (the detail page's `<main>`, or the wrapper it
   inserts for an in-place embed). Applied inline (a `style={{…}}` object or an
   added `className` the app already defines) — never by emitting a `.css` file.

## Default reading layout

When the user asks to render / embed / create a detail page and gives NO explicit
styling direction, apply this baseline on the render target:

- **Centered single column**, `max-width` ~`700px`, `margin: 0 auto`.
- **Large, readable typography** (body ~`1.125rem`, `line-height` ~`1.6–1.7`).
- **Ample whitespace** (generous padding around the column, spacing between fields).

This is a starting look, not a mandate — the prompt overrides it. "Make it full-bleed",
"use a 2-column card", "tighter spacing", "match our brand font" all replace the
relevant part. If the user names their own class or stylesheet, prefer wiring that
over inline values.

## Detail page vs. in-place embed — style them differently

- **Detail page** owns its `<main>` route → style generously (the full reading
  layout above: centered column, hero image, article spacing). Low clash risk.
- **In-place embed** is dropped into the app's own component → stay conservative.
  Apply typography/whitespace that inherits context; do NOT impose fixed widths,
  centering, or layout that fights the host. When unsure for an embed, lean on the
  class hook and let the app's stylesheet own layout.

## Classes emitted (always, regardless of styling)

| Scope | Class | Source |
|-------|-------|--------|
| Per-type card | `cms-<type>-card` | `{{type}}Layouts.card.className` |
| Per-type detail | `cms-<type>-detail` | `{{type}}Layouts.detail.className` |
| Detail page wrapper | `cms-detail-page cms-<type>-detail-page` | React `assets/react/DetailPage.tsx` / Angular `assets/angular/DetailPage.component.ts` |

Same class hooks in both frameworks: React emits them on the renderer's
`<article>` / detail-page `<main>`; Angular's `<cms-content>` article and the
`{{PageName}}Component` `<main>` emit the identical strings. Inner tags (`<h1>`,
`<img>`, …) carry no class — reach them via descendant selectors
(`.cms-news-card > img { … }`) or style the container.

## Precedence & override

`className` prop on the embed beats the layout preset's className (React
`className="…"`, Angular `[className]="…"`). Override presets in the above-marker
region of `src/cms/<framework>/types/<type>.ts` (regeneration preserves it):

```ts
export const newsLayouts = {
  card:   { fields: ['title', 'bannerImage', 'excerpt'] as const, className: 'my-news-tile' },
  detail: { fields: undefined,                                     className: 'my-news-hero' },
} as const;
```

React custom slot components (`components={{ Image: MyImg }}`) own their own
className; the wrapper `<article>` keeps the type-scoped class so ancestor
selectors work. Angular has no slot props — style via the class hooks.
