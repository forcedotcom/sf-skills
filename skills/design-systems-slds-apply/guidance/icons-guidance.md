---
id: slds.guidance.icons
title: SLDS Icons Guidance
description: Icon selection and implementation guidance for coding agents
summary: "Icon implementation guide covering the sprite:symbol naming model, category decision guide (action, utility, standard, custom, doctype), implementation patterns for Lightning and SLDS markup, and accessibility requirements."

artifact_type: guide
domain: icons
topic: icons

content_format: structured
complexity: intermediate
audience: [implementer]

tasks: [choose, implement]

refs:
  - slds.guidance.development
  - slds.guidance.design
  - slds.guidance.blueprints

tags: [icons, sprites, svg, utility-icons, action-icons, standard-icons]
keywords: [icon sprites, utility icons, action icons, standard icons, custom icons, doctype icons, icon accessibility, SVG icons]
---

# SLDS Icons Guidance

## Overview

SLDS icons are a curated set of reusable SVG symbols grouped into **sprite categories**. They're used to add quick, consistent visual meaning to UI elements (buttons, navigation, record headers, status indicators, file types, and more).

This guidance covers:

- **Category guidance** for picking the right sprite
- **Implementation patterns** (Lightning + SLDS markup)
- **Accessibility requirements** for icons in UI

---

## Icon Naming Model (Critical)

An icon is referenced as:

- **`sprite:symbol`** (example: `utility:search`, `action:save`, `standard:account`)

Where:

- **sprite** = category (action, utility, standard, custom, doctype)
- **symbol** = the icon name within that sprite

---

## Category Decision Guide (What to Use When)

### Action Icons (`action:*`)

- **Use for**: verbs / user actions (save, delete, edit, add, close)
- **Common placements**: buttons, menus, toolbars, row actions
- **Rule of thumb**: if the UI text could start with "Do …", use `action:`

### Utility Icons (`utility:*`)

- **Use for**: general interface affordances and controls (search, settings, filter, chevrons)
- **Common placements**: nav, search fields, utility panels, small inline UI hints
- **Rule of thumb**: if it's a UI control concept (not a business object), use `utility:`

### Standard Icons (`standard:*`)

- **Use for**: Salesforce objects/entities (Account, Contact, Case, Opportunity)
- **Common placements**: record headers, object pickers, list tiles
- **Rule of thumb**: if the icon represents "what this thing is" (a noun/object), use `standard:`

### Custom Icons (`custom:*`)

- **Use for**: generic shapes/symbols, often for custom objects when no standard icon fits
- **Common placements**: custom object tiles, app launcher tiles, branded placeholders
- **Rule of thumb**: use `custom:` when `standard:` is not appropriate and you still want a "record/object style" icon

### Doctype Icons (`doctype:*`)

- **Use for**: file types (pdf, image, spreadsheet, etc.)
- **Common placements**: attachments, file lists, previews
- **Rule of thumb**: if you're representing a file format, use `doctype:`

---

## How to Search Icons

**Effective query patterns:**

- **Intent-first**: "save", "delete", "filter", "settings", "add user"
- **Object-first**: "account", "contact", "case"
- **UI affordance**: "chevron right", "close x", "search magnifier"

**Optional filters:**

- Restrict to a sprite category (action / utility / standard / custom / doctype)
- Limit results to keep responses tight

### Searchable Metadata Fields

Each icon entry in the JSON metadata supports these lookup strategies:

- **Exact match**: `category` + icon name (mapped to `sprite:symbol` at runtime, e.g. `utility:chevronright`)
- **Discovery**: `synonyms` (best for intent searches — e.g. "next" finds `chevronright`)
- **Styling**: `className` (computed as `slds-icon-{category}-{name}` for SLDS `<svg>` containers)
- **Context**: `description` (matches long-form queries about icon purpose)
- **RTL**: `directionality.hasRtl` (rare, but important for directional glyphs)

---

## Implementation Patterns

### Lightning Web Components (preferred inside Salesforce)

**Icon only:**

```html
<lightning-icon
  icon-name="utility:search"
  alternative-text="Search"
  title="Search"
  size="x-small">
</lightning-icon>
```

**Icon button:**

```html
<lightning-button-icon
  icon-name="action:save"
  alternative-text="Save"
  title="Save"
  onclick={handleSave}>
</lightning-button-icon>
```

### SLDS (raw HTML/SVG usage)

If you're implementing outside Lightning components, use the `className` from the JSON (example: `slds-icon-utility-search`) with the appropriate SLDS blueprint patterns for icon containers.

---

## Sizes

When rendering icons in Lightning Web Components, prefer the built-in size tokens on `lightning-icon` / `lightning-button-icon` instead of custom CSS.

| Size token | Typical use |
|-----------|-------------|
| `xx-small` | Inline with dense UI or text-adjacent glyphs |
| `x-small` | Compact layouts / tight controls |
| `small` | Default for most utility UI icons |
| `medium` | Default for object/record representation icons |
| `large` | Featured / hero contexts (use sparingly) |

---

## Accessibility Requirements (Do Not Skip)

### When the icon communicates meaning

- **Provide text** for assistive tech:
  - LWC: `alternative-text` (required), `title` (recommended)
  - HTML/SVG: ensure an accessible name via text, `aria-label`, or `title` as appropriate

### When the icon is purely decorative

- Hide it from assistive tech (don't create "noise"):
  - LWC: use an empty `alternative-text=""` only if the containing control already has an accessible label
  - HTML/SVG: `aria-hidden="true"` on the decorative icon element

### Don't rely on icons alone

If the icon represents status (success/error/warning), ensure there's **text and/or non-color cues** in addition to the icon.

---

## Icon Metadata Structure

All 1,732 icons are stored in a single `icon-metadata.json` file, keyed by icon name. Each entry includes:

- `displayName` — the icon identifier (e.g. `chevronright`, `add_contact`)
- `category` — sprite category: `action`, `utility`, `standard`, `custom`, `doctype`
- `synonyms` — search terms for discovery (e.g. `["next", "forward", "arrow", "chevron"]`)
- `description` — what the icon represents
- `directionality` — `type` (`common` or `directional`) and `hasRtl` flag
