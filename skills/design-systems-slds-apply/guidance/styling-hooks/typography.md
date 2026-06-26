---
id: slds.guidance.hooks.typography
title: Typography Styling Hooks
description: Styling hooks for font size, weight, line height, and content width constraints
summary: "Guidance for typography styling hooks including font-scale, font-weight, line-height, and max-read hooks. Covers systematic text sizing, weight selection, and readability optimization."

artifact_type: reference
domain: styling-hooks
topic: typography

content_format: structured
complexity: intermediate
audience: [implementer]

tasks: [choose, implement, troubleshoot]

refs:
  - slds.guidance.hooks
  - slds.guidance.hooks.spacing
  - slds.guidance.utilities.typography
tags: [styling-hooks, typography, font-scale, font-weight, line-height, text-sizing]
keywords: [font size, text scale, font weight, line height, typography hierarchy, readable content]
---

# Typography Styling Hooks

## Overview

Typography styling hooks provide systematic control over font properties including size, weight, line height, and content width constraints. These hooks ensure visual consistency, establish clear content hierarchy, and maintain readability across all interfaces. Use typography styling hooks to create scalable, accessible text that adapts to different contexts, devices, and user preferences.

---

## `--slds-g-font-scale-*`

### Description

Font scale values that control text size throughout the interface. The styling hook values are relative to the root font size and create a systematic scale from small text to large display text.

**Hook Pattern:** `--slds-g-font-scale-{size}` where `{size}` is the scale step

**Base Size:** `--slds-g-font-size-base` sets the default application font size.

**Scale Categories:**
- **Body text:** Scales `neg-2` through `2`
- **Headings/Titles:** Scales `3` through `6`
- **Display text:** Scales `6` through `8`

### Usage

####  Do

- Use font-scale hooks for all text sizing to maintain typographic consistency
- Use font-scale hooks to establish clear visual hierarchy through systematic size progression
- Use body text scales (neg-2 through 2), heading scales (3-6), and display text scales (7-8) for their intended purposes
- Combine font-scale hooks with appropriate font weights to create distinct type styles
- Use smaller scales (neg-2 through 2) for data-dense interfaces
- Use larger scales (3 through 8) for headings, titles, and prominent text
- Font scales are relative to root font size, enabling global scaling

####  Don't

- Avoid hard-coded pixel or point font sizes instead of using font-scale hooks
- Avoid using scales smaller than neg-1 for body text (readability concerns)
- Avoid using display scales (7-8) for anything other than short, prominent text
- Avoid inconsistent scale selection that breaks typographic hierarchy
- Avoid mixing font-scale hooks with fixed pixel values in the same component
- Avoid using font-scale for spacing or sizing properties (use spacing/sizing hooks instead)

#### Context

- All text content requiring size specification
- Body text and paragraph content
- Headings and titles at all levels
- Form labels and input text
- Button text and interactive element labels
- Display text and hero sections
- Data tables and list content

### Accessibility

- **Regular text**: Minimum 4.5:1 contrast ratio (50-point separation in SLDS grade system)
- **Large text** (18pt or 14pt bold): Minimum 3:1 contrast ratio (40-point separation)
- Use font-scale-1 or larger for all body text to ensure readability
- Smaller scales (neg-2, neg-1): Only for non-essential secondary text with sufficient contrast
- Test text at all scales with actual system fonts (SF Pro, Segoe UI, Roboto)
- Accessibility requirements apply — consult your project's accessibility standards

---

## `--slds-g-font-size-base`

### Description

The base font size property that establishes the foundational text size for the application. All other font scales are calculated relative to this base value.

**Hook Pattern:** `--slds-g-font-size-base`

This is the starting point for the entire typographic system. This is the default size for standard body text.

### Usage

####  Do

- Use font-size-base as the reference point for understanding the scale system
- Use font-size-base as the default size for standard body text in data-dense applications
- Use font-size-base to establish a baseline that other scales build upon
- Use font-size-base directly when base-level text sizing is appropriate

####  Don't

- Avoid modifying the base font size value itself (use scale variants instead)
- Avoid using base size for headings or emphasized content (use larger scales)
- Avoid assuming base is always the right choice (font-scale-1 provides more readable body text)

#### Context

- Default application text size
- Body text in compact interfaces
- Reference point for scale calculations
- Foundational typography sizing

### Accessibility

- 13px (0.8125rem) is at the lower limit for comfortable reading
- Use font-scale-1 (14px equivalent) or larger for primary body text when readability is critical
- Ensure sufficient contrast when using base size text
- Account for user preferences and viewport context when selecting text sizes

---

## `--slds-g-font-weight-*`

### Description

Font weight values that control text thickness and visual emphasis. SLDS 2 uses four primary weights to maintain clarity and consistency across all platforms.

**Hook Pattern:** `--slds-g-font-weight-{weight}` where `{weight}` is the font weight level

**Primary Weights Used in SLDS 2:**
- **Light (weight-3):** Display text at `font-scale-7` and above
- **Regular (weight-4):** Titles (`font-scale-3` through `font-scale-6`) and all body text
- **Semibold (weight-6):** Buttons and smaller body titles (`font-size-base` through `font-scale-2`)
- **Bold (weight-7):** Emphasis within body text only, never for headings

> **Note:** Weights 1, 2, and 5 are available but not commonly used in SLDS 2.

### Usage

####  Do

- Use font-weight-4 (regular) as the default for most body text
- Use font-weight-6 (semibold) for buttons, labels, and minor headings
- Use font-weight-3 (light) for large display text (scales 7-8)
- Use font-weight-7 (bold) sparingly for emphasis within body content
- Pair lighter weights with larger font scales for elegant typography
- Use heavier weights (semibold, bold) for smaller text that needs emphasis

####  Don't

- Avoid using font weights lighter than regular (400) for body text or small sizes
- Avoid using bold (700) for all headings (use semibold instead)
- Avoid using ultra-thin, thin, or medium weights (not part of SLDS 2 standard)
- Avoid inconsistent weight usage that breaks visual hierarchy
- Avoid overusing bold weight (reduces its effectiveness for emphasis)
- Avoid mixing too many different weights in a single interface section

#### Context

- All text requiring weight specification
- Body text (regular weight)
- Headings and titles (regular or semibold)
- Buttons and interactive labels (semibold)
- Display text (light weight for large sizes)
- Emphasis within paragraphs (bold, sparingly)
- Form labels and field text

### Accessibility

- Font weights lighter than regular (400) may be difficult to read, especially at small sizes
- Light weight (300) should only be used for large text (scale 6 and above)
- Ensure sufficient contrast is maintained at all font weights
- Heavier weights (semibold, bold) improve readability for users with low vision
- Regular weight (400) provides optimal readability for most body text
- Test all font weights with actual system fonts across different operating systems

---

## `--slds-g-font-lineheight-*`

### Description

Line height values that control vertical spacing between lines of text. These unitless values are multiplied by the font size to calculate the actual line height.

**Hook Pattern:** `--slds-g-font-lineheight-{level}` where `{level}` is the line height level

**Usage Guidance:**
- **Tight spacing (1-2):** Single-line text, headings
- **Standard spacing (3-4):** Body text, paragraphs (lineheight-4 recommended for body)
- **Spacious (5-6):** Enhanced readability, special cases

### Usage

####  Do

- Use lineheight-4 (1.5) as the default for most body text and paragraphs
- Use lineheight-2 or lineheight-3 (1.25-1.375) for headings and titles
- Use lineheight-1 (1) for single-line text or badges
- Use lineheight-5 (1.75) for enhanced readability in long-form content
- Use tighter line heights for larger font scales (headings)
- Use more generous line heights for smaller font scales (body text)
- Unitless values scale proportionally with font size

####  Don't

- Avoid using lineheight-1 (1) for multi-line text (reduces readability)
- Avoid using lineheight-6 (2) for standard body text (excessive spacing)
- Avoid inconsistent line height values within related content
- Avoid line heights that create awkward vertical rhythm
- Avoid tight line heights (below 1.25) for body text
- Avoid overly generous line heights that disrupt reading flow

#### Context

- All multi-line text content
- Body text and paragraphs (lineheight-4 recommended)
- Headings and titles (lineheight-2 or lineheight-3)
- Single-line text elements (lineheight-1)
- Form field text and labels
- List items and table content
- Long-form content and articles

### Accessibility

- Line height significantly impacts readability for all users
- Use minimum 1.5 line height for body text (WCAG 1.4.12 Text Spacing)
- Adequate line height helps users with dyslexia and other reading difficulties
- Line heights below 1.25 for multi-line text may fail accessibility requirements
- Generous line heights (1.5-1.75) improve scanning and comprehension
- Line height affects the overall vertical rhythm and scanability of content
- Ensure line height accommodates descenders and ascenders without clipping

---

## `--slds-g-sizing-content-*`

### Description

Character-based width constraints for readable text content. These hooks use the `ch` unit to prevent text lines from becoming too long and difficult to read.

**Hook Pattern:** `--slds-g-sizing-content-{level}` where `{level}` is the content width level

**Usage Guidance:**
- **content-1:** Very narrow content, short text blocks
- **content-2:** Narrow columns, captions and descriptions
- **content-3:** Optimal reading width for body text (recommended)

### Usage

####  Do

- Use sizing-content-3 (60ch) for optimal paragraph readability
- Use sizing-content-2 (45ch) for narrower columns or sidebars
- Use sizing-content-1 (20ch) for very short text blocks or labels
- Apply sizing-content hooks as max-width on text containers to prevent overly long lines
- 45-75 characters per line is optimal for readability
- Combine sizing-content hooks with appropriate padding for comfortable reading experience

####  Don't

- Avoid using content sizing hooks for non-text elements (use sizing hooks instead)
- Avoid letting body text extend beyond 75-80 characters per line
- Avoid using content sizing for headings (use heading sizing hooks)
- Avoid applying rigid width constraints where responsive behavior is needed
- Avoid very narrow widths (below 20ch) for multi-line body text
- Avoid using ch units for layouts unrelated to text content

#### Context

- Paragraph text and body content containers
- Article or blog post content areas
- Text blocks within cards or panels
- Description text and longer form labels
- Caption and secondary text containers
- Long-form content that needs readable line lengths

### Accessibility

- Optimal line length (45-75 characters) significantly improves readability
- Overly long lines force excessive eye movement and reduce comprehension
- Character-based width constraints adapt naturally to font size changes
- Appropriate line length helps users with dyslexia and reading difficulties
- Ensures comfortable reading experience for all users regardless of viewport size
- Test content widths with actual text content at various font scales

---

## `--slds-g-sizing-heading-*`

### Description

Character-based width constraints for heading text. Headings typically require shorter line lengths than body text for optimal readability and visual impact.

**Hook Pattern:** `--slds-g-sizing-heading-{level}` where `{level}` is the heading width level

**Usage Guidance:**
- **heading-1:** Very short headings, compact spaces
- **heading-2:** Standard heading width (recommended)
- **heading-3:** Longer headings, subheadings

### Usage

####  Do

- Use sizing-heading-2 (25ch) as the default for most headings
- Use sizing-heading-1 (20ch) for short, punchy headings in cards or panels
- Use sizing-heading-3 (35ch) for longer headings or subheadings
- Apply sizing-heading hooks as max-width on heading elements to prevent awkward line breaks
- Shorter line lengths enhance heading scannability
- Combine sizing-heading hooks with appropriate font scales and weights for clear hierarchy

####  Don't

- Avoid using heading sizing hooks for body text (use content sizing hooks)
- Avoid letting headings extend beyond 35-40 characters
- Avoid rigid width constraints that create awkward wrapping
- Avoid applying heading widths to non-heading text elements
- Avoid very narrow constraints that force single-word lines
- Avoid using heading sizing for display text (large scales 7-8)

#### Context

- Page titles and section headings
- Card and panel headings
- Modal and dialog titles
- Component headings and labels
- Subheadings and secondary titles
- Navigation headers

### Accessibility

- Appropriate heading width improves scannability for all users
- Short, focused headings are easier to process and remember
- Character-based constraints scale naturally with font size and user preferences
- Headings serve as navigation landmarks for screen reader users
- Ensure headings remain readable and don't wrap awkwardly at different viewport sizes
- Test heading widths with various lengths and languages for internationalization

---

## `--slds-g-font-scale-var-*`

### Description

Density-aware font scale hooks that automatically adapt text size when the system switches between comfy and compact display density settings.

**Hook Pattern:** `--slds-g-font-scale-var-{size}` where `{size}` is the density-aware scale step

These hooks provide the same scale categories as fixed font-scale hooks but respond to user density preferences.

### Usage

####  Do

- Use density-aware font scales for components in data-dense contexts (tables, lists, forms)
- Use density-aware font scales when users need control over information density and text size
- Use density-aware font scales for components that appear differently in comfy vs. compact settings
- Use density-aware font scales when text sizing should respond to user preferences automatically
- Density-aware hooks maintain readability across both density modes
- Use density-aware font scales for form labels, table text, and list content that benefits from density control

####  Don't

- Avoid using density-aware scales when fixed sizing is required for consistency
- Avoid mixing density-aware and fixed font scales inconsistently within the same component
- Avoid assuming only one density mode will be used
- Avoid using density-aware hooks for display text or hero sections (remain fixed)
- Avoid applying density-aware scales to branding elements that must remain consistent

#### Context

- Data tables and grid text
- Form field labels and input text
- List items and navigation text
- Card content that adapts to density
- Toolbar and action bar text
- Any component where density-aware sizing improves usability

### Accessibility

- Density-aware fonts support user preferences for information density
- Compact mode must maintain minimum readable font sizes (12px+)
- Ensure text remains legible at the smallest density-aware scale values
- Both comfy and compact modes must meet WCAG 2.1 text size requirements
- Test density-aware typography with actual content in both modes
- Users with low vision may prefer comfy mode for larger text

> **For complete density-aware font scale details** including comfy and compact values, see the [Spacing and Sizing Hooks](ref:slds.guidance.hooks.spacing) for density-aware values.

---

## `--slds-g-font-lineheight-var-base`

### Description

Density-aware line height hook that automatically adjusts vertical text spacing based on user density preferences.

**Hook Pattern:** `--slds-g-font-lineheight-var-base`

This hook provides appropriate line height for body text in both comfy and compact density modes.

### Usage

####  Do

- Use lineheight-var-base for body text in density-aware components
- Use lineheight-var-base for text in tables, lists, and forms that adapt to density
- Use lineheight-var-base when combined with density-aware font scale hooks
- Apply lineheight-var-base to any text that should adjust vertical spacing with density changes
- This hook maintains readability while supporting density preferences

####  Don't

- Avoid using density-aware line height when fixed spacing is required
- Avoid mixing density-aware and fixed line heights inconsistently
- Avoid assuming only one density mode will be used
- Avoid using for headings or display text (typically remain fixed)
- Avoid applying to single-line text elements where line height doesn't impact layout

#### Context

- Body text in density-aware components
- Table cell text and data
- List item content
- Form field text
- Any multi-line text in components that adapt to density settings

### Accessibility

- Appropriate line height is critical for readability in both density modes
- Compact mode must maintain minimum 1.25 line height for multi-line text
- Ensure text remains readable and doesn't feel cramped in compact mode
- Users with reading difficulties benefit from appropriate line height
- Both density modes should provide comfortable reading experience
- Test with actual content to verify readability at both settings

> **For complete density-aware line height details** including specific values and implementation patterns, see the [Spacing and Sizing Hooks](ref:slds.guidance.hooks.spacing) for density-aware values.


