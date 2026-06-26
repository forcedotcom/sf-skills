---
id: slds.guidance.hooks.color.system
title: System Color Styling Hooks
description: Direct access to brand, neutral, and feedback color palettes for edge cases
summary: "Guidance for system color hooks providing direct palette access. Covers neutral, brand, error, warning, and success base colors. Use only when semantic hooks don't apply (5-10% of cases)."

artifact_type: reference
domain: styling-hooks
topic: color
subtopic: system

content_format: structured
complexity: advanced
audience: [implementer] 

tasks: [choose, implement, troubleshoot]

refs:
  - slds.guidance.hooks.color
  - slds.guidance.hooks.color.accent
  - slds.guidance.hooks.color.surface
  - slds.guidance.hooks.color.feedback
  - slds.guidance.uplift
  - slds.guidance.hooks.color.expressive-palette
tags: [styling-hooks, color, system, neutral, brand, feedback, palette]
keywords: [system colors, neutral palette, brand colors, error colors, warning colors, success colors, edge cases]
---

# System Color Styling Hooks

> **Hook Selection:** System hooks are for edge cases (5-10% of use). For standard UI, use semantic hooks first. See [Hook Selection Hierarchy](ref:slds.guidance.hooks.color).

## Overview

System color styling hooks contain the complete set of values based on their semantics: brand, neutral, and feedback colors. These hooks provide direct access to the underlying color palette values and should only be used in edge cases where a semantic UI color does not make sense.

### Internal Hooks (Not for External Use)

| Prefix | Audience |
|--------|----------|
| `--slds-s-*` | Internal Salesforce only |
| `--slds-c-*` | Internal Salesforce only |

---

## Available System Color Categories

### Neutral Colors
Used for various UI elements such as text, surfaces, and non-functional UI.

**Hook Pattern:** `--slds-g-color-neutral-base-{grade}`

### Brand Colors
Electric-blue colors used for buttons, hover states, and selected or active states. Do not use for decorative purposes.

**Hook Pattern:** `--slds-g-color-brand-base-{grade}`

### Feedback Colors

#### Error Colors
Pink colors only to be used for error feedback or alert states.

**Hook Pattern:** `--slds-g-color-error-base-{grade}`

#### Warning Colors
Yellow colors only to be used for warning feedback or alert states.

**Hook Pattern:** `--slds-g-color-warning-base-{grade}`

#### Success Colors
Teal colors only to be used for success feedback or alert states.

**Hook Pattern:** `--slds-g-color-success-base-{grade}`

---

## Usage

###  Do
- Use system colors only in edge cases where semantic UI colors (accent, surface, feedback) do not make sense
- Use neutral-base colors for various UI elements such as text, surfaces, and non-functional UI
- Use brand-base colors (electric-blue) for buttons, hover states, and selected or active states
- Use feedback colors (error-base, warning-base, success-base) for their intended feedback or alert states
- Use system colors when building custom components that need direct palette access
- System colors provide precise color control for specific design scenarios

###  Don't
- Avoid using system colors as a first choice—always prefer semantic UI colors (accent, surface, feedback) when available
- Avoid using brand-base colors for decorative purposes
- Avoid using error-base, warning-base, or success-base colors outside of their designated feedback contexts
- Avoid mixing system colors with semantic colors unnecessarily
- Avoid using system colors when a semantic color hook would provide the same result
- Avoid overriding the design system's intended color semantics

### Context: When to Use System Colors

**System colors are appropriate for:**

| Scenario | Example | Why System Colors |
|----------|---------|-------------------|
| Data visualization | Charts, graphs, heatmaps | Need precise color control beyond semantic meaning |
| Custom brand elements | Product-specific features | Require exact palette values |
| Legacy migration | Updating older components | Matching specific existing colors |
| Edge case UI | Specialized indicators | No semantic color fits the use case |

**Decision flow:** Before using a system color, verify that no semantic color (accent, surface, feedback) serves the same purpose. System colors bypass the design system's built-in accessibility guarantees.

## When to Use Semantic Colors Instead

Before using system colors, always consider if one of these semantic options would be more appropriate:

- **For brand elements and interactive states:** Use `--slds-g-color-accent-*` instead of `--slds-g-color-brand-base-*`
- **For backgrounds and surfaces:** Use `--slds-g-color-surface-*` or `--slds-g-color-surface-container-*` instead of `--slds-g-color-neutral-base-*`
- **For feedback states:** Use `--slds-g-color-error-*`, `--slds-g-color-warning-*`, or `--slds-g-color-success-*` instead of the base feedback colors
- **For text and icons:** Use `--slds-g-color-on-surface-*`, `--slds-g-color-on-accent-*`, or appropriate on-feedback colors

## Accessibility

- System colors do not inherently guarantee accessible contrast ratios
- **Manual verification required:** Ensure 50-point separation for text (4.5:1) and 40-point for UI (3:1)
- When using system colors, you must manually verify WCAG 2.1 color contrast requirements
- Semantic color hooks (accent, surface, feedback) are designed to maintain proper contrast when used as intended
- Always test custom combinations of system colors for accessibility compliance
- Prefer semantic color hooks which handle contrast ratios automatically

## Color Grade Scale

> **Grade Scale:** SLDS uses a 0-100 grade scale where 0 is darkest and 100 is lightest. Point separations guarantee accessibility: 50-point = 4.5:1 contrast (text), 40-point = 3:1 contrast (UI).
>
> For complete grade scale documentation and the numerical color system, see the [Color Hooks Index](ref:slds.guidance.hooks.color).


