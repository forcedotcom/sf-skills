#!/usr/bin/env bash
# Resolve the existing path of a UIBundle's meta XML file.
#
# UIBundle metadata may live at either the nested bundle-style path
# (uiBundles/{appName}/{appName}.uibundle-meta.xml) or, in older/hand-authored
# projects, the flat path (uiBundles/{appName}.uibundle-meta.xml). This script
# performs the deterministic file-existence check and prints whichever path
# already exists, preferring the nested layout.
#
# Usage: scripts/resolve-uibundle-path.sh <appName>

set -euo pipefail

APP="${1:-}"
if [ -z "$APP" ]; then
  echo "ERROR: appName argument is required" >&2
  exit 1
fi

NESTED="uiBundles/${APP}/${APP}.uibundle-meta.xml"
FLAT="uiBundles/${APP}.uibundle-meta.xml"

if [ -f "$NESTED" ]; then
  echo "$NESTED"
elif [ -f "$FLAT" ]; then
  echo "$FLAT"
else
  echo "ERROR: no .uibundle-meta.xml found for $APP" >&2
  exit 1
fi
