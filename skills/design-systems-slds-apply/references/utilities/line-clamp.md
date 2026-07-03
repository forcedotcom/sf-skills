---
id: slds.guidance.utilities.line-clamp
title: Line-clamp Utilities
description: SLDS line-clamp utility classes for multi-line text truncation
summary: "Utilities for multi-line text truncation (2-7 lines). Provides controlled text overflow with ellipsis for readable content length management."

artifact_type: reference
domain: utilities
topic: line-clamp

content_format: structured
complexity: intermediate
audience: [implementer]

tasks: [implement]

refs:
  - slds.guidance.utilities
  - slds.guidance.overview.utilities
  - slds.guidance.utilities.truncate

tags: [utilities, line-clamp, truncation, text]
keywords: [slds-line-clamp, text-truncation, ellipsis, multi-line]
---

# Line Clamp - Multi-line Text Truncation

Controlled multi-line text truncation with ellipsis.

## Line Limit Scale

| Class | Lines | Use Case |
|-------|-------|----------|
| `slds-line-clamp` | 3 lines | Default truncation for card descriptions |
| `slds-line-clamp_x-small` | 2 lines | Compact list items and previews |
| `slds-line-clamp_small` | 3 lines | Standard card and tile descriptions |
| `slds-line-clamp_medium` | 5 lines | Extended previews and summaries |
| `slds-line-clamp_large` | 7 lines | Long-form content with controlled height |

## Common Patterns

### Card Description Truncation
```html
<!-- Standard 3-line truncation for card descriptions -->
<div class="slds-card">
  <div class="slds-card__body">
    <p class="slds-line-clamp">
      This is a long description that will be truncated after three lines
      of text. Any content beyond the third line will be hidden with an
      ellipsis to indicate more content is available.
    </p>
  </div>
</div>
```

### Compact List Item Preview
```html
<!-- 2-line truncation for list items -->
<ul class="slds-has-dividers_bottom">
  <li class="slds-item">
    <div class="slds-line-clamp_x-small">
      Item description that displays only two lines before truncating
      with ellipsis for space-efficient list layouts.
    </div>
  </li>
</ul>
```

### Extended Article Summary
```html
<!-- 5-line truncation for article previews -->
<article class="slds-box">
  <h3 class="slds-text-heading_small">Article Title</h3>
  <div class="slds-line-clamp_medium">
    This article summary can display up to five lines of content before
    truncation occurs. This provides enough context for readers to understand
    the main points while maintaining consistent layout height across
    multiple article cards in a grid or list view.
  </div>
</article>
```

### Long-form Content Preview
```html
<!-- 7-line truncation for detailed previews -->
<div class="slds-panel">
  <div class="slds-panel__body">
    <div class="slds-line-clamp_large">
      Extended content preview that allows up to seven lines of text
      to be displayed. This is useful for detailed descriptions,
      documentation excerpts, or any scenario where more context is
      beneficial while still maintaining a maximum height constraint
      for consistent layouts across different content lengths.
    </div>
  </div>
</div>
```

### Responsive Text Truncation
```html
<!-- Different truncation levels for different contexts -->
<div class="slds-grid slds-wrap">
  <div class="slds-col slds-size_1-of-2">
    <h4>Product Name</h4>
    <p class="slds-line-clamp_x-small">
      Brief product description limited to two lines
    </p>
  </div>
  <div class="slds-col slds-size_1-of-2">
    <h4>Product Details</h4>
    <p class="slds-line-clamp_medium">
      More detailed product information that can extend
      up to five lines before being truncated
    </p>
  </div>
</div>
```

## Best Practices

✅ Apply line-clamp classes directly to text elements (`<p>`, `<div>`, `<span>`)
✅ Use `slds-line-clamp_x-small` (2 lines) for compact layouts and list items
✅ Use `slds-line-clamp` or `slds-line-clamp_small` (3 lines) for standard card descriptions
✅ Use `slds-line-clamp_medium` (5 lines) for extended previews
✅ Test truncation with actual content to ensure readability
✅ Provide "Show More" functionality when truncated content needs full access

❌ Do not apply to container elements with HTML children
❌ Never use on elements containing interactive components
❌ Do not rely on line-clamp for IE11 support (uses -webkit-line-clamp)
❌ Avoid using with single-line truncation (use [Truncate Utilities](ref:slds.guidance.utilities.truncate) instead)