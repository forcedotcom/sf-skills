#!/usr/bin/env bash
# Lists the DevOps Center environments of a source org and resolves an optional
# identifier (alias, username, My Domain URL, 15/18-char org id, or environment name)
# to one of them. Read-only. Prints one JSON document on stdout.
#
# Usage: resolve-environment.sh <source-org-alias> [identifier] [--rows-file <file>] [--user-auth-file <file>] [--check-sessions]
#   --rows-file       read the DevopsEnvironment query result JSON from a file (tests)
#   --user-auth-file  read the per-user sign-in map (named credential -> configured | notConfigured | unknown)
#                     from a file instead of calling the org (tests)
#   --check-sessions  probe each workspace login that belongs to a listed environment with one
#                     cheap query (SELECT Id FROM Organization LIMIT 1) and report .session
#                     (valid / expired / unknown). Off by default: one org call per login.
#
# Exit codes: 0 ok (check .match / .matchStatus), 1 usage or call error.
set -uo pipefail

command -v jq >/dev/null || { echo "jq required" >&2; exit 1; }
SRC="${1:-}"
[ -n "$SRC" ] || { echo "usage: resolve-environment.sh <source-org-alias> [identifier] [--rows-file <file>]" >&2; exit 1; }
shift
IDENT=""; ROWS_FILE=""; USER_AUTH_FILE=""; CHECK_SESSIONS=0
while [ $# -gt 0 ]; do
  case "$1" in
    --rows-file) [ $# -ge 2 ] || { echo "--rows-file needs a value" >&2; exit 1; }; ROWS_FILE="$2"; shift 2 ;;
    --user-auth-file) [ $# -ge 2 ] || { echo "--user-auth-file needs a value" >&2; exit 1; }; USER_AUTH_FILE="$2"; shift 2 ;;
    --check-sessions) CHECK_SESSIONS=1; shift ;;
    -*) echo "unknown option $1" >&2; exit 1 ;;
    *) [ -z "$IDENT" ] || { echo "one identifier only; quote a name with spaces: \"Dev 12 Org\"" >&2; exit 1; }; IDENT="$1"; shift ;;
  esac
done

sfj() { env FORCE_COLOR=0 SF_CLI_DISABLE_AUTOUPDATE=true "$@" 2>/dev/null; }
tmpd=$(mktemp -d); trap 'rm -rf "$tmpd"' EXIT

# Source org (the org the user built in).
src_json=$(sfj sf org display --target-org "$SRC" --json) \
  || { echo "cannot read source org '$SRC'" >&2; exit 1; }
source_obj=$(printf '%s' "$src_json" | jq -c --arg a "$SRC" \
  '{alias:$a, username:.result.username, orgId:.result.id, instanceUrl:.result.instanceUrl}')

# DevopsEnvironment rows.
if [ -n "$ROWS_FILE" ]; then
  rows_json=$(cat "$ROWS_FILE")
else
  rows_json=$(sfj sf data query --target-org "$SRC" --json --query \
    "SELECT Id, Name, NamedCredential, OrgType, IsExpired, OrgUrl, OrgIdentifier FROM DevopsEnvironment ORDER BY Name") \
    || {
      # sf prints its JSON error on stdout; tell "not enabled" apart from an expired session or other failure.
      qmsg=$(printf '%s' "$rows_json" | jq -r '[.name, .message] | map(select(. != null)) | join(": ")' 2>/dev/null)
      case "$qmsg" in
        *INVALID_TYPE*|*"sObject type"*|*"not supported"*|*INSUFFICIENT_ACCESS*)
          echo "DevOps Center not enabled or no access: DevopsEnvironment is unavailable ($qmsg)" >&2 ;;
        *) echo "DevopsEnvironment query failed, not an enablement problem: ${qmsg:-unknown error}" >&2 ;;
      esac
      exit 1
    }
fi
printf '%s' "$rows_json" | jq -e '.result.records' >/dev/null 2>&1 \
  || { echo "unexpected query result" >&2; exit 1; }

# Workspace logins: the aliases (and the org each one points at) that `sf ... --target-org <alias>` accepts
# here. Core registers an environment's name as an alias when its connect PATCH runs with
# registerWorkspaceAlias=true. An environment counts as present when an alias carries its name OR points
# at its org id (several environments can share one org). Local read, no org call.
# "null" = could not be read: workspace status is then reported as unknown.
aliases_json=$(sfj sf org list --skip-connection-status --json | jq -c \
  '[.result | to_entries[] | .value | arrays[] | select(.alias != null) | {alias: .alias, orgId: ((.orgId // "")[0:15]), host: ((.instanceUrl // "") | sub("^https?://"; "") | sub("/.*$"; "") | ascii_downcase)}]' 2>/dev/null) || aliases_json=null
[ -n "$aliases_json" ] || aliases_json=null

# Optional session probe. One cheap query per login that belongs to a listed environment.
# A mapping alias -> valid | expired | unknown. A probe that times out or fails for any other reason is
# "unknown", never "expired": only a recognised session/refresh-token error counts as expired.
sessions_json='{}'
# Bound each probe to 20s with whatever is available (GNU timeout in the image, perl on macOS, else none).
if command -v timeout >/dev/null; then tmo="timeout 20"
elif command -v perl >/dev/null; then tmo="perl -e alarm(20);exec(@ARGV) --"
else tmo=""; fi
if [ "$CHECK_SESSIONS" = 1 ] && [ "$aliases_json" != null ]; then
  want=$(printf '%s' "$rows_json" | jq -r '[.result.records[]? | (.OrgIdentifier // "")[0:15] | select(. != "")] | unique | .[]')
  # Probes are independent, so run them side by side. Read line by line: an alias may contain spaces ("Dev 12 Org").
  i=0
  while IFS= read -r a; do
    [ -n "$a" ] || continue
    i=$((i+1)); printf '%s' "$a" > "$tmpd/s$i.k"
    (
      out=$(SF_TARGET_ORG="$a" SF_DISABLE_TELEMETRY=true sfj $tmo \
        sf data query --target-org "$a" --json --query "SELECT Id FROM Organization LIMIT 1" </dev/null)
      if printf '%s' "$out" | jq -e '.status == 0' >/dev/null 2>&1; then st=valid
      elif printf '%s' "$out" | grep -Eiq 'INVALID_SESSION_ID|invalid_grant|RefreshTokenAuthError|Bad_OAuth_Token|expired access/refresh|Session expired or invalid'; then st=expired
      else st=unknown; fi
      printf '%s' "$st" > "$tmpd/s$i.v"
    ) &
  done < <(printf '%s' "$aliases_json" | jq -r --arg want "$want" \
      '($want | split("\n")) as $w | .[] | select(.orgId as $o | $w | index($o)) | .alias')
  wait
  for k in "$tmpd"/s*.k; do
    [ -f "$k" ] || continue
    sessions_json=$(printf '%s' "$sessions_json" | jq -c --arg a "$(cat "$k")" --arg s "$(cat "${k%.k}.v" 2>/dev/null || echo unknown)" '. + {($a): $s}')
  done
fi

# Hub credential read starts now and runs alongside the checks below (consumed at the hub step).
hub_ver="${DLC_API_VERSION:-68.0}"
if [ -z "$USER_AUTH_FILE" ]; then
  ( sfj $tmo sf api request rest "/services/data/v${hub_ver}/named-credentials/named-credential-setup/ALMDevOpsCenterHub" --target-org "$SRC" </dev/null > "$tmpd/hub.nc"
    sfj $tmo sf api request rest "/services/data/v${hub_ver}/named-credentials/external-credentials/ALMDevOpsCenterHub" --target-org "$SRC" </dev/null > "$tmpd/hub.ec" ) &
fi

# Per-user sign-in. DevopsEnvironment rows are shared by everyone with access to the dev org, but the OAuth
# token behind each one belongs to a single user (the external credential's PerUserPrincipal). Ask, for the
# user running this, whether each connected environment's principal is Configured. The external credential
# carries the same developer name as the row's named credential. A failed or unreadable check is "unknown",
# never "notConfigured": only an explicit NotConfigured counts.
user_auth_json='{}'
if [ -n "$USER_AUTH_FILE" ]; then
  user_auth_json=$(cat "$USER_AUTH_FILE")
else
  api_ver="${DLC_API_VERSION:-68.0}"
  # One independent call per credential: run them side by side.
  i=0
  for nc in $(printf '%s' "$rows_json" | jq -r '.result.records[]? | select((.IsExpired // false) == false and (.OrgUrl // "") != "" and (.OrgIdentifier // "") != "")
      | (.NamedCredential // "") | gsub("<[^>]*>"; "") | gsub("^\\s+|\\s+$"; "") | select(. != "" and . != "ALMDevOpsCenterHub")' | sort -u); do
    i=$((i+1)); printf '%s' "$nc" > "$tmpd/u$i.k"
    (
      out=$(sfj $tmo sf api request rest "/services/data/v${api_ver}/named-credentials/external-credentials/${nc}" --target-org "$SRC" </dev/null)
      st=$(printf '%s' "$out" | jq -r '[.principals[]? | select(.principalType == "PerUserPrincipal") | .authenticationStatus][0]
          | if . == "Configured" then "configured" elif . == "NotConfigured" then "notConfigured" else "unknown" end' 2>/dev/null)
      printf '%s' "${st:-unknown}" > "$tmpd/u$i.v"
    ) &
  done
  wait
  for k in "$tmpd"/u*.k; do
    [ -f "$k" ] || continue
    user_auth_json=$(printf '%s' "$user_auth_json" | jq -c --arg k "$(cat "$k")" --arg s "$(cat "${k%.k}.v" 2>/dev/null || echo unknown)" '. + {($k): $s}')
  done
fi

# Lifecycle Center hub. Its row is dropped from environments[] (it is never a deploy target) but is reported
# separately as .hub so a list can show it, labelled. The hub counts as connected when its DevopsEnvironment row
# exists (made in DX Inspector) or its credential is readable (made by hub mode, which creates no row). The URL and
# this user's sign-in come from the credential. Unreadable pieces are null / "unknown".
hub_json=null
hub_name=$(printf '%s' "$rows_json" | jq -r '[.result.records[]? | select(((.NamedCredential // "") | gsub("<[^>]*>"; "") | gsub("^\\s+|\\s+$"; "")) == "ALMDevOpsCenterHub") | .Name][0] // ""')
hub_present=0; [ -n "$hub_name" ] && hub_present=1
hub_url=""; hub_auth=unknown
if [ -n "$USER_AUTH_FILE" ]; then
  [ "$hub_present" = 1 ] && hub_auth=$(printf '%s' "$user_auth_json" | jq -r '.ALMDevOpsCenterHub // "unknown"')
else
  wait
  hub_url=$(jq -r '.calloutUrl // empty' "$tmpd/hub.nc" 2>/dev/null)
  [ -n "$hub_url" ] && hub_present=1
  if [ "$hub_present" = 1 ]; then
    hub_auth=$(jq -r '[.principals[]? | select(.principalType == "PerUserPrincipal") | .authenticationStatus][0]
        | if . == "Configured" then "configured" elif . == "NotConfigured" then "notConfigured" else "unknown" end' "$tmpd/hub.ec" 2>/dev/null)
  fi
fi
if [ "$hub_present" = 1 ]; then
  # CLI access by alias exists only if something registered the row's name as an alias here (Core skips names
  # with spaces today). "conflict" = an alias of that name points at a different org than the hub.
  hub_host=$(printf '%s' "$hub_url" | sed -E 's#^https?://##; s#[/?].*$##' | tr 'A-Z' 'a-z')
  hub_alias=unknown
  if [ "$aliases_json" != null ] && [ -n "$hub_name" ]; then
    hub_alias=$(printf '%s' "$aliases_json" | jq -r --arg n "$hub_name" --arg h "$hub_host" \
      '[.[] | select(.alias == $n)][0] as $x | if $x == null then "missing" elif ($h != "" and ($x.host // "") != "" and $x.host != $h) then "conflict" else "registered" end')
  fi
  hub_json=$(jq -nc --arg u "$hub_url" --arg a "${hub_auth:-unknown}" --arg w "$hub_alias" --arg n "$hub_name" \
    '{label: "Lifecycle Center (Production Org)", url: (if $u == "" then null else $u end), userAuth: $a, workspaceAlias: $w, cliAlias: (if $n == "" then null else $n end), isDeployTarget: false}')
fi

# Identifier -> comparable keys: org id (first 15), host, and a lowercase name.
# Local alias or username: expand through `sf org display` to its org id and host.
id15=""; host=""; name=""
if [ -n "$IDENT" ]; then
  if printf '%s' "$IDENT" | grep -Eq '^00D[A-Za-z0-9]{12}([A-Za-z0-9]{3})?$'; then
    id15="${IDENT:0:15}"
  elif printf '%s' "$IDENT" | grep -Eiq '^https?://' \
       || printf '%s' "$IDENT" | grep -Eiq '^[A-Za-z0-9.-]+\.(salesforce\.com|salesforce-setup\.com|force\.com|pc-rnd\.salesforce\.com)(/.*)?$'; then
    host=$(printf '%s' "$IDENT" | sed -E 's#^[Hh][Tt][Tt][Pp][Ss]?://##; s#[/?].*$##' | tr 'A-Z' 'a-z')
  else
    # Environment name, alias, or username. An authorized alias also yields an org id and host.
    name=$(printf '%s' "$IDENT" | tr 'A-Z' 'a-z')
    exp=$(sfj sf org display --target-org "$IDENT" --json) && {
      id15=$(printf '%s' "$exp" | jq -r '.result.id // empty | .[0:15]')
      host=$(printf '%s' "$exp" | jq -r '.result.instanceUrl // empty' | sed -E 's#^https?://##')
      # A resolved org is matched by identity only: an environment that merely shares its name is another org.
      [ -n "$id15" ] && name=""
    }
  fi
fi

jq -n \
  --argjson source "$source_obj" \
  --argjson rows "$rows_json" \
  --argjson aliases "$aliases_json" \
  --argjson sessions "$sessions_json" \
  --argjson userauth "$user_auth_json" \
  --argjson hub "$hub_json" \
  --arg ident "$IDENT" --arg id15 "$id15" --arg host "$host" --arg name "$name" '
  # setup and lightning hosts point at the same org as the My Domain host
  def norm: ascii_downcase | sub("^https?://"; "") | sub("[/?].*$"; "")
            | sub("\\.salesforce-setup\\.com$"; ".salesforce.com")
            | sub("\\.lightning\\.force\\.com$"; ".my.salesforce.com");
  # expired = retired or replaced by an environment swap (not an OAuth expiry).
  # unauthenticated = connect never finished: the PATCH fills OrgUrl and OrgIdentifier.
  # The DevOps Center hub row is created with only the fixed hub NC (no OrgUrl) and is the control
  # plane, not a deploy target, so it is dropped before listing or matching (also by its fixed
  # name while it has no OrgUrl, in case its credential was removed).
  # NamedCredential is plain text in the API; strip an <a> wrapper in case a UI layer added one.
  def ncname: ((.NamedCredential // "") | gsub("<[^>]*>"; "") | gsub("^\\s+|\\s+$"; ""));
  def state: if (.IsExpired == true) then "expired"
             elif ((ncname == "") or (.OrgUrl // "") == "" or (.OrgIdentifier // "") == "") then "unauthenticated"
             else "selectable" end;
  # The alias that gives this workspace a login for the environment: one named like it, else any alias on its org.
  # A name match only counts when it points at the same org; an alias carrying the environment name, but on
  # another org, is a collision (aliasConflict), never a login for this environment.
  def namedAlias: (.Name // "") as $n | ([ $aliases[]? | select(.alias == $n) ][0]);
  def aliasConflict: (namedAlias) as $a | ((.OrgIdentifier // "")[0:15]) as $o
      | ($a != null and $o != "" and ($a.orgId // "") != "" and $a.orgId != $o);
  def workspaceLogin: (.Name // "") as $n | ((.OrgIdentifier // "")[0:15]) as $o
      | ( if aliasConflict then null else (namedAlias | if . == null then null else .alias end) end
          // (if $o == "" then null else [ $aliases[]? | select(.orgId == $o) | .alias ][0] end) );
  [ ($rows.result.records // [])[] | select(ncname != "ALMDevOpsCenterHub" and ((.Name // "") != "Doce Hub Environment" or (.OrgUrl // "") != "")) ] as $recs
  | ($host | if . == "" then "" else norm end) as $h
  | [ $recs[] | {
        id: .Id, name: .Name, orgType: .OrgType,
        orgUrl: (.OrgUrl // null),
        orgId: (.OrgIdentifier // null),
        namedCredential: (ncname | if . == "" then null else . end),
        state: state,
        workspaceAlias: ( if $aliases == null then "unknown"
                          elif (workspaceLogin != null) then "registered"
                          else "missing" end ),
        workspaceAliasName: (if $aliases == null then null else workspaceLogin end),
        aliasConflict: (if $aliases == null then false else aliasConflict end),
        userAuth: (if state == "selectable" then ($userauth[ncname] // "unknown") else null end),
        session: ( (workspaceLogin) as $a | if $a == null then null else ($sessions[$a] // "unknown") end ),
        readiness: ( if state == "expired" then "retired"
                     elif state == "unauthenticated" then "needs-signin"
                     elif ($userauth[ncname] // "unknown") == "notConfigured" then "needs-my-signin"
                     elif $aliases == null then "unverified"
                     elif aliasConflict and workspaceLogin == null then "alias-conflict"
                     elif workspaceLogin == null then "needs-sync"
                     elif $sessions[workspaceLogin] == "expired" then "needs-refresh"
                     else "ready" end ),
        isSource: ((.OrgIdentifier // "")[0:15] == ($source.orgId // "")[0:15] and (.OrgIdentifier // "") != "")
    } ] as $envs
  | ( if $ident == "" then []
      else [ $envs[] | select(
               ($id15 != "" and ((.orgId // "")[0:15] == $id15))
            or ($h != "" and ((.orgUrl // "") != "") and ((.orgUrl | norm) == $h))
            or ($name != "" and ((.name | ascii_downcase) == $name))) ]
      end ) as $m
  | { source: $source,
      environments: $envs,
      hub: $hub,
      identifier: $ident,
      matchStatus: ( if $ident == "" then "none-requested"
                     elif ($m | length) == 0 then "not-connected"
                     elif ($m | length) > 1 then "ambiguous"
                     else "matched" end ),
      matches: $m,
      match: (if ($m | length) == 1 then $m[0] else null end),
      sourceMatched: ( $ident != "" and
        ( ($id15 != "" and $id15 == ($source.orgId // "")[0:15])
       or ($h != "" and (($source.instanceUrl // "") | norm) == $h)
       or ($name != "" and $name == ($source.alias | ascii_downcase))
       or (($m | length) == 1 and $m[0].isSource) ) ) }'
