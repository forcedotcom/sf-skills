# Error Handling Guide

Common Code Analyzer errors and their resolutions.

## Common Errors and Resolutions

| Error Pattern | Likely Cause | Resolution |
|---|---|---|
| `command not found: sf` | SF CLI not installed | "Install Salesforce CLI: `npm install -g @salesforce/cli`" |
| `plugin-code-analyzer` not found | Plugin not installed | "Install: `sf plugins install @salesforce/plugin-code-analyzer`" |
| `Java not found` / `JAVA_HOME not set` | Java missing/misconfigured | "Install Java 11+. Set JAVA_HOME or add `engines.pmd.java_command` to config" |
| `Node.js` version error | Old Node version | "Upgrade Node.js to v18+" |
| `Python` not found (Flow engine) | Python not installed | "Install Python 3. Or set `engines.flow.python_command` in config" |
| `Config file error` / YAML parse error | Invalid code-analyzer.yml | "Your config file has a syntax error. Run `sf code-analyzer config` to validate" |
| `No rules matched selector` | Invalid rule selector | Check selector syntax. Run `sf code-analyzer rules --rule-selector <selector>` to verify |
| `Target file does not exist` | File path typo or deleted | Verify file path exists |
| `Org not authenticated` (ApexGuru) | No default org | "Authenticate: `sf org login web --alias myorg`" |
| Timeout / heap space | Large project + SFGE | "Increase heap: add `engines.sfge.java_max_heap_size: '4g'` to code-analyzer.yml" |

## Diagnosis Steps

If the scan command fails:

1. Check the error message for hints
2. Run `sf --version` to verify CLI
3. Run `sf plugins --core | grep code-analyzer` to verify plugin
4. Run `java -version` to verify Java
5. Run `sf code-analyzer rules --rule-selector <selector>` to verify the selector matches rules
6. If config error: run `sf code-analyzer config` to validate
