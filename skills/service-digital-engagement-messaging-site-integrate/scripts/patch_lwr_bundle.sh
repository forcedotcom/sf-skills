#!/usr/bin/env bash
# patch_lwr_bundle.sh
# Idempotently inserts (or updates in place) the experience_messaging:embeddedMessaging
# component inside the "content" region of an LWR site's home/content.json.
#
# Deterministic path — same input yields the same output. If the component
# already exists inside .contentBody.component.children[] (recursively), its
# .attributes are refreshed and the existing .id is preserved. Otherwise a new
# community_layout:section wrapper is appended to the region whose
# .type == "region" AND .name == "content".
#
# Usage:
#   patch_lwr_bundle.sh <content.json> <deploymentName> <scrtUrl> <siteEndpoint>
#
# Requires: jq, uuidgen (or /proc/sys/kernel/random/uuid, or python3).

set -euo pipefail

if [ "$#" -ne 4 ]; then
    echo "Usage: $0 <content.json> <deploymentName> <scrtUrl> <siteEndpoint>" >&2
    exit 1
fi

CONTENT_JSON="$1"
DEPLOYMENT_NAME="$2"
SCRT_URL="$3"
SITE_ENDPOINT="$4"

if [ ! -f "$CONTENT_JSON" ]; then
    echo "Error: file not found: $CONTENT_JSON" >&2
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

    def has_messaging(children):
        (children // []) | any(
            (.definition? == "experience_messaging:embeddedMessaging") or
            has_messaging(.children // [])
        );

    def update_messaging(children):
        (children // []) | map(
            if .definition? == "experience_messaging:embeddedMessaging" then
                .attributes = attrs
            elif (.children // []) | length > 0 then
                .children = update_messaging(.children)
            else . end
        );

    def section_config:
        ({columns: [{id: $uuidRegion, width: 12}]} | tostring);

    def new_section:
        {
            id: $uuidSection,
            definition: "community_layout:section",
            sectionConfig: section_config,
            children: [
                {
                    id: $uuidRegion,
                    name: "column",
                    title: "Column",
                    type: "region",
                    children: [
                        {
                            id: $uuidMessaging,
                            definition: "experience_messaging:embeddedMessaging",
                            attributes: attrs
                        }
                    ]
                }
            ]
        };

    def patch_region:
        if has_messaging(.children // []) then
            .children = update_messaging(.children)
        else
            .children = ((.children // []) + [new_section])
        end;

    .contentBody.component.children |=
        (map(
            if (.type? == "region") and (.name? == "content") then
                patch_region
            else . end
        ))
    ' "$CONTENT_JSON" > "$TMP_OUT"

mv "$TMP_OUT" "$CONTENT_JSON"
trap - EXIT

echo "Patched: $CONTENT_JSON"
