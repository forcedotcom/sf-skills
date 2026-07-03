---
id: slds.guidance.utilities.dark-mode
title: Dark Mode Utilities
description: SLDS color scheme utility classes for controlling light, dark, and system color preferences
summary: "Utilities for controlling color scheme preferences. Forces light mode, dark mode, or respects system preference."

artifact_type: reference
domain: utilities
topic: dark-mode

content_format: structured
complexity: intermediate
audience: [implementer]

tasks: [implement]

refs:
  - slds.guidance.utilities
  - slds.guidance.overview.utilities
  - slds.guidance.hooks.color
  - slds.guidance.utilities.themes

tags: [utilities, dark-mode, color-scheme, theme]
keywords: [slds-color-scheme, dark mode, light mode, system preference]
---

# Dark Mode - Color Scheme Control

Utilities for controlling browser color scheme preferences. Uses CSS `color-scheme` property.

## Core Classes

| Class | Purpose |
|-------|---------|
| `slds-color-scheme--light` | Forces light mode only |
| `slds-color-scheme--dark` | Forces dark mode only |
| `slds-color-scheme--system` | Respects system preference |

## Common Patterns

```html
<!-- Force light mode on entire application -->
<body class="slds-color-scheme--light">
  <!-- All content renders in light mode -->
</body>

<!-- Force dark mode on specific component -->
<div class="slds-card slds-color-scheme--dark">
  <!-- Card content renders in dark mode -->
</div>

<!-- System preference for modal -->
<div class="slds-modal slds-color-scheme--system">
  <!-- Modal adapts to user's OS preference -->
</div>

<!-- Mixed mode layout -->
<div class="slds-page">
  <nav class="slds-color-scheme--dark">
    <!-- Navigation always dark -->
  </nav>
  <main class="slds-color-scheme--system">
    <!-- Content follows system preference -->
  </main>
</div>

<!-- Override system preference locally -->
<body class="slds-color-scheme--system">
  <div class="slds-box slds-color-scheme--light">
    <!-- Box always light even if system is dark -->
  </div>
</body>
```

## Implementation Details

### How It Works
- Uses CSS `color-scheme` property
- Applies to element and descendants
- When on `<body>`, affects entire document via `:has()` selector
- Browser automatically adjusts form controls, scrollbars, and system colors

### Property Values
| Class | CSS Property | Effect |
|-------|--------------|--------|
| `slds-color-scheme--light` | `color-scheme: only light` | Forces light colors |
| `slds-color-scheme--dark` | `color-scheme: only dark` | Forces dark colors |
| `slds-color-scheme--system` | `color-scheme: light dark` | Allows both schemes |

## Best Practices

✅ Apply `slds-color-scheme--system` to `<body>` for app-wide system preference support
✅ Use `slds-color-scheme--dark` for navigation bars and headers
✅ Use `slds-color-scheme--light` for data-heavy tables and forms
✅ Test both light and dark modes for all components
✅ Use modern double-dash syntax (`--`) for new implementations

❌ Don't use deprecated underscore syntax (`_`) in new code
❌ Don't mix color scheme classes on the same element
❌ Don't assume dark mode without testing contrast ratios
❌ Don't override user system preference without clear UI controls

## Deprecated Classes

The following BEM-style classes are deprecated. Use double-dash syntax instead:

| Deprecated | Use Instead |
|------------|-------------|
| `slds-color-scheme_light` | `slds-color-scheme--light` |
| `slds-color-scheme_dark` | `slds-color-scheme--dark` |
| `slds-color-scheme_system` | `slds-color-scheme--system` |