#!/usr/bin/env bash
# patch_aura_bundle.sh
# Idempotently inserts (or updates in place) the
# experience_messaging:embeddedMessaging component inside an Aura site's
# homeGuestLayout.json.
#
# Locates the first .regions[] entry whose .components[] is non-empty and either
# refreshes the existing messaging component's .componentAttributes (preserving
# its .id) or appends a new forceCommunity:section wrapper containing the
# messaging component. Recursion descends into forceCommunity:section wrappers'
# nested .componentAttributes.regions[].components[].
#
# Usage:
#   patch_aura_bundle.sh <homeGuestLayout.json> <deploymentName> <scrtUrl> <siteEndpoint>
#
# Requires: jq, uuidgen (or /proc/sys/kernel/random/uuid, or python3).

set -euo pipefail

if [ "$#" -ne 4 ]; then
    echo "Usage: $0 <homeGuestLayout.json> <deploymentName> <scrtUrl> <siteEndpoint>" >&2
    exit 1
fi

LAYOUT_JSON="$1"
DEPLOYMENT_NAME="$2"
SCRT_URL="$3"
SITE_ENDPOINT="$4"

if [ ! -f "$LAYOUT_JSON" ]; then
    echo "Error: file not found: $LAYOUT_JSON" >&2
    exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
    echo "Error: jq is required" >&2
    exit 1
fi

gen_uuid() {
    if command -v uuidgen >/dev/null 2>&1; then
        uuidgen | tr '[:upper:]' '[:lower:]'
    elif [ -r /proc/sys/kernel/random/uuid ]; then
        cat /proc/sys/kernel/random/uuid
    else
        python3 -c 'import uuid; print(uuid.uuid4())'
    fi
}

UUID_SECTION="$(gen_uuid)"
UUID_REGION="$(gen_uuid)"
UUID_MESSAGING="$(gen_uuid)"

TMP_OUT="$(mktemp)"
trap 'rm -f "$TMP_OUT"' EXIT

jq \
    --arg deploymentName "$DEPLOYMENT_NAME" \
    --arg scrtUrl "$SCRT_URL" \
    --arg siteEndpoint "$SITE_ENDPOINT" \
    --arg uuidSection "$UUID_SECTION" \
    --arg uuidRegion "$UUID_REGION" \
    --arg uuidMessaging "$UUID_MESSAGING" \
    '
    def attrs:
        {
            deploymentName: $deploymentName,
            scrtUrl: $scrtUrl,
            siteEndpoint: $siteEndpoint,
            isExpSiteAuthMode: false,
            hideChatButtonOnLoad: "Default",
            clientVersion: "WebV1"
        };

    def has_messaging(components):
        (components // []) | any(
            (.componentName? == "experience_messaging:embeddedMessaging") or
            (any((.componentAttributes.regions // [])[]?; has_messaging(.components // [])))
        );

    def update_messaging(components):
        (components // []) | map(
            if .componentName? == "experience_messaging:embeddedMessaging" then
                .componentAttributes = attrs
            elif ((.componentAttributes.regions // []) | length) > 0 then
                .componentAttributes.regions |= map(
                    .components = update_messaging(.components)
                )
            else . end
        );

    def new_section:
        {
            id: $uuidSection,
            componentName: "forceCommunity:section",
            componentAttributes: {
                regions: [
                    {
                        id: $uuidRegion,
                        type: "region",
                        regionLabel: "Column",
                        regionName: "column",
                        renditionMap: {},
                        components: [
                            {
                                id: $uuidMessaging,
                                componentName: "experience_messaging:embeddedMessaging",
                                componentAttributes: attrs
                            }
                        ]
                    }
                ]
            }
        };

    # Find index of first region whose .components[] is non-empty.
    (.regions // []) as $regions
    | ($regions | to_entries | map(select((.value.components // []) | length > 0)) | .[0].key) as $idx
    | if $idx == null then
          .
      else
          .regions[$idx] |= (
              if has_messaging(.components // []) then
                  .components = update_messaging(.components)
              else
                  .components = ((.components // []) + [new_section])
              end
          )
      end
    ' "$LAYOUT_JSON" > "$TMP_OUT"

mv "$TMP_OUT" "$LAYOUT_JSON"
trap - EXIT

echo "Patched: $LAYOUT_JSON"
