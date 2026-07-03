---
id: slds.guidance.hooks.spacing
title: Spacing and Sizing Styling Hooks
description: Styling hooks for margins, padding, gaps, and element dimensions
summary: "Guidance for spacing and sizing hooks including spacing scale for margins/padding/gaps and sizing scale for element dimensions. Covers the 4-point grid system, density-aware sizing, and touch target requirements."

artifact_type: reference
domain: styling-hooks
topic: spacing-and-sizing

content_format: structured
complexity: intermediate
audience: [implementer]

tasks: [choose, implement, troubleshoot]

refs:
  - slds.guidance.hooks
  - slds.guidance.hooks.borders
  - slds.guidance.hooks.typography
  - slds.guidance.utilities.margin
  - slds.guidance.utilities.padding
  - slds.guidance.utilities.sizing
tags: [styling-hooks, spacing, sizing, margins, padding, gaps, dimensions]
keywords: [spacing scale, sizing scale, 4-point grid, density-aware, touch targets, layout spacing]
---

# Spacing and Sizing Styling Hooks

## Overview

Spacing and sizing styling hooks establish harmony and hierarchy through deliberate spacing and sizing. Spacing controls the empty areas around or within components, while sizing defines the dimensions of elements. These hooks ensure visual consistency, create balance, and guide user focus across the interface.

---

## `--slds-g-spacin`g`-*`

### Description
Base spacing values that create space between elements. The styling hook values are relative to the root font size and follow a modular scale of 4 to align with the 4-point grid system. Use these hooks to set values for margins and padding.

### Usage

####  Do
- Use spacing hooks for margins and padding to create consistent spacing between elements
- Use spacing hooks to establish visual hierarchy through deliberate use of space
- Use spacing hooks for proper alignment of components
- Use spacing hooks to create clear differentiation between grouped and unrelated elements
- Use smaller values (1-4) for compact layouts and tight spacing
- Use medium values (5-8) for standard component spacing
- Use larger values (9-12) for section spacing and major divisions

####  Don't
- Avoid using spacing properties to establish an element's dimensions targeting width and height
- Avoid hard-coded pixel values instead of using spacing hooks
- Avoid breaking the 4-point grid system with custom values
- Avoid inconsistent spacing patterns that disrupt visual rhythm
- Avoid using spacing hooks for element dimensions (use sizing hooks instead)

#### Context
- Margins between components
- Padding within containers
- Gaps in flexbox and grid layouts
- Consistent spacing patterns throughout the interface
- Visual rhythm and balance

### Accessibility
- Consistent spacing improves scanability and readability for all users
- Adequate spacing between interactive elements supports users with motor impairments
- Clear visual grouping through spacing helps users with cognitive disabilities understand relationships between elements
- Padding is the primary method for achieving minimum target sizes on interactive elements
- **Target Size Requirements (WCAG 2.2):**
  - **Desktop/Pointer inputs:** Minimum 24×24 CSS pixels (Level AA required), 44×44 CSS pixels recommended (Level AAA)
  - **Mobile/Touch inputs:** Minimum 44×44 pt/dp/px (industry standard and WCAG 2.1 AAA)
  - **Salesforce applications (mixed environments):** Default to 44×44 for consistency across touch and pointer interactions
- **Spacing Exception:** Targets smaller than 24×24 CSS pixels may be acceptable if sufficient spacing ensures a 24 CSS pixel diameter circle around each target does not intersect another target
- Accessibility requirements apply — consult your project's accessibility standards

---

## `--slds-g-spacing-var-*`

### Description
Density-aware styling hooks that control spacing applied equally to all sides of an element when the system switches between comfy and compact display density settings. The spacing corresponds to the top, bottom, left, and right margins or paddings. Use these hooks to ensure components adapt correctly to the user's chosen density setting.

### Usage

####  Do
- Use density-aware hooks for components that need to adapt to user density preferences
- Use density-aware hooks for padding and margin values that should adjust based on density settings
- Use density-aware hooks for creating responsive spacing that maintains usability in both comfy and compact modes
- Use density-aware hooks when spacing needs to be applied equally to all sides (top, bottom, left, right)
- Density-aware hooks automatically adapt spacing values between comfy and compact display modes

####  Don't
- Avoid using density-aware hooks when fixed spacing is required regardless of density
- Avoid mixing density-aware and fixed spacing hooks inconsistently within the same component
- Avoid assuming only one density mode will be used
- Avoid using when directional spacing (vertical or horizontal only) is more appropriate

#### Context: When to Use Density-Aware Spacing Hooks

**Components that benefit from density-aware hooks:**

| Component Category | Specific Components | Why Density Matters |
|--------------------|---------------------|---------------------|
| Data-dense displays | Tables, lists, grids | More rows visible in compact |
| Form layouts | Form elements, field arrangements | Label positioning changes |
| Containers | Cards, panels | Padding adjusts with density |
| Navigation | Toolbars, tabs | Spacing affects click targets |

**SLDS Components with Built-in Density Support:**
- Cards
- File selector
- Tabs
- Feed
- Page header
- Path
- Split view

**Use density-aware hooks (`--slds-g-spacing-var-*`) when building custom versions of these component types.**

### Accessibility
- Density-aware spacing supports user preferences for information density
- Compact mode maintains usability while maximizing screen space
- Comfy mode provides generous spacing for users who benefit from more breathing room
- Both density modes must maintain minimum target sizes through appropriate padding hook selection:
  - Desktop/Pointer: 24×24 CSS pixels minimum (AA), 44×44 recommended (AAA)
  - Mobile/Touch: 44×44 pt/dp/px minimum
  - Salesforce default: 44×44 for consistency
- Compact mode requires careful padding selection to ensure targets remain accessible in both pointer and touch contexts

---

## `--slds-g-spacing-var-block-*`

### Description
Density-aware styling hooks that control spacing along the vertical (block) axis when the system switches between comfy and compact display density settings. This spacing corresponds to top and bottom margins or paddings. Use these hooks for vertical spacing that needs to adapt to density preferences.

### Usage

####  Do
- Use block spacing hooks for top and bottom margins or padding
- Use block spacing hooks for vertical rhythm and spacing between stacked elements
- Use block spacing hooks for section spacing that adapts to density
- Use block spacing hooks with padding-block or margin-block CSS properties
- Use block spacing hooks for list item vertical spacing, card stack spacing, or form field vertical margins

####  Don't
- Avoid using block spacing hooks for horizontal (left/right) spacing
- Avoid mixing block and inline spacing inconsistently
- Avoid when all-sides spacing would be more appropriate
- Avoid when fixed vertical spacing is required regardless of density

#### Context
- Vertical spacing between list items
- Top and bottom padding in containers
- Section spacing in stacked layouts
- Form field vertical margins
- Vertical rhythm in content areas

### Accessibility
- Vertical spacing supports readability and scanability
- Adequate vertical spacing helps users navigate through content
- Density-aware vertical spacing maintains usability while adapting to user preferences
- Both density modes must maintain clear visual separation between elements
- Vertical padding (top/bottom) contributes to interactive element height and must support minimum target sizing:
  - Desktop/Pointer: 24×24 CSS pixels minimum height (AA), 44×44 recommended (AAA)
  - Mobile/Touch: 44×44 pt/dp/px minimum height
  - Salesforce default: 44×44 height for consistency

---

## `--slds-g-spacing-var-inline-*`

### Description
Density-aware styling hooks that control spacing along the horizontal (inline) axis when the system switches between comfy and compact display density settings. This spacing corresponds to left and right margins or paddings. Use these hooks for horizontal spacing that needs to adapt to density preferences.

### Usage

####  Do
- Use inline spacing hooks for left and right margins or padding
- Use inline spacing hooks for horizontal spacing between adjacent elements
- Use inline spacing hooks for button padding, icon spacing, or horizontal layouts
- Use inline spacing hooks with padding-inline or margin-inline CSS properties
- Use inline spacing hooks for horizontal gaps in flex or grid layouts

####  Don't
- Avoid using inline spacing hooks for vertical (top/bottom) spacing
- Avoid mixing inline and block spacing inconsistently
- Avoid when all-sides spacing would be more appropriate
- Avoid when fixed horizontal spacing is required regardless of density

#### Context
- Horizontal spacing between buttons
- Left and right padding in containers
- Icon and text spacing
- Horizontal gaps in navigation
- Side margins in content layouts

### Accessibility
- Horizontal spacing supports readability and clear visual separation
- Adequate horizontal spacing helps users distinguish between interactive elements
- Density-aware horizontal spacing maintains usability while adapting to user preferences
- Horizontal padding (left/right) contributes to interactive element width and must support minimum target sizing:
  - Desktop/Pointer: 24×24 CSS pixels minimum width (AA), 44×44 recommended (AAA)
  - Mobile/Touch: 44×44 pt/dp/px minimum width
  - Salesforce default: 44×44 width for consistency
- Both density modes must maintain minimum target sizes through appropriate inline padding selection across pointer and touch contexts

---

## `--slds-g-sizing-*`

### Description
Sizing values used to create dimensions of an element, using height and width-based properties. Use these styling hooks for elements such as icons to set their height and width relative to the root element's font-size. Sizing in SLDS uses values with multiples of 8 to align with the 8-point grid system.

### Usage

####  Do
- Use sizing hooks for element dimensions like height and width
- Use sizing hooks for icon sizes, button heights, and component dimensions
- Use sizing hooks for creating consistent, predictable component sizes
- Use sizing hooks for min-width, max-width, min-height, and max-height properties
- Use smaller values (1-9) for icons, buttons, and small elements
- Use larger values (10-16) for containers, panels, and layout widths
- Sizing values scale relative to root font-size for responsive behavior

####  Don't
- Avoid using sizing hooks for margins or padding (use spacing hooks instead)
- Avoid hard-coded pixel values instead of using sizing hooks
- Avoid breaking the 8-point grid alignment with custom dimension values
- Avoid using sizing hooks for spacing between elements
- Avoid mixing sizing and spacing hooks inappropriately

#### Context
- Icon dimensions (width and height)
- Button heights
- Avatar sizes
- Component fixed dimensions
- Container widths and max-widths
- Minimum and maximum element sizes
- Thumbnail dimensions

### Accessibility
- Consistent sizing creates predictable interfaces that are easier to navigate
- Fixed dimensions (height/width) must support target size requirements for interactive elements like icon-only buttons:
  - **Desktop/Pointer:** Minimum 24×24 CSS pixels (WCAG 2.2 Level AA), 44×44 CSS pixels recommended (Level AAA)
  - **Mobile/Touch:** Minimum 44×44 pt/dp/px (industry standard and WCAG 2.1 AAA)
  - **Salesforce applications:** Default to 44×44 for consistency across mixed pointer and touch environments
- Icon sizes must be large enough to be perceivable by users with low vision
- Interactive element sizing should support users with motor impairments
- Account for responsive sizing across different viewport contexts
- **Important:** Most interactive elements achieve target sizing through padding (spacing hooks) rather than fixed dimensions. Sizing hooks are primarily used for icon-only buttons, avatars, and elements where explicit dimensions are required

