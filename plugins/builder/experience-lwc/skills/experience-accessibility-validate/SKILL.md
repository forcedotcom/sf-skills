---
name: experience-accessibility-validate
description: "Use this skill to determine whether a Lightning Web Component (LWC) is accessible and meets WCAG accessibility guidelines. TRIGGER when the user asks \"is my component accessible?\", \"does my LWC meet accessibility guidelines?\", \"is this component WCAG compliant?\", \"find accessibility problems in this LWC\", \"is this LWC keyboard accessible?\", \"does this component work with a screen reader?\", \"does this component have sufficient color contrast?\", \"check ARIA usage in this LWC\", or \"WCAG 2.2 accessibility check\". Also TRIGGER when the user wants to fix or improve accessibility (a11y, WCAG, ARIA) in an LWC's HTML, JS, or CSS — semantic markup, focus, keyboard nav, contrast, screen-reader labels, WCAG 2.2 SC. Produces `a11y-review.md` with WCAG-cited findings. DO NOT TRIGGER for general LWC generation (use `experience-lwc-generate`) or SLDS visual/design review not focused on accessibility (use `design-systems-slds-validate`)."
metadata:
  version: "1.1"
  domains: ["Experience"]
  cliTools:
    - tool: ["python3"]
      semver: ">=3.8"
  relatedSkills:
    - "design-systems-slds-validate"
    - "experience-lwc-generate"
---
<!-- adk-managed-skill -->

# Web Component Accessibility

Accessibility (a11y) patterns and remediation guidance for web components.
Reference any time work involves the visible or interactive surface of a
component — generating, modifying, reviewing, or styling HTML, JS, or
CSS — to apply WCAG 2.2 standards.

## Review Context

Conduct a review specifically focused on enhancing web accessibility, guided by the WCAG (Web Content Accessibility Guidelines).

In order to mark code as a violation, it must have a direct correlation to the WCAG rule cited such that it is a clear violation of the criteria.

Key Review Criteria:

1. Focus Exclusively on Accessibility:

- Evaluate the component solely for accessibility.
- Only consider compliance with the cited WCAG Success Criteria, ignoring violations that can be attributed to other criteria.
- Avoid addressing general code style, patterns, or issues unrelated to accessibility.

2. Ensure Minimum and Sufficient Accessibility:

- Identify accessibility issues that prevent the component from meeting the minimum requirements outlined by WCAG.
- Avoid suggesting enhancements that go beyond the scope of WCAG compliance unless strictly necessary.

3. WAI-ARIA Usage:

- Use WAI-ARIA attributes only when strictly required to achieve accessibility that cannot otherwise be addressed with semantic HTML.
- Avoid unnecessary complexity or potential regressions caused by incorrect or overuse of ARIA attributes.

4. Component Library Usage

- Assume that well-known component libraries (e.g., Salesforce Lightning, Material UI, Chakra UI) are accessible out of the box when correctly implemented. Unless they are used specifically in conflict with WCAG, library-provided components can be ignored for this review, as they are implemented in an accessible way beneath the abstraction.

**Focus**: Provide actionable feedback to ensure the component meets the necessary WCAG accessibility requirements, avoiding extraneous feedback unrelated to the prompt's scope. Identify issues in code only if there is an immediate fix. You MUST conduct the review, and subsequently suggest the code fix that solves this issue.



## Success Criteria Reviewers

Identify which Success Criteria apply to the code under review, then open the reference files relevant to that code. Each reference is a
self-contained reviewer with analysis framework, examples, and remediation
guidance.

### Perceivable

- [SC 1.1.1 Non-text Content](references/reviewers/sc-1-1-1-non-text-content.md)
- [SC 1.3.1 (i) Lists](references/reviewers/sc-1-3-1-i-lists.md)
- [SC 1.3.1 (ii) Tables](references/reviewers/sc-1-3-1-ii-tables.md)
- [SC 1.3.1 (iii) Form Labels](references/reviewers/sc-1-3-1-iii-form-labels.md)
- [SC 1.3.1 (iv) Regions](references/reviewers/sc-1-3-1-iv-regions.md)
- [SC 1.3.1 (v) Groups](references/reviewers/sc-1-3-1-v-groups.md)
- [SC 1.3.5 Identify Input Purpose](references/reviewers/sc-1-3-5-identify-input.md)
- [SC 1.4.3 Contrast (Minimum)](references/reviewers/sc-1-4-3-contrast.md)

### Operable

- [SC 2.1.1 Keyboard](references/reviewers/sc-2-1-1-keyboard.md)
- [SC 2.4.4 Link Purpose](references/reviewers/sc-2-4-4-link-purpose.md)
- [SC 2.4.6 Headings and Labels](references/reviewers/sc-2-4-6-headings-labels.md)
- [SC 2.5.1 Pointer Gestures](references/reviewers/sc-2-5-1-pointer-gestures.md)
- [SC 2.5.2 Pointer Cancellation](references/reviewers/sc-2-5-2-pointer-cancellation.md)
- [SC 2.5.3 Label in Name](references/reviewers/sc-2-5-3-label-in-name.md)
- [SC 2.5.7 Dragging Movements](references/reviewers/sc-2-5-7-dragging-movement.md)

### Understandable

- [SC 3.2.1 On Focus](references/reviewers/sc-3-2-1-on-focus.md)
- [SC 3.2.2 On Input](references/reviewers/sc-3-2-2-on-input.md)
- [SC 3.3.1 Error Identification](references/reviewers/sc-3-3-1-error-identification.md)
- [SC 3.3.2 Labels or Instructions](references/reviewers/sc-3-3-2-labels-instructions.md)
- [SC 3.3.3 Error Suggestion](references/reviewers/sc-3-3-3-error-suggestion.md)

### Robust

- [SC 4.1.2 (i) Name](references/reviewers/sc-4-1-2-i-name.md)
- [SC 4.1.2 (ii) Role](references/reviewers/sc-4-1-2-ii-role.md)
- [SC 4.1.2 (iii) Value](references/reviewers/sc-4-1-2-iii-value.md)

### Vision-Assisted Review

When component screenshots or design mocks are available, augment the
source-code review with these vision-level reviewers. Each reference covers
image-based evaluation for the corresponding Success Criterion — contrast
ratios, color dependence, resize/reflow behavior, and non-text content
identification from pixels rather than from the DOM.

- [SC 1.1.1 Non-text Content (vision)](references/vision/sc-1-1-1-non-text-content.md)
- [SC 1.4.1 Use of Color (vision)](references/vision/sc-1-4-1-use-of-color.md)
- [SC 1.4.3 Contrast (vision)](references/vision/sc-1-4-3-contrast.md)
- [SC 1.4.10 Reflow (vision)](references/vision/sc-1-4-10-resize-reflow.md)
- [SC 1.4.11 Non-text Contrast (vision)](references/vision/sc-1-4-11-non-text-contrast.md)

## Review Output

For each Success Criterion you evaluated, report violations found. If no
violations exist for a criterion, return an empty list for that criterion.
