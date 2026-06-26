---
name: mobile-platform-offline-validate
description: "Review a Lightning Web Component for **mobile offline** compatibility — the Komaci offline static analyzer that pre-primes the data graph for Salesforce Mobile App Plus and Field Service Mobile App. Produces a finding list with code-level fixes covering inline GraphQL queries in `@wire` configurations, modern `lwc:if` / `lwc:elseif` / `lwc:else` directives, and Komaci ESLint rule violations (private wire properties, non-local reactive references, getter side-effects). Use when the user asks for a \"mobile offline review\", \"Komaci check\", \"offline priming audit\", \"offline priming failure\", or \"offline data graph error\", or to validate an LWC against the `@salesforce/eslint-plugin-lwc-graph-analyzer` recommended ruleset. Do not use for generic LWC code review (use an appropriate domain review skill) or for building LWCs with native mobile capabilities (use `mobile-platform-native-capabilities-integrate`)."
metadata:
  version: "1.0"
---

# Reviewing LWC Mobile Offline

Run a structured offline-priming compliance pass over a Lightning Web
Component, producing a report of issues found and code-level fixes to bring
the component into compliance with Komaci's static analysis requirements
for the Salesforce Mobile App Plus and Field Service Mobile App.

## When to Use

- The user asks for a "mobile offline review", "Komaci check", or "offline
  priming audit" on a specific LWC.
- Preparing a component to ship in Salesforce Mobile App Plus or Field
  Service Mobile App offline mode.
- Investigating priming failures reported by the offline analyzer.

Do NOT use this skill for:

- Building an LWC that uses native mobile capabilities (barcode scanner,
  biometrics, location, etc.) — use `mobile-platform-native-capabilities-integrate`.
- Generic LWC code review — use the appropriate domain skill
  (`reviewing-lws-security`, `reviewing-lwc-rtl`, `accessibility-code-review`).

## Prerequisites

- Component path (LWC bundle under `modules/…`).
- Access to the component's JS/TS and HTML templates.
- Local Node + npm; ability to run `npx eslint` with the
  `@salesforce/eslint-plugin-lwc-graph-analyzer` plugin.

## Knowledge Base

[Mobile Offline Grounding](references/grounding.md) explains the three
violation categories and why each blocks offline priming. Read it before
judging. The per-reviewer references below are the source of truth for the
rules and remediations:

- Inline GraphQL wire configuration: [Inline GraphQL Reviewer](references/inline-graphql.md)
- `lwc:if` conditional rendering compatibility: [lwc:if Reviewer](references/lwc-if.md)
- Komaci ESLint static analysis: [Komaci ESLint Reviewer](references/komaci-eslint.md)

## Workflow

### Step 1 — Scope the review

Identify the component bundle: `.html`, `.js`/`.ts`. CSS and meta files are
not in scope for offline priming. If the bundle has multiple HTML
templates, all are reviewed.

### Step 2 — Read the grounding and per-reviewer references

Read [Mobile Offline Grounding](references/grounding.md) and the three
per-reviewer references end-to-end before judging. Cite the specific
reviewer when emitting each finding so the report is auditable.

### Step 3 — `lwc:if` / `lwc:elseif` / `lwc:else` (HTML)

Walk every `.html` file in the bundle and apply the rules in
[lwc:if Reviewer](references/lwc-if.md). For each occurrence of
`lwc:if={…}`, `lwc:elseif={…}`, or `lwc:else`, emit a finding with the
exact `if:true` / `if:false` rewrite — including the nesting required to
preserve `lwc:elseif` and `lwc:else` semantics.

### Step 4 — Inline GraphQL in `@wire` (JS)

Walk every `.js`/`.ts` file in the bundle and apply the rules in
[Inline GraphQL Reviewer](references/inline-graphql.md). For each `@wire`
that references a `gql` template literal directly (or via a top-level
constant), emit a finding that names a concrete getter and shows the
rewritten `@wire` configuration.

### Step 5 — Komaci ESLint pass (JS)

Run the Komaci ESLint analyzer over the bundle's JS file using the
bundled script. It applies the
`@salesforce/eslint-plugin-lwc-graph-analyzer` recommended ruleset with
the `bundleAnalyzer` processor enabled.

```bash
scripts/run-komaci.sh path/to/component.js
```

The script requires `@salesforce/eslint-plugin-lwc-graph-analyzer` to
be resolvable from the working directory, and the component's sibling
HTML templates must live next to the JS file (the plugin's
`bundleAnalyzer` processor uses them to resolve the offline data
graph). Output is ESLint `--format json` on stdout.

For each `messages[*]` entry in the output, group by `ruleId` and look
up the per-rule remediation in
[Komaci ESLint Reviewer](references/komaci-eslint.md). Emit a finding
per (rule, line) pair with the exact remediation text from the
reference; do not invent new advice. See the reference for the manual
`npx eslint ...` invocation if the script is unavailable in the runtime
environment.

### Step 6 — Produce the report

Emit a report in this shape:

```
## Mobile Offline (Komaci priming)
- <reviewer> — <file>:<startLine>:<startColumn>-<endLine>:<endColumn> — <type>
  Description: <verbatim from the reviewer reference>
  Intent analysis: <verbatim from the reviewer reference>
  Suggested action: <verbatim from the reviewer reference>
  Code: |
    <source snippet from startLine through endLine, optional but
     recommended when the violation spans multiple lines>
  Applied: yes/no

## Summary
- <n> issues found; <m> fixed; <k> deferred (with reason)
```

For Komaci ESLint findings, take `startLine`/`startColumn`/`endLine`/
`endColumn` from the ESLint message's `line`/`column`/`endLine`/`endColumn`.
For Inline GraphQL and `lwc:if` findings, supply the line/column range you
observed in the source. If `endLine`/`endColumn` are not available for a
finding, fall back to `<file>:<startLine>` and omit the trailing range.

Cite the reviewer (Inline GraphQL / lwc:if / Komaci ESLint rule id) on every
finding.

### Step 7 — Apply fixes

Apply the remediations directly when the user asked for fixes. If a
remediation conflicts with the component's behavior outside offline (e.g.
the developer relies on `lwc:elseif` for readability and the user is not
yet shipping to mobile offline), surface the conflict in the deferred list
rather than silently rewriting.


## Verification Checklist

- [ ] Every `lwc:if` / `lwc:elseif` / `lwc:else` flagged or absent.
- [ ] Every `@wire` referencing `gql` checked; inline queries extracted to
      a getter.
- [ ] Komaci ESLint analyzer was actually run; findings cite real rule
      ids, not invented ones.
- [ ] Each finding cites the originating reviewer or rule id.
- [ ] No remediation outside the three categories above (other concerns
      belong to other skills).


## Troubleshooting

- **`npx eslint` cannot find the plugin** — install
  `@salesforce/eslint-plugin-lwc-graph-analyzer` in the workspace, or use a
  pinned local install path. The plugin is the canonical source of Komaci
  rules.
- **`bundleAnalyzer` related errors** — the recommended config drives the
  bundle processor; do not strip it. The processor expects sibling HTML
  files to be discoverable. If running on a stripped-down JS file, supply
  the matching HTML in the temp directory.
- **No findings for a component you expect to fail** — confirm the
  recommended ruleset is applied (not just `bundleAnalyzer` with empty
  rules). Some rules require the HTML to be present alongside the JS.
- **Findings duplicate `lwc:if` from the dedicated reviewer** — the Komaci
  plugin does not check templates; the `lwc:if` check is HTML-only and
  comes from Step 3. Findings from Step 5 are JS-only.
