# Build Your Own (LWR) Template

**Use when** creating a new site or retrieving default values for site metadata.

## Table of Contents

- Bootstrap Options
- Default Values Reference

## Bootstrap Options

**IMPORTANT**: First site setup initializes services. Warn user - recommend Option 1 for first site.

Ask user to choose:

1. Create in org, then download metadata
2. Scaffold locally before deploying

### Option 1: Create in Org

```bash
sf community create --name "{siteName}" --template-name 'Build Your Own (LWR)' --url-path-prefix "{prefix}"
```

After creation, retrieve metadata using sf CLI.

### Option 2: Scaffold Locally

```bash
sf template generate digital-experience site --name "{siteName}" --template-name 'Build Your Own (LWR)' --url-path-prefix "{prefix}"
```

Generates metadata with defaults: DigitalExperienceConfig, DigitalExperiences, Network, CustomSite, and content (route, view, themeLayout, etc.).

#### Post-Creation Config

After site metadata is generated, use MCP tool `execute_metadata_action` to fetch additional information about the template:

```json
{
  "metadataType": "ExperienceSiteLwr",
  "actionName": "getSiteTemplateMetadata",
  "parameters": { "templateDevName": "talon-template-byo" }
}
```

If result provides `disabledViews`, delete both view and route directories.

**Example**: If `disabledViews` includes "tooManyRequests":

- Delete: `digitalExperiences/site/{siteDevName}/sfdc_cms__view/tooManyRequests/`
- Delete: `digitalExperiences/site/{siteDevName}/sfdc_cms__route/Too_Many_Requests/`

---

## Default Values Reference

**Note**: CLI generates these. Listed for reference only - use CLI first.

### Metadata Defaults

**DigitalExperienceConfig**:

```yaml
label: {siteName}
urlPathPrefix: {siteUrlPathPrefix}
space: site/{siteName}1
```

**DigitalExperienceBundle**:

```yaml
label: {siteName}1
modules: [sfdc_cms__collection, sfdc_cms__mobilePublisherConfig]
```

**Network**:

```yaml
allowInternalUserLogin: false
allowMembersToFlag: false
changePasswordTemplate: unfiled$public/CommunityChangePasswordEmailTemplate
disableReputationRecordConversations: true
emailSenderAddress: {adminEmailAddress}
emailSenderName: {siteName}
embeddedLoginEnabled: false
enableApexCDNCaching: true
enableCustomVFErrorPageOverrides: false
enableDirectMessages: true
enableExpFriendlyUrlsAsDefault: false
enableExperienceBundleBasedSnaOverrideEnabled: true
enableGuestChatter: false
enableGuestFileAccess: false
enableGuestMemberVisibility: false
enableImageOptimizationCDN: true
enableInvitation: false
enableKnowledgeable: false
enableLWRExperienceConnectedApp: true
enableMemberVisibility: false
enableNicknameDisplay: true
enablePrivateMessages: false
enableReputation: false
enableShowAllNetworkSettings: false
enableSiteAsContainer: true
enableTalkingAboutStats: true
enableTopicAssignmentRules: true
enableTopicSuggestions: false
enableUpDownVote: false
forgotPasswordTemplate: unfiled$public/CommunityForgotPasswordEmailTemplate
gatherCustomerSentimentData: false
headlessForgotPasswordTemplate: unfiled$public/CommunityHeadlessForgotPasswordTemplate
headlessRegistrationTemplate: unfiled$public/CommunityHeadlessRegistrationTemplate
networkMemberGroups:
  - profile: admin
networkPageOverrides:
  - changePasswordPageOverrideSetting: Standard
  - forgotPasswordPageOverrideSetting: Designer
  - homePageOverrideSetting: Designer
  - loginPageOverrideSetting: Designer
  - selfRegProfilePageOverrideSetting: Designer
newSenderAddress: admin@company.com
picassoSite: {siteName}1
selfRegistration: false
sendWelcomeEmail: true
site: {siteName}
siteArchiveStatus: NotArchived
status: UnderConstruction
tabs:
  - defaultTab: home
  - standardTab: Chatter
urlPathPrefix: {siteUrlPathPrefix}vforcesite
welcomeTemplate: unfiled$public/CommunityWelcomeEmailTemplate
```

**CustomSite**:

```yaml
active: true
allowGuestPaymentsApi: false
allowHomePage: false
allowStandardAnswersPages: false
allowStandardIdeasPages: false
allowStandardLookups: false
allowStandardPortalPages: true
allowStandardSearch: false
authorizationRequiredPage: CommunitiesLogin
bandwidthExceededPage: BandwidthExceeded
browserXssProtection: true
cachePublicVisualforcePagesInProxyServers: true
clickjackProtectionLevel: SameOriginOnly
contentSniffingProtection: true
enableAuraRequests: true
fileNotFoundPage: FileNotFound
genericErrorPage: Exception
inMaintenancePage: InMaintenance
indexPage: CommunitiesLanding
masterLabel: {siteName}
redirectToCustomDomain: false
referrerPolicyOriginWhenCrossOrigin: true
selfRegPage: CommunitiesSelfReg
siteType: ChatterNetwork
urlPathPrefix: {siteUrlPathPrefix}vforcesite
```

### Content Defaults

apiNames and other metadata of site contents:

**sfdc_cms__appPage**:

- mainAppPage

**sfdc_cms__brandingSet**:

- Build_Your_Own_LWR

**sfdc_cms__languageSettings**:

- languages

**sfdc_cms__mobilePublisherConfig**:

- mobilePublisherConfig

**sfdc_cms__theme**:

- Build_Your_Own_LWR

**sfdc_cms__route**:

| Route | apiName | routeType | urlPrefix | urlName | viewId | configurationTags |
|-------|---------|-----------|-----------|---------|--------|-------------------|
| Home | Home | home | "" | home | home | |
| Login | Login | login-main | login | login | login | |
| Register | Register | self-register | SelfRegister | register | register | |
| Forgot_Password | Forgot_Password | forgot-password | ForgotPassword | forgot-password | forgotPassword | |
| Check_Password | Check_Password | check-password | CheckPasswordResetEmail | check-password | checkPasswordResetEmail | |
| Error | Error | error | error | error | error | |
| Service_Not_Available | Service_Not_Available | service-not-available | service-not-available | service-not-available | serviceNotAvailable | allow-in-static-site |
| Too_Many_Requests | Too_Many_Requests | too-many-requests | too-many-requests | too-many-requests | tooManyRequests | too-many-requests, allow-in-static-site |
| News_Detail__c | News_Detail__c | managed-content-sfdc_cms__news | news | news-detail | newsDetail | |

**sfdc_cms__view**:

| View | apiName | viewType | urlName | themeLayoutType |
|------|---------|----------|---------|-----------------|
| home | home | home | home | Inner |
| login | login | login-main | login | Inner |
| register | register | self-register | register | Inner |
| forgotPassword | forgotPassword | forgot-password | forgot-password | Inner |
| checkPasswordResetEmail | checkPasswordResetEmail | check-password | check-password | Inner |
| error | error | error | error | Inner |
| serviceNotAvailable | serviceNotAvailable | service-not-available | service-not-available | ServiceNotAvailable |
| tooManyRequests | tooManyRequests | too-many-requests | too-many-requests | ServiceNotAvailable |
| newsDetail | newsDetail | managed-content-sfdc_cms__news | news-detail | Inner |

**sfdc_cms__site**:

- {siteName}1

**sfdc_cms__themeLayout**:

- scopedHeaderAndFooter
- snaThemeLayout
