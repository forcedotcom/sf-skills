## SC 2.5.3 - Label in Name (Level A)

For user interface components with labels that include text or images of text, the name contains the text that is presented visually.

## SC: 2.5.3 - Label In Name

Analyze the given file using the following framework:

Review the provided HTML and JS files for accessibility violations per WCAG 2.2 SC 2.5.3, 'Label in Name'. For all controls on the page, compare the visible label with the associate accessible name as defined below, and determine if they meet SC 2.5.3. If they do not, then flag this as a violation.

The visible label is the label that is rendered to the DOM and associated with a control.

The accessible name is the value computed by assistive technology associated with a control.

You must use the following algorithm to compute the accessible name for comparison with the visible label:

```text
  1. Initialize: Set the root node to the given element, the current node to the root node, and the total accumulated text to the empty string ("").
  2. Compute the text alternative for the current node:
    A. If the current node is hidden and is not directly referenced by aria-labelledby, nor directly referenced by a native host language text alternative element (e.g. label in HTML) or attribute, return the empty string.
    B. Otherwise:
      - If the current node has an aria-labelledby attribute that contains at least one valid IDREF, and the current node is not already part of an aria-labelledby traversal, process its IDREFs in the order they occur:
         i. Set the accumulated text to the empty string.
        ii. For each IDREF:
            a. Set the current node to the node referenced by the IDREF.
            b. Compute the text alternative of the current node beginning with step 2. Set the result to that text alternative.
            c. Append the result, with a space, to the accumulated text.
       iii. Return the accumulated text.
    C. Otherwise, if the current node has an aria-label attribute whose value is not the empty string, nor, when trimmed of white space, is not the empty string:
      - If traversal of the current node is due to recursion and the current node is an embedded control as defined in step 2E, ignore aria-label and skip to rule 2E.
      - Otherwise, return the value of aria-label.
    D. Otherwise, if the current node's native markup provides an attribute (e.g. title) or element (e.g. HTML label) that defines a text alternative, return that alternative in the form of a flat string as defined by the host language, unless the element is marked as presentational (role="presentation" or role="none").
    E. Otherwise, if the current node is a control embedded within the label (e.g. the label element in HTML or any element directly referenced by aria-labelledby) for another widget, where the user can adjust the embedded control's value, then include the embedded control as part of the text alternative in the following manner:
      - If the embedded control has role textbox, return its value.
      - If the embedded control has role menu button, return the text alternative of the button.
      - If the embedded control has role combobox or listbox, return the text alternative of the chosen option.
      - If the embedded control has role range (e.g., a spin button or slider):
        - If the aria-valuetext property is present, return its value,
        - Otherwise, if the aria-valuenow property is present, return its value,
        - Otherwise, use the value as specified by a host language attribute.
    F. Otherwise, if the current node's role allows name from content, or if the current node is referenced by aria-labelledby, or is a native host language text alternative element (e.g. label in HTML), or is a descendant of a native host language text alternative element:
         i. Set the accumulated text to the empty string.
        ii. Check for CSS generated textual content associated with the current node and include it in the accumulated text. The CSS :before and :after pseudo-elements [CSS2] can provide textual content for elements that have a content model.
           - For :before pseudo-elements, User agents MUST prepend CSS textual content, without a space, to the textual content of the current node.
           - For :after pseudo-elements, User agents MUST append CSS textual content, without a space, to the textual content of the current node.
       iii. For each child node of the current node:
          a. Set the current node to the child node.
          b. Compute the text alternative of the current node beginning with step 2. Set the result to that text alternative.
          c. Append the result to the accumulated text.
        iv. Return the accumulated text.

  Important: Each node in the subtree is consulted only once. If text has been collected from a descendant, but is referenced by another IDREF in some descendant node, then that second, or subsequent, reference is not followed. This is done to avoid infinite loops.

    G. Otherwise, if the current node is a Text node, return its textual contents.
    H. Otherwise, if the current node is a descendant of an element whose Accessible Name is being computed, and contains descendants, proceed to 2F.i.
    I. Otherwise, if the current node has a Tooltip attribute, return its value.

  Append the result of each step above, with a space, to the total accumulated text.

  After all steps are completed, the total accumulated text is used as the accessible name of the element that initiated the computation.
```

For every element in the component, determine both its visible label and its accessible name using the aforementioned algorithm. If the two values are unique, then this must be flagged as a violation. For example, `aria-label` uses different wording to add additional context for screen readers, but it fails to include or prefix the visible text, such as when the visible text displays "nonstandard" and the `aria-label` uses "this field is not standard".

This is ONLY about accessible name computation. Details regarding accessible description should be ignored. Eg. an `aria-describedby` attribute/value should not be considered for the accessible name, and should be ignored in this case.

Rules to follow:

- Find all violations of SC 2.5.3 'Label in Name' in the provided HTML file.
  - For each issue found, provide a separate, detailed report.
- Keep issues concise, avoid duplicated issues or unnecessary or non-applicable problems.
- Assume that any imported functionality works as expected and was already analyzed.
- Components do not supplement or provide global functionalities.
- Lightning base components (`lightning-input`, `lightning-combobox`, `lightning-textarea`, `lightning-icon`, etc.) provide their own accessible labeling, ARIA, and error handling in shadow DOM via their dedicated attributes (`label`, `alternative-text`, field-level validation). When such a component is given a `label` attribute it is already programmatically labeled — even with `variant="label-hidden"`, which hides the label visually but keeps it for assistive technology. Do **not** flag a sibling/wrapper `<label>` or `<span>` for a missing `for`/`id` when the actual control is a self-labeling Lightning component, and do not treat a visible heading as if it were the control's only label. This also covers navigation and icon base components (`lightning-vertical-navigation-item`, `lightning-vertical-navigation-item-icon`, `lightning-button-icon`, etc.): when a `label` (or `alternative-text`) attribute is supplied, the base component renders it as the visible link/control text **and** exposes it as the accessible name, and any `icon-name` is decorative — do not emit a 4.1.2 "verify the label is associated with the icon" warning, even a hedged one. The presence of the `label` attribute is the association.
- Resolve template bindings before judging them. A template expression like `{someValue}` refers to a property or getter on the component's controller (`.js`/`.ts`) — including `@api` properties and `get someValue()` getters — not to a module-level imported constant (which LWC templates cannot bind to). Check the controller for the binding's definition before concluding a value is undefined, empty, or missing. When reviewing a diff, verify which side is the corrected code; do not assume the change introduced the problem.
- Prefer a real `<button>` for actions; for a link, `href="#"` with `event.preventDefault()` (the canonical SLDS pattern). Don't recommend `href="javascript:void(0)"` as a first-line remediation — it's a no-op-anchor anti-pattern. It is acceptable only as a last resort when moving `<a>` → `<button>` is genuinely impossible, and even then only when paired with the full set of attributes that make the anchor behave as an accessible button (`role="button"`, keyboard activation, etc.) — `void(0)` on its own is an incomplete fix. Don't flag existing `javascript:void(0)` as a violation.
- ARIA attribute spelling depends on the element type. On a **plain HTML element** (`div`, `span`, `button`, `input`, `a`, `img`, `iframe`, …) the only valid spelling is the W3C form `aria-labelledby` / `aria-describedby`; the hyphen-split `aria-labelled-by` / `aria-described-by` there **is** a real bug — keep flagging it. But on an **LWC component tag** (`lightning-*` or a custom `ns-name` element), the hyphen-split form is the kebab-case binding of the component's `@api ariaLabelledBy` / `ariaDescribedBy` property (each capital letter maps to `-` + lowercase), and LWC reflects it to the spec-correct `aria-labelledby` in the rendered DOM. Do **not** flag `aria-labelled-by` on a component tag as a misspelling, and do not claim it "breaks the accessible name computation" — you cannot determine that from the attribute name alone, because both `aria-labelled-by` (via `@api` property kebab-casing) and `aria-labelledby` (via LWC's ARIA reflection) can wire to the same property depending on the component. Treat a hyphen-split ARIA attribute on a component tag as a valid binding, not a violation.
