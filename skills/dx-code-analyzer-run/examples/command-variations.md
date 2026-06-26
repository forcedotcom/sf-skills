# Common Command Variations

Real-world command patterns with explanations. Use these as reference when building commands for specific scenarios.

---

## Basic Scans

### 1. Scan Entire Workspace (Default)
```bash
sf code-analyzer run \
  --rule-selector Recommended \
  --output-file ./code-analyzer-results-20260519-101030.json \
  --include-fixes \
  2>&1 | tee ./code-analyzer-results-20260519-101030.log
```
**When:** User says "scan my code" with no specifics.

---

### 2. Security-Focused Scan
```bash
sf code-analyzer run \
  --rule-selector "all:Security:(1,2)" \
  --output-file ./code-analyzer-results-20260519-101030.json \
  --include-fixes \
  2>&1 | tee ./code-analyzer-results-20260519-101030.log
```
**When:** User says "check for security issues", "find vulnerabilities", "AppExchange security review".  
**Selector breakdown:** `all` = all engines, `:Security` = Security category only, `:(1,2)` = Critical and High severity only.

---

### 3. Specific Engine
```bash
sf code-analyzer run \
  --rule-selector "pmd" \
  --output-file ./code-analyzer-results-20260519-101030.json \
  --include-fixes \
  2>&1 | tee ./code-analyzer-results-20260519-101030.log
```
**When:** User says "run PMD", "check my Apex code".

---

### 4. Multiple Engines
```bash
sf code-analyzer run \
  --rule-selector "(pmd,eslint)" \
  --output-file ./code-analyzer-results-20260519-101030.json \
  --include-fixes \
  2>&1 | tee ./code-analyzer-results-20260519-101030.log
```
**When:** User says "scan Apex and JavaScript", "run PMD and ESLint".  
**Selector breakdown:** Parentheses + comma = OR logic.

---

## Target-Specific Scans

### 5. Scan Specific File
```bash
sf code-analyzer run \
  --rule-selector Recommended \
  --target "force-app/main/default/classes/AccountService.cls" \
  --output-file ./code-analyzer-results-20260519-101030.json \
  --include-fixes \
  2>&1 | tee ./code-analyzer-results-20260519-101030.log
```
**When:** User says "scan AccountService.cls".

---

### 6. Scan Specific Folder
```bash
sf code-analyzer run \
  --rule-selector Recommended \
  --target "force-app/main/default/lwc" \
  --output-file ./code-analyzer-results-20260519-101030.json \
  --include-fixes \
  2>&1 | tee ./code-analyzer-results-20260519-101030.log
```
**When:** User says "scan my LWC components", "check the lwc folder".

---

### 7. Scan Multiple Paths
```bash
sf code-analyzer run \
  --rule-selector Recommended \
  --target "force-app/main/default/classes,force-app/main/default/triggers" \
  --output-file ./code-analyzer-results-20260519-101030.json \
  --include-fixes \
  2>&1 | tee ./code-analyzer-results-20260519-101030.log
```
**When:** User says "scan classes and triggers".  
**Note:** Comma-separated paths in a single `--target` value.

---

### 8. Scan Using Glob Pattern
```bash
sf code-analyzer run \
  --rule-selector Recommended \
  --target "**/*.cls,**/*.trigger" \
  --output-file ./code-analyzer-results-20260519-101030.json \
  --include-fixes \
  2>&1 | tee ./code-analyzer-results-20260519-101030.log
```
**When:** User says "scan all Apex files", "check all classes and triggers".  
**Note:** Glob patterns must match from workspace root.

---

## Diff-Based Scans

### 9. Scan Changed Files (Git Diff)
**Step 1:** Get changed files
```bash
git diff --name-only main...HEAD
```

**Step 2:** Filter to scannable types (`.cls`, `.trigger`, `.js`, `.ts`, `.flow-meta.xml`, etc.)

**Step 3:** Pass as `--target`
```bash
sf code-analyzer run \
  --rule-selector Recommended \
  --target "force-app/main/default/classes/AccountService.cls,force-app/main/default/lwc/accountCard/accountCard.js" \
  --output-file ./code-analyzer-results-20260519-101030.json \
  --include-fixes \
  2>&1 | tee ./code-analyzer-results-20260519-101030.log
```
**When:** User says "scan my changes", "check what I modified", "analyze the diff".

---

## Advanced Scenarios

### 10. Deep Analysis with SFGE (Data Flow)
```bash
sf code-analyzer run \
  --rule-selector "sfge" \
  --workspace "force-app" \
  --output-file ./code-analyzer-results-20260519-101030.json \
  --include-fixes \
  2>&1 | tee ./code-analyzer-results-20260519-101030.log
```
**When:** User says "deep analysis", "data flow analysis", "path-based analysis", "find CRUD violations with certainty".  
**Note:** Requires Java 11+. May take 10-20 minutes. Use `--workspace` to avoid compiling template files.  
**Timeout:** Set to 1200000ms (20 minutes).

---

### 11. Find Code Duplicates (CPD)
```bash
sf code-analyzer run \
  --rule-selector "cpd" \
  --output-file ./code-analyzer-results-20260519-101030.json \
  --include-fixes \
  2>&1 | tee ./code-analyzer-results-20260519-101030.log
```
**When:** User says "find duplicates", "check for copy-paste", "detect code clones".

---

### 12. Check Vulnerable Libraries (RetireJS)
```bash
sf code-analyzer run \
  --rule-selector "retire-js" \
  --output-file ./code-analyzer-results-20260519-101030.json \
  --include-fixes \
  2>&1 | tee ./code-analyzer-results-20260519-101030.log
```
**When:** User says "check for vulnerable libraries", "scan dependencies", "find CVEs".

---

### 13. Analyze Flows
```bash
sf code-analyzer run \
  --rule-selector "flow" \
  --target "**/*.flow-meta.xml" \
  --output-file ./code-analyzer-results-20260519-101030.json \
  --include-fixes \
  2>&1 | tee ./code-analyzer-results-20260519-101030.log
```
**When:** User says "analyze my Flows", "check Flow best practices".  
**Note:** Requires Python 3.

---

### 14. Performance Analysis (ApexGuru)
```bash
sf code-analyzer run \
  --rule-selector "apexguru" \
  --output-file ./code-analyzer-results-20260519-101030.json \
  --include-fixes \
  2>&1 | tee ./code-analyzer-results-20260519-101030.log
```
**When:** User says "performance analysis", "find slow code", "check governor limits".  
**Note:** Requires authenticated Salesforce org. See `references/special-behaviors.md` for auth setup.

---

## Output Format Variations

### 15. HTML Report
```bash
sf code-analyzer run \
  --rule-selector Recommended \
  --output-file ./code-analyzer-results-20260519-101030.html \
  --include-fixes \
  2>&1 | tee ./code-analyzer-results-20260519-101030.log
```
**When:** User explicitly requests HTML format.  
**Note:** Extension determines format. JSON is default.

---

### 16. SARIF (GitHub/IDE Integration)
```bash
sf code-analyzer run \
  --rule-selector Recommended \
  --output-file ./code-analyzer-results-20260519-101030.sarif \
  --include-fixes \
  2>&1 | tee ./code-analyzer-results-20260519-101030.log
```
**When:** User says "SARIF format", "GitHub integration", "IDE integration".

---

### 17. CSV (Spreadsheet)
```bash
sf code-analyzer run \
  --rule-selector Recommended \
  --output-file ./code-analyzer-results-20260519-101030.csv \
  --include-fixes \
  2>&1 | tee ./code-analyzer-results-20260519-101030.log
```
**When:** User says "CSV format", "export to spreadsheet", "Excel format".

---

## Complex Rule Selectors

### 18. Multiple Categories
```bash
sf code-analyzer run \
  --rule-selector "all:(Security,Performance):(1,2,3)" \
  --output-file ./code-analyzer-results-20260519-101030.json \
  --include-fixes \
  2>&1 | tee ./code-analyzer-results-20260519-101030.log
```
**Selector breakdown:** All engines, Security OR Performance categories, Severity 1-3 (Critical to Moderate).

---

### 19. Specific Rule by Name
```bash
sf code-analyzer run \
  --rule-selector "pmd:ApexCRUDViolation" \
  --output-file ./code-analyzer-results-20260519-101030.json \
  --include-fixes \
  2>&1 | tee ./code-analyzer-results-20260519-101030.log
```
**When:** User says "check for ApexCRUDViolation", "run the CRUD rule".  
**Note:** Must be exact full rule name. If uncertain, look up first: `sf code-analyzer rules --rule-selector all 2>&1 | grep -i "CRUD"`

---

### 20. Engine + Category + Severity
```bash
sf code-analyzer run \
  --rule-selector "(pmd,eslint):Security:(1,2)" \
  --output-file ./code-analyzer-results-20260519-101030.json \
  --include-fixes \
  2>&1 | tee ./code-analyzer-results-20260519-101030.log
```
**Selector breakdown:** (PMD OR ESLint) AND Security AND (Sev 1 OR Sev 2).

---

## Key Patterns

| Pattern | Meaning | Example |
|---------|---------|---------|
| `:` | AND | `pmd:Security` = PMD **and** Security |
| `,` | OR | `(pmd,eslint)` = PMD **or** ESLint |
| `()` | Grouping | `(pmd,eslint):Security` = (PMD or ESLint) and Security |
| `(1,2)` | Severity range | `:(1,2)` = Severity 1 or 2 |
| `--target <path>` | Specific files/folders | Comma-separated in single arg |
| `--workspace <path>` | Compilation scope (SFGE only) | Prevents compiling template files |
| `.json`, `.html`, `.sarif`, `.csv`, `.xml` | Output format | Extension of `--output-file` |

---

## Anti-Patterns (DO NOT USE)

### ❌ Using `--format` flag
```bash
# WRONG - v3 syntax, does not exist in v4+
sf code-analyzer run --format json
```
**Why:** The `--format` flag was removed in v4+. Use `--output-file` with extension instead.

---

### ❌ Using `$TIMESTAMP` variable in command
```bash
# WRONG - variable substitution fails in permission prompts
sf code-analyzer run --output-file "./results-${TIMESTAMP}.json"
```
**Why:** Generate timestamp first, then use literal string in command.

---

### ❌ Running in background for long scans
```bash
# WRONG - loses output stream
sf code-analyzer run --rule-selector sfge &
```
**Why:** Use foreground with high timeout (1200000ms). Backgrounding loses the output.

---

### ❌ Partial rule names
```bash
# WRONG - returns 0 results
sf code-analyzer run --rule-selector "no-hardcoded-values"
```
**Why:** Rule names must be exact. Look up first: `sf code-analyzer rules --rule-selector all | grep -i "hardcoded"`
**Correct:** `--rule-selector "@salesforce-ux/slds/no-hardcoded-values-slds2"`
