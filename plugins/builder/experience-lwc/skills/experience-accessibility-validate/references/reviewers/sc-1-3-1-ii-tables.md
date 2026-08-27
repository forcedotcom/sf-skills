## SC 1.3.1 - Info and Relationships (Level A)

Information, structure, and relationships conveyed through presentation can be programmatically determined or are available in text.

## SC: 1.3.1 (ii) - Tables Only

Analyze the given files using the following framework:

Review the provided HTML and JS files for accessibility violations per WCAG 2.2 SC 1.3.1 (ii), 'Tables'.
(Only tables from this rule should be considered). For all tables on the components, ensure that any information conveyed through presentation is programmatically determinable in order to determine if they meet SC 1.3.1 (ii).

For each of these elements, check if any of the following conditions of WCAG 2.2 SC 1.3.1 (ii), 'Tables' are true:

- The objective of this technique is to present tabular information in a way that preserves relationships within the information even when users cannot see the table or the presentation format is changed. Information is considered tabular when logical relationships among text, numbers, images, or other data exist in two dimensions (vertical and horizontal). These relationships are represented in columns and rows, and the columns and rows must be recognizable in order for the logical relationships to be perceived.
  Check for the presence of tabular information.
  For each instance of the `<table>` element found, perform the following checks:
- Verify the presence of table rows (`<tr>`): Ensure that each `<table>` element contains at least one `<tr>` element
- Verify the presence of table data cells (`<td>`) within rows (`<tr>`): For each `<tr>` element within a `<table>`, confirm that it contains one or more `<td>` elements representing the data cells
- Verify the presence of table header cells (`<th>`) when applicable: If the table includes headers, ensure that the header information is marked up using `<th>` elements, typically within the first `<tr>` element or within `<thead>` elements
- Check that all data content within the table is enclosed within `<td>` cell elements and that header content (if present) is within `<th>` elements
- For every `<table>` element identified, verify that it contains at least the following elements: `<tr>`, `<th>` (if headers are present, otherwise `<td>`), and `<td>`
- Providing an accessible name for a table is considered a best practice that significantly enhances usability for all users, especially those relying on assistive technologies.The accessible name can be provided in various ways:
- By either using a `aria-label` or `aria-labelledby` attributes or `<caption>` element in the table. Its a best practice and absence of accessible name is acceptable but not a violation.
- The objective of this technique is to associate header cells with data cells in simple data tables using the `scope` attribute.
- The `scope` attribute identifies whether the cell is a header for a row, column, or group of rows or columns
- Valid `scope` values: `row`, `col`, `rowgroup`, `colgroup`

For simple data tables:

- If headers are in the first row or column:
  - `th` elements without `scope` are sufficient
- If headers are not in the first row or column:
  - Check that all `th` elements have a `scope` attribute
  - Verify `scope` values match the header's role (`row`/`col`/`rowgroup`/`colgroup`)
    Note: For complex tables (multiple levels of headers, headers spanning rows/columns), use id and headers attributes instead (see H43)
- The objective of this technique is to associate each data cell (in a data table) with the appropriate headers.
  Check for layout tables and data tables:
- For layout tables:
  - Determine if content has a relationship with other content in both its column and row
  - If "no", the table is a layout table
- For data tables:
  - Check that any cell associated with multiple row/column headers contains a headers attribute listing all associated header IDs
  - For cells with id or headers attributes:
    - Verify each id in headers attribute matches a header element's id
    - Verify headers attribute contains all associated header IDs
    - Ensure all IDs are unique within the component

In order to fix a violation for a given element, you must examine the given component code and apply the most logical fix available such that the element satisfies one of the following conditions of WCAG 2.2 SC 1.3.1 (ii), 'Tables':

- The objective of this technique is to present tabular information in a way that preserves relationships within the information even when users cannot see the table or the presentation format is changed. Information is considered tabular when logical relationships among text, numbers, images, or other data exist in two dimensions (vertical and horizontal). These relationships are represented in columns and rows, and the columns and rows must be recognizable in order for the logical relationships to be perceived.
  Check for the presence of tabular information.
  For each instance of the `<table>` element found, perform the following checks:
- Verify the presence of table rows (`<tr>`): Ensure that each `<table>` element contains at least one `<tr>` element
- Verify the presence of table data cells (`<td>`) within rows (`<tr>`): For each `<tr>` element within a `<table>`, confirm that it contains one or more `<td>` elements representing the data cells
- Verify the presence of table header cells (`<th>`) when applicable: If the table includes headers, ensure that the header information is marked up using `<th>` elements, typically within the first `<tr>` element or within `<thead>` elements
- Check that all data content within the table is enclosed within `<td>` cell elements and that header content (if present) is within `<th>` elements
- For every `<table>` element identified, verify that it contains at least the following elements: `<tr>`, `<th>` (if headers are present, otherwise `<td>`), and `<td>`
- Providing an accessible name for a table is considered a best practice that significantly enhances usability for all users, especially those relying on assistive technologies.The accessible name can be provided in various ways:
- By either using a `aria-label` or `aria-labelledby` attributes or `<caption>` element in the table. Its a best practice and absence of accessible name is acceptable but not a violation.
- The objective of this technique is to associate header cells with data cells in simple data tables using the `scope` attribute.
- The `scope` attribute identifies whether the cell is a header for a row, column, or group of rows or columns
- Valid `scope` values: `row`, `col`, `rowgroup`, `colgroup`

For simple data tables:

- If headers are in the first row or column:
  - `th` elements without `scope` are sufficient
- If headers are not in the first row or column:
  - Check that all `th` elements have a `scope` attribute
  - Verify `scope` values match the header's role (`row`/`col`/`rowgroup`/`colgroup`)
    Note: For complex tables (multiple levels of headers, headers spanning rows/columns), use id and headers attributes instead (see H43)
- The objective of this technique is to associate each data cell (in a data table) with the appropriate headers.
  Check for layout tables and data tables:
- For layout tables:
  - Determine if content has a relationship with other content in both its column and row
  - If "no", the table is a layout table
- For data tables:
  - Check that any cell associated with multiple row/column headers contains a headers attribute listing all associated header IDs
  - For cells with id or headers attributes:
    - Verify each id in headers attribute matches a header element's id
    - Verify headers attribute contains all associated header IDs
    - Ensure all IDs are unique within the component

Note: A complex table is one where:

- Headers span multiple rows or columns
- Headers are not in the first row or column
- Multiple levels of headers exist
- Cells are associated with multiple headers
- The table structure requires additional context to understand relationships between data

If they do not meet this success criterion, then flag this as a violation.

Rules to follow:

- Find all violations of SC 1.3.1 (ii) 'Tables' in the provided HTML and JS files
- Do not worry about violations of SC 1.3.1 that are not specific to tables (handled by other reviewers)
- If no changes are needed, then produce an empty list
  - For each issue found, provide a separate, detailed report.
- Keep issues concise, avoid duplicated issues or unnecessary or non-applicable problems.
- Assume that any imported functionality works as expected and was already analyzed.
- Components do not supplement or provide global functionalities.
- Lightning base components (`lightning-input`, `lightning-combobox`, `lightning-textarea`, `lightning-icon`, etc.) provide their own accessible labeling, ARIA, and error handling in shadow DOM via their dedicated attributes (`label`, `alternative-text`, field-level validation). When such a component is given a `label` attribute it is already programmatically labeled — even with `variant="label-hidden"`, which hides the label visually but keeps it for assistive technology. Do **not** flag a sibling/wrapper `<label>` or `<span>` for a missing `for`/`id` when the actual control is a self-labeling Lightning component, and do not treat a visible heading as if it were the control's only label. This also covers navigation and icon base components (`lightning-vertical-navigation-item`, `lightning-vertical-navigation-item-icon`, `lightning-button-icon`, etc.): when a `label` (or `alternative-text`) attribute is supplied, the base component renders it as the visible link/control text **and** exposes it as the accessible name, and any `icon-name` is decorative — do not emit a 4.1.2 "verify the label is associated with the icon" warning, even a hedged one. The presence of the `label` attribute is the association.
- Resolve template bindings before judging them. A template expression like `{someValue}` refers to a property or getter on the component's controller (`.js`/`.ts`) — including `@api` properties and `get someValue()` getters — not to a module-level imported constant (which LWC templates cannot bind to). Check the controller for the binding's definition before concluding a value is undefined, empty, or missing. When reviewing a diff, verify which side is the corrected code; do not assume the change introduced the problem.
- Prefer a real `<button>` for actions; for a link, `href="#"` with `event.preventDefault()` (the canonical SLDS pattern). Don't recommend `href="javascript:void(0)"` as a first-line remediation — it's a no-op-anchor anti-pattern. It is acceptable only as a last resort when moving `<a>` → `<button>` is genuinely impossible, and even then only when paired with the full set of attributes that make the anchor behave as an accessible button (`role="button"`, keyboard activation, etc.) — `void(0)` on its own is an incomplete fix. Don't flag existing `javascript:void(0)` as a violation.
- ARIA attribute spelling depends on the element type. On a **plain HTML element** (`div`, `span`, `button`, `input`, `a`, `img`, `iframe`, …) the only valid spelling is the W3C form `aria-labelledby` / `aria-describedby`; the hyphen-split `aria-labelled-by` / `aria-described-by` there **is** a real bug — keep flagging it. But on an **LWC component tag** (`lightning-*` or a custom `ns-name` element), the hyphen-split form is the kebab-case binding of the component's `@api ariaLabelledBy` / `ariaDescribedBy` property (each capital letter maps to `-` + lowercase), and LWC reflects it to the spec-correct `aria-labelledby` in the rendered DOM. Do **not** flag `aria-labelled-by` on a component tag as a misspelling, and do not claim it "breaks the accessible name computation" — you cannot determine that from the attribute name alone, because both `aria-labelled-by` (via `@api` property kebab-casing) and `aria-labelledby` (via LWC's ARIA reflection) can wire to the same property depending on the component. Treat a hyphen-split ARIA attribute on a component tag as a valid binding, not a violation.
