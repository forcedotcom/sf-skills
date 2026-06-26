---
id: slds.guidance.overview.borders
title: Borders and Radius Overview
description: Foundational principles and constraints for border and radius decisions in SLDS
summary: "Comprehensive border guidance covering SLDS 2 design philosophy (minimal borders), border width usage, radius categories, and when borders are appropriate. Critical for SLDS 1 to SLDS 2 migration."

artifact_type: overview
domain: overviews
topic: borders

content_format: narrative
complexity: foundational
audience: [implementer, designer]

tasks: [learn, choose, implement]

refs:
  - slds.guidance.hooks.borders

tags: [borders, radius, corners, visual-structure, slds2-migration]
keywords: [border width, border radius, corners, SLDS 2 design, minimal borders, visual separation, container borders]
---

# Borders and Radius Guidance for SLDS Implementation

**Purpose:** This document provides the foundational principles and constraints for all border and radius decisions in Salesforce Lightning Design System. Borders and radiuses are basic visual design elements that help create clarity, hierarchy, and a consistent look. When implementing components and layouts, follow these guidelines to ensure visual harmony and cohesion across all experiences.

---

## Core Principles

When working with borders and radiuses in UI interfaces, adhere to these foundational principles:

1. **Create clarity through structure.** Borders delineate components and sections for better readability and navigation. Use them to separate content areas, indicate clickable elements, or highlight active states.

2. **Support hierarchy and meaning.** Borders differentiate elements to show importance or interactivity. Ensure border treatments draw attention to important features without overwhelming the experience.

3. **Maintain consistency and harmony.** Apply consistent thickness, color, and radius across similar elements. Avoid mixing sharp and rounded corners within the same component to keep designs looking polished and cohesive.

4. **Foster accessibility.** Use subtle but effective visual cues to support usability for all users. Ensure borders remain visible and easy to perceive across all screen sizes and resolutions.

---

## SLDS 2 Design Philosophy

**CRITICAL:** SLDS 2 does not use borders around cards and components, unlike SLDS 1.

This represents a significant design shift from previous versions. When uplifting code from SLDS 1 to SLDS 2, remove decorative borders from cards, panels, and container components. SLDS 2 relies more on spacing, shadows, and surface colors to create visual separation rather than explicit borders.

**When borders ARE appropriate in SLDS 2:**
- Separating content using neutral borders to divide sections or groups of related content
- Highlighting interactive elements by applying neutral borders for structure, or accent colors for specific branded variants and focus states
- Communicating component states with context-appropriate colors like red for error states or lighter shades for disabled components
- Creating subtle divider lines between content areas

---

## Borders Fundamentals

### What are Borders?

Borders outline elements and provide structure, serving as visual separators, indicators of interactivity, or highlights for active or selected states. Border width, sometimes called stroke width, refers to the thickness of the lines that define the edges of components, containers, and other visual elements.

**Borders help with these design aspects:**
- Differentiate between various UI elements, such as cards, panels, or input fields
- Highlight important information and de-emphasize less important information
- Make content more accessible by ensuring that borders are always visible and easy to read on all screen sizes and resolutions

### Best Practices for Borders

- **Less is Best** — Apply borders sparingly to avoid visual clutter. SLDS 2 favors minimal border usage.
- **Consistency** — Use consistent thickness and color across similar elements.
- **Subtlety** — Use light or subtle borders to create separation without overwhelming the interface.

---

## Radius Fundamentals

### What is Radius?

Radius defines how rounded the corners are on elements. Borders have a radius, and container elements such as cards and buttons have a radius too. Rounded corners soften the visual appearance and create a more approachable design style.

**Radius contributes to the design in these ways:**
- Establish a consistent style for rounded corners across components such as cards, modals, and buttons
- Create a modern, approachable aesthetic that aligns with the brand identity
- Improve usability by subtly guiding users' focus to key interface elements

> **For radius sizing guidance** and component examples, refer to the Borders and Radius Styling Hooks documentation.

### Best Practices for Radius

- **Consistency** — Apply the same radius to similar elements for a cohesive design style throughout the interface.
- **Harmony** — Avoid mixing sharp and rounded corners. Mixing these styles within the same component can create a visually jarring experience and reduce design harmony.
- **Branding** — Use the radius to reflect the brand's personality. Whether the brand should be approachable, professional, or bold, use the SLDS 2 design guidelines to choose the right radius for the elements.
- **Usability** — Confirm through testing that rounded corners don't detract from clarity or usability, especially for focus and hover states in interactive elements.

### Nested Container Pattern

Nested containers should use the next smaller radius value to maintain visual harmony. For example, if an outer card uses `--slds-g-radius-border-4`, a nested card inside should use `--slds-g-radius-border-3`. This creates a consistent visual rhythm where inner elements have subtly tighter corners than their parent containers.

---

## Border Color Fundamentals

SLDS 2 uses specific colors for borders to align with the system's visual design, ensuring clarity and usability across all products.

### Common Border Colors and Meanings

- **Neutral grays** — The standard choice for creating structural separation and outlining functional components
- **Accent colors (Blue)** — Reserved for specialized branded treatments and thematic emphasis
- **Dark blue** — Indicates an element has focus
- **Red** — Indicates an error state
- **Yellow** — Indicates a warning state
- **Transparent or white** — Maintains visual balance in lighter or less prominent elements

### Where to Use Border Colors

- **Separate and outline content** — Use neutral gray borders to divide sections or outline standard functional components (buttons, inputs)
- **Highlight branded elements** — Apply accent colors for specialized branded treatments or thematic emphasis
- **Communicate focus** — Use dark blue focus indicators to support accessibility

> **For complete border color hook details**, refer to the Color Overview and Semantic Color Styling Hooks documentation, which covers the full semantic color system including border-specific tokens.

---

## Theming Considerations

SLDS 2 allows for customizable theming. When making changes to borders or radiuses:

- Ensure any customizations align with brand guidelines
- Maintain contrast ratios for accessibility
- Verify border treatments appear correctly across light/dark themes
- Use styling hooks to enable theme adaptability rather than hard-coded values

---

## Density Awareness Note

**Important:** Unlike spacing and typography, borders and radius values are NOT density-aware in SLDS 2. Border width and radius values remain constant regardless of whether the user has selected comfy or compact display density mode.

When implementing density-aware layouts, note that:
- Border thickness stays the same across density modes
- Radius values stay the same across density modes
- Spacing around bordered elements may change (via density-aware spacing hooks), but the borders themselves do not adapt

---

## Available Styling Hooks

### Border Width Hooks

- `--slds-g-sizing-border-*`

### Border Radius Hooks

- `--slds-g-radius-border-*`
- `--slds-g-radius-border-circle`
- `--slds-g-radius-border-pill`

### Border Color Hooks

Border color hooks are part of the semantic color system. Key hooks include:

- `--slds-g-color-border-*` — Neutral borders for functional structure
- `--slds-g-color-border-accent-*` — Branded emphasis and thematic exceptions
- `--slds-g-color-border-error-*` — Error state borders
- `--slds-g-color-border-success-*` — Success state borders
- `--slds-g-color-border-warning-*` — Warning state borders
- `--slds-g-color-border-disabled-*` — Disabled state borders
- `--slds-g-color-border-inverse-*` — Borders on dark backgrounds

> **For detailed usage patterns**, refer to the Borders and Radius Styling Hooks documentation.

---

## Implementation Workflow

Follow this sequence when implementing any border or radius solution:

### Step 1: Determine if a Border is Needed

Apply the SLDS 2 design philosophy — borders should be used sparingly. Ask:
- Is this border necessary for structure or clarity?
- Could spacing or shadows achieve the same visual separation?
- Am I uplifting from SLDS 1 where borders were used decoratively?

### Step 2: Select the Appropriate Treatment

If a border is needed, determine:
- **Width** — Select the visual weight needed for the component type
- **Radius** — Match to content density (smaller for dense, larger for spacious)
- **Color** — Select based on semantic meaning (neutral, accent, feedback, inverse)

### Step 3: Apply Styling Hooks

Never use hard-coded values. Use the appropriate styling hooks:
- Width: `--slds-g-sizing-border-*`
- Radius: `--slds-g-radius-border-*`
- Color: `--slds-g-color-border-*`

### Step 4: Validate Implementation

Before finalizing, verify the implementation using the Pre-Implementation Checklist below.

---

## Pre-Implementation Checklist

Before generating or modifying any border or radius related code, verify:

| Requirement | Status |
|-------------|--------|
| **Design Philosophy** | |
| Confirmed border is necessary (not decorative holdover from SLDS 1) | [ ] |
| Evaluated alternatives (spacing, shadows) before adding border | [ ] |
| **Hook Selection** | |
| Using styling hooks (no hard-coded pixel values) | [ ] |
| Width hook selected matches visual weight needed | [ ] |
| Radius hook selected matches content density | [ ] |
| Color hook selected matches semantic meaning | [ ] |
| **Consistency & Harmony** | |
| Consistent border treatment across similar elements | [ ] |
| No mixing of sharp and rounded corners in same component | [ ] |
| Border color aligns with surrounding design context | [ ] |
| **Accessibility** | |
| Border visible and perceivable across screen sizes | [ ] |
| Sufficient contrast with adjacent surfaces | [ ] |
| Focus states clearly indicated | [ ] |
| **Theming** | |
| Works across light/dark themes | [ ] |
| Maintains brand alignment | [ ] |

**Target outcome:** Clean, minimal interfaces that use borders purposefully for structure and meaning, not decoration. Visual separation achieved through spacing and depth where possible.



