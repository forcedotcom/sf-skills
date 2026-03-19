---
name: building-webapp-react-components
description: Use when editing any React code in the web application — creating or modifying components, pages, layout, headers, footers, or any TSX/JSX files. Follow this skill for add component, add page, header/footer, and general React UI implementation patterns (shadcn UI and Tailwind CSS).
---

# React Web App (Components, Pages, Layout)

Use this skill whenever you are editing React/TSX code in the web app (creating or modifying components, pages, header/footer, or layout).

## Step 1 — Identify the type of component

Determine which of these three categories the request falls into, then follow the corresponding section below:

- **Page** — user wants a new routed page (e.g. "add a contacts page", "create a dashboard page", "add a settings section")
- **Header / Footer** — user wants a site-wide header, footer, nav bar, or page footer that appears on every page
- **Component** — everything else: a widget, card, table, form, dialog, or other UI element placed within an existing page

If it is not immediately clear from the user's message, ask:

> "Are you looking to add a new page, a site-wide header or footer, or a component within an existing page?"

Then follow the matching section.

---

## Clarifying Questions

Ask **one question at a time** and wait for the response before asking the next. Stop when you have enough to build accurately — do not guess or assume.

### For a Page

1. **What is the name and purpose of the page?** (e.g., Contacts, Dashboard, Settings)
2. **What URL path should it use?** (e.g., `/contacts`, `/dashboard`) — or derive from the page name?
3. **Should the page appear in the navigation menu?**
4. **Who can access it?** Public, authenticated users only (`PrivateRoute`), or unauthenticated only (e.g., login — `AuthenticationRoute`)?
5. **What content or sections should the page include?** (list, form, table, detail view, etc.)
6. **Does it need to fetch any data?** If so, from where?

### For a Header / Footer

1. **Header, footer, or both?**
2. **What should the header contain?** (logo/app name, nav links, user avatar, CTA button, etc.)
3. **What should the footer contain?** (copyright text, links, social icons, etc.)
4. **Should the header be sticky (fixed to top while scrolling)?**
5. **Is there a logo or brand name to display?** (or placeholder?)
6. **Any specific color scheme or style direction?** (dark background, branded primary color, minimal, etc.)
7. **Should navigation links appear in the header?** If so, which pages?

### For a Component

1. **What should the component do?** (display data, accept input, trigger an action, etc.)
2. **What page or location should it appear on?**
3. **Is this shared/reusable across pages, or specific to one feature?** (determines file location)
4. **What data or props does it need?** (static content, props, fetched data)
5. **Does it need internal state?** (loading, toggle, form state, etc.)
6. **Are there any specific shadcn components to use?** (Card, Table, Dialog, Form, etc.)
7. **Should it appear in a specific layout position?** (full-width, sidebar, inline, etc.)

---

## Implementation

Once you have identified the type and gathered answers to the clarifying questions, read and follow the corresponding implementation guide:

- **Page** — read `implementation/page.md` and follow the instructions there.
- **Header / Footer** — read `implementation/header-footer.md` and follow the instructions there.
- **Component** — read `implementation/component.md` and follow the instructions there.

---

## TypeScript Standards

- **Never use `any`** — use proper types, generics, or `unknown` with type guards.
- **Event handlers:** `(event: React.FormEvent<HTMLFormElement>): void`
- **State:** `useState<User | null>(null)` — always provide the type parameter.
- **No unsafe assertions** (`obj as User`). Use type guards:
  ```typescript
  function isUser(obj: unknown): obj is User {
    return typeof obj === 'object' && obj !== null && typeof (obj as User).id === 'string';
  }
  ```

---

## Verification (MANDATORY)

Before completing, run from the web app directory `force-app/main/default/webapplications/<appName>/`:

```bash
cd force-app/main/default/webapplications/<appName> && npm run lint && npm run build
```

- **Lint:** MUST result in 0 errors.
- **Build:** MUST succeed (includes TypeScript check).

If either fails, fix the errors and re-run. Do not leave the session with failing quality gates.
