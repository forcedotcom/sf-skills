# Application FlexiPage Mapping Reference

## Overview

The application file at `.lsc-starter-config/LSStarterConfig/PackageComponents/applications/lsc4ce__lifeSciencesCommercial.app-meta.xml` contains both `<actionOverrides>` and `<profileActionOverrides>` that reference flexipages. After selective flexipage deployment, the application file must be updated to include only overrides for deployed pages.

## FlexiPage-to-ActionOverride Mapping

The `<actionOverrides>` section uses **managed package prefixed** content names (`lsc4ce__`). These are package-level overrides that reference flexipages from the managed package. They should be **retained as-is** since they reference package flexipages that already exist.

| actionOverrides content | pageOrSobjectType | Corresponding Deployable FlexiPage |
|------------------------|-------------------|-------------------------------------|
| lsc4ce__AccountHCP | Account | LSCAccountHCP |
| lsc4ce__Account_Plan | AccountPlan | Account_Plan3 |
| lsc4ce__Account_Plan_Objective_Record_Page | AccountPlanObjective | Account_Plan_Objective_Record_Page3 |
| lsc4ce__Goal_Definition | GoalDefinition | Goal_Definition1 |
| lsc4ce__Provider_Visit | ProviderVisit | CPVisitLandingPage (Visit-level override) |
| lsc4ce__Sprint | Sprint | (no direct deployable equivalent) |
| lsc4ce__TerritoryBusinessPlanRecordPage | TerritoryBusinessPlan | (no direct deployable equivalent) |

## FlexiPage-to-ProfileActionOverride Mapping

The `<profileActionOverrides>` section uses **unmanaged** content names that directly correspond to deployable flexipages. These must be filtered based on user selection.

| profileActionOverrides content | pageOrSobjectType | Record Types | FlexiPage File |
|-------------------------------|-------------------|--------------|----------------|
| CPVisitLandingPage | Visit | — | CPVisitLandingPage.flexipage-meta.xml |
| LSC_Inquiry | Inquiry | Adverse_Event, LSC_General, Medical_Inquiry, (none) | LSC_Inquiry.flexipage-meta.xml |
| Goal_Definition1 | GoalDefinition | — | Goal_Definition1.flexipage-meta.xml |
| Account_Plan3 | AccountPlan | — | Account_Plan3.flexipage-meta.xml |
| Account_Plan_Objective_Record_Page3 | AccountPlanObjective | — | Account_Plan_Objective_Record_Page3.flexipage-meta.xml |
| LSCAccountHCP | Account | Business, Business_Account, Health_Care_Organization, PersonAccount.Health_Care_Provider, PersonAccount.PersonAccount, (none) | LSCAccountHCP.flexipage-meta.xml |
| Contact_Point_Address_Record_Page | ContactPointAddress | — | Contact_Point_Address_Record_Page.flexipage-meta.xml |
| Home_Page_LSC_Default | standard-home | — | Home_Page_LSC_Default.flexipage-meta.xml |

## Update Rules

### actionOverrides

The `<actionOverrides>` entries (lines 3–128 of the app file) reference managed package flexipages (`lsc4ce__*`). These should be **kept as-is** regardless of user selection — they reference pre-existing package pages.

### profileActionOverrides

For `<profileActionOverrides>` (lines 138–665), apply these rules:

1. **Keep** overrides where `<content>` matches a SELECTED flexipage name
2. **Remove** overrides where `<content>` matches an UNSELECTED flexipage name
3. Each selected flexipage generates overrides for BOTH profiles (LSC Custom Profile and Admin) and BOTH form factors (Small and Large)
4. Some flexipages have multiple record-type-specific overrides (e.g., LSC_Inquiry has entries for Adverse_Event, LSC_General, Medical_Inquiry, and a default with no recordType)

### Example: User selects only CPVisitLandingPage and LSC_Inquiry

Keep only these `<profileActionOverrides>` blocks:

```xml
<!-- CPVisitLandingPage overrides (4 entries: 2 profiles x 2 form factors) -->
<profileActionOverrides>
    <actionName>View</actionName>
    <content>CPVisitLandingPage</content>
    <formFactor>Small</formFactor>
    <pageOrSobjectType>Visit</pageOrSobjectType>
    <type>Flexipage</type>
    <profile>LSC Custom Profile</profile>
</profileActionOverrides>
<profileActionOverrides>
    <actionName>View</actionName>
    <content>CPVisitLandingPage</content>
    <formFactor>Large</formFactor>
    <pageOrSobjectType>Visit</pageOrSobjectType>
    <type>Flexipage</type>
    <profile>LSC Custom Profile</profile>
</profileActionOverrides>
<profileActionOverrides>
    <actionName>View</actionName>
    <content>CPVisitLandingPage</content>
    <formFactor>Small</formFactor>
    <pageOrSobjectType>Visit</pageOrSobjectType>
    <type>Flexipage</type>
    <profile>Admin</profile>
</profileActionOverrides>
<profileActionOverrides>
    <actionName>View</actionName>
    <content>CPVisitLandingPage</content>
    <formFactor>Large</formFactor>
    <pageOrSobjectType>Visit</pageOrSobjectType>
    <type>Flexipage</type>
    <profile>Admin</profile>
</profileActionOverrides>

<!-- LSC_Inquiry overrides (many entries: per record type x 2 profiles x 2 form factors) -->
<!-- Include ALL LSC_Inquiry entries (Adverse_Event, LSC_General, Medical_Inquiry, and default) -->
```

### Home_Page_LSC_Default Special Case

The Home Page flexipage uses `actionName=Tab` (not `View`) and `pageOrSobjectType=standard-home`:
```xml
<profileActionOverrides>
    <actionName>Tab</actionName>
    <content>Home_Page_LSC_Default</content>
    <formFactor>Large</formFactor>
    <pageOrSobjectType>standard-home</pageOrSobjectType>
    <type>Flexipage</type>
    <profile>Admin</profile>
</profileActionOverrides>
```

## Static Elements to Always Keep

These elements in the application file are NOT related to flexipages and must always be preserved:
- `<description>`
- `<formFactors>`
- `<isNav*>` settings
- `<isOmniPinnedViewEnabled>`
- `<label>`
- `<navType>`
- `<subscriberTabs>`
- `<tabs>`
- `<uiType>`
- `<utilityBar>`

## Deploy Command

After updating the application file:
```bash
sf project deploy start --source-dir .lsc-starter-config/LSStarterConfig/PackageComponents/applications --target-org <org>
```
