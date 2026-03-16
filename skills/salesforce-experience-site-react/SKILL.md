---
name: salesforce-experience-site-react
description: Use this skill when users need to create or configure a Salesforce Digital Experience Site that hosts a React web application. Trigger when users mention creating an Experience site for a React app, setting up a React site on Salesforce, configuring Network/CustomSite/DigitalExperience metadata for a web app, or when they need to deploy site infrastructure for a React application. Also trigger when users mention site URL path prefixes, app namespaces, guest access configuration, DigitalExperienceConfig, DigitalExperienceBundle, or sfdc_cms__site content types in the context of React apps. Always use this skill for any React web application site creation or site infrastructure configuration work, even if the user just says "create a site for my React app."
---

# Digital Experience Site for React Web Applications

Create and configure Digital Experience Sites that host React web applications on Salesforce. This skill generates the minimum necessary site infrastructure — Network, CustomSite, DigitalExperienceConfig, DigitalExperienceBundle, and the sfdc_cms__site content type — to stand up a working site.

## Required Properties

Resolve all five properties before generating any metadata. Each has a fallback resolution chain — work through each option in order until a value is found.

| Property | Format | How to Resolve |
|----------|--------|----------------|
| **siteName** | `UpperCamelCase` (e.g., `MyCommunity`) | Ask user or derive from context |
| **siteUrlPathPrefix** | `kebab-case` (e.g., `my-community`) | User-provided, or convert siteName to kebab-case |
| **appNamespace** | String | `namespace` in `sfdx-project.json` → `sf data query -q "SELECT NamespacePrefix FROM Organization" --target-org ${usernameOrAlias}` → default `c` |
| **appDevName** | String | `webApplication` metadata in the project → `sf data query -q "SELECT DeveloperName FROM WebApplication" --target-org ${usernameOrAlias}` → default to siteName |
| **enableGuestAccess** | Boolean | Ask user whether unauthenticated guest users can access site APIs → default `false` |

## Generation Workflow

### Step 1: Resolve All Required Properties

Determine values for all five properties before constructing anything. Use the resolution strategies above, falling through each option until a value is found.

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

The DigitalExperience directory needs both a `_meta.json` and a `content.json` file. The only required content type is `sfdc_cms__site`.

### Step 3: Populate All Metadata Fields

Use the field configurations below. Values in `{braces}` are resolved property references.

#### Network

| Field | Value |
|-------|-------|
| allowInternalUserLogin | false |
| allowMembersToFlag | false |
| changePasswordTemplate | unfiled$public/CommunityChangePasswordEmailTemplate |
| disableReputationRecordConversations | true |
| emailSenderAddress | admin@company.com |
| emailSenderName | {siteName} |
| embeddedLoginEnabled | false |
| enableApexCDNCaching | true |
| enableCustomVFErrorPageOverrides | false |
| enableDirectMessages | true |
| enableExpFriendlyUrlsAsDefault | false |
| enableExperienceBundleBasedSnaOverrideEnabled | true |
| enableGuestChatter | {enableGuestAccess} |
| enableGuestFileAccess | false |
| enableGuestMemberVisibility | false |
| enableImageOptimizationCDN | true |
| enableInvitation | false |
| enableKnowledgeable | false |
| enableLWRExperienceConnectedApp | false |
| enableMemberVisibility | false |
| enableNicknameDisplay | true |
| enablePrivateMessages | false |
| enableReputation | false |
| enableShowAllNetworkSettings | false |
| enableSiteAsContainer | true |
| enableTalkingAboutStats | true |
| enableTopicAssignmentRules | true |
| enableTopicSuggestions | false |
| enableUpDownVote | false |
| forgotPasswordTemplate | unfiled$public/CommunityForgotPasswordEmailTemplate |
| gatherCustomerSentimentData | false |
| headlessForgotPasswordTemplate | unfiled$public/CommunityHeadlessForgotPasswordTemplate |
| headlessRegistrationTemplate | unfiled$public/CommunityHeadlessRegistrationTemplate |
| networkMemberGroups | profile: admin |
| networkPageOverrides | changePasswordPageOverrideSetting: Standard, forgotPasswordPageOverrideSetting: Designer, homePageOverrideSetting: Designer, loginPageOverrideSetting: Designer, selfRegProfilePageOverrideSetting: Designer |
| newSenderAddress | admin@company.com |
| picassoSite | {siteName}1 |
| selfRegistration | false |
| sendWelcomeEmail | true |
| site | {siteName} |
| siteArchiveStatus | NotArchived |
| status | Live |
| tabs | defaultTab: home, standardTab: Chatter |
| urlPathPrefix | {siteUrlPathPrefix}vforcesite |
| welcomeTemplate | unfiled$public/CommunityWelcomeEmailTemplate |

#### CustomSite

| Field | Value |
|-------|-------|
| active | true |
| allowGuestPaymentsApi | false |
| allowHomePage | false |
| allowStandardAnswersPages | false |
| allowStandardIdeasPages | false |
| allowStandardLookups | false |
| allowStandardPortalPages | true |
| allowStandardSearch | false |
| authorizationRequiredPage | CommunitiesLogin |
| bandwidthExceededPage | BandwidthExceeded |
| browserXssProtection | true |
| cachePublicVisualforcePagesInProxyServers | true |
| clickjackProtectionLevel | SameOriginOnly |
| contentSniffingProtection | true |
| enableAuraRequests | true |
| fileNotFoundPage | FileNotFound |
| genericErrorPage | Exception |
| inMaintenancePage | InMaintenance |
| indexPage | CommunitiesLanding |
| masterLabel | {siteName} |
| redirectToCustomDomain | false |
| referrerPolicyOriginWhenCrossOrigin | true |
| selfRegPage | CommunitiesSelfReg |
| siteType | ChatterNetwork |
| urlPathPrefix | {siteUrlPathPrefix}vforcesite |

#### DigitalExperienceConfig

| Field | Value |
|-------|-------|
| label | {siteName} |
| site.urlPathPrefix | {siteUrlPathPrefix} |
| space | site/{siteName}1 |

#### DigitalExperienceBundle

| Field | Value |
|-------|-------|
| label | {siteName}1 |

#### DigitalExperience (sfdc_cms__site)

| Field | Value |
|-------|-------|
| apiName | {siteName}1 |
| type | sfdc_cms__site |
| title | {siteName} |
| urlName | {siteUrlPathPrefix} |
| contentBody.authenticationType | AUTHENTICATED_WITH_PUBLIC_ACCESS_ENABLED |
| contentBody.appContainer | true |
| contentBody.appSpace | {appNamespace}__{appDevName} |

### Step 4: Resolve Additional Configurations

Address any extra configurations the user requests. Use the schemas returned by `get_metadata_api_context` in Step 2 to understand each field's purpose, and update only the minimum necessary fields.

## Verification Checklist

Before deploying, confirm:

- [ ] All five required properties are resolved
- [ ] All metadata directories and files exist per the project structure
- [ ] All metadata fields are populated per the configurations and user requests
- [ ] Deployment validates successfully:

```bash
sf project deploy validate --metadata Network CustomSite DigitalExperienceConfig DigitalExperienceBundle DigitalExperience --target-org ${usernameOrAlias}
```