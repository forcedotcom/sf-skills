# Implementation — Component

### Rules

1. **Always use shadcn components** from `@/components/ui` — never build raw HTML equivalents for buttons, inputs, cards, alerts, tabs, tables, or labels.
2. **All styling via Tailwind** — utility classes only. No inline `style={{}}`, CSS Modules, or other styling systems.
3. **Use design tokens** — prefer `bg-background`, `text-foreground`, `text-muted-foreground`, `border`, `bg-primary`, `text-destructive`, `rounded-lg` over hardcoded colors.
4. **Use `cn()`** from `@/lib/utils` for conditional or composable class names.
5. **TypeScript** — functional components with typed props interface; always accept `className?: string`.
6. **Never assume a primitive or its exports exist** — the shadcn inventory below is a common baseline, not a guarantee for every app. Before importing anything from `@/components/ui`, read `src/components/ui/index.ts` (the barrel) to confirm the component is actually re-exported there. If it isn't, either import directly from its file (`@/components/ui/<file>`) or add the export to the barrel yourself — never invent a component that isn't present in either place.

### Common shadcn/ui Inventory

Apps scaffolded from the standard template typically ship these primitives under `src/components/ui/`. Treat this as a starting checklist, not a source of truth — always verify against the actual files and the barrel (`index.ts`) in the current project, since apps diverge (custom primitives get added, unused ones get removed, and not every file is necessarily re-exported from the barrel).

| Primitive | Typical file | Notes |
|---|---|---|
| Alert | `alert.tsx` | `Alert`, `AlertTitle`, `AlertDescription` |
| Avatar | `avatar.tsx` | `Avatar`, `AvatarImage`, `AvatarFallback` |
| Badge | `badge.tsx` | Often exists as a file but may not be barrel-exported — check first |
| Breadcrumb | `breadcrumb.tsx` | |
| Button | `button.tsx` | `Button`, `buttonVariants` |
| Calendar | `calendar.tsx` | |
| Card | `card.tsx` | `Card`, `CardHeader`, `CardTitle`, `CardContent`, `CardFooter` |
| Checkbox | `checkbox.tsx` | |
| Collapsible | `collapsible.tsx` | |
| Date Picker | `datePicker.tsx` | |
| Dialog | `dialog.tsx` | `Dialog`, `DialogContent`, `DialogHeader`, `DialogTitle`, `DialogTrigger` |
| Dropdown Menu | `dropdown-menu.tsx` | |
| Field | `field.tsx` | Composable form-field wrapper (label + error + description) |
| Input | `input.tsx` | |
| Label | `label.tsx` | |
| Pagination | `pagination.tsx` | |
| Popover | `popover.tsx` | |
| Select | `select.tsx` | |
| Separator | `separator.tsx` | |
| Skeleton | `skeleton.tsx` | |
| Sonner (Toast) | `sonner.tsx` | Exists as a file but is typically **not** barrel-exported — check `index.ts` first, or import `{ Toaster, toast }` directly from `@/components/ui/sonner` |
| Spinner | `spinner.tsx` | |
| Table | `table.tsx` | `Table`, `TableHeader`, `TableBody`, `TableRow`, `TableCell` |
| Tabs | `tabs.tsx` | `Tabs`, `TabsList`, `TabsTrigger`, `TabsContent` |

**Not part of this baseline** — do not assume these exist without checking: `Sheet`, `Combobox`, `Accordion`, `Slider`, `Switch`, `RadioGroup`, `Command`, `Menubar`, `NavigationMenu`, `Tooltip`, `Progress`, `Carousel`, `Drawer`. If the task needs one of these, check `src/components/ui/` first; if it's genuinely missing, either compose it from an existing primitive or tell the user it needs to be added rather than fabricating an import.

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

- **Programmatic navigation:** use `useNavigate` from `react-router`; call `navigate(path)` — consistent with GlobalSearchInput, SearchResultCard, MaintenanceTable, and other components in the UI bundle.
- **Page container:** `max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12`
- **Icons:** `lucide-react`; add `aria-hidden="true"` on decorative icons
- **Focus styles:** use `focus-visible:` variants
- **Multiple visual variants:** use CVA (`cva`) and `VariantProps`
- **shadcn import barrel:** `import { Button, Card, Input } from "@/components/ui"` — only for components confirmed present in `index.ts`; see rule 6 above

### Confirm — Component

- Imports use path aliases (`@/`, not deep relative paths)
- No raw `<button>`, `<input>`, or styled `<div>` where shadcn equivalents exist
- No inline `style={{}}` — Tailwind only
