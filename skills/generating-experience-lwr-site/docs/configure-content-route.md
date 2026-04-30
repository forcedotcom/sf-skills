# Content Type: sfdc_cms__route

**Use when** user explicitly requests creating a new page. Not for editing existing routes.

## Table of Contents

- Generation Guidelines
- Core Principles
- Directory Structure (All Routes)
- _meta.json Structure
- Part A: CUSTOM PAGES
- Part B: OBJECT PAGES

## Generation Guidelines

**PAGE TYPES**: These guidelines supports two types of pages:

1. **Custom Pages** - Single route pages for custom content (e.g., About Us). **Note**: Standard pages (e.g., Home, Login) come pre-built with the site and cannot be created.
2. **Object Pages** - Requires 3 routes: Detail, List, and Related List (e.g., Account, custom objects)

## Core Principles

1. **Purpose**: Generate new routes under the `sfdc_cms__route` directory.
2. **View Association**: Each route must reference a corresponding view in the `sfdc_cms__view` directory.
3. **CRITICAL**: The `routeType` in the route's `content.json` MUST exactly match the `viewType` in the corresponding view's `content.json`. This is a required validation rule.

## Directory Structure (All Routes)

1. **Location**: `digitalExperiences/site/[SITE_NAME]/sfdc_cms__route/[ROUTE_NAME]/`
2. **Required Files**:
  - `_meta.json` - Metadata file defining the API name and type
  - `content.json` - Content file defining the configuration and layout
3. **Naming Convention**: Underscore-separated names with "__c" suffix (About_Us__c, Account_Detail__c)

## _meta.json Structure (All Routes)

The `_meta.json` file must contain:

```json
{
  "apiName": "[ROUTE_NAME]",
  "type": "sfdc_cms__route",
  "path": "routes"
}
```

**Rules**:

- `apiName`: Must match the route directory name exactly
- `type`: Always `"sfdc_cms__route"`
- `path`: Always `"routes"`

## Part A: CUSTOM PAGES

Use this section when creating single-route custom content pages.

### A.1. content.json Structure

The `content.json` file must contain:

```json
{
  "type": "sfdc_cms__route",
  "title": "[DISPLAY_TITLE]",
  "contentBody": {},
  "urlName": "[URL_NAME]"
}
```

**Field Definitions**:

- `type`: Always `"sfdc_cms__route"`
- `title`: Human-readable display title (e.g., About Us)
- `contentBody`: Include all `required` properties from `schemaDefinition`. Use `examplesOfContentType` for reference.
- `urlName`: URL identifier (lowercase with hyphens, e.g., `about-us`)

### A.2. Naming Conventions

For a page named "About Us":

| Field | Format | Example |
|-------|--------|--------|
| Directory Name | Underscore-separated + "__c" | `About_Us__c` |
| apiName | Same as directory | `About_Us__c` |
| title | Human-readable | `About Us` |
| contentBody.activeViewId | Underscore-separated (no __c) | `About_Us` |
| contentBody.routeType | "custom-" + lowercase hyphens | `custom-about-us` |
| contentBody.urlPrefix | Lowercase hyphens | `about-us` |
| urlName | Lowercase hyphens | `about-us` |

**CRITICAL**: `routeType` MUST exactly match `viewType` in the corresponding view's `content.json`.

### A.3. View Dependency

- Before creating a route, ensure the corresponding view exists in `sfdc_cms__view/[view_name]/`
- If the view doesn't exist, create it first following the view creation guidelines

### A.4. Generation Checklist

- [ ] Route directory and files created (see Directory Structure)
- [ ] `_meta.json` follows structure (see _meta.json Structure)
- [ ] `content.json` follows structure (see A.1)
- [ ] All naming conventions applied (see A.2)
- [ ] Corresponding view exists (see A.3)

## Part B: OBJECT PAGES

Use this section when creating object pages that require Detail, List, and Related List routes.

### B.1. Overview

Object pages require **three routes** to be created together:

1. **Detail Route** - Displays a single record
2. **List Route** - Displays a list of records
3. **Related List Route** - Displays related records for a parent record

**OBJECT TYPES**: Two types of Salesforce objects use different `routeType` formats:

| Object Type | routeType Format | Example |
|-------------|------------------|----------|
| **Standard** (Account, Contact) | `[type]-[keyPrefix]` | `detail-001`, `list-001`, `relatedlist-001` |
| **Custom** (Test_Object__c) | `[type]-[ObjectApiName]` | `detail-Test_Object__c`, `list-Test_Object__c` |

- **keyPrefix**: 3-character identifier unique to each standard object (Account=001, Contact=003)
- **ObjectApiName**: Custom object API name including the "__c" suffix

Obtain object information from the `objectList` MCP output:

```json
[
  ["Label", "ApiName", "KeyPrefix", "IsCustom"]
]
```

### B.2. Required Routes

Create three directories under `sfdc_cms__route/`:

- `[OBJECT_NAME]_Detail__c/`
- `[OBJECT_NAME]_List__c/`
- `[OBJECT_NAME]_Related_List__c/`

### B.3. content.json Structure

Each route's `content.json` file must contain:

```json
{
  "type": "sfdc_cms__route",
  "title": "[OBJECT_NAME] [TYPE]",
  "contentBody": {},
  "urlName": "[object_name_lowercase]-[type]"
}
```

**Field Definitions**:

- `type`: Always `"sfdc_cms__route"`
- `title`: Human-readable title (Account Detail, Account List)
- `contentBody`: Include all `required` properties from `schemaDefinition`. Use `examplesOfContentType` for reference.
- `contentBody.urlPrefix`: **CRITICAL**: Must be identical across all three object page views (Detail, List, and Related List) for the same object.
- `urlName`: Lowercase with hyphens (account-detail, account-list)

### B.4. Object Page Examples

Use `[ObjectName]` as the object name (Account, Test_Object) and `[IDENTIFIER]` as:

- **Standard objects**: keyPrefix (001 for Account, 003 for Contact)
- **Custom objects**: ObjectApiName (Test_Object__c)

#### content.json Template

```json
{
  "type": "sfdc_cms__route",
  "title": "[ObjectName] [Detail|List|Related List]",
  "contentBody": {
    "activeViewId": "[ObjectName]_[Detail|List|Related_List]",
    "configurationTags": [],
    "pageAccess": "UseParent",
    "routeType": "[detail|list|relatedlist]-[IDENTIFIER]",
    "urlPrefix": "[object-name-lowercase]"
  },
  "urlName": "[object-name-lowercase]-[detail|list|related-list]"
}
```

**Rules**:

- Before any actions, *always* call `execute_metadata_action` to get the full schema and examples per the skill document.

#### routeType Examples

| Route Type | Standard (Account) | Custom (Test_Object__c) |
|------------|-------------------|------------------------|
| Detail | `detail-001` | `detail-Test_Object__c` |
| List | `list-001` | `list-Test_Object__c` |
| Related List | `relatedlist-001` | `relatedlist-Test_Object__c` |

### B.5. Naming Conventions

For an object named "Account":

| Field | Detail | List | Related List |
|-------|--------|------|---------------|
| Directory Name | `Account_Detail__c` | `Account_List__c` | `Account_Related_List__c` |
| apiName | `Account_Detail__c` | `Account_List__c` | `Account_Related_List__c` |
| title | `Account Detail` | `Account List` | `Account Related List` |
| activeViewId | `Account_Detail` | `Account_List` | `Account_Related_List` |
| routeType (Standard) | `detail-[keyPrefix]` | `list-[keyPrefix]` | `relatedlist-[keyPrefix]` |
| routeType (Custom) | `detail-[ObjectApiName]` | `list-[ObjectApiName]` | `relatedlist-[ObjectApiName]` |
| urlPrefix | `account` | `account` | `account` |
| urlName | `account-detail` | `account-list` | `account-related-list` |

**CRITICAL**: `routeType` MUST exactly match `viewType` in the corresponding view's `content.json`.

### B.6. View Dependency

- Before creating routes, ensure corresponding views exist in `sfdc_cms__view/`:
  - `[ObjectName]_Detail/`, `[ObjectName]_List/`, `[ObjectName]_Related_List/`
- `activeViewId` must match the view directory name exactly
- `routeType` must exactly match `viewType` in the corresponding view
- If views don't exist, create them first following the view creation guidelines

### B.7. Generation Checklist

- [ ] Object type determined (Standard or Custom) and identifier obtained (keyPrefix or ObjectApiName)
- [ ] All three routes created: **Detail**, **List**, and **Related List**, each with `_meta.json` and `content.json`
- [ ] All naming conventions applied (see B.5)
- [ ] Corresponding views exist (see B.6)
- [ ] `routeType` matches `viewType` for all three routes
