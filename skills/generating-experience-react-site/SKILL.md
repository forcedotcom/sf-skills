---
name: generating-experience-react-site
description: Use this skill when users need to create or configure a Salesforce Digital Experience Site specifically for hosting a React web application. Trigger when users mention creating an Experience site for a React app, setting up a React site on Salesforce, configuring Network/CustomSite/DigitalExperience metadata for a web app, or deploying site infrastructure for a React application. Also trigger when users mention site URL path prefixes, app namespaces, appDevName, guest access configuration, DigitalExperienceConfig, DigitalExperienceBundle, or sfdc_cms__site content types in the context of React apps. Always use this skill for any React web application site creation or site infrastructure configuration work, even if the user just says "create a site for my React app" or "set up the site for my web application."
---

# Digital Experience Site for React Web Applications
Create and configure Digital Experience Sites that host React web applications on Salesforce. This skill generates the minimum necessary site infrastructure — Network, CustomSite, DigitalExperienceConfig, DigitalExperienceBundle, and the `sfdc_cms__site` content type — so a React app can be served from Salesforce.

React sites differ from standard LWR sites: they don't need routes, views, theme layouts, or branding sets. The site acts as a thin container (`appContainer: true`) that delegates rendering to the React application referenced by `appSpace`.

## Required Properties
Resolve all five properties before generating any metadata. Each has a fallback chain — work through each option in order until a value is found.

| Property | Format | How to Resolve |
|----------|--------|----------------|
| **siteName** | `UpperCamelCase` (e.g., `MyCommunity`) | Ask user or derive from context |
| **siteUrlPathPrefix** | `kebab-case` (e.g., `my-community`) | User-provided, or convert siteName to kebab-case |
| **appNamespace** | String | `namespace` in `sfdx-project.json` → `sf data query -q "SELECT NamespacePrefix FROM Organization" --target-org ${usernameOrAlias}` → default `c` |
| **appDevName** | String | `webApplication` metadata in the project → `sf data query -q "SELECT DeveloperName FROM WebApplication" --target-org ${usernameOrAlias}` → default to siteName |
| **enableGuestAccess** | Boolean | Ask user whether unauthenticated guest users can access site APIs → default `false` |

The `appNamespace` and `appDevName` properties connect the site to the correct React application. Getting these wrong means the site deploys but shows a blank page, so take care to resolve them from real project data.

## Generation Workflow
### Step 1: Resolve All Required Properties
Determine values for all five properties before constructing anything. Use the resolution strategies in the table above, falling through each option until a value is found.

### Step 2: Create the Project Structure
Call the `get_metadata_api_context` MCP tool to retrieve schemas for `Network`, `CustomSite`, `DigitalExperienceConfig`, and `DigitalExperienceBundle` metadata types. These schemas define the valid XML structure for each file.

Create any files and directories that don't already exist, using these paths:

| Metadata Type | Path |
|--------------|------|
| Network | `networks/{siteName}.network-meta.xml` |
| CustomSite | `sites/{siteName}.site-meta.xml` |
| DigitalExperienceConfig | `digitalExperienceConfigs/{siteName}1.digitalExperienceConfig-meta.xml` |
| DigitalExperienceBundle | `digitalExperiences/site/{siteName}1/{siteName}1.digitalExperience-meta.xml` |
| DigitalExperience (sfdc_cms__site) | `digitalExperiences/site/{siteName}1/sfdc_cms__site/{siteName}1/*` |

The DigitalExperience directory contains only `_meta.json` and `content.json`. Do not create any directories other than `sfdc_cms__site` inside the bundle.

### Step 3: Populate All Metadata Fields
Use the default templates in the docs below. Values in `{braces}` are resolved property references — substitute them with the actual values from Step 1.

| Metadata Type | Template Reference |
|--------------|-------------------|
| Network | [configure-metadata-network.md](docs/configure-metadata-network.md) |
| CustomSite | [configure-metadata-custom-site.md](docs/configure-metadata-custom-site.md) |
| DigitalExperienceConfig | [configure-metadata-digital-experience-config.md](docs/configure-metadata-digital-experience-config.md) |
| DigitalExperienceBundle | [configure-metadata-digital-experience-bundle.md](docs/configure-metadata-digital-experience-bundle.md) |
| DigitalExperience (sfdc_cms__site) | [configure-metadata-digital-experience.md](docs/configure-metadata-digital-experience.md) |

### Step 4: Resolve Additional Configurations
Address any extra configurations the user requests. Use the schemas returned by `get_metadata_api_context` in Step 2 to understand each field's purpose, and update only the minimum necessary fields.

## Verification Checklist
Before deploying, confirm:

- [ ] All five required properties are resolved
- [ ] All metadata directories and files exist per the project structure
- [ ] All metadata fields are populated per the templates and user requests
- [ ] `appSpace` in `content.json` matches an existing `WebApplication` metadata record
- [ ] Deployment validates successfully:
```bash
sf project deploy validate --metadata Network CustomSite DigitalExperienceConfig DigitalExperienceBundle DigitalExperience --target-org ${usernameOrAlias}
```
