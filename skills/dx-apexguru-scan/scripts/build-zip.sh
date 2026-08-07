#!/usr/bin/env bash
# Package a customer's Apex into a .zip for the ApexGuru SFAP Scan API.
#
# The API walks the ENTIRE uploaded archive and extracts every Apex file it
# finds — it does NOT require a force-app/ tree at the root (confirmed against
# production). So we scan whatever the customer points us at: collect every
# Apex source file (`.cls` / `.trigger`) under <project-root>, preserving its
# relative path, and zip that. A plain sfdx project, a loose folder of classes,
# or a deeply-nested monorepo subtree all work.
#
# Usage: bash build-zip.sh <project-root> <output-zip-path>
#
# <project-root> is any folder that contains Apex somewhere beneath it (an sfdx
# project root, a force-app/ subtree, or an ad-hoc folder of .cls files).
#
# Output (stdout, single line JSON):
#   {"zip":"<abs path>","bytes":123,"humanSize":"1.2M","apexFileCount":N,"scanRoot":"<path>"}
# On failure: {"error":"...","hint":"..."} and exit 1.
#
# API limits enforced here (fail fast, before upload): 200MB compressed.
# (1GB decompressed is enforced server-side; we cannot cheaply predict it.)
set -euo pipefail

MAX_COMPRESSED_BYTES=$((200 * 1024 * 1024))

PROJECT_ROOT="${1:-}"
OUT_ZIP="${2:-}"

if [ -z "$PROJECT_ROOT" ] || [ -z "$OUT_ZIP" ]; then
  printf '{"error":"missing args","hint":"usage: build-zip.sh <project-root> <output-zip-path>"}\n'
  exit 1
fi

if [ ! -d "$PROJECT_ROOT" ]; then
  printf '{"error":"project root not found: %s","hint":"pass a folder that contains Apex (.cls/.trigger) files"}\n' "$PROJECT_ROOT"
  exit 1
fi

# Resolve absolute paths.
ROOT_ABS="$(cd "$PROJECT_ROOT" && pwd)"
case "$OUT_ZIP" in
  /*) OUT_ABS="$OUT_ZIP" ;;
  *)  OUT_ABS="$(pwd)/$OUT_ZIP" ;;
esac

rm -f "$OUT_ABS"

# The set of Apex source files under the root (relative paths, noise excluded).
# Defined once as a function so the count pass and the zip pass use the exact
# same list. `zip -@` reads a newline-delimited list, so we emit newline-
# terminated relative paths with the leading "./" stripped.
apex_files() {
  find . -type f \( -name '*.cls' -o -name '*.trigger' \) \
    -not -path '*/node_modules/*' -not -path '*/.git/*' -print \
    | sed 's#^\./##'
}

APEX_COUNT=0
while IFS= read -r _; do
  APEX_COUNT=$((APEX_COUNT + 1))
done < <(cd "$ROOT_ABS" && apex_files)

if [ "$APEX_COUNT" -eq 0 ]; then
  printf '{"error":"no Apex (.cls/.trigger) files found under %s","hint":"point build-zip.sh at a folder that contains Apex classes or triggers"}\n' "$ROOT_ABS"
  exit 1
fi

# Feed the file list to zip via stdin (-@) so we never hit ARG_MAX on large
# projects. Paths are relative to ROOT_ABS, so the archive mirrors the project
# layout (the API re-walks it regardless of structure).
( cd "$ROOT_ABS" && apex_files | zip -q -X "$OUT_ABS" -@ >/dev/null )

if [ ! -f "$OUT_ABS" ]; then
  printf '{"error":"zip creation failed","hint":"check write permissions for %s"}\n' "$OUT_ABS"
  exit 1
fi

BYTES=$(wc -c < "$OUT_ABS" | tr -d '[:space:]')
if [ "$BYTES" -gt "$MAX_COMPRESSED_BYTES" ]; then
  printf '{"error":"zip is %s bytes, over the 200MB compressed limit","hint":"scope the scan to a subset of the project or split it"}\n' "$BYTES"
  exit 1
fi

HUMAN=$(echo "$BYTES" | awk '{ split("B K M G", u); s=$1; i=1; while (s>=1024 && i<4){s/=1024; i++} printf (i==1 ? "%d%s" : "%.1f%s"), s, u[i] }')

jq -cn --arg zip "$OUT_ABS" --argjson bytes "$BYTES" --arg human "$HUMAN" --argjson count "$APEX_COUNT" --arg root "$ROOT_ABS" \
  '{zip:$zip, bytes:$bytes, humanSize:$human, apexFileCount:$count, scanRoot:$root}'
