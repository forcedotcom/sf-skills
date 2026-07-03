---
id: slds.guidance.utilities.box
title: Box Utilities
description: SLDS box utility classes for containers with padding and borders
summary: "Utilities for creating styled containers with padding, borders, and interactive states. Use with theme utilities for semantic colors."

artifact_type: reference
domain: utilities
topic: box

content_format: structured
complexity: intermediate
audience: [implementer]

tasks: [implement]

refs:
  - slds.guidance.utilities
  - slds.guidance.overview.utilities
  - slds.guidance.utilities.themes
  - slds.guidance.utilities.borders
  - slds.guidance.utilities.padding

tags: [utilities, box, containers, padding, borders]
keywords: [slds-box, slds-box_xx-small, slds-box_x-small, slds-box_small, slds-box_link, container, padding]
---

# Box Utilities

Utilities for creating styled containers with consistent padding, borders, and interactive states.

## Core Classes

| Class | Purpose |
|-------|---------|
| `slds-box` | Creates a container with 16px padding, rounded corners, and subtle border |
| `slds-box_xx-small` | Container with 4px padding for compact layouts |
| `slds-box_x-small` | Container with 8px padding for small content areas |
| `slds-box_small` | Container with 12px padding for slightly reduced spacing |
| `slds-box_link` | Makes box clickable with hover/focus states and accent border |

## Related Utilities

- **Themes Utilities** - For background colors and semantic theming (success, error, warning, info), see [Themes Utilities](ref:slds.guidance.utilities.themes)
- **Borders Utilities** - For directional borders, see [Borders Utilities](ref:slds.guidance.utilities.borders)
- **Spacing Utilities** - For padding control, see [Padding Utilities](ref:slds.guidance.utilities.padding)

## Common Patterns

### Basic Container
```html
<!-- Standard box container with default 16px padding -->
<div class="slds-box">
  <h3 class="slds-text-heading_small">Container Title</h3>
  <p>Content with consistent padding and subtle border styling.</p>
</div>
```

### Themed Notification Box
```html
<!-- Success notification with semantic colors (see themes.md for theme utilities) -->
<div class="slds-box slds-theme_success">
  <div class="slds-media">
    <div class="slds-media__figure">
      <span class="slds-icon_container">
        <svg class="slds-icon slds-icon_small">
          <use xlink:href="/assets/icons/utility-sprite/svg/symbols.svg#success"></use>
        </svg>
      </span>
    </div>
    <div class="slds-media__body">
      <p>Operation completed successfully.</p>
    </div>
  </div>
</div>
```

### Interactive Box Link
```html
<!-- Clickable box that navigates to detail view -->
<a href="/record/detail" class="slds-box slds-box_link">
  <h3 class="slds-text-heading_small">Account Name</h3>
  <dl class="slds-list_horizontal slds-wrap">
    <dt class="slds-item_label">Type:</dt>
    <dd class="slds-item_detail">Customer</dd>
    <dt class="slds-item_label">Revenue:</dt>
    <dd class="slds-item_detail">$1.2M</dd>
  </dl>
</a>
```

### Compact Info Card
```html
<!-- Small padding variant for dense layouts (see themes.md for theme utilities) -->
<div class="slds-box slds-box_x-small slds-theme_shade">
  <div class="slds-grid slds-grid_align-spread">
    <span class="slds-text-body_small">Last Updated</span>
    <span class="slds-text-body_small">2 hours ago</span>
  </div>
</div>
```

### Error Message Box
```html
<!-- Error state with semantic styling (see themes.md for theme utilities) -->
<div class="slds-box slds-theme_error" role="alert">
  <h3 class="slds-text-heading_small">Validation Error</h3>
  <ul class="slds-list_dotted">
    <li>Email address is required</li>
    <li>Phone number format is invalid</li>
  </ul>
</div>
```

## Best Practices

✅ Use `slds-box` for consistent container styling across components
✅ Combine box utilities with theme utilities (see [Themes Utilities](ref:slds.guidance.utilities.themes)) for semantic state communication
✅ Use `slds-box_link` for entire containers that are clickable
✅ Combine size variants with theme classes for flexible layouts
✅ Apply `role="alert"` to error and warning themed boxes for accessibility

❌ Don't nest multiple `slds-box` containers without purpose
❌ Don't apply `slds-box_link` to non-interactive elements
❌ Don't override box padding with inline styles - use the size variants instead