# Bundled Guidance Index

Source: `packages/guidance/` -- SLDS domain knowledge for deep reference.

Read these files when the workflow phases in SKILL.md point you here. The Knowledge Map in SKILL.md tells you which file to read for each task.

---

## Root Files

| File | Read When | Description |
|------|-----------|-------------|
| `slds-development-guide.md` | Need comprehensive SLDS development patterns | Full development guide -- component hierarchy, framework patterns, code generation rules. SKILL.md has the core; this is the deep reference. |
| `blueprints-index.md` | Selecting a blueprint component | All SLDS blueprints mapped to categories and LBC equivalents |
| `icons-guidance.md` | Implementing icons | Icon implementation patterns, categories, accessibility |

## Overviews (`overviews/`)

Foundational concepts for each SLDS domain. Read when you need to understand the rules behind a domain before using specific hooks or utilities.

| File | Read When | Description |
|------|-----------|-------------|
| `color.md` | Making any color decision | 85-5-10 density rule, color role taxonomy, hook selection hierarchy, numerical color system |
| `spacing.md` | Setting spacing or sizing | 4-point spacing grid, semantic sizing scale, spacing-to-hook mappings |
| `typography.md` | Setting fonts, sizes, weights | Typography scale, heading hierarchy, font family hooks |
| `shadows.md` | Adding elevation or depth | Shadow levels, elevation system, when to use which shadow |
| `borders.md` | Adding borders or dividers | SLDS 2 minimal-border philosophy, border hooks and utility classes |
| `display-density.md` | Supporting comfy/compact modes | Display density utility patterns, density-responsive components |
| `illustrations.md` | Showing empty/error/info states | SLDS illustration markup, when to use which illustration |
| `icons.md` | Understanding icon system | Icon categories overview, sprite structure, sizing conventions |
| `utilities.md` | Understanding utility class system | Utility class philosophy, naming patterns, when to use utilities vs. hooks |

## Styling Hooks (`styling-hooks/`)

CSS custom property guidance. Read when applying `--slds-g-*`, `--slds-s-*`, or `--slds-c-*` hooks.

| File | Read When | Description |
|------|-----------|-------------|
| `index.md` | Starting any styling hooks work | Entry point: three-tier hierarchy (global/shared/component), core categories, decision trees |
| `color/index.md` | Working with color hooks | Color hook organization, palettes, selection hierarchy |
| `color/system-hooks.md` | Need system-level color hooks | Low-level palette hooks (`--slds-g-color-palette-*`) |
| `color/expressive-palette-hooks.md` | Need expressive/brand colors | Expressive palette hooks for brand-aligned color usage |
| `color/semantic/accent-hooks.md` | Need accent/brand colors | `--slds-g-color-accent-*` hooks for interactive and brand elements |
| `color/semantic/feedback-hooks.md` | Need success/warning/error colors | `--slds-g-color-error-*`, `--slds-g-color-success-*`, `--slds-g-color-warning-*` |
| `color/semantic/surface-hooks.md` | Need surface/background colors | `--slds-g-color-surface-*` and `--slds-g-color-on-surface-*` for surfaces and text |
| `typography.md` | Setting typography with hooks | Typography hooks: font-family, font-size, font-weight, line-height |
| `spacing.md` | Setting spacing/sizing with hooks | Spacing hooks: `--slds-g-spacing-*`, sizing hooks |
| `borders.md` | Setting borders with hooks | Border hooks: width, color, radius |
| `shadows.md` | Setting shadows with hooks | Shadow hooks: `--slds-g-shadow-*` levels |

## Utilities (`utilities/`)

Individual utility class categories. Read when you need specific classes for a layout or styling task.

| File | Read When | Description |
|------|-----------|-------------|
| `index.md` | Need utility class overview | All 26 categories with class counts and common patterns |
| `grid.md` | Building grid layouts | `slds-grid`, `slds-col`, `slds-size_*`, responsive sizing |
| `margin.md` | Adding margin | `slds-m-*` margin utilities by direction and size |
| `padding.md` | Adding padding | `slds-p-*` padding utilities by direction and size |
| `sizing.md` | Setting widths | `slds-size_*` fractional and absolute width utilities |
| `layout.md` | Page-level layout | Page layout containers and regions |
| `alignment.md` | Aligning content | Flex alignment, text alignment, vertical centering |
| `borders.md` | Adding border utilities | Border direction, radius, and removal utilities |
| `box.md` | Box model utilities | Box-sizing, overflow, display utilities |
| `color.md` | Color utility classes | Text and background color utilities |
| `dark-mode.md` | Dark mode support | Dark mode utility classes and patterns |
| `description-list.md` | Description lists | `dl`/`dt`/`dd` styling utilities |
| `floats.md` | Float layout | Float and clearfix utilities |
| `horizontal-list.md` | Horizontal lists | Inline list layout utilities |
| `hyphenation.md` | Word breaking | Hyphenation and word-break utilities |
| `interactions.md` | Pointer/cursor styles | Interaction and cursor utilities |
| `line-clamp.md` | Text line limiting | Line clamping utilities |
| `media-object.md` | Media object pattern | Figure + body layout utilities |
| `name-value-list.md` | Name-value pairs | Key-value display utilities |
| `position.md` | Positioning | Position, z-index, and sticky utilities |
| `print.md` | Print styles | Print-specific visibility and layout |
| `scrollable.md` | Scroll containers | Scrollable area utilities |
| `themes.md` | Theme containers | Theme override container utilities |
| `truncate.md` | Text truncation | Ellipsis and text truncation |
| `typography.md` | Text styling | Font size, weight, alignment utilities |
| `vertical-list.md` | Vertical lists | Stacked list layout utilities |
| `visibility.md` | Show/hide elements | Responsive and state visibility utilities |
