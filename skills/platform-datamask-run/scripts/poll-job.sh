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
# TERMINAL MODE: exits only on a terminal PARENT status. A `total_records_masked` detail row is NOT a
# completion signal: it can already exist, reading `0`, while the parent is still `running`, so
# stopping on the first row reports a count for a job that has not finished. Read the detail rows
# only AFTER this script exits.
#
# RUNNING MODE (for abort): exits the instant the parent status reads `running` — the only state in
# which the abort endpoint accepts the request (a `pending`/`scheduled` job 409s). Because the pool
# floor delays the `running` window by minutes, poll with a modest interval (e.g. 15s). If the job
# races past `running` straight to a terminal state before we catch it, that window is gone and the
# abort would be pointless — the poller reports the terminal status and exits 3 so the caller can
# report the missed window instead of aborting a job that already finished. Exit 3 is NOT a cue to
# start a replacement run; that needs an explicit user request.
#
# Exit codes:
#   terminal mode: 0 = terminal parent status observed (printed on stdout);
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

# JOB_ID is interpolated into a SOQL string below, so it must be a bare Salesforce Id — never let
# quotes or SOQL fragments through. ORG is passed to the CLI, so keep it to a plain alias/username.
if [[ ! "$JOB_ID" =~ ^[a-zA-Z0-9]{15,18}$ ]]; then
  echo "poll-job: Invalid Salesforce ID '${JOB_ID}' (expected 15 or 18 alphanumeric characters)" >&2
  exit 2
fi
if [[ ! "$ORG" =~ ^[a-zA-Z0-9][a-zA-Z0-9._@+-]*$ ]]; then
  echo "poll-job: Invalid org alias or username '${ORG}'" >&2
  exit 2
fi

# Bound the loop: an unbounded or sub-5s poll hammers the org, and a non-numeric cap breaks (( )).
if [[ ! "$MAX_SECONDS" =~ ^[0-9]+$ ]] || (( MAX_SECONDS < 10 || MAX_SECONDS > 3600 )); then
  echo "poll-job: maxSeconds must be an integer between 10 and 3600 (got '${MAX_SECONDS}')" >&2
  exit 2
fi
if [[ ! "$INTERVAL" =~ ^[0-9]+$ ]] || (( INTERVAL < 5 )); then
  echo "poll-job: intervalSeconds must be an integer >= 5 (got '${INTERVAL}')" >&2
  exit 2
fi

# Terminal statuses (incl. canceled after an abort). scheduled/running/pending are NOT terminal.
is_terminal() {
  case "$1" in
    completed|completed_with_errors|failed|canceled) return 0 ;;
    *) return 1 ;;
  esac
}

# Wall-clock elapsed, not a sum of sleeps: each query itself takes seconds, so summing intervals
# would let the real runtime overshoot the cap.
start_ts=$(date +%s)
elapsed=0
while (( elapsed < MAX_SECONDS )); do
  # CSV is a header line then one value per row, so bash can read it with no pipe and no
  # post-processor. stderr is left attached so an auth or alias failure is visible; a failed
  # query only skips this tick, it does not end the poll.
  csv="$(sf data query --target-org "$ORG" \
    --query "SELECT Status FROM DataMaskPolicyJobRun WHERE Id = '${JOB_ID}'" \
    --result-format csv)" || csv=""
  status=""
  { IFS= read -r _; IFS= read -r status; } <<< "$csv" || true
  status="${status:-UNKNOWN}"
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
  fi

  sleep "$INTERVAL"
  elapsed=$(( $(date +%s) - start_ts ))
done

if [[ "$POLL_MODE" == "running" ]]; then
  echo "[poll-job] TIMEOUT after ${MAX_SECONDS}s — job never reached 'running'" >&2
else
  echo "[poll-job] TIMEOUT after ${MAX_SECONDS}s — job never reached a terminal status" >&2
fi
exit 1
