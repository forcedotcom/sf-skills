---
id: slds.guidance.hooks
title: SLDS Styling Hooks - Agent Guidance
description: Comprehensive guidance for using SLDS styling hooks in component development
summary: "Entry point for all styling hooks guidance. Covers the three-tier hook hierarchy (global, shared, component), core categories (color, spacing, typography, shadows, borders), usage patterns, decision trees, and accessibility requirements. Use styling hooks instead of hard-coded values for theme-aware, maintainable components."

artifact_type: index
domain: styling-hooks

content_format: structured
complexity: intermediate
audience: [implementer]

tasks: [choose, implement, troubleshoot]

children:
  - slds.guidance.hooks.color
  - slds.guidance.hooks.typography
  - slds.guidance.hooks.spacing
  - slds.guidance.hooks.borders
  - slds.guidance.hooks.shadows

refs:
  - slds.guidance.hooks.shadows
  - slds.guidance.hooks.borders
tags: [styling-hooks, index, color, spacing, typography, shadows, borders, theming]
keywords: [styling hooks, CSS custom properties, theming, accessibility, design tokens, SLDS]
---

# SLDS Styling Hooks: Guidance for Coding Agents

## Overview

The Salesforce Lightning Design System (SLDS) styling hooks are CSS custom properties that provide a theme-aware, maintainable styling system. When generating or optimizing SLDS components, **always use styling hooks instead of hard-coded values** to ensure components adapt automatically to:

- Brand themes and customizations
- Light/dark mode switches
- Density settings (compact, comfy, spacious)
- Accessibility requirements
- Future design system updates

**Critical Rule:** Reference styling hooks using `var()` — never reassign their values. Salesforce controls these values and can change them at any time.

---

## Styling Hook Hierarchy

SLDS styling hooks follow a three-tier naming convention:

1. **Global Semantic** (`--slds-g-*`): System-wide hooks for universal use across all components
2. **Shared** (`--slds-s-*`): Private/internal hooks — **DO NOT USE** (reserved for Salesforce)
3. **Component-Specific** (`--slds-c-*`): Hooks scoped to individual component types for fine-tuning

**Always use global hooks (`--slds-g-*`) unless component-specific hooks exist for your use case.**

---

## Core Categories

### 1. Color Hooks (`--slds-g-color-*`)

SLDS provides a comprehensive color system organized into three tiers:

#### **Tier 1: Semantic UI Colors (PREFERRED)**

Purpose-driven colors that automatically adapt to themes and modes:

- **Surface** (`surface-*`): Page backgrounds, panels, modal overlays
- **Container** (`container-*`): Buttons, cards, tabs, input fields
- **Accent** (`accent-*`): Brand emphasis and selection states
- **Border** (`border-*`): Component borders, dividers, separators
- **Feedback** (`feedback-*`): Alerts, notifications, validation states
- **On-Colors** (`on-*`): Text and icons on colored backgrounds

#### **Tier 2: System Colors**

Accessible, system-wide colors for edge cases where semantic colors don't apply.

#### **Tier 3: Palette Colors (Use Sparingly)**

Raw color values for data visualization and custom scenarios.

> **💡 Detailed color guidance:** See [Color Styling Hooks Index](ref:slds.guidance.hooks.color) for the complete color system documentation.

---

### 2. Spacing Hooks (`--slds-g-spacing-*`)

SLDS uses a numbered scale (NOT named like "small/medium/large"):

| Hook Name             | Value   | Pixels | Legacy Equivalent |
| --------------------- | ------- | ------ | ----------------- |
| `--slds-g-spacing-1`  | 0.25rem | 4px    | xx-small          |
| `--slds-g-spacing-2`  | 0.5rem  | 8px    | x-small           |
| `--slds-g-spacing-3`  | 0.75rem | 12px   | small             |
| `--slds-g-spacing-4`  | 1rem    | 16px   | medium            |
| `--slds-g-spacing-5`  | 1.5rem  | 24px   | large             |
| `--slds-g-spacing-6`  | 2rem    | 32px   | x-large           |
| `--slds-g-spacing-7`  | 2.5rem  | 40px   | xx-large          |
| `--slds-g-spacing-8`  | 3rem    | 48px   | xxx-large         |
| `--slds-g-spacing-9`  | 3.5rem  | 56px   | -                 |
| `--slds-g-spacing-10` | 4rem    | 64px   | -                 |
| `--slds-g-spacing-11` | 4.5rem  | 72px   | -                 |
| `--slds-g-spacing-12` | 5rem    | 80px   | -                 |

**Usage:**

```css
/* Use numbered hooks - NOT named ones */
margin: var(--slds-g-spacing-4); /* ✅ Correct */
padding: var(--slds-g-spacing-2) var(--slds-g-spacing-4); /* ✅ Correct */

/* DON'T use named hooks - they don't exist */
margin: var(--slds-g-spacing-medium); /* ❌ Wrong - hook doesn't exist */
```

> **💡 Detailed spacing guidance:** See [Spacing and Sizing Hooks](ref:slds.guidance.hooks.spacing) for complete documentation.

---

### 3. Typography Hooks (`--slds-g-font-*`)

#### Font Families

- `--slds-g-font-family` - Default font family
- `--slds-g-font-family-base` - Base font family
- `--slds-g-font-family-monospace` - For code snippets

#### Font Weights (Numbered 1-7)

| Hook Name                | Typical Value | Common Name |
| ------------------------ | ------------- | ----------- |
| `--slds-g-font-weight-1` | 300           | Light       |
| `--slds-g-font-weight-2` | 300           | Light       |
| `--slds-g-font-weight-3` | 400           | Regular     |
| `--slds-g-font-weight-4` | 400           | Regular     |
| `--slds-g-font-weight-5` | 500           | Medium      |
| `--slds-g-font-weight-6` | 600           | Semi-Bold   |
| `--slds-g-font-weight-7` | 700           | Bold        |

**Usage:**

```css
/* Use numbered hooks */
font-weight: var(--slds-g-font-weight-7); /* Bold */

/* DON'T use named hooks - they don't exist */
font-weight: var(--slds-g-font-weight-bold); /* ❌ Wrong */
```

> **💡 Detailed typography guidance:** See [Typography Styling Hooks](ref:slds.guidance.hooks.typography) for complete documentation.

---

### 4. Other Styling Hooks

- **Sizing** (`--slds-g-sizing-*`): Component dimensions, icon sizes, border widths
- **Shadow** (`--slds-g-shadow-*`): Elevation and depth effects
- **Radius** (`--slds-g-radius-*`): Border radius values for rounded corners

---

## Usage Patterns

### Pattern 1: Interactive Component States (Accent Colors)

```css
.button {
  background: var(--slds-g-color-accent-container-1);
  color: var(--slds-g-color-on-accent-1);
  border: 1px solid var(--slds-g-color-border-accent-1);
  padding: var(--slds-g-spacing-2) var(--slds-g-spacing-4);
  border-radius: var(--slds-g-radius-border-1);
}

.button:hover {
  background: var(--slds-g-color-accent-container-2);
  color: var(--slds-g-color-on-accent-2);
  border-color: var(--slds-g-color-border-accent-2);
}

.button:active {
  background: var(--slds-g-color-accent-container-3);
  color: var(--slds-g-color-on-accent-3);
  border-color: var(--slds-g-color-border-accent-3);
}
```

### Pattern 2: Semantic Surfaces

```css
.card {
  background: var(--slds-g-color-surface-container-1);
  color: var(--slds-g-color-on-surface-1);
  padding: var(--slds-g-spacing-4);
  border: 1px solid var(--slds-g-color-border-1);
  border-radius: var(--slds-g-radius-border-1);
}
```

### Pattern 3: Feedback States

```css
.alert-error {
  background: var(--slds-g-color-error-container-1);
  color: var(--slds-g-color-on-error-1);
  border-left: 4px solid var(--slds-g-color-error-1);
  padding: var(--slds-g-spacing-2) var(--slds-g-spacing-4);
}

.alert-success {
  background: var(--slds-g-color-success-container-1);
  color: var(--slds-g-color-on-success-1);
  border-left: 4px solid var(--slds-g-color-success-1);
}
```

---

## Decision Tree for Coding Agents

### Step 1: Check for Component-Specific Hooks

Search for `--slds-c-[component-name]-*` hooks first (highest specificity).

### Step 2: Use Semantic UI Colors (Preferred)

For colors, prefer semantic hooks:

- **Surface/Container**: `surface-1/2/3`, `surface-container-1/2/3`, `on-surface-1/2/3`
- **Accent**: `accent-1/2/3`, `accent-container-1/2/3`, `border-accent-1/2/3`, `on-accent-1/2/3`
- **Feedback**: `error-1`, `success-1`, `warning-1`, `info-1` with their container and on-color variants

### Step 3: Use Numbered Spacing & Typography

Always use numbered hooks where available:

```css
padding: var(--slds-g-spacing-4);
font-weight: var(--slds-g-font-weight-5);
font-size: var(--slds-g-font-size-base); /* Or use rem values */
```

---

## Critical Rules

### ✅ DO:

- Reference hooks with `var()`: `color: var(--slds-g-color-accent-1);`
- Use numbered spacing: `spacing-4` not `spacing-medium`
- Use numbered font weights: `font-weight-5` not `font-weight-medium`
- Prefer semantic UI colors over system colors and palette colors
- Pair container colors with on-colors for text/icons
- Follow the 50-point rule for text contrast, 40-point rule for UI elements

### ❌ DON'T:

- Reassign hook values: `--slds-g-color-accent-1: #ff0000;` ❌
- Use private hooks (`--_slds-*` or `--slds-s-*`)
- Use `@layer` syntax (reserved for Salesforce)
- Use named spacing hooks (`spacing-small`, `spacing-medium`) - they don't exist
- Use named font hooks (`font-weight-medium`, `font-weight-bold`) - they don't exist
- Hard-code values when hooks exist

---

## Accessibility Compliance

### Color Contrast Rules

| Separation | Contrast Ratio | Use Case                   |
| ---------- | -------------- | -------------------------- |
| 50 points  | 4.5:1          | Text (WCAG AA)             |
| 40 points  | 3:1            | UI elements, borders       |

### Automatic Compliance with Semantic Colors

When using semantic accent colors, SLDS ensures contrast automatically:

```css
/* ✅ ALWAYS COMPLIANT when using matching pairs */
.accent-button {
  background: var(--slds-g-color-accent-container-1);
  color: var(--slds-g-color-on-accent-1); /* Pre-validated pairing */
}
```

---

## Troubleshooting

### Problem: Hook name not working

**Solution:** Verify naming convention:

- Use numbered spacing: `spacing-4` NOT `spacing-medium`
- Use numbered fonts: `font-weight-5` NOT `font-weight-medium`

### Problem: Colors have poor contrast

**Solution:**

- Use semantic hooks with paired on-colors
- For palette: 50-point separation for text, 40-point for UI elements

### Problem: Spacing inconsistent

**Solution:**

- Use numbered spacing hooks: `spacing-2`, `spacing-4`
- Check spacing scale: 8px=spacing-2, 16px=spacing-4, 24px=spacing-5

---

## Summary

When generating or optimizing SLDS components:

1. **Use semantic hooks first** — Prefer semantic UI colors over system/palette
2. **Use numbered hooks** — spacing-4, font-weight-5 (NOT named like "medium")
3. **Font sizes** — Use `font-size-base` or rem values
4. **Follow the three-tier color system** — Semantic UI → System Colors → Expressive Palette
5. **Pair containers with on-colors** — Use `on-surface-*`, `on-accent-*`, `on-error-*` for text/icons
6. **Test accessibility** — Verify contrast ratios and keyboard navigation

**The goal:** Build theme-aware, accessible components that adapt automatically to brand customizations, light/dark modes, and density settings.
