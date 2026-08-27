## SC 2.4.4 - Link Purpose (In Context) (Level A)

The purpose of each link can be determined from the link text alone or from the link text together with its programmatically determined link context, except where the purpose of the link would be ambiguous to users in general.

## SC: 2.4.4 - Link Purpose (In Context)

Analyze the given file using the following framework:

Review the provided HTML file for accessibility violations per WCAG 2.2 SC 2.4.4, 'Link Purpose (In Context)'. For all anchor elements (`<a>`) and other interactive elements that function as links, ensure that the link text is descriptive enough to convey the purpose of the link, either on its own or with its immediate context (such as the same sentence, list item, or table cell). If the link purpose cannot be determined, flag this as a violation.

Common modes of failure for this rule are:

- Using vague link text such as 'click here', 'read more', or 'more' without sufficient context. (Type: "Vague Link Text")
- Relying on context that is not programmatically associated with the link (e.g., context that is visually near but not in the same sentence, list item, or table cell).
- Using only an icon or image as a link without accessible text or an appropriate accessible name, such as an `aria-label`. (Type: "Non-descriptive Icon Link")
- Multiple links using the same non-descriptive text (e.g., "Read more") but pointing to different destinations. (Type: "Duplicate Link Text")

For each violation, provide:

- The exact type as listed above.
- A detailed description of why it is a problem, referencing accessibility best practices.
- An intent analysis explaining what the developer likely intended.
- A suggested action, with precise recommendations (e.g., for icon links, recommend adding an `aria-label`, not just alt text).
- For duplicate link text, identify and report all instances, not just the first.

Rules to follow:

- Find all violations of SC 2.4.4 'Link Purpose (In Context)' in the provided HTML file.
- If no changes are needed, then produce an empty list.
- Use the exact terminology for issue types as listed above.

- For each issue found, provide a separate, detailed report.
- Keep issues concise, avoid duplicated issues or unnecessary or non-applicable problems.
- Assume that any imported functionality works as expected and was already analyzed.
- Components do not supplement or provide global functionalities.
- Lightning base components (`lightning-input`, `lightning-combobox`, `lightning-textarea`, `lightning-icon`, etc.) provide their own accessible labeling, ARIA, and error handling in shadow DOM via their dedicated attributes (`label`, `alternative-text`, field-level validation). When such a component is given a `label` attribute it is already programmatically labeled — even with `variant="label-hidden"`, which hides the label visually but keeps it for assistive technology. Do **not** flag a sibling/wrapper `<label>` or `<span>` for a missing `for`/`id` when the actual control is a self-labeling Lightning component, and do not treat a visible heading as if it were the control's only label. This also covers navigation and icon base components (`lightning-vertical-navigation-item`, `lightning-vertical-navigation-item-icon`, `lightning-button-icon`, etc.): when a `label` (or `alternative-text`) attribute is supplied, the base component renders it as the visible link/control text **and** exposes it as the accessible name, and any `icon-name` is decorative — do not emit a 4.1.2 "verify the label is associated with the icon" warning, even a hedged one. The presence of the `label` attribute is the association.
- Resolve template bindings before judging them. A template expression like `{someValue}` refers to a property or getter on the component's controller (`.js`/`.ts`) — including `@api` properties and `get someValue()` getters — not to a module-level imported constant (which LWC templates cannot bind to). Check the controller for the binding's definition before concluding a value is undefined, empty, or missing. When reviewing a diff, verify which side is the corrected code; do not assume the change introduced the problem.
- Prefer a real `<button>` for actions; for a link, `href="#"` with `event.preventDefault()` (the canonical SLDS pattern). Don't recommend `href="javascript:void(0)"` as a first-line remediation — it's a no-op-anchor anti-pattern. It is acceptable only as a last resort when moving `<a>` → `<button>` is genuinely impossible, and even then only when paired with the full set of attributes that make the anchor behave as an accessible button (`role="button"`, keyboard activation, etc.) — `void(0)` on its own is an incomplete fix. Don't flag existing `javascript:void(0)` as a violation.
- ARIA attribute spelling depends on the element type. On a **plain HTML element** (`div`, `span`, `button`, `input`, `a`, `img`, `iframe`, …) the only valid spelling is the W3C form `aria-labelledby` / `aria-describedby`; the hyphen-split `aria-labelled-by` / `aria-described-by` there **is** a real bug — keep flagging it. But on an **LWC component tag** (`lightning-*` or a custom `ns-name` element), the hyphen-split form is the kebab-case binding of the component's `@api ariaLabelledBy` / `ariaDescribedBy` property (each capital letter maps to `-` + lowercase), and LWC reflects it to the spec-correct `aria-labelledby` in the rendered DOM. Do **not** flag `aria-labelled-by` on a component tag as a misspelling, and do not claim it "breaks the accessible name computation" — you cannot determine that from the attribute name alone, because both `aria-labelled-by` (via `@api` property kebab-casing) and `aria-labelledby` (via LWC's ARIA reflection) can wire to the same property depending on the component. Treat a hyphen-split ARIA attribute on a component tag as a valid binding, not a violation.
