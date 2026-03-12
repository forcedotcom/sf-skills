# Content Type: sfdc_cms__themeLayout

**Use when** user explicitly requests creating a new layout.

## Table of Contents

- I. Core Principles
- II. Directory Structure
- III. _meta.json Structure
- IV. content.json Structure
- V. Naming Conventions
- VI. Theme Sync After Creation
- VII. Generation Checklist

## I. Core Principles

1. **Purpose**: Generate new theme layouts for under the `sfdc_cms__themeLayout` directory.
2. **Naming Convention**: Theme Layout directory names should use camelCase.

## II. Directory Structure

1. **Location**: `digitalExperiences/site/[SITE_NAME]/sfdc_cms__themeLayout/[THEME_LAYOUT_NAME]/`
2. **Required Files**:
  - `_meta.json` - Metadata file defining the API name and type
  - `content.json` - Content file defining the configuration and layout

## III. _meta.json Structure

The `_meta.json` file must contain:

```json
{
  "apiName": "[THEME_LAYOUT_NAME]",
  "type": "sfdc_cms__themeLayout",
  "path": "themeLayouts"
}
```

**Rules**:

- `apiName`: Must match the themeLayout directory name exactly
- `type`: Always `"sfdc_cms__themeLayout"`
- `path`: Always `"themeLayouts"`

## IV. content.json Structure

The `content.json` file must contain:

```json
{
  "type": "sfdc_cms__themeLayout",
  "title": "[DISPLAY_TITLE]",
  "contentBody": {
    "component": {
        "attributes": { },
        "children": [ "[regions in the layout]" ],
        "definition": "[FQN of root layout component]",
        "id": "[root component id]",
        "type": "component"
    }
  },
  "urlName": "[url name]"
}
```

**Field Definitions**:

- `type`: Always `"sfdc_cms__themeLayout"`
- `title`: Human-readable display title, words separated by spaces (e.g. "Scoped Header and Footer")
- `contentBody`: Include all `required` properties from `schemaDefinition`. Use `examplesOfContentType` for reference.

Do not add additional fields.

- `urlName`: URL identifier (lowercase, words separated by dashes e.g., "scoped-header-and-footer")

## V. Naming Conventions

1. **Directory Name**: Should be in camelCase
2. **apiName**: Must exactly match the directory name
3. **title**: Human-readable title with spaces (e.g., "Service Not Available Theme Layout")
4. **urlName**: Lowercase with hyphens for URL-friendly format (e.g., "new-layout")

## VI. Theme Sync After Creation

After creating a new `sfdc_cms__themeLayout`, you MUST update:

```
digitalExperiences/site/[SITE_NAME]/sfdc_cms__theme/[THEME_API_NAME]/content.json
```

**Lookup**: To find the theme content.json for the current site:

1. Navigate up from the current theme layout directory to the site directory.
2. Look in sfdc_cms__theme/ (sibling directory to sfdc_cms__themeLayout/).
3. Find the theme directory (typically one per site).
4. Read the file: content.json.

**Action (append-only)**:

- ALWAYS append a new entry to `contentBody.layouts`.
- Do NOT replace or remove existing `layouts` entries.
- `layoutId` MUST exactly match the new theme layout `apiName`.
- `layoutType` MUST be chosen based on intended view usage.
  - **Default**: Generate a random 30-character alphanumeric string (e.g., `xEGgPxY5j5TForZe3J7SBguOfQicEy`) for the `layoutType`. Ensure this string is unique and does not match any existing `layoutType` in the list.

**Example**:

```json
{
  "contentBody": {
    "layouts": [
      { "layoutId": "existingLayoutA", "layoutType": "Inner" },
      { "layoutId": "existingLayoutB", "layoutType": "ServiceNotAvailable" },
      { "layoutId": "[NEW_THEME_LAYOUT_API_NAME]", "layoutType": "[30_CHAR_RANDOM_STRING]" }
    ]
  }
}
```

## VII. Generation Checklist

When generating a new theme layout, ensure:

- [ ] `_meta.json` created with correct `apiName`, `type`, and `path` (III)
- [ ] `content.json` created with all required fields (IV)
- [ ] `urlName` uses lowercase with hyphens (V)
- [ ] `title` is human-readable (V)
- [ ] `sfdc_cms__theme/[THEME_API_NAME]/content.json` updated by appending a new `contentBody.layouts` mapping (VI)
- [ ] **CRITICAL**: Complete all the UUID generation steps. See `docs/handle-component-and-region-ids.md`
