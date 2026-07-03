---
id: slds.guidance.utilities.themes
title: Themes Utilities
description: SLDS theme utility classes for background and text colors
summary: "Utilities for applying color themes including default, shade, inverse, and semantic states (success, info, warning, error, offline)."

artifact_type: reference
domain: utilities
topic: themes

content_format: structured
complexity: intermediate
audience: [implementer]

tasks: [implement]

refs:
  - slds.guidance.utilities
  - slds.guidance.overview.utilities
  - slds.guidance.hooks.color

tags: [utilities, themes, colors, backgrounds]
keywords: [slds-theme, background colors, semantic colors, inverse themes]
---

# Themes - Color & Background

Applying consistent color themes to containers and components.

## Core Classes

| Class | Purpose |
|-------|---------|
| `slds-theme_default` | White background with default text color |
| `slds-theme_shade` | Gray background (#F3F3F3) for subtle contrast |
| `slds-theme_inverse` | Dark blue background with white text |
| `slds-theme_alt-inverse` | Darker blue background variant |

## Semantic State Themes

| Class | Background Color | Text Color |
|-------|-----------------|------------|
| `slds-theme_success` | Green (#4BCA81) | White |
| `slds-theme_info` | Gray-blue (#706E6B) | White |
| `slds-theme_warning` | Yellow (#FFB75D) | Black |
| `slds-theme_error` | Red (#EA001E) | White |
| `slds-theme_offline` | Black (#444) | White |

## Texture Modifier

| Class | Purpose |
|-------|---------|
| `slds-theme_alert-texture` | Adds diagonal striped pattern overlay |

## Common Patterns

```html
<!-- Card with default theme -->
<div class="slds-card slds-theme_default">
  <div class="slds-card__header">Default themed card</div>
  <div class="slds-card__body">Card content with white background</div>
</div>

<!-- Section with shade background -->
<section class="slds-theme_shade slds-p-around_medium">
  <!-- Gray background for visual separation -->
  <h2>Section Title</h2>
  <p>Content on subtle gray background</p>
</section>

<!-- Success notification banner -->
<div class="slds-theme_success slds-p-around_small">
  <!-- Green background with white text -->
  <span class="slds-icon_container">
    <svg class="slds-icon slds-icon_small">...</svg>
  </span>
  <span>Operation completed successfully</span>
</div>

<!-- Warning alert with texture -->
<div class="slds-theme_warning slds-theme_alert-texture slds-p-around_medium">
  <!-- Yellow background with striped texture -->
  <strong>Warning:</strong> This action cannot be undone
</div>

<!-- Inverse header section -->
<header class="slds-theme_inverse slds-p-around_large">
  <!-- Dark blue background with white text -->
  <h1>Dashboard</h1>
  <p>All text and links are automatically styled for dark backgrounds</p>
</header>
```

## Best Practices

✅ Use `slds-theme_default` for standard white backgrounds
✅ Apply `slds-theme_shade` to visually separate sections
✅ Use semantic themes (success, error, warning) for status messages
✅ Combine `slds-theme_alert-texture` with semantic themes for critical alerts
✅ Apply themes to container elements, not individual text elements
✅ Use `slds-theme_inverse` for headers and navigation areas

❌ Nest multiple theme classes on the same element
❌ Override theme colors with inline styles
❌ Use semantic themes for decorative purposes
❌ Apply themes to elements smaller than 44×44px touch targets

## Deprecation Notes

The following double-dash variants are deprecated but still supported:
- `slds-theme--default` → Use `slds-theme_default`
- `slds-theme--shade` → Use `slds-theme_shade`
- `slds-theme--inverse` → Use `slds-theme_inverse`
- `slds-theme--alt-inverse` → Use `slds-theme_alt-inverse`
- `slds-theme--success` → Use `slds-theme_success`
- `slds-theme--info` → Use `slds-theme_info`
- `slds-theme--warning` → Use `slds-theme_warning`
- `slds-theme--error` → Use `slds-theme_error`
- `slds-theme--offline` → Use `slds-theme_offline`
- `slds-theme--alert-texture` → Use `slds-theme_alert-texture`
- `slds-theme--inverse-text` → Use `slds-theme_inverse-text`