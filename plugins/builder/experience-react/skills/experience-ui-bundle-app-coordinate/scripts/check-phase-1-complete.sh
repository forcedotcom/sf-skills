#!/usr/bin/env bash
# Verify Phase 1 (Scaffolding) completed successfully
# Exit 0 if complete, exit 1 with error message if incomplete

set -e

BUNDLE_DIR=$(find force-app/main/default/uiBundles -mindepth 1 -maxdepth 1 -type d 2>/dev/null | head -1)

if [ -z "$BUNDLE_DIR" ]; then
  echo "ERROR: Phase 1 incomplete: No UI bundle directory found in force-app/main/default/uiBundles/"
  exit 1
fi

if [ ! -d "$BUNDLE_DIR/src" ]; then
  echo "ERROR: Phase 1 incomplete: No src/ directory found in $BUNDLE_DIR"
  exit 1
fi

if ! ls "$BUNDLE_DIR"/*.uibundle-meta.xml >/dev/null 2>&1; then
  echo "ERROR: Phase 1 incomplete: No .uibundle-meta.xml file found in $BUNDLE_DIR"
  exit 1
fi

if ! grep -q '<target>' "$BUNDLE_DIR"/*.uibundle-meta.xml 2>/dev/null; then
  echo "ERROR: Phase 1 incomplete: .uibundle-meta.xml missing <target> element"
  exit 1
fi

if [ ! -f "$BUNDLE_DIR/package.json" ]; then
  echo "ERROR: Phase 1 incomplete: No package.json found in $BUNDLE_DIR"
  exit 1
fi

echo "SUCCESS: Phase 1 complete: Scaffold verified"
exit 0
