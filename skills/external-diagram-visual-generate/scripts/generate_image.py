#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["google-genai>=1.0.0", "pillow>=10.0.0"]
# ///
"""
Direct Gemini API image generation with resolution control.

This script complements the CLI extension for power features:
- Resolution control: 1K (draft), 2K (medium), 4K (production)
- Image editing: Modify existing images with natural language
- Timestamp filenames: Automatic versioning for iteration tracking

Usage:
  # Generate new image at 1K (draft)
  uv run scripts/generate_image.py -p "Salesforce ERD diagram..." -f "account-erd.png"

  # Generate at 4K (production)
  uv run scripts/generate_image.py -p "Salesforce ERD diagram..." -f "account-erd.png" -r 4K

  # Edit existing image
  uv run scripts/generate_image.py -p "Add a legend in bottom right" -i input.png -f "output.png"

Workflow: Draft → Iterate → Final
  1. Generate at 1K for quick feedback (~3s)
  2. Refine prompt until layout/content is correct
  3. Generate final at 4K for production quality (~10s)

License: MIT
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime
from io import BytesIO
from pathlib import Path

try:
    from google import genai
    from google.genai import types
    from PIL import Image
except ImportError as e:
    print(f"Error: Missing dependency - {e}")
    print("Run with: uv run scripts/generate_image.py ...")
    sys.exit(1)


# Resolution mapping (uppercase K required by API!)
RESOLUTIONS = {
    "1K": "1K",   # ~1024px - drafts, fast iteration
    "2K": "2K",   # ~2048px - medium quality
    "4K": "4K",   # ~4096px - production quality
}

# Default output directory (matches CLI extension)
OUTPUT_DIR = Path.home() / "nanobanana-output"


def get_auto_resolution(image_path: str) -> str:
    """Auto-detect resolution based on input image dimensions."""
    try:
        with Image.open(image_path) as img:
            max_dim = max(img.width, img.height)
            if max_dim < 1500:
                return "1K"
            elif max_dim < 3000:
                return "2K"
            else:
                return "4K"
    except Exception:
        return "1K"


def generate_image(
    prompt: str,
    filename: str,
    resolution: str = "1K",
    input_image: str | None = None,
    api_key: str | None = None,
    aspect_ratio: str | None = None,
) -> str:
    """Generate or edit an image using Gemini 3 Pro Image API.

    Args:
        prompt: Text description for generation or editing instruction
        filename: Output filename (timestamp will be prepended)
        resolution: Output resolution - 1K, 2K, or 4K (uppercase required!)
        input_image: Path to existing image for editing (optional)
        api_key: Gemini API key (falls back to GEMINI_API_KEY env var)
        aspect_ratio: Aspect ratio like "16:9", "1:1", "4:3" (optional)

    Returns:
        Path to saved image file
    """
    # Get API key
    api_key = api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY not found. Set it in ~/.zshrc or pass via --api-key"
        )

    # Initialize client
    client = genai.Client(api_key=api_key)

    # Build contents (image first if editing, then prompt)
    contents = []
    if input_image:
        img = Image.open(input_image)
        # Convert RGBA to RGB if needed
        if img.mode == "RGBA":
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        contents.append(img)

        # Auto-detect resolution for editing if not specified
        if resolution == "1K":
            resolution = get_auto_resolution(input_image)
            print(f"Auto-detected resolution: {resolution}")

    contents.append(prompt)

    # Build image config
    image_config_kwargs = {"image_size": RESOLUTIONS[resolution]}
    if aspect_ratio:
        image_config_kwargs["aspect_ratio"] = aspect_ratio

    # Generate with resolution config
    print(f"Generating at {resolution} resolution...")
    response = client.models.generate_content(
        model="gemini-3-pro-image-preview",
        contents=contents,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE", "TEXT"],
            image_config=types.ImageConfig(**image_config_kwargs),
        ),
    )

    # Save output with timestamp filename
    OUTPUT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

    # Clean filename (remove extension if present, we'll add .png)
    clean_name = Path(filename).stem
    output_filename = f"{timestamp}-{clean_name}.png"
    output_path = OUTPUT_DIR / output_filename

    # Extract and save image from response
    for part in response.candidates[0].content.parts:
        if hasattr(part, "inline_data") and part.inline_data:
            img = Image.open(BytesIO(part.inline_data.data))
            # Convert to RGB if needed
            if img.mode == "RGBA":
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])
                img = background
            img.save(output_path, "PNG")
            return str(output_path)

    raise RuntimeError("No image data in response")


def main():
    parser = argparse.ArgumentParser(
        description="Generate images with Gemini 3 Pro Image API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Draft (fast, cheap)
  uv run generate_image.py -p "Account ERD diagram" -f "account-erd.png"

  # Production (4K)
  uv run generate_image.py -p "Account ERD diagram" -f "account-erd.png" -r 4K

  # Edit existing image
  uv run generate_image.py -p "Add legend" -i prev.png -f "updated.png"

  # With aspect ratio
  uv run generate_image.py -p "Dashboard mockup" -f "dash.png" -a "16:9"
        """,
    )
    parser.add_argument(
        "-p", "--prompt",
        required=True,
        help="Image description or editing instruction",
    )
    parser.add_argument(
        "-f", "--filename",
        required=True,
        help="Output filename (timestamp auto-prepended)",
    )
    parser.add_argument(
        "-r", "--resolution",
        choices=["1K", "2K", "4K"],
        default="1K",
        help="Output resolution (default: 1K for drafts)",
    )
    parser.add_argument(
        "-i", "--input-image",
        help="Path to existing image for editing",
    )
    parser.add_argument(
        "-k", "--api-key",
        help="Gemini API key (defaults to GEMINI_API_KEY env var)",
    )
    parser.add_argument(
        "-a", "--aspect-ratio",
        help="Aspect ratio (e.g., '16:9', '1:1', '4:3')",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Don't auto-open the image in Preview after generation",
    )

    args = parser.parse_args()

    try:
        output_path = generate_image(
            prompt=args.prompt,
            filename=args.filename,
            resolution=args.resolution,
            input_image=args.input_image,
            api_key=args.api_key,
            aspect_ratio=args.aspect_ratio,
        )
        print(f"✅ Saved: {output_path}")

        # Auto-open in macOS Preview unless --no-open is specified
        if not args.no_open:
            subprocess.run(["open", output_path], check=False)
            print(f"   📸 Opened in Preview")
        else:
            print(f"   Open with: open {output_path}")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
