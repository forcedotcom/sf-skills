---
id: slds.guidance.overview.shadows
title: Shadows and Elevation Overview
description: Foundational guidance for implementing shadows and visual depth in SLDS
summary: "Comprehensive shadow guidance covering elevation levels, component shadow mappings, directional shadows, and accessibility considerations. Explains box-shadow concepts and stacking order relationships."

artifact_type: overview
domain: overviews
topic: shadows

content_format: narrative
complexity: foundational
audience: [implementer, designer]

tasks: [learn, choose, implement]

refs:
  - slds.guidance.hooks.shadows

tags: [shadows, elevation, depth, visual-hierarchy, stacking]
keywords: [box shadow, elevation levels, visual depth, stacking order, z-index, component shadows]
---

# Shadows and Elevation Guidance for SLDS Implementation

**Purpose:** This document provides guidance for implementing shadows in Salesforce Lightning Design System. Shadows add depth and dynamic layers to the UI, making it look more interesting and less static. When implementing components and layouts, follow these guidelines to ensure visual hierarchy and elevation are communicated effectively.

---

## About Shadows

### What is Box Shadow?

The `box-shadow` CSS property adds a shadow effect to an element. This property sets values for horizontal and vertical offsets, blur radius, spread radius, and shadow color. The combination of these properties creates a shadow around the frame of an element.

Box shadows indicate elevation and are applied to elements to show which elements are on top of one another. Elevation is applied to elements to show that surfaces can move on top of one another.

The SLDS 2 design uses soft shadows to create a sense of depth and dimension in the user interface. They also help separate components from each other and create a more realistic look.

The styling hook for shadows uses the label `shadow`.

### Elevation System

When applying a shadow, match the priority or stacking order of the elements. Elements with a higher stacking order or which appear on top of others on the page should have higher shadow values. Leverage the z-index property to manage stacking order, and ensure that the elements with the highest shadow value appear above others on the page.

**Elevation Levels:**

| Level | Shadow Hook | Description |
|-------|-------------|-------------|
| Base Level | No shadow | Components on the surface that don't cover other components |
| Elevation Level 1 | `--slds-g-shadow-1` | Subtle depth |
| Elevation Level 2 | `--slds-g-shadow-2` | Moderate depth |
| Elevation Level 3 | `--slds-g-shadow-3` | Prominent depth |
| Elevation Level 4 | `--slds-g-shadow-4` | Maximum depth |

### Component Shadow Usage

| Shadow Hook | Components |
|-------------|------------|
| `--slds-g-shadow-1` | Page headers, joined tables, filter panels, dropdowns, inline edit, images, slider handles |
| `--slds-g-shadow-2` | Menu, docked form footer, docked utility bar, color picker, notifications |
| `--slds-g-shadow-3` | Panel, docked composer, tooltip, toast |
| `--slds-g-shadow-4` | Modal, popover, App Launcher |

### Base Level (No Shadow)

Components that are **base level** sit on the surface and don't cover up other components. Base level components do not have shadows in the SLDS 2 design.

The background color of a base level component depends on the color of the surface it sits on:
- On a gray surface: A base level component has a white background
- On a white surface: A base level component has a white background with a border

---

## Shadow Types

### Depth Shadows

Depth shadows communicate elevation and visual hierarchy. They indicate which elements appear above others in the stacking order.

**Hook Pattern:** `--slds-g-shadow-{n}` where `{n}` is the depth level

- `shadow-1` through `shadow-4` provide increasing depth levels
- `shadow-5` and `shadow-6` are aliases that inherit from `shadow-4`

### Directional Shadows

Directional shadow variants allow shadows to be cast in specific directions. These are useful for components that are positioned against edges of the screen.

**Hook Pattern:** `--slds-g-shadow-{direction}-{n}` where `{direction}` is the shadow direction and `{n}` is the depth level

**Directions:**
- `block-start` — Upward shadow
- `block-end` — Downward shadow (default direction, inherits from base shadow)
- `inline-start` — Left shadow
- `inline-end` — Right shadow

### Focus Shadows

Focus shadows provide visual feedback for keyboard navigation and accessibility. Focus states within the SLDS 2 design consist of a white border outline surrounded by a dark blue border outline. This style ensures that the focus state meets accessibility requirements for any background.

**Hook Pattern:** `--slds-g-shadow-{type}-focus-1` where `{type}` is the focus style

**Types:**
- `outline-focus` — Simple outline focus
- `outset-focus` — Double ring outset focus
- `inset-focus` — Single ring inset focus
- `inset-inverse-focus` — Double ring inset focus (inverse)

### Inset Shadows (Component-Level)

Button components use a hover bevel and inner shadow on click that is separate from the elevation system. Bevels and insets are only used on buttons and inputs where specified and shouldn't be used in custom situations.

**Button shadows:**
- `--slds-s-button-shadow-active` — Used on all buttons when pressed, regardless of color or border
- `--slds-s-button-shadow-focus` — Focus state for buttons
- `--slds-s-button-brand-shadow-hover` — Hover effect for brand buttons
- `--slds-s-button-bordered-shadow-hover` — Hover effect for bordered/neutral buttons

**Input shadows:**
- `--slds-s-input-shadow-focus` — Used on active/focused input fields

**Mark shadows (checkboxes, radios, toggles):**
- `--slds-s-mark-shadow-checked` — Used on selected or active checkboxes, radio buttons, and checkbox toggles
- `--slds-s-mark-shadow-focus` — Focus state for mark elements

---

## Available Styling Hooks

> **For detailed usage patterns**, refer to the Shadows Styling Hooks documentation.

### Global Shadow Hooks (`--slds-g-`)

**Depth Shadows:**
- `--slds-g-shadow-{1-6}`

**Directional Shadows:**
- `--slds-g-shadow-block-start-{1-4}`
- `--slds-g-shadow-block-end-{1-4}`
- `--slds-g-shadow-inline-start-{1-4}`
- `--slds-g-shadow-inline-end-{1-4}`

**Focus Shadows:**
- `--slds-g-shadow-outline-focus-1`
- `--slds-g-shadow-outset-focus-1`
- `--slds-g-shadow-inset-focus-1`
- `--slds-g-shadow-inset-inverse-focus-1`

### Shared Shadow Hooks (`--slds-s-`)

**Button Shadows:**
- `--slds-s-button-shadow-focus`
- `--slds-s-button-shadow-focus-inverse`
- `--slds-s-button-shadow-active`
- `--slds-s-button-brand-shadow-hover`
- `--slds-s-button-bordered-shadow-hover`

**Input Shadows:**
- `--slds-s-input-shadow-focus`
- `--slds-s-input-shadow-invalid`

**Mark Shadows:**
- `--slds-s-mark-shadow-focus`
- `--slds-s-mark-shadow-checked`

### Component Shadow Hooks (`--slds-c-`)

**Button Variant Shadows:**
- `--slds-c-button-success-shadow-hover`
- `--slds-c-button-destructive-shadow-hover`
- `--slds-c-button-inverse-shadow-hover`




