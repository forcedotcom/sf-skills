## SC 1.1.1 - Non-text Content (Level A)

All non-text content that is presented to the user has a text alternative that serves the equivalent purpose, except for specific situations such as controls or input, time-based media, test, sensory, CAPTCHA, and decoration or formatting.

## SC: 1.1.1 - Non-text Content (All Images)

This reviewer focuses on both decorative and informative images and their proper accessibility handling.

### Definition of Decorative Image:

A decorative image is one that:

- Provides no information content
- Is used for visual formatting, spacing, or decoration
- Does not convey meaning or context
- Is not essential to understanding the content

### Definition of Informative Image:

An informative image is any image that conveys information, meaning, or context that is essential to understanding the content or functionality of a webpage or application.

### Analysis Framework(What to do):

1. Identify all `<img>` elements in the HTML
2. Determine if each image is decorative or informative
3. Check if decorative images have proper `alt=""` attributes
4. Check if informative images have meaningful descriptive alt text
5. Look for CSS background images that should be used instead
6. Check for ARIA hidden attributes on decorative images

### Goals for Decorative Images:

1. **Empty alt attribute**: Should have `alt=""` for purely decorative images
   - Good: `<img src="decorative-border.png" alt="" />`
   - Bad: `<img src="decorative-border.png" />`
2. **CSS background images**: Should not have alt text as they are not in the accessibility tree
3. **ARIA hidden**: Can use `aria-hidden="true"` for decorative images that must remain in DOM
   - Good: `<img src="spacer.gif" alt="" aria-hidden="true" />`
4. **No redundant text**: Avoid providing descriptive alt text for decorative images
   - Bad: `<img src="decorative-border.png" alt="Decorative border with flowers" />`
5. **Decorative image as link without context**: Add `aria-label` or `title` attribute to the anchor tag
   - Bad: `<a href="/page"><img src="decorative-icon.png" alt="" /></a>`
   - Good: `<a href="/page" aria-label="Navigate to main page"><img src="decorative-icon.png" alt="" /></a>`

### Goals for Informative Images:

1. **Must have alt attribute**: All informative images must have descriptive alt text
   - Good: `<img src="company-logo.png" alt="Our Company Logo" />`
   - Bad: `<img src="chart.png" />`
2. **Meaningful content**: Alt text should describe the information conveyed
   - Good: `<img src="chart.png" alt="Quarterly sales performance chart showing revenue trends" />`
   - Bad: `<img src="chart.png" alt="chart" />`

### What to Look For:

- `<img>` elements without alt attributes (both decorative and informative)
- `<img>` elements with generic alt text like "image", "picture", "photo"
- Decorative images that are not properly marked as decorative
- Informative images with missing or inadequate alt text
- Background images that are incorrectly implemented as `<img>` elements
- Decorative images used in interactive contexts without proper labeling

### Common Violations for Images:

- Missing alt attribute on decorative images
- Missing alt attribute on informative images
- Using `alt="image"` or `alt="picture"` for decorative images
- Providing descriptive alt text for purely decorative images
- Using decorative images as links without proper context
- Including decorative images in the accessibility tree when they should be hidden

Rules to follow:

- Focus specifically on decorative or non decorative images and their alt text handling in the provided HTML and JS files
- Flag missing alt attributes on decorative images
- Flag generic alt text (like "image", "picture") on decorative images
- Flag missing or generic alt text on informative images
- Flag overly descriptive alt text on clearly decorative images
- Consider the context and purpose of each image

- For each issue found, provide a separate, detailed report.
- Keep issues concise, avoid duplicated issues or unnecessary or non-applicable problems.
- Assume that any imported functionality works as expected and was already analyzed.
- Components do not supplement or provide global functionalities.
- Lightning base components (`lightning-input`, `lightning-combobox`, `lightning-textarea`, `lightning-icon`, etc.) provide their own accessible labeling, ARIA, and error handling in shadow DOM via their dedicated attributes (`label`, `alternative-text`, field-level validation). When such a component is given a `label` attribute it is already programmatically labeled — even with `variant="label-hidden"`, which hides the label visually but keeps it for assistive technology. Do **not** flag a sibling/wrapper `<label>` or `<span>` for a missing `for`/`id` when the actual control is a self-labeling Lightning component, and do not treat a visible heading as if it were the control's only label. This also covers navigation and icon base components (`lightning-vertical-navigation-item`, `lightning-vertical-navigation-item-icon`, `lightning-button-icon`, etc.): when a `label` (or `alternative-text`) attribute is supplied, the base component renders it as the visible link/control text **and** exposes it as the accessible name, and any `icon-name` is decorative — do not emit a 4.1.2 "verify the label is associated with the icon" warning, even a hedged one. The presence of the `label` attribute is the association.
- Resolve template bindings before judging them. A template expression like `{someValue}` refers to a property or getter on the component's controller (`.js`/`.ts`) — including `@api` properties and `get someValue()` getters — not to a module-level imported constant (which LWC templates cannot bind to). Check the controller for the binding's definition before concluding a value is undefined, empty, or missing. When reviewing a diff, verify which side is the corrected code; do not assume the change introduced the problem.
- Prefer a real `<button>` for actions; for a link, `href="#"` with `event.preventDefault()` (the canonical SLDS pattern). Don't recommend `href="javascript:void(0)"` as a first-line remediation — it's a no-op-anchor anti-pattern. It is acceptable only as a last resort when moving `<a>` → `<button>` is genuinely impossible, and even then only when paired with the full set of attributes that make the anchor behave as an accessible button (`role="button"`, keyboard activation, etc.) — `void(0)` on its own is an incomplete fix. Don't flag existing `javascript:void(0)` as a violation.
- ARIA attribute spelling depends on the element type. On a **plain HTML element** (`div`, `span`, `button`, `input`, `a`, `img`, `iframe`, …) the only valid spelling is the W3C form `aria-labelledby` / `aria-describedby`; the hyphen-split `aria-labelled-by` / `aria-described-by` there **is** a real bug — keep flagging it. But on an **LWC component tag** (`lightning-*` or a custom `ns-name` element), the hyphen-split form is the kebab-case binding of the component's `@api ariaLabelledBy` / `ariaDescribedBy` property (each capital letter maps to `-` + lowercase), and LWC reflects it to the spec-correct `aria-labelledby` in the rendered DOM. Do **not** flag `aria-labelled-by` on a component tag as a misspelling, and do not claim it "breaks the accessible name computation" — you cannot determine that from the attribute name alone, because both `aria-labelled-by` (via `@api` property kebab-casing) and `aria-labelledby` (via LWC's ARIA reflection) can wire to the same property depending on the component. Treat a hyphen-split ARIA attribute on a component tag as a valid binding, not a violation.
