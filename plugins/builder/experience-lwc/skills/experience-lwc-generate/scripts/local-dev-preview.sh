#!/usr/bin/env bash
# Local Development Server — preview LWC components with hot reload (no deployment needed).
# Requires an active org connection. Commands install just-in-time on first run and open
# a browser with live preview. Changes to .js, .html, and .css files auto-reload instantly.
#
# Usage: Pass --target-org <alias> and choose the mode that matches your use case.

TARGET_ORG="${1:-}"

if [ -z "$TARGET_ORG" ]; then
    echo "Usage: $0 <org-alias> [component|app|site]"
    echo "  component  Preview a single LWC component in isolation (default)"
    echo "  app        Preview a Lightning Experience app locally"
    echo "  site       Preview an Experience Cloud site locally"
    exit 1
fi

MODE="${2:-component}"

case "$MODE" in
    component)
        sf lightning dev component --target-org "$TARGET_ORG"
        ;;
    app)
        sf lightning dev app --target-org "$TARGET_ORG"
        ;;
    site)
        sf lightning dev site --target-org "$TARGET_ORG"
        ;;
    *)
        echo "Unknown mode: $MODE. Choose one of: component, app, site"
        exit 1
        ;;
esac
