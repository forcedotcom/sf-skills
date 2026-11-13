---
name: platform-custom-application-generate
description: "Use this skill when users need to create or configure tab-based Salesforce Custom Applications with navigation, branding, and action overrides. Trigger when users mention custom apps, application metadata, app navigation, or organizing tabs into applications. Use when users want to create app containers for tabs and pages. Do NOT use when the goal is hosting a React UI bundle in the App Launcher — use experience-ui-bundle-custom-app-generate for that case."
metadata:
  version: "1.0"
  domains: ["Platform"]
  minApiVersion: "60.0"
  relatedSkills:
    - "experience-ui-bundle-custom-app-generate"
---

## When to Use This Skill

Use this skill when you need to:
- Create Lightning applications
- Organize tabs and features into focused apps
- Configure application navigation and branding
- Set up custom page layouts for objects
- Troubleshoot deployment errors related to custom applications
# CustomApplication (Lightning App) Metadata Specification

## Overview

Custom applications (Lightning Apps) that group tabs and functionality to provide a focused user experience for specific business processes. Always configured for Lightning Experience.

## Required Properties

### Core Application Properties
- **fullName**: API name of the application
- **label**: Display name of the application
- **uiType**: Always "Lightning" for modern apps
- **navType**: CRITICAL - Choose based on user requirements and workflow patterns
    - "Standard": DEFAULT for general business applications (e.g., sales, marketing, operations)
    - "Console": ONLY when workflow requires managing multiple records simultaneously with split-view or multi-tab workspace (e.g., customer service, call centers, support operations)
- **formFactors**: Array of form factors (["LARGE"] for desktop, ["SMALL"] for mobile, or both)

### Optional Properties
- **description**: Brief description of the application's purpose
- **tabs**: Array of tab names to include
- **utilityBar**: API name of the Utility Bar configuration
- **brand**: HIGHLY RECOMMENDED - Branding configuration object (headerColor, shouldOverrideOrgTheme, footerColor)
- **actionOverrides**: REQUIRED when custom record pages exist - Action override configuration (actionName, content, formFactor, type, pageOrSobjectType)
- **profileActionOverrides**: Profile-specific action overrides (actionName, content, formFactor, pageOrSobjectType, type, profile)
- **isNavAutoTempTabsDisabled**, **isNavPersonalizationDisabled**, **isNavTabPersistenceDisabled**: automatic temporary tabs, user personalization, and tab persistence across sessions (default: false)

## Asking the User
- Ask every question as plain text in your reply, so the skill works in any client; do not depend on a picker, multi-select, or confirm UI component. Wait for the user's next message as the answer
- Ask only what the request leaves open (navigation style, tabs, utility items, profiles), all in one message, each with a sensible default the user can accept with "yes" or "go ahead". Profiles are the exception: if the request doesn't name the profiles, always ask before saving (a group such as "my support agents" names no profile: suggest the matching ones and ask), and don't default to the admin alone
- Finding an existing app by name: query Tooling `SELECT Id, DeveloperName, Label FROM CustomApplication WHERE Label = '<name>'` (or `LIKE`). Don't use AppDefinition for this, because it lists only the apps the running user can see, so an app shared with other profiles looks missing. If several apps match, or none does, ask in plain text with the closest labels as a numbered list
- Before saving, restate the plan in one short list (label, API name, navigation style, tabs, utility items, profiles including the admin) and save once the user agrees. When the request already says everything (including who should see the app), say what you'll create and go ahead. If no one can answer, use the defaults and say so

## Application Configuration

### Navigation Type Selection (CRITICAL)
**Decision Criteria for navType:**

**Choose "Standard" (DEFAULT) for:**
- General business applications and most workflows
- Single-record focus or linear navigation patterns
- Standard tab-based navigation is sufficient

**Choose "Console" ONLY when workflow requires:**
- Managing multiple related records simultaneously in split-view
- Multi-tab workspace for handling complex, interconnected data
- Contextual information from multiple sources visible at once
- Examples: customer service operations, support desks, call centers

**When in doubt:** Default to "Standard" for most general business use cases

### Tab Management
- **tabs**: Array of tab names to include in the application
- **workspaceConfig** (Console apps only): one `<mappings><tab>TAB</tab></mappings>` entry per tab, e.g. `standard-Case`. Every tab of a Console app needs a mapping, including tabs added later; otherwise the save fails with "The standard-Account tab doesn't include a workspace mapping"
- **formFactors**: Device-specific configurations (Large for desktop, Small for mobile)

### Utility Bar
- **utilityBar**: API name of a FlexiPage of type UtilityBar (the bar at the bottom of Lightning Experience). The page is separate metadata and must exist before the app references it, otherwise the app save fails with "In field: utilityBar - no FlexiPage named ... found". Generate it alongside the app: template `one:utilityBarTemplateDesktop`, one `utilityItems` Region for the items and one `backgroundComponents` Background region:
```xml
<FlexiPage xmlns="http://soap.sforce.com/2006/04/metadata">
    <flexiPageRegions>
        <itemInstances>
            <componentInstance>
                <componentName>console:history</componentName>
                <identifier>console_history</identifier>
            </componentInstance>
        </itemInstances>
        <name>utilityItems</name>
        <type>Region</type>
    </flexiPageRegions>
    <flexiPageRegions>
        <name>backgroundComponents</name>
        <type>Background</type>
    </flexiPageRegions>
    <masterLabel>Support Console UtilityBar</masterLabel>
    <template>
        <name>one:utilityBarTemplateDesktop</name>
    </template>
    <type>UtilityBar</type>
</FlexiPage>
```
- Common Service Console items (componentName): `console:history` (History), `notes:utilityBarNoteList` (Notes), `flexipage:recentItems` (Recent Items), `macros:macroUtilityItem` (Macros), `runtime_service_omnichannel:omniWidget` (Omni-Channel, only when Omni-Channel is enabled)
- `flexipage:recentItems` needs exactly these properties, or the save fails with "missing required decorator property [label]". Copy this instance; a decorator property keeps its plain name and adds `<type>decorator</type>` (never `decorator.label`), and `entityNames` is a `valueList` of the objects reps need (a plain string fails with "Value is not allowed for Array attribute type"). Other items (History, Notes, Macros, Omni-Channel) take no properties at all: adding decorators to them fails with "You can't modify decorator property":
```xml
<componentInstance>
<componentInstanceProperties><name>eager</name><type>decorator</type><value>false</value></componentInstanceProperties>
<componentInstanceProperties><name>entityNames</name><valueList><valueListItems><value>Case</value></valueListItems><valueListItems><value>Contact</value></valueListItems></valueList></componentInstanceProperties>
<componentInstanceProperties><name>height</name><type>decorator</type><value>480</value></componentInstanceProperties>
<componentInstanceProperties><name>icon</name><type>decorator</type><value>fallback</value></componentInstanceProperties>
<componentInstanceProperties><name>label</name><value>Standard.RecentItems</value></componentInstanceProperties>
<componentInstanceProperties><name>label</name><type>decorator</type><value>Recent Items</value></componentInstanceProperties>
<componentInstanceProperties><name>maxRecords</name><value>3</value></componentInstanceProperties>
<componentInstanceProperties><name>scrollable</name><type>decorator</type><value>true</value></componentInstanceProperties>
<componentInstanceProperties><name>width</name><type>decorator</type><value>340</value></componentInstanceProperties>
<componentName>flexipage:recentItems</componentName>
<identifier>flexipage_recentItems</identifier>
</componentInstance>
```
- Only `lightning:backgroundUtilityItem` goes in the Background region
- Changing a bar: read the current page and add only the requested items whose componentName isn't on it yet; leave existing items (identifiers, properties) as they are. Identifiers must be unique on the page, so give a new item an unused one (e.g. `console_history_2`). Running the same setup twice leaves the bar unchanged

### Branding (HIGHLY RECOMMENDED - DO NOT SKIP)
**IMPORTANT**: Provide branding configuration to create a professional, visually distinct application identity.

- **brand.headerColor**: Header bar color in hex format (e.g., "#0070D2") - RECOMMENDED
- **brand.shouldOverrideOrgTheme**: Override organization theme (true/false) - Default: false
- **brand.footerColor**: Footer color in hex format
- **logo**: a ContentAsset API name. Before setting it, look for `contentassets/<name>.asset-meta.xml` in the project or a ContentAsset with that DeveloperName in the org. If neither exists, omit `<logo>` even when the user names one (the deploy fails otherwise) and say so.

### Action Overrides (CRITICAL - DO NOT SKIP)
**IMPORTANT**: Action overrides MUST be created for every custom object tab that has a record page generated by flexipage expert.

- **actionOverrides.actionName**: Action to override ("View" or "Tab")
- **actionOverrides.content**: Page/component name (FlexiPage, Visualforce, Lightning component): the record page ("View") or home/app page ("Tab") generated by flexipage expert
- **actionOverrides.formFactor**: Device type ("Large" or "Small")
- **actionOverrides.type**: Override type ("Default", "Visualforce", "Flexipage", "LightningComponent", "Scontrol"); use "Flexipage" for Lightning record/home pages generated by flexipage expert
- **actionOverrides.pageOrSobjectType**: Object API name the override applies to
- **actionOverrides.comment**: Optional description (max 1000 characters)
- **actionOverrides.skipRecordTypeSelect**: Skip record type selection (default: false)

### Profile Action Overrides
- **profileActionOverrides.actionName**: Action to override ("View" or "Tab")
- **profileActionOverrides.content**: Page/component name: the profile-specific record page ("View") or home page ("Tab") generated by flexipage expert
- **profileActionOverrides.formFactor**: Device type ("Large" or "Small")
- **profileActionOverrides.pageOrSobjectType**: Object API name
- **profileActionOverrides.type**: Override type; use "Flexipage" for Lightning pages generated by flexipage expert
- **profileActionOverrides.profile**: Profile API name (e.g., "Admin", "Standard User")
    - Enables different page layouts for different user profiles
    - This does NOT control who can see the app; see App Visibility

### App Visibility (CRITICAL - DO NOT SKIP)
**IMPORTANT**: CustomApplication has no visibility field. An app that no profile or permission set grants is invisible to everyone, including the admin who created it. This is the User Profiles step (the last step) of the New Lightning App wizard. `profileActionOverrides` does not grant visibility. If the request asks only for the CustomApplication file, don't add Profile or FlexiPage files; mention visibility in the summary instead.

- **Always grant the running admin's profile** on top of the profiles the user names, as the wizard pre-selects it, in the same step; say so in the summary, and leave it out only when the user explicitly says the admin must not see the app. The admin is the user making the calls, not the app's creator, which matters when editing someone else's app (see Discovery queries)
- **Ask which other profiles should see the app** when the user hasn't said, once, in plain text (see Asking the User): a numbered list of the assignable profiles, support agents' profiles first for service/console apps, noting that System Administrator is already included and that the user can name several (names or numbers, e.g. "Standard User, Contract Manager" or "1, 3"), "all", or "just me"
- **Read the answer as a list**: split on commas, "and", and new lines; match each entry by number, exact name, or a case-insensitive unique prefix ("marketing" -> Marketing User). "all" means every assignable profile; "just me" / "only admins" means only the admin's. Grant every match in one save
- **Unmatched names**: if an entry matches no profile, or several, ask once about just those entries (show the closest names) before saving anything; never guess and never silently drop one. If the user then skips them, grant the rest and list the skipped names in the summary
- **Removing a profile**: remove only that profile: delete its SetupEntityAccess row (`DELETE /sobjects/SetupEntityAccess/<0J0 Id>`, found with `SELECT Id FROM SetupEntityAccess WHERE SetupEntityId = '<02u app Id>' AND ParentId = '<0PS Id>'`) or deploy its applicationVisibilities with `<visible>false</visible>`. Never remove the admin's profile unless the user names it
- **On a connected org, grant with SetupEntityAccess** (preferred): insert rows with `SetupEntityId` = the app's 02u Id and `ParentId` = the profile's PermissionSet Id, only for ids that don't have a row yet, in one `composite/sobjects` call. It adds profiles without touching the others and works for any profile name. The NavigationMenus (App Manager) skill is an alternative
- **Grant with Profile metadata**: one `applicationVisibilities` entry per Profile (or PermissionSet), deployed after (or in the same package as) the app; a Profile with only this element merges into the existing profile. Address the profile by metadata name, not label: "Admin" (System Administrator), "Standard" (Standard User), "MarketingProfile", "ContractManager"; look one up with Tooling `SELECT FullName FROM Profile WHERE Name = '<label>'`. `/headless/metadata` rejects names with spaces or special characters with "Invalid fullName" (most custom profiles, e.g. "Tier 2 Support Agent"), so use SetupEntityAccess for those. Set `<default>true</default>` only when the user asks for the app to be the profile's default. Example: [references/app-visibility.md](references/app-visibility.md)
- **Discovery queries** (data API `/query`, not Tooling, which has no Profile.UserType):
    - assignable profiles and their PermissionSet Ids: `SELECT Id, Profile.Name FROM PermissionSet WHERE IsOwnedByProfile = true AND Profile.UserType = 'Standard' ORDER BY Profile.Name`
    - support agents' profiles: `SELECT Profile.Name, COUNT(Id) FROM User WHERE IsActive = true AND UserPermissionsSupportUser = true GROUP BY Profile.Name`
    - the running admin's profile: `GET /services/data/v66.0/` returns `identity` as `…/id/<org Id>/<user Id>`; take the last segment, then `SELECT Profile.Name FROM User WHERE Id = '<user Id>'`
- **Verify**: `SELECT Parent.Profile.Name FROM SetupEntityAccess WHERE SetupEntityId = '<02u app Id>'` lists every chosen profile, and `SELECT DurableId FROM AppDefinition WHERE DeveloperName = '<app>'` returns the app for the admin

## Deploying to a Connected Org
- **Order**: UtilityBar FlexiPage, then the CustomApplication (references the FlexiPage), then the visibility grants (reference the app). Each fails with INVALID_CROSS_REFERENCE_KEY if the one before it isn't saved
- **Headless 360**: create with `POST /headless/metadata` and update with `PUT /headless/metadata`, body `{"type": "<FlexiPage|CustomApplication|Profile>", "fullName": "<api name>", "xmlRep": "<xml>"}`; read with `GET /headless/metadata?type=<type>&fullName=<api name>`.
- **Updating an existing app**: GET its current metadata first and send back the full definition with your changes; do not drop tabs, overrides, or utilityBar the user didn't ask to change
- **Timeouts and 500s can still mean it saved**: a metadata save can take a minute or more, and a FlexiPage save can commit and still return an opaque 500 "Internal error" (no componentFailures, no message). Never retry a POST straight away: first run Tooling `SELECT Id FROM FlexiPage|CustomApplication WHERE DeveloperName = '<name>'`. If a row comes back, the save landed; read it back and continue (PUT for any further change). A save can take a few seconds to show up, so if the query comes back empty, wait about 10 seconds and query once more before retrying. A retried POST that returns DUPLICATE_VALUE ("Component already exists") means an earlier save landed. A GET of a UtilityBar FlexiPage can also return 500; the query still tells you whether it exists
- **Org_Admin_Locked**: another setup change holds the org lock; wait a few seconds and retry the same save (check first that it didn't land). Save one component at a time, never in parallel
- **Errors are actionable**: "missing required decorator property" means a utility item lacks properties; "no FlexiPage named ... found" or "no CustomApplication named ... found" means the save order was wrong

## Device Support, Navigation Behavior, and Integration Points
See [references/app-properties.md](references/app-properties.md) for the purpose of an app, form factors per device, navigation behavior flags, accessibility, and the tab and component types an app can include.

## Best Practices
- **General design**: clear names and descriptions, related functionality grouped by user role (see references/app-properties.md)
- **Use accessible brand colors**: Ensure hex colors have sufficient contrast (WCAG AA compliant)
- **Configure utility bars**: Add useful quick-access tools for users (for console apps: History, Notes, Recent Items, Macros)
- **Always grant app visibility**: Ask which profiles should see the app and include the running admin's

## Enhancement Rules
- **uiType**: Always set to "Lightning" for modern app experience
- **navType**: CRITICAL DECISION - apply Navigation Type Selection; when in doubt, choose "Standard"
- **formFactors**: Always set to ["LARGE"] for desktop Lightning Experience
- **Standard Tabs**: Automatically add Home, Accounts, Contacts, Opportunities, Leads, Cases
- **Navigation Settings**: Set all navigation flags to false for best user experience
- **Branding**: ALWAYS include brand configuration for professional application identity
    - MANDATORY: Set brand.headerColor to appropriate color (e.g., "#0070D2" for Salesforce Blue)
    - Set brand.shouldOverrideOrgTheme based on requirements
- **Action Overrides**: ALWAYS create a "View" override (type "Flexipage", formFactor "Large") for every custom object with a flexipage expert record page
- **Profile Action Overrides**: Reference flexipage expert generated pages for role-based customization
- **Form Factors**: Use "Large" for desktop, "Small" for mobile in overrides

## CRITICAL Verification Checklist (MUST VERIFY)
- [ ] All tabs are included in the application
- [ ] **navType IS CORRECTLY SET** - Verify Console vs Standard selection
- [ ] "Console" ONLY if the workflow needs multiple records at once (split-view, multi-tab workspace); otherwise, or when ambiguous, "Standard"
- [ ] **BRANDING IS CONFIGURED** - This is HIGHLY RECOMMENDED for professional applications
- [ ] brand.headerColor is a valid hex color (e.g., "#0070D2") and brand.shouldOverrideOrgTheme is set (default: false)
- [ ] **ACTION OVERRIDES ARE CREATED** - This is MANDATORY for every custom object with a record page
- [ ] EACH custom object tab has an actionOverrides entry: actionName "View", type "Flexipage", formFactor "Large", the object's API name as pageOrSobjectType, and the exact flexipage expert FlexiPage name as content
- [ ] All required fields are populated (fullName, label, uiType, navType, formFactors)
- [ ] **APP VISIBILITY IS GRANTED** - the running admin's profile (even if the user didn't pick it) plus every profile the user chose have a SetupEntityAccess row or applicationVisibilities entry (visible true)
- [ ] Profiles are addressed by metadata name (Admin, Standard, ...), not label
- [ ] Console apps: every tab has a workspaceConfig mapping
- [ ] If utilityBar is set, the UtilityBar FlexiPage is generated (or already exists) and is saved before the app
- [ ] Every flexipage:recentItems item carries entityNames and its decorator properties
