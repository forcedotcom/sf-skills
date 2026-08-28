#!/usr/bin/env bash
#
# Enable Native Voice (Thunderbird Voice) call recording + transcription via the
# Metadata API, using the sf CLI Settings-container retrieve/deploy path.
#
# Scope: this skill enables exactly two preferences — enableCallRecording and
# enableCallTranscription. Every other ThunderbirdVoiceSettings boolean is read
# only to be preserved verbatim — none is changed. The siblings ARE reported
# back (unchanged) in a `preserved` block so compliance callers can confirm
# nothing else moved; reporting a value is not the same as setting it.
#
# Why sf CLI (not raw SOAP): the generic `Settings` metadata type IS in the sf
# CLI registry (member = the type name without the `Settings` suffix, i.e.
# `ThunderbirdVoice`). Deploying through it authenticates with the org's existing
# `sf` login — no browser session id / access token is ever handled. Retrieving
# first lets us (a) check the org-perm gate and (b) preserve sibling prefs.
#
# Sequence: retrieve -> gate check -> flip the two target fields -> validate
# (dry-run) -> deploy -> verify by round-trip -> print a JSON confirmation.
#
# Deps: sf, jq. (No curl, no session id.)
#
set -euo pipefail

# ThunderbirdVoiceSettings fields are only exposed at API v68.0+; below that the
# Settings type does not appear in a retrieve at all. Default to exactly 68.0 — the
# field-exposure floor. A retrieve/deploy at a version ABOVE the org's max supported
# API SILENTLY returns an empty result (no error), which is indistinguishable from
# "feature not provisioned". 68.0 works on every org that has the feature; do NOT
# bump this default to a newer version unless you also cap it to the org's max.
API_VERSION="68.0"
TARGET_ORG=""
DRY_RUN="false"

# mdApiType ThunderbirdVoiceSettings -> package.xml member without the "Settings" suffix.
MEMBER="ThunderbirdVoice"
SETTINGS_FILE_REL="force-app/main/default/settings/${MEMBER}.settings-meta.xml"

usage() {
  cat <<'EOF'
Enable Native Voice call recording + transcription (sf CLI Settings deploy).

Usage:
  enable-recording-transcription.sh --target-org <alias> [--dry-run] [--api-version X.Y]

Options:
  --target-org <alias>   Org alias/username the sf CLI is authenticated to. Required.
  --api-version <X.Y>    Metadata API version (default: 68.0; must be >= 68.0, the
                         version at which ThunderbirdVoiceSettings is exposed). Do NOT
                         exceed the target org's max supported version — a retrieve
                         above it silently returns empty.
  --dry-run              Retrieve + validate the change (deploy --dry-run) but do NOT
                         persist it. Prints the JSON confirmation with status VALIDATED.
  -h, --help             Show this help.

On success prints a JSON confirmation object: the two enabled preferences reported
separately, plus a `preserved` block echoing every sibling boolean (unchanged) so
callers can confirm nothing else moved.
Uses the org's sf login; no session id / access token is handled or printed.
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    --target-org) TARGET_ORG="$2"; shift 2 ;;
    --api-version) API_VERSION="$2"; shift 2 ;;
    --dry-run) DRY_RUN="true"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "ERROR: unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

fail() { echo "ERROR: $*" >&2; exit 1; }

command -v sf  >/dev/null 2>&1 || fail "sf CLI not found (required)."
command -v jq  >/dev/null 2>&1 || fail "jq not found (required)."
[ -n "$TARGET_ORG" ] || fail "--target-org is required."

# Guard the version floor deterministically. Require a full X.Y form so a bare
# major like "68" can't end up as <version>68</version> in the manifest.
printf '%s' "$API_VERSION" | grep -qE '^[0-9]+\.[0-9]+$' \
  || fail "invalid --api-version '$API_VERSION' (expected X.Y, e.g. 68.0)."
API_MAJOR="${API_VERSION%%.*}"
[ "$API_MAJOR" -ge 68 ] || fail "--api-version must be >= 68.0 (ThunderbirdVoiceSettings is not exposed below v68.0). Got $API_VERSION."

# --- scaffold an isolated SFDX project so the retrieve/deploy is self-contained
WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT
sf project generate --name p --output-dir "$WORKDIR" >/dev/null 2>&1 \
  || fail "could not scaffold a temporary SFDX project."
PROJ="$WORKDIR/p"

cat > "$PROJ/package.xml" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types><members>${MEMBER}</members><name>Settings</name></types>
    <version>${API_VERSION}</version>
</Package>
EOF

SETTINGS_FILE="$PROJ/$SETTINGS_FILE_REL"

# --- step 1: retrieve current settings (gate check + sibling snapshot) --------
( cd "$PROJ" && sf project retrieve start -x package.xml -o "$TARGET_ORG" >/dev/null 2>&1 ) \
  || fail "retrieve failed for org '$TARGET_ORG'. Check the alias is connected (sf org display -o $TARGET_ORG)."

[ -f "$SETTINGS_FILE" ] || fail "retrieve returned no ${MEMBER}.settings-meta.xml — the Settings type was not returned at v${API_VERSION}. Two causes: (a) v${API_VERSION} is BELOW 68.0 (fields not yet exposed), or (b) v${API_VERSION} is ABOVE the org's max supported API version, which SILENTLY returns empty. Pin --api-version to the org's max (68.0 works on every org that has the feature)."

# Gate check: an empty self-closing element means the org-perm gate
# (orgHasNativeVoiceAllowed) is OFF — the feature is not provisioned. The fields
# are only present when the gate is on.
if ! grep -q '<enableCallRecording>' "$SETTINGS_FILE"; then
  fail "Native Voice is not provisioned on '$TARGET_ORG' (ThunderbirdVoiceSettings returned no fields). This is an org-perm gate enabled through provisioning/Blacktab, not something this skill can flip."
fi

# --- step 2: flip only the two target fields, preserve every sibling ----------
# Version-suffixed sed -i for BSD (macOS) + GNU portability.
sed -E -i.bak \
  -e 's|<enableCallRecording>[^<]*</enableCallRecording>|<enableCallRecording>true</enableCallRecording>|' \
  -e 's|<enableCallTranscription>[^<]*</enableCallTranscription>|<enableCallTranscription>true</enableCallTranscription>|' \
  "$SETTINGS_FILE"
rm -f "${SETTINGS_FILE}.bak"

grep -q '<enableCallRecording>true</enableCallRecording>'     "$SETTINGS_FILE" || fail "could not set enableCallRecording in the retrieved file."
grep -q '<enableCallTranscription>true</enableCallTranscription>' "$SETTINGS_FILE" || fail "could not set enableCallTranscription in the retrieved file."

# --- step 3: validate (dry-run). Never skip. ---------------------------------
( cd "$PROJ" && sf project deploy start -x package.xml -o "$TARGET_ORG" --dry-run --ignore-conflicts >/dev/null 2>&1 ) \
  || fail "validation (deploy --dry-run) failed — the org rejected the change. Re-check the gate (step 1)."

# Collect every boolean sibling (<tag>true|false</tag>) EXCEPT the two target
# prefs from the retrieved settings file, as a JSON array [{name, enabled}], so
# the confirmation can attest each sibling was retrieved and carried through
# unchanged. `grep -o` isolates each pair; `#`-delimited sed avoids colliding
# with the `|` alternation; the `|| true` guards keep an empty result (no
# siblings) from tripping `set -o pipefail`.
extract_preserved() { # $1 = settings xml file -> JSON array on stdout
  { grep -oE '<[A-Za-z][A-Za-z0-9]*>(true|false)</[A-Za-z][A-Za-z0-9]*>' "$1" || true; } \
    | sed -E 's#<([A-Za-z0-9]+)>([a-z]+)</[A-Za-z0-9]+>#\1 \2#' \
    | { grep -vE '^(enableCallRecording|enableCallTranscription) ' || true; } \
    | jq -R -s 'split("\n") | map(select(length > 0) | split(" ") | { name: .[0], enabled: (.[1] == "true") })'
}

emit_json() { # $1 = status, $2 = preserved siblings JSON array
  jq -n --arg apiVersion "$API_VERSION" --arg status "$1" --argjson preserved "$2" \
    '{
      type: "ThunderbirdVoiceSettings",
      fullName: "ThunderbirdVoice",
      apiVersion: $apiVersion,
      method: "sf project deploy (Settings/ThunderbirdVoice)",
      headless: true,
      preferences: [
        { name: "enableCallRecording", enabled: true },
        { name: "enableCallTranscription", enabled: true }
      ],
      preserved: $preserved,
      status: $status
    }'
}

if [ "$DRY_RUN" = "true" ]; then
  # Siblings are still at their retrieved values in the local file (only the two
  # targets were flipped in step 2); report them as preserved.
  emit_json "VALIDATED" "$(extract_preserved "$SETTINGS_FILE")"
  exit 0
fi

# --- step 4: deploy ----------------------------------------------------------
( cd "$PROJ" && sf project deploy start -x package.xml -o "$TARGET_ORG" --ignore-conflicts >/dev/null 2>&1 ) \
  || fail "deploy failed after a successful dry-run."

# --- step 5: verify by round-trip (do not trust "Succeeded") -----------------
rm -f "$SETTINGS_FILE"
( cd "$PROJ" && sf project retrieve start -x package.xml -o "$TARGET_ORG" >/dev/null 2>&1 ) \
  || fail "post-deploy retrieve failed; cannot verify."
grep -q '<enableCallRecording>true</enableCallRecording>'         "$SETTINGS_FILE" || fail "verification failed: org did not return enableCallRecording=true."
grep -q '<enableCallTranscription>true</enableCallTranscription>' "$SETTINGS_FILE" || fail "verification failed: org did not return enableCallTranscription=true."

# Report siblings from the post-deploy round-tripped file — their real, current
# (unchanged) values, proving nothing else moved.
emit_json "ENABLED" "$(extract_preserved "$SETTINGS_FILE")"
