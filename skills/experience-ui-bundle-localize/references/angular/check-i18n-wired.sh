#!/usr/bin/env bash
set -euo pipefail  # exit on error (-e), undefined vars (-u), and propagate pipeline failures (-o pipefail)
#
# check-i18n-wired.sh — Confirm the Angular ngx-translate wiring exists, is
# registered with a custom loader, and is loaded at boot.
#
# Angular-specific: the detection targets are ngx-translate-shaped
# (provideTranslateService / TranslateModule.forRoot, a TranslateLoader subclass,
# and a boot-time TranslateService.use(...) call), which have no i18next analog,
# so this script lives under the Angular reference (references/angular/) rather
# than the shared scripts/ folder. The React equivalent (initI18n / SalesforceBackend
# detection) lives under references/react/.
#
# Whether the app already has i18n wiring is a file-existence plus call-site
# check, so run this rather than reading for it by hand. It looks for the
# ngx-translate provider registration, a custom TranslateLoader class, and a
# boot-time TranslateService.use(...) call.
#
# Usage (run from the UI bundle dir, or pass its src path):
#   bash <skill-dir>/references/angular/check-i18n-wired.sh [src-dir]
#
# src-dir defaults to "src".
#
# When wiring exists, it also reports whether the label manifest is imported AND
# actually referenced inside the loader class (not merely imported and left
# unused), so the reconcile decision is a script result rather than a by-hand read.
#
# Exit codes (aligned with references/react/check-i18n-wired.sh and
# scripts/check-manifest-registered.sh so the workflow branches on the code, not
# the message text):
#   0  fully wired — provideTranslateService / TranslateModule.forRoot registers
#      the custom loader, a boot-time TranslateService.use(...) runs, AND the
#      manifest is imported and referenced inside the loader. Just add new keys.
#   1  no ngx-translate wiring found — neither a provider registration nor a
#      TranslateLoader subclass. Scaffold the whole setup (see
#      references/angular/i18n-setup.md).
#   2  partially wired — a loader class OR a registration exists, but the setup is
#      incomplete: the loader is not registered via provideTranslateService /
#      TranslateModule.forRoot, or it is registered but nothing calls
#      TranslateService.use(...) at boot. Add ONLY the missing wiring; do NOT
#      re-scaffold or overwrite the existing loader.
#   3  registered and booted, but the manifest could not be confirmed as reaching
#      the loader (not imported into the loader file, no detectable loader class,
#      or imported but never referenced in it). This is a textual heuristic: the
#      manifest may be wired via a variable/factory/spread this check cannot see.
#      VERIFY by hand; reconcile only if it genuinely dangles, and never clobber
#      the existing loader.
#  64  usage error — the source dir does not exist (bad argument or wrong cwd).
#      This is NOT a "no wiring found" result; do not scaffold. Fix the path and
#      re-run. (64 = EX_USAGE, kept out of the 0-3 semantic range so exit 1
#      uniquely means "no wiring found".)
# The message still names the specific file/symbol/gap for the report, but the
# decision is the exit code.

SRC_DIR="${1:-src}"
if [ ! -d "$SRC_DIR" ]; then
  echo "ERROR: source dir not found: $SRC_DIR (run from the UI bundle dir, or pass its src path)" >&2
  exit 64
fi

# Use POSIX character classes, not \s / \b: BSD/macOS grep -E does not honor those.

# (A) The ngx-translate provider registration: standalone provideTranslateService()
#     or the NgModule TranslateModule.forRoot(). Either one means "the setup exists".
REGISTERED=$(grep -rlE 'provideTranslateService[[:space:]]*\(|TranslateModule[[:space:]]*\.[[:space:]]*forRoot[[:space:]]*\(' \
               "$SRC_DIR" --include='*.ts' 2>/dev/null | head -1 || true)

# (B) A custom loader class: `... implements TranslateLoader` or `... extends <X>TranslateLoader`.
#     -l over the whole tree; the file list is reused for the manifest-reach check.
LOADER_FILES=$(grep -rlE '(implements|extends)[[:space:]].*TranslateLoader' \
                 "$SRC_DIR" --include='*.ts' 2>/dev/null || true)
LOADER=$(printf '%s' "$LOADER_FILES" | head -1 || true)

# (C) A boot-time TranslateService.use(...) call: <translate-ish>.use( — matches
#     translate.use(, this.translate.use(, translateService.use(, etc. This is the
#     Angular analog of React's boot-time initI18n() call.
BOOTED=$(grep -rlE '[Tt]ranslate[A-Za-z0-9_]*[[:space:]]*\.[[:space:]]*use[[:space:]]*\(' \
           "$SRC_DIR" --include='*.ts' 2>/dev/null | head -1 || true)

# --- Decision tree (mirrors the React script's DEFINES/CALLS/reconcile shape) ---

# 1: nothing ngx-translate at all -> scaffold everything.
if [ -z "$REGISTERED" ] && [ -z "$LOADER" ]; then
  echo "no ngx-translate wiring found (no provideTranslateService/TranslateModule.forRoot and no TranslateLoader subclass under $SRC_DIR) -> scaffold it (see references/angular/i18n-setup.md)"
  exit 1
fi

# 2a: a loader class exists but is never registered -> add only the provider wiring.
if [ -z "$REGISTERED" ]; then
  echo "TranslateLoader subclass defined in $LOADER but not registered (no provideTranslateService/TranslateModule.forRoot) -> add the provider registration; do not re-scaffold the loader"
  exit 2
fi

# 2b: registered but nothing loads a language at boot -> add only the boot call.
if [ -z "$BOOTED" ]; then
  echo "ngx-translate registered in $REGISTERED but no boot-time TranslateService.use(...) call found -> add the boot wiring (fetch the i18n context and call translate.use(ctx.lang)); do not re-scaffold"
  exit 2
fi

# Registered AND booted. Confirm the manifest actually reaches the loader: the
# loader file must import the manifest AND reference the bound symbol somewhere
# OTHER than its import line. Importing alone is not enough — a loader can
# `import { labelManifest }` and never iterate it, in which case it fetches
# nothing and every key renders as its own literal name. Resolve the symbol PER
# loader file from that file's own import (named / aliased / default), because an
# imported binding is only usable in the file that imports it.
RESOLVE_SYMBOL='s/.*[{,][[:space:]]*labelManifest[[:space:]]+as[[:space:]]+([A-Za-z0-9_]+).*/\1/; t
                s/.*[{,][[:space:]]*labelManifest[[:space:]]*[,}].*/labelManifest/; t
                s/.*import[[:space:]]+labelManifest[[:space:]]+from.*/labelManifest/; t
                s/.*/labelManifest/'

MANIFEST_USED=""
MANIFEST_SYMBOL="labelManifest"  # fallback for the message if no hit is found
if [ -n "$LOADER_FILES" ]; then
  while IFS= read -r LOADER_FILE; do
    [ -z "$LOADER_FILE" ] && continue
    FILE_IMPORT=$(grep -nE '^[[:space:]]*import[^A-Za-z0-9_].*(label-manifest|labelManifest)' \
                    "$LOADER_FILE" 2>/dev/null | head -1 || true)
    [ -z "$FILE_IMPORT" ] && continue   # this file cannot use a binding it never imported
    SYM=$(printf '%s\n' "$FILE_IMPORT" | sed -E "$RESOLVE_SYMBOL")
    [ -z "$SYM" ] && continue
    # Reference to SYM anywhere OTHER than an import line (strip // comments and
    # import lines first, so `import { labelManifest }` and a commented mention do
    # not count as use). A bare `for (const e of labelManifest)` / `labelManifest.`
    # / `[...labelManifest]` all match.
    if sed -E 's://.*$::' "$LOADER_FILE" \
         | grep -vE '^[[:space:]]*import[^A-Za-z0-9_]' \
         | grep -qE "(^|[^A-Za-z0-9_])${SYM}([^A-Za-z0-9_]|$)" 2>/dev/null; then
      MANIFEST_USED="yes"; MANIFEST_SYMBOL="$SYM"; break
    fi
  done <<EOF
$LOADER_FILES
EOF
fi

if [ -n "$MANIFEST_USED" ]; then
  echo "i18n wired: ngx-translate registered in $REGISTERED, loaded at boot ($BOOTED), custom loader in $LOADER; the manifest ($MANIFEST_SYMBOL) is imported and referenced inside the loader -> add new keys to the manifest, do not clobber the loader"
  exit 0
fi

# Registered + booted, but the manifest reach into the loader could not be
# confirmed. Heuristic textual check, so treat exit 3 as "verify, do not clobber":
# the manifest may be wired through a form this script cannot see (a factory, a
# variable, a spread, or a loader class this check did not detect). Report the
# specific gap for the human/agent to confirm before editing.
MISSING=""
if [ -z "$LOADER" ]; then
  MISSING="no TranslateLoader subclass detected (the loader may use a factory/useFactory this check cannot see)"
else
  MANIFEST_IMPORT_ANY=$(grep -rhnE '^[[:space:]]*import[^A-Za-z0-9_].*(label-manifest|labelManifest)' \
                          "$SRC_DIR" --include='*.ts' 2>/dev/null | head -1 || true)
  if [ -z "$MANIFEST_IMPORT_ANY" ]; then
    MISSING="the manifest is not imported into the loader file ($LOADER)"
  else
    MISSING="could not confirm the manifest is referenced inside the loader ($LOADER) (it may be imported but unused, or reached via a variable this check cannot see)"
  fi
fi
echo "i18n wired: ngx-translate registered in $REGISTERED and loaded at boot ($BOOTED); but $MISSING -> verify by hand; if it genuinely dangles, reconcile (import the manifest AND iterate it in the loader's getTranslation) without clobbering"
exit 3
