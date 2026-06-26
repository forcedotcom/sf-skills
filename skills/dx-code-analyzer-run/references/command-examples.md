# Command Construction Examples

Full command examples for common scanning scenarios.

**Note:** All commands use `${TIMESTAMP}` which should be generated via `TIMESTAMP=$(date +%Y%m%d-%H%M%S)` before running the scan.

| User Request | Constructed Command |
|---|---|
| "Scan my code" | `sf code-analyzer run --rule-selector Recommended --output-file "./code-analyzer-results-${TIMESTAMP}.json" --include-fixes` |
| "Check for security issues" | `sf code-analyzer run --rule-selector Security --output-file "./code-analyzer-results-${TIMESTAMP}.json" --include-fixes` |
| "Run PMD on my Apex" | `sf code-analyzer run --rule-selector pmd --target "**/*.cls,**/*.trigger" --output-file "./code-analyzer-results-${TIMESTAMP}.json" --include-fixes` |
| "Check only my changed files" | `git diff --name-only main...HEAD \| grep -E '...' → sf code-analyzer run --target <files> --output-file "./code-analyzer-results-${TIMESTAMP}.json" --include-fixes` |
| "Find duplicate code" | `sf code-analyzer run --rule-selector cpd --output-file "./code-analyzer-results-${TIMESTAMP}.json"` |
| "Check vulnerable libraries" | `sf code-analyzer run --rule-selector retire-js --output-file "./code-analyzer-results-${TIMESTAMP}.json"` |
| "Run deep security analysis" | `sf code-analyzer run --rule-selector sfge --workspace "force-app" --target "force-app" --output-file "./code-analyzer-results-${TIMESTAMP}.json" --include-fixes` |
| "Critical PMD violations in this file" | `sf code-analyzer run --rule-selector "pmd:1" --target <file> --output-file "./code-analyzer-results-${TIMESTAMP}.json" --include-fixes` |
| "ESLint performance on LWC" | `sf code-analyzer run --rule-selector "eslint:Performance" --target "**/lwc/**" --output-file "./code-analyzer-results-${TIMESTAMP}.json" --include-fixes` |
| "AppExchange security review" | `sf code-analyzer run --rule-selector all --output-file "./code-analyzer-results-${TIMESTAMP}.json" --include-fixes` |
| "Generate HTML report" | `sf code-analyzer run --rule-selector Recommended --output-file "./code-analyzer-results-${TIMESTAMP}.html" --include-fixes` |
| "Scan with severity threshold 2" | `sf code-analyzer run --rule-selector Recommended --severity-threshold 2 --output-file "./code-analyzer-results-${TIMESTAMP}.json" --include-fixes` |
| "Run ApexCRUDViolation rule" | `sf code-analyzer run --rule-selector "pmd:ApexCRUDViolation" --output-file "./code-analyzer-results-${TIMESTAMP}.json" --include-fixes` |
| "Scan my Flows" | `sf code-analyzer run --rule-selector flow --output-file "./code-analyzer-results-${TIMESTAMP}.json"` |
| "Check ESLint recommended rules" | `sf code-analyzer run --rule-selector "eslint:Recommended" --output-file "./code-analyzer-results-${TIMESTAMP}.json" --include-fixes` |
| "Scan all with fail on high" | `sf code-analyzer run --rule-selector all --severity-threshold 2 --output-file "./code-analyzer-results-${TIMESTAMP}.json" --include-fixes` |
| "What rules are available for security?" | `sf code-analyzer rules --rule-selector Security --view detail` |
| "Scan this file for performance" | `sf code-analyzer run --rule-selector Performance --target <file> --output-file "./code-analyzer-results-${TIMESTAMP}.json" --include-fixes` |
| "Run all rules, no suppressions" | `sf code-analyzer run --rule-selector all --no-suppressions --output-file "./code-analyzer-results-${TIMESTAMP}.json" --include-fixes` |
