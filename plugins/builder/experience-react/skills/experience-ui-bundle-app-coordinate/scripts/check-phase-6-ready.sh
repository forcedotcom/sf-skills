#!/usr/bin/env bash
# Verify Phase 6 (Deployment) prerequisites are met
# Exit 0 if ready, exit 1 with error message if not ready

set -e

BUNDLE_DIR=$(find force-app/main/default/uiBundles -mindepth 1 -maxdepth 1 -type d 2>/dev/null | head -1)

if [ -z "$BUNDLE_DIR" ]; then
  echo "ERROR: Phase 6 cannot run: No UI bundle directory found (Phase 1 not complete)"
  exit 1
fi

# Check build artifact exists
if [ ! -f "$BUNDLE_DIR/dist/index.html" ]; then
  echo "ERROR: Phase 6 cannot run: No dist/index.html found (Phase 4 build not complete)"
  exit 1
fi

# Check org authentication
if ! sf org display --json >/dev/null 2>&1; then
  echo "ERROR: Phase 6 cannot run: No authenticated org found (run: sf org login web)"
  exit 1
fi

# Check hosting target is set
if ! grep -q '<target>' "$BUNDLE_DIR"/*.uibundle-meta.xml 2>/dev/null; then
  echo "ERROR: Phase 6 cannot run: .uibundle-meta.xml missing <target> element (Phase 1 not complete)"
  exit 1
fi

echo "SUCCESS: Phase 6 ready: All deployment prerequisites met"
exit 0
