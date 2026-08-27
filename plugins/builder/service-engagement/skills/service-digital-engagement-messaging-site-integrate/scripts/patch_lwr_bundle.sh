#!/usr/bin/env bash
# patch_lwr_bundle.sh
# Idempotently inserts (or updates in place) the experience_messaging:embeddedMessaging
# component into the footer region of every sfdc_cms__themeLayout content.json in an
# LWR DigitalExperienceBundle. Targeting the themeLayout footer places the widget
# site-wide (as a floating overlay on every page), equivalent to the Aura themeFooter.
#
# Usage:
#   patch_lwr_bundle.sh <site-dir> <deploymentName> <scrtUrl> <siteEndpoint>
#
#   <site-dir> is the path to the site root, e.g.:
#     force-app/main/default/digitalExperiences/site/<siteName>
#
# Requires: jq, uuidgen (or /proc/sys/kernel/random/uuid, or python3).

set -euo pipefail

if [ "$#" -ne 4 ]; then
    echo "Usage: $0 <site-dir> <deploymentName> <scrtUrl> <siteEndpoint>" >&2
    exit 1
fi

SITE_DIR="$1"
DEPLOYMENT_NAME="$2"
SCRT_URL="$3"
SITE_ENDPOINT="$4"

if [ ! -d "$SITE_DIR" ]; then
    echo "Error: site directory not found: $SITE_DIR" >&2
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

# Find all themeLayout content.json files (skip mobile/tablet rendition subdirs)
THEME_LAYOUTS=$(find "$SITE_DIR/sfdc_cms__themeLayout" -maxdepth 2 -name "content.json" 2>/dev/null || true)

if [ -z "$THEME_LAYOUTS" ]; then
    echo "Error: no sfdc_cms__themeLayout/*/content.json files found under $SITE_DIR" >&2
    exit 1
fi

PATCHED=0
SKIPPED=0

while IFS= read -r CONTENT_JSON; do
    # Skip mobile/tablet rendition files (they live in a subdirectory of the layout dir)
    LAYOUT_DIR=$(dirname "$CONTENT_JSON")
    PARENT_DIR=$(dirname "$LAYOUT_DIR")
    GRANDPARENT=$(basename "$PARENT_DIR")
    if [ "$GRANDPARENT" != "sfdc_cms__themeLayout" ]; then
        continue
    fi

    UUID_MESSAGING="$(gen_uuid)"
    TMP_OUT="$(mktemp)"
    trap 'rm -f "$TMP_OUT"' EXIT

    jq \
        --arg deploymentName "$DEPLOYMENT_NAME" \
        --arg scrtUrl "$SCRT_URL" \
        --arg siteEndpoint "$SITE_ENDPOINT" \
        --arg uuidMessaging "$UUID_MESSAGING" \
        '
        def attrs:
            {
                deploymentName: $deploymentName,
                scrtUrl: $scrtUrl,
                siteEndpoint: $siteEndpoint,
                isExpSiteAuthMode: false,
                hideChatButtonOnLoad: "Default",
                clientVersion: "WebV2"
            };

        # Recursively check whether a messaging component already exists
        def has_messaging:
            . as $n |
            if type == "array" then
                any(.[]; has_messaging)
            elif type == "object" then
                ((.definition? == "experience_messaging:embeddedMessaging") or
                 ((.children // []) | has_messaging))
            else false end;

        # Recursively update attributes of existing messaging component in place
        def update_messaging:
            if type == "array" then map(update_messaging)
            elif type == "object" then
                if .definition? == "experience_messaging:embeddedMessaging" then
                    .attributes = attrs
                elif (.children | type) == "array" then
                    .children |= update_messaging
                else . end
            else . end;

        # New standalone messaging component node (no section wrapper — it is a
        # floating overlay and does not need a layout container in the footer)
        def new_messaging:
            {
                id: $uuidMessaging,
                type: "component",
                definition: "experience_messaging:embeddedMessaging",
                attributes: attrs
            };

        # Inject into the footer region layout section. Two decisions, both made
        # over the ENTIRE footer subtree so a stale widget anywhere in the footer
        # is refreshed rather than duplicated:
        #   1. If the footer subtree already has a messaging component (in any
        #      region or as a direct section child), run update_messaging over
        #      the whole footer — never append a second one.
        #   2. Otherwise pick the best insertion slot: the first
        #      `community_layout:section` wrapper (by definition, since the footer
        #      can hold consent banners etc. before it) → its first inner region →
        #      else the section itself → else the footer root.
        # All child accessors default to [] so a component-only or empty footer
        # never pipes null into an array op (jq would abort).
        def patch_footer_region:
            . as $footer |
            if ($footer.children // []) | has_messaging then
                .children |= update_messaging
            else
                ([ ($footer.children // []) | to_entries[]
                   | select(.value.type? == "component"
                            and .value.definition? == "community_layout:section") ]
                 | .[0].key) as $si |
                if $si == null then
                    .children = ((.children // []) + [new_messaging])
                else
                    ((.children[$si].children // []) | to_entries
                     | map(select(.value.type? == "region")) | .[0].key) as $ri |
                    if $ri == null then
                        .children[$si].children =
                            ((.children[$si].children // []) + [new_messaging])
                    else
                        .children[$si].children[$ri].children =
                            ((.children[$si].children[$ri].children // []) + [new_messaging])
                    end
                end
            end;

        # Apply to every top-level footer region. Guard the children array so a
        # component-only layout (children == null) is a no-op, not a crash.
        .contentBody.component.children |= (
            (. // []) | map(
                if .type? == "region" and .name? == "footer" then
                    patch_footer_region
                else . end
            )
        )
        ' "$CONTENT_JSON" > "$TMP_OUT"

    mv "$TMP_OUT" "$CONTENT_JSON"
    trap - EXIT
    LAYOUT_NAME=$(basename "$(dirname "$CONTENT_JSON")")
    # Confirm the widget landed inside a FOOTER region specifically — not just
    # anywhere in the file. A stale messaging component elsewhere (e.g. the
    # content region) must not make a footerless layout count as patched, or the
    # script could exit 0 without ever placing the site-wide footer widget.
    # Recurse only into the footer region subtree(s) and look for the component.
    if jq -e '
        [ .contentBody.component.children[]?
          | select(.type? == "region" and .name? == "footer")
          | .. | select(type == "object" and .definition? == "experience_messaging:embeddedMessaging")
        ] | length > 0
    ' "$CONTENT_JSON" >/dev/null; then
        echo "Patched: $LAYOUT_NAME ($CONTENT_JSON)"
        PATCHED=$((PATCHED + 1))
    else
        echo "Skipped (no footer region): $LAYOUT_NAME ($CONTENT_JSON)" >&2
        SKIPPED=$((SKIPPED + 1))
    fi
done <<< "$THEME_LAYOUTS"

echo "Done: $PATCHED themeLayout(s) patched, $SKIPPED skipped."

if [ "$PATCHED" -eq 0 ]; then
    echo "Error: no themeLayout had a footer region to patch under $SITE_DIR" >&2
    exit 1
fi
