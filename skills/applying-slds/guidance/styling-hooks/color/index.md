---
id: slds.guidance.hooks.color
title: SLDS Color Styling Hooks
description: Index and decision guide for color styling hooks - semantic, system, and expressive palettes
summary: "Entry point for color styling hooks. Provides hook selection hierarchy (semantic 85%, system 5-10%, palette 5%), quick decision guide, and pointers to detailed documentation for accent, surface, feedback, system, and expressive colors."

artifact_type: index
domain: styling-hooks
topic: color

content_format: structured
complexity: intermediate
audience: [implementer]

tasks: [choose, explore]

children:
  - slds.guidance.hooks.color.accent
  - slds.guidance.hooks.color.surface
  - slds.guidance.hooks.color.feedback
  - slds.guidance.hooks.color.system
  - slds.guidance.hooks.color.expressive-palette

refs:
  - slds.guidance.hooks
  - slds.guidance.hooks.color.accent
  - slds.guidance.hooks.color.surface
  - slds.guidance.hooks.color.feedback
  - slds.guidance.hooks.color.system
  - slds.guidance.hooks.color.expressive-palette
tags: [styling-hooks, color, index, semantic, system, palette]
keywords: [color hooks, accent, surface, feedback, system colors, expressive palette, color selection]
---

# SLDS Color Styling Hooks

## Overview

SLDS color styling hooks provide a systematic approach to applying colors that maintain accessibility, support theming (including dark mode), and create consistent visual hierarchy across all Salesforce interfaces.

## Hook Selection Hierarchy

When choosing color hooks, follow this priority order:

1. **Semantic Hooks (85% of use cases)** - First choice for standard UI
2. **System Hooks (5-10%)** - Edge cases where semantic hooks don't apply
3. **Palette Hooks (5%)** - Data visualization and decorative purposes

---

## Semantic Color Hooks

Semantic hooks are purpose-driven and automatically handle accessibility and theming.

### Accent Colors

Brand identity and interactive elements like links, buttons, and icons.

**Hook patterns:** `--slds-g-color-accent-*`, `--slds-g-color-accent-container-*`, `--slds-g-color-border-accent-*`, `--slds-g-color-on-accent-*`

**Use for:** Links, brand buttons, interactive icons, selected states

> **Detailed guidance:** [Accent Color Hooks](ref:slds.guidance.hooks.color.accent)

### Surface Colors

Backgrounds and canvases that establish visual stacking context and enable theming.

**Hook patterns:** `--slds-g-color-surface-*`, `--slds-g-color-surface-container-*`, `--slds-g-color-on-surface-*`

**Use for:** Page backgrounds, modals, cards, panels, popovers

> **Detailed guidance:** [Surface Color Hooks](ref:slds.guidance.hooks.color.surface)

### Feedback Colors

Visual feedback for status and state communication.

**Hook patterns:** `--slds-g-color-error-*`, `--slds-g-color-warning-*`, `--slds-g-color-success-*`, `--slds-g-color-info-*`, `--slds-g-color-disabled-*`

**Use for:** Error messages, warnings, success confirmations, informational alerts, disabled states

> **Detailed guidance:** [Feedback Color Hooks](ref:slds.guidance.hooks.color.feedback)

---

## System Color Hooks

Direct access to brand, neutral, and feedback color palettes for edge cases.

**Hook patterns:** `--slds-g-color-neutral-base-{grade}`, `--slds-g-color-brand-base-{grade}`, `--slds-g-color-error-base-{grade}`, `--slds-g-color-warning-base-{grade}`, `--slds-g-color-success-base-{grade}`

**Use for:** Data visualization, custom brand elements, legacy migration, specialized UI

**Important:** System colors bypass built-in accessibility guarantees. Manual verification required.

> **Detailed guidance:** [System Color Hooks](ref:slds.guidance.hooks.color.system)

---

## Expressive Palette Hooks

Extended color palettes for data visualization and highlighting.

### Cool Tones (Recommended)

- **Cloud Blue:** `--slds-g-color-palette-cloud-blue-{grade}` - Professional, calm
- **Indigo:** `--slds-g-color-palette-indigo-{grade}` - Similar to brand
- **Purple:** `--slds-g-color-palette-purple-{grade}` - Expressive, creative
- **Violet:** `--slds-g-color-palette-violet-{grade}` - Accent, emphasis

### Warm Tones (Use with caution)

- **Green:** `--slds-g-color-palette-green-{grade}` - Highlights (avoid confusion with success)
- **Orange:** `--slds-g-color-palette-orange-{grade}` - Attention-grabbing
- **Hot Orange:** `--slds-g-color-palette-hot-orange-{grade}` - Maximum emphasis
- **Red:** `--slds-g-color-palette-red-{grade}` - Urgent (avoid confusion with error)

**Use for:** Charts, graphs, dashboards, data categories, infographics

> **Detailed guidance:** [Expressive Palette Hooks](ref:slds.guidance.hooks.color.expressive-palette)

---

## The Numerical Color System

SLDS uses a 0-100 grade scale where:

- **0** = Darkest
- **100** = Lightest

### Accessibility Guarantees

| Separation | Contrast Ratio | Use Case             |
| ---------- | -------------- | -------------------- |
| 50 points  | 4.5:1          | Text (WCAG AA)       |
| 40 points  | 3:1            | UI elements, borders |

### Common Pairings

| Background           | Foreground         | Purpose          |
| -------------------- | ------------------ | ---------------- |
| `surface-1`          | `on-surface-1/2/3` | Standard content |
| `accent-container-1` | `on-accent-1`      | Brand buttons    |
| `error-container-1`  | `on-error-1`       | Error alerts     |

---

## Quick Decision Guide

| Need              | Hook Category      | Example                                |
| ----------------- | ------------------ | -------------------------------------- |
| Link color        | Accent             | `--slds-g-color-accent-2`              |
| Page background   | Surface            | `--slds-g-color-surface-1`             |
| Card background   | Surface Container  | `--slds-g-color-surface-container-1`   |
| Button background | Accent Container   | `--slds-g-color-accent-container-1`    |
| Error message     | Feedback           | `--slds-g-color-error-1`               |
| Chart colors      | Expressive Palette | `--slds-g-color-palette-cloud-blue-50` |
| Body text         | On Surface         | `--slds-g-color-on-surface-2`          |

---

## Detailed Guidance

For implementation details on specific color types, see:

1. **Accent colors:** [Accent Color Hooks](ref:slds.guidance.hooks.color.accent)
2. **Surface colors:** [Surface Color Hooks](ref:slds.guidance.hooks.color.surface)
3. **Feedback colors:** [Feedback Color Hooks](ref:slds.guidance.hooks.color.feedback)
4. **System colors:** [System Color Hooks](ref:slds.guidance.hooks.color.system)
5. **Expressive palette:** [Expressive Palette Hooks](ref:slds.guidance.hooks.color.expressive-palette)
