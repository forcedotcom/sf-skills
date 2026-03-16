---
name: commerce-b2b-open-code-integration
description: Integrate Salesforce B2B Commerce open source components from GitHub into B2B Commerce stores. Use when users mention "integrate open code components", "open source B2B commerce", "replace OOTB components", "forcedotcom/b2b-commerce-open-source-components", or want to add/replace commerce components with open source versions. Handles component integration, dependency resolution, and OOTB component replacement.
license: Apache-2.0
compatibility: Requires Salesforce CLI (sf), Git, B2B Commerce license, and Experience Builder access
metadata:
  author: afv-library
  version: "1.0"
---

## When to Use This Skill

Use this skill when you need to:
- Integrate all open source B2B Commerce components into a store
- Replace all OOTB (out-of-the-box) components with open code equivalents
- Replace specific OOTB components with open code versions
- Add open source components to a new or existing B2B Commerce store
- Copy components with automatic dependency resolution

## Specification

## Overview

This skill enables integration of open source B2B Commerce components from the official Salesforce repository (https://github.com/forcedotcom/b2b-commerce-open-source-components) into existing or new B2B Commerce stores.

**Three main scenarios:**
1. **Integrate** - Add all open code components to a store (components become available in Experience Builder)
2. **Replace All** - Replace all OOTB components with open code equivalents in site metadata
3. **Replace Specific** - Replace individual OOTB components with open code equivalents

---

## Prerequisites Flow

### Store Selection/Creation

**Step 1: Check for Existing Store or Create New**

Ask user: "Would you like to work with an existing B2B store or create a new one?"

**Step 2: If Creating New Store**

- Prompt agent: "Create a Commerce B2B Store"
- Reference existing rules: `rules/commerce/commerce-b2b-store-requirements.md`
- Reference existing prompts: `prompts/commerce/create-retrieve-b2b-storefront.md`
- Wait for store creation to complete before proceeding

**Step 3: If Selecting Existing Store**

- Run: `sf org list metadata --metadata-type DigitalExperienceConfig --json`
- Parse response and extract `fullName` values
- Display list to user: "Please select a store from the following:"
- Capture user selection

### Site Metadata Verification

**Step 4: Check Local Site Metadata**

Check if path exists: `force-app/main/default/digitalExperiences/site/<selected-store-name>`

**Step 5: If Site Metadata NOT Present**

Automatically retrieve: `sf project retrieve start -m DigitalExperienceBundle:site/<selected-store-name>`

Use the `fullName` value from Step 3.

**Step 6: If Site Metadata Already Present**

- Ask user: "Site metadata already exists locally. Do you want to overwrite with latest from org? (y/n)"
- If yes: Run `sf project retrieve start -m DigitalExperienceBundle:site/<selected-store-name>`
- If no: Proceed with existing local metadata

---

## Core Tasks

### Task 1: Clone Open Source Repository

**Purpose:** Clone the B2B Commerce open source components repository

**Steps:**

1. Check if repo already cloned in tmp folder: `/tmp/b2b-commerce-open-source-components`
2. If exists:
   - Warn user: "Repository already cloned. Cloning again will overwrite any local changes. Continue? (y/n)"
   - If no: Skip to next task
   - If yes: Remove existing and proceed
3. Clone: `git clone https://github.com/forcedotcom/b2b-commerce-open-source-components /tmp/b2b-commerce-open-source-components`
4. Verify clone successful

### Task 2: Copy All Open Code Resources

**Purpose:** Copy all components and labels from repo to selected site

**Source Paths (from cloned repo):**
- Components: `force-app/main/default/sfdc_cms__lwc/*`
- Labels: `force-app/main/default/sfdc_cms__label/*`

**Destination Paths (local project):**
- Components: `force-app/main/default/digitalExperiences/site/<selected-store-name>/sfdc_cms__lwc/`
- Labels: `force-app/main/default/digitalExperiences/site/<selected-store-name>/sfdc_cms__label/`

**Steps:**

1. Check if destination directories already contain files
2. If files exist:
   - Warn user: "Components already exist. This will overwrite existing changes. Continue? (y/n)"
   - If no: Proceed with copying only new files (skip existing)
   - If yes: Overwrite all
3. Copy all component directories from source to destination
4. Copy all label directories from source to destination
5. Report: "Copied X components and Y label sets"

### Task 3: Copy Specific Open Code Component

**Purpose:** Copy a single component with all its dependencies

**Inputs:**
- Component name (e.g., "cartBadge")

**Steps:**

**1. Check if Component Exists**

Verify source exists: `/tmp/b2b-commerce-open-source-components/force-app/main/default/sfdc_cms__lwc/<component-name>`

If not found: Error and list available components

**2. Check Destination**

- Check if already exists: `force-app/main/default/digitalExperiences/site/<selected-store-name>/sfdc_cms__lwc/<component-name>`
- If exists: Ask to overwrite
- If no: Skip this component

**3. Identify Dependencies**

Scan the component files for:

**a) HTML Dependencies:** `<site-*>` tags
```html
<!-- Example: <site-cart-badge-ui> -->
```
Pattern: Extract component name from `<site-{component-name}>`, component-name is kebab case, needs to be converted to camelCase

**b) JavaScript Dependencies:** `import ... from 'site/*'`
```javascript
// Example: import { handleAddToCartSuccessWithToast } from 'site/productAddToCartUtils'
```
Pattern: Extract module name after `site/`

**c) Label Dependencies:** `@salesforce/label/site.<component-name>.*`
```javascript
// Example: import maximumCount from '@salesforce/label/site.cartBadge.maximumCount';
```
Pattern: Extract component name between `site.` and next `.`

**4. Copy Component and Dependencies**

- Copy main component directory
- For each dependency found:
  - Copy dependent component from: `sfdc_cms__lwc/<dependency-name>`
  - Copy dependent labels from: `sfdc_cms__label/<dependency-name>` (if exists)
- Recursively resolve dependencies (dependencies may have dependencies)

**5. Report:**
- "Copied component: {component-name}"
- "Copied dependencies: {list of dependencies}"

### Task 4: Extract All OOTB Components from Site Metadata

**Purpose:** Identify all OOTB components currently used in the site

**Steps:**

**1. Scan Theme Layouts**

- Search in: `force-app/main/default/digitalExperiences/site/<selected-store-name>/sfdc_cms__themeLayout/*/content.json`
- Parse each `content.json` file
- Extract values from `"definition"` keys

**2. Scan Views**

- Search in: `force-app/main/default/digitalExperiences/site/<selected-store-name>/sfdc_cms__view/*/content.json`
- Parse each `content.json` file
- Extract values from `"definition"` keys

**3. Filter OOTB Components**

Keep only components matching patterns:
- `commerce_builder/*`
- `commerce_cart/*`
- `commerce/*`
- `commerce_my_account/*`

**4. Return List**

Deduplicated list of OOTB component definitions

Example: `["commerce_builder:cartBadge", "commerce_builder:cartContents", "commerce/searchInput"]`

### Task 5: Find Specific OOTB Component in Site Metadata

**Purpose:** Check if a specific OOTB component is used in the site

**Inputs:**
- OOTB component name (e.g., "commerce_builder:cartBadge")

**Steps:**

1. Run Task 4 to get all OOTB components
2. Check if input component exists in the list
3. If found: Return true with locations (which content.json files)
4. If not found:
   - Inform user: "Component {name} not found in site metadata"
   - Display: "Components currently used in this site:"
   - List all found components
   - Ask: "Would you like to replace one of these instead?"

### Task 6: Replace OOTB Component with Open Code Component

**Purpose:** Map and replace OOTB component references with open code equivalents

**Component Naming Pattern:**

OOTB components follow pattern: `{namespace}:{componentName}`
Open code components follow pattern: `site/{domain}{Context}[{Variant}]` in camelCase

**Mapping Rules:**

| OOTB Pattern | Open Code Pattern | Notes |
|--------------|-------------------|-------|
| `commerce_builder/{name}` | `site/{name}` | Builder components |
| `commerce_cart/{name}` | `site/cart{Name}Ui` | Cart runtime with Ui suffix |
| `commerce/{name}` | `site/{name}Ui` | Runtime components with Ui suffix |
| `commerce/error` | `site/commonError` | Shared utilities use "common" domain |
| `commerce_builder/formattedCurrency` | `site/commonFormattedCurrency` | Common utilities |
| `commerce/formattedCurrency` | `site/commonFormattedCurrencyUi` | Runtime with Ui suffix |
| `commerce_my_account/myAccountLayout` | `site/themelayoutMyaccount` | Account layouts |
| `commerce/layoutSite` | `site/themelayoutSite` | Layout → themelayout domain |

**Example Mappings:**

```
commerce_builder:cartContents → site:cartContents
commerce_cart:items → site:cartItemsUi
commerce_builder:searchInput → site:searchInput
commerce:searchInput → site:searchInputUi
commerce:error → site:commonError
commerce_my_account:myAccountLayout → site:themelayoutMyaccount
```

**Steps:**

**1. Parse OOTB Component Name**

Extract namespace, category, and component name

**2. Apply Mapping Rules**

- Match against mapping table
- Generate open code component name

**3. Verify Open Code Component Exists**

- Check in cloned repo: `/tmp/b2b-commerce-open-source-components/force-app/main/default/sfdc_cms__lwc/`
- Look for camelCase directory name (e.g., "cartBadge" for "site:cartBadge")

**4. If Not Found**

- List all available open code components from repo
- Ask user: "No direct mapping found. Would you like to select from available components?"

**5. Update Site Metadata**

- For each `content.json` file where component is found:
  - Replace `"definition": "commerce_builder:cartBadge"`
  - With `"definition": "site:cartBadge"`
- Preserve all other properties in the JSON

**6. Track Changes**

- Log all files modified
- Count replacements made

---

## Use Case Workflows

### Use Case 1: Only Integrate Open Code Components

**User Intent:** "Integrate open code components to my store"

**Workflow:**

1. Execute Prerequisites Flow
2. Execute Task 1: Clone Open Source Repository
3. Execute Task 2: Copy All Open Code Resources
4. Provide next steps:

```
✅ Integration Complete!

Next Steps:
1. Deploy components to your org:
   sf project deploy start -d force-app/main/default/digitalExperiences/site/<store-name>

2. Open Experience Builder:
   - Navigate to your store in Experience Builder
   - The new components will appear in the component palette
   - Drag and drop them into your pages
   - Configure and test each component

3. Publish your site when ready
```

### Use Case 2: Replace All OOTB Components

**User Intent:** "Replace all OOTB components with open code versions"

**Workflow:**

1. Execute Prerequisites Flow
2. Execute Task 1: Clone Open Source Repository
3. Execute Task 2: Copy All Open Code Resources
4. Execute Task 4: Extract All OOTB Components
5. For each OOTB component found:
   - Execute Task 6: Replace OOTB Component
   - If successful: Log replacement
   - If mapping not found: Log warning and continue
6. Report summary:

```
✅ Replacement Complete!

Summary:
- Total OOTB components found: X
- Successfully replaced: Y
- Could not map: Z (list them)

Modified files:
- List of all content.json files changed

Next Steps:
1. Review changes:
   git diff force-app/main/default/digitalExperiences/site/<store-name>

2. Deploy to org:
   sf project deploy start -d force-app/main/default/digitalExperiences/site/<store-name>

3. Test the store thoroughly in Experience Builder
```

### Use Case 3: Replace Specific Component

**User Intent:** "Replace cartBadge with open code version"

**Workflow:**

1. Execute Prerequisites Flow
2. Execute Task 1: Clone Open Source Repository
3. Extract component name from user intent (e.g., "cartBadge")
4. Determine OOTB format:
   - If user provides "commerce_builder:cartBadge" → use as-is
   - If user provides "cartBadge" → try common patterns:
     - First try: `commerce_builder:cartBadge`
     - Then try: `commerce_cart:cartBadge`
     - Then try: `commerce:cartBadge`
5. Execute Task 5: Find Specific OOTB Component
6. If found:
   - Execute Task 6: Replace OOTB Component
   - Determine open code component name from mapping
   - Execute Task 3: Copy Specific Open Code Component
7. Report:

```
✅ Component Replacement Complete!

Replaced: commerce_builder:cartBadge → site:cartBadge

Copied components:
- cartBadge (main)
- cartBadgeUi (dependency)
- productAddToCartUtils (dependency)

Copied labels:
- cartBadge labels

Modified files:
- List of content.json files updated

Next Steps:
1. Review changes and deploy:
   sf project deploy start -d force-app/main/default/digitalExperiences/site/<store-name>

2. Test the component in Experience Builder
```

---

## Error Handling

### Common Errors and Responses

**1. Store Not Found**
- Message: "Store '{name}' not found in org. Would you like to see available stores?"
- Action: List stores again

**2. Component Not Found in Repo**
- Message: "Component '{name}' not found in open source repo."
- Action: List available components from repo

**3. Component Not Used in Site**
- Message: "Component '{name}' is not currently used in this site."
- Action: Show components that are used

**4. No OOTB Components Found**
- Message: "No OOTB commerce components found in site metadata. The site may already be using open code components."
- Action: Offer to integrate all components instead

**5. Git Clone Failed**
- Message: "Failed to clone repository. Check internet connection."
- Action: Retry or abort

**6. File Copy Failed**
- Message: "Failed to copy files. Check file permissions."
- Action: Show error details and abort

**7. No Mapping Found**
- Message: "No direct mapping found for '{ootb-component}' to open code component."
- Action: Show available components and ask user to manually select

---

## Verification Checklist

Before completing the integration, verify:

### Store Setup
- [ ] Store has been selected or created successfully
- [ ] Site metadata has been retrieved to local project
- [ ] Site metadata path exists and is accessible

### Repository
- [ ] Open source repository cloned successfully to `/tmp/b2b-commerce-open-source-components`
- [ ] Repository contains expected directories: `sfdc_cms__lwc` and `sfdc_cms__label`

### Component Integration
- [ ] Components copied to correct destination path
- [ ] Labels copied to correct destination path
- [ ] All dependencies identified and copied (if specific component)
- [ ] No file permission errors during copy

### Component Replacement (if applicable)
- [ ] All OOTB components identified correctly
- [ ] Mapping applied correctly for each component
- [ ] `content.json` files updated with new component definitions
- [ ] No JSON syntax errors introduced
- [ ] Original JSON structure preserved (only `definition` value changed)

### Deployment Readiness
- [ ] All files are in correct directory structure
- [ ] No git conflicts or unstaged changes blocking deployment
- [ ] Deployment command provided to user
- [ ] User informed about testing requirements

---

## Anti-Patterns to Avoid

**❌ DO NOT:**
- Copy components without checking for existing files first
- Modify component code or labels from the open source repo
- Replace components without verifying they exist in site metadata
- Skip dependency resolution for specific component copies
- Deploy without user confirmation
- Continue on error without informing user
- Clone repository multiple times unnecessarily
- Modify content.json structure beyond the `definition` value
- Add components to wrong site directory
- Skip verification of open code component existence before replacement

**✅ DO:**
- Always warn before overwriting existing files
- Always verify paths and existence before operations
- Always inform user of next steps
- Always provide clear error messages
- Always track and report changes made
- Always preserve JSON structure when updating metadata
- Always resolve dependencies recursively
- Always verify mappings exist before replacement
