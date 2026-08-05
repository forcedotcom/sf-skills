# Code Analyzer Configuration Schema

Full reference for the `code-analyzer.yml` configuration file.

## Top-Level Fields

```yaml
# code-analyzer.yml

# Root directory for resolving relative paths in the config
config_root: .

# Directory where Code Analyzer writes log files
log_folder: /tmp

# Log verbosity: 1=Error, 2=Warn, 3=Info, 4=Debug, 5=Fine
log_level: 3

# File patterns to exclude from analysis
ignores:
  files: []

# Rule severity, tag, and disable overrides
rules: {}

# Engine-specific configuration
engines: {}

# Bulk suppression rules
suppressions:
  disable_suppressions: false
```

## Ignores Section

```yaml
ignores:
  files:
    - "**/node_modules/**"      # npm dependencies
    - "**/.sfdx/**"             # Salesforce DX internal
    - "**/.sf/**"               # Salesforce CLI internal
    - "**/test/**"              # Test directories
    - "**/*.test.js"            # Test files
    - "**/*.min.js"             # Minified files
    - "**/staticresources/**"   # Static resources (often vendor)
```

**Pattern syntax:** Glob patterns using `*` (any filename chars), `**` (any path segment), `?` (single char).

## Rules Section

Override severity, tags, or disable rules per engine:

```yaml
rules:
  <engine_name>:
    <rule_name>:
      severity: <1-5 or "Critical"|"High"|"Moderate"|"Low"|"Info">
      tags: ["Tag1", "Tag2"]    # Override rule tags
      disabled: true|false       # Disable/enable rule
```

### Severity Values

| Number | Name | Meaning |
|--------|------|---------|
| 1 | Critical | Security vulnerabilities, must fix before release |
| 2 | High | Significant issues, should fix |
| 3 | Moderate | Recommended improvements |
| 4 | Low | Minor suggestions |
| 5 | Info | Informational, no action required |

### Example Rule Overrides

```yaml
rules:
  pmd:
    ApexCRUDViolation:
      severity: 1               # Promote to Critical
    AvoidGlobalModifier:
      disabled: true            # Disable entirely
    ApexDoc:
      severity: 5              # Demote to Info
      tags: ["Documentation"]
  eslint:
    no-console:
      severity: 4              # Demote to Low
    no-unused-vars:
      severity: 2              # Promote to High
```

## Engines Section

### PMD Engine

```yaml
engines:
  pmd:
    disable_engine: false
    java_command: "java"                    # Path to Java executable
    custom_rulesets:                        # Additional ruleset XML files
      - "./config/custom-pmd-rules.xml"
    java_classpath_entries:                 # JARs for custom Java rules
      - "./lib/my-custom-rules.jar"
    file_extensions:                        # Override scanned file types
      apex: [".cls", ".trigger"]
      visualforce: [".page", ".component"]
```

### ESLint Engine

```yaml
engines:
  eslint:
    disable_engine: false
    auto_discover_eslint_config: true       # Use project's eslint config files
    eslint_config_file: "./eslint.config.mjs"  # Explicit config file path
    disable_javascript_base_config: false   # Disable built-in JS rules
    disable_typescript_base_config: false   # Disable built-in TS rules
    disable_lwc_base_config: false          # Disable built-in LWC rules
    disable_flow_base_config: false         # Disable built-in Flow rules
```

**Note:** `auto_discover_eslint_config` requires a `--workspace` flag on the run command.

### CPD Engine (Copy-Paste Detector)

```yaml
engines:
  cpd:
    disable_engine: false
    minimum_tokens:                         # Min tokens for duplicate detection
      apex: 100                             # Lower = more sensitive
      html: 100
      javascript: 100
      visualforce: 100
      xml: 100
    skip_duplicate_files: false             # Skip files with identical content
```

### SFGE Engine (Salesforce Graph Engine)

```yaml
engines:
  sfge:
    disable_engine: false
    java_max_heap_size: "4g"               # JVM heap (increase for large projects)
    java_thread_count: 4                    # Parallel threads
    java_thread_timeout: 900000             # Per-thread timeout in ms
```

**Warning:** SFGE is resource-intensive. For projects with 500+ Apex classes, use 4g+ heap. Analysis can take 10-30 minutes.

### ApexGuru Engine

```yaml
engines:
  apexguru:
    disable_engine: false
    target_org: "my-org-alias"             # Authenticated org alias or username
    api_timeout_ms: 300000                  # API timeout in ms (default 5min)
```

**Requires:** Authenticated Salesforce org (`sf org login web`).

### Flow Engine

```yaml
engines:
  flow:
    disable_engine: false
    python_command: "python3"              # Path to Python 3 executable
```

**Requires:** Python 3 installed.

### Regex Engine

```yaml
engines:
  regex:
    disable_engine: false
    custom_rules:
      <RuleName>:
        regex: "/<pattern>/<flags>"         # JavaScript regex syntax
        regex_ignore: "/<pattern>/<flags>"  # Optional: false positive filter
        file_extensions: [".cls", ".trigger"]
        description: "What this rule checks"
        violation_message: "Message shown to developer"
        severity: 3
        tags: ["Recommended", "Security"]
```

### RetireJS Engine

```yaml
engines:
  retire-js:
    disable_engine: false
```

**Note:** RetireJS scans JavaScript dependencies for known CVEs. No additional configuration needed beyond enable/disable.

## Suppressions Section

```yaml
suppressions:
  disable_suppressions: false              # Set true to ignore ALL suppressions

  # Bulk suppressions by file/folder path
  "src/legacy/":
    - rule_selector: "pmd:ApexDoc"
      max_suppressed_violations: 50        # Quota (null = unlimited)
      reason: "Legacy code, documentation not required"

  "src/utils/Logger.cls":
    - rule_selector: "eslint:no-console"
      max_suppressed_violations: 10
      reason: "Logger intentionally uses console"
```

### Inline Suppression Markers

In addition to bulk config suppressions, violations can be suppressed inline:

```java
// Apex: PMD suppression
// NOPMD - reason here
@SuppressWarnings('PMD.ApexCRUDViolation')

// Any engine: universal marker
// code-analyzer-suppress(pmd:ApexCRUDViolation) - reason
// code-analyzer-suppress(eslint:no-console) - reason
```

## Config File Discovery

Code Analyzer automatically looks for configuration in this order:
1. File specified via `--config-file` flag
2. `code-analyzer.yml` in current working directory
3. `code-analyzer.yaml` in current working directory
4. No config (use defaults)

## Validating Configuration

Always validate after making changes:

```bash
# Validate config and show effective settings
sf code-analyzer config --config-file code-analyzer.yml

# Show config for specific rules
sf code-analyzer config --rule-selector pmd:Security

# Show all rule defaults (verbose)
sf code-analyzer config --include-unmodified-rules --rule-selector all
```
