#!/usr/bin/env bash
set -uo pipefail

SCRIPT="$(cd "$(dirname "$0")/.." && pwd)/detect-bundle-type.sh"
ROOT=$(mktemp -d)
trap 'rm -rf "$ROOT"' EXIT
PASS=0
FAIL=0

make_bundle() {
  local fixture="$1" bundle="$2"
  mkdir -p "$ROOT/$fixture/force-app/main/default/uiBundles/$bundle"
  printf '{"appName":"%s","appNamespace":"c"}\n' "$bundle" \
    >"$ROOT/$fixture/force-app/main/default/uiBundles/$bundle/ui-bundle.json"
}

make_site() {
  local fixture="$1" site="$2" app_space="$3" auth_type="$4" app_container="$5"
  local metadata="$ROOT/$fixture/force-app/main/default"
  mkdir -p "$metadata/digitalExperienceConfigs"
  mkdir -p "$metadata/digitalExperiences/site/$site/sfdc_cms__site/$site"
  cat >"$metadata/digitalExperienceConfigs/$site.digitalExperienceConfig-meta.xml" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<DigitalExperienceConfig xmlns="http://soap.sforce.com/2006/04/metadata">
  <space>site/$site</space>
</DigitalExperienceConfig>
EOF
  cat >"$metadata/digitalExperiences/site/$site/sfdc_cms__site/$site/content.json" <<EOF
{
  "type": "sfdc_cms__site",
  "contentBody": {
    "authenticationType": "$auth_type",
    "appContainer": $app_container,
    "appSpace": "$app_space"
  }
}
EOF
}

make_multiline_site() {
  local fixture="$1" site="$2" app_space="$3" auth_type="$4" app_container="$5"
  make_site "$fixture" "$site" "$app_space" "$auth_type" "$app_container"
  cat >"$ROOT/$fixture/force-app/main/default/digitalExperienceConfigs/$site.digitalExperienceConfig-meta.xml" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<DigitalExperienceConfig xmlns="http://soap.sforce.com/2006/04/metadata">
  <space>
    site/$site
  </space>
</DigitalExperienceConfig>
EOF
}

assert_exit() {
  local expected="$1" fixture="$2" bundle="$3" description="$4" expected_output="${5:-}" forbidden_output="${6:-}"
  local output status
  output=$(bash "$SCRIPT" "$ROOT/$fixture/force-app/main/default/uiBundles/$bundle" 2>&1)
  status=$?
  if [ "$status" -eq "$expected" ] \
     && { [ -z "$expected_output" ] || [[ "$output" == *"$expected_output"* ]]; } \
     && { [ -z "$forbidden_output" ] || [[ "$output" != *"$forbidden_output"* ]]; }; then
    PASS=$((PASS + 1))
    printf '  ok   %-42s -> exit %s\n' "$description" "$status"
  else
    FAIL=$((FAIL + 1))
    printf '  FAIL %-42s -> exit %s, expected %s; output=%q; required=%q; forbidden=%q\n' \
      "$description" "$status" "$expected" "$output" "$expected_output" "$forbidden_output"
  fi
}

echo "detect-bundle-type.sh — offline metadata fixtures"

make_bundle b2e EmployeeConsole
mkdir -p "$ROOT/b2e/force-app/main/default/applications"
cat >"$ROOT/b2e/force-app/main/default/applications/EmployeeConsole.app-meta.xml" <<'EOF'
<CustomApplication xmlns="http://soap.sforce.com/2006/04/metadata">
  <uiBundle>EmployeeConsole</uiBundle>
</CustomApplication>
EOF
assert_exit 0 b2e EmployeeConsole "B2E CustomApplication binding"

make_bundle internal InternalConsole
jq '.accessCheck = "LwrInternalApp.InternalConsole"' \
  "$ROOT/internal/force-app/main/default/uiBundles/InternalConsole/ui-bundle.json" \
  >"$ROOT/internal/force-app/main/default/uiBundles/InternalConsole/ui-bundle.tmp"
mv "$ROOT/internal/force-app/main/default/uiBundles/InternalConsole/ui-bundle.tmp" \
  "$ROOT/internal/force-app/main/default/uiBundles/InternalConsole/ui-bundle.json"
assert_exit 0 internal InternalConsole "in-core internal binding"

make_bundle public_site CustomerPortal
make_site public_site CustomerPortal1 c__CustomerPortal AUTHENTICATED_WITH_PUBLIC_ACCESS_ENABLED true
assert_exit 10 public_site CustomerPortal "public app-container site candidate" \
  "bound public site app-container candidate (site DeveloperName: CustomerPortal1;" "B2C"

make_bundle legacy_public_site LegacyPortal
make_site legacy_public_site LegacyPortal1 c__LegacyPortal UNAUTHENTICATED true
assert_exit 10 legacy_public_site LegacyPortal "legacy public app-container site candidate" \
  "bound public site app-container candidate (site DeveloperName: LegacyPortal1;" "B2C"

make_bundle multiline_public_site MultilinePortal
make_multiline_site multiline_public_site MultilinePortal1 c__MultilinePortal AUTHENTICATED_WITH_PUBLIC_ACCESS_ENABLED true
assert_exit 10 multiline_public_site MultilinePortal "multiline site space binding" \
  "bound public site app-container candidate (site DeveloperName: MultilinePortal1;" "B2C"

make_bundle b2b PartnerStore
make_site b2b PartnerStore1 c__PartnerStore AUTHENTICATED_WITH_PUBLIC_ACCESS_ENABLED true
assert_exit 10 b2b PartnerStore "same-shape B2B site candidate" \
  "bound public site app-container candidate (site DeveloperName: PartnerStore1;" "B2C"

make_bundle non_public PrivatePortal
make_site non_public PrivatePortal1 c__PrivatePortal AUTHENTICATED false
assert_exit 11 non_public PrivatePortal "bound non-public site" \
  "bound non-public/unsupported site (site DeveloperName: PrivatePortal1;"

make_bundle dual_bound SharedPortal
mkdir -p "$ROOT/dual_bound/force-app/main/default/applications"
cat >"$ROOT/dual_bound/force-app/main/default/applications/SharedPortal.app-meta.xml" <<'EOF'
<CustomApplication xmlns="http://soap.sforce.com/2006/04/metadata">
  <uiBundle>SharedPortal</uiBundle>
</CustomApplication>
EOF
make_site dual_bound SharedPortal1 c__SharedPortal AUTHENTICATED_WITH_PUBLIC_ACCESS_ENABLED true
assert_exit 12 dual_bound SharedPortal "dual CustomApplication and site binding" \
  "dual-bound bundle (authenticated app and bound public site app-container candidate (site DeveloperName: SharedPortal1;"

make_bundle dual_bound_non_public PrivateSharedPortal
mkdir -p "$ROOT/dual_bound_non_public/force-app/main/default/applications"
cat >"$ROOT/dual_bound_non_public/force-app/main/default/applications/PrivateSharedPortal.app-meta.xml" <<'EOF'
<CustomApplication xmlns="http://soap.sforce.com/2006/04/metadata">
  <uiBundle>PrivateSharedPortal</uiBundle>
</CustomApplication>
EOF
make_site dual_bound_non_public PrivateSharedPortal1 c__PrivateSharedPortal AUTHENTICATED false
assert_exit 12 dual_bound_non_public PrivateSharedPortal "dual CustomApplication and non-public site" \
  "dual-bound bundle (authenticated app and bound non-public/unsupported site (site DeveloperName: PrivateSharedPortal1;"

make_bundle internal_dual InternalSharedPortal
jq '.accessCheck = "LwrInternalApp.InternalSharedPortal"' \
  "$ROOT/internal_dual/force-app/main/default/uiBundles/InternalSharedPortal/ui-bundle.json" \
  >"$ROOT/internal_dual/force-app/main/default/uiBundles/InternalSharedPortal/ui-bundle.tmp"
mv "$ROOT/internal_dual/force-app/main/default/uiBundles/InternalSharedPortal/ui-bundle.tmp" \
  "$ROOT/internal_dual/force-app/main/default/uiBundles/InternalSharedPortal/ui-bundle.json"
make_site internal_dual InternalSharedPortal1 c__InternalSharedPortal AUTHENTICATED_WITH_PUBLIC_ACCESS_ENABLED true
assert_exit 12 internal_dual InternalSharedPortal "dual internal and site binding" \
  "dual-bound bundle (authenticated app and bound public site app-container candidate (site DeveloperName: InternalSharedPortal1;"

make_bundle unrelated EmployeeConsole
make_site unrelated OtherPortal1 c__OtherPortal AUTHENTICATED_WITH_PUBLIC_ACCESS_ENABLED true
assert_exit 2 unrelated EmployeeConsole "unrelated DigitalExperienceConfig"

make_bundle unknown LooseBundle
assert_exit 2 unknown LooseBundle "unbound bundle"

make_bundle multi_public SharedStorefront
make_site multi_public AlphaPortal c__SharedStorefront AUTHENTICATED_WITH_PUBLIC_ACCESS_ENABLED true
make_site multi_public BetaPortal c__SharedStorefront UNAUTHENTICATED true
assert_exit 13 multi_public SharedStorefront "multiple public site bindings" \
  "multiple Experience site bindings" "bound public site app-container candidate"
assert_exit 13 multi_public SharedStorefront "reports every public site binding" \
  "AlphaPortal (public), BetaPortal (public)"

make_bundle multi_mixed SharedExperience
make_site multi_mixed ZuluPublic c__SharedExperience AUTHENTICATED_WITH_PUBLIC_ACCESS_ENABLED true
make_site multi_mixed AlphaPrivate c__SharedExperience AUTHENTICATED false
assert_exit 13 multi_mixed SharedExperience "mixed public and non-public bindings" \
  "AlphaPrivate (non-public), ZuluPublic (public)"

make_bundle multi_non_public SharedPrivate
make_site multi_non_public BetaPrivate c__SharedPrivate AUTHENTICATED false
make_site multi_non_public AlphaPrivate c__SharedPrivate AUTHENTICATED false
assert_exit 13 multi_non_public SharedPrivate "multiple non-public site bindings" \
  "AlphaPrivate (non-public), BetaPrivate (non-public)"

make_bundle authenticated_multi_site SharedConsole
mkdir -p "$ROOT/authenticated_multi_site/force-app/main/default/applications"
cat >"$ROOT/authenticated_multi_site/force-app/main/default/applications/SharedConsole.app-meta.xml" <<'EOF'
<CustomApplication xmlns="http://soap.sforce.com/2006/04/metadata">
  <uiBundle>SharedConsole</uiBundle>
</CustomApplication>
EOF
make_site authenticated_multi_site AlphaPortal c__SharedConsole AUTHENTICATED_WITH_PUBLIC_ACCESS_ENABLED true
make_site authenticated_multi_site BetaPortal c__SharedConsole AUTHENTICATED false
assert_exit 13 authenticated_multi_site SharedConsole "authenticated app with multiple sites" \
  "authenticated app plus multiple Experience site bindings: AlphaPortal (public), BetaPortal (non-public)"

echo ""
echo "  $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
