#!/usr/bin/env bash
# Deterministic wrapper for runtime DOM extraction. Handles the two
# operations that are pure string ops (and therefore should not be left to
# an LLM):
#   1. Convert a component name to its LWC selector (camelCase / PascalCase
#      → kebab-case, prefixed with `c-`).
#   2. Wrap an already-extracted DOM subtree in the exact
#      DOM_OUTPUT_START / DOM_OUTPUT_END markers the harness expects.
#
# Actual DOM traversal must be done by the caller's browser-automation
# driver (Playwright / Puppeteer / CDP) since the agent harness controls
# the browser. Feed the extracted HTML into this script on stdin and its
# marker-wrapped output goes to stdout.
#
# Usage:
#   # 1. Compute the selector for a component
#   <skill_dir>/scripts/extract-dom.sh selector accountTile
#     → c-account-tile
#
#   # 2. Wrap an app-scope subtree captured by the browser driver
#   printf '%s' "$html_subtree" | <skill_dir>/scripts/extract-dom.sh wrap app
#
#   # 3. Wrap a component-scope subtree (selector inferred from the name)
#   printf '%s' "$html_subtree" | <skill_dir>/scripts/extract-dom.sh wrap component accountTile

set -euo pipefail

usage() {
  cat >&2 <<'EOF'
usage:
  extract-dom.sh selector <componentName>
  extract-dom.sh wrap app
  extract-dom.sh wrap component <componentName>
EOF
  exit 2
}

to_selector() {
  local name="$1"
  python3 - "$name" <<'PY'
import re, sys
name = sys.argv[1]
kebab = re.sub(r'(?<!^)(?=[A-Z])', '-', name).lower()
kebab = re.sub(r'[^a-z0-9]+', '-', kebab).strip('-')
print(f"c-{kebab}")
PY
}

cmd="${1:-}"
case "$cmd" in
  selector)
    [[ $# -eq 2 ]] || usage
    to_selector "$2"
    ;;
  wrap)
    scope="${2:-}"
    case "$scope" in
      app)
        [[ $# -eq 2 ]] || usage
        printf 'DOM_OUTPUT_START\n'
        cat
        printf '\nDOM_OUTPUT_END\n'
        ;;
      component)
        [[ $# -eq 3 ]] || usage
        selector="$(to_selector "$3")"
        printf 'DOM_OUTPUT_START\n<%s>' "$selector"
        cat
        printf '</%s>\nDOM_OUTPUT_END\n' "$selector"
        ;;
      *)
        usage
        ;;
    esac
    ;;
  *)
    usage
    ;;
esac
