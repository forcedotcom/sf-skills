---
name: searching-media
description: "Searches for and retrieves existing visual media (images, logos, icons, photos, graphics, banners, thumbnails, hero images, backgrounds) from sources such as Salesforce CMS, Data 360 or any other source. Use this skill ANY TIME a user request involves finding, searching, getting, fetching, retrieving, grab, looking up, locating media. NEVER call search_media_cms_channels, search_electronic_media tools directly — always go through this skill first. This skill must be activated before any tool is used for media search or retrieval, without exception.  Takes PRIORITY and activates FIRST when ANY media search/retrieval is mentioned, regardless of what else happens with the media afterward. Triggers for requests like \"search for logo\", \"find hero image\", \"get company logo\", \"locate icons\", \"fetch background image\", \"retrieve product photos\". Handles the search and source selection workflow. Does not apply when the request is about brand search, to generate NEW images with AI, or edit existing images."
compatibility: "Requires search_media_cms_channels and/or search_electronic_media MCP tools"
metadata:
  version: "1.0"
---

# Media Search

Universal routing skill for searching and retrieving existing images and media.

## Scope

**This skill is for SEARCHING FOR existing media, not CREATING new media.**

**Use this skill when the user wants to:**
- Search for images in Salesforce CMS, Data Cloud
- Find existing visual assets to use in their app
- Retrieve media from connected sources
- Browse available images for their project
- Locate specific photos or graphics

**DO NOT use this skill when the user wants to:**
- Generate new images with AI (use image generation tools)
- Create graphics or designs from scratch
- Edit or modify existing images
- Build custom visuals or diagrams

## Before You Search

**CRITICAL: This is a routing skill, not a direct search skill.**

When a user requests to find an image:

**Your first action MUST use the ask_followup_question tool to present search sources.**

1. **Use ask_followup_question** to present available search sources as options
2. **Receive the user's selection** from the tool response
3. **Then** call the appropriate search tool based on their choice


**Example of what NOT to do:**
- ❌ Calling ANY tool before the user picks a source (MCP tools, file reads, descriptor checks, etc.)
- ❌ "Checking which MCP tools are available" — do not probe or discover tools via tool calls
- ❌ Immediately calling `search_electronic_media` or `search_media_cms_channels`
- ❌ Reading MCP tool descriptors or schemas to see what's available
- ❌ Deciding which search source to use without asking

**Example of what TO do:**
- ✅ Respond with ONLY text — a numbered list of search sources
- ✅ Ask: "Which option would you like to use?"
- ✅ Wait for user to reply with their choice
- ✅ Then (and only then) call the tool they selected

**Your first response when this skill triggers MUST be a text-only message presenting search sources. No tool calls. No exceptions.**


## Workflow Overview

**The user MUST choose the search source. You CANNOT skip this step.**

Copy this checklist and track your progress:

```
Media Search Progress:
- [ ] Step 1: Check your own tool list for available search tools (no tool calls — just inspect what's in your context)
- [ ] Step 2: Present only the available options to the user as a numbered list (plain text, no tool calls)
- [ ] Step 3: Wait for the user to reply with their selection
- [ ] Step 4: Execute the selected search method (this is the first tool call)
- [ ] Step 5: Present all results to user for selection
- [ ] Step 6: Apply selected image to code
```

If you call any tool before step 4, you are not following this skill correctly.

## Presenting Search Sources (First Response)

**DO NOT call any tool, read any MCP descriptor, or make any external request to determine available tools.**

Your tools are already loaded into your context. Look at the tool names you already have access to — this is introspection, not a tool call.

**Step 1: Check your own tool list (no tool calls)**

Look at the tools already in your context and check for these names:
- `search_media_cms_channels` → If present, include **"Search using keywords"**
- `search_electronic_media` → If present, include **"Search using Data 360 hybrid search"**
- Always include **"Other"** as the last option

**Step 2: Build your response**

Include ONLY the sources whose tools you actually have. Number them sequentially.

```
I can help you find that image. Where would you like to search?

[NUMBER]. [SEARCH SOURCE NAME] — [Brief description]
...
[NUMBER]. Other — Provide your own URL or path

Which option would you like to use?
```

**Step 3: Stop and wait**

After presenting the list, STOP. Do not call any tool. Do not proceed. Wait for the user to reply with their choice.

### Examples

**Both tools available:**
```
I can help you find that image. Where would you like to search?

1. Search using Data 360 hybrid search — Semantic search across Salesforce CMS and connected DAMs
2. Search using keywords — Search Salesforce CMS by keywords and taxonomies
3. Other — Provide your own URL or path

Which option would you like to use?
```

**Only `search_media_cms_channels` available:**
```
I can help you find that image. Where would you like to search?

1. Search using keywords — Search Salesforce CMS by keywords and taxonomies
2. Other — Provide your own URL or path

Which option would you like to use?
```

**Only `search_electronic_media` available:**
```
I can help you find that image. Where would you like to search?

1. Search using Data 360 hybrid search — Semantic search across Salesforce CMS and connected DAMs
2. Other — Provide your own URL or path

Which option would you like to use?
```

**Neither tool available:**
```
No automated media search sources are currently configured. Please provide a direct URL or asset library path.
```

**Wait for the user to select** before proceeding.

## Executing the Selected Search Method

**⚠️ ONLY reach this step if the user has explicitly selected an option from your numbered list.**

If you haven't shown options yet, go back to the "Presenting Search Sources" section first.

After the user selects an option, execute the corresponding search method below.

### Search using keywords

**Tool:** `search_media_cms_channels`

**Process:**

1. **Analyze the query** — Understand what the user is searching for (subject, attributes, domain)

2. **Extract keywords** — Concrete nouns that would appear in image metadata
   - Use domain-specific synonyms
   - Maximum 10 terms
   - Examples:
     - "luxury apartments" → apartment, villa, penthouse, residence, condo
     - "company logo" → logo, emblem, corporate logo
     - "bright room" → _(empty if no concrete nouns)_

3. **Extract taxonomies** — Descriptive qualities, styles, moods, categories
   - Only adjectives and attributes
   - Examples:
     - "luxury apartment with river view" → Luxury, Premium, Waterfront, Riverside, Panoramic
     - "bright spacious room" → Bright, Spacious, Open, Airy, Light
     - "car" → _(empty if no descriptive terms)_

4. **Determine locale** — Use format `en_US`, `es_MX`, `fr_FR` (default: `en_US`)

5. **Build the JSON payload** — Construct this exact structure:

```json
{
  "inputs": [{
    "searchKeyword": "keyword1 OR keyword2 OR keyword3",
    "taxonomyExpression": "{\"OR\": [\"Taxonomy1\", \"Taxonomy2\"]}",
    "searchLanguage": "en_US",
    "channelIds": "",
    "channelType": "PublicUnauthenticated",
    "contentTypeFqn": "sfdc_cms__image",
    "pageOffset": 0,
    "searchLimit": 5
  }]
}
```

**Field rules:**
- `searchKeyword`: Join keywords with ` OR ` (space-OR-space). Use empty string if no keywords.
- `taxonomyExpression`: Stringify JSON object `{"OR": ["term1", "term2"]}`. Use `"{}"` if no taxonomies.
- `searchLanguage`: Locale with underscore (e.g., `en_US`)
- `channelIds`: Always empty string
- `channelType`: Always `"PublicUnauthenticated"`
- `contentTypeFqn`: Always `"sfdc_cms__image"`
- `pageOffset`: Start at `0`, increment by `searchLimit` for pagination
- `searchLimit`: Default `5`, adjust if user requests more

**Examples:**

Query: "luxury apartment with river view"
```json
{
  "inputs": [{
    "searchKeyword": "apartment OR villa OR penthouse OR residence",
    "taxonomyExpression": "{\"OR\": [\"Luxury\", \"Premium\", \"Waterfront\", \"Riverside\"]}",
    "searchLanguage": "en_US",
    "channelIds": "",
    "channelType": "PublicUnauthenticated",
    "contentTypeFqn": "sfdc_cms__image",
    "pageOffset": 0,
    "searchLimit": 5
  }]
}
```

Query: "bright spacious room" (no concrete nouns)
```json
{
  "inputs": [{
    "searchKeyword": "",
    "taxonomyExpression": "{\"OR\": [\"Bright\", \"Spacious\", \"Open\", \"Airy\"]}",
    "searchLanguage": "en_US",
    "channelIds": "",
    "channelType": "PublicUnauthenticated",
    "contentTypeFqn": "sfdc_cms__image",
    "pageOffset": 0,
    "searchLimit": 5
  }]
}
```

Query: "car images" (no descriptive terms)
```json
{
  "inputs": [{
    "searchKeyword": "car OR automobile OR vehicle OR auto",
    "taxonomyExpression": "{}",
    "searchLanguage": "en_US",
    "channelIds": "",
    "channelType": "PublicUnauthenticated",
    "contentTypeFqn": "sfdc_cms__image",
    "pageOffset": 0,
    "searchLimit": 5
  }]
}
```

6. **Call the tool** with the exact JSON payload

### Search using Data 360 hybrid search

**Tool:** `search_electronic_media`

**Process:**

1. Use the user's query **as-is** — no keyword extraction or transformation needed
2. Call `search_electronic_media`
3. Pass the query to the tool's `searchQuery` parameter

**Example:**
- User query: "modern luxury apartment with natural lighting"
- Tool call: `search_electronic_media(searchQuery="modern luxury apartment with natural lighting")`

### Other (User-Provided URL)

Ask the user to provide:
- Direct URL to the image
- Asset library path
- Specific system/location to check

## Presenting Search Results

**Your action MUST use the `ask_followup_question` tool to present search results as options.**
1. **Parse the tool response** — Extract all image results (title and source)
2. **Use `ask_followup_question`** to present ALL results as selectable options. Show the image title only — do not display the URL.
3. **Receive the user's selection** from the tool response
4. **Then** apply the selected image

```
I found 4 images. Which one would you like to use?

1. Luxury Apartment Exterior
   Source: Salesforce CMS

2. Modern High-Rise Building
   Source: Salesforce CMS

3. Waterfront Residence
   Source: Salesforce CMS

4. Premium Condominium
   Source: Salesforce CMS
```

**Never auto-select an image.** Always wait for user choice.

## Applying the Selected Image


After the user chooses:

1. Confirm the selection with image name and URL
2. Use the complete URL returned by the tool, including all query parameters. CMS and DAM URLs rely on query parameters for authentication, resizing, and CDN routing — dropping them breaks the image. For example, a URL like `https://cms.example.com/media/img.jpg?oid=00D&refid=0EM&v=2` must be used in full.
3. Apply the URL to the user's code/component
4. Show what was changed (file path and line number)

## Error Handling

| Error | Response |
|---|---|
| Tool unavailable | "The [source name] tool is unavailable. Would you like to try a different source?" |
| Tool returns error | Show error message, offer retry with different terms or alternative source |
| No results found | "No results found. Try broader keywords, removing descriptive terms, or a different source." |
| Invalid user selection | Re-display options and ask again |

**Never silently fail.** Always inform the user and offer alternatives.

## Search Behavior Notes

**Search using keywords:**
- Both keyword and taxonomy → results match keyword OR (keyword + taxonomy)
- Empty keyword → search by taxonomy only
- Empty taxonomy → search by keyword only
- Use `pageOffset` for pagination (increment by `searchLimit`)

**Search using Data 360 hybrid search:**
- Handles natural language queries
- Semantic similarity matching
- Searches across multiple connected systems

## Key Principles

1. **First response is always text-only** — Present search sources without calling any tool
2. **Only show configured sources** — Check your own tool list (introspection, not tool calls) and only present sources whose tools you have
3. **Wait for user selection** — Never auto-select a source or image
4. **Show all results** — Let the user choose the best match
5. **Confirm before applying** — Verify the selection before modifying code
6. **Handle errors gracefully** — Provide clear feedback and alternatives
