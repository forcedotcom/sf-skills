#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<EOF
Usage: $(basename "$0") --url <image_url> --id <response_id> --format <output_format> [--output-dir <dir>] [--preview]

Required:
  --url        URL of the generated image to download
  --id         Response ID used as the output filename
  --format     Output format (webp, jpeg, png)

Optional:
  --output-dir Directory to save the image (default: generatedimages)
  --preview    Open the image in VS Code after download
EOF
  exit 1
}

OUTPUT_DIR="generatedimages"
PREVIEW=false
URL=""
RESPONSE_ID=""
FORMAT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --url)        URL="$2"; shift 2 ;;
    --id)         RESPONSE_ID="$2"; shift 2 ;;
    --format)     FORMAT="$2"; shift 2 ;;
    --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
    --preview)    PREVIEW=true; shift ;;
    *)            usage ;;
  esac
done

if [[ -z "$URL" || -z "$RESPONSE_ID" || -z "$FORMAT" ]]; then
  usage
fi

case "$FORMAT" in
  webp|jpeg|png) ;;
  *) echo "Error: invalid format '$FORMAT'. Must be webp, jpeg, or png." >&2; exit 1 ;;
esac

if [[ "$RESPONSE_ID" == */* || "$RESPONSE_ID" == *..* ]]; then
  echo "Error: invalid response ID '$RESPONSE_ID'. Must not contain '/' or '..'." >&2
  exit 1
fi

if [[ ! "$URL" =~ ^https:// ]]; then
  echo "Error: URL must start with https://" >&2
  exit 1
fi

TARGET_ORG=$(sf config get target-org --json | jq -r '.result[0].value')

if [[ -z "$TARGET_ORG" || "$TARGET_ORG" == "null" ]]; then
  echo "Error: no target-org configured. Run 'sf config set target-org <org>'" >&2
  exit 1
fi

ACCESS_TOKEN=$(sf org display --target-org "$TARGET_ORG" --json | jq -r '.result.accessToken')

if [[ -z "$ACCESS_TOKEN" || "$ACCESS_TOKEN" == "null" ]]; then
  echo "Error: failed to retrieve access token for org '$TARGET_ORG'" >&2
  exit 1
fi

mkdir -p "$OUTPUT_DIR"

OUTPUT_FILE="${OUTPUT_DIR}/${RESPONSE_ID}.${FORMAT}"

if ! curl -fsS -H "Authorization: Bearer $ACCESS_TOKEN" -o "$OUTPUT_FILE" -- "$URL"; then
  rm -f "$OUTPUT_FILE"
  echo "Error: failed to download image from $URL" >&2
  exit 1
fi

echo "$OUTPUT_FILE"

if [[ "$PREVIEW" == true ]]; then
  code "$OUTPUT_FILE"
fi
