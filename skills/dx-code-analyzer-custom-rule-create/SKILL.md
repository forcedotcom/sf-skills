---
name: dx-code-analyzer-custom-rule-create
description: "Create custom Code Analyzer rules for Regex (pattern matching), PMD (XPath/AST for Apex and metadata XML), and ESLint (LWC/JavaScript/TypeScript). Use when users want to enforce coding standards, ban patterns, detect hardcoded values, govern metadata, or add rules not in the built-in set. TRIGGER when: user says 'create a rule', 'ban System.debug', 'enforce naming convention', 'detect hardcoded IDs', 'custom rule', 'xpath rule', 'regex rule', 'add a PMD rule', 'enforce a policy', 'create a check for', 'flag this pattern', 'make a rule that catches', 'metadata rule', 'check permissions', 'enforce API version', 'eslint rule', 'lwc rule', 'override rule threshold', 'customize complexity', or describes a pattern to enforce. DO NOT TRIGGER when: user wants to run a scan (use dx-code-analyzer-run), configure engines (use dx-code-analyzer-configure), or explain existing rules (use dx-code-analyzer-run)."
metadata:
  version: "1.0"
  relatedSkills:
    - "dx-code-analyzer-run"
    - "dx-code-analyzer-configure"
  cliTools:
    - tool: ["sf"]
      semver: ">=2.0.0"
    - tool: ["node"]
      semver: ">=18.0.0"
    - tool: ["npm"]
      semver: ">=9.0.0"
---

# dx-code-analyzer-custom-rule-create: Custom Code Analyzer Rule Authoring

> **Ecosystem:** This skill is part of a 3-skill Code Analyzer suite — `dx-code-analyzer-run` (scans & results) · `dx-code-analyzer-configure` (setup, config, CI/CD) · `dx-code-analyzer-custom-rule-create` (custom rule authoring).

Use this skill when the user needs to **create a custom rule** that enforces a pattern not covered by Code Analyzer's built-in rules. Supports Regex engine (text pattern matching) and PMD engine (structural XPath queries against the AST).

## When This Skill Owns the Task

Use `dx-code-analyzer-custom-rule-create` when the work involves:
- Creating a new custom rule for Code Analyzer (any engine)
- Enforcing team-specific coding standards via static analysis
- Banning specific patterns (System.debug, hardcoded IDs, TODOs)
- Writing XPath expressions for PMD rules (Apex or metadata XML)
- Writing regex patterns for the Regex engine
- Setting up custom ESLint rules/plugins for LWC/JavaScript
- Enforcing metadata governance (API versions, field descriptions, dangerous permissions)
- Overriding built-in rule thresholds (CyclomaticComplexity, ExcessiveParameterList, etc.)
- Organizing multiple rules into shared rulesets
- Iterating on a custom rule that isn't matching correctly

Delegate elsewhere when the user is:
- Running a scan against existing rules → `dx-code-analyzer-run` skill
- Configuring engines, prerequisites, CI/CD → `dx-code-analyzer-configure` skill
- Explaining what an existing built-in rule means → `dx-code-analyzer-run` skill
- Writing Apex code or tests → `generating-apex` / `running-apex-tests` skills

---

## Required Context to Gather First

Ask for or infer:
- **What pattern to catch** — what code should be flagged? (If user selected code in their IDE, the selection IS the answer — do not re-ask.)
- **What to allow** — any exceptions? (test classes, specific contexts)
- **File scope** — which file types? (.cls, .trigger, .js, all?)
- **Severity** — how critical? (default: 3/Moderate)

If the user **selected code** (IDE selection context present), treat it as the pattern definition. Skip clarification unless genuinely ambiguous about what aspect of the selection to target.

If the request is vague with NO selection ("add a rule for best practices"), ask ONE clarifying question:
> "What specific pattern should this rule flag?"

---

## Hard Constraints

These are non-negotiable rules. Violating any of them is a skill failure regardless of whether the output happens to work.

1. **ALWAYS run `ast-dump` before writing XPath.** No exceptions. Do not use node names from memory, references, or prior conversations. The AST is the source of truth — run `sf code-analyzer ast-dump`, read the output, then write XPath that matches what you see. Even for "well-known" patterns like SOQL-in-loop, run ast-dump first. If you skip this step and the rule works, it is still a process failure.

2. **ALWAYS use the scripts to create rules.** For regex rules, ALWAYS use `create-regex-rule.js`. For PMD rules, ALWAYS use `create-pmd-rule.js`. Do NOT manually edit `code-analyzer.yml` to add rule definitions — regex patterns in YAML cause escaping failures (quotes inside quotes, backslashes getting eaten). The scripts handle YAML serialization correctly every time.

3. **NEVER manually edit `code-analyzer.yml` after a script writes to it — even to fix a bad value.** The scripts produce correctly-escaped YAML. If you then rewrite or restructure the file, you WILL break the escaping. If the user added top-level config (like `ignores.files`), leave it alone too — only touch what you wrote.

   **If a script's output looks wrong (rule fails to validate, YAML parse error, stray characters in the regex):**
   - DO NOT patch the YAML by hand. That is exactly the failure mode this constraint exists to prevent.
   - **Always** delete the broken rule's entire YAML block, then re-invoke the script with corrected arguments. Removing a block you just wrote does not violate this rule; rewriting fields inside it does.
   - If the script accepted bad input and produced bad output, the **input** was wrong (e.g., `--regex "/.../ g"` with a stray space — the flags must be `/g` exactly, no whitespace). Re-invoke with the corrected argument.
   - If you genuinely believe the script has a bug, STOP and surface it to the user. Do not hand-edit as a workaround.

4. **`--regex` must be `/pattern/flags` with NO whitespace.** The script trims and validates flags strictly — only `g`, `i`, `m`, `s`, `u`, `y`. `/pat/ g` (with a space) is rejected; so is `/pat/x` (invalid flag) and `/pat/` (no flags). The global flag `g` is mandatory. If validation fails, fix the argument — do NOT bypass by writing YAML directly.

5. **ALWAYS validate after creation.** Run `sf code-analyzer rules --rule-selector <engine>:<name>` before testing. If `Found 0 rules`, the YAML didn't parse — delete the block, fix the argument, re-invoke the script.

6. **ALWAYS test against a sample file.** Confirm at least one true positive and one true negative.

   For regex rules, the negative sample MUST NOT contain the pattern text anywhere — including inside comments and string literals. Regex engines scan raw text; `// no System.debug here` IS a match for `/System\.debug/g`. Trace your pattern against the negative file mentally before running it.

7. **Create rules ONE AT A TIME, sequentially.** When the user requests multiple rules, create each rule individually through the full workflow (create → validate → test positive → test negative) before starting the next one. Do NOT batch-create rules — if one fails, it corrupts the config for all subsequent rules. Complete each rule end-to-end, confirm it works, then move to the next.

8. **For regex rules, exclude test classes via `ignores.files` — `regex_ignore` does NOT do this.** `regex_ignore` is a per-LINE filter (the line must match BOTH the rule and the ignore pattern); it cannot exclude an entire test class. If the user's intent is "skip test classes," add a top-level `ignores.files` block with globs like `"**/*Test.cls"` AFTER all rules are created — do not interleave config edits with script invocations.

---

## Engine Selection

| Pattern Type | Engine | Why |
|---|---|---|
| Text/string pattern (TODO, hardcoded ID, keyword) | **Regex** | Simple, fast, no Java needed |
| Apex code structure (method calls, nesting, SOQL in loops) | **PMD/XPath** (language=apex) | Understands AST, not fooled by comments/strings |
| Metadata XML governance (API version, permissions, descriptions) | **PMD/XPath** (language=xml) | Structural XML matching with namespace handling |
| LWC/JavaScript/TypeScript patterns | **ESLint*** | Standard JS tooling, plugin ecosystem |
| Both could work (Apex/metadata only) | **Regex first** | Simpler to create and maintain |

\* **For ESLint:** ALWAYS check Tier 1 (built-in rules) and Tier 2 (configurable rules) BEFORE creating a custom plugin. See `references/eslint-rules-discovery.md`.

⚠️ **"Both could work → Regex first" NEVER applies to JavaScript/LWC/TypeScript files.** JS/LWC/TS patterns MUST use ESLint — Regex cannot distinguish code from comments/strings in JS and produces false positives. Do NOT rationalize Regex for JS files based on "simplicity" or "no npm dependencies."

Tell the user which engine you chose and why. Respect their preference if they disagree.

### Excluding Test Classes — Strategy by Engine

When a rule should NOT apply to test classes, the approach differs by engine:

| Engine | How to exclude test classes | Notes |
|--------|---------------------------|-------|
| **PMD (Apex)** | Add `[not(ancestor::UserClass[ModifierNode[@Test = true()]])]` to the XPath | Structural exclusion — works perfectly, no config changes needed |
| **Regex** | Use `ignores.files` in `code-analyzer.yml` with globs like `**/*Test.cls` | `regex_ignore` is per-LINE, not per-FILE — it CANNOT exclude entire test classes. Only use `regex_ignore` for per-line patterns like `// NOPMD` |
| **ESLint** | Use `ignores` array in `eslint.config.js` | Standard ESLint file-level ignores |

⚠️ **`regex_ignore` is NOT file-level exclusion.** It only skips matches on lines that ALSO match the ignore pattern. Example: `regex_ignore: "/@isTest/i"` only suppresses violations on lines containing `@isTest` — a SOQL query on line 50 of a test class still flags because line 50 doesn't contain `@isTest`. To exclude test files from regex rules entirely, use:
```yaml
ignores:
  files:
    - "**/*Test.cls"
    - "**/*_Test.cls"
```

⚠️ **`ignores.files` is GLOBAL** — it affects ALL engines and ALL rules. If you need test-class exclusion for some rules but not others (e.g., exclude tests from SOQL rules but still scan tests for @AuraEnabled), use **PMD with XPath** for the rules that need selective exclusion. PMD's XPath can structurally check `@Test = true()` per-method or per-class — Regex cannot.

**Decision guide for Apex rules that should skip test classes:**
- If the pattern is structural (method calls, annotations, nesting) → use PMD. XPath handles test-class exclusion natively.
- If the pattern is purely textual AND all regex rules should skip tests → use Regex + `ignores.files`.
- If you have a mix (some rules skip tests, others don't) → use PMD for the test-sensitive rules, Regex for the others.

---

## Workflow

### When User Selects Code (IDE Selection)

When the user highlights a code block in their editor and asks to "catch this", "flag this pattern", "create a rule for this", or similar:

1. **The selection IS your positive sample.** Do NOT ask "what pattern should this rule flag?" — the user already showed you. Do NOT write a new sample from scratch.
2. **Identify what's structural vs. incidental** in the selection:
   - Structural (rule-worthy): the method call, the loop pattern, the missing keyword, the nesting
   - Incidental (ignore): specific variable names, string values, parameter counts
   - Ask ONE question if ambiguous: "Should the rule catch all `System.debug` calls, or only those without a LoggingLevel parameter?"
3. **Ast-dump the ACTUAL file** the user has open (not a new sample file):
   ```bash
   sf code-analyzer ast-dump --file <the-open-file.cls> --output-file <ast.xml>
   ```
4. **Find the selection in the AST output** — locate the nodes corresponding to the highlighted lines. These are your target nodes.
5. **Generalize the XPath** — write XPath that matches the structural pattern, NOT the specific instance. Replace specific variable names with wildcards, keep structural nodes and discriminating attributes.
6. **Continue with standard workflow** (negative sample, create rule, validate, test positive + negative).

**Example flow:**
- User selects: `Database.query('SELECT Id FROM ' + objectName)`
- Structural pattern: `Database.query` call (dynamic SOQL)
- Incidental: the specific string concatenation inside
- Engine: PMD (structural call detection)
- XPath: `//MethodCallExpression[@FullMethodName='Database.query']`
- NOT: regex matching `Database.query` (would miss multiline, match comments)

**Example flow (block selection):**
- User selects a 5-line block with SOQL inside a for-each loop
- Structural: SOQL query as descendant of loop body
- Incidental: specific query fields, variable names
- Engine: PMD
- Ast-dump the open file → find ForEachStatement + SoqlExpression in body
- XPath: `//ForEachStatement/BlockStatement//SoqlExpression`

---

### For Regex Rules

1. **Write a positive sample** (5-10 lines) demonstrating the violation. Write sample files inside the project workspace (e.g., a temporary `samples/` directory at the project root) so Code Analyzer can target them.
2. **Write a SEPARATE negative sample file** — code that looks similar but must NOT be flagged. Test your regex mentally against this file BEFORE creating the rule.
3. **Build and create the rule** — read `references/regex-rule-schema.md` for the complete schema, then run the script:
   ```bash
   node "<skill_dir>/scripts/create-regex-rule.js" \
     --name "<RuleName>" --regex "<pattern>" --description "<desc>" \
     --severity <1-5> --file-extensions ".cls,.trigger"
   ```
   ⚠️ **ALWAYS use the script.** Do NOT manually write regex patterns into `code-analyzer.yml` — regex characters (quotes, backslashes, braces) inside YAML cause parsing failures. The script handles serialization correctly.
4. **Validate** — `sf code-analyzer rules --rule-selector regex:<RuleName>`
5. **Test positive** — `sf code-analyzer run --rule-selector regex:<RuleName> --target <violation-sample>` — must find violations
6. **Test negative** — `sf code-analyzer run --rule-selector regex:<RuleName> --target <clean-sample>` — must find 0 violations. If it flags clean code, your regex is too broad — go back and tighten the pattern.
7. **Iterate** if test fails (adjust regex, add `regex_ignore`, narrow extensions)
8. **Cleanup** — delete ALL sample files you created. Do not leave temporary test fixtures in the user's project.

### For PMD/XPath Rules (Apex)

1. **Write a minimal sample** (5-10 lines) demonstrating the violation. Write sample files inside the project workspace (e.g., a temporary `samples/` directory at the project root) so Code Analyzer can target them. **After both positive and negative tests pass, delete ALL sample files you created** — both the original samples and any copies made during testing. Do not leave temporary test fixtures in the user's project. For loop-based rules, the positive sample MUST include all 3 Apex loop types (`for-each`, traditional `for`, and `while`) — omitting any loop type means the XPath won't be validated against it and may silently miss violations.
2. **⚠️ MANDATORY: Dump the AST** — `sf code-analyzer ast-dump --file <sample.cls> --output-file <ast.xml>` — this step is NOT optional. Do NOT skip it even if you "already know" the node names. Run it, read the output, confirm the exact node names and attributes.
3. **Read the AST output** — identify the target node and its attributes from the ACTUAL ast-dump output (not from memory). Use `references/apex-ast-reference.md` and `references/xpath-patterns.md` as supplementary context only.
4. **Write XPath** — target the smallest stable node with discriminating attributes. Every node name in your XPath MUST appear verbatim in the ast-dump output you just read. Use `/Child` (direct child) vs `//Descendant` deliberately — check the ast-dump to understand which nodes are siblings vs nested.
5. **⚠️ BEFORE creating the rule: Write a SEPARATE negative sample file** (5-10 lines) showing code that is CORRECT and must NOT be flagged. This MUST be a distinct file from the positive sample — do NOT combine positive and negative cases into one file. For loop-based rules, include `for (x : [SELECT...])` idiom. Run `sf code-analyzer ast-dump` on this negative sample file too. Read the output and trace your XPath against it — confirm it does NOT match any node in the negative AST. If it would match, go back to step 4 and tighten the XPath BEFORE proceeding. Do NOT skip this step or defer it until after rule creation. The negative file will be used again in step 9 for an explicit zero-violation confirmation.
6. **Create the rule** — run the script:
   ```bash
   node "<skill_dir>/scripts/create-pmd-rule.js" \
     --name "<RuleName>" --xpath "<expression>" --message "<msg>" \
     --language apex --priority <1-5>
   ```
7. **Validate** — `sf code-analyzer rules --rule-selector pmd:<RuleName>`
8. **Test positive** — `sf code-analyzer run --rule-selector pmd:<RuleName> --target <violation-sample.cls>` — must find violations
9. **Test negative** — `sf code-analyzer run --rule-selector pmd:<RuleName> --target <clean-sample.cls>` — must find 0 violations. If it flags clean code, your XPath is too broad — go back to step 4.
10. **Iterate** if test fails (re-examine AST, adjust XPath, check node names)
11. **Cleanup** — delete ALL sample files you created (both positive and negative samples, and any ast-dump output files). Do not leave temporary test fixtures in the user's project.

### For PMD/XPath Rules (Metadata XML)

1. **Identify the metadata file type** (field, permissionset, profile, flow, etc.)
2. **Dump the XML AST** — `sf code-analyzer ast-dump --file <file>-meta.xml --language xml --output-file <ast.xml>`. If ast-dump fails with an error (e.g., `"XmlEncoding is not a valid XML name"`), fall back to reading the raw XML file directly — the XML DOM structure IS the AST for metadata files (what you see in the file is what PMD sees). Read the file, note element names, nesting, and text content.
3. **Read the DOM structure** — confirm element names, nesting, and text content from the ast-dump output OR the raw file. Use `references/metadata-xml-rules.md` as supplementary context only.
4. **Write XPath for PMD 7** — CRITICAL rules for metadata XML XPath:
   - All element matching MUST use `local-name()='ElementName'` (namespace blocks bare names)
   - **Text content matching MUST use `@Text` attribute** (NOT `text()` — the `text()` function does not work in PMD 7's XML language). Example: `//*[@Text='ModifyAllData']`
   - Navigate from text nodes UP to parent elements using `../..` (text node → element → parent element)
   - Check sibling conditions via `.//*[@Text='value']` on the parent
   - See `references/metadata-xml-rules.md` for the complete PMD 7 XPath pattern
5. **Configure file extensions** — PMD's XML language only processes `.xml` by default. Salesforce metadata files use compound extensions (`.permissionset-meta.xml`, `.field-meta.xml`, etc.) but `path.extname()` returns `.xml` from these, so `.xml` is sufficient:
   ```yaml
   engines:
     pmd:
       file_extensions:
         xml: [".xml"]
   ```
   ⚠️ Do NOT add compound extensions like `.permissionset-meta.xml` — Code Analyzer's validator rejects them (`/^[.][a-zA-Z0-9]+$/` pattern). Just `.xml` covers all Salesforce metadata files automatically.
6. **Write a SEPARATE negative sample file** — same as Apex rules: create a metadata file that is correct and must NOT be flagged. Verify the XPath does not match it BEFORE creating the rule. Both positive and negative samples should be `.xml` extension files in the workspace so PMD can scan them directly.
7. **Create the rule** — run the script:
   ```bash
   node "<skill_dir>/scripts/create-pmd-rule.js" \
     --name "<RuleName>" --xpath "<expression>" --message "<msg>" \
     --language xml --priority <1-5>
   ```
8. **Validate** — `sf code-analyzer rules --rule-selector pmd:<RuleName>`
9. **Test positive** — `sf code-analyzer run --rule-selector pmd:<RuleName> --target <violation-sample>.xml` — must find violations
10. **Test negative** — `sf code-analyzer run --rule-selector pmd:<RuleName> --target <clean-sample>.xml` — must find 0 violations
11. **Iterate** if test fails (check `@Text` vs `text()`, verify `local-name()` usage, check file extensions config)
12. **Cleanup** — delete ALL sample files you created (both positive and negative samples, and any `.xml` copies made for testing). Do not leave temporary test fixtures in the user's project.

### For ESLint Rules (LWC/JavaScript/TypeScript)

#### ESLint Discovery Workflow (Read First)

ESLint has 200+ built-in rules plus thousands more from plugins. DO NOT attempt to create a custom plugin before checking if a built-in rule exists. The discovery workflow is:

1. **Tier 1 (Built-In Rules)** — 70% of requests
   - Run: `sf code-analyzer rules --rule-selector eslint`
   - Search for keywords (e.g., "console", "unused", "equal")
   - Check LWC plugin rules (`@lwc/lwc/*`)
   - If found: Configure and STOP

2. **Tier 2 (Configurable Rules)** — 20% of requests
   - Pattern is "ban function X"? → `no-restricted-globals`
   - Pattern is "ban syntax Y"? → `no-restricted-syntax`
   - Pattern is "ban property Z"? → `no-restricted-properties`
   - If applicable: Configure and STOP

3. **Tier 3 (Custom Plugins)** — 10% of requests
   - Only for domain-specific multi-node patterns
   - Requires Node.js code, testing, meta.docs metadata
   - See: `references/eslint-custom-plugins.md`

**See:** `references/eslint-rules-discovery.md` for complete discovery guide with examples.

---

0. **⚠️ MANDATORY: Run the ESLint discovery workflow FIRST.** 90% of ESLint requests are solved by built-in rules (Tier 1) or configurable rules like `no-restricted-syntax` (Tier 2). Creating a custom plugin (Tier 3) is a LAST RESORT. Before proceeding:
   
   a) **Run:** `sf code-analyzer rules --rule-selector eslint`
   b) **Search** the output for keywords from the user's request (e.g., "console", "equal", "unused")
   c) **Check LWC plugin rules:** grep for `@lwc/lwc/` in the output
   d) **If found:** Configure it (see `references/eslint-rules-discovery.md`) and STOP. Do NOT create a custom plugin.
   e) **If not found:** Check if `no-restricted-globals`, `no-restricted-syntax`, or `no-restricted-properties` can express the pattern (Tier 2).
   f) **Only if no Tier 1 or Tier 2 solution exists:** Proceed to custom plugin creation.
   
   **Validation:** After configuration, run `sf code-analyzer rules --rule-selector eslint:<ruleName>` to confirm it appears. If it doesn't, the config is wrong.
   
   ⚠️ **Skipping this discovery workflow and creating a custom plugin when a built-in rule exists is a skill failure**, regardless of whether the custom plugin works.

⚠️ **Built-in ESLint rules vs. configurable ESLint rules:** Code Analyzer bundles a SUBSET of ESLint rules in its base config. Rules like `no-restricted-globals`, `no-restricted-syntax`, and `no-restricted-properties` are core ESLint rules but are NOT active until you enable them in an `eslint.config.js`. They WILL appear in `sf code-analyzer rules` output ONLY after you configure them. **Always validate** (step 4) to confirm the rule actually loaded — do NOT assume a rule exists just because it's a core ESLint rule.

1. **Install the ESLint plugin** (skip if using a built-in/core ESLint rule) — `npm install --save-dev eslint-plugin-<name>`
2. **Create/update `eslint.config.js`** — add plugin and rule configuration (or just enable the built-in rule with `"error"` severity). **The file MUST exist** before configuring `engines.eslint.eslint_config_file` in `code-analyzer.yml` — Code Analyzer validates the path and fails if the file is missing.
3. **Configure Code Analyzer** — set `engines.eslint.eslint_config_file` in `code-analyzer.yml`. Do this AFTER the file exists.
4. **Validate** — `sf code-analyzer rules --rule-selector eslint:<ruleName>`. If the rule does NOT appear, the config is wrong — do NOT proceed to testing. Check: (a) Is the `eslint.config.js` file in the correct location? (b) Does the plugin have `meta.docs.description` and `meta.docs.url`? (c) Is the rule deprecated? Code Analyzer silently excludes deprecated rules.
5. **Write a test sample file** in the workspace (e.g., `lwc/testSample/testSample.js`) demonstrating the violation
6. **Test positive** — `sf code-analyzer run --rule-selector eslint:<ruleName> --target <test-sample>` — must find violations
7. **Test negative** — run against existing clean LWC files — must find 0 violations
8. **Cleanup** — delete ALL sample files AND their parent directories (LWC requires a folder per component). Use `rm -rf <directory>`, not just `rm <file>`. Do not leave empty directories or temporary test fixtures in the user's project.
9. See `references/eslint-custom-plugins.md` for complete guide

### Common ESLint patterns without a custom plugin

For `no-restricted-globals`, `no-restricted-syntax`, and `no-restricted-properties` config examples, see `<skill_dir>/references/eslint-custom-plugins.md` — "Banning APIs Without a Custom Plugin" section.

### ESLint Discovery Examples

**Example 1: Built-in rule (Tier 1)**
- User: "Ban console.log in LWC"
- Discovery: `sf code-analyzer rules --rule-selector eslint | grep console` → finds `no-console`
- Action: Enable `no-console` in eslint.config.js
- Result: ✅ Done in 2 minutes (no custom plugin needed)

**Example 2: Configurable rule (Tier 2)**
- User: "Ban setTimeout in LWC"
- Discovery: No built-in `no-setTimeout` rule
- Action: Use `no-restricted-globals` with custom message
- Result: ✅ Done in 5 minutes (no custom plugin needed)

**Example 3: LWC plugin rule (Tier 1)**
- User: "Ban innerHTML for XSS prevention"
- Discovery: `@lwc/lwc/no-inner-html` already exists
- Action: Enable `@lwc/lwc/no-inner-html` in config
- Result: ✅ Done in 2 minutes (no custom plugin needed)

**Example 4: Custom plugin justified (Tier 3)**
- User: "Flag imperative Apex calls without error handling"
- Discovery: No built-in rule for this pattern
- Analysis: Pattern requires checking `import` + `.then()` without `.catch()` — multi-node traversal
- Action: Create custom plugin with visitor pattern
- Result: ✅ Custom plugin is justified (20+ minutes effort)

See `references/eslint-rules-discovery.md` for complete discovery workflow.

---

### Overriding Built-in Rule Thresholds

To customize severity or properties on existing rules without writing new ones:

1. **Create a custom ruleset** referencing the built-in rule with overrides
2. **Add to config** — `engines.pmd.custom_rulesets` in `code-analyzer.yml`
3. See `references/advanced-pmd-patterns.md` for override syntax and common examples

---

## Multi-Rule Requests

When the user asks for multiple rules at once (e.g., "create 5 rules for AppExchange review"), follow this protocol:

### Step 1: Plan the engine assignments FIRST

Before creating any rules, list ALL requested rules with their engine assignments. Present this plan to the user:

```text
Rule plan:
1. RequireUserMode → PMD/XPath (needs test-class exclusion via AST)
2. NoHardcodedIds → Regex (text pattern, no structural context needed)
3. AuraEnabledCacheable → PMD/XPath (needs annotation + DML structural check)
4. CustomFieldDescription → PMD/XML (metadata governance)
5. NoSetTimeout → ESLint (JavaScript pattern)
```

Key decision factors for engine assignment:
- Does the rule need to **exclude test classes selectively**? → PMD (XPath can check `@Test = true()`)
- Is it a **pure text pattern** with no structural context? → Regex
- Does it need to **understand code structure** (annotations, nesting, DML)? → PMD
- Is it **JavaScript/LWC**? → ESLint (never Regex)
- Is it **metadata XML**? → PMD with `language="xml"`

### Step 2: Create rules ONE AT A TIME, sequentially

Create each rule through its full workflow (create → validate → test positive → test negative → confirm working) before starting the next one. Do NOT batch-create rules — if one fails, it corrupts the config for all subsequent rules.

**Order of creation:**
1. Regex rules first (fastest, fewest dependencies)
2. PMD Apex rules (require ast-dump per rule)
3. PMD XML rules (may share a single ruleset file)
4. ESLint rules last (require npm/config setup)

### Step 3: Multiple PMD rules can share ONE ruleset file

When creating multiple PMD rules, use the `create-pmd-rule.js` script for the first rule (it creates the ruleset XML file). For subsequent PMD rules going into the SAME ruleset file, you may add them manually to the existing XML file — this is the ONE exception to the "never edit manually" rule. The script always creates a new file; adding rules to an existing file requires editing the XML directly.

### What NOT to do

- ❌ Do NOT rewrite the entire `code-analyzer.yml` to reorganize it
- ❌ Do NOT create all rules in parallel then validate all at once
- ❌ Do NOT create a PMD rule with an unverified XPath from the reference docs — ast-dump each pattern
- ❌ Do NOT mix engine types in one creation step (e.g., creating regex + PMD rules simultaneously)
- ❌ Do NOT add `engines.eslint.eslint_config_file` to `code-analyzer.yml` before the file exists

---

## High-Signal Rules

| Rule | Rationale |
|------|-----------|
| Rule names must match `/^[A-Za-z@][A-Za-z_0-9@\-/]*$/` | Code Analyzer validation rejects others |
| Regex must be `/pattern/flags` format | JavaScript regex literal notation required |
| File extensions must start with `.` | Validation enforces `/^([.][a-zA-Z0-9-_]+)+$/` |
| Always validate after creation | `sf code-analyzer rules --rule-selector <engine>:<name>` catches config errors |
| Always test against sample code | Catches XPath/regex mismatches before full scan |
| Use `@FullMethodName` for method calls in XPath | More reliable than `@Image` or `@MethodName` alone |
| **⚠️ NEVER skip `ast-dump`** | Run `ast-dump`, read output, THEN write XPath. No exceptions — even for "obvious" patterns. Using node names from memory without ast-dump verification is a skill failure. |
| **PMD 7 boolean attributes: use `= false()` XPath function** | In PMD 7, boolean attributes like `@WithSharing`, `@Abstract`, `@Final` are ALWAYS present on the node (never absent). Compare with `= false()` (XPath boolean function), NOT string `'false'`. `@WithSharing = false()` works. `@WithSharing='false'` (string) does NOT. `not(@WithSharing)` does NOT (attribute is always present). |
| `code-analyzer.yml` at project root | Auto-discovered by CLI — placing it elsewhere causes silent failures for rule authors |
| **XML rules MUST use `local-name()`** | Salesforce metadata namespace breaks bare element names |
| **XML text matching MUST use `@Text` attribute** | `text()` does NOT work in PMD 7's XML language. Use `//*[@Text='value']` to match text content, then navigate up with `../..` to reach parent elements. |
| **`@Text` lives on CHILD text nodes, NOT on elements** | `//*[local-name()='apiVersion'][@Text < 60]` → WRONG (0 matches). `//*[local-name()='apiVersion']/*[number(@Text) < 60]` → CORRECT. The `/*` navigates to the child text node. For exact-match patterns, `//*[@Text='value']` works because it searches ALL nodes including text nodes. But when you target a specific element by `local-name()` first, you must use `/*[@Text...]` to reach its text child. |
| **XML rules need `file_extensions` config** | PMD only scans `.xml` by default — add `file_extensions: { xml: [".xml"] }` under `engines.pmd`. Do NOT add compound extensions (`.permissionset-meta.xml`) — the validator rejects them and `.xml` alone already covers all Salesforce metadata files. |
| Named capture groups `(?<target>...)` in regex | Narrows the violation highlight to just the captured portion |
| **Salesforce IDs start with `0`, are exactly 15 or 18 chars** | Use `/['"](?<target>0[a-zA-Z0-9]{14}(?:[a-zA-Z0-9]{3})?)['\"]/g` — NOT `{15,18}` which also matches 16/17 char strings and produces false positives on normal words like `'BusinessAccount'` |
| **`regex_ignore` is per-LINE, not per-FILE** | It only skips lines where the ignore pattern matches. It does NOT exclude entire files or classes. A hardcoded ID on line 10 of a test class still flags unless that specific line contains the ignore pattern (e.g., `@isTest`). |
| **ALWAYS use scripts to create rules** | Do NOT manually edit `code-analyzer.yml` for regex rules — quotes/backslashes in regex inside YAML cause parsing failures. The `create-regex-rule.js` script handles serialization correctly. |
| Override built-in rules via `<rule ref="...">` | Change thresholds without writing new rules |
| **NEVER use Regex for JS/LWC/TS files** | Regex cannot distinguish code from comments/strings in JS — always use ESLint for JavaScript patterns |
| **Check built-in ESLint rules before writing custom ones** | `no-console`, `no-debugger`, `no-alert`, `eqeqeq`, `no-eval` etc. already exist — just enable them in config |

---

## Gotchas

| Issue | Resolution |
|-------|------------|
| XPath written without running ast-dump | **ALWAYS run ast-dump first.** Even if the rule works, skipping ast-dump is a process failure. Node names change between PMD versions and are not guessable. |
| SOQL-in-loop rule flags `for (x : [SELECT...])` | Use `//ForEachStatement/BlockStatement//SoqlExpression` (scope to body). The iterable SOQL is a direct child of ForEachStatement alongside BlockStatement — `//ForEachStatement//SoqlExpression` matches it as a false positive. |
| Used Regex for a JS/LWC/TS pattern | **NEVER use Regex for JavaScript files.** Regex cannot distinguish code from comments/strings in JS. Always use ESLint — check if a built-in rule (e.g., `no-console`) already exists first. |
| XPath returns 0 matches (XML metadata) | Three common causes: (1) Forgot `local-name()` — namespace blocks bare element names. (2) Used `text()='value'` — does NOT work in PMD 7. Use `@Text='value'` instead. (3) Put `[@Text]` predicate on the element — `@Text` lives on CHILD text nodes. Use `/*[@Text...]` to reach them. |
| Regex rule written inline into `code-analyzer.yml` — YAML parse error | **ALWAYS use `create-regex-rule.js`** — quotes and backslashes inside YAML cause escaping failures. Never hand-write regex into the config file. |
| `regex_ignore` doesn't exclude test classes | `regex_ignore` is **per-LINE only**. A SOQL query on line 50 of a test class flags because line 50 doesn't contain `@isTest`. For file-level exclusion: use `ignores.files` (global) or PMD XPath `[not(ancestor::UserClass[ModifierNode[@Test = true()]])]` (per-rule). |
| XPath `@WithSharing='false'` or `not(@WithSharing)` doesn't work | PMD 7 boolean attributes (`@WithSharing`, `@Abstract`, `@Final`) are ALWAYS present. String `='false'` doesn't match (it's a boolean). `not(@attr)` doesn't work (attribute is always present). Use the XPath boolean function: `@WithSharing = false()`. |
| Loop-based rule only covers `ForEachStatement` | Apex has 3 loop types: `ForEachStatement`, `ForLoopStatement`, `WhileLoopStatement`. All 3 must be in the XPath — omitting any one creates a silent coverage gap. |
| Rewrote `code-analyzer.yml` after script wrote it — YAML parse error | **NEVER manually rewrite the file after a script runs.** Add top-level config blocks (like `ignores.files`) as new entries only — do NOT touch the `engines.regex.custom_rules` section the script generated. |
| Multiple rules created at once — one failure breaks all subsequent rules | **Create rules one at a time, sequentially.** Complete the full workflow (create → validate → test) for each rule before starting the next. |

For additional diagnostics (wrong severity, Java not found, ESLint config path, metadata file type scoping, etc.) see `<skill_dir>/references/troubleshooting.md`.

---

## Cross-Skill Integration

| Need | Delegate to | Reason |
|------|-------------|--------|
| Run a full scan after creating rule | `dx-code-analyzer-run` | Scan execution and result presentation |
| Install Code Analyzer / fix prerequisites | `dx-code-analyzer-configure` | Setup and troubleshooting |
| Explain an existing built-in rule | `dx-code-analyzer-run` | Rule description and docs lookup |
| Edit `code-analyzer.yml` for engine settings | `dx-code-analyzer-configure` | Configuration management |

---

## Script Execution

`<skill_dir>` is the absolute path to the directory containing this SKILL.md file.

All scripts are bundled in the `scripts/` subdirectory of the same directory that contains this SKILL.md file. Use the absolute path to that directory — do NOT use `./scripts/` as that resolves relative to the current working directory, not the skill directory.

```bash
node "<skill_dir>/scripts/create-regex-rule.js" \
  --name "RuleName" --regex "/pattern/flags" ...
```

⚠️ **DO NOT:**
- ❌ Invent or generate script code yourself
- ❌ Use bare relative paths like `node scripts/create-regex-rule.js` (won't resolve from user's CWD)
- ❌ Use heredocs or inline script content
- ❌ Skip resolving `<skill_dir>` — find the absolute path first

---

## Reference File Index

| File | When to read |
|------|-------------|
| `references/regex-rule-schema.md` | Building a regex rule — complete field reference, validation rules, multi-rule example |
| `references/xpath-patterns.md` | Writing XPath for Apex — index of pattern categories with syntax reference and AST node vocabulary |
| `references/xpath-patterns-governor-limits.md` | XPath patterns for SOQL/DML in loops, Database methods in loops |
| `references/xpath-patterns-method-calls.md` | XPath patterns for banning methods and annotation patterns (@AuraEnabled, @future, @IsTest) |
| `references/xpath-patterns-security.md` | XPath patterns for sharing declarations, SOQL security, hardcoded IDs |
| `references/xpath-patterns-structure.md` | XPath patterns for code structure, test quality, naming conventions |
| `references/apex-ast-reference.md` | Reading Apex AST dumps — node hierarchy, modifier attributes, key node types |
| `references/metadata-xml-rules.md` | Writing rules for metadata XML — namespace workaround, common structures, XPath patterns |
| `references/advanced-pmd-patterns.md` | Multi-rule rulesets, overriding built-in rules, exclusion patterns, Java rules, sharing across projects |
| `references/eslint-rules-discovery.md` | **READ FIRST for ANY ESLint request** — discovery workflow, built-in rules, Tier 1-3 index |
| `references/eslint-tier2-configurable.md` | ESLint Tier 2: no-restricted-globals, no-restricted-syntax, no-restricted-properties patterns |
| `references/eslint-tier3-custom-plugins.md` | ESLint Tier 3: when to create custom plugins + complete examples for all tiers |
| `references/eslint-custom-plugins.md` | Creating custom ESLint plugins — ONLY after discovery workflow confirms no built-in or configurable rule exists (Tier 3) |
| `references/troubleshooting.md` | When validation or testing fails — error diagnosis by engine type |
| `assets/pmd-ruleset-template.xml` | PMD XML skeleton with placeholders for the create-pmd-rule script |
| `examples/regex-examples.md` | 6 real-world regex rules solving community-reported problems |
| `examples/xpath-examples.md` | 6 real-world XPath rules for Apex with AST context and step-by-step creation |
| `examples/metadata-xml-examples.md` | Index of 6 real-world metadata XML rules (permissions, descriptions, API versions, flows) |
| `examples/metadata-xml-example-permissions.md` | Metadata examples: ModifyAllData/ViewAllData, field permissions in profiles |
| `examples/metadata-xml-example-fields-api.md` | Metadata examples: custom field descriptions, minimum API version |
| `examples/metadata-xml-example-flows.md` | Metadata examples: flow auto-layout, flow fault handlers |
