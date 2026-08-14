#!/usr/bin/env bash
#
# devhub.sh — Enable Dev Hub and view scratch org allocation for a Salesforce
#             org, via the Salesforce CLI (sf).
#
# Dev Hub is the org feature that lets you create and manage scratch orgs and
# second-generation (2GP)/unlocked packages. This script reports whether Dev Hub
# is enabled, ENABLES it (or configures its sub-preferences) via a Metadata API
# deploy, shows the org's scratch org ALLOCATION (Active/Daily limits and how
# many remain), and lists the active scratch orgs created from the Dev Hub.
#
# How enablement works: the Dev Hub master switch is the deployable metadata
# field DevHubSettings.enableScratchOrgManagementPref (there is NO "enableDevHub"
# field, and no dedicated `sf` command). Deploying it true is exactly what the
# Setup toggle does. This script builds a DevHub.settings-meta.xml and deploys
# it. Enabling requires a user with ModifyAllData or ModifyMetadata (System
# Administrator has these); the org must NOT have a registered namespace and must
# NOT be a sandbox; and once on, Dev Hub CANNOT be turned off.
#
# How enablement is detected: the standard object ScratchOrgInfo is provisioned
# and becomes queryable only when Dev Hub is enabled. A successful "SELECT
# COUNT() FROM ScratchOrgInfo" means Dev Hub is ON; an INVALID_TYPE error means
# it is OFF. (Note: `sf org list limits` reports ActiveScratchOrgs/
# DailyScratchOrgs rows even on non-Dev-Hub orgs, so limits alone are NOT a
# reliable enablement test.)
#
# Usage:
#   devhub.sh [org]                     # status: is Dev Hub on? + allocation
#   devhub.sh [org] --allocation        # scratch org allocation only
#   devhub.sh [org] --list-scratch      # list this Dev Hub's active scratch orgs
#   devhub.sh [org] --enable            # validate enabling Dev Hub (dry run)
#   devhub.sh [org] --enable --apply    # actually enable Dev Hub (irreversible)
#   devhub.sh [org] --enable --packaging --apply       # enable + turn on 2GP
#   devhub.sh [org] --configure --snapshots --apply    # set a sub-pref (Dev Hub already on)
#   devhub.sh [org] --json              # machine-readable status
#   devhub.sh --fail-if-disabled        # exit 3 if Dev Hub is not enabled (CI gate)
#   devhub.sh [alias] --instance-url https://my-domain.my.salesforce.com --enable --apply
#                                       # log in to that instance, then enable Dev Hub
#   devhub.sh https://my-domain.my.salesforce.com      # bare URL: log in to that instance
#   devhub.sh myalias --login           # just authenticate an org via the browser
#
# "org" is an alias or username. If omitted, the default target-org is used,
# and if that is unset, the default target-dev-hub. With --login/--instance-url,
# a supplied positional is used as the CLI alias for the org being logged in to.
# A bare positional that looks like a URL (contains "://") is treated as an
# --instance-url to log in to, not as an org alias.
#
# Options:
#   --allocation, -A        Show only the scratch org allocation (Active/Daily).
#   --list-scratch, -l      List active scratch orgs created from this Dev Hub.
#   --enable, -e            Enable Dev Hub (deploys enableScratchOrgManagementPref
#                           =true). Defaults to a validate-only dry run; add
#                           --apply to actually enable. May be combined with the
#                           sub-pref flags below to enable and configure at once.
#   --configure, -c         Configure Dev Hub sub-preferences without (re)enabling
#                           the master switch. Pair with one or more pref flags.
#                           Defaults to a dry run; add --apply to deploy.
#     --packaging             enablePackaging2=true  (Unlocked + 2GP packages)
#     --snapshots             enableScratchOrgSnapshotPref=true
#     --shape                 enableShapeExportPref=true
#     --scratch-management    enableScratchOrgManagementPref=true (the Dev Hub switch)
#     --pref KEY=VALUE        Any DevHubSettings sub-pref (KEY must start with
#                             "enable"; VALUE is true|false). Repeatable.
#   --apply                 Actually deploy (default for --enable/--configure is a
#                           validate-only dry run).
#   --login                 Authenticate an org first via `sf org login web`
#                           (opens a browser). Runs before the requested action.
#   --instance-url URL      Log in to a Salesforce instance (My Domain, sandbox,
#                           or pre-release/scratch instance) with
#                           `sf org login web --instance-url URL`. Implies --login.
#   --json                  Emit machine-readable JSON.
#   --fail-if-disabled      Exit 3 if Dev Hub is not enabled on the target org.
#   --help, -h              Show this help.
#
# Exit codes:
#   0  success
#   1  the org could not be queried, or a deploy failed (auth/connection/deploy)
#   2  bad usage / missing dependency (sf or jq)
#   3  Dev Hub is not enabled (only when --fail-if-disabled is set)

set -uo pipefail

die() { echo "Error: $*" >&2; exit 2; }

# The skill must be invoked by ABSOLUTE path (see SKILL.md): a relative path like
# ./scripts/devhub.sh resolves against the caller's CWD and can run the wrong
# file. Enforce it here so the guarantee is deterministic and not left to the
# model. (A leading "/" is the portable test for an absolute path.)
case "$0" in
  /*) : ;;
  *) die "Run this script by its absolute path (got: '$0'). Example: bash \"/abs/path/to/skills/dx-org-devhub-configure/scripts/devhub.sh\"" ;;
esac

command -v sf >/dev/null 2>&1 || die "Salesforce CLI ('sf') not found on PATH."
command -v jq >/dev/null 2>&1 || die "'jq' not found on PATH."

# Keep CLI update chatter out of captured JSON/stdout.
export SF_AUTOUPDATE_DISABLE=true

# --- constants -----------------------------------------------------------
SETTINGS_API_VERSION="47.0"          # DevHubSettings requires API >= 47.0
DEVHUB_SWITCH="enableScratchOrgManagementPref"

# --- option state --------------------------------------------------------
TARGET=""                   # org alias/username (positional or resolved default)
TARGET_EXPLICIT=0            # 1 when the caller supplied an org alias/username
MODE="status"               # status | allocation | list | deploy
MODE_EXPLICIT=0              # 1 when the caller selected an operation
ENABLING=0                  # 1 when --enable was passed (seeds the master switch)
OUTPUT="human"              # human | json
APPLY=0                     # deploy: 0 = dry run (validate only), 1 = real deploy
FAIL_IF_DISABLED=0
PREFS=()                    # requested DevHubSettings prefs (KEY=VALUE)
DO_LOGIN=0                  # 1 when --login or --instance-url requests a browser login
LOGIN_INSTANCE_URL=""       # instance URL for `sf org login web --instance-url`

# --- run state -----------------------------------------------------------
DEVHUB_STATE=""             # enabled | disabled | auth_error
DEVHUB_ERRNAME=""           # error .name when auth_error
DEVHUB_ERRMSG=""
SCRATCH_COUNT=""            # ScratchOrgInfo count when enabled
INSTANCE_URL=""             # resolved org instance URL (for the Setup deep link)

usage() {
  sed -n '2,/^set -uo/p' "$0" | sed '/^set -uo/d; s/^# \{0,1\}//; s/^#//'
}

# Set MODE, rejecting a second conflicting mode selection.
set_mode() {
  if [ "$MODE" != "status" ] && [ "$MODE" != "$1" ]; then
    die "Choose only one of --allocation, --list-scratch, --enable/--configure."
  fi
  MODE="$1"
}

# True if PREFS already contains a KEY (any value).
has_pref_key() {
  local p
  for p in "${PREFS[@]:-}"; do
    [ -n "$p" ] || continue
    [ "${p%%=*}" = "$1" ] && return 0
  done
  return 1
}

# Register a pref for deploy, validating shape and giving actionable guidance
# for the common wrong field name. De-dupes on key (later value wins).
add_pref() {
  local kv="$1" key val existing kept
  key="${kv%%=*}"; val="${kv#*=}"
  case "$key" in
    enableDevHub)
      die "There is no 'enableDevHub' field. Use --enable (which sets $DEVHUB_SWITCH=true)." ;;
    "$DEVHUB_SWITCH")
      [ "$val" = "true" ] || die "$DEVHUB_SWITCH cannot be set to false because Dev Hub enablement is irreversible."
      ENABLING=1 ;;
    enable*) : ;;
    *) die "--pref key must be a DevHubSettings field starting with 'enable' (got: '$key')." ;;
  esac
  case "$val" in
    true|false) : ;;
    *) die "--pref value must be true or false (got: '$key=$val')." ;;
  esac
  kept=()
  for existing in "${PREFS[@]:-}"; do
    [ -n "$existing" ] || continue
    [ "${existing%%=*}" = "$key" ] && continue
    kept+=("$existing")
  done
  kept+=("$key=$val")
  PREFS=("${kept[@]}")
}

# --- argument parsing ----------------------------------------------------
while [ $# -gt 0 ]; do
  case "$1" in
    --allocation|-A)      MODE_EXPLICIT=1; set_mode allocation; shift ;;
    --list-scratch|-l)    MODE_EXPLICIT=1; set_mode list; shift ;;
    --enable|-e)          MODE_EXPLICIT=1; ENABLING=1; set_mode deploy; shift ;;
    --configure|-c)       MODE_EXPLICIT=1; set_mode deploy; shift ;;
    --packaging)          MODE_EXPLICIT=1; add_pref "enablePackaging2=true"; set_mode deploy; shift ;;
    --snapshots)          MODE_EXPLICIT=1; add_pref "enableScratchOrgSnapshotPref=true"; set_mode deploy; shift ;;
    --shape)              MODE_EXPLICIT=1; add_pref "enableShapeExportPref=true"; set_mode deploy; shift ;;
    --scratch-management) MODE_EXPLICIT=1; add_pref "$DEVHUB_SWITCH=true"; set_mode deploy; shift ;;
    --pref)
      shift
      [ $# -gt 0 ] || die "--pref requires a KEY=VALUE argument (e.g. --pref enablePackaging2=true)."
      case "$1" in *=*) : ;; *) die "--pref expects KEY=VALUE (got: '$1')." ;; esac
      MODE_EXPLICIT=1; add_pref "$1"; set_mode deploy; shift ;;
    --pref=*)
      kv="${1#*=}"
      case "$kv" in *=*) : ;; *) die "--pref expects KEY=VALUE (got: '$kv')." ;; esac
      MODE_EXPLICIT=1; add_pref "$kv"; set_mode deploy; shift ;;
    --apply)              APPLY=1; shift ;;
    --login)              DO_LOGIN=1; shift ;;
    --instance-url)
      shift
      [ $# -gt 0 ] || die "--instance-url requires a URL (e.g. --instance-url https://my-domain.my.salesforce.com)."
      [ -n "$LOGIN_INSTANCE_URL" ] && die "Specify only one instance URL. Got extra: $1"
      LOGIN_INSTANCE_URL="$1"; DO_LOGIN=1; shift ;;
    --instance-url=*)
      [ -n "$LOGIN_INSTANCE_URL" ] && die "Specify only one instance URL. Got extra: ${1#*=}"
      LOGIN_INSTANCE_URL="${1#*=}"; DO_LOGIN=1; shift ;;
    --json)               OUTPUT="json"; shift ;;
    --fail-if-disabled)   FAIL_IF_DISABLED=1; shift ;;
    --help|-h)            usage; exit 0 ;;
    --)                   shift; break ;;
    -*)                   die "Unknown option: $1 (try --help)" ;;
    *://*)
      # A bare URL positional is an instance URL to log in to (My Domain,
      # sandbox, or pre-release/scratch instance), not an org alias — an alias or
      # username never contains "://". Route it to the login path.
      [ -n "$LOGIN_INSTANCE_URL" ] && die "Specify only one instance URL. Got extra: $1"
      LOGIN_INSTANCE_URL="$1"; DO_LOGIN=1; shift ;;
    *)
      [ -n "$TARGET" ] && die "Specify only one org. Got extra: $1"
      TARGET="$1"; TARGET_EXPLICIT=1; shift ;;
  esac
done

# --enable always includes the master switch.
if [ "$ENABLING" -eq 1 ] && ! has_pref_key "$DEVHUB_SWITCH"; then
  add_pref "$DEVHUB_SWITCH=true"
fi

if [ "$MODE" = "deploy" ] && [ "${#PREFS[@]}" -eq 0 ]; then
  die "--configure needs at least one preference (e.g. --packaging, --snapshots, or --pref KEY=VALUE). To enable Dev Hub, use --enable."
fi

if [ "$APPLY" -eq 1 ] && [ "$MODE" != "deploy" ]; then
  die "--apply is valid only with --enable, --configure, or a preference flag."
fi

if [ "$APPLY" -eq 1 ] && [ "$TARGET_EXPLICIT" -ne 1 ]; then
  die "--apply requires an explicit org alias or username; refusing to mutate an implicit default org."
fi

# A supplied instance URL must use an HTTPS Salesforce-owned hostname.
if [ -n "$LOGIN_INSTANCE_URL" ]; then
  case "$LOGIN_INSTANCE_URL" in
    https://*.salesforce.com|https://*.force.com|https://*.salesforce.mil) : ;;
    *) die "--instance-url must use an https:// Salesforce hostname (got: '$LOGIN_INSTANCE_URL')." ;;
  esac
fi

# --- org resolution ------------------------------------------------------
resolve_target() {
  [ -n "$TARGET" ] && return 0
  TARGET="$(sf config get target-org --json 2>/dev/null | jq -r '.result[0].value // empty')"
  [ -n "$TARGET" ] && return 0
  TARGET="$(sf config get target-dev-hub --json 2>/dev/null | jq -r '.result[0].value // empty')"
  [ -n "$TARGET" ] && return 0
  echo "No org specified and no default target-org / target-dev-hub is set." >&2
  echo >&2
  echo "Pass an org alias/username, or set a default:" >&2
  echo "    sf org login web --alias <my-alias>      # authenticate an org" >&2
  echo "    sf config set target-org <my-alias>      # make it the default" >&2
  exit 2
}

# --- interactive login ---------------------------------------------------
# Authenticate an org with `sf org login web`, honoring an optional
# --instance-url (My Domain, sandbox, or pre-release/scratch instance) and, when
# an org identifier was supplied, using it as the CLI alias. Opens a browser for
# the OAuth flow; returns non-zero if the login fails or times out.
do_login() {
  local args=(org login web)
  [ -n "$LOGIN_INSTANCE_URL" ] && args+=(--instance-url "$LOGIN_INSTANCE_URL")
  [ -n "$TARGET" ] && args+=(--alias "$TARGET")

  if [ "$OUTPUT" != "json" ]; then
    echo "Authenticating with the Salesforce CLI (a browser window will open)..."
    [ -n "$LOGIN_INSTANCE_URL" ] && echo "  instance URL: $LOGIN_INSTANCE_URL"
    [ -n "$TARGET" ] && echo "  alias:        $TARGET"
    echo "  Complete the login in the browser promptly (the session times out)."
    echo
  fi

  local out ok
  out="$(sf "${args[@]}" --json 2>/dev/null)"
  ok="$(printf '%s' "$out" | jq -r 'if .status==0 then "true" else "false" end' 2>/dev/null)"

  if [ "$ok" != "true" ]; then
    local msg
    msg="$(printf '%s' "$out" | jq -r '.message // empty' 2>/dev/null)"
    if [ "$OUTPUT" = "json" ]; then
      jq -n --arg msg "${msg:-login failed}" '{status:"login_failed", error:$msg}'
    else
      echo "Login failed: ${msg:-unknown error}." >&2
      echo "  Retry in your own terminal, or use the device flow if the browser flow keeps timing out:" >&2
      echo "    sf org login device${LOGIN_INSTANCE_URL:+ --instance-url $(shell_quote "$LOGIN_INSTANCE_URL")}${TARGET:+ --alias $(shell_quote "$TARGET")}" >&2
    fi
    return 1
  fi

  # Adopt the authenticated username as the target when none was supplied, so the
  # rest of the run operates on the org the user just logged in to.
  if [ -z "$TARGET" ]; then
    TARGET="$(printf '%s' "$out" | jq -r '.result.username // empty' 2>/dev/null)"
  fi
  [ "$OUTPUT" != "json" ] && echo "Authenticated: ${TARGET:-(org)}" && echo
  return 0
}

# Render one dynamic value as a safe, copy-pasteable shell argument.
shell_quote() {
  printf "'%s'" "$(printf '%s' "$1" | sed "s/'/'\\\\''/g")"
}

# --- Dev Hub detection ---------------------------------------------------
# Sets DEVHUB_STATE (+ SCRATCH_COUNT when enabled, or error fields on failure).
# ScratchOrgInfo is queryable ONLY on a Dev Hub, so a clean COUNT == enabled and
# INVALID_TYPE == not enabled; any other failure is treated as an auth/conn error.
detect_devhub() {
  local out rc
  out="$(sf data query --query "SELECT COUNT() FROM ScratchOrgInfo" \
          --target-org "$TARGET" --json 2>/dev/null)"
  rc=$?
  if [ "$rc" -eq 0 ]; then
    DEVHUB_STATE="enabled"
    SCRATCH_COUNT="$(printf '%s' "$out" | jq -r '.result.totalSize // empty')"
    return 0
  fi
  local ename emsg
  ename="$(printf '%s' "$out" | jq -r '.name // empty' 2>/dev/null)"
  emsg="$(printf '%s' "$out" | jq -r '.message // empty' 2>/dev/null | tr '\t\n' '  ')"
  case "$ename" in
    INVALID_TYPE)
      DEVHUB_STATE="disabled"; return 0 ;;
    *)
      DEVHUB_STATE="auth_error"; DEVHUB_ERRNAME="$ename"; DEVHUB_ERRMSG="$emsg"; return 1 ;;
  esac
}

# Echoes TSV rows "name<TAB>remaining<TAB>max" for the two scratch org limits,
# or nothing if the org could not be queried.
allocation_rows() {
  local out
  out="$(sf org list limits --target-org "$TARGET" --json 2>/dev/null)" || return 1
  printf '%s' "$out" | jq -r '
    .result[]?
    | select(.name=="ActiveScratchOrgs" or .name=="DailyScratchOrgs")
    | [.name, (.remaining|tostring), (.max|tostring)] | @tsv'
}

# Resolve the org instance URL for the Setup deep link (best effort).
resolve_instance_url() {
  [ -n "$INSTANCE_URL" ] && return 0
  INSTANCE_URL="$(sf org display --target-org "$TARGET" --json 2>/dev/null \
    | jq -r '.result.instanceUrl // empty')"
}

# --- auth error reporting ------------------------------------------------
print_auth_error() {
  if [ "$OUTPUT" = "json" ]; then
    jq -n --arg org "$TARGET" --arg name "$DEVHUB_ERRNAME" --arg msg "$DEVHUB_ERRMSG" \
      '{org:$org, devHubEnabled:null, status:"auth_error", error:{name:$name, message:$msg}}'
    return
  fi
  printf "  %-30s  could not query org (%s)\n" "$TARGET" "${DEVHUB_ERRNAME:-error}"
  [ -n "$DEVHUB_ERRMSG" ] && printf "  %-30s  (%s)\n" "" "$DEVHUB_ERRMSG"
  echo
  if [ -n "$LOGIN_INSTANCE_URL" ]; then
    # An instance URL was provided — show the exact command for it, and offer to
    # let the script run it directly via --login.
    echo "  To authenticate against $LOGIN_INSTANCE_URL, run:"
    echo "    sf org login web --instance-url $(shell_quote "$LOGIN_INSTANCE_URL")${TARGET:+ --alias $(shell_quote "$TARGET")}"
    echo "  Or let this script log you in and continue in one step:"
    echo "    devhub.sh ${TARGET:+$(shell_quote "$TARGET") }--instance-url $(shell_quote "$LOGIN_INSTANCE_URL") --login"
  else
    echo "  To authenticate, run one of:"
    echo "    sf org login web --alias $(shell_quote "$TARGET")                                             # interactive browser login"
    echo "    sf org login web --alias <my-alias> --instance-url https://MYDOMAIN.my.salesforce.com   # sandbox/My Domain"
    echo "  Or let this script log you in and continue in one step:"
    echo "    devhub.sh $(shell_quote "$TARGET") --login                                                    # prod/DE/trial"
    echo "    devhub.sh <my-alias> --instance-url https://MYDOMAIN.my.salesforce.com --login  # sandbox/My Domain"
  fi
  echo "  Then re-run. List existing logins with:  sf org list"
}

# --- Setup UI fallback text ----------------------------------------------
print_ui_fallback() {
  resolve_instance_url
  echo "  Manual alternative (Setup UI):"
  echo "    1. Log in as a System Administrator."
  echo "    2. Setup > Quick Find > \"Dev Hub\" > Dev Hub > turn Enable Dev Hub On."
  if [ -n "$INSTANCE_URL" ]; then
    echo "    Open it directly: sf org open --path \"lightning/setup/DevHub/home\" --target-org \"$TARGET\""
  fi
}

# --- allocation rendering ------------------------------------------------
render_allocation() {
  local rows a_max a_rem d_max d_rem
  rows="$(allocation_rows)" || { echo "Could not read org limits for '$TARGET'." >&2; return 1; }
  a_rem="$(printf '%s\n' "$rows" | awk -F'\t' '$1=="ActiveScratchOrgs"{print $2}')"
  a_max="$(printf '%s\n' "$rows" | awk -F'\t' '$1=="ActiveScratchOrgs"{print $3}')"
  d_rem="$(printf '%s\n' "$rows" | awk -F'\t' '$1=="DailyScratchOrgs"{print $2}')"
  d_max="$(printf '%s\n' "$rows" | awk -F'\t' '$1=="DailyScratchOrgs"{print $3}')"

  if [ "$OUTPUT" = "json" ]; then
    jq -n --arg org "$TARGET" \
      --argjson am "${a_max:-null}" --argjson ar "${a_rem:-null}" \
      --argjson dm "${d_max:-null}" --argjson dr "${d_rem:-null}" '
      {org:$org,
       allocation:{
         activeScratchOrgs:{max:$am, remaining:$ar, used:(if $am!=null and $ar!=null then ($am-$ar) else null end)},
         dailyScratchOrgs:{max:$dm, remaining:$dr, used:(if $dm!=null and $dr!=null then ($dm-$dr) else null end)}
       }}'
    return 0
  fi

  echo "Scratch org allocation for '$TARGET':"
  if [ -z "$a_max" ] && [ -z "$d_max" ]; then
    echo "  No scratch org limits reported (org may not be a Dev Hub, or could not be queried)."
    return 0
  fi
  printf "  %-22s %10s %10s %10s\n" "Limit" "Used" "Remaining" "Max"
  [ -n "$a_max" ] && printf "  %-22s %10s %10s %10s\n" "Active scratch orgs" "$(( a_max - a_rem ))" "$a_rem" "$a_max"
  [ -n "$d_max" ] && printf "  %-22s %10s %10s %10s\n" "Daily scratch orgs" "$(( d_max - d_rem ))" "$d_rem" "$d_max"
  echo
  echo "  Active = orgs alive right now; Daily = successful creations in a rolling 24h window."
  echo "  Allocation is set by the Dev Hub's edition (e.g. Developer/trial 3 & 6;"
  echo "  Enterprise 40 & 80; Unlimited/Performance 100 & 200) plus any purchased add-on."
}

# --- active scratch org listing ------------------------------------------
render_list() {
  local out rc
  out="$(sf data query --target-org "$TARGET" \
      --query "SELECT SignupUsername, OrgName, Edition, ExpirationDate, ScratchOrg FROM ActiveScratchOrg ORDER BY ExpirationDate NULLS LAST" \
      --json 2>/dev/null)"
  rc=$?
  if [ "$rc" -ne 0 ]; then
    if [ "$OUTPUT" = "json" ]; then echo "[]"; else
      echo "Could not list scratch orgs for '$TARGET' — is Dev Hub enabled and the org authenticated?" >&2
    fi
    return 1
  fi
  if [ "$OUTPUT" = "json" ]; then
    printf '%s' "$out" | jq '[.result.records[]? | {signupUsername:.SignupUsername, orgName:.OrgName, edition:.Edition, expirationDate:.ExpirationDate, scratchOrgId:.ScratchOrg}]'
    return 0
  fi
  local total
  total="$(printf '%s' "$out" | jq -r '.result.totalSize // 0')"
  echo "Active scratch orgs on Dev Hub '$TARGET': $total"
  if [ "$total" = "0" ]; then
    echo "  (none active)"
    return 0
  fi
  printf '%s' "$out" | jq -r '.result.records[]?
    | "  \(.SignupUsername // "?")  edition=\(.Edition // "?")  expires=\(.ExpirationDate // "?")  id=\(.ScratchOrg // "?")"'
}

# --- deploy (enable / configure sub-prefs) -------------------------------
DEPLOY_TEMP_DIR=""
cleanup_deploy_temp() {
  [ -n "$DEPLOY_TEMP_DIR" ] && rm -rf -- "$DEPLOY_TEMP_DIR"
}

render_deploy() {
  # Sub-prefs (packaging, snapshots, shape) require Dev Hub to be on. If the
  # user is configuring one without also enabling, and Dev Hub is off, warn.
  if [ "$ENABLING" -eq 0 ] && [ "$DEVHUB_STATE" = "disabled" ] && [ "$OUTPUT" != "json" ]; then
    echo "Note: Dev Hub is not enabled on '$TARGET'. Sub-preferences require Dev Hub — add --enable, or run --enable first." >&2
    echo >&2
  fi

  local tmp
  tmp="$(mktemp -d 2>/dev/null)" || die "Could not create a temporary directory for the deploy."
  DEPLOY_TEMP_DIR="$tmp"
  trap cleanup_deploy_temp EXIT

  mkdir -p "$tmp/force-app/main/default/settings"
  cat > "$tmp/sfdx-project.json" <<JSON
{ "packageDirectories": [{ "path": "force-app", "default": true }], "sourceApiVersion": "$SETTINGS_API_VERSION" }
JSON
  {
    echo '<?xml version="1.0" encoding="UTF-8"?>'
    echo '<DevHubSettings xmlns="http://soap.sforce.com/2006/04/metadata">'
    local kv key val
    for kv in "${PREFS[@]}"; do
      key="${kv%%=*}"; val="${kv#*=}"
      echo "    <$key>$val</$key>"
    done
    echo '</DevHubSettings>'
  } > "$tmp/force-app/main/default/settings/DevHub.settings-meta.xml"

  local dry="--dry-run" action="Validating (dry run)"
  if [ "$APPLY" -eq 1 ]; then dry=""; action="Deploying"; fi

  if [ "$OUTPUT" != "json" ]; then
    if [ "$ENABLING" -eq 1 ]; then
      echo "$action Dev Hub enablement on '$TARGET':"
    else
      echo "$action DevHubSettings on '$TARGET':"
    fi
    local kv2; for kv2 in "${PREFS[@]}"; do echo "    $kv2"; done
    if [ "$ENABLING" -eq 1 ] && [ "$APPLY" -eq 1 ]; then
      echo
      echo "  WARNING: enabling Dev Hub is IRREVERSIBLE — it cannot be turned off."
      echo "  Requires ModifyAllData or ModifyMetadata (System Administrator)."
      echo "  Not allowed in a sandbox, or in an org with a registered namespace."
    fi
    echo
  fi

  local out ok verified="unknown"
  out="$( cd "$tmp" && sf project deploy start $dry --source-dir force-app \
            --target-org "$TARGET" --json 2>/dev/null )"
  ok="$(printf '%s' "$out" | jq -r '.result.success // false')"

  # On a real, successful enablement, re-detect so we report verified state.
  if [ "$APPLY" -eq 1 ] && [ "$ENABLING" -eq 1 ] && [ "$ok" = "true" ]; then
    detect_devhub >/dev/null 2>&1
    verified="$DEVHUB_STATE"
  fi

  if [ "$OUTPUT" = "json" ]; then
    printf '%s' "$out" | jq \
      --arg applied "$([ "$APPLY" -eq 1 ] && echo true || echo false)" \
      --arg enabling "$([ "$ENABLING" -eq 1 ] && echo true || echo false)" \
      --arg verified "$verified" '
      {applied:($applied=="true"),
       enabling:($enabling=="true"),
       success:(.result.success // false),
       checkOnly:(.result.checkOnly // null),
       devHubVerifiedState:(if $verified=="unknown" then null else $verified end),
       failures:[.result.details.componentFailures[]? | {fullName, problem}],
       message:(.message // null)}'
    [ "$ok" = "true" ] && return 0 || return 1
  fi

  if [ "$ok" = "true" ]; then
    if [ "$APPLY" -eq 1 ]; then
      if [ "$ENABLING" -eq 1 ]; then
        echo "  Success — Dev Hub enabled (deploy succeeded)."
        if [ "$verified" = "enabled" ]; then
          echo "  Verified: ScratchOrgInfo is now queryable."
        else
          echo "  Note: provisioning may take a moment; re-run 'devhub.sh \"$TARGET\"' to confirm."
        fi
        echo "  Set it as your default Dev Hub:  sf config set target-dev-hub \"$TARGET\""
      else
        echo "  Success — Dev Hub preferences deployed."
      fi
    else
      echo "  Dry run passed — valid. Re-run with --apply to deploy."
      [ "$ENABLING" -eq 1 ] && echo "  (Enabling Dev Hub is irreversible; --apply commits it.)"
    fi
    return 0
  fi

  echo "  Deployment did not succeed:"
  printf '%s' "$out" | jq -r '.result.details.componentFailures[]? | "    - \(.fullName): \(.problem)"' 2>/dev/null
  printf '%s' "$out" | jq -r '.message // empty' 2>/dev/null | sed 's/^/    /'
  # Common cause: missing perms. Offer the UI route.
  if printf '%s' "$out" | grep -qi "INSUFFICIENT_ACCESS\|ModifyAllData\|ModifyMetadata"; then
    echo
    echo "  This looks like a permissions issue — the deploy needs ModifyAllData or ModifyMetadata."
    [ "$ENABLING" -eq 1 ] && print_ui_fallback
  fi
  return 1
}

# --- status (default) ----------------------------------------------------
render_status() {
  if [ "$OUTPUT" = "json" ]; then
    local rows a_max a_rem d_max d_rem
    rows="$(allocation_rows 2>/dev/null || true)"
    a_rem="$(printf '%s\n' "$rows" | awk -F'\t' '$1=="ActiveScratchOrgs"{print $2}')"
    a_max="$(printf '%s\n' "$rows" | awk -F'\t' '$1=="ActiveScratchOrgs"{print $3}')"
    d_rem="$(printf '%s\n' "$rows" | awk -F'\t' '$1=="DailyScratchOrgs"{print $2}')"
    d_max="$(printf '%s\n' "$rows" | awk -F'\t' '$1=="DailyScratchOrgs"{print $3}')"
    jq -n --arg org "$TARGET" --arg state "$DEVHUB_STATE" \
      --argjson count "${SCRATCH_COUNT:-null}" \
      --argjson am "${a_max:-null}" --argjson ar "${a_rem:-null}" \
      --argjson dm "${d_max:-null}" --argjson dr "${d_rem:-null}" '
      {org:$org,
       devHubEnabled:($state=="enabled"),
       status:$state,
       activeScratchOrgSignups:$count,
       allocation:{
         activeScratchOrgs:{max:$am, remaining:$ar},
         dailyScratchOrgs:{max:$dm, remaining:$dr}
       }}'
    return 0
  fi

  echo "Dev Hub status for '$TARGET':"
  if [ "$DEVHUB_STATE" = "enabled" ]; then
    echo "  Dev Hub: ENABLED  (ScratchOrgInfo is queryable)"
    [ -n "$SCRATCH_COUNT" ] && echo "  Scratch org signup records: $SCRATCH_COUNT"
    echo
    render_allocation
  else
    echo "  Dev Hub: NOT ENABLED"
    echo
    echo "  Enable it (deploys $DEVHUB_SWITCH=true; irreversible):"
    echo "    devhub.sh \"$TARGET\" --enable            # validate first (dry run)"
    echo "    devhub.sh \"$TARGET\" --enable --apply    # actually enable"
    echo "  Requires ModifyAllData or ModifyMetadata (System Administrator);"
    echo "  not allowed in a sandbox or an org with a registered namespace."
    echo
    print_ui_fallback
  fi
}

# --- dispatch ------------------------------------------------------------
# Authenticate first when requested. Login can supply the org, so it runs before
# resolve_target's "no org" guard; a bare positional (no other mode) with
# --login/--instance-url is treated as the alias to log in under.
if [ "$DO_LOGIN" -eq 1 ]; then
  do_login || exit 1
  if [ "$MODE_EXPLICIT" -eq 0 ] && [ "$FAIL_IF_DISABLED" -eq 0 ]; then
    exit 0
  fi
fi

resolve_target

# status/deploy need the enablement state; allocation and list query the org
# directly and surface their own errors.
case "$MODE" in
  status|deploy)
    if ! detect_devhub && [ "$DEVHUB_STATE" = "auth_error" ]; then
      print_auth_error
      exit 1
    fi
    ;;
esac

rc=0
case "$MODE" in
  status)     render_status || rc=1 ;;
  allocation) render_allocation || rc=1 ;;
  list)       render_list || rc=1 ;;
  deploy)     render_deploy || rc=1 ;;
esac

# CI gate: exit 3 if Dev Hub is not enabled (takes precedence for alerting).
if [ "$FAIL_IF_DISABLED" -eq 1 ]; then
  [ -z "$DEVHUB_STATE" ] && detect_devhub >/dev/null 2>&1
  if [ "$DEVHUB_STATE" != "enabled" ]; then
    echo "ALERT: Dev Hub is not enabled on '$TARGET'." >&2
    exit 3
  fi
fi

exit "$rc"
