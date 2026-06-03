# Komaci ESLint Static Analysis (`@salesforce/eslint-plugin-lwc-graph-analyzer`)

## Framework for the analysis

The Komaci offline analyzer is exposed as the ESLint plugin `@salesforce/eslint-plugin-lwc-graph-analyzer`. Its **recommended** ruleset catches LWC patterns that prevent offline data priming. This reviewer runs the plugin against the component's JS file and translates each lint message into an actionable remediation.

Use the documented per-rule remediations below — do not invent new ones — and only emit findings for rules that actually fired against the file in scope.

The recommended preset enables ~36 rules; only the 7 rules documented in **Per-rule remediation** below are surfaced as findings. Other recommended-preset rules (e.g. `no-eval-usage`, `no-functions-declared-within-getter-method`) may fire but are intentionally not mapped to remediations and must be dropped from the report.

## How to run the analyzer

Use the bundled script. It applies the plugin's recommended ruleset with the `bundleAnalyzer` processor enabled, and on first run installs the pinned versions of `@salesforce/eslint-plugin-lwc-graph-analyzer` and `eslint` into `scripts/node_modules` so the runner is isolated from whatever versions the host project happens to ship.

```bash
scripts/run-komaci.sh path/to/component/component.js
```

Prerequisites:

- The component's sibling HTML templates must live in the same directory as the JS file. The plugin's `bundleAnalyzer` processor discovers them automatically (via `readdirSync` on the bundle directory) and uses them to resolve the offline data graph across the bundle.
- A working `npm` and Node ≥ 18 on `PATH` for the first-run install.

The script emits ESLint's `--format json` output on stdout. Each `messages[*]` entry has `ruleId`, `severity`, `message`, `line`, `column`, `endLine`, `endColumn`, and `fix` (optional). Group messages by `ruleId`, then apply the per-rule remediation guidance below.

To run ESLint manually outside the script — using the same pinned versions, so the recommended config resolves to the flat-config-shaped form — install once and invoke the local binary:

```bash
cd scripts
npm install   # only on first run
node_modules/.bin/eslint \
  --no-config-lookup \
  --config komaci.config.mjs \
  --format json \
  path/to/component/component.js
```

`scripts/komaci.config.mjs` and `scripts/package.json` ship together; the package pin (`@salesforce/eslint-plugin-lwc-graph-analyzer ^1.1.0-beta.2`, `eslint ^9.35.0`) ensures the plugin's `recommended` config is flat-config-shaped (no legacy `extends:` key).

## Per-rule remediation

For each rule below, the `Type`, `Description`, `Intent analysis`, and `Suggested action` strings are canonical and must be emitted unchanged in the finding. Do not paraphrase or augment them.

### `@salesforce/lwc-graph-analyzer/no-private-wire-config-property`

- **Type:** Private Wire Configuration Property
- **Description:** Properties used in wire configurations must be decorated with `@api` to be public and resolvable by the wire service.
- **Intent analysis:** The developer used properties in wire configurations without making them public using the `@api` decorator.
- **Suggested action:**

  Make the properties public by using the `@api` decorator:

  - Add `@api` decorator to properties used in wire configurations.

### `@salesforce/lwc-graph-analyzer/no-wire-config-references-non-local-property-reactive-value`

- **Type:** Wire Configuration References Non-Local Property
- **Description:** Wire configurations with reactive values (`$prop`) must reference only component properties, not imported values or values defined outside the component class.
- **Intent analysis:** The developer is trying to use a non-local value (imported or module-level) as a reactive parameter in a wire configuration.
- **Suggested action:** Wrap the non-local value in a getter:

  - Introduce a getter which returns the imported value or the value of a module-level constant.
  - Update the wire configuration to use the getter name as the reactive parameter.

  ```js
  // Instead of:
  @wire(getData, { param: '$importedValue' })

  // Use:
  get localValue() {
      return importedValue;
  }
  @wire(getData, { param: '$localValue' })
  ```

### Getter-related violations

The five rules below all share the **Violations in Getter** classification and emit the same `description`, `intentAnalysis`, and `suggestedAction`. When any of them fires, emit one finding per (rule, line) pair with the strings reproduced below.

Rules:

- `@salesforce/lwc-graph-analyzer/no-assignment-expression-assigns-value-to-member-variable`
- `@salesforce/lwc-graph-analyzer/no-reference-to-class-functions`
- `@salesforce/lwc-graph-analyzer/no-reference-to-module-functions`
- `@salesforce/lwc-graph-analyzer/no-getter-contains-more-than-return-statement`
- `@salesforce/lwc-graph-analyzer/no-unsupported-member-variable-in-member-expression`

Canonical fields:

- **Type:** Violations in Getter
- **Description:** A getter method does more than just returning a value
- **Intent analysis:** The developer attempted to modify component state, prepare data for consumption, or reference functions within a getter function.
- **Suggested action:**

  **Compliant getter implementations**

  Getters that:
  - Directly access and return property values
  - Return a literal value
  - Compute and return values derived from existing properties

  **Non-compliant getter implementations**

  - **Violation: getters that call functions.** Getters that call functions cannot be primed for offline use cases.
    *Remediation:* Reorganize any getter implementation code that calls a function, to move such calls out of the getter. Avoid invoking any function calls within getters.
  - **Violation: getters with side effects.** Getters that assign values to member variables or modify state create unpredictable side effects and are not suitable for offline scenarios.
    *Remediation:* Never assign values to member variables within a getter. LWC getters should only retrieve data without modifying any state. If you need to compute and cache a value, perform the computation and assignment in a lifecycle hook or method, then have the getter simply return the cached value.
  - **Violation: getters that do more than just return a value.** Getters that perform complex operations beyond returning a value cannot be primed for offline use cases.
    *Remediation:* Review the getters and make sure that they're composed to only return a value. Move any complex logic, data processing, or multiple operations into separate methods or lifecycle hooks, and have the getter simply return the result.

## Rules to follow

- If no action is required, return an empty list. Do not return null or any other value — return an empty array.
- Keep issues concise; avoid duplicated issues or unnecessary analysis for things that are not real violations.
- Stick to the instructions for the specific reviewer in scope. Issues outside that scope will be analyzed by other reviewers.
- For each violation, provide:
  - `type` — verbatim from the rule entry above.
  - `description` — verbatim from the rule entry above.
  - `intentAnalysis` — verbatim from the rule entry above.
  - `suggestedAction` — verbatim from the rule entry above.
  - `filePath` — the path passed to ESLint.
  - `location` — `{ startLine, startColumn, endLine, endColumn }` taken from the ESLint message's `line`, `column`, `endLine`, `endColumn`.
  - `code` — *optional* — the source snippet from `startLine` through `endLine`, useful when the violation spans multiple lines.
- Drop messages whose `ruleId` is not in the seven rules above.
- Do not make assumptions about other components that may be referenced.
