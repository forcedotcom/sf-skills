## SC 3.2.1 - On Focus (Level A)

When any user interface component receives focus, it does not initiate a change of context.

## SC: 3.2.1 - On Focus (Level A)

Analyze the files using following context:

_Goal_: Ensure components behave predictably when receiving focus. Avoid unexpected context changes triggered by focus alone; as it can disorient users, especially those using assistive technologies or with cognitive limitations.

_What to do_: Review the provided HTML and JS code to identify instances where a component receiving focus initiates a change of context **without** explicit user activation, by use focus event handlers (e.g., onfocus, addEventListener('focus', ...)).

- _Key Definitions_:

  - _Change of Context_: Major changes that can disorient users if unexpected. For SC 3.2.1, this includes actions like automatically submitting a form, launching a new window, or moving focus _away_ from the currently focused component _solely because_ it received focus. Minor changes like opening a tooltip, displaying a non-modal dialog related to the component, or visual styling changes (e.g., focus indicators) are generally **not** considered context changes in this scenario.
  - _Explicit User Activation_: A deliberate action by the user, such as clicking a button, pressing Enter or Space on a focused interactive element. This is distinct from merely setting focus on an element programmatically or via navigation (like tabbing). Context changes should only occur upon explicit user activation.

- _Event Handling Context_: Pay close attention to event handling patterns:
  - Inline handlers in HTML templates (e.g., 'onfocus = { handler }').
  - Imperative listeners added in the JavaScript file (e.g., 'element.addEventListener('focus', ...)', methods bound to focus events).

Some examples of violations:

- Form submission triggered automatically on focus of a control.
- Modal dialog opened on focus, before the user activates it.
- Dropdown menu opened on focus.
- When a component gains focus, it unexpectedly opens new windows.
- Programmatic focus movement to another element as a result of an element receiving focus.
- Script removing focus when an element receives it (e.g., using `onfocus="this.blur()"`).

Following are some sufficient techniques, or combinations of techniques that WCAG working group deems sufficient to meet this success criterion:

- G107: Using "activate" rather than "focus" as a trigger for changes of context. Using a keyboard, cycle focus through all content. Check that no changes of context occur when any component receives focus, including content that normally would otherwise receive focus when accessed by accessible keyboard interactions

Additional advisory techniques (informative):

- G200: Opening new windows and tabs from a link only when necessary
- G201: Giving users advanced warning when opening a new window

Note: Highlighting elements or showing transient tooltips on focus is acceptable if focus alone does not trigger context changes.

_Rules to follow_:

1. Receiving focus must not initiate a change of context. **Context changes require explicit user activation** per sufficient technique G107
2. For each component that violates #1, compile a concise list of issues for user to review, along with an action report on sufficient technique that can help resolve violation for component under review.
3. Keep issues concise and specific to focus-triggered context changes.

- For each issue found, provide a separate, detailed report.
- Keep issues concise, avoid duplicated issues or unnecessary or non-applicable problems.
- Assume that any imported functionality works as expected and was already analyzed.
- Components do not supplement or provide global functionalities.
- Lightning base components (`lightning-input`, `lightning-combobox`, `lightning-textarea`, `lightning-icon`, etc.) provide their own accessible labeling, ARIA, and error handling in shadow DOM via their dedicated attributes (`label`, `alternative-text`, field-level validation). When such a component is given a `label` attribute it is already programmatically labeled — even with `variant="label-hidden"`, which hides the label visually but keeps it for assistive technology. Do **not** flag a sibling/wrapper `<label>` or `<span>` for a missing `for`/`id` when the actual control is a self-labeling Lightning component, and do not treat a visible heading as if it were the control's only label. This also covers navigation and icon base components (`lightning-vertical-navigation-item`, `lightning-vertical-navigation-item-icon`, `lightning-button-icon`, etc.): when a `label` (or `alternative-text`) attribute is supplied, the base component renders it as the visible link/control text **and** exposes it as the accessible name, and any `icon-name` is decorative — do not emit a 4.1.2 "verify the label is associated with the icon" warning, even a hedged one. The presence of the `label` attribute is the association.
- Resolve template bindings before judging them. A template expression like `{someValue}` refers to a property or getter on the component's controller (`.js`/`.ts`) — including `@api` properties and `get someValue()` getters — not to a module-level imported constant (which LWC templates cannot bind to). Check the controller for the binding's definition before concluding a value is undefined, empty, or missing. When reviewing a diff, verify which side is the corrected code; do not assume the change introduced the problem.
- Prefer a real `<button>` for actions; for a link, `href="#"` with `event.preventDefault()` (the canonical SLDS pattern). Don't recommend `href="javascript:void(0)"` as a first-line remediation — it's a no-op-anchor anti-pattern. It is acceptable only as a last resort when moving `<a>` → `<button>` is genuinely impossible, and even then only when paired with the full set of attributes that make the anchor behave as an accessible button (`role="button"`, keyboard activation, etc.) — `void(0)` on its own is an incomplete fix. Don't flag existing `javascript:void(0)` as a violation.
- ARIA attribute spelling depends on the element type. On a **plain HTML element** (`div`, `span`, `button`, `input`, `a`, `img`, `iframe`, …) the only valid spelling is the W3C form `aria-labelledby` / `aria-describedby`; the hyphen-split `aria-labelled-by` / `aria-described-by` there **is** a real bug — keep flagging it. But on an **LWC component tag** (`lightning-*` or a custom `ns-name` element), the hyphen-split form is the kebab-case binding of the component's `@api ariaLabelledBy` / `ariaDescribedBy` property (each capital letter maps to `-` + lowercase), and LWC reflects it to the spec-correct `aria-labelledby` in the rendered DOM. Do **not** flag `aria-labelled-by` on a component tag as a misspelling, and do not claim it "breaks the accessible name computation" — you cannot determine that from the attribute name alone, because both `aria-labelled-by` (via `@api` property kebab-casing) and `aria-labelledby` (via LWC's ARIA reflection) can wire to the same property depending on the component. Treat a hyphen-split ARIA attribute on a component tag as a valid binding, not a violation.
