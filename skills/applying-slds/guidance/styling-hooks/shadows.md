---
id: slds.guidance.hooks.shadows
title: Shadows Styling Hooks
description: Styling hooks for depth shadows, directional shadows, and inset shadows
summary: "Guidance for shadow styling hooks that establish visual hierarchy and elevation. Covers depth shadows (1-4), directional shadows, and inset shadows for pressed/focused states."

artifact_type: reference
domain: styling-hooks
topic: shadows

content_format: structured
complexity: intermediate
audience: [implementer]

tasks: [choose, implement, troubleshoot]

refs:
  - slds.guidance.hooks
  - slds.guidance.hooks.borders
  - slds.guidance.hooks.color.surface
tags: [styling-hooks, shadows, elevation, depth, visual-hierarchy]
keywords: [shadow depth, elevation, stacking order, directional shadow, inset shadow, focus shadow]
---

# Shadows Styling Hooks

## Overview

Shadow styling hooks establish visual hierarchy, depth, and elevation in UI interfaces. All shadow styling hooks are prefixed with `--slds-g-` for global scope, `--slds-s-` for shared scope, or `--slds-c-` for component scope, followed by the shadow name. For example, `--slds-g-shadow-1` is the styling hook for a shadow depth of 1.

---

## `--slds-g-shadow-*`

### Description

Depth shadow hooks communicate elevation and visual hierarchy. Use these hooks to indicate which elements appear above others in the stacking order. Higher shadow values indicate elements that are visually higher in the stacking order.

**Hook Pattern:** `--slds-g-shadow-{n}` where `{n}` is the depth level

### Usage

####  Do

- Match shadow values to stacking order — elements with higher stacking order should have higher shadow values
- Leverage z-index to manage stacking order alongside shadow values
- Use depth shadows for elements that need to appear above the base surface

####  Don't

- Avoid applying shadows to base level components — components that sit on the surface and don't cover other components should not have shadows in SLDS 2

#### Context

| Shadow Hook | Components |
|-------------|------------|
| `--slds-g-shadow-1` | Page headers, joined tables, filter panels, dropdowns, inline edit, images, slider handles |
| `--slds-g-shadow-2` | Menu, docked form footer, docked utility bar, color picker, notifications |
| `--slds-g-shadow-3` | Panel, docked composer, tooltip, toast |
| `--slds-g-shadow-4` | Modal, popover, App Launcher |

**Note:** `shadow-5` and `shadow-6` are aliases that inherit from `shadow-4`.

---

## `--slds-g-shadow-{direction}-*`

### Description

Directional shadow hooks allow shadows to be cast in specific directions. Use these hooks for components positioned against edges of the screen where the shadow direction matters.

**Hook Pattern:** `--slds-g-shadow-{direction}-{n}` where `{direction}` is the shadow direction and `{n}` is the depth level

**Available Directions:**
- `block-start` — Upward shadow
- `block-end` — Downward shadow (inherits from base `shadow-{n}`)
- `inline-start` — Left shadow
- `inline-end` — Right shadow

### Usage

####  Do

- Use directional shadows for panels and side-docked components
- Use directional shadows when components are positioned against screen edges
- Use `shadow-3 left` or `shadow-3 right` on panels depending on screen position

#### Context

- Panels use directional shadows based on which side of the screen they are placed
- `block-start` and `block-end` follow CSS logical properties (vertical axis)
- `inline-start` and `inline-end` follow CSS logical properties (horizontal axis)

---

## `--slds-g-shadow-{type}-focus-*`

### Description

Focus shadow hooks provide visual feedback for keyboard navigation and accessibility. Use these hooks to ensure focus states meet accessibility requirements across all backgrounds.

**Hook Pattern:** `--slds-g-shadow-{type}-focus-{n}` where `{type}` is the focus style and `{n}` is the focus level

**Available Types:**
- `outline-focus` — Simple outline focus
- `outset-focus` — Double ring outset focus (white inner ring, brand outer ring)
- `inset-focus` — Single ring inset focus
- `inset-inverse-focus` — Double ring inset focus (brand inner, white outer)

### Usage

####  Do

- Focus states within SLDS 2 consist of a white border outline surrounded by a dark blue border outline
- This style ensures that the focus state passes accessibility requirements on any background

#### Context

- Focus states within enhanced Lightning UI are applied via shadow
- The double-ring focus pattern provides sufficient contrast on both light and dark backgrounds

### Accessibility

- Focus shadows ensure minimum 3:1 contrast against any background color
- The white + dark blue double-ring pattern guarantees visibility on both light and dark backgrounds
- Focus visibility is required for WCAG 2.1 keyboard navigation compliance
- Accessibility requirements apply — consult your project's accessibility standards

---

## `--slds-s-button-shadow-*`

### Description

Button shadow hooks control the visual states for button interactions. Use these hooks for focus, active (pressed), and hover states on buttons.

**Available Hooks:**
- `--slds-s-button-shadow-focus` — Focus state for neutral buttons
- `--slds-s-button-shadow-focus-inverse` — Focus state for inverse buttons
- `--slds-s-button-shadow-active` — Pressed/active state (inset shadow)
- `--slds-s-button-brand-shadow-hover` — Hover lift effect for brand buttons
- `--slds-s-button-bordered-shadow-hover` — Hover lift effect for bordered/neutral buttons

### Usage

####  Do

- Button components use a hover bevel and inner shadow on click that is separate from the elevation system
- `button-shadow-active` is used on all buttons when pressed, regardless of color or border

####  Don't

- Avoid using bevel and inset shadows in custom situations — they are only used on buttons and inputs where specified

#### Context

- Active state uses inset shadows to create a "pressed in" appearance
- Hover state uses drop shadows with transform for a "lift" effect
- Focus state uses the standard focus ring pattern

---

## `--slds-s-input-shadow-*`

### Description

Input shadow hooks control the visual states for input field interactions. Use these hooks for focus and validation states on input containers.

**Available Hooks:**
- `--slds-s-input-shadow-focus` — Focus state for input containers (includes inset shadow + focus ring)
- `--slds-s-input-shadow-invalid` — Error state for input containers

### Usage

####  Do

- Input focus combines an inset shadow with the standard focus ring
- Use input shadow hooks for text inputs, comboboxes, and text areas

####  Don't

- Avoid using input inset shadows in custom situations — they are only used where specified in the design system

#### Context

- Focus state combines visual depth (inset shadow) with accessibility (focus ring)
- Invalid state may remove shadows to emphasize the error border treatment

---

## `--slds-s-mark-shadow-*`

### Description

Mark shadow hooks control the visual states for checkbox, radio button, and toggle interactions. Use these hooks for focus and checked states on mark elements.

**Available Hooks:**
- `--slds-s-mark-shadow-focus` — Focus state for checkboxes, radios, and toggles
- `--slds-s-mark-shadow-checked` — Checked/selected state (inset shadow)

### Usage

####  Do

- `mark-shadow-checked` is used on selected or active checkboxes, radio buttons, and checkbox toggles
- Use mark shadow hooks for indicating the selected state with visual depth

####  Don't

- Avoid using mark inset shadows in custom situations — they are only used on marks where specified

#### Context

- Checked state uses inset shadow to create visual depth indicating selection
- Focus state uses the standard focus ring pattern for accessibility

---

## `--slds-c-button-{variant}-shadow-hover`

### Description

Component-level button variant shadow hooks provide hover effects for specific button variants. Use these hooks when implementing success, destructive, or inverse button variants.

**Available Hooks:**
- `--slds-c-button-success-shadow-hover` — Hover shadow for success buttons
- `--slds-c-button-destructive-shadow-hover` — Hover shadow for destructive buttons
- `--slds-c-button-inverse-shadow-hover` — Hover shadow for inverse buttons

### Usage

#### Context

- These hooks provide variant-specific hover lift effects
- Each uses a tinted shadow that matches the button's color scheme
- Used in combination with transform for the lift animation effect


