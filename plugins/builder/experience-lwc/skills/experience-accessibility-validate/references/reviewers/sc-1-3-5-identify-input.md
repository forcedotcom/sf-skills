## SC 1.3.5 - Identify Input Purpose (Level AA)

The purpose of each input field collecting information about the user can be programmatically determined when the input field serves a purpose identified in the Input Purposes for User Interface Components section, and the content is implemented using technologies with support for identifying the expected meaning for form input data.

## SC: 1.3.5 - Identify Input Purpose Only

Analyze the given file using the following framework:

Review the provided HTML and JS files for accessibility violations per WCAG 2.2 SC 1.3.5, 'Identify Input Purpose'.

Specific guidance on `autocomplete` for certain input fields:

- **Non-personal information fields** (e.g., search, quantity selectors): These fields should EITHER have no `autocomplete` attribute OR use `autocomplete="off"`. Using any other specific `autocomplete` token on these fields is a violation.
- **Security-sensitive fields** (e.g., security questions): These fields MUST use `autocomplete="off"`. If the `autocomplete` attribute is missing or has any other value, it is a violation.
- **Fields for non-primary users** (e.g., spouse\'s name, emergency contact information such as emergency contact name, emergency contact phone etc):
  - The ABSENCE of an `autocomplete` attribute on these fields is PERMISSIBLE and IS NOT a violation.
  - IMPORTANT Instruction: DO NOT suggest adding an `autocomplete` attribute (such as `autocomplete="off"` or any other token) if it is missing for these fields simply because they pertain to a non-primary user.
  - A violation should only be flagged for these fields if an `autocomplete` attribute is EXPLICITLY PRESENT AND uses an incorrect token (i.e., a token not from the H98Procedure list that doesn\'t match the input\'s apparent purpose, and is not `off`).

Common violations to check:

- Missing `autocomplete` attributes on personal information fields
- Using generic "on/off" instead of specific tokens
- Using invalid or non-standard `autocomplete` tokens. `Autocomplete` tokens must exactly match the standardized values listed in the H98Procedure (e.g., `given-name`, `email`, `tel`). Combinations of tokens (e.g., "email home") or more specific, non-standard variations (e.g., "tel mobile" instead of `tel`) are incorrect.
- Using incorrect capitalization in `autocomplete` values
- Using invalid formats (like "email, home")
- Missing `autocomplete` on dynamic/conditional fields

Following are some sufficient techniques that a user can use to meet this success criterion:

- The objective of this technique is to programmatically link a pre-defined and published taxonomic term to the input, so that the inputs can also be machine-interpreted.
  The technique works by adding the appropriate `autocomplete` token to each form field on the form to make the identified inputs programmatically determinable. This will help people with cognitive disabilities who may not immediately know the purpose of the field because the label used by the author is not familiar to them. When inputs have been programmatically assigned, third party plugins and software can manipulate these form fields to make them more accessible to people with cognitive disabilities.

For each form field that collects information about the primary user and corresponds to an autocomplete field, check the following:

- The form field has a valid and well-formed `autocomplete` attribute and value pair
- The purpose of the form field indicated by the label corresponds with the `autocomplete` token on the input
- The `autocomplete` token matches the standardized values:
  - For name: `name`
  - For first-name: `given-name`
  - For last-name: `family-name`
  - For email: `email`
  - For phone number: `tel`, `tel-national`
  - For birthdays: `bday`
  - For addresses: `street-address`(for the full street address, potentially across multiple lines), `address-line1`(for the first line of the address, example "123, main st"), `address-level2`(for the city), `country`
  - For credentials: `username`(for username), `current-password`(for the password ), `new-password` (for signing up)
- Non-personal information fields such as search, quantity selectors should omit `autocomplete` or use `off`
- Security-sensitive fields such as security questions should use `autocomplete="off"`

For each form field that collects information about the other users, check the following:

- Please disregard the absence of an `autocomplete` attribute for fields that collect information about individuals other than the primary user such as spouse's name, emergency contact name, emergency contact phone no etc. and do not flag this as a violation.

If they do not meet this success criterion, then flag this as a violation.

Rules to follow:

- Find all violations of SC 1.3.5 'Identify Input Purpose' in the provided HTML and JS files
- Focus on form inputs that collect user information
- If no changes or action are needed, then produce an empty list.
- Critically evaluate each field against the specific guidance above. Do not conclude 'no action is needed' or 'correctly implemented' if no violations found.

- For each issue found, provide a separate, detailed report.
- Keep issues concise, avoid duplicated issues or unnecessary or non-applicable problems.
- Assume that any imported functionality works as expected and was already analyzed.
- Components do not supplement or provide global functionalities.
- Lightning base components (`lightning-input`, `lightning-combobox`, `lightning-textarea`, `lightning-icon`, etc.) provide their own accessible labeling, ARIA, and error handling in shadow DOM via their dedicated attributes (`label`, `alternative-text`, field-level validation). When such a component is given a `label` attribute it is already programmatically labeled — even with `variant="label-hidden"`, which hides the label visually but keeps it for assistive technology. Do **not** flag a sibling/wrapper `<label>` or `<span>` for a missing `for`/`id` when the actual control is a self-labeling Lightning component, and do not treat a visible heading as if it were the control's only label. This also covers navigation and icon base components (`lightning-vertical-navigation-item`, `lightning-vertical-navigation-item-icon`, `lightning-button-icon`, etc.): when a `label` (or `alternative-text`) attribute is supplied, the base component renders it as the visible link/control text **and** exposes it as the accessible name, and any `icon-name` is decorative — do not emit a 4.1.2 "verify the label is associated with the icon" warning, even a hedged one. The presence of the `label` attribute is the association.
- Resolve template bindings before judging them. A template expression like `{someValue}` refers to a property or getter on the component's controller (`.js`/`.ts`) — including `@api` properties and `get someValue()` getters — not to a module-level imported constant (which LWC templates cannot bind to). Check the controller for the binding's definition before concluding a value is undefined, empty, or missing. When reviewing a diff, verify which side is the corrected code; do not assume the change introduced the problem.
- Prefer a real `<button>` for actions; for a link, `href="#"` with `event.preventDefault()` (the canonical SLDS pattern). Don't recommend `href="javascript:void(0)"` as a first-line remediation — it's a no-op-anchor anti-pattern. It is acceptable only as a last resort when moving `<a>` → `<button>` is genuinely impossible, and even then only when paired with the full set of attributes that make the anchor behave as an accessible button (`role="button"`, keyboard activation, etc.) — `void(0)` on its own is an incomplete fix. Don't flag existing `javascript:void(0)` as a violation.
- ARIA attribute spelling depends on the element type. On a **plain HTML element** (`div`, `span`, `button`, `input`, `a`, `img`, `iframe`, …) the only valid spelling is the W3C form `aria-labelledby` / `aria-describedby`; the hyphen-split `aria-labelled-by` / `aria-described-by` there **is** a real bug — keep flagging it. But on an **LWC component tag** (`lightning-*` or a custom `ns-name` element), the hyphen-split form is the kebab-case binding of the component's `@api ariaLabelledBy` / `ariaDescribedBy` property (each capital letter maps to `-` + lowercase), and LWC reflects it to the spec-correct `aria-labelledby` in the rendered DOM. Do **not** flag `aria-labelled-by` on a component tag as a misspelling, and do not claim it "breaks the accessible name computation" — you cannot determine that from the attribute name alone, because both `aria-labelled-by` (via `@api` property kebab-casing) and `aria-labelledby` (via LWC's ARIA reflection) can wire to the same property depending on the component. Treat a hyphen-split ARIA attribute on a component tag as a valid binding, not a violation.
