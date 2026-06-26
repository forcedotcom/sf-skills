# SLDS Metadata

Structured data for all SLDS artifacts. Use the search scripts in `../scripts/` or grep directly.

Source: `packages/metadata/`

---

## Files

### `blueprints/components/*.yaml` (85 files)

One YAML file per SLDS blueprint component. Each contains:

- `name`, `description`, `category`
- `slds_classes.root` -- the BEM root class (e.g., `slds-modal`)
- `slds_classes.elements[]` -- child element classes with purpose
- `slds_classes.modifiers[]` -- variant modifier classes with usage guidance
- `slds_classes.states[]` -- state classes (active, disabled, open, etc.)
- `accessibility` -- required ARIA roles, attributes, keyboard interactions
- `example_html` -- reference markup

**Search**: `node ../scripts/search-blueprints.js --search "dialog"`

**Direct grep**: `grep -rl "category: Overlay" blueprints/components/`

### `hooks-index.json` (523 hooks)

All SLDS styling hooks with computed values and CSS property mappings.

Each hook entry:
```json
{
  "token": "--slds-g-color-accent-1",
  "category": "color",
  "value": "#0176d3",
  "properties": ["background-color", "color", "border-color", "fill"]
}
```

Categories: color (325), font (57), spacing (48), shadow (44), sizing (27), duration (8), radius (6), ratio (5), fontFamily (3)

**Search**: `node ../scripts/search-hooks.js --category "color"`

**Direct grep**: `grep -i "accent" hooks-index.json`

### `icon-metadata.json` (1,732 icons)

All SLDS icons with synonyms for semantic search across 5 categories.

Each icon entry:
```json
{
  "displayName": "add_contact",
  "category": "action",
  "description": "Represents adding a new contact...",
  "synonyms": ["add", "user", "contact", "create", "new", "person", "plus"]
}
```

Categories: action, custom, doctype, standard, utility

**Search**: `node ../scripts/search-icons.js --query "save button"`

**Direct grep**: `grep -B1 -A5 '"save"' icon-metadata.json`

### `utilities-index.json` (1,147 utilities)

All SLDS utility classes organized by category with CSS rules.

Each utility entry:
```json
{
  "class": "slds-m-bottom_small",
  "css": { "margin-bottom": "0.75rem" },
  "category": "margin"
}
```

27 categories: grid (80), margin (119), padding (120), sizing (613), color (48), text (24), and more.

**Search**: `node ../scripts/search-utilities.js --category "grid"`

**Direct grep**: `grep -i "slds-grid" utilities-index.json`
