#!/usr/bin/env bash
# Shared constants for the Agentforce Contact Center coordination scripts.
# Not invoked directly — sourced by the other scripts.
#
# All API calls go through `sf api request rest`, which uses the CLI's stored
# session for --target-org. Never extract the access token from `sf org display`.

set -euo pipefail

API_VERSION="v68.0"
NM_BASE="services/data/${API_VERSION}/connect/number-management/v1"

# URL-encode a value's spaces (sufficient for country/phoneType query params).
urlenc_spaces() { printf '%s' "${1// /%20}"; }

# XML-escape a value for safe interpolation into flow-template stringValue/label nodes.
# Free-text org data (queue names, agent labels) can contain &, <, >, ", ' — unescaped
# they produce malformed XML and an opaque `sf project deploy start` parse error.
# Escape & first so the entities emitted by the later rules aren't double-escaped.
xml_escape() { printf '%s' "$1" | sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g; s/"/\&quot;/g; s/'"'"'/\&apos;/g'; }

# Scaffold a minimal SFDX project at <dir> if one isn't already there. The Omni Flow path
# generates an agent authoring bundle and deploys RoutingFlows, both of which need a project
# context. sourceApiVersion is pinned to API_VERSION for consistency (v68).
ensure_sfdx_project() {
  local dir="$1"
  mkdir -p "$dir/force-app/main/default"
  if [[ ! -f "$dir/sfdx-project.json" ]]; then
    printf '%s\n' "{\"packageDirectories\":[{\"path\":\"force-app\",\"default\":true}],\"namespace\":\"\",\"sfdcLoginUrl\":\"https://login.salesforce.com\",\"sourceApiVersion\":\"${API_VERSION#v}\"}" \
      > "$dir/sfdx-project.json"
  fi
}

# Render a token template to stdout, replacing every {{KEY}} with the paired value.
# Usage: render_template <template-file> KEY=VALUE [KEY=VALUE ...]
# Plain string replacement (no regex) so XML/URL values pass through unchanged.
render_template() {
  local tmpl="$1"; shift
  local content pair key val
  content="$(<"$tmpl")"
  for pair in "$@"; do
    key="${pair%%=*}"; val="${pair#*=}"
    content="${content//\{\{${key}\}\}/${val}}"
  done
  printf '%s\n' "$content"
}
