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
# This script is framework-agnostic EXCEPT for the call-site extraction (which
# file extensions to scan, and the translation-call grammar). That single block
# is selected by --framework; the rest — find the manifest, strip its comments,
# set-compare called-vs-registered keys, report missing — is shared. React's
# grammar is t("Key") in .tsx/.jsx; Angular's ngx-translate grammar is the
# `| translate` pipe and `[translate]="'Key'"` binding in .html/.ts templates
# plus translate.instant/get/stream("Key") service calls in .ts (see
# references/angular/localize.md).
#
# Usage (run from the UI bundle dir, or pass its src path):
#   bash <skill-dir>/scripts/check-manifest-registered.sh [--framework react|angular] [src-dir]
#
# --framework defaults to "react". src-dir defaults to "src"; label-manifest.ts
# is found anywhere under it. Order of the flag and src-dir does not matter.
#
# Exit codes (kept aligned with references/react/check-i18n-wired.sh so the
# workflow branches on the code, not the message text):
#   0  every t() key is registered (or there are no t() calls / no manifest to
#      cross-check — nothing to gate)
#   1  one or more call-site keys are missing from the manifest — stop and register them
#  64  usage error — the source dir does not exist, an option is malformed, or the
#      requested framework is unknown. This is NOT a "keys missing" result; do not
#      scaffold or register. Fix the input and re-run. (64 = EX_USAGE, kept out of
#      the 0/1 semantic range so exit 1 uniquely means "keys missing".)

FRAMEWORK="react"
SRC_DIR=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --framework)
      [ "$#" -ge 2 ] || { echo "ERROR: --framework requires a value (react|angular)" >&2; exit 64; }
      FRAMEWORK="$2"; shift 2 ;;
    --framework=*) FRAMEWORK="${1#*=}"; shift ;;
    -*) echo "ERROR: unknown option: $1" >&2; exit 64 ;;
    *)
      if [ -z "$SRC_DIR" ]; then SRC_DIR="$1"; shift
      else echo "ERROR: unexpected extra argument: $1" >&2; exit 64; fi ;;
  esac
done
SRC_DIR="${SRC_DIR:-src}"

# Select the framework's call-site grammar. CALL_LABEL is the human name for a
# call site, used only in report messages so they read for the selected framework
# (React `t()`, Angular `translate`) instead of hardcoding one framework's
# convention in this otherwise-shared script. The extraction block itself is
# selected by FRAMEWORK further below.
case "$FRAMEWORK" in
  react) CALL_LABEL='t()' ;;        # extraction below is React's t("Key") grammar
  angular) CALL_LABEL='translate' ;; # extraction below is ngx-translate's grammar
  *) echo "ERROR: unknown framework: '$FRAMEWORK' (expected: react | angular)" >&2; exit 64 ;;
esac

if [ ! -d "$SRC_DIR" ]; then
  echo "ERROR: source dir not found: $SRC_DIR (run from the UI bundle dir, or pass its src path)" >&2
  exit 64
fi

MANIFEST=$(find "$SRC_DIR" -type f -name 'label-manifest.ts' | head -1 || true)

# Collect translation call sites, keeping the trailing key segment (drop any
# "ns:" prefix). Use POSIX character classes and explicit boundaries, not \b / \s:
# BSD/macOS grep -E silently ignores those, which would miss call sites on a Mac
# (the platform this skill targets) and let an unregistered key slip through —
# the exact silent-fail this script guards.
if [ "$FRAMEWORK" = "react" ]; then
  # React: t("Key") / t('Key') in .tsx/.jsx. (^|[^A-Za-z0-9_]) before t( stops
  # "insertText(" / "print(" from matching as t(.
  CALLED=$(grep -rhoE "(^|[^A-Za-z0-9_])t\([[:space:]]*[\"'\`][^\"'\`]+[\"'\`]" "$SRC_DIR" \
             --include='*.tsx' --include='*.jsx' 2>/dev/null \
           | sed -E "s/.*[\"'\`]([^\"'\`]+)[\"'\`].*/\1/; s/.*://" \
           | sort -u || true)
else
  # Angular / ngx-translate: keys appear in .html templates (and inline .ts
  # templates) via the `translate` pipe and the `[translate]` binding, and in .ts
  # via TranslateService.instant/get/stream(...). Each pass below emits a fragment
  # scoped to the KEY position (it stops before any trailing params object), then
  # a shared token extractor pulls the quoted key(s). Scoping keeps a params
  # object like {'0': x} — or an unrelated Map/HttpClient/FormGroup `.get(...)` —
  # from being mistaken for a key. The service-call passes require a `translate`-
  # shaped receiver ([Tt]ranslate...) precisely because a bare `.get(` is far too
  # common in TS to treat as a translation call.
  CALLED=$(
    {
      # pipe form:            'Key' | translate       (.html + inline templates)
      grep -rhoE "[\"'\`][^\"'\`]+[\"'\`][[:space:]]*\|[[:space:]]*translate" "$SRC_DIR" \
        --include='*.html' --include='*.ts' 2>/dev/null || true
      # property-binding form: [translate]="'Key'"    (literal string only)
      grep -rhoE "\[translate\][[:space:]]*=[[:space:]]*[\"'][[:space:]]*['\"\`][^'\"\`]+['\"\`]" "$SRC_DIR" \
        --include='*.html' --include='*.ts' 2>/dev/null || true
      # service call, single key:  translate.instant/get/stream('Key'
      grep -rhoE "[Tt]ranslate[A-Za-z0-9_]*[[:space:]]*\.[[:space:]]*(instant|get|stream)[[:space:]]*\([[:space:]]*[\"'\`][^\"'\`]+[\"'\`]" "$SRC_DIR" \
        --include='*.ts' 2>/dev/null || true
      # service call, array keys:  translate.get(['A','B'])  (stops at the ])
      grep -rhoE "[Tt]ranslate[A-Za-z0-9_]*[[:space:]]*\.[[:space:]]*(instant|get|stream)[[:space:]]*\([[:space:]]*\[[^]]*\]" "$SRC_DIR" \
        --include='*.ts' 2>/dev/null || true
    } \
    | grep -oE "['\"\`][^'\"\`]+['\"\`]" \
    | sed -E "s/['\"\`]//g; s/.*://" \
    | sort -u || true
  )
fi

if [ -z "$CALLED" ]; then
  echo "no ${CALL_LABEL} call sites to check (scenario may not require the manifest) -> proceed"
  exit 0
fi
if [ -z "$MANIFEST" ]; then
  echo "ERROR: ${CALL_LABEL} call sites exist but no label-manifest.ts was found under $SRC_DIR -> register them" >&2
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
  echo "ERROR: ${CALL_LABEL} keys not registered in label-manifest.ts (they render as literal key names at runtime):" >&2
  echo "$MISSING" | sed 's/^/  /' >&2
  exit 1
fi

echo "all $(echo "$CALLED" | wc -l | tr -d ' ') ${CALL_LABEL} key(s) registered in the manifest -> proceed"
exit 0
