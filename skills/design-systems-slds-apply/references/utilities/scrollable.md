---
id: slds.guidance.utilities.scrollable
title: Scrollable Utilities
description: SLDS scrollable utility classes for managing overflow behavior
summary: "Utilities for controlling scroll behavior (x, y, both, none)."

artifact_type: reference
domain: utilities
topic: scrollable

content_format: structured
complexity: intermediate
audience: [implementer]

tasks: [implement]

refs:
  - slds.guidance.utilities
  - slds.guidance.overview.utilities

tags: [utilities, scrollable, overflow, scroll]
keywords: [slds-scrollable, overflow, scroll, scrollable-x, scrollable-y]
---

# Scrollable - Overflow Management

Controlling scroll behavior in fixed-size containers.

## Core Classes

| Class | Purpose |
|-------|---------|
| `slds-scrollable` | Enables scrolling on both axes when content exceeds container dimensions |
| `slds-scrollable_x` | Enables horizontal scrolling only when content exceeds width |
| `slds-scrollable_y` | Enables vertical scrolling only when content exceeds height |
| `slds-scrollable_none` | Prevents scrolling and hides overflow content |

## Common Patterns

```html
<!-- Data table with horizontal scroll -->
<div class="slds-scrollable_x" style="max-width: 600px;">
  <!-- Table scrolls horizontally when wider than 600px -->
  <table class="slds-table slds-table_bordered">
    <thead>
      <tr>
        <th>Column 1</th>
        <th>Column 2</th>
        <th>Column 3</th>
        <th>Column 4</th>
        <th>Column 5</th>
        <th>Column 6</th>
      </tr>
    </thead>
    <tbody>
      <!-- Table rows -->
    </tbody>
  </table>
</div>

<!-- List with vertical scroll -->
<div class="slds-scrollable_y" style="height: 300px;">
  <!-- List scrolls vertically when taller than 300px -->
  <ul class="slds-has-dividers_bottom">
    <li class="slds-p-around_small">Item 1</li>
    <li class="slds-p-around_small">Item 2</li>
    <li class="slds-p-around_small">Item 3</li>
    <li class="slds-p-around_small">Item 4</li>
    <li class="slds-p-around_small">Item 5</li>
    <li class="slds-p-around_small">Item 6</li>
    <li class="slds-p-around_small">Item 7</li>
    <li class="slds-p-around_small">Item 8</li>
  </ul>
</div>

<!-- Modal with scrollable content -->
<div class="slds-modal__container">
  <div class="slds-modal__header">
    <h2>Modal Title</h2>
  </div>
  <div class="slds-modal__content slds-scrollable_y" style="height: 400px;">
    <!-- Content scrolls when exceeding 400px height -->
    <div class="slds-p-around_medium">
      Long form content that exceeds the modal height...
    </div>
  </div>
  <div class="slds-modal__footer">
    <button class="slds-button">Cancel</button>
    <button class="slds-button slds-button_brand">Save</button>
  </div>
</div>

<!-- Code block with both-axis scrolling -->
<div class="slds-scrollable slds-box" style="max-width: 500px; max-height: 200px;">
  <!-- Code scrolls both horizontally and vertically -->
  <pre class="slds-p-around_small">
    Long code snippet that exceeds both width and height...
    Multiple lines of code...
    With very long lines that exceed the container width...
  </pre>
</div>

<!-- Card with hidden overflow -->
<div class="slds-card">
  <div class="slds-card__body slds-scrollable_none" style="height: 150px;">
    <!-- Overflow content is hidden, not scrollable -->
    <div class="slds-p-around_medium">
      Content that might exceed the fixed height is clipped
    </div>
  </div>
</div>
```

## Best Practices

✅ Use `slds-scrollable_x` for wide tables in responsive layouts
✅ Use `slds-scrollable_y` for long lists with fixed height containers
✅ Use `slds-scrollable` for code blocks or content that may overflow in both directions
✅ Set explicit height on containers using `slds-scrollable_y`
✅ Set explicit width on containers using `slds-scrollable_x`
✅ Include touch scrolling support for mobile devices (automatically included)

❌ Avoid nesting multiple scrollable containers
❌ Avoid using `slds-scrollable_none` on content users need to access
❌ Avoid scrollable areas without visual scroll indicators
❌ Avoid horizontal scrolling on mobile when vertical layout works better