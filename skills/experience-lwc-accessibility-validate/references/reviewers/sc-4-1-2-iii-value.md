## SC 4.1.2 - Name, Role, Value (Level A)

For all user interface components, the name and role can be programmatically determined; states, properties, and values that can be set by the user can be programmatically set; and notification of changes to these items is available to user agents, including assistive technologies.

## SC: 4.1.2 (iii) - Value Only

Analyze the files using following context:

_Goal_: People using assistive technology understand all components correctly

_What to do_: Review the provided code for accessibility issues, focusing specifically and only on the Value requirement of 4.1.2 S.C. to ensure components have a valid value set. There is one exception- for ID Reference/List attributes, check only value syntax, not whether referenced elements exist. Attribute value(s) that is set on HTML element is the value that the attribute gets after being parsed and computed according to it's specifications. It may differ from the value that is actually written in the HTML code due to trimming whitespace or non-digits characters, default value(s), or case-insensitivity

- Enumerated attributes take on a finite set of states, the attribute value is either the state of the attribute, or the keyword that maps to it; even for the default states.
  - The state for such an attribute is derived by combining the attribute's value, a set of keyword/state mappings given in the specification of each attribute, and two possible special states that can also be given in the specification of the attribute
    - These special states are the invalid value default and the missing value default
  - Note: Multiple keywords can map to the same state. The empty string can be a valid keyword. Note that the missing value default applies only when the attribute is missing, not when it is present with an empty string value
  - For reflection purposes, states which have any keywords mapping to them are said to have a canonical keyword
- For boolean attributes, the attribute value is true when the attribute is present and false otherwise
  - The presence of a boolean attribute on an element represents the true value, and the absence of the attribute represents the false value. If the attribute is present, its value must either be the empty string or a value that is an ASCII case-insensitive match for the attribute's canonical name, with no leading or trailing whitespace
  - Note: The values "true" and "false" are not allowed on boolean attributes. To represent a false value, the attribute has to be omitted altogether
- If the attribute is present, its value must either be the empty string or a value that is an ASCII case-insensitive match for the attribute's canonical name, with no leading or trailing whitespace
- For attributes whose value is used in a case-insensitive context, the attribute value is the lowercase version of the value written in the HTML code
- For attributes that accept numbers, the attribute value is the result of parsing the value written in the HTML code according to the rules for parsing this kind of number. Following are some forms of a number for which individual parsing rules are applied:
  - Signed integers
  - Non-negative integers
  - Floating-point numbers
    - The Infinity and Not-a-Number (NaN) values are not valid floating-point numbers
    - The valid floating-point number concept is typically only used to restrict what is allowed for authors, while the user agent requirements use the rules for parsing floating-point number values
  - Percentages and lengths
  - Nonzero percentages and lengths
  - Lists of floating-point numbers
  - Lists of dimensions
- For aria-\* attributes, the attribute value is computed as indicated by it's type in the WAI-ARIA specification and the HTML Accessibility API Mappings

_Rules to follow_:

- Require programmatically determinable ARIA state or property for all user interface components to have a valid value. This rule is applicable to any WAI-ARIA state or property that has a non-empty ("") attribute value specified on an HTML or SVG element and which is not programmatically hidden. Each target has an attribute value that is valid according to its WAI-ARIA value type specification.
  - An element is programmatically hidden if either it has a computed CSS property visibility whose value is not 'visible'; or at least one of the following is true for any of its inclusive ancestors in DOM tree:
    - has computed CSS property of display of 'none'; or
    - has `aria-hidden` attribute set to 'true'
    - note: being programmatically hidden can change as users interact with the user interface component, while being marked decorative should stay the same through all states.
  - Following are some WAI-ARIA attributes types that are subject to consideration:
    - `aria-activedescendant`
    - `aria-atomic`
    - `aria-autocomplete`
    - `aria-busy`
    - `aria-checked`
    - `aria-colcount`
    - `aria-colindex`
    - `aria-colspan`
    - `aria-controls`
    - `aria-current`
    - `aria-describedby`
    - `aria-disabled`
    - `aria-errormessage`
    - `aria-expanded`
    - `aria-flowto`
    - `aria-haspopup`
    - `aria-hidden`
    - `aria-invalid`
    - `aria-keyshortcuts`
    - `aria-label`
    - `aria-labelledby`
    - `aria-level`
    - `aria-live`
    - `aria-modal`
    - `aria-multiline`
    - `aria-multiselectable`
    - `aria-orientation`
    - `aria-owns`
    - `aria-placeholder`
    - `aria-posinset`
    - `aria-pressed`
    - `aria-readonly`
    - `aria-relevant`
    - `aria-required`
    - `aria-roledescription`
    - `aria-rowcount`
    - `aria-rowindex`
    - `aria-rowspan`
    - `aria-selected`
    - `aria-setsize`
    - `aria-sort`
    - `aria-valuemax`
    - `aria-valuemin`
    - `aria-valuenow`
    - `aria-valuetext`
- For each component that violates #1 rule, compile a concise list of issues for user to review.

- For each issue found, provide a separate, detailed report.
- Keep issues concise, avoid duplicated issues or unnecessary or non-applicable problems.
- Assume that any imported functionality works as expected and was already analyzed.
- Components do not supplement or provide global functionalities.
- Lightning base components (`lightning-input`, `lightning-combobox`, `lightning-textarea`, `lightning-icon`, etc.) provide their own accessible labeling, ARIA, and error handling in shadow DOM via their dedicated attributes (`label`, `alternative-text`, field-level validation). When such a component is given a `label` attribute it is already programmatically labeled — even with `variant="label-hidden"`, which hides the label visually but keeps it for assistive technology. Do **not** flag a sibling/wrapper `<label>` or `<span>` for a missing `for`/`id` when the actual control is a self-labeling Lightning component, and do not treat a visible heading as if it were the control's only label. This also covers navigation and icon base components (`lightning-vertical-navigation-item`, `lightning-vertical-navigation-item-icon`, `lightning-button-icon`, etc.): when a `label` (or `alternative-text`) attribute is supplied, the base component renders it as the visible link/control text **and** exposes it as the accessible name, and any `icon-name` is decorative — do not emit a 4.1.2 "verify the label is associated with the icon" warning, even a hedged one. The presence of the `label` attribute is the association.
- Resolve template bindings before judging them. A template expression like `{someValue}` refers to a property or getter on the component's controller (`.js`/`.ts`) — including `@api` properties and `get someValue()` getters — not to a module-level imported constant (which LWC templates cannot bind to). Check the controller for the binding's definition before concluding a value is undefined, empty, or missing. When reviewing a diff, verify which side is the corrected code; do not assume the change introduced the problem.
- Prefer a real `<button>` for actions; for a link, `href="#"` with `event.preventDefault()` (the canonical SLDS pattern). Don't recommend `href="javascript:void(0)"` as a first-line remediation — it's a no-op-anchor anti-pattern. It is acceptable only as a last resort when moving `<a>` → `<button>` is genuinely impossible, and even then only when paired with the full set of attributes that make the anchor behave as an accessible button (`role="button"`, keyboard activation, etc.) — `void(0)` on its own is an incomplete fix. Don't flag existing `javascript:void(0)` as a violation.
- ARIA attribute spelling depends on the element type. On a **plain HTML element** (`div`, `span`, `button`, `input`, `a`, `img`, `iframe`, …) the only valid spelling is the W3C form `aria-labelledby` / `aria-describedby`; the hyphen-split `aria-labelled-by` / `aria-described-by` there **is** a real bug — keep flagging it. But on an **LWC component tag** (`lightning-*` or a custom `ns-name` element), the hyphen-split form is the kebab-case binding of the component's `@api ariaLabelledBy` / `ariaDescribedBy` property (each capital letter maps to `-` + lowercase), and LWC reflects it to the spec-correct `aria-labelledby` in the rendered DOM. Do **not** flag `aria-labelled-by` on a component tag as a misspelling, and do not claim it "breaks the accessible name computation" — you cannot determine that from the attribute name alone, because both `aria-labelled-by` (via `@api` property kebab-casing) and `aria-labelledby` (via LWC's ARIA reflection) can wire to the same property depending on the component. Treat a hyphen-split ARIA attribute on a component tag as a valid binding, not a violation.
