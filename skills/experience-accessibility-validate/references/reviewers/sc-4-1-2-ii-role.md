## SC 4.1.2 - Name, Role, Value (Level A)

For all user interface components, the name and role can be programmatically determined; states, properties, and values that can be set by the user can be programmatically set; and notification of changes to these items is available to user agents, including assistive technologies.

## SC: 4.1.2 (ii) - Role Only

Analyze the given file using the following framework:

Review the provided HTML and JS files for accessibility violations per WCAG 2.2 SC 4.1.2, 'Role' ('Name' and 'Value' from this rule should not be considered). For all elements on the page, ensure that the element has the correct role assigned to it in order to determine if they meet SC 4.1.2. If they do not meet this success criterion, flag it as a violation.

**ABSOLUTE AND STRICT EXCLUSION RULES FOR SC 4.1.2 'ROLE' ANALYSIS:**

- **DO NOT flag semantic HTML elements (e.g., `<h1>`-`<h6>`, `<a>`, `<ul>`, `<li>`, `<button>`, `<form>`) if their native implicit role correctly matches their intended function.** These elements **automatically pass** the 'Role' criterion by default.
- **DO NOT flag generic HTML elements (`div`, `span`) used _solely_ for visual layout, styling, or as non-semantic containers.** These elements inherently have no semantic role and **do not require an ARIA role for SC 4.1.2 'Role' compliance**. Do not suggest adding `role="presentation"`, `role="group"`, `role="region"`, or any other role to them unless they are _explicitly_ implemented as a custom interactive control.
- **DO NOT suggest general "semantic structure" improvements (e.g., wrapping in `<section>`), "accessible name" issues (e.g., `aria-label`), "value" issues, or general best practices.** These are **outside the narrow scope** of SC 4.1.2 'Role' analysis.
- **Specifically for `role="separator"`**: ONLY suggest this role if the element is an interactive divider (e.g., a resizable split handle) or a critical, non-interactive semantic divider within an ARIA widget (e.g., within a menu or toolbar). DO NOT suggest it for purely visual lines or spacing.
  **DO NOT flag Salesforce Lightning Base Components (e.g., `lightning-card`, `lightning-record-edit-form`, `lightning-input-field`, `lightning-button`). Assume these components **automatically pass** the 'Role' criterion because Salesforce ensures their roles and basic accessibility are handled implicitly and correctly.** Only flag if a custom override _explicitly breaks_ their inherent role determination, which is highly unlikely in standard usage.

For each of the following role categories, make sure that the given markup contains the relevant role to its intended purpose, either implicitly via semantic HTML, or explicitly via the role attribute. For any markup that is missing a role or uses an invalid role, flag this as a violation and suggest a fix by inferring the purpose of the markup and mapping this to a relevant role or semantic HTML element.

If semantic HTML is used and the programmatic behavior of the markup via Javascript matches its usual function, then this meets the criterion implicitly. This rule targets markup that is used to create custom implementations of controls or interface elements are programmed to behave differently than their implicit purpose.

In determining this, attempt to infer the intent of the code and determine whether the code in question maps to any valid role. Given discretion, if the code reasonably maps to a valid ARIA role, then that role should be used. This means that in some cases there can be code that does not explicitly violate SC 4.1.2 but should be flagged by you to be updated.

Some examples to be considered, but not limited to: - When template loop syntax (e.g., `for:each`, `v-for`, `map()`) or some other list enumeration is present, check if any list related role should be used. Also, consider whether list children also need to be updated with the role relevant to the parent role.

The following roles should be considered:
`toolbar`
`tooltip`
`feed`
`math`
`presentation`
`note`
`application`
`article`
`cell`
`columnheader`
`definition`
`directory`
`document`
`figure`
`group`
`heading`
`img`
`list`
`listitem`
`meter`
`row`
`rowgroup`
`rowheader`
`separator`
`table`
`term`
`scrollbar`
`searchbox`
`separator`
`slider`
`spinbutton`
`switch`
`tab`
`tabpanel`
`treeitem`
`combobox`
`menu`
`menubar`
`tablist`
`tree`
`treegrid`
`banner`
`complementary`
`contentinfo`
`form`
`main`
`navigation`
`region`
`search`
`alert`
`log`
`marquee`
`status`
`timer`
`alertdialog`
`dialog`

Also make sure to check that relationships between roles are present. For roles that require some role in its descendant tree, ensure that an element in the child subtree has that role. Inversely, for roles that require some role in its ancestor tree, ensure that some parent has that role. Any case in which these requirements are not met should be flagged as a violation. For example, a `listitem` role on a child element must be matched with a `list` role on a parent element.

Do not use Abstract Roles.

Rules to follow:

- Find all violations of SC 4.1.2 'Role' in the provided HTML and JS files.
  - For each issue found, provide a separate, detailed report.
- Keep issues concise, avoid duplicated issues or unnecessary or non-applicable problems.
- Assume that any imported functionality works as expected and was already analyzed.
- Components do not supplement or provide global functionalities.
- Lightning base components (`lightning-input`, `lightning-combobox`, `lightning-textarea`, `lightning-icon`, etc.) provide their own accessible labeling, ARIA, and error handling in shadow DOM via their dedicated attributes (`label`, `alternative-text`, field-level validation). When such a component is given a `label` attribute it is already programmatically labeled — even with `variant="label-hidden"`, which hides the label visually but keeps it for assistive technology. Do **not** flag a sibling/wrapper `<label>` or `<span>` for a missing `for`/`id` when the actual control is a self-labeling Lightning component, and do not treat a visible heading as if it were the control's only label. This also covers navigation and icon base components (`lightning-vertical-navigation-item`, `lightning-vertical-navigation-item-icon`, `lightning-button-icon`, etc.): when a `label` (or `alternative-text`) attribute is supplied, the base component renders it as the visible link/control text **and** exposes it as the accessible name, and any `icon-name` is decorative — do not emit a 4.1.2 "verify the label is associated with the icon" warning, even a hedged one. The presence of the `label` attribute is the association.
- Resolve template bindings before judging them. A template expression like `{someValue}` refers to a property or getter on the component's controller (`.js`/`.ts`) — including `@api` properties and `get someValue()` getters — not to a module-level imported constant (which LWC templates cannot bind to). Check the controller for the binding's definition before concluding a value is undefined, empty, or missing. When reviewing a diff, verify which side is the corrected code; do not assume the change introduced the problem.
- Prefer a real `<button>` for actions; for a link, `href="#"` with `event.preventDefault()` (the canonical SLDS pattern). Don't recommend `href="javascript:void(0)"` as a first-line remediation — it's a no-op-anchor anti-pattern. It is acceptable only as a last resort when moving `<a>` → `<button>` is genuinely impossible, and even then only when paired with the full set of attributes that make the anchor behave as an accessible button (`role="button"`, keyboard activation, etc.) — `void(0)` on its own is an incomplete fix. Don't flag existing `javascript:void(0)` as a violation.
- ARIA attribute spelling depends on the element type. On a **plain HTML element** (`div`, `span`, `button`, `input`, `a`, `img`, `iframe`, …) the only valid spelling is the W3C form `aria-labelledby` / `aria-describedby`; the hyphen-split `aria-labelled-by` / `aria-described-by` there **is** a real bug — keep flagging it. But on an **LWC component tag** (`lightning-*` or a custom `ns-name` element), the hyphen-split form is the kebab-case binding of the component's `@api ariaLabelledBy` / `ariaDescribedBy` property (each capital letter maps to `-` + lowercase), and LWC reflects it to the spec-correct `aria-labelledby` in the rendered DOM. Do **not** flag `aria-labelled-by` on a component tag as a misspelling, and do not claim it "breaks the accessible name computation" — you cannot determine that from the attribute name alone, because both `aria-labelled-by` (via `@api` property kebab-casing) and `aria-labelledby` (via LWC's ARIA reflection) can wire to the same property depending on the component. Treat a hyphen-split ARIA attribute on a component tag as a valid binding, not a violation.
