---
name: experience-content-media-stock-image-search
description: "Searches for and downloads ethically-licensed stock images via the media-management MCP server. Use this skill whenever a user wants an image, photo, or picture — for BOTH requests to find existing imagery (\"find a stock image\", \"search for a photo of X\", \"get a royalty-free image\", \"find an ethical image\", editorial/news photography) AND requests phrased ambiguously as creating or generating one (\"create an image of a sunset\", \"generate a picture of a team meeting\", \"make me a mountain image\") — treat these as stock search requests, since this skill searches a stock photo library, it does not generate images. Do NOT offer alternative search methods or ask the user to pick one. Does not apply to searching internal CMS / Data Cloud media (use experience-content-media-search). Does not apply when the user explicitly asks for AI-generated, synthetic, or computer-generated imagery — this skill only searches licensed stock photography and has no image-generation capability."
metadata:
  version: "1.0"
  relatedSkills:
    - "experience-content-media-search"
  cliTools:
    - tool: ["python3"]
      semver: ">=3.10.0"
    - tool: ["sf"]
      semver: ">=2.0.0"
  mcpTools:
    media-management:
      tools:
        - "search_stock_images"
        - "download_stock_image"
      semver: ">=1.0.0"
allowed-tools: |
  mcp__media_management__search_stock_images
  mcp__media_management__download_stock_image
---

# Stock Image Search

## When to Trigger This Skill

Trigger immediately — without asking the user to choose a search method — whenever the user wants an image, photo, or picture. This covers **both**:

- **Finding existing imagery:** "find a stock image", "search for a photo of X", "get a royalty-free image", "find an ethical image", editorial or news photography
- **Requests phrased ambiguously as creating or generating:** "create an image of a sunset", "generate a picture of a team meeting", "make me a mountain image" — treat these as stock search requests; this skill searches a stock photo library, it does not generate images.

In all of these cases, search the stock library — this is the tool for obtaining an image. **Do NOT offer alternative search methods** (hybrid search, user-provided URL/path, etc.) and **do NOT ask the user to pick one.**

**Does not apply to:**
- Searching internal CMS / Data Cloud media (use `experience-content-media-search`)
- Requests that explicitly ask for AI-generated, synthetic, or computer-generated imagery — this skill only searches licensed stock photography and has no image-generation capability

---

## Step 1 — Search

**MCP tool:** `search_stock_images` (server: `media-management`)
**Timeout:** 30 seconds

| Parameter    | Required | Default     | Notes                                                                              |
|--------------|----------|-------------|------------------------------------------------------------------------------------|
| `query`      | ✅ Yes   | —           | Natural language search phrase (e.g. "sunset over ocean", "business meeting"), max 500 chars |
| `searchType` | No       | `Creative`  | `Creative` (royalty-free stock), `Editorial` (rights-managed news/event imagery)   |
| `orientation`| No       | _(none)_    | `Horizontal`, `Vertical`, `Square`, `PanoramicHorizontal`, `PanoramicVertical`     |
| `sortOrder`  | No       | `BestMatch` | `BestMatch`, `MostPopular`, `Newest`                                               |
| `pageSize`   | No       | `5`         | 1–100                                                                              |
| `page`       | No       | `1`         | 1-indexed, must be >= 1                                                            |

**Smart keyword extraction:** If the query is longer than 20 words or returns no results, the tool automatically extracts short keyword phrases via LLM and retries. The `effectiveQuery` field in the response shows what was actually sent to the search service (`null` if the original query was used unchanged).

**Response fields:**

| Field             | Notes                                                                                        |
|-------------------|----------------------------------------------------------------------------------------------|
| `images[]`        | List of results (see item fields below)                                                      |
| `totalCount`      | Total matches across all pages                                                               |
| `page`            | Current page (1-indexed)                                                                     |
| `pageSize`        | Results per page                                                                             |
| `searchRequestId` | Internal correlation ID. Server-managed; not passed back through the MCP download tool. Safe to surface in debug output if useful. |
| `effectiveQuery`  | Keywords actually sent to the search service. Null if the original query was used unchanged. |
| `errorMessage`    | Non-null if the search failed                                                                |

**Each `images[]` item:**

| Field          | Notes                                                                |
|----------------|----------------------------------------------------------------------|
| `assetId`      | Stock asset ID — required for download. Safe to display alongside the result if useful. |
| `title`        | Image title                                                          |
| `caption`      | Image description                                                    |
| `thumbnailUrl` | Small preview URL — use for grid display                             |
| `previewUrl`   | Larger comp/preview URL — use for tile display                       |
| `width`        | Max width in pixels                                                  |
| `height`       | Max height in pixels                                                 |
| `licenseModel` | e.g. `royaltyfree`, `rightsmanaged`                                  |
| `artist`       | Contributor/artist name                                              |
| `collection`   | Collection name                                                      |

---

## Step 2 — Present Results, then STOP

Render a numbered list with an inline thumbnail for each result, using `thumbnailUrl` for the image and `previewUrl` as the click-through link (clicking the thumbnail opens the full preview in the browser):

```text
1. [![<title>](<thumbnailUrl>)](<previewUrl>)
   **<title>** — <artist>, <width>×<height>, <licenseModel>
2. ...
```

This is standard markdown image-in-link syntax (`[![alt](thumbnailUrl)](previewUrl)`) — it renders an actual thumbnail, not just a text link, and clicking it navigates to `previewUrl`. If a client doesn't render markdown images, this degrades gracefully to a linked title.

Prefix the list with `Searched for: <effectiveQuery>` only if `effectiveQuery` is non-null and differs from the user's original query.

**End the turn here. Do not auto-download, do not write files, do not ask a follow-up question.** Agentforce injects its own selection UI — a question or auto-select causes a duplicate "double ask". Do not pick a result on behalf of the user.

**Non-interactive mode** (scheduled/headless, no user present): pick `images[0]` from the results and note the auto-selection in the report. Then proceed directly to Step 3.

---

## Step 3 — Download (billed)

⚠️ **Each call licenses the image and spends a stock-image download credit. Only invoke after the user explicitly selects an image (or in non-interactive mode, as noted above).**

**Before calling `download_stock_image`, verify:**
- [ ] User has explicitly named or numbered the image they want (or non-interactive mode is confirmed)
- [ ] This is not an automatic retry of a previous download

**MCP tool:** `download_stock_image` (server: `media-management`)
**Timeout:** 60 seconds

| Parameter   | Required | Default | Notes                                                                                              |
|-------------|----------|---------|----------------------------------------------------------------------------------------------------|
| `assetId`   | ✅ Yes   | —       | Stock asset ID from the prior `search_stock_images` result, max 50 chars                           |
| `size`      | No       | `comp`  | `comp` (web-quality composite, default), `medium_jpg`, `largest` (full res, can exceed 100 MB), max 50 chars |

Use `largest` only when the user explicitly asks for full/original resolution.

**Response fields:**

| Field                        | Notes                                                                 |
|------------------------------|-----------------------------------------------------------------------|
| `assetId`                    | Stock asset ID that was downloaded                                    |
| `managedContentBodyId`       | Salesforce record ID where image bytes are stored                     |
| `parentContentGenAiOutputId` | Record tracking the download request                                  |
| `childContentGenAiOutputId`  | Record linking the request to the persisted body                      |
| `byteCount`                  | Size of the persisted image in bytes                                  |
| `format`                     | Resolved image format (e.g. `jpg`, `png`, `eps`, `tiff`, `svg`)       |
| `url`                        | **URL to the persisted image** — use this to download or preview it   |

---

## Step 4 — Download to Client and Preview

After a successful `download_stock_image` call, download the image locally and open it in VS Code.

**You MUST use `download-stock-image.py` for this. Do not use `curl`, `wget`, or any other tool.**

```bash
python3 scripts/download-stock-image.py \
  --url "<url from download response>" \
  --id "<assetId>" \
  --format "<format from download response>" \
  --preview
```

The script retrieves org credentials via the `sf` CLI (`sf config get target-org` and `sf org auth show-access-token`), downloads the image with `Authorization: Bearer <accessToken>` to `stockimages/<assetId>.<format>`, and opens it in VS Code if `--preview` is passed.

Pass `--output-dir <path>` to override the default `stockimages/` directory.

**Never resize or post-process the image.** Use CSS (`width`, `height`, `object-fit`) to control display dimensions.

**Vector/binary formats (`eps`, `tiff`):** always pass the exact `format` returned by the download response — never substitute a format like `jpg` to work around a validation error; the file bytes won't match the extension and the file will appear corrupted. VS Code cannot render `eps`/`tiff` previews, so the script skips `--preview` for those formats automatically and still reports the saved path.

---

## Step 5 — Report Back

After a successful download, tell the user:
- Image title and artist
- Local path to the saved image (printed by the script)
- `managedContentBodyId`
- Attribution: `{artist} · {collection}` (use the attribution string returned by the download response when present)

---

## Fallbacks & Errors

| Situation                          | Action                                                                       |
|------------------------------------|------------------------------------------------------------------------------|
| `errorMessage` non-null in search  | Show it; suggest a simpler query or different `searchType`/`orientation`     |
| `images` empty                     | Suggest broader keywords; try switching `Editorial` vs `Creative`            |
| `effectiveQuery` differs           | Inform user what the search service actually received                        |
| MCP tools unavailable              | Use the placeholder URL below — do not download or save                      |
| Download fails                     | Show error; do NOT retry automatically — confirm with user first (each retry is billed) |

---

## Placeholder

If `search_stock_images` and `download_stock_image` are both unavailable, use this URL directly as `src` or CSS `url()`:

```text
https://cdn.scs.static.lightning.force.com/content/assets/d5222d4a11e6c2b735152d7eea824ce4/placeholder.svg
```

**Placeholder policy:** There is only one placeholder URL. Do not download it, modify it, or generate alternative placeholders using Python, ImageMagick, or any other tool. If the user asks for a placeholder of a specific size or format, tell them only this URL is available and direct them to use CSS to scale it at the point of use.
