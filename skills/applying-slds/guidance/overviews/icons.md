---
id: slds.guidance.overview.icons
title: Icons Overview
description: Foundational principles and guidance for implementing icons in SLDS
summary: "Comprehensive icon guidance covering utility, object, action, doctype, and custom icons. Includes icon selection decision tree, accessibility requirements, and visual specifications."

artifact_type: overview
domain: overviews
topic: icons

content_format: narrative
complexity: foundational
audience: [implementer, designer]

tasks: [learn, choose, implement]

refs:
  - slds.guidance.icons
  - slds.guidance.accessibility.overview

tags: [icons, iconography, utility-icons, object-icons, accessibility]
keywords: [icon types, utility icons, object icons, action icons, icon accessibility, informational icons, decorative icons]
---

# Icons Guidance for SLDS Implementation

**Purpose:** This document provides the foundational principles and guidance for implementing icons in Salesforce Lightning Design System. When working with SLDS components and interfaces, follow these guidelines to ensure consistent, readable, and accessible iconography across all experiences.

---

## About Icons

Icons are symbols used to represent features, functionality, or content. They provide visual cues that help users navigate and interact with the interface more efficiently. Salesforce icon design blends professional and playful qualities, prioritizing simplicity, approachability, and legibility.

**Key Requirement:** To ensure an inclusive experience, implement icon accessibility by distinguishing between informational and decorative icons.

---

## Core Principles

When working with icons in UI interfaces, adhere to these four foundational principles:

1. **Choose the correct icon type for the context.** Match the icon category (utility, object, action, doctype, or product) to its specific functional role in the UI.
2. **Ensure accessibility compliance.** Distinguish between informational icons (requiring labels) and decorative icons (hidden from screen readers).
3. **Maintain visual consistency.** Follow SLDS standards for stroke weight, corner radius, and color usage to ensure a cohesive system.
4. **Follow the grid system and keyline shapes.** Align icons to the 8pt grid and use approved keyline shapes to maintain visual balance and weight.

---

## Icon Types

SLDS includes five distinct icon types, each optimized for specific use cases and platforms.

### 1. Utility Icons
Utility icons are simple, single-color glyphs that identify labels and actions. They are the most commonly used icons across all device types.

**Use for:**
- UI-specific actions (Close, Search, Edit, Settings)
- Global headers and navigation elements
- Button groups, alerts, and toasts
- Feed interactions (Share, Like, Comment)

**Anatomy and Specs:**
- **Grid Sizes:** 16x16px (small), 24x24px (standard).
- **Stroke Weight:** 1px (for 16px), 2px (for 24px).
- **Standard Scales:** 16x16, 24x24, 32x32, 48x48, and 60x60px.
- **Color:** No fixed background shape; can be any color (typically matches adjacent text).

**SLDS 2 Note:** Utility icons remain unchanged from SLDS 1.

### 2. Object Icons (Standard and Custom)
Object icons represent Salesforce entities. Standard icons are for core objects (e.g., Accounts), while custom icons represent customer-created objects.

**Use for:**
- Representing records in list views, search results, and page headers.
- Identifying entity types in related lists and cards.

**Anatomy and Specs:**
- **Background Shape:** White glyph on a solid colored circular background.
- **Grid Size:** 60x60px.
- **Stroke Weight:** 6px.
- **Corner Radius:** 6px (for glyph details).

**SLDS 2 Note:** The background shape for standard object icons has updated from a square to a **circle**.

> ** Accessibility Warning:** Not all custom object icons meet WCAG color contrast guidelines. Always pair them with text as decorative elements.

### 3. Action Icons
Action icons represent the primary ways users accomplish tasks on touch devices. They appear exclusively in the mobile action bar.

**Use for:**
- Touch-device specific actions (New Lead, Log a Call, Share Post).
- Mobile action bar interactions.

**Anatomy and Specs:**
- **Background Shape:** White glyph on a colored circle.
- **Grid Size:** 48x48px.
- **Stroke Weight:** 4px.
- **Artboard:** 52x52px with a 32x32px icon live area.

### 4. Doctype Icons
Doctype icons represent document file formats and are used when a file preview is unavailable.

**Use for:**
- Identifying file types (PDF, Word, Excel, Sheets, etc.).
- Feeds, publishers, cards, and related lists where files are attached.

**Anatomy and Specs:**
- **Background Shape:** Vertical rectangle (56x64px) with a folded corner (earflap).
- **Glyph:** White glyph or text abbreviation of the file extension.
- **Corner Radius:** 6px.

### 5. Product Icons
Product icons represent official Salesforce applications and feature product-specific branding.

**Use for:**
- App Launcher (Desktop) at 48x48px.
- Mobile device home screens and app headers.

**Anatomy and Specs:**
- **Glyph:** Two-color branded glyph on a white background.
- **Stroke:** 4px rounded stroke weight.

---

## Accessibility

Screen readers handle icons based on their functional role.

### Informational Icons
Icons that convey important information not present in surrounding text (e.g., a standalone button icon).
- **Requirement:** Must include an `aria-label` or assistive text.
- **Description Rule:** Describe the *purpose* (e.g., "Upload File"), not the *appearance* (e.g., "paperclip").

### Decorative Icons
Icons that reinforce adjacent text or provide purely visual interest.
- **Requirement:** Must use an empty `alt=""` tag or be hidden from screen readers.
- **Behavior:** Screen readers will skip these to avoid redundant announcements.

---

## Grid System and Keyline Shapes

SLDS icons are built on an 8pt grid system to ensure visual consistency across the entire library. Icons utilize four standard keyline shapes based on BPMN diagram conventions:
- **Circle**
- **Square**
- **Vertical Rectangle**
- **Horizontal Rectangle**

These shapes ensure that icons across different categories maintain consistent visual weight when appearing together.

---

## Mobile Tap Targeting

When designing for mobile, ensure icons are easy to select by providing adequate spacing.
- **Minimum Target Size:** Maintain a minimum tap target of 44x44px.
- **Spacing:** Add generous padding around icons in touch environments to prevent accidental taps.

---

## Usage and Best Practices

### Recommended Usage

| Context | Recommended Icon Type |
|---------|-----------------------|
| Generic UI Actions | Utility Icons |
| Record Representation | Object Icons |
| Mobile Action Bar | Action Icons |
| File Attachments | Doctype Icons |
| App Navigation | Product Icons |

### Implementation Constraints

- **Utility Color Matching:** Always match utility icon color to adjacent text (e.g., use `on-surface-3` if the title is that color).
- **White Glyphs:** Use only white glyphs for Object and Action icons.
- **Standard Scaling:** Only scale icons to standard sizes (16, 24, 32, 48, 60px). Avoid scaling outside these increments.

### Visual Standards (Dos and Don’ts)

#### Utility Icons
- ** Do:** Scale to standard pixel sizes (16x16, 24x24, etc.).
- ** Do:** Use front-facing solid shapes for clarity.
- ** Don't:** Use outlines or angled/dimensional views.
- ** Don't:** Make icons overly complicated for small scales.

#### Object Icons
- ** Do:** Use white glyphs on approved colored backgrounds.
- ** Do:** Use approved BPMN keyline shapes.
- ** Don't:** Use unapproved background shapes or non-white glyphs.

#### Doctype Icons
- ** Do:** Represent the earflap without a visible gap.
- ** Don't:** Add a gap or separation to the icon's earflap.

---

## Recommended Specs Summary

| Icon Type | Grid Size | Stroke Weight | Corner Radius | Artboard Size |
|-----------|-----------|---------------|---------------|---------------|
| Utility (S) | 16x16px | 1px | 1px | 52x52px |
| Utility (M) | 24x24px | 2px | 2px | 52x52px |
| Object | 60x60px | 6px | 6px | 100x100px |
| Action | 48x48px | 4px | 4px | 52x52px |
| Doctype | 56x64px | - | 6px | 56x64px |
| Product | 48x48px | 4px | - | - |

---

## Implementation Workflow

Follow this sequence when implementing icons:

1. **Identify Icon Need:** Determine the semantic role (action, record type, file, etc.).
2. **Select Icon Type:** Choose the category that matches the role (e.g., Utility for actions).
3. **Apply Sizing and Color:** Use standard scales and match colors to context (for Utility).
4. **Implement Accessibility:** Add `aria-label` for informational icons; use empty `alt` for decorative.
5. **Validate:** Check against the pre-implementation checklist for compliance.

---

## Pre-Implementation Checklist

| Requirement | Status |
|-------------|--------|
| **Type Selection** | |
| Icon type matches functional role (Utility/Object/Action/Doctype/Product) | [ ] |
| **Sizing & Specs** | |
| Icon scaled to standard size (16/24/32/48/60px) | [ ] |
| Anatomy specs (stroke, radius) match the chosen scale | [ ] |
| **Color & Consistency** | |
| Utility icon color matches adjacent text | [ ] |
| Object/Action icons use white glyphs on colored backgrounds | [ ] |
| **Accessibility** | |
| Informational icons have descriptive `aria-label` (purpose, not look) | [ ] |
| Decorative icons have empty `alt=""` or are hidden | [ ] |
| **Mobile** | |
| Touch target meets minimum 44x44px requirement | [ ] |
