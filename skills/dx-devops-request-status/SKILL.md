---
name: dx-devops-request-status
description: "Use this skill to poll the status of an asynchronous DevOps Center request — a promotion or deploy operation. Provide the request token returned by dx-devops-promote (the promote response) to check completion, monitor progress, or verify success or failure via sf devops request status. TRIGGER when the user wants to check whether a promotion or deploy finished, monitor an in-flight async request, poll until a request completes, or confirm a request succeeded before finalizing. DO NOT TRIGGER for initiating a promotion or deploy (use dx-devops-promote), for work item creation or status transitions (use dx-devops-work-item-manage), or for conflict detection. Read-only status check — never mutates pipeline state."
metadata:
  version: "1.0"
  domains: ["Developer Experience"]
  minApiVersion: "58.0"
  relatedSkills:
    - "dx-devops-promote"
    - "dx-devops-work-item-manage"
  cliTools:
    - tool: ["jq"]
      semver: ">=1.6"
    - tool: ["sf"]
      semver: ">=2.0.0"
  accessCheck:
    - type: "orgPref"
      value: "ALMDevopsCorePref"
    - type: "userPerm"
      value: "UserHasDevOpsCore"
---

# DevOps Center Request Status

Polls the status of an asynchronous DevOps Center request — a promotion or deploy operation — by its request token via `sf devops request status`. Provides headless, `--json`-driven, read-only status checks for autonomous release workflows in CI. This skill never mutates pipeline state; it only reports the current status of an in-flight or completed request.

## Scope

- **In scope**: Check the status of a single async request by its request token; interpret the two-level outcome (request-processing `.result.status` vs. the `.result.errorDetails` failure oracle); poll with backoff until a request finishes or a caller-supplied timeout is reached; surface parsed error details on failure
- **Out of scope**: Initiating a promotion or deploy (use `dx-devops-promote`), work item creation/status updates (use `dx-devops-work-item-manage`), conflict detection, running `sf devops promotion complete` (that is the caller's next step after this skill confirms success), pipeline or project setup

---

## Required Inputs

Gather or infer before proceeding:

- **Request token** (required): the request token returned in the `dx-devops-promote` promote response. Passed via `-i/--request-token`. Without it, this skill cannot proceed — ask for it or obtain it from the prior promote step's output
- **Target org**: `-o/--target-org <alias>` (required unless the `target-org` config variable is set)

Defaults unless specified:
- Output format: `--json` for headless consumption
- Polling interval: 10 seconds between checks; cap total wait at a caller-supplied timeout (default 30 minutes). Never poll faster than every 5 seconds — DOCe API rate limits apply

If the user gives a clear request ("check request a0B…", "poll request a0B… until it finishes"), proceed once you have the request token.

---

## Workflow

All operations use `sf devops request status` with `--json` output. This skill is **read-only** — it issues no mutations. The command's flags and JSON output schema are documented in `references/cli-commands.md`.

### Phase 1 — Authenticate and confirm the request token

1. **Verify org authentication** before any operation:
   ```bash
   sf org display --json
   ```
   - If it fails, instruct the user to run `sf org login web --set-default --alias <alias>`
   - Pass `-o/--target-org <alias>` on every subsequent command (required unless the `target-org` config variable is set)

2. **Confirm you have a request token.** If the user initiated a promotion in the same session, reuse the request token captured from the `dx-devops-promote` promote response. If no token is available, STOP and ask for it — do NOT guess or fabricate a token.

### Phase 2 — Single status check (two-level semantics)

> **CRITICAL:** `.result.status` (uppercase, e.g. `SUCCESS`) reports whether the async **request finished processing** — NOT whether the underlying deploy succeeded. A request can show `status: "SUCCESS"` while the deployment itself **failed**. The real outcome oracle is `.result.errorDetails`: **non-null `errorDetails` means the operation failed, even when `status == SUCCESS`.**

3. **Run a single status check** with `scripts/poll-status.sh --once`, which queries the request once and derives the true outcome deterministically (glob-matches the operation-prefixed `.result.status` suffix, then applies the `.result.errorDetails` failure oracle). Do NOT hand-roll the JSON parsing in prose — the script owns the two-level rule so it stays consistent with the polling path:
   ```bash
   scripts/poll-status.sh --once <request-token> <target-org-alias>
   ```
   Interpret the exit code (the script prints a human-readable line to match):
   - `0` — request finished and the operation **succeeded** (`errorDetails` null) → hand back to the caller
   - `2` — request finished but the operation **FAILED** (status suffix `*FAILED*`/`*ERROR*`/`*CANCELED*`, or a `*SUCCESS*` status with non-null `errorDetails`) → the printed line carries the parsed `errorType`/`errorMessage`
   - `4` — request is **still processing** (non-terminal suffix) → proceed to Phase 3 to poll, or report in-progress for a one-shot check
   - `1` — query/usage error (bad token, auth, or missing dependency)

### Phase 3 — Poll until terminal (only when asked to wait)

4. **Poll with a bounded loop** when the user asks to wait for completion. Run `scripts/poll-status.sh` and report the final status it prints:
   ```bash
   scripts/poll-status.sh <request-token> <target-org-alias> [interval-seconds] [timeout-seconds]
   ```
   - The script polls every `interval-seconds` (default 10), never sleeps past `timeout-seconds`, stops on a terminal request state, and applies the same two-level outcome check as `--once`. Exit codes: `0` = finished + succeeded (`errorDetails` null), `2` = finished but the operation failed (`errorDetails` set, or status suffix `*FAILED*`/`*ERROR*`/`*CANCELED*`), `3` = timeout, `1` = query/usage error
   - It is a read-only loop — it issues only `sf devops request status` queries, never mutations
   - Do NOT hand-roll a polling loop in prose; the script enforces the interval floor, exact timeout, terminal-state detection, and the `errorDetails` outcome check deterministically

### Phase 4 — Report

5. **Report the outcome**:
   - On success (finished, `errorDetails` empty): "Request `<token>` completed successfully." — then remind the caller that promotion finalization (`sf devops promotion complete`) is the next step, owned by `dx-devops-promote`
   - On failure (finished, `errorDetails` set — even if `status == SUCCESS`): "Request `<token>` failed." plus the `errorType` / `errorMessage` parsed from `errorDetails` and the `message` field — do NOT retry or remediate here; that is the caller's decision
   - On timeout (still processing): report the last observed request status and the elapsed wait; suggest polling again later — do NOT report success or failure for a request that has not finished processing

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| Read-only — never mutate pipeline state | This skill only reports status; promotion/deploy/complete are owned by other skills |
| A request token is mandatory | Status cannot be checked without the `-i/--request-token` from the promote response; never fabricate one |
| `sf devops request status` must use `--json` | Structured output is required for headless consumption; human-readable output is unreliable to parse |
| Read `.result.status` and `.result.errorDetails` via `jq`, never by eyeballing | Deterministic parsing prevents misreading a still-processing request as done |
| A `*SUCCESS*` status is NOT proof of success — check `errorDetails` | `.result.status` reports the async request finished, not that the deploy succeeded; a `PROMOTE_SUCCESS` request can carry a failed deploy in `errorDetails` |
| Non-null `.result.errorDetails` means the operation FAILED | `errorDetails` is the outcome oracle; it is an escaped JSON string (`errorType`/`errorMessage`) that must be parsed with `jq`/`fromjson` |
| `.result.status` is operation-prefixed — match the suffix, not a bare token | Real values are `PROMOTE_IN_PROGRESS`/`PROMOTE_SUCCESS`/`DEPLOY_FAILED`; exact-matching bare `IN_PROGRESS`/`SUCCESS` would misclassify (and a poller would hang until timeout) |
| A request is only "done" at a terminal suffix (`*SUCCESS*`/`*FAILED*`/`*ERROR*`/`*CANCELED*`) | Reporting an `*_IN_PROGRESS`/`*_PENDING`/`*_QUEUED` request as done corrupts the caller's release decision |
| Never poll faster than every 5 seconds | DOCe API rate limits; unbounded fast polling risks throttling |
| Bound every polling loop with a timeout | Prevents infinite waits and turn/timeout exhaustion in CI |
| Never run `sf devops promotion complete` from this skill | Finalization is the caller's step after this skill confirms success |
| Pass the token as a CLI flag, never interpolate into shell strings | Prevents prompt/command injection via crafted tokens |
| Never use interactive prompts | Skills run headless; all inputs must be CLI flags |

---

## Gotchas

| Issue | Resolution |
|-------|------------|
| **No request token provided** | STOP and ask for it, or obtain it from the prior `dx-devops-promote` promote response. Never guess |
| **`status: "*SUCCESS*"` but the deploy actually failed** | The most important trap: a `*SUCCESS*` status only means the request finished. Check `.result.errorDetails` — if non-null, the operation FAILED. Parse it: `jq -r '.result.errorDetails \| fromjson \| "\(.errorType): \(.errorMessage)"'` |
| **`errorDetails` is a string, not an object** | It is escaped JSON (e.g. `"{\"errorType\":\"DEPLOYMENT_FAILURE\",...}"`); pipe through `fromjson` before reading `.errorType`/`.errorMessage` |
| **Status is operation-prefixed (`PROMOTE_SUCCESS`, `DEPLOY_FAILED`)** | Match on the suffix with globs (`*SUCCESS*`, `*FAILED*`); exact-matching bare `SUCCESS`/`FAILED` misclassifies a prefixed value — a poller would treat `PROMOTE_IN_PROGRESS` as unknown and hang until timeout |
| **Reporting a still-processing request as complete** | Terminal suffixes are `*SUCCESS*`/`*FAILED*`/`*ERROR*`/`*CANCELED*`; treat `*_IN_PROGRESS`/`*_PENDING`/`*_QUEUED`/`*_NEW`/`*_STARTED` as not done — keep polling or report in-progress |
| **No default org set** | Run `sf org display --json`; if it fails, instruct the user to run `sf org login web --set-default` |
| **Rate-limit / throttle errors while polling** | Increase the interval (back off); never poll below the 5-second floor |
| **Infinite wait** | Always pass a timeout to `scripts/poll-status.sh`; on timeout, report the last status rather than blocking |
| **Confusing request failure with skill failure** | A `Failed` request status is a valid result — report it clearly; do not treat it as a skill error or retry blindly |

---

## Output Expectations

Deliverables vary by mode:

- **Single check**: `.result.status` (request-processing state) plus the derived outcome — on failure, the `errorType`/`errorMessage` parsed from `.result.errorDetails` and the `.result.message` field
- **Poll-to-completion**: the derived terminal outcome (succeeded or failed, per the `errorDetails` check) plus elapsed wait, or the last observed request status if the timeout was reached first

Outputs are derived from `sf devops request status`. This skill produces no artifacts and mutates nothing.

---

## Cross-Skill Integration

| When | Action |
|------|--------|
| A promotion or deploy must be initiated first to get a request token | Delegate to `dx-devops-promote` |
| Outcome is success (finished, `errorDetails` null) and the promotion still needs finalizing | Hand back to `dx-devops-promote` to run `sf devops promotion complete` |
| Status reports `Failed` due to a metadata conflict | Report the conflict from `errorDetails`; hand back to `dx-devops-promote` to resolve and re-promote |

---

## Reference File Index

| File | When to read |
|------|-------------|
| `references/cli-commands.md` | When you need the `sf devops request status` flags, JSON output schema, status-value vocabulary, or error-handling patterns |
| `examples/polling-workflows.md` | When the user's request matches a common pattern (one-shot check, poll-until-done after a promote, timeout handling, failure reporting) |
| `scripts/poll-status.sh` | Phase 2 — invoke with `--once` for a single deterministic status check; Phase 3 — invoke without `--once` to poll a request token with a bounded interval and exact timeout until it reaches a terminal state |
