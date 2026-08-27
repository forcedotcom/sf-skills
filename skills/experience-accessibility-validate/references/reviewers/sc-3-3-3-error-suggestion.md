## SC 3.3.3 - Error Suggestion (Level AA)

If an input error is automatically detected and suggestions for correction are known, then the suggestions are provided to the user, unless it would jeopardize the security or purpose of the content.

## SC: 3.3.3 - Error Suggestion

**What is a Sufficient Error Suggestion?**

A suggestion is sufficient if it clearly states the correction needed. You should not flag messages that are already clear just to make them more verbose. The goal is to ensure a corrective suggestion exists, not to rewrite it.

- **Sufficient Suggestion Examples (DO NOT FLAG these as violations):**

  - For an input field that requires only numbers, use a clear and direct error message. For example, "Please enter numbers only."
  - For a password confirmation that doesn't match, use a clear and direct error message: For example, "Passwords do not match."

- **Insufficient Suggestion Examples (These SHOULD BE FLAGGED):**
  - "Invalid input."
  - "Access Denied."
  - "Error."
  - "Please fix this field."

For each form field that can produce an input error, check the following:

- The form field provides a clear error message that indicates what went wrong and how it can be fixed, when an input error is detected.
- The error message includes a suggestion for correcting the error. Some examples include, requiring a specific format, requesting acceptable values, or defining a valid range of values.
- If the input requires a specific format (for example, a date or email format), the error message suggests that the user input their information using that format. The error message suggestion can be present either in input error messages or validation error messages.
- If the input requires a value from a limited set of values (for example, a drop-down menu) the error message suggests selecting from the available options.
- If the user must validate that they're above a certain age (for example, 18 years or older), the error message must explicitly state that requirement in the error message (for example, "You must be 18 or older to proceed.").
- If the input field has an error message, it must be programmatically associated with the field.
- If error messages are displayed at the top of a component without a clear and direct association to the fields that require a correction, then flag this as an accessibility improvement/violation against WCAG 3.3.1. Also, recommend moving the error messages to a location that directly associates the error to the input field that needs to be corrected.

Common violations to check:

- Missing error messages for input fields that can produce errors.
- Error messages that do not include suggestions for correction.
- Error messages that are unclear or do not guide the user on how to correct the error.
- Error messages that are not visually adjacent (exclude toast messages) to the input field(for example, error message at the top of the form), forcing users to scan the page to locate the field that needs correction.
- Error messages which includes suggestions but are not conveyed to assistive technology. For example, the error suggestion messages and the field are not programmatically associated using `aria-describedby`.

Special Rules:

- Error suggestions should be persistent enough for all users to perceive and understand without arbitrary time limits. The error message must not disappear after certain time limit and should be visible at all times.
- Toast notifications are designed to be accessible and the toast events are designed to follow accessibility guidelines.

**ABSOLUTE AND STRICT EXCLUSION RULES FOR SC 3.3.3 'Error Suggestion':**

- \*\*DO NOT flag that the field "cannot be empty" or that it needs a value for optional fields(not marked as required). The absence of a value is valid for an optional field.
- **DO NOT flag for using `aria-describedby` that references conditionally rendered error messages is valid and common. When the referenced element is not in the DOM, browsers and screen readers handle this gracefully.
  **DO NOT flag for components in the lightning namespace (prefixed with `lightning-`) if there is no form field validation or eror handling or programmatic association. They have built-in, accessible error handling and field validation that complies with WCAG standards.

Rules to follow:

- Find all violations of SC 3.3.3 'Error Suggestion' in the provided HTML and JS files (exclude CSS).
- Focus on form inputs that can produce input errors.
- If no changes or action are needed, then produce an empty list. Do not conclude 'no action is needed' or 'correctly implemented' if no violations found.
- Critically evaluate each field against the specific guidance above. Do not conclude 'no action is needed' or 'correctly implemented' if no violations found.
  - For each issue found, provide a separate, detailed report.
- Keep issues concise, avoid duplicated issues or unnecessary or non-applicable problems.
- Assume that any imported functionality works as expected and was already analyzed.
- Components do not supplement or provide global functionalities.
- Lightning base components (`lightning-input`, `lightning-combobox`, `lightning-textarea`, `lightning-icon`, etc.) provide their own accessible labeling, ARIA, and error handling in shadow DOM via their dedicated attributes (`label`, `alternative-text`, field-level validation). When such a component is given a `label` attribute it is already programmatically labeled — even with `variant="label-hidden"`, which hides the label visually but keeps it for assistive technology. Do **not** flag a sibling/wrapper `<label>` or `<span>` for a missing `for`/`id` when the actual control is a self-labeling Lightning component, and do not treat a visible heading as if it were the control's only label. This also covers navigation and icon base components (`lightning-vertical-navigation-item`, `lightning-vertical-navigation-item-icon`, `lightning-button-icon`, etc.): when a `label` (or `alternative-text`) attribute is supplied, the base component renders it as the visible link/control text **and** exposes it as the accessible name, and any `icon-name` is decorative — do not emit a 4.1.2 "verify the label is associated with the icon" warning, even a hedged one. The presence of the `label` attribute is the association.
- Resolve template bindings before judging them. A template expression like `{someValue}` refers to a property or getter on the component's controller (`.js`/`.ts`) — including `@api` properties and `get someValue()` getters — not to a module-level imported constant (which LWC templates cannot bind to). Check the controller for the binding's definition before concluding a value is undefined, empty, or missing. When reviewing a diff, verify which side is the corrected code; do not assume the change introduced the problem.
- Prefer a real `<button>` for actions; for a link, `href="#"` with `event.preventDefault()` (the canonical SLDS pattern). Don't recommend `href="javascript:void(0)"` as a first-line remediation — it's a no-op-anchor anti-pattern. It is acceptable only as a last resort when moving `<a>` → `<button>` is genuinely impossible, and even then only when paired with the full set of attributes that make the anchor behave as an accessible button (`role="button"`, keyboard activation, etc.) — `void(0)` on its own is an incomplete fix. Don't flag existing `javascript:void(0)` as a violation.
- ARIA attribute spelling depends on the element type. On a **plain HTML element** (`div`, `span`, `button`, `input`, `a`, `img`, `iframe`, …) the only valid spelling is the W3C form `aria-labelledby` / `aria-describedby`; the hyphen-split `aria-labelled-by` / `aria-described-by` there **is** a real bug — keep flagging it. But on an **LWC component tag** (`lightning-*` or a custom `ns-name` element), the hyphen-split form is the kebab-case binding of the component's `@api ariaLabelledBy` / `ariaDescribedBy` property (each capital letter maps to `-` + lowercase), and LWC reflects it to the spec-correct `aria-labelledby` in the rendered DOM. Do **not** flag `aria-labelled-by` on a component tag as a misspelling, and do not claim it "breaks the accessible name computation" — you cannot determine that from the attribute name alone, because both `aria-labelled-by` (via `@api` property kebab-casing) and `aria-labelledby` (via LWC's ARIA reflection) can wire to the same property depending on the component. Treat a hyphen-split ARIA attribute on a component tag as a valid binding, not a violation.
