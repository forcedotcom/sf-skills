---
id: slds.guidance.overview.spacing-and-sizing
title: Spacing and Sizing Overview
description: Foundational principles for spacing and sizing decisions in SLDS
summary: "Comprehensive spacing and sizing guidance covering the 4-point grid system, spacing scales, sizing scales, and responsive design patterns. Includes implementation workflow and pre-implementation checklist."

artifact_type: overview
domain: overviews
topic: spacing-and-sizing

content_format: narrative
complexity: foundational
audience: [implementer, designer]

tasks: [learn, choose, implement]

refs:
  - slds.guidance.hooks.spacing

tags: [spacing, sizing, layout, grid, margins, padding, dimensions]
keywords: [4-point grid, spacing scale, sizing scale, margins, padding, gaps, responsive design, layout]
---

# Spacing and Sizing Guidance for SLDS Implementation

**Purpose:** This document provides the foundational principles and constraints for all spacing and sizing decisions in Salesforce Lightning Design System. When implementing components and layouts, follow these guidelines to ensure visual harmony, hierarchy, and consistency across all experiences.

---

## Core Principles

When working with spacing and sizing in UI interfaces, adhere to these foundational principles:

1. **Establish harmony through consistency.** Spacing and sizing create predictable patterns that help users navigate interfaces efficiently. Use the spacing and sizing styling hooks consistently to create visual rhythm and balance.

2. **Create hierarchy through deliberate spacing.** Strategic use of space directs user attention, differentiates grouped elements from unrelated ones, and establishes clear relationships between components.

3. **Ensure scalability and responsiveness.** Components must adapt seamlessly across devices and screen sizes. Use relative units and the SLDS styling hooks to support responsive design patterns.

---

## Spacing Fundamentals

### What is Spacing?

Spacing controls the empty areas around or within components, such as margins, padding, and gaps between elements. In the context of styling hooks, spacing refers to padding or margins applied around an element.

**Spacing defines these visual aspects:**
- Proper alignment of components
- Clear differentiation of grouped and unrelated elements
- White space that directs user attention to key content or actions

### Benefits of Effective Spacing

Effective spacing provides these benefits:
- **Improves readability** by preventing visual clutter and creating breathing room
- **Reduces cognitive load** by establishing clear visual relationships
- **Enhances usability** by making interactive elements easier to target and distinguish

### The 4-Point Grid System

SLDS spacing follows a modular scale based on multiples of 4, aligning with the 4-point grid system. This mathematical foundation ensures consistent spacing relationships throughout the interface.

**System Architecture:**
- Base unit: 0.25rem (4px equivalent)
- Scale progression: Each step increases in predictable increments
- Values are relative to root font size for scalability

### Density-Aware Spacing

SLDS provides density-aware spacing hooks that automatically adapt when the system switches between comfy and compact display density settings. These hooks ensure components respond appropriately to user density preferences.

**Hook Patterns:**
- **All-Sides:** `--slds-g-spacing-var-{size}` - Applies equally to top, bottom, left, right
- **Vertical (Block):** `--slds-g-spacing-var-block-{size}` - Top and bottom margins or padding
- **Horizontal (Inline):** `--slds-g-spacing-var-inline-{size}` - Left and right margins or padding

Where `{size}` represents the scale value appropriate for your spacing need.

> **For complete density-aware hook details** including comfy and compact values, refer to the Spacing and Sizing Styling Hooks documentation.

---

## Sizing Fundamentals

### What is Sizing?

Sizing refers to the dimensions of a component, such as height, width, or size variants. In the context of styling hooks, sizing refers to the fixed height or width of an element. When sizes are consistent, it's easier for users to predict where things will be on the page. This predictability makes the interface easier to use.

**Sizing defines these aspects:**
- Physical dimensions of elements like buttons, icons, and cards
- Scalable size options (small, medium, large) to accommodate different contexts
- Responsive behavior to ensure designs function well on all screen sizes

### Benefits of Consistent Sizing

Consistent sizing provides these benefits:
- **Creates predictability** by establishing recognizable component sizes
- **Enhances usability** by making interactive targets appropriately sized
- **Supports responsiveness** by providing size options that scale appropriately

### The 8-Point Grid System

While spacing uses a 4-point grid, sizing aligns with an 8-point grid system using multiples of 8. This ensures dimension values work harmoniously with the spacing system while providing appropriate scaling for component dimensions.

**System Architecture:**
- Smaller increments for precise control (1-9)
- Larger increments for major dimensions (10-16)
- Values are relative to root font size for scalability

---

## Understanding Padding vs. Margin

When implementing layouts, understand the distinction between padding and margin as they serve different purposes:

**Padding:**
- Controls **internal spacing** within a component
- Creates breathing room between a container's edge and its content
- Affects the component's total dimensions (when using border-box)
- Use spacing hooks for padding values

**Margin:**
- Defines **external spacing** around a component
- Creates separation between adjacent elements
- Does not affect the component's own dimensions
- Use spacing hooks for margin values

**Design systems follow a consistent margin strategy** so that components interact predictably and maintain harmonious spacing throughout the interface. Apply spacing values systematically rather than arbitrarily to maintain this consistency.

---

## Implementation Workflow

Follow this sequence when implementing any spacing or sizing solution:

### Step 1: Identify the Spacing/Sizing Need

Determine what you're trying to accomplish:
- **For spacing:** Is this internal space (padding) or external space (margin)?
- **For spacing:** Does this need to adapt to density settings (use density-aware hooks)?
- **For sizing:** Are you setting dimensions (height/width) for an element?
- **For sizing:** Is this for a small element (icon, button) or larger container?

### Step 2: Choose the Appropriate Scale

Evaluate the visual hierarchy and relationship:
- **Smaller values (1-4):** Compact layouts, tight spacing, small elements
- **Medium values (5-8):** Standard spacing, common component sizes
- **Larger values (9-12/16):** Section spacing, large containers, major divisions

### Step 3: Apply the Styling Hook

Use the appropriate hook for your context:
- **Standard spacing:** `--slds-g-spacing-*` for fixed spacing values
- **Density-aware spacing (all sides):** `--slds-g-spacing-var-*` for adaptive spacing
- **Density-aware vertical spacing:** `--slds-g-spacing-var-block-*` for top/bottom adaptive spacing
- **Density-aware horizontal spacing:** `--slds-g-spacing-var-inline-*` for left/right adaptive spacing
- **Element sizing:** `--slds-g-sizing-*` for dimensions

### Step 4: Handle Exceptions

If no standard hook matches the requirement:
1. Document why standard patterns don't apply
2. Evaluate if a combination of hooks could achieve the goal
3. Ensure the custom approach maintains visual consistency
4. Flag for design system team review

### Step 5: Validate Implementation

Before finalizing, verify the implementation using the Pre-Implementation Checklist below to ensure all spacing and sizing requirements are met.

---

## Pre-Implementation Checklist

Before generating or modifying any spacing or sizing related code, verify:

| Requirement | Status |
|-------------|--------|
| **Need Identification** | |
| Spacing need identified (padding vs. margin, internal vs. external space) | [ ] |
| Sizing need identified (element dimensions vs. container size) | [ ] |
| Determined if spacing should adapt to density settings | [ ] |
| **Hook Selection & Scale** | |
| Appropriate hook selected from defined scale (no hard-coded pixel values) | [ ] |
| Scale value chosen matches visual hierarchy (1-4 compact, 5-8 standard, 9-12/16 sections) | [ ] |
| Correct hook type selected (spacing vs. spacing-var vs. sizing) | [ ] |
| **Grid System Alignment** | |
| Spacing aligns with 4-point grid system | [ ] |
| Sizing aligns with 8-point grid system | [ ] |
| **Proper Hook Usage** | |
| Spacing hooks used only for margins/padding (not dimensions) | [ ] |
| Sizing hooks used only for dimensions (not spacing) | [ ] |
| Semantic styling hooks used (no hard-coded values) | [ ] |
| **Density & Responsiveness** | |
| Density-aware hooks used when components need to adapt | [ ] |
| Density-aware hooks selected support both comfy and compact modes where applicable | [ ] |
| Layout responsive design requirements applied for viewport adaptability | [ ] |
| Works across all viewport sizes | [ ] |
| **Visual Consistency** | |
| Visual hierarchy maintained through spacing choices | [ ] |
| Component spacing consistent with similar elements | [ ] |
| Follows established patterns for similar components | [ ] |

**Target outcome:** Harmonious, predictable interfaces that maintain visual consistency and adapt seamlessly across devices, screen sizes, and user density preferences.

---

## Related Documentation

For detailed implementation guidance, refer to:
- **Spacing and Sizing Styling Hooks** - For complete hook listings, density-aware values, and usage patterns
- **Color Overview** - For understanding how spacing interacts with visual depth and surface layering
- **Accessibility Overview** - For ensuring spacing supports touch targets and keyboard navigation

