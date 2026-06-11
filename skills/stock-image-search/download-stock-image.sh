#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<EOF
Usage: $(basename "$0") --url <image_url> --id <asset_id> --format <output_format> [--output-dir <dir>] [--preview]

Required:
  --url        URL of the licensed image to download (from download_stock_image response)
  --id         Asset ID used as the output filename
  --format     Image format (jpg, jpeg, png, webp)

Optional:
  --output-dir Directory to save the image (default: stockimages)
  --preview    Open the image in VS Code after download
EOF
  exit 1
}

OUTPUT_DIR="stockimages"
PREVIEW=false
URL=""
ASSET_ID=""
FORMAT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --url)        URL="$2"; shift 2 ;;
    --id)         ASSET_ID="$2"; shift 2 ;;
    --format)     FORMAT="$2"; shift 2 ;;
    --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
    --preview)    PREVIEW=true; shift ;;
    *)            usage ;;
  esac
done

if [[ -z "$URL" || -z "$ASSET_ID" || -z "$FORMAT" ]]; then
  usage
fi

case "$FORMAT" in
  jpg|jpeg|png|webp) ;;
  *) echo "Error: invalid format '$FORMAT'. Must be jpg, jpeg, png, or webp." >&2; exit 1 ;;
esac

if [[ "$ASSET_ID" == */* || "$ASSET_ID" == *..* ]]; then
  echo "Error: invalid asset ID '$ASSET_ID'. Must not contain '/' or '..'." >&2
  exit 1
fi

if [[ ! "$URL" =~ ^https:// ]]; then
  echo "Error: URL must start with https://" >&2
  exit 1
fi

TARGET_ORG=$(sf config get target-org --json | jq -r '.result[0].value')
ACCESS_TOKEN=$(sf org display --target-org "$TARGET_ORG" --json | jq -r '.result.accessToken')

if [[ -z "$ACCESS_TOKEN" || "$ACCESS_TOKEN" == "null" ]]; then
  echo "Error: failed to retrieve access token for org '$TARGET_ORG'" >&2
  exit 1
fi

mkdir -p "$OUTPUT_DIR"

OUTPUT_FILE="${OUTPUT_DIR}/${ASSET_ID}.${FORMAT}"

if ! curl -f -H "Authorization: Bearer $ACCESS_TOKEN" -o "$OUTPUT_FILE" -- "$URL"; then
  echo "Error: failed to download image from $URL" >&2
  exit 1
fi

echo "$OUTPUT_FILE"

if [[ "$PREVIEW" == true ]]; then
  code "$OUTPUT_FILE"
fi
