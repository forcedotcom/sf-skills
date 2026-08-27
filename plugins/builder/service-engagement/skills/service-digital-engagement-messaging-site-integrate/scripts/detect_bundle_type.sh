#!/usr/bin/env bash
# detect_bundle_type.sh
# Deterministically detects whether an Experience Cloud site retrieved into a
# directory is an LWR (DigitalExperienceBundle) or Aura (ExperienceBundle) site
# by checking for the shape-defining file each bundle type produces.
#
# Assumes the caller has already invoked `sf project retrieve start` for one or
# both bundle types into <retrieve-dir>. This script only performs the
# deterministic path check — it does not call the CLI.
#
# Usage:
#   detect_bundle_type.sh <retrieve-dir> <siteName>
#
# Emits exactly one of: LWR, AURA, UNKNOWN
# Exit codes:
#   0 = LWR or AURA
#   1 = UNKNOWN or invalid args

set -euo pipefail

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <retrieve-dir> <siteName>" >&2
    echo "UNKNOWN"
    exit 1
fi

RETRIEVE_DIR="$1"
SITE_NAME="$2"

LWR_MARKER="${RETRIEVE_DIR}/digitalExperiences/site/${SITE_NAME}/sfdc_cms__view/home/content.json"
AURA_MARKER="${RETRIEVE_DIR}/experiences/${SITE_NAME}/views/homeGuestLayout.json"

if [ -f "$LWR_MARKER" ]; then
    echo "LWR"
    exit 0
fi

if [ -f "$AURA_MARKER" ]; then
    echo "AURA"
    exit 0
fi

echo "UNKNOWN"
exit 1
