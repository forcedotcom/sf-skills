---
id: slds.guidance.hooks.color.expressive-palette
title: Expressive Palette Color Styling Hooks
description: Extended color palettes for data visualization and expressive interfaces
summary: "Guidance for expressive palette hooks including cool tones (cloud blue, indigo, purple, violet) and warm tones (green, orange, hot orange, red). Use for data visualization and highlighting—not standard UI."

artifact_type: reference
domain: styling-hooks
topic: color
subtopic: expressive

content_format: structured
complexity: advanced
audience: [implementer]

tasks: [choose, implement]

refs:
  - slds.guidance.hooks.color
  - slds.guidance.hooks.color.accent
  - slds.guidance.hooks.color.surface
  - slds.guidance.hooks.color.feedback
  - slds.guidance.hooks.color.system
tags: [styling-hooks, color, palette, expressive, visualization, data]
keywords: [expressive colors, data visualization, cool tones, warm tones, cloud blue, indigo, purple, orange, green]
---

# Expressive Palette Color Styling Hooks

> **Hook Selection:** Palette hooks provide raw color access for rare cases. For standard UI, use semantic hooks first. See [Hook Selection Hierarchy](ref:slds.guidance.hooks.color).

## Overview

Expressive palette color styling hooks contain an extended range of colors beyond the core system palette. These palettes are useful for displaying data, visualizations, and highlighting important areas in your user experience. The expressive palettes offer variety while maintaining cohesion with the design system's overall aesthetic.

---

## Available Expressive Palette Categories

### Cool Tone Palettes (Recommended)

#### Cloud Blue
Useful for data visualization and cool-toned accents. A calm, professional blue palette. Use intentionally to avoid confusion with info feedback colors (blue).

**Hook Pattern:** `--slds-g-color-palette-cloud-blue-{grade}`

#### Indigo
A rich purple-blue palette similar to the brand color. Use intentionally to avoid disrupting button hierarchy.

**Hook Pattern:** `--slds-g-color-palette-indigo-{grade}`

#### Purple
A vibrant purple palette suitable for expressive, data-heavy interfaces.

**Hook Pattern:** `--slds-g-color-palette-purple-{grade}`

#### Violet
A deep, saturated purple palette that works well for accent and emphasis in visualizations.

**Hook Pattern:** `--slds-g-color-palette-violet-{grade}`

### Warm Tone Palettes (Use with Caution)

#### Green
Use to draw attention to important information. Use sparingly to avoid confusion with success feedback colors (teal).

**Hook Pattern:** `--slds-g-color-palette-green-{grade}`

#### Orange
A warm, energetic orange palette effective for highlighting critical areas. Use sparingly to avoid confusion with warning feedback colors (yellow). 

**Hook Pattern:** `--slds-g-color-palette-orange-{grade}`

#### Hot Orange
A bright, intense orange effective for maximum attention-grabbing. Reserve for truly critical states.

**Hook Pattern:** `--slds-g-color-palette-hot-orange-{grade}`

#### Red
A bold red palette effective for highlighting issues or important information. Use intentionally and sparingly to avoid confusion with error feedback colors (pink).

**Hook Pattern:** `--slds-g-color-palette-red-{grade}`

---

## Usage

###  Do
- Use expressive palette colors for data visualization and charts
- Use cool tones (cloud blue, indigo, purple, violet) as your primary choices
- Use warm tones (orange, hot orange, red, green) strategically to draw attention
- Combine multiple palettes in visualization scenarios when each color needs semantic meaning
- Use expressive palettes when you need colors beyond the semantic system (accent, surface, feedback)
- Proper contrast ratios are important when layering expressive colors over backgrounds
- Use a consistent palette approach to unify similar data visualizations

###  Don't
- Avoid using expressive palettes as a first choice—prefer semantic colors (accent, surface, feedback) first
- Avoid overusing warm colors like orange, red, and green—they work best for highlighting critical information
- Avoid using indigo in ways that could confuse users with the brand color (buttons, interactive states)
- Avoid mixing expressive palette colors with feedback colors without clear visual distinction
- Avoid using expressive colors where neutral grays or system colors would be more appropriate
- Avoid relying on color alone to convey meaning—pair colors with icons, labels, or patterns
- Avoid overriding accessibility requirements for visual appeal

### Context
- Data visualization and charting
- Complex dashboards with multiple data categories
- Highlighting specific data points or trends
- Geographic or hierarchical data representation
- Educational materials and infographics
- Scenario-based UI variations

## When to Use Semantic Colors Instead

Before choosing expressive palette colors, evaluate these alternatives:

- **For interactive elements:** Use `--slds-g-color-accent-*` instead of expressive palettes
- **For backgrounds and containers:** Use `--slds-g-color-surface-*` or `--slds-g-color-surface-container-*`
- **For feedback states:** Use `--slds-g-color-error-*`, `--slds-g-color-warning-*`, or `--slds-g-color-success-*` instead of palette colors
- **For text and icons:** Use `--slds-g-color-on-surface-*` or `--slds-g-color-on-accent-*` for proper contrast

## Palette Selection Guidelines

### Color Tone Recommendations

**Cool Tone Priority (Recommended for most designs):**
- Cloud Blue: Professional, calm, data-forward
- Indigo: Similar to brand, use intentionally
- Purple: Expressive, creative
- Violet: Accent, emphasis

**Warm Tone Use (Use when attention is needed):**
- Green: Issues, highlights (use sparingly to distinguish from teal success)
- Orange: Warnings, important data
- Hot Orange: Critical warnings, maximum emphasis
- Red: Errors, urgent information (use sparingly to distinguish from pink error state)

## Accessibility

- Expressive palette colors do not guarantee accessible contrast—manual verification required
- **Contrast requirements:** 50-point separation for text (4.5:1), 40-point for UI elements (3:1)
- **CVD warning:** Avoid Red+Green and Blue+Purple as sole differentiators
- Use patterns, icons, or labels in addition to color to convey meaning
- Test with colorblind simulation tools when using multiple palette colors
- Semantic color hooks are preferred when accessibility guarantees are required
- Accessibility requirements apply — consult your project's accessibility standards

## Color Grade Scale

> **Grade Scale:** SLDS uses a 0-100 grade scale where 0 is darkest and 100 is lightest. Point separations guarantee accessibility: 50-point = 4.5:1 contrast (text), 40-point = 3:1 contrast (UI).
>
> For complete grade scale documentation and the numerical color system, see the [Color Hooks Index](ref:slds.guidance.hooks.color).
