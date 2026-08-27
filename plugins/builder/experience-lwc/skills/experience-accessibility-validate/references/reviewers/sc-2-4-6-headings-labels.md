## SC 2.4.6 - Headings and Labels (Level AA)

Headings and labels describe topic or purpose.

## SC: 2.4.6 - Headings and Labels

This success criterion strictly concerns the content itself when such content is present, and does not address the following concerns, which are handled by different criteria:

- Heading or label markup or identification. These requirements are separately covered by 1.3.1 'Info and Relationships'
- Alternative accessible name methods linked to headings or labels. These requirements are separately covered by 4.1.2 'Name, Role, and Value'
- Whether a label is present or not. 3.3.2 'Labels or Instructions' handles the use of labels.

EXTREMELY IMPORTANT: For WCAG SC 2.4.6 'Headings and Labels' (Level AA), your ONLY task is to identify if an already present and identifiable heading or label is indescriptive, unclear, or ambiguous in its purpose or topic.

You MUST NOT report any issue where an accessible name (label) is entirely absent for an interactive element (like a button or link acting as a button), regardless of whether it uses an `aria-label`, `aria-labelledby`, or visible text content via a slot.

Specifically, you MUST NOT generate an output of type: "Missing aria-label or explicit label" or type: "Missing aria-labelledby Attribute" under ANY circumstances for SC 2.4.6.

Issues where an interactive element completely lacks an accessible name (e.g., `<a class="slds-button"></a>` with an empty slot or no text) fall under WCAG SC 4.1.2 'Name, Role, Value'. These are not 2.4.6 violations. Similarly, issues of missing labels for user input are 3.3.2.

For 2.4.6, if an element has no explicit label/name at all, you are to IGNORE IT. Only if a label/name exists (e.g., `<button>Edit</button>` or `<h1 id="x">...</h1>` `<label for="y">`...), then assess if that existing label/name is descriptive enough. Do NOT suggest adding an `aria-label` or `aria-labelledby` if none is present."

Analyze the given file using the following framework:

Review the provided HTML and JS files for accessibility violations per WCAG 2.2 SC 2.4.6, 'Headings and Labels'. For all headings or labels on the page, ensure the content is clear, descriptive, and contextually describes the content with which it's associated to determine if they meet SC 2.4.6. If they do not, then flag this as a violation.

Notes:

- Headings should be descriptive such that it's easy to understand what its associated section may contain. For example, a page that displays contact information can have a heading like "Contact Information" or "Main Contact".
- Form-related labels should clearly convey what type of input is required from the user. For example, name fields can have labels like "Salutation", "First Name", and "Last Name".

When flagging a violation, you should calculate an importance level: 'low', 'medium', or 'high'. This WCAG rule is often a matter of subjectivity and context, so we only want to include violations for which there is a high level of importance that it is fixed. The following can be used to assess importance level:

- Low: A given label or heading may not technically be descriptive, but a compelling argument could also be made that the element is sufficiently descriptive given context or some other unique subjective reading of the value.
- Medium: A given label or heading is lacking some potentially minor valuable information. There are better options for the heading or label value, but it's not strictly required in order to provide an accessible experience in all scenarios.
- High: A given label or heading is vague and unclear. If this issue is not corrected, then the code at hand is to be considered an objective and outright violation of WCAG rule 2.4.6. It is definitively a violation.

IMPORTANT: When evaluating the descriptiveness of headings or labels for SC 2.4.6, if the label's value is a variable (e.g., `aria-label={someVariable}`), you MUST assume it is compliant and descriptive, and therefore, you MUST NOT report it as a violation. This is particularly true if the variable might refer to an imported label for localization or dynamic content. Your analysis of descriptiveness for 2.4.6 should ONLY apply to hardcoded string values that are visibly present in the HTML/markup provided.

Rules to follow:

- Find all violations of SC 2.4.6 'Headings and Labels' in the provided HTML and JS files.
  - For each issue found, provide a separate, detailed report.
- Keep issues concise, avoid duplicated issues or unnecessary or non-applicable problems.
- Assume that any imported functionality works as expected and was already analyzed.
- Components do not supplement or provide global functionalities.
- Lightning base components (`lightning-input`, `lightning-combobox`, `lightning-textarea`, `lightning-icon`, etc.) provide their own accessible labeling, ARIA, and error handling in shadow DOM via their dedicated attributes (`label`, `alternative-text`, field-level validation). When such a component is given a `label` attribute it is already programmatically labeled — even with `variant="label-hidden"`, which hides the label visually but keeps it for assistive technology. Do **not** flag a sibling/wrapper `<label>` or `<span>` for a missing `for`/`id` when the actual control is a self-labeling Lightning component, and do not treat a visible heading as if it were the control's only label. This also covers navigation and icon base components (`lightning-vertical-navigation-item`, `lightning-vertical-navigation-item-icon`, `lightning-button-icon`, etc.): when a `label` (or `alternative-text`) attribute is supplied, the base component renders it as the visible link/control text **and** exposes it as the accessible name, and any `icon-name` is decorative — do not emit a 4.1.2 "verify the label is associated with the icon" warning, even a hedged one. The presence of the `label` attribute is the association.
- Resolve template bindings before judging them. A template expression like `{someValue}` refers to a property or getter on the component's controller (`.js`/`.ts`) — including `@api` properties and `get someValue()` getters — not to a module-level imported constant (which LWC templates cannot bind to). Check the controller for the binding's definition before concluding a value is undefined, empty, or missing. When reviewing a diff, verify which side is the corrected code; do not assume the change introduced the problem.
- Prefer a real `<button>` for actions; for a link, `href="#"` with `event.preventDefault()` (the canonical SLDS pattern). Don't recommend `href="javascript:void(0)"` as a first-line remediation — it's a no-op-anchor anti-pattern. It is acceptable only as a last resort when moving `<a>` → `<button>` is genuinely impossible, and even then only when paired with the full set of attributes that make the anchor behave as an accessible button (`role="button"`, keyboard activation, etc.) — `void(0)` on its own is an incomplete fix. Don't flag existing `javascript:void(0)` as a violation.
- ARIA attribute spelling depends on the element type. On a **plain HTML element** (`div`, `span`, `button`, `input`, `a`, `img`, `iframe`, …) the only valid spelling is the W3C form `aria-labelledby` / `aria-describedby`; the hyphen-split `aria-labelled-by` / `aria-described-by` there **is** a real bug — keep flagging it. But on an **LWC component tag** (`lightning-*` or a custom `ns-name` element), the hyphen-split form is the kebab-case binding of the component's `@api ariaLabelledBy` / `ariaDescribedBy` property (each capital letter maps to `-` + lowercase), and LWC reflects it to the spec-correct `aria-labelledby` in the rendered DOM. Do **not** flag `aria-labelled-by` on a component tag as a misspelling, and do not claim it "breaks the accessible name computation" — you cannot determine that from the attribute name alone, because both `aria-labelled-by` (via `@api` property kebab-casing) and `aria-labelledby` (via LWC's ARIA reflection) can wire to the same property depending on the component. Treat a hyphen-split ARIA attribute on a component tag as a valid binding, not a violation.
