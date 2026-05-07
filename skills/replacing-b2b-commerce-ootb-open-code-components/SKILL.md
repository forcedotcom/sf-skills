---
name: replacing-b2b-commerce-ootb-open-code-components
description: Replace OOTB (out-of-the-box) B2B Commerce components with open source equivalents in site metadata content.json files, or look up the equivalent open code `site:` component for OOTB definitions. Use when users mention "replace OOTB components", "replace commerce components with open code", "swap OOTB for open source", "replace commerce_builder:", "replace OOTB in site", "replace component in site metadata", "replace component definition", "find open code equivalent", "equivalent open code component", "OOTB to open code mapping", "what is the site component for", components "in this view" or "for a given view", or a specific list of component names — and want to update or only discover mappings in their store metadata.
license: Apache-2.0
compatibility: Requires integrating-b2b-commerce-open-code-components skill as prerequisite
allowed-tools: Bash Read Write
metadata:
  author: afv-library
  version: "1.0"
---

## When to Use This Skill

Use this skill when you need to:
- Replace OOTB B2B Commerce components with open code equivalents
- Update component definitions in site metadata `content.json` files
- Swap out-of-the-box commerce components for open source versions
- **Find the equivalent open code (`site:`) component** for one or more OOTB `commerce_builder:` / `commerce:` definitions — using the mapping table and verifying availability in the cloned open code repo
- **Scope discovery or replacement to a given Experience Builder view** — scan only that view’s `sfdc_cms__view/<ViewName>/content.json` (or the paths the user names) instead of the whole site
- **Answer “what open code component replaces X?”** when the user gives explicit component name(s) — look up each in the mapping table, report `site:` targets, and note unmapped entries or targets missing from the repo (no `content.json` edits unless the user also asks to replace)

**Trigger phrases:** “replace OOTB components with open code components”, “find equivalent open code”, “open code equivalent for OOTB”, “map commerce_builder to site”, “components in this view”, “for the Product Detail view”, “replace only these components: …”.

## Rules

1. **Always explain before executing.** Before running any command, you MUST tell the user what the command does and why you are running it. Never just show a raw command and ask for permission.
2. **ONLY use the mapping table in this skill.** The JSON mapping table below is the ONLY source of truth for OOTB-to-open-code component names. NEVER guess, infer, or hallucinate component names. If a component is not in the mapping table, tell the user there is no known mapping — do not make one up.
3. **Use Read and Write tools for JSON files.** Use the Read tool to parse `content.json` files and the Write tool to update them. Do NOT use bash to parse or edit JSON — no sed, awk, perl, or regex on JSON content. Bash is only for **simple file discovery** (`grep -rl`, `find`, `ls`) — never for extracting or modifying JSON values.
4. **Minimize commands.** Batch work into as few commands as possible. Use a single grep to scan all files, a single ls to verify the repo, and one Read/Write pass per file. Do NOT run a separate command for every component or every directory.
5. **Follow the workflow steps exactly.** Do not invent additional options, policies, or frameworks. Execute each step and show the user the results before proceeding.
6. **Always replace with `site:` after verifying in the open code repo.** For every replacement, the new `"definition"` MUST be the mapped value from the table below, which always uses the `site:` namespace (for example `site:productHeading`). Before changing `content.json`, verify the target exists in the cloned open code components repository — for example by confirming the corresponding bundle under `.tmp/b2b-commerce-open-source-components/force-app/main/default/sfdc_cms__lwc/` (or the path your integrating skill documents). If the mapped `site:` component is not present in the repo, **do not replace** — skip it and report it under “not in repo” (same as Step 1 categorization).

## Overview

This skill replaces OOTB B2B Commerce component definitions in site metadata `content.json` files with their open source equivalents. It uses an authoritative mapping table of 64 component pairs extracted from `ui-commerce-components/scripts/moduleConfig.js`.

**Modes:** **Full replace** runs the scan (Step 1), user selection if needed, then `content.json` updates (Step 2–3). **Lookup only** (user asks for equivalents but not to change files): use the same mapping table and repo verification (Rule 2 and Rule 6), report OOTB → `site:` for the named components or for definitions found in the scoped `content.json` — **do not** call Write unless the user confirms replacement. **View-scoped** work: limit file discovery and reads to `sfdc_cms__view/<ViewName>/` (or the path the user gives) instead of all views.

---

## Prerequisites

Before replacing components, delegate to the **integrating-b2b-commerce-open-code-components** skill (`skills/integrating-b2b-commerce-open-code-components/SKILL.md`) to ensure:

1. Open source repository is cloned at `.tmp/b2b-commerce-open-source-components`
2. Store is selected and site metadata is retrieved locally
3. Open code components are copied to the store's site metadata

Tell user: "Before replacing components, I need to verify that the open code components are set up in your store. Let me check..."

If any prerequisite is not met, the integrating skill will handle it. Once all checks pass, proceed to the replacement workflow.

**Required state** after prerequisites:
- **Store name** — e.g., `My_B2B_Store1`
- **Site metadata path** — `force-app/main/default/digitalExperiences/site/<store-name>/`
- **Repo path** — `.tmp/b2b-commerce-open-source-components/`

---

## Replacement Workflow

### Step 1: Scan Site and Cross-Reference Mapping

**This step is MANDATORY.** Always scan the site first before attempting any replacements.

Tell user: "I'm scanning your store's site metadata to find all OOTB commerce components currently in use and checking which have open code equivalents."

**Step 1a — Find affected files** (one command, simple literal match):

```bash
grep -rl '"commerce' \
  force-app/main/default/digitalExperiences/site/<store-name>/sfdc_cms__view/ \
  force-app/main/default/digitalExperiences/site/<store-name>/sfdc_cms__themeLayout/ \
  --include="content.json"
```

**Step 1b — Read and parse** each matched file using the **Read** tool. Extract all `"definition"` values that start with `commerce` (e.g., `commerce_builder:cartBadge`). Collect a deduplicated list of OOTB components across all files.

**Step 1c — List repo components** (one command):

```bash
ls .tmp/b2b-commerce-open-source-components/force-app/main/default/sfdc_cms__lwc/
```

Using the parsed definitions, the `ls` output, and the mapping table, categorize every discovered OOTB component into three groups:

**Show the user a breakdown and a selectable list:**

First, inform the user about skipped and unmapped components:
```
Found X OOTB components in your site:

In mapping table but NOT in repo (skipping):
  - commerce_builder:quoteSummary → site:quoteSummary (not found in repo)

No mapping available (not in mapping table):
  - commerce_builder:actionButtons
  - commerce_builder:layoutHeaderOne
  - commerce_builder:searchInputContainer
  - commerce_builder:myAccountMegaMenu
```

Then present the replaceable components as a **multi-select list** using the AskQuestion tool (allow_multiple: true) so the user can pick from checkboxes instead of typing. Include an "All of the above" option:

```
Which components would you like to replace?

☐ commerce_builder:heading → site:productHeading
☐ commerce_builder:cartBadge → site:cartBadge
☐ commerce_builder:searchInput → site:searchInput
☐ All of the above
```

If user provided specific component name(s) in the original request, pre-filter to those and skip the selection prompt.

### Step 2: Replace in content.json

Tell user: "I'm now replacing the selected OOTB component definitions with their open code equivalents in your site's content.json files."

The affected files are already known from Step 1. For each file that contains selected components:
1. Use the **Read** tool to read the file
2. For each selected OOTB component, confirm again that the mapped **`site:`** target from the mapping table exists in the open code repo (per Rule 6). Only proceed with replacements that pass this check.
3. Replace all matching `"definition"` values with their mapped open code equivalents — **always** the exact `site:<name>` string from the mapping table
   - Example: `"definition": "commerce_builder:heading"` → `"definition": "site:productHeading"`
4. Use the **Write** tool to save the updated file
5. Preserve all other JSON properties — only `"definition"` values change

**Batch efficiently:** if a file contains multiple OOTB components, apply ALL replacements in a single Read → modify → Write pass. Do NOT read and write the same file multiple times.

### Step 3: Report

```
✅ Replacement Complete!

Replaced X components across Y files:
- commerce_builder:heading → site:productHeading (3 files)
- commerce_builder:cartBadge → site:cartBadge (2 files)
- commerce_builder:searchInput → site:searchInput (4 files)

Skipped (not in repo):
- commerce_builder:quoteSummary

No mapping available (left unchanged):
- commerce_builder:actionButtons
- commerce_builder:layoutHeaderOne
- commerce_builder:searchInputContainer

Modified files:
- sfdc_cms__view/Home/content.json
- sfdc_cms__view/Product_Detail/content.json
- sfdc_cms__themeLayout/DefaultTheme/content.json

Next Steps:
1. Deploy: sf project deploy start -d force-app/main/default/digitalExperiences/site/<store-name>
2. Test the store thoroughly in Experience Builder
3. Publish your site when ready
```

---

## OOTB to Open Code Mapping

**Source:** ui-commerce-components/scripts/moduleConfig.js
**Total Mappings:** 64

```json
{
  "commerce_builder:actionButton": "site:commonButton",
  "commerce_builder:b2bCartContents": "site:cartB2bCartContents",
  "commerce_builder:cartAppliedPromotion": "site:cartPromotionApplied",
  "commerce_builder:cartApplyCoupon": "site:cartApplyCoupon",
  "commerce_builder:cartBadge": "site:cartBadge",
  "commerce_builder:cartPromotions": "site:cartPromotions",
  "commerce_builder:cartSummary": "site:cartSummary",
  "commerce_builder:checkoutButton": "site:checkoutButton",
  "commerce_builder:checkoutDeliveryAddress": "site:checkoutDeliveryAddress",
  "commerce_builder:checkoutDeliveryMethod": "site:checkoutDeliverymethod",
  "commerce_builder:checkoutGiftOptions": "site:checkoutGiftOptions",
  "commerce_builder:checkoutNotification": "site:checkoutNotification",
  "commerce_builder:checkoutPurchaseOrder": "site:checkoutPurchaseOrder",
  "commerce_builder:checkoutShippingInstructions": "site:checkoutShippingInstructions",
  "commerce_builder:checkoutSubscriptionPolicyDisclaimer": "site:checkoutSubscriptionPolicyDisclaimer",
  "commerce_builder:consentBlanket": "site:legalConsentBlanket",
  "commerce_builder:countryPickerV2": "site:commonCountryPicker",
  "commerce_builder:drilldownNavigation": "site:commonDrilldownNavigation",
  "commerce_builder:formattedCurrency": "site:commonFormattedCurrency",
  "commerce_builder:heading": "site:productHeading",
  "commerce_builder:layoutFooter": "site:layoutFooter",
  "commerce_builder:layoutHeaderSimple": "site:layoutHeaderSimple",
  "commerce_builder:linkList": "site:commonLinksList",
  "commerce_builder:myAccountAddressContainer": "site:myaccountAddress",
  "commerce_builder:navigationMenuItemList": "site:myaccountNavigationMenuItems",
  "commerce_builder:orderConfirmationBillingDetails": "site:orderConfirmationDetailsBilling",
  "commerce_builder:orderConfirmationDeliveryGroup": "site:orderConfirmationDeliverygroup",
  "commerce_builder:orderConfirmationErrorMessage": "site:orderConfirmationMessageError",
  "commerce_builder:orderConfirmationSuccessMessage": "site:orderConfirmationMessageSuccess",
  "commerce_builder:orderDetails": "site:orderDetails",
  "commerce_builder:orderList": "site:orderList",
  "commerce_builder:orderListDateFilter": "site:orderListDateFilter",
  "commerce_builder:orderProductsInfo": "site:orderProducts",
  "commerce_builder:orderPromotionsSummary": "site:orderPromotions",
  "commerce_builder:orderShipmentTracker": "site:orderShipmentTracker",
  "commerce_builder:paymentByExpress": "site:paymentByExpress",
  "commerce_builder:productAttachments": "site:productAttachments",
  "commerce_builder:productBundle": "site:productBundle",
  "commerce_builder:productBundleItem": "site:productBundleItem",
  "commerce_builder:productFieldsTable": "site:productFieldsTable",
  "commerce_builder:productFrequentlyBoughtTogether": "site:productFrequentlyBoughtTogether",
  "commerce_builder:productMediaGallery": "site:productMediaGallery",
  "commerce_builder:productPricingDetails": "site:productPricingDetails",
  "commerce_builder:productSellingModelSelector": "site:productSellingmodelSelector",
  "commerce_builder:productSet": "site:productSet",
  "commerce_builder:promotionDiscountsApproaching": "site:promotionDiscountsApproaching",
  "commerce_builder:purchaseOptions": "site:productPurchaseOptions",
  "commerce_builder:purchasedProducts": "site:productListPurchased",
  "commerce_builder:quickOrder": "site:orderQuickOrder",
  "commerce_builder:quoteSummary": "site:quoteSummary",
  "commerce_builder:searchFilters": "site:searchFilters",
  "commerce_builder:searchInput": "site:searchInput",
  "commerce_builder:searchNoResultsLayout": "site:searchResultsLayoutEmpty",
  "commerce_builder:searchResults": "site:searchResults",
  "commerce_builder:searchResultsLayout": "site:searchResultsLayout",
  "commerce_builder:searchSortMenu": "site:searchSortMenu",
  "commerce_builder:socialLinks": "site:commonLinksSocial",
  "commerce_builder:splitShipmentHeader": "site:cartSplitshipmentHeader",
  "commerce_builder:stickyContainer": "site:commonContainerSticky",
  "commerce_builder:subscriptions": "site:productSubscriptions",
  "commerce_builder:userProfileMenu": "site:myAccountUserProfileMenu",
  "commerce_builder:variantSelector": "site:productVariantSelector",
  "commerce_builder:wishlist": "site:productWishlist",
  "commerce_builder:wishlistShortcut": "site:productWishlistShortcut"
}
```

---

## Example Interaction

**User:** "Replace OOTB components with open code versions"

**Agent:** "Before replacing components, I need to verify that the open code components are set up in your store. Let me check..."
- ✓ Open source repo cloned
- ✓ Store metadata available for My_B2B_Store1
- ✓ Open code components are integrated

**Agent:** "I'm scanning your store's site metadata to find all OOTB commerce components and checking which have open code equivalents."

_(Runs grep -rl to find files with commerce definitions, Reads those files to extract component names, runs ls to list repo components, then cross-references with mapping table)_

```
Found 8 OOTB components in your site:

No mapping available (not in mapping table):
  - commerce_builder:searchInputContainer
  - commerce_builder:layoutHeaderOne
  - commerce_builder:myAccountMegaMenu
  - commerce_builder:actionButtons
```

**Agent** _(presents multi-select list via AskQuestion tool):_
```
Which components would you like to replace?

☐ commerce_builder:heading → site:productHeading
☐ commerce_builder:cartBadge → site:cartBadge
☐ commerce_builder:searchInput → site:searchInput
☐ commerce_builder:cartSummary → site:cartSummary
☐ All of the above
```

**User:** _(selects heading and cartBadge)_

**Agent:** "I'm now replacing the selected OOTB component definitions with their open code equivalents in your site's content.json files."

_(Files already known from scan — one Read/Write pass per affected file, all replacements batched)_

```
✅ Replacement Complete!

Replaced 2 components across 5 files:
- commerce_builder:heading → site:productHeading (3 files)
- commerce_builder:cartBadge → site:cartBadge (2 files)

No mapping available (left unchanged):
- commerce_builder:searchInputContainer
- commerce_builder:layoutHeaderOne
- commerce_builder:myAccountMegaMenu
- commerce_builder:actionButtons

Modified files:
- sfdc_cms__view/Home/content.json
- sfdc_cms__view/Product_Detail/content.json
- sfdc_cms__themeLayout/DefaultTheme/content.json

Next Steps:
1. Deploy: sf project deploy start -d force-app/main/default/digitalExperiences/site/My_B2B_Store1
2. Test the store thoroughly in Experience Builder
```

---

## Error Handling

| Error | Message | Action |
|-------|---------|--------|
| Prerequisites not met | "Open code components are not integrated yet." | Run integrating skill first |
| No mapping found | "No mapping found for '{component}'." | Show available mappings, report as unmapped |
| Component not in repo | "Open code component '{name}' not found in cloned repo." | Skip and inform user |
| No OOTB components in site | "No OOTB commerce components found in site metadata." | Inform user, nothing to replace |
| No replaceable components | "All OOTB components found are unmapped — none can be replaced." | Show the unmapped list, suggest checking for updated mappings |
| content.json parse error | "Failed to parse content.json: {file}" | Show error, skip file, continue with remaining files |

---

## Verification Checklist

- [ ] Prerequisites verified via integrating skill (repo, store, components)
- [ ] Site scanned + repo verified + mapping cross-referenced in minimal commands (Step 1)
- [ ] Each replacement uses the exact mapped `site:` definition and was verified present in the open code repo before write (Rule 6)
- [ ] Breakdown shown to user with three categories before proceeding
- [ ] User selected components to replace (or provided names)
- [ ] Each `content.json` file updated in a single Read → modify → Write pass
- [ ] JSON structure preserved, no syntax errors introduced
- [ ] User informed of skipped and unmapped components
- [ ] Deployment command provided

---

## Anti-Patterns

**DO NOT:**
- Skip the site scan step — ALWAYS scan first to discover actual OOTB components
- Use bash (sed, perl, awk, grep -o) to **parse or edit** JSON — use bash only for file discovery (`grep -rl`, `find`, `ls`)
- Run a separate command per component or per directory — batch into single commands
- Read the same file multiple times — apply all replacements for a file in one Read/Write pass
- Replace components without verifying the open code equivalent exists in the repo
- Write a `"definition"` that is not the exact mapped `site:` value from the table, or use any namespace other than `site:` for the replacement target
- Modify `content.json` structure beyond the `"definition"` value
- Skip prerequisite checks
- Replace components not in the mapping table
- Guess or hallucinate component mappings
- Invent additional options, policies, or frameworks beyond what this skill defines

**DO:**
- Use `grep -rl` to find affected files, then Read tool to parse JSON reliably
- Verify the repo with a single `ls` command
- Show the user a clear breakdown of replaceable, skipped, and unmapped components
- Use Read and Write tools for all JSON modifications
- Batch all replacements for the same file into one Read → modify → Write pass
- Explain each step before executing
- Verify prerequisites via the integrating skill
- Confirm each mapped `site:` component exists in the open code repo before replacing, and use only that exact `site:` string from the mapping table
- Show user the full replacement plan before executing
- Report all modified files and any skipped or unmapped components
