# Detail Pages

The Detail Page branch of Render Target (SKILL.md step 4). Reached when the prompt
asks for a route/page (e.g. *"create a detail page for X"*) OR when the user picks
"detail page" in answer to the step-4 render-target question. Never created
implicitly — either the prompt states it or the user chooses it.

For a same-type GROUP, this branch runs ONCE PER ITEM (default group target): N
pages, N routes, each targeting its own ref, with slugs deduped across the batch so
same-title items don't collide. The renderer + `<type>.ts` are shared (generated
once in step 2); only pages, routes, and refs multiply.

Paths below are under the detected framework's dir — `src/cms/react/` or
`src/cms/angular/`. Templates: React `assets/react/DetailPage.tsx`, Angular
`assets/angular/DetailPage.component.ts`.

## Prerequisites (else HALT)

1. `<framework>/types/{{type}}.ts` exists (markers intact).
2. The renderer exists — React `react/types/{{Type}}Renderer.tsx`, Angular
   `angular/types/{{Type}}Renderer.component.ts`.
3. `{{REF_CONST}}` registered in `src/cms/shared/externalRefs.ts`.
4. Router file has a marker-blocked route region (below).

## Inputs (confirm all in ONE prompt before writing)

| Input | Default |
|-------|---------|
| `PageName` | `<TitlePascal>DetailPage` (React) / `<TitlePascal>Component` (Angular) |
| `urlSlug` | `<title-kebab>` |
| target `ref` | most-recent Embed or explicit pick |
| router file | detected (show, allow override) |

If the user overrides a value, re-show the final diff and confirm again.

## Generation steps

1. Read the renderer — absent → HALT "run Embed for `{{type}}` first".
2. Read `shared/externalRefs.ts` — `{{REF_CONST}}` absent → HALT "run Embed first".
3. Page file — React `src/pages/{{type}}/{{PageName}}.tsx` from
   `assets/react/DetailPage.tsx`; Angular `src/pages/{{type}}/{{PageName}}.component.ts`
   from `assets/angular/DetailPage.component.ts` (token sub). Not present → write;
   present+differs → HALT; present+matches → no-op.
4. Insert the route (below).
5. Verify: report file path, route entry, slug. No typecheck/build.

## Router marker block

Pasted once by hand, exactly once per file:

**React** — inside `<Routes>` (react-router v6) OR a `RouteObject[]` literal:

```tsx
{/* <experience-cms-content-render:detail-routes-begin> */}
{/* <experience-cms-content-render:detail-routes-end> */}
```

**Angular** — inside the `Routes` array literal (e.g. `app.routes.ts`):

```ts
// <experience-cms-content-render:detail-routes-begin>
// <experience-cms-content-render:detail-routes-end>
```

**Detection:** grep candidates for the begin/end pair — React (`App.tsx`,
`routes.tsx`, `router.tsx`, `main.tsx`), Angular (`app.routes.ts`, `app.config.ts`,
`app-routing.module.ts`). Exactly one → use it. Multiple → HALT (list them). Zero →
HALT with the snippet to paste.

## Route insertion

Insert inside the block, above `:end`. Append-only, idempotent, collision-safe:

- React JSX: `<Route path="{{urlSlug}}" element={<{{PageName}} />} />`
- React data-router: `{ path: '{{urlSlug}}', element: <{{PageName}} /> },`
- Angular: `{ path: '{{urlSlug}}', component: {{PageName}} },` (lazy:
  `{ path: '{{urlSlug}}', loadComponent: () => import('./pages/{{type}}/{{PageName}}.component').then(m => m.{{PageName}}) },`)

Ensure `{{PageName}}` is imported (path recomputed per project); skip if already
imported. If the slug already routes to a DIFFERENT component → HALT (slug
collision). If it routes to `{{PageName}}` already → no-op.

## Non-goals

Static slugs only (dynamic `:id`/route params → future WI). Generated page is a
thin wrapper (one renderer, `layout="detail"`); customize in the renderer. No route
guards — user hand-wraps outside the marker block.
