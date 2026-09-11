#!/usr/bin/env bash
# Prepare a minimal SFDX project work directory for Agentforce agent generation.
# `sf agent generate agent-spec` requires Salesforce project context before the
# authoring-bundle script has a chance to call ensure_sfdx_project.
# Usage: prepare-agent-workdir.sh [work-dir]
# Output: absolute work-dir path on stdout.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

if [[ "${1:-}" == "--help" ]]; then
  echo "Usage: prepare-agent-workdir.sh [work-dir]" >&2
  exit 0
fi

WORK_DIR="${1:-acc-voice-build}"
ensure_sfdx_project "$WORK_DIR"
mkdir -p "$WORK_DIR/specs"
cd "$WORK_DIR"
pwd
