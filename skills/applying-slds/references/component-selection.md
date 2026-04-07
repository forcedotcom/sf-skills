# Component & Blueprint Selection

How to find the right SLDS artifact for a UI pattern.

---

## Decision Flow

```
What framework?
├─ LWC → Check Lightning Base Component (LBC) first
│   ├─ LBC exists → Use it. Done.
│   └─ No LBC → Fall through to SLDS Blueprint
├─ React / Vue / Angular / vanilla → Skip LBC, go to SLDS Blueprint
└─ Any framework → No blueprint match? → Build custom with styling hooks
```

## Step 1: Check for LBC (LWC only)

Lightning Base Components are pre-built, accessible, themed LWC components.

**Always check first:** [Lightning Component Library](https://developer.salesforce.com/docs/component-library/overview/components)

Common LBCs and their use cases:

| Component | Use Case |
|-----------|----------|
| `lightning-button` | All button actions |
| `lightning-input` | Text, email, number, date inputs |
| `lightning-combobox` | Dropdown selection |
| `lightning-datatable` | Tabular data with sorting/selection |
| `lightning-card` | Content containers |
| `lightning-modal` | Dialog overlays |
| `lightning-icon` | SLDS icons |
| `lightning-layout` | Responsive grid layout |

If an LBC exists, use it. Do not build a custom version from blueprint markup.

## Step 2: Search SLDS Blueprints

Blueprints are HTML/CSS patterns that work in any framework. Use when no LBC exists or when not building in LWC.

### How to search

```bash
# Keyword search
node scripts/search-blueprints.cjs --search "dialog"

# Browse by category
node scripts/search-blueprints.cjs --category "Overlay"

# Get full details for a specific blueprint
node scripts/search-blueprints.cjs --name "modals"
```

### Blueprint categories

| Category | Examples |
|----------|----------|
| Layout | Cards, Tiles, Page Headers |
| Forms | Input, Select, Combobox, Checkbox, Radio, Textarea |
| Navigation | Tabs, Vertical Navigation, Breadcrumbs, Path |
| Data Display | Data Tables, Trees, Activity Timeline |
| Feedback | Alert, Toast, Scoped Notifications, Spinners |
| Overlay | Modals, Popovers, Tooltips, Prompt |
| Media | Avatar, Carousel, Files, Illustration |
| Actions | Buttons, Button Groups, Button Icons, Menus |

### How to read a blueprint YAML

Each file in `metadata/blueprints/components/{name}.yaml` contains:

```yaml
name: "Modals"
description: "Dialog overlays..."
category: "Overlay"
slds_classes:
  root: "slds-modal"            # The BEM root class to apply
  elements:                     # Child element classes
    - class: "slds-modal__header"
      purpose: "Contains title and close action"
  modifiers:                    # Size/style variants
    - class: "slds-modal_large"
      usage: "For complex forms or detailed content"
  states:                       # State classes
    - class: "slds-fade-in-open"
accessibility:                  # Required ARIA attributes
  roles: ["dialog"]
  attributes: ["aria-modal", "aria-labelledby"]
example_html: "..."             # Reference markup
```

Use the `root` class, add `elements` for structure, `modifiers` for variants, and follow `accessibility` requirements.

## Step 3: Custom with Styling Hooks

If no LBC or blueprint matches your need, build custom markup with SLDS styling hooks.

See [styling-decision-guide.md](styling-decision-guide.md) for how to apply hooks correctly.

Rules for custom components:
- Use custom class prefixes (`my-*`, `c-*`) -- never override `slds-*` classes
- Use `var(--slds-g-*, fallback)` for all themeable values
- Follow the blueprint naming pattern (BEM-like) for consistency

---

## Deep Reference

- Full blueprint details: `guidance/blueprints-index.md`
- All blueprint YAMLs: `metadata/blueprints/components/`
- LBC documentation: [Lightning Component Library](https://developer.salesforce.com/docs/component-library/overview/components)
