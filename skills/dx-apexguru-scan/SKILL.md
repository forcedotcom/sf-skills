---
name: dx-apexguru-scan
description: "Run an ApexGuru performance scan on a Salesforce Apex project via the ApexGuru SFAP Scan API. Zips the project's Apex (any layout), submits it, polls to completion, decodes the base64 report, and presents performance antipattern violations (SOQL in loop, DML in loop, Schema.getGlobalDescribe(), SOQL without WHERE/LIMIT, unused SOQL fields) grouped by rule with severity, file:line, and suggested fixes — clearly attributed as 'Static only' or 'Production insights'. TRIGGER when the user says 'run ApexGuru', 'ApexGuru scan', 'check Apex performance', 'find governor-limit / performance antipatterns', 'SOQL in loop', 'scan my Apex for performance', or 'ApexGuru performance insights'. DO NOT TRIGGER for general static analysis or security scans (use dx-code-analyzer-run), for fixing code without scanning, or for onboarding an org to ApexGuru."
allowed-tools: Read, Bash(bash), Bash(node), Bash(curl), Bash(zip), Bash(unzip), Bash(jq), Bash(sf), Bash(date), Write
argument-hint: "[project-path] [--org <alias>] [--fast]"
metadata:
  version: "1.1"
  domains: ["Developer Experience"]
  relatedSkills:
    - "dx-code-analyzer-run"
  cliTools:
    - tool: ["curl"]
      semver: ">=7.0.0"
    - tool: ["jq"]
      semver: ">=1.6.0"
    - tool: ["node"]
      semver: ">=18.0.0"
    - tool: ["sf"]
      semver: ">=2.0.0"
---

# ApexGuru Performance Scan Skill

## CRITICAL: Mandatory Script Usage

Every step — token resolution, zipping, API calls, and report decoding — MUST go
through the bundled scripts in `<skill_dir>/scripts/`. No exceptions.

### WRONG — never do this:

```bash
# WRONG: hand-rolled curl to the API
curl -X POST https://api.salesforce.com/... -F file=@x.zip

# WRONG: inline base64 + jq to read the report
cat raw.json | jq -r .report | base64 -d | jq '.[]'

# WRONG: reading the raw result file directly (report is a large base64 blob)
Read tool → apexguru-raw-*.json

# WRONG: inline node/python to parse violations
node -e "const r = require('./raw.json'); ..."
```

### RIGHT — always do this:

```bash
# PREFERRED — one command runs all three steps (package → submit+poll →
# decode+present) and prints the ready-to-show report as its final stdout.
# Use this for every initial scan: it cannot be left half-finished.
bash "<skill_dir>/scripts/scan.sh" "<project-root>"

# Optionally persist the presented markdown to a file as well:
bash "<skill_dir>/scripts/scan.sh" "<project-root>" --out ./apexguru-report.md
```

The three underlying scripts still exist and `scan.sh` calls them in order.
Invoke them individually only for **drill-downs on an already-scanned result**
(Step 5), or when you deliberately need to inspect an intermediate artifact:

```bash
# Equivalent manual chain (scan.sh runs exactly these, in this order):
bash "<skill_dir>/scripts/build-zip.sh" "<project-root>" "./apexguru-<TS>.zip"
bash "<skill_dir>/scripts/run-scan.sh"  "./apexguru-<TS>.zip" "./apexguru-raw-<TS>.json"
node "<skill_dir>/scripts/decode-report.js" "./apexguru-raw-<TS>.json" --present

# Drill into a subset WITHOUT re-scanning (reuse the raw file scan.sh left, or
# pass --raw to scan.sh to keep it at a known path):
node "<skill_dir>/scripts/decode-report.js" "./apexguru-raw-<TS>.json" --rule SOQL_IN_LOOP --full
node "<skill_dir>/scripts/decode-report.js" "./apexguru-raw-<TS>.json" --group file --top 5
```

`<skill_dir>` is the absolute path to the directory containing this SKILL.md.
**Never** use `./scripts/` — that resolves against the user's CWD, not the skill dir.

Any filter/rank/group question ("which file has the most issues?", "show only
SOQL-in-loop", "break down by severity") is answered by re-running
`decode-report.js` with flags against the **same raw result file** — never re-scan,
never parse the JSON by hand.

---

## CRITICAL: Present `--present` output verbatim — never condense it

`decode-report.js --present` (Step 4) already produces the final, ready-to-show
markdown: severity legend, one detail card per violation (message, code, fix,
resource link), and a closing summary table. That stdout **is** the response.
Print it to the user exactly as printed — do not rewrite it into a shorter
table, do not drop the per-issue cards down to just the summary table, and do
not wait for the user to ask "explain a violation" before including
message/fix/resource. Condensing it defeats the entire point of `--present`.

The attribution is **already in that stdout** — the summary line is the exact
output that states the mode (e.g. "ApexGuru (static analysis) is active. To
unlock runtime intelligence…"). Do **NOT** prepend or append your own attribution sentence
(no "Attribution: analysisMode: static…", no naming the org, no restating
"static-only findings"). The script's line is the complete, approved wording;
adding your own makes the output non-deterministic and off-message.

### WRONG — never do this:

```text
Top Issues (worst first)
#  Severity   Rule                      Method    Line
1  Major      UsingTheTestMethodKeyword legacy... 136
...
Key Antipatterns Detected:
- SOQL/DML in loops (3 violations)
```
*(a hand-built summary that drops every message/code/fix — even for
violations that had one)*

```text
Attribution: analysisMode: static — source-only analysis. The scanned org
(ag-skills-org) is not onboarded to ApexGuru's full runtime metrics, so
these are static-only findings.
```
*(an agent-authored attribution line prepended to the report — the script's
own summary line already states the mode; this duplicate is non-deterministic
and names an org the script never had access to)*

### RIGHT — always do this:

Paste the full stdout from `decode-report.js --present` — every `### Issue N`
card and the closing `## Summary` table — unedited, in one response.

---

## Overview

ApexGuru detects **performance antipatterns** in Apex (SOQL/DML in loops,
`Schema.getGlobalDescribe()`, SOQL without `WHERE`/`LIMIT`, unused SOQL fields).
This skill drives the ApexGuru **SFAP Scan API**: it packages the user's Apex
(every `.cls`/`.trigger` under the project root, any layout) into a zip, submits
it, polls until the scan finishes, decodes the base64-encoded report, and
presents violations grouped by rule with severity, `file:line`, and suggested
fixes.

**Attribution is mandatory.** The API returns `analysisMode`:
- `static` → source-only analysis → label results **"Static only"**.
- `full` → enriched with runtime metrics from an org onboarded to ApexGuru →
  label results **"Production insights"**.

`decode-report.js --present` already renders this attribution into its summary
line and title ("Static only" / "Production insights") — that satisfies the
mandatory-attribution requirement. Print that line as the **exact output**; do **not**
author your own attribution sentence or name the org. If the user expected
`full` but got `static`, the script's static-mode line already explains the org
is not onboarded — point them to it rather than restating it (see error handling).

**In scope:** zipping a project's Apex, submitting/polling the scan, decoding + presenting
violations, filtering/grouping existing results, troubleshooting API errors.

**Out of scope:** general static analysis / security / lint (→ `dx-code-analyzer-run`,
which lists ApexGuru as an engine), applying fixes to code, onboarding an org to
ApexGuru, minting SFAP tokens.

---

## Prerequisites

- **An authenticated `sf` CLI org** (`sf org login web ...`). `resolve-token.sh`
  derives the SFAP JWT from it via `<instanceUrl>/ide/auth` — this is the normal
  IDE-session path. Alternatively, set `APEXGURU_SFAP_TOKEN` / `APEXGURU_SFAP_TOKEN_FILE`
  to supply a JWT directly (CI/headless). The org is derived from the token's `tnk`
  claim — no org id is passed. Pass `--org <alias>` to pick a specific org.
  See `<skill_dir>/references/authentication.md`. If no token can be resolved, the
  script returns a clear error with a hint.
- **`sf`, `bash`, `curl`, `zip`, `jq`, `node`** on PATH (standard on macOS/Linux dev boxes).
- **A folder containing Apex** — an sfdx project, a `force-app/` subtree, or any
  folder with `.cls`/`.trigger` files. `build-zip.sh` collects all Apex beneath
  it regardless of layout; the API walks the whole archive.

---

## Workflow

### Step 1: Identify the project root

The project root is any folder that **contains Apex** somewhere beneath it
(usually an sfdx project root next to `sfdx-project.json`, but a `force-app/`
subtree or a loose folder of `.cls` files works too). If the user gave a path,
use it; otherwise use the current working directory. `build-zip.sh` collects
every `.cls`/`.trigger` under it (any layout) and fails clearly if none exists.

### Step 2: Package the project

```bash
TS=$(date +%Y%m%d-%H%M%S)
bash "<skill_dir>/scripts/build-zip.sh" "<project-root>" "./apexguru-${TS}.zip"
```

Output JSON gives `zip`, `bytes`, `humanSize`, `apexFileCount`, `scanRoot`. The script enforces
the **200MB compressed** limit and fails fast if exceeded. On error (`error`/`hint`
fields), relay the hint and stop.

### Step 3: Submit and poll

```bash
bash "<skill_dir>/scripts/run-scan.sh" "./apexguru-${TS}.zip" "./apexguru-raw-${TS}.json"
```

- Add `--fast` if the user wants a quicker/cheaper run (skips LLM-heavy fix
  generation).
- **The endpoint follows the token's environment** — the base URL is derived
  from the token's `tnk` claim: a prod org hits `api.salesforce.com`, and an
  internal stage/dev org hits `stage.`/`dev.api.salesforce.com`. Customers
  authenticate a prod org, so they always hit prod; no extra flags or config.
- `--org <alias>` picks which authenticated `sf` org the JWT is derived from
  (omit to use the CLI's default org).
- Progress (`QUEUED → RUNNING → SUCCEEDED`) streams to stderr; the script polls
  ~every 15s. Default ceiling is 10 min (`--max-polls`, `--interval` to adjust).
- On success, stdout is a one-line JSON summary and the full raw body is written to
  `apexguru-raw-${TS}.json`. On failure, stdout is `{error, httpStatus, status, hint}` —
  relay the hint. For status-code specifics see `<skill_dir>/references/error-handling.md`.
- **Foreground only.** Do not background this; polling output must be observed.
- **A SUCCEEDED scan is not the finish line.** The raw result is a base64 blob,
  not a user-facing answer. Do not stop or report "done" after the scan
  succeeds — you MUST continue to Step 4 to decode and present the report.
  Ending the turn at Step 3 leaves the user with nothing readable.

### Step 4: Decode and present

```bash
node "<skill_dir>/scripts/decode-report.js" "./apexguru-raw-${TS}.json" --present
```

`--present` is the default way to decode for presentation: it implies `--full`
(no silent caps) and prints ready-to-show markdown directly — a severity
legend (Minor / Major / Critical, plus a Tip marker when `analysisMode: full`
enriches severity from production metrics), one `### Issue N` card per
violation (message, current code, suggested fix, help-doc link) for the
non-hotspot rules — capped at `--top` (default 10) worst-first, with the cap
stated in the heading — and a closing `## Summary` table listing **every**
violation regardless of the card cap. `ExpensiveMethods` (a per-method
CPU-hotspot ranking from `full` mode, not a line-level antipattern) is
collapsed into its own ranked "CPU Hotspots" table instead of repeating a
near-identical card per method. Print this output to the user verbatim —
**present immediately — do not pause to ask, and do not re-summarize it into
a shorter table.**

For Step 5 drill-downs (filtering/grouping an existing result), the bare
(non-`--present`) JSON form is fine — see the reading rules below, which apply
whenever you run the script without `--present`.

**DO NOT:** invent script code, use bare `./scripts/...` paths, decode base64
inline, `jq` the `report` field, or Read the raw file directly.

#### Instructions for reading bare (non-`--present`) `decode-report.js` output

The command prints one JSON object to stdout. Read it field by field before
presenting anything — do not eyeball a partial view as complete:

1. **Check `truncated` first, before anything else.** If `true`, `groups` was
   capped to the top `--top` (default 10) rules, each group's `sample` was capped
   to 3 items, and `topViolations` was capped to `--top` items. **Never present a
   `truncated:true` result as the full picture.** Re-run the same command with
   `--full` appended and use that output instead. Only skip this if the user
   explicitly asked for a quick/partial look.
2. **State attribution from `analysisMode`/`attribution`** — `static`/"Static
   only" or `full`/"Production insights". This is mandatory on every response,
   per "Attribution is mandatory" above.
3. **`serverViolationBreakdown`** is the raw API's internal rule-code tally
   (e.g. `SOQL_IN_LOOP_1HOP`, `GGD`) — it's a sanity-check total (sums to
   `violationCount`), not a display name. Never show these codes to the user;
   use the human-readable `groups[].key` names instead (e.g.
   `SoqlInALoopOneHop`, `SchemaGetGlobalDescribeNotEfficient`).
4. **`severityCounts`** (top-level) is the severity distribution across ALL
   violations — use it for the summary table. Each `groups[]` entry has its own
   `severityCounts` scoped to just that rule.
5. **Build the "Violations by Rule" table from `groups`**, one row per entry:
   `key` → Rule, `count` → Count, `severityCounts` → Severity, and one
   `sample[0]` (or `items[0]` when `--full`) → Example (`file:line`).
6. **Build the "Top Issues" table from `topViolations`** — already sorted
   worst-severity-first. Use `rule`, `severity`, `file:line`, and the first
   entry of `fixes` (if non-empty) as Suggested Fix. If `fixes` is empty, omit
   that column's value rather than inventing a fix.
7. **When the user asks to explain a specific violation** ("what does this
   mean", "why is this flagged"), surface that violation's `message` (plain-
   language why) and `resources[0]` (Help Doc URL) verbatim — both exist on
   every violation object but are intentionally left out of the summary tables
   in step 5/6 to keep those scannable. Fall back to
   `references/violation-catalog.md` only if `message` is empty.
8. **`fixes` being `[]`** is expected, not an error — the API's `suggestions`
   field (fix code) isn't populated for every rule (notably `ExpensiveMethods`,
   a CPU ranking with no single-line fix); don't say "no fix available", just
   omit the column.
9. With `--full`, each group also carries an `items` array (every violation for
   that rule, not just the 3-item `sample`) — use `items` instead of `sample`
   when the user wants the complete list for one rule ("show me all the SOQL
   unused-fields ones").

#### Presentation template (fallback — only when NOT using `--present`)

`--present` (the default, per Step 4 above) already renders the full
severity-legend + issue-cards + summary-table output described in the
"Instructions for reading bare output" section — just print its stdout
verbatim. Only build a table by hand from bare JSON if `--present` genuinely
can't be used (e.g. scripting/CI context with no markdown renderer):

**Filling the `<Static only | Production insights>` title placeholder:** derive
the label from the `attribution` field (not `analysisMode` alone) — it already
encodes the three states:
- "Production insights" (`analysisMode: full` **with** runtime metrics) —
  enriched with production runtime metrics.
- "Static only" + `analysisMode: full` (**no** runtime metrics) — org is
  onboarded, but there's no runtime data for this code yet; generate a runtime
  report in Scale Center.
- "Static only" + `analysisMode: static` — source-only. Onboard the org to
  ApexGuru for production insights.

The fenced block below is the literal rendered output — substitute the real
values and print it; do not emit any of the guidance above:

```text
## ApexGuru Scan Complete — <Static only | Production insights>

**Found X performance violations** across Y files.

| Severity | Count |
|----------|-------|
| Critical (1) | X |
| High (2) | X |
| Moderate (3) | X |

### Violations by Rule
| Rule | Count | Severity | Example |
|------|-------|----------|---------|
| SOQL_IN_LOOP | 15 | High (2) | AccountService.cls:42 |
| DML_IN_LOOP | 8 | Critical (1) | AccountService.cls:60 |
| GGD | 2 | Moderate (3) | Utils.cls:12 |

### Top Issues
| # | Rule | Sev | File:Line | Suggested Fix |
|---|------|-----|-----------|---------------|
| 1 | DML_IN_LOOP | 1 | AccountService.cls:60 | Collect records; DML once after the loop |
| ... up to 10 |

Raw result: `./apexguru-raw-<TS>.json`
```

Scale to result size: **0** → "no performance antipatterns found"; **1–10** → one
table; **11+** → severity counts + by-rule table + top 10. End with the raw result
path. Do **not** append your own follow-up offer (no "I can drill in without
re-scanning…", no "filter by rule / group by file / explain a violation" menu) —
`--present` already prints the script's "show all" footer; that is the complete,
approved closing line and adding your own makes the output non-deterministic.
Rule-catalog details: `<skill_dir>/references/violation-catalog.md`.

### Step 5: Drill into results (no re-scan)

Re-run `decode-report.js` against the **same raw file** with flags:

| User says | Flags |
|-----------|-------|
| "show only SOQL-in-loop" | `--rule SOQL_IN_LOOP --full` |
| "just the critical ones" | `--severity 1` |
| "what's in AccountService.cls?" | `--file AccountService.cls --full` |
| "group by file" / "which file is worst?" | `--group file --top 5` |
| "break down by severity" | `--group severity` |
| "show me everything" | `--present` (or `--full` for bare JSON) |

---

## Constraints & Gotchas

| Item | Why / Fix |
|------|-----------|
| Run scripts with absolute `<skill_dir>` path | `./scripts/` resolves against the user's CWD, not the skill dir |
| Any project layout is fine | The API walks the whole archive for Apex; `build-zip.sh` collects every `.cls`/`.trigger` under the root, no `force-app/` required |
| Never decode `report` inline | It is a large base64 blob — always use `decode-report.js` |
| Use `--present` for the initial decode | Implies `--full` (no silent caps) and renders ready-to-show markdown directly — severity legend, per-issue cards, closing summary table — mirroring the reference MCP tool's presentation density |
| Never re-scan to filter | Step 5 re-decodes the existing raw file instantly |
| Attribution is pre-rendered | `--present` already prints the mode line ("Static only" / "Production insights") — print it as the exact output; never author your own attribution sentence or name the org |
| `static` when `full` expected | Org not onboarded to ApexGuru — tell the user, don't treat as an error |
| 401 / 403 / 404 / 400 | Token / org-ownership / scanId / zip issues — see references/error-handling.md |
| Foreground only, ~15s polls | Backgrounding loses progress; scans can take minutes |
| Token is a secret | `resolve-token.sh` never echoes it; don't print it or write it to result files |
| Not a security/lint scanner | For PMD/ESLint/security, use `dx-code-analyzer-run` |

---

## Reference & Script Index

**Scripts** (execute via `bash`/`node` with the absolute `<skill_dir>/` prefix, never Read):

| File | When to use |
|------|-------------|
| `<skill_dir>/scripts/resolve-token.sh` | Resolve SFAP JWT + base URL (called by run-scan.sh) |
| `<skill_dir>/scripts/validate-token.js` | Local (no-network) JWT pre-flight: env/scope/expiry (called by resolve-token.sh) |
| `<skill_dir>/scripts/build-zip.sh` | Step 2 — collect the project's Apex into a size-checked zip |
| `<skill_dir>/scripts/run-scan.sh` | Step 3 — submit + poll to completion |
| `<skill_dir>/scripts/decode-report.js` | Steps 4–5 — decode base64 report, group/filter violations |

**References** (read on demand):

| File | When to read |
|------|--------------|
| `references/authentication.md` | Where the SFAP JWT comes from; env-var/file setup |
| `references/api-reference.md` | Endpoint contracts, request/response shapes, limits |
| `references/violation-catalog.md` | ApexGuru rule meanings and typical fixes |
| `references/error-handling.md` | 400/401/403/404, FAILED, timeout, static-vs-full diagnosis |

`examples/` contains a sample SUCCEEDED response and a decoded-summary sample.
