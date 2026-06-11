---
name: stock-image-search
description: "Searches Getty stock photography via the media-management MCP server and presents a clickable result list, then downloads the user's selected image. Use this skill when a user asks to \"find a stock image\", \"search for a photo of X\", \"get a royalty-free image\", \"find an ethical image\", \"look up a Getty image\", or when AI image generation fails and a stock fallback is appropriate. Triggers also for editorial/news photography requests. Does not apply to searching internal CMS / Data Cloud media (use searching-media), generating new images with AI (use generating-images), or applying brand guidelines (use applying-cms-brand). The skill ends after the result list is shown — Agentforce prompts the user for the selection. When the user picks one, the download flow at the bottom of this file is run to license and save the bytes locally."
compatibility: "Requires search_stock_images and download_stock_image MCP tools (media-management server)"
user-invocable: true
argument-hint: "<search query> [--orientation Horizontal|Vertical|Square|PanoramicHorizontal|PanoramicVertical] [--searchType Creative|Editorial] [--sortOrder BestMatch|MostPopular|Newest] [--pageSize N]"
metadata:
  version: "1.0"
---

# Stock Image Search (Getty via `media-management` MCP)

## Goal

Search Getty Images, present a concise clickable result list, and — on user selection — license and download the chosen image to disk.

## Workflow

1. Call `search_stock_images` with the user's query and any explicit options.
2. Render a numbered list with each title hyperlinked to its `previewUrl`. **End the turn.** Do not auto-download, write files, or ask a follow-up question — Agentforce injects its own picker prompt and a question here causes a duplicate "double ask".
3. When the user selects a result, run the download flow at the bottom of this file.

## Step 1 — Search

**MCP tool:** `search_stock_images` · **Timeout:** 30s · Default `pageSize: 5`.

| Parameter    | Required | Default     | Options                                                                          |
|--------------|----------|-------------|----------------------------------------------------------------------------------|
| `query`      | ✅       | —           | Natural language phrase                                                          |
| `searchType` | No       | `Creative`  | `Creative` (royalty-free stock), `Editorial` (rights-managed news/event imagery) |
| `orientation`| No       | _(none)_    | `Horizontal`, `Vertical`, `Square`, `PanoramicHorizontal`, `PanoramicVertical`   |
| `sortOrder`  | No       | `BestMatch` | `BestMatch`, `MostPopular`, `Newest`                                             |
| `pageSize`   | No       | `5`         | 1–100                                                                            |
| `page`       | No       | `1`         | 1-indexed                                                                        |

**Smart keyword extraction:** if the query is >20 words or returns no results, the tool LLM-extracts short keyword phrases and retries. The `effectiveQuery` field in the response shows what was actually sent — `null` if the original query was used unchanged.

**Per-result fields used:** `assetId`, `title`, `previewUrl`, `thumbnailUrl`, `width`, `height`, `licenseModel`, `artist`, `collection`. The response also returns `searchRequestId` (used by the download step). Do not display `assetId` or `searchRequestId` to the user.

## Step 2 — Present Results, then STOP

```markdown
1. [<title>](<previewUrl>) — <artist>, <width>×<height>, <licenseModel>
```

Prefix the list with `Getty searched for: <effectiveQuery>` only if `effectiveQuery` is non-null and differs from the user's original query.

After the list: stop. No "Pick 1–N", no "Reply with the number", no closing remark — Agentforce shows the selection UI on its own.

Do not download anything until the user replies with a selection.

---

# Download flow (separate invocation)

Run only when the user has selected a result from a prior search. Skip otherwise.

## Download (billed)

⚠️ **Each call spends a Getty download credit.** Only invoke after explicit user selection.

**MCP tool:** `download_stock_image` · **Timeout:** 60s

| Parameter         | Required | Default | Notes                                                                                   |
|-------------------|----------|---------|-----------------------------------------------------------------------------------------|
| `assetId`         | ✅       | —       | From the prior `search_stock_images` result                                             |
| `size`            | No       | `comp`  | `comp` (web-quality composite, default), `medium_jpg`, `largest` (full res, can exceed 100 MB) |
| `searchRequestId` | No       | —       | The `searchRequestId` from the originating search response. Pass it through so the service can record the asset's keywords and link the download to the search. |

Use `largest` only when the user explicitly asks for full/original resolution.

The response yields `url`, `format`, `assetId`, `managedContentBodyId`, `byteCount`, and tracking IDs (`contentGenAiOutputId`, child IDs).

**Non-interactive mode** (scheduled/headless, no user present): pick `images[0]` from the search and note auto-selection in the report.

## Save locally

```bash
bash skills/stock-image-search/download-stock-image.sh \
  --url "<url>" --id "<assetId>" --format "<format>" --preview
```

Pass `--output-dir <dir>` to override the default `stockimages/` directory. Use this script — not `curl`/`wget` — so the bearer-token retrieval and path-safety checks stay consistent across skills. Never resize or post-process; size at point of use via CSS (`width`, `height`, `object-fit`).

## Report

- Title and artist
- Local file path (printed by the script)
- `url` from the download response
- `managedContentBodyId`
- Attribution: `© Getty Images · {artist} · {collection}`

---

## Fallbacks & Errors

| Situation                          | Action                                                                  |
|------------------------------------|-------------------------------------------------------------------------|
| `errorMessage` non-null            | Show it; suggest a simpler query or different `searchType`/`orientation`|
| `images` empty                     | Suggest broader keywords; try `Editorial` vs `Creative`                 |
| MCP tools unavailable              | Use the placeholder URL below — do not download or save                 |
| Download fails                     | Show error; confirm with user before retrying (each retry is billed)    |

Placeholder (use directly as `src` / CSS `url()`):

```
https://cdn.scs.static.lightning.force.com/content/assets/d5222d4a11e6c2b735152d7eea824ce4/placeholder.svg
```

## Placeholder Policy

There is only one placeholder URL. Do not download it, modify it, or generate alternative placeholders using Python, ImageMagick, or any other tool. If the user asks for a placeholder of a specific size or format, tell them only this URL is available and direct them to use CSS to scale it at the point of use.
