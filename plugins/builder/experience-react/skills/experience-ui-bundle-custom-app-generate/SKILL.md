---
name: experience-ui-bundle-custom-app-generate
description: "MUST activate when the project contains a uiBundles/*/src/ directory and the task involves creating or configuring a Custom Application for hosting a UI bundle in Lightning Experience. Use this skill when creating a CustomApplication metadata record to surface the UI bundle in the App Launcher. Activate when files matching applications/*.app-meta.xml exist and need modification, or when the user wants to expose their app via the Lightning App Launcher without a Digital Experience Site. Do NOT use platform-custom-application-generate for this — UI bundle apps do not use tabs, action overrides, or flexipages."
metadata:
  version: "1.0"
  domains: ["Experience", "Platform"]
  minApiVersion: "67.0"
  relatedSkills:
    - "platform-custom-application-generate"
    - "platform-metadata-api-context-get"
  cliTools:
    - tool: ["node"]
      semver: ">=18.0.0"
    - tool: ["sf"]
      semver: ">=2.0.0"
---

# Custom Application for React UI Bundles
Create and configure a Salesforce Custom Application that hosts a React UI bundle in Lightning Experience. This skill generates the CustomApplication metadata so the app appears in the Lightning App Launcher and can be accessed by internal users.

**Before opening the XML template or writing metadata, invoke `platform-metadata-api-context-get` and attempt Step 2's section-specific lookups for `CustomApplication.uiBundle` and `UIBundle.target`.** A template, missing `sfdx-project.json`, or missing org connection does not substitute for that lookup. Resolve the skill through the available runtime catalog as well as local directories. The existing fallback below applies only after a real context invocation/lookup attempt fails; it is not permission to skip the attempt.

Custom Applications differ from Experience Sites: they don't need Networks, CustomSite, DigitalExperienceConfig, or DigitalExperienceBundle metadata. The Custom Application acts as a thin launcher entry that delegates rendering to the React UI bundle referenced by `uiBundle`.

## Required Properties
Resolve all properties before generating any metadata. Each has a fallback chain — work through each option in order until a value is found.

| Property | Format | How to Resolve |
|----------|--------|----------------|
| **appName** | `lowercamelcase` (e.g., `myInternalApp`) | The UI bundle name from `uiBundles/<name>/` directory |
| **appNamespace** | String | `namespace` in `sfdx-project.json` → `sf data query -q "SELECT NamespacePrefix FROM Organization" --target-org ${usernameOrAlias}` → default `c` |
| **appLabel** | Human-readable string | User-provided, or derive from appName by converting camelCase to Title Case |

The `appNamespace` and `appName` connect the Custom Application to the correct React UI bundle through `<uiBundle>{appNamespace}__{appName}</uiBundle>`. Getting this wrong means the app launcher entry exists but shows a blank page.

## Generation Workflow
### Step 1: Resolve All Required Properties
Determine values for all properties before constructing anything. Use the resolution strategies in the table above.

### Step 2: Load API Context (Version-Aware Field Reference)
Invoke `platform-metadata-api-context-get` before generating metadata. Resolve `CustomApplication` and `UIBundle` using that skill's documented asset lookup and consume only the relevant `fields` entries and any needed enum or version-availability sections with `jq` or programmatic parsing. Do not read entire schema files or shards.

Bundled schema is an authoring reference, not live-org discovery. Cross-check documented field availability against the project's deployment API version; do not silently change that version. A missing schema entry is unavailable context, not proof that the target version lacks the field.

Resolve the effective deployment API version from the explicit deployment configuration or `sfdx-project.json` (`sourceApiVersion`). If it is unknown, ask the user before writing metadata. If it is below 67.0, stop: `CustomApplication.uiBundle` and the `UIBundle.target` value `CustomApplication` are available from API 67.0. Do not substitute undocumented legacy fields or silently upgrade the deployment version.

The metadata-context companion's schema snapshot and runtime serving minimum are separate from the deployment API version. A newer snapshot does not make these fields newer-version-only. If the runtime withholds the companion for the org version, record that failed invocation attempt and use the disclosed unavailable-context fallback below; do not claim the companion was loaded. An org eligible for a newer companion can still use this workflow with an explicitly resolved deployment API version of 67.0 or later.

**Required lookups:**
1. `CustomApplication.uiBundle` — check the field definition and documented version availability.
2. `UIBundle.target` — check the field definition, the `CustomApplication` value, and documented version availability.

**Field resolution based on version-specific evidence:**

| Field Check | XML for supported deployment versions |
|-------------|---------------------------------------|
| `CustomApplication.uiBundle` | Use `<uiBundle>{appNamespace}__{appName}</uiBundle>` |
| `UIBundle.target` and its `CustomApplication` value | Use `<target>CustomApplication</target>` |

If the context skill or required schema entries are unavailable after a real lookup attempt, retain the existing fallback to the documented field names (`uiBundle` + `target`) only after resolving a deployment version of 67.0 or later. State that bundled schema compatibility was not confirmed; deployment validation remains required. Field availability is documented in the official [CustomApplication](https://developer.salesforce.com/docs/atlas.en-us.api_meta.meta/api_meta/meta_customapplication.htm) and [UIBundle](https://developer.salesforce.com/docs/atlas.en-us.api_meta.meta/api_meta/meta_uibundle.htm) references.

A validation rejection alone is not version-availability evidence: diagnose it rather than substituting legacy fields or omitting `target`; until validation succeeds, report the output as unvalidated rather than promising App Launcher availability. A bundled target description listing only older values, or omitting `CustomApplication`, is unavailable context, not permission to infer AppLauncher/default equivalence. Apply the disclosed fallback only within the supported deployment-version range.

### Step 3: Create the Project Structure
Create any files and directories that don't already exist:

| Metadata Type | Path |
|--------------|------|
| CustomApplication | `<sourceDir>/applications/{appName}.app-meta.xml` |

**Note:** `<sourceDir>` is determined from `sfdx-project.json`. Read `packageDirectories[]` and use the entry where `"default": true`; the full source directory is `<path>/main/default`. If no default is set, use the first entry. Commonly `force-app/main/default`, but this path is configurable.

### Step 4: Populate All Metadata Fields
Use the default template in the doc below. Values in `{braces}` are resolved property references — substitute them with the actual values from Step 1. Apply the field resolution from Step 2 to determine which XML elements to use.

| Metadata Type | Template Reference |
|--------------|-------------------|
| CustomApplication | [configure-metadata-custom-application.md](references/configure-metadata-custom-application.md) |

### Execution Note for Step 4: Load and use the doc
- Agents MUST read the full contents of the references/*.md file referenced in Step 4 before attempting to populate metadata fields.
- Read the file in full, replace placeholders (e.g. `{appName}`) with the resolved values, then use the expanded template to populate the metadata XML content.

### Step 5: Update UI Bundle Meta XML
This step edits an **existing** file — it never creates a new one. `UIBundle` is a bundle-style metadata type: its meta XML normally lives inside its own folder at `uiBundles/{appName}/{appName}.uibundle-meta.xml`, alongside the bundle's other source files (e.g. `index.html`, `src/`). Some older or hand-authored projects may instead have it at the flat path `uiBundles/{appName}.uibundle-meta.xml` (no subfolder).

From the resolved `<sourceDir>` containing `uiBundles`, run `node "<absolute-skill-dir>/scripts/resolve-uibundle-path.mjs" "{appName}"` — it prints the path of the existing meta XML (preferring the nested layout, falling back to the flat layout). Resolve `<absolute-skill-dir>` to this skill's installed directory; do not change into that directory to run the resolver, because it searches relative to the current working directory. Always invoke via `node` (never as a bare executable) so this works on Windows as well as macOS/Linux. Edit that exact file in place; do not create a second file at the other path or migrate it to a different layout as part of this skill. If resolution fails despite an already-read descriptor, check the source-root working directory and existing path; do not treat that discrepancy as permission to create another descriptor.

After Step 2's deployment-version check, add `<target>CustomApplication</target>` inside the existing `<UIBundle>` element of that file, preserving every other existing element and value untouched.

**Do NOT:**
- Create a new `.uibundle-meta.xml` file
- Create a second `.uibundle-meta.xml` file at a different path when one already exists (nested or flat) — edit the existing one in place, wherever it is
- Leave the original `uiBundles/{appName}/{appName}.uibundle-meta.xml` (or `uiBundles/{appName}.uibundle-meta.xml`, if that's the existing layout) unmodified while adding `<target>` somewhere else

The only files this skill produces or modifies are `applications/{appName}.app-meta.xml` (new) and the existing `{appName}.uibundle-meta.xml` (edited in place). Any other UI-bundle-related file appearing in the output is a bug.

Example of the fully updated file (at `uiBundles/{appName}/{appName}.uibundle-meta.xml`, or the flat path if that's the existing layout) — this illustrates the end state of the existing file, not a new file to create:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<UIBundle xmlns="http://soap.sforce.com/2006/04/metadata">
    <masterLabel>{appName}</masterLabel>
    <description>A Salesforce UI Bundle.</description>
    <isActive>true</isActive>
    <version>1</version>
    <target>CustomApplication</target>
</UIBundle>
```

### Step 6: Do Not Modify Non-Templated Properties
Do not modify any default property values for `CustomApplication` metadata that are not expressed as variables wrapped in `{braces}`.

## Verification Checklist
Before deploying, confirm:

- [ ] All required properties are resolved
- [ ] API context skill was loaded and relevant schema sections were consumed, or the existing unavailable-context fallback was recorded (Step 2)
- [ ] `applications/{appName}.app-meta.xml` exists with correct content
- [ ] The resolved deployment API version is 67.0 or later; it was not silently upgraded, and the bundle reference uses `<uiBundle>`
- [ ] The **existing** `{appName}.uibundle-meta.xml` (nested at `uiBundles/{appName}/`, or flat at `uiBundles/`, whichever already existed) has `<target>CustomApplication</target>`
- [ ] No extra `.uibundle-meta.xml` file was created — exactly one `{appName}.uibundle-meta.xml` exists, at whichever path it already lived at
- [ ] Deployment validates successfully at the resolved version (set `deploymentApiVersion` to that value; do not let the CLI choose a newer default):
```bash
sf project deploy validate --metadata CustomApplication UIBundle --target-org ${usernameOrAlias} --api-version ${deploymentApiVersion}
```
