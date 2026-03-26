---
name: searching-media
description: You MUST Use this skill ANY TIME the user's request involves finding, searching, getting, fetching, retrieving, grabbing, looking up, or locating existing visual media (images, logos, icons, photos, graphics, banners, thumbnails, hero images, backgrounds) from any source. This skill takes PRIORITY and should be used FIRST when ANY media search/retrieval is mentioned, regardless of what else the user wants to do with the media afterward. Trigger for requests like "search for logo", "find hero image", "get company logo", "locate icons", "fetch background image", "retrieve product photos". This skill handles the search and source selection workflow. Only skip if the user wants to generate NEW images with AI, design custom graphics from scratch, or edit existing images.
metadata:
  author: afv-library
  version: "1.0"
---

# Media Search

Universal routing skill for searching and retrieving existing images and media.

## Before You Search

**CRITICAL: This is a routing skill, not a direct search skill.**

When a user requests to find an image:

**DO NOT call any search tool directly.** You MUST follow this sequence:

1. **First response MUST include:** A list of numbered search source options for the user
2. **Wait for user to reply** with their selected option number
3. **Only then** call the appropriate search tool

**Example of what NOT to do:**
- ❌ Immediately calling `search_electronic_media` or `search_media_cms_channels`
- ❌ Deciding which search source to use without asking
- ❌ Saying "I'll search for you" and then calling a tool

**Example of what TO do:**
- ✅ Show numbered list: "1. Search using Data 360 hybrid search, 2. Search using keywords, 3. Other"
- ✅ Ask: "Which option would you like to use?"
- ✅ Wait for user to reply with their choice
- ✅ Then call the tool they selected

**Your first response when this skill triggers MUST present options and ask the user to choose. No exceptions.**

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

## Workflow Overview

**The user MUST choose the search source. You CANNOT skip this step.**

1. Identify which search sources (MCP tools) are available
2. **Present ALL available options** to the user as a numbered list
3. **Wait for user to reply** with their selection
4. Execute the selected search method
5. Return results for the user to choose from

If you skip steps 2-3 and call a search tool directly, you are not following this skill correctly.

## Discovering Available Search Sources

**Step 1: Check your available MCP tools**

Look at your environment and identify which of these tools you have:
- Do you have `search_media_cms_channels`? → If YES, include "Search using keywords"
- Do you have `search_electronic_media`? → If YES, include "Search using Data 360 hybrid search"
- Always include "Other" as the last option

**Step 2: Build your response**

Your first response must follow this structure exactly:

```
I'll help you find that image. Here are your search options:

[NUMBER]. [SEARCH SOURCE NAME] — [Brief description]
[NUMBER]. [SEARCH SOURCE NAME] — [Brief description]
[NUMBER]. Other — Provide your own URL or path

Which option would you like to use?
```

**Step 3: Stop and wait**

After presenting options, STOP. Do not proceed until the user replies with their choice.

### Example First Response

```
I'll help you find that image. Let me check which search sources are available.

Available search sources:
1. Search using Data 360 hybrid search — Semantic search across Salesforce CMS and connected DAMs
2. Search using keywords — Search Salesforce CMS by keywords and taxonomies
3. Other — Provide your own URL or path

Which option would you like to use?
```

If no automated search tools are available:
```
No automated media sources are currently configured. Please provide a direct URL or asset library path.
```

**Example (all sources available):**
```
I can help you find that image. Where would you like to search?

1. **Search using Data 360 hybrid search** — Semantic search across Salesforce CMS and connected DAMs
2. **Search using keywords** — Search Salesforce CMS by keywords and taxonomies
3. **Other** — Provide your own URL or path
```

**Example (only keyword search available):**
```
I can help you find that image. Where would you like to search?

1. **Search using keywords** — Search Salesforce CMS by keywords and taxonomies
2. **Other** — Provide your own URL or path
```

**Example (no automated sources):**
```
No automated media sources are currently configured. Please provide:
1. **Direct URL or asset library path**
```

**Wait for the user to select** before proceeding.

## Executing the Selected Search Method

**⚠️ ONLY reach this step if the user has explicitly selected an option from your numbered list.**

If you haven't shown options yet, go back to the "Discovering Available Search Sources" section first.

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
     - "company logo" → logo, brand, emblem, corporate logo
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
- ``: Always `"sfdc_cms__image"`
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
    "": "sfdc_cms__image",
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
    "": "sfdc_cms__image",
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
    "": "sfdc_cms__image",
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
3. Pass the query to the tool's search parameter (check the tool's schema for the exact parameter name - likely `query` or `search_query`)

**Example:**
- User query: "modern luxury apartment with natural lighting"
- Tool call: `search_electronic_media(query="modern luxury apartment with natural lighting")`
  (Note: Check the tool's schema - parameter might be `query` or `search_query`)

### Other (User-Provided URL)

Ask the user to provide:
- Direct URL to the image
- Asset library path
- Specific system/location to check

## Presenting Search Results

Parse the tool response and present **ALL** results as numbered options:

```
I found 4 images. Which one would you like to use?

1. **Luxury Apartment Exterior**
   URL: https://cms.example.com/media/luxury-apt-01.jpg
   Source: Salesforce CMS

2. **Modern High-Rise Building**
   URL: https://cms.example.com/media/highrise-02.jpg
   Source: Salesforce CMS

3. **Waterfront Residence**
   URL: https://cms.example.com/media/waterfront-03.jpg
   Source: Salesforce CMS

4. **Premium Condominium**
   URL: https://cms.example.com/media/condo-04.jpg
   Source: Salesforce CMS
```

**Never auto-select an image.** Always wait for user choice.

## Applying the Selected Image

After the user chooses:

1. **Confirm** the selection with image name and URL
2. **Apply** the URL to the user's code/component
3. **Show** what was changed (file path and line number)
4. **Offer** next steps:
   - Add alt text for accessibility
   - Adjust styling or dimensions
   - Find additional images
   - Optimize image loading

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

1. **Always discover sources first** — Never assume a tool exists
2. **Present only available options** — Don't show unavailable sources
3. **Wait for user selection** — Never auto-select a source or image
4. **Show all results** — Let the user choose the best match
5. **Confirm before applying** — Verify the selection before modifying code
6. **Handle errors gracefully** — Provide clear feedback and alternatives
