# experience-ui-bundle-performance-optimize

Frontend performance auditing and optimization skill for Salesforce React UI Bundles. Measures Vite build output against size budgets, then applies route-level code splitting and vendor chunking to cut first-load JavaScript — without touching data layer, routing structure, or visual design.

## Features

- **Bundle Measurement**: Reads Vite's build report (or runs the bundled analyzer) against explicit size budgets for entry chunks, individual chunks, route chunks, and CSS
- **Route-Level Code Splitting**: Converts eager page imports in `routes.tsx` to `React.lazy`, so each page ships its own chunk fetched on first navigation
- **Vendor Chunking**: Configures `manualChunks` in `vite.config.ts` to separate rarely-changing dependencies (React, router, UI primitives, charts) into their own cacheable chunks
- **Render-Waste Diagnosis**: Guidance for `memo`/`useMemo`/debouncing/virtualization — applied only against a reported symptom, not speculatively
- **Verification Workflow**: Rebuild, re-measure, and click through every navigation entry to confirm lazy chunks load correctly

## Quick Start

### 1. Invoke the skill

```
Skill: experience-ui-bundle-performance-optimize
Request: "This UI bundle's build is throwing a chunk-size warning, can you fix it?"
```

The skill also self-activates when a build prints Vite's `"Some chunks are larger than 500 kB"` warning, or when the user mentions slow load, bundle size, code splitting, or Core Web Vitals for a project under `uiBundles/*/src/`.

### 2. Run the analyzer directly

```bash
node skills/experience-ui-bundle-performance-optimize/scripts/analyze-bundle.mjs <app-dir>/dist
```

Add `--json` for machine-readable output. Exits `0` when every budget passes, `1` when any budget is exceeded (suitable for CI gating), `2` on usage/IO errors.

### 3. Typical use cases

- Diagnose why a UI bundle's `npm run build` prints a chunk-size warning
- Reduce first-load JavaScript before deploying a UI bundle to an org
- Add code splitting to a UI bundle app that has grown past its initial page set
- Investigate reported UI sluggishness (typing lag, slow list scroll, tab-switch delay)

## Results on the Reference Sample

Applied to `samples/ui-bundle-template-app-react-sample-b2e` (Property Management app):

| | Before | After |
|---|---|---|
| Entry chunk | 1,104.74 kB (326.44 kB gzip) | 50.21 kB (16.28 kB gzip) |
| Route chunks | none — all pages eager | 4 chunks, 9–16 kB each, loaded on navigation |
| Vendor chunks | none | `react`, `router`, `radix`, `charts` — cacheable across deploys |
| Vite size warning | yes | no |

Verified at runtime: the home route renders correctly, and navigating to each page fetches exactly that page's lazy chunk (confirmed via network trace), nothing more.

## Documentation

- [SKILL.md](SKILL.md) — full workflow: measure → split routes → split vendors → fix render waste → verify, with size budgets and template-specific rules
- [scripts/analyze-bundle.mjs](scripts/analyze-bundle.mjs) — standalone budget checker for `dist/` output

## Boundaries

- Does not touch the GraphQL data layer, router library, or component library — that is a rewrite, not an optimization
- Does not enable production sourcemaps to "measure" — uses the build report or the analyzer instead
- Does not change `outDir`, `assetsDir`, or `base` in `vite.config.ts` — those are relied on by deployment

## Related Skills

- `experience-ui-bundle-frontend-generate` — for visual/styling changes to an existing UI bundle app
- `experience-ui-bundle-app-coordinate` — for building a new UI bundle app from scratch
- `experience-ui-bundle-deploy` — for deploying the optimized bundle to a Salesforce org
- `experience-ui-bundle-salesforce-data-access` — for GraphQL/data-layer concerns (org latency, query shape) that this skill does not address
