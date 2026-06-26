---
id: slds.guidance.utilities.typography
title: Typography Utilities
description: SLDS text styling and typography utility classes
summary: "Utilities for text styling. Headings, body text, alignment, colors, and special formatting. Link utilities are documented in [Interactions](ref:slds.guidance.utilities.interactions)."

artifact_type: reference
domain: utilities
topic: typography

content_format: structured
complexity: intermediate
audience: [implementer]

tasks: [implement]

refs:
  - slds.guidance.utilities
  - slds.guidance.overview.utilities
  - slds.guidance.utilities.interactions
  - slds.guidance.hooks.typography

tags: [utilities, typography, text, headings, alignment]
keywords: [slds-text-heading, slds-text-body, slds-text-color, slds-text-align]
---

# Typography - Text Styling

Text styling, headings, alignment, and colors.

## Core Classes

### Heading Sizes

| Class | Purpose |
|-------|---------|
| `slds-text-heading_large` | Large heading (28px, line-height 1.25) |
| `slds-text-heading_medium` | Medium heading (20px, line-height 1.25) |
| `slds-text-heading_small` | Small heading (16px, line-height 1.25) |

### Title Styles

| Class | Purpose |
|-------|---------|
| `slds-text-title` | Standard title (12px, line-height 1.25) |
| `slds-text-title_caps` | Uppercase title (12px, weight 400, letter-spacing 0.0625rem) |
| `slds-text-title_bold` | Bold title (12px, weight 700) |

### Body Text

| Class | Purpose |
|-------|---------|
| `slds-text-body_regular` | Regular body text (13px) |
| `slds-text-body_small` | Small body text (12px) |

### Text Alignment

| Class | Purpose |
|-------|---------|
| `slds-text-align_left` | Aligns text to start |
| `slds-text-align_center` | Centers text |
| `slds-text-align_right` | Aligns text to end |

### Text Colors

| Class | Purpose |
|-------|---------|
| `slds-text-color_default` | Default text color |
| `slds-text-color_weak` | De-emphasized text color |
| `slds-text-color_error` | Error state text (red) |
| `slds-text-color_destructive` | Destructive action text (red) |
| `slds-text-color_success` | Success state text (green) |
| `slds-text-color_inverse` | Light text on dark background |
| `slds-text-color_inverse-weak` | De-emphasized inverse text |

### Special Formatting

| Class | Purpose |
|-------|---------|
| `slds-text-longform` | Applies default spacing to content blocks |
| `slds-text-font_monospace` | Applies monospace font family |
| `slds-line-height_reset` | Resets line-height to 1 |

## Common Patterns

### Page Header
```html
<!-- Main page title with subtitle -->
<div class="slds-page-header">
  <h1 class="slds-text-heading_large">
    <!-- 28px heading -->
    Account Details
  </h1>
  <p class="slds-text-body_regular slds-text-color_weak">
    <!-- 13px de-emphasized text -->
    View and manage account information
  </p>
</div>
```

### Section Headers
```html
<!-- Section with title caps -->
<section class="slds-m-top_large">
  <h2 class="slds-text-title_caps slds-m-bottom_small">
    <!-- 12px uppercase title -->
    CONTACT INFORMATION
  </h2>
  <div class="slds-text-body_regular">
    <!-- Content -->
  </div>
</section>
```

### Status Messages
```html
<!-- Success message -->
<div class="slds-text-color_success slds-text-align_center">
  <!-- Green centered text -->
  Record saved successfully
</div>

<!-- Error message -->
<div class="slds-text-color_error slds-m-top_small">
  <!-- Red error text -->
  Required field missing
</div>
```

### Long-Form Content
```html
<!-- Article with automatic spacing -->
<article class="slds-text-longform">
  <!-- Automatic margins for h1, h2, h3, p, ul, ol -->
  <h1>Article Title</h1>
  <p>First paragraph with automatic bottom margin.</p>
  <ul>
    <!-- Disc bullets with proper indentation -->
    <li>First item</li>
    <li>Second item</li>
  </ul>
</article>
```

### Code Display
```html
<!-- Monospace text for code -->
<code class="slds-text-font_monospace slds-text-body_small">
  <!-- 12px monospace font -->
  SELECT Id, Name FROM Account
</code>
```

## Best Practices

✅ Use semantic HTML elements (h1-h6) with text utility classes
✅ Apply `slds-text-heading_*` classes to maintain consistent sizing
✅ Use `slds-text-color_weak` for secondary information
✅ Apply `slds-text-title_caps` for section labels and tabs
✅ Use `slds-text-longform` for user-generated content areas
✅ Combine text utilities with spacing utilities for proper layout

❌ Avoid using heading classes on non-heading elements for sizing
❌ Never use color utilities as the only indicator of state
❌ Avoid mixing multiple text size classes on the same element
❌ Never override line-height unless using `slds-line-height_reset`