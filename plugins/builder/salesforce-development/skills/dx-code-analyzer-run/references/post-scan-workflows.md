# Post-Scan Workflows

After presenting initial scan results (Step 5), the user may ask follow-up questions to explore results or understand violations. This reference covers three post-scan workflows:

1. **Result Querying** — filter/drill into existing results without re-scanning
2. **Rule Description** — explain what a rule does and how to fix violations
3. **Rule Listing** — browse available rules without running a scan

---

## Result Querying (Step 7)

### When to Use

Trigger this workflow when the user asks to explore existing results:
- "Show me just the security violations"
- "What's in AccountService.cls?"
- "Show only PMD issues"
- "Filter to severity 1 and 2"
- "What ESLint rules fired?"
- "Show violations in the lwc folder"
- "Top 20 by file"

### How It Works

The `query-results.js` script re-filters the SAME results JSON file (from Step 4) with different criteria. No re-scan is needed — it is instant.

### Script Reference

```bash
node "<skill_dir>/scripts/query-results.js" "<results-file.json>" [options]
```

**Filter options (combine any):**

| Option | Description | Example |
|--------|-------------|---------|
| `--engine <name>` | Filter by engine | `--engine pmd` |
| `--severity <n>` | Filter by severity (comma-separated) | `--severity 1,2` |
| `--category <tag>` | Filter by category/tag | `--category Security` |
| `--rule <name>` | Filter by exact rule name | `--rule ApexCRUDViolation` |
| `--file <substring>` | Filter by file path substring | `--file AccountService` |
| `--top <n>` | Return top N results (default: 10) | `--top 20` |
| `--sort <field>` | Sort by: severity, rule, engine, file | `--sort file` |
| `--sort-dir <dir>` | Sort direction: asc, desc | `--sort-dir desc` |
| `--summary` | Show only counts (no individual violations) | `--summary` |

**Options can be combined freely:**
```bash
# Security violations in PMD, top 5
node "<skill_dir>/scripts/query-results.js" "./results.json" --engine pmd --category Security --top 5

# All Critical+High in a specific file
node "<skill_dir>/scripts/query-results.js" "./results.json" --severity 1,2 --file AccountService.cls

# Summary of ESLint issues only
node "<skill_dir>/scripts/query-results.js" "./results.json" --engine eslint --summary
```

### Output Format

The script outputs JSON with this structure:

```json
{
  "query": { "engine": "pmd", "severity": [1,2], ... },
  "totalViolations": 500,
  "totalMatches": 23,
  "severityCounts": { "1": 5, "2": 18, "3": 0, "4": 0, "5": 0 },
  "topRules": [{ "rule": "ApexCRUDViolation", "engine": "pmd", "count": 12 }, ...],
  "topFiles": [{ "file": "AccountService.cls", "count": 8 }, ...],
  "violations": [
    { "rule": "...", "engine": "...", "severity": 1, "message": "...", "file": "...", "startLine": 42, "tags": [...] },
    ...
  ]
}
```

When `--summary` is used, the `violations` array is omitted.

### Presentation Rules

Present query results using the same format as Step 5, but with a header indicating the active filter:

```
## Filtered Results: [description of filter]

**X matches** out of Y total violations.

| Severity | Count |
|----------|-------|
| Critical (1) | X |
| High (2) | X |
| ... |

### Matching Violations
| # | Rule | Engine | Sev | File | Line |
|---|------|--------|-----|------|------|
| 1 | ... | ... | ... | ... | ... |

### Top Rules (within filter)
| Rule | Engine | Count |
|------|--------|-------|
| ... | ... | ... |

Full results: `<original-results-file>`
```

### Follow-Up Offers

After presenting filtered results, offer:
- "Want me to narrow further?" (add more filters)
- "Want me to explain any of these rules?" (→ Step 8)
- "Want me to apply fixes for these?" (→ Step 6, scoped to matched rules)

---

## Rule Description (Step 8)

### When to Use

Trigger this workflow when the user asks about a specific rule:
- "What is ApexCRUDViolation?"
- "Explain this rule"
- "What does no-var mean?"
- "How do I fix OperationWithLimitsInLoop?"
- "Tell me about the ApexSOQLInjection rule"
- "Why is this flagged?"

### How It Works

The `describe-rule.js` script calls `sf code-analyzer rules` with a targeted selector to extract rule metadata including description and documentation links.

### Script Reference

```bash
node "<skill_dir>/scripts/describe-rule.js" "<rule-name>" [--engine <engine>]
```

**Arguments:**

| Argument | Description | Example |
|----------|-------------|---------|
| `<rule-name>` | The rule name to look up | `ApexCRUDViolation` |
| `--engine <engine>` | Narrow to a specific engine (optional) | `--engine pmd` |

**Examples:**
```bash
node "<skill_dir>/scripts/describe-rule.js" "ApexCRUDViolation" --engine pmd
node "<skill_dir>/scripts/describe-rule.js" "no-var" --engine eslint
node "<skill_dir>/scripts/describe-rule.js" "OperationWithLimitsInLoop"
```

### Output Format

**Success — single rule found:**
```json
{
  "status": "success",
  "rule": {
    "name": "ApexCRUDViolation",
    "engine": "pmd",
    "severity": "2 (High)",
    "tags": ["Security", "Recommended", "Apex"],
    "description": "Validates that CRUD and FLS checks are performed before DML operations...",
    "resources": ["https://pmd.github.io/latest/pmd_rules_apex_security.html#apexcrudviolation"]
  }
}
```

**Multiple matches (partial name):**
```json
{
  "status": "multiple_matches",
  "message": "Rule \"CRUD\" not found as exact match. Found 3 potential matches:",
  "candidates": [
    { "name": "ApexCRUDViolation", "engine": "pmd", "severity": "2", "tags": "Security, Recommended" },
    ...
  ]
}
```

**Not found:**
```json
{
  "status": "not_found",
  "message": "Rule \"FakeRule\" not found. Verify the rule name with: sf code-analyzer rules ..."
}
```

### Presentation Rules

**For a successful lookup**, present:

```
## Rule: ApexCRUDViolation

| Property | Value |
|----------|-------|
| Engine | pmd |
| Severity | 2 (High) |
| Tags | Security, Recommended, Apex |

### Description
Validates that CRUD and FLS checks are performed before DML operations. Without these
checks, data may be accessed or modified without proper user permissions, violating
the Salesforce security model.

### How to Fix
[Provide actionable fix guidance based on the description. If the description mentions
a fix pattern, elaborate. If resources are available, include the link.]

### Resources
- [PMD Documentation](https://pmd.github.io/...)

---
Want me to show all violations of this rule in your scan results?
```

**For multiple matches**, present:

```
I found multiple rules matching "CRUD":

| # | Rule | Engine | Severity |
|---|------|--------|----------|
| 1 | ApexCRUDViolation | pmd | 2 (High) |
| 2 | ... | ... | ... |

Which rule would you like details on?
```

**For not found**, present:

```
I couldn't find a rule named "FakeRule". Would you like me to:
- Search for similar rules? (I'll grep the full rule list)
- List all rules for a specific engine or category?
```

### After Describing a Rule

Offer next steps:
- "Want me to show all violations of this rule in your results?" (→ Step 7 with `--rule`)
- "Want me to apply the engine fix for this rule?" (→ Step 6)
- "Want me to explain another rule?"

---

## Rule Listing (Step 9)

### Presentation Rules

Present available rules in this format:

```
## Available Rules: Security

**Found X rules** across Y engines.

| Engine | Count |
|--------|-------|
| pmd | 12 |
| eslint | 6 |

| Severity | Count |
|----------|-------|
| Critical (1) | 3 |
| High (2) | 15 |

### Rules (top 25)
| # | Rule | Engine | Severity | Tags |
|---|------|--------|----------|------|
| 1 | ApexCRUDViolation | pmd | 2 (High) | Security, Recommended |
| 2 | ApexSOQLInjection | pmd | 1 (Critical) | Security, Recommended |
| ... |

Want me to explain any of these rules? Or run a scan with this selector?
```

### Follow-Up Offers

After listing rules:
- "Want me to explain any of these?" (→ Step 8)
- "Want me to scan with this selector?" (→ Steps 1-5 with the same selector)
- "Narrow to just high severity?" (re-run with `--severity 1,2`)
