# Examples — dx-apexguru-scan

Sample data and eval prompts for the ApexGuru performance-scan skill.

## Files

| File | Purpose |
|------|---------|
| [`sample-succeeded-response.json`](sample-succeeded-response.json) | A realistic API `SUCCEEDED` body (`analysisMode: static`) with a base64-encoded `report`. Feed it to `decode-report.js` to validate parsing offline. |
| [`sample-decoded-summary.json`](sample-decoded-summary.json) | The bare (non-`--present`) JSON output of `decode-report.js` on the sample response — the shape drill-down queries (Step 5) work against. |
| [`sample-full-no-runtime-response.json`](sample-full-no-runtime-response.json) | A real production `SUCCEEDED` body from scanning the eval seed class (`analysisMode: full`, no runtime metrics → renders as **Static only**). Use it to exercise `decode-report.js --present` offline, without a live org. Contains no token/secret. |

## Try it offline (no token / no API needed)

```bash
node ../scripts/decode-report.js sample-succeeded-response.json --present   # rendered markdown (default presentation)
node ../scripts/decode-report.js sample-succeeded-response.json             # bare JSON
node ../scripts/decode-report.js sample-succeeded-response.json --group file --top 5
node ../scripts/decode-report.js sample-succeeded-response.json --rule DML_IN_LOOP --full
```

## How the eval scores this skill

The eval judges the `dx-apexguru-scan` agent's output against each dataset's `prompt.md`
and `instruction.md` rubric — grouped-by-rule findings with severity, `file:line`, and a
suggested fix — rather than diffing against a fixed reference file. This suits the scan,
whose output varies per run and per org.

The sample JSON fixtures here are for exercising `decode-report.js` offline (see
"Try it offline" above); they are not eval references.

## Eval prompts

Per the authoring quality bar, the skill should pass at least these three evals.

### 1. Happy path (should trigger)
> "Run ApexGuru on my Apex project and show me the performance issues."

Expected: zips the project's Apex, submits, polls to `SUCCEEDED`, decodes the report, and
presents violations grouped by rule with severity, `file:line`, and fixes — labeled
**Static only** or **Production insights** per `analysisMode`.

### 2. Edge case (should trigger, handle gracefully)
> "ApexGuru scan — but I expected production insights and only got static results."

Expected: recognizes `analysisMode: static`, explains the org isn't onboarded to
ApexGuru, does **not** treat it as an error or retry. (Also covers the token-missing
and 401/403/404/400 paths → surface the hint from `run-scan.sh`.)

### 3. Should NOT trigger
> "Run a security scan on my Apex classes and check for CRUD/FLS violations."

Expected: defers to `dx-code-analyzer-run` (security/lint/PMD) — this skill is
performance-antipattern-only and should not activate.
