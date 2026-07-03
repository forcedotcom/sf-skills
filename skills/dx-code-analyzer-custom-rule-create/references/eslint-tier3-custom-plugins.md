# ESLint Tier 3: Custom Plugins

[← Back to ESLint Rules Discovery](eslint-rules-discovery.md)

## Tier 3: Custom Plugins (LAST RESORT)

Only create a custom ESLint plugin when:
- ❌ No built-in rule exists (checked Tier 1)
- ❌ No configurable rule can express the pattern (checked Tier 2 — see [eslint-tier2-configurable.md](eslint-tier2-configurable.md))
- ✅ The pattern requires checking multiple AST nodes with complex logic
- ✅ The pattern is domain-specific to your codebase

**Examples that justify custom plugins:**
- "Flag LWC components with @api properties but no input validation in connectedCallback"
- "Detect imperative Apex calls without error handling (import + .then() without .catch())"
- "Enforce naming conventions on specific decorator patterns"

**See:** [eslint-custom-plugins.md](eslint-custom-plugins.md) for the plugin creation guide.

---

## Tier-by-Tier Worked Examples

Tier 2 worked examples (banning globals, restricting syntax, restricting properties) live in [eslint-tier2-configurable.md](eslint-tier2-configurable.md). The examples below cover Tier 1 (built-in rules and the LWC plugin) so the discovery → configure → validate flow is documented end-to-end.

### Example 1: "Ban console.log" (Tier 1 — built-in)

**User Request:** "Create a rule to ban console.log in LWC"

**Discovery:**
```bash
$ sf code-analyzer rules --rule-selector eslint | grep -i console
eslint:no-console  disallow the use of console
```

**Result:** Built-in rule exists. ✅

**Configuration:**
```javascript
// eslint.config.js
module.exports = [
  {
    files: ["**/lwc/**/*.js"],
    rules: {
      "no-console": "error"
    }
  }
];
```

**Validation:**
```bash
sf code-analyzer rules --rule-selector eslint:no-console
# Should show: eslint:no-console | error | ...
```

**Test:**
```bash
sf code-analyzer run --rule-selector eslint:no-console --target lwc/
```

---

### Example 2: "Ban innerHTML" (Tier 1 — LWC plugin)

**User Request:** "Ban innerHTML in LWC for XSS prevention"

**Discovery:**
```bash
$ sf code-analyzer rules --rule-selector eslint | grep -i inner
@lwc/lwc/no-inner-html  disallow use of innerHTML
```

**Result:** LWC plugin rule exists. ✅

**Configuration:**
```javascript
// eslint.config.js
module.exports = [
  {
    files: ["**/lwc/**/*.js"],
    rules: {
      "@lwc/lwc/no-inner-html": "error"
    }
  }
];
```

**Validation:**
```bash
sf code-analyzer rules --rule-selector eslint:@lwc/lwc/no-inner-html
```

---

### Example 3: "Enforce === over ==" (Tier 1 — built-in)

**User Request:** "Enforce strict equality checks"

**Discovery:**
```bash
$ sf code-analyzer rules --rule-selector eslint | grep -i equal
eslint:eqeqeq  require the use of === and !==
```

**Result:** Built-in rule `eqeqeq` exists. ✅

**Configuration:**
```javascript
rules: {
  "eqeqeq": ["error", "always"]
}
```
