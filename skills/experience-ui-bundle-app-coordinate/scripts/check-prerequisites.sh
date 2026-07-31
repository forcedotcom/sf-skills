#!/usr/bin/env bash
# Check prerequisites for UI Bundle app building
# Exit 0 if all prerequisites met, exit 1 with error message if any missing

set -e

# Check Node.js version (requires >= 20.x)
if ! command -v node >/dev/null 2>&1; then
  echo "ERROR: Node.js not found. Install Node.js >= 20.x"
  exit 1
fi

NODE_VERSION=$(node --version 2>/dev/null | sed 's/^v//' | cut -d. -f1)
if [ "$NODE_VERSION" -lt 20 ]; then
  echo "ERROR: Node.js version $NODE_VERSION detected. Requires >= 20.x"
  exit 1
fi

echo "SUCCESS: Node.js v${NODE_VERSION} meets the >= 20.x requirement"
exit 0
