# Regex Rule Schema Reference

Custom regex rules are defined inline in `code-analyzer.yml` under `engines.regex.custom_rules`.

## Complete Schema

```yaml
engines:
  regex:
    custom_rules:
      RuleName:                          # Must match: /^[A-Za-z@][A-Za-z_0-9@\-/]*$/
        regex: "/pattern/flags"          # REQUIRED — JavaScript regex literal format
        description: "What this checks"  # REQUIRED — Purpose of the rule
        violation_message: "Fix this"    # Optional — Message shown on violation
        severity: 3                      # Optional — 1=Critical, 2=High, 3=Moderate, 4=Low, 5=Info
        tags:                            # Optional — Default: ['Recommended', 'Custom']
          - "Custom"
          - "Security"
        file_extensions:                 # Optional — Default: all text files
          - ".cls"
          - ".trigger"
        regex_ignore: "/exception/i"     # Optional — Matches excluded from violations
```

## Field Details

### `regex` (Required)

JavaScript regex literal format: `/pattern/flags`

| Format | Example | Meaning |
|--------|---------|---------|
| `/pattern/g` | `/TODO/g` | Case-sensitive, global (find all matches) — **minimum required** |
| `/pattern/gi` | `/todo/gi` | Global + case-insensitive |
| `/pattern/gm` | `/^import/gm` | Global + multiline (^ matches each line start) |

**Common pitfalls:**
- **The `/g` (global) flag is REQUIRED.** Code Analyzer rejects regex patterns without at least one flag after the closing `/`. Always include `/g` (or `/gi`, `/gm`, etc.).
- Backslashes must be escaped: `\d` → write as `/\\d/`
- Dots match any character: use `/\\.cls/` not `/.cls/`
- Regex is tested against file content line by line

**Named capture groups** narrow the violation highlight to a specific portion of the match:
```yaml
# Without named group — entire match is highlighted:
regex: "/System\\.debug\\([^)]*\\)/g"
# Highlights: "System.debug('hello')" (entire expression)

# With named group — only captured portion highlighted:
regex: "/(?<target>System\\.debug)\\([^)]*\\)/g"
# Highlights: "System.debug" (just the method name)
```

Use `(?<target>...)` when the regex needs surrounding context to match correctly, but the violation should point to a narrower location. Common patterns:

```yaml
# Highlight just the hardcoded ID, not the surrounding quotes
regex: "/['\"](?<target>[0-9a-zA-Z]{15,18})['\"]/g"

# Highlight the annotation, not the whole line
regex: "/(?<target>@SuppressWarnings\\([^)]*\\))/g"

# Highlight the method call within a larger expression
regex: "/(?<target>Database\\.query)\\(/g"
```

### `description` (Required)

Brief explanation of what the rule enforces. Used in rule listings and generated messages.

### `violation_message` (Optional)

Message shown when a violation is found. If omitted, auto-generated as:
> "A match of the regular expression `<regex>` was found for rule '<RuleName>': <description>"

Good violation messages tell the user HOW to fix, not just WHAT's wrong:
- ❌ "Hardcoded ID found"
- ✅ "Replace hardcoded Salesforce ID with a Custom Label or Custom Metadata reference"

### `severity` (Optional, default: 3)

| Value | Name | Meaning |
|-------|------|---------|
| 1 | Critical | Security vulnerability, must fix before deploy |
| 2 | High | Significant quality issue, should fix |
| 3 | Moderate | Recommended improvement |
| 4 | Low | Minor style issue |
| 5 | Info | Informational, no action required |

Also accepts string names: `"Critical"`, `"High"`, `"Moderate"`, `"Low"`, `"Info"`

### `tags` (Optional, default: ['Recommended', 'Custom'])

Array of tag strings. Used for `--rule-selector` filtering. Common tags:
- `Custom` — auto-applied to user-created rules
- `Security` — security-related rules
- `BestPractices` — coding standards
- `Performance` — performance anti-patterns
- `CodeStyle` — formatting/naming rules

### `file_extensions` (Optional, default: all text files)

Array of file extensions to scan. Each must start with `.` and match: `/^([.][a-zA-Z0-9-_]+)+$/`

Common values for Salesforce:
- `.cls` — Apex classes
- `.trigger` — Apex triggers
- `.js` — JavaScript/LWC
- `.html` — LWC HTML templates
- `.xml` — Metadata files
- `.page` — Visualforce pages
- `.component` — Visualforce components

### `regex_ignore` (Optional)

A second regex pattern — matches that ALSO match this pattern are excluded. Useful for reducing false positives.

⚠️ **`regex_ignore` operates per-LINE, not per-FILE.** It only skips a match if the same line also matches the ignore pattern. It does NOT exclude entire files or classes. For example, adding `/@isTest/` only suppresses violations on lines that literally contain `@isTest` — a hardcoded ID on line 50 of a test class still flags because line 50 doesn't contain `@isTest`.

To exclude entire files, use `ignores.files` in `code-analyzer.yml`:
```yaml
ignores:
  files:
    - "**/*Test.cls"
    - "**/test/**"
```

```yaml
# Flag System.debug everywhere EXCEPT in lines with "// OK" comment
regex: "/System\\.debug/g"
regex_ignore: "/\\/\\/ OK/"
```

## Validation Rules

| Rule | Error if violated |
|------|-------------------|
| Name matches `/^[A-Za-z@][A-Za-z_0-9@\-/]*$/` | "Invalid rule name" |
| Regex starts and ends with `/` | "Invalid regex format" |
| File extensions start with `.` | "Invalid file extension" |
| Severity is 1-5 or valid name | "Invalid severity" |
| No duplicate rule names | "Rule already exists" |

## Multiple Rules Example

```yaml
engines:
  regex:
    custom_rules:
      NoHardcodedIds:
        regex: "/['\"][0-9a-zA-Z]{15,18}['\"]/g"
        description: "Detects hardcoded Salesforce record IDs"
        violation_message: "Use Custom Labels or Custom Metadata instead of hardcoded IDs"
        severity: 2
        tags: ["Custom", "Security"]
        file_extensions: [".cls", ".trigger"]

      NoTodos:
        regex: "/TODO|FIXME|HACK/gi"
        description: "Flags TODO/FIXME/HACK comments that should be resolved"
        violation_message: "Resolve or remove this TODO/FIXME/HACK before merging"
        severity: 4
        tags: ["Custom", "BestPractices"]

      NoSuppressWarnings:
        regex: "/(?<target>@SuppressWarnings\\([^)]*\\))/g"
        description: "Bans @SuppressWarnings annotations — violations must be fixed, not suppressed"
        violation_message: "Remove @SuppressWarnings and fix the underlying violation instead"
        severity: 2
        tags: ["Recommended", "Custom", "BestPractices"]
        file_extensions: [".cls", ".trigger"]
```

⚠️ **Note on test-class exclusion:** The `regex_ignore` field is per-LINE only. Adding `regex_ignore: "/@isTest/i"` does NOT exclude entire test classes — it only skips lines that literally contain `@isTest`. For SOQL rules that should skip test classes, use PMD/XPath instead (which can structurally check `[not(ancestor::UserClass[ModifierNode[@Test = true()]])]`). See the "Excluding Test Classes" section in SKILL.md.
