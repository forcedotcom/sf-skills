---
id: slds.guidance.overview.display-density
title: Display Density Overview
description: Foundational guidance for implementing comfy and compact density modes in SLDS
summary: "Comprehensive display density guidance covering comfy vs compact settings, density-aware styling hooks, and responsive component design. Includes implementation workflow and common pitfalls."

artifact_type: overview
domain: overviews
topic: display-density

content_format: narrative
complexity: foundational
audience: [implementer, designer]

tasks: [learn, choose, implement]

refs:
  - slds.guidance.hooks.spacing
  - slds.guidance.hooks.typography

tags: [display-density, comfy, compact, responsive, user-preferences]
keywords: [comfy mode, compact mode, density-aware, user preferences, responsive design, data density, form layout]
---

# Display Density Guidance for SLDS Implementation

**Purpose:** This document provides the foundational principles and guidance for implementing display density in Salesforce Lightning Design System. When working with SLDS components and interfaces, follow these guidelines to ensure consistent user experiences across both comfy and compact density settings.

---

## About Display Density

Display density controls the spacing and layout of interface elements within a given screen area. Salesforce Lightning Design System 2 (SLDS 2) offers two density settings: **comfy** and **compact**.

**Comfy** (the default setting) places labels on top of fields and adds more space between page elements, creating a spacious view with increased vertical and horizontal spacing. **Compact** increases visual density with labels on the same line as fields and less space between lines, allowing more information to be visible simultaneously.

**Key Requirement:** Because users select which display density setting to use, design Salesforce interfaces to work well in both settings. Display density is a user preference that must be supported universally across all implementations.

---

## Core Principles

When working with display density in UI interfaces, adhere to these foundational principles:

1. **Respect user preferences.** Display density is a user-controlled setting, not a design decision. Interfaces must function equally well in both comfy and compact modes, as users select their preferred density based on their needs and workflows.

2. **Design for both settings from the start.** Implement components with density-aware styling hooks to ensure seamless adaptation. Retrofitting density support is more complex than building it in from the beginning.

3. **Maintain accessibility across densities.** Both comfy and compact modes must meet WCAG standards. Touch targets, text readability, and visual hierarchy must remain accessible regardless of the density setting.

4. **Use density-aware styling hooks strategically.** Not every element needs to adapt to density changes. Identify which components truly benefit from density responsiveness—typically data-dense elements like tables, lists, forms, and navigation.

---

## Comfy Setting

Comfy is the default density setting in Salesforce. The comfy setting offers a spacious view with increased vertical and horizontal spacing, and vertically stacked form elements.

### Benefits of Comfy Setting

The comfy setting provides these benefits:

- **Better accommodation for localized content** with longer text strings, reducing truncation and improving internationalization support
- **Enhanced visual separation** for improved accessibility, particularly benefiting users with cognitive disabilities or those who benefit from clear visual grouping
- **Reduced cognitive load and better scannability**, particularly beneficial for new users learning the system or users navigating complex workflows

### Comfy Setting Guidelines

When implementing components for comfy mode, address these factors:

- **Critical information prominence:** Ensure that critical information remains prominent despite additional whitespace. The increased spacing should enhance, not diminish, the visibility of important content.
- **Localized content testing:** Test with localized content to verify that spacing accommodates longer text strings common in languages like German or Finnish.
- **Vertical scrolling requirements:** Elements use more vertical space in comfy mode, which may increase scrolling requirements for long forms or data-heavy screens.

---

## Compact Setting

Compact mode creates a denser view with reduced spacing between elements, more information visibility in the viewport, and horizontally stacked form elements.

### Benefits of Compact Setting

The compact setting provides these benefits:

- **Improved efficiency** when working with large data sets, allowing users to see and compare more records without scrolling
- **Reduced scrolling** for data-heavy screens, improving workflow efficiency for power users
- **More information visible simultaneously**, supporting tasks that require viewing multiple data points at once

### Compact Setting Guidelines

When implementing components for compact mode, address these critical factors:

- **Touch target accessibility:** Verify that touch targets remain large enough for comfortable interaction, meeting minimum size requirements of 44×44 pt/dp/px for mobile and 24×24 CSS pixels for desktop (with 44×44 recommended for Salesforce mixed environments).
- **Text readability:** Ensure that text remains readable with reduced spacing, maintaining appropriate line height and letter spacing for legibility.
- **Horizontal layout behavior:** Test how horizontal layouts behave in narrower viewports, ensuring form elements that stack horizontally don't create usability issues on smaller screens.

---

## User Control of Density

To personalize the look of Lightning Experience, users can change their display density setting through their profile menu. After a user changes their display density setting, the page automatically refreshes to apply the new density. Salesforce administrators can also set org-wide defaults.

**Implementation Requirement:** When designing and developing interfaces, ensure that the interface adapts appropriately to both density settings. Components must respond gracefully to density changes without breaking layouts or compromising functionality.

---

## Density-Aware Styling Hooks

Use density-aware styling hooks when specific areas, components, spacing, and typographical elements require the ability to adapt or respond to a user's density setting. Density-aware styling hooks are denoted by **"var"** in the naming convention (e.g., `--slds-g-spacing-var-1`) and act as responsive variables that change their values when the density setting changes.

### Elements That Benefit from Density-Aware Hooks

Implement density-aware styling hooks for these element types:

- **Data-dense components** like tables, lists, and grids where information density directly impacts usability
- **Form layouts and field arrangements** where spacing affects scannability and completion efficiency
- **Card and container padding** where internal spacing adapts to user preference
- **Navigation and toolbar spacing** where compact spacing supports power users while comfy spacing aids discoverability

### Matching Hooks to Properties

When implementing density-aware styling hooks, match the styling hooks with the appropriate CSS properties:

- **For all-sides spacing (top-bottom-left-right):** Use `--slds-g-spacing-var-[size]`
- **For horizontal spacing (left-right):** Use `--slds-g-spacing-var-inline-[size]`
- **For vertical spacing (top-bottom):** Use `--slds-g-spacing-var-block-[size]`
- **For font sizes:** Use `--slds-g-font-scale-var-[size]`
- **For font line height:** Use `--slds-g-font-lineheight-var-base`

### Implementation Example

When the system detects a density change, properties using density-aware hooks automatically adapt:

```css
/* This hook provides different values based on density setting */
.my-component {
  padding: var(--slds-g-spacing-var-4);
  /* Comfy: 1rem | Compact: 0.5rem */
}
```

---

## Available Density-Aware Styling Hooks

The following sections list all density-aware styling hooks available in SLDS. For detailed usage patterns, dos and don'ts, and accessibility requirements for spacing-related hooks, refer to the Spacing and Sizing Styling Hooks documentation.

### Density-Aware Spacing (All Sides)

These density-aware styling hooks control spacing applied equally to all sides of an element (top, bottom, left, right) when the system switches between comfy and compact display density settings.

**Hook Pattern:** `--slds-g-spacing-var-{size}` where `{size}` is the spacing size

> **Reference:** See Spacing and Sizing Styling Hooks for complete usage guidance, accessibility requirements, and implementation patterns.

### Density-Aware Vertical Spacing (Block Axis)

These density-aware styling hooks control spacing along the vertical (block) axis when the system switches between comfy and compact display density settings. This spacing corresponds to top and bottom margins or paddings.

**Hook Pattern:** `--slds-g-spacing-var-block-{size}` where `{size}` is the spacing size

> **Reference:** See Spacing and Sizing Styling Hooks for complete usage guidance, accessibility requirements, and implementation patterns.

### Density-Aware Horizontal Spacing (Inline Axis)

These density-aware styling hooks control spacing along the horizontal (inline) axis when the system switches between comfy and compact display density settings. This spacing corresponds to left and right margins or paddings.

**Hook Pattern:** `--slds-g-spacing-var-inline-{size}` where `{size}` is the spacing size

> **Reference:** See Spacing and Sizing Styling Hooks for complete usage guidance, accessibility requirements, and implementation patterns.

### Density-Aware Line Height

This density-aware styling hook controls the line height when the system switches between comfy and compact display density settings.

**Hook Pattern:** `--slds-g-font-lineheight-var-base`

### Density-Aware Font Scale

These density-aware styling hooks control the font scale when the system switches between comfy and compact display density settings.

**Hook Pattern:** `--slds-g-font-scale-var-{size}` where `{size}` is the density-aware scale step

---

## Responsive Density

Density settings control global spacing, but different screen sizes require additional responsive adjustments. Combine density-aware hooks with responsive design patterns to create interfaces that adapt to both user preferences and device constraints.

### Implementing Responsive Density

When building responsive components, follow this approach:

1. **Use SLDS standard CSS media queries** (30em, 48em, 64em, 80em) to define responsive breakpoints
2. **Apply appropriate SLDS density-aware styling hooks** within each media query breakpoint
3. **Test thoroughly** across device sizes in both density settings to ensure layouts work in all combinations

### Responsive Density Example

Use this pattern for implementing responsive table cell padding that adapts to both viewport size and density setting:

```css
/* Default (Mobile-first) padding */
.my-custom-table td,
.my-custom-table th {
  padding: var(--slds-g-spacing-var-1); /* Smallest padding for narrow screens */
}

/* Medium screens and up (768px+) */
@media (min-width: 48em) {
  .my-custom-table td,
  .my-custom-table th {
    /* Increase padding for tablets / small laptops */
    padding: var(--slds-g-spacing-var-3);
  }
}

/* Large screens and up (1024px+) */
@media (min-width: 64em) {
  .my-custom-table td,
  .my-custom-table th {
    /* Use larger padding for standard desktops */
    padding: var(--slds-g-spacing-var-4);
  }
}
```

---

## Custom Component Guidelines

When building custom components that need to respond to density, follow these guidelines to ensure consistent behavior with SLDS standards.

### Design Guidelines

When implementing custom density-aware components:

- **Analyze similar SLDS components:** Review how existing SLDS components adapt to density and follow similar patterns for consistency
- **Identify which elements need to adapt:** Not everything needs to respond to density changes. Focus density adaptation on spacing, typography, and form layouts
- **Use appropriate styling hooks:** Select hooks that match the property's purpose (spacing-var for padding/margin, font-scale-var for text sizing)
- **Test in both density settings:** Verify that your component works well in both comfy and compact modes before finalizing implementation

### Testing Custom Density Implementation

When validating custom density implementations, ensure that interfaces work well across display density settings:

- **Test the same screens in both comfy and compact settings** to verify visual consistency and functional parity
- **Check rendering in different screen regions and viewports** to ensure responsive density works across device sizes
- **Verify that touch targets remain accessible in compact setting**, meeting minimum size requirements (44×44 pt/dp/px recommended for Salesforce)
- **Confirm that text remains readable and hierarchy is maintained** with reduced spacing in compact mode
- **Verify that localized content displays properly** in both density settings, particularly for languages with longer text strings

---

## SLDS Components with Built-in Density Support

SLDS includes several components with built-in density adaptation that automatically respond to density changes through density-aware styling hooks.

### Components with Automatic Density Adaptation

The following components include density-aware styling hooks that enable automatic adjustments for different display densities:

- [Cards](https://www.lightningdesignsystem.com/2e1ef8501/p/33cd77-cards)
- [File selector](https://www.lightningdesignsystem.com/2e1ef8501/p/77d584-file-selector)
- [Tabs](https://www.lightningdesignsystem.com/2e1ef8501/p/1152cf-tabs)

### Component Blueprints with Configurable Density Support

When using component blueprints, use the standard SLDS markup patterns and CSS classes. The following component blueprints include density-aware styling hooks:

- [Cards](https://www.lightningdesignsystem.com/2e1ef8501/p/33cd77-cards)
- [Feed](https://v1.lightningdesignsystem.com/components/feeds/)
- [File selector](https://www.lightningdesignsystem.com/2e1ef8501/p/77d584-file-selector)
- [Page header](https://v1.lightningdesignsystem.com/components/page-headers/)
- [Path](https://v1.lightningdesignsystem.com/components/path/)
- [Split view](https://v1.lightningdesignsystem.com/components/split-view/)
- [Tabs](https://www.lightningdesignsystem.com/2e1ef8501/p/1152cf-tabs)

> **Reference:** To access component blueprints, see the [Salesforce Lightning Design System 1](https://v1.lightningdesignsystem.com/) website.

---

## Implementation Workflow

Follow this sequence when implementing density-aware components:

### Step 1: Determine Density Requirement

Identify whether your component needs density adaptation:
- **Does the component contain data-dense elements?** (tables, lists, grids)
- **Does spacing significantly impact usability?** (forms, cards, navigation)
- **Will users benefit from density control?** (power users vs. new users)

If the answer is yes to any of these, implement density-aware hooks.

### Step 2: Select Appropriate Hooks

Choose the correct density-aware hooks for your use case:
- **For padding/margin on all sides:** Use `--slds-g-spacing-var-*`
- **For vertical spacing only:** Use `--slds-g-spacing-var-block-*`
- **For horizontal spacing only:** Use `--slds-g-spacing-var-inline-*`
- **For text sizing:** Use `--slds-g-font-scale-var-*`
- **For line height:** Use `--slds-g-font-lineheight-var-base`

### Step 3: Implement with Appropriate Scale

Apply hooks with appropriate scale values:
- **Smaller values (1-4):** For compact elements, tight spacing
- **Medium values (5-8):** For standard component spacing
- **Larger values (9-12):** For section spacing and major divisions

### Step 4: Validate Implementation

Before finalizing, verify the implementation using the Pre-Implementation Checklist below to ensure all requirements are met across both density settings.

---

## Pre-Implementation Checklist

Before generating or modifying any display density related code, verify:

| Requirement | Status |
|-------------|--------|
| **Analysis & Planning** | |
| Component analyzed to determine if density adaptation is beneficial | [ ] |
| Similar SLDS components reviewed for density patterns | [ ] |
| Identified which elements need to adapt vs. remain fixed | [ ] |
| **Hook Selection** | |
| Appropriate density-aware hooks selected (spacing-var, font-scale-var, etc.) | [ ] |
| Hooks matched to correct CSS properties (spacing for margin/padding, font-scale for text) | [ ] |
| Appropriate scale values chosen (1-4 compact, 5-8 standard, 9-12 sections) | [ ] |
| No hard-coded spacing or sizing values (all use styling hooks) | [ ] |
| **Testing: Comfy Mode** | |
| Component tested in comfy density setting | [ ] |
| Visual hierarchy maintained with increased spacing | [ ] |
| Localized content accommodated (longer text strings) | [ ] |
| Critical information remains prominent despite additional whitespace | [ ] |
| **Testing: Compact Mode** | |
| Component tested in compact density setting | [ ] |
| Touch targets meet minimum size requirements (44×44 pt/dp/px recommended) | [ ] |
| Text remains readable with reduced spacing and line height | [ ] |
| Horizontal layouts work in narrower viewports | [ ] |
| **Cross-Density Validation** | |
| Visual consistency maintained - component maintains its visual identity in both modes | [ ] |
| Functional parity confirmed - all functionality works equally well in both densities | [ ] |
| Component behavior consistent with similar SLDS components | [ ] |
| **Responsive & Accessibility** | |
| Responsive breakpoints tested with both density settings | [ ] |
| Component works across viewport sizes in both densities | [ ] |
| Accessibility standards met in both modes (WCAG 2.1 AA) | [ ] |

**Target outcome:** Interfaces that respect user density preferences while maintaining accessibility, visual consistency, and functional parity across both comfy and compact settings.

---

## Related Documentation

For detailed implementation guidance and related concepts, refer to:

- **Spacing and Sizing Styling Hooks** - For complete density-aware spacing hook details, usage patterns, dos and don'ts, and accessibility requirements
- **Spacing and Sizing Overview** - For foundational spacing and sizing principles and the grid system architecture
- **Accessibility Overview** - For ensuring touch targets, contrast, and keyboard navigation work across density settings
- **Typography Guidance** (when available) - For font-scale density hooks and line height implementation patterns
- **Color Overview** - For understanding how spacing and density interact with visual hierarchy and surface layering


