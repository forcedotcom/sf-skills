#!/usr/bin/env python3
"""
Download a licensed stock image to the local filesystem using org credentials.

Usage:
    python3 download-stock-image.py --url <image_url> --id <asset_id> --format <output_format> [--output-dir <dir>] [--preview]
"""

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ALLOWED_FORMATS = {"jpg", "jpeg", "png", "webp", "gif", "eps", "svg", "tiff", "tif"}

# Formats VS Code can render in its built-in image preview. EPS/TIFF are
# binary formats VS Code can't display — opening them shows a "damaged file"
# error even though the download is fine, so --preview is skipped for these.
PREVIEWABLE_FORMATS = {"jpg", "jpeg", "png", "webp", "gif", "svg"}


def run_sf_json(cmd: list[str]) -> dict:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: command failed: {' '.join(cmd)}\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(f"Error: failed to parse JSON from {' '.join(cmd)}: {e}", file=sys.stderr)
        sys.exit(1)


def get_access_token() -> str:
    target_org_data = run_sf_json(["sf", "config", "get", "target-org", "--json"])
    target_org = (target_org_data.get("result") or [{}])[0].get("value")
    if not target_org:
        print("Error: no target-org configured", file=sys.stderr)
        sys.exit(1)

    token_data = run_sf_json(
        ["sf", "org", "auth", "show-access-token", "--target-org", target_org, "--no-prompt", "--json"]
    )
    access_token = (token_data.get("result") or {}).get("accessToken")
    if not access_token:
        print(f"Error: failed to retrieve access token for org '{target_org}'", file=sys.stderr)
        sys.exit(1)
    return access_token


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download a licensed stock image using org credentials."
    )
    parser.add_argument("--url", required=True, help="URL of the licensed image to download")
    parser.add_argument("--id", required=True, dest="asset_id", help="Asset ID used as the output filename")
    parser.add_argument("--format", required=True, choices=sorted(ALLOWED_FORMATS), help="Image format")
    parser.add_argument("--output-dir", default="stockimages", help="Directory to save the image")
    parser.add_argument("--preview", action="store_true", help="Open the image in VS Code after download")
    args = parser.parse_args()

    if "/" in args.asset_id or ".." in args.asset_id:
        print(f"Error: invalid asset ID '{args.asset_id}'. Must not contain '/' or '..'.", file=sys.stderr)
        sys.exit(1)

    if not args.url.startswith("https://"):
        print("Error: URL must start with https://", file=sys.stderr)
        sys.exit(1)

    access_token = get_access_token()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{args.asset_id}.{args.format}"

    request = urllib.request.Request(
        args.url, headers={"Authorization": f"Bearer {access_token}"}
    )
    try:
        with urllib.request.urlopen(request) as response, open(output_file, "wb") as f:
            f.write(response.read())
    except (urllib.error.URLError, OSError) as e:
        print(f"Error: failed to download image from {args.url}: {e}", file=sys.stderr)
        sys.exit(1)

    print(output_file)

    if args.preview:
        if args.format in PREVIEWABLE_FORMATS:
            subprocess.run(["code", str(output_file)])
        else:
            print(
                f"Note: '{args.format}' is not previewable in VS Code; skipping --preview.",
                file=sys.stderr,
            )


if __name__ == "__main__":
    main()
