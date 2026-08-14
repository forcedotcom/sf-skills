## SC 1.3.1 - Info and Relationships (Level A)

Information, structure, and relationships conveyed through presentation can be programmatically determined or are available in text.

## SC: 1.3.1 (iv) - Info And Relationships - Regions (A)

Review the provided HTML and JS files for accessibility violations per WCAG 2.2 SC 1.3.1 (iv), 'Info and Relationships'
(Only regions from this rule should be considered). For all regions on the page, ensure that any information conveyed through presentation is programmatically determinable in order to determine if they meet SC 1.3.1 (iv).
If they do not meet this success criterion, flag it as a violation.

Rules to follow:

- Find all violations of SC 1.3.1 'Info and Relationships - Regions' in the provided HTML and JS files.
- Do not worry about violations of SC 1.3.1 that are not specific to regions. These will be handled by other reviewers.
- Use semantic HTML elements (`<header>`, `<nav>`, `<main>`, `<aside>`, `<footer>`, `<section>`) to mark up regions. There cannot be more than one `<main>` element that does not have a hidden attribute specified.
- When semantic elements cannot be used, use ARIA landmark roles (`role="banner"`, `role="navigation"`, `role="main"`, `role="complementary"`, `role="contentinfo"`, `role="region"`).
- Each region should have a descriptive label or heading that identifies its purpose.
- Regions should be properly nested and not overlap.
  - For each issue found, provide a separate, detailed report.
- Keep issues concise, avoid duplicated issues or unnecessary or non-applicable problems.
- Assume that any imported functionality works as expected and was already analyzed.
- Components do not supplement or provide global functionalities.
- Lightning base components (`lightning-input`, `lightning-combobox`, `lightning-textarea`, `lightning-icon`, etc.) provide their own accessible labeling, ARIA, and error handling in shadow DOM via their dedicated attributes (`label`, `alternative-text`, field-level validation). When such a component is given a `label` attribute it is already programmatically labeled — even with `variant="label-hidden"`, which hides the label visually but keeps it for assistive technology. Do **not** flag a sibling/wrapper `<label>` or `<span>` for a missing `for`/`id` when the actual control is a self-labeling Lightning component, and do not treat a visible heading as if it were the control's only label. This also covers navigation and icon base components (`lightning-vertical-navigation-item`, `lightning-vertical-navigation-item-icon`, `lightning-button-icon`, etc.): when a `label` (or `alternative-text`) attribute is supplied, the base component renders it as the visible link/control text **and** exposes it as the accessible name, and any `icon-name` is decorative — do not emit a 4.1.2 "verify the label is associated with the icon" warning, even a hedged one. The presence of the `label` attribute is the association.
- Resolve template bindings before judging them. A template expression like `{someValue}` refers to a property or getter on the component's controller (`.js`/`.ts`) — including `@api` properties and `get someValue()` getters — not to a module-level imported constant (which LWC templates cannot bind to). Check the controller for the binding's definition before concluding a value is undefined, empty, or missing. When reviewing a diff, verify which side is the corrected code; do not assume the change introduced the problem.
- Prefer a real `<button>` for actions; for a link, `href="#"` with `event.preventDefault()` (the canonical SLDS pattern). Don't recommend `href="javascript:void(0)"` as a first-line remediation — it's a no-op-anchor anti-pattern. It is acceptable only as a last resort when moving `<a>` → `<button>` is genuinely impossible, and even then only when paired with the full set of attributes that make the anchor behave as an accessible button (`role="button"`, keyboard activation, etc.) — `void(0)` on its own is an incomplete fix. Don't flag existing `javascript:void(0)` as a violation.
- ARIA attribute spelling depends on the element type. On a **plain HTML element** (`div`, `span`, `button`, `input`, `a`, `img`, `iframe`, …) the only valid spelling is the W3C form `aria-labelledby` / `aria-describedby`; the hyphen-split `aria-labelled-by` / `aria-described-by` there **is** a real bug — keep flagging it. But on an **LWC component tag** (`lightning-*` or a custom `ns-name` element), the hyphen-split form is the kebab-case binding of the component's `@api ariaLabelledBy` / `ariaDescribedBy` property (each capital letter maps to `-` + lowercase), and LWC reflects it to the spec-correct `aria-labelledby` in the rendered DOM. Do **not** flag `aria-labelled-by` on a component tag as a misspelling, and do not claim it "breaks the accessible name computation" — you cannot determine that from the attribute name alone, because both `aria-labelled-by` (via `@api` property kebab-casing) and `aria-labelledby` (via LWC's ARIA reflection) can wire to the same property depending on the component. Treat a hyphen-split ARIA attribute on a component tag as a valid binding, not a violation.
