#!/usr/bin/env bash
set -euo pipefail

PLUGIN_REPO="${PLUGIN_REPO:-https://github.com/Jaganpro/sf-cli-plugin-data360.git}"
BASE_DIR="${1:-${HOME}/.sf-community-tools/datacloud}"
PLUGIN_DIR="${BASE_DIR}/sf-cli-plugin-data360"
export SF_DATA_DIR="${SF_DATA_DIR:-${HOME}/.local/share/sf}"

need() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1" >&2
    exit 1
  }
}

need git
need node
need yarn
need sf
need npx

mkdir -p "${BASE_DIR}"

if [[ -d "${PLUGIN_DIR}/.git" ]]; then
  echo "Updating existing plugin checkout: ${PLUGIN_DIR}"
  git -C "${PLUGIN_DIR}" pull --ff-only
else
  echo "Cloning plugin into: ${PLUGIN_DIR}"
  git clone "${PLUGIN_REPO}" "${PLUGIN_DIR}"
fi

cd "${PLUGIN_DIR}"

echo "Installing dependencies..."
yarn install

echo "Compiling plugin..."
npx tsc

echo "Generating oclif command manifest..."
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
node "${SCRIPT_DIR}/generate-manifest.mjs" "${PLUGIN_DIR}"

echo "Linking plugin into Salesforce CLI..."
mkdir -p "${SF_DATA_DIR}"
sf plugins link .

echo "Verifying runtime..."
sf data360 man >/dev/null

echo "Done. Community Data Cloud runtime is linked."
echo "Location: ${PLUGIN_DIR}"
echo "Try: sf data360 man"
