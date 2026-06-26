# CI/CD Pipeline Templates

Ready-to-use templates for integrating Code Analyzer into CI/CD pipelines.

## GitHub Actions (using `forcedotcom/run-code-analyzer@v2`)

The official GitHub Action for Code Analyzer. It orchestrates the run, uploads artifacts, and optionally creates PR reviews with violation counts.

**Action inputs:**
| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `run-arguments` | No | `--view detail --output-file sfca_results.json` | Flags passed to `sf code-analyzer run` |
| `results-artifact-name` | No | `salesforce-code-analyzer-results` | Name of the uploaded ZIP artifact |
| `github-token` | No | *(none)* | Enables PR reviews + `*-in-changed-files` outputs |

**Action outputs:** `exit-code`, `num-violations`, `num-sev1-violations` through `num-sev5-violations`, `num-violations-in-changed-files`, `num-sev1-violations-in-changed-files` through `num-sev5-violations-in-changed-files`, `review-id`.

**Key `run-arguments` flags:**
| Flag | Purpose | Example |
|------|---------|---------|
| `--workspace` | Root directory to scan (scans all eligible files recursively) | `--workspace .` |
| `--target` | Specific files/directories to scan (comma-separated or repeated) | `--target force-app/main/default/classes --target force-app/main/default/triggers` |
| `--rule-selector` | Which rules to run | `Recommended`, `all`, `all:Security`, `pmd`, `"Severity:1,2"` |
| `--config-file` | Path to `code-analyzer.yml` — **omit if no config file exists** | `--config-file code-analyzer.yml` |
| `--output-file` | Output file (repeat for multiple formats; format inferred from extension) | `--output-file results.html --output-file results.sarif` |
| `--view` | Output verbosity | `detail` or `summary` |

**`--workspace` vs `--target`:**
- Use `--workspace .` for full-repo scans (most common in CI)
- Use `--target <path>` to scan specific directories (monorepos, scoped scans, faster feedback)
- If both are omitted, defaults to current working directory
- You can combine: `--workspace . --target force-app/` scans only `force-app/` within the workspace

### Basic Quality Gate (Pull Requests)

```yaml
# .github/workflows/code-analyzer.yml
name: Salesforce Code Analyzer

on:
  pull_request:
    branches: [main, develop]

jobs:
  code-analysis:
    permissions:
      pull-requests: write
      contents: read
      actions: read
    runs-on: ubuntu-latest
    steps:
      - name: Check out files
        uses: actions/checkout@v4

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '>=20.9.0'

      - name: Setup Java
        uses: actions/setup-java@v4
        with:
          distribution: 'temurin'
          java-version: '>=11'

      - name: Install Salesforce CLI
        run: npm install -g @salesforce/cli@latest

      - name: Install Code Analyzer Plugin
        run: sf plugins install code-analyzer@latest

      - name: Run Salesforce Code Analyzer
        id: run-code-analyzer
        uses: forcedotcom/run-code-analyzer@v2
        with:
          run-arguments: --workspace . --rule-selector Recommended --output-file sfca_results.html --output-file sfca_results.json
          results-artifact-name: code-analyzer-results
          github-token: ${{ github.token }}

      - name: Check Quality Gate (Changed Files Only)
        if: |
          steps.run-code-analyzer.outputs.num-sev1-violations-in-changed-files > 0 ||
          steps.run-code-analyzer.outputs.num-sev2-violations-in-changed-files > 0
        run: |
          echo "Critical/High violations found in changed files!"
          echo "Sev1: ${{ steps.run-code-analyzer.outputs.num-sev1-violations-in-changed-files }}"
          echo "Sev2: ${{ steps.run-code-analyzer.outputs.num-sev2-violations-in-changed-files }}"
          exit 1
```

### Strict Quality Gate (All Files + SARIF)

```yaml
# .github/workflows/code-analyzer-strict.yml
name: Salesforce Code Analyzer (Strict)

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  code-analysis:
    permissions:
      pull-requests: write
      contents: read
      actions: read
      security-events: write
    runs-on: ubuntu-latest
    steps:
      - name: Check out files
        uses: actions/checkout@v4

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '>=20.9.0'

      - name: Setup Java
        uses: actions/setup-java@v4
        with:
          distribution: 'temurin'
          java-version: '>=11'

      - name: Install Salesforce CLI
        run: npm install -g @salesforce/cli@latest

      - name: Install Code Analyzer Plugin
        run: sf plugins install code-analyzer@latest

      - name: Run Salesforce Code Analyzer
        id: run-code-analyzer
        uses: forcedotcom/run-code-analyzer@v2
        with:
          run-arguments: --workspace . --rule-selector Recommended --output-file sfca_results.html --output-file sfca_results.json --output-file sfca_results.sarif --config-file code-analyzer.yml
          results-artifact-name: code-analyzer-results
          github-token: ${{ github.token }}

      - name: Upload SARIF to GitHub Security
        if: always()
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: sfca_results.sarif

      - name: Check Quality Gate (All Files)
        if: |
          steps.run-code-analyzer.outputs.exit-code > 0 ||
          steps.run-code-analyzer.outputs.num-sev1-violations > 0 ||
          steps.run-code-analyzer.outputs.num-sev2-violations > 0
        run: |
          echo "Quality gate failed!"
          echo "Total violations: ${{ steps.run-code-analyzer.outputs.num-violations }}"
          echo "Sev1: ${{ steps.run-code-analyzer.outputs.num-sev1-violations }}"
          echo "Sev2: ${{ steps.run-code-analyzer.outputs.num-sev2-violations }}"
          exit 1
```

### Security-Focused (AppExchange Prep)

```yaml
# .github/workflows/code-analyzer-security.yml
name: Security Analysis

on:
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 6 * * 1'  # Weekly Monday 6am

jobs:
  security-scan:
    permissions:
      pull-requests: write
      contents: read
      actions: read
      security-events: write
    runs-on: ubuntu-latest
    steps:
      - name: Check out files
        uses: actions/checkout@v4

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '>=20.9.0'

      - name: Setup Java
        uses: actions/setup-java@v4
        with:
          distribution: 'temurin'
          java-version: '>=11'

      - name: Install Salesforce CLI
        run: npm install -g @salesforce/cli@latest

      - name: Install Code Analyzer Plugin
        run: sf plugins install code-analyzer@latest

      - name: Run Security Scan
        id: run-code-analyzer
        uses: forcedotcom/run-code-analyzer@v2
        with:
          run-arguments: --workspace . --rule-selector "all:Security" --output-file security-results.html --output-file security-results.json --output-file security-results.sarif --config-file code-analyzer.yml
          results-artifact-name: security-scan-results
          github-token: ${{ github.token }}

      - name: Upload SARIF to GitHub Security
        if: always()
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: security-results.sarif

      - name: Fail on Any Security Violations
        if: steps.run-code-analyzer.outputs.num-sev1-violations > 0
        run: |
          echo "Critical security violations found!"
          echo "Sev1: ${{ steps.run-code-analyzer.outputs.num-sev1-violations }}"
          exit 1
```

### With Path Filters (Faster Feedback)

Use `paths:` to only trigger the workflow when relevant source files change. This avoids running scans on README edits, CI config changes, etc.

```yaml
# .github/workflows/code-analyzer-filtered.yml
name: Salesforce Code Analyzer

on:
  pull_request:
    branches: [main, develop]
    paths:
      - 'force-app/**'
      - '**/*.cls'
      - '**/*.trigger'
      - '**/*.js'
      - '**/*.ts'
      - '**/*.html'
      - '**/*.flow-meta.xml'
      - 'code-analyzer.yml'

jobs:
  code-analysis:
    permissions:
      pull-requests: write
      contents: read
      actions: read
    runs-on: ubuntu-latest
    steps:
      - name: Check out files
        uses: actions/checkout@v4

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '>=20.9.0'

      - name: Setup Java
        uses: actions/setup-java@v4
        with:
          distribution: 'temurin'
          java-version: '>=11'

      - name: Install Salesforce CLI
        run: npm install -g @salesforce/cli@latest

      - name: Install Code Analyzer Plugin
        run: sf plugins install code-analyzer@latest

      - name: Run Salesforce Code Analyzer
        id: run-code-analyzer
        uses: forcedotcom/run-code-analyzer@v2
        with:
          run-arguments: --workspace . --rule-selector Recommended --output-file sfca_results.html --output-file sfca_results.json
          results-artifact-name: code-analyzer-results
          github-token: ${{ github.token }}

      - name: Check Quality Gate
        if: |
          steps.run-code-analyzer.outputs.num-sev1-violations-in-changed-files > 0 ||
          steps.run-code-analyzer.outputs.num-sev2-violations-in-changed-files > 0
        run: exit 1
```

**When to use path filters:**
- Use when the repo contains non-Salesforce code (docs, scripts, infra) that shouldn't trigger scans
- Always include `code-analyzer.yml` in paths so config changes trigger a validation run
- Don't use if you want every PR to get a scan regardless of what changed

### With Flow Engine (Python Required)

If the project contains `.flow-meta.xml` files and uses the Flow engine, Python 3.10+ must be installed:

```yaml
      - name: Setup Python (required for Flow engine)
        uses: actions/setup-python@v5
        with:
          python-version: '>=3.10'
```

Insert this step after the Java setup step. If you're unsure whether the project uses Flows, include it — it adds ~5s and avoids a partial scan failure.

### Monorepo / Scoped Scan

For monorepos where Salesforce code lives in a subdirectory, use `--target` to scope the scan:

```yaml
      - name: Run Salesforce Code Analyzer
        id: run-code-analyzer
        uses: forcedotcom/run-code-analyzer@v2
        with:
          run-arguments: --workspace . --target packages/salesforce-app/force-app --rule-selector Recommended --output-file sfca_results.html --output-file sfca_results.json
          results-artifact-name: code-analyzer-results
          github-token: ${{ github.token }}
```

For multiple packages:
```
--target packages/app-a/force-app --target packages/app-b/force-app
```

### Without a Config File

If the project has no `code-analyzer.yml`, simply omit `--config-file`. Code Analyzer uses built-in defaults:

```yaml
      - name: Run Salesforce Code Analyzer
        id: run-code-analyzer
        uses: forcedotcom/run-code-analyzer@v2
        with:
          run-arguments: --workspace . --rule-selector Recommended --output-file sfca_results.html --output-file sfca_results.json
          results-artifact-name: code-analyzer-results
          github-token: ${{ github.token }}
```

To conditionally use a config file if it exists:
```yaml
      - name: Check for config file
        id: config-check
        run: |
          if [ -f "code-analyzer.yml" ]; then
            echo "config-flag=--config-file code-analyzer.yml" >> $GITHUB_OUTPUT
          else
            echo "config-flag=" >> $GITHUB_OUTPUT
          fi

      - name: Run Salesforce Code Analyzer
        id: run-code-analyzer
        uses: forcedotcom/run-code-analyzer@v2
        with:
          run-arguments: --workspace . --rule-selector Recommended --output-file sfca_results.html --output-file sfca_results.json ${{ steps.config-check.outputs.config-flag }}
          results-artifact-name: code-analyzer-results
          github-token: ${{ github.token }}
```

## Jenkins

### Jenkinsfile (Declarative Pipeline)

```groovy
// Jenkinsfile
pipeline {
    agent {
        docker {
            image 'node:20'
            args '-v /usr/local/share/java:/usr/local/share/java'
        }
    }

    environment {
        JAVA_HOME = '/usr/lib/jvm/java-11-openjdk-amd64'
    }

    stages {
        stage('Setup') {
            steps {
                sh 'npm install -g @salesforce/cli@latest'
                sh 'sf plugins install code-analyzer@latest'
            }
        }

        stage('Code Analysis') {
            steps {
                sh '''
                    sf code-analyzer run \
                        --workspace . \
                        --rule-selector Recommended \
                        --output-file results.json \
                        --output-file results.html \
                        --config-file code-analyzer.yml 2>&1 | tee sfca_output.txt
                '''
                script {
                    def output = readFile('results.json')
                    def json = new groovy.json.JsonSlurper().parseText(output)
                    def sev1Count = json.violations?.count { it.severity == 1 } ?: 0
                    def sev2Count = json.violations?.count { it.severity == 2 } ?: 0
                    if (sev1Count > 0 || sev2Count > 0) {
                        error("Quality gate failed! Sev1: ${sev1Count}, Sev2: ${sev2Count}")
                    }
                }
            }
            post {
                always {
                    archiveArtifacts artifacts: 'results.*', allowEmptyArchive: true
                    publishHTML(target: [
                        reportName: 'Code Analyzer Report',
                        reportDir: '.',
                        reportFiles: 'results.html'
                    ])
                }
            }
        }
    }

    post {
        failure {
            echo 'Code analysis found violations above severity threshold!'
        }
    }
}
```

## GitLab CI

```yaml
# .gitlab-ci.yml
code-analysis:
  image: node:20
  stage: test
  before_script:
    - apt-get update && apt-get install -y openjdk-11-jdk python3
    - export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
    - npm install -g @salesforce/cli@latest
    - sf plugins install code-analyzer@latest
  script:
    - |
      sf code-analyzer run \
        --workspace . \
        --rule-selector Recommended \
        --output-file results.json \
        --output-file results.html \
        --config-file code-analyzer.yml
    - |
      # Quality gate: fail on sev1 or sev2 violations
      SEV1=$(cat results.json | python3 -c "import sys,json; d=json.load(sys.stdin); print(sum(1 for v in d.get('violations',[]) if v.get('severity')==1))")
      SEV2=$(cat results.json | python3 -c "import sys,json; d=json.load(sys.stdin); print(sum(1 for v in d.get('violations',[]) if v.get('severity')==2))")
      echo "Sev1: $SEV1, Sev2: $SEV2"
      if [ "$SEV1" -gt 0 ] || [ "$SEV2" -gt 0 ]; then
        echo "Quality gate failed!"
        exit 1
      fi
  artifacts:
    paths:
      - results.json
      - results.html
    reports:
      codequality: results.json
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
    - if: '$CI_COMMIT_BRANCH == "main"'
```

## Bitbucket Pipelines

```yaml
# bitbucket-pipelines.yml
pipelines:
  pull-requests:
    '**':
      - step:
          name: Code Analysis
          image: node:20
          script:
            - apt-get update && apt-get install -y openjdk-11-jdk
            - export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
            - npm install -g @salesforce/cli@latest
            - sf plugins install code-analyzer@latest
            - |
              sf code-analyzer run \
                --workspace . \
                --rule-selector Recommended \
                --output-file results.json \
                --output-file results.html \
                --config-file code-analyzer.yml
            - |
              # Quality gate: fail on sev1 or sev2 violations
              SEV1=$(cat results.json | python3 -c "import sys,json; d=json.load(sys.stdin); print(sum(1 for v in d.get('violations',[]) if v.get('severity')==1))")
              SEV2=$(cat results.json | python3 -c "import sys,json; d=json.load(sys.stdin); print(sum(1 for v in d.get('violations',[]) if v.get('severity')==2))")
              echo "Sev1: $SEV1, Sev2: $SEV2"
              if [ "$SEV1" -gt 0 ] || [ "$SEV2" -gt 0 ]; then
                echo "Quality gate failed!"
                exit 1
              fi
          artifacts:
            - results.json
            - results.html
```

## Configuration Tips for CI/CD

### Quality Gating Strategy

With `forcedotcom/run-code-analyzer@v2`, you control the quality gate via output checks:

| Strategy | Condition | Use Case |
|----------|-----------|----------|
| Block on critical only | `num-sev1-violations > 0` | Permissive — only block security vulnerabilities |
| Block on critical + high | `num-sev1-violations > 0 \|\| num-sev2-violations > 0` | Recommended for most teams |
| Block on changed files only | `num-sev1-violations-in-changed-files > 0` | Great for legacy codebases — don't block on pre-existing issues |
| Block on total count | `num-violations > 10` | Budget approach — allow some violations but cap total |
| Zero tolerance | `num-violations > 0` | For new greenfield projects only |

For non-GitHub platforms (Jenkins, GitLab, Bitbucket), parse `results.json` to count violations by severity and fail the pipeline accordingly.

### Output Formats

Specify multiple `--output-file` flags (format inferred from extension):

| Format | Extension | Best For |
|--------|-----------|----------|
| SARIF | `.sarif` | GitHub Code Scanning integration (requires `security-events: write` permission) |
| JSON | `.json` | Programmatic processing, quality gating scripts, custom dashboards |
| HTML | `.html` | Human-readable reports in artifacts |
| CSV | `.csv` | Spreadsheet analysis |
| XML | `.xml` | Legacy tool integration |

### Caching for Faster CI

```yaml
# GitHub Actions: Cache sf CLI plugins
- uses: actions/cache@v4
  with:
    path: ~/.local/share/sf/
    key: sf-plugins-${{ hashFiles('**/code-analyzer.yml') }}
    restore-keys: sf-plugins-
```

### Recommended PR Workflow

1. **On PR open/update:** Use `forcedotcom/run-code-analyzer@v2` with `github-token` — gate on changed-files outputs only
2. **On merge to main:** Full scan with SARIF upload to GitHub Security tab
3. **Weekly schedule:** Full security scan with `--rule-selector "all:Security"`

### When to Use Path Filters

| Situation | Use Path Filters? | Reasoning |
|-----------|-------------------|-----------|
| Mixed repo (docs, infra, salesforce code) | Yes | Avoid wasting CI minutes on non-code PRs |
| Pure Salesforce project | Optional | Every PR likely touches scannable files anyway |
| You want config changes to trigger a scan | Yes, include `code-analyzer.yml` | Validates config changes don't break the scan |
| Monorepo with multiple apps | Yes, scope to your package path | Avoid scanning unrelated packages |

---

## Composition & Adaptation Guide

When a user's request doesn't match an existing template exactly, compose from these building blocks:

### Prerequisites Block (always required)
```yaml
# ALWAYS include these — the action does NOT install them
- uses: actions/setup-node@v4    # Node >= 20.9.0
- uses: actions/setup-java@v4    # Java >= 11 (for PMD/CPD/SFGE)
- uses: actions/setup-python@v5  # Python >= 3.10 (ONLY if project has .flow-meta.xml files)
- run: npm install -g @salesforce/cli@latest
- run: sf plugins install code-analyzer@latest
```

### Composing `run-arguments`

Build the `run-arguments` string by combining these independent flags as needed:

| Need | Flag to Add |
|------|-------------|
| Scan the whole repo | `--workspace .` |
| Scan specific directory | `--target force-app/main/default/classes` |
| Scan multiple directories | `--target dir1 --target dir2` |
| Use recommended rules | `--rule-selector Recommended` |
| Use all rules | `--rule-selector all` |
| Security rules only | `--rule-selector "all:Security"` |
| Specific engine only | `--rule-selector pmd` or `--rule-selector eslint` |
| Specific severity filter | `--rule-selector "Severity:1,2"` |
| Combined selector | `--rule-selector "pmd:Security:(1,2)"` |
| Apply custom config | `--config-file code-analyzer.yml` |
| No custom config | *(omit --config-file entirely)* |
| HTML output | `--output-file results.html` |
| JSON output | `--output-file results.json` |
| SARIF for GitHub Security | `--output-file results.sarif` |
| Multiple formats | `--output-file a.html --output-file b.json --output-file c.sarif` |
| Verbose output | `--view detail` |

### Permissions Required

| Feature | Permission Needed |
|---------|------------------|
| PR review comments | `pull-requests: write` |
| Upload SARIF to Security tab | `security-events: write` |
| Private repo checkout | `contents: read` |
| Download artifacts | `actions: read` |

### Decision Tree for Template Selection

```
User wants CI/CD for Code Analyzer
├── Platform?
│   ├── GitHub Actions → Use forcedotcom/run-code-analyzer@v2
│   ├── Jenkins → Use Jenkinsfile template + JSON parsing for quality gate
│   ├── GitLab → Use .gitlab-ci.yml template + script-based quality gate
│   └── Bitbucket → Use bitbucket-pipelines.yml template + script-based quality gate
├── Scope?
│   ├── Full repo → --workspace .
│   ├── Specific folder → --target <path>
│   └── Changed files only → use github-token + *-in-changed-files outputs (GitHub only)
├── Strictness?
│   ├── Block on sev1 only → check num-sev1-violations
│   ├── Block on sev1+sev2 → check both (RECOMMENDED DEFAULT)
│   ├── Block on any violation → check num-violations
│   └── Legacy codebase → use *-in-changed-files to avoid blocking on old debt
├── Has config file?
│   ├── Yes → add --config-file code-analyzer.yml
│   ├── No → omit --config-file
│   └── Maybe → use conditional check pattern
├── Has Flow files?
│   ├── Yes → add actions/setup-python step
│   └── No → skip Python setup
└── Wants GitHub Security integration?
    ├── Yes → add --output-file *.sarif + upload-sarif step + security-events: write
    └── No → skip SARIF
```

### Common User Requests → Modifications

| User Says | What to Change |
|-----------|---------------|
| "Only scan on PRs to main" | Set `on: pull_request: branches: [main]` |
| "Scan only Apex classes" | Use `--target force-app/main/default/classes` |
| "Don't fail on existing violations" | Use `*-in-changed-files` outputs for quality gate |
| "I want to see results in GitHub Security tab" | Add `--output-file *.sarif` + `upload-sarif` step + `security-events: write` |
| "Run a nightly full scan" | Add `schedule: - cron: '0 0 * * *'` trigger |
| "We don't have a config file" | Remove `--config-file` from run-arguments |
| "Only run security rules" | Change `--rule-selector` to `"all:Security"` |
| "Block the PR if there are more than 5 violations" | Change gate to `num-violations > 5` |
| "We have Flows in our project" | Add `actions/setup-python@v5` with `python-version: '>=3.10'` |
| "Scan only what changed in the PR" | Use `github-token` + gate on `*-in-changed-files` outputs |
| "We're a monorepo" | Use `--target packages/my-sf-app/force-app` instead of `--workspace .` |
| "Cache the plugin install" | Add `actions/cache@v4` step for `~/.local/share/sf/` |
| "I want an HTML report I can download" | Add `--output-file results.html` (auto-uploaded via results-artifact-name) |
