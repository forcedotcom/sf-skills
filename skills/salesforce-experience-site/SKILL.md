---
name: salesforce-experience-site
description: Use this skill when users need to create, modify, or manage Salesforce Experience Cloud sites (LWR sites). Trigger when users mention Experience sites, LWR sites, DigitalExperience, Experience Cloud, community sites, portals, creating pages, adding routes, views, theme layouts, branding sets, or any DigitalExperience bundle work. Also use when users mention specific content types like sfdc_cms__route, sfdc_cms__view, sfdc_cms__themeLayout, or when troubleshooting site deployment. Always use this skill for any Experience Cloud or LWR site work.
---

## When to Use This Skill

Use this skill when you need to:
- Create Experience Cloud sites or communities
- Build LWR (Lightning Web Runtime) sites
- Set up site configuration and settings
- Generate Experience Site metadata
- Troubleshoot deployment errors related to Experience Sites

## Specification

# Experience LWR Site Metadata Specification
An LWR site can be represented by metadata DigitalExperienceConfig, DigitalExperienceBundle, Network, CustomSite, and CMS contents. Your purpose is to assist developers in creating and editing these metadata.

## Supported Template Types

Template name - Template DevName
- Build Your Own (LWR) - talon-template-byo

## Core Properties

Before doing anything else, identify the following properties from the local project if available. Check with the user if any of the following is missing:
- Site name: Required. (e.g., `'My Community'`).
- URL path prefix: Optional. Alphanumeric characters only. Convert from site name if not provided (e.g., `'mycommunity'`) and verify with the user for the converted value.
- Template type devName: Optional. Defaults to `talon-template-byo`.

## General Tips

TIP 1. When available, the site developer name can be found in the CustomSite filename (e.g., `sites/MySite.site-meta.xml` → developer name is `MySite`).

## Project Structure in DigitalExperienceBundle Format

### Site Metadata
- DigitalExperienceConfig
    - Path: `digitalExperienceConfigs/{siteName}1.digitalExperienceConfig-meta.xml`
- DigitalExperienceBundle
    - Path: `digitalExperiences/site/{siteName}1/{siteName}1.digitalExperience-meta.xml`
- Network
    - Path: `networks/{siteName}.network-meta.xml`
- CustomSite
    - Path: `sites/{siteName}.site-meta.xml`

### DigitalExperience Contents
- Path: `digitalExperiences/site/{siteName}1/sfdc_cms__*/{contentApiName}/*`
- Description: These are the content components defining routes, views, theme layouts, etc. Each component must have a `_meta.json` and `content.json` file.

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

## CUD Operations on DigitalExperience Contents
- Users can perform create, update, delete operations on DigitalExperience Contents.
- **IMPORTANT:** Before ANY modification (create, update, or delete) to content, ALWAYS call `execute_metadata_action` first to get the schema, examples, and instructions for that content type.
- **Call once per content type per user request**: If you're creating/modifying multiple items of the same content type (e.g., creating 3 routes), you only need to call `execute_metadata_action` ONCE for that content type. Reuse the schema and examples for all items of that type within the same user request.
- For each unique content type you need to work with, call `execute_metadata_action` using the following:
```json
{
  "metadataType": "ExperienceSite",
  "actionName": "getSiteContentMetadata",
  "parameters": {
    "contentType": "<content type from table above>",
    "shouldIncludeExamples": true
  }
}
```
- Do not call the `execute_metadata_action` MCP tool with any other site actionName unless specified in this knowledge doc/instructions.

## Retrieving Site URLs After Deployment

After successfully deploying the site using `sf project deploy`, use the `execute_metadata_action` MCP tool to get the preview and builder URLs:
```json
{
  "metadataType": "ExperienceSite",
  "actionName": "getSiteUrls",
  "parameters": {
    "siteDevName": "<site developer name>"
  }
}
```

Refer to TIP 1 to get the site developer name.

If the site is not found, an error message will be returned indicating that the site may not be deployed. Ensure the site has been successfully deployed before calling this action.

## Enhancement Rules

- If need to understand how site metadata should be configured, use the `get_metadata_api_context` MCP tool to get the schemas.

- Use MCP tool `execute_metadata_action` with `getSiteTemplateMetadata` to get the knowledge document about the template and its default configurations if needed. **IMPORTANT:** This MUST be used for new site:
```json
{
  "metadataType": "ExperienceSite",
  "actionName": "getSiteTemplateMetadata",
  "parameters": {
    "templateDevName": "<template DevName, e.g. talon-template-byo>"
  }
}
```

- To validate Experience Site metadata, run CLI command `sf project deploy validate --metadata DigitalExperienceBundle DigitalExperience DigitalExperienceConfig Network CustomSite --target-org ${usernameOrAlias}`

## Guest User Sharing Rules (Public Sites Only)

**When to use**: Only create guest sharing rules when the user explicitly wants to make the site **public** (accessible to unauthenticated visitors). If the site is private/login-required, guest sharing rules are not needed.
If sharingRules metadata is not available locally in force-app/main/default/sharingRules, retrieve it from the org before creating new rules.

To get the full SharingRules schema, use the `get_metadata_api_context` MCP tool:
```json
{
  "metadataType": "SharingRules"
}
```

### XML Example

```xml
<?xml version="1.0" encoding="UTF-8"?>
<SharingRules xmlns="http://soap.sforce.com/2006/04/metadata">
    <sharingGuestRules>
        <fullName>ShareAccountsWithSiteGuest</fullName>
        <accessLevel>Read</accessLevel>
        <includeHVUOwnedRecords>false</includeHVUOwnedRecords>
        <label>Share Accounts With Site Guest</label>
        <sharedTo>
            <guestUser>[site developer name]</guestUser>
        </sharedTo>
        <criteriaItems>
            <field>Name</field>
            <operation>notEqual</operation>
            <value>null</value>
      </criteriaItems>
    </sharingGuestRules>
</SharingRules>
```
Refer to TIP 1 to get the site developer name.

### Critical Requirements

1. **SharedTo Element**: Must use `<guestUser>{siteName}</guestUser>` where `{siteName}` is the Network name (not URL path prefix).
2. **includeHVUOwnedRecords**: Required field. Set to `false` unless records owned by high-volume site users should be included.
3. **One XML file per object**: Put all rules for a given object in one file. Do not create additional.

### Common Mistakes

- Using `<role>` or `<group>` instead of `<guestUser>` in sharedTo
- Omitting the required `includeHVUOwnedRecords` field
- Using `includeRecordsOwnedByAll` (that's for `sharingCriteriaRules`, not guest rules)

## Workflows

### Creating a new site

- Verify with user on the value of site name, url path prefix, and site template type.
- Retrieve template information from `getSiteTemplateMetadata` and strictly follow the rules of its knowledge document.
- Proceed to the workflow of editing an existing site.

### Editing an existing site

- Identify the intent of the user and break it down into steps.
- Make use of `get_metadata_api_context` if user wants to edit site metadata.
- Use `getSiteContentMetadata` to understand how to edit site contents.
- Once the tasks are done, perform site metadata validation.
