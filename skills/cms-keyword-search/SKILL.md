---
name: cms-keyword-search
description: Search Salesforce CMS for images by keywords and taxonomies via the search_media_cms_channels MCP tool. Delegated from cms-media-search when the user selects CMS Image Search. Analyzes the user query, extracts keywords and taxonomies, builds the search payload using the exact template and format rules defined in this skill, calls the tool, and presents results for user selection. Do NOT invoke this skill directly for initial image requests — it is always reached through cms-media-search.
license: Apache-2.0
metadata:
  author: afv-library
  version: "6.0"
---

# CMS Keyword Search

Search Salesforce CMS for images using keywords and taxonomies. **Delegated from `cms-media-search`** when the user selects "CMS Image Search".

## Execution Flow

Follow these steps **in order**. Do NOT call `search_media_cms_channels` until Step 5.

1. Analyze the user's query and ng expand with domain-specific terms
2. Extract keywords (concrete nouns)
3. Extract taxonomies (descriptive attributes)
4. Determine locale
5. Build the payload using the **Payload Template**
6. Call `search_media_cms_channels` with the payload
7. Present results and wait for user selection

---

## Step 1: Analyze and Expand the Query

Understand the user's intent and expand with domain knowledge:

- **Main subject** — what are they searching for? (apartments, cars, logos)
- **Attributes** — how should it look? (luxury, modern, spacious)
- **Domain** — what context? (real estate, automotive, corporate)

Expand with synonyms and domain-specific terms:

| Domain | Query term | Expansion |
|---|---|---|
| Real Estate | "luxury apartments" | villa, penthouse, residence, condo, duplex |
| Automotive | "cars" | automobile, vehicle, auto, SUV |
| Corporate | "company logo" | logo, brand, corporate logo, branding |
| Home/Interior | "modern kitchen" | kitchen, contemporary kitchen, kitchen interior |

## Step 2: Extract Keywords

Keywords are **concrete, searchable nouns** that would appear in image titles or metadata.

Rules:
- Only nouns and noun phrases — no verbs, adjectives, or stop words
- Include domain-specific synonyms from Step 1
- Maximum 10 terms
- If the query has no concrete nouns (e.g. "something bright"), use **empty string**

| Query | Keywords |
|---|---|
| "luxury apartments" | apartment, villa, penthouse, residence, condo |
| "company logo" | logo, brand, corporate logo, branding |
| "modern kitchen" | kitchen, contemporary kitchen |
| "bright spacious room" | _(empty — no concrete nouns)_ |
| "car images" | car, automobile, vehicle, auto |

## Step 3: Extract Taxonomies

Taxonomies are **descriptive qualities, styles, moods, or categories** — how the image should look or feel, or what category it belongs to.

Rules:
- Only adjectives, attributes, and categorical terms
- Include domain-relevant descriptors from Step 1
- If the query has no descriptive terms (e.g. "car"), use **empty string**

| Query | Taxonomies |
|---|---|
| "luxury apartment with river view" | Luxury, Premium, Waterfront, Riverside, Panoramic, Real Estate |
| "company logo" | Corporate, Business, Professional, Branding |
| "bright spacious room" | Bright, Spacious, Open, Airy, Light |
| "car" | _(empty — no descriptive terms)_ |

**Never mix**: descriptive terms like "modern", "luxury", "warm" go in taxonomies, NOT keywords. Exception: compound domain terms like "Luxury Apartments" can appear in keywords.

## Step 4: Determine Locale

Use **locale format with underscore** (e.g. `en_US`, `es_MX`, `fr_FR`). Default: `en_US`.

Priority:
1. Explicit language/region in query → use that locale
2. Query in non-English → infer locale with region
3. Context clues from conversation → include region
4. Default: `en_US`

---

## Step 5: Build the Payload

Construct the JSON payload for `search_media_cms_channels` using the template below. Follow every format rule exactly.

### Payload Template

```json
{
  "inputs": [{
    "searchKeyword": "<KEYWORDS>",
    "taxonomyExpression": "<TAXONOMY>",
    "searchLanguage": "<LOCALE>",
    "channelIds": "",
    "channelType": "PublicUnauthenticated",
    "contentTypeFqns": "sfdc_cms__image",
    "pageOffset": 0,
    "pageLimit": 5
  }]
}
```

### Critical: Single Input Object Only

The `inputs` array must contain **exactly ONE object**. All keywords go into a single `searchKeyword` field, OR-separated. Do NOT create multiple input objects.

```
✅  "inputs": [{ "searchKeyword": "logo OR brand OR emblem OR branding", ... }]
❌  "inputs": [{ "searchKeyword": "logo", ... }, { "searchKeyword": "brand", ... }]
```

### Format Rules

#### `searchKeyword` — Join keywords with ` OR ` (uppercase, space-padded)

```
✅  "logo OR brand OR emblem OR branding OR corporate logo"
✅  "car OR automobile OR vehicle OR auto"
✅  ""                                              ← no keywords
❌  "logo, brand, emblem"                           ← comma-separated
❌  "logo brand emblem"                             ← space-separated
❌  "logo or brand"                                 ← lowercase "or"
```

#### `taxonomyExpression` — Stringified JSON object, NOT a raw object or plain string

Build the object `{"OR": ["term1", "term2"]}`, then **convert it to a string**. The value must be a **string**, not an object.

```
✅  "{\"OR\": [\"Corporate\", \"Business\", \"Professional\", \"Branding\"]}"
✅  "{\"OR\": [\"Luxury\", \"Premium\", \"High-end\"]}"
✅  "{\"OR\": [\"Bright\"]}"                              ← single term
✅  "{}"                                                  ← no taxonomies
❌  {"OR": ["Corporate", "Business"]}                     ← raw object
❌  "Corporate OR Business OR Professional"               ← OR-separated
❌  "Corporate, Business, Professional"                   ← CSV
```

#### `searchLanguage` — Locale with underscore, never language-only

```
✅  "en_US"    "fr_CA"    "es_MX"    "ja_JP"    "de_DE"
❌  "en"       "fr"       "es"       "ja"       "de"
```

#### Hardcoded fields — never change these values

| Field | Value | Notes |
|---|---|---|
| `channelIds` | `""` | Always empty string |
| `channelType` | `"PublicUnauthenticated"` | Exact capitalization required |
| `contentTypeFqns` | `"sfdc_cms__image"` | Double underscore, all lowercase |
| `pageOffset` | `0` | Default start position |
| `pageLimit` | `5` | Default; user can request more |

---

### Worked Examples

**Query: "Look for logo and apply it to the header"**

- Keywords: logo, brand, emblem, branding, corporate logo
- Taxonomies: Corporate, Business, Professional, Branding
- Locale: en_US

```json
{
  "inputs": [{
    "searchKeyword": "logo OR brand OR emblem OR branding OR corporate logo",
    "taxonomyExpression": "{\"OR\": [\"Corporate\", \"Business\", \"Professional\", \"Branding\"]}",
    "searchLanguage": "en_US",
    "channelIds": "",
    "channelType": "PublicUnauthenticated",
    "contentTypeFqns": "sfdc_cms__image",
    "pageOffset": 0,
    "pageLimit": 5
  }]
}
```

**Query: "Find luxury car images"**

- Keywords: car, automobile, vehicle, auto
- Taxonomies: Luxury, Premium, High-end
- Locale: en_US

```json
{
  "inputs": [{
    "searchKeyword": "car OR automobile OR vehicle OR auto",
    "taxonomyExpression": "{\"OR\": [\"Luxury\", \"Premium\", \"High-end\"]}",
    "searchLanguage": "en_US",
    "channelIds": "",
    "channelType": "PublicUnauthenticated",
    "contentTypeFqns": "sfdc_cms__image",
    "pageOffset": 0,
    "pageLimit": 5
  }]
}
```

**Query: "Something bright and spacious" (no concrete nouns)**

- Keywords: _(empty)_
- Taxonomies: Bright, Spacious, Open, Airy, Light
- Locale: en_US

```json
{
  "inputs": [{
    "searchKeyword": "",
    "taxonomyExpression": "{\"OR\": [\"Bright\", \"Spacious\", \"Open\", \"Airy\", \"Light\"]}",
    "searchLanguage": "en_US",
    "channelIds": "",
    "channelType": "PublicUnauthenticated",
    "contentTypeFqns": "sfdc_cms__image",
    "pageOffset": 0,
    "pageLimit": 5
  }]
}
```

**Query: "Car images" (no descriptive terms)**

- Keywords: car, automobile, vehicle, auto
- Taxonomies: _(empty)_
- Locale: en_US

```json
{
  "inputs": [{
    "searchKeyword": "car OR automobile OR vehicle OR auto",
    "taxonomyExpression": "{}",
    "searchLanguage": "en_US",
    "channelIds": "",
    "channelType": "PublicUnauthenticated",
    "contentTypeFqns": "sfdc_cms__image",
    "pageOffset": 0,
    "pageLimit": 5
  }]
}
```

**Query: "Luxury apartment with river view"**

- Keywords: apartment, villa, penthouse, residence, condo, suite
- Taxonomies: Waterfront, Riverside, Panoramic, Luxury, Premium, Real Estate
- Locale: en_US

```json
{
  "inputs": [{
    "searchKeyword": "apartment OR villa OR penthouse OR residence OR condo OR suite",
    "taxonomyExpression": "{\"OR\": [\"Waterfront\", \"Riverside\", \"Panoramic\", \"Luxury\", \"Premium\", \"Real Estate\"]}",
    "searchLanguage": "en_US",
    "channelIds": "",
    "channelType": "PublicUnauthenticated",
    "contentTypeFqns": "sfdc_cms__image",
    "pageOffset": 0,
    "pageLimit": 5
  }]
}
```

**Query: "Cherche des images de voiture de luxe" (French)**

- Keywords: voiture, automobile, véhicule
- Taxonomies: Luxe, Premium, Haut de gamme
- Locale: fr_FR

```json
{
  "inputs": [{
    "searchKeyword": "voiture OR automobile OR véhicule",
    "taxonomyExpression": "{\"OR\": [\"Luxe\", \"Premium\", \"Haut de gamme\"]}",
    "searchLanguage": "fr_FR",
    "channelIds": "",
    "channelType": "PublicUnauthenticated",
    "contentTypeFqns": "sfdc_cms__image",
    "pageOffset": 0,
    "pageLimit": 5
  }]
}
```

---

## Step 6: Call the MCP Tool

Call `search_media_cms_channels` with the exact JSON payload from Step 5.

## Step 7: Present Results

Parse the response and present **all** results as numbered options. For each result, show:
- Image title or name (`title` or `name` field)
- Media URL (`mediaUrl` or from `deliveryInfo.urls`)

**Never auto-select an image.** Always wait for the user to choose.

Example:

```
I found 3 images in Salesforce CMS. Which one would you like to use?

1. **Stainless Steel Kitchen Utensils**
   URL: https://cms.example.com/media/kitchen-utensils.jpg

2. **Modern Cookware Set**
   URL: https://cms.example.com/media/modern-cookware.jpg

3. **Professional Kitchen Tools**
   URL: https://cms.example.com/media/professional-tools.jpg
```

### After User Selection

1. Confirm the selection with image name and URL
2. Apply the URL to the user's code or component
3. Show what was changed (file and line)
4. Offer next steps (alt text, styling, more images)

---

## Search Behavior

- When both keyword and taxonomy are provided: results match keyword OR (keyword + taxonomy)
- Empty keyword → search by taxonomy only
- Empty taxonomy → search by keyword only
- Default `pageLimit` is 5; user can request more
- Use `pageOffset` for pagination (increment by `pageLimit`)

## Error Handling

| Error | Response |
|---|---|
| `search_media_cms_channels` unavailable | Inform user; offer Data Cloud, Unsplash, or Other via `cms-media-search` |
| Tool returns an error | Show error message; offer retry with different terms or alternative source |
| No results found | Suggest broader keywords, removing taxonomies, or trying Data Cloud/Unsplash |
| Invalid user selection | Re-display the options and ask again |
