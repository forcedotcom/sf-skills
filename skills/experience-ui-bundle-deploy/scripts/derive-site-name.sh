#!/usr/bin/env bash
# Derive the Experience Cloud site name for the self-registration step.
#
# The site is the base name of the SINGLE *.network-meta.xml file in the
# project. Prints that name (without the .network-meta.xml suffix) and exits 0.
# Exits non-zero with a message on stderr when zero or more than one such file
# exists — the reference implementation refuses to guess an ambiguous site.
#
# Usage: scripts/derive-site-name.sh [search-dir]
#   search-dir defaults to the current directory; the file is located
#   recursively, so both <packageDir>/main/default/networks/ and a project-root
#   networks/ layout resolve correctly.
set -euo pipefail

search_dir="${1:-.}"

if [[ ! -d "$search_dir" ]]; then
  echo "derive-site-name: '$search_dir' is not a directory" >&2
  exit 1
fi

# Collect matches into an array (null-delimited to tolerate odd paths).
matches=()
while IFS= read -r -d '' f; do
  matches+=("$f")
done < <(find "$search_dir" -type f -name '*.network-meta.xml' -print0)

count="${#matches[@]}"
if (( count == 0 )); then
  echo "derive-site-name: no *.network-meta.xml file found under '$search_dir'" >&2
  exit 1
fi
if (( count > 1 )); then
  echo "derive-site-name: ambiguous site — found $count *.network-meta.xml files:" >&2
  printf '  %s\n' "${matches[@]}" >&2
  exit 1
fi

base="$(basename "${matches[0]}")"
echo "${base%.network-meta.xml}"
