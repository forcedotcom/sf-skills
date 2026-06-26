# Color Hooks Decision Guide

This guide helps you choose the correct SLDS 2 color hook. Use it when replacing hardcoded colors or when the linter suggests multiple options.

> **BEFORE choosing any hook:** Always inspect the element's context in this order:
> 1. **Markup** (`.html` for LWC, `.cmp` for Aura) — search for the CSS class. Check parent containers, nesting depth, ARIA attributes, interactive role.
> 2. **JavaScript** — if not in markup, search the JS/TS files for dynamic class insertion (`classList.add`, template literals, conditional class bindings).
>
> CSS alone is never enough — always determine context from markup or JS before choosing a hook.

## Table of Contents

- [Hook Selection Priority](#hook-selection-priority)
- [Surface Family](#surface-family)
- [Accent Family](#accent-family)
- [Feedback Family](#feedback-family)
- [Palette Family](#palette-family)
- [System Family](#system-family)
- [Choosing the Numbered Variant](#choosing-the-numbered-variant)
- [Background-Foreground Pairing Rules](#background-foreground-pairing-rules)
- [Applied Examples](#applied-examples--color-context-investigation)

## Hook Selection Priority

**Always try semantic hooks first.** ~85-90% of color decisions should use semantic hooks. System and palette hooks are last resorts, not alternatives.

```
1. SEMANTIC HOOKS (try first, ~85-90% of decisions)
   surface-*, accent-*, error/warning/success/info/disabled-*
   • Accessibility built-in  • Theme-aware  • Dark mode ready

2. SYSTEM HOOKS (5-10%, only when no semantic family fits)
   *-base-*
   • Manual accessibility required  • No semantic meaning

3. PALETTE (data viz & decorative only, <5%)
   palette-*
   • Manual accessibility  • Non-semantic color only
```

If you find yourself reaching for a system hook, re-check whether a semantic hook applies — surface, accent, or feedback families cover most cases.

**Decision flow:**
1. Page/overlay/container background? → Surface hooks
2. Brand/interactive? → Accent hooks
3. Error/warning/success/info/disabled state? → Feedback hooks
4. Edge case with no semantic fit? → System hooks
5. Data viz or decorative? → Palette hooks

> **Visual color density rule (85-5-10):** ~85% of UI surface area should be neutral grays/whites (surface hooks), ~5% accent/feedback colors, ~10% maximum expressive colors.

### "Color ≠ Semantic Meaning"

| Scenario | Wrong Choice | Right Choice | Why |
|----------|--------------|--------------|-----|
| Red text but no error class | `--slds-g-color-error-1` | `--slds-g-color-palette-red-50` | Color for emphasis, not error state |
| Blue that's not clickable | `--slds-g-color-accent-2` | `--slds-g-color-palette-cloud-blue-50` | Decorative blue, not interactive |
| Green in data chart | `--slds-g-color-success-1` | `--slds-g-color-palette-green-50` | Data point, not success state |
| Orange highlight span | `--slds-g-color-warning-1` | `--slds-g-color-palette-orange-90` | Visual emphasis, not warning |

Use system hooks if the element matches a semantic meaning. If it explicitly does not, use the palette equivalent (e.g., `--slds-g-color-palette-red-40`). Evaluate background-color first, as it informs the correct foreground color pair.

---

## Surface Family

### Core Question
Is this element a page foundation, an overlay (modal/popover/dropdown), or does it sit within the content flow on an existing surface?

| Characteristic | Use `surface-*` | Use `surface-container-*` |
|---|---|---|
| Creates new stacking context | Yes | No |
| Elevated/overlays other content | Yes | No |
| Exists within page's content flow | No | Yes |
| Sits on top of an existing surface | No | Yes |

### Linter Lists Both? Use Context

The linter lists hooks with similar color values in no particular order. When it suggests both `surface-N` and `surface-container-N`, check the element's DOM role:

| Question | Answer | Hook |
|---|---|---|
| Does it sit on top of another visible surface? | Yes | `surface-container-*` |
| Is it the page/modal/overlay/component root? | Yes | `surface-*` |

### Hook Types

| Hook Type | Pattern | Use For |
|---|---|---|
| Surface | `--slds-g-color-surface-1` / `-2` / `-3` | Pages, modals, popovers, overlays |
| Container | `--slds-g-color-surface-container-1` / `-2` / `-3` | Cards, buttons, panels on existing surfaces |
| On Surface | `--slds-g-color-on-surface-1` / `-2` / `-3` | Foreground (text, icons) on any surface or container |
| Inverse | `--slds-g-color-surface-inverse-1` / `-2` | Dark backgrounds on light themes (hero banners, inverted headers) |

### Surface Numbering (Light → Dark, NOT States)

Surface variants are an aesthetic progression, not interaction states:

| Variant | Description | Typical Use |
|---|---|---|
| `surface-1` | Lightest (white) | Clean base; cards/containers stand out against it |
| `surface-2` | Light gray | Softer separation; avoids harsh white backgrounds |
| `surface-3` | Medium gray | Additional depth; rare in practice |

The same numbering applies to `surface-container-*` (1=lightest, 3=darkest).

### On-Surface Emphasis Levels

On-surface variants represent **content emphasis**, not surface pairing:

| Variant | Emphasis | Use For |
|---|---|---|
| `on-surface-1` | Low (de-emphasized) | Captions, placeholder text, secondary content |
| `on-surface-2` | Medium (standard) | Body text, labels, filled input fields |
| `on-surface-3` | High (maximum weight) | Page titles, component headings, primary content |

All three `on-surface` variants can appear on the same surface background. Choose by content importance, not by matching the surface number.

### Markup Nesting Depth → Hook Choice

| DOM Position | Hook | Why |
|---|---|---|
| Page/app wrapper (`<body>` or root) | `surface-1` | Foundation canvas |
| Card/panel directly on page | `surface-container-1` | First container on a surface |
| Sub-panel inside a card | `surface-container-2` | Nested container |
| Modal / popover / dropdown | `surface-1` | Creates NEW stacking context — resets depth |

**Exception:** If a card/panel IS the component's entire visual footprint (notification bar, banner, standalone section with no visible parent surface), treat it as a surface, not a container.

### State Progression

The starting variant depends on which one matches the original default color — don't assume `-1`:

| Default | Hover | When |
|---|---|---|
| `surface-container-1` | `surface-container-2` | Default bg is white/near-white |
| `surface-container-2` | `surface-container-3` | Default bg is light gray (~#f4f4f4) |

### Edge Cases

| Scenario | Hook | Why |
|---|---|---|
| Full-page card (IS the page background) | `surface-*` | Acts as page surface, not a container |
| Slide-out panel overlaying content | `surface-*` | Creates new stacking context |
| Slide-out panel in page flow (no overlay) | `surface-container-*` | Sits within existing surface |
| Nested modals | `surface-1` for each | Each modal creates its own stacking context |
| Dropdown over page content | `surface-1` | Overlay, not a container |

### Inverse Hooks

Use when hardcoded dark-blue backgrounds (`#032d60`, `#03234d`) appear on light themes. Pair with `--slds-g-color-on-surface-inverse-*` — do NOT pair with regular `on-surface-*`.

### Warning: CSS Class Names Are Irrelevant

An element named `.card-container` might use `surface-*` if it's the page-level background, or `surface-container-*` if it's a card. **Always base the decision on structural DOM position, not naming conventions.**

Surface variants (1-2-3) are a light-to-dark aesthetic progression, NOT functional states. The linter's suggestion list is NOT ranked -- use element context, not list position.

---

## Accent Family

### Core Question
Is this element interactive or expressing brand identity?

### Hook Types

| Hook Type | Pattern | Use For |
|---|---|---|
| Accent | `accent-1` / `-2` / `-3` | Links, clickable text, interactive icons |
| Container | `accent-container-1` / `-2` / `-3` | Brand button backgrounds |
| Border | `border-accent-1` / `-2` / `-3` | High-emphasis brand borders |
| On Accent | `on-accent-1` / `-2` / `-3` | Text on brand backgrounds |

### Context Determines Hook Type

| Element Context | Hook | Example |
|---|---|---|
| Interactive container/button background | `accent-container-*` | Brand button `background-color` |
| Link text, icon fill (NOT on accent bg) | `accent-*` | Link `color`, icon `fill` |
| Text/icon ON an accent-container background | `on-accent-*` | Button label `color` |
| Border of an accent element | `border-accent-*` | Button `border-color` |

`accent-*` is for **foreground** (text, icons). `accent-container-*` is for **background fills** of interactive containers. Determine what the element IS first, then the CSS property follows naturally.

### Accent Container State Progression

| Default | Hover/Active |
|---|---|
| `accent-container-1` | `accent-container-2` |
| `accent-container-2` | `accent-container-3` |

### Why accent-2 is the default for links (not accent-1)

`accent-1` may not meet 4.5:1 WCAG contrast on non-white backgrounds. `accent-2` passes on all standard surfaces — use it as the safe default for text links. Go up one for hover: `accent-2` → `accent-3`.

### Quick Decision

1. Link or clickable text → `accent-2`
2. Brand button background → `accent-container-1`
3. Text on brand background → `on-accent-1`
4. Brand border → `border-accent-1` (use only when design explicitly requires brand-colored outline — default to neutral `border-2` for most borders)

### Accent vs Surface

| Element Type | Surface | Accent |
|---|---|---|
| Non-interactive card | `surface-container-*` | Never |
| Clickable card | `surface-container-*` (bg) | `accent-2` (text) |
| Primary button | Never | `accent-container-*` |

---

## Feedback Family

### Core Question
Does the markup/ARIA context indicate a specific state?

### Hook Types

| Type | Use For |
|---|---|
| `error-*` / `error-container-*` / `on-error-*` / `border-error-*` | Invalid inputs, errors, destructive actions |
| `warning-*` / `warning-container-*` / `on-warning-*` / `border-warning-*` | Cautions, alerts |
| `success-*` / `success-container-*` / `on-success-*` / `border-success-*` | Confirmations, valid states |
| `info-*` / `info-container-*` / `on-info-*` | Tips, help badges |
| `disabled-*` / `disabled-container-*` / `on-disabled-*` / `border-disabled-*` | Inactive elements |

### Quick Decision

1. `aria-invalid` attribute → `error-*`
2. Class with "error"/"invalid" → `error-*`
3. Class with "success"/"valid" → `success-*`
4. `[disabled]` attribute → `disabled-*`
5. `role="alert"` → check alert type

### Variant Availability

| Type | Has -2? | Why |
|---|---|---|
| Error | Yes | Destructive buttons need hover states |
| Success | Yes | Success buttons need hover states |
| Warning | No (only -1) | No warning buttons — only static alerts |
| Info | No (only -1) | No info buttons — only static badges |
| Disabled | Yes | Different visual weights |

---

## Palette Family

### Core Question
Is this color for data visualization or decoration without semantic meaning?

Use for: chart data series, decorative gradients, non-semantic colored elements — NOT standard UI.

**Hook Pattern:** `--slds-g-color-palette-{color}-{grade}`

**Grade Scale:** 0 (darkest) to 100 (lightest). Example: `--slds-g-color-palette-cloud-blue-50`.

**Cool Tones (Recommended):** `cloud-blue`, `indigo`, `purple`, `violet`
**Warm Tones (Use with caution):** `green`, `orange`, `hot-orange`, `red`

Warm tones risk confusion with feedback colors — green looks like success, red looks like error, orange looks like warning. Only use palette hooks when the color explicitly does NOT carry semantic meaning.

### Palette → Semantic Conversion

If existing code uses palette hooks but the element is actually interactive or semantic, convert to the appropriate semantic family:

| Element Role | Palette Hook (Before) | Semantic Hook (After) |
|---|---|---|
| Clickable icon/link | `palette-*-blue-*` | `accent-*` |
| Brand button bg | `palette-*-*` | `accent-container-*` |
| Error indicator | `palette-red-*` | `error-*` |
| Success indicator | `palette-green-*` | `success-*` |
| Chart data point | `palette-*` | Keep palette (correct usage) |
| Decorative element | `palette-*` | Keep palette (correct usage) |

Check markup context: if the element has click handlers, `href`, `role="button"`, or brand intent, it belongs in a semantic family.

### Accessibility

Palette hooks do NOT guarantee accessible contrast. Verify manually:
- **50-point rule:** 50 grade points between bg and text (4.5:1 WCAG)
- **40-point rule:** 40 grade points between bg and UI element (3:1 WCAG)

**Color vision deficiency:** Never use red+green or blue+purple as sole differentiators. Always pair with patterns, labels, or shapes.

---

## System Family

### Core Question
Have all semantic and palette options been exhausted?

| Need | Try First | System Fallback | Only If |
|---|---|---|---|
| Background | `surface-*` | `neutral-base-95` | Custom component, no semantic fit |
| Interactive | `accent-*` | `brand-base-50` | Legacy exact match required |
| Error state | `error-*` | `error-base-50` | Special non-standard requirement |

System hooks require manual accessibility testing. Never use as a first choice.

---

## Choosing the Numbered Variant

**Do not default to `-1`.** Numbered variants represent a light-to-dark progression. Pick the variant whose actual rendered value best matches the original hardcoded value.

1. Look at the original hardcoded value
2. Compare to the rendered values of available variants
3. Pick the closest match, not the lowest number

```css
/* Original: #014486 — very dark navy */
/* WRONG: defaulting to -1 */
border-color: var(--slds-g-color-border-accent-1, #014486);
/* RIGHT: -3 is darkest, closest to #014486 */
border-color: var(--slds-g-color-border-accent-3, #014486);
```

```css
/* Original: rgb(243,242,242) — very light gray */
/* container-1 ≈ #fff, container-2 ≈ #f4f4f4, container-3 ≈ #f3f2f2 */
/* RIGHT: container-3 is closest */
background-color: var(--slds-g-color-surface-container-3, rgb(243,242,242));
```

When an element has interactive states, variants progress sequentially from the starting match:

| Start At | Hover | Active |
|---|---|---|
| `-1` | `-2` | `-3` |
| `-2` | `-3` | — |

---

## Background-Foreground Pairing Rules

| If background uses... | Then text/fill MUST use... |
|---|---|
| `surface-*` or `surface-container-*` | `on-surface-*` |
| `surface-inverse-*` or `surface-container-inverse-*` | `on-surface-inverse-*` |
| `accent-container-*` | `on-accent-*` |
| `error-container-*` | `on-error-*` |
| `warning-container-*` | `on-warning-*` |
| `success-container-*` | `on-success-*` |
| `info-container-*` | `on-info-*` |
| `disabled-container-*` | `on-disabled-*` |

**Never mix families** — e.g., don't use `on-accent-*` on a `surface-container-*` background.

### Border Color Decision

| Context | Hook |
|---|---|
| Interactive element (default) | `border-2` (primary choice for most borders) |
| Decorative divider | `border-1` |
| Validation state | `border-[state]-1` |
| Disabled | `border-disabled-1` |

---

## Applied Examples — Color Context Investigation

### Context from Class Name

```css
/* Before — recordPage.css */
.headerBackground {
    background: var(--lwc-colorBackgroundAlt);
}
```

**Decision:** From class name `headerBackground`, this is a header container on another surface → `surface-container-1`.

```css
/* After */
.headerBackground {
    background: var(--slds-g-color-surface-container-1, var(--lwc-colorBackgroundAlt));
}
```

### Context from Component Name

```css
/* Before — defaultOrgSharingSettingsPanelFooter.css */
.THIS {
    background-color: t(colorBackground);
}
```

**Decision:** `.THIS` alone isn't enough. Component name says panel footer → container on a panel surface → `surface-container-2`.

```css
/* After */
.THIS {
    background-color: var(--slds-g-color-surface-container-2, var(--lwc-colorBackground));
}
```

### Context from Deep Investigation (Markup + JS)

```css
/* Before — floatingPanelContent.css */
.main-body {
    background-color: var(--lwc-colorBackgroundAlt);
}
```

**Investigation:**
- Component name `floatingPanelContent` is ambiguous
- `.main-body` not found in markup — it's a computed class
- JS shows the class is applied alongside `slds-popover*` classes

**Decision:** Main background of a popover → surface element → `surface-1`.

```css
/* After */
.main-body {
    background-color: var(--slds-g-color-surface-1, var(--lwc-colorBackgroundAlt));
}
```

### Border Color — Semantic Fit Over Math

```css
/* Before */
border: 1px solid #dddbda;
```

**Decision:** Mathematically closest might be `palette-neutral-90`, but `border-1` is still light grey, fits the design intention, and fits the semantic system better.

```css
/* After */
border: var(--slds-g-sizing-border-1, 1px) solid var(--slds-g-color-border-1, #dddbda);
```

### Pairing Examples

**Card on page surface:**
```css
.product-card {
  background-color: var(--slds-g-color-surface-container-1, #ffffff);
  color: var(--slds-g-color-on-surface-1, #2e2e2e);
}
```

**Error alert (role="alert" + error class):**
```css
.error-message {
  background: var(--slds-g-color-error-container-1, #fddde3);
  color: var(--slds-g-color-on-error-1, #b60554);
  border: 1px solid var(--slds-g-color-border-error-1, #b60554);
}
```

### Linter vs Agent Decision-Making

Linters suggest hooks by **color similarity** — they match hex values regardless of meaning. Agents must choose by **semantic family** — inspect markup (`.html`/`.cmp`), ARIA attributes, and element purpose. Always prioritize semantic correctness over color matching.
