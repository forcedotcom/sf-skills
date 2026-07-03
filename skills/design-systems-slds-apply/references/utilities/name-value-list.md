---
id: slds.guidance.utilities.name-value-list
title: Name-Value List Utilities
description: SLDS name-value list utility classes for structured data display
summary: "Utilities for structured data lists (labels and details). Creates horizontal, vertical, and inline label-value pair layouts."

artifact_type: reference
domain: utilities
topic: name-value-list

content_format: structured
complexity: intermediate
audience: [implementer]

tasks: [implement]

refs:
  - slds.guidance.utilities
  - slds.guidance.overview.utilities
  - slds.guidance.hooks.spacing

tags: [utilities, name-value-list, data-display, lists]
keywords: [slds-list_horizontal, slds-list_vertical, slds-list_inline, slds-item_label, slds-item_detail]
---

# Name-Value List - Structured Data Display

Creating label-value pair layouts in horizontal, vertical, and inline configurations.

## Core Classes

| Class | Purpose |
|-------|---------|
| `slds-list_horizontal` | Layout container for horizontal name-value pairs with 30/70 split |
| `slds-list_vertical` | Layout container for vertical (stacked) name-value pairs |
| `slds-list_inline` | Inline flex container for compact name-value pairs |
| `slds-item_label` | Label element with 30% width and right padding (12px) |
| `slds-item_detail` | Detail/value element with 70% width |

## Layout Variants

### Horizontal Layout (30/70 Split)
| Variant | Label Width | Detail Width | Spacing |
|---------|-------------|--------------|---------|
| `slds-list_horizontal` | 30% | 70% | 12px gap |

### Vertical Layout
| Variant | Display | Spacing |
|---------|---------|---------|
| `slds-list_vertical` | Block stacked | Default line height |

### Inline Layout
| Variant | Display | Max Width |
|---------|---------|-----------|
| `slds-list_inline` | `inline-flex` | 100% |

## Common Patterns

### Horizontal Name-Value List
```html
<!-- Standard 30/70 horizontal layout -->
<dl class="slds-list_horizontal">
  <dt class="slds-item_label">Account Name</dt>
  <dd class="slds-item_detail">Acme Corporation</dd>

  <dt class="slds-item_label">Account Type</dt>
  <dd class="slds-item_detail">Enterprise Customer</dd>

  <dt class="slds-item_label">Industry</dt>
  <dd class="slds-item_detail">Technology</dd>
</dl>
```

### Vertical Stacked List
```html
<!-- Vertical stacked layout for long content -->
<dl class="slds-list_vertical">
  <dt class="slds-item_label">Description</dt>
  <dd class="slds-item_detail">
    This is a detailed description that spans multiple lines
    and works better in a vertical layout.
  </dd>

  <dt class="slds-item_label">Notes</dt>
  <dd class="slds-item_detail">
    Additional notes and comments that may be lengthy.
  </dd>
</dl>
```

### Inline Compact List
```html
<!-- Inline layout for compact display -->
<dl class="slds-list_inline">
  <dt class="slds-item_label">Status:</dt>
  <dd class="slds-item_detail">Active</dd>

  <dt class="slds-item_label">Priority:</dt>
  <dd class="slds-item_detail">High</dd>
</dl>
```

### Mixed Layout in Card
```html
<!-- Name-value list within a card component -->
<article class="slds-card">
  <div class="slds-card__header">
    <h2>Contact Details</h2>
  </div>
  <div class="slds-card__body">
    <dl class="slds-list_horizontal">
      <dt class="slds-item_label">Name</dt>
      <dd class="slds-item_detail">John Smith</dd>

      <dt class="slds-item_label">Email</dt>
      <dd class="slds-item_detail">john.smith@example.com</dd>

      <dt class="slds-item_label">Phone</dt>
      <dd class="slds-item_detail">(555) 123-4567</dd>
    </dl>
  </div>
</article>
```

## Best Practices

✅ Use `slds-list_horizontal` for compact record details with short values
✅ Use `slds-list_vertical` for long text content or descriptions
✅ Use `slds-list_inline` for status indicators and brief metadata
✅ Use semantic `<dl>`, `<dt>`, `<dd>` elements for accessibility
✅ Apply `slds-item_label` to `<dt>` and `slds-item_detail` to `<dd>`
✅ Maintain the 30/70 ratio for horizontal layouts to ensure consistency

❌ Avoid using name-value lists for form inputs (use form layouts instead)
❌ Avoid mixing layout types within the same list
❌ Never omit `slds-item_label` or `slds-item_detail` classes
❌ Avoid horizontal layout for values longer than 2-3 lines

## Spacing Details

The name-value list utilities use these specific spacing tokens:
- **Horizontal gap**: `var(--slds-g-spacing-3)` (12px)
- **Inline spacing**: `var(--slds-g-spacing-3)` to `var(--slds-g-spacing-4)` (12-16px)
- **Label padding**: `padding-inline-end: var(--slds-g-spacing-3)` (12px right padding)

## Accessibility Notes

- Use `<dl>` (description list) as the container
- Use `<dt>` (description term) for labels with `slds-item_label`
- Use `<dd>` (description details) for values with `slds-item_detail`
- Screen readers announce the semantic relationship between labels and values
- Maintain logical reading order in the HTML structure