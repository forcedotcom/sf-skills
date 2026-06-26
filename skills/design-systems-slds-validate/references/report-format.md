# SLDS Quality Report Format

Guidelines for generating quality reports. **Default to the compact format** and expand sections when the user requests detail.

---

## Default: Compact Report

Always start with this format. It gives the user the full picture in a glanceable summary.

````markdown
# SLDS Quality Scorecard: `{component-name}`

**Path:** `{component-path}` | **Complexity:** {small|medium|large} ({n} files, {n} lines)
**Generated:** {date}

## Automated Grade: {grade} ({score}/100)

{grade-description}

**Manual Review Gate:** {Pass|Advisory|Blocking}
**Final Recommendation:** {Ready for production|Ready with follow-ups|Needs work|Failing}

| Category | Score | Grade |
|----------|-------|-------|
| Linter Compliance | {score}/100 | {status-emoji} {grade} |
| Theming | {score}/100 | {status-emoji} {grade} |
| Accessibility | {score}/100 | {status-emoji} {grade} |
| Code Quality | {score}/100 | {status-emoji} {grade} |
| Component Usage | {score}/100 | {status-emoji} {grade} |

**Issues:** {n} critical | {n} warnings | {n} info

### Top Issues

1. **{issue}** — `{file}:{line}` — {recommendation}
2. **{issue}** — `{file}:{line}` — {recommendation}
3. **{issue}** — `{file}:{line}` — {recommendation}

> Automated score reflects linter + script findings only. Manual review can still block ship.
>
> {accessibility-disclaimer-if-scored}

*Ask for the full report to see all findings, code examples, and action items.*
````

### When to Show Compact

- First response to a quality audit request
- Quick validation mode
- Auditing multiple components (show compact for each)

---

## Expanded: Full Report

Show this when the user asks to "expand", "show details", "full report", or "show all findings". Build on top of the compact report — don't repeat the summary, just add the detail sections below it.

````markdown
---

## Critical Issues ({count})

Issues that **must be fixed** before deployment.

### {issue-category}

| # | File | Line | Issue | Recommendation |
|---|------|------|-------|----------------|
| 1 | `{file}` | {line} | {description} | {fix} |
| 2 | `{file}` | {line} | {description} | {fix} |

**Example fix:**
```css
/* Before */
{problematic-code}

/* After */
{fixed-code}
```

---

## Warnings ({count})

Issues that **should be fixed** but are not blocking.

| # | File | Line | Issue | Impact |
|---|------|------|-------|--------|
| 1 | `{file}` | {line} | {description} | {impact} |

---

## Info ({count})

Suggestions for improvement.

| # | Category | Finding | Suggestion |
|---|----------|---------|------------|
| 1 | {category} | {finding} | {suggestion} |

---

## Detailed Findings

### Manual Review Gate

**Gate:** {Pass|Advisory|Blocking}

| Review Area | Outcome | Notes |
|-------------|---------|-------|
| Loading states | {Pass|Advisory|Blocking} | {notes} |
| Error states | {Pass|Advisory|Blocking} | {notes} |
| Empty states | {Pass|Advisory|Blocking} | {notes} |
| Disabled states | {Pass|Advisory|Blocking} | {notes} |
| Semantic HTML | {Pass|Advisory|Blocking} | {notes} |
| Blueprint compliance | {Pass|Advisory|Blocking} | {notes} |

---

### Linter Compliance

**Violations Found:** {count}

| Rule | Count | Files Affected |
|------|-------|----------------|
| `slds/class-override` | {count} | {files} |
| `slds/lwc-token-to-slds-hook` | {count} | {files} |
| `slds/no-hardcoded-values` | {count} | {files} |

<details>
<summary>Full Linter Output</summary>

```
{linter-output}
```

</details>

---

### Theming

**Hooks Usage Summary:**

| Hook Type | Used | Missing Fallback | Issues |
|-----------|------|------------------|--------|
| Color Hooks | {count} | {count} | {count} |
| Spacing Hooks | {count} | {count} | {count} |
| Typography Hooks | {count} | {count} | {count} |

**Hook Pairing Analysis:**

| Background Hook | Paired Text Hook | Status |
|-----------------|------------------|--------|
| `--slds-g-color-surface-1` | `--slds-g-color-on-surface-2` | {status} |

---

### Accessibility

> This section checks attribute presence only. It does not validate contrast ratios, keyboard flows, or screen reader behavior. Passing here does not guarantee WCAG compliance.

| Check | Status | Details |
|-------|--------|---------|
| Lightning input labels | {status} | {count} inputs, {count} labeled |
| Icon alternative text | {status} | {count} icons, {count} with alt |
| Image alt attributes | {status} | {count} images, {count} with alt |
| Heading hierarchy | {status} | {sequence} |
| Focus indicators | {status} | {findings} |

---

### Code Quality

| Metric | Value | Status |
|--------|-------|--------|
| Total CSS lines | {count} | {status} |
| !important usage | {count} | {status} |
| Inline styles | {count} | {status} |
| High z-index values | {count} | {status} |

---

### Component Usage

| Element Type | Native Count | LBC Alternative | Recommendation |
|--------------|-------------|-----------------|----------------|
| Inputs | {count} | `<lightning-input>` | {recommendation} |
| Buttons | {count} | `<lightning-button>` | {recommendation} |
| Selects | {count} | `<lightning-combobox>` | {recommendation} |

---

## Action Items

### Must Fix (Critical)

- [ ] {action-item}

### Should Fix (Warnings)

- [ ] {action-item}

### Nice to Have (Info)

- [ ] {action-item}

---

## Next Steps

1. Address all **{count} critical issues** immediately
2. Review and fix **{count} warnings** before code review
3. Consider **{count} suggestions** for future improvements
4. Re-run validation to confirm fixes

**Estimated Effort:** {estimate}
````

---

## JSON Output

For programmatic consumption (e.g., CI integration or tracking over time). Produce this only when explicitly requested or when auditing multiple components for comparison.

```json
{
  "component": "{component-name}",
  "path": "{component-path}",
  "timestamp": "{iso-date}",
  "complexity": {
    "classification": "medium",
    "totalFiles": 4,
    "totalLines": 280
  },
  "scores": {
    "automatedOverall": 85,
    "automatedGrade": "B",
    "categories": {
      "linter": { "score": 100, "grade": "A" },
      "theming": { "score": 80, "grade": "B" },
      "accessibility": { "score": 75, "grade": "C" },
      "codeQuality": { "score": 90, "grade": "A" },
      "componentUsage": { "score": 85, "grade": "B" }
    }
  },
  "manualReview": {
    "gate": "Advisory",
    "findings": []
  },
  "finalRecommendation": "Ready with follow-ups",
  "findings": {
    "critical": [],
    "warnings": [],
    "info": []
  },
  "summary": {
    "filesAnalyzed": 4,
    "totalLines": 280,
    "critical": 0,
    "warnings": 2,
    "info": 3
  }
}
```

---

## Status Indicators

| Score Range | Emoji | Meaning |
|-------------|-------|---------|
| 90-100 | ✅ | Excellent |
| 80-89 | 🟢 | Good |
| 70-79 | 🟡 | Acceptable |
| 60-69 | 🟠 | Needs Work |
| 0-59 | 🔴 | Critical |

---

## Grade Descriptions

| Grade | Description |
|-------|-------------|
| A | **Excellent** - Strong automated result. Requires a passing manual review gate before calling it production-ready. |
| B | **Good** - Solid automated result. Requires manual review before a production recommendation. |
| C | **Acceptable** - Automated issues should be addressed before production. |
| D | **Needs Work** - Significant automated issues require attention before code review. |
| F | **Critical** - Automated checks found blocking issues. Not suitable for deployment. |

---

## Report Delivery Guidelines

1. **Always default to compact** — show the scorecard first, expand on request
2. **Separate automated grade from final recommendation** — manual review can override ship readiness
3. **Group by severity** — critical issues first, then warnings, then info
4. **Include actionable recommendations** — every finding should have a clear fix
5. **Provide code examples** — show before/after for complex fixes in the expanded report
6. **Note complexity** — a "B" on a large component means something different than a "B" on a small one
7. **Add accessibility disclaimer** — when the accessibility score is included, note it checks attribute presence only
