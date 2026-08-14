## SC 2.5.2 - Pointer Cancellation (Level A)

For functionality that can be operated using a single pointer, at least one of the following is true: no down-event is used to execute any part of the function; abort or undo is available; the up-event reverses any outcome of the preceding down-event; or completing the function on the down-event is essential.

## SC: 2.5.2 - Pointer Cancellation

Analyze the given file using the following framework:

Review the provided JS and HTML for accessibility violations per WCAG 2.2 SC 2.5.2, 'Pointer Cancellation'. Violations occur when a single pointer operable HTML element does not satisfy one of the conditions set forth by 2.5.2, defined below.

You should analyze all elements in the HTML which are operable via a 'single pointer'- this is defined as "pointer input that operates with one point of contact with the screen, including single taps and clicks, double-taps and clicks, long presses, and path-based gestures" (w3.org).

For each of these elements, check if any of the following conditions of SC 2.5.2 are true:

1. The down event is not used to operate the function. This is the single most preferable behavior for this rule whenever is possible.
2. There is a method made available to cancel or abort the action.
3. The up-event reverses any action taken by the down event.
4. The down event is strictly required and ESSENTIAL to the functionality of the code.

If any of the conditions are satisfied, then you can ignore the element and move on, as it complies with the Success Criterion. If none of the conditions are satisfied, YOU MUST flag this as a violation.

Note that typically a violation occurs when an element, as defined above, operates on a down event and does not have an associated cancellation technique.

In order to fix a violation for a given element, you must examine the given component code and apply the most logical fix available such that the element satisfies one of the following conditions of SC 2.5.2:

1. The down event is not used to operate the function. This is the single most preferable behavior for this rule whenever is possible.
2. There is a method made available to cancel or abort the action.
3. The up-event reverses any action taken by the down event.
4. The down event is strictly required and ESSENTIAL to the functionality of the code.

Note that the first satisfiable condition listed is the most commonly preferable technique to comply with SC 2.5.2.

Provide your review in a clear, concise manner, listing each issue separately with its corresponding explanation and correction.

Rules to follow:

- Find all violations of SC 2.5.2 'Pointer Cancellation' in the provided HTML and JS.
- Components do not inherently provide or supplement global functionalities. They are designed to operate within their defined scope, focusing on reusable UI components rather than global behaviors.
- `onclick`, `onmouseup`, `onpointerup`, and `onkeyup` handlers fire on the **up-event**, which already satisfies condition 1 (the down-event is not used to operate the function). Do NOT flag an element for 2.5.2 merely because it is interactive — only flag handlers bound to a **down-event** (`onpointerdown`, `onmousedown`, `ontouchstart`) that lack a cancel, abort, or reverse mechanism. An `<a>`, `<button>`, `<li>`, or `<div>` activated via `onclick` is compliant; move on.
- An anchor's `href` value is not within the scope of 2.5.2 — it does not determine the down/up-event behavior. In particular, `href="#"` paired with a click handler that calls `event.preventDefault()` performs no navigation or scroll, so it is not a pointer-cancellation issue. This is the canonical SLDS interactive-link pattern (e.g. `slds-path__link` with `role="option"`). Do not flag it. If you do recommend changing an anchor, never suggest `href="javascript:void(0)"` (see general rules).

- For each issue found, provide a separate, detailed report.
- Keep issues concise, avoid duplicated issues or unnecessary or non-applicable problems.
- Assume that any imported functionality works as expected and was already analyzed.
- Components do not supplement or provide global functionalities.
- Lightning base components (`lightning-input`, `lightning-combobox`, `lightning-textarea`, `lightning-icon`, etc.) provide their own accessible labeling, ARIA, and error handling in shadow DOM via their dedicated attributes (`label`, `alternative-text`, field-level validation). When such a component is given a `label` attribute it is already programmatically labeled — even with `variant="label-hidden"`, which hides the label visually but keeps it for assistive technology. Do **not** flag a sibling/wrapper `<label>` or `<span>` for a missing `for`/`id` when the actual control is a self-labeling Lightning component, and do not treat a visible heading as if it were the control's only label. This also covers navigation and icon base components (`lightning-vertical-navigation-item`, `lightning-vertical-navigation-item-icon`, `lightning-button-icon`, etc.): when a `label` (or `alternative-text`) attribute is supplied, the base component renders it as the visible link/control text **and** exposes it as the accessible name, and any `icon-name` is decorative — do not emit a 4.1.2 "verify the label is associated with the icon" warning, even a hedged one. The presence of the `label` attribute is the association.
- Resolve template bindings before judging them. A template expression like `{someValue}` refers to a property or getter on the component's controller (`.js`/`.ts`) — including `@api` properties and `get someValue()` getters — not to a module-level imported constant (which LWC templates cannot bind to). Check the controller for the binding's definition before concluding a value is undefined, empty, or missing. When reviewing a diff, verify which side is the corrected code; do not assume the change introduced the problem.
- Prefer a real `<button>` for actions; for a link, `href="#"` with `event.preventDefault()` (the canonical SLDS pattern). Don't recommend `href="javascript:void(0)"` as a first-line remediation — it's a no-op-anchor anti-pattern. It is acceptable only as a last resort when moving `<a>` → `<button>` is genuinely impossible, and even then only when paired with the full set of attributes that make the anchor behave as an accessible button (`role="button"`, keyboard activation, etc.) — `void(0)` on its own is an incomplete fix. Don't flag existing `javascript:void(0)` as a violation.
- ARIA attribute spelling depends on the element type. On a **plain HTML element** (`div`, `span`, `button`, `input`, `a`, `img`, `iframe`, …) the only valid spelling is the W3C form `aria-labelledby` / `aria-describedby`; the hyphen-split `aria-labelled-by` / `aria-described-by` there **is** a real bug — keep flagging it. But on an **LWC component tag** (`lightning-*` or a custom `ns-name` element), the hyphen-split form is the kebab-case binding of the component's `@api ariaLabelledBy` / `ariaDescribedBy` property (each capital letter maps to `-` + lowercase), and LWC reflects it to the spec-correct `aria-labelledby` in the rendered DOM. Do **not** flag `aria-labelled-by` on a component tag as a misspelling, and do not claim it "breaks the accessible name computation" — you cannot determine that from the attribute name alone, because both `aria-labelled-by` (via `@api` property kebab-casing) and `aria-labelledby` (via LWC's ARIA reflection) can wire to the same property depending on the component. Treat a hyphen-split ARIA attribute on a component tag as a valid binding, not a violation.
