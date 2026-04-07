---
id: slds.guidance.hooks.color.accent
title: Accent Color Styling Hooks
description: Semantic hooks for brand identity, interactive elements, and visual emphasis
summary: "Guidance for accent color hooks used for links, buttons, and brand emphasis. Covers accent, accent-container, border-accent, and on-accent hooks with state progression and accessibility pairing."

artifact_type: reference
domain: styling-hooks
topic: color
subtopic: semantic

content_format: structured
complexity: intermediate
audience: [implementer]

tasks: [choose, implement, troubleshoot]

refs:
  - slds.guidance.hooks.color.surface
  - slds.guidance.hooks.color
  - slds.guidance.hooks.color.feedback

tags: [styling-hooks, color, semantic, accent, brand, interactive, links, buttons]
keywords: [accent color, brand color, links, buttons, interactive elements, visual hierarchy, hover states]
---

# Accent Color Styling Hooks

> **Hook Selection:** Semantic hooks like accent are the first choice (85% of use cases). See [Hook Selection Hierarchy](ref:slds.guidance.hooks.color).

## Overview

Accent colors express a brand's accent color throughout the user interface or to draw attention to an action. Brand colors highlight actions on the page through buttons and links.

---

## `--slds-g-color-accent-*`

### Description
Accent colors that are generally used for text or icons.

### Available Hooks
- `--slds-g-color-accent-1` - Lightest accent color
- `--slds-g-color-accent-2` - Medium accent color
- `--slds-g-color-accent-3` - Darkest accent color

### State Progression Logic

The variant number you use depends on the default state's contrast requirements:
- **If default state uses `accent-1`**: Use `accent-2` for hover states
- **If default state uses `accent-2`**: Use `accent-3` for hover states

**Why this matters**: `accent-2` is often the default for links and interactive text because `accent-1` may not meet accessibility contrast requirements on non-white backgrounds. The hover state then uses the next darker variant.

### Usage

####  Do
- Use accent colors for brand identity and interactive elements (links, buttons, icons)
- Use accent colors for emphasizing key actions and content
- Use accent colors to create visual hierarchy with brand colors
<!-- - Consider brand-base-90 and 80 for backgrounds and hover states for menu type components using the brand-base styling hook -->

####  Don't
- Avoid using for large background areas
- Avoid using for container backgrounds
- Avoid for body text or long-form content
- Avoid using without ensuring proper contrast
- Avoid using as the only color indicator for status
- Avoid using system colors or colors from another group like surface colors in combination with accent colors

#### Context
- Links and interactive text (commonly use accent-2 by default, accent-3 on hover)
- Brand elements and identity
- Icon fills and accents
- Icon Buttons and interactive text
- Indicates active or selected states in components
- **Note**: Interactive icons that respond to hover are treated as Button Icon components and handle the state changes on their own.

### Accessibility
- All accent colors are AA compliant and maintain a 4.5:1 contrast using semantic colors with a 50 gradepoint difference between the background and foreground
- Best paired with on-accent colors for foreground text and icons. Choose on-accent level based on content importance and required contrast, not strict number matching. For example, pair `--slds-g-color-accent-1` with `--slds-g-color-on-accent-1` for consistency, though other on-accent levels may be used based on emphasis needs while maintaining accessibility compliance

---

## `--slds-g-color-accent-container-*`

### Description
Background fills using accent colors for containers.

### Available Hooks
- `--slds-g-color-accent-container-1` - Lightest accent container background
- `--slds-g-color-accent-container-2` - Medium accent container background
- `--slds-g-color-accent-container-3` - Darkest accent container background

### State Progression Logic

Container variants follow a straightforward state progression pattern:
- **If default state uses `accent-container-1`**: Use `accent-container-2` for hover/active states
- **If default state uses `accent-container-2`**: Use `accent-container-3` for hover/active states

**Why this pattern**: Higher numbered variants provide increased visual emphasis and contrast, making interactive states clearly distinguishable from default states.

### Usage

####  Do
- Use accent container colors for containers such as brand buttons and their hover and active states
- Use accent container colors for interactive container backgrounds that need accent color emphasis
- Use accent container colors for interactive element backgrounds
- Use accent container colors for hover/focus/active states of interactive containers

####  Don't
- Avoid using for non-interactive decorative elements
- Avoid using as primary or secondary brand colors outside interactive container contexts
- Avoid for subtle interactions where less emphasis is needed
- Avoid using for large areas without specific interaction requirements
- Avoid without proper interaction context
- Avoid using system colors or colors from another group like surface colors in combination with accent container colors

**Important**: Accent containers carry brand significance indicating interaction and should only be used for interactive elements, not for non-interactive decorative purposes.

#### Context
- Brand button backgrounds and their interactive states
- Interactive element backgrounds
- Hover/focus/active state backgrounds for interactive containers
- Interactive content areas requiring brand emphasis

### Accessibility
- All container colors are AA compliant and maintain a 4.5:1 contrast using semantic colors with a 50 gradepoint difference between the background and foreground
- Best paired with on-accent colors for foreground text and icons. Choose on-accent level based on content importance and required contrast, not strict number matching. For example, pair `--slds-g-color-accent-container-1` with `--slds-g-color-on-accent-1` for consistency, though other on-accent levels may be used based on emphasis needs while maintaining accessibility compliance

---

## `--slds-g-color-border-accent-*`

### Description
Accent border colors for brand-colored outlines when higher visual emphasis is required beyond neutral borders.

### Available Hooks
- `--slds-g-color-border-accent-1` - Lightest accent border color
- `--slds-g-color-border-accent-2` - Medium accent border color
- `--slds-g-color-border-accent-3` - Darkest accent border color

### Usage

####  Do
- Use neutral border hooks (`--slds-g-color-border-2`) as the primary choice for standard interactive elements to ensure cross-component consistency
- Use border-accent hooks only when explicit brand-colored outlines are required by the design
- Use border-accent hooks for high-emphasis brand identity elements that need to stand out from standard UI
- Pair with accent container colors for unified brand treatments

####  Don't
- Avoid using border-accent hooks as the default border choice — prefer neutral borders unless brand emphasis is explicitly needed
- Avoid using as the default border for interactive elements unless a high-contrast brand treatment is specifically required
- Avoid using for large background areas (borders should define, not fill)
- Avoid for body text or long-form content
- Avoid using without ensuring proper contrast
- Avoid using as the only color indicator for status
- Avoid using non-border accent colors on borders to achieve a border with an accent color

#### Context
- Brand button outlines
- Interactive element outlines

**Note**: To align with current design patterns, most interactive components—including brand-variant buttons—rely on neutral border hooks (`--slds-g-color-border-2`) or are borderless. Border-accent hooks are primarily reserved for specialized theming, custom brand components, or specific focus indicators where standard neutral borders do not provide sufficient emphasis.

### Accessibility
- All border accent colors are AA compliant and maintain a 4.5:1 contrast using semantic colors with a 50 gradepoint difference between the background
- Works best on neutral backgrounds or paired with matching accent container colors.
- Maintains visibiltiy and consisteny when paired with `--slds-g-sizing-border-*` sizing hooks

---

## `--slds-g-color-on-accent-*`

### Description
Foreground colors for content placed on accent color backgrounds, such as text and icons.

### Available Hooks
- `--slds-g-color-on-accent-1` - Lightest foreground color for accent backgrounds
- `--slds-g-color-on-accent-2` - Medium foreground color for accent backgrounds
- `--slds-g-color-on-accent-3` - Darkest foreground color for accent backgrounds

### Usage

####  Do
- Use on-accent colors for text placed on accent color backgrounds
- Use on-accent colors for icons displayed on accent color backgrounds
- Use on-accent colors for any content that needs to be readable on accent backgrounds
- Pair on-accent colors with the corresponding accent background color

####  Don't
- Avoid using on light or non-accent backgrounds
- Avoid using without the corresponding accent background
- Avoid using for decorative elements that don't require readability
- Avoid mixing with non-matching accent backgrounds

#### Context
- Text on accent backgrounds
- Icons on accent surfaces

### Accessibility
- All on-accent colors are AA compliant and maintain a 4.5:1 contrast using semantic colors with a 50 gradepoint difference between the background
- Works best paired with a corresponding accent background color. Choose on-accent level based on content importance and required contrast, not strict number matching. For example, pair `--slds-g-color-on-accent-1` with `--slds-g-color-accent-1` or `--slds-g-color-accent-container-1` for consistency, though other pairings may be used based on emphasis needs while maintaining accessibility compliance

