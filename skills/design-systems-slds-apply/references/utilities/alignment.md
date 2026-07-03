---
id: slds.guidance.utilities.alignment
title: Alignment Utilities
description: SLDS alignment utility classes for centering content
summary: "Utility for absolute centering. Uses flexbox to center content both horizontally and vertically within containers."

artifact_type: reference
domain: utilities
topic: alignment

content_format: structured
complexity: intermediate
audience: [implementer]

tasks: [implement]

refs:
  - slds.guidance.utilities
  - slds.guidance.overview.utilities

tags: [utilities, alignment, centering, flexbox]
keywords: [slds-align, absolute-center, center-content, flexbox-center]
---

# Alignment - Content Centering

Utility for absolute centering of content within containers.

## Core Classes

| Class | Purpose |
|-------|---------|
| `slds-align_absolute-center` | Centers children both horizontally and vertically using flexbox |

## Common Patterns

### Center Content in Container
```html
<!-- Center a single element -->
<div class="slds-align_absolute-center" style="height: 200px;">
  <div class="slds-box">
    Centered Content
  </div>
</div>
```

### Center Modal Dialog
```html
<!-- Center a modal in viewport -->
<div class="slds-backdrop slds-backdrop_open">
  <div class="slds-align_absolute-center" style="height: 100vh;">
    <section class="slds-modal slds-fade-in-open">
      <div class="slds-modal__container">
        <!-- Modal content -->
      </div>
    </section>
  </div>
</div>
```

### Center Loading Spinner
```html
<!-- Center spinner in card -->
<article class="slds-card">
  <div class="slds-align_absolute-center" style="height: 300px;">
    <div class="slds-spinner slds-spinner_medium">
      <span class="slds-assistive-text">Loading</span>
      <div class="slds-spinner__dot-a"></div>
      <div class="slds-spinner__dot-b"></div>
    </div>
  </div>
</article>
```

### Center Empty State Message
```html
<!-- Center illustration and message -->
<div class="slds-align_absolute-center" style="min-height: 400px;">
  <div class="slds-illustration slds-illustration_small">
    <img src="/assets/images/illustrations/empty-state.svg" alt="" />
    <h3 class="slds-text-heading_medium">No items to display</h3>
    <p class="slds-text-body_regular">Get started by creating your first item</p>
  </div>
</div>
```

### Center Icon in Fixed Container
```html
<!-- Center icon in square container -->
<div class="slds-align_absolute-center" style="width: 100px; height: 100px; background: #f3f3f3;">
  <span class="slds-icon_container slds-icon-utility-check">
    <svg class="slds-icon slds-icon_small">
      <use xlink:href="/assets/icons/utility-sprite/svg/symbols.svg#check"></use>
    </svg>
  </span>
</div>
```

## Best Practices

✅ Use `slds-align_absolute-center` when content needs to be centered both horizontally and vertically
✅ Set explicit height on the container for vertical centering to work properly
✅ Combine with other layout utilities like `slds-box` or `slds-card` for complete designs
✅ Use for centering single elements or grouped content within defined containers

❌ Avoid using on elements without defined height - vertical centering requires container height
❌ Do not use for text alignment - use `slds-text-align_center` for inline text centering
❌ Avoid nesting multiple `slds-align_absolute-center` classes unnecessarily

## Technical Details

The `slds-align_absolute-center` class applies these CSS properties:
- `display: flex` - Creates a flex container
- `justify-content: center` - Centers content horizontally
- `align-content: center` - Centers flex lines
- `align-items: center` - Centers content vertically
- `margin: auto` - Ensures proper centering within parent

This utility leverages flexbox for reliable cross-browser centering without requiring absolute positioning or transform calculations.