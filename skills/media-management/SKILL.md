---
name: media-management
description: Generates new images using AI image generation tools. If image generation is not available or fails, uses a placeholder.svg. Use when the user asks to generate, create, or add new images or media assets — not when searching for existing media.
---

# Media Management

## Workflow

1. Check if the `media-management` MCP server is configured and its `create_image` tool is available.
2. If available, use `create_image` to generate the image.
3. If not available, use the placeholder fallback below.

## MCP: media-management

**Tool:** `create_image`

Check your available tools. If `create_image` is present, use it as the primary image generation method — pass the natural language prompt and applicable parameters from the table below.

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

Automatically download and preview the image:

**1. Retrieve credentials:**
```bash
TARGET_ORG=$(sf config get target-org --json | jq -r '.result[0].value')
```

**2. Download the image:**
```bash
mkdir -p "generatedimages"
curl -f -H "Authorization: Bearer $ACCESS_TOKEN" "$URL" -o "generatedimages/<responseId>.<outputFormat>"
```

**3. Preview in VS Code:**
```bash
code generatedimages/<responseId>.<outputFormat>
```

**Never resize or post-process the generated image with external tools.** To control display dimensions, use CSS properties (e.g. `width`, `height`, `object-fit`) at the point of use.

## Fallback: Use placeholder.svg

If image generation fails or is not enabled:

1. Check if `generatedimages/placeholder.svg` already exists.
2. If it exists, use it as-is — do not download again.
3. If it does not exist, download it:
```bash
mkdir -p generatedimages
curl -f -o generatedimages/placeholder.svg "https://res.cloudinary.com/dveb6nwve/image/upload/v1775081606/placeholderFinal_l03h2n.svg"
```

## Placeholder Policy

There is only one placeholder: `generatedimages/placeholder.svg`.

- **Never** generate alternative placeholder images using Python, ImageMagick, or any other tool.
- **Never** resize or create new placeholder files of different dimensions.
- If the user requests a placeholder of a specific size or format, inform them that only `placeholder.svg` is available and that it can be scaled to any size using CSS properties (e.g. `width`, `height`, `object-fit`) at the point of use.