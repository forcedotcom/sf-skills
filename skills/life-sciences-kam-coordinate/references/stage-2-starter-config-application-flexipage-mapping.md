# Application FlexiPage Mapping Reference (KAM)

## Overview

The application file at `.lsc-starter-config/LSStarterConfig/PackageComponents/applications/lsc4ce__lifeSciencesCommercial.app-meta.xml` contains both `<actionOverrides>` and `<profileActionOverrides>` that reference flexipages. After the KAM flexipages are deployed (Step 12), the application file must be updated to include only overrides for deployed pages.

## The Six KAM FlexiPages

For the KAM workflow, only these six flexipages are offered and confirmed with the user (see `stage-2-starter-config-overview.md`, Step 12):

| FlexiPage | pageOrSobjectType | Record Types |
|-----------|-------------------|--------------|
| Home_Page_LSC_Default | standard-home | — |
| LSCAccountHCP | Account | Business, Business_Account, Health_Care_Organization, PersonAccount.Health_Care_Provider, PersonAccount.PersonAccount, (none) |
| Contact_Point_Address_Record_Page | ContactPointAddress | — |
| Account_Plan_Objective_Record_Page3 | AccountPlanObjective | — |
| Account_Plan3 | AccountPlan | — |
| Goal_Definition1 | GoalDefinition | — |

## actionOverrides (keep as-is)

The `<actionOverrides>` section uses **managed package prefixed** content names (`lsc4ce__`). These are package-level overrides referencing managed-package flexipages that already exist; **retain them as-is** regardless of selection. The KAM-relevant ones:

| actionOverrides content | pageOrSobjectType | Corresponding deployable FlexiPage |
|------------------------|-------------------|-------------------------------------|
| lsc4ce__AccountHCP | Account | LSCAccountHCP |
| lsc4ce__Account_Plan | AccountPlan | Account_Plan3 |
| lsc4ce__Account_Plan_Objective_Record_Page | AccountPlanObjective | Account_Plan_Objective_Record_Page3 |
| lsc4ce__Goal_Definition | GoalDefinition | Goal_Definition1 |

## profileActionOverrides (filter to deployed pages)

The `<profileActionOverrides>` section uses **unmanaged** content names that directly correspond to deployable flexipages. Apply these rules:

1. **Keep** overrides where `<content>` matches a DEPLOYED (confirmed) flexipage name.
2. **Remove** overrides where `<content>` matches an UNSELECTED flexipage name.
3. Each selected flexipage generates overrides for BOTH profiles (LSC Custom Profile and Admin) and BOTH form factors (Small and Large).
4. Some flexipages have multiple record-type-specific overrides (e.g. `LSCAccountHCP`).

### Example: LSCAccountHCP profileActionOverrides block

```xml
<profileActionOverrides>
    <actionName>View</actionName>
    <content>LSCAccountHCP</content>
    <formFactor>Large</formFactor>
    <pageOrSobjectType>Account</pageOrSobjectType>
    <recordType>Health_Care_Organization</recordType>
    <type>Flexipage</type>
    <profile>LSC Custom Profile</profile>
</profileActionOverrides>
```
Repeat per record type × form factor (Small/Large) × profile (LSC Custom Profile/Admin). Include the record-type variants listed in the table above plus the default (no `<recordType>`) entry.

### Home_Page_LSC_Default special case

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
- `<description>`, `<formFactors>`, `<isNav*>` settings, `<isOmniPinnedViewEnabled>`, `<label>`, `<navType>`, `<subscriberTabs>`, `<tabs>`, `<uiType>`, `<utilityBar>`

## Deploy Command

After updating the application file:
```bash
sf project deploy start --source-dir .lsc-starter-config/LSStarterConfig/PackageComponents/applications --target-org <org>
```
