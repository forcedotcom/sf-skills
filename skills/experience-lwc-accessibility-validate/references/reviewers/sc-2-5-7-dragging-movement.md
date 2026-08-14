## SC 2.5.7 - Dragging Movements (Level AA)

All functionality that uses a dragging movement for operation can be achieved by a single pointer without dragging, unless dragging is essential or the functionality is determined by the user agent.

## SC: 2.5.7 - Dragging Movements (Level AA)

Analyze the files using following context:

_Goal_: Don't rely on dragging for a user action. A simple pointer alternative should be provided for actions that involves dragging operation, unless dragging is essential or the functionality is determined by user agent. This requirement applies to web content that interprets pointer actions.

_What to do_: Review the provided code for single pointer mode of operation for every dragging movement, without needing to drag elements. Not all users are capable of dragging actions while others use some alternative input devices which makes the dragging actions difficult. The 2.5.7 SC requirement is separate from keyboard accessibility. Keyboard specific actions like tabbing or arrow keys may not be available when encountering a drag-and-drop control. Providing text input can be an acceptable single-pointer alternative to a dragging movement action.

- Following are some discrete actions that are performed to establish a dragging movement:
  - tap or click to establish start position, then ...
  - press and hold that contact while ...
  - reposition the pointer before ...
  - release the pointer at end position
- Achieving keyboard equivalence (SC 2.1.1 and SC 2.1.3) for any dragging operation does not automatically meets 2.5.7 SC requirement and each requirement must be assessed independently.
- 2.5.7 SC applies to dragging operations, as opposed to pointer gestures which is covered under a separate SC 2.5.1. Only start and end point of movement matters and not the path itself.

Alternative for dragging movement on the same page can be executed with an equivalent option that allows for single pointer access without needing drag operation. It does not have to be the same component as long as the functionality is same. One example of this would be a color picker wheel, where a color can be changed by dragging the indicator. In addition, there could be text fields that allow the user to input a numerical color value without needing a drag movement.

Some more examples of single pointer alternatives are:

- A map allows users to drag the map view, while also providing up/down/left/right controls to move the view.
- A list of elements, alongside the ability to drag, also provides controls to move an element up/down by simply clicking on controls.
- A taskboard that allows users to drag-and-drop between different columns, also provides a pop-menu to move selected element.
- Radial controls that allow users to drag the marker/pointer to a position, also allows to pick a value and set marker to it.
- Linear slider controls allow tapping or clicking on any point of the slider track to change and set the value.

_Rules to follow_:

- For interface elements that require or support a dragging operation:
  - Check the interface for the presence of functions triggered by dragging movement.
  - Check that there is a single pointer alternative activation that does not require dragging to operate the same function.
- For each component that violates rule #1 above, compile a concise list of issues that user can review.

- For each issue found, provide a separate, detailed report.
- Keep issues concise, avoid duplicated issues or unnecessary or non-applicable problems.
- Assume that any imported functionality works as expected and was already analyzed.
- Components do not supplement or provide global functionalities.
- Lightning base components (`lightning-input`, `lightning-combobox`, `lightning-textarea`, `lightning-icon`, etc.) provide their own accessible labeling, ARIA, and error handling in shadow DOM via their dedicated attributes (`label`, `alternative-text`, field-level validation). When such a component is given a `label` attribute it is already programmatically labeled — even with `variant="label-hidden"`, which hides the label visually but keeps it for assistive technology. Do **not** flag a sibling/wrapper `<label>` or `<span>` for a missing `for`/`id` when the actual control is a self-labeling Lightning component, and do not treat a visible heading as if it were the control's only label. This also covers navigation and icon base components (`lightning-vertical-navigation-item`, `lightning-vertical-navigation-item-icon`, `lightning-button-icon`, etc.): when a `label` (or `alternative-text`) attribute is supplied, the base component renders it as the visible link/control text **and** exposes it as the accessible name, and any `icon-name` is decorative — do not emit a 4.1.2 "verify the label is associated with the icon" warning, even a hedged one. The presence of the `label` attribute is the association.
- Resolve template bindings before judging them. A template expression like `{someValue}` refers to a property or getter on the component's controller (`.js`/`.ts`) — including `@api` properties and `get someValue()` getters — not to a module-level imported constant (which LWC templates cannot bind to). Check the controller for the binding's definition before concluding a value is undefined, empty, or missing. When reviewing a diff, verify which side is the corrected code; do not assume the change introduced the problem.
- Prefer a real `<button>` for actions; for a link, `href="#"` with `event.preventDefault()` (the canonical SLDS pattern). Don't recommend `href="javascript:void(0)"` as a first-line remediation — it's a no-op-anchor anti-pattern. It is acceptable only as a last resort when moving `<a>` → `<button>` is genuinely impossible, and even then only when paired with the full set of attributes that make the anchor behave as an accessible button (`role="button"`, keyboard activation, etc.) — `void(0)` on its own is an incomplete fix. Don't flag existing `javascript:void(0)` as a violation.
- ARIA attribute spelling depends on the element type. On a **plain HTML element** (`div`, `span`, `button`, `input`, `a`, `img`, `iframe`, …) the only valid spelling is the W3C form `aria-labelledby` / `aria-describedby`; the hyphen-split `aria-labelled-by` / `aria-described-by` there **is** a real bug — keep flagging it. But on an **LWC component tag** (`lightning-*` or a custom `ns-name` element), the hyphen-split form is the kebab-case binding of the component's `@api ariaLabelledBy` / `ariaDescribedBy` property (each capital letter maps to `-` + lowercase), and LWC reflects it to the spec-correct `aria-labelledby` in the rendered DOM. Do **not** flag `aria-labelled-by` on a component tag as a misspelling, and do not claim it "breaks the accessible name computation" — you cannot determine that from the attribute name alone, because both `aria-labelled-by` (via `@api` property kebab-casing) and `aria-labelledby` (via LWC's ARIA reflection) can wire to the same property depending on the component. Treat a hyphen-split ARIA attribute on a component tag as a valid binding, not a violation.
