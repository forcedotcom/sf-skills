---
id: slds.guidance.overview.typography
title: Typography Overview
description: Foundational principles and guidance for implementing typography in SLDS
summary: "Comprehensive typography guidance covering system fonts, font scales, weights, line heights, and content width. Includes core principles, implementation workflow, and pre-implementation checklist."

artifact_type: overview
domain: overviews
topic: typography

content_format: narrative
complexity: foundational
audience: [implementer, designer]

tasks: [learn, choose, implement]

refs:
  - slds.guidance.hooks.typography

tags: [typography, fonts, text, hierarchy, readability, accessibility]
keywords: [font scale, font weight, line height, system fonts, typography hierarchy, text sizing, legibility]
---

# Typography Guidance for SLDS Implementation

**Purpose:** This document provides the foundational principles and guidance for implementing typography in Salesforce Lightning Design System. When working with SLDS components and interfaces, follow these guidelines to ensure consistent, readable, and accessible typography across all experiences.

---

## About Typography

Typography is a cornerstone of any design system, shaping how users consume and understand content. In the Salesforce Lightning Design System (SLDS), typography is standardized to create a consistent, readable, and accessible experience across all products. SLDS uses a predefined set of font sizes, weights, and styles that adapt to various screen sizes and contexts.

The design system leverages system fonts provided by a user device's operating system, ensuring optimal performance and native feel across different platforms. The system font varies by device: SF Pro on macOS/iOS, Segoe UI on Windows, and Roboto on Android.

**Key Requirement:** Because typography establishes the foundation for content hierarchy and readability, implement SLDS typography styling hooks consistently across all interfaces. Typography choices directly impact user comprehension, task completion speed, and overall accessibility.

---

## Core Principles

When working with typography in UI interfaces, adhere to these foundational principles:

1. **Prioritize legibility above all else.** To make text readable across devices and contexts, use appropriate font sizes and weights from the SLDS scale. Overly light or small text for essential content compromises usability and accessibility.

2. **Establish clear visual hierarchy.** To guide users through content efficiently, consistently apply the predefined heading styles, font scales, and text colors. Maintaining the SLDS typography scale creates predictable visual patterns that help users navigate complex interfaces.

3. **Use styling hooks for all typography.** To ensure consistency and receive automatic SLDS updates, use typography styling hooks instead of hardcoding font styles. Styling hooks provide resilience across theme changes and density settings.

4. **Meet accessibility requirements.** To make content accessible to all users, ensure proper contrast between text and background colors, use minimum font sizes for readability, and maintain appropriate line heights. 

---

## System Fonts

SLDS leverages the native fonts provided by each operating system, creating a seamless, high-performance user experience that feels natural on every platform.

### Why System Fonts?

System fonts provide these benefits:
- **Optimal performance:** No font downloads required, reducing page load time
- **Native appearance:** Interfaces feel natural on each platform
- **Automatic updates:** Users benefit from OS-level font improvements
- **Consistent sizing:** All font weights and sizes remain identical across system fonts

### Fonts by Platform

The Figma library for SLDS 2 uses SF Pro as its primary typeface for design work. In production, the actual font rendered depends on the user's operating system:

| Platform | System Font | Usage |
|----------|-------------|-------|
| macOS, iOS | SF Pro | Apple devices and design tools |
| Windows | Segoe UI | Windows-based devices |
| Android | Roboto | Android devices |

### Download System Fonts

For design work in Figma or other design tools, download the appropriate system font:

- **[Download SF Pro](https://devimages-cdn.apple.com/design/resources/download/SF-Pro.dmg)** - For macOS and iOS design work
- **[Download Segoe UI](https://aka.ms/WebFluentFonts)** - For Windows design work
- **[Download Roboto](https://fonts.google.com/specimen/Roboto)** - For Android design work

> **Important:** All font weights and sizes remain the same across all system fonts. A component designed with SF Pro will render identically in Segoe UI or Roboto in terms of sizing and spacing.

---

## Font Scale System

The SLDS font scale provides a systematic range of font sizes that create consistent typographic hierarchy across all interfaces. Font sizes are scaled based on the `--slds-g-font-size-base` property, which sets the default font size of the application.

### How Font Scale Works

The font scale uses styling hooks to provide systematic text sizing across the interface.

**Hook Pattern:** `--slds-g-font-scale-{size}` where `{size}` is the scale step

**Base Size:** `--slds-g-font-size-base` sets the default font size of the application.

**Scale Categories:**
- **Body text:** Scales `neg-2` through `2`
- **Headings/Titles:** Scales `3` through `6`
- **Display text:** Scales `6` through `8`

Use smaller scales for compact interfaces and larger scales for prominent content.

> **Note:** In SLDS 2, font sizes differ slightly from the original Salesforce Lightning Design System (SLDS 1). Review your components to verify the new type scale specification when migrating from SLDS 1 to SLDS 2.

---

## Font Weight System

SLDS 2 uses font weights to maintain clarity and consistency across all platforms. Each weight serves a specific purpose in the typographic hierarchy.

### Available Font Weights

SLDS 2 uses four primary font weights to maintain clarity and consistency.

**Hook Pattern:** `--slds-g-font-weight-{weight}` where `{weight}` is the font weight level

**Primary Weights:**
- **Light (weight-3):** Display text at `font-scale-7` and above
- **Regular (weight-4):** Titles (`font-scale-3` through `font-scale-6`) and all body text
- **Semibold (weight-6):** Buttons and smaller body titles (`font-size-base` through `font-scale-2`)
- **Bold (weight-7):** Emphasis within body text only, never for headings

> **Important:** Do not use font weights lighter than Regular (weight-4) for body text or small sizes, as they compromise readability and accessibility.

---

## Font Color for Typography

Typography colors in SLDS use semantic color tokens to ensure proper contrast and accessibility across all surfaces and themes. The color system is designed to work seamlessly with both light and dark backgrounds.

### On-Surface Colors for Text

For text on light backgrounds (surfaces), use the on-surface token hierarchy:

- **`--slds-g-color-on-surface-1`** - De-emphasized text (captions, placeholders, secondary content)
- **`--slds-g-color-on-surface-2`** - Body text (standard content, labels, descriptions)
- **`--slds-g-color-on-surface-3`** - Headings and titles only (reserved for headings, not body text)

For text on dark backgrounds, use:

- **`--slds-g-color-on-surface-inverse-1`** - Primary foreground color for inverse surfaces
- **`--slds-g-color-on-surface-inverse-2`** - Secondary foreground color for inverse surfaces

### Specialized Text Colors

For specific text contexts, use these tokens:

- **Text links:** Use `--slds-g-color-accent-2` (electric blue 40) for accessible links on light backgrounds
- **Error messages:** Use `--slds-g-color-error-1` or `--slds-g-color-on-error-1` as appropriate
- **Warning messages:** Use `--slds-g-color-warning-1` or `--slds-g-color-on-warning-1` as appropriate
- **Success messages:** Use `--slds-g-color-success-1` or `--slds-g-color-on-success-1` as appropriate

> **For complete typography color guidance** including pairing rules, contrast requirements, and accessibility requirements, see the Surface Color Styling Hooks documentation.

---

## Type Styles

A type style is a combination of font scale, weight, and line height designed for a specific purpose. SLDS has three type styles: body, title, and display. Each type style serves a distinct role in the content hierarchy.

### Body Type

Text that conveys details in the form of phrases, labels, sentences, or blocks of copy.

**Recommended Scales:** `--slds-g-font-scale-neg-2` through `--slds-g-font-scale-2`
**Recommended Weights:** Regular (weight-4), Semibold (weight-6) for emphasis

**When to use:**
- Paragraph content and long-form text
- Form labels and input text
- List items and table cells
- Button text (with semibold weight)

### Title Type

Headings of components or body content that establish hierarchy and structure.

**Recommended Scales:** `--slds-g-font-scale-3` through `--slds-g-font-scale-6`
**Recommended Weights:** Regular (weight-4), Semibold (weight-6)

**When to use:**
- Page titles and section headings
- Card and panel headings
- Modal and dialog titles
- Navigation headers

### Display Type

Short titles in banners or prominent sections to make a bold visual statement.

**Recommended Scales:** `--slds-g-font-scale-6` through `--slds-g-font-scale-8`
**Recommended Weights:** Light (weight-3)

**When to use:**
- Hero sections and landing page headers
- Empty state messages
- Large promotional banners
- Onboarding screens

---

## Usage Guidance

When implementing typography in SLDS, follow these best practices to maintain consistency and accessibility.

For detailed usage guidance, do's and don'ts, and accessibility considerations for each typography styling hook, refer to the Typography Styling Hooks documentation.

**Key principles:**
- Use predefined SLDS text styles from the typography scale
- Ensure sufficient contrast between text and backgrounds (minimum 4.5:1 for body text)
- Avoid ALL CAPS for any text or labels (reduces readability)
- Never hardcode font sizes in pixels or points

### Combining Typography Properties

When implementing typography, follow this systematic approach:

1. **Start with the content type:** Determine whether you need body, title, or display type
2. **Select the appropriate scale:** Choose a font scale that matches the content hierarchy
3. **Apply the correct weight:** Use Regular for most content, Semibold for emphasis, Bold sparingly
4. **Use semantic colors:** Apply on-surface tokens based on content importance (1 for low emphasis, 3 for high emphasis)
5. **Set line height:** Ensure appropriate line spacing for readability

---

## Implementation Workflow

Follow this sequence when implementing typography in your components:

### Step 1: Identify Typography Need

Determine the purpose and hierarchy of your text content:
- **Is this body content?** (paragraphs, labels, descriptions)
- **Is this a heading or title?** (section headers, component titles)
- **Is this display text?** (hero sections, prominent banners)
- **What level of emphasis is needed?** (primary, secondary, tertiary)

### Step 2: Select Font Scale and Weight

Choose the appropriate combination based on the content type:
- **Body text:** `font-scale-1` or `font-scale-2` with `font-weight-4` (regular)
- **Emphasized body:** Same scale with `font-weight-6` (semibold)
- **Small headings:** `font-scale-3` or `font-scale-4` with `font-weight-6`
- **Large headings:** `font-scale-5` or `font-scale-6` with `font-weight-4` or `font-weight-6`
- **Display text:** `font-scale-7` or `font-scale-8` with `font-weight-3` (light)

### Step 3: Apply Color Tokens

Select the appropriate color token based on emphasis and context:
- **High-emphasis text (headings, titles):** `--slds-g-color-on-surface-3`
- **Standard body text:** `--slds-g-color-on-surface-2`
- **De-emphasized text (captions, metadata):** `--slds-g-color-on-surface-1`
- **Links:** `--slds-g-color-accent-2`
- **Feedback messages:** Appropriate feedback color tokens

> **Reference:** See the Surface Color Styling Hooks documentation for complete color pairing guidance.

### Step 4: Evaluate Density Awareness

Determine if the typography should adapt to user density preferences:
- **Does this component appear in data-dense contexts?** (tables, lists, forms)
- **Would users benefit from density control?** (power users vs. casual users)
- **If yes:** Use `--slds-g-font-scale-var-*` instead of fixed scale
- **If no:** Use fixed `--slds-g-font-scale-*` for consistent sizing

> **Reference:** See the Display Density Overview for density-aware typography guidance.

### Step 5: Handle Exceptions

If standard patterns don't fit your requirement:
1. Document why standard typography styles don't apply
2. Verify contrast requirements manually (minimum 4.5:1 for body text)
3. Ensure the custom approach maintains brand consistency
4. Test across all platforms and screen sizes
5. Flag for design system team review

### Step 6: Validate Implementation

Before finalizing, verify the implementation using the Pre-Implementation Checklist below to ensure all typography requirements are met.

---

## Pre-Implementation Checklist

Before generating or modifying any typography-related code, verify:

| Requirement | Status |
|-------------|--------|
| **Typography Classification** | |
| Content type identified (body/title/display) | [ ] |
| Emphasis level determined (primary/secondary/tertiary) | [ ] |
| Context appropriate for chosen type style | [ ] |
| **Scale & Weight Selection** | |
| Font scale selected from SLDS predefined values | [ ] |
| Font weight appropriate for content type and size | [ ] |
| No hard-coded pixel or point values used | [ ] |
| Styling hooks used instead of direct values | [ ] |
| **Color & Contrast** | |
| Semantic color tokens used (on-surface, accent, feedback) | [ ] |
| Contrast requirements met (minimum 4.5:1 for body text) | [ ] |
| Color not used as sole indicator of meaning | [ ] |
| Colors work across light and dark modes where applicable | [ ] |
| **Accessibility** | |
| Text remains readable at minimum supported sizes | [ ] |
| Line height provides adequate spacing for readability | [ ] |
| Font weight not too light for small text sizes | [ ] |
| ALL CAPS avoided (reduces readability) | [ ] |
| Sufficient contrast between text and background (WCAG 2.1 AA) | [ ] |
| **Density & Responsiveness** | |
| Density-aware hooks used where appropriate (`font-scale-var-*`) | [ ] |
| Typography tested in both comfy and compact density settings | [ ] |
| Text scales appropriately across viewport sizes | [ ] |
| Long text strings tested (internationalization requirement) | [ ] |
| **Platform Consistency** | |
| Typography tested with system fonts (SF Pro, Segoe UI, Roboto) | [ ] |
| Sizing and spacing consistent across platforms | [ ] |
| Renders correctly on target devices and browsers | [ ] |

**Target outcome:** Clear, readable, accessible typography that maintains visual hierarchy and brand consistency across all platforms, screen sizes, and user density preferences.
