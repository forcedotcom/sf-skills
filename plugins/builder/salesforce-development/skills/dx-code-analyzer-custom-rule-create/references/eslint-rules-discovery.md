# ESLint Rules Discovery & Configuration

**READ THIS FIRST** for ANY ESLint request. 90% of ESLint rules already exist — this guide shows you how to find and configure them instead of creating custom plugins.

---

## Three Tiers of ESLint Rules

| Tier | What It Is | When to Use | Effort | Coverage |
|---|---|---|---|---|
| **Tier 1: Built-In Rules** | 200+ core ESLint rules | First choice — check here FIRST | LOW (enable in config) | 70% of requests |
| **Tier 2: Configurable Rules** | no-restricted-syntax, no-restricted-globals, no-restricted-properties | When no built-in rule exists but pattern is generic | MEDIUM (AST selector) | 20% of requests |
| **Tier 3: Custom Plugins** | Write your own ESLint plugin | LAST RESORT — domain-specific multi-node patterns only | HIGH (Node code, testing) | 10% of requests |

**Always start at Tier 1 and work down.**

---

## Tier 1: Discover Built-In Rules

### Discovery Workflow (MANDATORY)

Before creating ANY custom ESLint rule:

1. **Run:** `sf code-analyzer rules --rule-selector eslint`
2. **Search output** for keywords from the user's request:
   - User says "ban console.log" → search for "console"
   - User says "enforce ===" → search for "equal" or "strict"
   - User says "no unused variables" → search for "unused"
3. **Check naming patterns:**
   - `no-*` — Disallow something (no-console, no-debugger, no-eval)
   - `prefer-*` — Prefer one style (prefer-const, prefer-arrow-callback)
   - `require-*` — Require something (require-await, require-yield)
   - `@lwc/lwc/*` — LWC-specific rules (no-inner-html, no-document-query)
4. **If found:** Configure it (see "Configuration Workflow" below). **STOP — do NOT create a custom plugin.**
5. **If NOT found:** Proceed to Tier 2.

### Common Built-In Rules by Category

#### Code Quality
| User Request | Rule Name | Config Example |
|---|---|---|
| "No unused variables" | `no-unused-vars` | `"no-unused-vars": "error"` |
| "No unused imports" | `no-unused-vars` | Same rule covers imports |
| "Require await in async functions" | `require-await` | `"require-await": "error"` |
| "No empty blocks" | `no-empty` | `"no-empty": "error"` |
| "No unreachable code" | `no-unreachable` | `"no-unreachable": "error"` |

#### Security
| User Request | Rule Name | Config Example |
|---|---|---|
| "Ban eval()" | `no-eval` | `"no-eval": "error"` |
| "Ban debugger" | `no-debugger` | `"no-debugger": "error"` |
| "No implied eval" | `no-implied-eval` | `"no-implied-eval": "error"` |
| "Ban alert()" | `no-alert` | `"no-alert": "error"` |

#### Best Practices
| User Request | Rule Name | Config Example |
|---|---|---|
| "Enforce ===" | `eqeqeq` | `"eqeqeq": ["error", "always"]` |
| "Prefer const" | `prefer-const` | `"prefer-const": "error"` |
| "No var" | `no-var` | `"no-var": "error"` |
| "Prefer arrow functions" | `prefer-arrow-callback` | `"prefer-arrow-callback": "error"` |
| "Require default in switch" | `default-case` | `"default-case": "error"` |

#### Logging/Debugging
| User Request | Rule Name | Config Example |
|---|---|---|
| "Ban console.log" | `no-console` | `"no-console": "error"` |
| "Ban console.* except error" | `no-console` | `"no-console": ["error", { "allow": ["error", "warn"] }]` |

### LWC Plugin Rules (Check if Available)

If Code Analyzer has `@lwc/eslint-plugin-lwc` enabled:

| User Request | Rule Name | Notes |
|---|---|---|
| "Ban innerHTML" | `@lwc/lwc/no-inner-html` | XSS prevention |
| "No document.querySelector" | `@lwc/lwc/no-document-query` | Use template queries |
| "Validate @api usage" | `@lwc/lwc/no-api-reassignments` | Prevents reassigning @api properties |
| "Validate @wire syntax" | `@lwc/lwc/valid-wire` | Built-in |
| "No async in getters" | `@lwc/lwc/no-async-operation` | Lifecycle hook validation |

**Check availability:**
```bash
sf code-analyzer rules --rule-selector eslint | grep -i "@lwc"
```

### External Documentation

- **All ESLint built-in rules:** https://eslint.org/docs/latest/rules/
- **LWC ESLint plugin:** https://github.com/salesforce/eslint-plugin-lwc
- **Salesforce Lightning plugin:** https://github.com/forcedotcom/eslint-plugin-lightning

---

## Configuration Workflow (Tier 1)

When a built-in rule exists:

1. **Create `eslint.config.js`** if it doesn't exist:
   ```javascript
   module.exports = [
     {
       files: ["**/lwc/**/*.js"],  // or ["**/*.js"] for all JS files
       rules: {
         // Rules go here
       }
     }
   ];
   ```

2. **Add the rule** with desired severity:
   ```javascript
   rules: {
     "no-console": "error",              // Ban completely
     "eqeqeq": ["error", "always"],      // With options
     "no-unused-vars": ["warn"]          // Warning instead of error
   }
   ```

3. **Update `code-analyzer.yml`** (AFTER file exists):
   ```yaml
   engines:
     eslint:
       eslint_config_file: "eslint.config.js"
   ```

4. **Validate:**
   ```bash
   sf code-analyzer rules --rule-selector eslint:no-console
   ```
   If the rule does NOT appear in the output, the config is wrong. Do NOT proceed to testing.

5. **Test positive:**
   ```bash
   sf code-analyzer run --rule-selector eslint:no-console --target lwc/
   ```

6. **Test negative:** Run against clean code, confirm 0 violations.

---

## Tier 2 and Tier 3: Configurable Rules and Custom Plugins

For detailed information on these tiers:

| Tier | File | When to Use |
|------|------|-------------|
| **Tier 2: Configurable Rules** | [eslint-tier2-configurable.md](eslint-tier2-configurable.md) | no-restricted-globals, no-restricted-syntax, no-restricted-properties — ban specific patterns without writing plugins |
| **Tier 3: Custom Plugins** | [eslint-tier3-custom-plugins.md](eslint-tier3-custom-plugins.md) | Complete examples for all tiers + when to create custom plugins (LAST RESORT) |

---

## Decision Tree

```text
User asks for ESLint rule
    ↓
Run: sf code-analyzer rules --rule-selector eslint
    ↓
Search output for keywords
    ↓
    ├─ Built-in rule found? → Configure it (Tier 1) → DONE ✅
    │
    ├─ Pattern is "ban function X"? → Use no-restricted-globals (Tier 2) → DONE ✅
    │
    ├─ Pattern is "ban syntax Y"? → Use no-restricted-syntax (Tier 2) → DONE ✅
    │
    └─ Complex multi-node pattern? → Create custom plugin (Tier 3) → See eslint-custom-plugins.md
```

---

## Key Rules

1. **ALWAYS run discovery FIRST** — 90% of requests are Tier 1 or Tier 2
2. **NEVER create a custom plugin without checking built-in rules** — this is a skill failure
3. **VALIDATE after configuration** — `sf code-analyzer rules --rule-selector eslint:<name>` must show the rule
4. **TEST both positive and negative samples** — confirm violations are caught AND clean code passes

---

## When to Read Other References

- **All ESLint requests start here** (discovery)
- **If Tier 3 custom plugin needed:** Read `references/eslint-custom-plugins.md`
- **If troubleshooting config issues:** Read `references/troubleshooting.md` (ESLint section)
