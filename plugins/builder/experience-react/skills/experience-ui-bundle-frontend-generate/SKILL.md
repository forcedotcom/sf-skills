---
name: experience-ui-bundle-frontend-generate
description: "MUST activate before editing ANY file under uiBundles/*/src/ (or the bundle's index.html) for visual or UI changes to an EXISTING app — pages, components, sections, layout, styling, colors, fonts, navigation, animations, branding, or any look-and-feel change. Use this skill when modifying pages, components, layout, styling, navigation, or branding in an existing UI bundle app. Activate when the project contains appLayout.tsx, routes.tsx, src/pages/, src/components/, src/styles/global.css, or the bundle's index.html. This skill contains critical project-specific conventions (appLayout.tsx shell, shadcn/ui components, Tailwind CSS, Salesforce base-path routing, module restrictions) that override general knowledge. Without this skill, generated code will use wrong imports, break routing, or ignore project structure. Do NOT use when creating a new app from scratch or the bundle has not been scaffolded yet (use experience-ui-bundle-app-coordinate instead)."
metadata:
  version: "1.1"
  domains: ["Experience"]
  relatedSkills:
    - "experience-ui-bundle-app-coordinate"
    - "experience-ui-bundle-features-generate"
    - "experience-ui-bundle-metadata-generate"
    - "experience-ui-bundle-salesforce-data-access"
  cliTools:
    - tool: ["npm"]
      semver: ">=8.0.0"
    - tool: ["npx"]
      semver: ">=8.0.0"
    - tool: ["python3"]
      semver: ">=3.10.0"
---

# UI Bundle UI

## Resolve the Bundle Directory

**MUST** run `scripts/resolve-ui-bundle.sh [project-root]` before applying any rule below or writing any file — an ad-hoc `find`/`ls` is not a substitute; it does not enforce the exit-code gate below. It reads `sfdx-project.json`'s `packageDirectories[0].path` (does not assume `force-app` — the source path is configurable) and looks under `<sourceDir>/main/default/uiBundles/`:

- **Exit 0**, bundle path printed to stdout: exactly one bundle directory found — that is the bundle directory. Use that exact directory name; never substitute a different name (e.g. a generic "AcmePortal" example from a prompt template) for the one actually printed.
- **Exit 2**, candidates printed to stderr: multiple `uiBundles/*` subdirectories exist — do not guess, and do not write to any of them, or to a bundle name not in the printed list. Ask the user which app/bundle they mean before editing or running any command.
- **Exit 1**: `sfdx-project.json` missing/invalid, or no bundle directory found at all.

Run all `npm`/lint/build/dev commands from inside the resolved bundle directory, never from the project root.

## Preconditions

Before applying any rule below, confirm this is an existing, scaffolded UI bundle: **MUST** run `scripts/check-preconditions.sh <bundle-dir>` with the directory `resolve-ui-bundle.sh` printed.

- **Single-bundle (exit 0) case**: run it once, on that bundle.
- **Multi-bundle (exit 2) case**: do not run it yet — first ask the user which app/bundle they mean, per the Resolve step above. Once the user names the bundle, run `check-preconditions.sh` on that one bundle only. Never run it against multiple candidates speculatively before the user has chosen — that means touching/inspecting bundles the user didn't ask about.
- **Exit 0**: the bundle has `src/appLayout.tsx`, `src/routes.tsx`, and `src/components/ui/` — proceed.
- **Exit 1**, missing pieces listed: this is a fresh SFDX project, a non-UI-bundle React project, or a partially-scaffolded bundle — **stop**. Do not fall back to generic React knowledge (e.g. `react-router-dom`, a hardcoded basename, or raw HTML), and do not hand-write `appLayout.tsx`/`routes.tsx`/a page/a component to "fill in" the missing scaffold, even for a casual, vague, or urgent-sounding request ("just change the header", "make the background blue"). Tell the user the bundle isn't scaffolded yet and direct them to `experience-ui-bundle-app-coordinate` (or `experience-ui-bundle-metadata-generate`) to scaffold it first. If, after the user names their intended bundle, that one turns out to be unscaffolded, stop and redirect for it — do not silently switch to scaffolding a different candidate instead.

Never invent, assume, or fall back to a bundle name that doesn't appear in the actual `<sourceDir>/main/default/uiBundles/` listing on disk — including a name that only appears as example/template text elsewhere (a prompt, a directive, prior conversation). If what's on disk doesn't match that example, disk wins.

## Identify the Task

Determine which category the request falls into:

| Category | Examples | Implementation Guide |
|----------|----------|---------------------|
| **Page** | New routed page (contacts, dashboard, settings) | `references/page.md` |
| **Header / Footer** | Site-wide nav bar, footer, branding, renaming the app | `references/header-footer.md` |
| **Component** | Widget, card, table, form, dialog | `references/component.md` |

A request to rename/rebrand the app (e.g. "call it X everywhere a user would see it") is a **Header / Footer** task even though it doesn't mention "header" by name — it always touches at least two files: `src/appLayout.tsx` (header/nav brand text) AND `index.html`'s `<title>` (browser tab title). Treat these as one atomic change; a rename that only updates one of the two is incomplete.

---

## Pre-built Features (Check Before Hand-Building)

Some capabilities ship as pre-built, tested feature packages. The catalog **evolves and is not something you can know from memory** — never decide from the request wording alone whether a capability "is" or "isn't" a feature. Before hand-writing any non-trivial capability (anything beyond a plain page, component, or styling change) in this skill:

1. **Consult the authoritative catalog.** Invoke `experience-ui-bundle-features-generate`, which runs `list` to show the *current* set of installable features. Do not rely on a hardcoded or remembered list — this skill deliberately names none, because any names it listed would go stale.
2. **Detect whether a matching feature is already installed** in the bundle — inspect `package.json` dependencies and existing `src/` files. If present, use it as-is; do not reinstall or re-implement.
3. **If a matching feature exists in the catalog but isn't installed**, let `experience-ui-bundle-features-generate` install the tested package. Do not build it from scratch here.
4. **Only hand-build** a capability that has no matching catalog feature.

This gate is **idempotent**: when this skill runs as a phase of `experience-ui-bundle-app-coordinate` (which installs features earlier in its sequence), step 2 finds the feature already present and this collapses to a no-op. It only does real work when the skill was reached directly — the path that would otherwise skip feature detection.

---

## Layout and Navigation

`appLayout.tsx` is the source of truth for navigation and layout. Every page shares this shell.

When making any change that affects navigation, header, footer, sidebar, theme, or layout:

1. Edit `src/appLayout.tsx` — the layout used by `routes.tsx`
2. Replace all default/template nav items and labels with app-specific links and names
3. Replace placeholder app name everywhere: header, nav brand, footer, `<title>` in `index.html`

`index.html` lives at the bundle root (not under `src/`), but it is still in scope for this skill whenever branding or the app name changes — the leftover `<title>React App</title>` / `Vite + React` boilerplate is a common ship-blocker that `npm run lint`/`npm run build` never catches.

Before finishing, confirm: Did I update `appLayout.tsx` with real nav items and branding? Then run `scripts/verify-rules.sh` to check for residual boilerplate (see Verification below).

| What | Where |
|------|-------|
| Layout, nav, branding | `src/appLayout.tsx` |
| Document title | `index.html` (bundle root, outside `src/` — still in scope for branding) |
| Root page content | Component at root route in `routes.tsx` |

---

## React and TypeScript Standards

### Routing

Use a single router package. With `createBrowserRouter` / `RouterProvider`, all imports must come from `react-router` (not `react-router-dom`).

If the app uses a client-side router (React Router, Remix Router, Vue Router, etc.), always derive basename / basepath / base from the document's `<base href>` tag at runtime. Never hardcode the basename:

```js
const basename = document.querySelector('base')
  ? new URL(document.querySelector('base').href).pathname.replace(/\/$/, '')
  : '/';
const router = createBrowserRouter(routes, { basename });
```

### Component Library and Styling

- **shadcn/ui** for components: `import { Button } from '@/components/ui/button';`
- **Tailwind CSS** utility classes

### URL and Path Handling

Apps run behind dynamic base paths. Router navigation (`<Link to>`, `navigate()`) uses absolute paths (`/x`). Non-router attributes (`<img src>`) use dot-relative (`./x`). Prefer Vite `import` for static assets.

### TypeScript

- Never use `any` — use proper types, generics, or `unknown` with type guards
- Event handlers: `(event: React.FormEvent<HTMLFormElement>): void`
- State: `useState<User | null>(null)` — always provide the type parameter
- No unsafe assertions (`obj as User`) — use type guards instead

### Module Restrictions

React UI bundles must not import Salesforce platform modules like `lightning/*` or `@wire` (LWC-only). **Before writing any data-access code (GraphQL, REST, SDK initialization, or a hook that fetches data), you MUST invoke the `experience-ui-bundle-salesforce-data-access` skill first.** Do not write `fetch`/`axios` calls or invent a different data API inline in this skill — this applies even if the clarifying-question answer only implies data fetching in passing.

---

## Design Thinking

The rules in this section and "Frontend Aesthetics" below are creative direction, not hard constraints — they cannot be lint- or build-checked and are judged by review, not automation. Two hard, checkable exceptions: never default to Inter/Roboto/Arial/Space Grotesk/system fonts, and mobile responsiveness (Tailwind breakpoints, 44px touch targets) is a MUST, not a style preference.

Before coding, commit to a bold aesthetic direction:

- **Purpose:** What problem does this interface solve? Who uses it?
- **Tone:** Pick a clear direction — brutally minimal, maximalist, retro-futuristic, organic, luxury, playful, editorial, brutalist, art deco, soft/pastel, industrial. Use these as inspiration but design one true to the context.
- **Differentiation:** What makes this unforgettable? What's the one thing someone will remember?

Choose a clear conceptual direction and execute it with precision. Bold maximalism and refined minimalism both work — the key is intentionality, not intensity.

---

## Frontend Aesthetics

- **Typography:** Choose distinctive, characterful fonts. Pair a display font with a refined body font. Never default to Inter, Roboto, Arial, Space Grotesk, or system fonts.
- **Color:** Commit to a cohesive palette using CSS variables. Dominant colors with sharp accents outperform timid, evenly-distributed palettes. Avoid cliched purple gradients on white.
- **Motion:** Focus on high-impact moments — one well-orchestrated page load with staggered reveals (`animation-delay`) creates more delight than scattered micro-interactions. Use scroll-triggering and hover states that surprise. Prefer CSS-only solutions; use Motion library for React when available.
- **Spatial Composition:** Unexpected layouts — asymmetry, overlap, diagonal flow, grid-breaking elements. Generous negative space OR controlled density.
- **Backgrounds & Depth:** Create atmosphere rather than defaulting to solid colors. Gradient meshes, noise textures, geometric patterns, layered transparencies, dramatic shadows, decorative borders, grain overlays.

- **Mobile Responsiveness:** All generated UI MUST be mobile-responsive. Use Tailwind responsive prefixes (`sm:`, `md:`, `lg:`) to adapt layouts across breakpoints. Stack columns on small screens, use flexible grids, and ensure touch targets are at least 44px. Test that navigation, typography, and spacing work on mobile viewports.

Match implementation complexity to the aesthetic vision. Maximalist designs need elaborate animations and effects. Minimalist designs need restraint, precision, and careful spacing/typography. No two designs should look the same — vary themes, fonts, and aesthetics across generations.

---

## Clarifying Questions

Ask one question at a time and stop when you have enough context.

### For a Page
1. Name and purpose?
2. URL path?
3. Should it appear in navigation?
4. Access control? (public, authenticated via `PrivateRoute`, or unauthenticated via `AuthenticationRoute`)
5. Content sections? (list, form, table, detail view)
6. Data fetching needs?

### For a Header / Footer
1. Header, footer, or both?
2. Contents? (logo, nav links, user avatar, copyright, social icons)
3. Sticky header?
4. Color scheme or style direction?

### For a Component
1. What should it do?
2. Which page does it belong to?
3. Shared/reusable or specific to one feature?
4. Data or props needed?
5. Internal state? (loading, toggle, form state)
6. Specific shadcn components to use?

---

## Verification

Before completing, run all of the following from the resolved UI bundle directory (see "Resolve the Bundle Directory" above):

1. `npm run lint` — must result in 0 errors.
2. `npm run build` — must succeed.
3. `npm run dev` (or the project's dev-server script) — confirm the app starts cleanly so the change is verified at runtime, not just at build time.

**`lint`/`build` alone do not catch the highest-risk rules in this skill** — a wrong `react-router-dom` import, a hardcoded basename, an inline `style={{}}`, or a stray `lightning/*` import can all lint and build clean while breaking at runtime. After any change that touches routing, layout, styling, or module imports, run `scripts/verify-rules.sh <files-or-dirs-you-edited>`:

- **Exit 0**: no violations found.
- **Exit 1**, violations listed by rule and file: fix every one before considering the task complete, even if lint and build passed.
