# Configure Metadata: CustomApplication

## Purpose
This configuration file creates a **net-new, default** CustomApplication metadata record for a Lightning Experience app that hosts a React UI bundle. It is not intended to edit or modify an existing CustomApplication record. Use this template only when provisioning a brand-new Custom Application for a UI bundle.

## File Location
```
<sourceDir>/applications/{appName}.app-meta.xml
```

**Note:** Determine `<sourceDir>` from `sfdx-project.json` → `packageDirectories[]` → find the entry with `"default": true` → use its `path` value + `/main/default`. Commonly `force-app/main/default`, but this is configurable.

## Default Template (newer API versions — `uiBundle` field available)
```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomApplication xmlns="http://soap.sforce.com/2006/04/metadata">
    <brand>
        <headerColor>#0070D2</headerColor>
        <shouldOverrideOrgTheme>false</shouldOverrideOrgTheme>
    </brand>
    <formFactors>Small</formFactors>
    <formFactors>Large</formFactors>
    <isNavAutoTempTabsDisabled>false</isNavAutoTempTabsDisabled>
    <isNavPersonalizationDisabled>false</isNavPersonalizationDisabled>
    <isNavTabPersistenceDisabled>false</isNavTabPersistenceDisabled>
    <isOmniPinnedViewEnabled>false</isOmniPinnedViewEnabled>
    <label>{appLabel}</label>
    <navType>Standard</navType>
    <uiBundle>{appNamespace}__{appName}</uiBundle>
    <uiType>Lightning</uiType>
</CustomApplication>
```

## Fallback Template (older API versions — `uiBundle` field NOT available)
```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomApplication xmlns="http://soap.sforce.com/2006/04/metadata">
    <brand>
        <headerColor>#0070D2</headerColor>
        <shouldOverrideOrgTheme>false</shouldOverrideOrgTheme>
    </brand>
    <formFactors>Small</formFactors>
    <formFactors>Large</formFactors>
    <isNavAutoTempTabsDisabled>false</isNavAutoTempTabsDisabled>
    <isNavPersonalizationDisabled>false</isNavPersonalizationDisabled>
    <isNavTabPersistenceDisabled>false</isNavTabPersistenceDisabled>
    <isOmniPinnedViewEnabled>false</isOmniPinnedViewEnabled>
    <label>{appLabel}</label>
    <navType>Standard</navType>
    <webApplication>{appName}</webApplication>
    <uiType>Lightning</uiType>
</CustomApplication>
```

## Field Reference

| Field | Required | Version | Description |
|-------|----------|---------|-------------|
| `brand.headerColor` | Yes | All | Hex color for the app header bar in Lightning Experience. Default: `#0070D2` (Salesforce blue). |
| `brand.shouldOverrideOrgTheme` | Yes | All | Whether this app's branding overrides the org theme. Default: `false`. |
| `formFactors` | Yes | All | Supported form factors. Include both `Small` (mobile) and `Large` (desktop) for full coverage. |
| `isNavAutoTempTabsDisabled` | Yes | All | Disable auto-creation of temporary tabs. Default: `false`. |
| `isNavPersonalizationDisabled` | Yes | All | Disable user personalization of navigation. Default: `false`. |
| `isNavTabPersistenceDisabled` | Yes | All | Disable persistence of nav tabs across sessions. Default: `false`. |
| `isOmniPinnedViewEnabled` | Yes | All | Enable Omni-channel pinned view. Default: `false`. |
| `label` | Yes | All | Human-readable label shown in the App Launcher and app switcher. |
| `navType` | Yes | All | Navigation type. Use `Standard` for standard Lightning navigation. |
| `uiBundle` | Conditional | Newer | Namespace-qualified developer name of the UI bundle (`{appNamespace}__{appName}`). Use when `get_metadata_type_fields` confirms this field exists on `CustomApplication`. |
| `webApplication` | Conditional | Older | Developer name of the UI bundle (`{appName}`, no namespace). Use when `uiBundle` field is not available. |
| `uiType` | Yes | All | UI framework type. Must be `Lightning` for UI bundle apps. |
