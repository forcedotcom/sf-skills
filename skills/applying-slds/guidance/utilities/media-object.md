---
id: slds.guidance.utilities.media-object
title: Media Object Utilities
description: SLDS media object utility classes for image and text layouts
summary: "Utilities for image+text layouts. Provides flexible pairing of media elements (icons/images) with text content. Includes size variants (small/large), positioning (left/right/center), and responsive stacking."

artifact_type: reference
domain: utilities
topic: media-object

content_format: structured
complexity: intermediate
audience: [implementer]

tasks: [implement]

refs:
  - slds.guidance.utilities
  - slds.guidance.overview.utilities
  - slds.guidance.hooks.spacing

tags: [utilities, media-object, layout, flexbox]
keywords: [slds-media, media object, figure, image layout]
---

# Media Object - Image & Text Layouts

Flexible image and text pairing layouts using flexbox.

## Core Classes

| Class | Purpose |
|-------|---------|
| `slds-media` | Creates flex container for media object layout |
| `slds-media__figure` | Container for media element (image/icon/avatar) |
| `slds-media__body` | Container for text content next to figure |
| `slds-media__figure_reverse` | Positions figure on the right side instead of left |

## Size Variants

| Class | Purpose | Spacing |
|-------|---------|---------|
| `slds-media_small` | Reduces spacing between figure and body | 8px (`--slds-g-spacing-2`) |
| Default spacing | Standard spacing between figure and body | 12px (`--slds-g-spacing-3`) |
| `slds-media_large` | Increases spacing between figure and body | 20px (`--slds-g-spacing-5`) |

## Layout Modifiers

| Class | Purpose |
|-------|---------|
| `slds-media_center` | Vertically centers figure and body content |
| `slds-media_inline` | Makes body flow inline instead of taking full width |
| `slds-media_responsive` | Stacks figure above body on smaller screens |
| `slds-media__figure_fixed-width` | Sets fixed width on figure container (40px) |

## Common Patterns

```html
<!-- Basic media object with avatar and text -->
<div class="slds-media">
  <div class="slds-media__figure">
    <span class="slds-avatar slds-avatar_circle slds-avatar_medium">
      <img src="/avatar.jpg" alt="User" />
    </span>
  </div>
  <div class="slds-media__body">
    <h3 class="slds-text-heading_small">John Smith</h3>
    <p class="slds-text-body_regular">Sales Representative</p>
  </div>
</div>

<!-- Vertically centered icon and text -->
<div class="slds-media slds-media_center">
  <div class="slds-media__figure">
    <span class="slds-icon_container slds-icon-standard-account">
      <svg class="slds-icon slds-icon_small">
        <use href="/icons/standard-sprite.svg#account"></use>
      </svg>
    </span>
  </div>
  <div class="slds-media__body">
    <p>Acme Corporation</p>
  </div>
</div>

<!-- Figure on right side -->
<div class="slds-media">
  <div class="slds-media__body">
    <h4>Notification Settings</h4>
    <p>Email notifications are enabled</p>
  </div>
  <div class="slds-media__figure slds-media__figure_reverse">
    <button class="slds-button slds-button_icon">
      <svg class="slds-button__icon">
        <use href="/icons/utility-sprite.svg#settings"></use>
      </svg>
    </button>
  </div>
</div>

<!-- Small spacing variant for compact lists -->
<ul>
  <li class="slds-media slds-media_small">
    <div class="slds-media__figure">
      <span class="slds-icon_container">
        <svg class="slds-icon slds-icon_x-small">
          <use href="/icons/utility-sprite.svg#file"></use>
        </svg>
      </span>
    </div>
    <div class="slds-media__body">
      <span>Document.pdf</span>
    </div>
  </li>
</ul>

<!-- Responsive stacking for mobile -->
<div class="slds-media slds-media_responsive">
  <div class="slds-media__figure">
    <img src="/product.jpg" alt="Product" width="120" />
  </div>
  <div class="slds-media__body">
    <h3>Product Name</h3>
    <p>Product description that will stack below image on mobile devices</p>
  </div>
</div>
```

## Implementation Guidelines

### Component Combinations

| Use Case | Classes | Description |
|----------|---------|-------------|
| Avatar with name | `slds-media` | Standard user profile display |
| Icon with label | `slds-media slds-media_center slds-media_small` | Compact icon labels |
| Product image with details | `slds-media slds-media_large` | E-commerce layouts |
| Notification with action | `slds-media` + `slds-media__figure_reverse` | Action button on right |
| Mobile-friendly layout | `slds-media slds-media_responsive` | Stacks on small screens |

### Spacing Guidelines

| Context | Recommended Variant | Gap Size |
|---------|-------------------|----------|
| List items | `slds-media_small` | 8px |
| Standard cards | Default (no modifier) | 12px |
| Featured content | `slds-media_large` | 20px |

## Best Practices

✅ Use `slds-media__body` for text content to enable proper truncation
✅ Use `slds-media_center` when icon and text should align middle
✅ Use `slds-media_small` for compact list items
✅ Use `slds-media_responsive` for mobile-optimized layouts
✅ Place avatars and icons in `slds-media__figure`
✅ Use `min-width: 0` on body for text truncation support

❌ Don't nest media objects more than 2 levels deep
❌ Don't use media objects for complex grid layouts
❌ Don't forget `slds-media__figure` wrapper for images
❌ Don't apply spacing utilities directly to figure or body