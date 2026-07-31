#!/bin/bash
# Verifies that a UI bundle was created under force-app/main/default/uiBundles/
# (and not at the repo root, which would be non-deployable), AND that the
# scaffold itself is complete (package.json, src/, index.html present) — not
# just a hand-authored metadata-only directory.
#
# If a custom output directory was used (--output-dir on the scaffold command),
# pass it as the second argument. The script then verifies the bundle exists
# there instead of assuming the default location.

set -e

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "ERROR: Bundle name required"
  echo "Usage: bash verify-bundle-location.sh <BundleName> [<CustomOutputDir>]"
  exit 1
fi

BUNDLE_NAME="$1"
CUSTOM_OUTPUT_DIR="${2:-}"

# Checks that the scaffold actually produced a full React project, not just
# hand-written metadata files. Returns 1 (and prints guidance) if incomplete.
# Pass a second argument with the --output-dir value when checking a bundle
# in a custom location, so the remediation command matches where the bundle
# actually needs to end up rather than always pointing at the default path.
check_scaffold_complete() {
  local bundle_path="$1"
  local output_dir="${2:-}"
  local missing=()
  [[ -f "$bundle_path/package.json" ]] || missing+=("package.json")
  [[ -d "$bundle_path/src" ]] || missing+=("src/")
  [[ -f "$bundle_path/index.html" ]] || missing+=("index.html")

  if [[ ${#missing[@]} -gt 0 ]]; then
    local scaffold_cmd="sf template generate ui-bundle -n $BUNDLE_NAME --template reactbasic"
    if [[ -n "$output_dir" ]]; then
      scaffold_cmd="$scaffold_cmd --output-dir \"$output_dir\""
    fi
    echo "ERROR: Bundle found at $bundle_path, but the scaffold is incomplete. Missing:" >&2
    printf '  - %s\n' "${missing[@]}" >&2
    echo "" >&2
    echo "This usually means 'sf template generate ui-bundle' was never run — metadata" >&2
    echo "files alone were hand-authored instead. Run the scaffold command now:" >&2
    echo "  $scaffold_cmd" >&2
    echo "Metadata files are configuration ON TOP of the scaffold, not a substitute for it." >&2
    return 1
  fi
  return 0
}

if [[ -n "$CUSTOM_OUTPUT_DIR" ]]; then
  CUSTOM_PATH="$CUSTOM_OUTPUT_DIR/$BUNDLE_NAME"
  if [[ -d "$CUSTOM_PATH" ]]; then
    if check_scaffold_complete "$CUSTOM_PATH" "$CUSTOM_OUTPUT_DIR"; then
      echo "OK: Bundle found at $CUSTOM_PATH (custom output-dir location, scaffold complete)"
      exit 0
    fi
    exit 1
  fi
  echo "ERROR: Bundle not found at custom output-dir location: $CUSTOM_PATH"
  echo "Check that --output-dir matched what was passed to the scaffold command."
  exit 1
fi

EXPECTED_PATH="force-app/main/default/uiBundles/$BUNDLE_NAME"
WRONG_PATH="uiBundles/$BUNDLE_NAME"

if [[ -d "$EXPECTED_PATH" ]]; then
  if check_scaffold_complete "$EXPECTED_PATH"; then
    echo "OK: Bundle found at $EXPECTED_PATH (deployable location, scaffold complete)"
    exit 0
  fi
  exit 1
fi

if [[ -d "$WRONG_PATH" ]]; then
  echo "ERROR: Bundle found at repo root: $WRONG_PATH"
  echo "This location is NOT deployable. The SFDX deploy command will not find it."
  echo ""
  echo "To fix: Move the bundle to force-app/main/default/uiBundles/"
  echo "  mkdir -p force-app/main/default/uiBundles/ && mv $WRONG_PATH $EXPECTED_PATH"
  echo ""
  check_scaffold_complete "$WRONG_PATH" || true
  exit 1
fi

echo "ERROR: Bundle not found at either location:"
echo "  - Expected: $EXPECTED_PATH"
echo "  - Also checked: $WRONG_PATH"
echo ""
echo "If a custom --output-dir was used, re-run this script with that directory"
echo "as the second argument: bash verify-bundle-location.sh $BUNDLE_NAME <CustomOutputDir>"
echo ""
echo "Otherwise, the scaffold command may have failed. Check for errors above."
exit 1
