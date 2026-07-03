---
name: experience-ui-bundle-custom-app-generate
description: "MUST activate when the project contains a uiBundles/*/src/ directory and the task involves creating or configuring a Custom Application for hosting a UI bundle in Lightning Experience. Use this skill when creating a CustomApplication metadata record to surface the UI bundle in the App Launcher. Activate when files matching applications/*.app-meta.xml exist and need modification, or when the user wants to expose their app via the Lightning App Launcher without a Digital Experience Site. Do NOT use platform-custom-application-generate for this — UI bundle apps do not use tabs, action overrides, or flexipages."
metadata:
  version: "1.0"
---

# Custom Application for React UI Bundles
Create and configure a Salesforce Custom Application that hosts a React UI bundle in Lightning Experience. This skill generates the CustomApplication metadata so the app appears in the Lightning App Launcher and can be accessed by internal users.

Custom Applications differ from Experience Sites: they don't need Networks, CustomSite, DigitalExperienceConfig, or DigitalExperienceBundle metadata. The Custom Application acts as a thin launcher entry that delegates rendering to the React UI bundle referenced by `uiBundle`.

## Required Properties
Resolve all properties before generating any metadata. Each has a fallback chain — work through each option in order until a value is found.

| Property | Format | How to Resolve |
|----------|--------|----------------|
| **appName** | `lowercamelcase` (e.g., `myInternalApp`) | The UI bundle name from `uiBundles/<name>/` directory |
| **appNamespace** | String | `namespace` in `sfdx-project.json` → `sf data query -q "SELECT NamespacePrefix FROM Organization" --target-org ${usernameOrAlias}` → default `c` |
| **appLabel** | Human-readable string | User-provided, or derive from appName by converting camelCase to Title Case |

The `appNamespace` and `appName` connect the Custom Application to the correct React UI bundle. In newer API versions this uses `<uiBundle>{appNamespace}__{appName}</uiBundle>`; in older versions it uses `<webApplication>{appName}</webApplication>`. Getting this wrong means the app launcher entry exists but shows a blank page. Step 2 of the workflow determines which field to use.

## Generation Workflow
### Step 1: Resolve All Required Properties
Determine values for all properties before constructing anything. Use the resolution strategies in the table above.

### Step 2: Query API Context (Version-Aware Field Discovery)
Call `salesforce-api-context` MCP tools to discover which fields exist for the target org's API version. This ensures the generated metadata is compatible with the user's Salesforce version.

**Required calls:**
1. Call `get_metadata_type_fields` for `CustomApplication` — check whether the `uiBundle` field exists
2. Call `get_metadata_type_fields` for `UIBundle` — check whether the `target` field exists

**Field resolution based on API response:**

| Field Check | If present | If absent (older API version) |
|-------------|-----------|-------------------------------|
| `CustomApplication.uiBundle` | Use `<uiBundle>{appNamespace}__{appName}</uiBundle>` | Use `<webApplication>{appName}</webApplication>` (no namespace) |
| `UIBundle.target` | Use `<target>CustomApplication</target>` | Omit the `<target>` element entirely |

If `salesforce-api-context` is unavailable after a real attempt, fall back to the newer field names (`uiBundle` + `target`).

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
- If Step 2 determined the older field names apply, substitute `<uiBundle>` with `<webApplication>` in the generated output.

### Step 5: Update UI Bundle Meta XML
If Step 2 confirmed the `target` field exists on `UIBundle`, add `<target>CustomApplication</target>` to the `.uibundle-meta.xml` file (skip if the field doesn't exist in the org's API version):

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
- [ ] API context was queried to determine available fields (Step 2)
- [ ] `applications/{appName}.app-meta.xml` exists with correct content
- [ ] The bundle reference field matches the org's API version (`<uiBundle>` or `<webApplication>`)
- [ ] If `target` field is supported: `.uibundle-meta.xml` has `<target>CustomApplication</target>`
- [ ] Deployment validates successfully:
```bash
sf project deploy validate --metadata CustomApplication UIBundle --target-org ${usernameOrAlias}
```
