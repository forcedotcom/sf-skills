## SC 3.2.2 - On Input (Level A)

Changing the setting of any user interface component does not automatically cause a change of context unless the user has been advised of the behavior before using the component.

## SC: 3.2.2 - On Input (Level A)

Analyze the files using following context:

_Goal_: Content can be operated predictably, users (including users with disabilities) will need to be forewarned if a context change is expected based on their inputs.

_What to do_ : Review provided HTML and JS code for accessibility violations per WCAG 3.2.2 'On Input'. Ensure that content in the user interface component behaves predictably, including actions such as checking a checkbox, entering text, changing a selection on a dropdown. Changes in context can confuse users who do not perceive the change or are easily distracted by it. Clicking on links or buttons is considered as activating a control, and not changing the setting of that control.

Unexpected changes in context can be disorienting to users with disabilities, visual or cognitive limitations that they are unable to use the content. Individuals who cannot detect changes of context are less likely to become disoriented while navigating a site for example. Some people with low-vision, with reading and intellectual disabilities, and others who have difficulty interpreting visual cues may benefit from providing additional cues in order to detect such changes of context.

Some examples:

- A web-based calendaring form includes standard fields for subject, time, and location, along with radio buttons to select the entry type: meeting, appointment, or reminder etc. A user selecting "meeting" can add fields for participants, while selecting "reminder" displays different fields. The form's overall structure however remains consistent despite these changes.
- For phone numbers in US, the form can have separate fields for the area code, prefix and number. As the user completes one field, the focus automatically moves to the next field. This behavior is explained at the form's start.

Following are some sufficient techniques that WCAG working group deems sufficient to be used to meet this success criterion:

- G80: Providing a submit button to make it easier for users to initiate a change of context.
  - H32: Find all forms, and for each form check that it has a submit button.
  - H84: For each 'select' element/button combination, check that focus (including keyboard focus) on an option in the 'select' element does not result in any actions. Also check that selecting button performs action associated with current 'select' element.
- G13: Providing a description on what will happen before a change to a form control that causes a context change. Locate the content where change of the setting of a form control will result in a change of context, and check to see if there is an explanation or description of what will happen when the control is changed, is available prior to the control activations.
- SCR19: Using 'onchange' event on a select element without causing a change of context. This is achieved by following algorithm:
  1. Navigate to trigger select element and change the value of the select.
  2. Navigate to select element that is updated by trigger, check that matching option values are displayed in the other select element.
  3. Navigate to the trigger select element, navigate through the options but do not select or change the value. Check that the matching option values are still displayed in associated select element.

Note: A change of content is not always considered to be a change of context.

Note: G201, while beneficial for user experience, is considered an advisory technique for this success criterion and not sufficient on its own. G201 technique is as follows:

- For each link that opens automatically in a new window or tab, use the following algorithm:
  1. check if there is a warning spoken in assistive technology that this link opens to a new window
  2. check that there is a visual warning in text that this link opens to a new window

_Rules to follow_ :

- Require that content can be operated predictably. Users must be forewarned if a change of context is expected based on their inputs, per this WCAG 3.2.2 'On Input' success criterion.
- For each component that violates #1, compile a concise list of issues for user to review, along with an action report on sufficient technique that can help resolve violation for component under review.

- For each issue found, provide a separate, detailed report.
- Keep issues concise, avoid duplicated issues or unnecessary or non-applicable problems.
- Assume that any imported functionality works as expected and was already analyzed.
- Components do not supplement or provide global functionalities.
- Lightning base components (`lightning-input`, `lightning-combobox`, `lightning-textarea`, `lightning-icon`, etc.) provide their own accessible labeling, ARIA, and error handling in shadow DOM via their dedicated attributes (`label`, `alternative-text`, field-level validation). When such a component is given a `label` attribute it is already programmatically labeled — even with `variant="label-hidden"`, which hides the label visually but keeps it for assistive technology. Do **not** flag a sibling/wrapper `<label>` or `<span>` for a missing `for`/`id` when the actual control is a self-labeling Lightning component, and do not treat a visible heading as if it were the control's only label. This also covers navigation and icon base components (`lightning-vertical-navigation-item`, `lightning-vertical-navigation-item-icon`, `lightning-button-icon`, etc.): when a `label` (or `alternative-text`) attribute is supplied, the base component renders it as the visible link/control text **and** exposes it as the accessible name, and any `icon-name` is decorative — do not emit a 4.1.2 "verify the label is associated with the icon" warning, even a hedged one. The presence of the `label` attribute is the association.
- Resolve template bindings before judging them. A template expression like `{someValue}` refers to a property or getter on the component's controller (`.js`/`.ts`) — including `@api` properties and `get someValue()` getters — not to a module-level imported constant (which LWC templates cannot bind to). Check the controller for the binding's definition before concluding a value is undefined, empty, or missing. When reviewing a diff, verify which side is the corrected code; do not assume the change introduced the problem.
- Prefer a real `<button>` for actions; for a link, `href="#"` with `event.preventDefault()` (the canonical SLDS pattern). Don't recommend `href="javascript:void(0)"` as a first-line remediation — it's a no-op-anchor anti-pattern. It is acceptable only as a last resort when moving `<a>` → `<button>` is genuinely impossible, and even then only when paired with the full set of attributes that make the anchor behave as an accessible button (`role="button"`, keyboard activation, etc.) — `void(0)` on its own is an incomplete fix. Don't flag existing `javascript:void(0)` as a violation.
- ARIA attribute spelling depends on the element type. On a **plain HTML element** (`div`, `span`, `button`, `input`, `a`, `img`, `iframe`, …) the only valid spelling is the W3C form `aria-labelledby` / `aria-describedby`; the hyphen-split `aria-labelled-by` / `aria-described-by` there **is** a real bug — keep flagging it. But on an **LWC component tag** (`lightning-*` or a custom `ns-name` element), the hyphen-split form is the kebab-case binding of the component's `@api ariaLabelledBy` / `ariaDescribedBy` property (each capital letter maps to `-` + lowercase), and LWC reflects it to the spec-correct `aria-labelledby` in the rendered DOM. Do **not** flag `aria-labelled-by` on a component tag as a misspelling, and do not claim it "breaks the accessible name computation" — you cannot determine that from the attribute name alone, because both `aria-labelled-by` (via `@api` property kebab-casing) and `aria-labelledby` (via LWC's ARIA reflection) can wire to the same property depending on the component. Treat a hyphen-split ARIA attribute on a component tag as a valid binding, not a violation.
