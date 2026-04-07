---
name: validating-slds
description: >-
  Audit Lightning Web Components for SLDS compliance and produce a scored quality
  report. Runs the SLDS linter, analyzes CSS for theming hook usage and pairing,
  checks HTML for accessibility attributes, and scores findings across categories
  into an overall grade. Use when asked to "score my component", "SLDS scorecard",
  "quality report", "audit SLDS compliance", "how good is my SLDS", "check
  component quality", "rate my component", "evaluate my component", "is this
  component ready to ship?", "look at my LWC for issues", "audit this before I
  submit", "review my component before code review", or any time a user wants a
  quality assessment or production-readiness check on an LWC or SLDS component.
  Not for fixing violations (use slds-uplift) or building new components (use
  slds-authoring).
---

# SLDS Quality Audit

Audit Lightning Web Components for SLDS compliance and produce a scored quality scorecard. Combines SLDS linter output with supplementary static analysis to catch what the linter misses.

## Scope

Also valid for: auditing SLDS compliance across a project or component set, and before/after quality comparison after making changes.

Not for:
- **Fixing** linter violations — use `slds-uplift` instead
- **Building** new components — use `slds-authoring` instead
- **Just running the linter** — run `npx @salesforce-ux/slds-linter@latest lint .` directly
- **Full WCAG accessibility audit** — this skill checks attribute presence only (labels, alt text, focus indicators), not contrast ratios, keyboard flows, or screen reader behavior

---

## Quality Validation Process

```
1. Run SLDS Linter    → Collect violation counts (linter's job)
2. Run Analyze Script  → Check what linter doesn't cover (supplementary)
3. Agent Review        → Manual review prompts (not automatable)
4. Score & Grade       → Combine linter + script + review findings
5. Generate Report     → Produce formatted scorecard
```

## Step 1: Run SLDS Linter

Run the linter to collect baseline violation data:

```bash
npx @salesforce-ux/slds-linter@latest lint <component-path> 2>&1
```

Count violations by rule. These feed directly into the **Linter Compliance** score:

| Rule | Impact |
|------|--------|
| `slds/class-override` | Breaks theming, dark mode |
| `slds/lwc-token-to-slds-hook` | SLDS 1 technical debt |
| `slds/no-hardcoded-values` | Breaks theming, accessibility |

**Linter Compliance Score** = `100 - (total_violations × 10)`, minimum 0.

**If the linter is unavailable** (no Node.js, no network access, CI sandbox restrictions): skip this step, note "Linter not run" in the report header, mark Linter Compliance as N/A, and compute the Overall score using the remaining 4 categories renormalized to 100%:

```
Overall (linter unavailable) = (Theming × 0.29) + (Accessibility × 0.29)
                              + (CodeQuality × 0.21) + (ComponentUsage × 0.21)
```

## Step 2: Run Supplementary Analysis

Run the analyze script to catch issues the linter doesn't cover:

```bash
node scripts/analyze-quality.cjs <component-path>
```

The script outputs JSON with findings organized by severity. It checks:

### CSS Checks (linter-complementary)

| Check | What It Catches | Severity |
|-------|----------------|----------|
| Missing fallbacks | `var(--slds-g-*)` without a fallback value | Critical |
| Invented hooks (T051) | `--slds-g-*` tokens not found in `hooks-index.json` | Critical |
| Hook pairing | Background hooks without matching foreground hooks | Warning |
| `!important` | Specificity overrides | Warning |
| Magic pixel values | Hardcoded `px` not using spacing hooks | Info |
| High z-index | z-index values > 99 | Warning |
| Outline removal | `outline: none` without alternative focus style | Warning |

### JS Checks

| Check | What It Catches | Severity |
|-------|----------------|----------|
| Inline style assignment | `.style.*=` direct property assignment | Warning |
| SLDS class manipulation | Dynamic `.classList.add('slds-*')` manipulation | Info |

### HTML Checks

| Check | What It Catches | Severity |
|-------|----------------|----------|
| LBC input labels | `<lightning-input>` without `label` attribute | Critical |
| Icon alt text | `<lightning-icon>` without `alternative-text` | Critical |
| Image alt text | `<img>` without `alt` | Critical |
| Heading hierarchy | Skipped heading levels (h2 to h4) | Warning |
| Positive tabindex | `tabindex` values other than 0 or -1 | Warning |
| Clickable divs | `<div onclick>` instead of `<button>` | Warning |
| Inline styles | `style="..."` attributes | Warning |
| Native elements | `<input>`, `<button>`, `<select>` where LBC alternatives exist | Info |

### Hook Pairing Validation

The script checks that background/foreground hooks are semantically paired:

```
surface-* backgrounds     → on-surface-* text
surface-container-* bg    → on-surface-* text
accent-* backgrounds      → on-accent-* text
accent-container-* bg     → on-accent-container-* text
```

> **Limitation:** Hook pairing is checked at the file level, not per-selector. A file with `surface-1` in `.classA` and `on-accent-1` in `.classB` would pass because both surface and accent families are present. Review pairing correctness per-selector during manual review (Step 3).

### Invented Hook Detection (T051)

The script cross-references every `--slds-g-*` token in CSS against `hooks-index.json`. Any hook not found in metadata is flagged as critical — this catches the most common agent mistake of inventing hooks from naming patterns.

## Step 3: Agent Manual Review

These checks require understanding the component's purpose and cannot be automated reliably. Review each and note findings as additional context in the report.

| Review Area | What to Look For |
|-------------|-----------------|
| Loading states | Does the component show a spinner or skeleton when fetching data? |
| Error states | Are errors surfaced to the user with actionable messages? |
| Empty states | Is there a meaningful empty state when no data exists? |
| Disabled states | Do interactive elements visually and functionally handle disabled? |
| Semantic HTML | Are `<nav>`, `<article>`, `<section>` used where appropriate? |
| SLDS blueprint compliance | Do cards, modals, forms follow SLDS blueprint structure? |

> These are not scored. Note relevant findings in the "Recommendations" section of the report.

## Step 4: Calculate Quality Scores

### Component Complexity

Before scoring, classify the component to give the score context:

| Complexity | Criteria | Report Note |
|------------|----------|-------------|
| Small | 1-2 files, < 100 total lines | Score is high-confidence (small surface area) |
| Medium | 3-6 files, 100-500 total lines | Score reflects typical component |
| Large | 7+ files, 500+ total lines | Score reflects absolute issue count — even well-built large components may score lower |

Include the complexity classification in the report header. This prevents misreading a "B" on a 1000-line component vs. a "B" on a 20-line component.

### Scoring Formula

```
Category Score = 100 - (critical_issues × 10) - (warnings × 3) - (info × 1)
Minimum score: 0
```

### Categories and Weights

| Category | Weight | Source |
|----------|--------|--------|
| Linter Compliance | 30% | SLDS linter output (Step 1) |
| Theming | 20% | Script: fallbacks, hook pairing (Step 2) |
| Accessibility | 20% | Script: labels, alt text, focus (Step 2) |
| Code Quality | 15% | Script: !important, inline styles, z-index (Step 2) |
| Component Usage | 15% | Script: native elements, semantic HTML (Step 2) |

### Overall Score

```
Overall = (Linter × 0.30) + (Theming × 0.20) + (Accessibility × 0.20)
        + (CodeQuality × 0.15) + (ComponentUsage × 0.15)
```

### Grade Thresholds

| Score | Grade | Status |
|-------|-------|--------|
| 90-100 | A | Excellent - Ready for production |
| 80-89 | B | Good - Minor improvements suggested |
| 70-79 | C | Acceptable - Address issues before deployment |
| 60-69 | D | Needs Work - Significant issues to resolve |
| 0-59 | F | Failing - Critical issues blocking deployment |

## Step 5: Generate Quality Report

Use the template in **[report-format.md](references/report-format.md)** to produce the final report. Default to the **compact format** for initial output and expand sections on request.

The report includes:
- Executive summary with overall grade
- Scores by category with visual indicators
- Detailed findings organized by severity
- Specific code locations and recommendations
- Checklist of required actions

---

## Quick Validation Mode

For a rapid quality check without full analysis:

1. Run linter: `npx @salesforce-ux/slds-linter@latest lint <path>`
2. Count violations by type
3. Report summary only

```
Quick Quality Check: <component-name>
─────────────────────────────────────
Linter Violations:
  • Class Override:     0
  • Deprecated Tokens:  3
  • Hardcoded Values:   5

Quick Grade: C (estimated)
Run full validation for detailed report.
```

---

## Edge Cases and False Positives

| Situation | Guidance |
|-----------|----------|
| **Headless components** (JS-only, no HTML) | Skip HTML checks; score only CSS + linter categories |
| **Wrapper/container components** | May legitimately have minimal CSS; don't penalize low hook usage |
| **Intentional native elements** | `<button>` inside custom SLDS blueprints is correct; suppress C002 if inside an `slds-*` blueprint structure |
| **Components outside LEX** | LWR/Experience Cloud components may not use Lightning Base Components; note context in report |
| **Test/demo components** | Lower the bar — note in report but don't block on warnings |

If a check produces a false positive, note it in the report as "suppressed" with justification rather than silently dropping it.

---

## References

- **[Quality Checks](references/quality-checks.md)** - Complete list of all quality checks with detection patterns
- **[Report Format](references/report-format.md)** - Quality report template and formatting guide
- **[Analyze Script](scripts/analyze-quality.cjs)** - Automated analysis for linter-complementary checks
- **[SLDS Uplift Skill](../slds-uplift/SKILL.md)** - How to fix linter violations
- **[SLDS Applying Skill](../applying-slds/SKILL.md)** - Guide for building new components with correct patterns
