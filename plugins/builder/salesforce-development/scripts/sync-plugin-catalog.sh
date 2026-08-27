#!/bin/sh
# sync-plugin-catalog.sh — keep catalog/plugins.json in sync with its inputs.
#
# The plugin catalog is a GENERATED artifact (plugin_catalog.py --generate).
# build_catalog() derives it from:
#   1. config.yml                          (internalPlugins holds)
#   2. .claude-plugin/marketplace.json     (every plugin entry's source, description,
#                                            keywords, and metadata.match.examplePrompts)
# plus the generator/catalog code itself. When either input is staged, regenerate
# and re-stage the artifact so it can never drift out of sync.
#
# Wired into .husky/pre-commit (authoring) and .husky/pre-merge-commit (the drift a
# plain `git merge develop` caused when it pulled in others' file edits). The
# catalog's "is current" contract test (test_plugin_catalog.py, run by
# `npm run test:gates` in CI) is the HARD guarantee; this hook just keeps authors
# and mergers from ever hitting that red check.
#
# Test hooks (no git side effects): set CATALOG_SYNC_FILES to a newline-separated
# path list to bypass `git diff`, and CATALOG_SYNC_CHECK_ONLY=1 to print the
# decision (regen-needed|skip) instead of regenerating/staging.
set -e

PLUGIN="plugins/builder/salesforce-development"
GENERATOR="${PLUGIN}/scripts/plugin_catalog.py"
CAPABILITY_REGISTRY="${PLUGIN}/scripts/capability_registry.py"
MARKETPLACE=".claude-plugin/marketplace.json"
ARTIFACT="${PLUGIN}/catalog/plugins.json"

if [ "${CATALOG_SYNC_FILES+x}" = "x" ]; then
  changed="$CATALOG_SYNC_FILES"
else
  changed="$(git diff --cached --name-only --diff-filter=ACMRD)"
fi

# The catalog is derived only from config.yml (internalPlugins holds) and the
# repo-root marketplace (every plugin entry's source and match text), so only a
# staged change to one of those two inputs can change build_catalog()'s output.
inputs_changed="$(printf '%s\n' "$changed" | grep -E "^config\.yml$|^${MARKETPLACE}$" || true)"

if [ -z "$inputs_changed" ]; then
  [ "${CATALOG_SYNC_CHECK_ONLY:-}" = "1" ] && echo "skip"
  exit 0
fi

if [ "${CATALOG_SYNC_CHECK_ONLY:-}" = "1" ]; then
  echo "regen-needed"
  exit 0
fi

# Generate from the staged index rather than the worktree. Besides excluding
# unrelated unstaged edits, this bypasses core.autocrlf checkout conversion on
# Windows so the catalog hashes Git's canonical bytes on every platform.
snapshot="$(mktemp -d "${TMPDIR:-/tmp}/sf-plugin-catalog.XXXXXX")"
cleanup() {
  rm -rf "$snapshot"
}
trap cleanup EXIT HUP INT TERM
mkdir -p "$snapshot/skills"
git ls-files -z -- config.yml "$MARKETPLACE" "$GENERATOR" "$CAPABILITY_REGISTRY" |
  git -c core.autocrlf=false -c core.eol=lf \
    checkout-index --stdin -z --prefix="${snapshot}/"
python3 "${snapshot}/${GENERATOR}" --generate >/dev/null
python3 "${snapshot}/${GENERATOR}" --check >/dev/null
cp "${snapshot}/${ARTIFACT}" "$ARTIFACT"
git add "$ARTIFACT"
echo "sync-plugin-catalog: regenerated and staged ${ARTIFACT}"
