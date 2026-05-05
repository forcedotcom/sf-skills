---
name: applying-cms-brand
description: "Extracts, retrieves, and applies CMS brand guidelines (voice, tone, style, colors, typography) to generated content. Use this skill ANY TIME a user request involves branding, brand voice, brand tone, brand guidelines, brand identity, brand styling, or applying a brand to content. Triggers for requests like \"apply my brand\", \"use our brand voice\", \"match our brand guidelines\", \"find my brand\", \"search for brand\", \"get brand instructions\", \"apply brand tone\". Handles the full workflow: searching for brands in Salesforce CMS, extracting brand instructions, and applying brand voice/tone/guidelines to generated content. Does not apply to media/image search (use searching-media skill), logo search, or creating new brand definitions."
compatibility: "Requires get_brand_instructions and/or search_brands MCP tools"
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
- Search for images or media (use searching-media skill)
- Create a new brand from scratch
- Edit brand definitions in CMS
- Generate logos or visual brand assets

## Before You Start

**CRITICAL: You must retrieve brand instructions BEFORE generating or modifying any content.**

When a user requests branded content:

1. **Search for available brands** (if brand is not already identified)
2. **Extract brand instructions** for the selected brand
3. **Apply brand guidelines** to all content you generate

**Never generate content first and retrofit branding later.** Brand instructions must inform content generation from the start.

## Workflow Overview

Copy this checklist and track your progress:

```
CMS Branding Progress:
- [ ] Step 1: Determine if brand is already identified or needs search
- [ ] Step 2: Search for brands (if needed) and present options to user
- [ ] Step 3: Extract brand instructions for the selected brand
- [ ] Step 4: Apply brand guidelines to generated content
- [ ] Step 5: Confirm branding was applied correctly
```

## Step 1: Determine Brand Context

Check if the user has already specified which brand to use:

**Brand is known** (user named it, or only one brand exists):
- Skip to Step 3 (Extract Brand Instructions)

**Brand is unknown** (user says "apply my brand" without specifying which):
- Proceed to Step 2 (Search for Brands)

## Step 2: Search for Brands

**Tool:** `search_brands`

**Process:**

1. **Determine search query** — Use the user's description, company name, or a general keyword
2. **Build the request:**

```json
{
  "inputs": [{
    "searchQuery": "keyword or brand name"
  }]
}
```

3. **Call `search_brands`** with the query
4. **Parse the response** — Extract brand results:
   - `managedContentId` — Unique ID (use this for extraction in Step 3)
   - `managedContentKey` — Content key identifier
   - `title` — Brand display name
   - `contentUrl` — URL to the brand content
   - `totalResults` — Number of brands found

### Presenting Brand Results

**If multiple brands found**, use `ask_followup_question` to present options:

```
I found [N] brands in your CMS. Which one should I apply?

1. [Brand Title 1]
2. [Brand Title 2]
3. [Brand Title 3]

Which brand would you like to use?
```

**If one brand found**, confirm with the user:

```
I found the brand "[Brand Title]". Should I apply this brand's guidelines to the content?
```

**If no brands found:**

```
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

## Step 4: Apply Brand Guidelines

After extracting brand instructions, apply them to ALL content you generate:

### Text Content
- Match the specified brand voice and tone
- Use approved terminology and key messages
- Respect content guardrails (forbidden words, topics, claims)
- Follow formatting guidelines (sentence length, paragraph structure)

### UI Components (React/LWC)
- Apply brand colors using CSS custom properties or design tokens
- Use specified typography (font family, sizes, weights)
- Follow spacing and layout guidelines
- Match the visual tone (minimal, bold, playful, etc.)

### Code Generation
- Apply brand colors as variables/tokens at the top of stylesheets
- Use semantic naming that reflects brand terminology
- Include comments referencing which brand guideline drove a decision (only when non-obvious)

### Application Pattern

```
When generating content with branding:

1. Read the brand instructions from Step 3
2. Identify applicable guidelines for the content type
3. Generate content that adheres to ALL applicable guidelines
4. Self-check: Does this content match the brand voice? Tone? Rules?
5. If any guideline is violated, regenerate the affected content
```

## Step 5: Confirm Application

After applying branding:

1. Summarize which brand guidelines were applied
2. Highlight any guidelines that couldn't be applied (and why)
3. Ask the user if the branding feels right

```
I applied the "[Brand Name]" brand guidelines:
- Voice: [description]
- Tone: [description]
- Colors: [applied where]
- [Other guidelines applied]

Does the branding look correct, or would you like adjustments?
```

## Error Handling

| Error | Response |
|---|---|
| `search_brands` unavailable | "Brand search is unavailable. Please provide your brand name or guidelines directly." |
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
