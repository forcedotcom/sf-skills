# Implementation — Component

### Rules

1. **Always use shadcn components** from `@/components/ui` — never build raw HTML equivalents for buttons, inputs, cards, alerts, tabs, tables, or labels.
2. **All styling via Tailwind** — utility classes only. No inline `style={{}}`, CSS Modules, or other styling systems.
3. **Use design tokens** — prefer `bg-background`, `text-foreground`, `text-muted-foreground`, `border`, `bg-primary`, `text-destructive`, `rounded-lg` over hardcoded colors.
4. **Use `cn()`** from `@/lib/utils` for conditional or composable class names.
5. **TypeScript** — functional components with typed props interface; always accept `className?: string`.

### File Location — Component

| Component type                                 | Location                                 | Export                                   |
| ---------------------------------------------- | ---------------------------------------- | ---------------------------------------- |
| Shared UI primitive (reusable across features) | `src/components/ui/` — add to `index.ts` | Named export                             |
| Feature-specific (e.g., dashboard widget)      | `src/components/<feature>/`              | Named export, import directly where used |
| Page-level layout element                      | `src/components/layout/`                 | Named export                             |

### Component Structure

```tsx
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui";
import { cn } from "@/lib/utils";

interface MyComponentProps {
  title: string;
  value: string;
  className?: string;
}

export function MyComponent({ title, value, className }: MyComponentProps) {
  return (
    <Card className={cn("border", className)}>
      <CardHeader>
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-2xl font-semibold text-foreground">{value}</p>
      </CardContent>
    </Card>
  );
}
```

### State and Hooks

- **Local state only:** keep `useState`, `useReducer`, `useRef` inside the component.
- **Shared or complex state:** extract to a custom hook in `src/hooks/` (prefix with `use`, e.g. `useFormData`). Do this when more than one component needs the state, or when multiple hooks are composed together.

### Adding the Component to a Page

```tsx
// In the target page file, e.g. src/pages/HomePage.tsx
import { MyComponent } from "@/components/<feature>/MyComponent";

export default function HomePage() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <MyComponent title="Status" value="Active" />
    </div>
  );
}
```

### Useful Patterns — Component

- **Programmatic navigation:** use `useNavigate` from `react-router`; call `navigate(path)` — consistent with GlobalSearchInput, SearchResultCard, MaintenanceTable, and other components in the web application.
- **Page container:** `max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12`
- **Icons:** `lucide-react`; add `aria-hidden="true"` on decorative icons
- **Focus styles:** use `focus-visible:` variants
- **Multiple visual variants:** use CVA (`cva`) and `VariantProps`
- **shadcn import barrel:** `import { Button, Card, Input } from "@/components/ui"`

### Confirm — Component

- Imports use path aliases (`@/`, not deep relative paths)
- No raw `<button>`, `<input>`, or styled `<div>` where shadcn equivalents exist
- No inline `style={{}}` — Tailwind only
