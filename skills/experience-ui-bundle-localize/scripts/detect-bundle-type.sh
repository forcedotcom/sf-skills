#!/usr/bin/env bash
set -euo pipefail  # exit on error (-e), undefined vars (-u), and propagate pipeline failures (-o pipefail)
#
# detect-bundle-type.sh — Classify a UI Bundle as authenticated (supported) or
# a site (not yet supported) before localizing it.
#
# The bundle's type is decided by deterministic file and string checks, so run
# this rather than interpreting them by hand. It classifies in a fixed order and
# stops at the first hit:
#   - in-core internal: ui-bundle.json accessCheck starts with "LwrInternalApp." -> proceed
#   - B2E: a CustomApplication whose <uiBundle> names this bundle           -> proceed
#   - site: a digitalExperienceConfigs/*.digitalExperienceConfig-meta.xml   -> NOT supported, stop
#   - anything else: unbound / cannot auto-detect                           -> ask the user
#
# The B2E and site checks are package-local: CustomApplication and site config
# metadata are siblings of uiBundles/ under the package source path
# (e.g. force-app/main/default/{applications,uiBundles}/), so the script derives
# that metadata root from the bundle path rather than the current directory. If
# the bundle is bound elsewhere the script returns 2 (ask the user), the correct
# fallback. Do not gate on a <target> element inside *.uibundle-meta.xml;
# CLI-generated bundles do not carry it.
#
# Usage (pass the full path to the bundle dir; cwd does not matter):
#   bash <skill-dir>/scripts/detect-bundle-type.sh <path-to-uiBundles/<name>/ dir>
#
# Exit codes:
#   0  authenticated app (in-core internal or B2E) — proceed
#   1  site (B2C/B2B) — NOT supported; stop and tell the user
#   2  unbound / cannot auto-detect — ask the user to confirm the bundle is
#      an authenticated app (B2E or in-core internal); stop if they cannot

if [ "$#" -ne 1 ] || [ -z "${1:-}" ]; then
  echo "ERROR: pass exactly one bundle directory. Usage: detect-bundle-type.sh <path-to-uiBundles/<name>/ dir>" >&2
  exit 2
fi
bundleDir="${1%/}"
bundle=$(basename "$bundleDir")

# CustomApplication and site metadata sit beside uiBundles/ under the package
# source path, not at the cwd. Derive that metadata root from the bundle path:
# it's the parent of the uiBundles/ segment. Fall back to the cwd for a
# flattened layout with no uiBundles/ segment.
metaRoot="."
case "$bundleDir" in
  */uiBundles/*) metaRoot="${bundleDir%/uiBundles/*}" ;;
esac

if [ -f "${bundleDir}/ui-bundle.json" ] \
   && jq -e '(.accessCheck // "") | startswith("LwrInternalApp.")' "${bundleDir}/ui-bundle.json" >/dev/null 2>&1; then
  echo "in-core internal app -> proceed"; exit 0
elif grep -rlq --include='*.app-meta.xml' "<uiBundle>${bundle}</uiBundle>" "${metaRoot}/applications" 2>/dev/null; then
  echo "B2E (CustomApplication-bound) -> proceed"; exit 0
elif ls "${metaRoot}"/digitalExperienceConfigs/*.digitalExperienceConfig-meta.xml >/dev/null 2>&1; then
  echo "site (B2C/B2B) -> NOT supported; stop"; exit 1
else
  echo "unbound / cannot auto-detect -> ask the user"; exit 2
fi
