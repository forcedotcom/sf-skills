#!/bin/sh
# sync-discovery-catalog.sh — keep catalog/discovery.json in sync with its inputs.
#
# The discovery catalog is a GENERATED artifact (discovery_catalog.py --generate).
# build_catalog() derives it from exactly two things (repo_root is ignored):
#   1. the public manifest  catalog/public-release-manifest.json
#   2. the plugin's foundation skills  skills/**  (source_variant hashes the WHOLE
#      skill tree, so ANY file under a foundation skill dir changes the output)
# plus the generator/registry code itself. When any of those is staged, regenerate
# and re-stage the artifact so it can never drift out of sync.
#
# Wired into .husky/pre-commit (authoring) and .husky/pre-merge-commit (the drift a
# plain `git merge develop` caused when it pulled in others' SKILL.md edits). The
# catalog's "is current" contract test (test_discovery_catalog.py, run by
# `npm run test:gates` in CI) is the HARD guarantee; this hook just keeps authors
# and mergers from ever hitting that red check.
#
# Test hooks (no git side effects): set CATALOG_SYNC_FILES to a newline-separated
# path list to bypass `git diff`, and CATALOG_SYNC_CHECK_ONLY=1 to print the
# decision (regen-needed|skip) instead of regenerating/staging.
set -e

PLUGIN="plugins/builder/salesforce-development"
GENERATOR="${PLUGIN}/scripts/discovery_catalog.py"
REGISTRY="${PLUGIN}/scripts/capability_registry.py"
MANIFEST="${PLUGIN}/catalog/public-release-manifest.json"
ARTIFACT="${PLUGIN}/catalog/discovery.json"

# Paths whose change can alter the generated catalog.
PATTERN="^${PLUGIN}/skills/|^${PLUGIN}/catalog/public-release-manifest\.json$|^${PLUGIN}/scripts/(discovery_catalog|capability_registry)\.py$"

if [ "${CATALOG_SYNC_FILES+x}" = "x" ]; then
  changed="$CATALOG_SYNC_FILES"
else
  changed="$(git diff --cached --name-only --diff-filter=ACMRD)"
fi

if ! printf '%s\n' "$changed" | grep -qE "$PATTERN"; then
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
snapshot="$(mktemp -d "${TMPDIR:-/tmp}/sf-discovery-catalog.XXXXXX")"
cleanup() {
  rm -rf "$snapshot"
}
trap cleanup EXIT HUP INT TERM
mkdir -p "$snapshot/skills"
git ls-files -z -- config.yml "$GENERATOR" "$REGISTRY" "$MANIFEST" "${PLUGIN}/skills" |
  git -c core.autocrlf=false -c core.eol=lf \
    checkout-index --stdin -z --prefix="${snapshot}/"
executable_paths="${snapshot}/executable-paths.json"
git ls-files --stage -z -- "${PLUGIN}/skills" |
  python3 -c 'import json, sys; prefix = sys.argv[1].encode(); records = (row for row in sys.stdin.buffer.read().split(b"\0") if row); paths = [path[len(prefix):].decode("utf-8") for metadata, path in (row.split(b"\t", 1) for row in records) if metadata.startswith(b"100755 ") and path.startswith(prefix)]; json.dump(paths, sys.stdout, ensure_ascii=False); sys.stdout.write("\n")' \
    "${PLUGIN}/" >"$executable_paths"
python3 "${snapshot}/${GENERATOR}" --generate \
  --executable-paths-file "$executable_paths" >/dev/null
python3 "${snapshot}/${GENERATOR}" --check \
  --executable-paths-file "$executable_paths" >/dev/null
cp "${snapshot}/${ARTIFACT}" "$ARTIFACT"
git add "$ARTIFACT"
echo "sync-discovery-catalog: regenerated and staged ${ARTIFACT}"
