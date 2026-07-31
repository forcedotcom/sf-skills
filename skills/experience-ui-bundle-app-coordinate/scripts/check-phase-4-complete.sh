#!/usr/bin/env bash
# Verify Phase 4 (UI) completed successfully
# Exit 0 if complete, exit 1 with error message if incomplete

set -e

BUNDLE_DIR=$(find force-app/main/default/uiBundles -mindepth 1 -maxdepth 1 -type d 2>/dev/null | head -1)

if [ -z "$BUNDLE_DIR" ]; then
  echo "ERROR: Phase 4 cannot run: No UI bundle directory found (Phase 1 not complete)"
  exit 1
fi

# Check Phase 1 scaffold prerequisites
if [ ! -f "$BUNDLE_DIR/package.json" ]; then
  echo "ERROR: Phase 4 cannot run: No package.json found (Phase 1 not complete)"
  exit 1
fi

if ! grep -q '"react"' "$BUNDLE_DIR/package.json" 2>/dev/null; then
  echo "ERROR: Phase 4 cannot run: React dependencies not installed in package.json"
  exit 1
fi

# Check Phase 4 completion
if [ ! -f "$BUNDLE_DIR/src/App.tsx" ]; then
  echo "ERROR: Phase 4 incomplete: No App.tsx found in $BUNDLE_DIR/src/"
  exit 1
fi

if [ ! -d "$BUNDLE_DIR/src/pages" ]; then
  echo "ERROR: Phase 4 incomplete: No pages/ directory found in $BUNDLE_DIR/src/"
  exit 1
fi

if [ -z "$(find "$BUNDLE_DIR/src/pages" -name '*.tsx' 2>/dev/null)" ]; then
  echo "ERROR: Phase 4 incomplete: No .tsx files found in pages/ directory"
  exit 1
fi

if [ ! -f "$BUNDLE_DIR/dist/index.html" ]; then
  echo "ERROR: Phase 4 incomplete: No dist/index.html found (build not complete)"
  exit 1
fi

echo "SUCCESS: Phase 4 complete: UI verified"
exit 0
