# Troubleshooting Custom Rules

## Regex Rule Issues

| Problem | Cause | Fix |
|---------|-------|-----|
| "Invalid rule name" | Name starts with number or contains spaces | Use PascalCase: `NoHardcodedIds`, `BanTodoComments` |
| "Invalid regex" | Missing `/` delimiters | Must be `/pattern/flags` format |
| YAML parse error when adding regex | Quotes/backslashes in regex conflict with YAML syntax | **Use `create-regex-rule.js` script** — do not manually write regex into YAML. The script handles serialization correctly. |
| Rule not listed | YAML indentation wrong | Must be under `engines.regex.custom_rules` with correct nesting |
| No violations found | Regex doesn't match content | Test regex at regex101.com with your file content |
| Matches in wrong files | `file_extensions` not set | Add `file_extensions: [".cls"]` to limit scope |
| Matches in comments | Regex is text-based | Consider using PMD/XPath instead for code-aware matching |
| Too many matches | Regex too broad | Tighten pattern first (e.g., require leading `0` for IDs), then add `regex_ignore` for remaining edge cases |
| `regex_ignore` doesn't exclude test classes | `regex_ignore` is per-LINE, not per-FILE | It only skips lines where the ignore pattern matches. To exclude entire test files, use `ignores.files: ["**/*Test.cls"]` in `code-analyzer.yml` |
| Hardcoded ID regex flags normal words | Pattern `{15,18}` matches 16/17 char words | Salesforce IDs are exactly 15 OR 18 chars, start with `0`. Use: `0[a-zA-Z0-9]{14}(?:[a-zA-Z0-9]{3})?` |
| Special chars not working | YAML escaping issue | Use `create-regex-rule.js` script to avoid escaping issues. If manual: double-escape (`\\d` → `\d`) |

### Common Regex Escaping in YAML

| Character | In YAML | In regex |
|-----------|---------|----------|
| Backslash | `\\\\` | `\\` |
| Dot | `\\.` | `.` as literal |
| Quote | `\\"` or use single quotes | `"` |
| Newline | `\\n` | Line break |

## PMD/XPath Rule Issues

| Problem | Cause | Fix |
|---------|-------|-----|
| "Could not locate Java" | Java not installed or not on PATH | Install Java 11+ or set `engines.pmd.java_command` in config |
| "Language not supported" | Invalid language identifier | Use: apex, visualforce, html, xml, javascript |
| "File not found" for ruleset | Wrong path in `custom_rulesets` | Path is relative to `code-analyzer.yml` location |
| Rule not listed after creation | XML format wrong | Verify against template in `assets/pmd-ruleset-template.xml` |
| XPath returns 0 matches | Node name or attribute wrong | Re-run `sf code-analyzer ast-dump` and compare |
| XPath too broad | Missing attribute filter | Add `[@attribute='value']` conditions |
| XPath `@WithSharing='false'` returns 0 matches | PMD 7 boolean attributes are always present, not string-typed | Use XPath boolean function: `@WithSharing = false()`. NOT string `'false'`, NOT `not(@WithSharing)`. Same for `@Abstract`, `@Final`, etc. |
| Loop rule flags `for (x : [SELECT...])` | Used `//ForEachStatement//SoqlExpression` (matches iterable) | Scope to body: `//ForEachStatement/BlockStatement//SoqlExpression` |
| PMD parse error on sample code | Invalid Apex syntax in sample | Ensure sample compiles (doesn't need to deploy) |

### Debugging XPath Step by Step

1. **Dump the AST:** `sf code-analyzer ast-dump --file sample.cls`
2. **Find the target node:** Search the XML for the pattern (e.g., grep for "System.debug")
3. **Note the exact node name:** e.g., `MethodCallExpression` (not `MethodCall`)
4. **Note the exact attribute:** e.g., `FullMethodName='System.debug'` (not `Name` or `Image`)
5. **Check ancestry:** What's the parent chain? Does your XPath's `ancestor::` match?
6. **Simplify first:** Start with `//MethodCallExpression` → verify it matches → then add filters

### Verifying Rule Registration

```bash
# Check if rule appears in the rule list
sf code-analyzer rules --rule-selector regex:MyRuleName
sf code-analyzer rules --rule-selector pmd:MyRuleName

# Check all custom rules
sf code-analyzer rules --rule-selector Custom
```

### Verifying Rule Execution

```bash
# Test against a file that SHOULD violate
sf code-analyzer run --rule-selector regex:MyRuleName --target ./sample-violation.cls

# Test against a file that should NOT violate (expect 0 results)
sf code-analyzer run --rule-selector regex:MyRuleName --target ./clean-file.cls
```

## Metadata XML Rule Issues

| Problem | Cause | Fix |
|---------|-------|-----|
| XPath matches nothing on metadata | Missing `local-name()` | MUST use `*[local-name()='element']` — namespace blocks bare names |
| XPath matches nothing (text values) | Used `text()` — broken in PMD 7 | Use `@Text` attribute: `//*[@Text='value']` |
| Rule fires on wrong file type | XPath not scoped to root element | Add root check or `ancestor::*[local-name()='PermissionSet']` |
| `text()` comparison always returns 0 | PMD 7 XML language change | Replace ALL `text()='value'` with `@Text='value'`. This is a PMD 7 breaking change. |
| `@Text` matches but can't navigate up | `@Text` matches TEXT NODES, not elements | Navigate up: `//*[@Text='value']/..` (element), `/../..` (grandparent) |
| `[@Text]` predicate on element returns 0 matches | `@Text` lives on CHILD text nodes, not on elements | Use `/*[@Text...]` to navigate to child text node. E.g., `//*[local-name()='apiVersion']/*[number(@Text) < 60]` — NOT `//*[local-name()='apiVersion'][number(@Text) < 60]` |
| Child predicate `[*[local-name()='x'][@Text='y']]` returns 0 | PMD 7 doesn't support `@Text` in child predicates | Use bottom-up navigation: start from `@Text` match, go up with `../..` |
| Number comparison doesn't work | Need to use `@Text` not `text()` | `number(substring-before(@Text, '.'))` |
| Rule doesn't fire on metadata files | PMD only scans `.xml` extension by default | Add `file_extensions: { xml: [".xml"] }` under `engines.pmd`. This covers all compound extensions (`.permissionset-meta.xml`, etc.). Do NOT add compound extensions — the validator rejects them. |
| "Too many violations" on metadata | Rule too broad, scanning all XML | Scope to specific file types via root element check |
| ast-dump for XML fails with "XmlEncoding" error | Known bug in some versions | Read the raw XML file — the file content IS the DOM structure |
| ast-dump for XML shows flat DOM | Expected — XML AST is the literal DOM tree | Elements, text nodes, and attributes — not like Apex AST |

### Debugging Metadata XML XPath (PMD 7)

1. **Dump the AST** (or read raw file if ast-dump fails): `sf code-analyzer ast-dump --file MyField.field-meta.xml --language xml`
2. **Check namespace:** If file has `xmlns="..."`, ALL XPath must use `local-name()`
3. **Use `@Text` for text values:** Never use `text()` — it does not work in PMD 7 XML
4. **Start from the text node, navigate up:** `//*[@Text='TargetValue']/../..` to reach parent elements
5. **Test with `//*` first:** Confirm PMD is scanning the file at all (should return many violations)
6. **Test `@Text` matching:** `//*[@Text='YourValue']` — confirm the text node is found
7. **Add navigation one step at a time:** `../..`, then `[local-name()='parent']`, then sibling checks
8. **Check file extensions:** Ensure `file_extensions: { xml: [".xml"] }` is in your `engines.pmd` config. Just `.xml` is enough — it covers all Salesforce compound extensions.

## ESLint Rule Issues

| Problem | Cause | Fix |
|---------|-------|-----|
| Custom rules not appearing | Plugin missing `meta.docs.description` + `meta.docs.url` | Ensure plugin exports rule metadata |
| "Cannot find module" for plugin | Plugin not installed | Run `npm install --save-dev eslint-plugin-<name>` |
| Base rules conflict with custom | Both Code Analyzer base + custom config active | Set `disable_<type>_base_config: true` to suppress built-in rules |
| ESLint config not found | Wrong path or auto-discover off | Set `eslint_config_file` explicitly or enable `auto_discover_eslint_config` |
| Deprecated rules excluded | ESLint engine filters deprecated rules | Use replacement rule name (check ESLint docs) |
| `eslint_config_file` path in `code-analyzer.yml` fails at startup | Code Analyzer validates the path at load time | **Create `eslint.config.js` BEFORE adding it to `code-analyzer.yml`.** File must exist first. |
| Core rule (e.g., `no-restricted-globals`) not appearing in `sf code-analyzer rules` | Rule not enabled in `eslint.config.js` | Core ESLint rules only appear after you enable them in config AND Code Analyzer loads it. Always validate after configuration. |
| Created same rule in both Regex AND PMD — double-flagging | Rule defined in two engines | A rule should live in ONE engine only. Use PMD when structural exclusions (e.g., test classes) are needed; Regex for simple text patterns with no exclusions. |

## PMD Apex Rule Issues

> XPath authoring gotchas (loop-type coverage, PMD 7 boolean attributes like `@WithSharing`, etc.) live in the SKILL.md **Gotchas** table — that is the single source. This section covers PMD issues outside XPath authoring.

| Problem | Cause | Fix |
|---------|-------|-----|
| Rule works but wrong severity shows | Severity set in wrong place | Regex: edit `severity` under `engines.regex.custom_rules.<RuleName>` in `code-analyzer.yml`. PMD: set `<priority>` in the ruleset XML. |
| Too many false positives | Pattern too broad | Regex: tighten pattern, then add `regex_ignore` for edge cases. PMD: tighten XPath with `[not(...)]` predicates. |
| Want to customize threshold on a built-in rule | Can't modify built-in ruleset files | Use `<rule ref="category/...">` with nested `<properties>` override — see `references/advanced-pmd-patterns.md`. |

## Config File Issues

| Problem | Cause | Fix |
|---------|-------|-----|
| Config not picked up | File named wrong or in wrong directory | Must be `code-analyzer.yml` or `code-analyzer.yaml` at project root |
| YAML parse error | Invalid YAML syntax | Check indentation (2 spaces), colon spacing, quote balance |
| "engines.regex.custom_rules" not recognized | Wrong nesting level | Ensure correct hierarchy: `engines` → `regex` → `custom_rules` → `RuleName` |
| Multiple config files conflict | Both `.yml` and `.yaml` exist | Delete one — `.yaml` takes precedence over `.yml` |
| Custom ruleset path not found | Path not relative to config_root | `custom_rulesets` paths resolve relative to `code-analyzer.yml` directory |
| Rule severity override not working | Wrong config location | Use `rules.pmd.RuleName.severity` in config, not inside ruleset XML |
| Can't disable a specific rule | Wrong field name | Use `rules.pmd.RuleName.disabled: true` in `code-analyzer.yml` |

## Exclusion Issues

| Problem | Cause | Fix |
|---------|-------|-----|
| Rule still fires on excluded files | Glob pattern wrong | Use `**` for recursive: `"**/fflib_*"` not `"fflib_*"` |
| PMD exclude-pattern ignored | Pattern syntax differs from glob | PMD uses Java regex in `<exclude-pattern>`, not glob |
| Want to exclude one rule from a category | Missing `<exclude>` in ref | Use `<rule ref="category/..."><exclude name="RuleName"/></rule>` |
