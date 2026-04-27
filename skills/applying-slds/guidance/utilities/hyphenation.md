---
id: slds.guidance.utilities.hyphenation
title: Hyphenation Utilities
description: SLDS hyphenation utility class
summary: "Utility for text wrapping and hyphenation. Enables automatic word breaking in narrow containers."

artifact_type: reference
domain: utilities
topic: hyphenation

content_format: structured
complexity: intermediate
audience: [implementer]

tasks: [implement]

refs:
  - slds.guidance.utilities
  - slds.guidance.overview.utilities
  - slds.guidance.utilities.truncate

tags: [utilities, hyphenation, text-wrapping, word-break]
keywords: [slds-hyphenate, hyphenation, word-wrap, overflow-wrap]
---

# Hyphenation - Text Wrapping

Enabling automatic text hyphenation and word breaking in narrow width containers.

## Core Classes

| Class | Purpose |
|-------|---------|
| `slds-hyphenate` | Enables text hyphenation with word-wrapping fallbacks for narrow containers |

## Common Patterns

```html
<!-- Long text in narrow column -->
<div class="slds-size_1-of-3">
  <p class="slds-hyphenate">
    Supercalifragilisticexpialidocious text that needs to break appropriately.
  </p>
</div>

<!-- Table cell with potential long words -->
<td class="slds-cell-wrap">
  <span class="slds-hyphenate">
    VeryLongProductNameWithoutSpaces
  </span>
</td>

<!-- Card header with constrained width -->
<div class="slds-card__header">
  <h2 class="slds-text-heading_small slds-hyphenate">
    ExtremelyLongTitleThatMightOverflow
  </h2>
</div>

<!-- Form label in narrow sidebar -->
<div class="slds-form-element">
  <label class="slds-form-element__label slds-hyphenate">
    InternationalizationConfiguration
  </label>
</div>

<!-- Modal title with potential overflow -->
<div class="slds-modal__header">
  <h2 class="slds-text-heading_medium slds-hyphenate">
    SuperLongModalTitleForConfiguration
  </h2>
</div>
```

## Best Practices

✅ Use on text that might contain long words without spaces
✅ Apply to elements in narrow width containers
✅ Use with non-truncated text that needs to remain visible
✅ Combine with responsive grid columns where text might overflow

❌ Don't use with [Truncate Utilities](ref:slds.guidance.utilities.truncate) (choose one strategy)
❌ Don't apply to elements with fixed widths larger than their containers
❌ Don't use on numeric data or codes that shouldn't break