---
name: platform-dsar-policy-manage
description: "Configure, run, and audit DsarPolicy Right-to-Portability exports end to end: author the data map over a subject's related records, resolve a request's subject (email/name/id) to a root-entity record, run an export against an ACTIVE policy (poll a couple of times, then ask before continuing; download once terminal), and read run history. Use when the user needs to set up, edit, execute, or inspect a DsarPolicy or Right-to-Portability (RTP) export, or audit which personal data a policy does not cover yet. TRIGGER when: the user configures a DsarPolicy or RTP data map, authors DsarPolicyPath or DsarPolicyField metadata, runs or exports a subject's portable data, downloads an RTP export file, reviews DsarPolicy run history, or asks what personal data the policy does not cover yet (coverage gap analysis). DO NOT TRIGGER when: the user wants to erase, delete, or remove a subject's records (RTP is portability export, not erasure — this skill deletes nothing), mask sandbox PII, or deploy unrelated metadata."
metadata:
  version: "1.7"
  domains: ["Platform"]
  minApiVersion: "68.0"
  cliTools:
    - tool: ["python3"]
      semver: ">=3.10.0"
    - tool: ["sf"]
      semver: ">=2.0.0"
---

# platform-dsar-policy-manage: DsarPolicy Right to Portability, end to end

Operate a **`DsarPolicy`** — the metadata driving a **Right-to-Portability (RTP)** export — across
its lifecycle: **configure** the tree, **run** an export, **audit** runs. A `DsarPolicy` is a
*read/export map*: it names which of a subject's records an export collects. It **never deletes
anything**. The value here is **judgment**, not XML plumbing.

> **FIRST LINE OF EVERY RESPONSE — do not narrate the skill.** Your first output token is *work or
> the answer*, never a play-by-play. Do **not** open with "This is a coverage-gap audit / Workflow
> D…", "Let me read the skill's guide/mechanics…", "Per rule #1…", or "Let me discover the SOR…".
> Don't name the workflow, announce which reference files you're about to read, or describe your
> method before doing it — just start doing it (call the tool) and, when done, present the result.
> This is load-bearing call #8, stated up front because it governs your very first token. A
> plain-language sentence about *the user's data/org* is fine; a sentence about *the skill, its
> workflows, rules, tools, or files* is not.

## Load-bearing calls (get these right or the task fails)

These override any leading phrasing in the request. Read them first, every time. **Call #1 is the
literal first action of every task — before you pick a workflow, before any `sf` command.**

1. **Route through the SOR tool FIRST — before any `sf`/endpoint call, no exceptions.** The very
   first action of *every* task here — including a trivial read-only "does a policy exist / list the
   policies" lookup — is to scan **this run's available tools** for a capability-routing tool exposing
   **discover / describe / dispatch** verbs (project-codey / Headless 360 today; any host prefix such
   as `mcp__<host>__discover`; **match the verb shape, not a fixed name**). If one is present, that is
   the entry move: `discover → describe → dispatch` the **`DsarPolicyManager`** SOR (owner Privacy
   Center; `isActive` gates execute/edit/delete) and reject look-alikes (data mask, generic consent,
   subject *erasure*). Do **not** reach for `sf` first — grabbing `sf` on reflex because the task
   "looks like a quick lookup" is the top recurring miss, and it is wrong even when it would work.
   `sf` is the fallback **only** when no routing tool is in reach (checking `sf org list` to see which
   orgs are authenticated locally is fine — that is a client-side auth check, not a SOR call). Every
   `sf`/`salesforce-api-context` command shown in the workflows below is the *no-routing-tool*
   spelling; when the routing tool is present, dispatch the equivalent operation through it instead.
   Detail: `references/headless-sor.md`.
2. **Export, never erasure.** A run produces an **export file**; it does not erase/redact/delete the
   subject. If the request frames it as deletion ("remove them", "erase", "clear out"), **correct
   that first** and never report the subject as erased. Erasure is a separate mechanism — if that's
   the goal, say so and stop. You may still export if authorization is clear, after correcting the
   premise.
3. **Do not guess personal data.** Which objects/relationships hold *the subject's* data is the
   **admin's** classification call. If the request delegates it ("figure out what counts", "wire the
   whole thing up"), **do not author a guessed tree** — enumerate the decisions the admin must make
   (roots; per-relationship follow/stop; fields), mark any proposal *pending admin disposition*. An
   over-broad guess exports other people's records.
4. **Caps are hard — name the cap and stop; don't graph-walk.** Tree caps: **10 children/path, depth
   10, 200 nodes**. An unbounded request ("everything", "the whole graph") cannot fit. Do **not**
   enumerate the object graph to "try" (never finishes, burns the turn). Name the specific cap
   exceeded and offer a bounded alternative (split policies, prune branches). Never silently truncate.
5. **Poll a couple of times, then ask — don't block on terminal.** The run handle serves status
   **and** file. An early *getfile* returns `NOT_FOUND` / `"This file isn't ready yet"` — the
   contract working, not a failure. Poll ≈2–3×; if still not terminal, **stop and ask the user
   whether to keep polling** — don't loop. A run can sit non-terminal indefinitely on downstream
   async processing — **platform / Tool Factory territory, not this skill's to diagnose or reach
   into**; report status in plain terms (**running / completed / errored**) and let the user decide.
   Never download before terminal. A **failed run can return HTTP 201** — read the **envelope /
   `RequestStatus`** in the body, not the HTTP code. getfile segment is **`dsr`**, not `dsar`.
6. **History is a read.** Run history = a **SOQL query over `DsarPolicyLog`**. Not `installListView`,
   not a UI list; it starts no run.
7. **Never auto-activate or republish.** Activation is a deliberate, human-confirmed step. Editing an
   ACTIVE policy needs it deactivated first — **deactivate → edit → stop, report, get explicit user
   confirmation before reactivating**. New policies stay INACTIVE until the user activates.
   Auto-republishing breaks the reviewable audit trail disputes depend on.
8. **Work silently — never narrate the skill's internals (applies to every workflow; see the
   masthead above).** The user asked a domain question; answer it, don't describe how the skill
   answers it. Run the tools and present the result — **no intermediate narration** of: that you are
   about to read / are reading the skill's guide, mechanics, or reference files ("let me read the
   skill's guide and mechanics"); **which workflow this is** ("this is a coverage-gap audit / Workflow
   D", "Workflow C-style read") — the user does not think in workflow letters, so never name one;
   which SOR/routing tool you're using or that you're "loading schemas / discovering / dispatching";
   the load-bearing rule numbers ("per rule #1"); the reject-look-alikes step; the operation graph or
   GET-vs-dispatch plumbing (`getAccessInfo`, `dispatch_readonly`, etc.). These steer *how you work* —
   they are not status updates. (The harness still shows its own plain tool-call lines; that is fine —
   just don't add your own play-by-play.) **What the user DOES see:** the final answer, and — where a
   call requires it — a plain-language question (`AskUserQuestion`) or a short scope/consent line about
   *their org* ("I only listed policies; I changed nothing", "this exports, it doesn't delete"). Rule
   of thumb: a sentence about **their data/org** can be user-facing; a sentence about **the skill, its
   workflows, steps, tools, rules, or files** stays internal. Workflow D's method preamble is the one
   allowed "here's how I'll do it" line, and even it must be plain-language about *the audit approach*
   ("I'll look one level out from your policy's objects and flag fields that might hold personal
   data") — it names **no** workflow letter, rule, tool, or file. That preamble is *not* a licence to
   say "this is Workflow D" or "let me read the mechanics".

## The DsarPolicy object model

Each entity is reached a **different** way — guessing the surface is the top time-sink.

| Entity | What it is | How you reach it |
|--------|-----------|------------------|
| `DsarPolicy` | Policy shell + lifecycle (ACTIVE/INACTIVE) | **Metadata API** |
| `DsarPolicyPath` | A tree node: a root object, or a parent→related relationship | **Metadata API** (child of `DsarPolicy`) |
| `DsarPolicyField` | A field collected at a path | **Metadata API** (child of a path) |
| `DsarPolicyLog` | Run log (one row per run) | **Standard SOQL** |
| Execute an export | — | **Connect DSR endpoint** (`POST`) |
| Status / getfile | — | **Connect DSR endpoint** on the handle; getfile segment `dsr` |

Resolve the exact Connect route/version at run time via `salesforce-api-context` (or `sf`). Don't
`sf sobject describe DsarPolicy*` — the tree is metadata; only `DsarPolicyLog` answers standard
SOQL. On an MCP surface, each row is one `DsarPolicyManager` operation.

## Pick the workflow (by the verb)

| Want to… | Run | Ends when |
|---|---|---|
| Set up / edit a policy tree | **A — Configure** | Bounded policy authored INACTIVE; or an unbounded request's cap is named / an under-specified one's decisions enumerated — and stops |
| Run an export for a subject | **B — Export** | Subject resolved to a root Id, run status read (running/completed/errored), file located on success — or, if still running after a couple polls, the user is asked whether to continue |
| See past runs | **C — History** | Prior runs reported from `DsarPolicyLog`, no run started |
| Find PII not yet covered | **D — Coverage gap** | Candidates surfaced with per-field reasons, disposition left to the admin — read-only |

Mixed request → do the one asked; don't add an export to a configure, or a run to a history.

**Every workflow below assumes call #1 is already done** — you have routed through the discover/
describe/dispatch SOR tool (or confirmed none is in reach). The `sf`/`salesforce-api-context`
commands in each workflow are the *no-routing-tool* spelling; with the routing tool present, dispatch
the equivalent operation through it.

## Workflow A — Configure

Recipe (metadata shape, relationship/field resolution, lifecycle transitions): `references/configure.md`.

1. **Classify first — short-circuit before any describe.** Three shapes; two never reach authoring:
   - **Unbounded** ("everything", "whole graph") — can't fit caps. Don't describe/walk. Write the
     **cap-refusal report** (call #3), stop.
   - **Under-specified** — delegates classification, no root/field named. Don't author a guess.
     Write the **elicitation report** (the admin's decisions; support **multiple roots**; proposals
     *pending disposition*), stop.
   - **Bounded & specified** — named roots/relationships/fields fitting the caps → continue.
2. **Confirm type + describe named objects only** (don't assume names, don't expand beyond what's named):
   ```bash
   sf org list metadata --metadata-type DsarPolicy --target-org <alias> --json
   sf sobject describe --sobject <NamedObject> --target-org <alias> --json
   ```
   If `DsarPolicy` can't be listed/described, surface it and stop (accepted terminal outcome).
3. **Validate the tree** (don't eyeball caps/names):
   ```bash
   python3 scripts/validate-policy-tree.py <tree.json>
   ```
   Checks children≤10, depth≤10, nodes≤200, and devname `[a-zA-Z]+[a-zA-Z0-9_]*`.
4. **Author metadata INACTIVE** under `${outputDir}`, faithful to the sanctioned strategy — add no
   unapproved path, drop none approved.
   > **Lifecycle gate:** INACTIVE to edit/delete, ACTIVE to execute. Change an ACTIVE policy by
   > **deactivate → edit → STOP**; get explicit user confirmation before reactivating (call #7).
5. **Deploy (best effort):** `sf project deploy start --source-dir <outputDir> --target-org <alias> --json`.
   Deploy may fail where the type isn't fully enabled — surface the raw error + prerequisite; don't
   fake success. The classification work is valid regardless.
6. **Report** the outcome reached — **cap-refusal** / **elicitation** / **authored** — per
   `references/report-format.md`. Never a truncated tree called "complete".

## Workflow B — Run an export

Endpoints, sample envelopes, poll/download sequence: `references/export-and-history.md`.

- **B0. Resolve the subject.** Requests arrive as **email / name / id**, not a `dataSubjectId`.
  Resolve to the **Id of a record whose type is a ROOT** of the chosen policy (Account / Contact /
  Individual / Lead / User) — e.g. SOQL `Lead`/`Contact` by `Email`. Confirm the type **is a policy
  root** (execute matches only the root subtree of the subject's type — a non-root subject exports
  nothing). On **0 / many / non-root** matches, stop and report; never execute a guessed Id.
- **B1. Preconditions.** Policy must be **ACTIVE** (else route to A). Resolve DSR routes via
  `salesforce-api-context`.
  - **Pick the policy deliberately:** named → use it; else the in-context policy; if none is
    established or **multiple ACTIVE could match**, **ask to confirm** (e.g. *"Run `<policy>` for
    `<subject>` — confirm?"*). Never pick silently.
  - **Access:** on `401`/`403`, name the guard and stop — user perm `Consent.CAN_EXECUTE_DSAR_POLICY`,
    org feature `Consent.hasDsarPortability`. State the poll-then-download ordering even on this
    error path (accepted terminal outcome; don't retry blindly).
- **B2. Consent gate + correct deletion framing (call #2).** If framed as deletion, correct it first
  (export, not erasure). If authorization is ambiguous, **ask** via `AskUserQuestion`; clear
  authorization → proceed.
- **B3. Execute — trust the envelope, not the HTTP code.** POST execute, capture the **run handle**.
  A failed run can return **HTTP 201** — read the envelope status; report failure if it says so.
- **B4. Poll ≈2–3×, then ask; download only after terminal (call #5).** Poll the handle (or
  `DsarPolicyLog.RequestStatus`). Early `NOT_FOUND` / "not ready" is expected. Still not terminal
  after a couple polls → **stop and ask** whether to keep polling; don't loop (non-terminal =
  downstream async, not this skill's to diagnose). Report **running / completed / errored**.
- **B5. Download (terminal-success only) — segment `dsr`.** A `dsar` segment 404s. Report where the
  export landed.
- **B6. Report** per `references/report-format.md`: resolved subject (id + type) and policy chosen
  (+ that you asked if ambiguous); consent confirmed; **export not deletion**; outcome from the
  envelope / run status in plain terms; file location on success; poll ordering explicit (couple of
  polls, file only after terminal, asked if still running). State the ordering even if preconditions
  blocked the run.

## Workflow C — History (a read)

```bash
sf data query --target-org <alias> \
  --query "SELECT Id, DsarPolicyId, RequestStatus, CreatedDate FROM DsarPolicyLog WHERE DsarPolicyId = '<POLICY_ID>' ORDER BY CreatedDate DESC"
```
Report prior runs (when, status); "no prior runs" is valid. On absent log / `401`/`403`/`404`,
surface the raw error + prerequisite. Don't execute the policy; don't use `installListView` / a UI list.

## Workflow D — Coverage gap analysis (read-only audit)

*"What personal data isn't covered yet?"* Read-only, deterministic — surfaces **candidates** for the
admin; classifies nothing, adds/activates nothing. Script + rubric: `references/gap-analysis-guide.md`;
mechanics: `references/gap-scan.md`.

1. **Open with the plain-language method line (call #8)** — one sentence in the user's terms: from
   the policy's objects, look **one level** out and flag fields that *may* be PII, **with a reason
   each**; the admin decides. Do **not** say "Workflow D", "coverage-gap audit", or "let me read the
   mechanics" — just state the approach in plain words and start.
2. **Read current coverage** (read-only) — gaps are relative to it.
3. **Scan one hop only, and cap the breadth** — describe each root + **at most ~5** of its
   most privacy-relevant one-hop objects; depth-1 default, don't recurse. **Never read a raw
   `--json` describe into the turn** — a full describe is ~100KB and the accumulated payloads
   overflow the event stream, truncating the run before it writes the report (the top failure here).
   Project every describe to `{name,type,label}` first (see `references/gap-scan.md`). If the
   policy/type can't be read (feature off — the accepted env path), **stop at a single projected
   root describe**; don't fan out. Write the report from the root + a couple of one-hop describes,
   name the objects you skipped, offer them via the depth gate. **The written report is the
   deliverable — draft it early and write it; don't gather everything first.**
4. **Flag candidates with a per-field reason** — compliance metadata > field type > name semantics.
   Never "this *is* PII" (call #3).
5. **Report transparently** — objects scanned, each candidate + reason, covered vs newly surfaced,
   and the **one-level limit** stated (even when empty).
6. **Gate depth** — go deeper only on explicit confirmation (warn: large output, heavy cost).
7. **Disposition, don't mutate** — ask which to add; adding routes to Workflow A (INACTIVE, stops for
   confirmation before reactivating — call #7).

## Quick rules & gotchas

| Situation | Do |
|---|---|
| **Starting ANY task (even a trivial "list/does-a-policy-exist" read)** | **FIRST** scan this run's tools for a discover/describe/dispatch routing tool (project-codey/Headless 360; any `mcp__<host>__…` name — match the verb shape). Present → `discover`/`describe`/`dispatch` the `DsarPolicyManager` SOR. Do NOT open with `sf` on reflex. `sf` only when no routing tool is in reach (`sf org list` for local auth is exempt) |
| "Capture everything / whole graph" | Exceeds caps (10/10/200) — name the cap, offer split/prune; don't walk the graph |
| "What PII are we missing?" | Workflow D — read-only depth-1; candidates + reason; disposition to admin; add/activate nothing |
| Subject given by email/name, no Id | Resolve first (B0): query the policy's root entities; confirm a root type; 0 / many / non-root → stop |
| Multiple ACTIVE policies could match | Confirm which with the user before running — never silent |
| Run stuck `In Progress` after a couple polls | Downstream async (Tool Factory / platform), not the skill's to diagnose — report *still running*, ask whether to keep polling; don't loop |
| getfile "not ready" / `NOT_FOUND` | Expected pre-terminal — poll again; not a failure |
| HTTP 201 on execute | Not success — read the envelope status |
| getfile 404 | Segment must be `dsr`, not `dsar` |
| Just edited an ACTIVE policy | Don't auto-reactivate — stop, report, get explicit confirmation (call #6) |
| `sf sobject describe DsarPolicy` empty | Tree is Metadata-API; only `DsarPolicyLog` answers SOQL |
| `DsarPolicy` type absent | Surface + stop; don't fabricate |
| `401`/`403`/`404` or missing type | Name the prerequisite and stop; no blind retries |

## Output (write to `${outputDir}/report.md`)

Report only the workflow you ran; each command once; the key result in the first screenful.
**Be concise** — state each load-bearing point (poll ordering, export-not-deletion, the
one-level limit) **once**, not restated across an intro, an aside, and a next-steps list; keep it
well under ~150 lines and don't paste exhaustive per-object dumps. On a preflight-error path (feature
/ policy / subject absent), name the blocker + prerequisite, state the ordering once, and stop —
short. Per-workflow contracts (incl. the INACTIVE / confirmed-reactivation lifecycle and the poll
ordering): `references/report-format.md`.

## Reference index

| File | When |
|---|---|
| `references/headless-sor.md` | MCP surface: discover→describe→dispatch the SOR, reject look-alikes, `sf` fallback |
| `references/configure.md` | Metadata shape, root/relationship resolution, `<tree.json>` input, lifecycle, multi-root |
| `references/export-and-history.md` | DSR execute/status/getfile routes, envelopes, poll sequence, `dsr` segment, history query |
| `references/report-format.md` | Per-workflow report contracts |
| `references/gap-analysis-guide.md` | Workflow D: audit script, steps, candidate-flagging rubric |
| `references/gap-scan.md` | Workflow D mechanics: one-hop enumeration, diff, depth gate, report shape |
| `scripts/validate-policy-tree.py` | Deterministic cap + devname check before authoring |
