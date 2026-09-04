# Run an export & read history — reference

Deep detail for **Workflow B** (export) and **Workflow C** (history). Judgment (export-not-erasure,
consent, poll-before-download) lives in `SKILL.md`; this file is the mechanics.

## Resolve the DSR routes at run time

The execute / status / getfile routes are Connect DSR endpoints. Resolve them against the running
org — do not hardcode a version segment.

```text
salesforce-api-context   # MCP: resolve the current DSR execute/status/getfile routes + API version
```

Or discover via `sf`:

```bash
sf api request rest '/services/data' --target-org <alias>        # available API versions
```

## Resolve the subject (B0) — before anything else

A portability request names the subject by **email / name / external id**, not a `dataSubjectId`.
Resolve it to a record whose entity type is a **ROOT** of the policy you will run
(Account / Contact / Individual / Lead / User). Query the roots for the identifier, e.g.:

```bash
sf data query --target-org <alias> \
  --query "SELECT Id, Name, Email FROM Lead WHERE Email = '<subject-email>'"
```

Confirm the match is a **root type of the chosen policy** — execute matches only the root subtree of
the subject's type, so a subject whose type is not a policy root exports nothing. On **0 matches,
multiple matches, or a non-root type**, stop and report — never execute against a guessed Id.

## Pick the policy

If the request names a policy, use it; if not, use the policy established in the working context. If
none is established or **more than one ACTIVE policy could match the subject**, ask the user to
confirm which to run (surface the best match as a confirmation) before executing — never pick
silently.

## Preconditions

- Policy must be **ACTIVE** (INACTIVE cannot execute — route to Workflow A to activate).
- Run guards (name the missing one and stop on `401`/`403`; do not loop):
  - user permission `Consent.CAN_EXECUTE_DSAR_POLICY`
  - org feature `Consent.hasDsarPortability`

## Execute — capture the handle, trust the envelope

```bash
sf api request rest '<DSR_EXECUTE_ROUTE>' --method POST \
  --body '{"policy":"<POLICY_DEVNAME>","subject":"<SUBJECT_IDENTIFIER>"}' \
  --target-org <alias>
```

- Capture the **run handle** from the response — you need it for both status and getfile.
- **A failed run can return HTTP 201.** The real outcome is the **status field inside the
  envelope**, not the HTTP code. Parse the body; if it reports failure, report failure.
- This is an **export**, not a deletion. It produces a file; it removes nothing. If the request
  framed it as erasure, you have already corrected that (SKILL.md call #1) before reaching here.

Example failure envelope on a 201:

```json
{ "status": "FAILED", "message": "…", "runId": "…" }   // HTTP 201, but FAILED — report the failure
```

## Poll a couple of times — then ask; download only after terminal

Poll the **same handle** (or `DsarPolicyLog.RequestStatus` for the run) for a terminal status
(`COMPLETED` / `FAILED` or the org's equivalents). Only a terminal-success run has a downloadable
file.

```bash
sf api request rest '<DSR_STATUS_ROUTE_FOR_HANDLE>' --method GET --target-org <alias>
# or, by handle, over the run log:
sf data query --target-org <alias> \
  --query "SELECT Id, RequestStatus, CompletionDatetime, DsarError FROM DsarPolicyLog WHERE Id = '<handle>'"
```

Poll a **small, fixed number of times** (≈2–3). If the run is still not terminal, **stop and ask the
user whether to keep polling** — do **not** loop to terminal. A run can sit non-terminal
indefinitely on downstream async processing; **that is platform / Tool Factory territory, not this
skill's to diagnose or reach into** (don't go hunting message-queue internals). Report the status in
plain terms — **running / completed / errored** — from the run row; the user does not need to know
which internal entity or queue backs it.

**Do not quote a completion time (e.g. "~1s") — even if a data source suggests one.** Runtime
varies by org provisioning; poll to terminal or hand off the handle. Never promise a duration.

An early *getfile* returns `NOT_FOUND` / `"This file isn't ready yet"`. **That is the contract
working, not a failure** — poll again; do not treat it as a completed or errored run.

## Download the export file — segment is `dsr`

Only after terminal-success:

```bash
sf api request rest '<DSR_GETFILE_ROUTE_FOR_HANDLE>' --method GET --target-org <alias>
```

- The getfile path segment is **`dsr`**, not `dsar`. A `dsar` segment 404s. Double-check the
  segment before concluding the file is missing.
- Report where the export landed.

## Workflow C — history is a SOQL read

Run history lives in `DsarPolicyLog`, a standard object. Read it with SOQL — it is **not** an
`installListView` call, not a UI list, and it **never** starts a run.

```bash
sf data query --target-org <alias> \
  --query "SELECT Id, DsarPolicyId, RequestStatus, CreatedDate, CompletionDatetime \
           FROM DsarPolicyLog \
           WHERE DsarPolicyId = '<POLICY_ID>' \
           ORDER BY CreatedDate DESC"
```

- Report each prior run (when it ran, its status). "No prior runs" is a valid, correct result.
- If `DsarPolicyLog` is absent or the query returns `401`/`403`/`404`, surface the raw error and
  name the prerequisite — an accepted terminal outcome. Do not fall back to executing the policy.
