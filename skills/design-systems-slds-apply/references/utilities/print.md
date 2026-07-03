---
id: slds.guidance.utilities.print
title: Print Utilities
description: SLDS print utility class for controlling element visibility when printing
summary: "Utility class (.slds-no-print) for hiding elements when printing."

artifact_type: reference
domain: utilities
topic: print

content_format: structured
complexity: intermediate
audience: [implementer]

tasks: [implement]

refs:
  - slds.guidance.utilities
  - slds.guidance.overview.utilities

tags: [utilities, print, visibility, media-query]
keywords: [slds-no-print, print, hide-on-print]
---

# Print - Print Visibility Control

Hiding elements when printing pages.

## Core Classes

| Class | Purpose |
|-------|---------|
| `slds-no-print` | Hides element when page is printed (display: none in @media print) |

## Common Patterns

```html
<!-- Hide navigation when printing -->
<nav class="slds-context-bar slds-no-print">
  <!-- Navigation won't appear in printed output -->
  <div class="slds-context-bar__primary">
    Navigation Menu
  </div>
</nav>

<!-- Hide action buttons when printing -->
<div class="slds-page-header">
  <div class="slds-page-header__title">
    Report Title
  </div>
  <div class="slds-page-header__controls slds-no-print">
    <!-- Buttons hidden in print -->
    <button class="slds-button slds-button_neutral">Edit</button>
    <button class="slds-button slds-button_brand">Save</button>
  </div>
</div>

<!-- Hide UI controls on data table -->
<table class="slds-table">
  <thead>
    <tr>
      <th class="slds-no-print">
        <!-- Checkbox column hidden in print -->
        <input type="checkbox" />
      </th>
      <th>Name</th>
      <th>Status</th>
      <th class="slds-no-print">Actions</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td class="slds-no-print">
        <input type="checkbox" />
      </td>
      <td>Record Name</td>
      <td>Active</td>
      <td class="slds-no-print">
        <!-- Action buttons hidden in print -->
        <button class="slds-button">Edit</button>
      </td>
    </tr>
  </tbody>
</table>

<!-- Hide floating action button -->
<div class="slds-fab slds-no-print">
  <!-- Floating button hidden in print -->
  <button class="slds-button slds-button_icon">
    <svg class="slds-button__icon"><!-- Icon --></svg>
  </button>
</div>

<!-- Hide page footer with metadata -->
<footer class="slds-p-around_medium slds-no-print">
  <!-- Footer info hidden in print -->
  Last updated: Today at 3:45 PM
  <br />
  Page 1 of 10
</footer>
```

## Best Practices

✅ Use `slds-no-print` on navigation menus and app bars
✅ Use `slds-no-print` on action buttons and interactive controls
✅ Use `slds-no-print` on checkbox columns in data tables
✅ Use `slds-no-print` on floating action buttons and overlays
✅ Use `slds-no-print` on breadcrumbs and page metadata
✅ Test print preview to ensure proper hiding of elements

❌ Avoid hiding essential content that users need in printed output
❌ Avoid hiding data table headers or important labels
❌ Avoid hiding status badges or important visual indicators