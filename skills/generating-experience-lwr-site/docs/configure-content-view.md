# Content Type: sfdc_cms__view

**Use when** user explicitly requests creating a new page or editing an existing page.

## Table of Contents

- Purpose A: Generate New Views
- Purpose B: Editing Existing Views

## Purpose A: Generate New Views

### Generation Guidelines

**PAGE TYPES**: These guidelines supports two types of pages:

1. **Custom Pages** - Single view pages for custom content (e.g., About Us). **Note**: Standard pages (e.g., Home, Login) come pre-built with the site and cannot be created.
2. **Object Pages** - Requires 3 views: Detail, List, and Related List (e.g., Account, custom objects)

### Core Principles

1. **Route Association**: Views are referenced by routes via the `activeViewId` field.
2. **CRITICAL**: The `viewType` MUST exactly match the `routeType` in the corresponding route.

### Directory Structure (All Views)

1. **Location**: Views must be created under: `digitalExperiences/site/[SITE_NAME]/sfdc_cms__view/[VIEW_NAME]/`
2. **Required Files**:
  - `_meta.json` - Metadata file defining the API name and type
  - `content.json` - Content file defining the configuration and layout
3. **Naming Convention**: Underscore-separated names, no "__c" suffix (About_Us, Account_Detail)

### _meta.json Structure (All Views)

The `_meta.json` file must contain:

```json
{
  "apiName": "[VIEW_NAME]",
  "type": "sfdc_cms__view",
  "path": "views"
}
```

**Rules**:

- `apiName`: Must match directory name exactly. **No "__c" suffix**.
- `type`: Always `"sfdc_cms__view"`
- `path`: Always `"views"`

### Theme Layout Type (All Views)

The `contentBody.themeLayoutType` field specifies which theme layout to use for the view.

- **Default**: `"Inner"` - Use this default if the user does not specify a layout OR if the lookup fails to find a matching layoutType
- **Lookup**: To find valid values:
    1. Navigate up from the current view directory to the site directory
    2. Look in `sfdc_cms__theme/` (sibling directory to `sfdc_cms__view/`)
    3. Find the theme directory (typically one per site)
    4. Check `content.json` → `contentBody.layouts[]` for the layouts array

- **Layout Name/ID Resolution**: If the user provides only a layout name or ID (e.g., "scopedHeaderAndFooter"), you must look up the corresponding `layoutType`:
    1. Find the theme's `content.json` as described above
    2. Locate the `contentBody.layouts` array containing `layoutId`/`layoutType` pairs
    3. Match the user-provided name/ID against `layoutId` values
    4. Use the corresponding `layoutType` value for `contentBody.themeLayoutType`
    5. **Use ONLY the `layoutType` value** for `contentBody.themeLayoutType` - do NOT use the layoutId or user's provided name
    6. **If no match is found, use the default `"Inner"`**

### PART A: CUSTOM PAGES

Use this section when creating single-view custom content pages.

#### A.1. content.json Structure

The `content.json` file must contain:

```json
{
  "type": "sfdc_cms__view",
  "title": "[DISPLAY_TITLE]",
  "contentBody": {},
  "urlName": "[URL_NAME]"
}
```

**Field Definitions**:

- `type`: Always `"sfdc_cms__view"`
- `title`: Human-readable display title (e.g., About Us)
- `contentBody`: Include all `required` properties from `schemaDefinition`. Use `examplesOfContentType` for reference.
- `urlName`: Lowercase with hyphens (e.g., `about-us`)

#### A.2. Component Structure

**MUST** use `community_layout:sldsFlexibleLayout` as the root with exactly 2 regions (`content` and `sfdcHiddenRegion`), even if no components exist:

```
community_layout:sldsFlexibleLayout (root)
├── content (region) — main page content
└── sfdcHiddenRegion (region) — hidden region for SEO and metadata
```

**CRITICAL REQUIREMENTS**:

- **Region names are fixed**: The region `name` field MUST be exactly `content` or `sfdcHiddenRegion`. Do NOT invent custom region names.
- **sfdcHiddenRegion MUST contain seoAssistant**: The `sfdcHiddenRegion` region MUST ALWAYS include a `community_builder:seoAssistant` component in its `children` array.
- **Components live in children**: All components are placed inside the `children` array of a region. Use an empty `children: []` array for `content` if no components exist.

Each region requires: `id` (unique UUID), `name`, `title`, `type: "region"`, `children`. Do not add any other fields.

#### A.3. Naming Conventions Summary

| Field | Format | Example |
|-|-|-|
| Directory/apiName | Underscore-separated, no "__c" | `About_Us` |
| title | Human-readable | `About Us` |
| viewType | `custom-` + lowercase-hyphens | `custom-about-us` |
| urlName | Lowercase-hyphens | `about-us` |

#### A.4. Route Dependency

The route's `activeViewId` must match the view's directory name exactly.

#### A.5. Generation Checklist

- [ ] Directory and `_meta.json` follow structure (see Directory Structure, _meta.json Structure)
- [ ] `content.json` has all required fields (A.1)
- [ ] Component structure correct with both regions (A.1)
- [ ] **CRITICAL**: Complete all the UUID generation steps. see `docs/handle-component-and-region-ids.md`
- [ ] `viewType` matches route's `routeType` (CRITICAL)

### PART B: OBJECT PAGES

Use this section when creating object pages that require Detail, List, and Related List views.

#### B.1. Overview

Object pages require **three views**: Detail, List, and Related List. All share the same object name.

**Object Types & viewType Format**:

| Object Type | Identifier | viewType Example |
|-|-|-|
| Standard (Account, Contact) | `keyPrefix` (3-char) | `detail-001`, `list-001`, `relatedlist-001` |
| Custom (Test_Object__c) | API name with `__c` | `detail-Test_Object__c`, `list-Test_Object__c` |

Obtain object information from the `objectList` MCP output from `sfdc_cms__route`:

```json
[
   ["Label", "ApiName", "KeyPrefix", "IsCustom"]
]
```

#### B.2. Required Views

Create three directories under `sfdc_cms__view/`:

- `[OBJECT_NAME]_Detail/`
- `[OBJECT_NAME]_List/`
- `[OBJECT_NAME]_Related_List/`

#### B.3. content.json Structure

```json
{
  "type": "sfdc_cms__view",
  "title": "[OBJECT_NAME] [TYPE]",
  "contentBody": {
    "component": {},
    "dataProviders": [],
    "themeLayoutType": "[THEME_LAYOUT_TYPE]",
    "viewType": "[PREFIX]-[IDENTIFIER]"
  },
  "urlName": "[OBJECT_NAME_LOWERCASE]-[TYPE]"
}
```

**Field Definitions**:

- `type`: Always `"sfdc_cms__view"`
- `title`: Human-readable (e.g., "Account Detail")
- `contentBody`: Include all `required` properties from `schemaDefinition`. Use `examplesOfContentType` for reference.
- `contentBody.viewType`: **CRITICAL**: Must exactly match route's `routeType`
- `urlName`: Lowercase with hyphens (e.g., `account-detail`)

**Rules**:

- Before any actions, *always* call `execute_metadata_action` to get the full schema and examples per the skill document.

#### B.4. Component Structure

Uses same structure as Part A.1 (Component Structure) with these SEO assistant differences:

- **Detail View**: `pageTitle: "{!Record._Object}: {!Record._Title}"`
- **List/Related List Views**: `recordId: "{!recordId}"` (no pageTitle)

Default template includes one section with one empty column. `seedComponents` must be `[]` (not `null`).

#### B.5. Naming Conventions Summary

| Field | Detail | List | Related List |
|-|-|-|-|
| Directory/apiName | `[Object]_Detail` | `[Object]_List` | `[Object]_Related_List` |
| title | `[Object] Detail` | `[Object] List` | `[Object] Related List` |
| viewType (Standard) | `detail-[keyPrefix]` | `list-[keyPrefix]` | `relatedlist-[keyPrefix]` |
| viewType (Custom) | `detail-[ApiName__c]` | `list-[ApiName__c]` | `relatedlist-[ApiName__c]` |
| urlName | `[object]-detail` | `[object]-list` | `[object]-related-list` |

#### B.6. Route Dependency

The route's `activeViewId` must match the view's directory name exactly. The `viewType` must exactly match the route's `routeType`.

#### B.7. Generation Checklist

- [ ] Object type determined; identifier obtained (`keyPrefix` or API name with `__c`)
- [ ] All three views created: **Detail**, **List**, and **Related List**, each with `_meta.json` and `content.json`
- [ ] `viewType` matches route's `routeType` for all three views (CRITICAL)
- [ ] Component structure correct with both regions (see A.1)
- [ ] SEO assistant configured correctly per view type (B.4)
- [ ] **CRITICAL**: Complete both UUID generation steps. see `docs/handle-component-and-region-ids.md`

## Purpose B: Editing Existing Views

Use this section when modifying existing views under the `sfdc_cms__view` directory.

### Component Modifications

When adding, removing, or configuring components in existing views, **always** refer to [handle-ui-components.md](docs/handle-ui-components.md) for placement hierarchy, component structure, column layout, and property configuration.

### Theme Layout Type

To change a view's theme layout, update `contentBody.themeLayoutType` in the view's `content.json`. See **Theme Layout Type (All Views)** for default and lookup details
