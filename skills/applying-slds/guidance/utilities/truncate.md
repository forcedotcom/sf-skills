---
id: slds.guidance.utilities.truncate
title: Truncate Utilities
description: SLDS text truncation utility classes
summary: "Utilities for text truncation. Single-line truncation with ellipsis and container-based percentage truncation."

artifact_type: reference
domain: utilities
topic: truncate

content_format: structured
complexity: intermediate
audience: [implementer]

tasks: [implement]

refs:
  - slds.guidance.utilities
  - slds.guidance.overview.utilities
  - slds.guidance.utilities.line-clamp

tags: [utilities, truncate, text-overflow, ellipsis]
keywords: [slds-truncate, text overflow, ellipsis, truncation]
---

# Truncate - Text Overflow

Text truncation with ellipsis.

## Core Classes

| Class | Purpose |
|-------|---------|
| `slds-truncate` | Truncates text at 100% container width with ellipsis |
| `slds-truncate_container_25` | Truncates text at 25% of parent width |
| `slds-truncate_container_33` | Truncates text at 33% of parent width |
| `slds-truncate_container_50` | Truncates text at 50% of parent width |
| `slds-truncate_container_66` | Truncates text at 66% of parent width |
| `slds-truncate_container_75` | Truncates text at 75% of parent width |
| `slds-has-flexi-truncate` | Applied to flex container to enable truncation in nested flexbox layouts |

## Common Patterns

### Table Cell Truncation
```html
<!-- Truncate long text in table cells -->
<table class="slds-table slds-table_cell-buffer">
  <tbody>
    <tr>
      <td class="slds-truncate" title="Complete text for accessibility">
        <!-- Long customer name truncates with ellipsis -->
        Very Long Customer Name That Will Be Truncated
      </td>
    </tr>
  </tbody>
</table>
```

### List Item with Truncation
```html
<!-- Email recipient list with truncation -->
<ul class="slds-list_horizontal">
  <li class="slds-list__item">
    <span>To:</span>
    <span class="slds-truncate slds-m-left_xx-small" title="john.doe@example.com">
      <!-- Email truncates to fit available space -->
      john.doe@example.com
    </span>
  </li>
</ul>
```

### Card Header Truncation
```html
<!-- Card with truncated title -->
<article class="slds-card">
  <div class="slds-card__header">
    <h2 class="slds-truncate" title="Full opportunity name">
      <!-- Title truncates if too long -->
      Very Long Opportunity Name - Q4 2024 Enterprise Deal
    </h2>
  </div>
</article>
```

### Partial Width Truncation
```html
<!-- Truncate at specific percentage of parent -->
<div class="slds-grid">
  <div class="slds-truncate_container_50">
    <!-- Truncates at 50% of parent container -->
    This text will truncate at half the parent width
  </div>
  <div class="slds-col">
    <!-- Remaining content -->
  </div>
</div>
```

### Flexbox with Truncation
```html
<!-- Use with flexbox layouts -->
<div class="slds-grid">
  <div class="slds-col slds-has-flexi-truncate">
    <span class="slds-truncate" title="Full file name">
      <!-- Truncates within flexible column -->
      very-long-filename-with-many-words.pdf
    </span>
  </div>
  <div class="slds-col_fixed">
    <button class="slds-button">Download</button>
  </div>
</div>
```

## Best Practices

✅ Always include `title` attribute with full text for accessibility
✅ Use `slds-has-flexi-truncate` on flex container when truncating within flexbox
✅ Apply truncation to inline or block elements containing text
✅ Use container percentage classes for predictable truncation points
✅ Test truncation behavior across different viewport sizes

❌ Never truncate text without providing full text in title attribute
❌ Avoid truncating critical information like error messages
❌ Never use truncation on interactive elements without proper tooltips
❌ Avoid nested truncation classes