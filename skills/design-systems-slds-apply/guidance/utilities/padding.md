---
id: slds.guidance.utilities.padding
title: Padding Utilities
description: SLDS padding utility classes for internal spacing
summary: "Utilities for internal spacing within elements. Includes directional variants, size scale from xxx-small to xx-large, and variable density classes."

artifact_type: reference
domain: utilities
topic: padding

content_format: structured
complexity: intermediate
audience: [implementer]

tasks: [implement]

refs:
  - slds.guidance.utilities
  - slds.guidance.overview.utilities
  - slds.guidance.utilities.margin
  - slds.guidance.hooks.spacing

tags: [utilities, padding, spacing, internal-spacing]
keywords: [slds-p, slds-p-around, slds-p-horizontal, slds-p-vertical, padding]
---

# Padding - Internal Spacing

Internal spacing within elements. Base unit: **4px**.

## Size Scale

| Size | Token | Value | Pixels |
|------|-------|-------|--------|
| `none` | 0 | 0 | 0px |
| `xxx-small` | `--slds-g-spacing-1` | 0.125rem | 2px |
| `xx-small` | `--slds-g-spacing-2` | 0.25rem | 4px |
| `x-small` | `--slds-g-spacing-3` | 0.5rem | 8px |
| `small` | `--slds-g-spacing-4` | 0.75rem | 12px |
| `medium` | `--slds-g-spacing-5` | 1rem | 16px |
| `large` | `--slds-g-spacing-6` | 1.5rem | 24px |
| `x-large` | `--slds-g-spacing-7` | 2rem | 32px |
| `xx-large` | `--slds-g-spacing-8` | 3rem | 48px |

## Core Classes

### Directional Padding

| Class | Purpose |
|-------|---------|
| `slds-p-top_*` | Applies padding to element's top edge |
| `slds-p-right_*` | Applies padding to element's right edge |
| `slds-p-bottom_*` | Applies padding to element's bottom edge |
| `slds-p-left_*` | Applies padding to element's left edge |
| `slds-p-horizontal_*` | Applies padding to left and right edges |
| `slds-p-vertical_*` | Applies padding to top and bottom edges |
| `slds-p-around_*` | Applies padding to all four edges |

### Special Classes

| Class | Purpose |
|-------|---------|
| `slds-has-cushion` | Applies default padding of 12px (small) to all sides |

## Common Patterns

```html
<!-- Card with standard padding -->
<div class="slds-card">
  <div class="slds-card__header slds-p-around_medium">
    <!-- 16px padding on all sides -->
    Card Header
  </div>
  <div class="slds-card__body slds-p-horizontal_medium slds-p-vertical_small">
    <!-- 16px left/right, 12px top/bottom -->
    Card Content
  </div>
</div>

<!-- Button with extra padding -->
<button class="slds-button slds-button_neutral slds-p-horizontal_large">
  <!-- 24px left and right padding for wider button -->
  Wide Action Button
</button>

<!-- Form element spacing -->
<div class="slds-form-element slds-p-bottom_small">
  <!-- 12px bottom padding between form elements -->
  <label class="slds-form-element__label">Field Label</label>
  <div class="slds-form-element__control">
    <input type="text" class="slds-input" />
  </div>
</div>

<!-- Modal with appropriate padding -->
<div class="slds-modal__container">
  <div class="slds-modal__header slds-p-around_medium">
    <!-- 16px padding in header -->
    Modal Title
  </div>
  <div class="slds-modal__content slds-p-around_large">
    <!-- 24px padding for modal body content -->
    Modal content with comfortable spacing
  </div>
  <div class="slds-modal__footer slds-p-around_medium">
    <!-- 16px padding in footer -->
    Footer actions
  </div>
</div>

<!-- List item with asymmetric padding -->
<li class="slds-p-vertical_x-small slds-p-horizontal_medium">
  <!-- 8px top/bottom, 16px left/right for list items -->
  List item with comfortable touch target
</li>
```

## Variable Density Classes

Adapt padding to user density preferences (comfy/compact modes).

| Class | Comfy Mode | Compact Mode |
|-------|------------|--------------|
| `slds-var-p-around_small` | 0.75rem (12px) | 0.375rem (6px) |
| `slds-var-p-around_medium` | 1rem (16px) | 0.5rem (8px) |
| `slds-var-p-around_large` | 1.5rem (24px) | 0.75rem (12px) |
| `slds-var-p-horizontal_medium` | 1rem (16px) | 0.5rem (8px) |
| `slds-var-p-vertical_medium` | 1rem (16px) | 0.5rem (8px) |

## Common Use Cases

| Use Case | Class | Value |
|----------|-------|-------|
| Card body padding | `slds-p-around_medium` | 16px all sides |
| Button padding | `slds-p-horizontal_medium` | 16px left/right |
| Modal content | `slds-p-around_large` | 24px all sides |
| List item padding | `slds-p-vertical_x-small slds-p-horizontal_medium` | 8px top/bottom, 16px left/right |
| Compact form fields | `slds-p-around_small` | 12px all sides |
| Section padding | `slds-p-vertical_large` | 24px top/bottom |
| Icon button padding | `slds-p-around_x-small` | 8px all sides |
| Remove padding | `slds-p-around_none` | 0px all sides |

## Best Practices

✅ Use `slds-p-around_medium` (16px) for standard component padding
✅ Use `slds-p-around_small` (12px) for compact layouts and dense information
✅ Use `slds-p-around_large` (24px) for spacious layouts and primary content areas
✅ Use `slds-p-horizontal_*` and `slds-p-vertical_*` for asymmetric padding
✅ Use `slds-has-cushion` for quick default padding of 12px
✅ Use variable density classes (`slds-var-p-*`) for responsive density

❌ Avoid combining `slds-has-cushion` with other padding classes
❌ Avoid using padding for external spacing between elements (use [Margin Utilities](ref:slds.guidance.utilities.margin) instead)
❌ Avoid mixing different size scales within the same component
❌ Avoid excessive padding that creates wasted space