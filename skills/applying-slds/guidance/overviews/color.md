---
id: slds.guidance.overview.color
title: Color Overview
description: Foundational principles and constraints for all color decisions in SLDS
summary: "Comprehensive color guidance covering the 85-5-10 density rule, color role taxonomy, hook selection hierarchy, and numerical color system. The primary reference for all color implementation decisions."

artifact_type: overview
domain: overviews
topic: color

content_format: narrative
complexity: foundational
audience: [implementer, designer]

tasks: [learn, choose, implement]

refs:
  - slds.guidance.hooks.color.accent
  - slds.guidance.hooks.color.surface
  - slds.guidance.hooks.color.feedback
  - slds.guidance.hooks.color.system
  - slds.guidance.hooks.color.expressive-palette

tags: [color, semantic-color, accessibility, visual-hierarchy, theming]
keywords: [color roles, 85-5-10 rule, hook selection, semantic hooks, color taxonomy, surfaces, accents, feedback colors]
---

# Color Guidance for SLDS Implementation

**Purpose:** This document provides the foundational principles and constraints for all color-related decisions in Salesforce Lightning Design System. Always reference the companion metadata files for specific token names, contrast pairings, and approved combinations.

---

## Core Principles

When working with colors in UI interfaces, adhere to these three foundational principles:

1. **Signal hierarchy and meaning.** Color must highlight actions, alerts, and key information without overpowering the experience. Do not use color decoratively.

2. **Accessibility is mandatory.** All implementations must meet WCAG 2.1 AA minimum standards for text and interactive elements. Use only the approved pairings documented in the metadata layer.

3. **Maintain system consistency.** Always use semantic styling hooks. These tokens automatically adapt to brand themes, density modes, and light/dark modes. Never use hard-coded color values.

---

## Color Role Taxonomy

Every element must be classified into one of these five color roles before selecting a token:

- **Surfaces:** The base canvas for content. Each new layer (panel, modal, popover) is a distinct surface with its own depth level. Use surface tokens for backgrounds.

- **Containers:** Elements that hold interactive or readable content (cards, buttons, tabsets). Always pair container background colors with their corresponding "on-container" tokens for text and icons.

- **Accents:** Colors that draw attention to primary interactions or selected states. Use sparingly and only for meaningful emphasis. Overuse destroys visual hierarchy.

- **Feedback colors:** Status indicators (error, warning, success, info, disabled). Reserve exclusively for CRUD operations and system feedback. Never use for general styling.

- **Borders/dividers:** Structural elements that create separation. Must maintain sufficient contrast with adjacent surfaces and containers.

---

## Color Density Rule (85-5-10)

**CONSTRAINT:** All UI implementations should maintain the following color distribution. This distribution is strongly recommended for maintaining SLDS visual consistency.

### UI Foundation: 85% (Required)
Foundational colors create the neutral canvas for all content. Use whites, light grays, dark grays, and dark blue for contrast with text and interactive elements.

**Allowed Palettes:** Whites, light grays, dark grays, dark blue  
**Usage:** Page backgrounds, surface layers, neutral containers, structural elements

### Accents: 5% (Required)
Accent colors are reserved for strategic emphasis on interactive elements. Use the foundational accent (electric blue) and feedback palettes (pink, yellow, teal, blue) to guide users toward task completion.

**Allowed Palettes:** Foundational accent (electric blue), feedback (pink, yellow, teal, blue), functional accent colors  
**Usage:** Primary actions, selected states, status indicators, critical CTAs

### Expressive Colors: 10% (Maximum)
Expressive palettes provide extended color options for data visualization and customized app experiences. Use with restraint.

**Allowed Palettes:** Green, Cloud Blue, Indigo, Purple, Violet, Red, Hot Orange, Orange  
**Usage:** Data charts, custom branding, visualization highlights, app-specific accents

**Strict Usage Rules:**
- **Cool tones first.** Prioritize Cloud Blue, Purple, Indigo, Violet for general page designs. These integrate better with the foundational palette.
- **Indigo warning.** Indigo resembles electric blue. Using it carelessly will break button hierarchy and confuse users about interactive affordances.
- **Warm = attention only.** Orange, Red, and Green signal importance or issues. Reserve them exclusively for drawing user attention to critical information.
- **Prevent feedback confusion.** Expressive colors can be misinterpreted as system feedback (pink=error, yellow=warning, teal=success, blue=info). Apply expressive colors minimally to avoid this conflict.

---

## The Numerical Color System

**System Architecture:** SLDS uses a 0-100 point scale where accessibility compliance is mathematically guaranteed:

- **100 points** = white
- **0 points** = black
- **Color lane** = full 0-100 spectrum of a single hue
- **Color step** = 5-10 point increments within a lane (e.g., Cloud Blue-15, Cloud Blue-25, Cloud Blue-35)

### How It Works

Colors share horizontal point values across different hues. This means the same mathematical rules apply:
- Vertically within each monochromatic palette (single lane)
- Horizontally across all color lanes (different hues)

This consistency enables pattern replication across the entire system.

### Automatic Accessibility: Magic Numbers

**CRITICAL:** Use these point separations to achieve WCAG compliance without manual checking:

| Separation | Contrast Ratio | Use Case | WCAG Level |
|------------|----------------|----------|------------|
| **50 points** | 4.5:1+ | Text on backgrounds, body copy | AA (required) |
| **40 points** | 3:1+ | UI elements, borders, non-text | AA (required) |

**Works across hues:** A 50-point separation maintains 4.5:1 contrast even when using different color lanes.

**Example Application:**
- Page background: Gray-95
- Button background: Any-50 (45 point difference = compliant)
- Button hover: Any-40 (55 point difference = compliant)
- Button text: Any-0 or Any-100 depending on background

The 10-point step from 50→40 creates consistent hover states across all color lanes.

**Attribution:** The "magic numbers" concept originates from the U.S. Web Design System (USWDS) and has been adopted into SLDS to ensure systematic color progression and accessibility.

---

## Implementation Workflow

Follow this mandatory sequence when implementing any color solution:

### Step 1: Classify the Element
Identify the element's semantic role:
- Is it a **surface** (background layer)?
- Is it a **container** (holds content)?
- Is it an **accent** (emphasis/interaction)?
- Is it **feedback** (status/state)?
- Is it a **border/divider** (structure)?

### Step 2: Reference the Metadata
Never invent color values. The companion metadata files contain:
- Approved styling hook names
- Pre-validated contrast pairings
- State transition sequences (default → hover → active → disabled)
- Theme adaptations (light/dark/branded)

### Step 3: Handle Exceptions
If no semantic hook matches the requirement:
1. Document why standard patterns don't apply
2. Verify contrast manually using the numerical system
3. Ensure brand consistency is maintained
4. Flag for design system team review

### Step 4: Validate Implementation
Before finalizing, verify the implementation using the Pre-Implementation Checklist below to ensure all color requirements are met.

---

## Metadata Integration

**Source of Truth:** The metadata files are authoritative for all implementation details.

**What the metadata provides:**
- Exact token names and values
- Pre-validated contrast pairings (text-on-background, icon-on-surface)
- State progression maps (default → hover → active → focus → disabled)
- Cross-reference between semantic roles and color values
- Theme-specific overrides

**When to consult metadata:**
- Before selecting any color token
- When implementing state changes
- When validating a custom pattern
- When introducing new component styles

**Validation question:** Does this color choice reinforce semantic meaning, meet accessibility standards, and maintain brand consistency?

---

## Hook Selection Hierarchy

When selecting color hooks, follow this decision order:

### 1. Semantic Hooks (First Choice — 85% of Cases)
**Pattern:** `--slds-g-color-{purpose}-{n}` (e.g., `error-1`, `accent-container-1`, `surface-1`)

Use semantic hooks for standard UI patterns. These hooks:
- Are purpose-built for specific UI use cases (errors, accents, surfaces, feedback)
- Automatically adapt to light/dark mode with curated values
- Have pre-validated accessibility pairings
- Reference system and palette hooks underneath

**Use when:** You can describe your element using semantic terms (surface, accent, error, warning, success, disabled).

### 2. System Hooks (Edge Cases — 5-10% of Cases)
**Pattern:** `--slds-g-color-{category}-base-{grade}` (e.g., `error-base-50`, `brand-base-40`)

Use system hooks when semantic hooks don't cover your specific need. These hooks:
- Provide grade-level control within a color category
- Still adapt to light/dark mode with curated values per mode
- Reference palette hooks underneath

**Use when:** Data visualization, legacy migration, or custom requirements where semantic hooks are insufficient.

### 3. Palette Hooks (Raw Access — Rare Cases)
**Pattern:** `--slds-g-color-palette-{color}-{grade}` (e.g., `palette-pink-50`, `palette-cloud-blue-30`)

Use palette hooks only when system hooks don't meet your requirements. These hooks:
- Provide direct access to the color palette by color name and grade
- Have light/dark mode variants
- Are the foundation that semantic and system hooks reference

**Use when:** Custom color requirements that don't fit any semantic or system category.

### Internal Hooks (Not for External Use)

The following hook prefixes are **internal to Salesforce** and should not be used by external developers:

| Prefix | Name | Audience |
|--------|------|----------|
| `--slds-s-*` | Shared hooks | Internal Salesforce only |
| `--slds-c-*` | Component hooks | Internal Salesforce only |

### How They Connect (Aliasing Chain)

Semantic hooks reference system hooks, which reference palette hooks. When the theme changes (light → dark), the underlying references change, so semantic hooks automatically adapt.

**Example:** `--slds-g-color-error-1`
- Light mode: → `error-base-50` → `palette-pink-50` → #hex
- Dark mode: → `error-base-40` → `palette-pink-40` → #different-hex

This aliasing chain means you get theme adaptation "for free" when using semantic hooks.

---

## Pre-Implementation Checklist

Before generating or modifying any color-related code, verify:

| Requirement | Status |
|-------------|--------|
| **Element Classification** | |
| Element classified by semantic role (surface/container/accent/feedback/border) | [ ] |
| **Token Selection & Metadata** | |
| Color token identified from metadata (no hard-coded hex/RGB values) | [ ] |
| Metadata consulted for approved styling hook names | [ ] |
| Pre-validated contrast pairings referenced from metadata | [ ] |
| "On" counterpart specified (for containers) | [ ] |
| **Contrast & Accessibility** | |
| Contrast requirements met using numerical system (50pts text, 40pts UI) | [ ] |
| Works with the numerical color system for automatic accessibility | [ ] |
| **Color Distribution & Usage** | |
| 85-5-10 density rule maintained (85% foundation, 5% accent, 10% expressive) | [ ] |
| Accent/feedback colors used sparingly and meaningfully | [ ] |
| Color reinforces semantic meaning rather than decorative use | [ ] |
| **Theme Support & States** | |
| All theme modes supported (light/dark/compact/branded) | [ ] |
| State transitions defined (hover/active/focus/disabled) | [ ] |
| Theme-specific overrides reviewed from metadata where applicable | [ ] |

**Target outcome:** Calm, purposeful interfaces that are unmistakably Salesforce. Color should enhance usability without becoming decorative.

