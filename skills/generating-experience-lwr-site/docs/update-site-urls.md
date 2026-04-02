# Updating Experience Site URLs

Experience sites have a three-component architecture with two distinct URL patterns. Understanding this structure is critical when updating site URLs.

## Architecture Overview

Every Salesforce Experience Site consists of three components:

1. **Network** (metadata: `Network`) - Network configuration
2. **ChatterNetwork Site** (metadata: `CustomSite`) - Authentication endpoints and core site services  
3. **ChatterNetworkPicasso Site** (metadata: `DigitalExperienceConfig` + `DigitalExperienceBundle`) - Customer-facing pages and content

## URL Pattern

These three components use **two different URLs**:

- **Primary URL** (ChatterNetworkPicasso): Used for customer-facing pages
  - Defined in: `DigitalExperienceConfig` → `<urlPathPrefix>`
  - Example: `mysite`

- **Secondary URL** (Network + CustomSite): Used for authentication endpoints and other services
  - Defined in: `Network` → `<urlPathPrefix>` AND `CustomSite` → `<urlPathPrefix>`
  - Example: `mysitevforcesite`
  - **Must be synchronized** - both files must have identical values

By default, Salesforce differentiates these URLs by appending `vforcesite` suffix to the Network/CustomSite URL.

## URL Update Workflow

When updating site URLs, follow this workflow:

### Step 1: Discover All URL References

Search for all occurrences of `urlPathPrefix` across the project metadata files.

**For agents**: Use the `search_files` tool with these parameters:
- path: `force-app/main/default`
- regex: `urlPathPrefix`
- file_pattern: `*.xml`

**For humans**: Use your IDE's search functionality or command line tools:
```bash
# Using grep
grep -r "urlPathPrefix" force-app/main/default --include="*.xml"

# Using VS Code: Ctrl+Shift+F (Windows/Linux) or Cmd+Shift+F (Mac)
# Search for: urlPathPrefix
# Files to include: *.xml
```

### Step 2: Identify URL Groups

Determine which files belong to which URL group:

- **Primary URL Group**: `DigitalExperienceConfig`
- **Secondary URL Group**: `Network` AND `CustomSite`

### Step 3: Update URLs Consistently

Update the `<urlPathPrefix>` value in each file:

- **DigitalExperienceConfig**: Update to new primary URL
- **Network**: Update to new secondary URL (typically primary URL + `vforcesite`)
- **CustomSite**: Update to **same value as Network** (must be synchronized)

### Step 4: Validate Naming Convention

Ensure URL values follow best practices:
- Use lowercase letters only
- Avoid special characters except hyphens where appropriate
- Keep URLs concise and meaningful

### Step 5: Verify Consistency

Before deploying, confirm:
- [ ] Primary URL in `DigitalExperienceConfig` is set correctly
- [ ] Secondary URL in `Network` matches `CustomSite` exactly
- [ ] URLs are properly differentiated (typically via suffix)
- [ ] All URL values follow naming conventions

## Example URL Configuration

```
ChatterNetworkPicasso Site (Primary):
  DigitalExperienceConfig: <urlPathPrefix>bestsupport</urlPathPrefix>

Network + ChatterNetwork Site (Secondary):
  Network:    <urlPathPrefix>bestsupportvforcesite</urlPathPrefix>
  CustomSite: <urlPathPrefix>bestsupportvforcesite</urlPathPrefix>
```

## Common Pitfalls to Avoid

❌ **Don't** update only one or two files - all three must be updated  
❌ **Don't** use different values in Network and CustomSite  
❌ **Don't** use the same URL for both Primary and Secondary groups  
❌ **Don't** skip the discovery step with `search_files`  
✅ **Do** use `search_files` to find all occurrences first  
✅ **Do** maintain URL differentiation between the two groups  
✅ **Do** follow lowercase naming conventions