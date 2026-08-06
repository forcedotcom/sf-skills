---
name: experience-ui-bundle-performance-optimize
description: "MUST activate when a UI bundle build prints chunk-size warnings (\"Some chunks are larger than 500 kB\"), when the user mentions slow load, bundle size, code splitting, lazy loading, re-render, or Core Web Vitals for an app under uiBundles/*/src/, or when auditing frontend performance of a React UI bundle. Use this skill to measure bundle output, split oversized chunks, lazy-load routes, and fix render waste. Do NOT use for visual/styling changes (use experience-ui-bundle-frontend-generate), for creating new apps (use experience-ui-bundle-app-coordinate), or for Apex/server performance (use platform-apex-logs-debug)."
compatibility: UI Bundle React template (Vite 5+, React 18/19, react-router 7)
metadata:
  version: "1.0"
  relatedSkills: experience-ui-bundle-frontend-generate, experience-ui-bundle-app-coordinate, experience-ui-bundle-deploy
---

# UI Bundle Performance Optimization

Measure first, then optimize. Every change in this skill is driven by build output and verified by rebuilding — never apply techniques speculatively.

UI bundles run inside the Salesforce platform, so first-load JavaScript is the dominant cost: the bundle is fetched through the org's CDN/proxy and shares the page with platform chrome. A default template app that imports charts, Radix primitives, and all pages eagerly ships a single ~1.1 MB entry chunk (~326 kB gzip). The workflow below reduced that entry to ~50 kB (16 kB gzip) in the sample Property Management app with two localized changes.

## Workflow

1. **Measure** — build and read the chunk report (or run `scripts/analyze-bundle.mjs`).
2. **Split routes** — lazy-load every non-index page with `React.lazy`.
3. **Split vendors** — separate rarely-changing dependencies with `manualChunks`.
4. **Fix render waste** — only if the user reports interaction jank, not by default.
5. **Verify** — rebuild, compare the report, and click through the app in dev/preview.

---

## 1. Measure the Current Bundle

```bash
npm run build
```

Read the `dist/assets/*.js` lines Vite prints. Or run the bundled analyzer for budgets and JSON output:

```bash
node <skill-dir>/scripts/analyze-bundle.mjs <app-dir>/dist
```

Budgets (raw, minified — not gzip):

| Asset | Budget | Action when exceeded |
|---|---|---|
| Entry chunk (`index-*.js`) | ≤ 300 kB | Split routes (§2), then vendors (§3) |
| Any single chunk | ≤ 500 kB | Split that chunk's largest dependency |
| Route (lazy) chunk | ≤ 100 kB | Move heavy deps inside the page behind `lazy` |
| CSS total | ≤ 150 kB | Check Tailwind content globs; purge unused |

If the entry chunk is already within budget, stop — report the numbers and make no changes.

## 2. Route-Level Code Splitting

`routes.tsx` is the single routing source of truth in this template. Convert every page except the index route and `NotFound` to `React.lazy`:

```tsx
import { lazy, Suspense } from 'react';
import AppLayout from './appLayout';
import Home from './pages/Home';          // eager: first paint
import NotFound from './pages/NotFound';  // eager: tiny, avoids flash on bad URLs

const PropertySearch = lazy(() => import('./pages/PropertySearch'));

const suspend = (el: React.ReactNode) => <Suspense fallback={null}>{el}</Suspense>;

// in the RouteObject tree:
{ path: 'properties', element: suspend(<PropertySearch />), handle: { showInNavigation: true, label: 'Properties' } }
```

Rules:

- Keep the index route eager — lazy-loading it delays first paint instead of improving it.
- Keep `handle` metadata exactly as-is; navigation in `appLayout.tsx` is generated from it.
- Use `fallback={null}` or a lightweight skeleton — never a spinner that flashes on fast networks.
- Do not lazy-load `appLayout.tsx`; it wraps every route.
- Each page becomes its own chunk (typically 9–16 kB in this template) fetched on first navigation.

## 3. Vendor Chunking with `manualChunks`

In `vite.config.ts`, add `rollupOptions.output.manualChunks` inside the existing `build` block. Match specific packages before generic ones:

```ts
build: {
  // ...existing outDir/assetsDir/sourcemap...
  rollupOptions: {
    output: {
      manualChunks(id) {
        if (!id.includes('node_modules')) return;
        if (id.includes('recharts') || id.includes('d3-')) return 'charts';
        if (id.includes('radix-ui')) return 'radix';
        if (id.includes('lucide-react')) return 'icons';     // BEFORE the react check
        if (id.includes('react-router')) return 'router';
        if (id.includes('react')) return 'react';
        return 'vendor';
      },
    },
  },
},
```

**Pitfall — substring matching:** `id.includes('react')` also matches `lucide-react`, `react-day-picker`, and anything else with "react" in its path. Match the specific packages *first* (as above) or the react chunk silently absorbs them and stays oversized. After any `manualChunks` change, confirm chunk contents shifted the way you expected — sizes in the build report are the evidence.

Why vendor splitting matters even when total bytes stay the same: vendor chunks change rarely, so their hashed filenames survive app-code deploys and stay in the browser cache; and heavy optional deps (charts) stop blocking pages that never render a chart.

## 4. Render Waste (only when interaction is slow)

Apply only with a reported symptom (typing lag, slow list scroll, sluggish tab switch):

- Wrap list-row components in `React.memo` when a parent re-renders frequently with unchanged row props.
- Hoist object/array literals and inline handlers out of JSX in hot paths (`useMemo`/`useCallback`) — but only where profiling shows re-renders, otherwise it is noise.
- Paginate or virtualize lists over ~200 rows; this template already ships `PaginationControls` — prefer it over rendering full result sets.
- Debounce search inputs that fire a GraphQL query per keystroke (300 ms is a good default).
- Never fetch in a component body; keep data access in the existing hooks/api layer so React Query-style caching (or memoized hooks) prevents duplicate requests.

Diagnose with React DevTools Profiler (in dev mode) before changing code; state the suspected wasteful component and confirm it in the flame graph.

## 5. Verify

1. `npm run build` — compare against the §1 baseline. Expect: entry chunk sharply smaller, one chunk per lazy page, named vendor chunks, and no Vite size warning.
2. Run the analyzer again — it exits non-zero if any budget is still exceeded.
3. `npm run dev` (or `npm run preview` for the built output) and click every navigation entry. Watch the network panel: each first visit to a lazy route should fetch exactly that route's chunk, and revisits should fetch nothing.
4. `npm test` if the project has tests; route conversion to `lazy` must not change rendered output.

Report to the user: before/after entry size, chunk count, and which techniques were applied. Example from the sample Property Management app:

| | Before | After (§2 + §3) |
|---|---|---|
| Entry chunk | 1,104.74 kB (326 kB gzip) | 50.21 kB (16.3 kB gzip) |
| Route chunks | none (all eager) | 9–16 kB each, loaded on navigation |
| Vendor chunks | none | react / router / radix / charts, cached across deploys |
| Vite size warning | yes | no |

## Boundaries

- **Do not** enable `sourcemap: true` in production builds to "measure" — use the build report or the analyzer script.
- **Do not** remove or rename the existing `outDir`/`assetsDir`/`base: './'` settings; deployment (`experience-ui-bundle-deploy`) depends on them.
- **Do not** replace the GraphQL data layer, router, or component library in the name of performance — that is a rewrite, not an optimization; confirm scope with the user first.
- Salesforce org latency (GraphQL 401s locally, API response times) is not addressable from the bundle; direct data-layer concerns to `experience-ui-bundle-salesforce-data-access`.
