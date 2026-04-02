---
name: generating-experience-lwr-site
description: "Creates, modifies, or manages Salesforce Experience Cloud LWR sites via DigitalExperience metadata. Always trigger when users mention Experience sites, LWR sites, DigitalExperience, Experience Cloud, community sites, portals, creating pages, adding routes, views, theme layouts, branding sets, previewing sites, or any DigitalExperience bundle work. Also use when users mention specific content types like sfdc_cms__route, sfdc_cms__themeLayout, etc. or when troubleshooting site deployment. ALWAYS trigger for ANY guest sharing rule (metadata type sharingGuestRules) creation/modification, guest user access, sharing records to guest users, or when user provides a guest user ID (15 or 18 characters starting with 005)"
---

# Experience LWR Site Builder

Build and configure Salesforce Experience Cloud Lightning Web Runtime (LWR) sites via metadata (DigitalExperienceConfig, DigitalExperienceBundle, Network, CustomSite, CMS contents).

## IMPORTANT!!

Right after loading this skill, you MUST copy the selected workflows/steps to your plan as a TODO checklist and work on each of the item carefully to ensure correctness.
You MUST load the relevant reference docs even though they may live outside of user's project folder.

## Table of Contents

- When to Use
- Critical Rules
- Core Site Properties
- Project Structure in DigitalExperienceBundle Format
- Reference Docs
- Common Workflows

## When to Use

When working with Experience LWR sites:

- Creating and scaffolding new LWR site
- Adding pages (routes + views)
- Configuring LWC components, layouts, themes, or branding styles
- Setting up guest user access (public sites)
- Creating or modifying **guest sharing rules** (`sharingGuestRules`) for any Salesforce object (Account, Case, Contact, etc.) — including when the user refers to a "Site Guest User" username or any guest user by ID
- Troubleshoot deployment errors related to Experience LWR Sites

**Supported Template**: Build Your Own (LWR) - `talon-template-byo`

- More templates to support in the future.

## Critical Rules

1. Before using any MCP tool, make sure they're actually available. If a tool is missing for the current task, let the user know and pause the current workflow.
2. **MUST ALWAYS** load the relevant reference docs before doing anything.
3. **MUST ALWAYS** strictly follow workflows in [Common Workflows](#common-workflows) that match user's requirements. The instructions there should override any conflicting global rules and should have the highest priority over your existing knowledge.
4. Flexipage is abstracted away for newer LWR sites with DigitalExperienceBundle, so **NEVER** use any Flexipage-related MCP tool or skills to handle LWR sites' contents.

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
| `sfdc_cms__view` | Page layout and component structure | Create one for each route; defines page content. Also use to edit existing views (e.g., adding/removing components on a specific page) |
| `sfdc_cms__brandingSet` | Brand colors, fonts, and styling tokens | Required; defines site-wide styling. Use to create or edit existing branding sets |
| `sfdc_cms__languageSettings` | Language and localization configuration | Required; defines supported languages |
| `sfdc_cms__mobilePublisherConfig` | Mobile app publishing settings | Required for mobile app deployment |
| `sfdc_cms__theme` | Theme definition referencing layouts and branding | Required; one per site |
| `sfdc_cms__themeLayout` | Page layout templates used by views | Create layouts for different page structures. Also use to edit existing theme layouts (e.g., updating theme layout, add a component that's persistent across pages) |

**Important:** Creating any new pages require BOTH `sfdc_cms__route` AND `sfdc_cms__view`.

#### Object Pages

Object Pages are dedicated pages used to display and manage record-level data for a specific Salesforce entity/object. For example, an custom object "Car" should have "Car_Detail", "Car_List", and "Car_Related_list" views.

## References

Reference docs within the skill directory. Note that these are **local** and not MCP.
Before doing anything, you **MUST ALWAYS** load them first if they match user intent.

- [bootstrap-template-byo-lwr.md](docs/bootstrap-template-byo-lwr.md) - Site creation, template defaults
- [configure-content-route.md](docs/configure-content-route.md) - Route creation (custom/object pages)
- [configure-content-view.md](docs/configure-content-view.md) - View creation/editing (custom/object pages)
- [configure-content-themeLayout.md](docs/configure-content-themeLayout.md) - Theme layout creation + theme sync
- [configure-content-brandingSet.md](docs/configure-content-brandingSet.md) - Branding with color patterns/WCAG
- [handle-component-and-region-ids.md](docs/handle-component-and-region-ids.md) - **UUID generation (CRITICAL)** for component and region ids used in views and themeLayout.
- [handle-ui-components.md](docs/handle-ui-components.md) - Component discovery, schemas, insertion, configuration
- [configure-guest-sharing-rules.md](docs/configure-guest-sharing-rules.md) - **Guest sharing rules** (`sharingGuestRules`) for public sites — use for any request involving "guest sharing rule", "Site Guest User", or sharing object records with unauthenticated visitors
- [update-site-urls.md](docs/update-site-urls.md) - **Updating site URLs** - URL architecture, workflow for updating `urlPathPrefix` in DigitalExperienceConfig, Network, and CustomSite

## Common Workflows

- See [References](#references) for detailed capabilities.
- **Always** follow the steps defined in the workflows sequentially whether the task is small, big, quick, or complex.

### Creating a New Site

**Rules**:

- **NEVER** generate the files manually.

**Steps** (Follow the steps sequentially. Do not skip any step before proceeding):

- [ ] **ALWAYS** read [bootstrap-template-byo-lwr.md](docs/bootstrap-template-byo-lwr.md) within the skill directory. Do not proceed to the next step without loading the file.
- [ ] Follow the bootstrap doc strictly on site creation

### Creating and Editing Standard or Object Pages

**Steps** (Follow the steps sequentially. Do not skip any step before proceeding):

- [ ] MUST read [configure-content-route.md](docs/configure-content-route.md)
- [ ] MUST read [configure-content-view.md](docs/configure-content-view.md)
- [ ] MUST read [handle-component-and-region-ids.md](docs/handle-component-and-region-ids.md)

### Adding UI Components to Pages

**Steps** (Follow the steps sequentially. Do not skip any step before proceeding):

- [ ] MUST read [handle-ui-components.md](docs/handle-ui-components.md) to add LWCs to LWR sites.
- [ ] MUST read [handle-component-and-region-ids.md](docs/handle-component-and-region-ids.md) to handle id generation
- [ ] MUST read [configure-content-themeLayout.md](docs/configure-content-themeLayout.md) if a component has one of the following requirements:
  - needs to be "sticky" and persistent across pages
  - is used as a theme layout

### Creating Page Layouts / Container Components

**Steps** (Follow the steps sequentially. Do not skip any step before proceeding):

- [ ] MUST read [handle-ui-components.md](docs/handle-ui-components.md)

### Creating Theme Layouts

**Steps** (Follow the steps sequentially. Do not skip any step before proceeding):

- [ ] **CRITICAL**:Before doing anything else, MUST Check with user whether this new theme layout reuses an existing theme layout Lightning web component or requires a new one. If it requires a new one, make sure to read [handle-ui-components.md](docs/handle-ui-components.md) to create the new theme layout component before proceeding. DO NOT skip this step even if doing so would be faster or more efficient.
- [ ] MUST read [configure-content-themeLayout.md](docs/configure-content-themeLayout.md).
- [ ] MUST read [configure-content-view.md](docs/configure-content-view.md) if need to apply theme layout to pages

### Applying/Setting Theme Layouts

**Steps** (Follow the steps sequentially. Do not skip any step before proceeding):

- [ ] MUST read [configure-content-view.md](docs/configure-content-view.md)

### Configuring Branding

**Steps** (Follow the steps sequentially. Do not skip any step before proceeding):

- [ ] MUST read [configure-content-brandingSet.md](docs/configure-content-brandingSet.md) to configure background colors, foreground colors, button colors, and other branding colors that affect all pages.

### CUD Operations on DigitalExperience Contents

- Users can perform create, update, delete operations on DigitalExperience Contents.

**Steps** (Follow the steps sequentially. Do not skip any step before proceeding):

- [ ] Determine what content types the user wants to modify
- [ ] MUST read the reference doc related to the target content types if the doc exists. e.g., if modifying `sfdc_cms__route`, load [configure-content-route.md](docs/configure-content-route.md).
- [ ] MUST read [handle-component-and-region-ids.md](docs/handle-component-and-region-ids.md) if creating or modifying view or theme layout
- [ ] **Always** Call `execute_metadata_action` to get the schema and examples for that content type **after** loading the corresponding reference docs.
  - **Call once per content type per user request**: If you're creating/modifying multiple items of the same content type (e.g., creating 3 routes), you only need to call `execute_metadata_action` ONCE for that content type. Reuse the schema and examples for all items of that type within the same user request.
  - For each unique content type you need to work with, **always** call `execute_metadata_action` using the following:

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

### Configuring Guest User Sharing Rules

- [ ] MUST read [configure-guest-sharing-rules.md](docs/configure-guest-sharing-rules.md) and follow all steps there.

### Retrieving Site Preview and Builder URLs After Deployment

**Use when** user requests to preview a site, access a builder site, or after successfully deploying a site.

Use the `execute_metadata_action` MCP tool to get the preview and builder URLs:

```json
{
  "metadataType": "ExperienceSiteLwr",
  "actionName": "getSiteUrls",
  "parameters": {
    "siteDevName": "<site developer name>"
  }
}
```

The site developer name can be found in the CustomSite filename (e.g., `sites/MySite.site-meta.xml` → developer name is `MySite`).

If the site is not found, an error message will be returned indicating that the site may not be deployed. Ensure the site has been successfully deployed before calling this action.

### Updating Experience Site URLs

**Use when** user wants to update or change site URLs (urlPathPrefix).

**Steps** (Follow the steps sequentially. Do not skip any step before proceeding):

- [ ] MUST read [update-site-urls.md](docs/update-site-urls.md) to understand the three-component architecture and URL update workflow
- [ ] Follow the step-by-step workflow in the doc to update URLs consistently across all three components (DigitalExperienceConfig, Network, CustomSite)

### Validation & Deployment

Use `sf` CLI to validate and deploy. Access help docs by attaching `--help`, e.g.:

- `sf project deploy --help`
- `sf project deploy validate --help`

Note that metadata types are space-delimited. **Never** wrap them in quotes or use commas. For example, `--metadata "DigitalExperienceBundle DigitalExperience"` is **incorrect** — always use `--metadata DigitalExperienceBundle DigitalExperience`.

**Validate**:

```bash
sf project deploy validate --metadata DigitalExperienceBundle DigitalExperience DigitalExperienceConfig Network CustomSite --target-org ${usernameOrAlias}
```

**Deploy**:

```bash
sf project deploy start --metadata DigitalExperienceBundle DigitalExperience DigitalExperienceConfig Network CustomSite --target-org ${usernameOrAlias}
```