---
id: slds.guidance.utilities.vertical-list
title: Vertical-list Utilities
description: SLDS vertical list utility classes for list formatting and spacing
summary: "Utilities for vertical lists including dividers, cards, spacing, link blocks, and list styles (dotted, ordered)."

artifact_type: reference
domain: utilities
topic: vertical-list

content_format: structured
complexity: intermediate
audience: [implementer]

tasks: [implement]

refs:
  - slds.guidance.utilities
  - slds.guidance.overview.utilities

tags: [utilities, lists, vertical-list, dividers]
keywords: [slds-list, slds-has-dividers, vertical spacing, list formatting]
---

# Vertical List - Formatting & Spacing

Creating and styling vertical lists with consistent spacing, dividers, and interactive states.

## Core Classes

| Class | Purpose |
|-------|---------|
| `slds-list_vertical` | Base vertical list container |
| `slds-list__item` | Individual list item |
| `slds-item` | Generic item (alternative to `slds-list__item`) |
| `slds-is-selected` | Marks selected state with accent border |
| `slds-is-nested` | Indents nested lists by 16px |

## List Styles

| Class | Purpose |
|-------|---------|
| `slds-list_dotted` | Unordered list with disc bullets |
| `slds-list_ordered` | Ordered list with decimal numbers |

## Spacing Variants

| Class | Spacing Between Items |
|-------|----------------------|
| `slds-list_vertical-space` | 8px (`x-small`) |
| `slds-list_vertical-space-medium` | 16px (`medium`) |

## Divider Classes

### Line Dividers
| Class | Purpose |
|-------|---------|
| `slds-has-dividers` | Bottom border on items with hover states |
| `slds-has-dividers_top` | Top border on each item |
| `slds-has-dividers_bottom` | Bottom border on each item |
| `slds-has-dividers_top-space` | Top border with 8px padding |
| `slds-has-dividers_bottom-space` | Bottom border with 8px padding |

### Card Dividers
| Class | Purpose |
|-------|---------|
| `slds-has-cards` | Bordered cards with rounded corners |
| `slds-has-cards_space` | Bordered cards with 12px padding |
| `slds-has-dividers_around` | Full border around each item |
| `slds-has-dividers_around-space` | Full border with 12px padding |

### Single Dividers
| Class | Purpose |
|-------|---------|
| `slds-has-divider` | Single top divider (8px margin + padding) |
| `slds-has-divider_top` | Top border only |
| `slds-has-divider_bottom` | Bottom border only |
| `slds-has-divider_top-space` | Top border with padding |
| `slds-has-divider_bottom-space` | Bottom border with padding |
| `slds-has-divider_right` | Right border only |
| `slds-has-divider_left` | Left border only |

## Link Blocks

| Class | Purpose |
|-------|---------|
| `slds-has-block-links` | Makes links display block |
| `slds-has-block-links_space` | Block links with 12px padding |
| `slds-has-inline-block-links` | Makes links display inline-block |
| `slds-has-inline-block-links_space` | Inline-block links with 12px padding |

## Interactive States

| Class | Purpose |
|-------|---------|
| `slds-has-list-interactions` | Enables hover and active states |

## Common Patterns

```html
<!-- Basic vertical list with dividers -->
<ul class="slds-list_vertical slds-has-dividers">
  <li class="slds-list__item">Item 1</li>
  <li class="slds-list__item">Item 2</li>
  <li class="slds-list__item slds-is-selected">Selected Item</li>
</ul>

<!-- Card-style list with spacing -->
<ul class="slds-has-cards_space">
  <li class="slds-list__item">
    <!-- Each item appears as a card with padding -->
    <h3>Card Title</h3>
    <p>Card content with 12px padding</p>
  </li>
  <li class="slds-list__item">
    <h3>Another Card</h3>
    <p>Automatically spaced 8px apart</p>
  </li>
</ul>

<!-- List with block links -->
<ul class="slds-has-block-links_space">
  <li class="slds-list__item">
    <a href="/page1">
      <!-- Entire area is clickable with padding -->
      <h3>Link Title</h3>
      <p>Description text</p>
    </a>
  </li>
  <li class="slds-list__item">
    <a href="/page2">Another clickable item</a>
  </li>
</ul>

<!-- Nested list with bullets -->
<ul class="slds-list_dotted">
  <li>Parent item</li>
  <li>
    Another parent
    <ul class="slds-list_dotted slds-is-nested">
      <li>Nested child 1</li>
      <li>Nested child 2</li>
    </ul>
  </li>
</ul>

<!-- Interactive list with hover states -->
<ul class="slds-list_vertical slds-has-dividers slds-has-list-interactions">
  <li class="slds-list__item">Hover for gray background</li>
  <li class="slds-list__item">Click for active state</li>
</ul>
```

## Best Practices

✅ Use `slds-list_vertical` with `slds-has-dividers` for navigation menus
✅ Apply `slds-has-cards_space` for distinct content sections
✅ Use `slds-has-block-links_space` for clickable list items
✅ Add `slds-is-selected` to indicate current selection
✅ Combine `slds-list_dotted` or `slds-list_ordered` for structured content
✅ Use `slds-is-nested` for hierarchical lists

❌ Mix card styles with line dividers on the same list
❌ Apply multiple divider types to the same element
❌ Use `slds-list__item` and `slds-item` interchangeably in the same list
❌ Nest lists more than 3 levels deep