# Special Behaviors

Advanced scanning scenarios and engine-specific considerations.

## SFGE (Salesforce Graph Engine) Scans

When `--rule-selector sfge` is requested:
- **WARN the user**: "SFGE performs deep data-flow analysis and can be resource-intensive. It may take several minutes and use significant memory. Proceed?"
- If project is large (>100 Apex classes), suggest increasing heap: "Consider setting `engines.sfge.java_max_heap_size: '4g'` in your code-analyzer.yml"
- SFGE only analyzes Apex (`.cls`, `.trigger` files)

### SFGE Workspace Compilation Behavior

**CRITICAL:** SFGE compiles ALL `.cls` and `.trigger` files found anywhere in the `--workspace` directory (default: `.` = project root), NOT just files under `--target`. The `--target` flag only controls which files are used as **entry points** for data-flow analysis, but SFGE builds a complete inter-procedural call graph from the entire workspace.

This means:
1. If there are invalid/template Apex files ANYWHERE in the project (e.g., `datasets/`, `scripts/`, `templates/`), SFGE will try to compile them and CRASH with compilation errors.
2. **The `--target` flag does NOT prevent this** — even `--target "force-app"` still causes SFGE to compile files outside `force-app/`.

**To avoid compilation failures, ALWAYS set `--workspace` explicitly for SFGE scans:**
```bash
sf code-analyzer run --rule-selector sfge --workspace "force-app" --target "force-app" --output-file "./code-analyzer-results-${TIMESTAMP}.json" --include-fixes
```

Or if the user specifies a subfolder target like `force-app/main`:
```bash
sf code-analyzer run --rule-selector sfge --workspace "force-app" --target "force-app/main" --output-file "./code-analyzer-results-${TIMESTAMP}.json" --include-fixes
```

The `--workspace` flag restricts which files SFGE compiles into its graph. Set it to the narrowest directory that contains all valid, deployable Apex source code (typically `force-app` or `src`).

## ApexGuru Scans

When `--rule-selector apexguru` is requested:
- **Check org authentication**: Run `sf org display` first
- If no org authenticated: Guide user to `sf org login web` or `sf org login jwt`
- Add `--target-org <alias>` flag if user has specified an org
- ApexGuru analyzes Apex performance patterns via cloud service

## AppExchange Security Review Scans

When user mentions "AppExchange", "security review", "ISV", "partner":
- Use `--rule-selector all` to run comprehensive scan
- Output both JSON and HTML: `--output-file "./code-analyzer-results-${TIMESTAMP}.json" --output-file "./code-analyzer-results-${TIMESTAMP}.html"`
- In results, categorize violations as:
  - **Blockers** (sev 1-2, Security tag): MUST fix before submission
  - **Warnings** (sev 3, Security/BestPractices): Strongly recommended to fix
  - **Informational** (sev 4-5): Good to fix but won't block review
- Highlight specific AppExchange-critical rules:
  - `ApexCRUDViolation` (CRUD/FLS enforcement)
  - `ApexSharingViolations` (sharing model)
  - `ApexSOQLInjection` (injection prevention)
  - `ApexCSRF` (CSRF protection)
  - `ApexXSSFromEscapeFalse` / `ApexXSSFromURLParam` (XSS prevention)
  - `ApexInsecureEndpoint` (HTTPS enforcement)
  - `ApexBadCrypto` (crypto standards)
  - `ApexSuggestUsingNamedCred` (credential management)

## Diff-Based Scans

When user wants to scan only changed files:
1. Determine the base reference:
   - "my changes" / "what I changed" → `git diff --name-only` (unstaged) or `git diff --name-only --cached` (staged)
   - "branch changes" / "since main" → `git diff --name-only main...HEAD`
   - "last commit" → `git diff --name-only HEAD~1`
2. Filter to scannable file types:
   ```bash
   git diff --name-only main...HEAD | grep -E '\.(cls|trigger|js|ts|html|css|xml|flow-meta\.xml)$'
   ```
3. If no scannable files changed: "No scannable files in your diff. Code Analyzer supports: .cls, .trigger, .js, .ts, .html, .css, .xml, .flow-meta.xml"
4. Pass filtered files as comma-separated `--target` value

## Large Result Sets (500+ violations)

- Summarize: top 10 rules by frequency, top 10 files by violation count
- Offer: "Want me to export the full results? Or focus on a specific category/file?"
- Don't try to display all 500+ violations inline

## Mega Result Sets (5000+ violations)

- Same as above, but also proactively suggest narrowing scope:
  - "This is a very large number of violations. Want me to focus on just Critical/High severity, a specific category like Security, or a specific folder?"
- If the user originally said "scan and fix everything", still follow the full flow (scan → present → discover fixes → ask → apply → summarize) — do NOT shortcut any steps just because the result set is large
