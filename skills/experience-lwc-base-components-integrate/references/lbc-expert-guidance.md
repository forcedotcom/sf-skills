# Lightning Base Component Styling Guidelines

## Description

Styling guidelines for Lightning Web Components that consume Lightning Base Components: when component CSS layers custom styles on top of `lightning-*` components, certain SLDS-class usage patterns break the SLDS contract and must be rewritten to use component-owned custom classes.

## The core rule

Never target an SLDS class (`.slds-*`) in a component's CSS, either directly or as part of a compound selector. SLDS classes are owned by SLDS and may change their internal styling at any time; overriding them invalidates the SLDS guarantee.

## Scope

These guidelines apply when:

- The LWC uses one or more `lightning-*` Base Components, AND
- The component CSS contains selectors that include `.slds-*` class names.

## Fix pattern

Replace direct or compound SLDS-class selectors with component-owned custom classes. The fix always touches **both** the HTML template (to add the custom class) and the CSS (to retarget the selector).

### Example — overriding SLDS class properties directly

**Before**

CSS:

```css
.slds-button {
  background: pink;
}

.slds-component_active .slds-combobox {
  display: block;
}
```

HTML:

```html
<template>
  <button class="slds-button">Click me</button>
  <div class="slds-component_active slds-combobox">I'm going to display something based on state</div>
</template>
```

**Problem:** the CSS overrides SLDS styles directly. This invalidates the SLDS contract and breaks under SLDS internal changes.

**After**

HTML — add custom classes alongside the existing SLDS classes:

```html
<template>
  <button class="slds-button primary-button">Click me</button>
  <div class="slds-component_active slds-combobox active-display">I'm going to display something based on state</div>
</template>
```

CSS — target the custom classes, with the SLDS classes removed from the selectors entirely:

```css
.primary-button {
  background: pink;
}

.active-display {
  display: block;
}
```

### Key properties of the fix

- HTML: introduce a new custom class name (e.g. `primary-button`, `active-display`) on the element that needs styling.
- CSS: rewrite the selector to target the new custom class. The SLDS class is **completely removed** from the selector.
- Markup structure (tags, nesting, attributes other than `class`) is never changed.

## How to apply

For each LWC that uses a `lightning-*` Base Component, scan the CSS for selectors that contain `.slds-*` (direct or compound). For each occurrence, produce a paired HTML+CSS edit:

1. **HTML** — add a new custom class (kebab-case, component-scoped name) to the element being styled, alongside the existing SLDS class. Do not change tags, nesting, or any non-`class` attribute.
2. **CSS** — rewrite the selector to target the new custom class only. Remove the `.slds-*` segment from the selector entirely.

Produce one fix entry per violation with: file + line number for the HTML edit, file + line number for the CSS edit, and the corrected selector. Apply the same custom-class naming convention consistently across all violations in the same component.

### Example: component with SLDS class in CSS selector

**Component HTML:**

```html
<template>
  <div class="fooDiv">
    <button class="slds-button">Click me</button>
  </div>
</template>
```

**Component CSS:**

```css
.fooDiv .slds-button {
  background-color: red;
}
```

**Issue:** The CSS selector `.fooDiv .slds-button` targets the SLDS class directly. This overrides SLDS internal styles and breaks the SLDS contract.

**Fix:**

Add a custom class to the `button` element on line 3 of the HTML:

```html
<template>
  <div class="fooDiv">
    <button class="slds-button custom-button">Click me</button>
  </div>
</template>
```

Retarget the CSS selector to the custom class:

```css
.custom-button {
  background-color: red;
}
```
