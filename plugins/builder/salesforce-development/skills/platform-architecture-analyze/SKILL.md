---
name: platform-architecture-analyze
description: "Analyze a Salesforce project against the Salesforce Well-Architected framework (Trusted / Easy / Adaptable). Use when the developer asks to \"review the architecture\", \"run a Well-Architected check\", \"audit this project\", \"is this project well-architected?\", \"assess security/governor-limit/packageability risk across the project\", or wants a holistic code-and-metadata health report. Grades the criteria that are observable from code and metadata (sharing/FLS, bulkification, selective SOQL, trigger-handler separation, legacy tech, packageability) with file:line evidence, and emits a human checklist for governance/process pillars it cannot see (security matrix, BCP, roadmaps, AI governance). Distinct from `dx-code-analyzer-run` (single-tool Code Analyzer scan of Apex) — this skill is a multi-pillar architectural review that orchestrates several analysis skills and maps findings to Well-Architected. Read-only: it grades and advises, never edits."
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
metadata:
  cliTools:
    - tool: ["sf"]
      semver: ">=2.0.0"
  relatedSkills:
    - "dx-code-analyzer-run"
    - "platform-lsp-integrate"
    - "platform-metadata-retrieve"
    - "platform-apex-generate"
---

# Analyzing Architecture (Well-Architected Review)

Grade a Salesforce DX project against the **Salesforce Well-Architected** framework and produce an honest, evidence-backed report: a pillar-scored table for what's observable in code and metadata, plus a human checklist for the governance/process concerns a local repo can't reveal.

This skill is an **orchestrator**. It does not re-implement static analysis — it drives the analysis skills the plugin already ships and maps their output onto the Well-Architected pillars. It is **read-only**: it grades and recommends; it never edits, deploys, or deletes.

It also backs the `architecture-review` agent, which runs this exact workflow as a dedicated read-only reviewer. Invoke the agent for an end-to-end review; use this skill directly when you want the workflow inline in the current session.

## Capability resolution

1. **Skill-orchestrated review** (this skill) — runs the observable checks by delegating to existing skills/MCP tools, scores each sub-pillar, and emits the manual checklist.
2. **Direct CLI / grep** — used only for the lightweight structural signals the rubric names (sharing keywords, legacy-tech file types, deploy strategy). Fine standalone, but skips the pillar scoring and the governance checklist this skill provides.
3. **API** — not applicable.

## The rubric (read these first)

Before scoring, read the three reference files — they are the source of truth:

- [`references/well-architected-rubric.md`](references/well-architected-rubric.md) — the full pillar → sub-pillar → criteria tree, each criterion tagged `[observable]` or `[manual]`.
- [`references/observable-checks.md`](references/observable-checks.md) — each `[observable]` criterion mapped to its detection (skill / MCP tool / grep pattern) and the anti-pattern it flags.
- [`references/manual-review-checklist.md`](references/manual-review-checklist.md) — the `[manual]` criteria as a copy-pasteable governance checklist.

## Workflow

### Step 1 — Scope the project

```bash
# Package directories + API version
cat sfdx-project.json
```

Establish:
- **Package dirs** (from `packageDirectories[].path`) — where the source lives.
- **Inventory** — count Apex classes, triggers, LWC bundles, Aura, Flows, objects:
  ```bash
  find <pkgdir> -name '*.cls' | wc -l
  find <pkgdir> -name '*.trigger' | wc -l
  find <pkgdir> -name '*.js-meta.xml' | wc -l   # LWC bundles
  ```
- **Tooling signals** — does the repo have tests (`*Test.cls`, `__tests__/`), CI (`.github/workflows/`), linting (`.eslintrc*`, `.prettierrc*`), a `package.xml` vs source/package strategy?
- **Org connection** — `sf org display --json` succeeds → org-dependent checks (OWD, permission sets) are in play; otherwise mark them manual.

Record the scope line for the report header.

### Step 2 — Run the observable checks (delegate; don't re-scan)

Work through `references/observable-checks.md`. For the heavy lifting, delegate:

- **Apex security + performance** → `dx-code-analyzer-run`. It runs `sf code-analyzer` and classifies findings by severity. Map its rules onto the rubric:
  - `ApexSOQLInjection`, `ApexCRUDViolation`, `ApexInsecureEndpoint`, `ApexBadCrypto` → **Secure**
  - `ApexSharingViolations` → **Secure** (sharing) / **Composable** (separation)
  - `OperationWithLimitsInLoop`, `OperationWithHighCostInLoop` → **Reliable** / **Automated**
  - `AvoidDebugStatements` → **Automated**
- **Inline SOQL parse + selectivity, compile-level diagnostics** → `platform-lsp-integrate` (`apex_diagnostics`, `lwc_diagnostics`, `check_soql_selectivity`) when `lsp_health` is green → **Reliable** / **Automated**.
- **OWD / sharing model / permission sets** → `platform-metadata-retrieve` + `sf org` inspection, only if an org is connected → **Secure**.

For the lightweight structural signals, grep directly (patterns in `references/observable-checks.md`), e.g.:

```bash
# Secure — classes missing a sharing keyword
grep -rLE 'with(out)? sharing|inherited sharing' --include='*.cls' <pkgdir>

# Intentional — legacy tech still present
find <pkgdir> -name '*.workflow-meta.xml' -o -name '*.flowDefinition-meta.xml'
grep -rl '@future' --include='*.cls' <pkgdir>

# Composable — deploy strategy
ls manifest/package.xml 2>/dev/null            # package.xml-driven (anti-pattern past PoC)
grep -l '"path"' sfdx-project.json             # source/package strategy

# Composable — runtime config in custom settings vs CMT
find <pkgdir> -path '*objects*' -name '*.object-meta.xml' | xargs grep -l 'CustomSetting' 2>/dev/null
```

Collect every finding with `file:line` evidence. A check with no evidence is **not** a pass and **not** a fail — it's "not observable" and moves to the manual checklist.

### Step 3 — Score each observable sub-pillar

Assign ✅ / ⚠️ / ❌ per sub-pillar using the thresholds in `references/observable-checks.md`:

- **✅** no anti-patterns found in the observable checks for that sub-pillar.
- **⚠️** low/moderate findings, or only some criteria observable.
- **❌** critical/high findings (e.g. SOQL injection, FLS bypass, SOQL-in-loop at scale).

Then roll the sub-pillar verdicts up to a pillar verdict (worst-of, with a note).

### Step 4 — Emit the manual checklist

Copy the `[manual]` criteria from `references/manual-review-checklist.md` into the report as unchecked items, grouped by pillar. Label the section clearly: **"not auto-graded — assess with your team."** Do not guess at these; the point is to hand the developer a structured governance checklist, not to fake a score.

### Step 5 — Report

Produce one report using the format below. Lead with pillar verdicts, then observable findings (Trusted/Secure first — never bury security under style), then the manual checklist, then recommended next steps that name the skill which would apply each fix.

```text
Well-Architected Review — <project name>
Scope: <pkg dirs>, <N classes / M triggers / K LWC>, tests: <y/n>, CI: <y/n>, org: <connected alias / none>

PILLAR VERDICTS
  🛡️ Trusted     <✅|⚠️|❌>  (Secure …, Compliant …, Reliable …)
  ⚡ Easy         <✅|⚠️|❌>  (Intentional …, Automated …, Engaging …)
  🔁 Adaptable    <✅|⚠️|❌>  (Resilient …, Composable …)

OBSERVABLE FINDINGS  (graded from code + metadata)
  Sub-pillar | Verdict | Finding | Evidence (file:line / tool)

MANUAL REVIEW  (not auto-graded — assess with your team)
  [ ] <item>  …

RECOMMENDED NEXT STEPS
  - <highest-signal fix> → via `<skill>`
```

## Examples

### Example 1 — "Is this project well-architected?"

Scope the project, run all observable checks (delegating Apex analysis to `dx-code-analyzer-run`), score all three pillars, emit the full manual checklist, and report. This is the default full review.

### Example 2 — "Review my project's security and governor-limit risk"

Narrow to the **Secure** and **Reliable/Automated** sub-pillars: run `dx-code-analyzer-run` with a security + performance selector, use `platform-lsp-integrate` `check_soql_selectivity` for selectivity, grep for missing sharing keywords. Score those sub-pillars; still emit the Secure/Compliant manual items (security matrix, encryption strategy). Skip the Adaptable deep-dive unless asked.

### Example 3 — "Run a Well-Architected check before we package this for release"

Full review, weighting **Composable** (packageability — CMT vs custom settings, loose coupling, `LATEST` aliasing, no `package.xml`-driven deploys) and **Resilient** (source-tracked, CI, no failed deploys). Lead the report with the packageability readiness verdict.

## Failure modes

| Symptom | Cause | Recovery |
|---|---|---|
| `dx-code-analyzer-run` reports the analyzer isn't installed | Code Analyzer v5 missing | Note it in the report; fall back to grep-based structural checks for Apex and mark PMD-only criteria "not observable". |
| `sf org display` fails | No org connected | Mark OWD / permission-set / org-metadata criteria as manual; grade only file-based criteria. |
| LSP tools return `lsp_disabled` / `no_apex_workspace` | LSP off or no workspace | Skip the LSP-grounded checks; rely on `dx-code-analyzer-run` + grep. Note the gap. |
| No `sfdx-project.json` | Not an SFDX project | Stop — this skill reviews SFDX projects. Tell the developer. |
| Huge repo, scan is slow | Project-wide PMD + graph build | Scope `dx-code-analyzer-run` to the package dir; note that cross-file (sfge) findings may be partial. |

## Rules

- Read the three `references/*.md` files before scoring — the rubric is the source of truth.
- Delegate observable detection to existing skills/MCP tools; grep only for the lightweight structural signals the rubric names.
- Every observable finding carries `file:line` (or tool-result) evidence. No evidence → manual checklist, not the scored table.
- Never score a `[manual]` governance criterion from inference — list it for human review.
- Read-only: recommend fixes and name the skill that applies them (`platform-apex-generate` for Apex authoring / trigger refactoring); never edit, deploy, or delete.
- Lead with Trusted/Secure findings; don't bury security under style nits.
- Surface zero-finding sub-pillars briefly ("no issues found in observable checks") rather than omitting them.
