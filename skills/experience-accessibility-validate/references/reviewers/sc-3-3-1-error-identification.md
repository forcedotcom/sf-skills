## SC 3.3.1 - Error Identification (Level A)

If an input error is automatically detected, the item that is in error is identified and the error is described to the user in text.

## SC: 3.3.1 - Error Identification

Analyze the given file using the following framework:

Review the provided HTML and JS files for accessibility violations per WCAG 2.2 SC 3.3.1, 'Error Identification'. Violations occur when the component contains an input field that has an error, and the error is conveyed or presented to the user with one of the approaches listed below.

Analyze all of the elements in the HTML for which can be the site of an 'input error'. For any such element, you must make sure that the errors are conveyed to the user via a textual indicator. Non-textual methods of conveying the error, such as colors or images are prohibited when not accompanied by a textual indicator.

Elements that can cause an input error, which can be either of the following:

- information that is required by the web page, but has been omitted by the user.
- information that is provided by the user but that falls outside the required data format or allowed values.

You don't need to consider the following scenarios:

- Form/field states before validation and error detection: Anything related to the state of the UI before validation occurs should be ignored.
- This includes required state, disabled state, any WAI-ARIA state.

Always cross-check the HTML and JS files to ensure that form submission or input submission logic correctly handles the error path. Make sure the error path is textually identifiable.
If a submission handling logic and error states isn't reflected textually in the HTML template, then you have a violation.

Use the following scenarios as a guide to determine if a violation has occurred. Flag all violations that occur:

- Error state is ignored after validation. This is when validation occurs but the error path is not handled
- Error is conveyed without a text-based error
- Error state is not surfaced to the end user (console.log, etc.)
- Error state is indicated textually, but the indicator is not conveyed to assistive technology
  - This occurs when `aria-live` announcements or `role="alert"` are missing
- Form state is altered or reset after an invalid input is detected. This causes the user to lose context about the field or fields that caused the error. Make sure to check the logic of the form reset and make sure that resets only happens after the form submission is successful. If a form is reset within the control flow of an error case, then this is a violation.

Situations that may seem like violations, but are not and should not be flagged, examples below:

- **The error is not the result of user input.** SC 3.3.1 applies only to _input errors_ — information the user supplied (or omitted) that the page cannot accept. It does **not** apply to background/system errors that no user action triggered: init-time capability or permission probes, CRUD/FLS access checks, network or service-availability failures, data-load errors, etc. If no user-supplied input produced the error, do not flag it under 3.3.1 (a silent background failure may be a concern under a different criterion or none, but it is out of scope here).
- An optional field (i.e., not marked with `required` or `aria-required="true"`) is left empty by the user. This is expected behavior. DO NOT flag an empty optional field as a violation.
- A form state is altered or reset, but the form submission was **successful**. This is perfectly acceptable. Make sure to check the logic of the function before flagging a violation for form state mutation
- Error message isn't descriptive or isn't announced, but individual fields convey their own state (e.g. `aria-invalid="true"` is set on all errored fields). This is acceptable and not a violation
- Errors that aren't announced, but are visually and programmatically tied to a field (e.g. message is positioned beneath the field and use `aria-describedby`). This is acceptable.

- DO NOT flag for lightning base components if there is no form field validation or eror handling. They have built-in, accessible error handling and field validation that complies with WCAG standards.
  For conditional templates, also check the contents for the behavior you're looking for. Sometimes the `<template>` content contains the correct behavior so that an error only occurs in the conditional state. In these cases, the code is compliant and **no** violation should be flagged.

When a global error message is used, check that the following are true. Flag a violation for any of the following isn't true:

- The global message describes each field that's in an error state and the user can identify the field where the error occurred.
- The global message is announced via assistive technology when the error occurs. Assistive technology announcements can include, `aria-live` or `role="alert"` attributes on the error element or its parent.
  **Note: Generic error messages like "Please correct" are violations unless the field with the error explicitly marks the invalid state. Review all generic errors to ensure that they meet this criteria, or flag this as a violation.**

If the global error message does not satisfy these criteria, then you must flag as a violation

Be sure to ALWAYS track these error messages down to the source of the literal message content. This may cross HTML in to JS, and even across multiple JS references. It's important that you ensure that the error being surfaced is descriptive enough for the situation it's used in.

In order to fix an identified violation, use the following sufficient techniques for the two relevant scenarios in order to decide upon an appropriate fix:

- Providing text descriptions to identify required fields that were not completed:
- Two approaches exist:
  - Client-side: Show alert dialog identifying missing fields
  - Server-side: Re-display form with text descriptions for missing fields
- Identifying a required field with the `aria-required` property:
  - The objective of this technique is to provide programmatic indication that a form field (which shown through presentation to be required) is mandatory for successful submission of a form.
  - The WAI-ARIA `aria-required` property indicates that user input is required before submission. It can take values true or false. E.g., if a user must fill in a field, then `aria-required="true"`.
- Using `aria-invalid` to indicate an error field:
  - It's preferable to associate error messages with the failed field, but it may not always be feasible, so authors may programmatically set `aria-invalid` to 'true' on fields that have failed validation. This is interpretable mainly by assistive technologies (like screen readers / screen magnifiers) employed by users who are vision impaired.
- Using ARIA `role=alert` or live regions to identify errors:
  - The purpose of this technique is to notify Assistive Technologies (AT) when an input error occurs. The `aria-live` or `role="alert"` (which are interchangeable) attribute makes it possible for an AT (such as a screen reader) to be notified when error messages are injected into a Live Region container. The content within the `aria-live` region is automatically read by the AT, without the AT having to focus on the place where the text is displayed.
- Providing a text description when the user provides information that is not in the list of allowed values:
  - When users enter input that is validated, and errors are detected, the nature of the error needs to be described to the user in manner they can access. This can be with an alert dialog that describes fields with errors, or it could also be, when validation is done by the server, to return the form (with form state preserved) and a text description that indicates that there was a validation problem, describes the problem, and provides ways to locate the problematic field(s).

It is important to find all violations of this rule in order for all users of the component to be able to properly interact with it, and be notified of any issues in detail such that they can take the required actions to resolve them.

Rules to follow:

- Find all violations of SC 3.3.1 in the provided HTML and JS files.
  - For each issue found, provide a separate, detailed report.
- Keep issues concise, avoid duplicated issues or unnecessary or non-applicable problems.
- Assume that any imported functionality works as expected and was already analyzed.
- Components do not supplement or provide global functionalities.
- Lightning base components (`lightning-input`, `lightning-combobox`, `lightning-textarea`, `lightning-icon`, etc.) provide their own accessible labeling, ARIA, and error handling in shadow DOM via their dedicated attributes (`label`, `alternative-text`, field-level validation). When such a component is given a `label` attribute it is already programmatically labeled — even with `variant="label-hidden"`, which hides the label visually but keeps it for assistive technology. Do **not** flag a sibling/wrapper `<label>` or `<span>` for a missing `for`/`id` when the actual control is a self-labeling Lightning component, and do not treat a visible heading as if it were the control's only label. This also covers navigation and icon base components (`lightning-vertical-navigation-item`, `lightning-vertical-navigation-item-icon`, `lightning-button-icon`, etc.): when a `label` (or `alternative-text`) attribute is supplied, the base component renders it as the visible link/control text **and** exposes it as the accessible name, and any `icon-name` is decorative — do not emit a 4.1.2 "verify the label is associated with the icon" warning, even a hedged one. The presence of the `label` attribute is the association.
- Resolve template bindings before judging them. A template expression like `{someValue}` refers to a property or getter on the component's controller (`.js`/`.ts`) — including `@api` properties and `get someValue()` getters — not to a module-level imported constant (which LWC templates cannot bind to). Check the controller for the binding's definition before concluding a value is undefined, empty, or missing. When reviewing a diff, verify which side is the corrected code; do not assume the change introduced the problem.
- Prefer a real `<button>` for actions; for a link, `href="#"` with `event.preventDefault()` (the canonical SLDS pattern). Don't recommend `href="javascript:void(0)"` as a first-line remediation — it's a no-op-anchor anti-pattern. It is acceptable only as a last resort when moving `<a>` → `<button>` is genuinely impossible, and even then only when paired with the full set of attributes that make the anchor behave as an accessible button (`role="button"`, keyboard activation, etc.) — `void(0)` on its own is an incomplete fix. Don't flag existing `javascript:void(0)` as a violation.
- ARIA attribute spelling depends on the element type. On a **plain HTML element** (`div`, `span`, `button`, `input`, `a`, `img`, `iframe`, …) the only valid spelling is the W3C form `aria-labelledby` / `aria-describedby`; the hyphen-split `aria-labelled-by` / `aria-described-by` there **is** a real bug — keep flagging it. But on an **LWC component tag** (`lightning-*` or a custom `ns-name` element), the hyphen-split form is the kebab-case binding of the component's `@api ariaLabelledBy` / `ariaDescribedBy` property (each capital letter maps to `-` + lowercase), and LWC reflects it to the spec-correct `aria-labelledby` in the rendered DOM. Do **not** flag `aria-labelled-by` on a component tag as a misspelling, and do not claim it "breaks the accessible name computation" — you cannot determine that from the attribute name alone, because both `aria-labelled-by` (via `@api` property kebab-casing) and `aria-labelledby` (via LWC's ARIA reflection) can wire to the same property depending on the component. Treat a hyphen-split ARIA attribute on a component tag as a valid binding, not a violation.
