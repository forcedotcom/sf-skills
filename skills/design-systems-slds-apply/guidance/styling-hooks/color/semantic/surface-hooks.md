---

id: slds.guidance.hooks.color.surface
title: Surface Color Styling Hooks
description: Semantic hooks for page backgrounds, containers, and visual stacking contexts
summary: "Guidance for surface color hooks that express visual stacking context. Covers surface vs surface-container decision guide, elevation patterns, and dark mode compatibility."

artifact_type: reference
domain: styling-hooks
topic: color
subtopic: semantic

content_format: structured
complexity: intermediate
audience: [implementer]

tasks: [choose, implement, troubleshoot]

refs:

- slds.guidance.hooks.color.accent
- slds.guidance.hooks.color
- slds.guidance.hooks.color.feedback
- slds.guidance.hooks.color.system
- slds.guidance.utilities.dark-mode

## tags: [styling-hooks, color, semantic, surface, container, backgrounds, dark-mode]
keywords: [surface color, container color, page background, modal background, stacking context, elevation, dark mode]

# Surface Color Styling Hooks

> **Hook Selection:** Semantic hooks like surface are the first choice (85% of use cases). See [Hook Selection Hierarchy](ref:slds.guidance.hooks.color).

## Overview

A surface is a canvas that UI elements sit on. Surface colors express the visual stacking context of an app. Surface colors work together to enable sweeping changes, like dark mode. Surface colors are reserved for the bottom layer of a surface and establish the foundation for visual depth in the application.

---

## Surface vs Surface-Container: Decision Guide

### The Core Question

**Does this element create a visually isolated context, or does it exist within an existing context?**


| Characteristic                        | Use `surface-`* | Use `surface-container-*` |
| ------------------------------------- | --------------- | ------------------------- |
| Creates new stacking context          | Yes             | No                        |
| Elevated/overlays other content       | Yes             | No                        |
| Acts as foundation for child elements | Yes             | No                        |
| Exists within page's content flow     | No              | Yes                       |
| Sits on top of an existing surface    | No              | Yes                       |


### Quick Decision Tree

1. **Is this a page-level background or app canvas?** → `surface-`*
2. **Does this element overlay/elevate above the page (modal, popover, dropdown)?** → `surface-`*
3. **Does this element sit within the normal content flow on an existing background?** → `surface-container-`*

### Common Patterns


| Element             | Hook                  | Reasoning                       |
| ------------------- | --------------------- | ------------------------------- |
| Page background     | `surface-*`           | Foundational canvas             |
| Modal dialog        | `surface-*`           | Creates isolated visual context |
| Popover             | `surface-*`           | Elevated, creates new context   |
| Dropdown menu       | `surface-*`           | Elevated overlay                |
| Card on a page      | `surface-container-*` | Sits on page surface            |
| Card inside a modal | `surface-container-*` | Sits on modal surface           |
| Button              | `surface-container-*` | Sits on a surface               |
| List item           | `surface-container-*` | Part of content flow            |


### Edge Cases

- **Full-page card layout**: If a card-like element serves as the entire page background (no parent surface beneath it), use `surface-`* despite its card-like appearance.
- **Panel that overlays**: A slide-out panel that overlays page content creates a new context → `surface-`*. A panel embedded in the page flow → `surface-container-*`.
- **Nested modals**: Each modal creates its own surface. A confirmation dialog inside a modal uses `surface-`* for its background.

### Warning: CSS Class Names Are Irrelevant

The element's class name (e.g., `.card-container`, `.modal-content`, `.panel-wrapper`) does **not** determine hook choice. An element named `.card-container` might use `surface-`* if it's the page-level background, or `surface-container-*` if it's a card sitting on a surface.

**Always base the decision on visual stacking context, not naming conventions.**

---

## `--slds-g-color-surface-`*

### Description

Surface colors used for backgrounds and large areas of the application that express a new visual stacking context to create visual depth.

### Available Hooks

- `--slds-g-color-surface-1` - Primary page background (lightest, typically white)
- `--slds-g-color-surface-2` - Secondary page background (light gray, for visual distinction)
- `--slds-g-color-surface-3` - Tertiary page background (medium gray, for additional hierarchy)
- `--slds-g-color-surface-inverse-1` - Primary inverse surface background color
- `--slds-g-color-surface-inverse-2` - Secondary inverse surface background color

> **Note on Inverse Hooks:** Inverse hooks provide dark background colors designed for dark mode or inverted color schemes. They enable light content on dark backgrounds, as opposed to standard hooks which provide dark content on light backgrounds. Use inverse hooks for dark mode implementations, high-contrast sections, or visual emphasis through color inversion.

### Understanding Surface Numbering: NOT State-Based

**Critical Distinction**: Unlike accent or feedback hooks, surface variant numbers (1-2-3) do **NOT** represent interaction states (default/hover/active). They represent:

1. **Color progression from light to dark** (1 = lightest, 3 = darkest)
2. **Designer's aesthetic choice** for visual hierarchy or separation
3. **Contextual background needs** (e.g., white cards need gray backgrounds to stand out)

**When to choose which:**

- `**surface-1` (white)**: Clean, high-contrast base; use when cards/containers need strong definition
- `**surface-2` (light gray)**: Softer separation; use when layering elements without harsh white backgrounds
- `**surface-3` (medium gray)**: Additional depth; rare in practice, used for specific hierarchical needs

**NOT a rule**: There is no algorithmic decision tree. Designers choose based on composition, not function.

### Usage

#### Do

- Use surface colors for application backgrounds to establish the base canvas
- Use surface colors for panels that create new visual contexts
- Use surface colors for modal/dialog backgrounds (modals create isolated visual contexts, making them surfaces despite containing content)
- Apply surface colors to docked surfaces that establish surfaces
- Use surface colors for popovers and other elevated UI elements
- Anything that comes into the application's view with a higher stacking context establishes a new surface

#### Don't

- Avoid applying any decoration, brand bands, or textures to application backgrounds
- Avoid using for container elements that sit on top of surfaces (use surface-container instead)
- Avoid mixing surface colors with container colors in the same layer
- Don't use surface colors for text or icon fills
- **Don't assume numbering indicates states**: Surface variants are NOT for hover/active states—those typically use surface-container variants, accent colors, or component-level styling hooks depending on the theme

#### Context

- Application background (base canvas)
- Panels that establish new surfaces
- Modals and dialog backgrounds
- Docked containers
- Popovers and elevated UI elements
- Any element with a higher stacking context than previous surfaces

### Accessibility

- Surface colors are designed to work with on-surface colors for proper contrast
- Ensure WCAG 2.1 color contrast requirements by pairing with appropriate on-surface values
- Use `--slds-g-color-on-surface-`* for text and icons on surface backgrounds. Choose on-surface level based on content importance and required contrast, not strict number matching. For example, pair `--slds-g-color-surface-1` with `--slds-g-color-on-surface-1` for consistency, though other on-surface levels may be used based on emphasis needs while maintaining accessibility compliance

---

## `--slds-g-color-surface-container-*`

### Description

Surface container colors reserved for elements that sit on top of a surface and contain other UI elements or artifacts, such as text or icons.

### Available Hooks

- `--slds-g-color-surface-container-1` - Lightest container background (typically white)
- `--slds-g-color-surface-container-2` - Light gray container background
- `--slds-g-color-surface-container-3` - Medium gray container background for additional hierarchy
- `--slds-g-color-surface-container-inverse-1` - Primary inverse surface container background
- `--slds-g-color-surface-container-inverse-2` - Secondary inverse surface container background

> **Note on Inverse Hooks:** Inverse hooks provide dark background colors for containers in dark mode or inverted color schemes. They work with on-surface-inverse hooks to maintain proper contrast for light content on dark container backgrounds.

### Overlap with Surface Hooks

Surface and surface-container hooks use the **same color values** (e.g., `surface-1` and `surface-container-1` are both white). The distinction is **semantic**, not visual.

See [Surface vs Surface-Container: Decision Guide](#surface-vs-surface-container-decision-guide) for comprehensive guidance on when to use each.

### State Progression Logic

**Design Intent-Dependent Patterns**: Unlike semantic accent or feedback containers with universal state progressions, surface-container state behavior varies based on design intent and interaction context:

- **For neutral hover states**: Use `surface-container-2` for hover states when default is `surface-container-1`
- **For brand-emphasized hover states**: Use brand colors (e.g., `brand-base-90` from the color palette) instead of surface-container variants
- **Context-Dependent**: Choice also depends on parent surface color and desired contrast level

**Why the variation**: Surface containers serve as neutral, foundational backgrounds for UI elements. Interactive hover states can either maintain neutral emphasis (using surface-container progression) or add brand emphasis (using brand colors from the palette), depending on the design's intent for that specific component.

**Best Practice**: Refer to component-level styling hooks for specific interactive patterns. Button, card, and list item components each have their own hover state definitions that may use surface-container variants, brand colors, accent colors, or component-specific styling hooks based on design requirements.

### Usage

#### Do

- Use surface container colors for cards that sit on an established surface (page, modal, panel)
- Apply surface container colors to button icons that contain content
- Use surface container colors for button backgrounds
- Use surface container colors for tabset backgrounds
- One of the clearest signals for using surface container colors is if the element contains text or icons

#### Don't

- Avoid using for the base application background
- Avoid using for elements that don't contain other UI elements
- Avoid mixing with surface colors on the same visual layer
- Avoid using for decorative elements that don't establish containers

#### Context

- Cards within a page or modal (not full-page card layouts)
- Button backgrounds
- Button icon containers
- Tabset backgrounds
- Any element that contains text, icons, or other UI artifacts
- Interactive containers that sit above surfaces

### Accessibility

- All surface container colors are designed to work with `--slds-g-color-on-surface-`* values for proper contrast
- Ensures proper WCAG 2.1 color contrast requirements are met
- Choose on-surface level based on content importance and required contrast, not strict number matching. For example, pair `--slds-g-color-surface-container-3` with `--slds-g-color-on-surface-3` for consistency, though other on-surface levels may be used based on emphasis needs while maintaining accessibility compliance
- Valid to use accent or feedback colors for text/icons on top of surface containers as alternatives (e.g., `--slds-g-color-accent-1`)

---

## `--slds-g-color-on-surface-*`

### Description

Foreground colors for text or icons that appear on top of a surface or surface container, ensuring proper color contrast requirements.

### Available Hooks

- `--slds-g-color-on-surface-1` - De-emphasized text (lowest emphasis, for captions and secondary content)
- `--slds-g-color-on-surface-2` - Body text (medium emphasis, for standard content and labels)
- `--slds-g-color-on-surface-3` - High-emphasis text (highest emphasis, for headings and primary content)
- `--slds-g-color-on-surface-inverse-1` - Primary inverse foreground color for inverse surfaces
- `--slds-g-color-on-surface-inverse-2` - Secondary inverse foreground color for inverse surfaces

> **Note on Inverse Hooks:** Inverse hooks provide light foreground colors (text/icons) designed for use on dark surface or surface-container inverse backgrounds. They ensure proper contrast when displaying content in dark mode or inverted color schemes.

### Pairing Logic: Contrast Over Number-Matching

While the naming suggests pairing `on-surface-1` with `surface-1`, this is **NOT a strict rule**. Choose on-surface variants based on:

1. **Content importance**: Headlines use `on-surface-3` (highest contrast), body text uses `on-surface-2`, labels/captions use `on-surface-1`
2. **Accessibility requirements**: Always maintain 4.5:1 contrast ratio
3. **Visual hierarchy needs**: NOT the surface variant number

All three `on-surface` variants can appear on the same `surface-container-1` background.

### Usage

#### Do

- Use on-surface colors for text that appears on surface or surface container backgrounds
- Use on-surface colors for icons displayed on surfaces
- Use on-surface colors for any content that needs to meet WCAG 2.1 color contrast requirements

#### Don't

- Avoid using on accent color backgrounds (use on-accent colors instead)
- Avoid using on feedback color backgrounds (use on-feedback colors instead)
- Avoid using for large background areas
- Avoid using as standalone colors without appropriate surface backgrounds

#### Context

- Text on surface backgrounds
- Icons on surface or container backgrounds
- Body copy and content text
- UI labels and descriptive text
- Any foreground content requiring readability

#### Typography-Specific Usage


| Use Case         | Description                         |
| ---------------- | ----------------------------------- |
| Body text        | Standard paragraph text and content |
| Placeholder text | Input field placeholders            |
| Field labels     | Form field labels and descriptions  |
| Sub-headings     | Minor headings below primary titles |
| Taglines         | Supporting text and captions        |


**Background Requirements**: Use on backgrounds with lightness values 90-100 for optimal contrast.

**Applies to**: `--slds-g-color-on-surface-1`


| Use Case            | Description                                       |
| ------------------- | ------------------------------------------------- |
| Secondary text      | Supporting content and descriptions               |
| Tertiary headings   | Lower-hierarchy headings                          |
| Dark body copy      | Content requiring more emphasis than on-surface-1 |
| Filled input fields | Text entered by users in form fields              |


**Background Requirements**: Use on backgrounds with lightness values 70-100 for optimal contrast.

**Applies to**: `--slds-g-color-on-surface-2`


| Use Case              | Description                                |
| --------------------- | ------------------------------------------ |
| Page titles           | Primary titles for pages or major sections |
| Component titles      | Headings for cards, modals, and containers |
| High-emphasis content | Content requiring maximum visual weight    |


**Background Requirements**: Use on backgrounds with lightness values 65-100 for optimal contrast.

**Applies to**: `--slds-g-color-on-surface-3`


| Use Case                       | Description                                 |
| ------------------------------ | ------------------------------------------- |
| Title text on dark backgrounds | Page and component titles on dark surfaces  |
| Body text on dark backgrounds  | Content text on dark or colored backgrounds |


**Background Requirements**: Use on backgrounds with lightness values 0-50 for optimal contrast.

**Applies to**: `--slds-g-color-on-surface-inverse-1`

### Accessibility

- All on-surface colors are AA compliant and maintain a 4.5:1 contrast ratio with their corresponding surface backgrounds
- Designed specifically to meet Web Content Accessibility Guidelines (WCAG) 2.1
- Best paired with matching surface or surface-container colors. Choose on-surface level based on content importance and required contrast, not strict number matching. For example, pair `--slds-g-color-on-surface-1` with `--slds-g-color-surface-1` or `--slds-g-color-surface-container-1` for consistency, though other pairings may be used based on emphasis needs while maintaining accessibility compliance
- Text links use `--slds-g-color-accent-2` (not accent-1) on surface backgrounds for accessibility compliance
- Disabled text uses `--slds-g-color-on-disabled-2`
- Feedback text uses appropriate `--slds-g-color-on-error-`*, `--slds-g-color-on-warning-*`, etc.

