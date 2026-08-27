#!/bin/bash
# Validate a Shield Platform Encryption settings/field XML file for the two
# deterministic contracts this skill must never get wrong:
#   1. enableReplayDetection=true requires enableCacheOnlyKeys=true (one-way dependency)
#   2. encryptionScheme must be one of the four valid enum values
#
# Usage: validate-encryption-metadata.sh <file.xml>
#        validate-encryption-metadata.sh --help
# Output: prints "OK" on success; prints ERROR lines to stderr and exits 1 on failure.

set -euo pipefail

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  echo "Usage: validate-encryption-metadata.sh <file.xml>"
  echo "Checks: replay-detection dependency, encryptionScheme enum."
  exit 0
fi

FILE="${1:-}"
if [[ -z "$FILE" ]]; then
  echo "ERROR: no file given. Usage: validate-encryption-metadata.sh <file.xml>" >&2
  exit 1
fi
if [[ ! -f "$FILE" ]]; then
  echo "ERROR: file not found: $FILE" >&2
  exit 1
fi

errors=0

# 1. Replay-detection one-way dependency.
if grep -q '<enableReplayDetection>true</enableReplayDetection>' "$FILE"; then
  if ! grep -q '<enableCacheOnlyKeys>true</enableCacheOnlyKeys>' "$FILE"; then
    echo "ERROR: enableReplayDetection=true requires enableCacheOnlyKeys=true in the same file." >&2
    errors=$((errors + 1))
  fi
fi

# 2. encryptionScheme enum.
scheme=$(grep -oE '<encryptionScheme>[^<]*</encryptionScheme>' "$FILE" | sed -E 's/<\/?encryptionScheme>//g' || true)
if [[ -n "$scheme" ]]; then
  case "$scheme" in
    ProbabilisticEncryption|CaseSensitiveDeterministicEncryption|CaseInsensitiveDeterministicEncryption|None) ;;
    *)
      echo "ERROR: invalid encryptionScheme '$scheme'. Must be one of: ProbabilisticEncryption, CaseSensitiveDeterministicEncryption, CaseInsensitiveDeterministicEncryption, None." >&2
      errors=$((errors + 1))
      ;;
  esac
fi

if [[ "$errors" -gt 0 ]]; then
  exit 1
fi
echo "OK"
