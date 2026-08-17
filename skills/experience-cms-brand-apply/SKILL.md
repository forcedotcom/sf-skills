---
name: experience-cms-brand-apply
description: "Extracts, retrieves, and applies CMS brand guidelines (voice, tone, style, colors, typography) to generated content. Use this skill ANY TIME a user request involves branding, brand voice, brand tone, brand guidelines, brand identity, brand styling, or applying a brand to content. Triggers for requests like \"apply my brand\", \"use our brand voice\", \"match our brand guidelines\", \"find my brand\", \"search for brand\", \"get brand instructions\", \"apply brand tone\". Handles the full workflow: searching for brands in Salesforce CMS, extracting brand instructions, and applying brand voice/tone/guidelines to generated content. Does not apply to media/image search (use experience-content-media-search skill), logo search, or creating new brand definitions."
metadata:
  version: "1.0"
---

# Applying CMS Brand

Universal skill for searching, extracting, and applying CMS brand guidelines to generated content.

## Scope

**This skill is for APPLYING existing brand guidelines from Salesforce CMS to content you generate.**

**Use this skill when the user wants to:**
- Apply their brand voice/tone to generated content
- Find and use brand guidelines stored in Salesforce CMS
- Search for an existing brand in their org
- Get brand instructions for content generation
- Ensure generated content matches their brand identity
- Apply brand styling, tone, or voice to a page, component, or app

**DO NOT use this skill when the user wants to:**
- Search for images or media (use experience-content-media-search skill)
- Create a new brand from scratch
- Edit brand definitions in CMS
- Generate logos or visual brand assets

## Before You Start

**CRITICAL: You must retrieve brand instructions BEFORE applying any brand.**

When a user requests branded content:

1. **Search for available brands** (if brand is not already identified)
2. **Extract brand instructions** for the selected brand
3. **Apply brand guidelines** to all content you generate

**Never generate content first and retrofit branding later.** Brand instructions must inform content generation from the start.

## Workflow Overview

Copy this checklist and track your progress:

```text
CMS Branding Progress:
- [ ] Step 1: Determine if brand is already identified or needs search
- [ ] Step 2: Search for brands (if needed) and present options to user
- [ ] Step 3: Extract brand instructions for the selected brand
```

## Step 1: Determine Brand Context

Check if the user has already specified which brand to use:

**Brand is known** (user named it, or only one brand exists):
- Skip to Step 3 (Extract Brand Instructions)

**Brand is unknown** (user says "apply my brand" without specifying which):
- Proceed to Step 2 (Search for Brands)

## Step 2: Search for Brands

**Tool:** `search_media_cms_channels`

Brands are stored as CMS content of type `sfdc_cms__brand`. Search for them by
querying the CMS channels with the brand content type.

> **Note:** Brand content search (`contentTypeFqn=sfdc_cms__brand`) is explicitly
> excluded from the `experience-content-media-search` skill's scope. Calling
> `search_media_cms_channels` directly here is correct and intentional — do not
> route brand search through `experience-content-media-search`.

**Process:**

1. **Determine search query** — Use the user's keyword. Brand search matches on
   brand title and description.
2. **Build the request** with the fixed brand-search input contract:

```json
{
  "inputs": [{
    "searchKeyword": "keyword",
    "searchLanguage": "<detected_language>",
    "channelType": "PublicUnauthenticated",
    "contentTypeFqn": "sfdc_cms__brand",
    "pageOffset": 0,
    "searchLimit": 25
  }]
}
```

   Field rules:
   - `searchKeyword` — the user's keyword input
   - `searchLanguage` — auto-detect from the user's input; if unsure, use `en_US`
   - `channelType` — always `PublicUnauthenticated` (brand content is delivered
     via the public CMS channel; authenticated-channel brand search is not
     supported by this tool)
   - `contentTypeFqn` — always `sfdc_cms__brand`
   - `pageOffset` — `0`
   - `searchLimit` — `25`

3. **Call `search_media_cms_channels`** with the request
4. **Parse the response** — A brand result has an ID starting with **`9Ps`**. Extract:
   - `managedContentId` — Unique ID (use this for extraction in Step 3)
   - `managedContentKey` — Content key identifier
   - `title` — Brand display name
   - `contentUrl` — URL to the brand content, found under
     `managedContentChannelDeliveryDetails[0].contentUrl`
   - `pageNumber`, `pageSize`, `totalResults` — pagination summary

### Presenting Brand Results

**If brands found**, first show a summary line, then use `ask_followup_question`
to present options:

```text
Showing [N] of [totalResults] total results (page [pageNumber], page size [pageSize]).

Which brand should I apply?

1. [Brand Title 1]
2. [Brand Title 2]
3. [Brand Title 3]

Which brand would you like to use?
```

When the user replies with their selection, do NOT perform another search —
proceed immediately to Step 3.

**If one brand found**, confirm with the user:

```text
I found the brand "[Brand Title]". Should I apply this brand's guidelines to the content?
```

**If no brands found:**

```text
No brands found in Salesforce CMS. To use branding:
1. Create a brand in Salesforce CMS (Content Type: sfdc_cms__brand)
2. Provide brand guidelines directly in this conversation

Would you like to proceed without CMS branding, or provide guidelines manually?
```

**Never auto-select a brand without confirmation.** Always wait for user choice.

## Step 3: Extract Brand Instructions

**Tool:** `get_brand_instructions`

**Process:**

1. **Call `get_brand_instructions`** — This retrieves the branding extraction prompt template
2. **Parse the response:**
   - `promptBody` — Contains the full brand instruction prompt with extraction and application rules

3. **Follow the instructions in `promptBody`** — The prompt template contains specific guidance on:
   - How to extract brand properties from the brand content
   - Brand voice and tone rules
   - Typography and color guidelines
   - Content formatting rules
   - Guardrails and restrictions

### What Brand Instructions Contain

The extracted brand instructions typically include:

| Property | Description |
|---|---|
| Brand Voice | How the brand speaks (e.g., professional, friendly, authoritative) |
| Brand Tone | Emotional quality of communication (e.g., confident, warm, empathetic) |
| Key Messages | Core messaging pillars and value propositions |
| Content Rules | Dos and don'ts for content generation |
| Style Guidelines | Typography, color, spacing preferences |
| Guardrails | Hard restrictions on language, topics, or claims |

## Error Handling

| Error | Response |
|---|---|
| `search_media_cms_channels` unavailable | "Brand search is unavailable. Please provide your brand name or guidelines directly." |
| `get_brand_instructions` unavailable | "Cannot retrieve brand instructions. Please share your brand guidelines in this conversation and I'll apply them manually." |
| Org lacks Vibes branding | "CMS branding is not enabled for this org. Contact your admin to enable the Agentforce Vibes branding feature." |
| Permission denied | "You don't have permission to access CMS brands. Ensure you have Managed Content Authoring permission." |
| Brand extraction returns empty | "The brand exists but has no configured guidelines. Please add brand properties in CMS or provide guidelines here." |

**Never silently fail.** Always inform the user and offer alternatives.

## Key Principles

1. **Brand first, content second** — Always extract brand instructions before generating content
2. **Never assume brand guidelines** — Only apply what was explicitly retrieved from CMS
3. **Respect guardrails absolutely** — Brand content rules are hard constraints, not suggestions
4. **Confirm brand selection** — Never auto-select a brand without user confirmation
5. **Show your work** — Tell the user which guidelines you applied and how
6. **Graceful degradation** — If tools are unavailable, ask for manual guidelines rather than proceeding without branding
