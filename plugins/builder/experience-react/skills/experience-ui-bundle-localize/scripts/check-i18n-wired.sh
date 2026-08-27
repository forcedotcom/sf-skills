#!/usr/bin/env bash
set -euo pipefail  # exit on error (-e), undefined vars (-u), and propagate pipeline failures (-o pipefail)
#
# check-i18n-wired.sh — Confirm the i18n init exists and is called at boot.
#
# Whether the app already has i18n wiring is a file-existence plus call-site
# check, so run this rather than reading for it by hand. It looks for an init
# file that defines initI18n() and for a boot-time initI18n() call in an entry
# file.
#
# Usage (run from the UI bundle dir, or pass its src path):
#   bash <skill-dir>/scripts/check-i18n-wired.sh [src-dir]
#
# src-dir defaults to "src".
#
# When wiring exists, it also reports whether the label manifest is imported AND
# actually passed into the SalesforceBackend's backendOptions (not merely
# imported and left unused), so the reconcile decision is a script result rather
# than a by-hand read.
#
# Exit codes (each actionable state has its own code so the workflow branches on
# the code, not on the message text):
#   0  fully wired — initI18n() defined, called at boot, AND the manifest is
#      passed into the SalesforceBackend's backendOptions. Just add new keys.
#   1  no i18n init found — no initI18n() definition. Scaffold the whole setup
#      (see references/i18n-setup.md).
#   2  init defined but not called at boot — add only the boot-time initI18n()
#      call in the entry file; do NOT re-scaffold or overwrite the init.
#   3  wired at boot but the manifest could not be confirmed as passed into the
#      backend (not imported, no backendOptions/SalesforceBackend config, or
#      imported but not seen inside a backendOptions array). This is a textual
#      heuristic: the manifest may be wired via a variable/spread this check
#      cannot see. VERIFY by hand; reconcile only if it genuinely dangles, and
#      never clobber the existing init.
#  64  usage error — the source dir does not exist (bad argument or wrong cwd).
#      This is NOT a "no init found" result; do not scaffold. Fix the path and
#      re-run. (64 = EX_USAGE, kept out of the 0-3 semantic range so exit 1
#      uniquely means "no init found".)
# The message still names the specific file/symbol/gap for the report, but the
# decision is the exit code.

SRC_DIR="${1:-src}"
if [ ! -d "$SRC_DIR" ]; then
  echo "ERROR: source dir not found: $SRC_DIR (run from the UI bundle dir, or pass its src path)" >&2
  exit 64
fi

# An init file that DEFINES initI18n (function/const declaration, not just a call).
# Use POSIX character classes, not \s / \b: BSD/macOS grep -E does not honor those.
# A trailing [^A-Za-z0-9_] (or end of line) stands in for the word boundary so
# initI18nFoo does not match.
DEFINES=$(grep -rlE '(function|const)[[:space:]]+initI18n([^A-Za-z0-9_]|$)|initI18n[[:space:]]*=' "$SRC_DIR" \
            --include='*.ts' --include='*.tsx' 2>/dev/null | head -1 || true)

# A boot-time call to initI18n() somewhere other than its own definition file.
CALLS=$(grep -rlE '(^|[^A-Za-z0-9_])initI18n[[:space:]]*\(' "$SRC_DIR" \
          --include='*.ts' --include='*.tsx' 2>/dev/null \
        | grep -vF "${DEFINES:-/dev/null}" | head -1 || true)

if [ -n "$DEFINES" ] && [ -n "$CALLS" ]; then
  # Wiring exists. Determine whether the manifest is already reconciled into the
  # backend. Importing the manifest is not enough: an init can `import
  # { labelManifest }` and still omit it from backendOptions, in which case the
  # SalesforceBackend fetches nothing and every key renders as its own literal
  # name. So confirm three things, not just token presence:
  #   1. the manifest is imported (capture the symbol it binds),
  #   2. a backendOptions construction exists (where the SDK backend is fed),
  #   3. that symbol appears INSIDE the backendOptions array, not merely
  #      somewhere in the source.
  # (3) is what separates "imported and wired" from "imported but dropped". A
  # bare reference elsewhere (e.g. console.log(labelManifest)) must not count:
  # the backend only receives the manifest if it sits in backendOptions.
  # Search the WHOLE src tree, not just the init file: a valid app may define
  # initI18n() in one file and build the SalesforceBackend (with the manifest)
  # in a separate backend module or the entry file. Scanning only $DEFINES
  # falsely reports "not reconciled" for that layout. Find the manifest import
  # wherever it lives, and the file that actually constructs backendOptions.
  # Is the manifest imported anywhere at all? (Used only for the "manifest
  # import missing" message; the wired/dangling decision is made per-file below.)
  MANIFEST_IMPORT_LINE=$(grep -rhnE '^[[:space:]]*import[^A-Za-z0-9_].*(label-manifest|labelManifest)' "$SRC_DIR" \
                          --include='*.ts' --include='*.tsx' 2>/dev/null | head -1 || true)
  # EVERY file that constructs backendOptions, not just the first: a decoy (a
  # comment, a types file, an unused second backend) can sort earlier in the
  # tree walk, so we check whether the manifest lands in ANY file's backendOptions.
  BACKEND_FILES=$(grep -rlE 'backendOptions' "$SRC_DIR" \
                   --include='*.ts' --include='*.tsx' 2>/dev/null || true)
  # Any backend config token at all, for the "no backend config" message.
  BACKEND_OPTS=$(grep -rlE 'backendOptions|SalesforceBackend' "$SRC_DIR" \
                   --include='*.ts' --include='*.tsx' 2>/dev/null | head -1 || true)

  # sed program that resolves the manifest's LOCAL name from an import line.
  # Two forms bind a local name, plus the default import:
  #   named:   import { ..., labelManifest, ... }    -> labelManifest
  #   aliased: import { ..., labelManifest as foo }  -> foo
  #   default: import labelManifest from ...         -> labelManifest
  # Avoid \b: BSD/macOS sed does not support it.
  RESOLVE_SYMBOL='s/.*[{,][[:space:]]*labelManifest[[:space:]]+as[[:space:]]+([A-Za-z0-9_]+).*/\1/; t
                  s/.*[{,][[:space:]]*labelManifest[[:space:]]*[,}].*/labelManifest/; t
                  s/.*import[[:space:]]+labelManifest[[:space:]]+from.*/labelManifest/; t
                  s/.*/labelManifest/'

  # Determine whether the manifest is actually passed into a backendOptions
  # array (not merely imported and left unused). Importing is not enough: an
  # init can `import { labelManifest }` and still omit it from backendOptions,
  # in which case the backend fetches nothing and every key renders as its own
  # literal name. Resolve the symbol PER FILE from that file's own import: an
  # imported binding can only be used in the file that imports it, so the name
  # passed into a file's backendOptions is whatever that same file bound (named,
  # aliased, or default). Resolving per file avoids a cross-file alias mismatch
  # (file A imports `labelManifest`, file B imports it `as m` and uses `m`).
  # The awk emits every backendOptions array block in the file (bracket-balanced
  # from each "[" after a "backendOptions" token); we grep those blocks for the
  # file's own symbol. A bare reference elsewhere (console.log(labelManifest))
  # is outside every block, so it does not count.
  MANIFEST_USED=""
  MANIFEST_SYMBOL="labelManifest"  # fallback for the message if no hit is found
  if [ -n "$BACKEND_FILES" ]; then
    while IFS= read -r BACKEND_FILE; do
      [ -z "$BACKEND_FILE" ] && continue
      FILE_IMPORT=$(grep -nE '^[[:space:]]*import[^A-Za-z0-9_].*(label-manifest|labelManifest)' \
                      "$BACKEND_FILE" 2>/dev/null | head -1 || true)
      [ -z "$FILE_IMPORT" ] && continue   # this file cannot use a binding it never imported
      SYM=$(printf '%s\n' "$FILE_IMPORT" | sed -E "$RESOLVE_SYMBOL")
      [ -z "$SYM" ] && continue
      # Emit every backendOptions array block. State (started/seeking/capturing/
      # depth/out) is awk-global and persists across lines so a multi-line array
      # is captured whole. After a "backendOptions" token we SEEK its opening
      # "[": only whitespace and ":" may sit between token and bracket. If any
      # other non-space char comes first, the token is not followed by an array
      # literal (e.g. `backendOptions: buildOpts()`), so abandon it and re-scan —
      # without this, `started` would leak forward and capture an unrelated later
      # array as if it were the options array (a false "wired" result).
      # Known limit: a "]" inside a string literal in the array (e.g.
      # `["a]b", labelManifest]`) closes the block early and can miss the symbol.
      # That only ever pushes toward exit 3 (verify by hand), never a false exit
      # 0, so it is safe under the heuristic framing; not worth a string parser.
      BLOCKS=$(sed -E 's://.*$::' "$BACKEND_FILE" | awk '
        {
          line = $0; pos = 1; n = length(line)
          while (pos <= n) {
            if (!seeking && !capturing) {
              idx = index(substr(line, pos), "backendOptions")
              if (idx == 0) break
              seeking = 1
              pos = pos + idx - 1 + 14   # 14 = length("backendOptions")
              continue
            }
            c = substr(line, pos, 1)
            if (seeking) {
              if (c == "[") { seeking = 0; capturing = 1; depth = 1; out = c; pos++; continue }
              if (c == " " || c == "\t" || c == ":") { pos++; continue }
              seeking = 0; continue   # not an array literal -> re-scan for next token
            }
            # capturing
            out = out c
            if (c == "[") depth++
            if (c == "]") { depth--; if (depth <= 0) { print out; out=""; capturing=0 } }
            pos++
          }
          if (capturing) out = out "\n"
        }
      ')
      if printf '%s' "$BLOCKS" \
           | grep -qE "(^|[^A-Za-z0-9_])${SYM}([^A-Za-z0-9_]|$)" 2>/dev/null; then
        MANIFEST_USED="yes"; MANIFEST_SYMBOL="$SYM"; break
      fi
    done <<EOF
$BACKEND_FILES
EOF
  fi

  if [ -n "$MANIFEST_USED" ]; then
    echo "i18n wired: initI18n() defined in $DEFINES, called at boot in $CALLS; the manifest ($MANIFEST_SYMBOL) is imported and passed into the backend config -> add new keys to the manifest, do not clobber the init"
    exit 0
  fi
  # Could not confirm the manifest is passed into a backendOptions array. This
  # is a heuristic textual check, so treat exit 3 as "verify, do not clobber":
  # the manifest may be wired through a form this script cannot see (passed via
  # a variable, spread, or helper). Report the specific gap for the human/agent
  # to confirm before editing; only reconcile if it genuinely dangles.
  MISSING=""
  [ -z "$MANIFEST_IMPORT_LINE" ] && MISSING="manifest import"
  [ -z "$BACKEND_OPTS" ] && MISSING="${MISSING:+$MISSING and }backendOptions/SalesforceBackend config"
  [ -n "$MANIFEST_IMPORT_LINE" ] && [ -n "$BACKEND_OPTS" ] \
    && MISSING="${MISSING:+$MISSING and }could not confirm the manifest is passed into backendOptions (it may dangle unused, or be wired via a variable this check cannot see)"
  echo "i18n wired: initI18n() defined in $DEFINES, called at boot in $CALLS; but $MISSING -> verify by hand; if it genuinely dangles, reconcile (import the manifest AND pass it into the SalesforceBackend's backendOptions) without clobbering"
  exit 3
fi

if [ -z "$DEFINES" ]; then
  echo "no i18n init found (no initI18n() definition under $SRC_DIR) -> scaffold it"
  exit 1
fi
echo "initI18n() defined in $DEFINES but not called at boot -> add the boot-time call"
exit 2
