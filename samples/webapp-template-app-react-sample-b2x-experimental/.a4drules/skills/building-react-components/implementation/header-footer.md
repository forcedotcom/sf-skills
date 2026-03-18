# Implementation — Header / Footer

### Rules

1. **Edit `appLayout.tsx` only** — header and footer are layout-level concerns. Never add them to individual page files.
2. **Never modify `routes.tsx` or `app.tsx`** — the router setup must remain intact.
3. **Create component files in `src/components/layout/`** — the designated location for layout-level components.
4. **Use the full-height flex column pattern** — wrap layout in `min-h-screen flex flex-col` so footer stays at bottom.
5. **Use shadcn and Tailwind** — compose from `@/components/ui`; style with Tailwind utility classes and design tokens.
6. **Use path aliases** — import with `@/components/layout/...` and `@/components/ui`; no deep relative paths.
7. **Preserve existing content** — if `appLayout.tsx` already has a `<NavigationMenu />` or other shell elements, keep them in place.

### Step 1 — Create the header component (if requested)

Create `src/components/layout/AppHeader.tsx`:

```tsx
import { cn } from "@/lib/utils";

interface AppHeaderProps {
  className?: string;
}

export function AppHeader({ className }: AppHeaderProps) {
  return (
    <header
      className={cn(
        "w-full border-b bg-background px-4 sm:px-6 lg:px-8 py-4",
        className,
      )}
    >
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <span className="text-lg font-semibold text-foreground">My App</span>
      </div>
    </header>
  );
}
```

### Step 2 — Create the footer component (if requested)

Create `src/components/layout/AppFooter.tsx`:

```tsx
import { cn } from "@/lib/utils";

interface AppFooterProps {
  className?: string;
}

export function AppFooter({ className }: AppFooterProps) {
  return (
    <footer
      className={cn(
        "w-full border-t bg-background px-4 sm:px-6 lg:px-8 py-4",
        className,
      )}
    >
      <div className="max-w-7xl mx-auto text-center text-sm text-muted-foreground">
        &copy; {new Date().getFullYear()} My App. All rights reserved.
      </div>
    </footer>
  );
}
```

### Step 3 — Edit `appLayout.tsx`

Open `src/appLayout.tsx` — this is the **only file to modify** for layout-level additions. Wrap existing content in a flex column and add header above and footer below `<Outlet />`:

```tsx
import { Outlet } from "react-router";
import { AppHeader } from "@/components/layout/AppHeader";
import { AppFooter } from "@/components/layout/AppFooter";
// Keep all existing imports unchanged

export default function AppLayout() {
  return (
    <div className="min-h-screen flex flex-col bg-background">
      <AppHeader />
      {/* Keep any existing NavigationMenu or other shell elements here */}
      <main className="flex-1">
        <Outlet />
      </main>
      <AppFooter />
    </div>
  );
}
```

### File Locations — Header / Footer

| Component    | File                                  | Export                         |
| ------------ | ------------------------------------- | ------------------------------ |
| Header       | `src/components/layout/AppHeader.tsx` | Named export                   |
| Footer       | `src/components/layout/AppFooter.tsx` | Named export                   |
| Layout shell | `src/appLayout.tsx`                   | Default export (edit in place) |

### Why `appLayout.tsx` — Not Pages or Routes

`AppLayout` is the single shell rendered at the root route. Every page is a child rendered via `<Outlet />`. Placing the header and footer here ensures they appear on every page without touching individual pages or the route registry.

```
AppLayout (appLayout.tsx)
├── AppHeader          ← renders on every page
├── NavigationMenu     ← keep if already present
├── <Outlet />         ← active page renders here
└── AppFooter          ← renders on every page
```

### Useful Patterns — Header / Footer

- **Sticky header:** add `sticky top-0 z-50` to the `<header>` element
- **Separator:** use `<Separator />` from `@/components/ui` instead of `border-b`/`border-t` if a visible divider is preferred
- **Nav links in header:** use `<Button variant="ghost" asChild>` wrapping a React Router `<Link>`
- **Icons:** `lucide-react`; add `aria-hidden="true"` on decorative icons
- **Design tokens:** `bg-background`, `text-foreground`, `text-muted-foreground`, `border`, `bg-primary`

### Mobile hamburger / Menu icon — Must be functional

If the header includes a hamburger or `Menu` icon for mobile:

- **Do not** add a Menu/hamburger icon that does nothing. It must toggle a visible mobile menu.
- **Required:** (1) State: `const [isOpen, setIsOpen] = useState(false)`. (2) Button: `onClick={() => setIsOpen(!isOpen)}`, `aria-label="Toggle menu"`. (3) Conditional panel: `{isOpen && ( <div>...nav links...</div> )}` with responsive visibility (e.g. `md:hidden`). (4) Close on navigate: each link in the panel should `onClick={() => setIsOpen(false)}`.
- Implement in `appLayout.tsx` (or the component that owns the header). Use the `Menu` icon from `lucide-react`.

### Confirm — Header / Footer

- Header and footer appear on every page (navigate to at least two routes)
- Imports use path aliases (`@/components/layout/...`)
- No inline `style={{}}` — Tailwind only
- `src/routes.tsx` and `src/app.tsx` are unchanged
