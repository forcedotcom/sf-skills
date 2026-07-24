#!/usr/bin/env bash
#
# check_expiration.sh — Report when Salesforce orgs expire, prioritized by urgency.
#
# Determines expiration from the authoritative source per org kind:
#   - Trial / Developer Edition orgs: Organization.TrialExpirationDate (SOQL).
#     Null for paid/production orgs, which report "no trial expiration".
#   - Scratch orgs: the expirationDate reported by `sf org list`.
#
# Output is sorted soonest-first (already-expired first) and grouped by
# urgency, with a one-line summary. Structured --json / --csv output is
# available for dashboards, alerts, and cron. Optional guidance:
#   --preserve  print commands to back up an at-risk org before it lapses
#   --renew     print how to extend / reactivate a trial or DE org
#   --fail-if-expiring [N]  exit non-zero if any org expires within N days
#                           (default 7) — for cron / CI gating
#
# Usage:
#   check_expiration.sh [org-alias-or-username]     # one org
#   check_expiration.sh --all                       # every authenticated org
#   check_expiration.sh                             # default org (target-org)
#   check_expiration.sh --all --within 30           # expiring within 30 days
#   check_expiration.sh --all --json                # machine-readable
#   check_expiration.sh --all --fail-if-expiring 7  # cron watchdog
#
# Options:
#   --all, -a               Check every authenticated org.
#   --within <days>, -w     Only show orgs expiring within <days> days
#                           (includes already-expired; omits paid/production).
#   --json                  Emit a JSON array of org records (data only).
#   --csv                   Emit CSV rows (data only).
#   --preserve              Print backup commands for expiring/expired orgs.
#   --renew                 Print trial/DE extension & reactivation guidance.
#   --fail-if-expiring[=N]  Exit 3 if any org expires within N days (default 7).
#   --no-scratch            Exclude scratch orgs (trial/DE only).
#   --help, -h              Show this help.
#
# Exit codes:
#   0  success
#   1  an org could not be queried (auth/connection error)
#   2  bad usage / missing dependency (sf or jq)
#   3  --fail-if-expiring threshold breached (at least one org expiring)

set -uo pipefail

die() { echo "Error: $*" >&2; exit 2; }

command -v sf >/dev/null 2>&1 || die "Salesforce CLI ('sf') not found on PATH."
command -v jq >/dev/null 2>&1 || die "'jq' not found on PATH."

SEP="$(printf '\037')"      # US (unit separator): non-whitespace so empty
                            # fields are preserved by `read` (a whitespace IFS
                            # like TAB collapses runs, dropping empty columns).

# Sentinels used so records sort predictably by "days remaining" (ascending):
#   real days (negative = expired) sort first, then unparseable-date, then
#   no-expiration, then auth errors. Distinct values keep same-group records
#   contiguous so group headers are never duplicated.
DATEONLY_DAYS=999999997     # a date exists but could not be parsed
NO_EXP_DAYS=999999998       # paid/production (no TrialExpirationDate)
AUTH_DAYS=999999999         # org could not be queried
SENTINEL_MIN=999999997      # daysRemaining >= this is a sentinel, not real
SOON_DAYS=7                 # threshold for the "expiring soon" warning

# --- option state --------------------------------------------------------
MODE=""                     # "all" | "" (single/default)
TARGET=""                   # org alias/username for single mode
WITHIN_DAYS=""              # display filter (empty = show everything)
WITHIN_SEEN=0               # whether --within was passed (to reject empty value)
FAIL_SEEN=0                 # whether --fail-if-expiring was passed
OUTPUT="human"              # human | json | csv
DO_PRESERVE=0
DO_RENEW=0
FAIL_WITHIN=""              # --fail-if-expiring threshold (empty = off)
INCLUDE_SCRATCH=1           # scratch orgs included by default (--no-scratch off)

# --- run state -----------------------------------------------------------
RECORDS=""                  # accumulated TSV rows (one org per line)
HAD_AUTH_ERR=0
MATCH_COUNT=0
# compute() outputs:
DAYS=""
STATUS=""

usage() {
  sed -n '2,/^set -uo/p' "$0" | sed '/^set -uo/d; s/^# \{0,1\}//; s/^#//'
}

# --- date helpers (macOS/BSD and GNU/Linux) ------------------------------
now_epoch() { date "+%s"; }

# Convert an ISO-ish date (YYYY-MM-DD[ T...]) to epoch seconds.
date_to_epoch() {
  local d="$1"
  d="${d%%T*}"; d="${d%% *}"
  [ -z "$d" ] && return 1
  if date -j >/dev/null 2>&1; then
    date -j -f "%Y-%m-%d" "$d" "+%s" 2>/dev/null      # BSD/macOS
  else
    date -d "$d" "+%s" 2>/dev/null                    # GNU/Linux
  fi
}

# Given a date, set DAYS (integer; negative = expired) and STATUS.
# Sets STATUS=DATEONLY / DAYS=NO_EXP_DAYS when the date cannot be parsed.
compute() {
  local d="$1" epoch now
  epoch="$(date_to_epoch "$d")"
  if [ -z "$epoch" ]; then DAYS="$DATEONLY_DAYS"; STATUS="DATEONLY"; return 0; fi
  now="$(now_epoch)"
  DAYS=$(( (epoch - now) / 86400 ))
  if   [ "$DAYS" -lt 0 ];            then STATUS="EXPIRED"
  elif [ "$DAYS" -le "$SOON_DAYS" ]; then STATUS="SOON"
  else                                    STATUS="OK"
  fi
}

# Append a record. Args: days label kind exp status orgid errname errmsg
add_rec() {
  RECORDS="${RECORDS}$(printf '%s\037%s\037%s\037%s\037%s\037%s\037%s\037%s' \
    "$1" "$2" "$3" "$4" "$5" "$6" "$7" "$8")
"
}

# --- collection ----------------------------------------------------------
# Determine expiration for one org and record it.
# Args: label isScratch(true|false) listExpirationDate listOrgId
collect_one() {
  local label="$1" is_scratch="$2" list_exp="$3" orgid="$4"

  if [ "$is_scratch" = "true" ]; then
    local d="${list_exp%%T*}"; d="${d%% *}"
    if [ -z "$d" ] || [ "$d" = "null" ]; then
      add_rec "$NO_EXP_DAYS" "$label" "scratch" "" "NONE" "$orgid" "" ""
    else
      compute "$d"
      add_rec "$DAYS" "$label" "scratch" "$d" "$STATUS" "$orgid" "" ""
    fi
    return 0
  fi

  # Non-scratch: TrialExpirationDate is authoritative (null = paid/production).
  local out rc
  out="$(sf data query \
      --query "SELECT Id, TrialExpirationDate FROM Organization" \
      --target-org "$label" --json 2>/dev/null)"
  rc=$?
  if [ "$rc" -ne 0 ]; then
    local en em
    en="$(printf '%s' "$out" | jq -r '.name // empty' 2>/dev/null)"
    em="$(printf '%s' "$out" | jq -r '.message // empty' 2>/dev/null | tr '\t\n' '  ')"
    add_rec "$AUTH_DAYS" "$label" "unknown" "" "AUTH_ERROR" "" "$en" "$em"
    HAD_AUTH_ERR=1
    return 1
  fi

  local id texp
  id="$(printf '%s' "$out"   | jq -r '.result.records[0].Id // empty')"
  texp="$(printf '%s' "$out" | jq -r '.result.records[0].TrialExpirationDate // empty')"
  [ -n "$id" ] && orgid="$id"

  if [ -z "$texp" ] || [ "$texp" = "null" ]; then
    add_rec "$NO_EXP_DAYS" "$label" "paid" "" "NONE" "$orgid" "" ""
  else
    local d="${texp%%T*}"; d="${d%% *}"
    compute "$d"
    add_rec "$DAYS" "$label" "trial" "$d" "$STATUS" "$orgid" "" ""
  fi
  return 0
}

# Build a TSV table of authenticated orgs from `sf org list`.
# Columns: label  username  isScratch  expirationDate  orgId
org_table() {
  local list
  list="$(sf org list --json 2>/dev/null)" || return 1
  printf '%s' "$list" | jq -r --arg sep "$SEP" '
    .result
    | [ (.nonScratchOrgs // []), (.scratchOrgs // []), (.sandboxes // []), (.other // []) ]
    | add
    | map(select((.alias // .username // "") != ""))
    | unique_by(.username // .alias)
    | .[]
    | [ (.alias // .username), (.username // ""),
        ((.isScratch // false) | tostring),
        (.expirationDate // ""), (.orgId // "") ]
    | join($sep)'
}

# --- output helpers ------------------------------------------------------
print_header() {
  [ "$OUTPUT" = "human" ] || return 0
  if [ -n "$WITHIN_DAYS" ]; then
    echo "Orgs expiring within $WITHIN_DAYS day(s):"
  elif [ "$1" = "all" ]; then
    echo "Org expiration status for all authenticated orgs:"
  else
    echo "Org expiration status:"
  fi
}

group_of() {
  case "$1" in
    EXPIRED)     echo 1 ;;
    SOON)        echo 2 ;;
    OK|DATEONLY) echo 3 ;;
    NONE)        echo 4 ;;
    *)           echo 5 ;;
  esac
}

group_header() {
  case "$1" in
    1) echo "Expired:" ;;
    2) echo "Expiring soon (within $SOON_DAYS day(s)):" ;;
    3) echo "Active (not expiring soon):" ;;
    4) echo "No trial expiration (paid/production):" ;;
    5) echo "Could not query:" ;;
  esac
}

# Actionable authentication guidance for an org that could not be queried.
auth_help() {
  local label="$1" err_name="$2" err_msg="$3"
  case "$err_name" in
    NamedOrgNotFoundError|NoOrgFound*)
      printf "  %-30s  not authenticated — no saved credentials for this org\n" "$label" ;;
    *)
      printf "  %-30s  could not authenticate to org\n" "$label" ;;
  esac
  [ -n "$err_msg" ] && printf "  %-30s  (%s)\n" "" "$err_msg"
  echo
  echo "  To authenticate, run one of:"
  echo "    sf org login web --alias \"$label\"                                            # interactive browser login"
  echo "    sf org login web --alias <my-alias> --instance-url https://test.salesforce.com  # sandbox/My Domain"
  echo "  Then re-run this check. List existing logins with:  sf org list"
}

kind_label() {
  case "$1" in
    trial)   echo "trial/DE edition" ;;
    scratch) echo "scratch org" ;;
    *)       echo "" ;;
  esac
}

print_line() {
  local days="$1" label="$2" kind="$3" exp="$4" status="$5" en="$6" em="$7"
  local k; k="$(kind_label "$kind")"
  case "$status" in
    EXPIRED)  printf "  %-30s  %s expired %s  (EXPIRED %s day(s) ago)\n" "$label" "$k" "$exp" "$(( -days ))" ;;
    SOON)
      if [ "$days" -eq 0 ]; then
        printf "  %-30s  %s expires %s  (EXPIRES TODAY  Warning)\n" "$label" "$k" "$exp"
      else
        printf "  %-30s  %s expires %s  (expires in %s day(s)  Warning)\n" "$label" "$k" "$exp" "$days"
      fi ;;
    OK)       printf "  %-30s  %s expires %s  (expires in %s day(s))\n" "$label" "$k" "$exp" "$days" ;;
    DATEONLY) printf "  %-30s  %s expires %s\n" "$label" "$k" "$exp" ;;
    NONE)     printf "  %-30s  no trial expiration (paid/production org)\n" "$label" ;;
    AUTH_ERROR) auth_help "$label" "$en" "$em" ;;
  esac
}

sort_records() {
  printf '%s' "$RECORDS" | grep -v "^[[:space:]]*$" | sort -t"$SEP" -k1,1n
}

# jq program that turns the sorted TSV into structured records (with optional
# --within filtering applied via $within).
JQ_RECORDS='
  def dnum($d): ($d|tonumber) as $n | if $n >= 999999997 then null else $n end;
  split("\n") | map(select(length>0)) | map(split($sep))
  | map({
      org: .[1], kind: .[2],
      expirationDate: (if .[3]=="" then null else .[3] end),
      daysRemaining: dnum(.[0]),
      status: (.[4] | if .=="EXPIRED" then "expired"
                      elif .=="SOON" then "expiring_soon"
                      elif .=="OK" or .=="DATEONLY" then "active"
                      elif .=="NONE" then "no_expiration"
                      else "auth_error" end),
      orgId: (if .[5]=="" then null else .[5] end)
    })
  | (if $within == null then .
     else map(select(.daysRemaining != null and .daysRemaining <= $within)) end)'

render_json() {
  sort_records | jq -R -s --arg sep "$SEP" --argjson within "${WITHIN_DAYS:-null}" "$JQ_RECORDS"
}

render_csv() {
  printf 'org,kind,expiration_date,days_remaining,status,org_id\n'
  sort_records | jq -R -s -r --arg sep "$SEP" --argjson within "${WITHIN_DAYS:-null}" \
    "$JQ_RECORDS"' | .[]
     | [ .org, .kind, (.expirationDate // ""),
         (.daysRemaining | if .==null then "" else tostring end),
         .status, (.orgId // "") ] | @csv'
}

print_filter_summary() {
  [ -n "$WITHIN_DAYS" ] || return 0
  echo
  if [ "$MATCH_COUNT" -eq 0 ]; then
    echo "No orgs expire within $WITHIN_DAYS day(s)."
  else
    echo "$MATCH_COUNT org(s) expire within $WITHIN_DAYS day(s)."
  fi
}

# Human, prioritized, grouped output (soonest/expired first).
render_human() {
  local sorted; sorted="$(sort_records)"
  print_header "${1:-single}"
  [ -n "$WITHIN_DAYS" ] && echo

  local prev="" n_exp=0 n_soon=0 n_ok=0 n_none=0 n_auth=0
  local days label kind exp status orgid errname errmsg grp
  while IFS="$SEP" read -r days label kind exp status orgid errname errmsg; do
    [ -z "${label:-}" ] && continue

    if [ -n "$WITHIN_DAYS" ]; then
      case "$status" in EXPIRED|SOON|OK) ;; *) continue ;; esac
      [ "$days" -gt "$WITHIN_DAYS" ] && continue
      MATCH_COUNT=$(( MATCH_COUNT + 1 ))
      print_line "$days" "$label" "$kind" "$exp" "$status" "$errname" "$errmsg"
      continue
    fi

    grp="$(group_of "$status")"
    if [ "$grp" != "$prev" ]; then
      printf '\n%s\n' "$(group_header "$grp")"
      prev="$grp"
    fi
    print_line "$days" "$label" "$kind" "$exp" "$status" "$errname" "$errmsg"

    case "$status" in
      EXPIRED)     n_exp=$(( n_exp + 1 )) ;;
      SOON)        n_soon=$(( n_soon + 1 )) ;;
      OK|DATEONLY) n_ok=$(( n_ok + 1 )) ;;
      NONE)        n_none=$(( n_none + 1 )) ;;
      AUTH_ERROR)  n_auth=$(( n_auth + 1 )) ;;
    esac
  done <<EOF
$sorted
EOF

  if [ -n "$WITHIN_DAYS" ]; then
    print_filter_summary
  else
    echo
    local summary="Summary: $n_exp expired, $n_soon expiring within $SOON_DAYS day(s), $n_ok active, $n_none with no expiration"
    [ "$n_auth" -gt 0 ] && summary="$summary, $n_auth unreachable"
    echo "$summary."
  fi
}

# --preserve: backup commands for expiring/expired orgs (human mode only).
render_preserve() {
  [ "$OUTPUT" = "human" ] || return 0
  local sorted; sorted="$(sort_records)"
  local printed=0 days label kind exp status orgid errname errmsg
  while IFS="$SEP" read -r days label kind exp status orgid errname errmsg; do
    [ -z "${label:-}" ] && continue
    case "$status" in EXPIRED|SOON) ;; *) continue ;; esac
    if [ "$printed" -eq 0 ]; then
      echo
      echo "── Preserve your work (at-risk orgs) ────────────────────────────────"
      echo "When an org lapses you lose access to its metadata and data. Back it up:"
      printed=1
    fi
    echo
    echo "  $label:"
    echo "    # 1. Capture a manifest of all metadata, then retrieve it locally:"
    echo "    sf project generate manifest --from-org \"$label\" --name package.xml"
    echo "    sf project retrieve start --target-org \"$label\" --manifest package.xml --output-dir \"./backup-$label\""
    echo "    # 2. Export record data per object (repeat for each object you need):"
    echo "    sf data export bulk --target-org \"$label\" --query \"SELECT Id, Name FROM Account\" --output-file \"./backup-$label/Account.csv\" --wait 10"
  done <<EOF
$sorted
EOF
}

# --renew: trial/DE extension & reactivation guidance (human mode only).
render_renew() {
  [ "$OUTPUT" = "human" ] || return 0
  echo
  echo "── Extend / renew a Salesforce trial or Developer Edition org ────────"
  echo
  echo "  Partners — extend a Trial Org up to +12 months"
  echo "  (eligible while active or expired < 30 days; not for LDV orgs):"
  echo "    1. Log in to https://partners.salesforce.com"
  echo "    2. Click \"Ask Agentforce\" (bottom-right of the page)"
  echo "    3. Say: \"I want to extend my Trial Org\""
  echo "    4. Provide your 15- or 18-character Org ID (shown below if known)"
  echo "    You'll get an email once the extension is confirmed."
  echo "    Ref: Salesforce Help article 000387818"
  echo
  echo "  Nonprofits — trial extension (works even if already expired):"
  echo "    Email your Account Executive (Setup > Your Account) with the"
  echo "    subject \"Trial Extension\" and include:"
  echo "      - Email of the customer that started the trial"
  echo "      - Org ID (or your org's name if you can't access the Org ID)"
  echo "      - Username"
  echo "    AMER: PowerOfUsDesk@salesforce.com"
  echo "    Other regions: myaccount@salesforce.com or 1-800-NO-SOFTWARE"
  echo "    Ref: Salesforce Help article 004754220"
  echo
  echo "  Developer Edition orgs:"
  echo "    DE orgs have no subscription clock, but are deactivated after a"
  echo "    prolonged period (~180 days) with no login. Log in periodically to"
  echo "    keep yours active. If it is locked for inactivity (not yet deleted),"
  echo "    open a case with Salesforce Customer Support to reactivate it — once"
  echo "    permanently deleted an org cannot be recovered."
  echo
  echo "  To keep a standard trial's data and configuration, convert/subscribe"
  echo "  to a paid edition before it lapses."

  # Surface Org IDs for at-risk orgs so the steps above are actionable.
  local sorted ids="" days label kind exp status orgid errname errmsg
  sorted="$(sort_records)"
  while IFS="$SEP" read -r days label kind exp status orgid errname errmsg; do
    [ -z "${label:-}" ] && continue
    case "$status" in EXPIRED|SOON) ;; *) continue ;; esac
    [ -n "$orgid" ] && ids="${ids}    ${label}: ${orgid}
"
  done <<EOF
$sorted
EOF
  if [ -n "$ids" ]; then
    echo
    echo "  Org IDs for your at-risk orgs:"
    printf '%s' "$ids"
  fi
}

# --fail-if-expiring: exit 3 if any org expires within FAIL_WITHIN days.
check_fail_threshold() {
  [ -n "$FAIL_WITHIN" ] || return 0
  local sorted breach="" days label kind exp status orgid errname errmsg
  sorted="$(sort_records)"
  while IFS="$SEP" read -r days label kind exp status orgid errname errmsg; do
    [ -z "${label:-}" ] && continue
    case "$status" in EXPIRED|SOON|OK) ;; *) continue ;; esac
    [ "$days" -le "$FAIL_WITHIN" ] && breach="${breach} ${label}"
  done <<EOF
$sorted
EOF
  if [ -n "$breach" ]; then
    echo "ALERT: org(s) expiring within $FAIL_WITHIN day(s):${breach}" >&2
    return 3
  fi
  return 0
}

# Render whichever output mode is selected. Args: context ("all"|"single")
render() {
  case "$OUTPUT" in
    json) render_json ;;
    csv)  render_csv ;;
    *)
      render_human "$1"
      [ "$DO_PRESERVE" -eq 1 ] && render_preserve
      [ "$DO_RENEW" -eq 1 ] && render_renew
      ;;
  esac
}

# --- argument parsing ----------------------------------------------------
while [ $# -gt 0 ]; do
  case "$1" in
    --all|-a)        MODE="all"; shift ;;
    --within|-w)
      shift
      [ $# -gt 0 ] || die "--within requires a number of days (e.g. --within 30)."
      WITHIN_DAYS="$1"; WITHIN_SEEN=1; shift ;;
    --within=*)      WITHIN_DAYS="${1#*=}"; WITHIN_SEEN=1; shift ;;
    --json)          OUTPUT="json"; shift ;;
    --csv)           OUTPUT="csv"; shift ;;
    --preserve)      DO_PRESERVE=1; shift ;;
    --renew)         DO_RENEW=1; shift ;;
    --no-scratch)    INCLUDE_SCRATCH=0; shift ;;
    --fail-if-expiring)
      shift
      FAIL_SEEN=1
      if [ $# -gt 0 ] && printf '%s' "$1" | grep -qE '^[0-9]+$'; then
        FAIL_WITHIN="$1"; shift
      else
        FAIL_WITHIN="$SOON_DAYS"
      fi ;;
    --fail-if-expiring=*) FAIL_WITHIN="${1#*=}"; FAIL_SEEN=1; shift ;;
    --help|-h)       usage; exit 0 ;;
    --)              shift; break ;;
    -*)              die "Unknown option: $1 (try --help)" ;;
    *)
      [ -n "$TARGET" ] && die "Specify only one org (or use --all). Got extra: $1"
      TARGET="$1"; shift ;;
  esac
done

# Validate integer flags. Validate whenever the flag was seen (so an empty
# value from --within= / --fail-if-expiring= is rejected, not silently ignored).
if [ "$WITHIN_SEEN" -eq 1 ]; then
  case "$WITHIN_DAYS" in
    ''|*[!0-9]*) die "--within expects a non-negative integer number of days (got: '$WITHIN_DAYS')." ;;
  esac
fi
if [ "$FAIL_SEEN" -eq 1 ]; then
  case "$FAIL_WITHIN" in
    ''|*[!0-9]*) die "--fail-if-expiring expects a non-negative integer number of days (got: '$FAIL_WITHIN')." ;;
  esac
fi

if [ "$OUTPUT" != "human" ]; then
  if [ "$DO_PRESERVE" -eq 1 ] || [ "$DO_RENEW" -eq 1 ]; then
    echo "Note: --preserve/--renew produce human-readable guidance and are ignored with --json/--csv." >&2
  fi
fi

# --- dispatch ------------------------------------------------------------
[ "$MODE" = "all" ] && [ -n "$TARGET" ] && \
  die "Cannot combine --all with a specific org ($TARGET)."

if [ "$MODE" = "all" ]; then
  ORG_TSV="$(org_table)" || die "Could not list orgs (is the Salesforce CLI configured?)."
  if [ "$INCLUDE_SCRATCH" -eq 0 ]; then
    ORG_TSV="$(printf '%s' "$ORG_TSV" | awk -F"$SEP" '$3 != "true"')"
  fi
  if [ -z "$ORG_TSV" ]; then
    # Machine-readable modes must stay parseable even with nothing to report.
    case "$OUTPUT" in
      json) echo "[]"; exit 0 ;;
      csv)  echo "org,kind,expiration_date,days_remaining,status,org_id"; exit 0 ;;
    esac
    if [ "$INCLUDE_SCRATCH" -eq 0 ]; then
      echo "No authenticated non-scratch orgs found."
    else
      echo "No authenticated orgs found."
    fi
    echo
    echo "To authenticate, run:  sf org login web --alias <my-alias>"
    exit 1
  fi
  while IFS="$SEP" read -r label username is_scratch list_exp orgid; do
    [ -z "${label:-}" ] && continue
    collect_one "$label" "$is_scratch" "$list_exp" "$orgid" || true
  done <<EOF
$ORG_TSV
EOF
  render all
  rc=0; [ "$HAD_AUTH_ERR" -eq 1 ] && rc=1
  check_fail_threshold || rc=3
  exit "$rc"
fi

# Single org (explicit or default). Look it up in `sf org list` to learn
# whether it is a scratch org and to pick up its expirationDate / orgId.
if [ -z "$TARGET" ]; then
  TARGET="$(sf config get target-org --json 2>/dev/null | jq -r '.result[0].value // empty')"
  if [ -z "$TARGET" ]; then
    echo "No org specified and no default 'target-org' set." >&2
    echo >&2
    echo "Either pass an org alias/username, use --all, or set a default:" >&2
    echo "    sf org login web --alias <my-alias>      # authenticate a new org" >&2
    echo "    sf config set target-org <my-alias>      # make it the default" >&2
    exit 2
  fi
fi

ORG_TSV="$(org_table 2>/dev/null || true)"
match="$(printf '%s' "$ORG_TSV" | awk -F"$SEP" -v t="$TARGET" '$1==t || $2==t {print; exit}')"
if [ -n "$match" ]; then
  is_scratch="$(printf '%s' "$match" | awk -F"$SEP" '{print $3}')"
  list_exp="$(printf '%s' "$match" | awk -F"$SEP" '{print $4}')"
  orgid="$(printf '%s' "$match" | awk -F"$SEP" '{print $5}')"
  if [ "$INCLUDE_SCRATCH" -eq 0 ] && [ "$is_scratch" = "true" ]; then
    die "'$TARGET' is a scratch org and --no-scratch was given."
  fi
  collect_one "$TARGET" "$is_scratch" "$list_exp" "$orgid" || true
else
  # Not in the org list — treat as a direct username; SOQL surfaces auth errors.
  collect_one "$TARGET" "false" "" "" || true
fi

render single
rc=0; [ "$HAD_AUTH_ERR" -eq 1 ] && rc=1
check_fail_threshold || rc=3
exit "$rc"
