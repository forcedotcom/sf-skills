---
name: dx-code-analyzer-run
description: "Run Salesforce Code Analyzer to scan code for security, performance, best practice, and code style violations. Supports all engines (PMD, ESLint, CPD, RetireJS, Flow, SFGE, ApexGuru), targets (files, folders, git diff), categories, and severities. Also handles post-scan exploration: filtering results by engine/severity/category/file, and explaining what rules mean. TRIGGER when: user says 'scan my code', 'check security issues', 'run PMD/ESLint', 'find duplicates', 'analyze Flows', 'check vulnerable libraries', 'AppExchange review', 'lint my LWC', 'static analysis', 'code quality', 'show security violations', 'what is this rule', 'explain ApexCRUDViolation', 'filter results', or mentions engines/file types (.cls, .trigger, .js, .flow-meta.xml). Use this skill for scanning, exploring results, and listing rules. DO NOT TRIGGER when: user asks only about installation/configuration (use dx-code-analyzer-configure), or wants to create a custom rule (use dx-code-analyzer-custom-rule-create)."
metadata:
  version: "1.0"
  relatedSkills:
    - "dx-code-analyzer-configure"
    - "dx-code-analyzer-custom-rule-create"
  cliTools:
    - tool: ["sf"]
      semver: ">=2.0.0"
    - tool: ["node"]
      semver: ">=18.0.0"
    - tool: ["git"]
      semver: ">=2.0.0"
---

# Running Code Analyzer Skill

## CRITICAL: Mandatory Script Usage

Every interaction with Code Analyzer results MUST go through the bundled scripts in `<skill_dir>/scripts/`. No exceptions.

### WRONG — never do this:

```bash
# WRONG: inline Python to parse results
python3 -c "import json; data = json.load(open('results.json'))..."

# WRONG: inline Node.js to parse results
node -e "const data = require('./results.json')..."

# WRONG: jq to filter results
cat results.json | jq '.violations[] | select(.engine=="pmd")'

# WRONG: reading the results file directly (it can be 10MB+)
Read tool → code-analyzer-results-*.json
```

Also forbidden: `run_code_analyzer` and any `mcp__*` tool — Bash only.

### RIGHT — always do this:

```bash
# Summarize scan results
node "<skill_dir>/scripts/parse-results.js" "./code-analyzer-results-TIMESTAMP.json"

# Filter/rank/query results (by engine, severity, file, rule, category)
node "<skill_dir>/scripts/query-results.js" "./code-analyzer-results-TIMESTAMP.json" --engine pmd --summary

# List/browse available rules (by engine, category, language, severity)
node "<skill_dir>/scripts/list-rules.js" "Security" --top 10

# Look up what a rule means
node "<skill_dir>/scripts/describe-rule.js" "ApexCRUDViolation" --engine pmd

# Discover fixable violations
node "<skill_dir>/scripts/discover-fixes.js" "./code-analyzer-results-TIMESTAMP.json"

# Apply fixes (after user confirms)
node "<skill_dir>/scripts/apply-fixes.js" "./code-analyzer-results-TIMESTAMP.json"

# Summarize applied fixes
node "<skill_dir>/scripts/summarize-fixes.js" "./code-analyzer-results-TIMESTAMP.json"

# Filter vendor files (jQuery, Bootstrap, *.min.js) before applying fixes
node "<skill_dir>/scripts/filter-violations.js" "./code-analyzer-results-TIMESTAMP.json" "./code-analyzer-results-TIMESTAMP-filtered.json" --report
```

`<skill_dir>` is the absolute path to the directory containing this SKILL.md. **Never** use `./scripts/` — that resolves against the user's CWD, not the skill dir.

Any aggregation, filter, or rank question ("which file has the most violations?", "how many PMD issues?", "top rules by count", "break down by severity") is answered by `query-results.js` — its output already includes `topRules`, `topFiles`, and `severityCounts`.

---

## Overview

> **Ecosystem:** This skill is part of a 3-skill Code Analyzer suite — `dx-code-analyzer-run` (scans & results) · `dx-code-analyzer-configure` (setup, config, CI/CD) · `dx-code-analyzer-custom-rule-create` (custom rule authoring).

This skill translates natural-language requests ("scan for security issues", "check my changes") into the correct `sf code-analyzer run` command, executes scans across any combination of engines/targets/severities, and presents actionable results. When engine-provided fixes are available, it discovers them, asks for user confirmation, applies them safely, and offers verification. Use it for static analysis, security reviews, AppExchange certification, code-quality checks, and finding duplicates/vulnerabilities in Salesforce projects.

**In scope:** running scans, parsing/filtering/ranking results, applying engine auto-fixes, diff-based scans, all output formats (JSON/HTML/SARIF/CSV/XML), describing/listing rules, scan-failure troubleshooting.

**Out of scope:** installing/configuring `sf` or the plugin (→ `dx-code-analyzer-configure`), writing custom rules/engines (→ `dx-code-analyzer-custom-rule-create`), AI-generated fixes beyond engine-provided ones, deep refactoring, CI/CD setup (→ `dx-code-analyzer-configure`).

**Allowed tools:** Bash (`sf code-analyzer`, `node`, `git diff`, `date`), Read, Write, Edit. **Forbidden:** any MCP tool, Agent tool, web tools, other skills, Python, `jq`, inline scripts/heredocs. This skill owns the complete scan-fix-verify-query-explain workflow end-to-end.

---

## Command Syntax Rules (READ FIRST — ABSOLUTE)

1. The command is **`sf code-analyzer run`** — NOT `sf scanner run` (deprecated v3).
2. **No `--format` flag.** Use `--output-file <path>.<ext>`; the extension determines the format.
3. **Always** pass `--output-file` with a timestamped name (e.g., `./code-analyzer-results-20260512-143022.json`) — do not rely on stdout.
4. **Foreground only** (no `run_in_background`); timeout 1200000ms for large scans.
5. **Invalid v3 flags** that cause errors: `--format`, `--engine`, `--category`, `--json`. Use `--rule-selector` + `--output-file` instead.
6. **Tool restriction:** Bash, Read, Write, Edit only. No MCP tools, no Agent tool, no web tools, no other skills.

Why: the v4+ CLI redesigned the flag interface; v3 flags now error.

Full flag/selector docs: `<skill_dir>/references/flag-reference.md`.

---

## Prerequisites

User needs: **Salesforce CLI** (`sf`), **@salesforce/plugin-code-analyzer** (v5.x+), **Java 11+** (PMD/CPD/SFGE), **Node.js 18+** (ESLint/RetireJS), **Python 3** (Flow), **authenticated org** (ApexGuru).

Pre-flight: run `sf code-analyzer --help 2>&1 | head -1`. If that fails, or if a scan reports an engine startup error (e.g., "PMD failed to start", "java: command not found", "SFGE failed"):

1. **Stop** — do not attempt to install/diagnose prerequisites yourself.
2. **Delegate to `dx-code-analyzer-configure`** — it handles all setup.
3. After it finishes, return here and re-run the scan.

If a scan fails for other reasons, see `<skill_dir>/references/error-handling.md`.

---

## Quick Start: Common Patterns

Match the request below; if it matches, jump to Step 3 (Build Command). Otherwise, walk Step 1.

| User Says | Rule Selector | Notes |
|-----------|---------------|-------|
| "scan my code" / "run code analyzer" | `Recommended` | Curated set, all file types |
| "check for security issues" / "security review" | `all:Security:(1,2)` | All engines, Critical+High |
| "scan my changes" / "check the diff" | (see Step 1.5) | Get files via `git diff`, filter to scannable types, pass via `--target` |
| "run PMD" / "check my Apex" | `pmd` | Apex classes and triggers |
| "lint my LWC" / "check my JavaScript" | `eslint` | JavaScript/TypeScript/LWC |
| "find duplicates" / "check for copy-paste" | `cpd` | Code clones |
| "check for vulnerabilities" / "scan libraries" | `retire-js` | JavaScript library CVEs |
| "deep analysis" / "data flow analysis" | `sfge` | Java 11+, 10–20 min, use `--workspace "force-app"` |
| "performance analysis" / "governor limits" | `apexguru` | Authenticated org required |
| "analyze my Flows" | `flow` | `--target **/*.flow-meta.xml`, Python 3 |
| "AppExchange security review" | `all:Security:(1,2)` | See `<skill_dir>/references/special-behaviors.md` → AppExchange |

---

## Step 1: Parse the User's Intent

Analyze the request along these 7 dimensions; any can combine.

### 1.1 ENGINE
PMD/Apex → `pmd` · ESLint/JS/TS/lint → `eslint` · Flows → `flow` · duplicates/CPD → `cpd` · vulnerabilities/CVE/RetireJS → `retire-js` · SFGE/data flow → `sfge` · performance/ApexGuru → `apexguru` · regex → `regex` · everything → `all` · unspecified → `Recommended`.

### 1.2 CATEGORY
security/OWASP → `Security` · performance → `Performance` · best practices → `BestPractices` · style/format → `CodeStyle` · design/complexity → `Design` · bugs → `ErrorProne` · docs → `Documentation`.

### 1.3 SEVERITY
1=Critical · 2=High · 3=Moderate · 4=Low · 5=Info. "critical only" → `1` · "critical+high" → `(1,2)` · "moderate and above" → `(1,2,3)`.

### 1.4 SPECIFIC RULE
If the user names a rule (e.g., "ApexCRUDViolation", "no-unused-vars"): `--rule-selector <engine>:<ruleName>`, or just `<ruleName>` if engine is ambiguous.

⚠️ **Partial names:** `--rule-selector` requires the **exact full** rule name (e.g., `@salesforce-ux/slds/no-hardcoded-values-slds2`, not `no-hardcoded-values`). No wildcards. If you are not 100% certain, look it up first — **do not guess**:
```bash
sf code-analyzer rules --rule-selector all 2>&1 | grep -i "USER_KEYWORD"
```
Multiple matches → ask the user which. Zero matches → tell the user nothing matched.

### 1.5 TARGET
specific path → `--target <path>` · glob ("all Apex") → `--target **/*.cls,**/*.trigger` · "my changes"/"diff" → `git diff --name-only [base]...HEAD`, filter to scannable types, pass as `--target` · "LWC" → `--target **/lwc/**` · "Flows" → `--target **/*.flow-meta.xml` · unspecified → omit (entire workspace).

Diff-filtering details: `<skill_dir>/references/special-behaviors.md`.

### 1.6 OUTPUT
**Default JSON.** Only change if the user explicitly asks. Name: `./code-analyzer-results-<YYYYMMDD-HHmmss>.<ext>` via `TIMESTAMP=$(date +%Y%m%d-%H%M%S)`. Formats: `.json` (default), `.html`, `.sarif`, `.csv`, `.xml`.

### 1.7 COMPARISON / DELTA
"new since main" → `git diff --name-only main...HEAD` → scan those · "since last commit" → `HEAD~1` · "vs develop" → `develop...HEAD`.

---

## Step 2: Build the Rule Selector

Syntax: `:` = AND, `,` = OR, `()` = grouping.

- Engine only: `pmd`
- Engine + category: `pmd:Security`
- Engine + severity: `pmd:2`
- Complex: `(pmd,eslint):Security:(1,2)` = (PMD or ESLint) AND Security AND sev (1 or 2)
- Specific rule: `pmd:ApexCRUDViolation`
- All: `all`

More: `<skill_dir>/references/command-examples.md`.

---

## Step 3: Build the Full Command

```bash
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
sf code-analyzer run \
  --rule-selector <selector> \
  --target <targets> \                                              # optional
  --output-file "./code-analyzer-results-${TIMESTAMP}.json" \       # default JSON
  --include-fixes \                                                 # always
  --workspace <path>                                                # optional
```

- Default to timestamped JSON; only change format on explicit request.
- Always pass `--include-fixes` (enables Step 6 auto-fix).
- Omit `--target` to scan the whole workspace.
- Diff scans: `git diff --name-only` → filter scannable types → pass as `--target`.

Special cases (SFGE/ApexGuru/AppExchange/diff): `<skill_dir>/references/special-behaviors.md`.

---

## Step 4: Execute the Scan

Use the **Bash tool only** — never the `run_code_analyzer` MCP tool.

1. Generate the timestamp via Bash: `date +%Y%m%d-%H%M%S` → e.g. `20260512-143022`.
2. Tell the user:
   ```text
   Starting scan...
   Results: ./code-analyzer-results-20260512-143022.json
   Log:     ./code-analyzer-results-20260512-143022.log
   May take several minutes for large codebases.
   ```
3. Run with the **literal** timestamp baked in (not `$TIMESTAMP`), foreground, timeout 1200000ms, `tee` to a `.log`:
   ```bash
   sf code-analyzer run --rule-selector Recommended \
     --output-file "./code-analyzer-results-20260512-143022.json" \
     --include-fixes 2>&1 | tee "./code-analyzer-results-20260512-143022.log"
   ```
4. Exit 0 = success. On error, read both the log file and `<skill_dir>/references/error-handling.md`.
5. **Immediately** parse results (Step 5) — do not ask the user what to do next.

---

## Step 5: Parse and Present Results

Run the parse script straight after the scan — do not pause to ask:

```bash
node "<skill_dir>/scripts/parse-results.js" "./code-analyzer-results-TIMESTAMP.json"
```

⚠️ **DO NOT:**
- ❌ Invent or generate script code yourself
- ❌ Use bare relative paths like `node scripts/parse-results.js` (won't resolve from user's CWD)
- ❌ Use heredocs or inline script content
- ❌ Use `jq` as a substitute for the parse script (shell quoting will break)
- ❌ Read the JSON file directly

### Presentation template

```text
## Scan Complete

**Found X violations** across Y files.

| Severity | Count |
|----------|-------|
| Critical (1) | X |
| High (2) | X |
| Moderate (3) | X |
| Low (4) | X |
| Info (5) | X |

### Top Issues
| # | Rule | Engine | Sev | File | Line |
|---|------|--------|-----|------|------|
| 1 | ApexCRUDViolation | pmd | 2 | AccountService.cls | 42 |
| ... up to 10 most critical |

### Top Rules by Frequency
| Rule | Engine | Count |
|------|--------|-------|
| no-var | eslint | 170 |
| ... |

Full results: `./code-analyzer-results-20260512-143022.json`
```

Scale to result size: **0** → "no violations found"; **1–10** → all in one table; **11–50** → severity counts + top 10; **50–5000** → counts + top 10 violations + top 10 rules + top 5 files; **5000+** → same, plus suggest narrowing scope (severity/category/folder). Always end with the output path and offer next actions: filter / explain rule / apply fixes.

Large-result handling: `<skill_dir>/references/special-behaviors.md`.

---

## Step 6: Apply Engine-Provided Fixes (Post-Scan)

Engine-provided fixes are **deterministic** (not AI-generated). Flow: vendor filter (if needed) → discover → present → **wait for user confirmation** → apply → summarize.

### 6.1 Vendor file filter (when needed)

Run if the user said "fix my code" / "project source", or if top-violation files are vendor libs (jQuery, Bootstrap, `*.min.js`):

```bash
node "<skill_dir>/scripts/filter-violations.js" \
  "./code-analyzer-results-TIMESTAMP.json" \
  "./code-analyzer-results-TIMESTAMP-filtered.json" \
  --report
```

Report: "Excluded X vendor files (Y violations) — jQuery, Bootstrap, etc. Applying fixes to Z project files only." Use the filtered file in 6.2+. Detection logic: `<skill_dir>/references/vendor-file-handling.md`.

### 6.2 Discover

```bash
node "<skill_dir>/scripts/discover-fixes.js" "./code-analyzer-results-TIMESTAMP.json"
```

### 6.3 Present + ASK (then STOP)

```text
### Engine-Provided Fixes Available
**X of Y violations** have auto-fixes provided by the analysis engine:

| Rule | Engine | Sev | Fixable Count |
|------|--------|-----|---------------|
| no-var | eslint | 3 | 170 |
| ... |

These are safe, deterministic fixes generated by the engines (not AI-generated).

Would you like me to apply these fixes? (yes / no / select specific rules)
```

⚠️ **Stop and wait for the user's reply, even if they originally said "scan and fix everything".** Apply only on a fresh "yes" / "apply" / "go ahead" in the next turn.

### 6.4 Apply

```bash
node "<skill_dir>/scripts/apply-fixes.js" "./code-analyzer-results-TIMESTAMP.json"
```
(Filtered file if 6.1 created one.)

### 6.5 Summarize (MANDATORY immediately after 6.4)

```bash
node "<skill_dir>/scripts/summarize-fixes.js" "./code-analyzer-results-TIMESTAMP.json"
```

Then present:

```text
### Engine-Provided Fixes Applied Successfully ✓
**Applied X auto-fixes across Y files.**

| Severity | Fixes Applied |
|----------|---------------|
| Critical (1) | X |
| ... |

| Rule | Fixes Applied |
|------|---------------|
| no-var | 169 |
| ... |

Want me to re-run the scan to verify the fixes resolved the violations?
```

### 6.6 — Handling the user's choice
- **Decline / "no":** skip apply, skip summarize. Do not re-scan.
- **"Select rules":** filter the discovery list to those rules and pass the filtered file to `apply-fixes.js`.
- **"All" / "yes":** run `apply-fixes.js` against the full (or vendor-filtered) results file as-is.

### 6.7 — Optional re-scan for verification
If the user accepts the offer in 6.5, re-run the same scan with a **new timestamp** (do not overwrite the original). Compare violation counts before vs. after and show the delta — fixes that resolved cleanly will drop out; remaining violations either need manual remediation or are unrelated.

---

## Step 7: Query and Filter Existing Results

After Step 5, the user may want to **drill into specific subsets** without re-running the entire scan. This step handles all result-exploration requests.

### When to trigger
Activate when the user asks to slice, filter, rank, or explore existing results:
- "Show me just the security violations"
- "What's in AccountService.cls?"
- "Show only PMD issues" / "Filter to critical and high"
- "What ESLint rules fired?" / "Show violations in the lwc folder"
- "Top 20 most severe" / "Which file has the most violations?"
- "What are the most common rules?" / "How many violations per engine?" / "Break it down by severity"

**Important:** Any question about existing scan results — filtering, ranking, counting, aggregating — MUST use `query-results.js`. NEVER write inline Python, `jq`, or ad-hoc scripts to parse the results JSON. The query script already provides `topRules`, `topFiles`, and `severityCounts` in its output.

### How to execute
Run the query script against the **same results file** from Step 4 (no re-scan needed):

```bash
node "<skill_dir>/scripts/query-results.js" "./code-analyzer-results-TIMESTAMP.json" [options]
```

| User says | Options |
|-----------|---------|
| "security violations" | `--category Security` |
| "PMD issues only" | `--engine pmd` |
| "critical and high" / "sev 1-2" | `--severity 1,2` |
| "in AccountService.cls" | `--file AccountService.cls` |
| "the ApexCRUDViolation rule" | `--rule ApexCRUDViolation` |
| "top 20" | `--top 20` |
| "sort by file" | `--sort file` |
| "just give me counts" | `--summary` |
| "which file has the most violations?" | `--sort file --summary` (read `topFiles`) |
| "which file has most PMD violations?" | `--engine pmd --summary` (read `topFiles`) |
| "most common rules?" | `--summary` (read `topRules`) |
| "how many per engine?" | use Step 5's summary, or run with `--engine X --summary` per engine |
| Combinations | `--engine pmd --severity 1,2 --top 5` |

Output format and presentation templates: `<skill_dir>/references/post-scan-workflows.md`.

---

## Step 8: Describe a Rule

When the user asks "what does this rule mean?" or "how do I fix this?", use this step to look up and explain a specific rule.

### When to trigger
- "What is ApexCRUDViolation?"
- "Explain this rule" / "Why is this flagged?"
- "What does no-var mean?"
- "How do I fix OperationWithLimitsInLoop?"
- "Tell me about this violation"

### How to execute

```bash
node "<skill_dir>/scripts/describe-rule.js" "<rule-name>" [--engine <engine>]
```

Pass `--engine` when known (from scan context); omit for a broader search. Returns one of `success` / `multiple_matches` / `not_found`. Status handling and templates: `<skill_dir>/references/post-scan-workflows.md`.

---

## Step 9: List Available Rules

Triggers: "what security rules are available?", "list all PMD rules", "rules for JavaScript", "Recommended rules", "how many ESLint rules?", "rules for Apex".

```bash
node "<skill_dir>/scripts/list-rules.js" "<selector>" [options]
```

| User says | Selector | Options |
|-----------|----------|---------|
| "security rules" | `Security` | |
| "PMD rules" | `pmd` | |
| "ESLint security rules" | `eslint:Security` | |
| "JavaScript rules" | `JavaScript` | |
| "Apex rules" | `Apex` | |
| "Recommended rules" | `Recommended` | |
| "high severity rules" | `(1,2)` | |
| "just give me counts" | `Recommended` | `--count-only` |
| "top 10 security rules" | `Security` | `--top 10` |

Filters: `--engine`, `--severity`, `--top` (default 100), `--count-only`. The script pre-validates selector tokens (catches typos like `secruity`) before calling the CLI. Presentation: `<skill_dir>/references/post-scan-workflows.md`.

---
## Cross-Skill Integration

This skill is part of a 3-skill Code Analyzer ecosystem. Hand off cleanly rather than attempting work that belongs to another skill.

### When THIS skill delegates to `dx-code-analyzer-configure`:

- Pre-flight check fails (CLI missing, plugin not installed, engine prereqs broken) → stop, delegate, return here after fix
- User asks to set up CI/CD, edit `code-analyzer.yml`, change severities, or disable engines → delegate entirely

### When THIS skill delegates to `dx-code-analyzer-custom-rule-create`:

- User asks to create a new rule, write XPath, write a regex rule, or enforce a pattern not covered by built-in rules → delegate entirely. Do NOT attempt to create rules here.

### When other skills hand off HERE:

- `dx-code-analyzer-configure` completes setup → proceed with scan (Step 1–5)
- `dx-code-analyzer-custom-rule-create` finishes creating a rule → proceed with scan targeting the new rule (e.g., `--rule-selector pmd:<RuleName>`) to verify it works

### Ownership boundary

This skill owns the complete **scan → explore → fix** workflow end-to-end. It does NOT own installation, config file management, or rule authoring.

---

## Constraints & Gotchas

| Item | Why / Fix |
|------|-----------|
| Use timestamped JSON + `.log` via `tee` | Prevents overwrite; matches log to results |
| `--format` flag | Removed in v4+; use `--output-file <path>.<ext>` |
| Foreground, 1200000ms timeout | SFGE can take 10–20 min; backgrounding loses output |
| Run scripts with absolute `<skill_dir>` path | `./scripts/` resolves against the user's CWD, not the skill dir |
| Never apply fixes without confirmation | User must approve code modifications |
| Vendor file check before fixes | If 50%+ vendor (jQuery/Bootstrap/`*.min.js`), filter first |
| Fix-script order: filter (if needed) → discover → apply → summarize | Skipping summary leaves the user without an outcome report |
| SFGE needs explicit `--workspace` | Otherwise template files cause compilation errors |
| Look up partial rule names first | Guessing returns 0 results; use `sf code-analyzer rules` |
| `ONLY` Bash tool, never MCP | `run_code_analyzer` and other MCP tools bypass the script workflow |
| Never invoke other skills for fixes | This skill owns the full workflow end-to-end |
| Query existing results, don't re-scan | Step 7 filters existing JSON instantly |
| Scan returns 0 results | Invalid rule selector — verify with `sf code-analyzer rules --rule-selector <selector>` |
| `jq` parsing fails | Shell quoting — use `parse-results.js` / `query-results.js` instead |
| Inline scripts written by LLM | Never write scripts — use existing ones in `<skill_dir>/scripts/` |
| Ranking/aggregation answered by ad-hoc Python | Always use `query-results.js`; output already has `topFiles`/`topRules`/`severityCounts` |

---

## Reference File Index

**Scripts** (always execute via `node` with the absolute `<skill_dir>/` prefix, never Read):

| File | When to use |
|------|-------------|
| `<skill_dir>/scripts/parse-results.js` | Step 5 — extract summary from scan JSON |
| `<skill_dir>/scripts/filter-violations.js` | Step 6.1 — exclude vendor files (jQuery, Bootstrap) from fixes |
| `<skill_dir>/scripts/discover-fixes.js` | Step 6.2 — identify fixable violations |
| `<skill_dir>/scripts/apply-fixes.js` | Step 6.4 — apply engine fixes after user confirms |
| `<skill_dir>/scripts/summarize-fixes.js` | Step 6.5 — summarize applied changes |
| `<skill_dir>/scripts/query-results.js` | Step 7 — filter/drill into existing results without re-scanning |
| `<skill_dir>/scripts/describe-rule.js` | Step 8 — look up rule description and documentation |
| `<skill_dir>/scripts/list-rules.js` | Step 9 — list/browse available rules by selector with validation |

**References** (read on demand):

| File | When to read |
|------|--------------|
| `references/quick-start.md` | Command-syntax templates |
| `references/flag-reference.md` | Full flag docs, rule-selector syntax |
| `references/error-handling.md` | Scan-failure diagnosis |
| `references/engine-reference.md` | Engine capabilities, file types, rule tags |
| `references/command-examples.md` | Less-common command scenarios |
| `references/special-behaviors.md` | SFGE/ApexGuru/AppExchange/diff/large scans |
| `references/vendor-file-handling.md` | Vendor-file detection and filtering |
| `references/post-scan-workflows.md` | Steps 7–9 — querying, rule description, rule listing |

`examples/` contains output-structure validation and command patterns (basic/large/security scans, fix workflows).
