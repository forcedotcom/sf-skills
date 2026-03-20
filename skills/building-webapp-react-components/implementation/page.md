# Implementation — Page

### Rules

1. **Edit the component that owns the UI, never output raw HTML** — When editing the home page or any page content, modify the actual `.tsx` file that renders the target. If the target is inside a child component (e.g. `<GlobalSearchInput />` in `Home.tsx`), edit the child's file (e.g. `GlobalSearchInput.tsx`), not the parent. Do not wrap the component with extra elements in the parent; go into the component and change its JSX. Do not paste or generate raw HTML.
2. **`routes.tsx` is the only route registry** — never add routes in `app.tsx` or inside page files.
3. **All pages are children of the AppLayout route** — do not create top-level routes that bypass the layout shell.
4. **Default export per page** — each page file has exactly one default-export component.
5. **Path aliases in all imports** — use `@/pages/...`, `@/components/...`; no deep relative paths.
6. **No inline styles** — Tailwind utility classes and design tokens only.
7. **Catch-all last** — `path: '*'` (NotFound) must always remain the last child in the layout route.
8. **Never modify `appLayout.tsx`** when adding a page — layout changes are a separate concern.

### Step 1 — Create the page file

Create `src/pages/MyPage.tsx` with a **default export** and the standard page container:

```tsx
export default function MyPage() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <h1 className="text-3xl font-bold text-foreground">My Page</h1>
      <p className="mt-4 text-muted-foreground">Page content goes here.</p>
    </div>
  );
}
```

Use shadcn components from `@/components/ui` for UI elements. All styling via Tailwind — no inline `style={{}}`.

### Step 2 — Register the route in `routes.tsx`

Open `src/routes.tsx`. Import the page and add it inside the layout route's `children` array:

```tsx
import MyPage from "@/pages/MyPage";

// Inside the layout route's children array (before the catch-all):
{
  path: "my-page",
  element: <MyPage />,
  handle: { showInNavigation: true, label: "My Page" },
},
```

- `path` is a **relative segment** (e.g., `"contacts"`), not an absolute path.
- Include `handle: { showInNavigation: true, label: "Label" }` only if the page should appear in the navigation menu.
- The catch-all `path: '*'` must stay **last**.

### Step 3 — Apply an auth guard (if needed)

| Access type                        | Guard                   | Behavior                                |
| ---------------------------------- | ----------------------- | --------------------------------------- |
| Public                             | None                    | Direct child of layout                  |
| Authenticated only                 | `<PrivateRoute>`        | Redirects to login if not authenticated |
| Unauthenticated only (e.g., login) | `<AuthenticationRoute>` | Redirects away if already authenticated |

Example — private page:

```tsx
import { PrivateRoute } from "@/components/auth/private-route";

{
  path: "settings",
  element: <PrivateRoute><SettingsPage /></PrivateRoute>,
  handle: { showInNavigation: true, label: "Settings" },
},
```

Use `ROUTES.*` constants from `@/utils/authenticationConfig` for auth-related paths — do not hardcode `/login`, `/profile`, etc.

### File Conventions — Page

| Concern           | Location                                               |
| ----------------- | ------------------------------------------------------ |
| Page component    | `src/pages/<PageName>.tsx` (default export)            |
| Route definition  | `src/routes.tsx` only                                  |
| Layout shell      | `src/appLayout.tsx` — do not modify for page additions |
| Auth config paths | `ROUTES.*` from `@/utils/authenticationConfig`         |

### State and Data

- **Local state:** `useState`, `useReducer`, `useRef` inside the page component
- **Shared or complex state:** extract to `src/hooks/` with a `use` prefix (e.g., `useContacts`)
- **Data fetching:** prefer GraphQL (`executeGraphQL`) or REST utilities in `src/api/`; place shared data logic in `src/hooks/`
- **Auth context:** `useAuth()` from `@/context/AuthContext` when current user is needed — only valid under `AuthProvider`

### Confirm — Page

- The page renders inside the app shell (header/nav visible)
- If `showInNavigation: true`, the link appears in the navigation menu
- No TypeScript errors; no broken imports; no missing exports
- Imports use path aliases (`@/`, not deep relative paths)
