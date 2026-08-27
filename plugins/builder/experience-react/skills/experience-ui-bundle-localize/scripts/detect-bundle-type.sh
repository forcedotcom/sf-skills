#!/usr/bin/env bash
set -euo pipefail  # exit on error (-e), undefined vars (-u), and propagate pipeline failures (-o pipefail)
#
# detect-bundle-type.sh — Classify a UI Bundle as authenticated, a bound public
# site candidate, or a bound non-public/unsupported site before localizing it.
#
# The bundle's type is decided by deterministic file and string checks, so run
# this rather than interpreting them by hand. It classifies in a fixed order:
#   - in-core internal: ui-bundle.json accessCheck starts with "LwrInternalApp." -> proceed
#   - B2E: a CustomApplication whose <uiBundle> names this bundle           -> proceed
#   - public site candidate: content.json binds this appSpace and its
#          app-container metadata enables guest access                     -> ask product type
#   - non-public/unsupported site: the site binds this bundle without that
#          public app-container shape                                      -> stop
#   - anything else: unbound / cannot auto-detect                           -> ask the user
#
# The B2E and site checks are package-local: CustomApplication and site config
# metadata are siblings of uiBundles/ under the package source path
# (e.g. force-app/main/default/{applications,uiBundles}/), so the script derives
# that metadata root from the bundle path rather than the current directory. If
# the bundle is bound elsewhere the script returns 2 (ask the user), the correct
# fallback. Do not gate on a <target> element inside *.uibundle-meta.xml;
# CLI-generated bundles do not carry it.
#
# Usage (pass the full path to the bundle dir; cwd does not matter):
#   bash <skill-dir>/scripts/detect-bundle-type.sh <path-to-uiBundles/<name>/ dir>
#
# Exit codes:
#   0  authenticated app (in-core internal or B2E) — proceed
#   2  unbound / cannot auto-detect — report the result and stop rather than
#      guessing the bundle type
#  10  bound public site app-container candidate — metadata proves binding and
#      guest access, not B2C versus B2B product type
#  11  bound non-public/unsupported site — stop
#  12  bundle has both CustomApplication and site bindings — ask which runtime
#      context is being localized
#  13  bundle has multiple matching Experience site bindings — show every
#      matching site and ask which site/runtime context is being localized

if [ "$#" -ne 1 ] || [ -z "${1:-}" ]; then
  echo "ERROR: pass exactly one bundle directory. Usage: detect-bundle-type.sh <path-to-uiBundles/<name>/ dir>" >&2
  exit 2
fi
bundleDir="${1%/}"
bundle=$(basename "$bundleDir")

# CustomApplication and site metadata sit beside uiBundles/ under the package
# source path, not at the cwd. Derive that metadata root from the bundle path:
# it's the parent of the uiBundles/ segment. Fall back to the cwd for a
# flattened layout with no uiBundles/ segment.
metaRoot="."
case "$bundleDir" in
  */uiBundles/*) metaRoot="${bundleDir%/uiBundles/*}" ;;
esac

classify_site() {
  local config config_xml space site content app_namespace app_name app_space auth_type app_container
  local -a matches=() matched_sites=()
  app_namespace="c"
  app_name="$bundle"
  if [ -f "${bundleDir}/ui-bundle.json" ]; then
    app_namespace=$(jq -r '.appNamespace // "c"' "${bundleDir}/ui-bundle.json" 2>/dev/null || printf 'c')
    app_name=$(jq -r '.appName // empty' "${bundleDir}/ui-bundle.json" 2>/dev/null || true)
    [ -n "$app_name" ] || app_name="$bundle"
  fi
  app_space="${app_namespace}__${app_name}"

  for config in "${metaRoot}"/digitalExperienceConfigs/*.digitalExperienceConfig-meta.xml; do
    [ -f "$config" ] || continue
    config_xml=""
    while IFS= read -r line || [ -n "$line" ]; do
      config_xml+="$line"
    done <"$config"
    space=""
    if [[ "$config_xml" =~ \<space\>[[:space:]]*site/([^\<[:space:]]+) ]]; then
      space="${BASH_REMATCH[1]}"
    fi
    [ -n "$space" ] || continue
    site="${metaRoot}/digitalExperiences/site/${space}"
    content="${site}/sfdc_cms__site/${space}/content.json"
    [ -f "$content" ] || continue
    [ "$(jq -r '.contentBody.appSpace // empty' "$content" 2>/dev/null)" = "$app_space" ] || continue

    auth_type=$(jq -r '.contentBody.authenticationType // empty' "$content" 2>/dev/null)
    app_container=$(jq -r '.contentBody.appContainer // false' "$content" 2>/dev/null)
    if [ "$app_container" = "true" ] \
       && { [ "$auth_type" = "AUTHENTICATED_WITH_PUBLIC_ACCESS_ENABLED" ] \
         || [ "$auth_type" = "UNAUTHENTICATED" ]; }; then
      matches+=("${space} (public)")
    else
      matches+=("${space} (non-public)")
    fi
    matched_sites+=("$space")
  done

  if [ "${#matches[@]}" -gt 1 ]; then
    local joined="" match
    for match in "${matches[@]}"; do
      [ -z "$joined" ] || joined+=", "
      joined+="$match"
    done
    echo "multiple Experience site bindings: ${joined} -> ask which site/runtime context is being localized"
    return 13
  fi
  if [ "${#matches[@]}" -eq 1 ]; then
    if [[ "${matches[0]}" == *" (public)" ]]; then
      echo "bound public site app-container candidate (site DeveloperName: ${matched_sites[0]}; guest access enabled; product type not inferred)"
      return 10
    fi
    echo "bound non-public/unsupported site (site DeveloperName: ${matched_sites[0]}; DigitalExperienceConfig-bound)"
    return 11
  fi
  return 2
}

internal_bound=false
if [ -f "${bundleDir}/ui-bundle.json" ] \
   && jq -e '(.accessCheck // "") | startswith("LwrInternalApp.")' "${bundleDir}/ui-bundle.json" >/dev/null 2>&1; then
  internal_bound=true
fi

b2e_bound=false
if grep -rlq --include='*.app-meta.xml' "<uiBundle>${bundle}</uiBundle>" "${metaRoot}/applications" 2>/dev/null; then
  b2e_bound=true
fi

set +e
site_output=$(classify_site)
status=$?
set -e
if { [ "$internal_bound" = "true" ] || [ "$b2e_bound" = "true" ]; } \
   && { [ "$status" -eq 10 ] || [ "$status" -eq 11 ]; }; then
  echo "dual-bound bundle (authenticated app and $site_output) -> ask for target runtime context"
  exit 12
fi
if [ "$status" -eq 13 ]; then
  if [ "$internal_bound" = "true" ] || [ "$b2e_bound" = "true" ]; then
    echo "authenticated app plus $site_output"
    exit 13
  fi
  echo "$site_output"
  exit 13
fi
if [ "$status" -eq 10 ]; then
  echo "$site_output"
  exit "$status"
fi
if [ "$status" -eq 11 ]; then
  echo "$site_output -> stop"
  exit "$status"
fi
if [ "$internal_bound" = "true" ]; then
  echo "in-core internal app -> proceed"
  exit 0
fi
if [ "$b2e_bound" = "true" ]; then
  echo "B2E (CustomApplication-bound) -> proceed"
  exit 0
fi
echo "unbound / cannot auto-detect -> ask the user"; exit 2
