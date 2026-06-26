---
id: slds.guidance.hooks.borders
title: Borders and Radius Styling Hooks
description: Styling hooks for border width, border radius, and structural separation
summary: "Guidance for border and radius styling hooks. Covers border width hooks for interactive boundaries, radius hooks for corner rounding, and SLDS 2 philosophy of minimal border usage."

artifact_type: reference
domain: styling-hooks
topic: borders

content_format: structured
complexity: intermediate
audience: [implementer]

tasks: [choose, implement, troubleshoot]

refs:
  - slds.guidance.hooks.color.feedback
  - slds.guidance.hooks.color
  - slds.guidance.hooks
  - slds.guidance.hooks.spacing
  - slds.guidance.hooks.shadows
tags: [styling-hooks, borders, radius, corners, visual-structure]
keywords: [border width, border radius, corners, interactive boundaries, focus states, visual separation]
---

# Borders and Radius Styling Hooks

## Overview

Borders and radius styling hooks establish structure, clarity, and visual consistency in UI interfaces. All border styling hooks are prefixed with `--slds-g-` and are followed by a border-related property name. These hooks ensure that border treatments remain consistent, themeable, and aligned with SLDS design principles.

**Important:** Border and radius hooks are NOT density-aware. Unlike spacing and typography hooks, border values remain constant regardless of comfy or compact display density settings.

---

## `--slds-g-sizing-border-*`

### Description

Border width hooks specify the thickness of borders. Use these hooks to define the thickness of lines that outline components, containers, and other visual elements. The scale ranges from subtle separation to strong emphasis.

**Hook Pattern:** `--slds-g-sizing-border-*`

### Usage

####  Do

- Use border width hooks to specify the pixel width of borders
- Use border width hooks for creating visual separation between content areas without overwhelming the interface
- Use border width hooks for indicating interactive boundaries on form elements like inputs and textareas
- Use `--slds-g-sizing-border-1` for standard interactive elements such as buttons, inputs, and badges
- Use `--slds-g-sizing-border-3` specifically for focus states where additional visual emphasis is needed
- SLDS 2 favors minimal border usage — use borders purposefully for structure and meaning

####  Don't

- Avoid using borders decoratively around cards and containers in SLDS 2 (this is a design philosophy shift from SLDS 1)
- Avoid hard-coded pixel values instead of border width hooks
- Avoid inconsistent border widths across similar elements

#### Context: When to Use Border Width Hooks

**Use border width hooks when building:**

| Component Type | Border Application | Recommended Hook |
|----------------|-------------------|------------------|
| Form inputs (text, textarea, combobox) | Interactive boundary | `--slds-g-sizing-border-1` |
| Buttons | Interactive boundary | `--slds-g-sizing-border-1` |
| Badges | Subtle outline | `--slds-g-sizing-border-1` |
| Focus states | Emphasis ring | `--slds-g-sizing-border-3` |
| Divider lines | Content separation | `--slds-g-sizing-border-1` |

**SLDS 2 Philosophy:** Apply borders sparingly. Use consistent thickness and color. Prefer light/subtle borders for separation without overwhelming the interface.

### Accessibility

- Use `--slds-g-sizing-border-3` for focus states to ensure sufficient visibility for keyboard users
- Borders must maintain minimum 3:1 contrast ratio with adjacent surfaces (40-point separation in SLDS grade system)
- Accessibility requirements apply — consult your project's accessibility standards

---

## `--slds-g-radius-border-*`

### Description

Border radius hooks manage the curvature of UI elements' corners, impacting the perceived softness or hardness of components. Use these hooks to establish consistent rounded corner styles across components. The scale provides options from subtle rounding to fully circular shapes.

**Hook Patterns:**
- `--slds-g-radius-border-*` — Numbered radius scale
- `--slds-g-radius-border-circle` — Circular elements
- `--slds-g-radius-border-pill` — Pill-shaped elements

### Usage

### Component Radius Reference

| Hook | Components |
|------|------------|
| `--slds-g-radius-border-1` | Badges, Checkboxes |
| `--slds-g-radius-border-2` | Text Inputs, Comboboxes, Text Areas, Tooltips |
| `--slds-g-radius-border-3` | Menus, Popovers |
| `--slds-g-radius-border-4` | Cards, Modals, Docked Composers |
| `--slds-g-radius-border-circle` | Buttons, Button Icons, Avatars, Radios, Pills |

### Usage

####  Do

- Apply consistent radius to create a cohesive design throughout the interface
- Match radius scale to content density — smaller radius for dense content, larger for spacious elements

####  Don't

- Avoid mixing sharp corners (0 radius) with rounded corners within the same component — mixing these styles can create a visually jarring experience and reduce design harmony
- Avoid hard-coded pixel or rem values instead of radius hooks
- Avoid inconsistent radius values across similar elements
- Avoid radius values that conflict with the brand's visual identity

#### Context

- Establish a consistent style for rounded corners across components such as cards, modals, and buttons
- Create a modern, approachable aesthetic that aligns with the brand identity
- Improve usability by subtly guiding users' focus to key interface elements

### Accessibility

- Rounded corners must not obscure focus indicators or reduce visible border contrast
- Ensure focus states remain clearly visible regardless of radius value

---

## `--slds-g-color-border-*` (Summary)

### Description

Border color hooks are part of the SLDS semantic color system. They define colors for borders based on semantic meaning rather than specific color values. Use these hooks to ensure border colors adapt to themes, maintain accessibility, and communicate appropriate meaning.

> **For complete border color documentation**, see the Color Overview and [Feedback Hooks](ref:slds.guidance.hooks.color.feedback) for error/warning/success border patterns.

**Key Border Color Hook Patterns:**

- `--slds-g-color-border-*` — Neutral borders for functional structure, separation, and dividers
- `--slds-g-color-border-accent-*` — Branded emphasis and thematic exceptions
- `--slds-g-color-border-error-*` — Error states and destructive actions
- `--slds-g-color-border-success-*` — Success states
- `--slds-g-color-border-warning-*` — Warning states
- `--slds-g-color-border-disabled-*` — Disabled elements
- `--slds-g-color-border-inverse-*` — Dark backgrounds

### Usage

####  Do

- Use `--slds-g-color-border-1` for decorative borders and divider lines between content
- Use `--slds-g-color-border-2` as the standard choice for functional or interactive components
- Use accent border colors only for branded containers or specific thematic emphasis where neutral borders are insufficient
- Use error/warning/success border colors exclusively for communicating system feedback states
- Use inverse border colors when placing elements on dark backgrounds
- Border colors should reinforce semantic meaning, not serve as decoration

####  Don't

- Avoid using feedback border colors (error, warning, success) for general styling — reserve for actual states
- Avoid hard-coded color values instead of border color hooks
- Avoid border colors that don't meet contrast requirements with adjacent surfaces
- Avoid using accent border colors for standard interactive elements where neutral hooks are the established system pattern
- Avoid using accent border colors when the element doesn't represent a specific branded or thematic exception
- Avoid mixing border color semantics inconsistently (e.g., error border on non-error element)
- Avoid using inverse borders on light backgrounds (they won't be visible)

#### Context

- Form field borders (neutral for default, accent for focus, error for validation)
- Card and container borders (neutral, typically subtle)
- Status indicator borders (error, warning, success as appropriate)
- Disabled state borders
- Dark theme and inverse context borders
- Divider lines between content sections

### Accessibility

- **Interactive elements** (buttons, inputs): Use `--slds-g-color-border-2` for higher contrast
- **Non-interactive elements** (dividers): Use `--slds-g-color-border-1`
- Border colors must maintain minimum 3:1 contrast with adjacent surfaces (40-point separation)
- Color alone must not be the only indicator of state — combine with icons, text, or other cues
- Focus borders must use high-contrast colors; pair with `--slds-g-sizing-border-3` for visibility

---

### SLDS 2 Philosophy Reminder

SLDS 2 favors minimal border usage. Before applying borders, ask:
- Can spacing achieve the same visual separation?
- Can shadows create the desired depth?
- Is this a holdover from SLDS 1 patterns?

Use borders purposefully for structure, interactivity indication, and state communication — not as default decoration.

> **Complete Philosophy:** SLDS 2 favors minimal border usage — apply borders purposefully for structure, interactivity indication, and state communication.

