#!/usr/bin/env bash
#
# Komaci offline static analysis runner
#
# Runs @salesforce/eslint-plugin-lwc-graph-analyzer against an LWC bundle
# with the plugin's recommended ruleset and emits ESLint's JSON
# formatter output on stdout.
#
# The plugin's `bundleAnalyzer` processor expects the JS file to live
# next to its sibling HTML templates so the offline data graph can be
# resolved across the bundle.
#
# Plugin + ESLint versions are pinned in scripts/package.json and
# installed into scripts/node_modules on first run so the runner is
# isolated from whatever versions the host project happens to ship.
#
# Usage:
#   run-komaci.sh path/to/component.js
#
# Arguments:
#   $1  Path to the LWC component's JS file (required). The component's
#       sibling HTML templates must live in the same directory; the
#       plugin discovers them automatically via the bundle processor.
#
# Environment:
#   KOMACI_ESLINT_BIN   Override the eslint binary (default: scripts/node_modules/.bin/eslint)
#
# Output:
#   ESLint --format json on stdout. Non-zero exit if eslint reports
#   errors; the JSON is still emitted on stdout in either case.

set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 path/to/component.js" >&2
  exit 2
fi

JS_PATH="$1"

if [ ! -f "$JS_PATH" ]; then
  echo "Error: $JS_PATH does not exist" >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG_PATH="$SCRIPT_DIR/komaci.config.mjs"
PLUGIN_DIR="$SCRIPT_DIR/node_modules/@salesforce/eslint-plugin-lwc-graph-analyzer"

# Install the pinned ESLint + plugin versions on first run. We resolve
# them from SCRIPT_DIR so Node ESM picks up the right copy regardless
# of the caller's cwd or the host project's node_modules.
if [ ! -d "$PLUGIN_DIR" ]; then
  echo "Installing pinned Komaci runner deps in $SCRIPT_DIR ..." >&2
  (cd "$SCRIPT_DIR" && npm install --no-fund --no-save --silent) >&2
fi

ESLINT="${KOMACI_ESLINT_BIN:-$SCRIPT_DIR/node_modules/.bin/eslint}"

# Run eslint with the plugin's recommended config and emit JSON.
# `--no-config-lookup` ignores any host-project ESLint config so only
# the Komaci recommended ruleset applies; `--no-error-on-unmatched-pattern`
# avoids hard failure if the component path is empty.
$ESLINT \
  --no-config-lookup \
  --no-error-on-unmatched-pattern \
  --config "$CONFIG_PATH" \
  --format json \
  "$JS_PATH"
