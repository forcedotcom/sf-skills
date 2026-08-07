#!/usr/bin/env bash
# find-consumers.sh — deterministically find LWC consumers of a component.
#
# Usage: find-consumers.sh <project-root> <componentName>
#
# Behavior:
#   1. Canonicalize <project-root>. Fail if it is not a directory.
#   2. If <project-root>/sfdx-project.json exists, read every
#      packageDirectories[].path and canonicalize each one relative to the
#      project root. Reject absolute paths and any path that escapes the
#      canonical project root (S2 safety). Skip paths that do not resolve
#      to a real directory. If no usable paths remain, fail.
#      Otherwise the search list is just [project-root].
#   3. Grep every resolved directory for LWC import statements matching
#      "import ... from 'c/<componentName>'" (single OR double quotes),
#      limited to .js and .ts files.
#   4. Print matches (grep -H format: <path>:<match>) to stdout, one per
#      line. Empty output is a valid result — the caller should treat it
#      as "no consumers".
#   5. Exits 0 on success (matches or no matches). Nonzero only on invalid
#      arguments, unreadable project, or a malformed sfdx-project.json.
#
# The consumer-import search algorithm and directory-safety canonicalization
# both live here so SKILL.md contains no algorithmic logic (A9), and the
# search list is built into an array so paths with whitespace survive (no
# xargs word-splitting).
set -euo pipefail

if [ "$#" -lt 2 ] || [ -z "${1:-}" ] || [ -z "${2:-}" ]; then
  echo "find-consumers: missing arguments" >&2
  echo "usage: find-consumers.sh <project-root> <componentName>" >&2
  exit 64
fi

root_in="$1"
component="$2"

if [ ! -d "$root_in" ]; then
  echo "find-consumers: <project-root> is not a directory: $root_in" >&2
  exit 66
fi

# Canonicalize the project root so subsequent containment checks are exact.
root="$(cd "$root_in" && pwd -P)"

# Validate componentName — camelCase-ish alphanumeric, no separators that
# could inject shell/regex metacharacters into the grep pattern below.
if ! printf '%s' "$component" | grep -Eq '^[A-Za-z][A-Za-z0-9]*$'; then
  echo "find-consumers: componentName must match [A-Za-z][A-Za-z0-9]*: $component" >&2
  exit 64
fi

cfg="$root/sfdx-project.json"
search_dirs=()

if [ -f "$cfg" ]; then
  # jq -r prints one path per line; empty and null entries are elided.
  raw_paths="$(jq -r '.packageDirectories[]?.path // empty' "$cfg" 2>/dev/null)" || {
    echo "find-consumers: $cfg is not valid JSON" >&2
    exit 65
  }

  while IFS= read -r p; do
    [ -z "$p" ] && continue

    # S2: reject absolute paths outright — a project cfg has no business
    # pointing at anything outside its own root.
    case "$p" in
      /*)
        echo "find-consumers: rejecting absolute packageDirectory path: $p" >&2
        continue
        ;;
    esac

    # Resolve relative to the (canonical) project root.
    candidate="$root/${p%/}"

    if [ ! -d "$candidate" ]; then
      echo "find-consumers: packageDirectory not found on disk: $candidate" >&2
      continue
    fi

    # Canonicalize the candidate and ensure it stays inside the project
    # root. This catches `..` escapes and symlinks that point outward.
    canon="$(cd "$candidate" && pwd -P)"
    case "$canon" in
      "$root"|"$root"/*) ;;
      *)
        echo "find-consumers: rejecting packageDirectory that escapes project root: $canon" >&2
        continue
        ;;
    esac

    search_dirs+=("$canon")
  done <<< "$raw_paths"

  if [ "${#search_dirs[@]}" -eq 0 ]; then
    echo "find-consumers: no usable packageDirectory paths in $cfg" >&2
    exit 65
  fi
else
  search_dirs=("$root")
fi

# Build the grep pattern. We anchor on the module-specifier clause —
# `from <ws> ['"]c/<component>['"]` — which uniquely identifies a consumer
# import regardless of whether the binding is single-line, multi-line
# destructured, a `type` import, or a re-export. The `import ... from`
# prefix is intentionally dropped because in a multi-line import the
# closing `} from 'c/x'` line does not contain the word `import`; a
# per-line grep that requires both tokens on the same line would miss
# it. `[[:space:]]+` handles tabs and repeated spaces. Component name
# was already validated so it is safe to interpolate into the regex.
pattern="from[[:space:]]+['\"]c/${component}['\"]"

# Array-quoted expansion preserves paths that contain whitespace. grep
# returns 1 when there are no matches — treat that as a successful empty
# result, not an error.
grep -rHE "$pattern" \
  --include='*.js' --include='*.ts' \
  "${search_dirs[@]}" || rc=$?

# grep exit codes: 0=matched, 1=no matches, 2+=error. Only surface real errors.
rc="${rc:-0}"
if [ "$rc" -ge 2 ]; then
  exit "$rc"
fi
exit 0
