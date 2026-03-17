# Content Type: sfdc_cms__brandingSet

**Use when** user explicitly requests creating/updating branding set.

## Table of Contents

- Core Principles
- Generation Guidelines
- Branding Property Patterns

## Core Principles

1. **Purpose**: Manage site-wide branding properties (colors, fonts, etc.).
2. **Site Association**: Branding sets are linked to the site configuration.

## Generation Guidelines

### 1. Directory Structure

1. **Location**: `digitalExperiences/site/[SITE_NAME]/sfdc_cms__brandingSet/[BRANDING_SET_NAME]/`
2. **Required Files**:
  - `_meta.json` - Metadata file defining the API name and type
  - `content.json` - Content file defining the configuration and layout
3. **Naming Convention**: Underscore-separated names (e.g., `Branding_Set`).

### 2. _meta.json Structure

The `_meta.json` file must contain:

```json
{
  "apiName": "[BRANDING_SET_NAME]",
  "type": "sfdc_cms__brandingSet",
  "path": "brandingSets"
}
```

**Rules**:

- `apiName`: Must match the directory name exactly (e.g., `Branding_Set`)

### 3. content.json Structure

The `content.json` file must contain:

```json
{
  "type": "sfdc_cms__brandingSet",
  "title": "[DISPLAY_TITLE]",
  "contentBody": {},
  "urlName": "[URL_NAME]"
}
```

**Field Definitions**:

- `type`: **Required**. Represents the content type. The only supported value is `"sfdc_cms__brandingSet"`.
- `title`: **Required**. Human-readable display title (e.g., Branding Set).
  - Maximum length is **100 characters**.
  - Must be **unique** within the space's brandingSet content items.
- `contentBody`: Include all `required` properties from `schemaDefinition`. Use `examplesOfContentType` for reference.
  - `brandingSetType`: Represents whether the color palette is for the entire site or a specific section.
    - `APP`: The branding set applies to the entire site. There can be only one branding set of this type.
    - `SCOPED`: A `SCOPED` branding set can be applied only to a section component for granular overrides.
  - `definitionName`: **Required**. Represents the name for the branding set used in the site or template’s theme.
    - **Build Your Own (LWR)**: uses `talon-template-byo:branding`
    - **Microsite**: uses `microsite-template-marketing:branding`
  - `values`: **Required**. Represents a map (object) of branding values (colors, fonts, etc.) that can be applied to a site.
    - **Format**: An object containing key-value pairs that represent branding-set values.
    - **Patterns**: See the "Branding Property Patterns" section for details on value relationships.
- `urlName`: Lowercase with hyphens (e.g., `branding-set`)

**Rules**:

- Before any actions, *always* call `execute_metadata_action` to get the full schema and examples per the skill document.

### 4. Naming Conventions Summary

| Field | Format | Example |
|-------|--------|--------|
| Directory/apiName | Underscore-separated | `Branding_Set` |
| title | Human-readable | `Branding Set` |
| urlName | Lowercase-hyphens | `build-your-own-lwr` |

### 5. Generation Checklist

- [ ] Directory and `_meta.json` follow naming conventions (1, 2)
- [ ] `content.json` has all required fields (3)
- [ ] `contentBody` follows the schema provided by `execute_metadata_action`

## Branding Property Patterns

When generating or validating `contentBody.values`, follow these established patterns for consistency:

### 1. Color Scaling Patterns (The "Rule of 3")

Salesforce uses a numeric suffix system (`Color`, `Color1`, `Color2`, `Color3`) to create a tonal palette.

- **Darkening Trend**: As the suffix number increases, the color becomes progressively darker.
  - Example: `BackgroundColor` (#ffffff) → `_BackgroundColor1` (#ebebeb) → `_BackgroundColor2` (#c2c2c2) → `_BackgroundColor3` (#858585).
- **Contrast/Foreground Colors**: Every base color has a corresponding `ForegroundColor` to ensure accessibility.
  - **WCAG Compliance**: Ensure a color contrast ratio of at least **4.5:1** between the background and foreground colors for standard text.
  - Dark base colors usually have white (#ffffff) foregrounds.
  - Light base colors (like `_NeutralColor`) usually have black (#000000) foregrounds.

### 2. Font Size Hierarchy

- **Base vs. Small**: The `Small` variant is typically **75%** of the base size.
  - Example: `BodyFontSize` (1rem) → `BodySmallFontSize` (0.75rem).
- **Heading Scale**: Headings follow a standard typographic scale:
  - `HeadingExtraLarge`: 2.5rem
  - `HeadingLarge`: 1.75rem (~70% of XL)
  - `HeadingMedium`: 1.25rem (~50% of XL)
  - `HeadingSmall`: 1.125rem

### 3. Design Token Mapping

Prefer using **DXP Design Tokens** over hardcoded values where possible:

- **Fonts**: Use `var(--dxp-s-html-font-family)` for base, body, and button fonts.
- **Brand Alignment**: Use `var(--dxp-g-brand)` for primary brand colors and links.

### 4. Component Consistency

- **Buttons**: Maintain consistent `BorderRadius` (e.g., 4px) across all button sizes (Small, Medium, Large).
- **Form Elements**: `FormElementLabelFontSize` and `FormElementTextFontSize` should match.

### 5. Spacing and Ratios

- **Device Ratios**: Desktop spacing (padding/spacers) is typically **1.33x** larger than mobile spacing.
  - Example: `ColumnSpacerSizeDesktop` (1rem) vs `ColumnSpacerSizeMobile` (0.75rem).
