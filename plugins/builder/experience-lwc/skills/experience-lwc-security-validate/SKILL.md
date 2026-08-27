---
name: experience-lwc-security-validate
description: "Use this skill as THE specialized Lightning Web Security (LWS) validator for a Lightning Web Component bundle (`.js`, `.ts`, `.html`, `.css`, `.js-meta.xml`) — the canonical LWS/Product-Security review for LWCs, NOT a generic code-security pass. It produces either a severity-ranked finding list with code-level remediations or a SARIF 2.1.0 JSON score report keyed by the `lws-001`…`lws-023b` rule catalog. TRIGGER when the user asks to review, audit, or check an LWC component for LWS compliance issues and recommend fixes, score a component's LWS/security compliance, find dangerous DOM APIs or blocked sinks (`eval`, `Function`, `document.write`, `innerHTML`, `document.createElement('script')`, global-scope assignment to `window`/`globalThis`, unsafe URL schemes), or emit a SARIF security report. DO NOT TRIGGER for generic non-LWC security review, for building a new LWC (use experience-lwc-generate), accessibility (WCAG 2.2), RTL/i18n, or Apex/Aura/server-side review."
metadata:
  version: "1.0"
  domains: ["Experience"]
  relatedSkills:
    - design-systems-slds-validate
    - dx-code-analyzer-run
    - experience-lwc-generate
  cliTools:
    - tool: ["jq"]
      semver: ">=1.6"
    - tool: ["python3"]
      semver: ">=3.8"
---
<!-- adk-managed-skill -->

# Reviewing LWS Security

Run a structured Lightning Web Security (LWS) and Product Security compliance pass over a Lightning Web Component. Two output modes:

- **Review mode** (default) — severity-ranked findings + applied code fixes.
- **Score mode** — SARIF 2.1.0 JSON report keyed by the LWS rule catalog (`lws-001`…`lws-023b`) for downstream gating, eval scoring, or CI ingest.

Both modes use the same detection rules from the references; only the output format differs.

## When to Use

- The user asks for a "security review", "LWS check", "pre-ship security audit", or "compliance pass" on a specific LWC → review mode.
- The user asks to "score" a component's security or wants machine-readable findings to feed a gate or eval → score mode.
- Preparing a component for release and needing a unified security report.
- After implementing a fix, to verify no regression in security posture.

Do NOT use this skill for:
- Building new components (use `experience-lwc-generate`).
- Accessibility (apply WCAG 2.2 separately) or RTL review — out of scope.
- Gating a fix behind a feature flag (apply feature-flag gating after fixes land).
- Non-LWC security review (Apex, Aura, server-side) — out of scope.

## Prerequisites

- Component path (LWC bundle under `modules/…`).
- Access to the component's JS/TS, HTML templates, CSS, and `.js-meta.xml`.
- Output mode: `review` (default — find, fix, report) or `score` (find, emit SARIF JSON, do NOT modify code). Confirm with the user before starting if it isn't obvious from the request.

## Knowledge Bases

Each reference is the source of truth. Do not summarize from memory — open the reference, apply the guidelines, and cite the specific section you used in the report.

- Lightning Web Security (LWS) catalog: [LWS Security Expert](references/lws-security-expert.md) — blocked APIs and allowed alternatives.
- Rule catalog (`lws-001`…`lws-023b`): [Product Security Framework](references/security-analysis.md) — for every rule the catalog gives the detection patterns and the canonical SARIF `ruleId` / `level` / `message` template. **Score mode emits one SARIF result per match using these exact values.**

## Workflow

### Step 1 — Scope the review

Collect the component path and identify the files to review. Include every file in the component bundle: `.html`, `.js`/`.ts`, `.css`, `.js-meta.xml`, and any child components owned by the same team that are invoked from the target.

Note any existing feature-flag gates — findings that require code changes must respect them.

### Step 2 — Read the knowledge bases

Read [LWS Security Expert](references/lws-security-expert.md) and [Product Security Framework](references/security-analysis.md) top-to-bottom before judging. The LWS reference enumerates blocked DOM APIs and their allowed alternatives; the Product Security framework gives the severity taxonomy, the 23-rule SARIF catalog, and remediation patterns.

### Step 3 — Walk the rule catalog

Run every rule in [Product Security Framework](references/security-analysis.md) (`lws-001` through `lws-023b`) against the component bundle. For each rule:

1. Apply the **"How to Find the Issue"** patterns verbatim. Do NOT shortcut — each rule lists obfuscation patterns (bracket notation, unicode escapes, `Reflect.*`, string concatenation) you must consider.
2. For every match record: `ruleId`, `level` (`error` / `warning` from the catalog), `file`, `startLine`, `startColumn` (column 1 if unknown), `message` (use the catalog's `message` template, substituting any `{placeholder}` from the actual code).
3. If a rule has the prerequisite "Only analyze files that import from 'lwc'" (lws-008), gate it via `scripts/check-lwc-import.sh <file>` — the script prints `lwc-import=yes` when a `from 'lwc'` import is present and `lwc-import=no` otherwise. Skip the rule for that file when the answer is `no`.

This catalog is the canonical detection list; the JS/TS, HTML, and `.js-meta.xml` bullets that follow are *additional* checks beyond the SARIF rules.

### Step 4 — HTML template inspection (additional)

Walk each template for:

- `lwc:inner-html` usage — verify the source is trusted.
- Unescaped expressions feeding attributes LWS treats as sensitive (`href`, `src`, `srcdoc`, inline event handlers).
- Direct `style="…"` with bound expressions — candidates for CSS class swaps.
- Embedded `<iframe>` or `<object>` without sandboxing (Step 3 catches the `srcdoc` and protocol cases via lws-023a/lws-023b; this step catches missing `sandbox` attributes).

### Step 5 — Meta and configuration inspection (additional)

Inspect `.js-meta.xml` for:

- Over-broad API access (`lightning__FlowScreen`, `lightning__AppPage`, etc.) when the component doesn't need it.
- Public properties exposed that contain sensitive data.
- Missing `capabilities` restrictions for the target surface.

Inspect Apex bindings for:

- `@wire` to Apex methods without `@AuraEnabled(cacheable=true)` where caching is safe.
- Direct imperative calls that bypass permission checks.

Findings from Steps 4-5 use rule IDs `lws-tpl-001`…`lws-tpl-NNN` (HTML) and `lws-meta-001`…`lws-meta-NNN` (meta) — sequence numbers per finding within the report — so they don't collide with the SARIF catalog.

### Step 6 — Produce the report

Pick the output format based on the mode confirmed in Prerequisites.

#### Review mode (default)

Use [examples/review-report.md](examples/review-report.md) as the template — one bullet per finding under `## Security (LWS + Product)`, one totals line under `## Summary`.

Severity ordering: Critical → High → Medium → Low (map SARIF `error` → High, `warning` → Medium unless the rule says otherwise). Cite the reference section that produced each finding (e.g., "Product Security § lws-001 document.createProcessingInstruction").

#### Score mode

Emit a single SARIF 2.1.0 JSON document — and nothing else. No prose before or after. Do NOT write the JSON to a file; return it inline. Empty `results` array means no issues found.

Use [examples/score-report.sarif.json](examples/score-report.sarif.json) as the shape reference — same top-level structure (`$schema`, `version`, `runs[0].tool.driver.rules[]`, `runs[0].results[]`), populated with the actual rules that fired and the actual matches.

Rules:
- `ruleId` matches a catalog entry exactly (`lws-001`…`lws-023b`, or the `lws-tpl-*` / `lws-meta-*` namespaces from Steps 4-5).
- `level` is `error` for catalog rules marked `level: error` and `warning` for `level: warning`. No other values.
- `message.text` uses the catalog's `message` template with placeholders substituted (e.g., replace `{eventName}` with the actual event name found in code).
- One `result` per match. If a rule fires three times in a file, emit three results.
- Include only rules that fired in `tool.driver.rules`; an empty `results` array still requires `tool.driver.rules` to be present (use `[]`).

### Step 7 — Apply fixes (review mode only)

Skip in score mode — score mode is read-only.

For each accepted finding:

1. Edit the component files (HTML, JS/TS, CSS, meta.xml) to apply the fix.
2. Preserve existing correct behavior and existing feature-flag gates. If a gate is already configured for the same concern, leave it untouched. New feature-flag gates for phased rollout are out of scope for this skill — apply them separately.
3. Do NOT silently delete old code — preserve the original path where a gate is required.
4. Do NOT weaken the security posture to make tests pass; fix the test if it depends on the insecure pattern.

### Step 8 — Verify

- **Review mode**: Re-run Step 3's catalog walk against the updated files; every fixed finding must no longer appear. Run Jest tests and any component-level security tests. If fixes touched Apex access patterns, confirm permissions with the server-side reviewer.
- **Score mode**: Before returning, write the emitted SARIF to a temporary file and run `scripts/validate-sarif.sh <path>` — the script confirms the JSON parses, `version` is `2.1.0`, every `ruleId` matches the catalog pattern (`lws-NNN[a-z]?` / `lws-tpl-NNN` / `lws-meta-NNN`) and is declared in `tool.driver.rules`, every `level` is `error` or `warning`, and every result has a `physicalLocation.artifactLocation.uri` + `region.startLine`. Fix any failure before returning the SARIF.

## Cross-References

- Related skills:
  - `experience-lwc-generate` — for authoring new LWC bundles that are security-compliant from the start.
  - `design-systems-slds-validate` — SLDS/design-system compliance pass (accessibility overlaps with WCAG 2.2 — run separately).
  - `dx-code-analyzer-run` — repo-wide static-analysis pass; use it alongside this skill for coverage beyond the LWS catalog.

## Verification

- Every catalog rule (`lws-001`…`lws-023b`) was evaluated against the bundle, not a hand-curated subset.
- Every finding has either been applied (review mode) or surfaced in the SARIF result (score mode), or carries an explicit deferred note with a reason.
- Each finding cites a specific catalog rule ID — no freeform "looks suspicious" entries.
- No new XSS sinks, unsafe URL flows, or blocked DOM APIs introduced by the fixes.
- Score-mode output is valid SARIF 2.1.0 JSON, returned inline, with no surrounding prose.
