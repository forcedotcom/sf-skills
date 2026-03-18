---
name: salesforce-webapp-creating-webapp
description: Core web application rules for SFDX React apps
paths:
  - "**/webapplications/**/*"
---

# Skills-First (MUST FOLLOW)

**Before writing any code or running any command**, search for relevant skills (`SKILL.md` files) that cover your task. Read the full skill and follow its instructions. Skills live in `.a4drules/skills/` and `feature/*/skills/`. See **webapp-skills-first.md** for the full protocol and a task-to-skill lookup table.

# Web App Generation

## Before `sf webapp generate`

**Webapp name (`-n`):** Must be **alphanumerical only**—no spaces, hyphens, underscores, or special characters. Use only letters (A–Z, a–z) and digits (0–9). Example: `CoffeeBoutique` not `Coffee Boutique`.

```bash
sf webapp generate -n MyWebApp -t reactbasic
```

Do not use `create-react-app`, Vite, or other generic scaffolds; use `sf webapp generate` so the app is SFDX-aware.

## After Generation (MANDATORY)

After generating or when touching an existing app:

1. **Replace all default boilerplate** — "React App", "Vite + React", default `<title>`, placeholder text in shell. Use the actual app name.
2. **Populate the home page** — Never leave it as default template. Add real content: landing section, banners, hero, navigation to features.
3. **Update navigation and placeholders** — See [Navigation & Layout section](#navigation--layout-mandatory) below.

# Navigation & Layout (MANDATORY)

Agents consistently miss these. **You must not leave them default.**

## appLayout.tsx is the Source of Truth

- **Build navigation into the app layout** (`appLayout.tsx`). The layout must include nav (header, sidebar, or both) so every page shares the same shell.
- Path: `force-app/main/default/webapplications/<appName>/src/appLayout.tsx`

## When Making UI Changes

**When making any change** that affects navigation, header, footer, sidebar, theme, or overall layout:

1. **You MUST edit `src/appLayout.tsx`** (the layout used by `routes.tsx`).
2. Do not only edit pages/components and leave `appLayout.tsx` unchanged.
3. Before finishing: confirm you opened and modified `appLayout.tsx`. If you did not, the task is incomplete.

## Navigation Menu (Critical)

- **Always edit the navigation menu** in `appLayout.tsx`. Replace default nav items and labels with **app-specific** links and names.
- Do **not** leave template items (e.g. "Home", "About", generic placeholder links).
- Use real routes and labels matching the app (e.g. "Dashboard", "Products", "Orders").

**Check before finishing:** Did I change the nav items and labels to match this app?

## Placeholder Name & Design (Critical)

- **Replace the placeholder app name** everywhere: header, nav brand/logo, footer, `<title>` in `index.html`, any "Welcome to…" text.
- **Replace placeholder design** in the shell: default header/footer styling, generic branding.

**Check before finishing:** Is the app name and shell design still the template default? If yes, update it.

## Where to Edit


| What                | Where                                                                |
| ------------------- | -------------------------------------------------------------------- |
| Layout/nav/branding | `force-app/main/default/webapplications/<appName>/src/appLayout.tsx` |
| Document title      | `force-app/main/default/webapplications/<appName>/index.html`        |
| Root page content   | Component at root route (often `Home` in `routes.tsx`)               |


# Frontend Aesthetics

**Avoid AI slop.** Make creative, distinctive frontends:

- **Typography:** Avoid Inter, Roboto, Arial, Space Grotesk as defaults. Choose distinctive fonts.
- **Color:** Use cohesive color with sharp accents via CSS variables. Avoid purple-on-white clichés.
- **Motion:** Use high-impact motion (e.g. staggered reveals).
- **Depth:** Add atmosphere/depth in backgrounds.

# Shell Command Safety (MUST FOLLOW)

**Never use complex `node -e` one-liners** for file edits or multi-line transforms. They break in Zsh due to `!` history expansion and backtick interpolation. Use a temporary `.js` file, `sed`/`awk`, `jq`, or IDE file-editing tools instead.

# Development Cycle

- Execute tasks continuously until all planned items complete in the current iteration.
- Maintain a running checklist and proceed sequentially.

## Stop Conditions

Only stop when:

- All checklist items are completed and quality gates pass, or
- A blocking error cannot be resolved after reasonable remediation, or
- The user explicitly asks to pause.

