#!/usr/bin/env bash
set -euo pipefail  # exit on error (-e), undefined vars (-u), and propagate pipeline failures (-o pipefail)
#
# check-manifest-registered.sh — Confirm every t("Key") call site is registered
# in label-manifest.ts.
#
# An unregistered key renders as its own literal name at runtime with no error —
# the central silent-failure trap this skill exists to prevent. That check is a
# pure set comparison (call-site keys vs manifest keys), so run this rather than
# counting entries by hand.
#
# Keys are compared on their trailing segment: a manifest entry "c:Welcome_Text"
# matches a call site t("Welcome_Text") or t("c:Welcome_Text") either way. The
# manifest's boilerplate example comment is stripped first so a commented-out
# sample key does not mask a genuinely missing one.
#
# Usage (run from the UI bundle dir, or pass its src path):
#   bash <skill-dir>/scripts/check-manifest-registered.sh [src-dir]
#
# src-dir defaults to "src". label-manifest.ts is found anywhere under it.
#
# Exit codes (kept aligned with check-i18n-wired.sh so the workflow branches on
# the code, not the message text):
#   0  every t() key is registered (or there are no t() calls / no manifest to
#      cross-check — nothing to gate)
#   1  one or more t() keys are missing from the manifest — stop and register them
#  64  usage error — the source dir does not exist (bad argument or wrong cwd).
#      This is NOT a "keys missing" result; do not scaffold or register. Fix the
#      path and re-run. (64 = EX_USAGE, kept out of the 0/1 semantic range so
#      exit 1 uniquely means "keys missing".)

SRC_DIR="${1:-src}"
if [ ! -d "$SRC_DIR" ]; then
  echo "ERROR: source dir not found: $SRC_DIR (run from the UI bundle dir, or pass its src path)" >&2
  exit 64
fi

MANIFEST=$(find "$SRC_DIR" -type f -name 'label-manifest.ts' | head -1 || true)

# Collect t("Key") / t('Key') call sites from component files, keeping the
# trailing key segment (drop any "ns:" prefix). Use POSIX character classes and
# an explicit boundary, not \b / \s: BSD/macOS grep -E silently ignores those,
# which would miss call sites on a Mac (the platform this skill targets) and let
# an unregistered key slip through — the exact silent-fail this script guards.
# (^|[^A-Za-z0-9_]) before t( stops "insertText(" / "print(" matching as t(.
CALLED=$(grep -rhoE "(^|[^A-Za-z0-9_])t\([[:space:]]*[\"'\`][^\"'\`]+[\"'\`]" "$SRC_DIR" \
           --include='*.tsx' --include='*.jsx' 2>/dev/null \
         | sed -E "s/.*[\"'\`]([^\"'\`]+)[\"'\`].*/\1/; s/.*://" \
         | sort -u || true)

if [ -z "$CALLED" ]; then
  echo "no t() call sites to check (scenario may not require the manifest) -> proceed"
  exit 0
fi
if [ -z "$MANIFEST" ]; then
  echo "ERROR: t() call sites exist but no label-manifest.ts was found under $SRC_DIR -> register them" >&2
  echo "$CALLED" | sed 's/^/  missing: /' >&2
  exit 1
fi

# Manifest keys: strip comments first so a boilerplate example key (the scaffold
# ships one) does not count as registered and mask a genuinely missing key — the
# exact silent-fail this script guards. Block comments can span lines, so a
# line-based `s:/\*.*\*/::` misses a multi-line `/* ... */` around an example
# key; use an awk state machine that carries the in-comment flag across lines,
# then strip `//` line comments. Keys hold no `/`, so this never eats a key.
REGISTERED=$(awk '
               { s = $0 }
               {
                 out = ""
                 i = 1
                 n = length(s)
                 while (i <= n) {
                   if (incomment) {
                     if (substr(s, i, 2) == "*/") { incomment = 0; i += 2 }
                     else { i++ }
                   } else if (substr(s, i, 2) == "/*") {
                     incomment = 1; i += 2
                   } else {
                     out = out substr(s, i, 1); i++
                   }
                 }
                 print out
               }
             ' "$MANIFEST" \
             | sed -E 's://.*$::' \
             | grep -oE "[\"'\`][^\"'\`]+[\"'\`]" \
             | sed -E "s/[\"'\`]//g; s/.*://" \
             | sort -u || true)

MISSING=$(comm -23 <(echo "$CALLED") <(echo "$REGISTERED") || true)

if [ -n "$MISSING" ]; then
  echo "ERROR: t() keys not registered in label-manifest.ts (they render as literal key names at runtime):" >&2
  echo "$MISSING" | sed 's/^/  /' >&2
  exit 1
fi

echo "all $(echo "$CALLED" | wc -l | tr -d ' ') t() key(s) registered in the manifest -> proceed"
exit 0
