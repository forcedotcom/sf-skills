---
id: slds.guidance.utilities.visibility
title: Visibility Utilities
description: SLDS show/hide and responsive display utility classes
summary: "Utilities for controlling element visibility including basic show/hide, responsive breakpoints, screen reader support, and collapsed/expanded states."

artifact_type: reference
domain: utilities
topic: visibility

content_format: structured
complexity: intermediate
audience: [implementer]

tasks: [implement]

refs:
  - slds.guidance.utilities
  - slds.guidance.overview.utilities

tags: [utilities, visibility, responsive, accessibility]
keywords: [slds-show, slds-hide, slds-assistive-text, responsive visibility, screen reader]
---

# Visibility - Show/Hide Elements

Controlling element visibility and responsive display.

## Basic Visibility

| Class | Effect |
|-------|--------|
| `slds-show` | Display block |
| `slds-hide` | Display none (!important, hidden from screen readers) |
| `slds-hidden` | Visibility hidden (!important, maintains space) |
| `slds-visible` | Visibility visible |
| `slds-is-visually-empty` | Removes element from layout flow |

**Display Variants**:
- `slds-show_inline` - Display inline
- `slds-show_inline-block` - Display inline-block

## Screen Reader Support

| Class | Purpose |
|-------|---------|
| `slds-assistive-text` | Visually hidden but readable by screen readers |
| `slds-assistive-text_focus` | Becomes visible when focused (for skip links) |

```html
<!-- Icon with screen reader label -->
<button class="slds-button slds-button_icon">
  <svg class="slds-icon">...</svg>
  <span class="slds-assistive-text">Edit Record</span>
</button>

<!-- Skip navigation link -->
<a href="#main" class="slds-assistive-text slds-assistive-text_focus">
  Skip to main content
</a>
```

## Collapsed/Expanded States

| Class | Effect |
|-------|--------|
| `slds-is-collapsed` | Height: 0, overflow: hidden |
| `slds-is-expanded` | Height: auto, overflow: visible |

```html
<!-- Collapsible section -->
<div class="slds-section">
  <button aria-expanded="false" aria-controls="section-content">
    Toggle Section
  </button>
  <div id="section-content" class="slds-is-collapsed">
    <!-- Content hidden by default -->
    Collapsible content here
  </div>
</div>
```

## Transition Visibility

| Class | Effect |
|-------|--------|
| `slds-transition-hide` | Opacity: 0 |
| `slds-transition-show` | Opacity: 1 |

Add CSS transitions for smooth animations:
```css
.slds-transition-hide,
.slds-transition-show {
  transition: opacity 0.3s ease;
}
```

## Responsive Visibility

**Breakpoints**:
- `x-small`: 320px
- `small`: 480px
- `medium`: 768px
- `large`: 1024px
- `x-large`: 1280px

### Show Classes (Hidden Below, Visible At/Above)

| Class | Visible From |
|-------|--------------|
| `slds-x-small-show` | 320px+ |
| `slds-small-show` | 480px+ |
| `slds-medium-show` | 768px+ |
| `slds-large-show` | 1024px+ |

**Display Variants**:
- `slds-x-small-show_inline-block`
- `slds-x-small-show_inline`
- `slds-small-show_inline-block`
- `slds-small-show_inline`
- `slds-medium-show_inline-block`
- `slds-medium-show_inline`
- `slds-large-show_inline-block`
- `slds-large-show_inline`

### Show Only Classes (Visible Only Within Range)

| Class | Visible Range |
|-------|---------------|
| `slds-x-small-show-only` | 320px - 479px |
| `slds-small-show-only` | 480px - 767px |
| `slds-medium-show-only` | 768px - 1023px |

**Display Variants**:
- `slds-x-small-show-only_inline-block`
- `slds-x-small-show-only_inline`
- `slds-small-show-only_inline-block`
- `slds-small-show-only_inline`
- `slds-medium-show-only_inline-block`
- `slds-medium-show-only_inline`

### Hide Classes

| Class | Hidden At/Above | Visible Below |
|-------|-----------------|---------------|
| `slds-hide_x-small` | 320px+ | < 320px |
| `slds-hide_small` | 480px+ | < 480px |
| `slds-hide_medium` | 768px+ | < 768px |
| `slds-hide_large` | 1024px+ | < 1024px |
| `slds-hide_x-large` | 1280px+ | < 1280px |

### Max Hide Classes (Hidden Below Breakpoint)

| Class | Hidden Below |
|-------|--------------|
| `slds-max-x-small-hide` | < 480px |
| `slds-max-small-hide` | < 768px |
| `slds-max-medium-hide` | < 1024px |

### Inverse Show Classes (Hidden At/Above)

| Class | Visible Below | Hidden At/Above |
|-------|---------------|-----------------|
| `slds-show_x-small` | < 320px | 320px+ |
| `slds-show_small` | < 480px | 480px+ |
| `slds-show_medium` | < 768px | 768px+ |
| `slds-show_large` | < 1024px | 1024px+ |
| `slds-show_x-large` | < 1280px | 1280px+ |

## Common Patterns

```html
<!-- Mobile menu / Desktop nav -->
<button class="slds-button slds-hide_medium">
  <!-- Visible on mobile, hidden 768px+ -->
  <svg class="slds-icon">...</svg>
  <span class="slds-assistive-text">Open Menu</span>
</button>

<nav class="slds-medium-show">
  <!-- Hidden below 768px, visible 768px+ -->
  <ul class="slds-list_horizontal">...</ul>
</nav>

<!-- Responsive table/card view -->
<div class="slds-max-small-hide">
  <!-- Table hidden below 768px -->
  <table class="slds-table">...</table>
</div>

<div class="slds-small-show-only">
  <!-- Cards shown only 480px-767px -->
  <div class="slds-card">...</div>
</div>

<!-- Progressive disclosure -->
<div class="slds-small-show">
  <!-- Additional details shown 480px+ -->
  Extended information for larger screens
</div>

<!-- Accessible expandable section -->
<section class="slds-section slds-is-open">
  <h2>
    <button aria-expanded="true" aria-controls="content-id">
      Section Title
    </button>
  </h2>
  <div id="content-id" class="slds-is-expanded">
    Section content
  </div>
</section>
```

## Best Practices

✅ Use `slds-assistive-text` for all icon-only buttons
✅ Use `slds-hide` with `!important` to ensure hiding
✅ Test responsive classes at each breakpoint
✅ Pair `aria-expanded` with `slds-is-collapsed/expanded`
✅ Use `slds-assistive-text_focus` for skip links
✅ Apply mobile-first approach: hide by default, show at breakpoints

❌ Combine `slds-hide` and `slds-show` on the same element
❌ Use `slds-hidden` and `slds-visible` together
❌ Hide essential content from screen readers
❌ Use visibility classes for layout (use Grid or Flexbox instead)
❌ Rely only on `display: none` for animations (use transitions)