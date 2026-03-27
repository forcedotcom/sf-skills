---
name: generating-webapplication-ui
description: "Build and modify React UI for Salesforce web applications — pages, components, layout, navigation, and headers/footers. Use whenever creating or editing TSX/JSX files or making visual/layout changes. Triggers on: add page, add component, header, footer, navigation, layout, styling, Tailwind, shadcn, React component, appLayout."
---

# Web Application UI

## Identify the Task

Determine which category the request falls into:

| Category | Examples | Implementation Guide |
|----------|----------|---------------------|
| **Page** | New routed page (contacts, dashboard, settings) | `implementation/page.md` |
| **Header / Footer** | Site-wide nav bar, footer, branding | `implementation/header-footer.md` |
| **Component** | Widget, card, table, form, dialog | `implementation/component.md` |

---

## Layout and Navigation

`appLayout.tsx` is the source of truth for navigation and layout. Every page shares this shell.

When making any change that affects navigation, header, footer, sidebar, theme, or layout:

1. Edit `src/appLayout.tsx` — the layout used by `routes.tsx`
2. Replace all default/template nav items and labels with app-specific links and names
3. Replace placeholder app name everywhere: header, nav brand, footer, `<title>` in `index.html`

Before finishing, confirm: Did I update `appLayout.tsx` with real nav items and branding?

| What | Where |
|------|-------|
| Layout, nav, branding | `src/appLayout.tsx` |
| Document title | `index.html` |
| Root page content | Component at root route in `routes.tsx` |

---

## React and TypeScript Standards

### Routing

Use a single router package. With `createBrowserRouter` / `RouterProvider`, all imports must come from `react-router` (not `react-router-dom`).

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

React apps must not import Salesforce platform modules like `lightning/*` or `@wire` (LWC-only). For data access, use the `using-webapplication-salesforce-data` skill.

---

## Design Thinking

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

Before completing, run lint and build from the web application directory. Lint must result in 0 errors and build must succeed.
