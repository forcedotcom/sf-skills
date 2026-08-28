# Request Status Polling Examples

Common patterns for checking the status of an asynchronous DevOps Center request via `sf devops request status`. Every pattern is **read-only** — it issues only status queries and never mutates pipeline state. The request token is returned by `dx-devops-promote` in the promote response.

---

## Example 1 — One-shot status check (with the two-level outcome check)

**User prompt:** "What's the status of request 708b2286-bbf3-4621-9531-6d94334ff763?"

```bash
# 1. Verify auth
sf org display --json

# 2. Single deterministic status check. --once queries once and derives the TRUE
#    outcome (.result.status alone is not enough — the status is operation-prefixed
#    and a *SUCCESS* status can carry a failed deploy in errorDetails). The script
#    owns the two-level rule so it stays consistent with the polling path.
scripts/poll-status.sh --once 708b2286-bbf3-4621-9531-6d94334ff763 my-devops-org
# Exit codes: 0 succeeded · 2 operation failed · 4 still processing · 1 query error
```

For the real response above, `status` is a `*SUCCESS*` value but `errorDetails` is populated, so the script exits `2` and prints the derived failure: **`DEPLOYMENT_FAILURE: classes/HelloMCP.cls-meta.xml: Invalid api version:0.0`**.

**Report:** "Request `708b2286…` finished but the deploy FAILED — `DEPLOYMENT_FAILURE`: invalid API version on `HelloMCP.cls-meta.xml`." Never report success from a `*SUCCESS*` status alone.

---

## Example 2 — Poll until the request completes

**User prompt:** "Poll request a0B000000000200 until it finishes."

```bash
# scripts/poll-status.sh polls every 10s (default), caps at 30 min (default),
# stops on a terminal state, and exits non-zero on failure or timeout.
scripts/poll-status.sh a0B000000000200 my-devops-org
# Custom interval/timeout: scripts/poll-status.sh a0B000000000200 my-devops-org 15 900
```

The script prints progress lines while polling and a final line. It applies the two-level outcome check (request-finished AND `errorDetails` null). Exit codes:
- `0` — request finished and the operation succeeded (`errorDetails` null)
- `2` — request finished but the operation FAILED (`errorDetails` set, or status suffix `*FAILED*`/`*ERROR*`/`*CANCELED*`) — reason printed to stderr
- `3` — timeout reached, still processing

**Report:** on exit `0`, "Request `a0B000000000200` completed successfully. Run `sf devops promotion complete` to finalize (owned by `dx-devops-promote`)."

---

## Example 3 — Hand-off from a promotion

**Scenario:** `dx-devops-promote` initiated a promotion and returned a request token. Confirm completion before finalizing.

```bash
# REQUEST_TOKEN was captured by dx-devops-promote from the promote response.

# Poll it to a terminal state.
if scripts/poll-status.sh "$REQUEST_TOKEN" my-devops-org; then
  echo "Request $REQUEST_TOKEN succeeded — ready to finalize."
  # Finalization is the caller's step (dx-devops-promote), NOT this skill:
  #   sf devops promotion complete --target-stage-id <target-stage-id> --target-org my-devops-org --json
else
  echo "Request $REQUEST_TOKEN did not succeed — see status output above." >&2
fi
```

**Report:** relay the terminal status. Do not run `promotion complete` from this skill — hand back to `dx-devops-promote`.

---

## Example 4 — Timeout while still processing

**User prompt:** "Check request a0B000000000300, wait up to 5 minutes."

```bash
# 300s timeout, 15s interval
scripts/poll-status.sh a0B000000000300 my-devops-org 15 300
# Exit code 3 means the request was still processing at the 5-minute cap.
```

**Report:** "Request `a0B000000000300` was still in progress (e.g. `PROMOTE_IN_PROGRESS`) after 5 minutes. It has not failed — poll again later to confirm completion." Do NOT report success or failure for a request that has not finished processing.

---

## Example 5 — Failed operation vs. failed query

**Scenario:** distinguish a failed *query* (bad token / auth) from a failed *operation* (request finished, but `errorDetails` set).

```bash
# The exit code distinguishes the two failure modes: 1 = the QUERY failed (bad
# token / auth), 2 = the query succeeded but the OPERATION failed (errorDetails
# set, even when .result.status is a *SUCCESS* value).
scripts/poll-status.sh --once a0B000000000400 my-devops-org
case $? in
  1) echo "Query itself failed — check the request token and org auth." >&2 ;;
  2) echo "Operation failed — see the parsed errorType/errorMessage above." ;;
  0) echo "Operation succeeded." ;;
  4) echo "Still processing — poll to completion (Example 2)." ;;
esac
```

**Report:** a failed operation (non-null `errorDetails`) is a valid result — report the parsed `errorType`/`errorMessage`. If it failed on a metadata conflict, hand back to `dx-devops-promote` to resolve and re-promote.
