#!/usr/bin/env bash
# poll-job.sh — poll a DataMaskPolicyJobRun, with a bounded timeout. Two modes:
#   terminal (default) — wait until the job REACHES a terminal state (used by Workflow A, run→report)
#   running            — wait until the job ENTERS the `running` state (used by Workflow B, abort)
#
# DataMaskPolicyJobRun is a STANDARD data-API object (unlike DataMaskPolicy, which is
# Tooling/MDAPI), so plain `sf data query` works here.
#
# Usage:
#   poll-job.sh <orgAlias> <jobRunId> [maxSeconds] [intervalSeconds]   # terminal mode (default)
#   POLL_MODE=running poll-job.sh <orgAlias> <jobRunId> [maxSeconds] [intervalSeconds]
# Defaults: maxSeconds=600, intervalSeconds=20
#
# WHY THESE DEFAULTS: Data Mask jobs run on a backend pool/scheduler with a ~5-10 minute floor —
# even a tiny (20-row) job typically does not reach a terminal state or emit detail rows for several
# minutes after the run starts. A short cap (e.g. 180s) gives up BEFORE the job can possibly finish,
# so the default cap is 600s (10 min) with a 20s interval to keep the query volume low. Do NOT poll
# on a tight (sub-10s) interval — it just burns tool calls against a job that cannot finish sooner.
#
# TERMINAL MODE: The parent DataMaskPolicyJobRun.Status can LAG the real job state (it may read
# `pending`/`running` for a while after masking finished). So this poller ALSO checks
# DataMaskPolicyJobRunDtl: once a `total_records_masked` detail row exists, the job is effectively
# done and we stop, even if the parent status hasn't caught up. Ground truth is the detail rows.
#
# RUNNING MODE (for abort): exits the instant the parent status reads `running` — the only state in
# which the abort endpoint accepts the request (a `pending`/`scheduled` job 409s). Because the pool
# floor delays the `running` window by minutes, poll with a modest interval (e.g. 15s). If the job
# races past `running` straight to a terminal state before we catch it, that window is gone and the
# abort would be pointless — the poller reports the terminal status and exits 3 so the caller can
# start a fresh run rather than abort a job that already finished.
#
# Exit codes:
#   terminal mode: 0 = terminal status OR masked-count detail row observed (signal on stdout);
#                  1 = timed out; 2 = bad args.
#   running mode:  0 = `running` observed (prints `running`); 1 = timed out; 2 = bad args;
#                  3 = job reached a terminal state before `running` was seen (prints that status).

set -euo pipefail

ORG="${1:-}"
JOB_ID="${2:-}"
MAX_SECONDS="${3:-600}"
INTERVAL="${4:-20}"
POLL_MODE="${POLL_MODE:-terminal}"

if [[ -z "$ORG" || -z "$JOB_ID" ]]; then
  echo "usage: [POLL_MODE=running] poll-job.sh <orgAlias> <jobRunId> [maxSeconds] [intervalSeconds]" >&2
  exit 2
fi

case "$POLL_MODE" in
  terminal|running) ;;
  *) echo "poll-job: POLL_MODE must be 'terminal' or 'running' (got '${POLL_MODE}')" >&2; exit 2 ;;
esac

# Terminal statuses (incl. canceled after an abort). scheduled/running/pending are NOT terminal.
is_terminal() {
  case "$1" in
    completed|completed_with_errors|failed|canceled) return 0 ;;
    *) return 1 ;;
  esac
}

elapsed=0
while (( elapsed < MAX_SECONDS )); do
  status="$(
    sf data query --target-org "$ORG" \
      --query "SELECT Status FROM DataMaskPolicyJobRun WHERE Id = '${JOB_ID}'" \
      --json 2>/dev/null \
    | python3 -c "import json,sys; r=json.load(sys.stdin).get('result',{}).get('records',[]); print(r[0]['Status'] if r else 'UNKNOWN')"
  )"
  echo "[poll-job] ${JOB_ID} status=${status} (${elapsed}s/${MAX_SECONDS}s) mode=${POLL_MODE}"

  if [[ "$POLL_MODE" == "running" ]]; then
    # Abort window: stop the instant the job is `running` (the only abortable state).
    if [[ "$status" == "running" ]]; then
      echo "running"
      exit 0
    fi
    # If it slipped past `running` to a terminal state, the abort window is gone — signal the caller.
    if is_terminal "$status"; then
      echo "[poll-job] job reached terminal '${status}' before 'running' was observed — abort window missed" >&2
      echo "$status"
      exit 3
    fi
  else
    if is_terminal "$status"; then
      echo "$status"
      exit 0
    fi

    # Ground-truth check: a masked-count detail row means the job finished even if the parent lags.
    masked="$(
      sf data query --target-org "$ORG" \
        --query "SELECT Value FROM DataMaskPolicyJobRunDtl WHERE DataMaskPolicyJobRunId = '${JOB_ID}' AND Subtype = 'total_records_masked'" \
        --json 2>/dev/null \
      | python3 -c "import json,sys; r=json.load(sys.stdin).get('result',{}).get('records',[]); print(r[0]['Value'] if r else '')"
    )"
    if [[ -n "$masked" ]]; then
      echo "[poll-job] detail row total_records_masked=${masked} — job effectively complete (parent status=${status})"
      echo "completed"
      exit 0
    fi
  fi

  sleep "$INTERVAL"
  elapsed=$(( elapsed + INTERVAL ))
done

if [[ "$POLL_MODE" == "running" ]]; then
  echo "[poll-job] TIMEOUT after ${MAX_SECONDS}s — job never reached 'running'" >&2
else
  echo "[poll-job] TIMEOUT after ${MAX_SECONDS}s — neither terminal status nor masked-count detail row observed" >&2
fi
exit 1
