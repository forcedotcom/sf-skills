# ESLint Custom Rules for LWC/JavaScript

Create and integrate custom ESLint rules for Lightning Web Components, JavaScript, and TypeScript through Code Analyzer.

## How It Works

Code Analyzer's ESLint engine loads your project's ESLint configuration alongside its built-in rules. You can:
- Use your own `eslint.config.js` with custom plugins
- Extend or override built-in base configs (LWC, TypeScript, SLDS, React)
- Install any npm ESLint plugin and have Code Analyzer pick it up

## Configuration

```yaml
# code-analyzer.yml
engines:
  eslint:
    # Point to your project's ESLint config
    eslint_config_file: "eslint.config.js"

    # Or auto-discover from workspace (searches for eslint.config.js/mjs/cjs)
    auto_discover_eslint_config: true

    # Disable base configs you don't need
    disable_javascript_base_config: false
    disable_lwc_base_config: false
    disable_typescript_base_config: false
    disable_slds_base_config: false
    disable_react_base_config: false

    # Custom file extension mapping
    file_extensions:
      javascript: [".js", ".cjs", ".mjs", ".jsx"]
      typescript: [".ts", ".tsx"]
      html: [".html", ".htm", ".cmp"]
      css: [".css", ".scss"]
```

## Adding Custom ESLint Plugins

### Step 1: Install the plugin

```bash
npm install --save-dev eslint-plugin-my-custom
```

### Step 2: Create or update `eslint.config.js` (flat config)

```javascript
const myPlugin = require('eslint-plugin-my-custom');

module.exports = [
    {
        plugins: {
            'my-custom': myPlugin
        },
        rules: {
            'my-custom/no-dangerous-pattern': 'error',
            'my-custom/enforce-naming': ['warn', { pattern: '^[a-z]' }]
        }
    }
];
```

### Step 3: Reference in `code-analyzer.yml`

```yaml
engines:
  eslint:
    eslint_config_file: "eslint.config.js"
```

### Step 4: Validate and run

```bash
# Check that custom rules appear
sf code-analyzer rules --rule-selector eslint

# Run against targets
sf code-analyzer run --rule-selector eslint --target force-app/main/default/lwc/
```

## Common LWC Custom Rule Patterns

### Enforce component naming convention

```javascript
// eslint.config.js
module.exports = [
    {
        rules: {
            '@lwc/lwc/no-unknown-wire-adapters': 'error',
            '@lwc/lwc/no-api-reassignments': 'error',
            '@lwc/lwc/no-leaky-event-listeners': 'error'
        }
    }
];
```

### Add SSR compatibility checks

```javascript
module.exports = [
    {
        rules: {
            '@lwc/lwc/no-restricted-browser-globals-during-ssr': 'error',
            '@lwc/lwc/no-unsupported-ssr-properties': 'error'
        }
    }
];
```

### TypeScript strict rules

```javascript
module.exports = [
    {
        rules: {
            '@typescript-eslint/no-explicit-any': 'error',
            '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
            '@typescript-eslint/strict-boolean-expressions': 'warn'
        }
    }
];
```

## Disabling Base Configs

When you want full control over which rules run, disable the built-in base configs:

```yaml
engines:
  eslint:
    eslint_config_file: "eslint.config.js"
    disable_javascript_base_config: true
    disable_lwc_base_config: true
    disable_typescript_base_config: true
```

This prevents Code Analyzer's bundled rules from running — only your custom config's rules apply. Parsers are still configured (so files parse correctly), but no built-in rules fire.

## Overriding Rule Severity via Config

After ESLint rules are loaded, override severity in `code-analyzer.yml`:

```yaml
rules:
  eslint:
    no-unused-vars:
      severity: "Low"
    my-custom/dangerous-pattern:
      severity: "Critical"
    no-console:
      disabled: true
```

## Legacy Config Support

If your project uses `.eslintrc.js` (ESLint v8 format), it still works:

```yaml
engines:
  eslint:
    eslint_config_file: ".eslintrc.js"
    eslint_ignore_file: ".eslintignore"    # Only needed with legacy config
```

Flat config (`eslint.config.js`) is recommended for new projects.

## Plugin Requirements

For Code Analyzer to pick up custom plugin rules, each rule must have:
- `meta.docs.description` — rule description
- `meta.docs.url` — documentation URL

Rules without these metadata fields are silently excluded. Deprecated rules are also excluded.

## Banning APIs Without a Custom Plugin

Core ESLint includes powerful "restrictor" rules that can ban specific globals, syntax patterns, or properties — no plugin installation needed. These rules are NOT active by default — you must enable them in `eslint.config.js`:

### `no-restricted-globals` — ban global functions/variables

```javascript
module.exports = [
    {
        files: ["**/lwc/**/*.js"],
        rules: {
            "no-restricted-globals": ["error",
                { "name": "setTimeout", "message": "Use lifecycle hooks instead of setTimeout." },
                { "name": "setInterval", "message": "Use lifecycle hooks instead of setInterval." },
                { "name": "eval", "message": "eval is forbidden for security." }
            ]
        }
    }
];
```

### `no-restricted-syntax` — ban arbitrary AST patterns

```javascript
module.exports = [
    {
        files: ["**/lwc/**/*.js"],
        rules: {
            "no-restricted-syntax": ["error",
                { "selector": "CallExpression[callee.name='fetch']", "message": "Use Lightning Data Service instead of fetch." },
                { "selector": "NewExpression[callee.name='XMLHttpRequest']", "message": "Use fetch or LDS." }
            ]
        }
    }
];
```

### `no-restricted-properties` — ban specific object methods

```javascript
module.exports = [
    {
        files: ["**/lwc/**/*.js"],
        rules: {
            "no-restricted-properties": ["error",
                { "object": "window", "property": "location", "message": "Use NavigationMixin." },
                { "object": "document", "property": "cookie", "message": "Cookies are not available in LWC." }
            ]
        }
    }
];
```

⚠️ **These rules will NOT appear in `sf code-analyzer rules` output until you:**
1. Create the `eslint.config.js` file with the rule enabled
2. Set `engines.eslint.eslint_config_file: "eslint.config.js"` in `code-analyzer.yml`
3. Run `sf code-analyzer rules --rule-selector eslint:no-restricted-globals` to verify

They are core ESLint rules, not Code Analyzer built-ins — they require your config to activate.

## When to Use ESLint vs Regex vs PMD

| Need | Engine |
|------|--------|
| JavaScript/TypeScript code patterns | **ESLint** |
| LWC component best practices | **ESLint** (with @lwc plugin) |
| HTML template issues | **ESLint** (with SLDS or custom HTML plugin) |
| Simple string patterns in JS/TS | **ESLint** (Regex cannot distinguish code from comments/strings in JS) |
| Apex code structure | **PMD** (ESLint doesn't parse Apex) |
| Metadata XML governance | **PMD** with `language="xml"` |
