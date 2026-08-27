## SC 1.3.1 - Info and Relationships (Level A)

Information, structure, and relationships conveyed through presentation can be programmatically determined or are available in text.

## SC: 1.3.1 (v) - Info And Relationships - Groups only

Analyze the files using following context:

_Goal_: Information, structure and relationships conveyed through presentation can be programmatically determined or available in text.

_What to do_: Review the provided HTML and JS files for accessibility violations per WCAG 2.2 SC 1.3.1, 'Info and Relationships' with focus on groups requirements only.

Having structures and relationships programmatically determinable ensures that important information necessary for comprehension will be perceivable to all users. Grouping controls is most important for related radio buttons and checkboxes.

Examples:

- Form fields may be positioned as groups that share text labels.
- A multiple choice test with a question and set of radio buttons to present possible answers; the radio buttons are contained within a `fieldset` while the question is tagged with `legend` element.
- A user profile page allows users to indicate personal interests using checkboxes; the checkboxes are contained within a `fieldset`, and the `legend` element prompts the user to select one or more interests.

Following are some sufficient techniques that WCAG working group deems sufficient to meet this success criterion:

- ARIA17: Using grouping roles to identify related form controls within a form. Any label associated with group also serves as a common label for individual controls in this group.
  This is a viable alternative to using `fieldset` / `legend` technique (H71). For a group of radio buttons, `role="radiogroup"` should be used instead of `role="group"` and is not meant to be used for wrapping all controls on a form within a single container with `role="group"`.

- For groups of related controls where individual labels for each control do not provide sufficient description, and additional group level description is needed
  - Check that group of logically related input or select elements are contained within an element with `role="group"`, or `role="radiogroup"` depending on the type of elements in group.
  - Check that this group has an accessible name describing it's purpose using `aria-label` or `aria-labelledby` attribute.
  - The objective of this technique is to allow users to understand the relationship of form controls by providing semantic grouping and interact quickly.
    Form controls can be grouped by enclosing them within `fieldset` element. All controls within a given `fieldset` are then related. The first element inside `fieldset` must be a `legend` element. Avoid nesting fieldsets unnecessarily, as this can lead to confusion.
    A set of radio buttons or checkboxes are said to be related when they all submit values to single named field.
  - They work same as selection lists that allow users to choose from set of options, except selection lists are single controls while radio buttons and checkboxes are multiple controls.
  - The individual label associated with each radio button or checkbox control may not fully convey group's descriptive context.
    It can also be helpful to group other sets of controls less tightly related than radio buttons and checkboxes, like form fields that collect user address might be grouped together with `legend` of "Address".
    Authors sometimes avoid using `fieldset` element because the default display style draws a border around the grouped controls. However, this style can be modified with CSS by overriding 'border' property of `fieldset` and 'position' property of `legend`.

For groups of related controls where individual labels for each control do not provide sufficient context description, and additional group level description is needed; ensure following are true:

- Check that the group of logically related elements, like either `input` or `select` elements are contained within `fieldset` elements.
- Check that each `fieldset` has a `legend` element that is first child and includes a description for the group.
- The objective of this technique is to group items in a selection list.
  A selection list is a set of allowed values for a form control such as multi-select list or combo box. In semantic HTML, the `select` element is used to create both multi-select lists and combo boxes, where various allowed options are each indicated with `option` elements, grouped together using `optgroup` element, and labeled the group with `label`.

For each selection list:

- Check the set of options within the list to see if there are groups of related options.
- If there are groups of related options, check that they are properly grouped (like using `optgroup` element)

  - The objective of this technique is to group navigation links using HTML `nav` element or similar semantic sectioning elements. Using this markup can make groups of links easier to locate and navigate.
    When such element is employed more than once on a page, distinguish navigation groups by using `aria-label` or `aria-labelledby` attribute.
    Not all groups of links need to use `nav` element for markup. For example, links maybe grouped in other structures like lists or may use ARIA markup if do not present a discrete section of the page.

- Check that links that are grouped and represent a section of page, are enclosed in a `nav` element or similar semantics.

_Rules to follow_:

- Require code to reinforce structure, relationships and information conveyed through presentation for groups of related elements, per this WCAG 2.2 SC 1.3.1 'Info and Relationships - Groups only' success criterion, in the provided HTML and JS files.
- Do not worry about violations of SC 1.3.1 that are not specific to groups. These will be handled by other reviewers.
  - For each issue found, provide a separate, detailed report.
- Keep issues concise, avoid duplicated issues or unnecessary or non-applicable problems.
- Assume that any imported functionality works as expected and was already analyzed.
- Components do not supplement or provide global functionalities.
- Lightning base components (`lightning-input`, `lightning-combobox`, `lightning-textarea`, `lightning-icon`, etc.) provide their own accessible labeling, ARIA, and error handling in shadow DOM via their dedicated attributes (`label`, `alternative-text`, field-level validation). When such a component is given a `label` attribute it is already programmatically labeled — even with `variant="label-hidden"`, which hides the label visually but keeps it for assistive technology. Do **not** flag a sibling/wrapper `<label>` or `<span>` for a missing `for`/`id` when the actual control is a self-labeling Lightning component, and do not treat a visible heading as if it were the control's only label. This also covers navigation and icon base components (`lightning-vertical-navigation-item`, `lightning-vertical-navigation-item-icon`, `lightning-button-icon`, etc.): when a `label` (or `alternative-text`) attribute is supplied, the base component renders it as the visible link/control text **and** exposes it as the accessible name, and any `icon-name` is decorative — do not emit a 4.1.2 "verify the label is associated with the icon" warning, even a hedged one. The presence of the `label` attribute is the association.
- Resolve template bindings before judging them. A template expression like `{someValue}` refers to a property or getter on the component's controller (`.js`/`.ts`) — including `@api` properties and `get someValue()` getters — not to a module-level imported constant (which LWC templates cannot bind to). Check the controller for the binding's definition before concluding a value is undefined, empty, or missing. When reviewing a diff, verify which side is the corrected code; do not assume the change introduced the problem.
- Prefer a real `<button>` for actions; for a link, `href="#"` with `event.preventDefault()` (the canonical SLDS pattern). Don't recommend `href="javascript:void(0)"` as a first-line remediation — it's a no-op-anchor anti-pattern. It is acceptable only as a last resort when moving `<a>` → `<button>` is genuinely impossible, and even then only when paired with the full set of attributes that make the anchor behave as an accessible button (`role="button"`, keyboard activation, etc.) — `void(0)` on its own is an incomplete fix. Don't flag existing `javascript:void(0)` as a violation.
- ARIA attribute spelling depends on the element type. On a **plain HTML element** (`div`, `span`, `button`, `input`, `a`, `img`, `iframe`, …) the only valid spelling is the W3C form `aria-labelledby` / `aria-describedby`; the hyphen-split `aria-labelled-by` / `aria-described-by` there **is** a real bug — keep flagging it. But on an **LWC component tag** (`lightning-*` or a custom `ns-name` element), the hyphen-split form is the kebab-case binding of the component's `@api ariaLabelledBy` / `ariaDescribedBy` property (each capital letter maps to `-` + lowercase), and LWC reflects it to the spec-correct `aria-labelledby` in the rendered DOM. Do **not** flag `aria-labelled-by` on a component tag as a misspelling, and do not claim it "breaks the accessible name computation" — you cannot determine that from the attribute name alone, because both `aria-labelled-by` (via `@api` property kebab-casing) and `aria-labelledby` (via LWC's ARIA reflection) can wire to the same property depending on the component. Treat a hyphen-split ARIA attribute on a component tag as a valid binding, not a violation.
