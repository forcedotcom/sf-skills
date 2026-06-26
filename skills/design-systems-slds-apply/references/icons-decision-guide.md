# Icons Decision Guide

How to select and use SLDS icons correctly.

---

## Icon Categories

SLDS provides 1,732 icons across 5 categories. Pick the right category first:

| Category | Purpose | Size | Example |
|----------|---------|------|---------|
| **utility** | UI affordances: actions, navigation, status indicators | 16-24px | `utility:search`, `utility:close`, `utility:save` |
| **standard** | Object/entity representations | 48px | `standard:account`, `standard:contact`, `standard:opportunity` |
| **action** | Actions on objects, typically in button icons | 24px | `action:new_task`, `action:edit`, `action:delete` |
| **custom** | Custom object representations (custom1-custom113) | 48px | `custom:custom1`, `custom:custom42` |
| **doctype** | File type representations | 48px | `doctype:pdf`, `doctype:excel`, `doctype:word` |

### Category Decision Tree

```
What does the icon represent?
├─ A UI control or indicator? → utility
├─ A Salesforce object or entity? → standard
├─ An action the user can take? → action
├─ A custom object? → custom
└─ A file type? → doctype
```

---

## How to Search

```bash
# Semantic search with synonym matching
node scripts/search-icons.cjs --query "save button"

# Filter by category
node scripts/search-icons.cjs --query "user" --category "standard"

# List all categories
node scripts/search-icons.cjs --list-categories
```

The search engine matches against icon names, synonyms, and descriptions. Multi-word queries match across all fields with relevance scoring.

---

## Usage in LWC

Use `<lightning-icon>` for display and `<lightning-button-icon>` for interactive icons:

```html
<!-- Display icon -->
<lightning-icon
    icon-name="utility:search"
    alternative-text="Search"
    size="small">
</lightning-icon>

<!-- Interactive icon button -->
<lightning-button-icon
    icon-name="utility:close"
    alternative-text="Close dialog"
    title="Close"
    onclick={handleClose}>
</lightning-button-icon>
```

### Size options

| Size | Use for |
|------|---------|
| `xx-small` | Inline with text |
| `x-small` | Dense layouts |
| `small` | Default for utility icons |
| `medium` | Default for standard/custom icons |
| `large` | Hero/feature icons |

---

## Usage in Non-LWC (Blueprint Markup)

Use SVG with SLDS icon classes:

```html
<span class="slds-icon_container slds-icon-utility-search" title="Search">
  <svg class="slds-icon slds-icon_small" aria-hidden="true">
    <use xlink:href="/assets/icons/utility-sprite/svg/symbols.svg#search"></use>
  </svg>
  <span class="slds-assistive-text">Search</span>
</span>
```

Key classes:
- `slds-icon_container` -- wrapper with background color
- `slds-icon` -- the SVG element
- `slds-icon_small` / `slds-icon_large` -- sizing
- `slds-icon-utility-*` / `slds-icon-standard-*` -- category-specific containers

---

## Accessibility Rules

**Every icon must have an accessibility story.**

| Scenario | LWC | Non-LWC |
|----------|-----|---------|
| **Meaningful icon** (conveys information) | `alternative-text="Description"` | `<span class="slds-assistive-text">Description</span>` |
| **Decorative icon** (next to text label) | `alternative-text=""` | `aria-hidden="true"` on SVG |
| **Interactive icon** (button) | `alternative-text="Action"` + `title="Tooltip"` | `aria-label="Action"` on button |

**Rules:**
- Never leave `alternative-text` undefined on `<lightning-icon>` -- set it to empty string `""` if decorative
- `title` provides a visible tooltip; `alternative-text` provides screen reader text
- Icon-only buttons always need `alternative-text` describing the action, not the icon

---

## Deep Reference

- Icon implementation guidance: `guidance/icons-guidance.md`
- Icons overview: `guidance/overviews/icons.md`
- Full icon metadata (1,732 icons with synonyms): `metadata/icon-metadata.json`
