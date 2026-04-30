---
id: slds.guidance.overview.utilities
title: Utility Classes Overview
description: Foundational principles and constraints for utility class decisions in SLDS
summary: "Comprehensive guidance on SLDS utility classes covering core principles, naming conventions, responsive patterns, accessibility considerations, and when to use utilities vs. other styling approaches."

artifact_type: overview
domain: overviews
topic: utilities

content_format: narrative
complexity: foundational
audience: [implementer, designer]

tasks: [learn, choose, implement]

refs:
  - slds.guidance.utilities
  - slds.guidance.hooks.spacing
  - slds.guidance.hooks.typography
  - slds.guidance.hooks.color

tags: [utilities, css-classes, layout, spacing, typography, responsive, mobile-first]
keywords: [utility classes, slds-grid, spacing scale, responsive breakpoints, mobile-first, flexbox, naming convention]
---

# Utility Classes Guidance for SLDS Implementation

**Purpose:** This document provides the foundational principles and constraints for all utility class decisions in Salesforce Lightning Design System. Utility classes are single-purpose CSS classes that provide rapid styling capabilities for layout, spacing, typography, visibility, and common visual patterns. When implementing components and layouts, follow these guidelines to ensure consistency, maintainability, and integration with the SLDS design system.

---

## Core Principles

When working with utility classes in UI interfaces, adhere to these foundational principles:

1. **Prefer utilities over custom CSS.** Utility classes are pre-built, tested, and optimized for consistency with the Salesforce design language. They integrate seamlessly with SLDS design tokens, reduce CSS bundle size, and provide responsive behavior out of the box. Use utilities as the first approach before writing custom CSS.

2. **Respect the system's scale.** SLDS provides deliberate scales for spacing (`none` through `xx-large`), sizing (fractional widths from `1-of-2` through `12-of-12`), and typography (heading hierarchy and body text sizes). These scales create visual rhythm and hierarchy. Do not invent arbitrary values—work within the defined scales to maintain design consistency.

3. **Compose, don't customize.** Combining 2-3 utility classes is the intended pattern for achieving complex styling. The grid system demonstrates this: `slds-grid` + `slds-wrap` + `slds-gutters` + sizing classes compose to create responsive layouts. Prefer composition over creating one-off custom classes.

4. **Design mobile-first.** SLDS responsive utilities follow a mobile-first approach where base classes apply to all viewport sizes and responsive modifiers (`slds-small-`, `slds-medium-`, `slds-large-`) progressively enhance for larger screens. This ensures optimal performance and progressive enhancement across all devices.

---

## What Are Utility Classes?

Utility classes are single-purpose CSS classes that apply specific styling to elements. The Salesforce Lightning Design System provides utility classes across multiple categories for rapid component styling without writing custom CSS.

**Utility classes solve these problems:**
- Provide consistent spacing, sizing, and typography aligned with SLDS design tokens
- Enable responsive layouts through mobile-first breakpoint modifiers
- Reduce CSS bundle size by reusing common patterns instead of duplicating styles
- Ensure accessibility patterns are built-in (screen reader utilities, focus states)
- Allow rapid prototyping and styling without context-switching to CSS files

**SLDS utility naming convention:**

```
slds-[property]-[direction]_[size/value]
```

**Examples:**
- `slds-m-top_small` — Small top margin
- `slds-p-around_medium` — Medium padding on all sides
- `slds-text-heading_large` — Large heading typography
- `slds-size_1-of-2` — 50% width
- `slds-grid_align-center` — Center-aligned grid

**Key naming patterns:**
- Underscores (`_`) separate the modifier value
- Hyphens (`-`) separate compound words
- Direction modifiers: `top`, `bottom`, `left`, `right`, `horizontal`, `vertical`, `around`
- Size scale: `none`, `xxx-small`, `xx-small`, `x-small`, `small`, `medium`, `large`, `x-large`, `xx-large`, `xxx-large`

---

## Utilities vs. Other Styling Approaches

SLDS provides multiple styling mechanisms. Understanding when to use each approach ensures maintainable, consistent code.

### Styling Hierarchy

**1. Component Classes** — Complete component patterns with built-in structure, accessibility, and interaction states. Use first when a full component pattern exists.

**2. Utility Classes** — Layout composition, spacing, sizing, typography, visibility, and common visual patterns. Utilities are the "glue" between components, handling relationships and responsive behavior.

**3. Styling Hooks** — Colors, theming, border radius, shadows, and brand customization via CSS custom properties. Use for visual customization that needs to adapt across themes.

**4. Custom CSS** — Component-specific styling, animations, and business-logic-driven needs not covered by the above. Use as last resort.

### When NOT to Use Utility Classes

**Don't use utilities when:**
- A component class already handles the pattern (use `slds-card`, not utilities to recreate it)
- You need colors or theming (use styling hooks instead)
- The styling is component-specific logic (write scoped custom CSS)
- You're combining more than 5 utilities on a single element (indicates missing component class)

<!--
PENDING REVIEW - NOT FOR LLM GUIDANCE CONSUMPTION

The following edge cases need design system team validation:
- Specific threshold for when utility composition becomes unwieldy (current guidance says 4-5+ utilities suggests missing component, but is this team consensus?)
- Whether color utilities (slds-color__text_gray-*, slds-color__background_gray-*) should ever be used given that styling hooks exist for colors
- Team position on mixing utility classes with component-level custom properties in the same element
- Whether there are scenarios where writing custom CSS is preferred over complex utility composition

Source references for review:
- packages/knowledge/utility-classes/index.md (lines 17-43: utility philosophy section)
- packages/guidance/utilities/borders.md (lines 126-137: box vs card decision framework)
- packages/guidance/styling-hooks/index.md (guidance on when to use styling hooks)
-->

---

## SLDS 2 Design Philosophy

SLDS 2 introduced several changes to utility classes focused on consistency, accessibility, and modern CSS practices.

### Naming Convention Standardization

SLDS 2 standardized the naming convention from double-hyphen (`--`) to underscore (`_`) for modifiers:
- SLDS 1: `slds-m-top--small`
- SLDS 2: `slds-m-top_small`

This convention applies consistently across all utility classes, making the naming system more predictable and easier to learn.

### Deprecated Utilities

Several utility classes have been deprecated in SLDS 2, primarily for accessibility or consistency reasons. **Avoid using these classes:**

**Visibility utilities:**
- `.slds-collapsed` → Use `slds-is-collapsed` instead
- `.slds-expanded` → Use `slds-is-expanded` instead

**Media object utilities:**
- `.slds-media_reverse` → Deprecated for accessibility reasons (WCAG 1.3.2 reading order concerns)
- `.slds-media_double` → Deprecated for accessibility reasons

**Vertical list utilities:**
- `.slds-has-dividers` (on `slds-list_vertical`) → Use positional divider helpers instead (`has-dividers_top`, `has-dividers_bottom`)
- `.slds-has-cards` → Use `has-dividers_around` instead
- `.slds-has-divider` → Spacing now comes from divider position utilities

The presence of `_deprecate.scss` files in the source code (visibility, media-objects, vertical-list, horizontal-list, grid) indicates active deprecation tracking. Refer to per-utility guidance for specific deprecated classes and replacements. Use the utility class names documented in this guidance. When uncertain about a class name, refer to the per-category utility guides (`slds.guidance.utilities.*`).

### Relationship to SLDS 2 System

Utility classes in SLDS 2 work alongside the styling hooks system:
- Utilities provide structural layout and spacing
- Styling hooks provide semantic theming and color customization
- Together they enable fully themeable, responsive components without custom CSS

<!--
PENDING REVIEW - NOT FOR LLM GUIDANCE CONSUMPTION

The following SLDS 2 migration details need design system team validation:
- Complete list of all deprecated utility classes between SLDS 1 and SLDS 2 (beyond the ones documented in _deprecate.scss files)
- Whether any utility categories were added in SLDS 2 that didn't exist in SLDS 1
- Whether any utility categories were removed or significantly restructured
- Specific migration steps for uplifting SLDS 1 code that uses deprecated utilities
- Whether variable-density utilities (slds-var-m-*, slds-var-p-*) are SLDS 2 specific or existed in SLDS 1
- Whether the removal of decorative borders in SLDS 2 (documented in borders overview) affects border utilities usage patterns

Source references for filling this in:
- source-data/reference-documentation/salesforce-design-system-develop/packages/design-system/ui/utilities/*/RELEASENOTES.md
- SLDS 2 migration guides or release notes (if they exist in documentation)
- Design system team knowledge of SLDS 1 vs SLDS 2 utility differences
-->

---

## Responsive Utilities

SLDS utility classes support responsive design through a mobile-first breakpoint system. Responsive modifiers allow different styling at different viewport sizes without writing media queries.

### Breakpoint System

SLDS uses a mobile-first approach with three primary responsive breakpoints:

| Breakpoint | Min Width | Modifier Prefix | Use For |
|------------|-----------|-----------------|---------|
| Default (Mobile) | 0px | `slds-` | Base styling, applies to all sizes |
| Small (Tablet) | 480px (30em) | `slds-small-` | Tablet and larger |
| Medium (Desktop) | 768px (48em) | `slds-medium-` | Desktop and larger |
| Large (Wide Desktop) | 1024px (64em) | `slds-large-` | Large desktop screens |

**Max breakpoints** (uncommon, use sparingly):
- `slds-max-small-` — Up to 480px
- `slds-max-medium-` — Up to 768px
- `slds-max-large-` — Up to 1024px

### Which Utilities Support Responsive Modifiers

**Sizing utilities:**
- Width classes: `slds-size_*`, `slds-small-size_*`, `slds-medium-size_*`, `slds-large-size_*`
- Supports all fractional widths (1-of-2 through 12-of-12)

**Visibility utilities:**
- Show/hide: `slds-show_*`, `slds-hide_*` for each breakpoint
- Enables mobile vs. desktop content differentiation

**Ordering utilities:**
- Column order: `slds-order_*`, `slds-small-order_*`, `slds-medium-order_*`, `slds-large-order_*`
- Supports visual reordering up to 12 positions

### Mobile-First Approach

Always start with the mobile (base) class and progressively enhance for larger screens:

```html
<!-- Correct: Mobile-first responsive sizing -->
<div class="slds-col slds-size_1-of-1 slds-small-size_1-of-2 slds-medium-size_1-of-3 slds-large-size_1-of-4">
  100% mobile → 50% tablet → 33% desktop → 25% wide desktop
</div>

<!-- Incorrect: Desktop-first approach -->
<div class="slds-col slds-large-size_1-of-4">
  Missing base mobile sizing, will break on mobile
</div>
```

### Responsive Layout Pattern

The grid system requires `slds-wrap` when using responsive sizing that may exceed 12 columns:

```html
<div class="slds-grid slds-wrap slds-gutters">
  <div class="slds-col slds-size_1-of-1 slds-medium-size_1-of-2 slds-large-size_1-of-3">
    Column 1: Stacked mobile, half tablet, third desktop
  </div>
  <div class="slds-col slds-size_1-of-1 slds-medium-size_1-of-2 slds-large-size_1-of-3">
    Column 2
  </div>
  <div class="slds-col slds-size_1-of-1 slds-medium-size_1-of-2 slds-large-size_1-of-3">
    Column 3
  </div>
</div>
```

### Responsive Visibility Pattern

Show or hide content at specific breakpoints for device-appropriate experiences:

```html
<!-- Mobile: show hamburger menu, hide full navigation -->
<button class="slds-button slds-show slds-hide_medium">
  <svg class="slds-icon"><!-- menu icon --></svg>
  Menu
</button>

<!-- Desktop: hide hamburger, show full navigation -->
<nav class="slds-hide slds-show_medium">
  <ul class="slds-list_horizontal">
    <li><a href="#">Home</a></li>
    <li><a href="#">About</a></li>
    <li><a href="#">Contact</a></li>
  </ul>
</nav>
```

---

## Accessibility Considerations

SLDS utility classes include built-in accessibility patterns and considerations. Follow these guidelines to ensure WCAG compliance.

### DOM Order vs. Visual Order (WCAG 1.3.2)

**Critical:** The grid ordering utilities (`slds-order_*`) and flexbox reordering can create visual order that differs from DOM order. This violates WCAG 1.3.2 (Meaningful Sequence) and creates barriers for screen reader users and keyboard navigation.

**Accessibility Warning from SLDS Grid Documentation:**
> "You can visually reorder columns independently from their position in the markup, but you should avoid doing so if you wish to remain WCAG compliant."

**Rule:** Structure HTML in the correct semantic order. Do not use visual reordering utilities (`slds-order_*`). If visual reordering is required by a design specification that cannot be achieved by restructuring the DOM, ensure:
- The DOM order still makes logical sense when read sequentially
- Tab order follows a logical flow for keyboard users
- Screen reader testing confirms the experience is coherent

### Visibility Utilities and Screen Readers

Different visibility utilities have different screen reader behavior:

| Utility | Visual Display | Screen Reader | Layout Space |
|---------|----------------|---------------|--------------|
| `slds-show` | Visible | Read | Occupies space |
| `slds-hide` | Hidden | Not read | No space |
| `slds-hidden` | Hidden | Not read | Occupies space |
| `slds-assistive-text` | Hidden | Read | No space |

**Use `slds-assistive-text` when:**
- Providing context for icon-only buttons
- Adding descriptive labels for screen readers
- Including skip navigation links
- Supplementing visual-only information with text equivalents

```html
<!-- Icon button with screen reader label -->
<button class="slds-button slds-button_icon">
  <svg class="slds-icon slds-icon_small">
    <use xlink:href="/assets/icons/utility-sprite/svg/symbols.svg#edit"></use>
  </svg>
  <span class="slds-assistive-text">Edit Record</span>
</button>
```

### Focus State Preservation

The interactions utilities include focus management classes:
- `slds-has-blur-focus` — Apply blur focus styles
- `slds-has-input-focus` — Apply input-specific focus styles

Never remove focus indicators with utilities or custom CSS. Focus visibility is required for keyboard navigation (WCAG 2.4.7).

### Touch Target Sizing

When using spacing and sizing utilities for interactive elements, ensure touch targets meet minimum size requirements:
- Minimum touch target (Level AA): 24×24px (WCAG 2.5.8)
- Minimum touch target (Level AAA): 44×44px (WCAG 2.5.5)
- Recommended touch target: 48×48px

Combine padding utilities with component classes to achieve appropriate interactive areas:

```html
<!-- Adequate touch target for mobile -->
<button class="slds-button slds-button_neutral slds-p-around_medium">
  Button with comfortable touch area
</button>
```

### Truncation Accessibility

When using `slds-truncate` or `slds-line-clamp` utilities, always provide the full text:
- Add `title` attribute for hover tooltips (benefits sighted mouse users)
- Screen readers read the full content regardless of visual truncation
- Consider providing "Read more" interactions for truncated content in critical contexts

```html
<!-- Truncated text with full content accessible -->
<td class="slds-truncate" title="Full customer name visible on hover">
  Very Long Customer Name That Is Truncated Visually
</td>
```

### Color and Meaning

When using text color utilities (`slds-text-color_error`, `slds-text-color_success`, `slds-text-color_warning`), do not rely on color alone to convey meaning (WCAG 1.4.1). Supplement with:
- Icons that convey status
- Text labels that describe the state
- ARIA attributes for dynamic state changes

```html
<!-- Error message with icon, not just color -->
<div class="slds-text-color_error slds-m-top_small">
  <svg class="slds-icon slds-icon_x-small">
    <use xlink:href="/assets/icons/utility-sprite/svg/symbols.svg#error"></use>
  </svg>
  Please correct the errors below
</div>
```

---

## Implementation Workflow

Follow this sequence when implementing utility class solutions:

### Step 1: Identify the Styling Need

Determine what aspect of styling you're addressing:

- **Layout?** → Grid, position, scrollable, float utilities
- **Spacing?** → Margin and padding utilities
- **Sizing?** → Width and height utilities with responsive variants
- **Typography?** → Text, truncate, line-clamp utilities
- **Visibility?** → Show, hide, assistive-text utilities
- **Visual styling?** → Border, box, color, themes, dark mode utilities
- **Specialized patterns?** → Media object, list, description list utilities

### Step 2: Check Component Classes First

Before adding utilities, verify whether an SLDS component class already provides the pattern:

```html
<!-- Component class provides the foundation -->
<div class="slds-card">
  <div class="slds-card__header">Card Header</div>
  <div class="slds-card__body slds-card__body_inner">Card Content</div>
</div>

<!-- Add utilities only for additional composition needs -->
<div class="slds-card slds-m-bottom_medium">
  <div class="slds-card__body slds-p-around_large">
    Override default padding with utility when needed
  </div>
</div>
```

Component classes like `slds-card`, `slds-button`, `slds-form-element`, `slds-table` already include padding, borders, and structural styling. Don't recreate these patterns with utilities.

### Step 3: Compose Utilities

Combine 2-3 utilities to achieve the desired styling. The grid system demonstrates the composition pattern:

```html
<!-- Grid composition: container + behavior + spacing + sizing -->
<div class="slds-grid slds-wrap slds-gutters">
  <div class="slds-col slds-size_1-of-1 slds-medium-size_1-of-2">
    Composed layout from 4 utilities
  </div>
</div>
```

**Composition best practices:**
- Start with structural utilities (grid, position)
- Add spacing utilities (margin, padding)
- Apply typography utilities (text styling, alignment)
- Include responsive modifiers last

### Step 4: Apply Responsive Modifiers

Add breakpoint-specific overrides following mobile-first approach:

```html
<!-- Base + responsive modifiers -->
<div class="slds-col 
            slds-size_1-of-1 
            slds-small-size_1-of-2 
            slds-medium-size_1-of-3 
            slds-large-size_1-of-4">
  Progressive enhancement from mobile to large desktop
</div>
```

### Step 5: Validate Implementation

Before finalizing, verify the implementation using the Pre-Implementation Checklist below to ensure all requirements are met.

---

## Pre-Implementation Checklist

Before generating or modifying any utility class code, verify:

| Requirement | Status |
|-------------|--------|
| **Appropriateness** | |
| Utility classes used for layout, spacing, sizing, typography, visibility | [ ] |
| Component classes checked first (not recreating patterns with utilities) | [ ] |
| Utilities preferred over custom CSS where applicable | [ ] |
| Not combining more than 4-5 utilities on single element | [ ] |
| **Naming & Convention** | |
| Utility class names spelled correctly (exact SLDS naming) | [ ] |
| Underscore (`_`) used for modifiers, not double-hyphen | [ ] |
| No deprecated utilities used (checked against current SLDS docs) | [ ] |
| Naming convention followed: `slds-[property]-[direction]_[size]` | [ ] |
| **Consistency** | |
| Spacing utilities use consistent size scale (e.g., all `medium`) | [ ] |
| Typography utilities match content hierarchy (headings → body → small) | [ ] |
| Visual rhythm maintained across similar components | [ ] |
| **Responsiveness** | |
| Mobile-first approach: base class → responsive modifiers | [ ] |
| Breakpoint modifiers ordered correctly (small → medium → large) | [ ] |
| `slds-wrap` added to grids with responsive sizing | [ ] |
| Responsive visibility tested at actual breakpoints (480px, 768px, 1024px) | [ ] |
| **Accessibility** | |
| `slds-assistive-text` used for screen reader-only content | [ ] |
| `title` attributes added to all truncated text | [ ] |
| Semantic HTML tags used with utility classes (h1, h2, p, ul, li) | [ ] |
| Visual order matches DOM order (no `slds-order_*` reordering) | [ ] |
| Focus states maintained and visible (not removed by utilities) | [ ] |
| Color utilities supplemented with icons/text (not color alone for meaning) | [ ] |
| Touch targets meet minimum 44×44px size for interactive elements | [ ] |
| **Code Quality** | |
| Utilities combined efficiently (not redundant or contradictory) | [ ] |
| Markup is clean and readable | [ ] |
| Comments added for non-obvious utility combinations | [ ] |

**Target outcome:** Consistent, accessible, responsive interfaces built with composable utility classes that integrate seamlessly with SLDS component classes and styling hooks.

---

## Utility Class Categories

SLDS organizes utility classes into the following categories. For detailed per-category guidance, refer to the individual utility reference documentation.

### Layout & Positioning
- **Grid** — Flexbox layout system: `slds-grid`, `slds-col`, alignment, gutters
- **Position** — CSS positioning: `slds-is-relative`, `slds-is-absolute`, `slds-is-fixed`
- **Scrollable** — Overflow control: `slds-scrollable`, `slds-scrollable_x/y`
- **Float** — Legacy float positioning (prefer grid for new layouts)
- **Alignment** — Absolute centering: `slds-align_absolute-center`
- **Layout** — Global spacing: `slds-has-buffer`, magnet utilities

### Spacing
- **Margin** — External spacing: `slds-m-[direction]_[size]`
- **Padding** — Internal spacing: `slds-p-[direction]_[size]`

### Sizing
- **Sizing** — Fractional widths, responsive breakpoints, full width/height

### Typography
- **Text** — Headings, body text, alignment, colors, transforms
- **Truncate** — Single-line ellipsis, container-based truncation
- **Line Clamp** — Multi-line truncation (2, 3, 5, 7 lines)
- **Hyphenation** — Word breaking for long text

### Visual Styling
- **Color** — Text and background grays (prefer styling hooks)
- **Borders** — Directional borders: `slds-border_top/bottom/left/right`
- **Box** — Container styling with padding variants
- **Visibility** — Show/hide, responsive display, screen reader utilities
- **Themes** — Semantic surface theming: `slds-theme_default`, `slds-theme_inverse`, success/error/warning backgrounds
- **Dark Mode** — Future dark mode support (currently use styling hooks)

### Specialized
- **Media Object** — Image/icon with text layout pattern
- **Vertical List** — Lists with dividers, selection states
- **Horizontal List** — Inline list layouts
- **Description List** — Name-value pair layouts
- **Name Value List** — Structured data display

### Special Purpose
- **Interactions** — Link styling, focus patterns
- **Print** — Print-specific visibility

> For detailed usage guidance, code examples, and best practices for each category, refer to the [per-category utility reference documentation](ref:slds.guidance.utilities).

---

## Related Documentation

For detailed implementation guidance, refer to:

- **Utility Reference Documentation** (`slds.guidance.utilities`) — Individual category guides with complete class listings and code examples
- **Spacing and Sizing Styling Hooks** (`slds.guidance.hooks.spacing`) — For density-aware spacing and when to use hooks vs. utilities
- **Typography Overview** (`slds.guidance.overview.typography`) — For understanding type hierarchy that utilities implement
- **Borders Overview** (`slds.guidance.overview.borders`) — For understanding when borders are appropriate in SLDS 2
- **Accessibility Overview** (`slds.guidance.accessibility.overview`) — For comprehensive accessibility requirements across all utilities

