# Report format — per-workflow report contracts

Write the report to `${outputDir}/report.md`, reporting only **the workflow you ran**. The
length/concision rules (say each load-bearing point once, well under ~150 lines, no exhaustive
per-object dumps) live in SKILL.md's `## Output` section — they are not repeated here. **This file
adds only what SKILL.md does not: the per-workflow section contracts below.** The expected-content
lists are a ceiling, not a checklist to pad toward.

## Workflow A (configure)

**Bounded request:** (1) the classification strategy — subject, root(s), per-relationship
follow/stop and why; (2) the tree — roots, paths, fields, with node count vs 200, max depth vs 10,
max children vs 10; (3) lifecycle — authored INACTIVE, must be activated to run, ACTIVE edits need
deactivate→edit→then **explicit user-confirmed** reactivation (never auto-reactivated); (4) the
guardrail — authoring/editing/deleting the policy never deletes the subject's records; (5) deploy
outcome — deployed, or the raw error + prerequisite.

**Unbounded request:** instead state the caps, name the specific cap the request would exceed, and
offer the bounded alternative (split/prune) — never a silently truncated "complete" map.

**Under-specified request:** instead enumerate the classification decisions the admin must make
(roots; per-relationship follow/stop; fields) and mark any proposal disposition-pending — never an
authoritative map of guessed personal data.

## Workflow B (export)

(1) the **resolved subject** — identifier (email/name/id) → root-entity Id + type — and the
**policy chosen** (noting if it was ambiguous and you asked); (2) consent confirmed, or the run
withheld as ambiguous; (3) that this was an **export, not a deletion**; (4) the **poll ordering**
made explicit — a couple of polls, the file retrieved only after the run reaches a terminal state,
an early not-ready response is expected, and if still non-terminal you **asked** the user before
continuing (never looped); stated even on the accepted preflight-error path; (5) outcome from the
**envelope / run status** in plain terms — running / completed / errored — not the HTTP code; (6)
file location on success (from the `dsr` getfile route, after terminal); (7) any missing
permission/feature named with the raw error. A non-terminal run is a valid stopping point — report
it as *still running* and defer to the user, don't diagnose the async backend.

**Preflight-error path (feature/policy/subject absent — the run never started):** keep it short.
Lead with the blocker(s) and the prerequisite to unblock each; state export-not-deletion **once**;
state the poll-then-download ordering **once** (a single short paragraph — this is item 4, not a
recurring theme). Do **not** add a separate essay re-explaining "grab it right away," and do **not**
enumerate every subject-search query — one representative command and the outcome is enough. Two
blockers → two short entries, not two full-screen tables.

## Workflow C (history)

The prior runs from the `DsarPolicyLog` SOQL read (or an explicit "no prior runs"), and that **no
new run was started**.

## Workflow D (coverage gap analysis)

(1) the **method** stated once up front — from the policy root(s), one relationship hop out,
candidate fields flagged with a reason each, admin disposes; (2) the **objects scanned** by name
(roots + the one-hop objects); (3) a **candidate table** — `object | field | reason | in policy?`;
(4) **covered vs newly surfaced**; (5) the **one-level search limit** stated explicitly, plus the
offer to go deeper only on confirmation (with the token-cost warning); (6) a **disposition prompt** —
which to add (adding routes to Workflow A: authored INACTIVE, no auto-reactivation) — and that the
audit deletes nothing. "No uncovered candidates at one level" is a valid result. Keep the candidate
table to the roots + one hop; don't append further-hop objects to look thorough.
