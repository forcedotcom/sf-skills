---
name: generating-images
description: "Generates high-fidelity visual assets, logos, and UI mockups using the media-management MCP server. Trigger this skill whenever the user asks to generate an image, create a logo, produce a hero banner, design a UI icon, or build a visual asset. It is explicitly designed to handle technical specifications including file formats (PNG, JPEG, WEBP), specific dimensions (e.g. 1024x1024), and transparency requirements. Use this skill when the user needs to integrate generated imagery into application code or web pages. It ensures consistent output quality and provides a standardized SVG fallback if the generation tool is unavailable."
metadata:
  version: "1.0"
---

# Generating Images

## Goal

To programmatically generate, download, and preview visual assets requested by the user, ensuring specific format and quality standards are met while providing a robust fallback mechanism.

## Workflow

1. Check if the `media-management` MCP server is configured and its `create_image` tool is available.
2. If available, use `create_image` to generate the image.
3. If not available, use the placeholder fallback below.

## MCP: media-management

**Tool:** `create_image`

Check your available tools. If `create_image` is present, use it as the primary image generation method — pass the natural language prompt and applicable parameters from the table below. (`media-management` here refers to the MCP server name, not this skill.)

If `create_image` is not in your tool list, the `media-management` MCP is not configured — use the placeholder fallback below.

## Image Generation Parameters

Use these defaults unless the user specifies otherwise:

| Parameter | Default | Options |
|---|---|---|
| `model` | `Standard` | `Standard`, `Premium` |
| `size` | `auto` | `auto`, `1024x1024`, `1536x1024`, `1024x1536` (pick closest to user-requested size) |
| `quality` | `medium` | `low`, `medium`, `high` |
| `outputCompression` | `75` | `0–100` (webp/jpeg only) |
| `outputFormat` | `webp` | `webp`, `jpeg`, `png` |
| `background` | `auto` | `auto`, `transparent`, `opaque` |

**Format rule:** If `outputFormat` is `png`, set `outputCompression` to `100`.

## After Successful Generation

Run `download-image.sh` (located in this skill's `scripts/` directory) to download and preview the image:

```bash
bash scripts/download-image.sh \
  --url "<image_url_from_response>" \
  --id "<responseId>" \
  --format "<outputFormat>" \
  --preview
```

The script handles credential retrieval, download, and VS Code preview. Pass `--output-dir <dir>` to override the default `generatedimages/` directory.

**Never resize or post-process the generated image with external tools.** To control display dimensions, use CSS properties (e.g. `width`, `height`, `object-fit`) at the point of use.

## Fallback: Use placeholder URL

If image generation fails or is not enabled, return the following URL as the image source — do not download it, do not save it locally:

```
https://cdn.scs.static.lightning.force.com/content/assets/d5222d4a11e6c2b735152d7eea824ce4/placeholder.svg
```

Use this URL directly wherever the image is referenced in code (e.g. as a `src` attribute or CSS `url()`).

## Placeholder Policy

There is only one placeholder URL. Do not download it, modify it, or generate alternative placeholders using Python, ImageMagick, or any other tool.

If the user requests a placeholder of a specific size or format, inform them that only this placeholder URL is available and direct them to use CSS properties (e.g. `width`, `height`, `object-fit`) to scale it at the point of use.
