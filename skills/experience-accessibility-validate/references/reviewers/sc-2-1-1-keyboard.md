## SC 2.1.1 - Keyboard (Level A)

All functionality of the content is operable through a keyboard interface without requiring specific timings for individual keystrokes, except where the underlying function requires input that depends on the path of the user's movement and not just the endpoints.

## SC: 2.1.1 - Keyboard

Analyze the given file using the following framework:

Review the provided HTML and JS files for accessibility violations per WCAG 2.2 SC 2.1.1, 'Keyboard'. For all elements on the page, ensure that the element exposes all interactivity that is achievable via mouse to keyboard in order to determine if they comply with SC 2.1.1. If they don't comply with the success criterion, then flag them a violation.

Interactive controls must be accessible when using the keyboard alone, and when using a keyboard along with assistive technology, such as a screen reader, without requiring specific timings for keystrokes. The exception to this is when the underlying functionality requires path-based movement.

Common modes of failure for this rule are:

- Custom input implementations don't have an equivalent keyboard functionality. For example, an element with click or pointer handlers, but no equivalent functionality for keypress.
- Elements that can't be navigated to via the keyboard but can be interacted with via the mouse. For example, an interactive element that's missing a `tabindex`, either because it doesn't have one by default or it hasn't been explicitly assigned.
- Tooltips that are only accessible through mouse hover. For example, an element that displays a tooltip on mouse hover, however, there is no way to access the tooltip via keyboard. The tooltip should be accessible via hover, keyboard and click.
- Anchor (`<a>`) elements that are used as interactive controls (e.g., with `onclick` or have an `onclick` attribute) and don't have an `href` attribute aren't focusable or operable via keyboard. This is a violation. Use a `button` element or ensure that the anchor has an `href` and is accessible via the keyboard.
- **Incorrect Tab Indices**: When a parent element has `tabindex="0"` but its child interactive element has `tabindex="-1"`, this creates a keyboard trap. The parent becomes focusable but the child button/link cannot be activated via keyboard. Always flag this pattern as "Incorrect Tab Indices".
- **Tabindex out of sequence**: When `tabindex` values are greater than 0, they disrupt the natural keyboard navigation order. Flag any `tabindex` with positive values (1, 2, 10, etc.) as violations that need to be removed.
- **DIV elements with event handlers**: Non-semantic elements (`div`, `span`) with click handlers must have `tabindex="0"` to be keyboard accessible. Without `tabindex`, they cannot receive focus.

Given the common modes of failure, consider:

- Is the control using semantic HTML? If the semantic HTML default behaviors aren't overridden and new mouse functions aren't added, it will work with a keyboard. Don't flag this as a violation.
- Is the control focusable? If the control is focusable, it can properly handle a keyboard event. Don't flag this as a violation.
- Does anything override the focus event? If native focus is allowed, then nothing will override the focus event and elements should receive and handle focus events correctly. If the focus is altered, elements might not receive or handle focus events correctly.

**SPECIFIC TABINDEX PATTERNS TO IDENTIFY:**

1. **Parent-Child Tabindex Conflicts**: Scan for `<li tabindex="0">` containing `<button tabindex="-1">` or similar patterns where parent is focusable but child interactive element is not.
2. **High Tabindex Values**: Look for any `tabindex="X"` where X > 0 (like `tabindex="10"`, `tabindex="5"`). These disrupt natural tab order.
3. **Semantic Elements with Unnecessary Tabindex**: Buttons, links, and form controls don't need explicit `tabindex` values.

Rules to follow:

- Find all violations of SC 2.1.1 'Keyboard' in the provided HTML and JS files.
- DO NOT flag issues when native HTML elements provide sufficient keyboard accessibility.

- For each issue found, provide a separate, detailed report.
- Keep issues concise, avoid duplicated issues or unnecessary or non-applicable problems.
- Assume that any imported functionality works as expected and was already analyzed.
- Components do not supplement or provide global functionalities.
- Lightning base components (`lightning-input`, `lightning-combobox`, `lightning-textarea`, `lightning-icon`, etc.) provide their own accessible labeling, ARIA, and error handling in shadow DOM via their dedicated attributes (`label`, `alternative-text`, field-level validation). When such a component is given a `label` attribute it is already programmatically labeled — even with `variant="label-hidden"`, which hides the label visually but keeps it for assistive technology. Do **not** flag a sibling/wrapper `<label>` or `<span>` for a missing `for`/`id` when the actual control is a self-labeling Lightning component, and do not treat a visible heading as if it were the control's only label. This also covers navigation and icon base components (`lightning-vertical-navigation-item`, `lightning-vertical-navigation-item-icon`, `lightning-button-icon`, etc.): when a `label` (or `alternative-text`) attribute is supplied, the base component renders it as the visible link/control text **and** exposes it as the accessible name, and any `icon-name` is decorative — do not emit a 4.1.2 "verify the label is associated with the icon" warning, even a hedged one. The presence of the `label` attribute is the association.
- Resolve template bindings before judging them. A template expression like `{someValue}` refers to a property or getter on the component's controller (`.js`/`.ts`) — including `@api` properties and `get someValue()` getters — not to a module-level imported constant (which LWC templates cannot bind to). Check the controller for the binding's definition before concluding a value is undefined, empty, or missing. When reviewing a diff, verify which side is the corrected code; do not assume the change introduced the problem.
- Prefer a real `<button>` for actions; for a link, `href="#"` with `event.preventDefault()` (the canonical SLDS pattern). Don't recommend `href="javascript:void(0)"` as a first-line remediation — it's a no-op-anchor anti-pattern. It is acceptable only as a last resort when moving `<a>` → `<button>` is genuinely impossible, and even then only when paired with the full set of attributes that make the anchor behave as an accessible button (`role="button"`, keyboard activation, etc.) — `void(0)` on its own is an incomplete fix. Don't flag existing `javascript:void(0)` as a violation.
- ARIA attribute spelling depends on the element type. On a **plain HTML element** (`div`, `span`, `button`, `input`, `a`, `img`, `iframe`, …) the only valid spelling is the W3C form `aria-labelledby` / `aria-describedby`; the hyphen-split `aria-labelled-by` / `aria-described-by` there **is** a real bug — keep flagging it. But on an **LWC component tag** (`lightning-*` or a custom `ns-name` element), the hyphen-split form is the kebab-case binding of the component's `@api ariaLabelledBy` / `ariaDescribedBy` property (each capital letter maps to `-` + lowercase), and LWC reflects it to the spec-correct `aria-labelledby` in the rendered DOM. Do **not** flag `aria-labelled-by` on a component tag as a misspelling, and do not claim it "breaks the accessible name computation" — you cannot determine that from the attribute name alone, because both `aria-labelled-by` (via `@api` property kebab-casing) and `aria-labelledby` (via LWC's ARIA reflection) can wire to the same property depending on the component. Treat a hyphen-split ARIA attribute on a component tag as a valid binding, not a violation.
