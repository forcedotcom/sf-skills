---
id: slds.guidance.utilities.interactions
title: Interactions Utilities
description: SLDS link reset, faux link, and focus state utility classes
summary: "Utilities for link resets, faux links, and focus states. Enables custom link styling and accessible focus indicators."

artifact_type: reference
domain: utilities
topic: interactions

content_format: structured
complexity: intermediate
audience: [implementer]

tasks: [implement]

refs:
  - slds.guidance.utilities
  - slds.guidance.overview.utilities
  - slds.guidance.utilities.typography

tags: [utilities, interactions, links, focus, accessibility]
keywords: [slds-text-link, slds-has-blur-focus, slds-text-link_reset, slds-text-link_faux]
---

# Interactions - Links & Focus States

Managing link appearance, creating faux links, and implementing accessible focus states.

## Core Classes

| Class | Purpose |
|-------|---------|
| `slds-text-link_reset` | Makes links and buttons appear as regular text |
| `slds-text-link` | Restores link styling inside `slds-text-link_reset` |
| `slds-text-link_faux` | Creates underline-on-hover for non-anchor elements |
| `slds-type-focus` | Legacy alias for slds-text-link_faux |
| `slds-has-blur-focus` | Adds accessible blurred outline on focus |
| `slds-has-input-focus` | JavaScript-applied focus state for input containers |

## Common Patterns

```html
<!-- Reset link to look like plain text -->
<a href="/path" class="slds-text-link_reset">
  This link looks like regular text
</a>

<!-- Reset with partial link styling restored -->
<a href="/article" class="slds-text-link_reset">
  This article discusses important topics
  <span class="slds-text-link">Read more</span>
</a>

<!-- Faux link on heading + button combo -->
<div class="slds-page-header__name">
  <h1 class="slds-page-header__title slds-text-link_faux">
    Account Name
  </h1>
  <button class="slds-button slds-button_icon slds-text-link_faux">
    <svg class="slds-button__icon">...</svg>
  </button>
</div>

<!-- Accessible blur focus on custom button -->
<button class="slds-button slds-has-blur-focus">
  Custom Action
</button>

<!-- Input container with JavaScript focus state -->
<div class="slds-form-element__control" id="input-container">
  <input class="slds-input"
         onfocus="document.getElementById('input-container').classList.add('slds-has-input-focus')"
         onblur="document.getElementById('input-container').classList.remove('slds-has-input-focus')" />
</div>
```

## Best Practices

✅ Use `slds-text-link_reset` to remove default link styling
✅ Use `slds-text-link_faux` for non-anchor elements that need link behavior
✅ Use `slds-has-blur-focus` for keyboard navigation accessibility
✅ Apply `slds-has-input-focus` via JavaScript when input receives focus
✅ Combine `slds-text-link_reset` with `slds-text-link` for partial link styling

❌ Don't use `slds-text-link_faux` on actual anchor elements
❌ Don't forget to handle both focus and blur events for `slds-has-input-focus`
❌ Don't remove focus indicators without providing alternatives
❌ Don't apply multiple interaction utilities to the same element