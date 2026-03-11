---
name: salesforce-experience-lwr-site
description: Creates, modifies, or manages Salesforce Experience Cloud sites (LWR sites) via DigitalExperience metadata. Always trigger when users mention Experience sites, LWR sites, DigitalExperience, Experience Cloud, community sites, portals, creating pages, adding routes, views, theme layouts, branding sets, or any DigitalExperience bundle work. Also use when users mention specific content types like sfdc_cms__route, sfdc_cms__themeLayout, etc. or when troubleshooting site deployment.
---

# Experience LWR Site Builder

Build and configure Salesforce Experience Cloud Lightning Web Runtime (LWR) sites via metadata (DigitalExperienceConfig, DigitalExperienceBundle, Network, CustomSite, CMS contents).

## Table of Contents

- When to Use
- Critical Rules
- General Tips
- Core Site Properties
- Project Structure in DigitalExperienceBundle Format
- Reference Docs
- Common Workflows

## When to Use

- Creating/modifying Experience LWR sites
- Adding pages (routes + views)
- Configuring LWC components, layouts, themes, or branding styles
- Setting up guest user access (public sites)
- Troubleshoot deployment errors related to Experience LWR Sites

**Supported Template**: Build Your Own (LWR) - `talon-template-byo`

- More templates to support in the future.

## Critical Rules

1. Before using any MCP tool, make sure they're actually available. If a tool is missing for the current task, let the user know and pause the current workflow.

## General Tips

1. When available, the site developer name can be found in the CustomSite filename (e.g., `sites/MySite.site-meta.xml` → developer name is `MySite`).

## Core Site Properties

Before doing anything else, note down the following properties from the local project if available as they will be used for various operations. Check with the user if any of the following is missing:

- **Site name**: Required. (e.g., `'My Community'`).
- **URL path prefix**: Optional. Alphanumeric characters only. Convert from site name if not provided (e.g., `'mycommunity'`) and verify with the user for the converted value.
- **Template type devName**: `talon-template-byo`.

## Project Structure in DigitalExperienceBundle Format

### Site Metadata

- DigitalExperienceConfig
  - `digitalExperienceConfigs/{siteName}1.digitalExperienceConfig-meta.xml`
- DigitalExperienceBundle
  - `digitalExperiences/site/{siteName}1/{siteName}1.digitalExperience-meta.xml`
- Network
  - `networks/{siteName}.network-meta.xml`
- CustomSite
  - `sites/{siteName}.site-meta.xml`

### DigitalExperience Contents

- `digitalExperiences/site/{siteName}1/sfdc_cms__*/{contentApiName}/*`
- These are the content components defining routes, views, theme layouts, etc. Each component must have a `_meta.json` and `content.json` file.

#### Content Type Descriptions

| Content Type | Description | When to Use |
|-|-|-|
| `sfdc_cms__site` | Root site configuration containing site-wide settings | Required for every site; one per site |
| `sfdc_cms__appPage` | Application page container that groups routes and views | Required; defines the app shell |
| `sfdc_cms__route` | URL routing definition mapping paths to views | Create one for each page/URL path |
| `sfdc_cms__view` | Page layout and component structure | Create one for each route; defines page content. Also use to edit existing views (e.g., adding/removing components, updating theme layout) |
| `sfdc_cms__brandingSet` | Brand colors, fonts, and styling tokens | Required; defines site-wide styling |
| `sfdc_cms__languageSettings` | Language and localization configuration | Required; defines supported languages |
| `sfdc_cms__mobilePublisherConfig` | Mobile app publishing settings | Required for mobile app deployment |
| `sfdc_cms__theme` | Theme definition referencing layouts and branding | Required; one per site |
| `sfdc_cms__themeLayout` | Page layout templates used by views | Create layouts for different page structures |

**Important:** Creating any new pages require BOTH `sfdc_cms__route` AND `sfdc_cms__view`.

## Knowledge Docs

- `docs/bootstraping-template-byo-lwr.md` - Site creation, template defaults
- `docs/configuring-content-route.md` - Route creation/editing (custom/object pages)
- `docs/configuring-content-view.md` - View creation/editing (custom/object pages)
- `docs/configuring-content-themeLayout.md` - Theme layout creation + theme sync
- `docs/configuring-content-brandingSet.md` - Branding with color patterns/WCAG
- `docs/handling-component-and-region-ids.md` - **UUID generation (CRITICAL)** for component and region ids used in views
- `docs/handling-ui-components.md` - Component discovery, schemas, insertion, configuration

## Common Workflows

See [Knowledge Docs](#knowledge-docs) for detailed capabilities.

### Creating a New Site

See `docs/bootstraping-template-byo-lwr.md` on site creation options and default values of metadata

### CUD Operations on DigitalExperience Contents

- Users can perform create, update, delete operations on DigitalExperience Contents.
- Refer to `docs/configuring-content-*.md` for details on configuring content types.
- **IMPORTANT:** Before ANY modification (create, update, or delete) to content, ALWAYS call `execute_metadata_action` first to get the schema and examples for that content type.
- **Call once per content type per user request**: If you're creating/modifying multiple items of the same content type (e.g., creating 3 routes), you only need to call `execute_metadata_action` ONCE for that content type. Reuse the schema and examples for all items of that type within the same user request.
- For each unique content type you need to work with, call `execute_metadata_action` using the following:

```json
{
  "metadataType": "ExperienceSiteLwr",
  "actionName": "getSiteContentMetadata",
  "parameters": {
    "contentType": "<content type from table above>",
    "shouldIncludeExamples": true
  }
}
```

- Do not call the `execute_metadata_action` MCP tool with any other site actionName unless specified in this knowledge doc.

### Retrieving Site URLs After Deployment

After successfully deploying the site using `sf project deploy`, use the `execute_metadata_action` MCP tool to get the preview and builder URLs:

```json
{
  "metadataType": "ExperienceSiteLwr",
  "actionName": "getSiteUrls",
  "parameters": {
    "siteDevName": "<site developer name>"
  }
}
```

Refer to TIP 1 to get the site developer name.

If the site is not found, an error message will be returned indicating that the site may not be deployed. Ensure the site has been successfully deployed before calling this action.

### Adding and Editing Pages

See both `docs/configuring-content-route.md` and `docs/configuring-content-view.md` for details as a page is composed of a view and a route.

### Adding UI Components to Pages

See `docs/handling-ui-components.md` to add LWCs to LWR sites. Also check `docs/configuring-content-themeLayout.md` if a component is used as a theme layout.

### Creating Theme Layouts

See `docs/configuring-content-themeLayout.md`.

### Configuring Branding

See `docs/configuring-content-brandingSet.md` to configure background colors, foreground colors, button colors, and other branding colors that affect all pages.

### Retrieve Site Metadata Schemas and Documentation

`get_metadata_api_context` MCP tool can be used to retrieve metadata schemas and documentation. For Experience sites, these metadata types are used: DigitalExperienceConfig, DigitalExperienceBundle, Network, CustomSite.

```json
{ "metadataType": "<metadata type>" }
```

### Validation & Deployment

Use `sf` CLI to validate and deploy. Access help docs by attaching `--help`, e.g.:

- `sf project deploy --help`
- `sf project deploy validate --help`

Note that metadata types are space-delimited.

**Validate**:
`sf project deploy validate --metadata DigitalExperienceBundle DigitalExperience DigitalExperienceConfig Network CustomSite --target-org ${usernameOrAlias}`

**Deploy**:
`sf project deploy start --metadata DigitalExperienceBundle DigitalExperience DigitalExperienceConfig Network CustomSite --target-org ${usernameOrAlias}`
