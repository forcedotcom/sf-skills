## SC 1.4.3 - Contrast (Minimum) (Level AA)

The visual presentation of text and images of text has a contrast ratio of at least 4.5:1, except for large text (at least 3:1), incidental text (part of inactive components, purely decorative, not visible, or part of a picture containing significant other visual content), and logotypes.

## SC: 1.4.3 - Contrast (Minimum) (Level AA)

This reviewer focuses on ensuring enough contrast between text and its background so that it can be read by people with moderately low vision (who do not use contrast-enhancing assistive technology) as well as those with color deficiencies.

### Analysis Framework (What to do):

1.  Identify all visible text elements (e.g., in tags like `<h1>`, `<div>`, `<p>`, `<label>`, `<button>`, etc.).
2.  Determine the **color** (foreground) and **background color** (background) for each text element.
3.  Determine the **font size** and **weight** to classify the text as Standard or Large-Scale.
4.  Compute the contrast ratio with the bundled helper — **do not calculate luminance by hand**:

    ```bash
    python3 scripts/contrast-ratio.py FOREGROUND BACKGROUND [--large]
    ```

    Pass the resolved foreground and background colors (`#RGB`, `#RRGGBB`, `rgb()`, or `rgba()`); add `--large` when the text is large-scale (≥24px, or ≥18.66px bold). The script alpha-composites a translucent *foreground* over the background, applies the exact WCAG formula $(L1 + 0.05) / (L2 + 0.05)$, and prints the ratio plus a `PASS`/`FAIL` verdict for both thresholds (exit code `0` = meets the applicable threshold, `1` = below it, `2` = parse error). The **background must be opaque** — a translucent `rgba()` background is rejected (exit code `2`) because its rendered color depends on the unknown layer beneath it; resolve the effective opaque background first and pass that. Use `--json` for a machine-readable object. The script's verdict is authoritative; use it rather than an estimate.
5.  Treat the script's verdict against the required threshold (4.5:1 standard, 3:1 large) as the check result.

> **Do not estimate luminance by hand.** Mentally approximating relative luminance is unreliable — it has produced false positives and even different ratios for the _same_ color. Run `scripts/contrast-ratio.py` for the exact value. The verified reference below (sRGB gray `#NNNNNN` on `#FFFFFF`) is a quick sanity check for the common grayscale-text-on-white case, not a substitute for the script:
>
> | Gray      | Ratio | Standard (4.5:1) | Large (3:1)     |
> | --------- | ----- | ---------------- | --------------- |
> | `#595959` | 7.00  | pass             | pass            |
> | `#666666` | 5.74  | pass             | pass            |
> | `#767676` | 4.54  | pass (boundary)  | pass            |
> | `#777777` | 4.48  | **fail**         | pass            |
> | `#808080` | 3.95  | fail             | pass            |
> | `#959595` | 3.00  | fail             | pass (boundary) |
> | `#999999` | 2.85  | fail             | **fail**        |
> | `#AAAAAA` | 2.32  | fail             | fail            |
> | `#BBBBBB` | 1.92  | fail             | fail            |
>
> Rule of thumb for grayscale on white: `#767676` is the standard-text boundary — anything **darker** (lower hex value) passes 4.5:1; `#959595` is the large-text boundary for 3:1. In particular, **`#666666` and darker pass standard-text contrast — do not flag them.** For non-grayscale colors, non-white backgrounds, gradients, or alpha compositing, compute the exact ratio; if you cannot, do not guess — only flag when you are confident the ratio is below threshold.

### Goals for Contrast Compliance:

1.  **Standard Text (Ratio 4.5:1):**
    - **Good:** Black text on a white background (Ratio 21:1).
    - **Bad:** Light gray text on a white background (e.g., #AAAAAA on #FFFFFF, Ratio 2.32:1).
2.  **Large-Scale Text (Ratio 3:1):**
    - **Good:** Medium gray text on a white background (e.g., #808080 on #FFFFFF, Ratio 3.95:1 — passes large-text 3:1 but fails standard-text 4.5:1).
    - **Bad:** Light gray text on a white background (e.g., #BBBBBB on #FFFFFF, Ratio 1.92:1).
3.  **Focus/Hover States:** While the primary check is for the default state, flag any explicit color changes defined in CSS that might reduce contrast below the minimum thresholds during focus or hover states. _(Note: Full dynamic state checking is complex, but hard-coded poor contrast colors must be flagged.)_

### What to Look For:

- Text elements where the foreground color is too similar to the background color.
- Hard-coded color combinations in CSS or inline styles that fail the 4.5:1 or 3:1 ratio.
- Text sizes that are small (Standard Text) but have a contrast ratio less than 4.5:1.
- Text sizes that are large-scale but have a contrast ratio less than 3:1.
- Usage of transparency/opacity that negatively impacts the calculated contrast ratio.

### Common Violations for Contrast:

- **Placeholder Text:** Placeholder text should have enough contrast.
- **Secondary/Hint Text:** Secondary text (e.g., helper text or captions) styled with low-contrast gray colors.
- **Disabled/Inactive Elements:** Though exempt under strict rules, _functional_ elements styled to look inactive when they are not.
- **Text on Complex Backgrounds:** Text placed over gradient or patterned backgrounds where the minimum contrast requirement is not met across the entire text area.

### To fix the Contrast Violations, Use the following techniques:

• **Foreground Color (Text) Fix:**

- **Action:** Locate the style rule (inline style, CSS file, or JS variable) defining the text color.
- **Correction:** If the current color is a light color (e.g., #AAAAAA), change it to a darker, compliant color (e.g., #595959).
- **Priority:** Prioritize using standard, dark text colors (e.g., #333333 or #000000) for accessibility whenever possible.

• **Background Color Fix:**

- **Action:** Locate the style rule defining the element's background-color.
- **Correction:** If the current background-color is a dark color (e.g., #333333), change it to a lighter, compliant color (e.g., #CCCCCC).
- **Priority:** Prioritize using standard, light background colors (e.g., #FFFFFF or #F5F5F5).

• **Inline Style Correction Example:**

- **Violation:** `<div style="color: #AAAAAA; background-color: #FFFFFF;">Low Contrast Text</div>`
- **Fix:** `<div style="color: #444444; background-color: #FFFFFF;">Compliant Contrast Text</div>`

• **Placeholder/Secondary Text Fix:**

- **Action:** For elements like `<input placeholder="text">` or secondary helper text, find the dedicated style (often `:placeholder` or a class for secondary text).
- **Correction:** Ensure the foreground color of the placeholder/secondary text is adjusted to meet at least the 4.5:1 ratio against the background of the input/container.

• **Remediation Strategy:**

- **Goal:** Modify the least number of color declarations (either `color` or `background-color`) necessary to achieve the target ratio (4.5:1 for standard text, 3:1 for large text).
- **Method:** If foreground text is light, darken it. If foreground text is dark, lighten the background.
- **Context:** Only modify color values (#RRGGBB, rgb(), hsl()) found in inline styles or referenced CSS blocks identified by the analysis.

## Exemptions (DO NOT FLAG):

1.  **Decorative:** Text used purely for decorative purposes, where its specific lettering is not essential to understanding the content (e.g., text used as a stylized border).
2.  **Logotypes:** Text that is part of a logo or brand name.
3.  **Inactive UI Components:** Text in components that are disabled (e.g., a grayed-out button).

Rules to follow:

- Focus specifically on **visible text** in HTML and JS files.
- Only flag when the computed ratio falls below 4.5:1 for standard text or 3:1 for large-scale text
- Flag color combinations that result in a contrast ratio **below 4.5:1 for Standard Text**.
- Flag color combinations that result in a contrast ratio **below 3:1 for Large-Scale Text**.
- **Ignore** text clearly marked as decorative, part of a logo, or permanently disabled/inactive components.
- Do not assume or estimate the contrast ratio — compute it with `scripts/contrast-ratio.py` (which also handles alpha compositing), falling back to the grayscale-on-white reference table above only as a sanity check. When the resolved colors themselves are uncertain (gradients, images behind text, unknown background), do not flag.
  - For each issue found, provide a separate, detailed report.
- Keep issues concise, avoid duplicated issues or unnecessary or non-applicable problems.
- Assume that any imported functionality works as expected and was already analyzed.
- Components do not supplement or provide global functionalities.
- Lightning base components (`lightning-input`, `lightning-combobox`, `lightning-textarea`, `lightning-icon`, etc.) provide their own accessible labeling, ARIA, and error handling in shadow DOM via their dedicated attributes (`label`, `alternative-text`, field-level validation). When such a component is given a `label` attribute it is already programmatically labeled — even with `variant="label-hidden"`, which hides the label visually but keeps it for assistive technology. Do **not** flag a sibling/wrapper `<label>` or `<span>` for a missing `for`/`id` when the actual control is a self-labeling Lightning component, and do not treat a visible heading as if it were the control's only label. This also covers navigation and icon base components (`lightning-vertical-navigation-item`, `lightning-vertical-navigation-item-icon`, `lightning-button-icon`, etc.): when a `label` (or `alternative-text`) attribute is supplied, the base component renders it as the visible link/control text **and** exposes it as the accessible name, and any `icon-name` is decorative — do not emit a 4.1.2 "verify the label is associated with the icon" warning, even a hedged one. The presence of the `label` attribute is the association.
- Resolve template bindings before judging them. A template expression like `{someValue}` refers to a property or getter on the component's controller (`.js`/`.ts`) — including `@api` properties and `get someValue()` getters — not to a module-level imported constant (which LWC templates cannot bind to). Check the controller for the binding's definition before concluding a value is undefined, empty, or missing. When reviewing a diff, verify which side is the corrected code; do not assume the change introduced the problem.
- Prefer a real `<button>` for actions; for a link, `href="#"` with `event.preventDefault()` (the canonical SLDS pattern). Don't recommend `href="javascript:void(0)"` as a first-line remediation — it's a no-op-anchor anti-pattern. It is acceptable only as a last resort when moving `<a>` → `<button>` is genuinely impossible, and even then only when paired with the full set of attributes that make the anchor behave as an accessible button (`role="button"`, keyboard activation, etc.) — `void(0)` on its own is an incomplete fix. Don't flag existing `javascript:void(0)` as a violation.
- ARIA attribute spelling depends on the element type. On a **plain HTML element** (`div`, `span`, `button`, `input`, `a`, `img`, `iframe`, …) the only valid spelling is the W3C form `aria-labelledby` / `aria-describedby`; the hyphen-split `aria-labelled-by` / `aria-described-by` there **is** a real bug — keep flagging it. But on an **LWC component tag** (`lightning-*` or a custom `ns-name` element), the hyphen-split form is the kebab-case binding of the component's `@api ariaLabelledBy` / `ariaDescribedBy` property (each capital letter maps to `-` + lowercase), and LWC reflects it to the spec-correct `aria-labelledby` in the rendered DOM. Do **not** flag `aria-labelled-by` on a component tag as a misspelling, and do not claim it "breaks the accessible name computation" — you cannot determine that from the attribute name alone, because both `aria-labelled-by` (via `@api` property kebab-casing) and `aria-labelledby` (via LWC's ARIA reflection) can wire to the same property depending on the component. Treat a hyphen-split ARIA attribute on a component tag as a valid binding, not a violation.
