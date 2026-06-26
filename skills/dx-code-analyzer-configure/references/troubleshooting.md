# Troubleshooting Code Analyzer Setup

Common issues and solutions during installation and configuration.

## Installation Issues

### sf CLI Not Found

**Symptom:** `sf: command not found` or `'sf' is not recognized`

**Solutions:**
1. Check if installed: `which sf` or `where sf`
2. If not installed: `npm install -g @salesforce/cli`
3. If installed but not in PATH:
   - macOS/Linux: Add `export PATH="$(npm prefix -g)/bin:$PATH"` to `~/.zshrc` or `~/.bashrc`
   - Windows: Add npm global bin to System PATH
4. Restart terminal after PATH changes

### Plugin Install Fails

**Symptom:** `Error: EACCES permission denied` or timeout errors

**Solutions:**
| Error | Fix |
|-------|-----|
| Permission denied | `sudo sf plugins install @salesforce/plugin-code-analyzer` or fix npm permissions |
| Network timeout | Check proxy: `npm config set proxy http://proxy:port` |
| Node version error | Upgrade Node.js to 18+: `nvm install 20 && nvm use 20` |
| Corrupt install | `sf plugins uninstall @salesforce/plugin-code-analyzer && sf plugins install @salesforce/plugin-code-analyzer` |

### Plugin Version Mismatch

**Symptom:** Command flags don't work, unexpected behavior

**Check version:**
```bash
sf plugins --core | grep code-analyzer
```

**Expected:** `@salesforce/plugin-code-analyzer` v5.x+

**If on v3/v4 (legacy):**
```bash
sf plugins uninstall @salesforce/sfdx-scanner  # Remove legacy v3
sf plugins install @salesforce/plugin-code-analyzer  # Install v5+
```

## Java Issues

### Java Not Found

**Symptom:** PMD/CPD/SFGE fails with `java: command not found` or `JAVA_HOME not set`

**Fix:**
```bash
# macOS
brew install openjdk@11
export JAVA_HOME="/opt/homebrew/opt/openjdk@11"
export PATH="$JAVA_HOME/bin:$PATH"

# Add to ~/.zshrc for persistence
echo 'export JAVA_HOME="/opt/homebrew/opt/openjdk@11"' >> ~/.zshrc
echo 'export PATH="$JAVA_HOME/bin:$PATH"' >> ~/.zshrc
```

### Wrong Java Version

**Symptom:** `UnsupportedClassVersionError` or `class file version X.Y`

**Fix:** Code Analyzer needs Java 11+. Check and switch:
```bash
java -version  # Check current

# If using SDKMAN:
sdk install java 11.0.21-tem
sdk use java 11.0.21-tem

# If using Homebrew:
brew install openjdk@11
export JAVA_HOME="/opt/homebrew/opt/openjdk@11"
```

### SFGE Out of Memory

**Symptom:** `java.lang.OutOfMemoryError: Java heap space`

**Fix:** Increase heap in `code-analyzer.yml`:
```yaml
engines:
  sfge:
    java_max_heap_size: "4g"  # Default is 1g, increase for large projects
```

**Guidelines:**
| Project Size | Heap Recommendation |
|-------------|-------------------|
| < 200 Apex classes | 2g |
| 200-500 Apex classes | 4g |
| 500-1000 Apex classes | 6g |
| 1000+ Apex classes | 8g |

## Node.js Issues

### Node.js Version Too Old

**Symptom:** `Error: Node.js v16 is not supported` or ESLint failures

**Fix:**
```bash
# Check version
node --version

# Upgrade via nvm
nvm install 20
nvm use 20
nvm alias default 20

# Or via Homebrew
brew upgrade node
```

### ESLint Config Conflicts

**Symptom:** ESLint rules not loading, or unexpected rules appearing

**Possible causes:**
1. Project has its own `.eslintrc.*` conflicting with Code Analyzer's built-in config
2. `auto_discover_eslint_config` is enabled but project config is incompatible

**Fix options:**
```yaml
# Option A: Disable auto-discovery (use only Code Analyzer's built-in rules)
engines:
  eslint:
    auto_discover_eslint_config: false

# Option B: Use project's config exclusively
engines:
  eslint:
    auto_discover_eslint_config: true
    disable_javascript_base_config: true
    disable_typescript_base_config: true
    disable_lwc_base_config: true
```

## Configuration Issues

### Config File Not Picked Up

**Symptom:** Custom settings not applied, default behavior persists

**Checklist:**
1. File must be named exactly `code-analyzer.yml` or `code-analyzer.yaml`
2. File must be in the current working directory when running commands
3. Or specify explicitly: `--config-file ./path/to/code-analyzer.yml`
4. Check for YAML syntax errors: `sf code-analyzer config --config-file code-analyzer.yml`

### YAML Syntax Errors

**Symptom:** `YAMLException: bad indentation` or `unexpected token`

**Common YAML mistakes:**
```yaml
# WRONG - tabs instead of spaces
engines:
	pmd:           # TAB character - YAML requires spaces!

# CORRECT - spaces only
engines:
  pmd:             # 2 spaces

# WRONG - missing quotes around special values
rules:
  pmd:
    MyRule:
      severity: High    # String values need quotes or use numbers

# CORRECT
rules:
  pmd:
    MyRule:
      severity: 2       # Use numbers 1-5
      # OR
      severity: "High"  # Or quoted strings
```

### Unknown Engine or Rule Name

**Symptom:** Rule selector returns 0 results

**Fix:** Verify the engine/rule name:
```bash
# List all available engines
sf code-analyzer rules --rule-selector all 2>&1 | head -50

# Search for a specific rule
sf code-analyzer rules --rule-selector all 2>&1 | grep -i "CRUD"

# List rules for specific engine
sf code-analyzer rules --rule-selector pmd 2>&1 | head -50
```

## Engine-Specific Issues

### PMD: Custom Rules Not Loading

**Symptom:** Custom PMD rules don't appear in `sf code-analyzer rules`

**Checklist:**
1. Ruleset XML must be valid PMD format
2. Path in `custom_rulesets` must be relative to `config_root`
3. For Java rules: JAR must be in `java_classpath_entries`
4. Validate: `sf code-analyzer rules --rule-selector pmd:<YourRuleName>`

### RetireJS: False Positives on Test Files

**Symptom:** RetireJS flags test fixtures or mock data

**Fix:** Add test paths to ignores:
```yaml
ignores:
  files:
    - "**/test/**"
    - "**/__tests__/**"
    - "**/jest-mocks/**"
    - "**/*.test.js"
    - "**/*.spec.js"
```

### Flow Engine: Python Not Found

**Symptom:** `python3: command not found` when scanning Flows

**Fix:**
```bash
# Install Python 3
brew install python3  # macOS
# OR
sudo apt install python3  # Linux

# If python3 is at non-standard path:
# code-analyzer.yml
engines:
  flow:
    python_command: "/usr/local/bin/python3"
```

### ApexGuru: Authentication Error

**Symptom:** `No authenticated org found` or `Session expired`

**Fix:**
```bash
# Login to org
sf org login web --alias my-org

# Set as default
sf config set target-org my-org

# Configure in code-analyzer.yml
engines:
  apexguru:
    target_org: "my-org"
```

## Performance Issues

### Scan Takes Too Long

**Possible causes and solutions:**

| Cause | Solution |
|-------|----------|
| SFGE on large project | Increase heap, reduce thread timeout, or disable SFGE for routine scans |
| Scanning node_modules | Add `**/node_modules/**` to ignores |
| Too many engines enabled | Use `--rule-selector Recommended` instead of `all` for routine scans |
| Large static resources | Add `**/staticresources/**` to ignores |
| Many Flow files | Flow engine can be slow; scan Flows separately |

### Reduce Scan Time in CI

```yaml
# Fast CI scan: recommended rules only, severity gate at High
sf code-analyzer run \
  --rule-selector Recommended \
  --severity-threshold 2 \
  --target force-app/main/default \
  --output-file results.json
```

## Getting Help

If none of the above solves your issue:

1. **Check logs:** Look in the log folder (default: `/tmp` or configured `log_folder`)
2. **Increase log level:** Set `log_level: 5` in config for maximum detail
3. **Run with debug:** `SF_LOG_LEVEL=debug sf code-analyzer run ...`
4. **File an issue:** https://github.com/forcedotcom/code-analyzer-core/issues
