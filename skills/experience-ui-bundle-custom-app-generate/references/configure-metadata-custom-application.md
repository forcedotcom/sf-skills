# Configure Metadata: CustomApplication

## Context prerequisite

Before expanding the template, invoke `platform-metadata-api-context-get` and attempt the generator's Step 2 lookups. Resolve a deployment API version of 67.0 or later; stop if it is lower, and ask the user if it is unknown. This reference is a template, not schema or deployment-version evidence. Preserve Step 2's existing unavailable-context fallback only after an actual lookup attempt and within that supported version range. The companion's snapshot version and org-version serving gate do not determine the introduction version of individual fields.

## Purpose
This configuration file creates a **net-new, default** CustomApplication metadata record for a Lightning Experience app that hosts a React UI bundle. It is not intended to edit or modify an existing CustomApplication record. Use this template only when provisioning a brand-new Custom Application for a UI bundle.

## File Location
```xml
<sourceDir>/applications/{appName}.app-meta.xml
```

**Note:** Determine `<sourceDir>` from `sfdx-project.json` → `packageDirectories[]` → find the entry with `"default": true` → use its `path` value + `/main/default`. Commonly `force-app/main/default`, but this is configurable.

## Default Template (supported workflow: API 67.0 and later)
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
| `uiBundle` | Required for this workflow | 67.0+ | Namespace-qualified developer name of the UI bundle (`{appNamespace}__{appName}`). Follow Step 2's context lookup, deployment-version check, and disclosed unavailable-context fallback. |
| `uiType` | Yes | All | UI framework type. Must be `Lightning` for UI bundle apps. |
