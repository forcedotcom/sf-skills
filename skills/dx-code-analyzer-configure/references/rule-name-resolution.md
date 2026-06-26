# Rule Name Resolution (Fuzzy Matching)

**⚠️ CRITICAL:** The `rules` section in `code-analyzer.yml` requires the EXACT full rule name as it appears in Code Analyzer's rule registry. A misspelled or partial name will be silently ignored — the override won't apply, and no error is shown.

## Why This Matters

Unlike `--rule-selector` (which returns 0 results on mismatch), a wrong name in `code-analyzer.yml` is SILENTLY ignored. The config validates fine, but the override simply doesn't apply. This makes typos and partial names dangerous.

## Common Fuzzy → Exact Mappings

Users will often refer to rules by approximate, partial, or descriptive names:

| User Says | Exact Rule Name | Engine |
|-----------|----------------|--------|
| "the ApexDoc rule" | `ApexDoc` | `pmd` |
| "no-console" | `no-console` | `eslint` |
| "CRUD violation" | `ApexCRUDViolation` | `pmd` |
| "hardcoded values" | `@salesforce-ux/slds/no-hardcoded-values-slds2` | `eslint` |
| "unused variables" | `no-unused-vars` | `eslint` |
| "soql injection" | `ApexSOQLInjection` | `pmd` |
| "global modifier" | `AvoidGlobalModifier` | `pmd` |
| "empty catch" | `EmptyCatchBlock` | `pmd` |

## Lookup Procedure

When you are NOT 100% certain of the exact full rule name:

1. **Do NOT guess** — a wrong name silently fails (the override is ignored with no error)
2. **Look up the rule first** using the `sf code-analyzer rules` command with grep:
   ```bash
   sf code-analyzer rules --rule-selector all 2>&1 | grep -i "<USER_KEYWORD>"
   ```
3. **If grep returns exactly one match** → use that exact rule name in the YAML
4. **If grep returns multiple matches** → present them to the user and ask which one they meant
5. **If grep returns 0 matches** → try broader keywords or tell the user no rule matched

## When You CAN Skip the Lookup

Skip only when confident in the exact name:
- User provides the full exact name (e.g., "ApexCRUDViolation", "no-unused-vars")
- The rule is extremely common AND unambiguous (e.g., "ApexDoc", "no-console")

## Matching Strategies for Ambiguous Input

| User Says | Grep Command | Notes |
|-----------|-------------|-------|
| "the doc rule" | `grep -i "doc"` | May match ApexDoc, JSDoc, etc. — ask user if multiple |
| "CRUD" | `grep -i "crud"` | Likely matches ApexCRUDViolation |
| "hardcoded" | `grep -i "hardcoded"` | May match multiple SLDS/custom rules |
| "console" | `grep -i "console"` | Likely matches no-console |
| "security rules" | Use `--rule-selector all:Security` | Category-based, not name-based |
| "the injection rule" | `grep -i "injection"` | May match ApexSOQLInjection, ApexXSSFromURLParam, etc. |
| "unused" | `grep -i "unused"` | May match no-unused-vars, UnusedLocalVariable, etc. |

## Identifying the Engine

The YAML structure requires nesting under the correct engine. Always extract BOTH the engine and rule name from the `sf code-analyzer rules` output:

```yaml
rules:
  <engine>:      # ← must match the engine that owns the rule
    <rule_name>:
      severity: ...
      disabled: ...
```

The output of `sf code-analyzer rules` shows engine name alongside each rule. Use that to determine the correct YAML path.
