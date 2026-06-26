---
name: dx-code-analyzer-configure
description: "Set up, configure, and troubleshoot Salesforce Code Analyzer for any project. Handles installation, prerequisite checks, diagnosing broken setups, creating and editing code-analyzer.yml overrides, engine-specific settings, ignore patterns, severity overrides, and CI/CD pipeline setup. TRIGGER when: user says 'set up code analyzer', 'configure code analyzer', 'install code analyzer', 'code analyzer not working', 'fix my setup', 'scan is failing', 'check my setup', 'is code analyzer installed', 'enable/disable engine', 'exclude files', 'change severity', 'set up GitHub Actions', 'set up CI/CD', 'add code analyzer to pipeline', 'make pipeline fail', 'update my workflow', 'quality gate', 'fail on violations', 'scan changed files only', 'add SARIF', 'code-analyzer.yml', 'ESLint config', 'increase SFGE memory', or reports errors running Code Analyzer. DO NOT TRIGGER when: user wants to run a scan (use dx-code-analyzer-run), fix violations, explain rules, create custom rules, or suppress violations."
metadata:
  version: "1.0"
  argument-hint: "[--check-prerequisites] [--generate-config] [--engine pmd|eslint|cpd|retire-js|regex|flow|sfge|apexguru] [--ci github-actions|jenkins]"
---

# Configuring Code Analyzer Skill

## Overview

This skill manages the `code-analyzer.yml` configuration file — the single source of truth for how Code Analyzer behaves in a project. All customization (engines, rules, ignores, suppressions) is done by creating or editing this file. If the file doesn't exist, this skill creates it in the current working directory.

---

## Scope

**In scope:**
- Checking prerequisites (sf CLI, Java, Node.js, Python, org auth)
- Installing/updating the Code Analyzer plugin
- Creating `code-analyzer.yml` if it doesn't exist
- Editing `code-analyzer.yml` for all configuration changes
- Engine settings, rule overrides, ignore patterns, suppressions
- CI/CD pipeline setup (GitHub Actions, Jenkins, etc.)
- Environment validation and troubleshooting

**Out of scope:**
- Running scans (use `dx-code-analyzer-run` skill)
- Fixing violations, explaining rules, creating custom rules, suppression management

---

## Tool Usage Rules

**Allowed:** Bash (sf, java, node, python3, git, npm), Read, Write, Edit
**Forbidden:** MCP tools, Agent tool, Web tools, other skills, `which`, `find`, `locate`, searching for binaries

---

## Core Principle: YAML Only When Customizing

Code Analyzer works out of the box with NO config file — all defaults are built into the tool. The `code-analyzer.yml` file is ONLY created when the user explicitly requests a customization.

**Rules:**
- **Do NOT create `code-analyzer.yml` proactively** — only when user asks to change something
- **Do NOT duplicate built-in defaults** — only write entries that intentionally override behavior
- **Always place at project root** — where `sfdx-project.json` or `sf-project.json` lives
- **The CLI auto-discovers it** — `sf code-analyzer run` from project root automatically picks up `code-analyzer.yml` in that directory. No `--config-file` flag needed.
- User says "configure code analyzer" with no specifics? → **Ask what they want to customize**. Don't create an empty or boilerplate file.

**Workflow:**
1. User requests a customization (e.g., "disable PMD", "ignore test files", "increase SFGE memory")
2. Check if `code-analyzer.yml` exists at project root
3. If NO → create it at project root with ONLY the requested override
4. If YES → read it, then edit in the requested change
5. Validate with `sf code-analyzer config`

---

## Step 1: Understand Intent and Map to Config Sections

The user can request ANY combination of configuration changes in natural language. Your job is to:

1. **Parse what they want** — may be one thing or many things combined
2. **Map each request to the correct section(s) of `code-analyzer.yml`**
3. **Create the file if it doesn't exist, then apply all changes**

### The `code-analyzer.yml` Structure (what you can write/edit)

```yaml
config_root: .                    # Root for relative path resolution
log_folder: <path>                # Where logs are written
log_level: <1-5>                  # 1=Error, 2=Warn, 3=Info, 4=Debug, 5=Fine

ignores:                          # Files/folders excluded from scanning
  files: [<glob patterns>]

engines:                          # Per-engine settings
  <engine_name>:
    disable_engine: <bool>
    <engine_specific_keys>: ...

rules:                            # Per-rule overrides
  <engine_name>:
    <rule_name>:
      severity: <1-5>
      tags: [<strings>]
      disabled: <bool>

suppressions:                     # Bulk suppression configuration
  disable_suppressions: <bool>
  "<file_or_folder_path>":
    - rule_selector: "<selector>"
      max_suppressed_violations: <number|null>
      reason: "<why>"
```

### Mapping Principle

Any user request maps to one or more sections above. Parse the intent and edit the right section(s):

| Intent Category | Maps To | Examples of What User Might Say |
|----------------|---------|-------------------------------|
| Setup / Install | Step 2 (prerequisites + install) | "set up", "install", "get started", "new laptop", "from scratch" |
| **Diagnose / Fix** | **Step 2A (systematic debug)** | **"not working", "broken", "fix my setup", "scan fails", "getting errors"** |
| Engine control | `engines.<name>.disable_engine` | "disable X", "turn off Y", "only use Z", "enable all" |
| Engine tuning | `engines.<name>.<property>` | "increase memory", "change heap", "use my eslint config", "set tokens to 50" |
| File exclusions | `ignores.files` | "exclude", "ignore", "skip", "don't scan X" |
| Rule severity | `rules.<engine>.<rule>.severity` | "make X critical", "promote", "demote", "change severity" |
| Rule disable | `rules.<engine>.<rule>.disabled` | "disable rule X", "turn off Y rule", "remove Z" |
| Rule tags | `rules.<engine>.<rule>.tags` | "tag X as security", "add recommended tag" |
| Suppressions | `suppressions` section | "suppress X in folder Y", "allow N violations" |
| CI/CD | Generate pipeline file (separate from config) | "github actions", "CI", "quality gate" |
| View/inspect | Read file + `sf code-analyzer config` | "show config", "what's configured", "current settings" |

### File Existence Decision

**BEFORE editing anything**, check if `code-analyzer.yml` exists at project root:

```bash
ls code-analyzer.yml code-analyzer.yaml 2>/dev/null
```

- **File does NOT exist** → Create it at project root with ONLY the user's requested override(s)
- **File exists** → Read it, then Edit to add/modify the requested section(s)

The CLI auto-discovers `code-analyzer.yml` in the current directory. Since scans run from project root, the file must live there.

### ⚠️ Rule Name Resolution — ALWAYS Before Writing YAML

When a user references rules by partial, descriptive, or approximate names (e.g., "the doc rule", "CRUD violation", "console rule", "hardcoded values"), you MUST resolve to exact rule names using the lookup in **Step 6.1** BEFORE writing any YAML. The `code-analyzer.yml` file silently ignores rule names that don't exactly match — there is no error, the override just won't apply.

**Examples of fuzzy → exact resolution needed:**
- "Disable the ApexDoc rule" → lookup confirms `ApexDoc` (engine: `pmd`)
- "Demote no-console to low" → lookup confirms `no-console` (engine: `eslint`)
- "Make CRUD violations critical" → lookup confirms `ApexCRUDViolation` (engine: `pmd`)
- "Turn off the hardcoded values check" → lookup finds `@salesforce-ux/slds/no-hardcoded-values-slds2` (engine: `eslint`)
- "Disable the injection rule" → multiple matches possible → ask user which one

**Only skip the lookup** when the user provides an unambiguous, exact, well-known name (e.g., "ApexDoc", "no-console", "no-unused-vars").

### Handling Combined/Complex Requests

Users will often combine multiple changes in one request. Handle ALL of them in a single edit:

- "Disable PMD's ApexDoc rule and make CRUD violations critical" → edit two entries under `rules.pmd`
- "Exclude test files and vendor code, and increase SFGE memory" → edit `ignores.files` + `engines.sfge.java_max_heap_size`
- "Set up code analyzer with only ESLint and PMD, ignore node_modules" → create file with `engines` (disable others) + `ignores`
- "Make all security rules severity 1" → look up rules via `sf code-analyzer rules --rule-selector Security`, then override each
- "Configure code analyzer" (no specifics) → ask user what they want to customize before creating any file

### Quick Reference: Common Requests → Config Output

| User Says | Resulting YAML |
|-----------|---------------|
| "configure code analyzer" | Ask user what to customize — don't create file until there's an actual override |
| "disable the ApexDoc rule" | `rules: pmd: ApexDoc: disabled: true` |
| "only scan Apex, no JavaScript" | `engines: eslint: disable_engine: true` + `engines: retire-js: disable_engine: true` |
| "ignore all test files" | `ignores: files: ["**/test/**", "**/__tests__/**", "**/*.test.js"]` |
| "make security rules critical" | Look up rules, then `rules: <engine>: <rule>: severity: 1` for each |
| "increase SFGE memory to 8g" | `engines: sfge: java_max_heap_size: "8g"` |
| "use my project's ESLint config" | `engines: eslint: auto_discover_eslint_config: true` |
| "suppress CRUD violations in legacy folder" | `suppressions: "force-app/legacy/": [{rule_selector: "pmd:ApexCRUDViolation", reason: "..."}]` |

**The AI must understand the YAML schema and write valid config for ANY request, not just the examples above.**

---

## Step 2: Check Prerequisites and Install

Run `bash "<skill_dir>/scripts/check-prerequisites.sh"` or check manually:

```bash
sf --version 2>&1                                    # sf CLI
sf plugins --core 2>&1 | grep -i "code-analyzer"    # Plugin
java -version 2>&1                                   # Java 11+ (PMD, CPD, SFGE)
node --version 2>&1                                  # Node 18+ (ESLint, RetireJS)
python3 --version 2>&1                               # Python 3 (Flow engine)
```

If anything is missing, install it (**always ask user first**):

```bash
npm install -g @salesforce/cli                       # sf CLI
sf plugins install @salesforce/plugin-code-analyzer  # Code Analyzer plugin
```

For Java/Node/Python installs, read `<skill_dir>/references/engine-prerequisites.md`.
If install fails, read `<skill_dir>/references/troubleshooting.md`.

---

## Step 2A: Diagnose and Fix a Broken Setup

**TRIGGER:** User says "not working", "broken", "getting errors", "scan fails", "help me fix", etc.

**Read `<skill_dir>/references/diagnostic-flow.md`** for the complete layered diagnostic procedure, fix table, and anti-patterns.

**Key principles (always apply):**
- Never search for binaries (`which`, `find`, `ls /opt/homebrew/bin/`)
- Never use `sfdx` as a workaround — only `sf`
- Fix layer by layer: CLI → Plugin → Engine deps → verify scan
- Give user ONE command at a time, wait for confirmation before continuing
- After fix succeeds, proceed to run the full scan automatically

---

## Step 3: Create or Edit `code-analyzer.yml`

**Only triggered when user requests a customization.** Never create proactively.

### Creating (file doesn't exist)

Choose **one** of the two approaches below — do not run both:

**Option A — Auto-generate from project type (recommended for first-time setup):**

Run `bash "<skill_dir>/scripts/generate-config.sh"`. This detects Apex, LWC, and Flow markers and produces a minimal `code-analyzer.yml` suited to the project. Skip to the "After any create/edit, validate" section.

> Note: The script exits with an error if `code-analyzer.yml` already exists. Delete the existing file first if you need to regenerate.

**Option B — Write manually (when the user has specific customizations in mind):**

Read the appropriate example config as a reference for structure:
- For Apex-only projects, read `<skill_dir>/examples/apex-project-config.yml`
- For LWC-only projects, read `<skill_dir>/examples/lwc-project-config.yml`
- For full-stack (Apex + LWC + Flows), read `<skill_dir>/examples/fullstack-project-config.yml`

Write the file at project root using the Write tool. Include ONLY the user's requested changes:

```bash
# Example: user said "ignore test files and increase SFGE memory"
# → Write to project root (where sfdx-project.json lives):
```

```yaml
ignores:
  files:
    - "**/test/**"
    - "**/__tests__/**"

engines:
  sfge:
    java_max_heap_size: "4g"
```

Do NOT add `config_root`, `log_folder`, or any other field the user didn't ask for.

### Editing (file already exists)

Read the file, then use the Edit tool to add/modify only the relevant section. Preserve everything else.

### After any create/edit, validate:

Run `bash "<skill_dir>/scripts/validate-config.sh"` to validate YAML syntax and schema correctness, or use the CLI directly:

```bash
sf code-analyzer config
```

(No `--config-file` needed — the CLI auto-discovers `code-analyzer.yml` in CWD.)

### If user says "configure code analyzer" with no specifics

Ask: "What would you like to customize? For example: ignore certain files, change rule severities, tune engine settings, or disable engines you don't need."

---

## Step 4: Enable/Disable Engines

Edit the `engines` section in `code-analyzer.yml`:

```yaml
engines:
  pmd:
    disable_engine: true       # Disable PMD
  eslint:
    disable_engine: false      # Enable ESLint (default)
```

Valid engine names: `pmd`, `cpd`, `eslint`, `regex`, `retire-js`, `flow`, `sfge`, `apexguru`

**Always validate after editing:**
```bash
sf code-analyzer config --config-file code-analyzer.yml
```

---

## Step 5: Ignore Patterns

Edit the `ignores` section in `code-analyzer.yml`:

```yaml
ignores:
  files:
    - "**/node_modules/**"
    - "**/.sfdx/**"
    - "**/.sf/**"
    - "**/vendor/**"
    - "**/*.min.js"
```

Common patterns:

| Pattern | Excludes |
|---------|----------|
| `**/node_modules/**` | npm dependencies |
| `**/.sfdx/**`, `**/.sf/**` | SF CLI internals |
| `**/test/**`, `**/__tests__/**` | Test directories |
| `**/*.test.js`, `**/*.spec.js` | Test files |
| `**/jest-mocks/**` | Jest mocks |
| `**/vendor/**`, `**/*.min.js` | Third-party/minified |
| `**/staticresources/**` | Static resources |

---

## Step 6: Rule Overrides

Edit the `rules` section in `code-analyzer.yml`. Each rule can have `severity`, `tags`, and `disabled` overrides:

```yaml
rules:
  pmd:
    ApexCRUDViolation:
      severity: 1              # Promote to Critical
    AvoidGlobalModifier:
      disabled: true           # Turn off entirely
    ApexDoc:
      severity: 5              # Demote to Info
      tags: ["Documentation"]
  eslint:
    no-console:
      severity: 4              # Demote to Low
    no-unused-vars:
      severity: 2              # Promote to High
```

**Severity values:** `1`/Critical, `2`/High, `3`/Moderate, `4`/Low, `5`/Info

### 6.1 Rule Name Resolution (Fuzzy Matching)

**⚠️ CRITICAL:** A misspelled or partial rule name in `code-analyzer.yml` is SILENTLY IGNORED — no error, the override just won't apply.

**When users reference rules by approximate names** (e.g., "the doc rule", "CRUD violation", "hardcoded values"), resolve to exact names BEFORE writing YAML:

```bash
sf code-analyzer rules --rule-selector all 2>&1 | grep -i "<USER_KEYWORD>"
```

- **1 match** → use that exact name + its engine for the YAML path
- **Multiple matches** → ask user which one they meant
- **0 matches** → try broader keywords or inform user

**Skip the lookup only** when the name is unambiguous and exact (e.g., "ApexDoc", "no-console", "no-unused-vars").

**For detailed matching strategies, common fuzzy→exact mappings, and engine identification:** Read `<skill_dir>/references/rule-name-resolution.md`.

---

## Step 7: Engine-Specific Settings

Edit the `engines` section. Most common overrides:

```yaml
engines:
  sfge:
    java_max_heap_size: "4g"      # <200 classes→"2g", 200-500→"4g", 500+→"6g"/"8g"
    java_thread_count: 4
    java_thread_timeout: 900000
  eslint:
    auto_discover_eslint_config: true    # Use project's own ESLint config
    eslint_config_file: "./eslint.config.mjs"
  pmd:
    custom_rulesets: ["./config/custom-pmd-rules.xml"]
    java_classpath_entries: ["./lib/custom-rules.jar"]
  cpd:
    minimum_tokens: { apex: 100, javascript: 100 }
  apexguru:
    target_org: "my-org-alias"
  flow:
    python_command: "python3"
  regex:
    custom_rules:
      NoHardcodedIds:
        regex: "/[a-zA-Z0-9]{15,18}/"
        file_extensions: [".cls", ".trigger"]
        description: "Detects hardcoded Salesforce record IDs"
        severity: 2
        tags: ["Security"]
```

For full property list per engine, read `<skill_dir>/references/config-schema.md`.

---

## Step 8: CI/CD Pipeline Setup

Detect CI system from workspace (`.github/workflows/` → GitHub Actions, `Jenkinsfile` → Jenkins, etc.). Read `<skill_dir>/references/ci-cd-templates.md` for templates. Use `<skill_dir>/examples/ci-github-actions.yml` as GitHub Actions base. Key flags: `--severity-threshold 2` (gate), `--output-file results.sarif` (GitHub scanning), `--config-file code-analyzer.yml`.

---

## Step 9: View Current Configuration

```bash
sf code-analyzer config                               # Show effective config
sf code-analyzer config --rule-selector pmd:Security  # Specific rules
sf code-analyzer config --include-unmodified-rules    # All defaults
```

---

## Cross-Skill Integration

This skill works together with `dx-code-analyzer-run`. The AI agent should seamlessly hand off between them:

### When `dx-code-analyzer-run` delegates HERE:

If a user says "scan my code" / "run code analyzer" but it fails (CLI missing, plugin not installed, or scan errors out), `dx-code-analyzer-run` delegates to this skill. In that case:

1. Run the **diagnose and fix** flow (Step 2A) — find what's broken, fix it
2. After everything works, **automatically proceed to run the scan** — do not stop and ask. The user's original intent was to scan.
3. Hand execution back to `dx-code-analyzer-run` behavior (build command, execute, parse results).

### When THIS skill hands off to `dx-code-analyzer-run`:

After any successful configuration action, offer to run a scan (e.g., "Setup complete! Want me to run a scan?", "Config updated — want to scan and verify?"). If user says yes, proceed with `dx-code-analyzer-run` behavior.

### When user intent spans BOTH skills:

Handle end-to-end: "not working" → Diagnose → Fix → Scan. "Set up and scan" → Install → Scan. "Disable ESLint and scan Apex" → Edit config → Run with `--rule-selector pmd`. Always follow through to the user's final intent.

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| Only create YAML when user requests a customization | Defaults work without any file — don't create boilerplate |
| Place YAML at project root only | CLI auto-discovers `code-analyzer.yml` from CWD |
| Write only overrides, never duplicate defaults | Keep file minimal and intentional |
| Use Write tool to create, Edit tool to modify | Preserves existing settings |
| Validate after every change | `sf code-analyzer config` catches YAML errors |
| Ask before installing prerequisites | Never auto-install without consent |
| Never delete existing config without asking | User may have custom settings |
| After setup, offer to scan | Close the loop — config without scan is incomplete |

---

## Gotchas

| Issue | Solution |
|-------|----------|
| Config not picked up | Must be `code-analyzer.yml` in CWD or use `--config-file` |
| YAML validation fails | Spaces only (no tabs), check colon spacing |
| SFGE out of memory | Increase `java_max_heap_size` in engines section |
| ESLint rules missing | Set `auto_discover_eslint_config: true` |

For full troubleshooting, read `<skill_dir>/references/troubleshooting.md`.

---

## Reference File Index

`<skill_dir>` is the absolute path to the directory containing this SKILL.md file.

| File | Purpose |
|------|---------|
| `<skill_dir>/scripts/check-prerequisites.sh` | Environment check |
| `<skill_dir>/scripts/generate-config.sh` | Auto-detect project type and generate config |
| `<skill_dir>/scripts/validate-config.sh` | Validate YAML after changes |
| `<skill_dir>/references/config-schema.md` | Full YAML schema documentation |
| `<skill_dir>/references/diagnostic-flow.md` | Step 2A: layered diagnostic procedure and fix table |
| `<skill_dir>/references/rule-name-resolution.md` | Step 6.1: fuzzy rule name lookup strategies and mappings |
| `<skill_dir>/references/engine-prerequisites.md` | Install instructions per engine |
| `<skill_dir>/references/ci-cd-templates.md` | CI/CD pipeline templates |
| `<skill_dir>/references/troubleshooting.md` | Common setup issues and fixes |
| `<skill_dir>/examples/apex-project-config.yml` | Config for Apex-only project |
| `<skill_dir>/examples/lwc-project-config.yml` | Config for LWC-only project |
| `<skill_dir>/examples/fullstack-project-config.yml` | Config for Apex + LWC + Flows |
| `<skill_dir>/examples/ci-github-actions.yml` | GitHub Actions workflow |
